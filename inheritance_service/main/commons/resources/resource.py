from typing import Optional

from main.commons.pattern_common.resource_subject_base import ResourceSubjectBase
from main.commons.pattern_common.visitors import HierarchyVisitor


class Resource(ResourceSubjectBase):
    """
    Resource entity represents hierarchical resources (e.g., servers, files, databases).
    Inherits common logic from ResourceSubjectBase.
    """

    def __init__(
        self,
        name: str,
        parent: Optional["Resource"] = None,
    ):
        super().__init__(name, parent)

    def accept(self, visitor: HierarchyVisitor) -> None:
        """Accept visitor for Resource"""
        visitor.visit_resource(self)

    def get_types(self) -> list[str]:
        """
        Get list of class names from MRO (Method Resolution Order) using visitor pattern.
        Includes the current class and all parent classes (excluding base classes).

        Returns:
            List of class names (e.g., ["LinuxServer", "Server"])
        """
        # Lazy import to avoid circular import
        from main.commons.visitors.collect_parent_classes_visitor import (
            CollectParentClassesVisitor,
        )

        visitor = CollectParentClassesVisitor()
        self.accept(visitor)
        return visitor.parent_class_names

    def get_primary_type(self) -> str:
        """
        Get the primary type (current class name) from types.
        This is equivalent to the old resource_type field.

        Returns:
            Primary class name (e.g., "LinuxServer", "Server")
        """
        types = self.get_types()
        return types[0] if types else self.__class__.__name__

    def get_resource_hierarchy(self) -> list["Resource"]:
        """Get all resources in hierarchy (typed return)"""
        return [
            node
            for node in [self] + self.get_all_descendants()
            if isinstance(node, Resource)
        ]
