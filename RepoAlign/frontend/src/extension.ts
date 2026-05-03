import * as vscode from "vscode";
import axios from "axios";
import { execFile } from "child_process";
import { promisify } from "util";
import * as path from "path";
import {
  createValidationPanel,
  updateValidationPanel,
} from "./validationPanel";

const execFileAsync = promisify(execFile);

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

interface StagedFileChange {
  status: string;
  path: string;
  previousPath?: string;
  additions?: number;
  deletions?: number;
}

interface StagedDiffHunk {
  header: string;
  oldStart: number;
  oldLines: number;
  newStart: number;
  newLines: number;
  changedOldLines: number[];
  changedNewLines: number[];
  patch: string;
}

interface ChangedSymbol {
  name: string;
  type: "function" | "class";
  startLine: number;
  endLine: number;
  changedLines: number[];
  content: string;
  filePath?: string;
}

interface StagedFilePayload extends StagedFileChange {
  language: "python" | "other";
  oldContent: string;
  newContent: string;
  hunks: StagedDiffHunk[];
  changedSymbols: ChangedSymbol[];
}

interface StagedAnalysisPayload {
  workspaceId?: string;
  workspaceName: string;
  backendUrl: string;
  files: StagedFilePayload[];
}

interface CommitBlockingFinding {
  severity: "info" | "warning" | "error" | "blocker";
  affected_file: string;
  affected_symbol?: string;
  reason: string;
  matched_pattern?: string;
  suggested_fix?: string;
  validation_status: "passed" | "warning" | "failed";
}

interface CommitAnalysisResponse {
  status: "ok";
  recommendation: "ready" | "review" | "blocked";
  findings: CommitBlockingFinding[];
  pattern_results?: PatternDetectionResult[];
  diagnostics: string[];
  summary: {
    total_files: number;
    python_files: number;
    total_hunks: number;
    total_changed_symbols: number;
    additions: number;
    deletions: number;
  };
}

interface PatternDetectionResult {
  changed_symbol: string;
  mismatch_score: number;
  confidence: number;
  candidates?: Array<{
    name: string;
    type: string;
    score: number;
    path?: string;
    content?: string;
  }>;
  summary?: {
    convention: string;
    examples: string[];
    structural_features: Record<string, unknown>;
  };
  findings: CommitBlockingFinding[];
}

interface StoredIgnoreDecision {
  type: "once" | "pattern";
  key: string;
  reason: string;
  createdAt: string;
}

const WELCOME_SHOWN_KEY = "repoalign.welcomeShown";
const INDEXING_STATE_KEY = "repoalign.indexingState";
const IGNORE_DECISIONS_KEY = "repoalign.ignoreDecisions";
const outputChannel = vscode.window.createOutputChannel("RepoAlign");
let extensionContext: vscode.ExtensionContext;
let lastActiveFindings: CommitBlockingFinding[] = [];

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

function getFindingKey(finding: CommitBlockingFinding): string {
  return [
    finding.affected_file,
    finding.affected_symbol ?? "",
    finding.matched_pattern ?? "",
    finding.reason,
  ].join("|");
}

function getIgnoreDecisions(
  context: vscode.ExtensionContext,
): StoredIgnoreDecision[] {
  return context.workspaceState.get<StoredIgnoreDecision[]>(
    IGNORE_DECISIONS_KEY,
    [],
  );
}

async function saveIgnoreDecisions(
  context: vscode.ExtensionContext,
  decisions: StoredIgnoreDecision[],
): Promise<void> {
  await context.workspaceState.update(IGNORE_DECISIONS_KEY, decisions);
}

function applyIgnoreDecisions(
  context: vscode.ExtensionContext,
  findings: CommitBlockingFinding[],
): { active: CommitBlockingFinding[]; ignored: CommitBlockingFinding[] } {
  const decisions = getIgnoreDecisions(context);
  const onceKeys = new Set(
    decisions.filter((decision) => decision.type === "once").map((decision) => decision.key),
  );
  const ignoredPatterns = new Set(
    decisions.filter((decision) => decision.type === "pattern").map((decision) => decision.key),
  );

  const active: CommitBlockingFinding[] = [];
  const ignored: CommitBlockingFinding[] = [];

  for (const finding of findings) {
    const key = getFindingKey(finding);
    const pattern = finding.matched_pattern ?? "";
    if (onceKeys.has(key) || (pattern && ignoredPatterns.has(pattern))) {
      ignored.push(finding);
    } else {
      active.push(finding);
    }
  }

  return { active, ignored };
}

async function ignoreFindingOnce(context: vscode.ExtensionContext): Promise<void> {
  if (!lastActiveFindings.length) {
    vscode.window.showInformationMessage("RepoAlign has no active findings to ignore.");
    return;
  }

  const picked = await vscode.window.showQuickPick(
    lastActiveFindings.map((finding) => ({
      label: finding.matched_pattern ?? finding.severity,
      description: finding.affected_symbol
        ? `${finding.affected_file} :: ${finding.affected_symbol}`
        : finding.affected_file,
      detail: finding.reason,
      finding,
    })),
    { placeHolder: "Select a RepoAlign finding to ignore once." },
  );

  if (!picked) {
    return;
  }

  const decisions = getIgnoreDecisions(context);
  decisions.push({
    type: "once",
    key: getFindingKey(picked.finding),
    reason: picked.finding.reason,
    createdAt: new Date().toISOString(),
  });
  await saveIgnoreDecisions(context, decisions);
  vscode.window.showInformationMessage("RepoAlign will ignore that finding once.");
}

