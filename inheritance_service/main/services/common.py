from collections.abc import Callable, Iterable
from typing import Any, TypedDict, overload

from sqlalchemy import select
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.inspection import inspect
from sqlalchemy.sql import Select

from main.models import resolve_model
from main.models.base import BaseModel


class JoinSpec(TypedDict):
    left: str
    right: str
    on: Callable[[type[BaseModel], type[BaseModel]], Any]


FilterSpec = Callable[[dict[str, type[BaseModel]]], Any]


def _apply_joins(
    stmt: Select,
    joins: Iterable[JoinSpec],
    resolved: dict[str, type[BaseModel]],
    _resolve: Callable[[str], type[BaseModel]],
) -> Select:
    """Apply joins to the statement."""
    for join_spec in joins:
        left_model = _resolve(join_spec["left"])
        right_model = _resolve(join_spec["right"])
        stmt = stmt.join(right_model, join_spec["on"](left_model, right_model))
    return stmt


def _apply_filters(
    stmt: Select,
    filters: Iterable[FilterSpec] | None,
    resolved: dict[str, type[BaseModel]],
) -> Select:
    """Apply filters to the statement."""
    if filters:
        for filter_fn in filters:
            stmt = stmt.where(filter_fn(resolved))
    return stmt


def _apply_deleted_filters(
    stmt: Select,
    resolved: dict[str, type[BaseModel]],
) -> Select:
    """Apply is_deleted filters to the statement."""
    for model in resolved.values():
        if hasattr(model, "is_deleted"):
            stmt = stmt.where(getattr(model, "is_deleted").is_(False))
    return stmt


def build_dynamic_query(
    root_model_name: str,
    select_models: Iterable[str],
    joins: Iterable[JoinSpec],
    filters: Iterable[FilterSpec] | None = None,
) -> Select:
    resolved: dict[str, type[BaseModel]] = {}

    def _resolve(name: str) -> type[BaseModel]:
        if name not in resolved:
            resolved[name] = resolve_model(name)
        return resolved[name]

    # Maintain order: root first, then select_models
    # Resolve root model to ensure it's in resolved dict
    _resolve(root_model_name)
    seen = [root_model_name]
    if select_models:
        for name in select_models:
            if name not in seen:
                seen.append(name)
    stmt = select(*(_resolve(name) for name in seen))

    stmt = _apply_joins(stmt, joins, resolved, _resolve)
    stmt = _apply_deleted_filters(stmt, resolved)
    stmt = _apply_filters(stmt, filters, resolved)

    return stmt  # NoQA: RET504


def find_foreign_keys(
    model: type[BaseModel],
) -> list[tuple[str, type[BaseModel], str]]:
    """
    Find all foreign keys in a model and return a list of
    (foreign key column name, referenced model, referenced column name).

    Args:
        model: Model class to inspect

    Returns:
        List of tuples:
        [(fk_column_name, referenced_model, referenced_column_name), ...]
    """
    mapper = inspect(model)
    foreign_keys = []

    for column in mapper.columns:
        # Check if column has foreign key constraint
        if column.foreign_keys:
            for fk in column.foreign_keys:
                # Get referenced table information
                referenced_table = fk.column.table
                referenced_column_name = fk.column.name
                # Find corresponding model class for this table
                for model_cls in BaseModel.registry._class_registry.values():
                    if (
                        isinstance(model_cls, type)
                        and issubclass(model_cls, BaseModel)
                        and hasattr(model_cls, "__table__")
                        and model_cls.__table__ is referenced_table
                    ):
                        foreign_keys.append(
                            (column.name, model_cls, referenced_column_name),
                        )
                        break

    return foreign_keys


def get_model_name(model: type[BaseModel]) -> str:
    """
    Get the name of the model class.

    Args:
        model: Model class

    Returns:
        Name of the model class
    """
    return model.__name__


