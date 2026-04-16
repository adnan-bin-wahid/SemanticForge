# AI ML Final Year Project: RepoAlign Implementation Phases

This document provides an extremely granular breakdown of the development of the "RepoAlign" repository assistant. The project is divided into 10 main phases, and each of these is further divided into 10 sub-phases. Each sub-phase has a clear, specific outcome to ensure precise, measurable progress.

---

---

## **Phase 1: Foundational Setup**

**Main Goal:** Establish the core project structure, including the backend service and the basic VS Code extension frontend, fully containerized.

- **Sub-phase 1.1: Project Initialization**
  - **Task:** Create the root project directory and initialize a Git repository.
  - **Outcome:** A local directory named `RepoAlign` with a `.git` sub-directory, ready for version control.

- **Sub-phase 1.2: Backend Directory Structure**
  - **Task:** Create the standard directory structure for the FastAPI backend (e.g., `/backend/app`, `/backend/tests`).
  - **Outcome:** A clean, organized folder structure within the `/backend` directory that follows common Python project conventions.

- **Sub-phase 1.3: "Hello World" FastAPI Service**
  - **Task:** Create a `main.py` file inside `/backend/app` with a single root endpoint (`/`) that returns a "Hello World" JSON message.
  - **Outcome:** A runnable FastAPI application file that can be started to serve a basic endpoint.

- **Sub-phase 1.4: Backend Dependencies**
  - **Task:** Create a `requirements.txt` file listing `fastapi` and `uvicorn`.
  - **Outcome:** A `requirements.txt` file that allows for reproducible installation of the backend's dependencies.

- **Sub-phase 1.5: Backend Dockerfile**
  - **Task:** Write a `Dockerfile` in the `/backend` directory to containerize the FastAPI application.
  - **Outcome:** A `Dockerfile` that can build a container image of the backend service, including its dependencies.

- **Sub-phase 1.6: Initial Docker Compose**
  - **Task:** Create a `docker-compose.yml` file at the project root to define and run the backend service.
  - **Outcome:** A `docker-compose.yml` file that can successfully build and run the backend container, making the service accessible on a local port.

- **Sub-phase 1.7: Frontend Scaffolding**
  - **Task:** Use `yo code` or a similar tool to generate the boilerplate for a new TypeScript-based VS Code extension in a `/frontend` directory.
  - **Outcome:** A functional, basic VS Code extension that can be loaded and activated in a development host window.

- **Sub-phase 1.8: Frontend Command**
  - **Task:** Implement a basic VS Code command (e.g., `repoalign.healthCheck`) that, when triggered, shows a simple info message.
  - **Outcome:** A new command available in the VS Code command palette that displays a "Hello from RepoAlign" message.

- **Sub-phase 1.9: Frontend-to-Backend Communication**
  - **Task:** Write the code within the new frontend command to make an HTTP request to the backend's health check endpoint.
  - **Outcome:** The VS Code extension command now successfully calls the running backend service and can log the response.

- **Sub-phase 1.10: Full System Health Check**
  - **Task:** Refine the frontend command to display the actual message received from the backend.
  - **Outcome:** A complete, end-to-end "health check" loop. Running the VS Code command triggers a call to the containerized backend, and the backend's "Hello World" response is displayed in the VS Code UI.

---

## **Phase 2: Static Repository Analysis**

**Main Goal:** Implement the logic to parse a Python repository and extract its static structure into an in-memory representation.

- **Sub-phase 2.1: Repository Ingestion Endpoint**
  - **Task:** Create a new API endpoint in the backend (e.g., `/ingest`) that accepts a local file path to a Python repository.
  - **Outcome:** A new, non-functional API endpoint that can receive and validate a repository path from a request.

- **Sub-phase 2.2: File Discovery Module**
  - **Task:** Implement a utility module that walks a given directory path and identifies all `*.py` files.
  - **Outcome:** A function that returns a list of absolute paths to all Python files within a target repository.

- **Sub-phase 2.3: AST Parsing for Files**
  - **Task:** Integrate Python's built-in `ast` module to parse a single Python file into an Abstract Syntax Tree.
  - **Outcome:** A function that takes a file path, reads its content, and returns a parsed `ast` tree object.

