# Phase 6 Complete Testing Procedure - Step by Step

Testing all validation layers (6.1-6.10) with helpers.py as test file

## Prerequisites Checklist

- [ ] helpers.py file is in your test-project/utils/ directory
- [ ] Docker and Docker Compose installed
- [ ] VS Code with extension repository open
- [ ] All code compiled (frontend TypeScript compiled)

---

## Part 1: Clean Docker Shutdown & Restart

### Step 1.1: Close Docker Compose Gracefully

```bash
cd E:\A A SPL3\SemanticForge\SemanticForge\RepoAlign

# Stop all running containers
docker-compose down

# Verify all containers stopped
docker ps
# Expected: No containers listed
```

### Step 1.2: Clean Docker Volumes (Optional - for fresh start)

```bash
# WARNING: This removes all data. Only do this for clean testing
docker-compose down -v

# Verify volumes removed
docker volume ls
```

### Step 1.3: Start Fresh Docker Containers

```bash
# Start all services (backend, ollama, neo4j, qdrant)
docker-compose up -d

# Wait 30-60 seconds for all services to be ready
sleep 30
```

### Step 1.4: Verify All Services Running

```bash
# Check all containers are running
docker ps

# Expected output should show:
# - backend (port 8000)
# - ollama (port 11434)
# - neo4j (port 7474, 7687)
# - qdrant (port 6333)
```

### Step 1.5: Verify Backend Health

```bash
# Test backend is responding
curl -s http://localhost:8000/api/v1/health

# Expected: Should return a health status (200 OK)
```

### Step 1.6: Check Backend Logs for Errors

```bash
# View backend startup logs (press Ctrl+C to exit)
docker-compose logs backend

# Look for:
# - "Application startup complete" message
# - No error messages about Neo4j, Qdrant, or Ollama connection
```

---

## Part 2: Prepare Frontend Extension

### Step 2.1: Verify Frontend Compilation

```bash
cd E:\A A SPL3\SemanticForge\SemanticForge\RepoAlign\frontend

# Compile TypeScript (should have 0 errors)
npm run compile

# Expected output:
# > repoalign-frontend@0.0.1 compile
# > tsc -p ./
# (no errors)
```

### Step 2.2: Check Compiled JavaScript Exists

```bash
# Verify dist folder exists with compiled files
dir out\

# Should contain:
# - extension.js
# - validationPanel.js
```

### Step 2.3: Load Extension in VS Code

```
In VS Code:
1. Open RepoAlign folder as workspace
2. Press F5 or Run → Start Debugging
3. Wait for new VS Code window to open (Extension Development Host)
4. Extension should load automatically
```

### Step 2.4: Verify Extension Loaded

```
In the Extension Development Host window:
1. Press Ctrl+Shift+P
2. Type "RepoAlign"
3. Should see commands like:
   - RepoAlign: Health Check
   - RepoAlign: Generate Patch
```

---

## Part 3: Open Test File (helpers.py)

### Step 3.1: Open helpers.py in Extension Host

```
In Extension Development Host:
1. File → Open Folder
2. Navigate to: E:\A A SPL3\SemanticForge\SemanticForge\test-project
3. Click Select Folder

Expected: test-project folder opens with utils/helpers.py visible
```

### Step 3.2: Navigate to helpers.py

```
In Extension Host:
1. Open file explorer (Ctrl+B)
2. Find and click: utils → helpers.py
3. File opens in editor

Expected: You can see the helpers.py code with functions:
- format_greeting
- validate_email
- sanitize_input
- split_fullname
- format_user_info
```

### Step 3.3: Verify File Content

```python
# helpers.py should show these functions (you can see them in editor)
def format_greeting(name: str) -> str:
def validate_email(email: str) -> bool:
def sanitize_input(text: str) -> str:
def split_fullname(fullname: str) -> tuple[str, str]:
def format_user_info(name: str, email: str) -> str:
```

---

## Part 4: Generate Patch (This Triggers Validation)

### Step 4.1: Open Command Palette

```
In Extension Host editor with helpers.py visible:
1. Press Ctrl+Shift+P
2. Type "Generate"
3. Click "RepoAlign: Generate Patch"
```

### Step 4.2: Enter Generation Instruction

```
A text input box appears asking for instruction.

Enter this instruction (simple task for tinyllama):
"Add docstrings to the split_fullname function explaining the parameters and return value"

Click OK or press Enter

Expected:
- A progress notification appears: "RepoAlign: Generating patch..."
- Backend starts processing
- This will take 2-5 minutes with tinyllama
```

