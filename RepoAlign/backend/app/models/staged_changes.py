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
    filePath: Optional[str] = None


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


class CommitBlockingFinding(BaseModel):
    severity: Literal["info", "warning", "error", "blocker"]
    affected_file: str
    affected_symbol: Optional[str] = None
    reason: str
    matched_pattern: Optional[str] = None
    suggested_fix: Optional[str] = None
    validation_status: Literal["passed", "warning", "failed"]


class PatternCandidate(BaseModel):
    name: str
    type: str
    score: float
    path: Optional[str] = None
    content: Optional[str] = None


class PatternSummary(BaseModel):
    convention: str
    examples: list[str] = Field(default_factory=list)
    structural_features: dict[str, Any] = Field(default_factory=dict)


class PatternDetectionResult(BaseModel):
    changed_symbol: str
    candidates: list[PatternCandidate] = Field(default_factory=list)
    summary: Optional[PatternSummary] = None
    mismatch_score: float = 0.0
    confidence: float = 0.0
    findings: list[CommitBlockingFinding] = Field(default_factory=list)


class CommitAnalysisResponse(BaseModel):
    status: Literal["ok"]
    recommendation: Literal["ready", "review", "blocked"]
    summary: CommitAnalysisSummary
    changed_symbols: list[ChangedSymbol]
    findings: list[CommitBlockingFinding] = Field(default_factory=list)
    pattern_results: list[PatternDetectionResult] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
    retrieved_context: dict[str, Any] = Field(default_factory=dict)
