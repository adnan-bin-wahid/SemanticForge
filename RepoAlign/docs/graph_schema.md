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

*(To be defined in Sub-phase 3.4)*
