# Phase 6 Testing - Monitoring & Debugging Guide

Where to look and what to check during testing

---

## 1. Docker Container Logs

### Check Backend Validation Processing

```bash
# Watch backend logs in real-time
docker-compose logs -f backend

# Filter for validation messages
docker-compose logs backend | grep -i "validat"

# Filter for specific phase
docker-compose logs backend | grep "Ruff"      # Phase 6.2
docker-compose logs backend | grep "Mypy"      # Phase 6.3
docker-compose logs backend | grep "syntax"    # Phase 6.4
docker-compose logs backend | grep "constraint"# Phase 6.5
docker-compose logs backend | grep "pytest"    # Phase 6.6
```

### What Good Logs Look Like

```
✓ backend_1  | INFO: Started validation pipeline
✓ backend_1  | INFO: Basic rules check: PASSED
✓ backend_1  | INFO: Ruff linting: PASSED (0 errors, 1 warning)
✓ backend_1  | INFO: Mypy type checking: PASSED
✓ backend_1  | INFO: Validation complete: overall_status=passed
```

### What Bad Logs Look Like

```
✗ backend_1  | ERROR: Failed to run Ruff
✗ backend_1  | ERROR: Mypy execution timeout
✗ backend_1  | ERROR: Neo4j connection failed
✗ backend_1  | ERROR: Could not create temporary directory
```

### Each Phase's Log Signature

| Phase    | What to Look For            | Log Line                              |
| -------- | --------------------------- | ------------------------------------- |
| 6.1      | Temp directory creation     | "Creating temp directory"             |
| 6.2      | Ruff subprocess call        | "Running ruff check"                  |
| 6.3      | Mypy subprocess call        | "Running mypy check"                  |
| 6.4      | AST parsing                 | "Running basic rules"                 |
| 6.5      | Pipeline orchestration      | "Starting validation pipeline"        |
| 6.6      | Pytest execution            | "Running pytest" or "Tests: X passed" |
| 6.7      | Endpoint called             | "POST /api/v1/validate-patch"         |
| 6.8      | Integration with generation | "Auto-validating patch"               |
| 6.9-6.10 | Response sent               | "Returning response with validation"  |

---

## 2. Extension Console Output

### How to Access

```
In Extension Development Host window:
Ctrl+Shift+P → "Toggle Developer Tools" → "Console" tab
```

### Expected Frontend Logs

```javascript
✓ [INFO] Validation panel created
✓ [INFO] Panel configuration: viewType=repoalignValidation
✓ [INFO] Validation data received: {overall_status: "passed", ...}
✓ [INFO] updateValidationPanel called
✓ [INFO] HTML generated with X stages
✓ [INFO] Panel updated successfully
```

### Error Signs

```javascript
✗ [ERROR] Cannot read property 'overall_status' of undefined
  → Validation data missing from response

✗ [ERROR] WebviewPanel is undefined
  → Panel creation failed

✗ [ERROR] TypeError: renderValidationStages is not a function
  → Module import failed

✗ [ERROR] Unexpected token in JSON
  → Response parsing error
```

### What Each Function Logs

| Function                 | Logs What                             |
| ------------------------ | ------------------------------------- |
| createValidationPanel()  | "Panel created"                       |
| updateValidationPanel()  | "Panel updated" with validation data  |
| getValidationHtml()      | HTML generation (silent unless error) |
| renderValidationStages() | "Rendering X stages"                  |
| renderStageDetails()     | "Rendering stage: X" per stage        |
| escapeHtml()             | HTML escaping (silent)                |

---

## 3. VS Code Output Channel

### Access Output Panel

```
In Extension Host:
Ctrl+Shift+` (backtick) opens Terminal
View → Output → Select "RepoAlign" or "Extension Host"
```

### What to Monitor

```
✓ "RepoAlign extension activated"
✓ "Patch generation command registered"
✓ "Backend available at http://localhost:8000"
✓ "Patch generated successfully"
✓ "Validation data received"
```

### Common Issues

```
✗ "Failed to connect to backend"
  → Backend not running

✗ "Request timeout after 330000ms"
  → LLM taking too long

✗ "Extension activation failed"
  → TypeScript compilation error
```

---

## 4. Network Traffic & API Responses

### Monitor HTTP Requests

#### Option A: VS Code Network Tab

```
DevTools → Network tab → Generate Patch
Shows:
- POST /api/v1/generate-patch (Status: 200)
- Response size: ~5-50 KB
- Time: ~3-5 minutes for tinyllama
```

#### Option B: Backend Logging

```bash
# Check what endpoints are being hit
docker-compose logs backend | grep "POST\|GET"

Expected flow:
1. POST /api/v1/generate-patch → 200 OK
2. Internal: retrieve-context
3. Internal: LLM call
4. Internal: validation pipeline
5. Response: ~2-3 MB JSON
```

#### Option C: Manual Curl Test

```bash
# Test validation endpoint directly
curl -X POST http://localhost:8000/api/v1/validate-patch \
  -H "Content-Type: application/json" \
  -d '{
    "repo_path": "E:/A A SPL3/SemanticForge/SemanticForge/test-project",
    "file_relative_path": "utils/helpers.py",
    "generated_code": "def test():\n    pass"
  }' | python -m json.tool | head -50

