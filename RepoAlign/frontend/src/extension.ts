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

  // --- Diff Content Provider Setup ---
  const diffContentProvider = new (class
    implements vscode.TextDocumentContentProvider
  {
    private contentStore = new Map<string, string>();
    private _onDidChange = new vscode.EventEmitter<vscode.Uri>();

    get onDidChange(): vscode.Event<vscode.Uri> {
      return this._onDidChange.event;
    }

    provideTextDocumentContent(uri: vscode.Uri): string {
      return this.contentStore.get(uri.toString()) || "";
    }

    update(
      originalUri: vscode.Uri,
      generatedUri: vscode.Uri,
      originalContent: string,
      generatedContent: string,
    ) {
      this.contentStore.set(originalUri.toString(), originalContent);
      this.contentStore.set(generatedUri.toString(), generatedContent);

      this._onDidChange.fire(originalUri);
      this._onDidChange.fire(generatedUri);
    }
  })();

  context.subscriptions.push(
    vscode.workspace.registerTextDocumentContentProvider(
      "repoalign-diff",
      diffContentProvider,
    ),
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

              // 5. Call the /generate-patch endpoint (with extended timeout for LLM processing)
              const response = await axios.post(
                "http://localhost:8000/api/v1/generate-patch",
                {
                  query: instruction,
                  original_content: originalContent,
                  file_path: filePath,
                  limit: 10,
                },
                {
                  timeout: 330000, // 330 seconds (5.5 minutes) to account for 300s backend + overhead
                },
              );

              progress.report({
                increment: 50,
                message: "Processing generated patch...",
              });

              const result = response.data;

              // 6. Define unique URIs for the diff view
              const originalUri = vscode.Uri.parse(
                `repoalign-diff:${filePath}.original`,
              );
              const generatedUri = vscode.Uri.parse(
                `repoalign-diff:${filePath}.generated`,
              );

              // 7. Update the content provider with the new content
              diffContentProvider.update(
                originalUri,
                generatedUri,
                originalContent,
                result.generated_code,
              );

              // 8. Show the diff view
              await vscode.commands.executeCommand(
                "vscode.diff",
                originalUri,
                generatedUri,
                `RepoAlign: ${filePath} (Original vs. Generated)`,
              );

              progress.report({
                increment: 100,
                message: "Patch displayed.",
              });

              // 9. Show quick pick with Accept/Reject options (similar to merge conflicts)
              const userAction = await vscode.window.showQuickPick(
                [
                  {
                    label: "$(check) Accept Patch",
                    description: "Apply the generated code changes to the file",
                    value: "accept",
                  },
                  {
                    label: "$(x) Reject Patch",
                    description:
                      "Discard the generated code and keep the original",
                    value: "reject",
                  },
                ],
                {
                  placeHolder:
                    "Review the diff and choose: Accept or Reject the generated patch",
                  canPickMany: false,
                },
              );

              if (userAction?.value === "accept") {
                try {
                  // Apply the generated code to the active editor
                  const edit = new vscode.WorkspaceEdit();
                  const fullRange = new vscode.Range(
                    editor.document.positionAt(0),
                    editor.document.positionAt(originalContent.length),
                  );
                  edit.replace(
                    editor.document.uri,
                    fullRange,
                    result.generated_code,
                  );

                  await vscode.workspace.applyEdit(edit);
                  
                  // Close the diff view
                  await vscode.commands.executeCommand(
                    "workbench.action.closeActiveEditor",
                  );
                  
                  // Focus back on the original file
                  await vscode.window.showTextDocument(editor.document);
                  
                  vscode.window.showInformationMessage(
                    "✓ Patch accepted and applied to the file.",
                  );
                } catch (applyError) {
                  vscode.window.showErrorMessage(
                    "Failed to apply the patch to the file.",
                  );
                  console.error("Apply error:", applyError);
                }
              } else if (userAction?.value === "reject") {
                // Close the diff view
                await vscode.commands.executeCommand(
                  "workbench.action.closeActiveEditor",
                );
                
                // Focus back on the original file
                await vscode.window.showTextDocument(editor.document);
                
                vscode.window.showInformationMessage("✗ Patch rejected.");
              }
            } catch (error) {
              vscode.window.showErrorMessage(
                "Failed to generate code patch. See console for details.",
              );
              console.error("Patch generation error:", error);
            }
          },
        );
      } catch (error) {
        vscode.window.showErrorMessage(
          "An error occurred while running the command.",
        );
        console.error("Command execution error:", error);
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
