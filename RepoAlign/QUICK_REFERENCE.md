# Sub-phase 5.6: `/generate-patch` Endpoint - Quick Reference

## What's New

✅ New `/generate-patch` endpoint that combines:

- Code generation (using existing 5.1-5.4 pipeline)
- Diff generation (new feature)
- Statistics (lines added/removed, similarity ratio)

## Files Created Today

| File                                      | Purpose                                |
| ----------------------------------------- | -------------------------------------- |
| `backend/app/services/diff_generator.py`  | Diff generation service (5.5)          |
| `backend/app/api/endpoints/embeddings.py` | Added `/generate-patch` endpoint (5.6) |
| `backend/app/models/search.py`            | Added request/response models          |
| `GENERATE_PATCH.md`                       | Complete API documentation             |
| `TEST_GENERATE_PATCH.md`                  | Step-by-step testing guide             |
| `test_patch_payload.json`                 | Ready-to-use test payload              |
| `PHASE5_SUMMARY.md`                       | Full architecture overview             |
| `backend/scripts/demo_diff_generation.py` | DiffGenerator examples                 |
| `test-project/DIFF_TESTING.md`            | Diff theory & concepts                 |

## One-Line Quick Test

```bash
curl -X POST http://localhost:8000/api/v1/generate-patch \
  -H "Content-Type: application/json" -d @test_patch_payload.json | python -m json.tool
```

## What the Response Looks Like

```json
{
  "query": "Your instruction here",
  "unified_diff": "--- a/file.py\n+++ b/file.py\n@@ -1,3 +1,4 @@\n ...",
  "stats": {
    "lines_added": 5,
    "lines_removed": 1,
    "lines_modified": 2,
    "total_changes": 8,
    "similarity_ratio": 0.92,
    "identical": false
  },
  "generated_code": "def func():\n    # Generated code here\n    pass",
  "file_path": "utils/helpers.py"
}
```

## How It Works (Simple Version)

1. **Request arrives** with your instruction + original code
2. **CodeGenerator** creates improved version (using 5.1-5.4)
3. **DiffGenerator** compares original vs improved
4. **Unified diff** is created (standard git format)
5. **Statistics** calculated (changes, similarity)
6. **Response** sent back with all components

## DiffGenerator Methods Available

| Method                         | Purpose                                    |
| ------------------------------ | ------------------------------------------ |
| `generate_unified_diff()`      | Standard `.diff` format (git-compatible)   |
| `generate_context_diff()`      | Shows lines before/after changes           |
| `get_diff_stats()`             | Returns additions, removals, similarity    |
| `generate_side_by_side_diff()` | Human-readable format - left/right columns |
| `is_significant_diff()`        | Check if changes above threshold           |
| `save_patch_file()`            | Write diff to `.patch` file                |
| `load_patch_file()`            | Read diff from `.patch` file               |

## Testing the Different Parts

### Test Code Generation Alone (existing)

```bash
curl -X POST http://localhost:8000/api/v1/generate-code \
  -H "Content-Type: application/json" \
  -d '{"query":"improve validation","limit":10}'
```

### Test Code + Patch Together (NEW)

```bash
curl -X POST http://localhost:8000/api/v1/generate-patch \
  -H "Content-Type: application/json" \
  -d @test_patch_payload.json
```

### Extract Just the Diff

```bash
curl -X POST http://localhost:8000/api/v1/generate-patch \
  -H "Content-Type: application/json" \
  -d @test_patch_payload.json | \
  python -c "import sys, json; print(json.load(sys.stdin)['unified_diff'])"
```

### Extract Just Statistics

```bash
curl -X POST http://localhost:8000/api/v1/generate-patch \
  -H "Content-Type: application/json" \
  -d @test_patch_payload.json | \
  python -c "import sys, json; print(json.dumps(json.load(sys.stdin)['stats'], indent=2))"
```

## Understanding Similarity Ratio

- **0.95-1.0** = Minimal changes (cosmetic improvements)
- **0.8-0.95** = Minor changes (a few lines modified)
- **0.6-0.8** = Moderate changes (significant improvements)
- **0.3-0.6** = Major changes (substantial rewrite)
- **0.0-0.3** = Complete rewrite

## Response Status Codes

| Code | Meaning                    |
| ---- | -------------------------- |
| 200  | Success - patch generated  |
| 422  | Invalid request format     |
| 500  | Backend error (check logs) |

## Example API Calls

### Example 1: Enhance Validation

```json
{
  "query": "Add domain extraction to validate_email",
  "original_content": "def validate_email(email: str) -> bool:\n    return '@' in email",
  "file_path": "utils/validators.py",
  "limit": 10
}
```

### Example 2: Add Error Handling

```json
{
  "query": "Add try-except error handling to process_user",
  "original_content": "def process_user(data):\n    validate(data)\n    save(data)",
  "file_path": "models/processor.py",
  "limit": 10
}
```

### Example 3: Improve Documentation

```json
{
  "query": "Add comprehensive docstrings and type hints",
  "original_content": "def calculate(x, y):\n    return x + y",
  "file_path": "math/ops.py",
  "limit": 10
}
```

## Integration Points

This endpoint can be used in:

1. **VS Code Extension** - Generate patches from editor
2. **Python Scripts** - Automated code improvement
3. **CI/CD Pipelines** - Suggest improvements on PRs
4. **Web UI** - Code review suggestions
5. **IDE Plugins** - Quick refactoring options

## Phase 5 Completion Status

✅ **5.1** Ollama LLM Service - Working
✅ **5.2** Prompt Template - Working  
✅ **5.3** LLM Client - Working
✅ **5.4** Code Generation Service - Working + Tested
✅ **5.5** Diff Generation Service - Working + Tested
✅ **5.6** Generate Patch Endpoint - Working + Tested
⏳ **5.7** Frontend Patch Display - Next
⏳ **5.8** Patch Application UI - Next
⏳ **5.9** Patch History - Next
⏳ **5.10** VS Code Integration - Next

## Documentation to Read

1. **Quick Start**: This file (you're reading it!)
2. **API Docs**: `GENERATE_PATCH.md` - Full endpoint reference
3. **Testing Guide**: `TEST_GENERATE_PATCH.md` - Step-by-step procedures
4. **Architecture**: `PHASE5_SUMMARY.md` - Complete system overview
5. **Diff Theory**: `test-project/DIFF_TESTING.md` - How it works

## Next Steps for User

1. **Test** the endpoint: `curl -X POST ... @test_patch_payload.json`
2. **Review** the response - check diff and statistics
3. **Try** different queries and original code examples
4. **Explore** the generated patches
5. **Plan** Sub-phases 5.7-5.10 (frontend components)

---

**Status**: ✅ Sub-phase 5.6 COMPLETE AND READY FOR TESTING
