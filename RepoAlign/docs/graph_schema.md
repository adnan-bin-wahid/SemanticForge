# RepoAlign Graph Schema

This document formally defines the schema for the knowledge graph used by RepoAlign.

## Node Labels

### `Repository`

Represents a single code repository.

- **Properties:**
  - `name` (String): The name of the repository (e.g., "RepoAlign").
  - `path` (String): The root path of the repository that was analyzed.

### `File`

Represents a single source code file.

- **Properties:**
  - `name` (String): The name of the file (e.g., "main.py").
  - `path` (String): The full path to the file within the repository.

### `Module`

Represents a Python module that is imported.

- **Properties:**
  - `name` (String): The fully qualified name of the module (e.g., "fastapi.routing").

### `Class`

Represents a class definition.

- **Properties:**
  - `name` (String): The name of the class.
  - `start_line` (Integer): The starting line number of the class definition.
  - `end_line` (Integer): The ending line number of the class definition.

### `Function`

Represents a function or method definition.

- **Properties:**
  - `name` (String): The name of the function or method.
  - `signature` (String): The function's signature, including parameters and type hints.
  - `start_line` (Integer): The starting line number of the function definition.
  - `end_line` (Integer): The ending line number of the function definition.

---

## Relationship Types

### `CONTAINS`

Connects a `Repository` to the `File` nodes within it.

- **Structure:** `(Repository)-[:CONTAINS]->(File)`

### `DEFINES`

Connects a `File` to a `Class` or `Function` it defines.

- **Structure:** `(File)-[:DEFINES]->(Class)`
- **Structure:** `(File)-[:DEFINES]->(Function)`

### `IMPORTS`

Connects a `File` to a `Module` it imports.

- **Structure:** `(File)-[:IMPORTS]->(Module)`

### `INHERITS`

Connects a `Class` to a parent `Class` it inherits from.

- **Structure:** `(Class)-[:INHERITS]->(Class)`

### `CALLS`

Connects a `Function` to another `Function` it calls.

- **Structure:** `(Function)-[:CALLS]->(Function)`
