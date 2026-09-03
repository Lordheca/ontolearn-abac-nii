from datetime import datetime

from .subject import Subject


class User(Subject):
    """
    Concrete example of a Subject.
    Represents a user with specific properties.
    Has attributes matching UserModel: id, username, password, subject_metadata, is_deleted, created_at, updated_at
    """

    # Fields to exclude from dict conversion by default
    # Can be overridden when calling to_dict(exclude_fields={...})
    _exclude_from_dict: set[str] = {
        "password",  # Exclude password for security
        "children",  # Exclude children to avoid circular references
        "is_deleted",  # Exclude is_deleted by default (can include if needed)
        "created_at",  # Exclude created_at by default (can include if needed)
        "updated_at",  # Exclude updated_at by default (can include if needed)
    }

    def __init__(
        self,
        id: int | None = None,
        username: str = "",
        password: str = "",
        subject_metadata: dict | None = None,
        parent: Subject | None = None,
        is_deleted: bool = False,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        # Extract Subject fields from subject_metadata if provided
        metadata = subject_metadata or {}
        name = username or metadata.get("name", "")

        super().__init__(name, parent, subject_type="user")

        # UserModel attributes
        self.id = id
        self.username = username
        self.password = password
        self.subject_metadata = metadata
        self.is_deleted = is_deleted
        self.created_at = created_at
        self.updated_at = updated_at

        # Store subject_metadata in metadata for compatibility
        if subject_metadata:
            for key, value in subject_metadata.items():
                if key not in ["name", "description", "tags"]:
                    self.set_metadata(key, value)

    def get_user_info(self) -> dict:
        """Get comprehensive user information"""
        return {
            "id": self.id,
            "username": self.username,
            "type": self.subject_type,
            "path": " > ".join(self.get_path()),
            "tags": list(self.tags),
            "subject_metadata": self.subject_metadata,
            "is_deleted": self.is_deleted,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.get_all_metadata(),
        }
