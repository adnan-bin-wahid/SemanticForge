# Testing Sub-phases 5.1-5.4: Your Workflow

This guide shows how to test the code generation pipeline using your preferred method:

1. **Open test-project in VS Code extension**
2. **Run "Analyze Workspace" via Ctrl+Shift+P**
3. **Test via Web API**

---

## Step 1: Open Test Project in VS Code

```bash
cd e:\A A SPL3\SemanticForge\SemanticForge\test-project
code .
```

Or open VS Code and File → Open Folder → `test-project`

---

## Step 2: Run Extension "Analyze Workspace"

With the test-project folder open:

1. Press **Ctrl+Shift+P** (or Cmd+Shift+P on Mac)
2. Type `RepoAlign: Analyze Workspace` or `Analyze`
3. Press Enter

You should see:

```
"RepoAlign: Knowledge graph built successfully!"
```

This will:

- ✅ Ingest all Python files (main.py, models/user.py, models/database.py, utils/helpers.py, utils/**init**.py)
- ✅ Extract all functions and classes (User, UserDatabase, validate_email, etc.)
- ✅ Build the Neo4j knowledge graph
- ✅ Index embeddings in Qdrant

---

## Step 3: Test Code Generation via Web API

Now that the graph is built, test the code generation endpoint.

### Test 1: Generate Email Validation Method

```bash
curl -X POST http://localhost:8000/api/v1/generate-code \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Add a method to validate email addresses with regex pattern",
    "limit": 5
  }' | python -m json.tool
```

**Expected Response:**

```json
{
  "generated_code": "def validate_email_extended(email: str) -> bool:\n    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'\n    return re.match(pattern, email) is not None",
  "prompt": "# Code Generation Task\n\n## User Request\nValidate email addresses...",
  "status": "success"
}
```

**What to verify:**

- ✅ `generated_code` is not empty
- ✅ Contains Python code (def, return, etc.)
- ✅ Mentions email validation logic
- ✅ References the User or validation patterns from context

---

### Test 2: Generate Database Query Function

```bash
curl -X POST http://localhost:8000/api/v1/generate-code \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Create a function to query users by email domain from the database",
    "limit": 5
  }' | python -m json.tool
```

**Expected Response:**

```json
{
  "generated_code": "def query_users_by_domain(db: UserDatabase, domain: str) -> List[User]:\n    users = db.get_all_users()\n    return [user for user in users if user.get_domain() == domain]",
  "prompt": "# Code Generation Task\n\n## User Request\nCreate a function to query users by email domain...",
  "status": "success"
}
```

**What to verify:**

- ✅ Generated code references `UserDatabase` class (from context)
- ✅ Uses `get_all_users()` method that exists (properly learned from codebase)
- ✅ Calls `user.get_domain()` which is actually defined in User class

---

### Test 3: Generate Sanitization Enhancement

```bash
curl -X POST http://localhost:8000/api/v1/generate-code \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Enhance the sanitize input function to also convert to lowercase and trim whitespace",
    "limit": 5
  }' | python -m json.tool
```

**Expected Response:**

```json
{
  "generated_code": "def sanitize_input_enhanced(text: str) -> str:\n    return sanitize_input(text).strip().lower()",
  "prompt": "# Code Generation Task\n\n## User Request\nEnhance the sanitize input function...",
  "status": "success"
}
```

**What to verify:**

- ✅ References the existing `sanitize_input()` function from helpers.py
- ✅ Shows understanding of string operations (strip, lower)
- ✅ Properly chains the operations

---

## Verifying It's Working

### Signs of Success ✅

1. **API returns generated code** (not empty)
2. **Generated code looks like Python** (has `def`, `return`, proper indentation)
3. **Code references functions/classes from your project**:
   - User class methods: `validate_email()`, `get_domain()`, `get_username()`
   - Database methods: `get_all_users()`, `create_user()`, `delete_user()`
   - Helper functions: `sanitize_input()`, `validate_email()`, `format_greeting()`

4. **Prompt contains rich context** with your actual code snippets
5. **No errors** in response (status is 200)

### Signs of Issues ❌

- Empty `generated_code` field
- Error messages in response
- Generated code doesn't match query intent
- Doesn't reference project code

---

## Checking Graph Was Built

### View Graph in Neo4j

```bash
# Access Neo4j browser
# Go to: http://localhost:7687

# Login with: neo4j / password

# Run queries:
MATCH (f:Function) RETURN f.name LIMIT 20
MATCH (c:Class) RETURN c.name LIMIT 20
MATCH (f:Function)-[:CALLS]->(g:Function) RETURN f.name, g.name LIMIT 10
```

You should see:

- **Functions**: `validate_email`, `sanitize_input`, `format_greeting`, `format_user_info`, `split_fullname`, etc.
- **Classes**: `User`, `UserDatabase`
- **Calls**: Function relationships showing which functions call which

---

## What Each Sub-phase Is Testing

| Sub-phase | What's Being Tested     | What You'll See                                          |
| --------- | ----------------------- | -------------------------------------------------------- |
| **5.1**   | Ollama service running  | Generated code returned from LLM                         |
| **5.2**   | Prompt template quality | Structured prompt in response with context               |
| **5.3**   | LLM client working      | Code generation without errors                           |
| **5.4**   | Full orchestration      | Context retrieved, formatted, LLM called, code generated |

---

## Test Project Enhancements

The test-project now has:

```
test-project/
├── main.py                    # Entry point with User & Database usage
├── models/
│   ├── __init__.py           # Package init
│   ├── user.py               # User class with 8+ methods
│   └── database.py           # UserDatabase with CRUD operations
└── utils/
    ├── __init__.py           # Package init
    └── helpers.py            # 5+ utility functions
```

**Total Code Symbols**: ~20 functions/methods across 5 files

- Provides rich context for code generation
- Demonstrates complex relationships (UserDatabase uses User)
- Shows various patterns (validation, CRUD, string processing)

---

## Debugging If Something Fails

### If "Analyze Workspace" Shows Error

```bash
# Check backend logs
docker-compose logs backend --tail=50

# Verify services running
docker-compose ps

# Restart backend
docker-compose restart backend
```

### If API Returns Empty Code

- Graph might not be fully built yet
- Wait 10 seconds after "Analyze Workspace" completes
- Try simpler query: `"Create a function that returns hello world"`
- Check Neo4j has nodes: `MATCH (n) RETURN COUNT(n)`

### If API Returns Error 500

```bash
# Check backend logs for detailed error
docker-compose logs backend

# Restart Ollama (LLM might be stuck)
docker-compose restart ollama

# Wait 30 seconds before retrying
```

---

## Expected Performance

- **Analyze Workspace**: 3-5 seconds
- **API Response (simple query)**: 30-60 seconds (LLM generation on CPU)
- **API Response (complex query)**: 60-120 seconds (may be slow on CPU)

This is normal with TinyLLaMA on CPU. Speed improves with GPU.

---

## Summary

✅ **Your Workflow:**

1. Open test-project in VS Code
2. Ctrl+Shift+P → "Analyze Workspace"
3. See success message
4. Test via API endpoints with curl

✅ **Verify Working:**

- Generated code is returned
- Code matches query intent
- References your project code
- No errors in response

That's it! No complex test scripts needed. Just use your preferred workflow! 🎯
