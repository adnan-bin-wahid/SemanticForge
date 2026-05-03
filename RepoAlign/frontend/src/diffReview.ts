/**
 * Diff Review Module for Phase 12.2
 * 
 * Provides side-by-side diff review functionality showing staged code
 * versus RepoAlign's suggested aligned version.
 */

import * as vscode from "vscode";
import * as path from "path";
import * as fs from "fs";
import axios from "axios";

interface AlignedCodeRequest {
  workspace_name: string;
  affected_file: string;
  affected_symbol: string | null;
  current_code: string;
  reason: string;
  matched_pattern?: string;
  pattern_convention?: string;
  pattern_examples?: string[];
  file_content?: string;
}

interface AlignedCodeResponse {
  status: string;
  suggested_code: string;
  explanation: string;
  confidence: number;
  changes_summary: string;
}

interface DiffReviewContext {
  finding: any;
  workspaceName: string;
  workspacePath: string;
  backendUrl: string;
  changedSymbols?: any[];
}

/**
 * Opens a diff editor showing staged code vs suggested aligned version.
 */
export async function reviewFindingDiff(context: DiffReviewContext): Promise<void> {
  try {
    // Step 1: Get the current staged code for the affected symbol
    const currentCode = await getCurrentStagedCode(context);
    
    if (!currentCode) {
      vscode.window.showErrorMessage("Could not extract staged code for this finding.");
      return;
    }

    // Step 2: Generate aligned code suggestion from backend
    const alignedResponse = await generateAlignedCode(context, currentCode);
    
    if (!alignedResponse || !alignedResponse.suggested_code) {
      vscode.window.showErrorMessage("Failed to generate aligned code suggestion.");
      return;
    }

    // Step 3: Create temporary files for diff comparison
    const tempDir = await createTempDiffFiles(
      context,
      currentCode,
      alignedResponse.suggested_code
    );

    // Step 4: Open diff editor
    // Resolve actual file name for display
    let displayFileName = context.finding.affected_file;
    if (displayFileName === "staged-change" && context.changedSymbols && context.finding.affected_symbol) {
      const matchingSymbol = context.changedSymbols.find(
        (sym: any) => sym.name === context.finding.affected_symbol
      );
      if (matchingSymbol && matchingSymbol.filePath) {
        displayFileName = matchingSymbol.filePath;
      }
    }
    
    await openDiffEditor(
      tempDir.stagedFile,
      tempDir.suggestedFile,
      displayFileName,
      alignedResponse
    );

    // Step 5: Show action buttons for accept/reject/edit
    await showDiffActions(context, tempDir, alignedResponse);

  } catch (error: any) {
    vscode.window.showErrorMessage(
      `Diff review failed: ${error.message || String(error)}`
    );
  }
}

/**
 * Extract the current staged code for the affected symbol.
 */
async function getCurrentStagedCode(context: DiffReviewContext): Promise<string | null> {
  const { finding, workspacePath, changedSymbols } = context;
  
  try {
    // Resolve the actual file path if affected_file is "staged-change"
    const actualFilePath = resolveActualFilePath(finding, changedSymbols);
    
    if (!actualFilePath) {
      console.error("Could not resolve file path");
      return null;
    }
    
    // Get the full file content from staged changes
    const filePath = path.join(workspacePath, actualFilePath);
    
    // Read the current file (staged version should be in working directory)
    if (fs.existsSync(filePath)) {
      const content = fs.readFileSync(filePath, "utf-8");
      
      // If there's a specific symbol, try to extract it
      if (finding.affected_symbol) {
        const symbolCode = extractSymbolFromCode(content, finding.affected_symbol);
        if (symbolCode) {
          return symbolCode;
        }
      }
      
      // Return full file content as fallback
      return content;
    }
    
    return null;
  } catch (error) {
    console.error("Error getting current staged code:", error);
    return null;
  }
}

/**
 * Resolve the actual file path from a finding.
 * Handles "staged-change" placeholder by looking up in changed_symbols.
 */
function resolveActualFilePath(
  finding: any,
  changedSymbols?: any[]
): string | null {
  let actualFilePath = finding.affected_file;
  
  if (actualFilePath === "staged-change" && changedSymbols && finding.affected_symbol) {
    // Look up the real file path from changed_symbols
    const matchingSymbol = changedSymbols.find(
      (sym: any) => sym.name === finding.affected_symbol
    );
    
    if (matchingSymbol && matchingSymbol.filePath) {
      actualFilePath = matchingSymbol.filePath;
    } else {
      return null;
    }
  }
  
  return actualFilePath === "staged-change" ? null : actualFilePath;
}