async function ignoreFindingPattern(context: vscode.ExtensionContext): Promise<void> {
  const patterns = Array.from(
    new Set(
      lastActiveFindings
        .map((finding) => finding.matched_pattern)
        .filter((pattern): pattern is string => Boolean(pattern)),
    ),
  );

  if (!patterns.length) {
    vscode.window.showInformationMessage("RepoAlign has no finding patterns to ignore.");
    return;
  }

  const picked = await vscode.window.showQuickPick(patterns, {
    placeHolder: "Select a RepoAlign finding pattern to ignore for this workspace.",
  });

  if (!picked) {
    return;
  }

  const decisions = getIgnoreDecisions(context);
  decisions.push({
    type: "pattern",
    key: picked,
    reason: `Ignored pattern ${picked}`,
    createdAt: new Date().toISOString(),
  });
  await saveIgnoreDecisions(context, decisions);
  vscode.window.showInformationMessage(`RepoAlign will ignore pattern: ${picked}`);
}

async function clearIgnoredFindings(context: vscode.ExtensionContext): Promise<void> {
  await saveIgnoreDecisions(context, []);
  vscode.window.showInformationMessage("RepoAlign ignored finding decisions cleared.");
}

async function consumeIgnoreOnceDecisions(
  context: vscode.ExtensionContext,
  findings: CommitBlockingFinding[],
): Promise<void> {
  const consumed = new Set(findings.map(getFindingKey));
  const remaining = getIgnoreDecisions(context).filter(
    (decision) => decision.type !== "once" || !consumed.has(decision.key),
  );
  await saveIgnoreDecisions(context, remaining);
}

async function runGit(
  workspaceFolder: vscode.WorkspaceFolder,
  args: string[],
): Promise<string> {
  const result = await execFileAsync("git", args, {
    cwd: workspaceFolder.uri.fsPath,
    maxBuffer: 20 * 1024 * 1024,
    windowsHide: true,
  });

  return result.stdout.toString();
}

async function runGitWithResult(
  workspaceFolder: vscode.WorkspaceFolder,
  args: string[],
): Promise<{ stdout: string; stderr: string }> {
  const result = await execFileAsync("git", args, {
    cwd: workspaceFolder.uri.fsPath,
    maxBuffer: 20 * 1024 * 1024,
    windowsHide: true,
  });

  return {
    stdout: result.stdout.toString(),
    stderr: result.stderr.toString(),
  };
}

async function runGitOptional(
  workspaceFolder: vscode.WorkspaceFolder,
  args: string[],
): Promise<string> {
  try {
    return await runGit(workspaceFolder, args);
  } catch {
    return "";
  }
}

function parseOptionalCount(value: string): number | undefined {
  if (value === "-") {
    return undefined;
  }

  const parsed = Number.parseInt(value, 10);
  return Number.isNaN(parsed) ? undefined : parsed;
}

function parseStagedNameStatus(output: string): StagedFileChange[] {
  return output
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => {
      const parts = line.split("\t");
      const status = parts[0] ?? "";

      if (status.startsWith("R") || status.startsWith("C")) {
        return {
          status,
          previousPath: parts[1] ?? "",
          path: parts[2] ?? parts[1] ?? "",
        };
      }

      return {
        status,
        path: parts[1] ?? "",
      };
    })
    .filter((change) => change.path.length > 0);
}

function mergeStagedNumstat(
  changes: StagedFileChange[],
  output: string,
): StagedFileChange[] {
  const countsByPath = new Map<string, { additions?: number; deletions?: number }>();

  for (const line of output.split(/\r?\n/).filter(Boolean)) {
    const parts = line.split("\t");
    const path = parts[3] ?? parts[2] ?? "";
    if (!path) {
      continue;
    }

    countsByPath.set(path, {
      additions: parseOptionalCount(parts[0] ?? "-"),
      deletions: parseOptionalCount(parts[1] ?? "-"),
    });
  }

  return changes.map((change) => ({
    ...change,
    ...countsByPath.get(change.path),
  }));
}

