# Phase 5.6: Testing `/generate-patch` Endpoint

## Quick Start Test

Use the pre-configured test payload:

```bash
curl -X POST http://localhost:8000/api/v1/generate-patch \
  -H "Content-Type: application/json" \
  -d @test_patch_payload.json | python -m json.tool
```

## What to Expect

You should see a response like:

```json
{
  "query": "Enhance the validate_email function to extract and return the domain part...",
  "unified_diff": "--- a/test-project/utils/helpers.py\n+++ b/test-project/utils/helpers.py\n@@ -1,6 +1,20 @@\n ...",
  "stats": {
    "lines_added": 5,
    "lines_removed": 0,
    "lines_modified": 1,
    "total_changes": 6,
    "similarity_ratio": 0.9234,
    "identical": false
  },
  "generated_code": "import re\nfrom typing import List, Tuple, Optional\n\ndef format_greeting(name: str) -> str:\n    ...",
  "file_path": "test-project/utils/helpers.py"
}
```

## Step-by-Step Testing

### Step 1: Verify Backend is Running

```bash
curl http://localhost:8000/api/v1/health
```

Expected response: `{"status":"ok"}`

### Step 2: Verify Code Indexing

First, make sure the code has been indexed for context retrieval:

```bash
curl -X POST http://localhost:8000/api/v1/index-embeddings
```

Expected response: Indexing statistics with created embeddings

### Step 3: Test `/generate-patch` Endpoint

**Option A: Using curl with pre-made payload**

```bash
curl -X POST http://localhost:8000/api/v1/generate-patch \
  -H "Content-Type: application/json" \
  -d @test_patch_payload.json | python -m json.tool
```

**Option B: Using curl with inline JSON**

```bash
curl -X POST http://localhost:8000/api/v1/generate-patch \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Add error handling to the validate_email function",
    "original_content": "def validate_email(email: str) -> bool:\n    pattern = r'"'"'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'"'"'\n    return re.match(pattern, email) is not None",
    "file_path": "utils/helpers.py",
    "limit": 10
  }' | python -m json.tool
```

**Option C: Using Python script**

```python
import requests
import json

# Prepare the request
payload = {
    "query": "Add domain extraction to validate_email",
    "original_content": open("test-project/utils/helpers.py").read(),
    "file_path": "test-project/utils/helpers.py",
    "limit": 10
}

# Call the endpoint
response = requests.post(
    "http://localhost:8000/api/v1/generate-patch",
    json=payload
)

# Show the result
result = response.json()
print(json.dumps(result, indent=2))
```

### Step 4: Inspect the Response

Extract specific parts of the response:

**View the generated diff:**
```bash
curl -X POST http://localhost:8000/api/v1/generate-patch \
  -H "Content-Type: application/json" \
  -d @test_patch_payload.json | \
  python -c "import sys, json; print(json.load(sys.stdin)['unified_diff'])"
```

**View the statistics:**
```bash
curl -X POST http://localhost:8000/api/v1/generate-patch \
  -H "Content-Type: application/json" \
  -d @test_patch_payload.json | \
  python -c "import sys, json; stats = json.load(sys.stdin)['stats']; print(json.dumps(stats, indent=2))"
```

**View the generated code:**
```bash
curl -X POST http://localhost:8000/api/v1/generate-patch \
  -H "Content-Type: application/json" \
  -d @test_patch_payload.json | \
  python -c "import sys, json; print(json.load(sys.stdin)['generated_code'])"
```

### Step 5: Save Response to File

```bash
curl -X POST http://localhost:8000/api/v1/generate-patch \
  -H "Content-Type: application/json" \
  -d @test_patch_payload.json > patch_response.json

# View the saved response
python -m json.tool patch_response.json
```

## Testing Different Scenarios

### Scenario 1: Minor Enhancement

