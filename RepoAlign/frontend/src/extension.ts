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

  // Command to generate a code patch based on user instruction
  let generatePatchDisposable = vscode.commands.registerCommand(
    "repoalign.generatePatch",
    async () => {
      try {
        // 1. Get the active text editor
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
          vscode.window.showErrorMessage(
            "Please open a file in the editor first.",
          );
          return;
        }

        // 2. Get the current file content
        const originalContent = editor.document.getText();
        const filePath = vscode.workspace.asRelativePath(editor.document.uri);

        // 3. Show input box for user's instruction
        const instruction = await vscode.window.showInputBox({
          title: "RepoAlign: Code Generation",
          placeHolder:
            'e.g., "Add error handling to this function" or "Improve documentation"',
          prompt:
            "Enter your instruction for improving the code in the current file:",
          ignoreFocusOut: true,
        });

        if (!instruction || instruction.trim() === "") {
          vscode.window.showWarningMessage("No instruction provided.");
          return;
        }

        // 4. Show progress while calling the backend
        vscode.window.withProgress(
          {
            location: vscode.ProgressLocation.Notification,
            title: "RepoAlign: Generating patch...",
            cancellable: false,
          },
          async (progress) => {
            try {
              progress.report({
                increment: 0,
                message: "Sending request to backend...",
              });

              // 5. Call the /generate-patch endpoint
              const response = await axios.post(
                "http://localhost:8000/api/v1/generate-patch",
                {
                  query: instruction,
                  original_content: originalContent,
                  file_path: filePath,
                  limit: 10,
                },
              );

              progress.report({
                increment: 50,
                message: "Processing generated patch...",
              });

              const result = response.data;

              // 6. Create output channel to display results
              const outputChannel =
                vscode.window.createOutputChannel("RepoAlign");
              outputChannel.clear();
              outputChannel.appendLine(
                "=== RepoAlign Patch Generation Results ===",
              );
              outputChannel.appendLine("");
              outputChannel.appendLine(`Query: ${result.query}`);
              outputChannel.appendLine(`File: ${result.file_path}`);
              outputChannel.appendLine("");
              outputChannel.appendLine("--- Statistics ---");
              outputChannel.appendLine(
                `Lines Added: ${result.stats.lines_added}`,
              );
              outputChannel.appendLine(
                `Lines Removed: ${result.stats.lines_removed}`,
              );
              outputChannel.appendLine(
                `Lines Modified: ${result.stats.lines_modified}`,
              );
              outputChannel.appendLine(
                `Total Changes: ${result.stats.total_changes}`,
              );
              outputChannel.appendLine(
                `Similarity Ratio: ${(result.stats.similarity_ratio * 100).toFixed(2)}%`,
              );
              outputChannel.appendLine("");
              outputChannel.appendLine("--- Generated Diff ---");
              outputChannel.appendLine(result.unified_diff);
              outputChannel.appendLine("");
              outputChannel.appendLine("--- Generated Code ---");
              outputChannel.appendLine(result.generated_code);
              outputChannel.show();

              progress.report({
                increment: 100,
                message: "Patch generated successfully!",
              });

              vscode.window.showInformationMessage(
                `Patch generated! View results in the RepoAlign output channel.`,
              );
            } catch (error: any) {
              vscode.window.showErrorMessage(
                `Failed to generate patch: ${error.response?.data?.detail || error.message}`,
              );
              console.error("Patch generation error:", error);
            }
          },
        );
      } catch (error) {
        vscode.window.showErrorMessage("An error occurred during patch generation.");
        console.error(error);
      }
    },
  );

  context.subscriptions.push(
    healthCheckDisposable,
    analyzeWorkspaceDisposable,
    generatePatchDisposable,
  );
}

export function deactivate() {}
