/**
 * Validation Report Panel
 *
 * Displays the validation results from the patch generation in a dedicated webview panel.
 * Shows syntax errors, lint warnings, type errors, and test results with color coding.
 */

import * as vscode from "vscode";

interface ValidationStage {
  stage_name: string;
  passed: boolean;
  error_count: number;
  warning_count: number;
  summary: string;
}

interface ValidationReport {
  overall_status: "passed" | "failed";
  overall_summary: string;
  constraint_check?: {
    status: string;
    summary: string;
    statistics?: {
      total_issues?: number;
      errors?: number;
      warnings?: number;
    };
    results?: {
      issues?: Array<{
        line: number;
        column: number;
        issue_type: string;
        message: string;
        severity: string;
      }>;
    };
  };
  test_results?: {
    status: string;
    summary: string;
    statistics?: {
      total_tests?: number;
      passed?: number;
      failed?: number;
      errors?: number;
      skipped?: number;
    };
  };
  total_issues: number;
  total_errors: number;
  total_warnings: number;
  validation_stages?: Record<string, ValidationStage>;
}

export function createValidationPanel(
  context: vscode.ExtensionContext,
): vscode.WebviewPanel {
  const panel = vscode.window.createWebviewPanel(
    "repoalignValidation",
    "RepoAlign Validation Report",
    vscode.ViewColumn.Beside,
    {
      enableScripts: true,
      enableForms: false,
      localResourceRoots: [],
    },
  );

  return panel;
}

export function updateValidationPanel(
  panel: vscode.WebviewPanel,
  validation: ValidationReport | null,
  filePath: string,
): void {
  if (!validation) {
    panel.webview.html = getEmptyValidationHtml();
    return;
  }

  panel.webview.html = getValidationHtml(validation, filePath);
}

function getEmptyValidationHtml(): string {
  return `
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>Validation Report</title>
      <style>
        body {
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
          padding: 20px;
          background-color: var(--vscode-editor-background);
          color: var(--vscode-editor-foreground);
          margin: 0;
        }
        .container {
          max-width: 100%;
        }
        .info {
          padding: 12px;
          border-radius: 4px;
          background-color: var(--vscode-inputValidation-infoBorder);
          color: var(--vscode-editor-foreground);
          border-left: 4px solid var(--vscode-inputValidation-infoBorder);
        }
      </style>
    </head>
    <body>
      <div class="container">
        <div class="info">
          <p>⏳ Validation data will appear here after patch generation with a repository path.</p>
        </div>
      </div>
    </body>
    </html>
  `;
}