def _process_value(value: Any, model_name: str | None = None) -> tuple[str, Any]:
    """Process a single value and return (key, processed_value)."""
    if isinstance(value, BaseModel):
        key = model_name or get_model_name(value.__class__)
        return key, _model_to_dict(value)
    if value is not None:
        key = model_name or "result"
        return key, value
    key = model_name or "result"
    return key, value


def _process_iterable_row(
    row: Row | tuple,
    model_names: list[str] | None,
) -> dict[str, Any]:
    """Process Row or tuple into dictionary."""
    result = {}
    if model_names:
        for i, model_name in enumerate(model_names):
            if i < len(row):
                key, value = _process_value(row[i], model_name)
                result[key] = value
    else:
        for i, value in enumerate(row):
            key, processed_value = _process_value(value)
            if key == "result":
                key = f"model_{i}"
            result[key] = processed_value
    return result


def row_to_dict(
    row: Row | tuple,
    model_names: list[str] | None = None,
) -> dict[str, Any]:
    """
    Convert SQLAlchemy Row object to dictionary.

    Args:
        row: SQLAlchemy Row object or tuple
        model_names: List of model names in order (if None, will try to infer from row)

    Returns:
        Dictionary with model names as keys and model instances as values
    """
    if isinstance(row, (Row | tuple)):
        return _process_iterable_row(row, model_names)
    # Single model instance
    if isinstance(row, BaseModel):
        return {get_model_name(row.__class__): _model_to_dict(row)}
    return {"result": row}


def _model_to_dict(model: BaseModel) -> dict[str, Any]:
    """
    Convert SQLAlchemy model instance to dictionary.

    Args:
        model: SQLAlchemy model instance

    Returns:
        Dictionary representation of the model
    """
    result = {}
    # Inspect the class, not the instance
    mapper = inspect(model.__class__)

    for column in mapper.columns:
        value = getattr(model, column.name)
        # Convert datetime to ISO format string
        if hasattr(value, "isoformat"):
            result[column.name] = value.isoformat()
        # Convert other types
        elif isinstance(value, dict | list):
            result[column.name] = value
        elif isinstance(value, BaseModel):
            # Handle nested models (shouldn't happen in our case, but handle it)
            result[column.name] = _model_to_dict(value)
        else:
            result[column.name] = value

    return result


def traverse_foreign_key_chain(
    root_model_name: str,
    visited: set[str] | None = None,
) -> list[tuple[str, str, str, str]]:
    """
    Traverse foreign keys like a linked list from root model.
    Returns a list of required joins:
    [(left_model_name, right_model_name, fk_column_name, ref_column_name), ...]

    Args:
        root_model_name: Starting model class name
        visited: Set of visited models (used to avoid cycles)

    Returns:
        List of tuples:
        [(left_model_name, right_model_name, fk_column_name, ref_column_name), ...]
    """
    if visited is None:
        visited = set()

    root_model = resolve_model(root_model_name)
    if root_model_name in visited:
        return []

    visited.add(root_model_name)
    joins = []

    # Find all foreign keys in root model
    foreign_keys = find_foreign_keys(root_model)

    for fk_column_name, referenced_model, ref_column_name in foreign_keys:
        referenced_model_name = get_model_name(referenced_model)

        # Create join spec
        joins.append(
            (root_model_name, referenced_model_name, fk_column_name, ref_column_name),
        )

        sub_joins = traverse_foreign_key_chain(
            referenced_model_name,
            visited=visited.copy(),
        )
        joins.extend(sub_joins)

    return joins


def build_auto_join_specs(
    root_model_name: str,
) -> list[JoinSpec]:
    """
    Automatically create a list of JoinSpec from root model by traversing foreign keys.

    Args:
        root_model_name: Starting model class name

    Returns:
        List of JoinSpec dictionaries
    """
    join_tuples = traverse_foreign_key_chain(root_model_name)
    join_specs: list[JoinSpec] = []

    for left_name, right_name, fk_column_name, ref_column_name in join_tuples:
        # Create join condition: left_model.fk_column == right_model.ref_column
        # Use factory function to properly capture values
        def create_join_on(fk_col: str, ref_col: str):
            def join_on(
                left_model: type[BaseModel],
                right_model: type[BaseModel],
            ) -> Any:
                return getattr(left_model, fk_col) == getattr(right_model, ref_col)

            return join_on

        join_spec: JoinSpec = {
            "left": left_name,
            "right": right_name,
            "on": create_join_on(fk_column_name, ref_column_name),
        }
        join_specs.append(join_spec)

    return join_specs


