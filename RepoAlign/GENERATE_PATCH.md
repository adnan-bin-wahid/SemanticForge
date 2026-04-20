# Sub-phase 5.6: Generate Patch Endpoint

## Overview

The `/generate-patch` endpoint combines:

1. **CodeGenerator** - Creates LLM-generated code
2. **DiffGenerator** - Compares original vs generated to create a patch

## API Endpoint

```
POST /api/v1/generate-patch
```

## Request Format

```json
{
  "query": "Add email domain validation to validate_email function",
  "original_content": "def validate_email(email: str) -> bool:\n    pattern = r'^[a-zA-Z0-9]+@[a-zA-Z0-9]+\\.[a-zA-Z]{2,}$'\n    return bool(re.match(pattern, email))",
  "file_path": "utils/helpers.py",
  "limit": 10
}
```

### Request Parameters

| Parameter          | Type    | Required | Description                                    |
| ------------------ | ------- | -------- | ---------------------------------------------- |
| `query`            | string  | Yes      | User instruction for code generation           |
| `original_content` | string  | Yes      | Original file content to compare against       |
| `file_path`        | string  | No       | Path for diff header (default: "generated.py") |
| `limit`            | integer | No       | Number of context results (default: 10)        |

## Response Format

```json
{
  "query": "Add email domain validation to validate_email function",
  "unified_diff": "--- a/utils/helpers.py\n+++ b/utils/helpers.py\n@@ -1,6 +1,12 @@\n def validate_email(email: str) -> bool:\n+    # Extract domain from email\n+    parts = email.split('@')\n+    if len(parts) != 2:\n+        return False\n+    domain = parts[1]\n+    \n     pattern = r'^[a-zA-Z0-9]+@[a-zA-Z0-9]+\\.[a-zA-Z]{2,}$'\n     return bool(re.match(pattern, email))",
  "stats": {
    "lines_added": 5,
    "lines_removed": 0,
    "lines_modified": 0,
    "total_changes": 5,
    "similarity_ratio": 0.9234,
    "identical": false
  },
  "generated_code": "def validate_email(email: str) -> bool:\n    # Extract domain from email\n    parts = email.split('@')\n    if len(parts) != 2:\n        return False\n    domain = parts[1]\n    \n    pattern = r'^[a-zA-Z0-9]+@[a-zA-Z0-9]+\\.[a-zA-Z]{2,}$'\n    return bool(re.match(pattern, email))",
  "file_path": "utils/helpers.py"
}
```

### Response Fields

| Field                    | Type    | Description                                   |
| ------------------------ | ------- | --------------------------------------------- |
| `query`                  | string  | The user's instruction (echoed back)          |
| `unified_diff`           | string  | Standard unified diff format (git-compatible) |
| `stats`                  | object  | Diff statistics                               |
| `stats.lines_added`      | int     | Number of lines added                         |
| `stats.lines_removed`    | int     | Number of lines removed                       |
| `stats.lines_modified`   | int     | Number of lines modified                      |
| `stats.total_changes`    | int     | Total number of changes                       |
| `stats.similarity_ratio` | float   | Similarity ratio (0.0-1.0)                    |
| `stats.identical`        | boolean | Whether files are identical                   |
| `generated_code`         | string  | The full LLM-generated code                   |
| `file_path`              | string  | File path used in diff header                 |

## Testing with curl

### Example 1: Basic Test

```bash
curl -X POST http://localhost:8000/api/v1/generate-patch \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Add domain extraction to validate_email",
    "original_content": "def validate_email(email: str) -> bool:\n    pattern = r'"'"'^[a-zA-Z0-9]+@[a-zA-Z0-9]+\\.[a-zA-Z]{2,}$'"'"'\n    return bool(re.match(pattern, email))",
    "file_path": "utils/helpers.py",
    "limit": 10
  }' | python -m json.tool
```

### Example 2: Using a Real File

1. Read the file content into a variable:

**Bash/Linux:**

```bash
ORIGINAL=$(cat test-project/utils/helpers.py | jq -Rs .)

curl -X POST http://localhost:8000/api/v1/generate-patch \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"Add more robust input validation\",
    \"original_content\": $ORIGINAL,
    \"file_path\": \"utils/helpers.py\",
    \"limit\": 10
  }" | python -m json.tool
```

**PowerShell (Windows):**

```powershell
$content = Get-Content -Path "test-project/utils/helpers.py" -Raw | ConvertTo-Json

$body = @{
    query = "Add more robust input validation"
    original_content = ($content -replace '"', '')
    file_path = "utils/helpers.py"
    limit = 10
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:8000/api/v1/generate-patch" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body | Select-Object -ExpandProperty Content | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

### Example 3: Save Response to File

```bash
curl -X POST http://localhost:8000/api/v1/generate-patch \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Improve error handling in process_user function",
    "original_content": "def process_user(user):\n    validate(user)\n    user.activate()\n    save(user)",
    "file_path": "models/user_processor.py",
    "limit": 10
  }' \
  -o response.json

