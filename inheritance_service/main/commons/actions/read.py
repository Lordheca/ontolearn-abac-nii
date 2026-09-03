from main.commons.actions.action import Action


class ReadAction(Action):
    """
    Concrete example of an Action.
    Represents a read action with specific properties.
    """

    def __init__(
        self,
        name: str,
        parent: Action | None = None,
        requires_permission: bool = True,
        is_destructive: bool = False,
    ):
        super().__init__(
            name,
            parent,
            action_type="read",
            requires_permission=requires_permission,
        )
        self._is_destructive = is_destructive

    @property
    def is_destructive(self) -> bool:
        return self._is_destructive

    def get_action_info(self) -> dict:
        """Get comprehensive action information"""
        return {
            "name": self.name,
            "type": self.action_type,
            "requires_permission": self.requires_permission,
            "is_destructive": self._is_destructive,
            "path": " > ".join(self.get_path()),
        }