- **Sub-phase 2.4: Function and Class Extraction**
  - **Task:** Write an AST visitor class to traverse the tree and extract top-level function and class definitions.
  - **Outcome:** A module that can extract the names and line numbers of all functions and classes in a file.

- **Sub-phase 2.5: Import Statement Extraction**
  - **Task:** Enhance the AST visitor to specifically identify and extract `import` and `from ... import` statements.
  - **Outcome:** The analysis module can now list all modules and symbols imported by a given Python file.

- **Sub-phase 2.6: Static Call Extraction**
  - **Task:** Further enhance the AST visitor to find `ast.Call` nodes to identify static function/method calls within the code.
  - **Outcome:** The analysis module can produce a list of function calls made within each function or method body.

- **Sub-phase 2.7: Signature and Parameter Extraction**
  - **Task:** Refine the function/method extraction to also capture function signatures, including parameter names and type annotations.
  - **Outcome:** The extracted data for a function now includes its full signature details.

- **Sub-phase 2.8: Data Structure Definition**
  - **Task:** Use Pydantic models to define clear, typed data structures for the extracted information (e.g., `FileReport`, `FunctionDef`, `ClassDef`).
  - **Outcome:** A set of Pydantic models that provide a clean, validated schema for the in-memory representation of the repository's structure.

- **Sub-phase 2.9: Aggregation Service**
  - **Task:** Create a service that orchestrates the entire process: takes a repository path, uses the file discovery module, parses each file, and aggregates the results into a single structured object.
  - **Outcome:** A main service class that can generate a complete, structured JSON object representing the entire static codebase of a repository.

- **Sub-phase 2.10: Endpoint Integration**
  - **Task:** Connect the aggregation service to the `/ingest` endpoint.
  - **Outcome:** Calling the `/ingest` endpoint with a valid path now returns a full JSON representation of the target repository's static structure.

---

## **Phase 3: Static Knowledge Graph Construction**

**Main Goal:** Store the extracted repository structure in a Neo4j graph database, making the relationships queryable.

- **Sub-phase 3.1: Neo4j Containerization**
  - **Task:** Add the official Neo4j image as a new service in the `docker-compose.yml` file.
  - **Outcome:** A running Neo4j container, accessible from the backend service within the Docker network.

- **Sub-phase 3.2: Backend Neo4j Driver**
  - **Task:** Add the `neo4j` Python driver to `requirements.txt` and create a connection manager module in the backend.
  - **Outcome:** The FastAPI application can successfully connect to the Neo4j database.

- **Sub-phase 3.3: Node Schema Definition**
  - **Task:** Formally define the graph schema for nodes: `Repository`, `File`, `Class`, `Function`, `Module`.
  - **Outcome:** A document or script outlining the properties for each node type (e.g., a `Function` node has `name`, `signature`, `start_line`, `end_line`).

- **Sub-phase 3.4: Edge Schema Definition**
  - **Task:** Formally define the graph schema for relationships: `CONTAINS`, `IMPORTS`, `DEFINES`, `CALLS`, `INHERITS`.
  - **Outcome:** A document outlining the semantics of each edge type (e.g., `(Function)-[:CALLS]->(Function)`).

- **Sub-phase 3.5: Graph Writer for Files and Modules**
  - **Task:** Implement a `GraphBuilder` module that takes the analysis result and creates `File` and `Module` nodes.
  - **Outcome:** A script that can populate the Neo4j database with nodes representing all the Python files in the repository.

- **Sub-phase 3.6: Graph Writer for Classes and Functions**
  - **Task:** Extend the `GraphBuilder` to create `Class` and `Function` nodes and link them to their parent `File` nodes with `DEFINES` edges.
  - **Outcome:** The graph now contains nodes for all classes and functions, correctly associated with the files they are defined in.

- **Sub-phase 3.7: Graph Writer for Inheritance**
  - **Task:** Extend the `GraphBuilder` to identify base classes and create `INHERITS` relationships between `Class` nodes.
  - **Outcome:** The graph now correctly models the class inheritance hierarchy of the repository.

