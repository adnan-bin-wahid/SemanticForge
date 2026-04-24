# Phase 6 Testing - Visual & Expected Output Guide

This guide shows EXACTLY what you should see at each step.

---

## STEP 1: After Docker Restart - Backend Health Check

### Command

```bash
curl http://localhost:8000/api/v1/health
```

### Expected Output

```json
{
  "status": "healthy",
  "services": {
    "neo4j": "connected",
    "qdrant": "connected",
    "ollama": "ready"
  }
}
```

### If You See Different Output

- If error message: Backend not running
  - Fix: `docker-compose logs backend` to check errors
- If timeout: Take longer to start
  - Wait 60 seconds and try again

---

## STEP 2: After Extension Compiles

### Command

```bash
npm run compile
```

### Expected Output

```
> repoalign-frontend@0.0.1 compile
> tsc -p ./
```

**Nothing else should print** = SUCCESS (0 errors)

### If You See Errors

```
src/extension.ts(10,5): error TS2339: Property 'X' does not exist
```

- There's a TypeScript error
- Check files were saved correctly
- Restart compilation

---

## STEP 3: Extension Development Host Opens

### What You'll See

```
NEW WINDOW OPENS (looks like normal VS Code)

Title: "[Extension Development Host]"

In the title bar area, you'll see a notification:
"This is the Extension Development Host window"
```

### How to Know It's Working

1. New VS Code window opens
2. Shows as "Extension Development Host" in taskbar
3. No preview banner visible
4. Command palette works (Ctrl+Shift+P)

---

## STEP 4: After Opening test-project Folder

### Left Sidebar Shows

```
EXPLORER
├── test-project
│   ├── .gitignore
│   ├── utils/
│   │   └── helpers.py          ← CLICK THIS
│   ├── pytest.ini
│   └── tests/
│       └── test_helpers.py
```

### After Clicking helpers.py - Editor Shows

```
File: utils/helpers.py

import re
from typing import List


def format_greeting(name: str) -> str:
    """
    Formats a greeting message.
    """
    return f"Hello, {name}!"


def validate_email(email: str) -> bool:
    """
    Validates if an email address has correct format.

    Args:
        email: Email address to validate

    Returns:
        bool: True if email format is valid
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

    [... more functions ...]
```

✓ If this shows: **helpers.py is open and ready**

---

## STEP 5: Generate Patch Command

### Command Palette

```
Ctrl+Shift+P (opens command palette)

Type: "Gen"

Shows:
> RepoAlign: Generate Patch

Click it or press Enter
```

### Input Box Appears

```
PROMPT: "Enter your instruction for improving the code in the current file:"

TYPE THIS:
"Add docstrings to the split_fullname function explaining the parameters and return value"

Then press Enter or click OK
```

---

## STEP 6: Generation Progress (2-5 minutes)

### Notification Popup (Bottom Right)

```
🔄 RepoAlign: Generating patch...
   ├─ 0% Sending request to backend...
   ├─ 25% Processing generated patch...
   └─ 100% Patch displayed.
```

### What Happens During Wait

```
During wait (2-5 minutes), you'll see:

0-10 sec:    "Sending request to backend..." (quick)
10-30 sec:   "Processing generated patch..." (quick)
30-180 sec:  Quiet (LLM generating - takes time)
180-210 sec: "Processing..." again (validation running)
210+ sec:    Patch displays and notification closes
```

### If It Gets Stuck

```
If progress doesn't move after 10 minutes:
- Check backend is running: docker ps
- Check logs: docker-compose logs backend
- Try killing process: docker-compose down && docker-compose up -d
```

---

## STEP 7: Diff Viewer Appears (Left/Center)

### Visual Layout