### Step 4.3: Wait for Generation + Validation

```
While waiting, you should see:
1. "Sending request to backend..." (step 1)
2. "Processing generated patch..." (step 2)
3. "Patch displayed." (step 3)

Timeline:
- 0-10 seconds: Request sent to backend
- 10-30 seconds: Context retrieval
- 30-180 seconds: LLM code generation
- 180-210 seconds: Validation execution
- 210+: Results displayed

Total: 3-5 minutes approximately
```

---

## Part 5: Verify Diff View (Phase 5.10 part)

### Step 5.1: Check Diff Display

```
After generation completes, you should see:
1. Diff viewer showing Original (left) vs Generated (right)
2. Highlighted changes showing the docstring additions
3. Accept/Reject quick pick menu below diff

If you DON'T see this:
- Check Extension Host console for errors
- Verify backend is still running
- Check docker logs: docker-compose logs backend
```

### Step 5.2: Verify Code Generation Quality

```
In the diff viewer, verify:
- New docstrings were added to split_fullname
- Code syntax looks correct
- No obvious errors or incomplete code
- The function signature wasn't broken

Example expected change:
Before:
  def split_fullname(fullname: str) -> tuple[str, str]:

After:
  def split_fullname(fullname: str) -> tuple[str, str]:
      """
      Splits a full name into first and last name.

      Args:
          fullname: Full name string

      Returns:
          tuple: (first_name, last_name)
      """
```

---

## Part 6: Verify Validation Panel (Phase 6.9 part)

### Step 6.1: Check for Validation Panel

```
After diff displays, look for TWO panels:
1. Diff viewer (on left/center) - shows code changes
2. Validation Report panel (on right) - shows validation results

If you only see diff and NOT validation panel:
- This could mean:
  a) Backend didn't include validation data
  b) Panel failed to create
  c) repo_path wasn't in request

Check Extension Host console for errors (Ctrl+Shift+P → Toggle Developer Tools)
```

### Step 6.2: Examine Validation Panel Content

```
The Validation Panel should show:

✓ HEADER (color-coded):
  ✓ Validation Passed (or ✗ Validation Failed)
  Overall summary message

✓ FILE INFO:
  📄 File: utils/helpers.py

✓ STATISTICS:
  [Error count]  [Warning count]

✓ VALIDATION STAGES (collapsible):
  ▸ ✓ Syntax Validation (0 errors)
  ▸ ✓ Code Linting (Ruff) (0 errors, X warnings)
  ▸ ✓ Type Checking (Mypy) (0 errors)
  ▸ ✓ Test Execution (Pytest) (optional)
```

### Step 6.3: Expand Validation Stages

```
Click on each stage header to expand:

1. Click "Syntax Validation":
   - Should show: "No syntax errors found"
   - Passed: Yes (green checkmark)

2. Click "Code Linting":
   - Should show: Ruff check results
   - Might have warnings about line length or imports
   - If errors: Shows issue list with line numbers

3. Click "Type Checking":
   - Should show: Mypy results
   - Might have type annotation warnings
   - If errors: Shows type mismatch details

4. Click "Test Execution":
   - If tests ran: Shows pass/fail counts
   - Otherwise: "All tests passed" or "Tests not executed"
```

### Step 6.4: Check Issue Details (if any)

```
If validation found issues, you should see for each:

Issue Format:
  Issue Type: [Type of issue]
  Line X, Column Y
  [Message about the issue]

Example:
  Warning: Line too long (E501)
  Line 45, Column 5
  Line exceeds 100 characters (120 chars)
```

### Step 6.5: Verify Panel Colors

```
Check color coding:
- Status icon:
  ✓ Green if validation passed
  ✗ Red if validation failed

- Error count card: Red if > 0
- Warning count card: Yellow if > 0

If all stages show green checkmarks with 0 errors:
✓ This is SUCCESS - validation passed!
```

---

## Part 7: Test Accept with Validation Gate (Phase 6.10)

### Step 7.1: Click Accept Patch

```
In the quick pick menu that appeared with the diff:
- Click "✓ Accept Patch"

OR press the button if visible in diff UI
```

### Step 7.2: Validation Gate Check - Scenario A (Passed Validation)

```
If validation PASSED (all green):

Expected behavior:
1. Patch applies immediately (no warning modal)
2. File content updates with new docstrings
3. Diff view closes
4. Editor refocuses on helpers.py
5. Success message: "✓ Patch accepted and applied to the file. (Validation passed)"

If this happens:
✓ PHASE 6.10 ACCEPT LOGIC WORKS CORRECTLY
```