function getValidationHtml(
  validation: ValidationReport,
  filePath: string,
): string {
  const statusColor =
    validation.overall_status === "passed" ? "#4ec9b0" : "#f48771";
  const statusIcon = validation.overall_status === "passed" ? "✓" : "✗";

  return `
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>Validation Report</title>
      <style>
        * {
          box-sizing: border-box;
        }
        body {
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
          padding: 16px;
          background-color: var(--vscode-editor-background);
          color: var(--vscode-editor-foreground);
          margin: 0;
          font-size: 13px;
          line-height: 1.6;
        }
        .container {
          max-width: 100%;
        }
        .header {
          display: flex;
          align-items: center;
          margin-bottom: 20px;
          padding: 12px;
          border-radius: 4px;
          background-color: ${
            validation.overall_status === "passed"
              ? "rgba(78, 201, 176, 0.1)"
              : "rgba(244, 135, 113, 0.1)"
          };
          border-left: 4px solid ${statusColor};
        }
        .header-status {
          font-size: 32px;
          margin-right: 12px;
          color: ${statusColor};
        }
        .header-text h2 {
          margin: 0;
          font-size: 16px;
          font-weight: 600;
          color: ${statusColor};
        }
        .header-text p {
          margin: 4px 0 0 0;
          font-size: 13px;
          opacity: 0.8;
        }
        .file-info {
          margin-bottom: 16px;
          padding: 8px;
          background-color: var(--vscode-inputOption-activeBorder);
          border-radius: 3px;
          opacity: 0.8;
          font-size: 12px;
        }
        .stats {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 8px;
          margin-bottom: 16px;
        }
        .stat-card {
          padding: 12px;
          border-radius: 4px;
          background-color: var(--vscode-button-secondaryBackground);
          border: 1px solid var(--vscode-button-border);
        }
        .stat-number {
          font-size: 24px;
          font-weight: bold;
          color: var(--vscode-editor-foreground);
        }
        .stat-label {
          font-size: 11px;
          opacity: 0.7;
          margin-top: 4px;
          text-transform: uppercase;
        }
        .stat-errors {
          color: #f48771;
        }
        .stat-warnings {
          color: #dcdcaa;
        }
        .stages {
          margin-bottom: 20px;
        }
        .stage {
          margin-bottom: 12px;
          border-radius: 4px;
          overflow: hidden;
          border: 1px solid var(--vscode-button-border);
        }
        .stage-header {
          padding: 12px;
          background-color: var(--vscode-button-secondaryBackground);
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: space-between;
          user-select: none;
        }
        .stage-header:hover {
          background-color: var(--vscode-button-hoverBackground);
        }
        .stage-title {
          display: flex;
          align-items: center;
          flex: 1;
        }
        .stage-icon {
          font-size: 16px;
          margin-right: 8px;
          width: 20px;
          text-align: center;
        }
        .stage-name {
          font-weight: 500;
          flex: 1;
        }
        .stage-meta {
          font-size: 11px;
          opacity: 0.7;
          margin-left: 8px;
        }
        .stage-body {
          padding: 12px;
          background-color: var(--vscode-editor-background);
          border-top: 1px solid var(--vscode-button-border);
          display: none;
        }
        .stage-body.active {
          display: block;
        }
        .issue-list {
          list-style: none;
          padding: 0;
          margin: 0;
        }
        .issue {
          padding: 8px;
          margin-bottom: 8px;
          border-radius: 3px;
          border-left: 3px solid;
          background-color: rgba(0, 0, 0, 0.2);
          font-size: 12px;
        }
        .issue-error {
          border-left-color: #f48771;
        }
        .issue-warning {
          border-left-color: #dcdcaa;
        }
        .issue-note {
          border-left-color: #4ec9b0;
        }
        .issue-title {
          font-weight: 500;
          margin-bottom: 4px;
        }
        .issue-location {
          font-size: 11px;
          opacity: 0.7;
        }
        .issue-message {
          margin-top: 4px;
          word-break: break-word;
        }
        .empty-message {
          padding: 12px;
          text-align: center;
          opacity: 0.6;
          font-style: italic;
        }
        .toggle-arrow {
          display: inline-block;
          transition: transform 0.2s ease;
          width: 16px;
          text-align: center;
        }
        .toggle-arrow.active {
          transform: rotate(90deg);
        }
        h3 {
          margin: 0 0 12px 0;
          font-size: 13px;
          font-weight: 600;
          text-transform: uppercase;
          opacity: 0.8;
        }
        .passed {
          color: #4ec9b0;
        }
        .failed {
          color: #f48771;
        }
      </style>
    </head>
    <body>
      <div class="container">
        <!-- Overall Status -->
        <div class="header">
          <div class="header-status">${statusIcon}</div>
          <div class="header-text">
            <h2>${
              validation.overall_status === "passed"
                ? "Validation Passed"
                : "Validation Failed"
            }</h2>
            <p>${validation.overall_summary}</p>
          </div>
        </div>

        <!-- File Info -->
        <div class="file-info">
          📄 <strong>File:</strong> ${escapeHtml(filePath)}
        </div>

        <!-- Statistics -->
        <div class="stats">
          <div class="stat-card">
            <div class="stat-number stat-errors">${validation.total_errors}</div>
            <div class="stat-label">Errors</div>
          </div>
          <div class="stat-card">
            <div class="stat-number stat-warnings">${validation.total_warnings}</div>
            <div class="stat-label">Warnings</div>
          </div>
        </div>

        <!-- Validation Stages -->
        <div class="stages">
          ${renderValidationStages(validation)}
        </div>
      </div>

      <script>
        document.querySelectorAll('.stage-header').forEach(header => {
          header.addEventListener('click', function() {
            const body = this.nextElementSibling;
            const arrow = this.querySelector('.toggle-arrow');
            body.classList.toggle('active');
            arrow.classList.toggle('active');
          });
        });
      </script>
    </body>
    </html>
  `;
}

