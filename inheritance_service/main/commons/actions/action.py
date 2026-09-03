from typing import Optional

from main.commons.pattern_common.base import HierarchicalEntity
from main.commons.pattern_common.visitors import HierarchyVisitor


class Action(HierarchicalEntity):
    """
    Action entity represents hierarchical actions (e.g., read, write, execute).
    Only shares hierarchy traversal logic, has different behavior from Resource/Subject.
    """

    def __init__(
        self,
        name: str,
        parent: Optional["Action"] = None,
        action_type: str = "generic",
        requires_permission: bool = True,
    ):
        super().__init__(name, parent)
        self._action_type = action_type
        self._requires_permission = requires_permission

    @property
    def action_type(self) -> str:
        return self._action_type

    @property
    def requires_permission(self) -> bool:
        return self._requires_permission

    def accept(self, visitor: HierarchyVisitor) -> None:
        """Accept visitor for Action"""
        visitor.visit_action(self)

    def get_action_hierarchy(self) -> list["Action"]:
        """Get all actions in hierarchy (typed return)"""
        return [
            node
            for node in [self] + self.get_all_descendants()
            if isinstance(node, Action)
        ]

    def implies(self, other_action: "Action") -> bool:
        """
        Check if this action implies another action.
        An action implies another if the other is a descendant.
        """
        return other_action in self.get_all_descendants()