function parseUnifiedDiff(diff: string): Map<string, StagedDiffHunk[]> {
  const hunksByPath = new Map<string, StagedDiffHunk[]>();
  const lines = diff.split(/\r?\n/);
  let currentPath = "";
  let currentHunk: StagedDiffHunk | undefined;
  let oldLine = 0;
  let newLine = 0;

  const finishHunk = () => {
    if (!currentPath || !currentHunk) {
      return;
    }

    const hunks = hunksByPath.get(currentPath) ?? [];
    hunks.push({
      ...currentHunk,
      patch: currentHunk.patch.replace(/\r?\n$/, ""),
    });
    hunksByPath.set(currentPath, hunks);
    currentHunk = undefined;
  };

  for (const line of lines) {
    if (line.startsWith("diff --git ")) {
      finishHunk();
      const match = /^diff --git a\/(.+) b\/(.+)$/.exec(line);
      currentPath = match?.[2] ?? "";
      continue;
    }

    if (line.startsWith("+++ b/")) {
      currentPath = line.slice("+++ b/".length);
      continue;
    }

    if (line.startsWith("@@ ")) {
      finishHunk();
      const match =
        /^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$/.exec(line);
      if (!match) {
        continue;
      }

      oldLine = Number.parseInt(match[1], 10);
      newLine = Number.parseInt(match[3], 10);
      currentHunk = {
        header: line,
        oldStart: oldLine,
        oldLines: Number.parseInt(match[2] ?? "1", 10),
        newStart: newLine,
        newLines: Number.parseInt(match[4] ?? "1", 10),
        changedOldLines: [],
        changedNewLines: [],
        patch: `${line}\n`,
      };
      continue;
    }

    if (!currentHunk) {
      continue;
    }

    currentHunk.patch += `${line}\n`;

    if (line.startsWith("+") && !line.startsWith("+++")) {
      currentHunk.changedNewLines.push(newLine);
      newLine += 1;
    } else if (line.startsWith("-") && !line.startsWith("---")) {
      currentHunk.changedOldLines.push(oldLine);
      oldLine += 1;
    } else if (!line.startsWith("\\")) {
      oldLine += 1;
      newLine += 1;
    }
  }

  finishHunk();
  return hunksByPath;
}

function getPythonSymbols(content: string): ChangedSymbol[] {
  const lines = content.split(/\r?\n/);
  const symbols: ChangedSymbol[] = [];

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const match = /^(\s*)(async\s+def|def|class)\s+([A-Za-z_][A-Za-z0-9_]*)/.exec(line);
    if (!match) {
      continue;
    }

    const indent = match[1].replace(/\t/g, "    ").length;
    const keyword = match[2].includes("class") ? "class" : "function";
    let endLine = lines.length;

    for (let nextIndex = index + 1; nextIndex < lines.length; nextIndex += 1) {
      const nextLine = lines[nextIndex];
      if (!nextLine.trim()) {
        continue;
      }

      const nextIndent = nextLine.match(/^\s*/)?.[0].replace(/\t/g, "    ").length ?? 0;
      if (nextIndent <= indent) {
        endLine = nextIndex;
        break;
      }
    }

    symbols.push({
      name: match[3],
      type: keyword,
      startLine: index + 1,
      endLine,
      changedLines: [],
      content: lines.slice(index, endLine).join("\n"),
    });
  }

  return symbols;
}

function mapHunksToSymbols(
  content: string,
  hunks: StagedDiffHunk[],
  useOldLines = false,
): ChangedSymbol[] {
  const changedLines = new Set<number>();
  for (const hunk of hunks) {
    const lines =
      useOldLines || hunk.changedNewLines.length === 0
        ? hunk.changedOldLines
        : [...hunk.changedNewLines, ...hunk.changedOldLines];
    for (const line of lines) {
      changedLines.add(line);
    }
  }

  return getPythonSymbols(content)
    .map((symbol) => ({
      ...symbol,
      changedLines: Array.from(changedLines)
        .filter((line) => line >= symbol.startLine && line <= symbol.endLine)
        .sort((a, b) => a - b),
    }))
    .filter((symbol) => symbol.changedLines.length > 0);
}

async function getStagedFileContent(
  workspaceFolder: vscode.WorkspaceFolder,
  file: StagedFileChange,
): Promise<{ oldContent: string; newContent: string }> {
  const isAdded = file.status.startsWith("A");
  const isDeleted = file.status.startsWith("D");
  const oldPath = file.previousPath ?? file.path;

  const oldContent = isAdded
    ? ""
    : await runGitOptional(workspaceFolder, ["show", `HEAD:${oldPath}`]);
  const newContent = isDeleted
    ? ""
    : await runGitOptional(workspaceFolder, ["show", `:${file.path}`]);

  return { oldContent, newContent };
}

async function buildStagedAnalysisPayload(
  workspaceFolder: vscode.WorkspaceFolder,
): Promise<StagedAnalysisPayload> {
  const [nameStatus, numstat, diff] = await Promise.all([
    runGit(workspaceFolder, ["diff", "--cached", "--name-status"]),
    runGit(workspaceFolder, ["diff", "--cached", "--numstat"]),
    runGit(workspaceFolder, ["diff", "--cached", "--no-ext-diff"]),
  ]);

  const stagedFiles = mergeStagedNumstat(
    parseStagedNameStatus(nameStatus),
    numstat,
  );
  const hunksByPath = parseUnifiedDiff(diff);
  const files: StagedFilePayload[] = [];

  for (const file of stagedFiles) {
    const { oldContent, newContent } = await getStagedFileContent(
      workspaceFolder,
      file,
    );
    const language = file.path.endsWith(".py") ? "python" : "other";
    const hunks = hunksByPath.get(file.path) ?? [];
    const useOldLines = file.status.startsWith("D");
    const symbolContent = useOldLines ? oldContent : newContent;

    files.push({
      ...file,
      language,
      oldContent,
      newContent,
      hunks,
      changedSymbols:
        language === "python"
          ? mapHunksToSymbols(symbolContent, hunks, useOldLines).map((symbol) => ({
              ...symbol,
              filePath: file.path,
            }))
          : [],
    });
  }

  return {
    workspaceId: getWorkspaceId(),
    workspaceName: workspaceFolder.name,
    backendUrl: getRepoAlignConfig().backendUrl,
    files,
  };
}

