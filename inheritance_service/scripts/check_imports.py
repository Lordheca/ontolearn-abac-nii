#!/usr/bin/env python3
"""
Script to inspect the import tree within inheritance_service.
"""
import ast
from collections import defaultdict
from pathlib import Path


def get_imports(file_path: Path) -> tuple[list[str], list[str]]:
    """Extract imports from a Python file."""
    with open(file_path, encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=str(file_path))
        except SyntaxError as e:
            print(f"⚠️  Syntax error in {file_path}: {e}")
            return [], []

    imports = []
    from_imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module = node.module
                for alias in node.names:
                    if alias.name == "*":
                        from_imports.append(f"{module}.*")
                    else:
                        from_imports.append(f"{module}.{alias.name}")

    return imports, from_imports


def analyze_directory(root_dir: Path) -> dict[str, dict]:
    """Analyze all Python files in the directory."""
    results = {}

    for py_file in root_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue

        rel_path = py_file.relative_to(root_dir)
        imports, from_imports = get_imports(py_file)

        # Filter only imports within the inheritance_service namespace
        local_imports = [
            imp
            for imp in from_imports
            if imp.startswith(
                (
                    "main.commons.actions.",
                    "main.commons.resources.",
                    "main.commons.subjects.",
                    "main.commons.visitors.",
                    "main.commons.pattern_common.",
                    "main.commons.",
                )
            )
        ]

        results[str(rel_path)] = {
            "imports": imports,
            "from_imports": from_imports,
            "local_imports": local_imports,
            "file": str(py_file),
        }

    return results


def check_circular_imports(results: dict[str, dict]) -> list[tuple[str, str]]:
    """Check for circular imports."""
    circular = []

    # Build dependency graph
    graph = defaultdict(set)
    for file_path, data in results.items():
        for imp in data["local_imports"]:
            # Convert import path to file path
            parts = imp.split(".")
            if len(parts) >= 2:
                module_path = "/".join(parts[:-1]) + ".py"
                if module_path in results:
                    graph[file_path].add(module_path)

    # DFS to detect cycles
    def has_cycle(node: str, visited: set[str], rec_stack: set[str]) -> bool:
        visited.add(node)
        rec_stack.add(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if has_cycle(neighbor, visited, rec_stack):
                    return True
            elif neighbor in rec_stack:
                return True

        rec_stack.remove(node)
        return False

    visited = set()
    for node in graph:
        if node not in visited:
            if has_cycle(node, visited, set()):
                circular.append((node, "circular dependency detected"))

    return circular


def print_report(results: dict[str, dict], circular: list[tuple[str, str]]):
    """Print a human-readable report."""
    print("=" * 80)
    print("IMPORT TREE ANALYSIS REPORT - inheritance_service")
    print("=" * 80)

    print("\n📁 IMPORT STRUCTURE BY FILE:\n")
    for file_path in sorted(results.keys()):
        data = results[file_path]
        print(f"📄 {file_path}")
        if data["local_imports"]:
            print("   Local imports:")
            for imp in sorted(data["local_imports"]):
                print(f"     → {imp}")
        else:
            print("   (No local imports)")
        print()

    print("\n" + "=" * 80)
    print("CIRCULAR IMPORT CHECK")
    print("=" * 80)

    if circular:
        print("⚠️  Circular imports detected:")
        for file_path, issue in circular:
            print(f"   {file_path}: {issue}")
    else:
        print("✅ No circular imports detected")

    print("\n" + "=" * 80)
    print("STATISTICS")
    print("=" * 80)

    total_files = len(results)
    files_with_local_imports = sum(1 for d in results.values() if d["local_imports"])
    total_local_imports = sum(len(d["local_imports"]) for d in results.values())

    print(f"Total Python files: {total_files}")
    print(f"Files with local imports: {files_with_local_imports}")
    print(f"Total local imports: {total_local_imports}")

    # Statistics per module
    print("\n📊 Statistics by module:")
    module_counts = defaultdict(int)
    for data in results.values():
        for imp in data["local_imports"]:
            module = imp.split(".")[0]
            module_counts[module] += 1

    for module in sorted(module_counts.keys()):
        print(f"   {module}: {module_counts[module]} imports")


if __name__ == "__main__":
    root_dir = Path(__file__).parent
    results = analyze_directory(root_dir)
    circular = check_circular_imports(results)
    print_report(results, circular)
