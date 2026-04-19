from pydantic import BaseModel
from typing import List, Optional

class SearchRequest(BaseModel):
    query: str
    limit: int = 10

class VectorSearchResult(BaseModel):
    name: str
    type: str
    score: float
    start_line: int

class VectorSearchResponse(BaseModel):
    query: str
    results: List[VectorSearchResult]
    total_results: int

class KeywordSearchResult(BaseModel):
    name: str
    score: float
    docstring: Optional[str] = None

class KeywordSearchResponse(BaseModel):
    query: str
    results: List[KeywordSearchResult]
    total_results: int