function writeCommitAnalysisReport(
  payload: StagedAnalysisPayload,
  analysis: CommitAnalysisResponse,
  ignoredFindings: CommitBlockingFinding[] = [],
): void {
  const ignoreDecisions = getIgnoreDecisions(extensionContext);

  outputChannel.clear();
  outputChannel.appendLine("RepoAlign Commit Analysis");
  outputChannel.appendLine("");
  outputChannel.appendLine("Debug Snapshot");
  outputChannel.appendLine("--------------");
  outputChannel.appendLine(`Timestamp: ${new Date().toISOString()}`);
  outputChannel.appendLine(`Workspace: ${payload.workspaceName}`);
  outputChannel.appendLine(`Workspace ID: ${payload.workspaceId ?? "n/a"}`);
  outputChannel.appendLine(`Backend URL: ${payload.backendUrl}`);
  outputChannel.appendLine(`Backend status: ${analysis.status}`);
  outputChannel.appendLine(`Recommendation: ${analysis.recommendation}`);
  outputChannel.appendLine(`Files: ${analysis.summary.total_files}`);
  outputChannel.appendLine(`Python files: ${analysis.summary.python_files}`);
  outputChannel.appendLine(`Changed symbols: ${analysis.summary.total_changed_symbols}`);
  outputChannel.appendLine(`Pattern results: ${analysis.pattern_results?.length ?? 0}`);
  outputChannel.appendLine(`Active findings: ${analysis.findings.length}`);
  outputChannel.appendLine(`Ignored findings: ${ignoredFindings.length}`);
  outputChannel.appendLine(`Stored ignore decisions: ${ignoreDecisions.length}`);
  outputChannel.appendLine(`Lines: +${analysis.summary.additions}/-${analysis.summary.deletions}`);
  outputChannel.appendLine("");
  outputChannel.appendLine("Staged Files");
  outputChannel.appendLine("------------");

  for (const file of payload.files) {
    outputChannel.appendLine(
      `${file.status} ${file.path} (${file.hunks.length} hunk(s), ${file.changedSymbols.length} symbol(s))`,
    );
    outputChannel.appendLine(
      `  language=${file.language}, oldContent=${file.oldContent.length} chars, newContent=${file.newContent.length} chars`,
    );
    if (!file.hunks.length) {
      outputChannel.appendLine("  warning: no parsed hunks for this staged file");
    }
    for (const hunk of file.hunks.slice(0, 5)) {
      outputChannel.appendLine(
        `  hunk ${hunk.header} oldChanged=[${hunk.changedOldLines.join(",")}] newChanged=[${hunk.changedNewLines.join(",")}]`,
      );
    }
    if (!file.changedSymbols.length && file.language === "python") {
      outputChannel.appendLine(
        "  warning: no changed Python symbols mapped from staged hunks",
      );
    }
    for (const symbol of file.changedSymbols) {
      outputChannel.appendLine(
        `  symbol ${symbol.type} ${symbol.name} lines ${symbol.startLine}-${symbol.endLine}, changedLines=[${symbol.changedLines.join(",")}]`,
      );
    }
  }

  outputChannel.appendLine("");
  outputChannel.appendLine("Pattern Detection");
  outputChannel.appendLine("-----------------");
  if (!analysis.pattern_results?.length) {
    outputChannel.appendLine("No pattern_results returned by backend.");
    outputChannel.appendLine(
      "Likely causes: no changed symbols, embeddings not indexed, graph not built, or backend pattern detection failed.",
    );
  } else {
    for (const result of analysis.pattern_results) {
      outputChannel.appendLine(
        `Symbol: ${result.changed_symbol} mismatch=${result.mismatch_score.toFixed(3)} confidence=${result.confidence.toFixed(3)} findings=${result.findings.length}`,
      );
      if (result.summary) {
        outputChannel.appendLine(`  convention: ${result.summary.convention}`);
        outputChannel.appendLine(
          `  examples: ${result.summary.examples.join(", ") || "none"}`,
        );
        outputChannel.appendLine(
          `  structural_features: ${JSON.stringify(result.summary.structural_features)}`,
        );
      } else {
        outputChannel.appendLine("  warning: no pattern summary returned");
      }
      if (!result.candidates?.length) {
        outputChannel.appendLine(
          "  warning: no similar candidates returned. Rebuild graph and re-index embeddings before Phase 11 tests.",
        );
      } else {
        outputChannel.appendLine("  candidates:");
        for (const candidate of result.candidates) {
          outputChannel.appendLine(
            `    - ${candidate.name} (${candidate.type}) score=${candidate.score.toFixed(3)} path=${candidate.path ?? "n/a"} content=${candidate.content?.length ?? 0} chars`,
          );
        }
      }
      if (result.findings.length) {
        outputChannel.appendLine("  raw pattern findings:");
        for (const finding of result.findings) {
          outputChannel.appendLine(
            `    - [${finding.severity}] ${finding.matched_pattern ?? "finding"}: ${finding.reason}`,
          );
        }
      }
    }
  }

  outputChannel.appendLine("");
  outputChannel.appendLine("Findings");
  outputChannel.appendLine("--------");

  if (!analysis.findings.length) {
    outputChannel.appendLine("No blocking findings.");
  } else {
    for (const finding of analysis.findings) {
      const symbol = finding.affected_symbol
        ? ` :: ${finding.affected_symbol}`
        : "";
      outputChannel.appendLine(
        `[${finding.severity}] ${finding.affected_file}${symbol}`,
      );
      outputChannel.appendLine(`  reason: ${finding.reason}`);
      if (finding.matched_pattern) {
        outputChannel.appendLine(`  pattern: ${finding.matched_pattern}`);
      }
      if (finding.suggested_fix) {
        outputChannel.appendLine(`  suggested fix: ${finding.suggested_fix}`);
      }
      outputChannel.appendLine(`  validation: ${finding.validation_status}`);
      outputChannel.appendLine(`  ignore key: ${getFindingKey(finding)}`);
    }
  }

  if (analysis.diagnostics.length) {
    outputChannel.appendLine("");
    outputChannel.appendLine("Diagnostics");
    outputChannel.appendLine("-----------");
    for (const diagnostic of analysis.diagnostics) {
      outputChannel.appendLine(diagnostic);
    }
  }

  if (ignoredFindings.length) {
    outputChannel.appendLine("");
    outputChannel.appendLine("Ignored Findings");
    outputChannel.appendLine("----------------");
    for (const finding of ignoredFindings) {
      outputChannel.appendLine(
        `[ignored] ${finding.matched_pattern ?? "finding"} in ${finding.affected_file}`,
      );
      outputChannel.appendLine(`  reason: ${finding.reason}`);
      outputChannel.appendLine(`  ignore key: ${getFindingKey(finding)}`);
    }
  }

  outputChannel.appendLine("");
  outputChannel.appendLine("Stored Ignore Decisions");
  outputChannel.appendLine("-----------------------");
  if (!ignoreDecisions.length) {
    outputChannel.appendLine("None.");
  } else {
    for (const decision of ignoreDecisions) {
      outputChannel.appendLine(
        `${decision.type}: ${decision.key} (${decision.createdAt})`,
      );
      outputChannel.appendLine(`  reason: ${decision.reason}`);
    }
  }

  outputChannel.appendLine("");
  outputChannel.appendLine("Raw Backend Response");
  outputChannel.appendLine("--------------------");
  outputChannel.appendLine(JSON.stringify(analysis, null, 2));

  outputChannel.show(true);
}

