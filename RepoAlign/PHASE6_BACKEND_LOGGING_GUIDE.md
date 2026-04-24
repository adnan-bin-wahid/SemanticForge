# Phase 6 Backend Logging Guide

Complete explanation of all logs you should see for each Phase 6 component.

---

## 🎯 Quick Start - See Phase 6 Logs Now

### 1. Watch Backend Logs Live

```bash
cd "e:/A A SPL3/SemanticForge/SemanticForge/RepoAlign"
docker-compose logs -f backend
```

### 2. Generate a Patch with Validation

- In VS Code Extension: Ctrl+Shift+P → "Generate Patch"
- Instruction: "Add docstrings to the split_fullname function"
- Watch the terminal - you'll see Phase 6 logs!

### 3. What You'll See

```
========== PHASE 5.6 START: /generate-patch Endpoint Called ==========
[PHASE 5.6] User instruction: Add docstrings to the split_fullname function...
[PHASE 5.6] File: utils/helpers.py
[PHASE 5.6] Validation enabled: True
========== PHASE 6 START: Validation Pipeline ==========
[PHASE 6.1] Starting validation pipeline for: utils/helpers.py
[PHASE 6.4] ✓ Basic rules PASSED
[PHASE 6.2] ✓ Ruff linting PASSED
[PHASE 6.3] ✓ Mypy type check PASSED
[PHASE 6.5] ✓ OVERALL VALIDATION PASSED
========== PHASE 6 END: Validation Complete ==========
========== PHASE 5.6 END: Response Ready ==========
```

---

## 📋 Phase 6 Log Format Reference

Each Phase 6 component logs in a specific format so you can track execution. Here's what to look for:

---

## Phase 6.1: Temporary Patch Application

### What It Does

- Creates temporary sandbox directory
- Copies repository to temp location
- Writes generated code to temp file

### Expected Logs

```
[PHASE 6.1] Starting validation pipeline for: utils/helpers.py
[PHASE 6.1] Original file path: /app/test-project/utils/helpers.py
[PHASE 6.1] Creating temporary sandbox environment...
[PHASE 6.1] Sandbox created at: /tmp/repoalign_xyz123abc
[PHASE 6.1] Patched file copied to: /tmp/repoalign_xyz123abc/utils/helpers.py
```

### What Success Looks Like

```
✓ Lines appear in order
✓ Temporary directory path is shown
✓ File is copied successfully
```

### What Failure Looks Like

```
✗ Error creating temporary directory
✗ Permission denied
✗ Disk space issues
```

---

## Phase 6.2: Ruff Linting Integration

### What It Does

- Runs Ruff linter on patched code
- Checks code style, complexity, errors
- Captures linting violations

### Expected Logs

#### When Linting Passes (No Issues)

```
[PHASE 6.2] Starting Ruff code linting check...
[PHASE 6.2] ✓ Ruff linting PASSED (0 errors, 0 warnings)
```

#### When Linting Finds Issues

```
[PHASE 6.2] Starting Ruff code linting check...
[PHASE 6.2] ✗ Ruff linting FAILED (2 errors, 3 warnings)
[PHASE 6.2] Summary: Line 45: F841 local variable assigned but never used
```

### Common Ruff Issues

- F841: Local variable assigned but never used
- E501: Line too long
- W293: Blank line with whitespace
- E701: Multiple statements on one line

### What Success Looks Like

```
✓ "✓ Ruff linting PASSED" message
✓ Shows (0 errors, X warnings) or (X errors, 0 warnings)
```

### What Failure Looks Like

```
✗ "✗ Ruff linting FAILED"
✗ Shows specific linting violations with line numbers
```

---

## Phase 6.3: Mypy Type Checking

### What It Does

- Runs Mypy type checker
- Validates type annotations
- Detects type inconsistencies

### Expected Logs

#### When Type Checking Passes

```
[PHASE 6.3] Starting Mypy type checking...
[PHASE 6.3] ✓ Mypy type check PASSED (0 errors, 0 warnings)
```

#### When Type Checking Finds Issues

```
[PHASE 6.3] Starting Mypy type checking...
[PHASE 6.3] ✗ Mypy type check FAILED (1 errors, 2 warnings)
[PHASE 6.3] Summary: line 25: error: Argument 1 to "func" has incompatible type
```

### Common Mypy Errors

- Incompatible return type
- Incompatible argument type
- Missing type annotation
- Name not defined

### What Success Looks Like

```
✓ "✓ Mypy type check PASSED" message
✓ No errors shown
```

### What Failure Looks Like

```
✗ "✗ Mypy type check FAILED"
✗ Shows specific type errors with line numbers
```

---

## Phase 6.4: Basic Rules Checker (Syntax Validation)

### What It Does

- Parses code with AST
- Checks basic Python syntax
- Fastest validation stage

