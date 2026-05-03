/**
 * Findings Panel
 *
 * Displays commit-time findings from staged change analysis in a dedicated webview panel.
 * Groups findings by file and severity, providing a clear review dashboard.
 */

import * as vscode from "vscode";

interface CommitBlockingFinding {
  severity: "blocker" | "error" | "warning" | "info";
  affected_file: string;
  affected_symbol: string | null;
  reason: string;
  matched_pattern?: string;
  suggested_fix?: string;
  validation_status: "passed" | "warning" | "failed";
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

interface CommitAnalysisResponse {
  status: string;
  recommendation: "ready" | "review" | "blocked";
  summary: {
    total_files: number;
    python_files: number;
    total_hunks: number;
    total_changed_symbols: number;
    additions: number;
    deletions: number;
  };
  changed_symbols: any[];
  findings: CommitBlockingFinding[];
  pattern_results?: PatternDetectionResult[];
  diagnostics: string[];
  retrieved_context?: any;
}

interface GroupedFindings {
  blocker: CommitBlockingFinding[];
  error: CommitBlockingFinding[];
  warning: CommitBlockingFinding[];
  info: CommitBlockingFinding[];
}

interface FindingsByFile {
  [filePath: string]: GroupedFindings;
}

let currentPanel: vscode.WebviewPanel | undefined;

export function createFindingsPanel(
  context: vscode.ExtensionContext,
): vscode.WebviewPanel {
  // If panel already exists, reveal it
  if (currentPanel) {
    currentPanel.reveal(vscode.ViewColumn.Beside);
    return currentPanel;
  }

  const panel = vscode.window.createWebviewPanel(
    "repoalignFindings",
    "RepoAlign Findings",
    vscode.ViewColumn.Beside,
    {
      enableScripts: true,
      enableForms: false,
      localResourceRoots: [],
      retainContextWhenHidden: true,
    },
  );

  // Handle panel disposal
  panel.onDidDispose(() => {
    currentPanel = undefined;
  });

  currentPanel = panel;
  return panel;
}

export function updateFindingsPanel(
  panel: vscode.WebviewPanel,
  response: CommitAnalysisResponse | null,
  workspaceName: string,
): void {
  if (!response) {
    panel.webview.html = getEmptyFindingsHtml();
    return;
  }

  panel.webview.html = getFindingsHtml(response, workspaceName);
}

function groupFindingsByFile(
  findings: CommitBlockingFinding[],
): FindingsByFile {
  const grouped: FindingsByFile = {};

  for (const finding of findings) {
    const file = finding.affected_file || "*";

    if (!grouped[file]) {
      grouped[file] = {
        blocker: [],
        error: [],
        warning: [],
        info: [],
      };
    }

    grouped[file][finding.severity].push(finding);
  }

  return grouped;
}

function getEmptyFindingsHtml(): string {
  return `
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>RepoAlign Findings</title>
      <style>
        ${getSharedStyles()}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="empty-state">
          <div class="empty-icon">🔍</div>
          <h2>No Analysis Results</h2>
          <p>Run <strong>RepoAlign: Analyze Staged Changes</strong> to see findings here.</p>
        </div>
      </div>
    </body>
    </html>
  `;
}

function getFindingsHtml(
  response: CommitAnalysisResponse,
  workspaceName: string,
): string {
  const groupedFindings = groupFindingsByFile(response.findings);
  const fileCount = Object.keys(groupedFindings).length;
  const totalFindings = response.findings.length;

  const recommendationConfig = {
    ready: {
      icon: "✓",
      color: "#4ec9b0",
      label: "Ready to Commit",
      description: "No blocking issues found.",
    },
    review: {
      icon: "⚠",
      color: "#ce9178",
      label: "Review Recommended",
      description: "Please review the findings before committing.",
    },
    blocked: {
      icon: "✗",
      color: "#f48771",
      label: "Commit Blocked",
      description: "Critical issues must be resolved before committing.",
    },
  };

  const config = recommendationConfig[response.recommendation];

  return `
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>RepoAlign Findings</title>
      <style>
        ${getSharedStyles()}
      </style>
    </head>
    <body>
      <div class="container">
        <!-- Header -->
        <div class="header">
          <h1>RepoAlign Commit Analysis</h1>
          <div class="workspace-name">${escapeHtml(workspaceName)}</div>
        </div>

        <!-- Recommendation Banner -->
        <div class="recommendation recommendation-${response.recommendation}" style="border-color: ${config.color}">
          <div class="recommendation-icon" style="color: ${config.color}">${config.icon}</div>
          <div class="recommendation-content">
            <div class="recommendation-label">${config.label}</div>
            <div class="recommendation-description">${config.description}</div>
          </div>
        </div>

        <!-- Summary Stats -->
        <div class="summary-stats">
          <div class="stat-card">
            <div class="stat-value">${response.summary.total_files}</div>
            <div class="stat-label">Files Changed</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">${response.summary.total_changed_symbols}</div>
            <div class="stat-label">Symbols Changed</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">${totalFindings}</div>
            <div class="stat-label">Total Findings</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">+${response.summary.additions} -${response.summary.deletions}</div>
            <div class="stat-label">Lines Changed</div>
          </div>
        </div>

        <!-- Findings Section -->
        ${totalFindings === 0 ? getNoFindingsHtml() : getFindingsListHtml(groupedFindings)}

        <!-- Diagnostics Section -->
        ${response.diagnostics.length > 0 ? getDiagnosticsHtml(response.diagnostics) : ""}

        <!-- Pattern Results Section -->
        ${response.pattern_results && response.pattern_results.length > 0 ? getPatternResultsHtml(response.pattern_results) : ""}
      </div>
    </body>
    </html>
  `;
}

function getNoFindingsHtml(): string {
  return `
    <div class="section">
      <div class="section-header">
        <h2>Findings</h2>
      </div>
      <div class="no-findings">
        <div class="no-findings-icon">✓</div>
        <div class="no-findings-text">No issues found in staged changes</div>
      </div>
    </div>
  `;
}

function getFindingsListHtml(groupedFindings: FindingsByFile): string {
  const files = Object.keys(groupedFindings).sort();

  let html = `
    <div class="section">
      <div class="section-header">
        <h2>Findings by File</h2>
        <div class="section-subtitle">${files.length} ${files.length === 1 ? "file" : "files"} with findings</div>
      </div>
  `;

  for (const file of files) {
    const findings = groupedFindings[file];
    const allFindings = [
      ...findings.blocker,
      ...findings.error,
      ...findings.warning,
      ...findings.info,
    ];

    html += `
      <div class="file-group">
        <div class="file-header">
          <div class="file-icon">📄</div>
          <div class="file-path">${escapeHtml(file)}</div>
          <div class="file-badge">${allFindings.length}</div>
        </div>
        <div class="findings-list">
    `;

    // Render findings by severity order
    const severityOrder: Array<keyof GroupedFindings> = [
      "blocker",
      "error",
      "warning",
      "info",
    ];

    for (const severity of severityOrder) {
      for (const finding of findings[severity]) {
        html += getFindingCardHtml(finding);
      }
    }

    html += `
        </div>
      </div>
    `;
  }

  html += `</div>`;
  return html;
}

function getFindingCardHtml(finding: CommitBlockingFinding): string {
  const severityConfig = {
    blocker: { icon: "🛑", color: "#f48771", label: "Blocker" },
    error: { icon: "❌", color: "#f48771", label: "Error" },
    warning: { icon: "⚠️", color: "#ce9178", label: "Warning" },
    info: { icon: "ℹ️", color: "#4ec9b0", label: "Info" },
  };

  const config = severityConfig[finding.severity];

  return `
    <div class="finding-card finding-${finding.severity}">
      <div class="finding-header">
        <span class="finding-severity" style="color: ${config.color}">${config.icon} ${config.label}</span>
        ${finding.affected_symbol ? `<span class="finding-symbol">Symbol: <code>${escapeHtml(finding.affected_symbol)}</code></span>` : ""}
      </div>
      <div class="finding-reason">${escapeHtml(finding.reason)}</div>
      ${finding.matched_pattern ? `<div class="finding-pattern">Pattern: <code>${escapeHtml(finding.matched_pattern)}</code></div>` : ""}
      ${
        finding.suggested_fix
          ? `
        <div class="finding-fix">
          <div class="fix-label">💡 Suggested Fix:</div>
          <div class="fix-content">${escapeHtml(finding.suggested_fix)}</div>
        </div>
      `
          : ""
      }
    </div>
  `;
}

function getDiagnosticsHtml(diagnostics: string[]): string {
  return `
    <div class="section">
      <div class="section-header">
        <h2>Diagnostics</h2>
        <div class="section-subtitle">${diagnostics.length} ${diagnostics.length === 1 ? "message" : "messages"}</div>
      </div>
      <div class="diagnostics-list">
        ${diagnostics.map((diag) => `<div class="diagnostic-item">${escapeHtml(diag)}</div>`).join("")}
      </div>
    </div>
  `;
}

function getPatternResultsHtml(
  patternResults: PatternDetectionResult[],
): string {
  return `
    <div class="section">
      <div class="section-header">
        <h2>Pattern Detection Results</h2>
        <div class="section-subtitle">${patternResults.length} ${patternResults.length === 1 ? "symbol" : "symbols"} analyzed</div>
      </div>
      <div class="pattern-results">
        ${patternResults.map((result) => getPatternResultCardHtml(result)).join("")}
      </div>
    </div>
  `;
}

function getPatternResultCardHtml(result: PatternDetectionResult): string {
  return `
    <div class="pattern-card">
      <div class="pattern-header">
        <span class="pattern-symbol"><code>${escapeHtml(result.changed_symbol)}</code></span>
      </div>
      ${result.summary ? `<div class="pattern-name">Convention: <strong>${escapeHtml(result.summary.convention)}</strong></div>` : ""}
      ${result.confidence > 0 ? `<div class="pattern-score">Confidence: ${(result.confidence * 100).toFixed(1)}%</div>` : ""}
      ${result.mismatch_score > 0 ? `<div class="pattern-score">Mismatch: ${(result.mismatch_score * 100).toFixed(1)}%</div>` : ""}
      ${result.findings.length > 0 ? `<div class="pattern-findings-count">${result.findings.length} ${result.findings.length === 1 ? "finding" : "findings"}</div>` : ""}
    </div>
  `;
}

function getSharedStyles(): string {
  return `
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background-color: var(--vscode-editor-background);
      color: var(--vscode-editor-foreground);
      font-size: 13px;
      line-height: 1.5;
    }

    .container {
      max-width: 1200px;
      margin: 0 auto;
      padding: 20px;
    }

    /* Header */
    .header {
      margin-bottom: 24px;
    }

    .header h1 {
      font-size: 24px;
      font-weight: 600;
      margin-bottom: 4px;
    }

    .workspace-name {
      font-size: 12px;
      opacity: 0.7;
    }

    /* Recommendation Banner */
    .recommendation {
      display: flex;
      align-items: center;
      padding: 16px;
      border-radius: 6px;
      border: 2px solid;
      margin-bottom: 24px;
      background-color: var(--vscode-inputValidation-infoBackground);
    }

    .recommendation-icon {
      font-size: 32px;
      margin-right: 16px;
    }

    .recommendation-content {
      flex: 1;
    }

    .recommendation-label {
      font-size: 16px;
      font-weight: 600;
      margin-bottom: 4px;
    }

    .recommendation-description {
      font-size: 13px;
      opacity: 0.9;
    }

    /* Summary Stats */
    .summary-stats {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }

    .stat-card {
      padding: 16px;
      border-radius: 6px;
      background-color: var(--vscode-input-background);
      border: 1px solid var(--vscode-input-border);
      text-align: center;
    }

    .stat-value {
      font-size: 24px;
      font-weight: 600;
      margin-bottom: 4px;
    }

    .stat-label {
      font-size: 11px;
      opacity: 0.7;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    /* Section */
    .section {
      margin-bottom: 32px;
    }

    .section-header {
      margin-bottom: 16px;
    }

    .section-header h2 {
      font-size: 18px;
      font-weight: 600;
      margin-bottom: 4px;
    }

    .section-subtitle {
      font-size: 12px;
      opacity: 0.7;
    }

    /* Empty State */
    .empty-state {
      text-align: center;
      padding: 60px 20px;
    }

    .empty-icon {
      font-size: 64px;
      margin-bottom: 16px;
    }

    .empty-state h2 {
      font-size: 20px;
      margin-bottom: 8px;
    }

    .empty-state p {
      opacity: 0.7;
    }

    /* No Findings */
    .no-findings {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 32px;
      border-radius: 6px;
      background-color: var(--vscode-inputValidation-infoBackground);
      border: 1px solid var(--vscode-inputValidation-infoBorder);
    }

    .no-findings-icon {
      font-size: 32px;
      margin-right: 12px;
      color: #4ec9b0;
    }

    .no-findings-text {
      font-size: 14px;
      font-weight: 500;
    }

    /* File Group */
    .file-group {
      margin-bottom: 24px;
      border-radius: 6px;
      border: 1px solid var(--vscode-input-border);
      overflow: hidden;
    }

    .file-header {
      display: flex;
      align-items: center;
      padding: 12px 16px;
      background-color: var(--vscode-input-background);
      border-bottom: 1px solid var(--vscode-input-border);
    }

    .file-icon {
      margin-right: 8px;
    }

    .file-path {
      flex: 1;
      font-family: "Consolas", "Courier New", monospace;
      font-size: 13px;
    }

    .file-badge {
      padding: 2px 8px;
      border-radius: 12px;
      background-color: var(--vscode-badge-background);
      color: var(--vscode-badge-foreground);
      font-size: 11px;
      font-weight: 600;
    }

    /* Findings List */
    .findings-list {
      padding: 8px;
    }

    /* Finding Card */
    .finding-card {
      padding: 12px;
      margin-bottom: 8px;
      border-radius: 4px;
      border-left: 4px solid;
      background-color: var(--vscode-editor-background);
    }

    .finding-blocker {
      border-left-color: #f48771;
    }

    .finding-error {
      border-left-color: #f48771;
    }

    .finding-warning {
      border-left-color: #ce9178;
    }

    .finding-info {
      border-left-color: #4ec9b0;
    }

    .finding-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 8px;
    }

    .finding-severity {
      font-weight: 600;
      font-size: 12px;
    }

    .finding-symbol {
      font-size: 11px;
      opacity: 0.7;
    }

    .finding-reason {
      margin-bottom: 8px;
      font-size: 13px;
    }

    .finding-pattern {
      font-size: 11px;
      opacity: 0.8;
      margin-bottom: 8px;
    }

    .finding-fix {
      margin-top: 12px;
      padding: 8px;
      border-radius: 4px;
      background-color: var(--vscode-textBlockQuote-background);
      border-left: 3px solid var(--vscode-textBlockQuote-border);
    }

    .fix-label {
      font-size: 11px;
      font-weight: 600;
      margin-bottom: 4px;
    }

    .fix-content {
      font-size: 12px;
    }

    code {
      font-family: "Consolas", "Courier New", monospace;
      padding: 2px 4px;
      border-radius: 3px;
      background-color: var(--vscode-textCodeBlock-background);
      font-size: 11px;
    }

    /* Diagnostics */
    .diagnostics-list {
      padding: 12px;
      border-radius: 6px;
      background-color: var(--vscode-input-background);
      border: 1px solid var(--vscode-input-border);
    }

    .diagnostic-item {
      padding: 8px;
      margin-bottom: 4px;
      font-size: 12px;
      font-family: "Consolas", "Courier New", monospace;
    }

    .diagnostic-item:last-child {
      margin-bottom: 0;
    }

    /* Pattern Results */
    .pattern-results {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 12px;
    }

    .pattern-card {
      padding: 12px;
      border-radius: 6px;
      background-color: var(--vscode-input-background);
      border: 1px solid var(--vscode-input-border);
    }

    .pattern-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 8px;
    }

    .pattern-symbol {
      font-weight: 600;
    }

    .pattern-type {
      font-size: 11px;
      padding: 2px 6px;
      border-radius: 3px;
      background-color: var(--vscode-badge-background);
      color: var(--vscode-badge-foreground);
    }

    .pattern-name {
      font-size: 12px;
      margin-bottom: 4px;
    }

    .pattern-score {
      font-size: 11px;
      opacity: 0.7;
      margin-bottom: 4px;
    }

    .pattern-findings-count {
      font-size: 11px;
      margin-top: 8px;
      padding: 4px 8px;
      border-radius: 3px;
      background-color: var(--vscode-badge-background);
      color: var(--vscode-badge-foreground);
      display: inline-block;
    }
  `;
}

function escapeHtml(unsafe: string): string {
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

export function getFindingsPanel(): vscode.WebviewPanel | undefined {
  return currentPanel;
}
