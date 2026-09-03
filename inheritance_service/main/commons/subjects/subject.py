from typing import Optional

from main.commons.pattern_common.resource_subject_base import ResourceSubjectBase
from main.commons.pattern_common.visitors import HierarchyVisitor


class Subject(ResourceSubjectBase):
    """
    Subject entity represents hierarchical subjects (e.g., users, groups, roles).
    Inherits common logic from ResourceSubjectBase.
    """

    def __init__(
        self,
        name: str,
        parent: Optional["Subject"] = None,
        subject_type: str = "generic",
    ):
        super().__init__(name, parent)
        self.subject_type = subject_type

    def accept(self, visitor: HierarchyVisitor) -> None:
        """Accept visitor for Subject"""
        visitor.visit_subject(self)

    def get_subject_hierarchy(self) -> list["Subject"]:
        """Get all subjects in hierarchy (typed return)"""
        return [
            node
            for node in [self] + self.get_all_descendants()
            if isinstance(node, Subject)
        ]