```
┌─────────────────────────────────────────────┐
│ RepoAlign: utils/helpers.py                 │ ← Tab title
│ (Original vs. Generated)                    │
├──────────────────┬──────────────────────────┤
│  ORIGINAL        │  GENERATED               │
│  (from file)     │  (from LLM)              │
├──────────────────┼──────────────────────────┤
│ def split_full   │ def split_fullname      │
│ name(fullname):  │ (fullname: str):        │
│     parts = ...  │     """                 │
│     if len(parts)│     Splits a full name..│
│                  │     Args:                │
│                  │       fullname: ...     │
│                  │     Returns:             │
│                  │       tuple: (first...  │
│                  │     """                 │
│                  │     parts = ...         │
│                  │     if len(parts)       │
└──────────────────┴──────────────────────────┘

Differences shown in LIGHTER BACKGROUND COLOR
New lines HIGHLIGHTED IN GREEN
Removed lines CROSSED OUT
```

### Quick Pick Menu (Below Diff)

```
? Review the diff and choose: Accept or Reject the generated patch
▶ ✓ Accept Patch
  ✗ Reject Patch
```

**If you see this: ✓ Diff view working (Phase 5.10 confirmed)**

---

## STEP 8: Validation Panel Appears (Right Side)

### Visual Layout - Panel on Right

```
┌────────────────────────┬──────────────────────────────┐
│ DIFF VIEW (Left)       │ VALIDATION PANEL (Right)     │
│                        │                              │
│ def split_fullname     │ ✓ Validation Passed         │
│   """                  │ All validation stages passed │
│   Splits a full name   │                              │
│   ...                  │ 📄 File: utils/helpers.py   │
│                        │                              │
│                        │ ┌──────────┬──────────────┐  │
│                        │ │ [0]      │ [0]          │  │
│                        │ │ Errors   │ Warnings     │  │
│                        │ └──────────┴──────────────┘  │
│                        │                              │
│                        │ ▸ ✓ Syntax Validation        │
│                        │   (0 errors)                 │
│                        │ ▸ ✓ Code Linting (Ruff)      │
│                        │   (0 errors, 1 warning)      │
│                        │ ▸ ✓ Type Checking (Mypy)     │
│                        │   (0 errors)                 │
│                        │ ▸ ✓ Test Execution (Pytest)  │
│                        │   (All tests passed)         │
└────────────────────────┴──────────────────────────────┘
```

### Color Indicators

```
STATUS: GREEN if ✓ (passed), RED if ✗ (failed)

ERRORS CARD: Shows as RED number if > 0
WARNINGS CARD: Shows as YELLOW/ORANGE number if > 0

STAGES:
- ✓ in GREEN = stage passed
- ✗ in RED = stage failed
- Stage name is UNDERLINED if clickable
```

**If you see this: ✓ Validation panel working (Phase 6.9 part 1)**

---

## STEP 9: Expand a Validation Stage

### Before Clicking

```
▸ ✓ Code Linting (Ruff) (0 errors, 1 warning)
  ^
  Arrow pointing RIGHT (collapsed)
```

### After Clicking

```
▼ ✓ Code Linting (Ruff) (0 errors, 1 warning)
   Found 1 error and 1 warning during linting

   - Warning: Line too long (E501)
     Line 35, Column 5
     Line exceeds 100 characters (135 chars)
  ^
  Arrow now points DOWN (expanded)
```

### Expected Content for Each Stage

**Syntax Validation**

```
▼ ✓ Syntax Validation (0 errors)
   No syntax errors found
   [or errors list if validation failed]
```

**Code Linting**

```
▼ ✓ Code Linting (Ruff) (0 errors, X warnings)
   Found N issues during linting

   - Issue Type: [Name of linting rule]
     Line XX, Column YY
     [Message about the issue]

   - [More issues...]
```

**Type Checking**

```
▼ ✓ Type Checking (Mypy) (0 errors)
   All type checks passed
   [or mypy errors if validation failed]
```

**Test Execution**

```
▼ ✓ Test Execution (Pytest)
   All tests passed

   Passed: 10
   Failed: 0
   Errors: 0
   Skipped: 0
```

**If you see this: ✓ Validation stages rendering (Phase 6.9 part 2)**

---

## STEP 10: Click Accept Button - Scenario A (Valid Patch)

