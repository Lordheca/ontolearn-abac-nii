import importlib
import inspect as py_inspect
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.inspection import inspect

from main.commons.resources.resource import Resource
from main.models import resolve_model
from main.models.base import BaseModel

from ..commons.constants import MODEL_TO_RESOURCE_CLASS_MAP
from .common import FilterSpec, execute_auto_query, find_foreign_keys, get_model_name


def _get_resource_class(resource_class_name: str) -> type[Resource]:
    """
    Dynamically import and return the resource class by name.

    Args:
        resource_class_name: Name of the resource class (e.g., "Server")

    Returns:
        The resource class

    Raises:
        ImportError: If the class cannot be imported
        AttributeError: If the class doesn't exist in the module
    """
    try:
        # Import from main.commons.resources module (classes are exported in __init__.py)
        module = importlib.import_module("main.commons.resources")
        resource_class = getattr(module, resource_class_name)
        if not issubclass(resource_class, Resource):
            raise TypeError(f"{resource_class_name} is not a subclass of Resource")
        return resource_class
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Cannot import resource class '{resource_class_name}': {e}")


def _map_model_to_resource_class(model_name: str) -> str:
    """
    Map model name to resource class name.

    Args:
        model_name: Model class name (e.g., "ServerModel")

    Returns:
        Resource class name (e.g., "Server")

    Raises:
        ValueError: If no mapping exists for the model name
    """
    resource_class_name = MODEL_TO_RESOURCE_CLASS_MAP.get(model_name)
    if not resource_class_name:
        raise ValueError(
            f"No resource class mapping found for model '{model_name}'. "
            f"Available mappings: {list(MODEL_TO_RESOURCE_CLASS_MAP.keys())}",
        )
    return resource_class_name


def _find_valid_environments_to_check(
    parent_instance: Resource | None,
) -> dict | None:
    """
    Recursively find the first valid environments_to_check from parent hierarchy.

    Args:
        parent_instance: Parent Resource instance to traverse

    Returns:
        First valid environments_to_check dict found, or None if not found
    """
    if not parent_instance:
        return None

    # Check current parent instance
    if hasattr(parent_instance, "environments_to_check"):
        envs = parent_instance.environments_to_check
        if envs and isinstance(envs, dict) and len(envs) > 0:
            return envs

    # Recursively check parent's parent
    if hasattr(parent_instance, "parent") and parent_instance.parent:
        return _find_valid_environments_to_check(parent_instance.parent)

    return None


def _create_resource_instance_from_model_data(
    resource_class: type[Resource],
    model_data: dict,
    parent_model_data: dict | None = None,
    parent_instance: Resource | None = None,
) -> Resource:
    """
    Create a resource instance from model data.
    If parent_model_data is provided, merge parent attributes into kwargs.
    If parent_instance is provided, set it as the parent of the child instance.
    Only passes parameters that the constructor actually accepts.

    Args:
        resource_class: The resource class to instantiate
        model_data: Dictionary containing model data
        parent_model_data: Optional parent model data (for inheritance - attributes are merged)
        parent_instance: Optional parent Resource instance to set as parent

    Returns:
        Resource instance
    """
    # Get constructor signature to know which parameters it accepts
    sig = py_inspect.signature(resource_class.__init__)
    accepted_params = set(sig.parameters.keys()) - {"self"}  # Exclude 'self'

    # Start with child model data
    combined_data = model_data.copy()

    # If parent model data exists, merge parent attributes into combined_data
    # Parent attributes take precedence (child can override)
    if parent_model_data:
        parent_resource_metadata = parent_model_data.get("resource_metadata", {}) or {}
        child_resource_metadata = combined_data.get("resource_metadata", {}) or {}

        # Merge resource_metadata (child overrides parent)
        merged_metadata = {**parent_resource_metadata, **child_resource_metadata}
        combined_data["resource_metadata"] = merged_metadata

        # Merge other fields from parent (child overrides parent)
        for key, value in parent_model_data.items():
            if key not in combined_data and key not in (
                "id",
                "created_at",
                "updated_at",
                "is_deleted",
            ):
                combined_data[key] = value

    resource_metadata = combined_data.get("resource_metadata", {}) or {}

    # Extract name from resource_metadata or use a default
    name = (
        resource_metadata.get("name", "") or combined_data.get("name", "") or "Unnamed"
    )

    kwargs = {
        "name": name,
        "parent": parent_instance,  # Use provided parent instance if available
    }

    # Add model-specific fields dynamically, but only if constructor accepts them
    # Exclude standard fields that are handled separately or not in constructor
    excluded_fields = {
        "id",
        "resource_metadata",
        "parent",
        "created_at",
        "updated_at",
        "is_deleted",
        "name",  # Already extracted from metadata and set in kwargs
        "description",  # Not in Resource constructor
        "tags",  # Not in Resource constructor
    }

    # Add fields from combined_data (excluding foreign key fields that point to parent)
    # Field names in models now match constructor parameter names directly
    # Example: ServerModel.location -> Server.location, LinuxServerModel.ram -> LinuxServer.ram
    for key, value in combined_data.items():
        if key not in excluded_fields and not key.endswith(
            "_id",
        ):  # Exclude foreign key columns
            # Use field name directly (no mapping needed since names match)
            # Only add if constructor accepts this parameter
            if key in accepted_params:
                kwargs[key] = value

    # Also add fields from resource_metadata that aren't standard fields
    # Standard fields (name, description, tags) are not passed to constructor
    standard_metadata_fields = {"name", "description", "tags"}
    for key, value in resource_metadata.items():
        if key not in standard_metadata_fields:
            # Use field name directly (no mapping needed since names match)
            # Only add if constructor accepts this parameter and not already in kwargs
            if key in accepted_params and key not in kwargs:
                kwargs[key] = value

    # Create resource instance dynamically
    resource_instance = resource_class(**kwargs)

    # Store environments_to_check from model data as instance attribute
    # This field is from ResourceBase but not in constructor, so we store it separately
    # If child has a valid (non-empty dict) environments_to_check, use it
    # Otherwise, inherit from parent hierarchy if parent has it
    child_environments = combined_data.get("environments_to_check")
    if (
        child_environments
        and isinstance(child_environments, dict)
        and len(child_environments) > 0
    ):
        resource_instance.environments_to_check = child_environments
    else:
        # Try to find valid environments_to_check from parent hierarchy
        parent_environments = None

        # First check parent_model_data (which contains merged data from all ancestors)
        if parent_model_data:
            parent_environments = parent_model_data.get("environments_to_check")
            if not (
                parent_environments
                and isinstance(parent_environments, dict)
                and len(parent_environments) > 0
            ):
                parent_environments = None

        # If not found in parent_model_data, check parent_instance hierarchy recursively
        if not parent_environments and parent_instance:
            parent_environments = _find_valid_environments_to_check(parent_instance)

        # Set environments_to_check if found
        if parent_environments:
            resource_instance.environments_to_check = parent_environments

    # Add id field to resource instance if available
    if "id" in model_data:
        resource_instance.id = model_data["id"]

    return resource_instance


