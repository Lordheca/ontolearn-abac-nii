from abc import ABC, abstractmethod
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from main.commons.actions.action import Action
    from main.commons.resources.resource import Resource
    from main.commons.subjects.subject import Subject


class HierarchyVisitor(ABC):
    """Abstract visitor for traversing hierarchical entities"""

    @abstractmethod
    def visit_resource(self, resource: "Resource") -> None:
        """Visit a resource node"""
        pass

    @abstractmethod
    def visit_subject(self, subject: "Subject") -> None:
        """Visit a subject node"""
        pass

    @abstractmethod
    def visit_action(self, action: "Action") -> None:
        """Visit an action node"""
        pass