### Step 7.3: Validation Gate Check - Scenario B (Failed Validation)

```
If validation FAILED (red X marks):

Expected behavior:
1. Warning modal appears:
   "⚠ Validation failed: N error(s), M warning(s). Apply anyway?"
2. Two buttons: "Yes, Apply" and "No, Cancel"

If warning appears:
✓ VALIDATION GATE IS WORKING

Now test the choices:
```

### Step 7.4: Test "Yes, Apply" Button

```
In the warning modal:
Click "Yes, Apply"

Expected:
1. Modal closes
2. Patch applies despite validation failures
3. File updates with generated code
4. Diff closes
5. Success message shows: "... (Validation had issues, but you confirmed)"

If this works:
✓ USER CAN OVERRIDE FAILED VALIDATION
```

### Step 7.5: Test "No, Cancel" Button (Do another generation first)

```
To test the Cancel button, you need another validation failure:

1. Generate another patch (repeat Steps 4.1-4.3)
2. Wait for validation to complete
3. If validation shows failures, click Accept
4. In warning modal, click "No, Cancel"

Expected:
1. Modal closes
2. Message: "Patch application cancelled..."
3. Diff view stays open (not closed)
4. helpers.py file unchanged
5. You can review patch again or click Reject

If this works:
✓ USER CAN CANCEL PATCH APPLICATION
```

---

## Part 8: Test Reject Button

### Step 8.1: Click Reject

```
With diff viewer still open from any generation:
1. Click "✗ Reject Patch" in quick pick

Expected:
1. Diff view closes
2. File unchanged
3. Message: "✗ Patch rejected."
4. helpers.py content stays as original
```

---

## Part 9: Comprehensive Validation Testing

### Step 9.1: Multiple Generations Test

```
Repeat the generation process 2-3 times with different instructions:

Generation 1: "Add docstrings..."
Generation 2: "Add type hints to return values..."
Generation 3: "Add error handling..."

For each:
1. Check validation panel appears
2. Verify all stages show results
3. Test Accept with validation gate
4. File should update each time

Expected: All 3 should work consistently
```

### Step 9.2: Test with Deliberately Bad Instruction

```
Try an instruction that might generate invalid Python:
"Change validate_email to use invalid syntax"

Expected validation behavior:
1. Syntax validation should FAIL (red X)
2. Error message: "Invalid syntax at line X"
3. Diff might not even display
4. Or diff displays but Accept shows warning

This tests:
✓ Syntax validation is working (Phase 6.4)
✓ Validation gate prevents broken code (Phase 6.10)
```

### Step 9.3: Check Console for Validation Errors

```
In VS Code Extension Host:
1. Press Ctrl+Shift+P
2. Type "Toggle Developer Tools"
3. Press Enter

In Console tab, you should see logs like:
- "Validation panel created"
- "Validation data received"
- "Panel updated with validation results"
- No ERROR messages

This verifies backend-frontend communication.
```

---

## Part 10: Verify Backend Validation Services

### Step 10.1: Check Backend Logs

```bash
# View validation-related logs
docker-compose logs backend | grep -i "validat"

Expected to see:
- Validation requests being processed
- Ruff execution logs
- Mypy execution logs
- Test execution logs (if enabled)
```

### Step 10.2: Manual Validation Test (Optional)

```bash
# Test validation endpoint directly
curl -X POST http://localhost:8000/api/v1/validate-patch \
  -H "Content-Type: application/json" \
  -d '{
    "repo_path": "E:/A A SPL3/SemanticForge/SemanticForge/test-project",
    "file_relative_path": "utils/helpers.py",
    "generated_code": "def test():\n    pass",
    "run_tests": false
  }'

Expected: JSON response with validation_report showing:
- overall_status: "passed" or "failed"
- constraint_check results
- validation_stages breakdown
```

---

## Part 11: Success Criteria Checklist

### Phase 6.1-6.5: Validation Services ✓

- [ ] Backend doesn't crash when validating patch
- [ ] Validation response includes structured report

### Phase 6.6: Test Runner ✓

- [ ] Test execution shows in logs (if enabled)
- [ ] Test results included in validation report

### Phase 6.7: Validation Endpoint ✓

- [ ] /validate-patch endpoint returns proper response
- [ ] Response includes validation_stages breakdown

### Phase 6.8: Auto-Validation Integration ✓

- [ ] /generate-patch response includes validation field
- [ ] Validation field is not null (data is present)

