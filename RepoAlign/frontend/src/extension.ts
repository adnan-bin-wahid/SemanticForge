import * as vscode from "vscode";
import axios from "axios";
import {
  createValidationPanel,
  updateValidationPanel,
} from "./validationPanel";

// Define the structure for file content payload
interface FileContent {
  path: string;
  content: string;
}

interface WorkspaceValidationResult {
  status: "ready" | "no-workspace" | "not-git-repo" | "no-python-files";
  message: string;
  pythonFiles: vscode.Uri[];
  workspaceFolder?: vscode.WorkspaceFolder;
}

const BACKEND_URL = "http://localhost:8000/api/v1";
const WELCOME_SHOWN_KEY = "repoalign.welcomeShown";

function isPythonDocument(document: vscode.TextDocument): boolean {
  return (
    document.uri.scheme === "file" &&
    (document.languageId === "python" || document.uri.fsPath.endsWith(".py"))
  );
}

function getWorkspaceId(): string | undefined {
  return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
}

async function sendWorkspaceFileChange(
  uri: vscode.Uri,
  changeType: "added" | "modified" | "deleted",
  content?: string,
) {
  const filePath = vscode.workspace.asRelativePath(uri, false);

  await axios.post(`${BACKEND_URL}/workspace-file-change`, {
    file_path: filePath,
    change_type: changeType,
    content,
    workspace_id: getWorkspaceId(),
  });
}

async function hasPythonWorkspace(): Promise<boolean> {
  if (!vscode.workspace.workspaceFolders?.length) {
    return false;
  }

  const pythonFiles = await vscode.workspace.findFiles(
    "**/*.py",
    "{**/.git/**,**/.venv/**,**/venv/**,**/__pycache__/**,**/node_modules/**}",
    1,
  );

  return pythonFiles.length > 0;
}

async function hasGitRepository(
  workspaceFolder: vscode.WorkspaceFolder,
): Promise<boolean> {
  try {
    await vscode.workspace.fs.stat(
      vscode.Uri.joinPath(workspaceFolder.uri, ".git"),
    );
    return true;
  } catch {
    return false;
  }
}

async function validateWorkspace(): Promise<WorkspaceValidationResult> {
  const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
  if (!workspaceFolder) {
    return {
      status: "no-workspace",
      message: "RepoAlign needs an opened workspace folder before analysis.",
      pythonFiles: [],
    };
  }

  if (!(await hasGitRepository(workspaceFolder))) {
    return {
      status: "not-git-repo",
      message: "RepoAlign needs the opened workspace to be a Git repository.",
      pythonFiles: [],
      workspaceFolder,
    };
  }

  const pythonFiles = await vscode.workspace.findFiles(
    "**/*.py",
    "{**/.git/**,**/.venv/**,**/venv/**,**/__pycache__/**,**/node_modules/**,**/dist/**,**/build/**}",
  );

  if (pythonFiles.length === 0) {
    return {
      status: "no-python-files",
      message: "RepoAlign found no Python files in this workspace.",
      pythonFiles,
      workspaceFolder,
    };
  }

  return {
    status: "ready",
    message: `RepoAlign workspace is ready: ${pythonFiles.length} Python file(s) found in a Git repository.`,
    pythonFiles,
    workspaceFolder,
  };
}

function reportWorkspaceValidation(result: WorkspaceValidationResult): void {
  if (result.status === "ready") {
    vscode.window.showInformationMessage(result.message);
    return;
  }

  vscode.window.showWarningMessage(result.message);
}

function getWelcomeHtml(webview: vscode.Webview): string {
  const nonce = `${Date.now()}-${Math.random().toString(16).slice(2)}`;

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta
    http-equiv="Content-Security-Policy"
    content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}';"
  >
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>RepoAlign Welcome</title>
  <style>
    body {
      color: var(--vscode-foreground);
      background: var(--vscode-editor-background);
      font-family: var(--vscode-font-family);
      margin: 0;
      padding: 28px;
      line-height: 1.5;
    }

    main {
      max-width: 760px;
    }

    h1 {
      font-size: 26px;
      font-weight: 600;
      margin: 0 0 8px;
    }

    p {
      color: var(--vscode-descriptionForeground);
      margin: 0 0 18px;
    }

    .steps {
      border: 1px solid var(--vscode-panel-border);
      border-radius: 8px;
      margin: 20px 0;
      overflow: hidden;
    }

    .step {
      border-bottom: 1px solid var(--vscode-panel-border);
      padding: 14px 16px;
    }

    .step:last-child {
      border-bottom: 0;
    }

    .step strong {
      display: block;
      color: var(--vscode-foreground);
      margin-bottom: 2px;
    }

    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 20px;
    }

    button {
      background: var(--vscode-button-background);
      color: var(--vscode-button-foreground);
      border: 0;
      border-radius: 4px;
      cursor: pointer;
      font: inherit;
      padding: 8px 12px;
    }

    button:hover {
      background: var(--vscode-button-hoverBackground);
    }

    button.secondary {
      background: var(--vscode-button-secondaryBackground);
      color: var(--vscode-button-secondaryForeground);
    }

    button.secondary:hover {
      background: var(--vscode-button-secondaryHoverBackground);
    }
  </style>
