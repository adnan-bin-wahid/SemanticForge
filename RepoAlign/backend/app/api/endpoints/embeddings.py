from fastapi import APIRouter
from ...services.embedding_indexer import EmbeddingIndexer
from ...services.vector_search import search_by_query
from ...models.search import VectorSearchQuery, VectorSearchResponse, SearchResult
from app.services.keyword_search import keyword_search_instance
from app.models.search import KeywordSearchQuery, KeywordSearchResponse
from app.services.hybrid_search import hybrid_search_instance
from app.models.search import HybridSearchResponse

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

@router.post("/keyword-search", response_model=KeywordSearchResponse)
async def keyword_search(request: KeywordSearchQuery):
    """
    Search for code symbols using keyword matching.
    
    Args:
        request: Contains the query and optional limit
        
    Returns:
        List of relevant code symbols with scores
    """
    # Ensure the index is built before searching
    if not keyword_search_instance.bm25:
        await keyword_search_instance.index_documents()
        
    results = keyword_search_instance.search(request.query, request.limit)
    
    return KeywordSearchResponse(
        query=request.query,
        results=results,
        total_results=len(results),
    )

@router.post("/hybrid-search", response_model=HybridSearchResponse)
async def hybrid_search(request: VectorSearchQuery):
    """
    Perform a hybrid search combining vector and keyword search.
    """
    results = await hybrid_search_instance.search(request.query, request.limit)
    return results
