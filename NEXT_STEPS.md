# RepoAlign: Development Roadmap - Phases 8.7 to 8.10

**Status**: Phases 8.1-8.6 Complete ✅ | Phases 8.7-8.10 Pending 🔵

---

## 🎯 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    RepoAlign Full Pipeline                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Phase 8.1: File Watcher        ──┐                              │
│  Phase 8.2: Git Diff Polling    ──┼──→ Change Queue             │
│  Phase 8.3: Change Queue        ──┘                              │
│         ↓                                                         │
│  Phase 8.4: AST Diffing         ──→ Detect what changed         │
│         ↓                                                         │
│  ┌─────────────────────────────────────────┐                    │
│  │   DAILY DEMO SHOWS (Phases 8.5 & 8.6)   │                    │
│  │                                         │                    │
│  │  Phase 8.5: Invalidate Stale Data   ──→ Remove old metadata  │
│  │  Phase 8.6: Re-analyze Changes      ──→ Extract new metadata │
│  └─────────────────────────────────────────┘                    │
│         ↓                                                         │
│  Phase 8.7: Update Knowledge Graph  ──→ Write data back to DB   │
│         ↓                                                         │
│  Phase 8.8: Maintenance Worker      ──→ Orchestrate pipeline    │
│         ↓                                                         │
│  Phase 8.9: Agent Control           ──→ Start/stop endpoints    │
│         ↓                                                         │
│  Phase 8.10: Full Loop              ──→ Automatic sync          │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 Phase 8.7: Targeted Graph Update

### Purpose
Write Phase 8.6 re-analyzed data back to Neo4j, creating/updating nodes and relationships.

### Input
```python
ReAnalyzedSymbol(
    symbol_name: str,
    symbol_type: str,  # "function" | "class"
    file_path: str,
    signature: str,
    parameters: List[ParameterInfo],
    docstring: str,
    cyclomatic_complexity: int,
    lines_of_code: int,
    imports_used: List[ImportInfo],
    functions_called: List[CallInfo]
)
```

### Operations

#### Create New Symbol Nodes
```cypher
CREATE (sym:Function {
  name: "add",
  signature: "def add(a, b, c)",
  docstring: "Add three numbers",
  complexity: 1,
  lines_of_code: 3,
  file_path: "/app/test.py"
})
```

#### Create Parameter Nodes
```cypher
CREATE (param:Parameter {
  name: "a",
  order: 0
})
CREATE (sym)-[:HAS_PARAMETER]->(param)
```

#### Create Call Relationships
```cypher
CREATE (sym)-[:CALLS]->(other_func)
CREATE (sym)-[:IMPORTS]->(module)
```

### Service Layer: `graph_updater.py`
```python
class GraphUpdater:
    def create_symbol_node(self, symbol: ReAnalyzedSymbol) -> dict
    def update_symbol_node(self, symbol: ReAnalyzedSymbol) -> dict
    def create_parameter_nodes(self, symbol: ReAnalyzedSymbol) -> dict
    def create_relationships(self, symbol: ReAnalyzedSymbol) -> dict
    def update_file_symbols(self, file_path: str, symbols: List[ReAnalyzedSymbol]) -> dict
```

### Integration Layer: `graph_updater_integration.py`
```python
def update_symbol(symbol: ReAnalyzedSymbol) -> dict:
    # Thread-safe wrapper
    # Return {status, nodes_created, relationships_created}

def update_batch(symbols: List[ReAnalyzedSymbol]) -> dict:
    # Batch wrapper
    # Return {status, total_nodes, total_relationships, errors}
```

### REST Endpoints
```
POST /api/v1/update-symbol
    Input: ReAnalyzedSymbol
    Output: {status, nodes_created, relationships_created}

POST /api/v1/update-batch
    Input: {symbols: [ReAnalyzedSymbol]}
    Output: {status, total_nodes, total_relationships, errors}
```

### Expected Response
```json
{
  "status": "success",
  "symbol_name": "add",
  "nodes_created": 3,
  "relationships_created": 2,
  "message": "Created node for 'add' with 2 parameters and 0 call relationships"
}
```

### Implementation Priority
**High** - Directly uses Phase 8.6 output, completes the write-back cycle

---

## 🔄 Phase 8.8: Maintenance Worker

### Purpose
Background worker that continuously processes the change queue (Phase 8.3) through the full 8.5→8.6→8.7 pipeline.

### Architecture
```
Change Queue (Phase 8.3)
        ↓
[Polling Thread]
        ↓
Batch Processor
        ├─→ Phase 8.5: Invalidate stale symbols
        ├─→ Phase 8.6: Re-analyze changed symbols
        └─→ Phase 8.7: Update knowledge graph
        ↓
Status Log & Monitoring
```

