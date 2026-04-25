# Phase 7.2: Coverage.py Integration Implementation

## ✅ Status: COMPLETE

Phase 7.2 has been fully implemented. This phase runs pytest with coverage.py to generate line-by-line execution data for all tested files.

---

## 🎯 What Phase 7.2 Does

Provides **line-by-line execution data** showing which parts of the codebase are tested:

```
File: utils/helpers.py
Line 1:  import sys           [EXECUTED]
Line 2:  import os            [EXECUTED]
Line 3:                        [EXCLUDED]
Line 4:  def format_greeting  [EXECUTED]
Line 5:      return f"..."    [EXECUTED]
Line 6:                        [NOT EXECUTED]
Line 7:  def unused_function  [NOT EXECUTED]
```

---

## 📋 Implementation Details

### 1. **Pytest Execution with Coverage**
- Runs pytest as subprocess with coverage.py instrumentation
- Collects which lines are executed during test run
- Captures test results (passed, failed, errors)

### 2. **Coverage Data Export**
- Exports coverage data to JSON format
- Parses JSON to extract per-file coverage information
- Identifies executed, missing, and excluded lines

### 3. **Coverage Report Generation**
- Calculates per-file coverage percentages
- Aggregates overall coverage statistics
- Links line numbers to execution status

### 4. **Data Structure**
```json
{
  "phase": "7.2",
  "test_summary": {
    "total": 1,
    "passed": 1,
    "failed": 0,
    "errors": 0
  },
  "statistics": {
    "total_files": 1,
    "total_lines": 10,
    "covered_lines": 8,
    "missing_lines": 2,
    "overall_coverage": 80.0
  },
  "coverage_by_file": {
    "utils/helpers.py": {
      "total_lines": 10,
      "covered_lines": 8,
      "missing_lines": 2,
      "coverage_percent": 80.0,
      "executed_lines": [1, 2, 4, 5, 8, 9, 10, 11],
      "missing_lines": [6, 7]
    }
  }
}
```

---

## 🔧 Files Created

### Backend Services
- **`backend/app/services/coverage_analyzer.py`** (Main module)
  - `CoverageAnalyzer` class
  - Subprocess management for pytest + coverage.py
  - JSON parsing and report generation
  - ~400 lines of production code

- **`backend/app/services/coverage_analyzer_integration.py`** (Integration)
  - High-level API: `get_coverage_analysis(repo_path)`
  - Wraps CoverageAnalyzer functionality

### Dependencies Updated
- **`backend/requirements.txt`**
  - Added: `coverage` (for coverage.py)
  - Added: `pytest` (for test execution)

### API Endpoint
- **`POST /api/v1/analyze-coverage`**
  - Query parameter: `repo_path` (default: `/app/test-project`)
  - Returns: Complete coverage report with line-by-line data

---

## 📊 How It Works

### Step 1: Run Pytest with Coverage
```bash
coverage run --data-file=/tmp/.coverage -m pytest /repo -v
```
- Runs test suite with coverage instrumentation
- Stores coverage database at temporary location

### Step 2: Export to JSON
```bash
coverage json --data-file=/tmp/.coverage -o=/tmp/coverage.json
```
- Converts coverage database to machine-readable JSON
- Includes line execution data for all files

### Step 3: Parse Coverage Data
```python
{
  "files": {
    "/repo/utils/helpers.py": {
      "executed_lines": [1, 2, 4, 5],
      "missing_lines": [6, 7],
      "excluded_lines": []
    }
  }
}
```
- Extracts per-file coverage information
- Identifies executed vs missing lines

### Step 4: Generate Report
- Calculate coverage percentages
- Aggregate statistics
- Format for API consumption

---

## 🧪 Example Usage

### Via FastAPI Swagger UI

1. Go to `http://localhost:8000/docs`
2. Find `POST /api/v1/analyze-coverage`
3. Click "Try it out"
4. Execute with default `repo_path="/app/test-project"`
5. See the coverage report!

### Via cURL

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/analyze-coverage' \
  -H 'accept: application/json'
```

### Via Python

```python
import requests

response = requests.post(
    'http://localhost:8000/api/v1/analyze-coverage',
    params={'repo_path': '/app/test-project'}
)

coverage = response.json()
print(f"Overall coverage: {coverage['statistics']['overall_coverage']}%")
print(f"Covered lines: {coverage['statistics']['covered_lines']}")
```

---

## 📤 API Response Example

```json
{
  "phase": "7.2",
  "title": "Coverage Analysis Report",
  "test_summary": {
    "total": 1,
    "passed": 1,
    "failed": 0,
    "errors": 0
  },
  "statistics": {
    "total_files": 1,
    "total_lines": 10,
    "covered_lines": 8,
    "missing_lines": 2,
    "overall_coverage": 80.0
  },
  "coverage_by_file": {
    "utils/helpers.py": {
      "total_lines": 10,
      "covered_lines": 8,
      "missing_lines": 2,
      "excluded_lines": 0,
      "coverage_percent": 80.0,
      "executed_lines": [1, 2, 4, 5, 8, 9, 10, 11],
      "missing_lines": [6, 7]
    }
  }
}
```

---

## 🎯 Key Features

✅ **Full Coverage Collection**: Line-by-line execution tracking for all test files
✅ **Test Result Integration**: Captures passed/failed/error counts with coverage
✅ **JSON Export**: Uses coverage.py's JSON format for structured data
✅ **Per-File Analysis**: Detailed coverage metrics for each source file
✅ **Statistics Aggregation**: Overall coverage percentage and line counts
✅ **Error Handling**: Graceful handling of subprocess timeouts and failures
✅ **Temporary Cleanup**: Removes temporary coverage databases after analysis
✅ **Logging**: Full [PHASE 7.2] logging throughout execution
✅ **Production Ready**: Cross-platform compatible (Windows/Linux/Mac)

---

## 🔧 Advanced Features

### Accessing Coverage Data

```python
# Get overall statistics
stats = coverage_report['statistics']
coverage_pct = stats['overall_coverage']
covered_lines = stats['covered_lines']
total_lines = stats['total_lines']

