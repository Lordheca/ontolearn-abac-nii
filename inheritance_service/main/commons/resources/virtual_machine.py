from main.commons.resources.resource import Resource


class VirtualMachine(Resource):
    """
    VirtualMachine represents a virtual machine resource.
    Inherits from Resource and adds VM-specific properties.
    """

    def __init__(
        self,
        name: str,
        parent: Resource | None = None,
        cpu_cores: int = 2,
        memory_gb: int = 4,
        disk_gb: int = 50,
    ):
        super().__init__(name, parent)
        self.cpu_cores = cpu_cores
        self.memory_gb = memory_gb
        self.disk_gb = disk_gb
        self.status = "stopped"

    def start(self) -> None:
        """Start the virtual machine"""
        self.status = "running"

    def stop(self) -> None:
        """Stop the virtual machine"""
        self.status = "stopped"

    def get_vm_info(self) -> dict:
        """Get comprehensive VM information"""
        return {
            "name": self.name,
            "type": self.get_primary_type(),
            "cpu_cores": self.cpu_cores,
            "memory_gb": self.memory_gb,
            "disk_gb": self.disk_gb,
            "status": self.status,
            "path": " > ".join(self.get_path()),
            "tags": list(self.tags),
            "metadata": self.get_all_metadata(),
        }