/**
 * Extract a specific symbol (function/class) from Python code.
 */
function extractSymbolFromCode(code: string, symbolName: string): string | null {
  const lines = code.split("\n");
  let startLine = -1;
  let endLine = -1;
  let indentLevel = 0;

  // Find the start of the symbol definition
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();
    
    // Match function or class definition
    const defMatch = trimmed.match(/^(?:async\s+)?def\s+(\w+)/) || trimmed.match(/^class\s+(\w+)/);
    
    if (defMatch && defMatch[1] === symbolName) {
      startLine = i;
      // Calculate indent level
      indentLevel = line.length - line.trimStart().length;
      break;
    }
  }

  if (startLine === -1) {
    return null;
  }

  // Find the end of the symbol (next def/class at same or lower indent level)
  for (let i = startLine + 1; i < lines.length; i++) {
    const line = lines[i];
    const currentIndent = line.length - line.trimStart().length;
    const trimmed = line.trim();
    
    // Empty lines or comments are part of the symbol
    if (!trimmed || trimmed.startsWith("#")) {
      continue;
    }
    
    // If we hit something at same or lower indent level, we've found the end
    if (currentIndent <= indentLevel && trimmed) {
      endLine = i;
      break;
    }
  }

  // If no end found, go to end of file
  if (endLine === -1) {
    endLine = lines.length;
  }

  return lines.slice(startLine, endLine).join("\n");
}

/**
 * Call backend API to generate aligned code suggestion.
 */
async function generateAlignedCode(
  context: DiffReviewContext,
  currentCode: string
): Promise<AlignedCodeResponse | null> {
  const { finding, workspaceName, backendUrl } = context;
  
  const request: AlignedCodeRequest = {
    workspace_name: workspaceName,
    affected_file: finding.affected_file,
    affected_symbol: finding.affected_symbol,
    current_code: currentCode,
    reason: finding.reason,
    matched_pattern: finding.matched_pattern,
    pattern_convention: undefined, // Could be passed from pattern detection results
    pattern_examples: [],
  };

  try {
    const response = await axios.post<AlignedCodeResponse>(
      `${backendUrl}/generate-aligned-code`,
      request,
      { timeout: 60000 }  // 60 second timeout for LLM generation
    );
    
    return response.data;
  } catch (error: any) {
    if (axios.isAxiosError(error)) {
      console.error("Backend error:", error.response?.data || error.message);
    } else {
      console.error("Error generating aligned code:", error);
    }
    return null;
  }
}

/**
 * Create temporary files for diff comparison.
 */
async function createTempDiffFiles(
  context: DiffReviewContext,
  stagedCode: string,
  suggestedCode: string
): Promise<{ stagedFile: vscode.Uri; suggestedFile: vscode.Uri; tempDir: string }> {
  const tempDir = path.join(context.workspacePath, ".repoalign", "diffs");
  
  // Ensure temp directory exists
  if (!fs.existsSync(tempDir)) {
    fs.mkdirSync(tempDir, { recursive: true });
  }

  const timestamp = Date.now();
  
  // Resolve actual file path for base name
  const actualFilePath = resolveActualFilePath(context.finding, context.changedSymbols) || context.finding.affected_file;
  const baseName = path.basename(actualFilePath, ".py");
  
  const stagedPath = path.join(tempDir, `${baseName}.staged.${timestamp}.py`);
  const suggestedPath = path.join(tempDir, `${baseName}.aligned.${timestamp}.py`);

  fs.writeFileSync(stagedPath, stagedCode, "utf-8");
  fs.writeFileSync(suggestedPath, suggestedCode, "utf-8");

  return {
    stagedFile: vscode.Uri.file(stagedPath),
    suggestedFile: vscode.Uri.file(suggestedPath),
    tempDir
  };
}

/**
 * Open VS Code's built-in diff editor.
 */
async function openDiffEditor(
  stagedFile: vscode.Uri,
  suggestedFile: vscode.Uri,
  originalFileName: string,
  alignedResponse: AlignedCodeResponse
): Promise<void> {
  const title = `${path.basename(originalFileName)} ↔ RepoAlign Suggestion`;
  
  // Open diff editor
  await vscode.commands.executeCommand(
    "vscode.diff",
    stagedFile,
    suggestedFile,
    title
  );

  // Show explanation in info message
  vscode.window.showInformationMessage(
    `RepoAlign Suggestion (${(alignedResponse.confidence * 100).toFixed(0)}% confidence): ${alignedResponse.explanation}`,
    "Accept Changes",
    "Reject",
    "Edit Manually"
  ).then((choice) => {
    if (choice === "Accept Changes") {
      vscode.window.showInformationMessage("Use the action buttons below the diff to accept changes.");
    } else if (choice === "Edit Manually") {
      vscode.window.showInformationMessage("Edit the right pane and save your changes.");
    }
  });
}

