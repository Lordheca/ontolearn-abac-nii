package policy

# Deny by default
default allow := false

#
# Policy rules:
# - subject.role must be "employee"
# - action.name must be "read"
# - subject.department must match resource.department
#
allow if {
    input.subject.role == "employee"
    input.action.name == "read"
    input.subject.department == input.resource.department

    some i
    input.environments.get_device_type[i] == "Device_1"
}
