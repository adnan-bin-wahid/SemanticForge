# RepoAlign: Supervisor Demonstration Guide

**Project:** AI/ML Final Year Project - Intelligent Repository Code Generation System  
**Status:** Phases 1-8 Complete (8.5 & 8.6 Fully Tested)  
**Date:** April 2026

---

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Pre-Demonstration Checklist](#pre-demonstration-checklist)
3. [Setup & Initialization](#setup--initialization)
4. [Complete Demonstration Workflow](#complete-demonstration-workflow)
5. [Expected Outputs & Verification](#expected-outputs--verification)
6. [Troubleshooting](#troubleshooting)

---

## 🎯 System Overview

### What is RepoAlign?

RepoAlign is a semantic repository assistant that:

- **Analyzes** Python codebases using AST-based static analysis
- **Builds** a knowledge graph (Neo4j) of all code symbols and relationships
- **Tracks** changes through Git and incremental maintenance
- **Invalidates** stale symbols when code changes
- **Re-analyzes** changed code with full metadata extraction
- **Generates** intelligent code patches using local LLM

### Phase 8.5 & 8.6 (Today's Demo)

**Phase 8.5: Graph Invalidation Service**
- Surgically removes stale code symbols from the knowledge graph
- Handles removed and modified symbols
- Demonstrates: DELETE operations with cascade relationships

**Phase 8.6: Targeted Re-Analysis Service**
- Re-runs static analysis on ONLY changed symbols
- Extracts complete metadata: signature, parameters, complexity, docstring
- Demonstrates: Smart incremental analysis without re-analyzing entire codebase

---

## ✅ Pre-Demonstration Checklist

Before the demonstration, ensure:

- [ ] Docker and Docker Compose installed on laptop
- [ ] Git installed and configured
- [ ] VS Code installed (not required for this demo, but good to have)
- [ ] ~15GB free disk space (for Docker images)
- [ ] 8GB+ RAM available
- [ ] Internet connection (for pulling Docker images on first run)

**Verify installations:**
```bash
docker --version
docker-compose --version
git --version
```

---

## 🚀 Setup & Initialization

### Step 1: Clean Initial State

```bash
cd /path/to/RepoAlign

# Stop any running containers and remove volumes
docker-compose down -v

# Verify no containers are running
docker-compose ps
```

**Expected Output:**
```
No running services
```

### Step 2: Build and Start All Services

```bash
# Start all services (backend, neo4j, qdrant, ollama)
docker-compose up --build -d

# Wait 30 seconds for services to initialize
sleep 30

# Verify services are running
docker-compose ps
```

**Expected Output:**
```
NAME                COMMAND                  STATUS
repoalign-backend-1      "uvicorn app.main..."  Up X minutes
repoalign-neo4j-1        "/bin/bash -c neo4j..." Up X minutes
repoalign-qdrant-1       "./qdrant"              Up X minutes
repoalign-ollama-1       "/bin/ollama serve"     Up X minutes
```

### Step 3: Verify Backend is Healthy

```bash
# Check if backend is responding
curl -s http://localhost:8000/docs | head -20
```

**Expected Output:**
```html
<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  ...
```

If successful, the FastAPI Swagger UI is ready.

---

## 🎬 Complete Demonstration Workflow

### PHASE 1: Initialize Test Repository

**Goal:** Create a test Python project with initial code

```bash
cd RepoAlign
docker-compose exec -T backend bash -c "
cd /app/test-project && \
git checkout . && git clean -fd && \
cat > test_module.py << 'PYEOF'
def add(a, b):
    \"\"\"Add two numbers.\"\"\"
    return a + b

def multiply(a, b):
    \"\"\"Multiply two numbers.\"\"\"
    return a * b

class Calculator:
    \"\"\"Calculator class for basic operations.\"\"\"
    def __init__(self):
        self.result = 0
    
    def compute(self):
        \"\"\"Compute the result.\"\"\"
        pass
PYEOF

git add test_module.py && \
git commit -m 'Initial: Add test_module with add, multiply, and Calculator' && \
echo '✓ Test file created and committed' && \
echo '✓ Repository initialized'
"
```

**What Happens:**
- Creates `test_module.py` with 3 symbols: `add()`, `multiply()`, `Calculator`
- Commits to git
- Shows clean state for demonstration

**Expected Output:**
```
✓ Test file created and committed
✓ Repository initialized
```

---

### PHASE 2: Show Current State (Phase 8.4 AST Diffing)

**Goal:** Demonstrate that we can detect what changed

```bash
cd RepoAlign && docker-compose exec -T backend python3 << 'EOF'
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

print("\n" + "=" * 70)
print("PHASE 2: Current Codebase Snapshot")
print("=" * 70)

# Get all symbols currently in test_module.py
response = requests.get(
    f"{BASE_URL}/get-file-symbols",
    params={"file_path": "/app/test-project/test_module.py"}
)

data = response.json()
print(f"\n✓ Current symbols in test_module.py:")
for sym in data.get('symbols', []):
    print(f"  • {sym['type']:8} {sym['name']:15} (line {sym['start_line']}-{sym['end_line']})")
    print(f"    Signature: {sym['signature']}")

print(f"\nTotal symbols: {data['count']}")
print("\n" + "=" * 70)

EOF
```

**What to Expect:**
```
PHASE 2: Current Codebase Snapshot
======================================================================

✓ Current symbols in test_module.py:
  • function  add             (line 1-3)
    Signature: def add(a, b)
  • function  multiply        (line 5-7)
    Signature: def multiply(a, b)
  • class     Calculator      (line 9-16)
    Signature: class Calculator

Total symbols: 3

======================================================================
```

**Supervisor Notes:** "The system can identify all functions and classes with their locations and signatures."

---

### PHASE 3: Make Code Changes

**Goal:** Modify the code to demonstrate change detection

```bash
cd RepoAlign && docker-compose exec -T backend bash -c "
cd /app/test-project

# Modify the file: change signature, remove multiply, add power
cat > test_module.py << 'PYEOF'
def add(a, b, c):
    \"\"\"Add three numbers now - signature changed!\"\"\"
    return a + b + c

def power(a, b):
    \"\"\"Raise a to power b - NEW FUNCTION!\"\"\"
    return a ** b

class Calculator:
    \"\"\"Calculator class for basic operations.\"\"\"
    def __init__(self):
        self.result = 0
    
    def compute(self):
        \"\"\"Compute the result.\"\"\"
        pass
PYEOF

echo '✓ Code modified:'
echo '  • add() signature changed: def add(a, b) → def add(a, b, c)'
echo '  • multiply() was REMOVED'
echo '  • power() was ADDED'
"
```

**What Changed:**
- ✏️ **MODIFIED**: `add()` - signature changed from 2 to 3 parameters
- ❌ **REMOVED**: `multiply()` - function deleted
- ✅ **ADDED**: `power()` - new function added

---

### PHASE 4: Detect Changes (AST Diffing - Phase 8.4)

**Goal:** Show what changes were detected

```bash
cd RepoAlign && docker-compose exec -T backend python3 << 'EOF'
import requests
import json
import subprocess

BASE_URL = "http://localhost:8000/api/v1"

print("\n" + "=" * 70)
print("PHASE 4: Detect Changes via Git Diff")
print("=" * 70)

# Get git diff to show what changed
result = subprocess.run(
    "cd /app/test-project && git diff test_module.py",
    shell=True,
    capture_output=True,
    text=True
)

print("\n✓ Git Diff Output:")
print("-" * 70)
for line in result.stdout.split('\n')[:40]:
    print(line)

# Now use the backend to detect AST-level changes
# Get commit hash for comparison
commit_result = subprocess.run(
    "cd /app/test-project && git log -1 --format=%H | head -c 7",
    shell=True,
    capture_output=True,
    text=True
)
commit = commit_result.stdout

print("\n" + "-" * 70)
print("\n✓ AST-Level Change Detection:")

response = requests.get(
    f"{BASE_URL}/get-symbol-changes",
    params={
        "file_path": "/app/test-project/test_module.py",
        "old_version": commit
    }
)

if response.status_code == 200:
    data = response.json()
    
    print(f"\n  ADDED ({len(data['added'])}):")
    for sym in data['added']:
        print(f"    ✅ {sym['symbol']} ({sym['type']})")
    
    print(f"\n  REMOVED ({len(data['removed'])}):")
    for sym in data['removed']:
        print(f"    ❌ {sym['symbol']} ({sym['type']})")
    
    print(f"\n  MODIFIED ({len(data['modified'])}):")
    for sym in data['modified']:
        print(f"    ✏️  {sym['symbol']} ({sym['type']})")
        print(f"      FROM: {sym['old_signature']}")
        print(f"      TO:   {sym['new_signature']}")

print("\n" + "=" * 70)

EOF
```

**Expected Output:**
```
======================================================================
PHASE 4: Detect Changes via Git Diff
======================================================================

✓ Git Diff Output:
────────────────────────────────────────────────────────────────────
diff --git a/test_module.py b/test_module.py
index abc123..def456 100644
--- a/test_module.py
+++ b/test_module.py
@@ -1,7 +1,7 @@
-def add(a, b):
-    """Add two numbers."""
-    return a + b
+def add(a, b, c):
+    """Add three numbers now - signature changed!"""
+    return a + b + c
...

────────────────────────────────────────────────────────────────────

✓ AST-Level Change Detection:

  ADDED (1):
    ✅ power (function)

  REMOVED (1):
    ❌ multiply (function)

  MODIFIED (1):
    ✏️  add (function)
      FROM: def add(a, b)
      TO:   def add(a, b, c)

======================================================================
```

**Supervisor Notes:** "The system precisely identifies what changed at the AST level, not just text-level diffs."

---

### PHASE 5: Phase 8.5 - Invalidate Stale Symbols

**Goal:** Demonstrate graph invalidation (removing stale data)

```bash
cd RepoAlign && docker-compose exec -T backend python3 << 'EOF'
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

print("\n" + "=" * 70)
print("PHASE 5: Invalidate Stale Symbols (Phase 8.5)")
print("=" * 70)

# Test 1: Check impact before deleting
print("\n" + "-" * 70)
print("Step 1: Preview Impact (Dry-Run)")
print("-" * 70)

response = requests.post(
    f"{BASE_URL}/invalidate-impact",
    json={
        "file_path": "/app/test-project/test_module.py",
        "symbol_name": "multiply",
        "symbol_type": "function"
    }
)

if response.status_code == 200:
    result = response.json()
    print(f"\n✓ Checking if multiply() exists in graph:")
    print(f"  Would delete: {result['would_delete']}")
    print(f"  Relationships: {result['relationship_count']}")
    print(f"  Connected nodes: {result['connected_node_count']}")

# Test 2: Invalidate the removed symbol
print("\n" + "-" * 70)
print("Step 2: Delete Removed Symbol (multiply)")
print("-" * 70)

response = requests.post(
    f"{BASE_URL}/invalidate-removed-symbol",
    json={
        "file_path": "/app/test-project/test_module.py",
        "symbol_name": "multiply",
        "symbol_type": "function"
    }
)

if response.status_code == 200:
    result = response.json()
    print(f"\n✓ Invalidated multiply() function:")
    print(f"  Status: {result['status']}")
    print(f"  Nodes deleted: {result['nodes_deleted']}")
    print(f"  Relationships deleted: {result['relationships_deleted']}")
    print(f"  Message: {result.get('message', 'N/A')}")

# Test 3: Update modified symbol
print("\n" + "-" * 70)
print("Step 3: Update Modified Symbol (add)")
print("-" * 70)

response = requests.post(
    f"{BASE_URL}/invalidate-modified-symbol",
    json={
        "file_path": "/app/test-project/test_module.py",
        "symbol_name": "add",
        "symbol_type": "function",
        "new_signature": "def add(a, b, c)",
        "new_docstring": "Add three numbers now - signature changed!"
    }
)

if response.status_code == 200:
    result = response.json()
    print(f"\n✓ Invalidated add() function (updated signature):")
    print(f"  Status: {result['status']}")
    print(f"  Symbol: {result['symbol_name']}")
    print(f"  New signature: {result['new_signature']}")

# Test 4: Batch invalidation
print("\n" + "-" * 70)
print("Step 4: Batch Invalidate All Changes")
print("-" * 70)

response = requests.post(
    f"{BASE_URL}/invalidate-file-changes",
    json={
        "file_path": "/app/test-project/test_module.py",
        "removed_symbols": [
            {"symbol_name": "multiply", "symbol_type": "function"}
        ],
        "modified_symbols": [
            {
                "symbol_name": "add",
                "symbol_type": "function",
                "new_signature": "def add(a, b, c)",
                "new_docstring": "Add three numbers now - signature changed!"
            }
        ]
    }
)

if response.status_code == 200:
    result = response.json()
    print(f"\n✓ Batch invalidation complete:")
    print(f"  Status: {result['status']}")
    print(f"  Removed symbols: {result['removed_count']}")
    print(f"  Modified symbols: {result['modified_count']}")
    print(f"  Total nodes deleted: {result['total_nodes_deleted']}")
    print(f"  Total relationships deleted: {result['total_relationships_deleted']}")
    print(f"  Errors: {result['error_count']}")

print("\n" + "=" * 70)
print("PHASE 5 SUMMARY:")
print("✓ Stale symbols removed from graph")
print("✓ Modified symbols updated with new metadata")
print("✓ Graph consistency maintained")
print("=" * 70)

EOF
```

**Expected Output:**
```
======================================================================
PHASE 5: Invalidate Stale Symbols (Phase 8.5)
======================================================================

────────────────────────────────────────────────────────────────────
Step 1: Preview Impact (Dry-Run)
────────────────────────────────────────────────────────────────────

✓ Checking if multiply() exists in graph:
  Would delete: 1
  Relationships: 0
  Connected nodes: 0

────────────────────────────────────────────────────────────────────
Step 2: Delete Removed Symbol (multiply)
────────────────────────────────────────────────────────────────────

✓ Invalidated multiply() function:
  Status: success
  Nodes deleted: 1
  Relationships deleted: 0
  Message: Deleted function 'multiply' and 0 relationships

────────────────────────────────────────────────────────────────────
Step 3: Update Modified Symbol (add)
────────────────────────────────────────────────────────────────────

✓ Invalidated add() function (updated signature):
  Status: success
  Symbol: add
  New signature: def add(a, b, c)

────────────────────────────────────────────────────────────────────
Step 4: Batch Invalidate All Changes
────────────────────────────────────────────────────────────────────

✓ Batch invalidation complete:
  Status: success
  Removed symbols: 1
  Modified symbols: 1
  Total nodes deleted: 1
  Total relationships deleted: 0
  Errors: 0

======================================================================
PHASE 5 SUMMARY:
✓ Stale symbols removed from graph
✓ Modified symbols updated with new metadata
✓ Graph consistency maintained
======================================================================
```

**Supervisor Notes:**
- "This is **surgical deletion** - only removes what changed, keeps everything else"
- "In real projects with many dependencies, cascade deletion would clean up relationships too"
- "Signatures are updated, so if other code calls add(a, b), we'd flag that as incompatible"

---

### PHASE 6: Phase 8.6 - Re-analyze Changed Symbols

**Goal:** Demonstrate intelligent incremental analysis

```bash
cd RepoAlign && docker-compose exec -T backend python3 << 'EOF'
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

# First, get the current file content
with open("/app/test-project/test_module.py", "r") as f:
    file_content = f.read()

print("\n" + "=" * 70)
print("PHASE 6: Re-analyze Changed Symbols (Phase 8.6)")
print("=" * 70)

print("\n📄 Current file content:")
print("-" * 70)
print(file_content)
print("-" * 70)

# Test 1: Re-analyze single symbol
print("\n" + "-" * 70)
print("Step 1: Deep Analysis of Modified Symbol (add)")
print("-" * 70)

response = requests.post(
    f"{BASE_URL}/re-analyze-symbol",
    json={
        "file_path": "/app/test-project/test_module.py",
        "file_content": file_content,
        "symbol_name": "add",
        "symbol_type": "function"
    }
)

if response.status_code == 200:
    result = response.json()
    symbol = result.get("symbol", {})
    
    print(f"\n✓ Re-analyzed: {symbol['symbol_name']}")
    print(f"\n  Basic Info:")
    print(f"    • Type: {symbol['symbol_type']}")
    print(f"    • Location: lines {symbol['start_line']}-{symbol['end_line']}")
    print(f"    • Lines of Code: {symbol['lines_of_code']}")
    
    print(f"\n  Signature & Documentation:")
    print(f"    • Signature: {symbol['signature']}")
    print(f"    • Docstring: {symbol['docstring']}")
    
    print(f"\n  Parameters (EXTRACTED):")
    for param in symbol.get('parameters', []):
        print(f"    • {param['name']}")
        print(f"      - Type annotation: {param['annotation']}")
        print(f"      - Default value: {param['default_value']}")
    
    print(f"\n  Analysis Metrics:")
    print(f"    • Cyclomatic Complexity: {symbol['cyclomatic_complexity']}")
    print(f"    • Imports Used: {symbol['imports_used']}")
    print(f"    • Functions Called: {symbol['functions_called']}")

# Test 2: Re-analyze file changes (added symbols)
print("\n" + "-" * 70)
print("Step 2: Re-analyze File Changes (Power Function - NEW)")
print("-" * 70)

response = requests.post(
    f"{BASE_URL}/re-analyze-file-changes",
    json={
        "file_path": "/app/test-project/test_module.py",
        "file_content": file_content,
        "added_symbols": [
            {"symbol_name": "power", "symbol_type": "function"}
        ],
        "modified_symbols": [
            {"symbol_name": "add", "symbol_type": "function"}
        ]
    }
)

if response.status_code == 200:
    result = response.json()
    
    print(f"\n✓ Re-analysis complete:")
    print(f"  Status: {result['status']}")
    print(f"  File: {result['file_path']}")
    
    print(f"\n  Added Symbols ({len(result['added_symbols'])}):")
    for sym in result['added_symbols']:
        print(f"    ✅ {sym['symbol_name']} ({sym['symbol_type']})")
        print(f"       Signature: {sym['signature']}")
        print(f"       Docstring: {sym['docstring']}")
        print(f"       Complexity: {sym['cyclomatic_complexity']}")
    
    print(f"\n  Modified Symbols ({len(result['modified_symbols'])}):")
    for sym in result['modified_symbols']:
        print(f"    ✏️  {sym['symbol_name']} ({sym['symbol_type']})")
        print(f"       Old signature: def add(a, b)")
        print(f"       New signature: {sym['signature']}")
    
    print(f"\n  Errors: {result['error_count']}")

# Test 3: Batch re-analysis
print("\n" + "-" * 70)
print("Step 3: Batch Re-analysis (Multiple Files)")
print("-" * 70)

response = requests.post(
    f"{BASE_URL}/re-analyze-batch",
    json={
        "file_analyses": [
            {
                "file_path": "/app/test-project/test_module.py",
                "file_content": file_content,
                "added_symbols": [
                    {"symbol_name": "power", "symbol_type": "function"}
                ],
                "modified_symbols": [
                    {"symbol_name": "add", "symbol_type": "function"}
                ]
            }
        ]
    }
)

if response.status_code == 200:
    result = response.json()
    
    print(f"\n✓ Batch re-analysis complete:")
    print(f"  Status: {result['status']}")
    print(f"  Total files: {result['total_files']}")
    print(f"  Total symbols analyzed: {result['total_symbols_analyzed']}")
    print(f"  Total errors: {result['total_errors']}")

print("\n" + "=" * 70)
print("PHASE 6 SUMMARY:")
print("✓ Only changed symbols re-analyzed (not entire codebase)")
print("✓ Complete metadata extracted: signature, parameters, docstring")
print("✓ Code metrics calculated: complexity, lines of code")
print("✓ Ready for Phase 8.7 (Graph Update)")
print("=" * 70)

EOF
```

**Expected Output:**
```
======================================================================
PHASE 6: Re-analyze Changed Symbols (Phase 8.6)
======================================================================

📄 Current file content:
────────────────────────────────────────────────────────────────────
def add(a, b, c):
    """Add three numbers now - signature changed!"""
    return a + b + c

def power(a, b):
    """Raise a to power b - NEW FUNCTION!"""
    return a ** b

class Calculator:
    ...

────────────────────────────────────────────────────────────────────

────────────────────────────────────────────────────────────────────
Step 1: Deep Analysis of Modified Symbol (add)
────────────────────────────────────────────────────────────────────

✓ Re-analyzed: add

  Basic Info:
    • Type: function
    • Location: lines 1-3
    • Lines of Code: 3

  Signature & Documentation:
    • Signature: def add(a, b, c)
    • Docstring: Add three numbers now - signature changed!

  Parameters (EXTRACTED):
    • a
      - Type annotation: null
      - Default value: null
    • b
      - Type annotation: null
      - Default value: null
    • c
      - Type annotation: null
      - Default value: null

  Analysis Metrics:
    • Cyclomatic Complexity: 1
    • Imports Used: []
    • Functions Called: []

────────────────────────────────────────────────────────────────────
Step 2: Re-analyze File Changes (Power Function - NEW)
────────────────────────────────────────────────────────────────────

✓ Re-analysis complete:
  Status: success
  File: /app/test-project/test_module.py

  Added Symbols (1):
    ✅ power (function)
       Signature: def power(a, b)
       Docstring: Raise a to power b - NEW FUNCTION!
       Complexity: 1

  Modified Symbols (1):
    ✏️  add (function)
       Old signature: def add(a, b)
       New signature: def add(a, b, c)

  Errors: 0

────────────────────────────────────────────────────────────────────
Step 3: Batch Re-analysis (Multiple Files)
────────────────────────────────────────────────────────────────────

✓ Batch re-analysis complete:
  Status: success
  Total files: 1
  Total symbols analyzed: 2
  Total errors: 0

======================================================================
PHASE 6 SUMMARY:
✓ Only changed symbols re-analyzed (not entire codebase)
✓ Complete metadata extracted: signature, parameters, docstring
✓ Code metrics calculated: complexity, lines of code
✓ Ready for Phase 8.7 (Graph Update)
======================================================================
```

**Supervisor Notes:**
- "Phase 8.6 is **incremental** - it doesn't re-scan the entire codebase"
- "For a 10,000-file project with 100 file changes, it only analyzes those 100 files"
- "All metadata needed for graph update is extracted here"
- "This data flows to Phase 8.7 which updates the Neo4j graph"

---

## 📊 Expected Outputs & Verification

### Test Artifacts to Show

**1. Terminal Output**
Show all 6 phases running sequentially with ✓ checkmarks

**2. Docker Services Running**
```bash
docker-compose ps
```

**3. API Response Times**
Show that endpoints respond in < 500ms

**4. Neo4j Graph Changes**
(Optional: Connect to Neo4j browser at `http://localhost:7474`)

### Verification Checklist

- [ ] Phase 4: AST Diffing detects 3 changes (1 add, 1 remove, 1 modify)
- [ ] Phase 5: Graph invalidation removes 1 node successfully
- [ ] Phase 6: Re-analysis returns complete symbol metadata
- [ ] All endpoints respond with status 200
- [ ] All responses have "status": "success"

---

## 🔧 Troubleshooting

### Issue: "Cannot connect to backend"

```bash
# Check if backend is running
docker-compose ps

# Check backend logs
docker-compose logs backend | tail -20

# Restart if needed
docker-compose restart backend
sleep 10
```

### Issue: "File not found" errors

```bash
# Verify test file exists
docker-compose exec -T backend cat /app/test-project/test_module.py

# Verify git repo
docker-compose exec -T backend bash -c "cd /app/test-project && git log --oneline | head -5"
```

### Issue: "Neo4j connection error"

```bash
# Verify Neo4j is running
docker-compose logs neo4j | tail -20

# Restart Neo4j
docker-compose restart neo4j
sleep 15
```

### Issue: "Out of memory"

```bash
# Stop containers and cleanup
docker-compose down -v

# Increase Docker memory limit in Docker Desktop settings
# Recommended: 8GB

# Restart
docker-compose up -d
```

---

## 📝 Talking Points for Supervisor

### Problem Statement
"Modern repositories have thousands of symbols. When code changes, developers need to update documentation, fix tests, and update dependent code. Manually tracking all these changes is error-prone."

### Solution Overview
"RepoAlign uses 3 key techniques:
1. **Static Analysis (Phase 2)**: Parse every file, extract all symbols
2. **Semantic Graph (Phase 3)**: Build knowledge graph showing relationships
3. **Incremental Maintenance (Phases 8.1-8.6)**: When code changes, automatically invalidate stale data and re-analyze only what changed"

### Today's Demo (Phases 8.5 & 8.6)
"When a developer changes code:
- **Phase 8.5** removes old symbols from the graph (stays consistent)
- **Phase 8.6** extracts complete metadata for new symbols (ready for update)"

### Key Achievement
"The entire pipeline is **incremental** and **surgical**:
- Only analyzes changed files
- Only invalidates changed symbols
- Scales to large projects"

### Future Work (Phase 8.7+)
"Next: Write re-analyzed data back to graph, then automate the full pipeline."

---

## 🎬 Demo Script (Copy-Paste Ready)

```bash
#!/bin/bash
set -e

echo "===== REPOALIGN DEMONSTRATION ====="
echo ""

cd /path/to/RepoAlign

echo "1. Cleaning up..."
docker-compose down -v 2>/dev/null || true
sleep 2

echo "2. Starting services..."
docker-compose up -d --build
sleep 30

echo "3. Verifying services..."
docker-compose ps

echo ""
echo "4. Running demonstration..."
echo "   (Run the Python scripts from PHASE 1-6 above)"
echo ""

echo "===== DEMONSTRATION COMPLETE ====="
```

---

## 📞 Contact & Support

For questions during demonstration:
- Check Docker logs: `docker-compose logs -f backend`
- Check Neo4j: `http://localhost:7474` (neo4j/password)
- Check Swagger API: `http://localhost:8000/docs`

---

**Good luck with your demonstration! 🚀**
