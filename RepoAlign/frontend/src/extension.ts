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

interface IndexingReadResult {
  files: FileContent[];
  failedReads: Array<{ path: string; message: string }>;
}

type GraphIndexStatus = "indexed" | "failed" | "cancelled";

interface IndexingState {
  workspaceId: string;
  workspaceName: string;
  lastIndexedAt: string;
  discoveredFileCount: number;
  indexedFileCount: number;
  failedReadCount: number;
  backendUrl: string;
  graphStatus: GraphIndexStatus;
  durationSeconds?: number;
  lastError?: string;
}

interface WorkspaceValidationResult {
  status: "ready" | "no-workspace" | "not-git-repo" | "no-python-files";
  message: string;
  pythonFiles: vscode.Uri[];
  workspaceFolder?: vscode.WorkspaceFolder;
}

type ValidationMode = "off" | "basic" | "full";

interface RepoAlignConfig {
  backendUrl: string;
  excludedFolders: string[];
  excludedGlobs: string[];
  similarityThreshold: number;
  modelName: string;
  validationMode: ValidationMode;
  autoSyncOnSave: boolean;
}

interface ReadinessService {
  status: "ok" | "error" | "unknown";
  message: string;
  collections?: number;
  models?: string[];
}

interface ReadinessResponse {
  status: "ready" | "not_ready";
  ready: boolean;
  model: string;
  services: Record<string, ReadinessService>;
}

const WELCOME_SHOWN_KEY = "repoalign.welcomeShown";
const INDEXING_STATE_KEY = "repoalign.indexingState";
const outputChannel = vscode.window.createOutputChannel("RepoAlign");

function getRepoAlignConfig(): RepoAlignConfig {
  const config = vscode.workspace.getConfiguration("repoalign");
  const backendUrl = config
    .get<string>("backendUrl", "http://localhost:8000/api/v1")
    .replace(/\/+$/, "");

  return {
    backendUrl,
    excludedFolders: config.get<string[]>("excludedFolders", [
      ".git",
      ".venv",
      "venv",
      "__pycache__",
      "node_modules",
      "dist",
      "build",
      ".pytest_cache",
      ".mypy_cache",
      ".ruff_cache",
      ".tox",
      ".nox",
      "htmlcov",
      "*.egg-info",
    ]),
    excludedGlobs: config.get<string[]>("excludedGlobs", [
      "**/*.pyc",
      "**/*.pyo",
      "**/.coverage",
      "**/.coverage.*",
      "**/coverage.xml",
      "**/coverage.json",
      "**/htmlcov/**",
      "**/*_pb2.py",
      "**/*_pb2_grpc.py",
      "**/generated/**",
      "**/*generated*.py",
    ]),
    similarityThreshold: config.get<number>("similarityThreshold", 0.72),
    modelName: config.get<string>("modelName", "tinyllama"),
    validationMode: config.get<ValidationMode>("validationMode", "basic"),
    autoSyncOnSave: config.get<boolean>("autoSyncOnSave", true),
  };
}

function getFolderExcludeGlobs(folders: string[]): string[] {
  return folders
    .filter(Boolean)
    .flatMap((folder) => {
      if (folder.includes("/") || folder.includes("\\")) {
        return [folder.replace(/\\/g, "/")];
      }

      return [`**/${folder}/**`];
    });
}

function getExcludeGlob(extraFolders: string[] = []): string {
  const config = getRepoAlignConfig();
  const folders = Array.from(
    new Set([...config.excludedFolders, ...extraFolders]),
  ).filter(Boolean);
  const globs = Array.from(
    new Set([...getFolderExcludeGlobs(folders), ...config.excludedGlobs]),
  ).filter(Boolean);

  return `{${globs.join(",")}}`;
}

function escapeRegExp(value: string): string {
  return value.replace(/[|\\{}()[\]^$+?.]/g, "\\$&");
}

