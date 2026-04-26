# RepoAlign: A Semantic Repository Assistant

RepoAlign is a production-ready, SemanticForge-inspired repository-level code generation system for Python. It uses a semantic knowledge graph, learned context selection, and constraint-guided patch generation to provide intelligent, pattern-aligned code suggestions directly within the VS Code editor.

## Prerequisites

Before you begin, ensure you have the following installed on your system:

- **Docker and Docker Compose:** Required to run the containerized backend service.
  - [Install Docker Desktop](https://www.docker.com/products/docker-desktop/)
- **Node.js and npm:** Required for the VS Code extension frontend.
  - [Install Node.js](https://nodejs.org/)
- **Visual Studio Code:** The editor environment for the frontend.
  - [Install VS Code](https://code.visualstudio.com/)

## Running the Project

To get the project running, you will need to start the backend service and the frontend extension separately.

### 1. Start the Backend Service

The backend is a containerized FastAPI application managed by Docker Compose. It includes Neo4j (knowledge graph), Qdrant (vector database), and Ollama (local LLM).

1.  **Open a terminal** at the root of the `RepoAlign` project directory.

2.  **Stop and clean up any existing containers** (recommended for fresh starts):

    ```bash
    docker-compose down -v
    ```

3.  **Build and run all services**:

    ```bash
    docker-compose up --build -d
    ```

    This command will:
    - Build the Docker image for the backend
    - Start all services: backend, neo4j, qdrant, and ollama
    - Run them in detached mode (`-d`)

4.  **Verify all services are running**:

    ```bash
    docker-compose ps
    ```

    You should see 4 services with status "Up".

5.  **Pull the TinyLLaMA model** (required for code generation):

    ```bash
    docker-compose exec ollama ollama pull tinyllama
    ```

    This may take a few minutes depending on your internet connection. The model (~1.1GB) will be downloaded and stored.

6.  **Index embeddings** (required on first run or after data reset):

    ```bash
    curl -X 'POST' \
      'http://localhost:8000/api/v1/index-embeddings' \
      -H 'accept: application/json'
    ```

    This will generate embeddings for all code symbols and store them in Qdrant for semantic search.

### 2. Test the Backend API

Once the backend is running, you can test the core functionality:

**Test Context Retrieval:**

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/retrieve-context' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "query": "user",
  "limit": 10
}'
```

**Test Code Generation:**

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/generate-code' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "query": "create a function to calculate factorial",
  "limit": 10
}'
```

**Test Patch Generation (NEW Sub-phase 5.6):**

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/generate-patch' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "query": "add error handling to the validate_email function",
  "original_content": "def validate_email(email: str) -> bool:\\n    pattern = r'"'"'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'"'"'\\n    return bool(re.match(pattern, email))",
  "file_path": "utils/helpers.py",
  "limit": 10
}'
```

This endpoint generates code and compares it with the original to create a diff/patch. Response includes:

- `unified_diff`: Standard diff format (git-compatible)
- `stats`: Diff statistics (lines added/removed, similarity ratio)
- `generated_code`: The LLM-generated code
- `file_path`: File path used in diff header

For detailed patch generation testing, see: `TEST_GENERATE_PATCH.md`

You can also explore the API interactively at: **http://localhost:8000/docs**

### 3. Run the Frontend Extension

The frontend is a VS Code extension that communicates with the backend.

1.  **Open a new terminal** and navigate to the `frontend` directory:

    ```bash
    cd frontend
    ```

2.  **Install the dependencies** for the extension:

    ```bash
    npm install
    ```

3.  **Compile the TypeScript code:**

    ```bash
    npm run compile
    ```

4.  **Launch the Extension Development Host** by pressing `F5` in VS Code's frontend folder.

    This will open a new VS Code window with the RepoAlign extension activated.

### 4. Verify the Full Setup

Now, let's test that the frontend and backend are communicating correctly.

1.  In the new **"Extension Development Host"** VS Code window, open the **Command Palette** (`Ctrl+Shift+P` or `Cmd+Shift+P`).

2.  Type `RepoAlign` and select the command **"RepoAlign: Health Check"**.

3.  If everything is working correctly, a notification will appear in the bottom-right corner with the message: **"RepoAlign Backend is running!"**

You have now successfully set up and run the full RepoAlign system.

### 5. Testing Phase 8.5 & 8.6: Incremental Maintenance (RECOMMENDED FOR DEMO)

**Phase 8.5 & 8.6** implement the core incremental maintenance system that keeps the knowledge graph synchronized with code changes.

#### Quick Test with FastAPI Swagger UI

1. **Open Swagger UI**:
   ```
   http://localhost:8000/docs
   ```

2. **Create test file** (in a new terminal):
   ```bash
   docker-compose exec -T backend bash -c '
   cd /app/test-project
   cat > test_module.py << "EOF"
   def add(a, b):
       """Add two numbers."""
       return a + b
   
   def multiply(a, b):
       """Multiply two numbers."""
       return a * b
   
   class Calculator:
       """Calculator class."""
       pass
   EOF
   
   git add test_module.py
   git commit -m "Initial: Add test_module"
   echo "Test file created and committed"
   '
   ```

3. **Test Phase 8.6: Re-analyze Symbol** (Most Impressive!)
   - Navigate to `POST /api/v1/re-analyze-symbol`
   - Click "Try it out"
   - Paste this JSON:
   ```json
   {
     "file_path": "/app/test-project/test_module.py",
     "file_content": "def add(a, b):\n    \"\"\"Add two numbers.\"\"\"\n    return a + b\n\ndef multiply(a, b):\n    \"\"\"Multiply two numbers.\"\"\"\n    return a * b\n\nclass Calculator:\n    \"\"\"Calculator class.\"\"\"\n    pass\n",
     "symbol_name": "add",
     "symbol_type": "function"
   }
   ```
   - Click "Execute"
   - **Result**: Returns complete symbol metadata (signature, parameters, docstring, complexity, etc.)

4. **Test Phase 8.5: Invalidate Modified Symbol**
   - Navigate to `POST /api/v1/invalidate-modified-symbol`
   - Click "Try it out"
   - Paste:
   ```json
   {
     "file_path": "/app/test-project/test_module.py",
     "symbol_name": "add",
     "symbol_type": "function",
     "new_signature": "def add(a, b, c)",
     "new_docstring": "Add three numbers"
   }
   ```
   - **Result**: Updates symbol with new signature

#### Available Phase 8.5 & 8.6 Endpoints

| Endpoint | Purpose | Use Case |
|----------|---------|----------|
| `POST /invalidate-impact` | Dry-run preview | See what would be deleted |
| `POST /invalidate-removed-symbol` | Delete removed symbol | Remove deleted function from graph |
| `POST /invalidate-modified-symbol` | Update modified symbol | Update changed signature |
| `POST /invalidate-file-changes` | Batch invalidation | Handle all changes at once |
| `POST /re-analyze-symbol` | Single symbol analysis | Deep dive into one function |
| `POST /re-analyze-file-changes` | Batch file analysis | Re-analyze all changed symbols |
| `POST /re-analyze-batch` | Multi-file analysis | Process entire changeset |

**For comprehensive demonstration guide**, see: [`DEMONSTRATION.md`](./DEMONSTRATION.md)

### Troubleshooting


**Issue: Qdrant collection not found**

- Run: `curl -X 'POST' 'http://localhost:8000/api/v1/index-embeddings'`

**Issue: To restart everything cleanly**

- Run: `docker-compose down -v && docker-compose up --build -d`
- Then re-pull model: `docker-compose exec ollama ollama pull tinyllama`
- And re-index: `curl -X 'POST' 'http://localhost:8000/api/v1/index-embeddings'`

**Issue: Check backend logs**

- Run: `docker-compose logs -f backend`

**Issue: Check Ollama logs**

- Run: `docker-compose logs -f ollama`
