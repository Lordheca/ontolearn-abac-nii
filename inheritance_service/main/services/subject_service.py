import importlib

from sqlalchemy.ext.asyncio import AsyncSession

from main.commons.subjects.subject import Subject
from main.models import resolve_model

from ..commons.constants import MODEL_TO_SUBJECT_CLASS_MAP
from .common import execute_auto_query, find_foreign_keys, get_model_name


def _get_subject_class(subject_class_name: str) -> type[Subject]:
    """
    Dynamically import and return the subject class by name.

    Args:
        subject_class_name: Name of the subject class (e.g., "User")

    Returns:
        The subject class

    Raises:
        ImportError: If the class cannot be imported
        AttributeError: If the class doesn't exist in the module
    """
    try:
        # Import from main.commons.subjects module (classes are exported in __init__.py)
        module = importlib.import_module("main.commons.subjects")
        subject_class = getattr(module, subject_class_name)
        if not issubclass(subject_class, Subject):
            raise TypeError(f"{subject_class_name} is not a subclass of Subject")
        return subject_class
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Cannot import subject class '{subject_class_name}': {e}")


def _map_model_to_subject_class(model_name: str) -> str:
    """
    Map model name to subject class name.

    Args:
        model_name: Model class name (e.g., "UserModel")

    Returns:
        Subject class name (e.g., "User")

    Raises:
        ValueError: If no mapping exists for the model name
    """
    subject_class_name = MODEL_TO_SUBJECT_CLASS_MAP.get(model_name)
    if not subject_class_name:
        raise ValueError(
            f"No subject class mapping found for model '{model_name}'. "
            f"Available mappings: {list(MODEL_TO_SUBJECT_CLASS_MAP.keys())}",
        )
    return subject_class_name


async def get_subject_attributes(
    session: AsyncSession,
    subject_id: int,
    subject_type: str,
    subject_class_name: str | None = None,
) -> Subject | None:
    """
    Get subject attributes from database and cast to the appropriate Subject class.

    Args:
        session: Database session
        subject_id: ID of the subject
        subject_type: Model class name (e.g., "UserModel")
        subject_class_name: Optional subject class name (e.g., "User").
                          If not provided, will be looked up from MODEL_TO_SUBJECT_CLASS_MAP.

    Returns:
        Instance of the appropriate Subject subclass, or None if not found
    """
    subject_attributes_db = await execute_auto_query(
        session=session,
        root_model_name=subject_type,
        filters=[lambda models: models[subject_type].id == subject_id],
        is_only_one_model=True,
        return_as_dict=True,
    )

    # Unpack the result dictionary
    if not subject_attributes_db:
        return None

    # Extract the model data - subject_type should be the model class name (e.g., "UserModel")
    model_data = subject_attributes_db.get(subject_type, {})

    if not model_data:
        return None

    # Get subject class name (either from parameter or from mapping)
    if subject_class_name is None:
        subject_class_name = _map_model_to_subject_class(subject_type)

    # Dynamically import the subject class
    subject_class = _get_subject_class(subject_class_name)

    # Check if model has foreign keys to parent
    model = resolve_model(subject_type)
    foreign_keys = find_foreign_keys(model)

    parent_instance = None
    if foreign_keys:
        # Get the first foreign key (assuming single inheritance)
        fk_column_name, parent_model_class, ref_column_name = foreign_keys[0]
        parent_model_name = get_model_name(parent_model_class)

        # Get parent model data from the query result
        parent_model_data = subject_attributes_db.get(parent_model_name, {})

        if parent_model_data:
            # Map parent model to parent subject class
            parent_subject_class_name = _map_model_to_subject_class(parent_model_name)
            parent_subject_class = _get_subject_class(parent_subject_class_name)

            # Prepare kwargs for parent subject class constructor
            parent_kwargs = parent_model_data.copy()
            parent_kwargs["parent"] = None  # Parent's parent would be None for now

            # Create parent subject instance
            parent_instance = parent_subject_class(**parent_kwargs)

            # Add id field to parent instance if available
            if "id" in parent_model_data:
                parent_instance.id = parent_model_data["id"]

    # Prepare kwargs for subject class constructor
    kwargs = model_data.copy()
    kwargs["parent"] = parent_instance

    # Create subject instance dynamically
    subject_instance = subject_class(**kwargs)

    # Add id field to subject instance if available
    if "id" in model_data:
        subject_instance.id = model_data["id"]

    return subject_instance