function globToRegExp(glob: string): RegExp {
  const normalized = glob.replace(/\\/g, "/");
  let pattern = "";

  for (let index = 0; index < normalized.length; index += 1) {
    const char = normalized[index];
    const next = normalized[index + 1];

    if (char === "*" && next === "*") {
      pattern += ".*";
      index += 1;
    } else if (char === "*") {
      pattern += "[^/]*";
    } else if (char === "?") {
      pattern += "[^/]";
    } else {
      pattern += escapeRegExp(char);
    }
  }

  return new RegExp(`^${pattern}$`);
}

function matchesExcludedGlob(
  relativePath: string,
  basename: string,
  globs: string[],
): boolean {
  return globs.some((glob) => {
    const normalized = glob.replace(/\\/g, "/");
    const matcher = globToRegExp(normalized);

    if (matcher.test(relativePath)) {
      return true;
    }

    return !normalized.includes("/") && matcher.test(basename);
  });
}

function shouldSyncUri(uri: vscode.Uri): boolean {
  const config = getRepoAlignConfig();
  const relativePath = vscode.workspace.asRelativePath(uri, false).replace(/\\/g, "/");
  const pathParts = relativePath.split("/").filter(Boolean);
  const basename = pathParts[pathParts.length - 1] ?? "";

  const excludedByFolder = config.excludedFolders.some((folder) =>
    pathParts.includes(folder),
  );

  const excludedGlobs = [
    ...getFolderExcludeGlobs(config.excludedFolders),
    ...config.excludedGlobs,
  ];

  return (
    !excludedByFolder &&
    !matchesExcludedGlob(relativePath, basename, excludedGlobs)
  );
}

function isPythonDocument(document: vscode.TextDocument): boolean {
  return (
    document.uri.scheme === "file" &&
    (document.languageId === "python" || document.uri.fsPath.endsWith(".py"))
  );
}

function getWorkspaceId(): string | undefined {
  return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
}

function getIndexingState(
  context: vscode.ExtensionContext,
): IndexingState | undefined {
  return context.workspaceState.get<IndexingState>(INDEXING_STATE_KEY);
}

async function saveIndexingState(
  context: vscode.ExtensionContext,
  state: IndexingState,
): Promise<void> {
  await context.workspaceState.update(INDEXING_STATE_KEY, state);
}

async function clearIndexingState(
  context: vscode.ExtensionContext,
): Promise<void> {
  await context.workspaceState.update(INDEXING_STATE_KEY, undefined);
}

function createIndexingState(
  validation: WorkspaceValidationResult,
  graphStatus: GraphIndexStatus,
  values: {
    discoveredFileCount: number;
    indexedFileCount: number;
    failedReadCount: number;
    durationSeconds?: number;
    lastError?: string;
  },
): IndexingState {
  const config = getRepoAlignConfig();

  return {
    workspaceId: getWorkspaceId() ?? "unknown-workspace",
    workspaceName: validation.workspaceFolder?.name ?? "workspace",
    lastIndexedAt: new Date().toISOString(),
    discoveredFileCount: values.discoveredFileCount,
    indexedFileCount: values.indexedFileCount,
    failedReadCount: values.failedReadCount,
    backendUrl: config.backendUrl,
    graphStatus,
    durationSeconds: values.durationSeconds,
    lastError: values.lastError,
  };
}

function formatIndexingState(state: IndexingState): string {
  const indexedAt = new Date(state.lastIndexedAt).toLocaleString();
  const duration =
    typeof state.durationSeconds === "number"
      ? `${state.durationSeconds.toFixed(1)}s`
      : "n/a";

  return [
    `Workspace: ${state.workspaceName}`,
    `Status: ${state.graphStatus}`,
    `Last indexed: ${indexedAt}`,
    `Backend: ${state.backendUrl}`,
    `Discovered files: ${state.discoveredFileCount}`,
    `Indexed files: ${state.indexedFileCount}`,
    `Failed reads: ${state.failedReadCount}`,
    `Duration: ${duration}`,
    ...(state.lastError ? [`Last error: ${state.lastError}`] : []),
  ].join("\n");
}