### Phase 6.9: Frontend Panel Display ✓

- [ ] Validation panel appears alongside diff
- [ ] All stages render (syntax, linting, type check, tests)
- [ ] Color coding works (green/red/yellow)
- [ ] Stages are collapsible
- [ ] Issue details display with line numbers

### Phase 6.10: Accept Logic Validation Gate ✓

- [ ] Valid patches apply without warning
- [ ] Invalid patches show warning modal
- [ ] User can override with "Yes, Apply"
- [ ] User can cancel with "No, Cancel"
- [ ] Success messages reflect validation status
- [ ] File updates correctly on Accept

---

## Part 12: Troubleshooting Guide

### Issue: Validation Panel Doesn't Appear

```
Possible causes:
1. repo_path not in request
   → Fix: Check extension.ts includes repo_path

2. Backend validation failed silently
   → Fix: Check docker logs: docker-compose logs backend

3. Panel creation failed
   → Fix: Check Extension Host console (Ctrl+Shift+P → Toggle Developer Tools)

4. Validation field is null
   → Fix: This is backward compatible - panel shows "Validation data will appear here..."
```

### Issue: Validation Shows All Failures

```
Possible causes:
1. Ruff/Mypy not installed in Docker
   → Fix: Rebuild container: docker-compose build backend

2. Generated code has legitimate syntax errors
   → Fix: Try simpler instruction or check LLM output

3. Repository path wrong
   → Fix: Verify repo_path in extension.ts matches actual path
```

### Issue: Accept Button Doesn't Work

```
Possible causes:
1. userAction is undefined
   → Check Extension Host console for errors

2. Workspace edit failed
   → Verify file is not read-only
   → Check VS Code permissions

3. File not saving
   → File might be modified externally
   → Try closing and reopening file
```

### Issue: Panel Shows Wrong Stage Results

```
Possible causes:
1. Backend validation stages not in response
   → Check validation report includes validation_stages

2. Frontend parsing error
   → Check Extension Host console for JSON parse errors

3. Stage results incomplete
   → Verify all stages ran (syntax → lint → type → tests)
```

---

## Part 13: Performance Benchmarks

### Expected Timing

```
Step                          Duration        Total
1. Request sent              1-5 sec         1-5 sec
2. Context retrieval         5-15 sec        6-20 sec
3. LLM generation            60-180 sec      66-200 sec
4. Validation execution:
   - Syntax check            1-2 sec         67-202 sec
   - Ruff linting            2-5 sec         69-207 sec
   - Mypy type check         3-10 sec        72-217 sec
   - Pytest (if enabled)     30-60 sec       102-277 sec
5. Panel render              <1 sec          102-278 sec

TOTAL: 2-5 minutes (expected with tinyllama)
```

### Memory Usage

```
Expected resource consumption:
- Backend container: 2-4 GB RAM during LLM inference
- Docker total: 6-8 GB with all services
- Frontend panel: <50 MB

If memory exceeds 10 GB:
- Check for memory leaks
- Restart Docker: docker-compose down && docker-compose up -d
```

---

## Part 14: Next Steps After Phase 6 Testing

If all tests pass:

1. ✓ Phase 6 is production-ready
2. → Move to Phase 7: Dynamic Analysis
3. → Document any edge cases found
4. → Note performance benchmarks
5. → Plan performance optimization if needed

---

## Quick Reference Commands

```bash
# Start testing
docker-compose down && docker-compose up -d && sleep 30

# Check backend
curl http://localhost:8000/api/v1/health

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose build backend && docker-compose up -d

# Clean everything
docker-compose down -v && rm -rf backend/__pycache__
```

---

## Test Results Log Template

```
Date: [DATE]
Test File: helpers.py
Test Instruction: [INSTRUCTION]
LLM Model: tinyllama

Phase 6.1-6.5 (Validation Services): [ ] PASS [ ] FAIL
Phase 6.6 (Test Runner): [ ] PASS [ ] FAIL (if enabled)
Phase 6.7 (Validation Endpoint): [ ] PASS [ ] FAIL
Phase 6.8 (Auto-Validation): [ ] PASS [ ] FAIL
Phase 6.9 (Frontend Panel): [ ] PASS [ ] FAIL
Phase 6.10 (Accept Logic): [ ] PASS [ ] FAIL

Issues Found:
[List any issues]

Performance:
- Total time: [TIME]
- Panel render time: [TIME]

Recommendations:
[Suggestions for improvement]
```

---

**Ready to start testing? Begin with Part 1: Clean Docker Shutdown & Restart**
