from typing import Any, Optional

from main.commons.pattern_common.base import HierarchicalEntity


class ResourceSubjectBase(HierarchicalEntity):
    """
    Abstract base class for Resource and Subject entities.
    They share common logic for metadata, tags, and permissions.
    """

    # Class attribute to define default fields to exclude from dict conversion
    # Can be overridden in subclasses
    _exclude_from_dict: set[str] = set()

    def __init__(
        self,
        name: str,
        parent: Optional["ResourceSubjectBase"] = None,
    ):
        super().__init__(name, parent)
        self.metadata = {}

    def get_metadata(self, key: str) -> Any | None:
        """Get metadata value by key"""
        return self.metadata.get(key)

    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata key-value pair"""
        self.metadata[key] = value

    def get_all_metadata(self) -> dict:
        """Get all metadata"""
        return self.metadata.copy()

    def to_dict(
        self,
        exclude_fields: set[str] | None = None,
        include_private: bool = True,
    ) -> dict[str, Any]:
        """
        Convert instance to dictionary, excluding specified fields.

        Args:
            exclude_fields: Set of field names to exclude from the result.
                          If None, uses class attribute _exclude_from_dict.
                          Fields can be specified with or without leading underscore.
            include_private: If True, includes private attributes (starting with _).
                           If False, only includes public attributes.

        Returns:
            Dictionary representation of the instance with excluded fields removed.
            All values are converted to JSON-serializable format.
        """
        # Merge exclude_fields with class-level _exclude_from_dict
        if exclude_fields is None:
            exclude_fields = set()

        # Combine with class-level exclude fields
        final_exclude = self._exclude_from_dict.copy() | exclude_fields

        # Normalize field names (handle both with and without leading underscore)
        normalized_exclude = set()
        for field in final_exclude:
            normalized_exclude.add(field)
            if field.startswith("_"):
                normalized_exclude.add(field[1:])  # Also exclude without underscore
            else:
                normalized_exclude.add(f"_{field}")  # Also exclude with underscore

        result = {}

        # Get all instance attributes
        if hasattr(self, "__dict__"):
            for key, value in self.__dict__.items():
                # Skip if field is in exclude list
                if key in normalized_exclude:
                    continue

                # Handle include_private flag
                if not include_private and key.startswith("_"):
                    continue

                # Convert value to JSON-serializable format
                result[key] = self._make_json_serializable(value)

        return result
