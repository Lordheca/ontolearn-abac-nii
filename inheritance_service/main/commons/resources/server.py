from main.commons.resources.resource import Resource


class Server(Resource):
    """
    Concrete example of a Resource.
    Represents a server with specific properties.
    Matches ServerModel fields: location
    """

    def __init__(
        self,
        name: str,
        parent: Resource | None = None,
        location: str = "",
    ):
        super().__init__(name, parent)
        self.location = location

    def get_server_info(self) -> dict:
        """Get comprehensive server information"""
        return {
            "name": self.name,
            "type": self.get_primary_type(),
            "location": self.location,
            "path": " > ".join(self.get_path()),
            "tags": list(self.tags),
            "metadata": self.get_all_metadata(),
        }
