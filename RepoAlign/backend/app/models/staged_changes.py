from pydantic import BaseModel, Field
from typing import Literal, Optional, Any


class StagedDiffHunk(BaseModel):
    header: str
    oldStart: int
    oldLines: int
    newStart: int
    newLines: int
    changedOldLines: list[int] = Field(default_factory=list)
    changedNewLines: list[int] = Field(default_factory=list)
    patch: str


class ChangedSymbol(BaseModel):
    name: str
    type: Literal["function", "class"]
    startLine: int
    endLine: int
    changedLines: list[int] = Field(default_factory=list)
    content: str


class StagedFileChange(BaseModel):
    status: str
    path: str
    previousPath: Optional[str] = None
    additions: Optional[int] = None
    deletions: Optional[int] = None
    language: Literal["python", "other"]
    oldContent: str
    newContent: str
    hunks: list[StagedDiffHunk] = Field(default_factory=list)
    changedSymbols: list[ChangedSymbol] = Field(default_factory=list)


class AnalyzeStagedChangesRequest(BaseModel):
    workspaceId: Optional[str] = None
    workspaceName: str
    backendUrl: str
    files: list[StagedFileChange] = Field(default_factory=list)


class CommitAnalysisSummary(BaseModel):
    total_files: int
    python_files: int
    total_hunks: int
    total_changed_symbols: int
    additions: int
    deletions: int


class CommitAnalysisResponse(BaseModel):
    status: Literal["ok"]
    recommendation: Literal["ready", "review", "blocked"]
    summary: CommitAnalysisSummary
    changed_symbols: list[ChangedSymbol]
    diagnostics: list[str] = Field(default_factory=list)
    retrieved_context: dict[str, Any] = Field(default_factory=dict)
