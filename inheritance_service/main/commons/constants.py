# Mapping from model names to subject class names
# Example: "UserModel" -> "User"
MODEL_TO_SUBJECT_CLASS_MAP = {
    "UserModel": "User",
    # Add more mappings here as new subject types are added
    # "GroupModel": "Group",
    # "RoleModel": "Role",
}

# Mapping from model names to resource class names
# Example: "ServerModel" -> "Server"
MODEL_TO_RESOURCE_CLASS_MAP = {
    "ServerModel": "Server",
    "LinuxServerModel": "LinuxServer",  # LinuxServerModel maps to LinuxServer class (inherits from Server)
    # Add more mappings here as new resource types are added
    # "VirtualMachineModel": "VirtualMachine",
    # "DatabaseModel": "Database",
}