# Get per-file coverage
file_coverage = coverage_report['coverage_by_file']['utils/helpers.py']
executed = file_coverage['executed_lines']
missing = file_coverage['missing_lines']
```

### Identifying Untested Code

```python
# Find all untested lines in all files
for file_path, coverage in coverage_report['coverage_by_file'].items():
    untested = coverage['missing_lines']
    if untested:
        print(f"{file_path}: Lines {untested} are not covered")
```

### Coverage Threshold Checking

```python
stats = coverage_report['statistics']
if stats['overall_coverage'] < 80:
    print("WARNING: Coverage is below 80% threshold!")
```

---

## 📈 What's Next (Phase 7.3-7.10)

| Phase | Task | Outcome |
|-------|------|---------|
| 7.1 | ✅ Test-to-Code Mapping | Links test files to source |
| 7.2 | ✅ Coverage.py Integration | Line-by-line execution data |
| 7.3 | Coverage Graph Edges | `COVERED_BY` relationships in Neo4j |
| 7.4 | Profiling with sys.setprofile | Runtime function calls |
| 7.5 | Dynamic Call Trace Processing | Structured call data |
| 7.6 | Dynamic Call Graph | `DYNAMICALLY_CALLS` in Neo4j |
| 7.7 | Runtime Type Collection | Capture actual types |
| 7.8 | Type Graph Enrichment | Store types in Neo4j |
| 7.9 | Dynamic Analysis Service | Orchestrate pipeline |
| 7.10 | Dynamic Analysis Endpoint | Expose `/run-dynamic-analysis` |

---

## ⚙️ Technical Details

### Coverage.py Integration

The implementation uses three coverage.py commands:

1. **Coverage Run**
   ```
   coverage run --data-file=<path> -m pytest <repo> -v
   ```
   - Runs pytest with coverage instrumentation
   - Stores results in a binary database

2. **Coverage JSON Export**
   ```
   coverage json --data-file=<path> -o=<output>
   ```
   - Exports database to JSON format
   - Makes data accessible to our Python code

3. **JSON Parsing**
   - Parses coverage.json structure
   - Extracts executed/missing/excluded lines per file

### Subprocess Management

- Proper timeout (300 seconds / 5 minutes)
- Error capture with stderr logging
- Output parsing for test count extraction
- Temporary directory cleanup

### Data Processing Pipeline

```
pytest execution
    ↓
coverage.py collects data
    ↓
Export to JSON
    ↓
Parse JSON file
    ↓
Generate structured report
    ↓
Return to API
```

---

## 🐛 Troubleshooting

### Error: "coverage command not found"
**Solution:** Install coverage.py in the container
```bash
pip install coverage
```

### Error: "pytest: command not found"
**Solution:** pytest should be installed with coverage
```bash
pip install pytest coverage
```

### Coverage shows 0% or empty
**Possible causes:**
- No test files found in repository
- Test files are not matching patterns
- Coverage database not exported properly

**Solutions:**
- Verify test files exist: `find /app/test-project -name "*test*.py"`
- Check logs for [PHASE 7.2] messages
- Ensure repository structure matches expectations

### Timeout after 300 seconds
**Cause:** Test suite takes too long to run
**Solution:** Increase timeout in `CoverageAnalyzer._run_pytest_with_coverage()` or optimize tests

---

## 🎉 Phase 7.2 Complete!

**Outcome:** ✅ Line-by-line execution data for all tested code

**What you can now do:**
- See exactly which lines are covered by tests
- Identify untested code paths
- Calculate coverage percentages per file
- Track coverage metrics over time
- Plan test expansion based on missing coverage

**Next: Phase 7.3** - Coverage Graph Edges to enrich Neo4j!

---

## 📝 Implementation Notes

- Uses subprocess for pytest/coverage.py isolation
- Proper cleanup of temporary directories even on errors
- Comprehensive logging with [PHASE 7.2] markers
- Error-resilient (returns partial data if possible)
- Cross-platform compatible (tested on Windows/Linux/Mac paths)

---

## 💡 Integration with Phase 7.1

| Phase | Purpose | Output |
|-------|---------|--------|
| 7.1 | Test-to-Code Mapping | Which tests cover which files |
| 7.2 | Coverage Analysis | **Which lines in those files are covered** |

Phase 7.2 complements Phase 7.1 by providing line-level granularity!

---

Created: 2026-04-24  
Status: Ready for Production  
Phase: 7.2 of 10
