import json
from abc import ABC, abstractmethod
from typing import Any, Optional

from main.commons.pattern_common.visitors import HierarchyVisitor


class HierarchicalEntity(ABC):
    """
    Base class for all hierarchical entities using Composite Pattern.
    Provides common hierarchy management functionality.
    """

    def __init__(self, name: str, parent: Optional["HierarchicalEntity"] = None):
        self.name = name
        self.parent = parent
        self.children: list["HierarchicalEntity"] = []

        if parent:
            parent._add_child(self)

    def _add_child(self, child: "HierarchicalEntity") -> None:
        """Internal method to add a child to this node"""
        if child not in self.children:
            self.children.append(child)

    def remove_child(self, child: "HierarchicalEntity") -> None:
        """Remove a child from this node"""
        if child in self.children:
            self.children.remove(child)
            child.parent = None

    def get_all_descendants(self) -> list["HierarchicalEntity"]:
        """Get all descendants (children, grandchildren, etc.) recursively"""
        descendants = []
        for child in self.children:
            descendants.append(child)
            descendants.extend(child.get_all_descendants())
        return descendants

    def get_ancestors(self) -> list["HierarchicalEntity"]:
        """Get all ancestors (parent, grandparent, etc.) up to root"""
        ancestors = []
        current = self.parent
        while current:
            ancestors.append(current)
            current = current.parent
        return ancestors

    def get_path(self) -> list[str]:
        """Get path from root to this node"""
        path = [self.name]
        current = self.parent
        while current:
            path.insert(0, current.name)
            current = current.parent
        return path

    def is_ancestor_of(self, node: "HierarchicalEntity") -> bool:
        """Check if this node is an ancestor of the given node"""
        return self in node.get_ancestors()

    def is_descendant_of(self, node: "HierarchicalEntity") -> bool:
        """Check if this node is a descendant of the given node"""
        return node in self.get_ancestors()

    @abstractmethod
    def accept(self, visitor: HierarchyVisitor) -> None:
        """Accept a visitor (Visitor Pattern)"""
        pass

    def traverse(self, visitor: HierarchyVisitor) -> None:
        """
        Template method for traversing the hierarchy.
        Visits this node and all descendants.
        """
        self.accept(visitor)
        for child in self.children:
            child.traverse(visitor)

    def _make_json_serializable(self, value: Any) -> Any:
        """
        Convert a value to JSON-serializable format.

        Args:
            value: The value to convert

        Returns:
            JSON-serializable value
        """
        # Handle None
        if value is None:
            return None

        # Handle basic JSON types
        if isinstance(value, (str, int, float, bool)):
            return value

        # Handle list/tuple
        if isinstance(value, (list, tuple)):
            return [self._make_json_serializable(item) for item in value]

        # Handle set
        if isinstance(value, set):
            return [self._make_json_serializable(item) for item in value]

        # Handle dict
        if isinstance(value, dict):
            return {k: self._make_json_serializable(v) for k, v in value.items()}

        # Handle HierarchicalEntity objects (parent, children)
        if isinstance(value, HierarchicalEntity):
            # For parent objects, serialize as dict but exclude children and parent's parent to avoid deep nesting
            if hasattr(value, "to_dict"):
                return value.to_dict(
                    exclude_fields={"children", "parent", "environments_to_check"},
                )
            # Fallback to name if to_dict is not available
            return value.name

        # Try to convert to string for other types
        try:
            # Try JSON serialization to check if it's already serializable
            json.dumps(value)
            return value
        except (TypeError, ValueError):
            # If not serializable, convert to string representation
            return str(value)

    def get_all_attributes(self) -> dict[str, Any]:
        """
        Get all attribute values of the instance and all parent classes.
        Returns a dictionary with JSON-serializable values only.

        Returns:
            Dict containing all attribute values from the instance and parent classes,
            with all values converted to JSON-serializable format
        """
        result = {}

        # Get attributes from instance (instance attributes)
        if hasattr(self, "__dict__"):
            for key, value in self.__dict__.items():
                result[key] = self._make_json_serializable(value)

        # Get attributes from all classes in MRO (Method Resolution Order)
        # MRO includes the current class and all parent classes
        for cls in self.__class__.__mro__:
            # Skip object class as it doesn't have useful attributes
            if cls is object:
                continue

            # Get class attributes (not instance attributes)
            for attr_name in dir(cls):
                # Skip special attributes (starting and ending with __)
                if attr_name.startswith("__") and attr_name.endswith("__"):
                    continue

                # Skip if already in result (instance attributes have priority)
                if attr_name in result:
                    continue

                # Get attribute value from class
                try:
                    attr_value = getattr(cls, attr_name)
                    # Check if it's a property descriptor
                    if isinstance(attr_value, property):
                        # For properties, get the actual value from the instance
                        try:
                            prop_value = getattr(self, attr_name)
                            result[attr_name] = self._make_json_serializable(prop_value)
                        except AttributeError:
                            pass
                    # Only include if not a method or callable
                    elif not callable(attr_value):
                        result[attr_name] = self._make_json_serializable(attr_value)
                except AttributeError:
                    pass

        return result

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