function reportIndexingState(state: IndexingState | undefined): void {
  if (!state) {
    vscode.window.showInformationMessage(
      "RepoAlign has not indexed this workspace yet. Run RepoAlign: Analyze Workspace.",
    );
    return;
  }

  outputChannel.clear();
  outputChannel.appendLine("RepoAlign Indexing Status");
  outputChannel.appendLine("");
  outputChannel.appendLine(formatIndexingState(state));
  outputChannel.show(true);

  vscode.window.showInformationMessage(
    `RepoAlign graph status: ${state.graphStatus}. Indexed ${state.indexedFileCount}/${state.discoveredFileCount} file(s).`,
  );
}

function appendOutputSection(title: string, lines: string[] = []): void {
  outputChannel.appendLine("");
  outputChannel.appendLine(title);
  outputChannel.appendLine("-".repeat(title.length));
  for (const line of lines) {
    outputChannel.appendLine(line);
  }
}

function notifyRepoAlignError(title: string, error: unknown): void {
  const message = getErrorMessage(error);
  appendOutputSection(title, [message]);
  outputChannel.show(true);
  vscode.window.showErrorMessage(`${title}: ${message}`);
}

async function sendWorkspaceFileChange(
  uri: vscode.Uri,
  changeType: "added" | "modified" | "deleted",
  content?: string,
) {
  const filePath = vscode.workspace.asRelativePath(uri, false);

  await axios.post(`${getRepoAlignConfig().backendUrl}/workspace-file-change`, {
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
    getExcludeGlob(),
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
    getExcludeGlob(),
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

function writeReadinessReport(readiness: ReadinessResponse): void {
  outputChannel.clear();
  outputChannel.appendLine("RepoAlign Backend Readiness");
  outputChannel.appendLine(`Overall: ${readiness.status}`);
  outputChannel.appendLine(`Model: ${readiness.model}`);
  outputChannel.appendLine("");

  for (const [name, service] of Object.entries(readiness.services)) {
    outputChannel.appendLine(`${name}: ${service.status}`);
    outputChannel.appendLine(`  ${service.message}`);

    if (typeof service.collections === "number") {
      outputChannel.appendLine(`  collections: ${service.collections}`);
    }

    if (service.models?.length) {
      outputChannel.appendLine(`  models: ${service.models.join(", ")}`);
    }
  }
}

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data
      ? JSON.stringify(error.response.data)
      : error.message;
    return detail;
  }

  return error instanceof Error ? error.message : String(error);
}

function writeIndexingReport(lines: string[]): void {
  outputChannel.clear();
  outputChannel.appendLine("RepoAlign Initial Repository Indexing");
  outputChannel.appendLine("");
  for (const line of lines) {
    outputChannel.appendLine(line);
  }
}

async function readWorkspaceFilesForIndexing(
  uris: vscode.Uri[],
  progress: vscode.Progress<{ increment?: number; message?: string }>,
  token: vscode.CancellationToken,
): Promise<IndexingReadResult> {
  const files: FileContent[] = [];
  const failedReads: Array<{ path: string; message: string }> = [];
  const total = Math.max(uris.length, 1);

  for (let index = 0; index < uris.length; index += 1) {
    if (token.isCancellationRequested) {
      break;
    }

    const uri = uris[index];
    const path = vscode.workspace.asRelativePath(uri, false);

    progress.report({
      increment: 30 / total,
      message: `Reading ${index + 1}/${uris.length}: ${path}`,
    });

    try {
      const document = await vscode.workspace.openTextDocument(uri);
      files.push({
        path,
        content: document.getText(),
      });
    } catch (error) {
      failedReads.push({
        path,
        message: getErrorMessage(error),
      });
    }
  }

  return { files, failedReads };
}

async function runInitialRepositoryIndexing(
  context: vscode.ExtensionContext,
  validation: WorkspaceValidationResult,
  progress: vscode.Progress<{ increment?: number; message?: string }>,
  token: vscode.CancellationToken,
): Promise<void> {
  const startedAt = Date.now();
  const config = getRepoAlignConfig();
  const workspaceName = validation.workspaceFolder?.name ?? "workspace";
  const pythonFiles = validation.pythonFiles;

  writeIndexingReport([
    `Workspace: ${workspaceName}`,
    `Backend: ${config.backendUrl}`,
    `Python files discovered: ${pythonFiles.length}`,
    `Excluded folders: ${config.excludedFolders.join(", ")}`,
    `Excluded globs: ${config.excludedGlobs.join(", ")}`,
  ]);

  progress.report({
    increment: 5,
    message: "Checking backend readiness...",
  });

  const readiness = await runBackendReadinessCheck();
  if (!readiness?.ready) {
    throw new Error("Backend readiness check failed. See RepoAlign output for details.");
  }

  if (token.isCancellationRequested) {
    await saveIndexingState(
      context,
      createIndexingState(validation, "cancelled", {
        discoveredFileCount: pythonFiles.length,
        indexedFileCount: 0,
        failedReadCount: 0,
      }),
    );
    vscode.window.showWarningMessage("RepoAlign indexing cancelled.");
    return;
  }

  progress.report({
    increment: 10,
    message: `${pythonFiles.length} Python file(s) ready for indexing.`,
  });

  const readResult = await readWorkspaceFilesForIndexing(
    pythonFiles,
    progress,
    token,
  );

  if (token.isCancellationRequested) {
    await saveIndexingState(
      context,
      createIndexingState(validation, "cancelled", {
        discoveredFileCount: pythonFiles.length,
        indexedFileCount: readResult.files.length,
        failedReadCount: readResult.failedReads.length,
      }),
    );
    writeIndexingReport([
      `Workspace: ${workspaceName}`,
      "Status: cancelled while reading files",
      `Files read before cancellation: ${readResult.files.length}/${pythonFiles.length}`,
      `Failed reads: ${readResult.failedReads.length}`,
    ]);
    vscode.window.showWarningMessage("RepoAlign indexing cancelled.");
    outputChannel.show(true);
    return;
  }

  if (readResult.files.length === 0) {
    throw new Error("No readable Python files were available for indexing.");
  }

  progress.report({
    increment: 15,
    message: `Sending ${readResult.files.length} file(s) to backend...`,
  });

  const response = await axios.post(`${config.backendUrl}/build-graph`, {
    files: readResult.files,
  });

  if (token.isCancellationRequested) {
    await saveIndexingState(
      context,
      createIndexingState(validation, "cancelled", {
        discoveredFileCount: pythonFiles.length,
        indexedFileCount: readResult.files.length,
        failedReadCount: readResult.failedReads.length,
      }),
    );
    vscode.window.showWarningMessage(
      "RepoAlign indexing finished on backend, but the command was cancelled before completion reporting.",
    );
    return;
  }

  progress.report({
    increment: 40,
    message: "Knowledge graph construction complete.",
  });

  const durationSeconds = (Date.now() - startedAt) / 1000;
  await saveIndexingState(
    context,
    createIndexingState(validation, "indexed", {
      discoveredFileCount: pythonFiles.length,
      indexedFileCount: readResult.files.length,
      failedReadCount: readResult.failedReads.length,
      durationSeconds,
    }),
  );

  writeIndexingReport([
    `Workspace: ${workspaceName}`,
    "Status: success",
    `Discovered Python files: ${pythonFiles.length}`,
    `Indexed files: ${readResult.files.length}`,
    `Failed reads: ${readResult.failedReads.length}`,
    `Duration: ${durationSeconds.toFixed(1)}s`,
    `Backend response: ${JSON.stringify(response.data)}`,
    "",
    ...readResult.failedReads.map(
      (failure) => `Read warning: ${failure.path} - ${failure.message}`,
    ),
  ]);

  const warningText =
    readResult.failedReads.length > 0
      ? ` (${readResult.failedReads.length} file(s) could not be read)`
      : "";

  vscode.window.showInformationMessage(
    `RepoAlign indexed ${readResult.files.length}/${pythonFiles.length} Python file(s)${warningText}.`,
  );
}

async function runReindexEmbeddings(): Promise<void> {
  const config = getRepoAlignConfig();

  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: "RepoAlign: Re-indexing embeddings...",
      cancellable: false,
    },
    async (progress) => {
      progress.report({ increment: 10, message: "Checking backend..." });
      const readiness = await runBackendReadinessCheck();
      if (!readiness?.ready) {
        throw new Error("Backend readiness check failed. See RepoAlign output for details.");
      }

      progress.report({ increment: 40, message: "Indexing symbols into Qdrant..." });
      const response = await axios.post(`${config.backendUrl}/index-embeddings`, {}, {
        timeout: 180000,
      });

      progress.report({ increment: 50, message: "Embeddings indexed." });
      outputChannel.clear();
      outputChannel.appendLine("RepoAlign Embedding Re-index");
      outputChannel.appendLine("");
      outputChannel.appendLine(JSON.stringify(response.data, null, 2));
      outputChannel.show(true);

      const indexedSymbols = response.data?.indexed_symbols;
      vscode.window.showInformationMessage(
        typeof indexedSymbols === "number"
          ? `RepoAlign re-indexed ${indexedSymbols} symbol embedding(s).`
          : "RepoAlign embedding re-index completed.",
      );
    },
  );
}