### If Validation PASSED (all green):

**Click "✓ Accept Patch"**

### Expected Behavior - Timeline

```
IMMEDIATELY (1-2 seconds):
- Success notification appears:
  "✓ Patch accepted and applied to the file. (Validation passed)"

- Diff viewer closes
- Validation panel closes

THEN (1-2 seconds):
- Editor refocuses on helpers.py
- File content updates with new docstrings
- You see the cursor at the top of the file

RESULT:
- helpers.py now has docstrings added to split_fullname
- split_fullname function now looks like:

  def split_fullname(fullname: str) -> tuple[str, str]:
      """
      Splits a full name into first and last name.

      Args:
          fullname: Full name string

      Returns:
          tuple: (first_name, last_name)
      """
      parts = fullname.strip().split()
      if len(parts) >= 2:
          return parts[0], ' '.join(parts[1:])
      return fullname, ""
```

**If you see this: ✓ Accept logic works for valid patches (Phase 6.10 part 1)**

---

## STEP 11: Click Accept Button - Scenario B (Invalid Patch)

### If Validation FAILED (red X marks):

**Click "✓ Accept Patch"**

### Expected Behavior - Timeline

```
IMMEDIATELY (<1 second):
⚠ WARNING MODAL APPEARS - looks like this:

┌─────────────────────────────────────────────┐
│ ⚠                                            │
│ Validation failed: 2 error(s), 1 warning(s) │
│ Apply patch anyway?                         │
│                                             │
│  ┌──────────────────┐  ┌──────────────────┐ │
│  │  Yes, Apply      │  │   No, Cancel     │ │
│  └──────────────────┘  └──────────────────┘ │
└─────────────────────────────────────────────┘

- The error and warning counts come from validation panel
- Modal is BLOCKING (you must click a button)
```

### Test Option 1: "Yes, Apply"

```
Click "Yes, Apply":

IMMEDIATELY (1-2 seconds):
- Modal closes
- Success notification:
  "✓ Patch accepted and applied to the file. (Validation had issues, but you confirmed)"

- Diff viewer closes
- helpers.py file updates with the patch (despite warnings)

RESULT:
- File modified with generated code
- User confirmed to override validation failures
```

### Test Option 2: "No, Cancel"

```
Click "No, Cancel":

IMMEDIATELY (<1 second):
- Modal closes
- Info notification appears:
  "Patch application cancelled due to validation failures."

- Diff viewer STAYS OPEN (not closed)
- helpers.py file unchanged

RESULT:
- User can review patch again
- Or click Reject to discard
- File not modified
```

**If you see this: ✓ Accept logic validates before applying (Phase 6.10 part 2)**

---

## STEP 12: View Backend Logs During Validation

### Command

```bash
docker-compose logs backend | tail -50
```

### Expected Output (Examples)

```
backend_1  | INFO:     Received POST /api/v1/generate-patch
backend_1  | INFO:     Starting context retrieval for file: utils/helpers.py
backend_1  | INFO:     Retrieved 3 relevant functions from codebase
backend_1  | INFO:     Calling LLM for code generation...
backend_1  | INFO:     LLM returned 150 tokens
backend_1  | INFO:     Generated code length: 245 characters
backend_1  | INFO:     Starting validation pipeline
backend_1  | INFO:     Running basic syntax check...
backend_1  | INFO:     Syntax check PASSED (0 errors)
backend_1  | INFO:     Running Ruff linting...
backend_1  | INFO:     Ruff found 1 warning: E501 line too long
backend_1  | INFO:     Running Mypy type checking...
backend_1  | INFO:     Mypy check PASSED (0 errors)
backend_1  | INFO:     Test execution disabled (run_tests=false)
backend_1  | INFO:     Validation complete: overall_status=passed
backend_1  | INFO:     Returning response with validation data
```

**If you see this: ✓ Backend validation running (Phase 6.1-6.8)**

---

## STEP 13: Check Extension Console for Integration Logs

### How to Open