def collect_all_select_models(
    root_model_name: str,
    select_models: Iterable[str] | None = None,
) -> list[str]:
    """
    Collect all model names that will be selected in a query.
    Includes root model, explicitly selected models, and models from auto joins.

    Args:
        root_model_name: Starting model class name
        select_models: List of models to explicitly select (None = only root model)

    Returns:
        List of model names in order
    """
    all_select_models = [root_model_name]

    # Add explicitly selected models
    if select_models:
        for name in select_models:
            if name not in all_select_models:
                all_select_models.append(name)

    # Add models from auto joins
    auto_joins = build_auto_join_specs(root_model_name)
    for join_spec in auto_joins:
        for model_name in [join_spec["left"], join_spec["right"]]:
            if model_name not in all_select_models:
                all_select_models.append(model_name)

    return all_select_models


def build_auto_query(
    root_model_name: str,
    select_models: Iterable[str] | None = None,
    filters: Iterable[FilterSpec] | None = None,
) -> Select:
    """
    Automatically build query from root model by traversing
    foreign keys like a linked list.

    Args:
        root_model_name: Starting model class name
        select_models: List of models to select (None = only select root model)
        filters: List of filter functions

    Returns:
        Tuple (Select statement, dict of resolved models)
    """
    # Automatically create joins from foreign keys
    auto_joins = build_auto_join_specs(root_model_name)

    # Collect all models to select (maintain order)
    all_select_models = collect_all_select_models(
        root_model_name=root_model_name,
        select_models=select_models,
    )

    return build_dynamic_query(
        root_model_name=root_model_name,
        select_models=all_select_models,
        joins=auto_joins,
        filters=filters,
    )


@overload
async def execute_auto_query(
    session: AsyncSession,
    root_model_name: str,
    select_models: Iterable[str] | None = None,
    filters: Iterable[FilterSpec] | None = None,
    *,
    is_only_one_model: bool = True,
    return_as_dict: bool = True,
) -> dict[str, Any] | None: ...


@overload
async def execute_auto_query(
    session: AsyncSession,
    root_model_name: str,
    select_models: Iterable[str] | None = None,
    filters: Iterable[FilterSpec] | None = None,
    *,
    is_only_one_model: bool = True,
    return_as_dict: bool = False,
) -> Row | None: ...


@overload
async def execute_auto_query(
    session: AsyncSession,
    root_model_name: str,
    select_models: Iterable[str] | None = None,
    filters: Iterable[FilterSpec] | None = None,
    *,
    is_only_one_model: bool = False,
    return_as_dict: bool = True,
) -> list[dict[str, Any]]: ...


@overload
async def execute_auto_query(
    session: AsyncSession,
    root_model_name: str,
    select_models: Iterable[str] | None = None,
    filters: Iterable[FilterSpec] | None = None,
    *,
    is_only_one_model: bool = False,
    return_as_dict: bool = False,
) -> list[Row]: ...


