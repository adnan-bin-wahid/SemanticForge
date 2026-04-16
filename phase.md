# AI ML Final Year Project: SemanticForge Implementation Phases

This document breaks down the development of the "RepoAlign" repository assistant into distinct phases. Each phase builds upon the previous one, culminating in a production-ready system as described in the project specification.

## Phase 1: Core Backend, Frontend, and Static Graph Construction

**Goal:** Establish the foundational architecture, including the user-facing extension, the backend server, and the ability to ingest a repository to build a static knowledge graph.

**Key Tasks:**

1.  **Frontend (VS Code Extension):**
    - Set up a basic TypeScript-based VS Code extension.
    - Implement UI components for:
      - An "Index Repository" button.
      - A text input for user instructions (e.g., "add validation to user registration").
      - A view to display status messages and eventually the results.

2.  **Backend (FastAPI Service):**
    - Initialize a Python FastAPI project.
    - Create API endpoints to handle requests from the VS Code extension (e.g., `/index`, `/request`).
    - Set up Docker Compose to manage the backend service and other components.

3.  **Repository Ingestion & Static Analysis:**
    - Implement the logic to ingest a local Python repository.
    - Use static analysis tools (`ast`, `LibCST`, `tree-sitter`) to parse Python files.
    - Extract key code structures: files, modules, classes, functions, methods, imports, and calls.

4.  **Knowledge Graph (Neo4j):**
    - Define the graph schema with nodes (e.g., `File`, `Function`, `Class`) and edges (e.g., `IMPORTS`, `CALLS`, `DEFINES`).
    - Implement the graph builder module to populate the Neo4j database with the data from the static analysis step.

5.  **Basic Context Retrieval:**
    - Implement a first-pass hybrid retrieval system:
      - **Keyword Search:** Use BM25 on source code and docstrings.
      - **Vector Search:** Generate embeddings for code summaries (e.g., function docstrings) and store them in Qdrant for similarity search.

---

## Phase 2: Code Generation and Basic Validation

**Goal:** Integrate a local Large Language Model (LLM) to generate code patches and validate them using static checks.

**Key Tasks:**

1.  **Code Generation:**
    - Set up a local code LLM (e.g., a 7B parameter model using Ollama).
    - Create a `CodeGenerator` module in the backend.
    - This module will take the user instruction and the retrieved context from Phase 1 to prompt the LLM.

2.  **Patch Generation:**
    - Implement logic to format the LLM's output into a patch file (e.g., a `.diff` or `.patch` format).

3.  **Static Constraint Checking:**
    - Create a `ConstraintChecker` module.
    - Integrate static analysis tools to validate the generated patch:
      - **Linting:** Use `Ruff`.
      - **Type Checking:** Use `mypy` or `pyright`.
      - **Basic Rules:** Check for simple constraints like symbol existence, correct import statements, and function parameter counts.

4.  **Frontend Integration:**
    - Add a view in the VS Code extension to display the generated patch/diff to the user.
    - Implement "Accept" / "Reject" / "Regenerate" buttons to allow user interaction.

---

## Phase 3: Dynamic Analysis and Incremental Maintenance

**Goal:** Enrich the knowledge graph with runtime information and implement an agent to keep the graph up-to-date automatically.

**Key Tasks:**

1.  **Dynamic Trace Collection:**
    - Instrument the target repository's test suite.
    - Use tools like `pytest`, `coverage.py`, and `sys.setprofile` to capture runtime data during test execution, such as:
      - Actual call traces between functions.
      - Runtime type information.
      - Which tests cover which functions.

2.  **Graph Enrichment:**
    - Implement a process to merge the captured dynamic data back into the Neo4j graph. This creates a more accurate representation of the repository's behavior.

3.  **Continual Maintenance Agent:**
    - Develop a background agent that monitors the repository for file changes (e.g., by watching the filesystem or using `git diff`).
    - When a file is changed, the agent should:
      - Identify the changed symbols using an AST-diff.
      - Invalidate and re-index only the affected parts of the graph, avoiding a full repository re-scan.

---

## Phase 4: Learned Query Planner

**Goal:** Replace the basic retrieval system with a more intelligent, machine-learning-based query planner that translates natural language instructions into precise graph queries.

**Key Tasks:**

1.  **Synthetic Data Generation:**
    - Create a pipeline to generate synthetic training pairs of (instruction, graph query). This can be done by analyzing existing repository dependencies and code structures.

2.  **Model Training:**
    - Train a small sequence-to-sequence model (like Flan-T5) on the synthetic dataset. The model's goal is to learn how to map a user's natural language instruction to a structured query for your knowledge graph.

3.  **Query Planner Integration:**
    - Replace the hybrid retrieval mechanism from Phase 1 with this new learned query planner.
    - The planner will now generate a specific graph query to retrieve the most relevant context for the code generation step.

4.  **(Optional) Reward Tuning:**
    - Implement a REINFORCE-style algorithm to fine-tune the query planner based on feedback signals like test pass rates, type-check success, or the conciseness of the retrieved context.

---

## Phase 5: Advanced Constraints and Final Evaluation

**Goal:** Implement a more sophisticated, SMT-based constraint-guided decoder and conduct a thorough evaluation of the entire system.

**Key Tasks:**

1.  **SMT-Guided Decoding:**
    - Integrate the Z3 SMT solver into the code generation process.
    - Implement a partial constraint-guided decoder that prunes invalid code generations _during_ the decoding process. Focus on critical constraints:
      - Type compatibility.
      - Repository-specific architectural rules (e.g., "controller must call a service").
      - Correct decorator usage.

2.  **Evaluation Benchmark:**
    - Create a small, custom benchmark of 8-12 Python repositories.
    - Author 150-300 tasks based on real commit histories, feature requests, and bug-fix scenarios.

3.  **System Evaluation:**
    - Measure the system's performance against the benchmark.
    - Track key metrics aligned with the original paper:
      - `Pass@1` (the percentage of tasks for which the first generated patch is correct).
      - Compile, lint, and test pass rates.
      - Hallucination rates (both schematic and logical).
      - Retrieval precision and latency.

4.  **Final Report and Presentation:**
    - Compile the results into your final year project report.
    - Prepare a presentation that demonstrates the system and discusses the results, challenges, and learnings.
