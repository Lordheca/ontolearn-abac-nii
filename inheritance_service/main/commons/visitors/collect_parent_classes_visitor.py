from main.commons.actions.action import Action
from main.commons.pattern_common.visitors import HierarchyVisitor
from main.commons.resources.resource import Resource
from main.commons.subjects.subject import Subject


class CollectParentClassesVisitor(HierarchyVisitor):
    """
    Visitor that collects parent class names from the Method Resolution Order (MRO)
    of Action, Resource, or Subject instances. Uses visitor pattern to traverse and collect class names.
    Excludes base classes like Action, Resource, ResourceSubjectBase, HierarchicalEntity.
    """

    # Base classes to exclude from the results (common for all entity types)
    COMMON_BASE_CLASSES_TO_EXCLUDE = {
        "HierarchicalEntity",
        "object",
        "ABC",
    }

    # Base classes to exclude for Action entities
    ACTION_BASE_CLASSES_TO_EXCLUDE = {
        "Action",
        *COMMON_BASE_CLASSES_TO_EXCLUDE,
    }

    # Base classes to exclude for Resource entities
    RESOURCE_BASE_CLASSES_TO_EXCLUDE = {
        "Resource",
        "ResourceSubjectBase",
        *COMMON_BASE_CLASSES_TO_EXCLUDE,
    }

    # Base classes to exclude for Subject entities
    SUBJECT_BASE_CLASSES_TO_EXCLUDE = {
        "Subject",
        "ResourceSubjectBase",
        *COMMON_BASE_CLASSES_TO_EXCLUDE,
    }

    def __init__(self):
        self.parent_class_names: list[str] = []

    def visit_resource(self, resource: Resource) -> None:
        """
        Visit a resource node and collect class names from MRO (including the current class).
        Excludes base classes (Resource, ResourceSubjectBase, HierarchicalEntity),
        and built-in classes (object, ABC) from the results.
        """
        # Get Method Resolution Order (MRO) which includes all parent classes
        mro = resource.__class__.__mro__

        # Collect class names (including current class), excluding base classes and duplicates
        for cls in mro:
            class_name = cls.__name__
            # Skip base classes, built-in classes, and duplicates
            if (
                class_name not in self.RESOURCE_BASE_CLASSES_TO_EXCLUDE
                and class_name not in self.parent_class_names
            ):
                self.parent_class_names.append(class_name)

    def visit_subject(self, subject: Subject) -> None:
        """
        Visit a subject node and collect class names from MRO (including the current class).
        Excludes base classes (Subject, ResourceSubjectBase, HierarchicalEntity),
        and built-in classes (object, ABC) from the results.
        """
        # Get Method Resolution Order (MRO) which includes all parent classes
        mro = subject.__class__.__mro__

        # Collect class names (including current class), excluding base classes and duplicates
        for cls in mro:
            class_name = cls.__name__
            # Skip base classes, built-in classes, and duplicates
            if (
                class_name not in self.SUBJECT_BASE_CLASSES_TO_EXCLUDE
                and class_name not in self.parent_class_names
            ):
                self.parent_class_names.append(class_name)

    def visit_action(self, action: Action) -> None:
        """
        Visit an action node and collect class names from MRO (including the current class).
        Excludes base classes (Action, HierarchicalEntity),
        and built-in classes (object, ABC) from the results.
        """
        # Get Method Resolution Order (MRO) which includes all parent classes
        mro = action.__class__.__mro__

        # Collect class names (including current class), excluding base classes and duplicates
        for cls in mro:
            class_name = cls.__name__
            # Skip base classes, built-in classes, and duplicates
            if (
                class_name not in self.ACTION_BASE_CLASSES_TO_EXCLUDE
                and class_name not in self.parent_class_names
            ):
                self.parent_class_names.append(class_name)
