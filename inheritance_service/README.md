# Inheritance Service - Code Architecture

> **FastAPI microservice** for handling inheritance logic in ABAC (Attribute-Based Access Control) systems

---

## Table of Contents

- [Project Structure](#-project-structure)
- [Design Patterns](#-design-patterns)
- [Inheritance Model](#-inheritance-model)
- [Field Exclusion](#-field-exclusion)
- [Environment Variable Checking](#-environment-variable-checking)
- [Nested Class Creation](#-nested-class-creation)

---

## 📁 Project Structure

```
inheritance_service/
├── main/                    # Main application
│   ├── controllers/         # 🌐 API endpoints and route handlers
│   ├── libs/                # 🧩 Business logic aggregation layer
│   ├── services/            # 💾 Database repository and external services layer
│   ├── models/              # 🗄️ Database models (SQLAlchemy)
│   ├── schemas/             # 📝 Pydantic schemas for validation
│   ├── commons/             # 🔧 Utilities, Resources, Subjects, Actions
│   └── middlewares/         # ⚙️ Middleware (access logging, database, auth)
├── migrations/              # 📊 Alembic migration scripts
├── tests/                   # 🧪 Test suite
└── scripts/                 # 📜 Utility scripts
```

### Directory Descriptions

| Directory | Description |
|-----------|-------------|
| **controllers/** | API endpoints and route handlers |
| **libs/** | Aggregates business logic from different services |
| **services/** | Database (repository) or external services interaction |
| **models/** | Database models (SQLAlchemy) |
| **schemas/** | Pydantic schemas for request/response validation |
| **commons/** | Utilities, Resources, Subjects, Actions |
| **middlewares/** | Access logging, database session, authentication |

---

## 🎨 Design Patterns

The service uses four design patterns that work together to manage hierarchical ABAC entities.

### 🏗️ Composite Pattern

**Purpose**: Treat Resources, Subjects, and Actions as tree structures where each node can contain children. This allows uniform handling of leaf nodes and composite nodes (e.g., a single Server vs. a DataCenter containing many Servers).

**Location**: `main/commons/pattern_common/base.py`

**Key Components**:
- `HierarchicalEntity` - Abstract base class with `parent`, `children`, and hierarchy traversal methods
- `get_all_descendants()` - Recursively collects all descendants
- `get_ancestors()` - Walks up the tree to root
- `get_path()` - Returns path from root to current node (e.g., `["DataCenter", "WebServer", "APIServer"]`)
- `is_ancestor_of()`, `is_descendant_of()` - Relationship checks

**How it works**: When a child is created with a parent reference, it automatically registers itself via `parent._add_child(self)`. The tree is built implicitly through constructor calls.

**Example hierarchy**:
```
DataCenter (root)
  └── WebServer
      └── APIServer (leaf)
```

---

### 👁️ Visitor Pattern

**Purpose**: Add new operations (e.g., collect nodes, extract types) without modifying the entity classes. The Visitor Pattern decouples the algorithm from the object structure.

**Location**:
- Interface: `main/commons/pattern_common/visitors.py` - `HierarchyVisitor` with `visit_resource()`, `visit_subject()`, `visit_action()`
- Concrete visitors: `main/commons/visitors/` - `CollectNodesVisitor`, `CollectParentClassesVisitor`

**Key Components**:
- Each entity implements `accept(visitor)` which delegates to the appropriate `visit_*` method (double dispatch)
- `CollectNodesVisitor` - Separates Resources, Subjects, Actions into typed lists during traversal
- `CollectParentClassesVisitor` - Extracts class names from MRO (Method Resolution Order) for type information in API responses

**How it works with Composite**: The `traverse()` method (Template Method) calls `accept()` on each node. The visitor receives the concrete type (Resource, Subject, Action) and can perform type-specific logic without `isinstance` checks in the entity classes.

---

### 📐 Template Method Pattern

**Purpose**: Define the traversal algorithm once in the base class. Subclasses only customize *what* happens at each node via `accept()`, not *how* the tree is walked.

**Location**: `main/commons/pattern_common/base.py` - `traverse()` method

**Key Components**:
- `traverse(visitor)` - Fixed algorithm: (1) visit current node, (2) recursively traverse each child
- Subclasses override `accept()` to dispatch to the correct visitor method
- The traversal order (depth-first) is consistent across all entity types

**How it works**: `HierarchicalEntity.traverse()` is the template. `Resource.accept()` calls `visitor.visit_resource(self)`, `Subject.accept()` calls `visitor.visit_subject(self)`, etc. The visitor accumulates state as it visits each node.

---

### 🗄️ Repository Pattern

**Purpose**: Hide SQLAlchemy and database details behind a simple query interface. Callers specify models and relationships; the repository builds joins and filters automatically.

**Location**: `main/services/common.py`

**Key Components**:
- `execute_auto_query()` - Main entry point; resolves models by name, applies joins from foreign keys, returns rows
- `build_dynamic_query()` - Lower-level builder for custom joins and filters
- `JoinSpec`, `FilterSpec` - Typed specifications for joins and filters
- Automatic `is_deleted=False` filtering for soft-deleted models

**How it works**: Services pass model names (e.g., `"LinuxServerModel"`, `"ServerModel"`) and the repository resolves them, follows foreign keys to build joins, and executes the query. This keeps business logic free of raw SQL.

---

## 🔗 Inheritance Model

The service uses two forms of inheritance:

### 1. Class Inheritance (OOP)

Entities form class hierarchies that mirror the domain:

**Resources**:
```
Resource (base)
├── Server (adds: location)
│   └── LinuxServer (adds: ram, cpu_cores)
└── VirtualMachine (adds: cpu_cores, memory_gb, disk_gb, status)
    └── VirtualBoxVirtualMachine (adds: vbox_version, snapshot_count, guest_os)
```

**Subjects**:
```
Subject (base, adds: subject_type)
└── User (adds: id, username, password, subject_metadata, ...)
```

**Actions**:
```
Action (base, adds: action_type, requires_permission)
└── ReadAction (adds: is_destructive)
    └── WriteAction (overrides: action_type="write")
```

Child classes inherit attributes and behavior from parents. For example, `LinuxServer` has `location` (from Server) and `ram`, `cpu_cores` (its own). `get_types()` uses MRO to return `["LinuxServer", "Server", "Resource", ...]` for API responses.

### 2. Hierarchical Inheritance (Parent-Child)

Entities also form **instance-level** hierarchies via the Composite Pattern. A `LinuxServer` instance can have a `Server` instance as its parent (or another `LinuxServer`). This represents organizational or containment relationships (e.g., a server belongs to a data center).

**Attribute flow**:
- When retrieving attributes, the service merges data from the instance and its ancestors
- Child values override parent values for the same field
- `environments_to_check` and `resource_metadata` inherit up the hierarchy (see Environment Variable Checking and Nested Class Creation)

**MRO (Method Resolution Order)**:
- `get_all_attributes()` walks `__class__.__mro__` to collect attributes from the instance and all parent classes
- `CollectParentClassesVisitor` uses MRO to build the `types` list for API responses (e.g., `["VirtualBoxVirtualMachine", "VirtualMachine", "Resource"]`)
- Base classes like `HierarchicalEntity`, `ResourceSubjectBase` are excluded from the `types` output

---

## 🔒 Field Exclusion

Mechanism for excluding fields when converting Resource/Subject instances to dictionaries (used for API responses).

### Overview

- **Base Class**: `ResourceSubjectBase` (`main/commons/pattern_common/resource_subject_base.py`)
- **Method**: `to_dict(exclude_fields=None, include_private=True)`
- **Class Attribute**: `_exclude_from_dict` - defines default fields to exclude

### Default Exclusions

**User class** (`main/commons/subjects/user.py`):
- `password` - Security
- `children` - Avoid circular references
- `is_deleted`, `created_at`, `updated_at` - Typically not needed in API response

**Resource classes**: Exclude `environments_to_check` when converting to dict to avoid exposing internal config.

### Features

1. **Field Name Normalization**: Can use `password` or `_password`
2. **JSON Serialization**: Automatically converts to JSON-serializable format
3. **Inheritance Support**: Subclasses can override `_exclude_from_dict`
4. **Flexible Control**: Override defaults or add exclusions per call

---

## 🌍 Environment Variable Checking

System for checking environment attributes by hierarchy, allowing resources to inherit and override config from parent.

### Overview

- **Location**: `main/services/resource_service.py`, `main/libs/retrieve_lib/environment_retrieve_lib.py`
- **Field**: `environments_to_check` - JSON field in ResourceBase model
- **Purpose**: Dynamically call environment functions to retrieve additional attributes

### Flow

1. **Environment Inheritance**: Child takes priority → if not present, inherit from parent hierarchy
2. **Environment Function Registry**: Functions must be registered before use (`external_service.register_environment_function()`)
3. **Merging**: Merge from most distant ancestor → closest parent → child (child overrides parent)
4. **Dynamic Function Calling**: Supports registered functions, dynamic import (`"module_path.function_name"`), async/sync

---

## 🏗️ Nested Class Creation

Creates nested Resource/Subject class instances from database models, maintaining parent-child relationships without deep nesting.

### Overview

- **Location**: `main/services/resource_service.py`, `main/services/subject_service.py`
- **Function**: `_create_resource_instance_from_model_data()`, similar for subjects

### Process

1. **Parent Instance**: Create parent first (without parent's parent to avoid deep nesting)
2. **Child Instance**: Create child with parent set
3. **Attribute Merging**: Child overrides parent for same field
4. **Constructor Filtering**: Only pass parameters accepted by constructor (using `inspect.signature`)

### Design Decisions

- **Shallow Nesting**: Parent does not have its own parent in response
- **Attribute Inheritance**: Parent merges into child, child has precedence
- **Type Safety**: Only pass parameters accepted by constructor
