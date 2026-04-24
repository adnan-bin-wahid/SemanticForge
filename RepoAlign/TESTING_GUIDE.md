# Phase 6 Validation Layer - Testing & Deployment Guide

## Prerequisites for Testing

### Backend Requirements

- Docker and Docker Compose installed, OR
- Python 3.11+, Neo4j, Qdrant, and Ollama running locally
- Backend API accessible at `http://localhost:8000`

### Frontend Requirements

- VS Code with extension compiled
- Node.js 18+ (for extension development)
- Python file open for testing

### Environment Setup

#### Option 1: Docker (Recommended)

```bash
cd RepoAlign
docker-compose up -d

# Verify services
curl http://localhost:8000/api/v1/health
curl http://localhost:11434/api/tags
curl http://localhost:6333/health
```

#### Option 2: Local Setup

```bash
# Backend
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload

# In separate terminals:
# Neo4j, Qdrant, and Ollama should be running
```

### Extension Setup

```bash
cd frontend
npm install
npm run compile

# In VS Code:
# Open folder as extension workspace
# F5 or Run → Start Debugging
```

## Testing Procedures

### Test 1: Validation Panel - Successful Validation

**Setup:**

1. Create test file: `test_valid.py`

   ```python
   def add(a: int, b: int) -> int:
       """Add two numbers."""
       return a + b
   ```

2. Open file in VS Code extension

**Test Steps:**

1. Press `Ctrl+Shift+P` → Run "RepoAlign: Generate Patch"
2. Enter instruction: "Add error handling and logging"
3. Wait for patch generation (2-5 minutes with tinyllama)

**Expected Results:**

- ✅ Diff view appears
- ✅ Validation panel appears beside diff
- ✅ Panel shows "✓ Validation Passed" (green header)
- ✅ All stages show green checkmarks
- ✅ Error count: 0, Warning count: 0

**Validation:**

- [ ] Panel displays without errors
- [ ] Color coding is green
- [ ] All stages show passed status
- [ ] Click Accept directly applies patch (no warning)

### Test 2: Validation Panel - Failed Validation

**Setup:**

1. Create test file: `test_invalid.py`

   ```python
   def function_with_very_long_name_that_violates_pep8_line_length_limit_standards_and_conventions():
       pass
   ```

2. Open file in VS Code extension

**Test Steps:**

1. Run "RepoAlign: Generate Patch"
2. Enter instruction: "Improve this function"
3. Wait for generation

**Expected Results:**

- ✅ Diff view appears
- ✅ Validation panel shows "✗ Validation Failed" (red header)
- ✅ At least one stage shows red X
- ✅ Error or warning count > 0
- ✅ Issues list visible with details

**Validation:**

- [ ] Panel displays with red status
- [ ] Issues are listed with line numbers
- [ ] Clicking Accept shows warning modal
- [ ] Warning shows error/warning counts

### Test 3: Accept with Validation Failed - User Confirms

**Setup:**
Use same file as Test 2 with failed validation

**Test Steps:**

1. Generate patch (validation should fail)
2. Click "Accept Patch" in quick pick
3. When warning appears: "⚠ Validation failed: N error(s). Apply anyway?"
4. Click "Yes, Apply"

**Expected Results:**

- ✅ Warning modal appears with validation status
- ✅ Patch applies despite warnings
- ✅ Success message: "✓ Patch accepted... (Validation had issues, but you confirmed)"
- ✅ File updated with generated code
- ✅ Diff view closes

**Validation:**

- [ ] Warning modal shows correct error/warning counts
- [ ] Both modal buttons work
- [ ] File content updates correctly
- [ ] Focus returns to editor

### Test 4: Accept with Validation Failed - User Cancels

**Setup:**
Use same file as Test 2 with failed validation

**Test Steps:**

1. Generate patch (validation should fail)
2. Click "Accept Patch" in quick pick
3. When warning appears
4. Click "No, Cancel"

**Expected Results:**

- ✅ Warning modal appears
- ✅ Patch NOT applied
- ✅ File content unchanged
- ✅ Diff view still open
- ✅ Information message: "Patch application cancelled..."

**Validation:**

- [ ] Diff view remains open
- [ ] Original file unchanged
- [ ] User can review again or click Reject

### Test 5: Panel Interaction - Expand/Collapse Stages

**Setup:**
Generate patch with validation results (either passing or failing)

**Test Steps:**

1. Look at validation panel
2. Click on stage headers (e.g., "▸ Code Linting (Ruff)")
3. Verify stage body appears/disappears
4. Click multiple times to verify toggle works

**Expected Results:**

- ✅ Clicking stage header expands/collapses body
- ✅ Arrow icon rotates (▸ → ▼)
- ✅ Issues/content visible when expanded
- ✅ Issues/content hidden when collapsed
- ✅ Smooth CSS transitions

**Validation:**

- [ ] All stages can be toggled
- [ ] Arrow icon rotates correctly
- [ ] Content shows/hides smoothly
- [ ] No JavaScript errors in console

### Test 6: Backward Compatibility - No Validation

**Setup:**
Temporarily modify extension to not send repo_path

**Test Steps:**

1. In `extension.ts`, comment out repo_path in request
2. Recompile: `npm run compile`
3. Reload VS Code extension
4. Generate patch

**Expected Results:**

- ✅ Patch generates successfully
- ✅ Diff view shows
- ✅ Validation panel shows empty message: "⏳ Validation data will appear here..."
- ✅ Accept/Reject works normally
- ✅ Patch applies without validation gate

**Validation:**

- [ ] No errors in console
- [ ] System handles missing validation gracefully
- [ ] Backward compatible

### Test 7: Edge Cases

#### Test 7a: Syntax Error in Generated Code

**Expected:** Syntax validation stage shows red X, issue listed