def _get_all_parent_model_data(
    model_name: str,
    all_model_data: dict,
    visited: set | None = None,
) -> dict | None:
    """
    Recursively get all parent model data by following foreign keys.

    Args:
        model_name: Name of the model
        all_model_data: Dictionary containing all model data from query
        visited: Set of visited models (to avoid cycles)

    Returns:
        Merged parent model data or None
    """
    if visited is None:
        visited = set()

    if model_name in visited:
        return None

    visited.add(model_name)

    model = resolve_model(model_name)
    foreign_keys = find_foreign_keys(model)

    if not foreign_keys:
        return None

    # Handle first foreign key (assuming single inheritance)
    fk_column_name, parent_model_class, ref_column_name = foreign_keys[0]
    parent_model_name = get_model_name(parent_model_class)

    # Get parent model data from the query result
    parent_model_data = all_model_data.get(parent_model_name, {})

    if not parent_model_data:
        return None

    # Recursively get parent's parent data
    parent_parent_data = _get_all_parent_model_data(
        parent_model_name,
        all_model_data,
        visited.copy(),
    )

    # Merge parent's parent data into parent data
    if parent_parent_data:
        parent_resource_metadata = parent_model_data.get("resource_metadata", {}) or {}
        parent_parent_resource_metadata = (
            parent_parent_data.get("resource_metadata", {}) or {}
        )
        merged_metadata = {
            **parent_parent_resource_metadata,
            **parent_resource_metadata,
        }
        merged_data = {**parent_parent_data, **parent_model_data}
        merged_data["resource_metadata"] = merged_metadata
        return merged_data

    return parent_model_data


def _find_model_with_attribute(
    root_model_name: str,
    attribute_name: str,
    visited: set | None = None,
) -> str | None:
    """
    Find which model in the inheritance chain contains the given attribute.

    Args:
        root_model_name: Starting model class name
        attribute_name: Name of the attribute to find
        visited: Set of visited models (to avoid cycles)

    Returns:
        Model name that contains the attribute, or None if not found
    """
    if visited is None:
        visited = set()

    if root_model_name in visited:
        return None

    visited.add(root_model_name)

    # Check if root model has this attribute
    model = resolve_model(root_model_name)
    if hasattr(model, attribute_name):
        # Check if it's a column (not a relationship or method)
        mapper = inspect(model)
        for column in mapper.columns:
            if column.name == attribute_name:
                return root_model_name

    # Check parent models
    foreign_keys = find_foreign_keys(model)
    for fk_column_name, parent_model_class, ref_column_name in foreign_keys:
        parent_model_name = get_model_name(parent_model_class)
        parent_result = _find_model_with_attribute(
            parent_model_name,
            attribute_name,
            visited.copy(),
        )
        if parent_result:
            return parent_result

    return None


