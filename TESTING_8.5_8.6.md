# Testing Phase 8.5 & 8.6 with FastAPI Swagger UI

## Quick Start: Access Swagger UI

1. **Start the backend**:
```bash
cd RepoAlign
docker-compose up -d
```

2. **Open Swagger UI** in your browser:
```
http://localhost:8000/docs
```

You'll see all endpoints organized by tags. Look for:
- `PHASE 8.5: GRAPH INVALIDATION`
- `PHASE 8.6: RE-ANALYSIS`

---

## Testing Workflow

### Step 1: Prepare Test Data (Create & Commit a File)

First, create a test file and commit it to git:

```bash
docker-compose exec -T backend bash -c '
cd /app/test-project

# Create initial version
cat > test_module.py << "EOF"
def add(a, b):
    """Add two numbers."""
    return a + b

def multiply(a, b):
    """Multiply two numbers."""
    return a * b

class Calculator:
    """Basic calculator class."""
    def compute(self):
        pass
EOF

# Commit it
git add test_module.py
git commit -m "Initial version with add, multiply, Calculator"
echo "Committed. Note the commit hash."
'
```

Get the commit hash from the output (or use the full path approach below).

---

## Phase 8.5: Invalidation Logic Testing

### Endpoint 1: GET `/invalidate-impact` (Dry-Run Preview)

**Purpose**: Preview what would be deleted before actually deleting it.

**Steps in Swagger UI**:

1. Navigate to **GET `/invalidate-impact`**
2. Fill in parameters:
   ```
   file_path: /app/test-project/test_module.py
   symbol_name: add
   symbol_type: function
   ```
3. Click **Try it out** → **Execute**

**Expected Response**:
```json
{
  "status": "success",
  "symbol_name": "add",
  "would_delete": true,
  "relationship_count": 0,
  "connected_node_count": 0,
  "relationship_types": [],
  "connected_labels": ["Function"]
}
```

**What it means**: The `add` function exists in the graph and would be deleted with no dependent relationships.

---

### Endpoint 2: POST `/invalidate-removed-symbol` (Delete Removed Symbol)

**Purpose**: Delete a removed function/class from the graph.

**Scenario**: The `divide()` function was deleted from the file.

**Steps in Swagger UI**:

1. Navigate to **POST `/invalidate-removed-symbol`**
2. Fill in parameters:
   ```
   file_path: /app/test-project/test_module.py
   symbol_name: multiply
   symbol_type: function
   ```
3. Click **Try it out** → **Execute**

**Expected Response**:
```json
{
  "status": "success",
  "nodes_deleted": 1,
  "relationships_deleted": 0,
  "message": "Successfully invalidated removed symbol"
}
```

---

### Endpoint 3: POST `/invalidate-modified-symbol` (Update Modified Symbol)

**Purpose**: Update a symbol that changed signature/docstring but still exists.

**Scenario**: The `add()` function now accepts 3 parameters instead of 2.

**Steps in Swagger UI**:

1. Navigate to **POST `/invalidate-modified-symbol`**
2. Fill in parameters:
   ```
   file_path: /app/test-project/test_module.py
   symbol_name: add
   symbol_type: function
   new_signature: def add(a, b, c=0)
   new_docstring: Add two or three numbers with optional third parameter.
   ```
3. Click **Try it out** → **Execute**

**Expected Response**:
```json
{
  "status": "success",
  "symbol_name": "add",
  "symbol_type": "function",
  "new_signature": "def add(a, b, c=0)",
  "message": "Successfully updated modified symbol"
}
```

---

### Endpoint 4: POST `/invalidate-file-changes` (Batch Invalidation)

**Purpose**: Invalidate multiple symbols at once (added, removed, modified).

**Steps in Swagger UI**:

1. Navigate to **POST `/invalidate-file-changes`**
2. Fill in the request body (JSON):

```json
{
  "file_path": "/app/test-project/test_module.py",
  "removed_symbols": [
    {
      "symbol_name": "multiply",
      "symbol_type": "function"
    }
  ],
  "modified_symbols": [
    {
      "symbol_name": "add",
      "symbol_type": "function"
    },
    {
      "symbol_name": "Calculator",
      "symbol_type": "class"
    }
  ]
}
```

3. Click **Try it out** → **Execute**

