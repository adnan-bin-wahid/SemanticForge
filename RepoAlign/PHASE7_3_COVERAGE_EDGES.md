# Phase 7.3: Coverage Graph Edges - Implementation Guide

**Status:** ✅ **IMPLEMENTED**  
**Date:** April 25, 2026

## Overview

Phase 7.3 enriches the Neo4j knowledge graph by processing coverage data from Phase 7.2 and creating `COVERED_BY` edges between `Function` nodes and `Test` nodes. This establishes explicit links between functions and the tests that execute them.

## Architecture

### Core Components

#### 1. **CoverageGraphEnricher** (`coverage_graph_enricher.py`)

Main service class that orchestrates the entire enrichment process.

**Key Methods:**

- `enrich_coverage_graph()`: Main orchestration method
- `_fetch_functions_from_graph()`: Retrieves all Function nodes from Neo4j with line ranges
- `_run_coverage_analysis()`: Executes pytest with coverage.py
- `_identify_test_files()`: Discovers test files using pytest conventions
- `_map_coverage_to_functions()`: Maps coverage data to Function nodes
- `_create_coverage_edges()`: Creates COVERED_BY edges in Neo4j

**Coverage Mapping Logic:**

```
1. For each file in coverage data:
   - Extract executed_lines
   - Match to Function nodes by line range
   - If any line of function was executed → function is covered
   - Create COVERED_BY edge to test file
```

#### 2. **Test Node Creator** (`test_node_creator.py`)

Utility to ensure Test nodes exist in the graph before creating edges.

**Key Functions:**

- `create_test_nodes()`: Creates Test nodes from discovered test files
- `_discover_test_files()`: Finds all test files matching pytest patterns (test\__.py, _\_test.py)

#### 3. **Integration Wrapper** (`coverage_graph_enricher_integration.py`)

High-level API wrapper providing clean interface for endpoint use.

### Graph Schema

#### Test Node

```cypher
(t:Test {
  name: "test_utils",           // Test file name without .py
  path: "test/test_utils.py",   // File path
  file_name: "test_utils.py"    // Full file name
})
```

#### COVERED_BY Edge

```cypher
(f:Function)-[:COVERED_BY]->(t:Test)

// Represents: "This function is covered by this test"
// Created when function's lines appear in coverage data
```

## API Endpoints

### 1. Create Test Nodes

**Endpoint:** `POST /api/v1/create-test-nodes`

**Purpose:** Create Test nodes in Neo4j from discovered test files

**Parameters:**

- `repo_path` (query string): Path to repository (default: `/app/test-project`)

**Response:**

```json
{
  "phase": "7.3",
  "title": "Test Node Creation",
  "status": "success",
  "nodes_created": 4
}
```

**Example:**

```bash
curl -X POST 'http://localhost:8000/api/v1/create-test-nodes?repo_path=%2Fapp%2Ftest-project' \
  -H 'accept: application/json'
```

### 2. Enrich Coverage Graph

**Endpoint:** `POST /api/v1/enrich-coverage-graph`

**Purpose:** Process coverage data and create COVERED_BY edges

**Parameters:**

- `repo_path` (query string): Path to repository (default: `/app/test-project`)

**Response:**

```json
{
  "phase": "7.3",
  "title": "Coverage Graph Enrichment",
  "status": "success",
  "functions_processed": 4,
  "edges_created": 8,
  "coverage_data": {
    "test_utils.py": {
      "executed_lines": [3, 4, 7, 9, ...],
      "summary": {...}
    },
    "utils.py": {
      "executed_lines": [4, 6, 9, 11, ...],
      "summary": {...}
    }
  }
}
```

**Example:**

```bash
curl -X POST 'http://localhost:8000/api/v1/enrich-coverage-graph?repo_path=%2Fapp%2Ftest-project' \
  -H 'accept: application/json'
```

## Workflow

### Step-by-Step Process

1. **Test Node Creation** (Prerequisites)

   ```
   POST /api/v1/create-test-nodes
   ↓
   Discover test files (test_*.py, *_test.py)
   ↓
   Create Test nodes in Neo4j
   ```

2. **Coverage Analysis**

   ```
   POST /api/v1/analyze-coverage (from Phase 7.2)
   ↓
   Runs pytest with coverage.py
   ↓
   Generates coverage.json with executed lines per file
   ```

3. **Coverage to Function Mapping**

   ```
   Fetch Function nodes with line ranges
   ↓
   For each file in coverage data:
     - Extract executed_lines
     - Find Functions that contain executed lines
     - Mark those Functions as "covered"
   ```

4. **Graph Enrichment**
   ```
   For each covered Function:
     - Create COVERED_BY edge to Test node
     - Query creates merged edge (idempotent)
   ```

### Complete Example

```python
# Step 1: Create Test nodes
response = requests.post(
    'http://localhost:8000/api/v1/create-test-nodes',
    params={'repo_path': '/app/test-project'}
)
# Response: {"nodes_created": 4}

# Step 2: Run coverage analysis (Phase 7.2)
response = requests.post(
    'http://localhost:8000/api/v1/analyze-coverage',
    params={'repo_path': '/app/test-project'}
)
# Response: coverage report with executed_lines per file

# Step 3: Enrich coverage graph
response = requests.post(
    'http://localhost:8000/api/v1/enrich-coverage-graph',
    params={'repo_path': '/app/test-project'}
)
# Response: {"edges_created": 8}

# Now query the graph:
# MATCH (f:Function)-[:COVERED_BY]->(t:Test)
# RETURN f.name, t.name
```

