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
