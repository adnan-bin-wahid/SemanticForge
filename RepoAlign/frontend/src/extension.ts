import * as vscode from "vscode";
import axios from "axios";

// Define the structure for file content payload
interface FileContent {
  path: string;
  content: string;
}

export function activate(context: vscode.ExtensionContext) {
  console.log(
    'Congratulations, your extension "repoalign-frontend" is now active!',
  );

  // Command for backend health check
  let healthCheckDisposable = vscode.commands.registerCommand(
    "repoalign.healthCheck",
    async () => {
      try {
        const response = await axios.get("http://localhost:8000/api/v1/health");
        if (response.data.status === "ok") {
          vscode.window.showInformationMessage("RepoAlign Backend is running!");
        } else {
          vscode.window.showErrorMessage("RepoAlign Backend status is not ok.");
        }
      } catch (error) {
        vscode.window.showErrorMessage(
          "Failed to connect to RepoAlign Backend. Is it running?",
        );
        console.error(error);
      }
    },
  );

  // Command to analyze the current workspace
  let analyzeWorkspaceDisposable = vscode.commands.registerCommand(
    "repoalign.analyzeWorkspace",
    async () => {
      vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: "RepoAlign: Analyzing workspace...",
          cancellable: false,
        },
        async (progress) => {
          try {
            progress.report({
              increment: 0,
              message: "Finding Python files...",
            });

            // 1. Find all Python files in the workspace
            const pythonFiles = await vscode.workspace.findFiles(
              "**/*.py",
              "**/node_modules/**",
            );
            if (pythonFiles.length === 0) {
              vscode.window.showInformationMessage(
                "No Python files found in this workspace.",
              );
              return;
            }

            progress.report({
              increment: 20,
              message: "Reading file contents...",
            });

            // 2. Read the content of each file
            const fileContents: FileContent[] = await Promise.all(
              pythonFiles.map(async (uri) => {
                const document = await vscode.workspace.openTextDocument(uri);
                return {
                  path: vscode.workspace.asRelativePath(uri),
                  content: document.getText(),
                };
              }),
            );

            progress.report({
              increment: 50,
              message:
                "Sending data to backend for analysis and graph construction...",
            });

            // 3. Send the data to the backend for graph construction
            await axios.post("http://localhost:8000/api/v1/build-graph", {
              files: fileContents,
            });

            progress.report({
              increment: 100,
              message: "Graph construction complete.",
            });

            vscode.window.showInformationMessage(
              "RepoAlign: Knowledge graph built successfully!",
            );
          } catch (error) {
            vscode.window.showErrorMessage(
              "An error occurred during workspace analysis.",
            );
            console.error(error);
          }
        },
      );
    },
  );

  context.subscriptions.push(healthCheckDisposable, analyzeWorkspaceDisposable);
}

export function deactivate() {}