async function runResetWorkspaceIndex(
  context: vscode.ExtensionContext,
): Promise<void> {
  const config = getRepoAlignConfig();
  const choice = await vscode.window.showWarningMessage(
    "Reset RepoAlign graph and embedding index for this workspace? This clears the current backend graph/index data.",
    { modal: true },
    "Reset",
  );

  if (choice !== "Reset") {
    return;
  }

  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: "RepoAlign: Resetting graph/index...",
      cancellable: false,
    },
    async (progress) => {
      progress.report({ increment: 20, message: "Sending reset request..." });
      const response = await axios.post(`${config.backendUrl}/workspace-index/reset`, {
        workspace_id: getWorkspaceId(),
        clear_graph: true,
        clear_embeddings: true,
      });

      await clearIndexingState(context);

      progress.report({ increment: 80, message: "Reset complete." });
      outputChannel.clear();
      outputChannel.appendLine("RepoAlign Workspace Reset");
      outputChannel.appendLine("");
      outputChannel.appendLine(JSON.stringify(response.data, null, 2));
      outputChannel.show(true);
      vscode.window.showInformationMessage(
        "RepoAlign graph/index data reset. Run RepoAlign: Analyze Workspace to rebuild.",
      );
    },
  );
}

async function runBackendReadinessCheck(): Promise<ReadinessResponse | undefined> {
  const config = getRepoAlignConfig();

  try {
    const response = await axios.get<ReadinessResponse>(
      `${config.backendUrl}/readiness`,
      {
        params: {
          model: config.modelName,
        },
        timeout: 10000,
      },
    );
    const readiness = response.data;
    writeReadinessReport(readiness);

    if (readiness.ready) {
      vscode.window.showInformationMessage("RepoAlign backend is ready.");
    } else {
      const failed = Object.entries(readiness.services)
        .filter(([, service]) => service.status !== "ok")
        .map(([name, service]) => `${name}: ${service.message}`)
        .join(" | ");
      vscode.window.showWarningMessage(`RepoAlign backend is not ready. ${failed}`);
      outputChannel.show(true);
    }

    return readiness;
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Unknown readiness check error.";
    outputChannel.clear();
    outputChannel.appendLine("RepoAlign Backend Readiness");
    outputChannel.appendLine("Overall: not_ready");
    outputChannel.appendLine(`FastAPI/backend request failed: ${message}`);
    outputChannel.show(true);
    vscode.window.showErrorMessage(
      `RepoAlign backend is not reachable at ${config.backendUrl}.`,
    );
    return undefined;
  }
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
        Confirm FastAPI, Neo4j, Qdrant, and Ollama/model are ready.
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
      <button data-command="readiness">Backend Readiness</button>
      <button data-command="analyze">Analyze Workspace</button>
      <button data-command="indexStatus">Indexing Status</button>
      <button data-command="rebuild">Rebuild Graph</button>
      <button data-command="embeddings">Re-index Embeddings</button>
      <button data-command="reset">Reset Graph/Index</button>
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
      case "readiness":
        await vscode.commands.executeCommand("repoalign.checkReadiness");
        break;
      case "health":
        await vscode.commands.executeCommand("repoalign.healthCheck");
        break;
      case "analyze":
        await vscode.commands.executeCommand("repoalign.analyzeWorkspace");
        break;
      case "indexStatus":
        await vscode.commands.executeCommand("repoalign.showIndexingStatus");
        break;
      case "rebuild":
        await vscode.commands.executeCommand("repoalign.rebuildGraph");
        break;
      case "embeddings":
        await vscode.commands.executeCommand("repoalign.reindexEmbeddings");
        break;
      case "reset":
        await vscode.commands.executeCommand("repoalign.resetWorkspaceIndex");
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
  outputChannel.appendLine("RepoAlign extension activated.");

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

  const checkReadinessDisposable = vscode.commands.registerCommand(
    "repoalign.checkReadiness",
    async () => runBackendReadinessCheck(),
  );

  const showIndexingStatusDisposable = vscode.commands.registerCommand(
    "repoalign.showIndexingStatus",
    async () => {
      reportIndexingState(getIndexingState(context));
    },
  );

  const rebuildGraphDisposable = vscode.commands.registerCommand(
    "repoalign.rebuildGraph",
    async () => {
      const validation = await validateWorkspace();
      if (validation.status !== "ready") {
        reportWorkspaceValidation(validation);
        return;
      }

      const choice = await vscode.window.showWarningMessage(
        "Rebuild the RepoAlign graph from the current workspace files?",
        "Rebuild",
        "Cancel",
      );

      if (choice !== "Rebuild") {
        return;
      }

      await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: "RepoAlign: Rebuilding graph...",
          cancellable: true,
        },
        async (progress, token) => {
          try {
            await runInitialRepositoryIndexing(context, validation, progress, token);
          } catch (error) {
            const message = getErrorMessage(error);
            await saveIndexingState(
              context,
              createIndexingState(validation, "failed", {
                discoveredFileCount: validation.pythonFiles.length,
                indexedFileCount: 0,
                failedReadCount: 0,
                lastError: message,
              }),
            );
            notifyRepoAlignError("RepoAlign graph rebuild failed", error);
          }
        },
      );
    },
  );

  const resetWorkspaceIndexDisposable = vscode.commands.registerCommand(
    "repoalign.resetWorkspaceIndex",
    async () => {
      try {
        await runResetWorkspaceIndex(context);
      } catch (error) {
        notifyRepoAlignError("RepoAlign reset failed", error);
      }
    },
  );

  const reindexEmbeddingsDisposable = vscode.commands.registerCommand(
    "repoalign.reindexEmbeddings",
    async () => {
      try {
        await runReindexEmbeddings();
      } catch (error) {
        notifyRepoAlignError("RepoAlign embedding re-index failed", error);
      }
    },
  );

  // Command for backend health check
  let healthCheckDisposable = vscode.commands.registerCommand(
    "repoalign.healthCheck",
    async () => {
      await runBackendReadinessCheck();
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

      const existingIndex = getIndexingState(context);
      const config = getRepoAlignConfig();
      if (
        existingIndex?.graphStatus === "indexed" &&
        existingIndex.backendUrl === config.backendUrl &&
        existingIndex.workspaceId === getWorkspaceId()
      ) {
        const choice = await vscode.window.showInformationMessage(
          `RepoAlign already indexed this workspace at ${new Date(existingIndex.lastIndexedAt).toLocaleString()} (${existingIndex.indexedFileCount} file(s)).`,
          "Re-index",
          "Show Status",
          "Cancel",
        );

        if (choice === "Show Status") {
          reportIndexingState(existingIndex);
          return;
        }

        if (choice !== "Re-index") {
          return;
        }
      }

      vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: "RepoAlign: Indexing repository...",
          cancellable: true,
        },
        async (progress, token) => {
          try {
            await runInitialRepositoryIndexing(context, validation, progress, token);
          } catch (error) {
            const message = getErrorMessage(error);
            await saveIndexingState(
              context,
              createIndexingState(validation, "failed", {
                discoveredFileCount: validation.pythonFiles.length,
                indexedFileCount: 0,
                failedReadCount: 0,
                lastError: message,
              }),
            );
            outputChannel.appendLine("");
            outputChannel.appendLine(`Indexing failed: ${message}`);
            outputChannel.show(true);
            vscode.window.showErrorMessage(`RepoAlign indexing failed: ${message}`);
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
              const repoAlignConfig = getRepoAlignConfig();

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
                `${repoAlignConfig.backendUrl}/generate-patch`,
                {
                  query: instruction,
                  original_content: originalContent,
                  file_path: filePath,
                  limit: 10,
                  strict: repoAlignConfig.validationMode === "full",
                  // Optional validation parameters (only if workspace available)
                  ...(dockerRepoPath && repoAlignConfig.validationMode !== "off" && {
                    repo_path: dockerRepoPath,
                    file_relative_path: filePath,
                    run_tests: repoAlignConfig.validationMode === "full",
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
                  notifyRepoAlignError(
                    "RepoAlign failed to apply the generated patch",
                    applyError,
                  );
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
              notifyRepoAlignError("RepoAlign patch generation failed", error);
            }
          },
        );
      } catch (error) {
        notifyRepoAlignError("RepoAlign command failed", error);
      }
    },
  );

  context.subscriptions.push(
    showWelcomeDisposable,
    validateWorkspaceDisposable,
    checkReadinessDisposable,
    showIndexingStatusDisposable,
    rebuildGraphDisposable,
    resetWorkspaceIndexDisposable,
    reindexEmbeddingsDisposable,
    healthCheckDisposable,
    analyzeWorkspaceDisposable,
    generatePatchDisposable,
    vscode.workspace.onDidSaveTextDocument(async (document) => {
      if (!getRepoAlignConfig().autoSyncOnSave) {
        return;
      }

      if (!isPythonDocument(document)) {
        return;
      }

      if (!shouldSyncUri(document.uri)) {
        return;
      }

      try {
        await sendWorkspaceFileChange(
          document.uri,
          "modified",
          document.getText(),
        );
        outputChannel.appendLine(`Synced modified file: ${vscode.workspace.asRelativePath(document.uri, false)}`);
      } catch (error) {
        notifyRepoAlignError("RepoAlign failed to sync saved file", error);
      }
    }),
    vscode.workspace.onDidCreateFiles(async (event) => {
      if (!getRepoAlignConfig().autoSyncOnSave) {
        return;
      }

      for (const uri of event.files) {
        if (!uri.fsPath.endsWith(".py")) {
          continue;
        }

        if (!shouldSyncUri(uri)) {
          continue;
        }

        try {
          const document = await vscode.workspace.openTextDocument(uri);
          await sendWorkspaceFileChange(uri, "added", document.getText());
          outputChannel.appendLine(`Synced added file: ${vscode.workspace.asRelativePath(uri, false)}`);
        } catch (error) {
          notifyRepoAlignError("RepoAlign failed to sync created file", error);
        }
      }
    }),
    vscode.workspace.onDidDeleteFiles(async (event) => {
      if (!getRepoAlignConfig().autoSyncOnSave) {
        return;
      }

      for (const uri of event.files) {
        if (!uri.fsPath.endsWith(".py")) {
          continue;
        }

        if (!shouldSyncUri(uri)) {
          continue;
        }

        try {
          await sendWorkspaceFileChange(uri, "deleted");
          outputChannel.appendLine(`Synced deleted file: ${vscode.workspace.asRelativePath(uri, false)}`);
        } catch (error) {
          notifyRepoAlignError("RepoAlign failed to sync deleted file", error);
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
