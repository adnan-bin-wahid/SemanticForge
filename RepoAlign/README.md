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

The backend is a containerized FastAPI application managed by Docker Compose.

1.  **Open a terminal** at the root of the `RepoAlign` project directory.

2.  **Build and run the backend container** using the following command:

    ```bash
    docker compose up --build
    ```

    This command will build the Docker image for the backend, download any necessary base images, and start the service. You should see logs from the `uvicorn` server in your terminal.

    > **Note:** Keep this terminal running. Closing it will stop the backend service.

### 2. Run the Frontend Extension

The frontend is a VS Code extension that you will launch in a separate development environment.

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
4.  **Open the frontend project in VS Code.** You can do this directly from your terminal:

    ```bash
    code .
    ```

4.  Once the `frontend` folder is open in a new VS Code window, **press `F5`**. This will compile the TypeScript code and launch a new "Extension Development Host" window with the RepoAlign extension activated.

### 3. Verify the Setup

Now, let's test that the frontend and backend are communicating correctly.

1.  In the new **"Extension Development Host"** VS Code window (the one that appeared after you pressed `F5`), open the **Command Palette** (`Ctrl+Shift+P` or `Cmd+Shift+P`).

2.  Type `RepoAlign` and select the command **"RepoAlign: Health Check"**.

3.  If everything is working correctly, a notification will appear in the bottom-right corner with the message: **"RepoAlign Backend is running!"**

You have now successfully set up and run the RepoAlign project.