function getManagedHookContent(backendUrl: string): string {
  return `#!/bin/sh
# RepoAlign managed pre-commit hook
# Remove with: RepoAlign: Remove Pre-Commit Hook
BACKEND_URL="${backendUrl}"

python - <<'PY'
import json
import subprocess
import sys
import urllib.error
import urllib.request

backend_url = "${backendUrl}"

def git(*args):
    return subprocess.check_output(["git", *args], text=True, stderr=subprocess.DEVNULL)

name_status = git("diff", "--cached", "--name-status").splitlines()
files = []
for line in name_status:
    parts = line.split("\\t")
    if len(parts) < 2:
        continue
    status = parts[0]
    path = parts[-1]
    if not path.endswith(".py"):
        continue
    try:
        new_content = "" if status.startswith("D") else git("show", f":{path}")
    except Exception:
        new_content = ""
    files.append({
        "status": status,
        "path": path,
        "language": "python",
        "oldContent": "",
        "newContent": new_content,
        "hunks": [],
        "changedSymbols": [],
    })

if not files:
    sys.exit(0)

payload = {
    "workspaceId": git("rev-parse", "--show-toplevel").strip(),
    "workspaceName": "git-hook",
    "backendUrl": backend_url,
    "files": files,
}

request = urllib.request.Request(
    backend_url + "/analyze-staged-changes",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)

try:
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))
except urllib.error.URLError as exc:
    print(f"RepoAlign hook warning: backend unavailable ({exc}). Commit allowed.")
    sys.exit(0)

recommendation = result.get("recommendation", "review")
if recommendation == "blocked":
    print("RepoAlign blocked this commit:")
    for finding in result.get("findings", []):
        print(f"- [{finding.get('severity')}] {finding.get('affected_file')}: {finding.get('reason')}")
    print("Use git commit --no-verify to bypass this optional local hook.")
    sys.exit(1)

print(f"RepoAlign hook analysis: {recommendation}")
sys.exit(0)
PY
`;
}

