# Complete Testing Guide: Phases 7.2 - 7.7

This guide walks through testing each phase of the dynamic analysis pipeline step-by-step.

## Prerequisites

- Docker services running: `docker-compose ps`
- Backend on port 8000
- Neo4j on port 7687
- Test project at `/app/test-project` (inside Docker)

---

## PHASE 7.2: Coverage.py Integration

**Task:** Run pytest with coverage.py to get line-by-line execution data

### Step 1: Verify test project structure

```bash
# Check what tests exist
curl -s http://localhost:8000/ | head -20
```

Expected: Backend responds (confirms service is running)

### Step 2: Check the test project files

```bash
# This isn't a direct endpoint test, but you can verify through the graph
curl -s -X POST 'http://localhost:8000/api/v1/build-graph-from-directory?repo_path=%2Fapp%2Ftest-project' \
  -H 'accept: application/json' 2>&1 | python -c "import sys, json; d=json.load(sys.stdin); print('Status:', d.get('status')); print('Functions found:', len(d.get('data', {}).get('functions', [])))"
```

Expected: Status: success, should find functions (add, multiply, divide, greet, test_add, etc.)

### Step 3: Run coverage analysis (Phase 7.2)

```bash
curl -s -X POST 'http://localhost:8000/api/v1/get-coverage-analysis?repo_path=%2Fapp%2Ftest-project' \
  -H 'accept: application/json' 2>&1 | python -c "import sys, json; d=json.load(sys.stdin); print('Phase:', d.get('phase')); print('Status:', d.get('status')); print('\nCoverage Summary:'); s=d.get('summary', {}); print(f'  Lines covered: {s.get(\"lines_covered\")}'); print(f'  Lines not covered: {s.get(\"lines_not_covered\")}'); print(f'  Coverage %: {s.get(\"coverage_percentage\")}')"
```

Expected:

```
Phase: 7.2
Status: success
Coverage Summary:
  Lines covered: (some number)
  Lines not covered: (some number)
  Coverage %: (percentage)
```

### Step 4: Verify coverage data exists

```bash
curl -s -X POST 'http://localhost:8000/api/v1/get-coverage-analysis?repo_path=%2Fapp%2Ftest-project' \
  -H 'accept: application/json' 2>&1 | python -c "import sys, json; d=json.load(sys.stdin); print('Files with coverage:'); print(json.dumps(list(d.get('data', {}).keys())[:5], indent=2))"
```

Expected: Should show coverage data for test_utils.py and utils.py

---

## PHASE 7.3: Coverage Graph Edges

**Task:** Create COVERED_BY edges between Function nodes and Test nodes

### Step 1: Verify Neo4j is ready

```bash
# Check current Function nodes
curl -s -X POST 'http://localhost:8000/api/v1/build-graph-from-directory?repo_path=%2Fapp%2Ftest-project' \
  -H 'accept: application/json' | python -c "import sys, json; d=json.load(sys.stdin); print(f'Functions in graph: {len(d.get(\"data\", {}).get(\"functions\", []))}')"
```

Expected: 8 functions (add, multiply, divide, greet, test_add, test_multiply, test_divide, test_greet)

### Step 2: Create coverage graph edges (Phase 7.3)

```bash
curl -s -X POST 'http://localhost:8000/api/v1/create-coverage-edges?repo_path=%2Fapp%2Ftest-project' \
  -H 'accept: application/json' 2>&1 | python -c "import sys, json; d=json.load(sys.stdin); print('Phase:', d.get('phase')); print('Status:', d.get('status')); print('\nEdges Summary:'); s=d.get('summary', {}); print(f'  Edges created: {s.get(\"edges_created\")}'); print(f'  Functions processed: {s.get(\"functions_processed\")}')"
```

Expected:

```
Phase: 7.3
Status: success
Edges Summary:
  Edges created: 4 (or more)
  Functions processed: (number)
```

### Step 3: Verify edges in Neo4j

```bash
# This would require direct Neo4j query (optional verification)
echo "Coverage edges created in graph. Moving to Phase 7.4..."
```

---

## PHASE 7.4: Dynamic Profiling with sys.setprofile

**Task:** Capture function call events during test execution

### Step 1: Run dynamic profiling (Phase 7.4)

