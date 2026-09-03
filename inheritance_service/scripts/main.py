from main.commons.actions.write import WriteAction
from main.commons.resources.server import Server
from main.commons.subjects.user import User
from main.commons.visitors.collect_visitor import CollectNodesVisitor
from main.commons.visitors.print_visitor import PrintHierarchyVisitor


if __name__ == "__main__":
    print("=" * 70)
    print("HIERARCHICAL ENTITY SYSTEM DEMO")
    print("=" * 70)

    # Create Resource hierarchy (Servers)
    print("\n1. Creating Resource Hierarchy (Servers):")
    print("-" * 70)
    root_server = Server("DataCenter", location="US-East")
    root_server.set_metadata("owner", "IT Department")

    web_server = Server(
        "WebServer",
        parent=root_server,
        location="US-East",
    )

    api_server = Server(
        "APIServer",
        parent=web_server,
        location="US-East",
    )

    db_server = Server(
        "DatabaseServer",
        parent=root_server,
        location="US-East",
    )

    print(f"Created: {root_server}")
    print(f"  └─ {web_server}")
    print(f"      └─ {api_server}")
    print(f"  └─ {db_server}")

    # Create Subject hierarchy (Users)
    print("\n2. Creating Subject Hierarchy (Users):")
    print("-" * 70)
    admin_group = User(
        username="Admins",
        subject_metadata={"email": "admins@company.com", "role": "admin_group"},
    )

    alice = User(
        username="Alice",
        parent=admin_group,
        subject_metadata={"email": "alice@company.com", "role": "admin"},
    )

    bob = User(
        username="Bob",
        parent=admin_group,
        subject_metadata={"email": "bob@company.com", "role": "admin"},
    )

    regular_group = User(
        username="RegularUsers",
        subject_metadata={"email": "users@company.com", "role": "user_group"},
    )
    charlie = User(
        username="Charlie",
        parent=regular_group,
        subject_metadata={"email": "charlie@company.com", "role": "user"},
    )

    print(f"Created: {admin_group}")
    print(f"  ├─ {alice}")
    print(f"  └─ {bob}")
    print(f"Created: {regular_group}")
    print(f"  └─ {charlie}")

    # Create Action hierarchy
    print("\n3. Creating Action Hierarchy:")
    print("-" * 70)
    write_action = WriteAction("Write", is_destructive=False)

    update_action = WriteAction("Update", parent=write_action, is_destructive=False)
    delete_action = WriteAction("Delete", parent=write_action, is_destructive=True)

    print(f"Created: {write_action}")
    print(f"  ├─ {update_action}")
    print(f"  └─ {delete_action}")

    # Demonstrate hierarchy traversal
    print("\n4. Traversing Resource Hierarchy:")
    print("-" * 70)
    visitor = PrintHierarchyVisitor()
    root_server.traverse(visitor)

    print("\n5. Traversing Subject Hierarchy:")
    print("-" * 70)
    visitor = PrintHierarchyVisitor()
    admin_group.traverse(visitor)

    print("\n6. Traversing Action Hierarchy:")
    print("-" * 70)
    visitor = PrintHierarchyVisitor()
    write_action.traverse(visitor)

    # Demonstrate path and ancestor queries
    print("\n7. Path and Ancestor Queries:")
    print("-" * 70)
    print(f"API Server path: {' > '.join(api_server.get_path())}")
    print(f"Alice path: {' > '.join(alice.get_path())}")
    print(f"Delete action path: {' > '.join(delete_action.get_path())}")

    print(f"\nAPI Server ancestors: {[str(a) for a in api_server.get_ancestors()]}")
    print(
        f"Root Server descendants: {[str(d) for d in root_server.get_all_descendants()]}",
    )

    # Demonstrate resource and subject types
    print("\n8. Resource and Subject Types:")
    print("-" * 70)
    print(f"API Server types: {api_server.get_types()}")
    print(f"API Server primary type: {api_server.get_primary_type()}")
    print(f"Alice subject type: {alice.subject_type}")

    # Demonstrate action implication
    print("\n9. Action Implications:")
    print("-" * 70)
    print(f"Write implies Delete? {write_action.implies(delete_action)}")
    print(f"Delete implies Write? {delete_action.implies(write_action)}")

    # Collect all nodes
    print("\n10. Collecting All Nodes:")
    print("-" * 70)
    collector = CollectNodesVisitor()
    root_server.traverse(collector)
    admin_group.traverse(collector)
    write_action.traverse(collector)

    print(f"Total Resources: {len(collector.resources)}")
    print(f"Total Subjects: {len(collector.subjects)}")
    print(f"Total Actions: {len(collector.actions)}")

    # Demonstrate get_all_attributes method
    print("\n11. Getting All Attributes (Instance + Parent Classes):")
    print("-" * 70)

    # Demo with Server instance
    print(f"\nAll attributes of {api_server.name}:")
    api_attrs = api_server.get_all_attributes()
    for key, value in sorted(api_attrs.items()):
        if isinstance(value, (list, dict)) and len(str(value)) > 80:
            print(f"  {key}: {type(value).__name__} (length: {len(value)})")
        else:
            print(f"  {key}: {value}")

    # Demo with User instance
    print(f"\nAll attributes of {alice.username}:")
    alice_attrs = alice.get_all_attributes()
    for key, value in sorted(alice_attrs.items()):
        if isinstance(value, (list, dict)) and len(str(value)) > 80:
            print(f"  {key}: {type(value).__name__} (length: {len(value)})")
        else:
            print(f"  {key}: {value}")

    # Demo with Action instance
    print(f"\nAll attributes of {delete_action.name}:")
    delete_attrs = delete_action.get_all_attributes()
    for key, value in sorted(delete_attrs.items()):
        if isinstance(value, (list, dict)) and len(str(value)) > 80:
            print(f"  {key}: {type(value).__name__} (length: {len(value)})")
        else:
            print(f"  {key}: {value}")

    # Demonstrate to_dict method
    print("\n12. Converting to Dictionary (to_dict method):")
    print("-" * 70)
    print(f"\nServer as dict (excluding children):")
    server_dict = api_server.to_dict(exclude_fields={"children", "parent"})
    for key, value in sorted(server_dict.items()):
        if isinstance(value, (list, dict)) and len(str(value)) > 80:
            print(f"  {key}: {type(value).__name__} (length: {len(value)})")
        else:
            print(f"  {key}: {value}")

    print(f"\nUser as dict (excluding password and children):")
    user_dict = alice.to_dict(exclude_fields={"children", "parent"})
    for key, value in sorted(user_dict.items()):
        if isinstance(value, (list, dict)) and len(str(value)) > 80:
            print(f"  {key}: {type(value).__name__} (length: {len(value)})")
        else:
            print(f"  {key}: {value}")

    print("\n" + "=" * 70)
    print("DEMO COMPLETED")
    print("=" * 70)
