from main.commons.resources.server import Server


class LinuxServer(Server):
    """
    LinuxServer represents a Linux-specific server.
    Inherits from Server and adds Linux-specific properties.
    Matches LinuxServerModel fields: ram, cpu_cores (inherits location from Server)
    """

    def __init__(
        self,
        name: str,
        parent: Server | None = None,
        location: str = "",
        ram: int = 0,
        cpu_cores: int = 0,
    ):
        # Initialize parent Server class with Server-specific fields
        super().__init__(name, parent, location)

        # LinuxServer-specific attributes (matching LinuxServerModel)
        self.ram = ram
        self.cpu_cores = cpu_cores

    def get_linux_server_info(self) -> dict:
        """Get comprehensive Linux server information"""
        server_info = self.get_server_info()
        server_info.update(
            {
                "ram": self.ram,
                "cpu_cores": self.cpu_cores,
            },
        )
        return server_info