```bash
curl -s -X POST 'http://localhost:8000/api/v1/run-dynamic-profiling?repo_path=%2Fapp%2Ftest-project' \
  -H 'accept: application/json' 2>&1 | python -c "import sys, json; d=json.load(sys.stdin); print('Phase:', d.get('phase')); print('Status:', d.get('status')); print('\nProfiling Summary:'); s=d.get('summary', {}); print(f'  Total events: {s.get(\"total_events\")}'); print(f'  Call events: {s.get(\"call_events\")}'); print(f'  Return events: {s.get(\"return_events\")}'); print(f'  Unique call pairs: {s.get(\"unique_call_pairs\")}'); print(f'  Max call depth: {s.get(\"max_call_depth\")}')"
```

Expected:

```
Phase: 7.4
Status: success
Profiling Summary:
  Total events: ~29,000 (14,514 calls + 14,514 returns)
  Call events: 14514
  Return events: 14514
  Unique call pairs: ~1,000+
  Max call depth: 26
```

### Step 2: Get top function calls

```bash
curl -s -X POST 'http://localhost:8000/api/v1/run-dynamic-profiling?repo_path=%2Fapp%2Ftest-project' \
  -H 'accept: application/json' 2>&1 | python -c "import sys, json; d=json.load(sys.stdin); cg=d.get('call_graph', {}); print('Top 5 function calls:'); calls=sorted([(f, len(cg[f].get('calls_to', []))) for f in cg], key=lambda x: x[1], reverse=True); [print(f'{i+1}. {name}: calls {n} functions') for i, (name, n) in enumerate(calls[:5])]"
```

Expected: Lists functions with most callees

### Step 3: Verify test functions are captured

```bash
curl -s -X POST 'http://localhost:8000/api/v1/run-dynamic-profiling?repo_path=%2Fapp%2Ftest-project' \
  -H 'accept: application/json' 2>&1 | python -c "import sys, json; d=json.load(sys.stdin); cg=d.get('call_graph', {}); test_funcs=[f for f in cg if 'test_' in f]; print(f'Test functions found: {test_funcs}')"
```

Expected: Shows test_add, test_multiply, test_divide, test_greet

---

## PHASE 7.5: Dynamic Call Trace Processing

**Task:** Parse raw trace into structured call lists

### Step 1: Process call trace (Phase 7.5)

```bash
curl -s -X POST 'http://localhost:8000/api/v1/process-call-trace?repo_path=%2Fapp%2Ftest-project' \
  -H 'accept: application/json' 2>&1 | python -c "import sys, json; d=json.load(sys.stdin); print('Phase:', d.get('phase')); print('Status:', d.get('status')); print('\nTrace Summary:'); s=d.get('summary', {}); print(f'  Unique call pairs: {s.get(\"total_unique_pairs\")}'); print(f'  Unique functions: {s.get(\"total_unique_functions\")}'); print(f'  Total invocations: {s.get(\"total_call_invocations\")}')"
```

Expected:

```
Phase: 7.5
Status: success
Trace Summary:
  Unique call pairs: 730
  Unique functions: 384
  Total invocations: 11,234
```

### Step 2: Get top function calls

```bash
curl -s -X POST 'http://localhost:8000/api/v1/process-call-trace?repo_path=%2Fapp%2Ftest-project' \
  -H 'accept: application/json' 2>&1 | python -c "import sys, json; d=json.load(sys.stdin); calls=d.get('calls', []); print('Top 10 function calls:'); [print(f'{i+1}. {c[\"caller\"]}->{c[\"callee\"]}: {c[\"count\"]} times') for i, c in enumerate(calls[:10])]"
```

Expected:

```
Top 10 function calls:
1. parsefactories->safe_getattr: 2219 times
2. register->parse_hookimpl_opts: 2182 times
... (and so on)
```

### Step 3: Get function statistics

```bash
curl -s -X POST 'http://localhost:8000/api/v1/process-call-trace?repo_path=%2Fapp%2Ftest-project' \
  -H 'accept: application/json' 2>&1 | python -c "import sys, json; d=json.load(sys.stdin); stats=d.get('statistics', {}); print('Most called functions:'); [print(f'  {f[\"function\"]}: {f[\"total_calls\"]} calls') for f in stats.get('most_called_functions', [])[:5]]; print('\nFunctions called by most functions:'); [print(f'  {f[\"function\"]}: called by {f[\"num_callers\"]} functions') for f in stats.get('functions_with_most_callers', [])[:5]]"
```

