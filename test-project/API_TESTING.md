# Quick API Testing Commands

After running "Analyze Workspace" in your VS Code extension, use these commands to test the code generation pipeline.

## Quick Test - Email Validation

```bash
curl -X POST http://localhost:8000/api/v1/generate-code \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Add a method to validate email addresses with regex pattern",
    "limit": 5
  }'
```

Copy the full command above and paste into PowerShell or Command Prompt.

---

## Quick Test - Database Query

```bash
curl -X POST http://localhost:8000/api/v1/generate-code \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Create a function to query users by email domain from the database",
    "limit": 5
  }'
```

---

## Quick Test - String Enhancement

```bash
curl -X POST http://localhost:8000/api/v1/generate-code \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Enhance the sanitize input function to also convert to lowercase and trim whitespace",
    "limit": 5
  }'
```

---

## What to Look For in Response

✅ **Success - You'll See:**

```json
{
  "generated_code": "def validate_email(...",
  "prompt": "# Code Generation Task\n...",
  "status": "success"
}
```

✅ **Good Signs:**

- `generated_code` is not empty
- Contains Python syntax (`def`, `return`, etc.)
- References classes/functions from your project (User, UserDatabase, sanitize_input, etc.)
- `prompt` shows rich context with your actual code

❌ **Issues:**

- Empty `generated_code`
- Error in response
- Generated code is gibberish
- Takes more than 2 minutes (LLM timeout)

---

## Pretty Print Response

Add `| python -m json.tool` to see formatted output:

```bash
curl -X POST http://localhost:8000/api/v1/generate-code \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Add a method to validate email addresses",
    "limit": 5
  }' | python -m json.tool
```

---

## Windows PowerShell Version

If curl doesn't work, try PowerShell Invoke-WebRequest:

```powershell
$body = @{
    query = "Add a method to validate email addresses"
    limit = 5
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:8000/api/v1/generate-code" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body | ConvertTo-Json
```

---

## Expected Workflow

1. **Open test-project** in VS Code
2. **Ctrl+Shift+P** → "Analyze Workspace"
3. **Wait** for "RepoAlign: Knowledge graph built successfully!"
4. **Copy one curl command** from above
5. **Paste into terminal** (makes HTTP request to backend)
6. **View response** - should see generated Python code!

That's all! The API will show you:

- What code was generated
- What prompt was used
- That sub-phases 5.1-5.4 are working ✓