**Expected Response**:
```json
{
  "status": "success",
  "removed_count": 1,
  "modified_count": 2,
  "total_nodes_deleted": 1,
  "total_relationships_deleted": 0,
  "error_count": 0,
  "reports": [
    {
      "file_path": "/app/test-project/test_module.py",
      "scope": "REMOVED",
      "symbol_name": "multiply",
      "symbol_type": "function",
      "nodes_deleted": 1,
      "relationships_deleted": 0
    }
  ]
}
```

---

## Phase 8.6: Re-Analysis Testing

### Endpoint 1: POST `/re-analyze-symbol` (Single Symbol)

**Purpose**: Re-analyze a single changed symbol to get its new structure.

**Steps in Swagger UI**:

1. Navigate to **POST `/re-analyze-symbol`**
2. Fill in parameters:
   ```
   file_path: /app/test-project/test_module.py
   symbol_name: add
   symbol_type: function
   ```
3. Paste the current file content in `file_content` parameter:

```python
def add(a, b, c=0):
    """Add up to three numbers with optional third parameter."""
    return a + b + c

def multiply(a, b):
    """Multiply two numbers."""
    return a * b

class Calculator:
    """Basic calculator class."""
    def compute(self):
        pass
```

4. Click **Try it out** → **Execute**

**Expected Response**:
```json
{
  "status": "success",
  "symbol": {
    "symbol_name": "add",
    "symbol_type": "function",
    "file_path": "/app/test-project/test_module.py",
    "start_line": 1,
    "end_line": 3,
    "signature": "def add(a, b, c)",
    "docstring": "Add up to three numbers with optional third parameter.",
    "decorators": [],
    "parameters": [
      {
        "name": "a",
        "annotation": null,
        "default_value": null
      },
      {
        "name": "b",
        "annotation": null,
        "default_value": null
      },
      {
        "name": "c",
        "annotation": null,
        "default_value": "0"
      }
    ],
    "return_type": null,
    "base_classes": [],
    "methods": [],
    "imports_used": [],
    "functions_called": [],
    "cyclomatic_complexity": 1,
    "lines_of_code": 3
  }
}
```

---

### Endpoint 2: POST `/re-analyze-file-changes` (Batch Re-Analysis)

**Purpose**: Re-analyze all changed symbols in a file.

**Steps in Swagger UI**:

1. Navigate to **POST `/re-analyze-file-changes`**
2. Fill in the request body:

```json
{
  "file_path": "/app/test-project/test_module.py",
  "file_content": "def add(a, b, c=0):\n    \"\"\"Add up to three numbers with optional third parameter.\"\"\"\n    return a + b + c\n\ndef multiply(a, b):\n    \"\"\"Multiply two numbers.\"\"\"\n    return a * b\n\ndef power(a, b):\n    \"\"\"Calculate a to the power of b.\"\"\"\n    return a ** b\n\nclass Calculator:\n    \"\"\"Basic calculator class.\"\"\"\n    def compute(self):\n        pass",
  "added_symbols": [
    {
      "symbol_name": "power",
      "symbol_type": "function"
    }
  ],
  "modified_symbols": [
    {
      "symbol_name": "add",
      "symbol_type": "function"
    }
  ]
}
```

3. Click **Try it out** → **Execute**

**Expected Response**:
```json
{
  "status": "success",
  "file_path": "/app/test-project/test_module.py",
  "added_symbols": [
    {
      "symbol_name": "power",
      "symbol_type": "function",
      "signature": "def power(a, b)",
      "docstring": "Calculate a to the power of b.",
      "parameters": [...],
      "functions_called": [],
      "cyclomatic_complexity": 1,
      "lines_of_code": 2
    }
  ],
  "modified_symbols": [
    {
      "symbol_name": "add",
      "symbol_type": "function",
      "signature": "def add(a, b, c)",
      "docstring": "Add up to three numbers with optional third parameter.",
      "parameters": [...],
      "functions_called": [],
      "cyclomatic_complexity": 1,
      "lines_of_code": 3
    }
  ],
  "error_count": 0,
  "errors": []
}
```

---

### Endpoint 3: POST `/re-analyze-batch` (Multiple Files)

**Purpose**: Re-analyze changes across multiple files in one request.

**Steps in Swagger UI**:

1. Navigate to **POST `/re-analyze-batch`**
2. Fill in the request body:

```json
{
  "file_analyses": [
    {
      "file_path": "/app/test-project/test_module.py",
      "file_content": "def add(a, b, c=0):\n    return a + b + c\n\ndef power(a, b):\n    return a ** b",
      "added_symbols": [
        {
          "symbol_name": "power",
          "symbol_type": "function"
        }
      ],
      "modified_symbols": [
        {
          "symbol_name": "add",
          "symbol_type": "function"
        }
      ]
    },
    {
      "file_path": "/app/test-project/utils.py",
      "file_content": "def helper():\n    pass",
      "added_symbols": [
        {
          "symbol_name": "helper",
          "symbol_type": "function"
        }
      ],
      "modified_symbols": []
    }
  ]
}
```

3. Click **Try it out** → **Execute**

**Expected Response**:
```json
{
  "status": "success",
  "total_files": 2,
  "results": [
    {
      "file_path": "/app/test-project/test_module.py",
      "status": "success",
      "added_symbols": [...],
      "modified_symbols": [...],
      "error_count": 0
    },
    {
      "file_path": "/app/test-project/utils.py",
      "status": "success",
      "added_symbols": [...],
      "modified_symbols": [],
      "error_count": 0
    }
  ],
  "total_symbols_analyzed": 3,
  "total_errors": 0
}
```

---

## Complete Testing Scenario (Step-by-Step)

### Scenario: Simulate file evolution and track graph changes

**Step 1**: Create and commit initial version
```bash
docker-compose exec -T backend bash -c '
cd /app/test-project
cat > scenario.py << "EOF"
def calculate(x, y):
    """Calculate sum."""
    return x + y

def display():
    """Display results."""
    print("Results")

class Helper:
    """Helper class."""
    pass
EOF

git add scenario.py
git commit -m "v1: calculate, display, Helper"
'
```

**Step 2**: Test Phase 8.4 (Get AST Diff)
- Modify the file
- Use GET `/diff-file` to see what changed

**Step 3**: Test Phase 8.5 (Invalidate Changes)
- Use GET `/invalidate-impact` to preview impact
- Use POST `/invalidate-removed-symbol` for removed symbols
- Use POST `/invalidate-file-changes` for batch operations

**Step 4**: Test Phase 8.6 (Re-Analyze)
- Use POST `/re-analyze-file-changes` to get new structure
- Use POST `/re-analyze-batch` for multiple files

---

## Tips for Testing

### 1. **Use Small Test Files**
   - Easier to understand the flow
   - Faster to re-analyze
   - Clear input/output relationship

### 2. **Test Incrementally**
   - Test one endpoint at a time
   - Verify each response carefully
   - Note the data structures returned

### 3. **Copy Actual File Content**
   - For `file_content` parameter, copy the actual Python file content
   - Use the exact file paths from your filesystem
   - Ensure file is valid Python

### 4. **Combine with Phase 8.4**
   - Use Phase 8.4 AST Diffing to identify changes
   - Pass those changes to Phase 8.5/8.6
   - Test the full flow: Diff → Invalidate → Re-Analyze

### 5. **Check Logs**
   - While testing, check backend logs:
   ```bash
   docker-compose logs -f backend | grep PHASE
   ```
   - Look for `[PHASE 8.5]` and `[PHASE 8.6]` tags
   - They show execution flow and timing

---

## Sample Request Builder

Use this template to quickly build requests:

```bash
# Get file content for copy-paste
cd /app/test-project
cat test_module.py  # Copy this into file_content parameter

# Get file paths
pwd
ls -la test_module.py

# Check git commit history
git log --oneline
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **"Symbol not found"** | Verify symbol exists in file, use exact case |
| **"Syntax error"** | Ensure file_content is valid Python, no truncation |
| **Empty response** | Check if file_path is absolute (not relative) |
| **Import errors** | File being analyzed must be valid Python |
| **Status: "partial"** | Some symbols had errors; check `errors` array |

---

## Next Steps After Testing

Once Phase 8.5 & 8.6 are working:

1. **Phase 8.7**: Test Targeted Graph Update
   - Takes Phase 8.6 output
   - Writes to Neo4j

2. **Integration Test**: Full 8.4→8.5→8.6→8.7 pipeline
   - Make file changes
   - Run AST Diff
   - Invalidate old nodes
   - Re-analyze new symbols
   - Update graph

3. **Phase 8.8**: Maintenance Worker
   - Automates this entire flow
   - Runs continuously in background