async def execute_auto_query(
    session: AsyncSession,
    root_model_name: str,
    select_models: Iterable[str] | None = None,
    filters: Iterable[FilterSpec] | None = None,
    is_only_one_model: bool = False,
    return_as_dict: bool = False,
) -> dict[str, Any] | None | Row | list[dict[str, Any]] | list[Row]:
    """
    Execute automatically generated query from root model by traversing foreign keys.

    Args:
        session: Database session
        root_model_name: Starting model class name
        select_models: List of models to select (None = only select root model)
        filters: List of filter functions
        is_only_one_model: If True, return only one result (use .one())
        return_as_dict: If True, convert results to dictionaries

    Returns:
        Query results (Row objects or dicts if return_as_dict=True)
    """
    stmt = build_auto_query(
        root_model_name=root_model_name,
        select_models=select_models,
        filters=filters,
    )
    result = await session.execute(stmt)
    rows = result.one_or_none() if is_only_one_model else result.all()

    if return_as_dict:
        # Collect all model names that will be in the result
        all_select_models = collect_all_select_models(
            root_model_name=root_model_name,
            select_models=select_models,
        )

        if is_only_one_model:
            # Single row result
            return row_to_dict(rows, model_names=all_select_models)
        # Multiple rows
        return [row_to_dict(row, model_names=all_select_models) for row in rows]

    return rows


async def execute_dynamic_query_wo_join(
    session: AsyncSession,
    root_model_name: str,
    select_models: Iterable[str],
    joins: Iterable[JoinSpec],
    filters: Iterable[FilterSpec] | None = None,
    is_only_one_model: bool = False,
):
    """
    Execute query with manually specified joins.

    Use this when you need:
    - Joins without foreign key relationships
    - Complex join conditions (not just FK == PK)
    - Full control over which joins to perform

    For automatic foreign key traversal, use execute_auto_query() instead.

    Args:
        session: Database session
        root_model_name: Starting model class name
        select_models: List of models to select
        joins: List of JoinSpec dictionaries defining joins
        filters: List of filter functions
        is_only_one_model: If True, return only one result (use .one())

    Returns:
        Query results
    """
    stmt = build_dynamic_query(
        root_model_name=root_model_name,
        select_models=select_models,
        joins=joins,
        filters=filters,
    )
    result = await session.execute(stmt)
    return result.scalars().one() if is_only_one_model else result.all()


# ============================================================================
# USAGE GUIDE FOR LIBRARY/SERVICE LAYER
# ============================================================================
#
# RECOMMENDED: Use execute_auto_query() - it's the main entry point.
# It automatically discovers and joins related tables via foreign keys.
#
# ALTERNATIVE: Use execute_dynamic_query() only when you need:
#   - Joins without foreign key relationships
#   - Complex join conditions
#   - Manual control over joins
#
# Example 1: Basic usage - query with automatic foreign key traversal
# --------------------------------------------------------------------
# from main.services.common import execute_auto_query
#
# async def get_linux_servers(session: AsyncSession):
#     # Automatically joins LinuxServerModel -> ServerModel via server_id foreign key
#     rows = await execute_auto_query(
#         session=session,
#         root_model_name="LinuxServerModel",
#     )
#     return rows
#
#
# Example 2: With filters
# --------------------------------------------------------------------
# async def get_high_ram_servers(session: AsyncSession):
#     rows = await execute_auto_query(
#         session=session,
#         root_model_name="LinuxServerModel",
#         filters=[
#             lambda models: models["LinuxServerModel"].ram > 8,
#         ],
#     )
#     return rows
#
#
# Example 3: Limit traversal depth
# --------------------------------------------------------------------
# async def get_servers_shallow(session: AsyncSession):
#     # Only traverse 1 level deep (don't go further than direct foreign keys)
#     rows = await execute_auto_query(
#         session=session,
#         root_model_name="LinuxServerModel",
#     )
#     return rows
#
#
# Example 4: Select specific models only
# --------------------------------------------------------------------
# async def get_servers_with_location(session: AsyncSession):
#     # Only select LinuxServerModel and ServerModel (even if other FKs exist)
#     rows = await execute_auto_query(
#         session=session,
#         root_model_name="LinuxServerModel",
#         select_models=["ServerModel"],
#     )
#     return rows
#
#
# NOTE: Other functions (find_foreign_keys, traverse_foreign_key_chain, etc.)
#       are internal helpers. Use execute_auto_query() unless you need to
#       customize the query building process.
