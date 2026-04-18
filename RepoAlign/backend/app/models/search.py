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