### Expected Logs

#### When Syntax is Valid

```
[PHASE 6.4] Starting basic syntax rules check...
[PHASE 6.4] ✓ Basic rules PASSED (0 errors, 0 warnings)
```

#### When Syntax is Invalid

```
[PHASE 6.4] Starting basic syntax rules check...
[PHASE 6.4] ✗ Basic rules FAILED (1 errors, 0 warnings)
[PHASE 6.4] Summary: SyntaxError: invalid syntax at line 15
```

### What Success Looks Like

```
✓ Appears before other validation stages
✓ "✓ Basic rules PASSED" message
✓ 0 errors (warnings might be OK)
```

### What Failure Looks Like

```
✗ "✗ Basic rules FAILED"
✗ Shows SyntaxError details
✗ Pipeline might stop here (if not continue_on_errors)
```

---

## Phase 6.5: Constraint Checker Service (Orchestrator)

### What It Does

- Orchestrates all validation stages (6.1-6.4)
- Aggregates results
- Calculates overall status

### Expected Logs

#### When All Validations Pass

```
[PHASE 6.5] Finalizing constraint checker report...
[PHASE 6.5] ✓ OVERALL VALIDATION PASSED - All checks successful
[PHASE 6.5] Stages passed: basic_rules, ruff, mypy
[PHASE 6.5] Report summary: Syntax OK, No linting issues, Type checking passed
```

#### When Some Validations Fail

```
[PHASE 6.5] Finalizing constraint checker report...
[PHASE 6.5] ✗ OVERALL VALIDATION FAILED
[PHASE 6.5] Stages passed: basic_rules, ruff
[PHASE 6.5] Stages failed: mypy
[PHASE 6.5] Total issues: 2 errors, 1 warnings
```

#### Cleanup After

```
[PHASE 6.1] Cleaning up temporary sandbox: /tmp/repoalign_xyz123abc
```

### What Success Looks Like

```
✓ "✓ OVERALL VALIDATION PASSED" message
✓ All stages listed in "Stages passed"
✓ Cleanup message at end
```

### What Failure Looks Like

```
✗ "✗ OVERALL VALIDATION FAILED" message
✗ Failed stages listed in "Stages failed"
✗ Error counts shown
```

---

## Phase 6.6: Test Execution (Optional)

### What It Does

- Runs pytest suite (if enabled)
- Executes project tests
- Reports test results

### Expected Logs

#### When run_tests=False (Default)

```
[PHASE 6.6] Test execution skipped (run_tests=false)
```

#### When Tests Pass

```
[PHASE 6.6] Starting test execution runner (Pytest)...
[PHASE 6.6] ✓ Test execution completed
[PHASE 6.6] Result: passed
```

#### When Tests Fail

```
[PHASE 6.6] Starting test execution runner (Pytest)...
[PHASE 6.6] ✓ Test execution completed
[PHASE 6.6] Result: failed
[PHASE 6.6] Test execution failed: 2 tests failed, 3 errors
```

### What Success Looks Like

```
✓ Shows if tests were run or skipped
✓ Shows "Result: passed" or "Result: failed"
```

---

## Phase 6.7: Validation Endpoint

### What It Does

- Provides REST API endpoint for validation
- Can be called standalone
- Returns comprehensive validation report

### Expected Endpoint Response

```json
POST /api/v1/validate-patch

Response:
{
  "status": "success",
  "validation_report": {
    "overall_status": "passed|failed",
    "constraint_check": {...},
    "test_results": {...},
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

## Phase 6.8: Auto-Validation Integration

### What It Does

- Automatically validates during /generate-patch
- Returns validation in response
- Integrated with frontend

### Expected Logs

```
[PHASE 6.8] Building validation stages for frontend display...
[PHASE 6.8] ✓ VALIDATION PASSED - All checks successful
```

or

```
[PHASE 6.8] Building validation stages for frontend display...
[PHASE 6.8] ✗ VALIDATION FAILED - 2 static analysis error(s), 1 warning(s)
```

---

## Phase 6.9: Frontend Validation Panel Display

### What It Does

- Frontend receives validation data
- Displays panel with results
- Shows collapsible stages

### Expected Frontend Logs (Ctrl+Shift+J)

```
[INFO] Validation panel created
[INFO] updateValidationPanel called
[INFO] Panel HTML generated with 4 stages
[INFO] Panel updated successfully
```

---

## Phase 6.10: Accept Logic Validation Gate

### What It Does

- Checks validation status before accept
- Shows warning for invalid patches
- Prevents applying bad patches

### Expected Frontend Logs

#### Valid Patch (Fast Accept)

```
[INFO] Checking validation status before accept
[INFO] Validation passed - applying patch
[INFO] Workspace edit succeeded
[INFO] File updated
```

#### Invalid Patch (Warning Modal)

```
[WARNING] Validation failed - showing warning modal
[WARNING] 2 errors, 1 warning found
[INFO] User chose: Yes, Apply (or No, Cancel)
```

---

## 🔍 Complete Example: Successful Generation with Validation

Here's what a complete successful flow looks like in the logs:

```
========== PHASE 5.6 START: /generate-patch Endpoint Called ==========
[PHASE 5.6] User instruction: Add docstrings to the split_fullname function...
[PHASE 5.6] File: utils/helpers.py
[PHASE 5.6] Context limit: 10
[PHASE 5.6] Validation enabled: True

