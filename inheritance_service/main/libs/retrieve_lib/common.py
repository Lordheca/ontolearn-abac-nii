from main.commons.resources import Resource
from main.commons.visitors.collect_parent_classes_visitor import (
    CollectParentClassesVisitor,
)


def get_resource_instance_types(resource_instance: Resource) -> list[str]:
    """
    Get parent class names of a resource instance using visitor pattern.
    Uses the actual resource instance to collect parent classes.

    Args:
        resource_instance: Resource instance

    Returns:
        List of parent class names from Method Resolution Order (MRO)
    """
    try:
        # Create visitor to collect parent class names
        visitor = CollectParentClassesVisitor()

        # Use visitor pattern to traverse and collect parent class names
        resource_instance.accept(visitor)

        return visitor.parent_class_names
    except (ImportError, AttributeError, TypeError):
        # If error occurs, return empty list
        return []
