import ast
from fastapi import APIRouter, Request

from app.models.staged_changes import (
    AnalyzeStagedChangesRequest,
    ChangedSymbol,
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


def _validate_staged_python(request: AnalyzeStagedChangesRequest) -> list[str]:
    diagnostics: list[str] = []

    for file in request.files:
        if file.language != "python" or file.status.startswith("D"):
            continue

        try:
            ast.parse(file.newContent)
        except SyntaxError as e:
            diagnostics.append(
                f"{file.path}: syntax error at line {e.lineno}: {e.msg}"
            )

    return diagnostics


def _recommend(summary: CommitAnalysisSummary, diagnostics: list[str]) -> str:
    if any("syntax error" in diagnostic for diagnostic in diagnostics):
        return "blocked"

    if diagnostics:
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
    diagnostics = _validate_staged_python(request)
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
        recommendation=_recommend(summary, diagnostics),
        summary=summary,
        changed_symbols=changed_symbols,
        diagnostics=diagnostics,
        retrieved_context=retrieved_context,
    )