def _build_filters_from_query(
    root_model_name: str,
    resource_attributes_query: dict,
) -> list[FilterSpec]:
    """
    Build filter functions from resource_attributes_query.

    Args:
        root_model_name: Root model class name
        resource_attributes_query: Dictionary of attribute names to values

    Returns:
        List of filter functions
    """
    filters = []

    for attribute_name, attribute_value in resource_attributes_query.items():
        # Find which model contains this attribute
        model_name = _find_model_with_attribute(root_model_name, attribute_name)

        if model_name:
            # Create a filter function for this attribute
            # Use a factory function to properly capture values in closure
            def create_filter(attr_name: str, attr_value: Any, model: str):
                def filter_fn(models: dict[str, type[BaseModel]]) -> Any:
                    return getattr(models[model], attr_name) == attr_value

                return filter_fn

            filters.append(create_filter(attribute_name, attribute_value, model_name))

    return filters


async def get_resource_attributes(
    session: AsyncSession,
    resource_id: int | None,
    resource_type: str,
    resource_attributes_query: dict | None = None,
    resource_class_name: str | None = None,
) -> list[Resource]:
    """
    Get resource attributes from database and cast to the appropriate Resource class.
    Handles inheritance: if a model has foreign keys to parent models, merges parent attributes.

    Args:
        session: Database session
        resource_id: ID of the resource (if provided, filters by this ID)
        resource_type: Model class name (e.g., "LinuxServerModel")
        resource_attributes_query: Optional dictionary of attribute filters (e.g., {"ram": 8, "location": "US"})
        resource_class_name: Optional resource class name (e.g., "LinuxServer").
                          If not provided, will be looked up from MODEL_TO_RESOURCE_CLASS_MAP.

    Returns:
        List of Resource subclass instances that match the query conditions, or empty list if none found
    """
    # Build filters list
    filters = []

    # Add resource_id filter if provided
    if resource_id is not None:
        filters.append(lambda models: models[resource_type].id == resource_id)

    # Add filters from resource_attributes_query if provided
    if resource_attributes_query:
        query_filters = _build_filters_from_query(
            resource_type,
            resource_attributes_query,
        )
        filters.extend(query_filters)

    # Query for multiple results (list of resources)
    resource_attributes_db_list = await execute_auto_query(
        session=session,
        root_model_name=resource_type,
        filters=filters if filters else None,
        is_only_one_model=False,  # Changed to False to get multiple results
        return_as_dict=True,
    )

    # Handle empty results
    if not resource_attributes_db_list:
        return []

    # Ensure it's a list (execute_auto_query returns a list when is_only_one_model=False)
    if not isinstance(resource_attributes_db_list, list):
        resource_attributes_db_list = [resource_attributes_db_list]

    # Get resource class name (either from parameter or from mapping)
    if resource_class_name is None:
        resource_class_name = _map_model_to_resource_class(resource_type)

    # Dynamically import the resource class
    resource_class = _get_resource_class(resource_class_name)

    # Process each result and create resource instances
    resource_instances = []
    for resource_attributes_db in resource_attributes_db_list:
        # Extract the model data - resource_type should be the model class name (e.g., "LinuxServerModel")
        model_data = resource_attributes_db.get(resource_type, {})

        if not model_data:
            continue

        # Get all parent model data recursively (following foreign keys) for merging attributes
        parent_model_data = _get_all_parent_model_data(
            resource_type,
            resource_attributes_db,
        )

        # Get direct parent model data and create parent instance if foreign key exists
        parent_instance = None
        model = resolve_model(resource_type)
        foreign_keys = find_foreign_keys(model)

        if foreign_keys:
            # Get the first foreign key (assuming single inheritance)
            fk_column_name, parent_model_class, ref_column_name = foreign_keys[0]
            parent_model_name = get_model_name(parent_model_class)

            # Get direct parent model data from the query result
            direct_parent_model_data = resource_attributes_db.get(parent_model_name, {})

            if direct_parent_model_data:
                # Map parent model to parent resource class
                parent_resource_class_name = _map_model_to_resource_class(
                    parent_model_name,
                )
                parent_resource_class = _get_resource_class(parent_resource_class_name)

                # Get parent's parent model data for merging (if exists)
                parent_parent_model_data = _get_all_parent_model_data(
                    parent_model_name,
                    resource_attributes_db,
                )

                # Create parent resource instance (without parent's parent instance to avoid deep nesting)
                parent_instance = _create_resource_instance_from_model_data(
                    parent_resource_class,
                    direct_parent_model_data,
                    parent_parent_model_data,
                    parent_instance=None,  # Parent's parent would be None
                )

                # Add id field to parent instance if available
                if "id" in direct_parent_model_data:
                    parent_instance.id = direct_parent_model_data["id"]

        # Create the resource instance (child class)
        # Parent model data will be merged into child model data
        # Parent instance will be set as the parent of the child
        resource_instance = _create_resource_instance_from_model_data(
            resource_class,
            model_data,
            parent_model_data,
            parent_instance,
        )

        resource_instances.append(resource_instance)

    return resource_instances
