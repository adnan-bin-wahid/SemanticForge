# Phase 6 Logs - Quick Reference Card

Fast commands to see Phase 6 validation logs

---

## 🎯 Watch Phase 6 Logs Live (RECOMMENDED)

```bash
cd "e:/A A SPL3/SemanticForge/SemanticForge/RepoAlign"
docker-compose logs -f backend
```

Then trigger generation in VS Code and watch logs flow in real-time!

---

## 📺 View Logs by Focus

### See Complete Phase 6 Flow

```bash
docker-compose logs backend | grep "PHASE [5-6]"
```

### See Only Validation Stages

```bash
docker-compose logs backend | grep "PHASE 6\.[1-6]"
```

### See Phase 6.1 (Temporary Environment)

```bash
docker-compose logs backend | grep "PHASE 6.1"
```

### See Phase 6.2 (Ruff Linting)

```bash
docker-compose logs backend | grep "PHASE 6.2"
```

### See Phase 6.3 (Mypy Type Checking)

```bash
docker-compose logs backend | grep "PHASE 6.3"
```

### See Phase 6.4 (Basic Rules)

```bash
docker-compose logs backend | grep "PHASE 6.4"
```

### See Phase 6.5 (Orchestrator/Final Result)

```bash
docker-compose logs backend | grep "PHASE 6.5"
```

### See Passed vs Failed

```bash
docker-compose logs backend | grep "✓\|✗"
```

### See Only Failures

```bash
docker-compose logs backend | grep "✗\|FAILED"
```

### See Only Successes

```bash
docker-compose logs backend | grep "✓\|PASSED"
```

---

## 📊 Get Last 50 Lines

```bash
docker-compose logs backend --tail=50
```

---

## 🔄 Get Real-Time Updates

### Watch logs continuously

```bash
docker-compose logs -f backend
```

### In separate terminal, trigger generation

```bash
# In VS Code: Ctrl+Shift+P → Generate Patch
```

---

## 💾 Save Logs to File

```bash
# Save complete logs
docker-compose logs backend > phase6_logs.txt

# Save only Phase 6
docker-compose logs backend | grep "PHASE [5-6]" > phase6_validation.txt

# Save only failures
docker-compose logs backend | grep "✗\|FAILED" > phase6_failures.txt
```

---

## 🔍 Search in Logs

```bash
# Find a specific error
docker-compose logs backend | grep "error"

# Find status for a specific phase
docker-compose logs backend | grep "PHASE 6.2"

# Find timing info
docker-compose logs backend | grep "time="

# Find all requests
docker-compose logs backend | grep "POST /api/v1"
```

---

## 📈 Count Issues

```bash
# Count failures
docker-compose logs backend | grep -c "✗"

# Count successes
docker-compose logs backend | grep -c "✓"

# Count total phases
docker-compose logs backend | grep -c "PHASE 6"
```

---

## ⚙️ Troubleshooting Commands

```bash
# Check if backend is running
docker-compose ps

# Restart backend with fresh logs
docker-compose down && docker-compose up -d backend

# View only error lines
docker-compose logs backend | grep -i "error"

# View with timestamps
docker-compose logs backend --timestamps
```

---

## 🎯 Expected Log Pattern

When you generate a patch with validation, you should see:

```
========== PHASE 5.6 START: /generate-patch Endpoint Called ==========
[PHASE 5.6] User instruction: ...
...
[PHASE 5.4] ✓ Code generated successfully
[PHASE 5.5] ✓ Diff generated successfully
========== PHASE 6 START: Validation Pipeline ==========
[PHASE 6.1] Sandbox created at: /tmp/repoalign_...
[PHASE 6.4] ✓ Basic rules PASSED
[PHASE 6.2] ✓ Ruff linting PASSED
[PHASE 6.3] ✓ Mypy type check PASSED
[PHASE 6.5] ✓ OVERALL VALIDATION PASSED
========== PHASE 6 END: Validation Complete ==========
HTTP/1.1" 200 OK
```

---

## ✅ If You Don't See Phase 6 Logs

**Check this:**

1. Is backend running? → `docker-compose ps`
2. Did you provide repo_path? → Check extension request
3. Is validation enabled? → Should be true by default
4. Are you watching the right logs? → Use `grep "PHASE 6"`

**Fix it:**

1. Restart: `docker-compose down && docker-compose up -d backend`
2. Check repo_path in extension code
3. Try: `docker-compose logs backend | tail -100`

---

## 🚀 Start Here

```bash
# 1. Go to RepoAlign directory
cd "e:/A A SPL3/SemanticForge/SemanticForge/RepoAlign"

# 2. Watch logs live
docker-compose logs -f backend

# 3. In VS Code (separate terminal or VS Code extension):
# Ctrl+Shift+P → Generate Patch
# Type: Add docstrings to split_fullname
# Press Enter

# 4. Watch logs update with Phase 6 validation!
```

---

**That's it! Now you can see ALL of Phase 6 working in real-time! 🎯**