```
In Extension Development Host window:
Ctrl+Shift+P → "Toggle Developer Tools"
→ Click "Console" tab
```

### Expected Logs

```
✓ Validation panel created
✓ Panel revealed in ViewColumn.Beside
✓ updateValidationPanel called with validation data
✓ Validation data: {overall_status: "passed", total_errors: 0, ...}
✓ Panel updated successfully
```

### If You See Errors

```
ERROR: Cannot read property 'overall_status' of undefined
→ Validation data not in response
→ Check backend sent validation field

ERROR: validationPanel is undefined
→ Panel failed to create
→ Check WebviewPanel API usage

SYNTAX ERROR in HTML generation
→ Check escapeHtml function
```

**If no errors: ✓ Frontend-backend communication working**

---

## STEP 14: Test Scenario Matrix

### Test #1 - Simple Addition

```
Input: helpers.py with 5 functions
Instruction: "Add docstrings to the split_fullname function"

Expected:
- Split_fullname gets docstring
- Other functions unchanged
- Validation: PASSED (green)
- Accept: Works without warning

Result: ✓ PASS
```

### Test #2 - Type Hints

```
Input: helpers.py with 5 functions
Instruction: "Add return type hints to all functions that are missing them"

Expected:
- Type hints added to relevant functions
- Validation: PASSED or minor warnings
- Accept: Works

Result: ✓ PASS
```

### Test #3 - Poor Quality Code

```
Input: helpers.py
Instruction: "Change all function names to very_long_names_that_exceed_pep8_standards"

Expected:
- Functions renamed (LLM might refuse or do it)
- Validation: FAILED (red X)
- Linting: Shows multiple E501 errors
- Accept: Shows warning modal
- User can accept or cancel

Result: ✓ PASS (validation gate works)
```

---

## Final Success Indicators

### ✓ Everything Working If You See:

1. **Diff appears after generation**
   ✓ Phase 5.10 working

2. **Validation panel appears on right**
   ✓ Phase 6.9 frontend display working

3. **All 4 validation stages render with results**

   ```
   ✓ Syntax Validation
   ✓ Code Linting (Ruff)
   ✓ Type Checking (Mypy)
   ✓ Test Execution (Pytest)
   ```

   ✓ Phase 6.1-6.8 backend validation working

4. **Stages are collapsible (▸ → ▼)**
   ✓ Phase 6.9 interactivity working

5. **Valid patches apply without warning**
   ✓ Phase 6.10 accept gate working

6. **Invalid patches show warning modal**
   ✓ Phase 6.10 validation gate working

7. **File updates after accept**
   ✓ File write permissions working

8. **No console errors**
   ✓ Code quality good

### ✗ Something Wrong If You See:

1. **No validation panel appears**
   → Check docker-compose logs backend
   → Check Extension console for errors
   → Verify repo_path in request

2. **Panel shows but no stages render**
   → Check validation data structure
   → Check JSON parsing in frontend

3. **Accept button doesn't work**
   → Reload extension (Ctrl+R)
   → Check file permissions
   → Check VS Code console for errors

4. **File doesn't update**
   → File might be read-only
   → File might be modified externally
   → Try closing and reopening file

---

## Success Criteria Summary

```
Phase 6 is WORKING if:

□ Validation panel displays          (6.9)
□ All stages show results             (6.1-6.8)
□ Color coding works (green/red)      (6.9)
□ Stages collapsible                  (6.9)
□ Valid patches: no warning           (6.10)
□ Invalid patches: warning shown      (6.10)
□ Can override with confirmation      (6.10)
□ Can cancel patch application        (6.10)
□ File updates correctly              (6.1-6.8, 6.10)
□ No console errors                   (All)

Total Tests Passed: ____ / 10

If ≥9: Phase 6 is READY ✓
If <9: Debug issues from troubleshooting guide
```

---

**Use PHASE6_TESTING_PROCEDURE.md for step-by-step details**
**Use PHASE6_QUICK_CHECKLIST.md for fast reference**
