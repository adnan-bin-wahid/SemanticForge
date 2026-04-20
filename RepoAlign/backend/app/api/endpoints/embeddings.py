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
from app.models.search import GeneratePatchRequest, GeneratePatchResponse, DiffStats
from app.services.code_generation import CodeGenerator
from app.services.diff_generator import DiffGenerator
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
    Orchestrates the full context retrieval pipeline.
    """
    context_retriever = fastapi_req.app.state.context_retriever
    response_data = await context_retriever.retrieve_context(request.query, request.limit)
    return ContextRetrievalResponse(**response_data)

@router.post("/generate-code")
async def generate_code(fastapi_req: Request, request: ContextRetrievalRequest):
    """
    Generate code based on a user instruction.
    """
    code_generator = fastapi_req.app.state.code_generator
    result = await code_generator.generate_code(request.query, request.limit)
    return result


@router.post("/generate-patch", response_model=GeneratePatchResponse)
async def generate_patch(fastapi_req: Request, request: GeneratePatchRequest):
    """
    Generate a patch/diff by comparing original code with LLM-generated code.
    
    Args:
        fastapi_req: FastAPI request context (contains app state)
        request: GeneratePatchRequest containing:
            - query: User instruction for code generation
            - original_content: Original file content to compare against
            - file_path: Path for the diff header (default: "generated.py")
            - limit: Number of context results to use (default: 10)
    
    Returns:
        GeneratePatchResponse containing:
            - unified_diff: Standard unified diff format (git-compatible)
            - stats: Diff statistics (lines added/removed/modified, similarity ratio)
            - generated_code: The LLM-generated code
            - file_path: The file path used in the diff
    """
    code_generator = fastapi_req.app.state.code_generator
    diff_generator = DiffGenerator()
    
    # Step 1: Generate code based on user instruction
    generation_result = await code_generator.generate_code(request.query, request.limit)
    generated_code = generation_result.get("generated_code", "")
    
    # Step 2: Create diff between original and generated
    unified_diff = diff_generator.generate_unified_diff(
        original_content=request.original_content,
        generated_content=generated_code,
        file_path=request.file_path
    )
    
    # Step 3: Calculate statistics
    stats_dict = diff_generator.get_diff_stats(request.original_content, generated_code)
    stats = DiffStats(**stats_dict)
    
    # Step 4: Return complete response
    return GeneratePatchResponse(
        query=request.query,
        unified_diff=unified_diff,
        stats=stats,
        generated_code=generated_code,
        file_path=request.file_path
    )
