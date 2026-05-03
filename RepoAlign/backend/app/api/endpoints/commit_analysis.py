import ast
from fastapi import APIRouter, Request

from app.models.staged_changes import (
    AnalyzeStagedChangesRequest,
    ChangedSymbol,
    CommitBlockingFinding,
    CommitAnalysisResponse,
    CommitAnalysisSummary,
)

router = APIRouter()


def _summarize_request(request: AnalyzeStagedChangesRequest) -> CommitAnalysisSummary:
    return CommitAnalysisSummary(
        total_files=len(request.files),
        python_files=sum(1 for file in request.files if file.language == "python"),
        total_hunks=sum(len(file.hunks) for file in request.files),
        total_changed_symbols=sum(len(file.changedSymbols) for file in request.files),
        additions=sum(file.additions or 0 for file in request.files),
        deletions=sum(file.deletions or 0 for file in request.files),
    )


def _collect_changed_symbols(
    request: AnalyzeStagedChangesRequest,
) -> list[ChangedSymbol]:
    symbols: list[ChangedSymbol] = []
    seen: set[tuple[str, str, int]] = set()

    for file in request.files:
        for symbol in file.changedSymbols:
            key = (file.path, symbol.name, symbol.startLine)
            if key in seen:
                continue
            seen.add(key)
            symbols.append(symbol)

    return symbols


def _validate_staged_python(
    request: AnalyzeStagedChangesRequest,
) -> tuple[list[str], list[CommitBlockingFinding]]:
    diagnostics: list[str] = []
    findings: list[CommitBlockingFinding] = []

    for file in request.files:
        if file.language != "python" or file.status.startswith("D"):
            continue

        try:
            ast.parse(file.newContent)
        except SyntaxError as e:
            reason = f"syntax error at line {e.lineno}: {e.msg}"
            diagnostics.append(f"{file.path}: {reason}")
            findings.append(
                CommitBlockingFinding(
                    severity="blocker",
                    affected_file=file.path,
                    affected_symbol=None,
                    reason=reason,
                    matched_pattern="python-syntax-error",
                    suggested_fix="Fix the staged Python syntax error, stage the corrected file, and run analysis again.",
                    validation_status="failed",
                )
            )

    return diagnostics, findings


def _build_scope_findings(
    request: AnalyzeStagedChangesRequest,
    summary: CommitAnalysisSummary,
) -> list[CommitBlockingFinding]:
    findings: list[CommitBlockingFinding] = []

    if summary.total_changed_symbols > 5:
        findings.append(
            CommitBlockingFinding(
                severity="warning",
                affected_file="*",
                affected_symbol=None,
                reason=f"large symbol scope: {summary.total_changed_symbols} changed symbols",
                matched_pattern="large-symbol-scope",
                suggested_fix="Review the staged symbols before committing, or split the change into smaller commits.",
                validation_status="warning",
            )
        )

    for file in request.files:
        if len(file.hunks) > 8:
            findings.append(
                CommitBlockingFinding(
                    severity="warning",
                    affected_file=file.path,
                    affected_symbol=None,
                    reason=f"large file diff: {len(file.hunks)} staged hunks",
                    matched_pattern="large-file-diff",
                    suggested_fix="Review this file carefully or split unrelated changes.",
                    validation_status="warning",
                )
            )

    return findings


def _recommend(
    summary: CommitAnalysisSummary,
    diagnostics: list[str],
    findings: list[CommitBlockingFinding],
) -> str:
    if any(finding.severity == "blocker" for finding in findings):
        return "blocked"

    if diagnostics:
        return "review"

    if any(finding.severity in {"warning", "error"} for finding in findings):
        return "review"

    if summary.total_files == 0:
        return "ready"

    if summary.total_changed_symbols > 5 or summary.total_files > 8:
        return "review"

    return "ready"


@router.post(
    "/analyze-staged-changes",
    response_model=CommitAnalysisResponse,
    tags=["Commit Analysis", "Extension"],
)
async def analyze_staged_changes(
    fastapi_req: Request,
    request: AnalyzeStagedChangesRequest,
):
    """
    Analyze structured staged changes for the commit-time workflow.

    The extension sends parsed hunks, staged old/new content, and changed Python
    symbol metadata. This endpoint keeps the commit path advisory only: it
    returns diagnostics, retrieved graph context, and a recommendation without
    mutating Git state or blocking a push.
    """
    summary = _summarize_request(request)
    changed_symbols = _collect_changed_symbols(request)
    diagnostics, findings = _validate_staged_python(request)
    findings.extend(_build_scope_findings(request, summary))
    retrieved_context = {}

    if changed_symbols:
        query = " ".join(symbol.name for symbol in changed_symbols[:10])
        try:
            context_retriever = fastapi_req.app.state.context_retriever
            retrieved_context = await context_retriever.retrieve_context(query, 10)
        except Exception as e:
            diagnostics.append(f"context retrieval unavailable: {str(e)}")

    return CommitAnalysisResponse(
        status="ok",
        recommendation=_recommend(summary, diagnostics, findings),
        summary=summary,
        changed_symbols=changed_symbols,
        findings=findings,
        diagnostics=diagnostics,
        retrieved_context=retrieved_context,
    )