Expected response structure:
{
  "status": "success",
  "validation_report": {
    "overall_status": "passed",
    "total_errors": 0,
    "total_warnings": 0,
    "validation_stages": {
      "syntax": {...},
      "linting": {...},
      "type_checking": {...},
      "tests": {...}
    }
  }
}
```

---

## 5. File System Changes During Testing

### Track Temporary Files

```bash
# See what temporary files are created during validation
ls -la /tmp/repoalign*

Expected:
- Temporary directory created
- helpers.py copied to temp location
- Generated code written to temp file
- Validation runs on temp copies
- Cleanup removes temp directories
```

### Verify File Modifications

```bash
# Check if helpers.py was actually updated after Accept
cat test-project/utils/helpers.py

Expected change:
Before: split_fullname function has minimal docstring
After: split_fullname has detailed docstring (if generated correctly)
```

### Monitor Disk Space

```bash
# Check if temp files are cleaned up
df -h

Expected: No continuous growth of /tmp after tests complete
If growing: Temp cleanup not working (bug in phase 6.1)
```

---

## 6. Database Changes (Neo4j)

### Check Graph Updates

```bash
# Access Neo4j browser
http://localhost:7474

# Query after patch applied
MATCH (f:Function {name: "split_fullname"})
RETURN f.docstring, f.signature

Expected: Function node might have updated metadata
(Optional - only if graph update implemented)
```

---

## 7. Real-Time Monitoring Dashboard

### Setup Combined Monitoring

```bash
# Terminal 1: Watch backend logs
docker-compose logs -f backend

# Terminal 2: Watch temp files
watch 'ls -la /tmp/repoalign* 2>/dev/null | tail -20'

# Terminal 3: Monitor Docker stats
docker stats backend

# VS Code: Extension console (Ctrl+Shift+J)
# VS Code: Output panel (Ctrl+Shift+`)
```

### What You Should See Over Time

```
T=0s:    User clicks "Generate Patch"
T=2s:    Backend receives request (in terminal 1)
T=10s:   Context retrieval logs appear
T=30s:   "Calling LLM..." log appears
T=60-180s: Silent (LLM processing, watch Docker stats)
T=190s:   Validation logs appear (Ruff, Mypy, etc)
T=210s:   Response sent, extension receives data (console)
T=212s:   Diff viewer appears in VS Code
T=215s:   Validation panel appears (check console)
T=216s:   Quick pick menu appears
T=220s:   User clicks "Accept Patch"
T=221s:   File updated, panels close
T=225s:   Temp files cleaned up (terminal 2)
```

---

## 8. Phase-by-Phase Validation Points

### Phase 6.1: Temporary Patch Application

**File to Monitor:** Backend logs
**What to Look For:**

```
✓ "Creating temporary directory for patch validation"
✓ "Copying repository to temporary location"
✓ "Writing generated code to temp file"
✓ "Temp directory: /tmp/repoalign_XXXXX"
```

### Phase 6.2: Ruff Integration

**File to Monitor:** Backend logs + Docker stats
**What to Look For:**

```
✓ "Running ruff check on temporary code"
✓ "Ruff output:" (followed by linting results)
✓ CPU usage spike (brief)
✓ "Ruff check complete"
```

### Phase 6.3: Mypy Integration

**File to Monitor:** Backend logs
**What to Look For:**

```
✓ "Running mypy type checking"
✓ "Mypy output:" (followed by type results)
✓ "No type errors found" or error list
```

### Phase 6.4: Basic Rules Checker

**File to Monitor:** Backend logs
**What to Look For:**

```
✓ "Running basic syntax rules"
✓ "AST parsing successful"
✓ "Syntax validation passed"
```

### Phase 6.5: Constraint Checker Service

**File to Monitor:** Backend logs
**What to Look For:**

```
✓ "Starting validation pipeline"
✓ "Overall status: passed" or "failed"
✓ "Aggregated results: X errors, Y warnings"
```

### Phase 6.6: Test Execution

**File to Monitor:** Backend logs (if run_tests=true)
**What to Look For:**

```
✓ "Running pytest in temporary directory"
✓ "pytest output:" (test results)
✓ "Tests: 10 passed, 0 failed"
```

### Phase 6.7-6.8: Validation Integration

**File to Monitor:** Network response body
**What to Look For:**

```json
{
  "validation": {
    "overall_status": "passed",
    "validation_stages": { ... }
  }
}
```

### Phase 6.9: Frontend Panel Display

**File to Monitor:** Extension console
**What to Look For:**

```
✓ "Validation panel created"
✓ "updateValidationPanel called"
✓ "Panel HTML generated with 4 stages"
```

### Phase 6.10: Accept Logic

**File to Monitor:** Extension console + File system
**What to Look For:**

```
✓ "Checking validation status before accept"
✓ "Validation passed - applying patch"
✓ [File updated on disk]
OR
✓ "Validation failed - showing warning modal"
✓ "User chose: Yes, Apply" / "No, Cancel"
```

---

## 9. Troubleshooting Checklist by Monitoring Point

| Issue                     | Monitor           | Expected            | Actual           | Fix                          |
| ------------------------- | ----------------- | ------------------- | ---------------- | ---------------------------- |
| Validation panel missing  | Extension console | Panel logs          | Errors or silent | Check backend logs           |
| Stages not rendering      | Extension console | "4 stages rendered" | "0 stages"       | Check response structure     |
| Accept doesn't work       | File system       | File updated        | Not updated      | Check file permissions       |
| Validation takes too long | Docker stats      | 1-2 min generation  | 10+ min          | Model too slow               |
| Panel shows errors        | Validation panel  | All green           | Red X marks      | Check generated code quality |
| Backend connection fails  | Network tab       | Status 200          | 500/timeout      | Restart docker-compose       |

---

## 10. Performance Baseline Measurements

### Take These Measurements During Testing

```bash
# 1. Total Response Time
START: User clicks "Generate Patch"
END: Validation panel appears
MEASURE: Record time in seconds
TARGET: 180-300 seconds (3-5 minutes) with tinyllama