#### Test 7b: Lint Warnings

**Expected:** Linting stage shows issue with yellow/orange coloring

#### Test 7c: Type Annotation Errors

**Expected:** Type checking stage shows red X with mypy error details

#### Test 7d: Large File (>1000 lines)

**Expected:** Panel renders correctly, no performance issues

#### Test 7e: Multiple Issues in One Stage

**Expected:** All issues listed with proper formatting

## Performance Testing

### Response Times

- [ ] Patch generation: 2-5 minutes (expected with tinyllama)
- [ ] Validation: <30 seconds for typical files
- [ ] Panel render: <500ms
- [ ] Panel interaction: Instant (no lag on click)

### Resource Usage

- [ ] No memory leaks after multiple patch generations
- [ ] Panel reuse doesn't accumulate memory
- [ ] No excessive DOM operations

## Known Issues & Workarounds

### Issue 1: Backend Connection Failed

**Symptom:** "Failed to generate code patch"
**Cause:** Backend not running
**Fix:** Start Docker Compose or backend service

### Issue 2: Panel Not Showing

**Symptom:** Diff appears but no panel visible
**Cause:** Validation data is null or backend error
**Fix:** Check browser console for errors

### Issue 3: Accept Button Unresponsive

**Symptom:** No quick pick appears after patch generation
**Cause:** Extension not properly reloaded
**Fix:** Reload VS Code window (Ctrl+R)

### Issue 4: Timeout Error

**Symptom:** "Request timeout" after 6+ minutes
**Cause:** LLM inference taking longer than timeout
**Fix:** Increase axios timeout in extension.ts (currently 330s)

## Verification Checklist

### Code Quality

- [x] TypeScript compilation: 0 errors
- [x] No console errors on startup
- [x] Proper error handling for edge cases
- [x] HTML escaping prevents XSS
- [ ] Unit tests for validation panel (optional)
- [ ] Integration tests for full workflow (optional)

### Functionality

- [ ] Panel creates and displays correctly
- [ ] All validation stages render
- [ ] Issues display with correct line numbers
- [ ] Color coding reflects status accurately
- [ ] Accept gate prevents invalid patches
- [ ] Warning modal appears for failed validation
- [ ] Panel reuses between generations
- [ ] Backward compatibility maintained

### User Experience

- [ ] Panel styled consistently with VSCode theme
- [ ] No broken layouts on different panel sizes
- [ ] Stages collapsible and interactive
- [ ] Success/error messages are clear
- [ ] Modal dialog is prominent and clear

### Documentation

- [x] Architecture documented
- [x] API contracts documented
- [x] Testing guide provided
- [x] Deployment guide provided
- [ ] User-facing documentation (optional)

## Deployment Steps

### 1. Pre-Deployment

```bash
# Verify compilation
npm run compile

# Run linter
npm run lint

# Run tests (if added)
npm run test
```

### 2. Build Extension

```bash
# Create production build
vsce package

# Or use specific version
vsce package --out repoalign-0.0.1.vsix
```

### 3. Install Extension

```bash
# Option A: Install from VSIX
code --install-extension repoalign-0.0.1.vsix

# Option B: Publish to marketplace
vsce publish
```

### 4. Deploy Backend

```bash
# Using Docker (recommended)
docker-compose up -d

# Or deploy to cloud provider
# (follow cloud provider docs)
```

### 5. Verify Deployment

```bash
# Test backend health
curl http://localhost:8000/api/v1/health

# Open VS Code
# Test extension with sample file
# Verify all test scenarios pass
```

## Next Phase: Phase 7 - Dynamic Analysis

Once Phase 6 testing is complete:

1. **Start Phase 7 Planning**
   - Define dynamic analysis requirements
   - Design runtime profiling approach
   - Plan integration with existing system

2. **Implementation Outline**
   - Add runtime monitoring to patch execution
   - Capture performance metrics
   - Display analysis results

3. **Integration**
   - Add dynamic analysis to validation pipeline
   - Update panel with performance data
   - Enhance reporting

## Support & Troubleshooting

### Debug Logging

Enable verbose logging:

```typescript
// In extension.ts
console.log("Validation panel:", validationPanel);
console.log("Validation data:", result.validation);
```

### Panel HTML Debugging

View generated HTML:

1. Right-click in panel
2. Inspect element
3. Check webview HTML structure

### Backend Debugging

```bash
# Check backend logs
docker-compose logs -f backend

# Or if running locally
# View console output from uvicorn
```

### Performance Profiling

1. Open Chrome DevTools in extension host
2. Check panel rendering time
3. Look for memory issues
4. Profile panel interactions

## Success Criteria

Phase 6.9-6.10 is successfully complete when:

✅ Validation panel displays patch quality issues before acceptance
✅ User receives clear feedback on syntax errors, lint warnings, type errors
✅ Invalid patches require user confirmation before application
✅ All color coding and UI elements work correctly
✅ System gracefully handles missing validation data
✅ Backward compatibility maintained
✅ TypeScript compilation succeeds with 0 errors
✅ End-to-end workflow tested and verified

## Timeline

| Task                                | Estimated Time  |
| ----------------------------------- | --------------- |
| Environment setup                   | 15-30 min       |
| Test 1-4 (basic tests)              | 30-45 min       |
| Test 5-7 (interaction & edge cases) | 30-60 min       |
| Performance testing                 | 15-30 min       |
| Issue resolution                    | As needed       |
| **Total**                           | **1.5-3 hours** |

## Final Notes

- All code has been implemented and compiled successfully
- No TypeScript errors encountered
- Panel integration is complete
- Validation gate in accept logic is implemented
- System is ready for end-to-end testing
- Documentation is comprehensive

The validation layer represents a significant step toward production-ready patch generation with confidence-building feedback to users.