- **Sub-phase 3.8: Graph Writer for Imports**
  - **Task:** Extend the `GraphBuilder` to create `IMPORTS` relationships from `File` nodes to the `Module` nodes they import.
  - **Outcome:** The graph now contains edges representing all import statements, linking files to the modules they depend on.

- **Sub-phase 3.9: Graph Writer for Static Calls**
  - **Task:** Extend the `GraphBuilder` to create `CALLS` relationships between `Function` nodes based on the static analysis of call sites.
  - **Outcome:** The graph now models the static call graph, showing which functions call which other functions.

- **Sub-phase 3.10: Full Graph Construction Endpoint**
  - **Task:** Create a new endpoint (e.g., `/build-graph`) that orchestrates the full analysis and graph-building process.
  - **Outcome:** An API endpoint that, when called, ingests a repository, analyzes it, and populates the Neo4j database with a complete static knowledge graph.

---

## **Phase 4: Hybrid Context Retrieval**

**Main Goal:** Implement a baseline context retrieval system that can find relevant code snippets based on a user's instruction.

- **Sub-phase 4.1: Qdrant Containerization**
  - **Task:** Add the Qdrant vector database as a new service in the `docker-compose.yml` file.
  - **Outcome:** A running Qdrant container, accessible from the backend service.

- **Sub-phase 4.2: Backend Qdrant Client**
  - **Task:** Add the `qdrant-client` library to `requirements.txt` and create a connection manager for it.
  - **Outcome:** The FastAPI application can successfully connect to the Qdrant database and create collections.