# 2. Backend Processing Time
START: GET request sent
END: Response returned
MEASURE: Use network tab or curl timing
TARGET: 180+ seconds (mostly LLM)

# 3. Validation Execution Time
START: "Starting validation pipeline"
END: "Validation complete"
MEASURE: From backend logs
TARGET: 5-20 seconds (syntax + ruff + mypy)

# 4. Frontend Rendering Time
START: Response received
END: Panel visible
MEASURE: From extension console timestamps
TARGET: <1 second

# 5. Memory Usage Peak
docker stats backend --no-stream
TARGET: 2-4 GB during LLM inference
```

### Record Results

```
Test Date: __________
Model: tinyllama
File: helpers.py
Instruction: "Add docstrings..."

Total Time: ____ seconds
Backend Time: ____ seconds
Validation Time: ____ seconds
Frontend Time: ____ seconds
Peak Memory: ____ MB

Notes: ________________________
```

---

## 11. Quick Debugging Commands

```bash
# Check everything is running
docker-compose ps

# See all recent logs
docker-compose logs --tail=100

# Monitor in real-time
docker-compose logs -f

# Rebuild after code changes
docker-compose build backend && docker-compose up -d

# Clean restart
docker-compose down -v && docker-compose up -d

# Check a specific service
docker-compose logs backend
docker-compose logs ollama
docker-compose logs neo4j

# Test backend endpoint
curl http://localhost:8000/api/v1/health

# Test validation directly
curl -X POST http://localhost:8000/api/v1/validate-patch \
  -H "Content-Type: application/json" \
  -d '{"repo_path":"...","file_relative_path":"...","generated_code":"..."}'

# View network requests (in DevTools)
F12 → Network → Generate Patch → Click request → Response tab

# Check for errors
docker-compose logs backend 2>&1 | grep -i error
```

---

## 12. Success Indicators Checklist

Use this to verify each phase while monitoring:

### Phase 6.1 ✓

- [ ] Logs show "Creating temporary directory"
- [ ] Temp directory exists in /tmp
- [ ] File copied to temp location

### Phase 6.2 ✓

- [ ] Logs show "Running ruff check"
- [ ] Ruff output appears in logs
- [ ] Takes 2-5 seconds

### Phase 6.3 ✓

- [ ] Logs show "Running mypy"
- [ ] Mypy output appears in logs
- [ ] Takes 3-10 seconds

### Phase 6.4 ✓

- [ ] Logs show "Basic syntax rules"
- [ ] AST parsing completes
- [ ] Takes <1 second

### Phase 6.5 ✓

- [ ] Logs show "Starting validation pipeline"
- [ ] All checks run in order
- [ ] Takes 5-20 seconds total

### Phase 6.6 ✓

- [ ] Logs show "Running pytest" (if enabled)
- [ ] Test results appear
- [ ] Takes 30-60 seconds

### Phase 6.7-6.8 ✓

- [ ] Response includes "validation" field
- [ ] Response is not null
- [ ] Contains validation_stages

### Phase 6.9 ✓

- [ ] Extension console shows panel logs
- [ ] Panel appears in UI
- [ ] All 4 stages render

### Phase 6.10 ✓

- [ ] Accept button works
- [ ] File updates after accept
- [ ] Validation gate shows warning for failures

---

**Use this guide alongside the three main testing guides:**

- PHASE6_TESTING_PROCEDURE.md (detailed steps)
- PHASE6_QUICK_CHECKLIST.md (quick reference)
- PHASE6_VISUAL_GUIDE.md (what you should see)