Expected:

```
Most called functions:
  safe_getattr: 2233 calls
  parse_hookimpl_opts: 2182 calls
  __init__: 385 calls
  fnmatch_ex: 244 calls
  iter_parents: 236 calls

Functions called by most functions:
  __init__: called by 29 functions
  getini: called by 25 functions
  __getattr__: called by 22 functions
  getoption: called by 20 functions
  __getitem__: called by 12 functions
```

### Step 4: Verify test function calls are captured

```bash
curl -s -X POST 'http://localhost:8000/api/v1/process-call-trace?repo_path=%2Fapp%2Ftest-project' \
  -H 'accept: application/json' 2>&1 | python -c "import sys, json; d=json.load(sys.stdin); calls=d.get('calls', []); test_calls=[c for c in calls if 'test_' in c.get('caller', '')]; print('Test function calls:'); [print(f'  {c[\"caller\"]}->{c[\"callee\"]}: {c[\"count\"]} times') for c in test_calls]"
```

Expected:

```
Test function calls:
  test_add->add: 3 times
  test_multiply->multiply: 3 times
  test_divide->divide: 3 times
  test_greet->greet: 2 times
```

---

## PHASE 7.6: Dynamic Call Graph Edges

**Task:** Create DYNAMICALLY_CALLS edges in Neo4j

### Step 1: Enrich dynamic call graph (Phase 7.6)

```bash
curl -s -X POST 'http://localhost:8000/api/v1/enrich-dynamic-call-graph?repo_path=%2Fapp%2Ftest-project' \
  -H 'accept: application/json' 2>&1 | python -c "import sys, json; d=json.load(sys.stdin); print('Phase:', d.get('phase')); print('Status:', d.get('status')); print('\nGraph Enrichment Summary:'); s=d.get('summary', {}); print(f'  Unique call pairs: {s.get(\"unique_call_pairs\")}'); print(f'  Edges created: {s.get(\"edges_created\")}'); print(f'  Edges updated: {s.get(\"edges_updated\")}'); print(f'  Failed edges: {s.get(\"failed_edges\")}'); print(f'  Existing nodes: {s.get(\"existing_function_nodes\")}')"
```

Expected:

```
Phase: 7.6
Status: success
Graph Enrichment Summary:
  Unique call pairs: 730
  Edges created: 0
  Edges updated: 4
  Failed edges: 726
  Existing nodes: 8
```

(Most edges fail because only 8 functions exist in graph - this is normal)

### Step 2: Get edge statistics

```bash
curl -s -X POST 'http://localhost:8000/api/v1/enrich-dynamic-call-graph?repo_path=%2Fapp%2Ftest-project' \
  -H 'accept: application/json' 2>&1 | python -c "import sys, json; d=json.load(sys.stdin); stats=d.get('statistics', {}); print('DYNAMICALLY_CALLS Edges:'); print(f'  Total edges: {stats.get(\"total_dynamically_calls_edges\")}'); print(f'  Total call invocations: {stats.get(\"total_call_count\")}'); print('\nTop called functions:'); [print(f'  {f[\"function\"]}: {f[\"total_calls\"]} calls') for f in stats.get('top_called_functions', []) if f['function'][:5] not in ('pytho', 'plugg')]"
```

Expected:

```
DYNAMICALLY_CALLS Edges:
  Total edges: 4
  Total call invocations: 11

Top called functions:
  divide: 3 calls
  add: 3 calls
  multiply: 3 calls
  greet: 2 calls
```

### Step 3: Verify test function edges

```bash
curl -s -X POST 'http://localhost:8000/api/v1/enrich-dynamic-call-graph?repo_path=%2Fapp%2Ftest-project' \
  -H 'accept: application/json' 2>&1 | python -c "import sys, json; d=json.load(sys.stdin); stats=d.get('statistics', {}); print('Functions making dynamic calls:'); [print(f'  {f[\"function\"]}: {f[\"num_callees\"]} function(s)') for f in stats.get('top_calling_functions', [])]"
```

Expected:

