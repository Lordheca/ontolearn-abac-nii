from main.commons.actions.action import Action
from main.commons.pattern_common.visitors import HierarchyVisitor
from main.commons.resources.resource import Resource
from main.commons.subjects.subject import Subject


class CollectNodesVisitor(HierarchyVisitor):
    """Visitor that collects all nodes by type"""

    def __init__(self):
        self.resources: list[Resource] = []
        self.subjects: list[Subject] = []
        self.actions: list[Action] = []

    def visit_resource(self, resource: Resource) -> None:
        self.resources.append(resource)

    def visit_subject(self, subject: Subject) -> None:
        self.subjects.append(subject)

    def visit_action(self, action: Action) -> None:
        self.actions.append(action)
