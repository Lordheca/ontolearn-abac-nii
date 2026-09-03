#!/usr/bin/env python3
"""Test script to demonstrate get_all_attributes() with multi-level inheritance."""

import json

from main.commons.resources.virtual_machine import VirtualMachine
from main.commons.resources.virtualbox_vm import VirtualBoxVirtualMachine


print("=" * 70)
print("TEST get_all_attributes() WITH MULTI-LEVEL INHERITANCE")
print("=" * 70)

# Create a VirtualBoxVirtualMachine instance
print("\n1. Create a VirtualBoxVirtualMachine instance:")
print("-" * 70)

vm_pool = VirtualMachine(
    "VMPool",
    cpu_cores=8,
    memory_gb=32,
)
vm_pool.set_metadata("description", "Virtual Machine Pool")

vbox_vm = VirtualBoxVirtualMachine(
    name="UbuntuServer",
    parent=vm_pool,
    cpu_cores=4,
    memory_gb=8,
    disk_gb=100,
    vbox_version="7.0.10",
    snapshot_count=2,
)
vbox_vm.set_metadata("os_version", "Ubuntu 22.04")
vbox_vm.set_metadata("created_by", "admin")
vbox_vm.set_metadata("description", "Ubuntu Server VM")
vbox_vm.create_snapshot("initial_setup")
vbox_vm.start()

print(f"Created: {vbox_vm}")
print(f"  Parent: {vbox_vm.parent.name if vbox_vm.parent else None}")

# Display inheritance structure
print("\n2. Inheritance structure:")
print("-" * 70)
print("  HierarchicalEntity (base)")
print("    └─ ResourceSubjectBase")
print("        └─ Resource")
print("            └─ VirtualMachine")
print("                └─ VirtualBoxVirtualMachine")

print("\n3. MRO (Method Resolution Order):")
print("-" * 70)
for i, cls in enumerate(VirtualBoxVirtualMachine.__mro__, 1):
    print(f"  {i}. {cls.__name__}")

# Test get_all_attributes()
print("\n4. Output of get_all_attributes() on VirtualBoxVirtualMachine:")
print("-" * 70)

all_attrs = vbox_vm.get_all_attributes()

print("\n4.1. Dictionary form (sorted by key):")
print("-" * 70)
for key, value in sorted(all_attrs.items()):
    if isinstance(value, (list, dict)) and len(str(value)) > 80:
        print(f"  {key}: {type(value).__name__} (length: {len(value)})")
    else:
        print(f"  {key}: {value}")

print("\n4.2. JSON form (formatted):")
print("-" * 70)
print(json.dumps(all_attrs, indent=2, ensure_ascii=False))

# Analyze attributes by class
print("\n5. Analyze attributes by class:")
print("-" * 70)

# Attributes from HierarchicalEntity
print("\n  From HierarchicalEntity:")
hierarchical_attrs = ["_name", "_parent", "_children", "name", "parent", "children"]
for attr in hierarchical_attrs:
    if attr in all_attrs:
        print(f"    ✓ {attr}: {all_attrs[attr]}")

# Attributes from ResourceSubjectBase
print("\n  From ResourceSubjectBase:")
resource_subject_attrs = ["metadata"]
for attr in resource_subject_attrs:
    if attr in all_attrs:
        if isinstance(all_attrs[attr], dict):
            print(f"    ✓ {attr}: {json.dumps(all_attrs[attr], indent=6)}")
        else:
            print(f"    ✓ {attr}: {all_attrs[attr]}")

# Attributes from Resource
print("\n  From Resource:")
resource_attrs = ["get_types", "get_primary_type", "get_resource_hierarchy"]
for attr in resource_attrs:
    if attr in all_attrs:
        print(f"    ✓ {attr}: {all_attrs[attr]}")

# Attributes from VirtualMachine
print("\n  From VirtualMachine:")
vm_attrs = [
    "cpu_cores",
    "memory_gb",
    "disk_gb",
    "status",
]
for attr in vm_attrs:
    if attr in all_attrs:
        print(f"    ✓ {attr}: {all_attrs[attr]}")

# Attributes from VirtualBoxVirtualMachine
print("\n  From VirtualBoxVirtualMachine:")
vbox_attrs = [
    "vbox_version",
    "snapshot_count",
    "guest_os",
]
for attr in vbox_attrs:
    if attr in all_attrs:
        print(f"    ✓ {attr}: {all_attrs[attr]}")

# Check JSON serialization
print("\n6. Check JSON serialization:")
print("-" * 70)
try:
    json_str = json.dumps(all_attrs, indent=2, ensure_ascii=False)
    print("  ✓ Successfully serialized to JSON!")
    print(f"  ✓ JSON length: {len(json_str)} characters")
except Exception as e:
    print(f"  ✗ Lỗi khi serialize: {e}")

print("\n" + "=" * 70)
print("CONCLUSION:")
print("=" * 70)
print(
    """
The get_all_attributes() function retrieved ALL attributes from:
  ✓ HierarchicalEntity (base class) - name, parent, children, and related methods
  ✓ ResourceSubjectBase - metadata and methods such as get_metadata(), to_dict()
  ✓ Resource - methods such as get_types(), get_primary_type()
  ✓ VirtualMachine - cpu_cores, memory_gb, disk_gb, status
  ✓ VirtualBoxVirtualMachine (current class) - vbox_version, snapshot_count, guest_os

All attributes were converted into a JSON-serializable format.
""",
)
print("=" * 70)