### Service: `maintenance_worker.py`
```python
class MaintenanceWorker:
    def __init__(self, poll_interval: int = 5):
        self.poll_interval = poll_interval  # Check queue every 5 seconds
        self.running = False
    
    def start(self):
        # Start background thread
        # Continuously: check queue → process batch → update graph
    
    def stop(self):
        # Gracefully shutdown
    
    def process_batch(self, changes: List[FileChange]) -> dict:
        # 1. Invalidate removed/modified symbols (Phase 8.5)
        # 2. Re-analyze all changed symbols (Phase 8.6)
        # 3. Update knowledge graph (Phase 8.7)
        # Return stats
```

### Configuration
```python
MAINTENANCE_CONFIG = {
    "poll_interval": 5,  # Check queue every 5 seconds
    "batch_size": 50,    # Process 50 changes at once
    "max_workers": 3,    # 3 parallel workers
    "retry_failed": True,
    "log_level": "info"
}
```

### Monitoring Endpoints
```
GET /api/v1/maintenance-status
    Output: {running, files_processed, symbols_processed, errors, uptime}

GET /api/v1/maintenance-logs
    Output: {recent_logs: [timestamp, status, files_processed]}

POST /api/v1/maintenance-start
    Start the background worker

POST /api/v1/maintenance-stop
    Stop the background worker
```

### Expected Flow
```
1. File changes detected in test_module.py
2. Change queued in Phase 8.3
3. Maintenance worker polls queue
4. Detects 3 changes (1 add, 1 remove, 1 modify)
5. Phase 8.5: Invalidates "multiply" function
6. Phase 8.6: Re-analyzes "add" and "power" functions
7. Phase 8.7: Updates Neo4j with new data
8. Logs: "Processed test_module.py: 1 removed, 1 modified, 1 added"
```

### Implementation Priority
**Medium** - Orchestration layer, nice to have for automation

---

## 🎮 Phase 8.9: Agent Control

### Purpose
Start/stop endpoints and system-level control for the maintenance pipeline.

### REST Endpoints
```
POST /api/v1/start-maintenance
    Start all background workers
    Output: {status, workers_started}

POST /api/v1/stop-maintenance
    Stop all background workers gracefully
    Output: {status, workers_stopped}

POST /api/v1/pause-maintenance
    Pause processing (queue still collects changes)
    Output: {status, paused_at}

POST /api/v1/resume-maintenance
    Resume from pause
    Output: {status, resumed_at}

GET /api/v1/system-health
    Check if all phases are operational
    Output: {status, phases: {8.5: "ok", 8.6: "ok", ...}}

POST /api/v1/restart-system
    Full system restart (useful for debugging)
    Output: {status, restart_time}
```

### Configuration Endpoints
```
GET /api/v1/config/maintenance
    Get current maintenance config
    Output: {poll_interval, batch_size, max_workers, ...}

PUT /api/v1/config/maintenance
    Update maintenance config
    Input: {poll_interval: 10, batch_size: 100}
```

### Implementation Priority
**Medium** - Control layer for operational management

---

## ⚙️ Phase 8.10: Full Loop / Autonomous Sync

### Purpose
Complete end-to-end automation: code changes trigger full pipeline without manual intervention.

### Architecture
```
User commits code
        ↓
File Watcher detects change (Phase 8.1)
        ↓
Git Diff extracts details (Phase 8.2)
        ↓
Change queued (Phase 8.3)
        ↓
Maintenance Worker polls queue
        ↓
Invalidate stale symbols (Phase 8.5)
        ↓
Re-analyze changed symbols (Phase 8.6)
        ↓
Update knowledge graph (Phase 8.7)
        ↓
Graph is now fully synchronized ✅
```

### Telemetry & Monitoring
```python
class PipelineMetrics:
    def __init__(self):
        self.total_cycles = 0
        self.avg_cycle_time = 0.0
        self.total_symbols_processed = 0
        self.error_rate = 0.0
    
    def record_cycle(self, duration: float, symbols: int, errors: int):
        # Update metrics
        pass
    
    def get_report(self) -> dict:
        # Return {cycles, avg_time, symbols_processed, error_rate}
        pass
```

### Endpoints
```
GET /api/v1/pipeline-metrics
    Output: {total_cycles, avg_cycle_time, symbols_processed, error_rate}

GET /api/v1/pipeline-history
    Output: {last_10_cycles: [{timestamp, duration, symbols, errors}]}

POST /api/v1/test-full-pipeline
    Trigger one complete pipeline cycle on test data
    Output: {status, cycle_time, symbols_processed}
```

### Expected User Experience
```
1. Developer edits test_module.py in VS Code
2. Saves the file
3. Commits to git: git commit -m "Update add() signature"
4. RepoAlign automatically:
   ✓ Detects the change (Phase 8.1-8.4)
   ✓ Invalidates old metadata (Phase 8.5)
   ✓ Extracts new metadata (Phase 8.6)
   ✓ Updates knowledge graph (Phase 8.7)
   ✓ Logs to metrics (Phase 8.10)
5. System stays synchronized with zero human intervention
```

### Implementation Priority
**Low** - Final integration, but adds tremendous value

---

## 🛠️ Implementation Sequence

### Recommended Order
1. **Phase 8.7** (1-2 days)
   - Depends on: Phase 8.6 ✅
   - Unblocks: Phases 8.8, 8.10
   - Complexity: Medium