function renderValidationStages(validation: ValidationReport): string {
  if (!validation.validation_stages) {
    return "";
  }

  let html = "";

  // Render stages in order: syntax, linting, type_checking, tests
  const stageOrder = ["syntax", "linting", "type_checking", "tests"];

  for (const stageKey of stageOrder) {
    if (!(stageKey in validation.validation_stages)) {
      continue;
    }

    const stage = validation.validation_stages[stageKey];
    const statusIcon = stage.passed ? "✓" : "✗";
    const statusColor = stage.passed ? "#4ec9b0" : "#f48771";
    const statusClass = stage.passed ? "passed" : "failed";

    html += `
      <div class="stage">
        <div class="stage-header">
          <div class="stage-title">
            <span class="toggle-arrow">›</span>
            <span class="stage-icon" style="color: ${statusColor};">${statusIcon}</span>
            <span class="stage-name">${escapeHtml(formatStageName(stageKey))}</span>
            <span class="stage-meta ${statusClass}">
              ${stage.error_count} error${stage.error_count !== 1 ? "s" : ""}
              ${stage.warning_count > 0 ? `, ${stage.warning_count} warning${stage.warning_count !== 1 ? "s" : ""}` : ""}
            </span>
          </div>
        </div>
        <div class="stage-body">
          <p>${escapeHtml(stage.summary)}</p>
          ${renderStageDetails(stageKey, validation)}
        </div>
      </div>
    `;
  }

  return html;
}

function renderStageDetails(
  stageKey: string,
  validation: ValidationReport,
): string {
  let html = "";

  if (stageKey === "syntax" && validation.constraint_check?.results?.issues) {
    const issues = validation.constraint_check.results.issues;
    if (issues.length > 0) {
      html += renderIssuesList(issues);
    } else {
      html += '<div class="empty-message">No issues found</div>';
    }
  } else if (
    stageKey === "linting" &&
    validation.constraint_check?.results?.issues
  ) {
    const issues = validation.constraint_check.results.issues.filter(
      (i) => i.severity !== "error",
    );
    if (issues.length > 0) {
      html += renderIssuesList(issues);
    } else {
      html += '<div class="empty-message">No lint issues</div>';
    }
  } else if (
    stageKey === "type_checking" &&
    validation.constraint_check?.results?.issues
  ) {
    const issues = validation.constraint_check.results.issues.filter(
      (i) =>
        i.issue_type &&
        (i.issue_type.toLowerCase().includes("type") ||
          i.issue_type.toLowerCase().includes("annotation")),
    );
    if (issues.length > 0) {
      html += renderIssuesList(issues);
    } else {
      html += '<div class="empty-message">No type errors</div>';
    }
  } else if (stageKey === "tests" && validation.test_results) {
    if (
      validation.test_results.statistics?.failed &&
      validation.test_results.statistics.failed > 0
    ) {
      html += `
        <div style="margin-bottom: 12px;">
          <strong>Test Summary:</strong>
          <ul style="margin: 8px 0; padding-left: 20px;">
            <li>Passed: ${validation.test_results.statistics.passed || 0}</li>
            <li>Failed: <span style="color: #f48771;">${validation.test_results.statistics.failed}</span></li>
            <li>Errors: <span style="color: #f48771;">${validation.test_results.statistics.errors || 0}</span></li>
            ${validation.test_results.statistics.skipped ? `<li>Skipped: ${validation.test_results.statistics.skipped}</li>` : ""}
          </ul>
        </div>
      `;
    } else {
      html += '<div class="empty-message">All tests passed</div>';
    }
  }

  return html;
}

function renderIssuesList(
  issues: Array<{
    line: number;
    column: number;
    issue_type: string;
    message: string;
    severity: string;
  }>,
): string {
  if (issues.length === 0) {
    return '<div class="empty-message">No issues</div>';
  }

  const listItems = issues
    .map((issue) => {
      const severityClass =
        issue.severity === "error"
          ? "issue-error"
          : issue.severity === "warning"
            ? "issue-warning"
            : "issue-note";

      return `
        <li class="issue ${severityClass}">
          <div class="issue-title">${escapeHtml(issue.issue_type)}</div>
          <div class="issue-location">Line ${issue.line}, Column ${issue.column}</div>
          <div class="issue-message">${escapeHtml(issue.message)}</div>
        </li>
      `;
    })
    .join("");

  return `<ul class="issue-list">${listItems}</ul>`;
}

function formatStageName(stage: string): string {
  const names: Record<string, string> = {
    syntax: "Syntax Validation",
    linting: "Code Linting (Ruff)",
    type_checking: "Type Checking (Mypy)",
    tests: "Test Execution (Pytest)",
  };
  return names[stage] || stage;
}

function escapeHtml(text: string): string {
  const map: Record<string, string> = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  };
  return text.replace(/[&<>"']/g, (char) => map[char] || char);
}
