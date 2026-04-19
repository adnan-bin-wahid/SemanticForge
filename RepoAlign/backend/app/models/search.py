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