- **Sub-phase 4.3: Embeddings Generation Module**
  - **Task:** Add `sentence-transformers` to `requirements.txt`. Create a module that can take a string of text (like a function's code) and convert it into a vector embedding.
  - **Outcome:** A utility that can produce a vector representation of any given code snippet.

- **Sub-phase 4.4: Embedding Indexing Service**
  - **Task:** Create a service that iterates through all `Function` and `Class` nodes in the Neo4j graph, generates embeddings for their code, and stores them in Qdrant.
  - **Outcome:** The Qdrant database is populated with vector embeddings for all major code symbols in the repository.

- **Sub-phase 4.5: Vector Search Endpoint**
  - **Task:** Create an API endpoint that takes a natural language query, generates an embedding for it, and performs a similarity search in Qdrant.
  - **Outcome:** An API that can return a list of symbol names (e.g., function names) that are semantically similar to the user's query.

- **Sub-phase 4.6: Keyword Search Index**
  - **Task:** Implement a basic in-memory keyword search index (e.g., using BM25 from the `rank_bm25` library) for docstrings and function names.
  - **Outcome:** A searchable index that allows for efficient keyword-based retrieval of code symbols.

- **Sub-phase 4.7: Keyword Search Endpoint**
  - **Task:** Create an API endpoint that takes a query and returns a ranked list of symbols based on keyword matching.
  - **Outcome:** An API that provides keyword search functionality over the codebase.

- **Sub-phase 4.8: Hybrid Search Strategy**
  - **Task:** Design and implement a module that combines the results from both vector search and keyword search (e.g., using a simple weighted score).
  - **Outcome:** A retrieval function that leverages both semantic and keyword matching for more robust results.

- **Sub-phase 4.9: Graph Expansion**
  - **Task:** Implement a function that takes a list of retrieved symbols and expands the context by querying the Neo4j graph for their immediate neighbors (e.g., functions they call, or functions that call them).
  - **Outcome:** A function that can enrich the initial retrieval results with directly related code from the knowledge graph.

- **Sub-pPhase 4.10: Full Retrieval Endpoint**
  - **Task:** Create a final retrieval endpoint (`/retrieve-context`) that orchestrates the entire hybrid search and graph expansion process.
  - **Outcome:** A single API endpoint that takes a user instruction and returns a rich, structured context containing the most relevant code snippets and their immediate graph neighbors.

---

## **Phase 5: Code Generation and Frontend Display**

**Main Goal:** Integrate a local LLM to generate a code patch and display it to the user in the VS Code extension.

- **Sub-phase 5.1: Ollama LLM Service**
  - **Task:** Add a service to `docker-compose.yml` that runs a local code LLM via Ollama (e.g., `codellama:7b`).
  - **Outcome:** A running LLM service accessible to the backend for inference.

- **Sub-phase 5.2: Code Generation Prompt Template**
  - **Task:** Design a structured prompt template that incorporates the user's instruction and the context retrieved in Phase 4.
  - **Outcome:** A well-defined prompt string that can be programmatically filled to guide the LLM's code generation.

- **Sub-phase 5.3: LLM Client Module**
  - **Task:** Create a client module in the backend to send the formatted prompt to the Ollama service and receive the generated code.
  - **Outcome:** A function that can call the LLM and get a raw string of generated code as a response.

- **Sub-phase 5.4: Code Generation Service**
  - **Task:** Create a `CodeGenerator` service that orchestrates the process: retrieves context, formats the prompt, and calls the LLM.
  - **Outcome:** A service that can generate a block of code in response to a user instruction.

- **Sub-phase 5.5: Diff Generation**
  - **Task:** Implement a utility to compare the original source file with the LLM-generated code to create a diff in the standard `.diff` format.
  - **Outcome:** A function that can produce a patch file from the LLM's output.

- **Sub-phase 5.6: Generation Endpoint**
  - **Task:** Create a `/generate-patch` endpoint that ties everything together.
  - **Outcome:** An API endpoint that returns a diff/patch file based on a user instruction.

- **Sub-phase 5.7: Frontend Request Trigger**
  - **Task:** Add a text input and a "Generate" button to the VS Code extension UI.
  - **Outcome:** A user can now type an instruction and click a button to trigger the `/generate-patch` endpoint.

- **Sub-phase 5.8: Frontend Diff Viewer**
  - **Task:** Implement the logic in the VS Code extension to receive the diff content and display it using VS Code's native diff viewer.
  - **Outcome:** The generated patch is displayed to the user in a clean, side-by-side comparison view within their editor.

- **Sub-phase 5.9: Frontend User Actions**
  - **Task:** Add "Accept" and "Reject" buttons to the diff viewer UI.
  - **Outcome:** A UI with buttons that are ready to be wired up to perform actions.

- **Sub-phase 5.10: End-to-End Generation Loop**
  - **Task:** Wire up the full, non-functional loop.
  - **Outcome:** A user can type an instruction, see a generated diff, and click buttons (which currently only log to the console). The core user flow is now visible.

---

## **Phase 6: Basic Constraint Checking and Testing**

**Main Goal:** Add a validation layer to check the generated patch against basic static analysis and the repository's own test suite.

- **Sub-phase 6.1: Temporary Patch Application**
  - **Task:** Implement a utility that can take a patch and apply it to a temporary copy of the repository in a sandboxed directory.
  - **Outcome:** A function that can safely prepare a temporary version of the codebase with the LLM's suggested changes.

- **Sub-phase 6.2: Ruff Integration**
  - **Task:** Add `ruff` to `requirements.txt`. Create a module that runs Ruff as a subprocess on the temporary directory and captures the output.
  - **Outcome:** A validation function that can programmatically lint the patched code.

- **Sub-phase 6.3: Mypy Integration**
  - **Task:** Add `mypy` to `requirements.txt`. Create a module that runs Mypy as a subprocess and captures any type errors.
  - **Outcome:** A validation function that can programmatically type-check the patched code.

- **Sub-phase 6.4: Basic Rules Checker**
  - **Task:** Implement a simple checker that re-parses the patched file to ensure basic integrity (e.g., no syntax errors).
  - **Outcome:** A quick validation step that catches fundamental syntax issues before running heavier checks.

- **Sub-phase 6.5: Constraint Checker Service**
  - **Task:** Create a `ConstraintChecker` service that orchestrates the application of the patch and runs all static checks (Ruff, Mypy, syntax).
  - **Outcome:** A service that returns a structured report of all static analysis violations found in the generated patch.

- **Sub-phase 6.6: Test Execution Runner**
  - **Task:** Implement a module that can run the target repository's `pytest` suite as a subprocess within the temporary directory.
  - **Outcome:** A function that can execute the project's tests and capture the results (pass/fail and error logs).

- **Sub-phase 6.7: Validation Endpoint**
  - **Task:** Create a `/validate-patch` endpoint that takes a patch, runs all static checks and the test suite, and returns a full validation report.
  - **Outcome:** An API that can provide a comprehensive quality report for any given patch.

- **Sub-phase 6.8: Integration with Generation**
  - **Task:** Modify the `/generate-patch` endpoint to automatically call the validation service after generation.
  - **Outcome:** The generation process now immediately provides a validation report along with the diff.

- **Sub-phase 6.9: Frontend Feedback Display**
  - **Task:** Enhance the VS Code extension to display the validation report (lint errors, type errors, test failures) in a dedicated panel.
  - **Outcome:** The user can see not only the proposed change but also a clear report of any issues it might introduce.

- **Sub-phase 6.10: "Accept" Logic**
  - **Task:** Implement the logic for the "Accept" button to apply the patch to the user's actual workspace files.
  - **Outcome:** A functional "Accept" button that permanently applies the validated patch to the user's codebase.

---

## **Phase 7: Dynamic Analysis and Graph Enrichment**

**Main Goal:** Enhance the knowledge graph with runtime information captured from executing the repository's test suite.

- **Sub-phase 7.1: Test-to-Code Mapping**
  - **Task:** Use `pytest` hooks or plugins to determine which test files cover which source code files.
  - **Outcome:** A mapping that links test files to the application code they are intended to verify.

- **Sub-phase 7.2: Coverage.py Integration**
  - **Task:** Implement a service that runs `pytest` with `coverage.py` to get line-by-line execution data.
  - **Outcome:** A function that can generate a coverage report, showing which lines of code are executed by the test suite.

- **Sub-phase 7.3: Coverage Graph Edges**
  - **Task:** Process the coverage report and add `COVERED_BY` edges between `Function` nodes and `Test` nodes in the Neo4j graph.
  - **Outcome:** The knowledge graph now explicitly links functions to the tests that execute them.

- **Sub-phase 7.4: Profiling with `sys.setprofile`**
  - **Task:** Develop a simple tracer using `sys.setprofile` to capture function call events (`call`, `return`) during test execution.
  - **Outcome:** A module that can produce a raw log of the dynamic call stack as tests are running.

- **Sub-phase 7.5: Dynamic Call Trace Processing**
  - **Task:** Write a parser that processes the raw trace log and aggregates it into a list of dynamic calls (e.g., `(caller_function, callee_function)`).
  - **Outcome:** A structured list of all function-to-function calls that occurred during the test run.

- **Sub-phase 7.6: Dynamic Call Graph Edges**
  - **Task:** Add `DYNAMICALLY_CALLS` edges to the Neo4j graph based on the processed trace data.
  - **Outcome:** The graph is enriched with a dynamic call graph, representing the actual runtime behavior of the code under test.

- **Sub-phase 7.7: Runtime Type Collection**
  - **Task:** Enhance the `sys.setprofile` tracer to inspect the types of arguments passed to functions during the `call` event.
  - **Outcome:** The tracer now captures examples of real runtime types used in function calls.

- **Sub-phase 7.8: Runtime Type Graph Enrichment**
  - **Task:** Add the collected runtime types as properties on the `Function` nodes or their parameters in the graph.
  - **Outcome:** The graph now contains valuable information about the types of data that functions actually handle at runtime.

- **Sub-phase 7.9: Dynamic Analysis Service**
  - **Task:** Create a service that orchestrates the entire dynamic analysis pipeline: runs tests, collects traces, processes data, and updates the graph.
  - **Outcome:** A single service that can be called to enrich the static graph with comprehensive dynamic data.

- **Sub-phase 7.10: Dynamic Analysis Endpoint**
  - **Task:** Create an endpoint (`/run-dynamic-analysis`) to trigger this service.
  - **Outcome:** An API that allows for on-demand enrichment of the knowledge graph with runtime information.

---

## **Phase 8: Incremental Maintenance Agent**

**Main Goal:** Implement an agent that keeps the knowledge graph synchronized with the repository as code changes are made.

- **Sub-phase 8.1: File Watcher**
  - **Task:** Implement a background process using a library like `watchdog` to monitor the repository's directory for file system events (create, delete, modify).
  - **Outcome:** A background agent that can detect when a file has been changed on disk.

- **Sub-phase 8.2: Git Diff Polling (Alternative)**
  - **Task:** Implement an alternative strategy where the agent periodically runs `git diff` to find changed files.
  - **Outcome:** A robust, Git-based mechanism for detecting file changes.

- **Sub-phase 8.3: Change Queue**
  - **Task:** Set up a simple in-memory queue where the file watcher/poller can place the paths of changed files.
  - **Outcome:** A decoupled system where file changes are queued for processing without blocking the detection mechanism.

- **Sub-phase 8.4: AST Diffing Logic**
  - **Task:** For a modified file, implement logic to parse both the old and new versions and perform a comparison of their ASTs to find changed symbols.
  - **Outcome:** A function that can identify exactly which functions or classes have been added, removed, or modified within a file.

- **Sub-phase 8.5: Invalidation Logic for Nodes**
  - **Task:** Implement the logic to delete the nodes (and their relationships) corresponding to removed or modified symbols from the Neo4j graph.
  - **Outcome:** A function that can surgically remove stale information from the graph.

- **Sub-phase 8.6: Targeted Re-Analysis**
  - **Task:** Implement logic to run the static analysis pipeline (from Phase 2) only on the changed or newly added symbols.
  - **Outcome:** A function that can generate the new structured data for the updated parts of the code.

- **Sub-phase 8.7: Targeted Graph Update**
  - **Task:** Implement the logic to take the new analysis data and write it back to the graph, creating new nodes and relationships.
  - **Outcome:** A function that can insert the updated information back into the knowledge graph.

- **Sub-phase 8.8: Maintenance Worker**
  - **Task:** Create a worker process that continuously pulls changed file paths from the queue and runs the full diff, invalidate, and update cycle.
  - **Outcome:** An autonomous worker that processes changes and keeps the graph synchronized.

- **Sub-phase 8.9: Agent Control Endpoints**
  - **Task:** Create API endpoints to start, stop, and check the status of the maintenance agent.
  - **Outcome:** Administrative control over the background maintenance process.

- **Sub-phase 8.10: Full Maintenance Loop**
  - **Task:** Integrate all components so that saving a file in the repository automatically triggers the agent and updates the graph.
  - **Outcome:** A "living" knowledge graph that stays consistent with the codebase in near real-time.

---

## **Phase 9: Learned Query Planner**

**Main Goal:** Upgrade the retrieval system with a fine-tuned model that translates natural language instructions into precise graph queries.

- **Sub-phase 9.1: Graph Query DSL Definition**
  - **Task:** Define a simple, structured Domain-Specific Language (DSL) for querying the knowledge graph (e.g., `find function with name "x" and get its callers`).
  - **Outcome:** A formal specification for a query language that the learned model will generate.

- **Sub-phase 9.2: Synthetic Instruction Generation**
  - **Task:** Write a script that traverses the graph and generates simple natural language instructions (e.g., "What calls the 'get_user' function?").
  - **Outcome:** A dataset of simple, template-based instructions.

- **Sub-phase 9.3: Synthetic Query Generation**
  - **Task:** For each synthetic instruction, automatically generate the corresponding ground-truth query in the defined DSL.
  - **Outcome:** A parallel corpus of (instruction, query) pairs, forming the initial training dataset.

- **Sub-phase 9.4: Fine-Tuning Environment Setup**
  - **Task:** Set up the environment for training a sequence-to-sequence model (e.g., Flan-T5) using a library like Hugging Face's `transformers`.
  - **Outcome:** A Python script and environment capable of running a model fine-tuning job.

- **Sub-phase 9.5: Initial Model Fine-Tuning**
  - **Task:** Run the fine-tuning script on the synthetic dataset.
  - **Outcome:** A fine-tuned model saved to disk, capable of translating simple instructions into DSL queries.

- **Sub-phase 9.6: Query Planner Service**
  - **Task:** Create a new service in the backend that loads the fine-tuned model and provides an endpoint to translate an instruction into a DSL query.
  - **Outcome:** An API that exposes the learned query planner.

- **Sub-phase 9.7: DSL Query Executor**
  - **Task:** Implement a module that can parse the generated DSL query and execute it against the Neo4j database.
  - **Outcome:** A function that can turn the model's output into actual graph query results.

- **Sub-phase 9.8: Integration with Retrieval**
  - **Task:** Replace the hybrid search mechanism in the main retrieval endpoint with the new learned query planner.
  - **Outcome:** The context retrieval process is now driven by a machine-learning model instead of keyword/vector search.

- **Sub-phase 9.9: Feedback Signal Collection**
  - **Task:** Implement logging to track whether the context retrieved by the planner ultimately leads to a successful patch (e.g., passes tests).
  - **Outcome:** A dataset of (instruction, query, success_signal) triples for future reward-based tuning.

- **Sub-phase 9.10: (Optional) Reward Tuning Loop**
  - **Task:** Implement a simple REINFORCE-style algorithm to further fine-tune the planner model using the collected success signals as a reward.
  - **Outcome:** A more intelligent query planner that optimizes for generating useful context, not just syntactically correct queries.

---

## **Phase 10: Advanced SMT Constraints and Final Evaluation**

**Main Goal:** Implement a sophisticated, SMT-based constraint-guided decoder and conduct a final, thorough evaluation of the entire system.

- **Sub-phase 10.1: Z3 Integration**
  - **Task:** Add the `z3-solver` library to `requirements.txt` and create a basic module to interact with the Z3 solver.
  - **Outcome:** The backend can now create and solve simple SMT formulas.

- **Sub-phase 10.2: Architectural Rule Definition**
  - **Task:** Define a set of repository-specific architectural rules in a configurable format (e.g., "Controllers can only call Services").
  - **Outcome:** A configuration file that formally specifies the desired software architecture.

- **Sub-phase 10.3: SMT Rule Encoder**
  - **Task:** Implement a module that translates these architectural rules into Z3 constraints.
  - **Outcome:** A function that can build a Z3 solver state representing the architectural constraints of the repository.

- **Sub-phase 10.4: SMT-based Validation**
  - **Task:** Create a validation service that checks a generated patch against the Z3 constraints. For example, if a patch adds a call from a Controller to a database model, the SMT solver would report a violation.
  - **Outcome:** A powerful validation step that can detect violations of high-level architectural patterns.

- **Sub-phase 10.5: (Advanced) Guided Decoding Hook**
  - **Task:** Implement a custom generation hook for the Hugging Face `generate` method that checks partial generations against the Z3 solver.
  - **Outcome:** A proof-of-concept for a guided decoding loop that can prune invalid code _as it is being generated_.

- **Sub-phase 10.6: Evaluation Benchmark Curation**
  - **Task:** Select 8-12 suitable open-source Python repositories for the evaluation benchmark.
  - **Outcome:** A defined set of target repositories for the final evaluation.

- **Sub-phase 10.7: Evaluation Task Creation**
  - **Task:** Manually create 150-300 evaluation tasks, including bug fixes and feature requests, based on the commit history and issue trackers of the benchmark repos.
  - **Outcome:** A comprehensive set of tasks to quantitatively measure the system's performance.

- **Sub-phase 10.8: Evaluation Harness**
  - **Task:** Write an automated script that runs all evaluation tasks against the RepoAlign system and records the results.
  - **Outcome:** An automated evaluation pipeline that can be run to benchmark the system.

- **Sub-pPhase 10.9: Metrics Calculation**
  - **Task:** Implement scripts to calculate the final performance metrics from the evaluation results (e.g., `Pass@1`, test pass rate, lint pass rate).
  - **Outcome:** A quantitative report of the system's final performance.

- **Sub-phase 10.10: Final Report and Presentation**
  - **Task:** Write the final project report, documenting the entire architecture, the journey through the phases, the final evaluation results, and key learnings. Prepare a presentation to demonstrate the system.
  - **Outcome:** The completed final year project, including all deliverables: the working system, the comprehensive report, and a presentation.