</head>
<body>
  <main>
    <h1>RepoAlign</h1>
    <p>Set up repository-aware code generation and live graph sync for this Python workspace.</p>

    <section class="steps">
      <div class="step">
        <strong>1. Check backend</strong>
        Confirm the local FastAPI backend is reachable.
      </div>
      <div class="step">
        <strong>2. Analyze workspace</strong>
        Build the initial knowledge graph from the opened Python project.
      </div>
      <div class="step">
        <strong>3. Work normally</strong>
        Saving Python files keeps the graph synchronized automatically.
      </div>
      <div class="step">
        <strong>4. Generate patches</strong>
        Open a Python file and run RepoAlign's patch generation command.
      </div>
    </section>

    <div class="actions">
      <button data-command="validate">Validate Workspace</button>
      <button data-command="health">Health Check</button>
      <button data-command="analyze">Analyze Workspace</button>
      <button data-command="generate">Generate Patch</button>
      <button class="secondary" data-command="hide">Do Not Show Again</button>
    </div>
  </main>

  <script nonce="${nonce}">
    const vscode = acquireVsCodeApi();
    document.querySelectorAll("button[data-command]").forEach((button) => {
      button.addEventListener("click", () => {
        vscode.postMessage({ command: button.dataset.command });
      });
    });
  </script>
