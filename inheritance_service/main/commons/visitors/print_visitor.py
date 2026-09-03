from main.commons.actions.action import Action
from main.commons.pattern_common.visitors import HierarchyVisitor
from main.commons.resources.resource import Resource
from main.commons.subjects.subject import Subject


class PrintHierarchyVisitor(HierarchyVisitor):
    """Visitor that prints the hierarchy structure"""

    def __init__(self):
        self._depth = 0

    def visit_resource(self, resource: Resource) -> None:
        indent = "  " * self._depth
        primary_type = resource.get_primary_type()
        print(f"{indent}[Resource] {resource.name} (type: {primary_type})")
        self._depth += 1
        for child in resource.children:
            child.accept(self)
        self._depth -= 1

    def visit_subject(self, subject: Subject) -> None:
        indent = "  " * self._depth
        print(f"{indent}[Subject] {subject.name} (type: {subject.subject_type})")
        self._depth += 1
        for child in subject.children:
            child.accept(self)
        self._depth -= 1

    def visit_action(self, action: Action) -> None:
        indent = "  " * self._depth
        perm = "requires permission" if action.requires_permission else "no permission"
        print(f"{indent}[Action] {action.name} ({perm})")
        self._depth += 1
        for child in action.children:
            child.accept(self)
        self._depth -= 1
