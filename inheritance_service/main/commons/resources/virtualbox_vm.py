from main.commons.resources.virtual_machine import VirtualMachine


class VirtualBoxVirtualMachine(VirtualMachine):
    """
    VirtualBoxVirtualMachine represents a VirtualBox-specific virtual machine.
    Inherits from VirtualMachine and adds VirtualBox-specific properties.
    """

    def __init__(
        self,
        name: str,
        parent: VirtualMachine | None = None,
        cpu_cores: int = 2,
        memory_gb: int = 4,
        disk_gb: int = 50,
        vbox_version: str = "7.0",
        snapshot_count: int = 0,
    ):
        super().__init__(name, parent, cpu_cores, memory_gb, disk_gb)
        self.vbox_version = vbox_version
        self.snapshot_count = snapshot_count
        self.guest_os = "Linux"

    def create_snapshot(self, snapshot_name: str) -> None:
        """Create a snapshot of the VM"""
        self.snapshot_count += 1
        self.set_metadata(f"snapshot_{self.snapshot_count}", snapshot_name)

    def set_guest_os(self, os_name: str) -> None:
        """Set the guest operating system"""
        self.guest_os = os_name

    def get_vbox_info(self) -> dict:
        """Get comprehensive VirtualBox VM information"""
        return {
            "name": self.name,
            "type": self.get_primary_type(),
            "vbox_version": self.vbox_version,
            "snapshot_count": self.snapshot_count,
            "guest_os": self.guest_os,
            "cpu_cores": self.cpu_cores,
            "memory_gb": self.memory_gb,
            "disk_gb": self.disk_gb,
            "status": self.status,
            "path": " > ".join(self.get_path()),
            "tags": list(self.tags),
            "metadata": self.get_all_metadata(),
        }