</body>
</html>`;
}

function showWelcomePanel(context: vscode.ExtensionContext) {
  const panel = vscode.window.createWebviewPanel(
    "repoalignWelcome",
    "RepoAlign Welcome",
    vscode.ViewColumn.One,
    {
      enableScripts: true,
      retainContextWhenHidden: true,
    },
  );

  panel.webview.html = getWelcomeHtml(panel.webview);
  panel.webview.onDidReceiveMessage(async (message) => {
    switch (message.command) {
      case "validate":
        await vscode.commands.executeCommand("repoalign.validateWorkspace");
        break;
      case "health":
        await vscode.commands.executeCommand("repoalign.healthCheck");
        break;
      case "analyze":
        await vscode.commands.executeCommand("repoalign.analyzeWorkspace");
        break;
      case "generate":
        await vscode.commands.executeCommand("repoalign.generatePatch");
        break;
      case "hide":
        await context.workspaceState.update(WELCOME_SHOWN_KEY, true);
        panel.dispose();
        vscode.window.showInformationMessage(
          "RepoAlign welcome will stay hidden for this workspace.",
        );
        break;
    }
  });
}

export function activate(context: vscode.ExtensionContext) {
  console.log(
    'Congratulations, your extension "repoalign-frontend" is now active!',
  );

  // Validation panel for displaying patch validation results
  let validationPanel: vscode.WebviewPanel | undefined;

  const showWelcomeDisposable = vscode.commands.registerCommand(
    "repoalign.showWelcome",
    async () => {
      showWelcomePanel(context);
      await context.workspaceState.update(WELCOME_SHOWN_KEY, true);
    },
  );

  const validateWorkspaceDisposable = vscode.commands.registerCommand(
    "repoalign.validateWorkspace",
    async () => {
      const result = await validateWorkspace();
      reportWorkspaceValidation(result);
      return result;
    },
  );

  // Command for backend health check
  let healthCheckDisposable = vscode.commands.registerCommand(
    "repoalign.healthCheck",
    async () => {
      try {
        const response = await axios.get(`${BACKEND_URL}/health`);
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
      const validation = await validateWorkspace();
      if (validation.status !== "ready") {
        reportWorkspaceValidation(validation);
        return;
      }

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

            const pythonFiles = validation.pythonFiles;

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
            await axios.post(`${BACKEND_URL}/build-graph`, {
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
              // Include repo path for validation
              const workspaceFolderPath =
                vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;

              // Convert Windows path to Docker path for backend
              // The backend runs in Docker where test-project is mounted at /app/test-project
              let dockerRepoPath: string | undefined = undefined;
              if (workspaceFolderPath) {
                // Check if path contains 'test-project' - if so, use Docker path
                if (workspaceFolderPath.includes("test-project")) {
                  dockerRepoPath = "/app/test-project";
                } else {
                  // Otherwise use the workspace path as-is
                  dockerRepoPath = workspaceFolderPath;
                }
              }

              const response = await axios.post(
                `${BACKEND_URL}/generate-patch`,
                {
                  query: instruction,
                  original_content: originalContent,
                  file_path: filePath,
                  limit: 10,
                  // Optional validation parameters (only if workspace available)
                  ...(dockerRepoPath && {
                    repo_path: dockerRepoPath,
                    file_relative_path: filePath,
                    run_tests: false, // Disable tests by default for speed
                  }),
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

              // 8.5 Display validation panel if validation data is available
              if (result.validation) {
                // Create or reuse validation panel
                if (!validationPanel) {
                  validationPanel = createValidationPanel(context);

                  // Handle panel disposal
                  validationPanel.onDidDispose(() => {
                    validationPanel = undefined;
                  });
                } else {
                  validationPanel.reveal(vscode.ViewColumn.Beside);
                }

                // Update panel with validation data
                updateValidationPanel(
                  validationPanel,
                  result.validation,
                  filePath,
                );
              }

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
                  // 1. Check validation status if available
                  if (
                    result.validation &&
                    result.validation.overall_status === "failed"
                  ) {
                    // Validation failed - ask user to confirm override
                    const confirmOverride =
                      await vscode.window.showWarningMessage(
                        `⚠ Validation failed: ${result.validation.total_errors} error(s), ${result.validation.total_warnings} warning(s). Apply patch anyway?`,
                        { modal: true },
                        "Yes, Apply",
                        "No, Cancel",
                      );

                    if (confirmOverride !== "Yes, Apply") {
                      vscode.window.showInformationMessage(
                        "Patch application cancelled due to validation failures.",
                      );
                      return;
                    }
                  }

                  // 2. Apply the generated code to the active editor
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

                  // 3. Close the diff view
                  await vscode.commands.executeCommand(
                    "workbench.action.closeActiveEditor",
                  );

                  // 4. Focus back on the original file
                  await vscode.window.showTextDocument(editor.document);

                  // 5. Show success message with validation status
                  const validationMsg =
                    result.validation &&
                    result.validation.overall_status === "passed"
                      ? " (Validation passed)"
                      : result.validation
                        ? " (Validation had issues, but you confirmed)"
                        : "";
                  vscode.window.showInformationMessage(
                    `✓ Patch accepted and applied to the file.${validationMsg}`,
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
    showWelcomeDisposable,
    validateWorkspaceDisposable,
    healthCheckDisposable,
    analyzeWorkspaceDisposable,
    generatePatchDisposable,
    vscode.workspace.onDidSaveTextDocument(async (document) => {
      if (!isPythonDocument(document)) {
        return;
      }

      try {
        await sendWorkspaceFileChange(
          document.uri,
          "modified",
          document.getText(),
        );
        console.log(`RepoAlign synced modified file: ${document.uri.fsPath}`);
      } catch (error) {
        console.error("RepoAlign failed to sync saved file:", error);
      }
    }),
    vscode.workspace.onDidCreateFiles(async (event) => {
      for (const uri of event.files) {
        if (!uri.fsPath.endsWith(".py")) {
          continue;
        }

        try {
          const document = await vscode.workspace.openTextDocument(uri);
          await sendWorkspaceFileChange(uri, "added", document.getText());
          console.log(`RepoAlign synced added file: ${uri.fsPath}`);
        } catch (error) {
          console.error("RepoAlign failed to sync created file:", error);
        }
      }
    }),
    vscode.workspace.onDidDeleteFiles(async (event) => {
      for (const uri of event.files) {
        if (!uri.fsPath.endsWith(".py")) {
          continue;
        }

        try {
          await sendWorkspaceFileChange(uri, "deleted");
          console.log(`RepoAlign synced deleted file: ${uri.fsPath}`);
        } catch (error) {
          console.error("RepoAlign failed to sync deleted file:", error);
        }
      }
    }),
  );

  void (async () => {
    if (context.workspaceState.get<boolean>(WELCOME_SHOWN_KEY)) {
      return;
    }

    if (await hasPythonWorkspace()) {
      showWelcomePanel(context);
      await context.workspaceState.update(WELCOME_SHOWN_KEY, true);
    }
  })();
}

export function deactivate() {}