2. **Phase 8.8** (1-2 days)
   - Depends on: Phase 8.7 ✅
   - Unblocks: Phase 8.10
   - Complexity: Medium-High

3. **Phase 8.9** (0.5-1 day)
   - Depends on: Phase 8.8 ✅
   - Unblocks: Operational control
   - Complexity: Low

4. **Phase 8.10** (1-2 days)
   - Depends on: Phases 8.7, 8.8, 8.9 ✅
   - Unblocks: Production deployment
   - Complexity: Low-Medium

### Parallel Work
- Can work on Phase 8.7 documentation while Phase 8.5/8.6 are being tested
- Phase 8.9 can be designed in parallel with 8.8 implementation

### Total Estimated Time
- **8.7**: 1-2 days
- **8.8**: 1-2 days
- **8.9**: 0.5-1 day
- **8.10**: 1-2 days
- **Testing & Integration**: 2-3 days

**Grand Total: ~1-2 weeks of focused development**

---

## 📊 Testing Strategy

### Phase 8.7 Tests
```python
def test_create_symbol_node():
    # Create a new symbol, verify node in Neo4j
    
def test_update_symbol_node():
    # Update existing symbol, verify properties changed
    
def test_create_relationships():
    # Add relationships, verify in Neo4j
    
def test_batch_update():
    # Update 100 symbols, verify all succeed
```

### Phase 8.8 Tests
```python
def test_worker_polling():
    # Add changes to queue, verify worker processes them
    
def test_batch_processing():
    # 50 changes, verify all phases execute
    
def test_error_handling():
    # Invalid changes, verify graceful handling
    
def test_worker_restart():
    # Stop/start worker, verify state preserved
```

### Phase 8.9 Tests
```python
def test_start_stop():
    # Start/stop maintenance, verify state changes
    
def test_system_health():
    # Check health endpoint, verify all phases ok
    
def test_config_update():
    # Change config, verify worker uses new values
```

### Phase 8.10 Tests
```python
def test_full_pipeline():
    # End-to-end: file change → graph update
    # Measure latency, verify accuracy
    
def test_large_changeset():
    # 100+ files changed, verify handles gracefully
    
def test_telemetry():
    # Verify metrics are recorded and accurate
```

---

## 📚 Database Schema Updates

### Nodes (Already Defined)
- `File`, `Function`, `Class`, `Module`, `Repository`
- `Parameter`, `Import`, `Call`

### Relationships (Phase 8.7 will use)
```
Function -[:HAS_PARAMETER]-> Parameter
Function -[:CALLS]-> Function | Class
Function -[:IMPORTS]-> Module | Function
Class -[:HAS_METHOD]-> Function
Class -[:INHERITS]-> Class
File -[:CONTAINS]-> Function | Class
Module -[:IMPORTS]-> Module | Function
```

### Properties to Store (Phase 8.6 extracts, 8.7 writes)
```
Function {
  signature: String,
  docstring: String,
  complexity: Integer,
  lines_of_code: Integer,
  start_line: Integer,
  end_line: Integer
}

Parameter {
  name: String,
  order: Integer,
  annotation: String,
  default_value: String
}

Call {
  type: String,  # "direct" | "indirect"
  confidence: Float
}
```

---

## 🎓 Learning Resources

### Required Knowledge
- Neo4j Cypher Query Language (for Phase 8.7)
- Python threading/async patterns (for Phase 8.8)
- REST API design (for Phase 8.9)
- System monitoring & telemetry (for Phase 8.10)

### Recommended Reading
1. Neo4j Documentation: `CREATE`, `MERGE`, `SET`
2. Python: `threading`, `queue`, `logging`
3. FastAPI: Background tasks, lifecycle events
4. Prometheus/OpenTelemetry for metrics

---

## ✨ Production Readiness Checklist

- [ ] Phase 8.7: Neo4j integration tests pass
- [ ] Phase 8.8: Worker stress test (1000s of changes)
- [ ] Phase 8.9: Health check endpoints verified
- [ ] Phase 8.10: End-to-end latency < 10 seconds
- [ ] Comprehensive error handling & logging
- [ ] Documentation for each phase
- [ ] Docker integration tests
- [ ] Performance profiling (target: 1000 symbols/minute)
- [ ] Security audit (especially Phase 8.10 automation)
- [ ] Supervisor review & approval

---

## 🚀 Next Action After Supervisor Demo

1. **Complete supervisor demonstration** (today)
2. **Get feedback** on Phase 8.5 & 8.6
3. **Start Phase 8.7 implementation** (update graph)
4. **Test with real codebase** (RepoAlign itself)
5. **Measure performance** on production data
6. **Deploy Phase 8.8** (maintenance worker)
7. **Add monitoring** (Phase 8.9)
8. **Enable full automation** (Phase 8.10)

---

**You're on the home stretch! 🎉 Phases 8.5 & 8.6 are done. Now let's complete the pipeline! 🚀**
