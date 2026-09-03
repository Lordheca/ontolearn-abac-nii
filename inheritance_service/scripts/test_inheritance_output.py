#!/usr/bin/env python3
"""Test script to show output of get_all_attributes() with multiple inheritance levels."""

import json

from main.commons.resources.server import Server


"""Create a Server instance with multiple inheritance layers.
Inheritance chain:
Server -> Resource -> ResourceSubjectBase -> HierarchicalEntity -> ABC -> object
"""
print("=" * 70)
print("INHERITANCE STRUCTURE OF Server:")
print("=" * 70)
print("Server")
print("  └─ Resource")
print("      └─ ResourceSubjectBase")
print("          └─ HierarchicalEntity")
print("              └─ ABC")
print("                  └─ object")
print()

# Create a Server with full attributes
root_server = Server("DataCenter", location="US-East")
root_server.set_metadata("owner", "IT Department")

api_server = Server(
    "APIServer",
    parent=root_server,
    location="US-East",
)
api_server.set_metadata("version", "2.0")

print("=" * 70)
print("MRO (Method Resolution Order) of Server:")
print("=" * 70)
for i, cls in enumerate(api_server.__class__.__mro__):
    print(f"  {i+1}. {cls.__name__}")

print("\n" + "=" * 70)
print("OUTPUT OF get_all_attributes() FOR Server:")
print("=" * 70)

api_attrs = api_server.get_all_attributes()

print("\n1. All attributes (sorted by key):")
print("-" * 70)
for key, value in sorted(api_attrs.items()):
    print(f"  {key}: {value}")

print("\n2. JSON output:")
print("-" * 70)
print(json.dumps(api_attrs, indent=2, ensure_ascii=False))

print("\n3. Classify attributes by origin:")
print("-" * 70)

# Attributes from instance (__dict__)
instance_attrs = set(api_server.__dict__.keys())
print(f"\nAttributes from instance (__dict__): {len(instance_attrs)}")
for attr in sorted(instance_attrs):
    if attr in api_attrs:
        value = api_attrs[attr]
        if isinstance(value, (list, dict)) and len(str(value)) > 80:
            print(f"  - {attr}: {type(value).__name__} (length: {len(value)})")
        else:
            print(f"  - {attr}: {value}")

# Attributes from classes in the MRO
print("\nAttributes from classes in the MRO:")
for cls in api_server.__class__.__mro__:
    if cls is object:
        continue
    class_attrs = []
    for attr_name in dir(cls):
        if attr_name.startswith("__") and attr_name.endswith("__"):
            continue
        if attr_name not in instance_attrs and attr_name in api_attrs:
            class_attrs.append(attr_name)
    if class_attrs:
        print(f"  - {cls.__name__}: {sorted(class_attrs)}")

print("\n" + "=" * 70)
print("EXPLANATION:")
print("=" * 70)
print(
    """
The get_all_attributes() function works as follows:

1. Collect all attributes from the instance (__dict__):
   - name, parent, children (from HierarchicalEntity.__init__)
   - metadata (from ResourceSubjectBase.__init__)
   - location (from Server.__init__)

2. Traverse the MRO (Method Resolution Order) to collect class attributes:
   - From Server: no class attributes
   - From Resource: methods such as get_types(), get_primary_type()
   - From ResourceSubjectBase: methods such as get_metadata(), set_metadata(), to_dict()
   - From HierarchicalEntity: properties (name, parent, children) and methods
   - From ABC: _abc_impl (internal attribute)

3. Special handling:
   - parent -> serialized as a dict or name
   - children -> list of child objects is serialized
   - Properties are resolved from the instance
   - All values are converted to be JSON-serializable

4. Result:
   - Includes both instance attributes and properties
   - All values can be serialized to JSON
""",
)