```json
{
  "query": "Add better documentation to format_user_info function",
  "original_content": "def format_user_info(name: str, email: str) -> str:\n    domain = email.split('@')[1] if '@' in email else 'unknown'\n    return f\"{name} ({email}) - domain: {domain}\"",
  "file_path": "utils/helpers.py",
  "limit": 5
}
```

Expected: Low similarity ratio (>0.8), few lines changed

### Scenario 2: Major Refactoring

```json
{
  "query": "Completely refactor to use a class-based approach with validation decorator",
  "original_content": "def validate_email(email: str) -> bool:\n    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'\n    return re.match(pattern, email) is not None",
  "file_path": "utils/validation.py",
  "limit": 10
}
```

Expected: Low similarity ratio (<0.7), many lines added

### Scenario 3: Bug Fix

```json
{
  "query": "Fix the split_fullname function to handle empty strings gracefully",
  "original_content": "def split_fullname(fullname: str) -> tuple[str, str]:\n    parts = fullname.split()\n    if len(parts) >= 2:\n        return parts[0], \" \".join(parts[1:])\n    return fullname, \"\"",
  "file_path": "utils/helpers.py",
  "limit": 5
}
```

Expected: Medium similarity ratio (0.7-0.85), a few lines changed

## Response Analysis

### Interpreting Statistics

- **lines_added**: Number of new code lines
- **lines_removed**: Number of deleted lines
- **lines_modified**: Number of changed lines
- **total_changes**: Sum of all modifications
- **similarity_ratio**: Coefficient from 0.0 to 1.0
  - 0.9-1.0 = Very similar (minor tweaks)
  - 0.7-0.9 = Similar (moderate improvements)
  - 0.5-0.7 = Different (significant changes)
  - <0.5 = Very different (major rewrite)
- **identical**: True if no changes were made

### Analyzing the Diff

The `unified_diff` field contains standard diff format:

```diff
--- a/original/path.py         ← Original file indicator
+++ b/new/path.py                ← New file indicator
@@ -10,5 +10,8 @@           ← Lines 10-14 in original, 10-17 in new
 unchanged line
-removed line                    ← Deleted with minus
+added line                      ← Added with plus
 unchanged line
```

## Troubleshooting

### Issue: 422 Unprocessable Entity

**Cause**: Invalid JSON request format

**Solution**: Verify JSON syntax
```bash
python -m json.tool test_patch_payload.json
```

### Issue: 500 Internal Server Error

**Cause**: Backend error during processing

**Solution**: Check backend logs
```bash
docker-compose logs backend | tail -50
```

Common issues:
- Ollama not running: `docker-compose logs ollama`
- Neo4j connection issue: `docker-compose logs neo4j`
- Qdrant connection issue: `docker-compose logs qdrant`

### Issue: Empty `generated_code` in Response

**Cause**: LLM couldn't generate code

**Solutions**:
1. Increase `limit` parameter (get more context)
2. Make query more specific
3. Check if code has been indexed

### Issue: Too High Similarity (>0.99)

**Cause**: LLM mostly repeated original

**Solutions**:
1. More specific instruction
2. Different query phrasing
3. Add context about desired changes

## Performance Notes

- First request may take 5-10 seconds (LLM inference)
- Subsequent requests typically 2-5 seconds
- Response time depends on:
  - Ollama model response time
  - File size (diffs larger files slower)
  - Context retrieval complexity

## Success Criteria

✅ Endpoint responds with Status 200 OK
✅ Response includes all required fields
✅ `unified_diff` is valid diff format
✅ `stats` show reasonable values
✅ `generated_code` is non-empty
✅ `similarity_ratio` is between 0.0 and 1.0

## Next Steps

Once testing is complete:

1. **Sub-phase 5.7**: Create frontend UI to display patches
2. **Sub-phase 5.8**: Add patch acceptance/rejection buttons
3. **Sub-phase 5.9**: Implement patch history tracking
4. **Sub-phase 5.10**: Integrate with VS Code (code lens, etc.)

---

**Status**: Sub-phase 5.6 - COMPLETE AND TESTED ✅