[PHASE 5.4] Calling LLM CodeGenerator service...
[PHASE 5.4] ✓ Code generated successfully (1245 bytes)

[PHASE 5.5] Generating unified diff...
[PHASE 5.5] ✓ Diff generated successfully

[PHASE 5.5] Calculating diff statistics...
[PHASE 5.5] ✓ Stats: +12 -3 (95.2% similar)

========== PHASE 6 START: Validation Pipeline ==========
[PHASE 6] Repository path: /app/test-project
[PHASE 6] File relative path: utils/helpers.py

[PHASE 6.5] Starting constraint checker service (orchestrator)...
[PHASE 6.1] Starting validation pipeline for: utils/helpers.py
[PHASE 6.1] Original file path: /app/test-project/utils/helpers.py
[PHASE 6.1] Creating temporary sandbox environment...
[PHASE 6.1] Sandbox created at: /tmp/repoalign_abc123def
[PHASE 6.1] Patched file copied to: /tmp/repoalign_abc123def/utils/helpers.py

[PHASE 6.4] Starting basic syntax rules check...
[PHASE 6.4] ✓ Basic rules PASSED (0 errors, 0 warnings)

[PHASE 6.2] Starting Ruff code linting check...
[PHASE 6.2] ✓ Ruff linting PASSED (0 errors, 0 warnings)

[PHASE 6.3] Starting Mypy type checking...
[PHASE 6.3] ✓ Mypy type check PASSED (0 errors, 0 warnings)

[PHASE 6.5] Finalizing constraint checker report...
[PHASE 6.5] ✓ OVERALL VALIDATION PASSED - All checks successful
[PHASE 6.5] Stages passed: basic_rules, ruff, mypy
[PHASE 6.5] Report summary: ✓ Validation passed for utils/helpers.py

[PHASE 6.5] ✓ Constraint checker completed
[PHASE 6.5] Overall result: PASSED
[PHASE 6.5] Errors: 0, Warnings: 0

[PHASE 6.6] Test execution skipped (run_tests=false)

[PHASE 6.8] Building validation stages for frontend display...
[PHASE 6.8] ✓ VALIDATION PASSED - All checks successful

[PHASE 6.1] Cleaning up temporary sandbox: /tmp/repoalign_abc123def

========== PHASE 6 END: Validation Complete ==========

[PHASE 5.6] ✓ /generate-patch endpoint returning response
========== PHASE 5.6 END: Response Ready ==========

INFO:     172.18.0.1:45678 - "POST /api/v1/generate-patch HTTP/1.1" 200 OK
```

---

## ❌ Complete Example: Failed Validation

Here's what a failed validation looks like:

```
========== PHASE 5.6 START: /generate-patch Endpoint Called ==========
[PHASE 5.6] User instruction: Add docstrings to the split_fullname function...
[PHASE 5.6] File: utils/helpers.py
[PHASE 5.6] Validation enabled: True

[PHASE 5.4] Calling LLM CodeGenerator service...
[PHASE 5.4] ✓ Code generated successfully (1580 bytes)

[PHASE 5.5] Generating unified diff...
[PHASE 5.5] ✓ Diff generated successfully

[PHASE 5.5] Calculating diff statistics...
[PHASE 5.5] ✓ Stats: +18 -2 (92.1% similar)

========== PHASE 6 START: Validation Pipeline ==========
[PHASE 6] Repository path: /app/test-project
[PHASE 6] File relative path: utils/helpers.py

[PHASE 6.5] Starting constraint checker service (orchestrator)...
[PHASE 6.1] Starting validation pipeline for: utils/helpers.py
[PHASE 6.1] Sandbox created at: /tmp/repoalign_xyz789

[PHASE 6.4] Starting basic syntax rules check...
[PHASE 6.4] ✓ Basic rules PASSED (0 errors, 0 warnings)

[PHASE 6.2] Starting Ruff code linting check...
[PHASE 6.2] ✗ Ruff linting FAILED (1 errors, 2 warnings)
[PHASE 6.2] Summary: Line 45: E501 line too long (89 > 88 characters)
[PHASE 6.2] Summary: Line 50: W293 blank line contains whitespace

[PHASE 6.3] Starting Mypy type checking...
[PHASE 6.3] ✓ Mypy type check PASSED (0 errors, 0 warnings)

