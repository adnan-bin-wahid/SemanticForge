# Phase 6 Testing - Quick Reference Checklist

## Quick Start (3-5 minutes wait + execution)

### 1. DOCKER RESTART

```bash
cd E:\A A SPL3\SemanticForge\SemanticForge\RepoAlign
docker-compose down
docker-compose up -d
sleep 30
curl http://localhost:8000/api/v1/health
```

### 2. EXTENSION SETUP

```bash
cd frontend
npm run compile
# Then F5 in VS Code to start debugging
```

### 3. OPEN helpers.py

- In Extension Host window (new VS Code)
- File → Open Folder → test-project
- Click utils/helpers.py

### 4. GENERATE PATCH

```
Ctrl+Shift+P → "Generate Patch"
Instruction: "Add docstrings to the split_fullname function"
Wait 2-5 minutes...
```

---

## Testing Checklist

### ✓ Phase 6.1-6.5: Validation Services

- [ ] Diff view displays after generation
- [ ] No backend errors in docker logs
- [ ] Response includes "validation" field

### ✓ Phase 6.9: Validation Panel Display

```
Look for these in the right panel:
- [ ] Header shows "✓ Validation Passed" or "✗ Validation Failed"
- [ ] Color is green (passed) or red (failed)
- [ ] File path shows: "📄 File: utils/helpers.py"
- [ ] Error count and Warning count cards visible
```

### ✓ Phase 6.9: Validation Stages (Expandable)

```
Click each to expand:
- [ ] ✓ Syntax Validation - Shows "No syntax errors"
- [ ] ✓ Code Linting (Ruff) - Shows lint results or "No lint issues"
- [ ] ✓ Type Checking (Mypy) - Shows type results or "No type errors"
- [ ] ✓ Test Execution (Pytest) - Shows "All tests passed" or test counts
```

### ✓ Phase 6.10: Accept Logic - Scenario A (Passed Validation)

```
If validation shows all green checkmarks:
1. [ ] Click "Accept Patch" button
2. [ ] NO warning modal appears
3. [ ] Patch applies immediately
4. [ ] File updated with new docstrings
5. [ ] Success message: "✓ Patch accepted... (Validation passed)"
6. [ ] Diff viewer closes
7. [ ] Focus returns to helpers.py

Result: ✓ ACCEPT LOGIC WORKS FOR VALID PATCHES
```

### ✓ Phase 6.10: Accept Logic - Scenario B (Failed Validation)

```
If validation shows red X marks with errors:
1. [ ] Click "Accept Patch" button
2. [ ] Warning modal APPEARS with message:
      "⚠ Validation failed: N error(s), M warning(s). Apply anyway?"
3. [ ] Two buttons visible: "Yes, Apply" and "No, Cancel"

Test "Yes, Apply":
4. [ ] Click "Yes, Apply"
5. [ ] Patch applies despite warnings
6. [ ] Success message: "... (Validation had issues, but you confirmed)"

Test "No, Cancel":
6. [ ] Generate another patch (wait 2-5 min)
7. [ ] If validation fails again, click "Accept Patch"
8. [ ] Click "No, Cancel" in warning
9. [ ] Message: "Patch application cancelled..."
10. [ ] Diff stays open, file unchanged

Result: ✓ ACCEPT LOGIC VALIDATES BEFORE APPLYING
```

### ✓ Phase 6: Overall Pass/Fail

```
PASS if:
- [ ] Validation panel appears with results
- [ ] All 4 stages render (syntax, linting, type, tests)
- [ ] Color coding works (green/red)
- [ ] Stages expand/collapse
- [ ] Accept blocks invalid patches (warning shown)
- [ ] Accept applies valid patches (no warning)
- [ ] File updates correctly
- [ ] No crashes or errors

FAIL if:
- [ ] Panel doesn't appear
- [ ] Backend returns validation: null
- [ ] Accept button doesn't work
- [ ] File doesn't update
- [ ] Error in console
```

---

## Validation Panel Quick Reference

### What You Should See - Valid Patch

```
┌─────────────────────────────────────┐
│ ✓ Validation Passed                 │ ← Green
│ All validation stages completed     │
├─────────────────────────────────────┤
│ 📄 File: utils/helpers.py           │
├─────────────────────────────────────┤
│  [0]  Errors      [0]  Warnings     │
├─────────────────────────────────────┤
│ ▸ ✓ Syntax Validation (0 errors)    │ ← Green
│ ▸ ✓ Code Linting (0 errors)         │ ← Green
│ ▸ ✓ Type Checking (0 errors)        │ ← Green
│ ▸ ✓ Test Execution (tests passed)   │ ← Green
└─────────────────────────────────────┘
```

