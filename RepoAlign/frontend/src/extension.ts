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
              message: "Sending data to backend for analysis...",
            });

            // 3. Send the data to the backend
            const response = await axios.post(
              "http://localhost:8000/api/v1/ingest",
              {
                files: fileContents,
              },
            );

            progress.report({
              increment: 80,
              message: "Displaying results...",
            });

            // 4. Display the results in a new document
            const analysisResult = JSON.stringify(response.data, null, 2);
            const document = await vscode.workspace.openTextDocument({
              content: analysisResult,
              language: "json",
            });
            await vscode.window.showTextDocument(document, {
              viewColumn: vscode.ViewColumn.Beside,
              preview: false,
            });

            progress.report({ increment: 100, message: "Analysis complete." });
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