async function getGitHooksPath(
  workspaceFolder: vscode.WorkspaceFolder,
): Promise<string> {
  const gitDir = (await runGit(workspaceFolder, ["rev-parse", "--git-dir"])).trim();
  const hooksPath = path.isAbsolute(gitDir)
    ? path.join(gitDir, "hooks")
    : path.join(workspaceFolder.uri.fsPath, gitDir, "hooks");
  return hooksPath;
}

async function installPreCommitHook(): Promise<void> {
  const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
  if (!workspaceFolder) {
    vscode.window.showWarningMessage("Open a Git workspace before installing the RepoAlign hook.");
    return;
  }

  if (!(await hasGitRepository(workspaceFolder))) {
    vscode.window.showWarningMessage("RepoAlign hook installation needs a Git repository.");
    return;
  }

  const hooksPath = await getGitHooksPath(workspaceFolder);
  const hookUri = vscode.Uri.file(path.join(hooksPath, "pre-commit"));

  try {
    const existing = await vscode.workspace.fs.readFile(hookUri);
    const existingText = Buffer.from(existing).toString("utf8");
    if (!existingText.includes("RepoAlign managed pre-commit hook")) {
      vscode.window.showWarningMessage(
        "A non-RepoAlign pre-commit hook already exists. RepoAlign did not overwrite it.",
      );
      return;
    }
  } catch {
    await vscode.workspace.fs.createDirectory(vscode.Uri.file(hooksPath));
  }

  const content = new TextEncoder().encode(
    getManagedHookContent(getRepoAlignConfig().backendUrl),
  );
  await vscode.workspace.fs.writeFile(hookUri, content);

  if (process.platform !== "win32") {
    await execFileAsync("chmod", ["755", hookUri.fsPath], { windowsHide: true });
  }

  outputChannel.appendLine(`Installed RepoAlign pre-commit hook: ${hookUri.fsPath}`);
  outputChannel.show(true);
  vscode.window.showInformationMessage(
    "RepoAlign pre-commit hook installed for this repository. Push remains normal; commits can bypass with --no-verify.",
  );
}

async function removePreCommitHook(): Promise<void> {
  const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
  if (!workspaceFolder) {
    vscode.window.showWarningMessage("Open a Git workspace before removing the RepoAlign hook.");
    return;
  }

  const hookUri = vscode.Uri.file(path.join(await getGitHooksPath(workspaceFolder), "pre-commit"));

  try {
    const existing = await vscode.workspace.fs.readFile(hookUri);
    const existingText = Buffer.from(existing).toString("utf8");
    if (!existingText.includes("RepoAlign managed pre-commit hook")) {
      vscode.window.showWarningMessage(
        "The existing pre-commit hook is not RepoAlign-managed. RepoAlign did not remove it.",
      );
      return;
    }

    await vscode.workspace.fs.delete(hookUri);
    outputChannel.appendLine(`Removed RepoAlign pre-commit hook: ${hookUri.fsPath}`);
    outputChannel.show(true);
    vscode.window.showInformationMessage("RepoAlign pre-commit hook removed.");
  } catch {
    vscode.window.showInformationMessage("No RepoAlign pre-commit hook was found.");
  }
}

async function requestStagedAnalysis(
  workspaceFolder: vscode.WorkspaceFolder,
): Promise<{ payload: StagedAnalysisPayload; analysis: CommitAnalysisResponse }> {
  const payload = await buildStagedAnalysisPayload(workspaceFolder);
  if (payload.files.length === 0) {
    throw new Error("No staged changes found. Stage files before committing with analysis.");
  }

  try {
    const response = await axios.post<CommitAnalysisResponse>(
      `${getRepoAlignConfig().backendUrl}/analyze-staged-changes`,
      payload,
      { timeout: 120000 },
    );

    return { payload, analysis: response.data };
  } catch (error) {
    outputChannel.clear();
    outputChannel.appendLine("RepoAlign Staged Analysis Request Failed");
    outputChannel.appendLine("");
    outputChannel.appendLine(`Backend URL: ${getRepoAlignConfig().backendUrl}`);
    outputChannel.appendLine(`Workspace: ${payload.workspaceName}`);
    outputChannel.appendLine(`Files: ${payload.files.length}`);
    outputChannel.appendLine(
      `Changed symbols: ${payload.files.reduce((total, file) => total + file.changedSymbols.length, 0)}`,
    );
    outputChannel.appendLine("");
    outputChannel.appendLine("Request Files");
    outputChannel.appendLine("-------------");
    for (const file of payload.files) {
      outputChannel.appendLine(
        `${file.status} ${file.path}: hunks=${file.hunks.length}, symbols=${file.changedSymbols.length}, old=${file.oldContent.length}, new=${file.newContent.length}`,
      );
      for (const symbol of file.changedSymbols) {
        outputChannel.appendLine(
          `  symbol ${symbol.type} ${symbol.name} lines ${symbol.startLine}-${symbol.endLine}`,
        );
      }
    }
    outputChannel.appendLine("");
    outputChannel.appendLine("Error");
    outputChannel.appendLine("-----");
    outputChannel.appendLine(getErrorMessage(error));
    if (axios.isAxiosError(error)) {
      outputChannel.appendLine("");
      outputChannel.appendLine(`HTTP status: ${error.response?.status ?? "n/a"}`);
      outputChannel.appendLine(
        `Response body: ${JSON.stringify(error.response?.data ?? null, null, 2)}`,
      );
    }
    outputChannel.show(true);
    throw error;
  }
}

