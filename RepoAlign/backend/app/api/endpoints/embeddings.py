from fastapi import APIRouter
from ...services.embedding_indexer import EmbeddingIndexer
from ...services.vector_search import search_by_query
from ...models.search import VectorSearchQuery, VectorSearchResponse, SearchResult

router = APIRouter()

@router.post("/index-embeddings")
async def index_embeddings():
    """
    Trigger indexing of all code symbols from Neo4j into Qdrant.
    Generates embeddings and stores them for vector search.
    
    Returns:
        Indexing statistics and status
    """
    indexer = EmbeddingIndexer()
    result = await indexer.index_repository()
    return result

@router.post("/vector-search", response_model=VectorSearchResponse)
async def vector_search(request: VectorSearchQuery):
    """
    Search for code symbols using semantic similarity.
    
    Args:
        request: Contains the natural language query and optional limit
        
    Returns:
        List of semantically similar code symbols with scores
    """
    results = await search_by_query(request.query, request.limit)
    
    # Convert to SearchResult objects
    search_results = [
        SearchResult(
            name=r["name"],
            type=r["type"],
            score=r["score"],
            start_line=r["start_line"],
        )
        for r in results
    ]
    
    return VectorSearchResponse(
        query=request.query,
        results=search_results,
        total_results=len(search_results),
    )