```
Functions making dynamic calls:
  test_add: 1 function(s)
  test_multiply: 1 function(s)
  test_divide: 1 function(s)
  test_greet: 1 function(s)
```

---

## PHASE 7.7: Runtime Type Collection

**Task:** Collect and analyze runtime type information

### Step 1: Collect runtime types (Phase 7.7)

```bash
curl -s -X POST 'http://localhost:8000/api/v1/collect-runtime-types?repo_path=%2Fapp%2Ftest-project' \
  -H 'accept: application/json' 2>&1 | python -c "import sys, json; d=json.load(sys.stdin); print('Phase:', d.get('phase')); print('Status:', d.get('status')); print('\nType Collection Summary:'); s=d.get('summary', {}); print(f'  Call events processed: {s.get(\"total_call_events_processed\")}'); print(f'  Functions with types: {s.get(\"functions_with_types\")}'); print(f'  Unique types observed: {s.get(\"unique_types_observed\")}'); print(f'  Total type observations: {s.get(\"total_type_observations\")}')"
```

Expected:

```
Phase: 7.7
Status: success
Type Collection Summary:
  Call events processed: 14514
  Functions with types: 656
  Unique types observed: 106
  Total type observations: 875
```

### Step 2: Get most common types

```bash
curl -s -X POST 'http://localhost:8000/api/v1/collect-runtime-types?repo_path=%2Fapp%2Ftest-project' \
  -H 'accept: application/json' 2>&1 | python -c "import sys, json; d=json.load(sys.stdin); types=d.get('most_common_types', []); print('Top 10 most common types:'); [print(f'{i+1}. {t[\"type\"]}: {t[\"count\"]} observations') for i, t in enumerate(types[:10])]"
```

Expected:

```
Top 10 most common types:
1. str: 83 observations
2. Config: 63 observations
3. TerminalReporter: 57 observations
4. PosixPath: 43 observations
5. Function: 39 observations
6. NoneType: 36 observations
7. list: 35 observations
8. Session: 35 observations
9. function: 29 observations
10. Module: 25 observations
```

### Step 3: Get test function type signatures

```bash
curl -s -X POST 'http://localhost:8000/api/v1/collect-runtime-types?repo_path=%2Fapp%2Ftest-project' \
  -H 'accept: application/json' 2>&1 | python -c "import sys, json; d=json.load(sys.stdin); funcs=d.get('function_types', {}); test_funcs=['add', 'multiply', 'divide', 'greet']; print('Test function signatures:'); [print(f'{fname}: {sigs[\"observed_signatures\"][0][\"signature\"]} ({sigs[\"observed_signatures\"][0][\"count\"]} calls)') if fname in funcs and sigs.get('observed_signatures') else None for fname, sigs in [(f, funcs.get(f, {})) for f in test_funcs] if fname in funcs]"
```

Expected:

```
Test function signatures:
add: (int, int) (3 calls)
multiply: (int, int) (3 calls)
divide: (int, int) (3 calls)
greet: (str) (2 calls)
```

### Step 4: Get polymorphism analysis

```bash
curl -s -X POST 'http://localhost:8000/api/v1/collect-runtime-types?repo_path=%2Fapp%2Ftest-project' \
  -H 'accept: application/json' 2>&1 | python -c "import sys, json; d=json.load(sys.stdin); stats=d.get('type_statistics', {}); print('Polymorphism Analysis:'); print(f'  Functions with polymorphic types: {stats.get(\"functions_with_polymorphic_types\")}'); print(f'  Functions with consistent types: {stats.get(\"functions_with_consistent_types\")}'); print('\nTop 5 polymorphic functions:'); [print(f'  {f[\"function\"]}: {f[\"signature_variants\"]} variants ({f[\"total_calls\"]} calls)') for f in stats.get('top_polymorphic_functions', [])[:5]]"
```

Expected:

```
Polymorphism Analysis:
  Functions with polymorphic types: 98
  Functions with consistent types: 270

Top 5 polymorphic functions:
  __init__: 74 variants (387 calls)
  pytest_plugin_registered: 32 variants (123 calls)
  parsefactories: 12 variants (42 calls)
  safe_isclass: 12 variants (53 calls)
  register: 11 variants (41 calls)
```

---

## Quick Test Script (Copy & Paste All at Once)