async function inspectStagedChanges(): Promise<void> {
  const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
  if (!workspaceFolder) {
    vscode.window.showWarningMessage(
      "RepoAlign needs an opened workspace folder before inspecting staged changes.",
    );
    return;
  }

  if (!(await hasGitRepository(workspaceFolder))) {
    vscode.window.showWarningMessage(
      "RepoAlign staged change inspection needs a Git repository.",
    );
    return;
  }

  const [nameStatus, numstat, stat, diff] = await Promise.all([
    runGit(workspaceFolder, ["diff", "--cached", "--name-status"]),
    runGit(workspaceFolder, ["diff", "--cached", "--numstat"]),
    runGit(workspaceFolder, ["diff", "--cached", "--stat"]),
    runGit(workspaceFolder, ["diff", "--cached", "--no-ext-diff"]),
  ]);

  const stagedFiles = mergeStagedNumstat(
    parseStagedNameStatus(nameStatus),
    numstat,
  );

  outputChannel.clear();
  outputChannel.appendLine("RepoAlign Staged Changes");
  outputChannel.appendLine("");
  outputChannel.appendLine(`Workspace: ${workspaceFolder.name}`);
  outputChannel.appendLine(`Repository: ${workspaceFolder.uri.fsPath}`);
  outputChannel.appendLine(`Staged files: ${stagedFiles.length}`);
  outputChannel.appendLine("");

  if (stagedFiles.length === 0) {
    outputChannel.appendLine("No staged files found.");
    outputChannel.show(true);
    vscode.window.showInformationMessage(
      "RepoAlign found no staged changes. Your normal Git push flow is unchanged.",
    );
    return;
  }

  outputChannel.appendLine("Files");
  outputChannel.appendLine("-----");
  for (const file of stagedFiles) {
    const counts =
      typeof file.additions === "number" && typeof file.deletions === "number"
        ? ` (+${file.additions}/-${file.deletions})`
        : "";
    const rename =
      file.previousPath && file.previousPath !== file.path
        ? ` from ${file.previousPath}`
        : "";
    outputChannel.appendLine(`${file.status} ${file.path}${rename}${counts}`);
  }

  outputChannel.appendLine("");
  outputChannel.appendLine("Stat");
  outputChannel.appendLine("----");
  outputChannel.appendLine(stat.trim() || "No staged diff stat available.");
  outputChannel.appendLine("");
  outputChannel.appendLine("Staged Diff");
  outputChannel.appendLine("-----------");
  outputChannel.appendLine(diff.trim() || "No staged text diff available.");
  outputChannel.show(true);

  vscode.window.showInformationMessage(
    `RepoAlign inspected ${stagedFiles.length} staged file(s). No commit or push behavior was changed.`,
  );
}

async function analyzeStagedChanges(): Promise<void> {
  const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
  if (!workspaceFolder) {
    vscode.window.showWarningMessage(
      "RepoAlign needs an opened workspace folder before analyzing staged changes.",
    );
    return;
  }

  if (!(await hasGitRepository(workspaceFolder))) {
    vscode.window.showWarningMessage(
      "RepoAlign staged analysis needs a Git repository.",
    );
    return;
  }

  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: "RepoAlign: Analyzing staged changes...",
      cancellable: false,
    },
    async (progress) => {
      progress.report({ increment: 20, message: "Parsing staged diff..." });
      const { payload, analysis } = await requestStagedAnalysis(workspaceFolder);
      const filtered = applyIgnoreDecisions(extensionContext, analysis.findings);
      analysis.findings = filtered.active;
      lastActiveFindings = filtered.active;

      progress.report({ increment: 40, message: "Commit analysis complete." });
      writeCommitAnalysisReport(payload, analysis, filtered.ignored);
      await consumeIgnoreOnceDecisions(extensionContext, filtered.ignored);
      vscode.window.showInformationMessage(
        `RepoAlign staged analysis complete. Recommendation: ${analysis.recommendation}. Your Git commit/push flow was not changed.`,
      );
    },
  );
}