# Extract just the diff
cat response.json | python -c "import sys, json; print(json.load(sys.stdin)['unified_diff'])" > generated.patch

# View the patch
cat generated.patch
```

## Workflow: Using Generated Patches

### Step 1: Generate the Patch

```bash
curl -X POST http://localhost:8000/api/v1/generate-patch \
  -H "Content-Type: application/json" \
  -d @patch_request.json > patch_response.json
```

### Step 2: Review the Diff

```bash
# Extract and view the unified diff
python -c "import json; print(json.load(open('patch_response.json'))['unified_diff'])"

# Or save it to a file
python -c "import json; print(json.load(open('patch_response.json'))['unified_diff'])" > generated.patch
less generated.patch
```

### Step 3: Check Statistics

```bash
# View change statistics
python -c "import json; print(json.dumps(json.load(open('patch_response.json'))['stats'], indent=2))"
```

### Step 4: Apply the Patch (Optional)

If you want to apply the patch using standard Unix tools:

```bash
# Save the diff
python -c "import json; print(json.load(open('patch_response.json'))['unified_diff'])" > fix.patch

# Apply to original file (may require adjustment depending on file structure)
patch utils/helpers.py < fix.patch

# Or just view the proposed changes
patch --dry-run -p0 < fix.patch
```

## Python Integration Example

```python
import requests
import json

# Prepare request
original_code = open("utils/helpers.py").read()

request_data = {
    "query": "Add email domain validation",
    "original_content": original_code,
    "file_path": "utils/helpers.py",
    "limit": 10
}

# Call endpoint
response = requests.post(
    "http://localhost:8000/api/v1/generate-patch",
    json=request_data
)

result = response.json()

# Extract components
diff = result["unified_diff"]
stats = result["stats"]
generated_code = result["generated_code"]

print(f"Changes: +{stats['lines_added']} -{stats['lines_removed']} "
      f"(similarity: {stats['similarity_ratio']:.1%})")

print("\n--- Generated Diff ---")
print(diff)

# Save patch file
with open("generated.patch", "w") as f:
    f.write(diff)
```

## Implementation Details

### How It Works

1. **Context Retrieval**: Uses the same hybrid search + graph expansion as `/generate-code`
2. **Code Generation**: Calls CodeGenerator.generate_code() to get LLM output
3. **Diff Computation**: Uses Python's `difflib` for unified diff format
4. **Statistics**: Calculates similarity ratio, lines added/removed/modified
5. **Response**: Returns complete patch with metadata

### Diff Format

The `unified_diff` uses standard unified diff format:

- `---` lines show deleted content
- `+++` lines show added content
- `@@` sections show change locations
- Context lines (unchanged) included for readability

### Similarity Ratio

- **1.0** = Files are identical
- **0.8+** = Very similar (minor changes)
- **0.5-0.8** = Moderate changes
- **<0.5** = Significant changes

## Next Steps (Sub-phase 5.7+)

The `/generate-patch` endpoint provides the backend foundation for:

### 5.7: Frontend Patch Display

- Show unified diff in editor with syntax highlighting
- Color-coded additions (green) and deletions (red)

### 5.8: Patch Application UI

- "Accept" button to apply patch
- "Reject" button to discard patch
- "Edit" to manually adjust before applying

### 5.9: Patch History

- Keep track of generated patches
- Allow reviewing previous suggestions

### 5.10: Integration with VS Code

- Inline code lens for "Generate better code"
- QuickFix that shows generated patch inline
- Diff preview before acceptance

## Troubleshooting

### 500 Internal Server Error

**Check the backend logs:**

```bash
docker-compose logs backend
```

**Common issues:**

- Ollama service not running: `docker-compose logs ollama`
- Context retriever failing: Check Neo4j/Qdrant connection
- Invalid JSON in request: Verify JSON syntax

### Empty Generated Code

This means the LLM didn't understand the query or had no context. Try:

1. Increase `limit` parameter to get more context
2. Make query more specific
3. Check that code has been indexed with `/index-embeddings`

### Very High Similarity (>0.99)

This suggests the LLM mostly repeated the original. Try:

1. More specific instruction ("improve error handling with try/except")
2. Different query phrasing
3. Check if context is relevant to query

## Status

✅ **Sub-phase 5.6: COMPLETE**

The `/generate-patch` endpoint is now fully integrated and ready for use!
