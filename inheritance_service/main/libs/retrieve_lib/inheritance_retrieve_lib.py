import importlib

from sqlalchemy.ext.asyncio import AsyncSession

from main.commons.actions.action import Action
from main.commons.resources.resource import Resource
from main.commons.subjects.subject import Subject
from main.commons.visitors.collect_parent_classes_visitor import (
    CollectParentClassesVisitor,
)
from main.libs.retrieve_lib.common import get_resource_instance_types
from main.services import resource_service, subject_service


async def get_subject_attributes(
    session: AsyncSession,
    subject_id: int,
    subject_type: str,
    exclude_fields: set[str] | None = None,
) -> dict | None:
    """
    Get subject attributes as dictionary.

    Args:
        session: Database session
        subject_id: ID of the subject
        subject_type: Model class name (e.g., "UserModel")
        exclude_fields: Optional set of field names to exclude from the result.
                       Fields can be specified with or without leading underscore.
                       Common fields to exclude: {"_password", "_children", "_parent"}

    Returns:
        Dictionary representation of the subject, or None if not found
    """
    subject: Subject = await subject_service.get_subject_attributes(
        session=session,
        subject_id=subject_id,
        subject_type=subject_type,
    )
    return subject.to_dict(exclude_fields=exclude_fields) if subject else None


async def get_resource_attributes(
    session: AsyncSession,
    resource_id: int | None,
    resource_type: str,
    resource_attributes_query: dict | None = None,
) -> list[dict] | None:
    resource_attributes_list = await resource_service.get_resource_attributes(
        session=session,
        resource_id=resource_id,
        resource_type=resource_type,
        resource_attributes_query=resource_attributes_query,
    )

    # Convert list of resource instances to list of dicts with types
    if not resource_attributes_list:
        return None

    result = []
    for resource in resource_attributes_list:
        # Use to_dict() method instead of __dict__ for better control
        # Exclude environments_to_check from response
        resource_dict = resource.to_dict(exclude_fields={"environments_to_check"})
        # Get types for this specific resource instance
        resource_dict["types"] = get_resource_instance_types(resource)
        result.append(resource_dict)

    return result


def _get_action_class(action_class_name: str) -> type[Action]:
    """
    Dynamically import and return the action class by name.

    Args:
        action_class_name: Name of the action class (e.g., "WriteAction", "Action")

    Returns:
        The action class

    Raises:
        ImportError: If the class cannot be imported
        AttributeError: If the class doesn't exist in the module
    """
    try:
        # Import from main.commons.actions module
        module = importlib.import_module("main.commons.actions")
        action_class = getattr(module, action_class_name)
        if not issubclass(action_class, Action):
            raise TypeError(f"{action_class_name} is not a subclass of Action")
        return action_class
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Cannot import action class '{action_class_name}': {e}")


def _get_resource_class(resource_class_name: str) -> type[Resource]:
    """
    Dynamically import and return the resource class by name.

    Args:
        resource_class_name: Name of the resource class (e.g., "Server", "LinuxServer")

    Returns:
        The resource class

    Raises:
        ImportError: If the class cannot be imported
        AttributeError: If the class doesn't exist in the module
    """
    try:
        # Import from main.commons.resources module
        module = importlib.import_module("main.commons.resources")
        resource_class = getattr(module, resource_class_name)
        if not issubclass(resource_class, Resource):
            raise TypeError(f"{resource_class_name} is not a subclass of Resource")
        return resource_class
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Cannot import resource class '{resource_class_name}': {e}")


def get_actions(action: str) -> list[str]:
    """
    Get parent class names of an action using visitor pattern.

    Args:
        action: Action class name (e.g., "WriteAction", "Action")

    Returns:
        List of parent class names from Method Resolution Order (MRO)
    """
    try:
        # Get the Action class dynamically
        action_class = _get_action_class(action)

        # Create a temporary instance to use with visitor
        # We need an instance to traverse using visitor pattern
        action_instance = action_class(name="temp")

        # Create visitor to collect parent class names
        visitor = CollectParentClassesVisitor()

        # Use visitor pattern to traverse and collect parent class names
        action_instance.accept(visitor)

        return visitor.parent_class_names
    except (ImportError, AttributeError, TypeError):
        # If action class not found, return empty list or raise exception
        # For now, return empty list on error
        return []