async function commitWithAnalysis(): Promise<void> {
  const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
  if (!workspaceFolder) {
    vscode.window.showWarningMessage(
      "RepoAlign needs an opened workspace folder before committing.",
    );
    return;
  }

  if (!(await hasGitRepository(workspaceFolder))) {
    vscode.window.showWarningMessage(
      "RepoAlign commit analysis needs a Git repository.",
    );
    return;
  }

  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: "RepoAlign: Commit with analysis...",
      cancellable: false,
    },
    async (progress) => {
      progress.report({ increment: 15, message: "Analyzing staged changes..." });
      const { payload, analysis } = await requestStagedAnalysis(workspaceFolder);
      const filtered = applyIgnoreDecisions(extensionContext, analysis.findings);
      analysis.findings = filtered.active;
      lastActiveFindings = filtered.active;
      writeCommitAnalysisReport(payload, analysis, filtered.ignored);
      await consumeIgnoreOnceDecisions(extensionContext, filtered.ignored);

      const hasActiveBlocker = filtered.active.some(
        (finding) => finding.severity === "blocker",
      );
      if (analysis.recommendation === "blocked" && hasActiveBlocker) {
        vscode.window.showErrorMessage(
          "RepoAlign blocked this commit. Review the RepoAlign output findings, fix the staged change, and try again.",
        );
        return;
      }

      if (analysis.recommendation === "review") {
        const choice = await vscode.window.showWarningMessage(
          "RepoAlign recommends review before committing. Continue anyway?",
          { modal: true },
          "Commit Anyway",
        );

        if (choice !== "Commit Anyway") {
          return;
        }
      }

      const commitMessage = await vscode.window.showInputBox({
        title: "RepoAlign: Commit With Analysis",
        prompt: "Enter the Git commit message.",
        placeHolder: "Describe the staged change",
        ignoreFocusOut: true,
      });

      if (!commitMessage?.trim()) {
        vscode.window.showInformationMessage("RepoAlign commit cancelled: no commit message provided.");
        return;
      }

      progress.report({ increment: 55, message: "Running git commit..." });
      const result = await runGitWithResult(workspaceFolder, [
        "commit",
        "-m",
        commitMessage.trim(),
      ]);

      progress.report({ increment: 30, message: "Commit complete." });
      outputChannel.appendLine("");
      outputChannel.appendLine("Git Commit Result");
      outputChannel.appendLine("-----------------");
      outputChannel.appendLine(result.stdout.trim() || result.stderr.trim() || "Commit completed.");
      outputChannel.appendLine("");
      outputChannel.appendLine(`Analysis event: passed at ${new Date().toISOString()}`);
      outputChannel.show(true);
      vscode.window.showInformationMessage(
        "RepoAlign analysis passed and Git commit completed. Push flow remains normal.",
      );
    },
  );
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
      <button data-command="staged">Inspect Staged Changes</button>
      <button data-command="analyzeStaged">Analyze Staged Changes</button>
      <button data-command="commitAnalysis">Commit With Analysis</button>
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
      case "staged":
        await vscode.commands.executeCommand("repoalign.inspectStagedChanges");
        break;
      case "analyzeStaged":
        await vscode.commands.executeCommand("repoalign.analyzeStagedChanges");
        break;
      case "commitAnalysis":
        await vscode.commands.executeCommand("repoalign.commitWithAnalysis");
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
  extensionContext = context;
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

  const inspectStagedChangesDisposable = vscode.commands.registerCommand(
    "repoalign.inspectStagedChanges",
    async () => {
      try {
        await inspectStagedChanges();
      } catch (error) {
        notifyRepoAlignError("RepoAlign staged change inspection failed", error);
      }
    },
  );

  const analyzeStagedChangesDisposable = vscode.commands.registerCommand(
    "repoalign.analyzeStagedChanges",
    async () => {
      try {
        await analyzeStagedChanges();
      } catch (error) {
        notifyRepoAlignError("RepoAlign staged change analysis failed", error);
      }
    },
  );

  const commitWithAnalysisDisposable = vscode.commands.registerCommand(
    "repoalign.commitWithAnalysis",
    async () => {
      try {
        await commitWithAnalysis();
      } catch (error) {
        notifyRepoAlignError("RepoAlign commit with analysis failed", error);
      }
    },
  );

  const installPreCommitHookDisposable = vscode.commands.registerCommand(
    "repoalign.installPreCommitHook",
    async () => {
      try {
        await installPreCommitHook();
      } catch (error) {
        notifyRepoAlignError("RepoAlign hook installation failed", error);
      }
    },
  );

  const removePreCommitHookDisposable = vscode.commands.registerCommand(
    "repoalign.removePreCommitHook",
    async () => {
      try {
        await removePreCommitHook();
      } catch (error) {
        notifyRepoAlignError("RepoAlign hook removal failed", error);
      }
    },
  );

  const ignoreFindingOnceDisposable = vscode.commands.registerCommand(
    "repoalign.ignoreFindingOnce",
    async () => ignoreFindingOnce(context),
  );

  const ignoreFindingPatternDisposable = vscode.commands.registerCommand(
    "repoalign.ignoreFindingPattern",
    async () => ignoreFindingPattern(context),
  );

  const clearIgnoredFindingsDisposable = vscode.commands.registerCommand(
    "repoalign.clearIgnoredFindings",
    async () => clearIgnoredFindings(context),
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
    inspectStagedChangesDisposable,
    analyzeStagedChangesDisposable,
    commitWithAnalysisDisposable,
    installPreCommitHookDisposable,
    removePreCommitHookDisposable,
    ignoreFindingOnceDisposable,
    ignoreFindingPatternDisposable,
    clearIgnoredFindingsDisposable,
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