[PHASE 6.5] Finalizing constraint checker report...
[PHASE 6.5] ✗ OVERALL VALIDATION FAILED
[PHASE 6.5] Stages passed: basic_rules, mypy
[PHASE 6.5] Stages failed: ruff
[PHASE 6.5] Total issues: 1 errors, 2 warnings

[PHASE 6.5] ✓ Constraint checker completed
[PHASE 6.5] Overall result: FAILED
[PHASE 6.5] Errors: 1, Warnings: 2

[PHASE 6.6] Test execution skipped (run_tests=false)

[PHASE 6.8] Building validation stages for frontend display...
[PHASE 6.8] ✗ VALIDATION FAILED - 1 static analysis error(s), 2 warning(s)

[PHASE 6.1] Cleaning up temporary sandbox: /tmp/repoalign_xyz789

========== PHASE 6 END: Validation Complete ==========

[PHASE 5.6] ✓ /generate-patch endpoint returning response
========== PHASE 5.6 END: Response Ready ==========

INFO:     172.18.0.1:45678 - "POST /api/v1/generate-patch HTTP/1.1" 200 OK
```

---

## 🎯 Logging Level Reference

### Log Levels You'll See

```
INFO    - Normal flow, important checkpoints
WARNING - Issues found but non-critical
ERROR   - Critical failures
```

### Color Coding (if available)

```
[PHASE X.Y] ✓ = Green (success)
[PHASE X.Y] ✗ = Red (failure)
[PHASE X.Y] = Blue (info)
```

---

## 📊 Log Filtering for Specific Phases

### See Only Phase 6.1 Logs

```bash
docker-compose logs backend | grep "PHASE 6.1"
```

### See Only Validation Failures

```bash
docker-compose logs backend | grep "✗\|FAILED"
```

### See Specific Phase Results

```bash
docker-compose logs backend | grep "PHASE 6\.[2-3]"
```

### See Complete Validation Flow

```bash
docker-compose logs backend | grep "PHASE 6"
```

### See All Phases 5 & 6

```bash
docker-compose logs backend | grep "PHASE [5-6]"
```

---

## 🔧 Troubleshooting by Logs

### Problem: No Phase 6 logs appear

**Check:**

- Is validation enabled? Look for `[PHASE 6] Validation enabled: True`
- Is repo_path provided? Look for `[PHASE 6] Repository path: ...`
- Is temporary directory created? Look for `[PHASE 6.1] Sandbox created at:`

**Fix:**

- Ensure repo_path is in the request
- Check repo_path actually exists
- Check file permissions

### Problem: Validation appears but no detail logs

**Check:**

- Are stages showing? Look for `[PHASE 6.4]`, `[PHASE 6.2]`, `[PHASE 6.3]`
- Are stages passing/failing? Look for `✓` or `✗`

**Fix:**

- Check generated code for actual issues
- Try simpler instruction
- Verify Ruff/Mypy are working

### Problem: Only some stages show logs

**Check:**

- Pipeline might have stopped early
- Look for `Stopping validation - X failed`

**Fix:**

- Check error messages from failed stage
- Review generated code quality
- May need to fix actual code issues

---

## ✅ Success Checklist

### You're Good If You See:

- [x] `========== PHASE 5.6 START ==========`
- [x] `[PHASE 5.4] ✓ Code generated successfully`
- [x] `[PHASE 5.5] ✓ Diff generated successfully`
- [x] `========== PHASE 6 START ==========`
- [x] `[PHASE 6.1] Sandbox created at:`
- [x] `[PHASE 6.4] ✓ Basic rules PASSED`
- [x] `[PHASE 6.2] ✓ Ruff linting PASSED` (or FAILED if has issues)
- [x] `[PHASE 6.3] ✓ Mypy type check PASSED` (or FAILED if has issues)
- [x] `[PHASE 6.5] OVERALL VALIDATION PASSED` (or FAILED)
- [x] `[PHASE 6.1] Cleaning up temporary sandbox`
- [x] `========== PHASE 6 END ==========`
- [x] `HTTP/1.1" 200 OK` at the end

---

## 🚀 Next Steps

### Run a Test Now

1. Watch logs: `docker-compose logs -f backend`
2. Generate patch in VS Code extension
3. See all Phase 6 logs in real-time!

### Validate Everything Works

- [x] See Phase 6.1 sandbox creation
- [x] See Phase 6.2-6.4 validation stages
- [x] See Phase 6.5 overall result
- [x] See Phase 6.8 integration
- [x] Frontend receives validation data

### Check Frontend

- [x] Validation panel appears
- [x] Stages render correctly
- [x] Accept logic checks validation status

---

**Now you can see EXACTLY what Phase 6 is doing! 🎯**

Generate a patch and watch the logs!
