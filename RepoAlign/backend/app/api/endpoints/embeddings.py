from fastapi import APIRouter
from ...services.embedding_indexer import EmbeddingIndexer
from ...services.vector_search import search_by_query
from ...models.search import VectorSearchQuery, VectorSearchResponse, SearchResult
from app.services.keyword_search import keyword_search_instance
from app.models.search import KeywordSearchQuery, KeywordSearchResponse
from app.services.hybrid_search import hybrid_search_instance
from app.models.search import HybridSearchResponse
from app.services.graph_expansion import GraphExpansion
from app.models.search import GraphExpansionRequest, GraphExpansionResponse
from app.models.search import ContextRetrievalRequest, ContextRetrievalResponse
from fastapi import Request

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

@router.post("/expand-context", response_model=GraphExpansionResponse)
async def expand_context(fastapi_req: Request, request: GraphExpansionRequest):
    """
    Expand the context of a list of symbols by querying the graph for neighbors.
    """
    graph_expansion_service = fastapi_req.app.state.graph_expansion_service
    expanded_context = await graph_expansion_service.expand_context(request.symbols)
    return GraphExpansionResponse(expanded_context=expanded_context)

@router.post("/retrieve-context", response_model=ContextRetrievalResponse)
async def retrieve_context(fastapi_req: Request, request: ContextRetrievalRequest):
    """
    Retrieve a rich, structured context for a given query.
    Orchestrates hybrid search and graph expansion.
    """
    context_retriever = fastapi_req.app.state.context_retriever
    response_data = await context_retriever.retrieve_context(request.query, request.limit)
    
    # The response from the service already matches the structure needed,
    # but we'll build the Pydantic model for validation and clarity.
    return ContextRetrievalResponse(
        query=response_data["query"],
        search_results=response_data["search_results"],
        expanded_context=response_data["expanded_context"]
    )
