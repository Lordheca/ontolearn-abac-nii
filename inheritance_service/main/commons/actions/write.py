from main.commons.actions.read import ReadAction


class WriteAction(ReadAction):
    """
    WriteAction inherits from ReadAction.
    Represents a read action with specific properties.
    """

    def __init__(
        self,
        name: str,
        parent: ReadAction | None = None,
        requires_permission: bool = True,
        is_destructive: bool = False,
    ):
        # Call ReadAction's __init__ but override action_type to "read"
        # We need to call Action's __init__ directly to set action_type="read"
        from main.commons.actions.action import Action

        Action.__init__(
            self,
            name,
            parent,
            action_type="write",
            requires_permission=requires_permission,
        )
        # Set WriteAction specific attribute
        self._is_destructive = is_destructive

    def get_action_info(self) -> dict:
        """Get comprehensive action information"""
        return {
            "name": self.name,
            "type": self.action_type,
            "requires_permission": self.requires_permission,
            "is_destructive": self._is_destructive,
            "path": " > ".join(self.get_path()),
        }
