from typing import Dict, Any, List
from app.services.hybrid_search import hybrid_search_instance
from app.services.graph_expansion import GraphExpansion

class ContextRetriever:
    def __init__(self, graph_expansion_service: GraphExpansion):
        self.hybrid_search = hybrid_search_instance
        self.graph_expansion = graph_expansion_service

    async def retrieve_context(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """
        Orchestrates the full context retrieval pipeline.
        1. Performs a hybrid search to get initial candidate symbols.
        2. Extracts the names of the top symbols.
        3. Expands the context for these symbols using graph expansion.
        4. Combines the results into a single, rich context.
        """
        # 1. Perform hybrid search
        hybrid_results = await self.hybrid_search.search(query, limit)
        
        # 2. Extract symbol names from the top results
        symbol_names = [result.name for result in hybrid_results.results]
        
        if not symbol_names:
            return {
                "query": query,
                "search_results": [],
                "expanded_context": {}
            }
            
        # 3. Expand context using the graph
        expanded_context = await self.graph_expansion.expand_context(symbol_names)
        
        # 4. Combine and return the rich context
        return {
            "query": query,
            "search_results": hybrid_results.results,
            "expanded_context": expanded_context
        }
