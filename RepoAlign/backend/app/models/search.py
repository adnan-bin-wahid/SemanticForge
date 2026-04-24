from pydantic import BaseModel

class VectorSearchQuery(BaseModel):
    """Request model for vector search."""
    query: str
    limit: int = 10

class SearchResult(BaseModel):
    """Single search result."""
    name: str
    type: str  # "function" or "class"
    score: float
    start_line: int

class VectorSearchResponse(BaseModel):
    """Response model for vector search."""
    query: str
    results: list[SearchResult]
    total_results: int

class KeywordSearchQuery(BaseModel):
    """Request model for keyword search."""
    query: str
    limit: int = 10

class KeywordSearchResult(BaseModel):
    """Single keyword search result."""
    name: str
    score: float
    docstring: str | None = None

class KeywordSearchResponse(BaseModel):
    """Response model for keyword search."""
    query: str
    results: list[KeywordSearchResult]
    total_results: int

class HybridSearchResult(BaseModel):
    """Single hybrid search result."""
    name: str
    score: float
    docstring: str | None = None

class HybridSearchResponse(BaseModel):
    """Response model for hybrid search."""
    query: str
    results: list[HybridSearchResult]
    total_results: int

class GraphExpansionRequest(BaseModel):
    """Request model for graph expansion."""
    symbols: list[str]
    
class NeighborInfo(BaseModel):
    """Information about a neighboring symbol."""
    code: str | None
    path: str | None
    type: str # "caller" or "callee"

class SymbolContext(BaseModel):
    """Expanded context for a single symbol."""
    code: str | None
    path: str | None
    neighbors: dict[str, NeighborInfo]

class GraphExpansionResponse(BaseModel):
    """Response model for graph expansion."""
    expanded_context: dict[str, SymbolContext]

class ContextRetrievalRequest(BaseModel):
    """Request model for full context retrieval."""
    query: str
    limit: int = 10

class ContextRetrievalResponse(BaseModel):
    """Response model for full context retrieval."""
    query: str
    search_results: list[HybridSearchResult]
    expanded_context: dict[str, SymbolContext]


class GeneratePatchRequest(BaseModel):
    """Request model for patch generation."""
    query: str  # The user's instruction for code generation
    original_content: str  # Original file content to compare against
    file_path: str = "generated.py"  # For use in diff header
    limit: int = 10  # Number of context results to use
    # Optional validation parameters
    repo_path: str | None = None  # Path to repository (if provided, validation runs)
    file_relative_path: str | None = None  # Relative path in repo (if not provided, uses file_path)
    run_tests: bool = False  # Whether to run tests (default False for speed)
    test_directory: str = "tests"  # Path to tests relative to repo
    strict: bool = False  # Use strict type checking in validation
    test_timeout: int = 60  # Test execution timeout in seconds


class DiffStats(BaseModel):
    """Statistics about generated diff."""
    lines_added: int
    lines_removed: int
    lines_modified: int
    total_changes: int
    similarity_ratio: float  # 0.0 to 1.0
    identical: bool


class ValidationReport(BaseModel):
    """Validation report for a patch."""
    overall_status: str  # "passed" or "failed"
    overall_summary: str
    constraint_check: dict | None = None
    test_results: dict | None = None
    total_issues: int
    total_errors: int
    total_warnings: int
    validation_stages: dict | None = None


class GeneratePatchResponse(BaseModel):
    """Response model for patch generation."""
    query: str
    unified_diff: str  # The actual diff in unified format
    stats: DiffStats
    generated_code: str  # The generated code
    file_path: str
    validation: ValidationReport | None = None  # Validation report (if validation ran)
