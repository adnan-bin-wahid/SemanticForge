import asyncio
from ..db.qdrant_client import get_qdrant_client
from .embeddings import generate_embedding

COLLECTION_NAME = "code_embeddings"

async def search_by_query(query: str, limit: int = 10) -> list[dict]:
    """
    Search for code symbols similar to a natural language query.
    
    Args:
        query: Natural language query text
        limit: Maximum number of results to return
        
    Returns:
        List of search results with metadata
    """
    qdrant = get_qdrant_client()
    
    # Generate embedding for the query
    query_embedding = generate_embedding(query)

    # Run the search in an executor to avoid blocking the event loop
    loop = asyncio.get_event_loop()
    search_results = await loop.run_in_executor(
        None,
        lambda: qdrant.query_points(
            collection_name=COLLECTION_NAME,
            query=query_embedding,
            limit=limit,
            with_payload=True,
        )
    )
    
    # Format results
    results = []
    if search_results and search_results.points:
        for scored_point in search_results.points:
            result = {
                "name": scored_point.payload.get("name", "") if scored_point.payload else "",
                "type": scored_point.payload.get("type", "unknown") if scored_point.payload else "unknown",
                "score": scored_point.score,
                "start_line": scored_point.payload.get("start_line", 0) if scored_point.payload else 0,
            }
            results.append(result)
    
    return results
