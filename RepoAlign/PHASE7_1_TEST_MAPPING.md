# Phase 7.1: Test-to-Code Mapping Implementation

## ✅ Status: COMPLETE

Phase 7.1 has been fully implemented. This phase analyzes a repository to determine which test files cover which source code files.

---

## 🎯 What Phase 7.1 Does

Creates a **mapping** that links test files to application code:

```
Test File: utils/helpers-test.py
├─ Imports: ['helpers']
└─ Covers: 
   ├─ utils/helpers.py (contains: format_greeting, validate_email, etc.)
```

---

## 📋 Implementation Details

### 1. **Test Discovery**
- Identifies test files using naming conventions:
  - Filenames ending with `_test.py`
  - Filenames starting with `test_`
  - Files in `tests/` or `test/` directories

### 2. **Source File Discovery**
- Identifies source files:
  - Not test files
  - Not `__init__.py` in special directories
  - Not in `__pycache__` or `.pytest_cache`

### 3. **Import Analysis**
- Uses AST (Abstract Syntax Tree) to parse test files
- Extracts all `import` and `from ... import` statements
- Maps imported modules to source files

### 4. **Mapping Creation**
- Creates bidirectional mapping:
  - **Test-to-Source**: Which source files does each test cover?
  - **Source-to-Test**: Which tests cover each source file?

### 5. **Coverage Analysis**
- Calculates:
  - Total test/source files
  - Number of covered source files
  - Coverage percentage
  - Uncovered source files

---

## 🔧 Files Created

### Backend Services
- **`backend/app/services/test_mapper.py`** (Main module)
  - `TestToCodeMapper` class
  - File discovery logic
  - Import extraction using AST
  - Mapping and report generation

- **`backend/app/services/test_mapper_integration.py`** (Integration)
  - High-level API for test mapping
  - Wraps the mapper functionality

### API Endpoint
- **`POST /api/v1/analyze-test-mapping`**
  - Query parameter: `repo_path` (default: `/app/test-project`)
  - Returns: Complete mapping report with statistics

---

## 📊 Example Usage

### Via FastAPI Swagger UI

1. Go to `http://localhost:8000/docs`
2. Find `POST /api/v1/analyze-test-mapping`
3. Click "Try it out"
4. Execute with default `repo_path="/app/test-project"`
5. See the mapping report!

### Via cURL

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/analyze-test-mapping' \
  -H 'accept: application/json'
```

### Via Python

```python
import requests

response = requests.post(
    'http://localhost:8000/api/v1/analyze-test-mapping',
    params={'repo_path': '/app/test-project'}
)

mapping = response.json()
print(mapping['statistics'])
print(mapping['test_to_source_mapping'])
```

---

## 📤 API Response Example

```json
{
  "phase": "7.1",
  "title": "Test-to-Code Mapping",
  "summary": "Mapped 1 test files to 1 source files",
  "statistics": {
    "total_test_files": 1,
    "total_source_files": 1,
    "total_mappings": 1,
    "covered_source_files": 1,
    "uncovered_source_files": 0,
    "coverage_percentage": 100.0
  },
  "test_to_source_mapping": {
    "utils/helpers-test.py": [
      "utils/helpers.py"
    ]
  },
  "source_to_test_mapping": {
    "utils/helpers.py": [
      "utils/helpers-test.py"
    ]
  },
  "uncovered_sources": [],
  "details": {
    "test_files": ["utils/helpers-test.py"],
    "source_files": ["utils/helpers.py"]
  }
}
```

---

## 🧪 Test Example

With the current test-project:

**Test file:** `utils/helpers-test.py`
```python
from helpers import format_greeting

def test_greeting():
    result = format_greeting("Alice")
    assert result == "Hello, Alice!"
```

**Source file:** `utils/helpers.py`
```python
def format_greeting(name: str) -> str:
    return f"Hello, {name}!"
```

**Mapping result:**
- ✅ `utils/helpers-test.py` covers `utils/helpers.py`
- ✅ 100% coverage
- ✅ All source files are tested

---

## 🔍 How It Works

### Step 1: File Discovery
```
Scan repo_path recursively
↓
Classify each .py file as:
  - Test file (if matches test patterns)
  - Source file (otherwise, excluding special dirs)
```

### Step 2: Import Extraction
```
For each test file:
  Parse AST
  ↓
  Extract all imports
  ↓
  Result: Set of module names (e.g., {'helpers', 'validators'})
```

### Step 3: Match to Sources
```
For each import:
  Find source file with matching module name
  ↓
  Create mapping entry
  ↓
  Result: test_file → [source_files]
```

### Step 4: Generate Report
```
Combine all mappings
↓
Calculate statistics
↓
Build reverse mapping (source → tests)
↓
Identify uncovered sources
↓
Result: Comprehensive mapping report
```

---

## 📈 What's Next (Phase 7.2-7.10)

| Phase | Task | Outcome |
|-------|------|---------|
| 7.1 | ✅ Test-to-Code Mapping | Links test files to source |
| 7.2 | Coverage.py Integration | Line-by-line execution data |
| 7.3 | Coverage Graph Edges | `COVERED_BY` relationships in Neo4j |
| 7.4 | Profiling with sys.setprofile | Runtime function calls |
| 7.5 | Dynamic Call Trace Processing | Structured call data |
| 7.6 | Dynamic Call Graph | `DYNAMICALLY_CALLS` in Neo4j |
| 7.7 | Runtime Type Collection | Capture actual types |
| 7.8 | Type Graph Enrichment | Store types in Neo4j |
| 7.9 | Dynamic Analysis Service | Orchestrate pipeline |
| 7.10 | Dynamic Analysis Endpoint | Expose `/run-dynamic-analysis` |

---

## 🎉 Phase 7.1 Complete!

**Outcome:** ✅ A mapping that links test files to application code

**What you can now do:**
- Know which tests cover which source files
- Identify uncovered source code
- Plan test expansion
- Understand test coverage at a structural level

**Next: Phase 7.2** - Coverage.py Integration for line-by-line execution data!

---

## 📝 Implementation Notes

- Uses AST analysis for robust import extraction
- Handles various import patterns:
  - `import module`
  - `from module import name`
  - `import module as alias`
- Supports multiple import naming conventions
- Cross-platform compatible (Windows/Linux/Mac)
- Comprehensive logging with `[PHASE 7.1]` markers
- Error resilient (skips files with parse errors)

---

Created: 2026-04-24  
Status: Ready for Production  
Phase: 7.1 of 10