## Data Flow Diagram

```
Test Files Discovery
    ↓
Create Test Nodes → Neo4j
    ↓
Run Coverage Analysis (Phase 7.2)
    ↓
Coverage JSON (executed_lines per file)
    ↓
Fetch Function Nodes (with line ranges)
    ↓
Map Coverage to Functions
    ↓
Create COVERED_BY Edges → Neo4j
    ↓
Knowledge Graph with:
  (Function)-[:COVERED_BY]->(Test)
```

## Query Examples

### Find all functions covered by a specific test

```cypher
MATCH (f:Function)-[:COVERED_BY]->(t:Test {name: "test_utils"})
RETURN f.name, f.start_line, f.end_line
```

### Find all tests covering a specific function

```cypher
MATCH (f:Function {name: "add"})-[:COVERED_BY]->(t:Test)
RETURN t.name, t.path
```

### Find uncovered functions

```cypher
MATCH (f:Function)
WHERE NOT (f)-[:COVERED_BY]->()
RETURN f.name, f.start_line
```

### Find test coverage statistics

```cypher
MATCH (f:Function)
WITH
  COUNT(f) as total_functions,
  COUNT {MATCH (f)-[:COVERED_BY]->(:Test)} as covered_functions
RETURN
  total_functions,
  covered_functions,
  round(100.0 * covered_functions / total_functions, 2) as coverage_percent
```

## Error Handling

### Common Issues

1. **No Test Nodes Found**
   - Ensure `POST /api/v1/create-test-nodes` is called first
   - Check test file patterns: test\__.py or _\_test.py

2. **No COVERED_BY Edges Created**
   - Verify test files actually test the code (coverage should show execution)
   - Check Function nodes have correct line ranges
   - Review logs for line range matching errors

3. **Neo4j Connection Failed**
   - Verify Neo4j is running: `docker-compose ps`
   - Check credentials: default is neo4j/password
   - Verify connection URI: bolt://neo4j:7687

### Debug Logging

All Phase 7.3 operations log with `[PHASE 7.3]` prefix. View logs:

```bash
docker-compose logs backend | grep "PHASE 7.3"
```

## Performance Characteristics

- **Test Discovery:** O(n) where n = files in repo
- **Coverage Analysis:** Depends on test suite size (300s timeout)
- **Graph Enrichment:** O(f × t) where f = functions, t = tests
- **Edge Creation:** O(covered_functions) separate queries

## Implementation Details

### Coverage Line Matching

```python
# For each function:
for func in functions_in_file:
    start_line = func['start_line']
    end_line = func['end_line']

    # Check if any line of function was executed
    is_covered = any(
        start_line <= line <= end_line
        for line in coverage_data['executed_lines']
    )

    # Create edge if covered
    if is_covered:
        CREATE_EDGE(Function, Test)
```

### Neo4j Integration

Uses `neo4j-driver` with connection pooling:

```python
driver = GraphDatabase.driver(
    "bolt://neo4j:7687",
    auth=("neo4j", "password")
)

with driver.session() as session:
    result = session.run(query, parameters)
```

## Dependencies

- **neo4j** (6.1.0): Graph database driver
- **coverage** (7.13.5): Coverage analysis (from Phase 7.2)
- **pytest** (9.0.3): Test framework (from Phase 7.2)

## Next Steps

### Phase 7.4: Profiling with sys.setprofile

- Capture dynamic function call traces during test execution
- Process traces into call graph data
- Create DYNAMICALLY_CALLS edges

### Integration Notes

- Phase 7.3 assumes Phase 7.2 (Coverage Analysis) is complete
- Phase 7.3 output feeds into Phase 7.4 (Dynamic Tracing)
- COVERED_BY edges are queryable immediately after creation

## Testing

To test Phase 7.3 locally:

```bash
# Terminal 1: Start services
cd RepoAlign
docker-compose up -d

# Terminal 2: Run test
curl -X POST 'http://localhost:8000/api/v1/create-test-nodes?repo_path=%2Fapp%2Ftest-project'
curl -X POST 'http://localhost:8000/api/v1/analyze-coverage?repo_path=%2Fapp%2Ftest-project'
curl -X POST 'http://localhost:8000/api/v1/enrich-coverage-graph?repo_path=%2Fapp%2Ftest-project'

# Verify in Neo4j
docker-compose exec neo4j cypher-shell -u neo4j -p password \
  "MATCH (f:Function)-[:COVERED_BY]->(t:Test) RETURN f.name, t.name LIMIT 10"
```

## Monitoring

View Phase 7.3 progress:

```bash
# Real-time logs
docker-compose logs -f backend | grep "PHASE 7.3"

# Neo4j statistics
docker-compose exec neo4j cypher-shell -u neo4j -p password \
  "MATCH ()-[r:COVERED_BY]->() RETURN COUNT(r) as edge_count"
```

---

**Phase 7.3 Completion Status:** ✅ READY FOR TESTING