/**
 * Show action buttons for accept/reject/edit in the diff view.
 */
async function showDiffActions(
  context: DiffReviewContext,
  tempFiles: { stagedFile: vscode.Uri; suggestedFile: vscode.Uri; tempDir: string },
  alignedResponse: AlignedCodeResponse
): Promise<void> {
  const actions = [
    "Accept Suggestion",
    "Reject and Keep Staged",
    "Edit and Apply",
    "Cancel"
  ];

  const choice = await vscode.window.showInformationMessage(
    `Review the diff above. ${alignedResponse.changes_summary}`,
    ...actions
  );

  switch (choice) {
    case "Accept Suggestion":
      await acceptSuggestion(context, tempFiles.suggestedFile);
      break;
    
    case "Reject and Keep Staged":
      await rejectSuggestion(context);
      break;
    
    case "Edit and Apply":
      await editAndApply(context, tempFiles.suggestedFile);
      break;
    
    default:
      // Cancel or dismissed
      cleanupTempFiles(tempFiles.tempDir);
      break;
  }
}

/**
 * Accept the suggestion and apply it to the file.
 */
async function acceptSuggestion(
  context: DiffReviewContext,
  suggestedFile: vscode.Uri
): Promise<void> {
  try {
    // Read the suggested code
    const suggestedCode = fs.readFileSync(suggestedFile.fsPath, "utf-8");
    
    // Resolve the actual file path
    const actualFilePath = resolveActualFilePath(context.finding, context.changedSymbols);
    
    if (!actualFilePath) {
      vscode.window.showErrorMessage("Could not determine target file path.");
      return;
    }
    
    // Get the target file path
    const targetFile = path.join(context.workspacePath, actualFilePath);
    
    // If it's a symbol-level change, we need to replace just that symbol
    if (context.finding.affected_symbol) {
      // For now, replace the whole file (symbol-level replacement is complex)
      vscode.window.showWarningMessage(
        "Symbol-level replacement not yet supported. Applying to whole file."
      );
    }
    
    // Write the suggested code to the target file
    fs.writeFileSync(targetFile, suggestedCode, "utf-8");
    
    // Re-stage the file
    await vscode.commands.executeCommand("git.stage", vscode.Uri.file(targetFile));
    
    // Show resolved file path in success message
    vscode.window.showInformationMessage(
      `✓ Applied aligned code to ${actualFilePath} and re-staged.`
    );
    
    // Re-run analysis to update findings
    await vscode.commands.executeCommand("repoalign.analyzeStagedChanges");
    
  } catch (error: any) {
    vscode.window.showErrorMessage(`Failed to apply suggestion: ${error.message}`);
  }
}

/**
 * Reject the suggestion and keep the staged code as-is.
 */
async function rejectSuggestion(context: DiffReviewContext): Promise<void> {
  const actualFilePath = resolveActualFilePath(context.finding, context.changedSymbols) || context.finding.affected_file;
  
  vscode.window.showInformationMessage(
    `Keeping staged code in ${actualFilePath}. You may want to add an ignore comment if this is intentional.`
  );
  
  // Close the diff editor
  await vscode.commands.executeCommand("workbench.action.closeActiveEditor");
}

/**
 * Let user edit the suggestion and then apply it.
 */
async function editAndApply(
  context: DiffReviewContext,
  suggestedFile: vscode.Uri
): Promise<void> {
  // Open the suggested file for editing
  const doc = await vscode.workspace.openTextDocument(suggestedFile);
  await vscode.window.showTextDocument(doc);
  
  vscode.window.showInformationMessage(
    "Edit the code as needed, then save and click 'Apply Edited Code'.",
    "Apply Edited Code",
    "Cancel"
  ).then(async (choice) => {
    if (choice === "Apply Edited Code") {
      await acceptSuggestion(context, suggestedFile);
    }
  });
}

/**
 * Clean up temporary diff files.
 */
function cleanupTempFiles(tempDir: string): void {
  try {
    if (fs.existsSync(tempDir)) {
      const files = fs.readdirSync(tempDir);
      for (const file of files) {
        fs.unlinkSync(path.join(tempDir, file));
      }
    }
  } catch (error) {
    console.error("Error cleaning up temp files:", error);
  }
}