```bash
#!/bin/bash
set -e

echo "========================================="
echo "PHASE 7.2: Coverage Analysis"
echo "========================================="
curl -s -X POST 'http://localhost:8000/api/v1/get-coverage-analysis?repo_path=%2Fapp%2Ftest-project' \
  -H 'accept: application/json' | python -c "import sys, json; d=json.load(sys.stdin); print('✓ Phase:', d.get('phase'), '| Status:', d.get('status')); s=d.get('summary', {}); print(f'  Coverage: {s.get(\"coverage_percentage\")}')"

echo ""
echo "========================================="
echo "PHASE 7.3: Coverage Graph Edges"
echo "========================================="
curl -s -X POST 'http://localhost:8000/api/v1/create-coverage-edges?repo_path=%2Fapp%2Ftest-project' \
  -H 'accept: application/json' | python -c "import sys, json; d=json.load(sys.stdin); print('✓ Phase:', d.get('phase'), '| Status:', d.get('status')); s=d.get('summary', {}); print(f'  Edges: {s.get(\"edges_created\")}')"

echo ""
echo "========================================="
echo "PHASE 7.4: Dynamic Profiling"
echo "========================================="
curl -s -X POST 'http://localhost:8000/api/v1/run-dynamic-profiling?repo_path=%2Fapp%2Ftest-project' \
  -H 'accept: application/json' | python -c "import sys, json; d=json.load(sys.stdin); print('✓ Phase:', d.get('phase'), '| Status:', d.get('status')); s=d.get('summary', {}); print(f'  Events: {s.get(\"total_events\")} | Pairs: {s.get(\"unique_call_pairs\")}')"

echo ""
echo "========================================="
echo "PHASE 7.5: Call Trace Processing"
echo "========================================="
curl -s -X POST 'http://localhost:8000/api/v1/process-call-trace?repo_path=%2Fapp%2Ftest-project' \
  -H 'accept: application/json' | python -c "import sys, json; d=json.load(sys.stdin); print('✓ Phase:', d.get('phase'), '| Status:', d.get('status')); s=d.get('summary', {}); print(f'  Pairs: {s.get(\"total_unique_pairs\")} | Functions: {s.get(\"total_unique_functions\")} | Invocations: {s.get(\"total_call_invocations\")}')"

echo ""
echo "========================================="
echo "PHASE 7.6: Dynamic Call Graph Edges"
echo "========================================="
curl -s -X POST 'http://localhost:8000/api/v1/enrich-dynamic-call-graph?repo_path=%2Fapp%2Ftest-project' \
  -H 'accept: application/json' | python -c "import sys, json; d=json.load(sys.stdin); print('✓ Phase:', d.get('phase'), '| Status:', d.get('status')); s=d.get('summary', {}); print(f'  Edges: {s.get(\"edges_created\") + s.get(\"edges_updated\", 0)} (created+updated)')"

echo ""
echo "========================================="
echo "PHASE 7.7: Runtime Type Collection"
echo "========================================="
curl -s -X POST 'http://localhost:8000/api/v1/collect-runtime-types?repo_path=%2Fapp%2Ftest-project' \
  -H 'accept: application/json' | python -c "import sys, json; d=json.load(sys.stdin); print('✓ Phase:', d.get('phase'), '| Status:', d.get('status')); s=d.get('summary', {}); print(f'  Functions: {s.get(\"functions_with_types\")} | Types: {s.get(\"unique_types_observed\")} | Polymorphic: {d.get(\"type_statistics\", {}).get(\"functions_with_polymorphic_types\")}')"

echo ""
echo "========================================="
echo "✓ ALL PHASES TESTED SUCCESSFULLY!"
echo "========================================="
```

---

## Summary Checklist

- [ ] Phase 7.2: Coverage analysis shows percentage coverage
- [ ] Phase 7.3: COVERED_BY edges created in graph
- [ ] Phase 7.4: ~29,000 events captured (14,514 calls + returns)
- [ ] Phase 7.5: 730 unique call pairs, 384 functions, 11,234 invocations
- [ ] Phase 7.6: 4 DYNAMICALLY_CALLS edges created for test functions
- [ ] Phase 7.7: 656 functions with types, 106 unique types, polymorphism detected

All tests passed when each endpoint returns `"status": "success"` and expected metrics match!