### What You Should See - Invalid Patch

```
┌─────────────────────────────────────┐
│ ✗ Validation Failed                 │ ← Red
│ 2 validation stages failed          │
├─────────────────────────────────────┤
│ 📄 File: utils/helpers.py           │
├─────────────────────────────────────┤
│  [3]  Errors      [1]  Warnings     │ ← Red/Yellow
├─────────────────────────────────────┤
│ ▸ ✓ Syntax Validation (0 errors)    │ ← Green
│ ▸ ✗ Code Linting (1 error, 2 warn)  │ ← Red
│   - Warning: Line too long          │
│     Line 45, Column 5               │
│ ▸ ✗ Type Checking (2 errors)        │ ← Red
│   - Error: Type mismatch            │
│     Line 32, Column 10              │
│ ▸ ✓ Test Execution (tests passed)   │ ← Green
└─────────────────────────────────────┘
```

---

## Common Issues & Quick Fixes

| Issue                                     | Check                            | Fix                              |
| ----------------------------------------- | -------------------------------- | -------------------------------- |
| No panel appears                          | docker logs backend              | Restart docker-compose           |
| Panel shows "Validation data will appear" | repo_path in request             | Panel works - data not validated |
| Accept button unresponsive                | Extension console (Ctrl+Shift+P) | Reload extension (Ctrl+R)        |
| File doesn't update                       | File permissions                 | Make file writable               |
| Validation shows all failures             | Generated code quality           | Try simpler instruction          |
| 2-5 min wait seems long                   | Expected with tinyllama          | Upgrade to faster model later    |

---

## Key Things to Verify

### Backend Validation Working?

```bash
curl -X POST http://localhost:8000/api/v1/validate-patch \
  -H "Content-Type: application/json" \
  -d '{
    "repo_path": "E:/A A SPL3/SemanticForge/SemanticForge/test-project",
    "file_relative_path": "utils/helpers.py",
    "generated_code": "def test():\n    pass"
  }'

Response should include: "overall_status", "constraint_check", "validation_stages"
```

### Frontend Integration Working?

```
Check Extension Host Console:
Ctrl+Shift+P → Toggle Developer Tools
Look for "Validation panel" or "updateValidationPanel" logs
Should NOT show errors
```

### Accept Logic Working?

```
When you click Accept:
- [ ] If validation passed: Direct apply (1-2 seconds)
- [ ] If validation failed: Warning modal (requires confirmation)
- [ ] File should update in both cases
- [ ] Success message should appear
```

---

## Test Matrix (Can Do Multiple Generations)

| Test # | Instruction                                                      | Expected Result                | ✓/✗ |
| ------ | ---------------------------------------------------------------- | ------------------------------ | --- |
| 1      | "Add docstrings to split_fullname"                               | Valid patch, passes validation |     |
| 2      | "Add type hints to all functions"                                | Likely valid, should pass      |     |
| 3      | "Add error handling to validate_email"                           | Likely valid, should pass      |     |
| 4      | "Make function names very_long_name_that_exceeds_pep8_standards" | Might have lint warnings       |     |

---

## Final Verification

When all tests pass, verify:

```
✓ Diff viewer shows code changes (Phase 5.10)
✓ Validation panel displays results (Phase 6.9)
✓ All 4 stages render with results (Phase 6.1-6.8)
✓ Color coding works (green/red/yellow) (Phase 6.9)
✓ Stages are collapsible (Phase 6.9)
✓ Issue details show line numbers (Phase 6.9)
✓ Accept shows warning for invalid patches (Phase 6.10)
✓ Accept applies valid patches directly (Phase 6.10)
✓ User can override with confirmation (Phase 6.10)
✓ File updates correctly (Phase 6.10)
✓ No console errors (All phases)

If all ✓:
=> PHASE 6 IS WORKING CORRECTLY
=> Ready for Phase 7 (Dynamic Analysis)
```

---

## Time Breakdown

```
Total test time: ~15-20 minutes per generation

Docker setup:           2-3 min
Extension setup:        1-2 min
Open file:              1 min
Generate patch:         3-5 min (wait for LLM)
Review diff:            1 min
Check validation panel: 2 min
Test Accept logic:      2 min
Test scenarios:         2-3 min
```

**Start with Part 1 of PHASE6_TESTING_PROCEDURE.md for detailed steps**
