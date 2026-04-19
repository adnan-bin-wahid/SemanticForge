from ..services.vector_search import search_vectors
from ..services.keyword_search import keyword_search_instance
from ..models.search import VectorSearchQuery, KeywordSearchQuery, HybridSearchResponse, HybridSearchResult
import asyncio

class HybridSearch:
    def __init__(self, vector_weight: float = 0.6, keyword_weight: float = 0.4):
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight

    async def search(self, query: str, limit: int = 10) -> HybridSearchResponse:
        """
        Performs a hybrid search by combining vector and keyword search results.
        """
        # Run vector and keyword searches in parallel
        vector_search_query = VectorSearchQuery(query=query, limit=limit)
        keyword_search_query = KeywordSearchQuery(query=query, limit=limit)

        vector_results_task = search_vectors(vector_search_query)
        keyword_results_task = keyword_search_instance.search(keyword_search_query.query, keyword_search_query.limit)

        vector_response, keyword_response = await asyncio.gather(
            vector_results_task,
            keyword_results_task
        )

        # Combine and rank results
        combined_results = self._combine_and_rank(
            vector_response.results,
            keyword_response['results']
        )

        # Limit to the requested number of results
        top_results = sorted(combined_results.values(), key=lambda x: x.score, reverse=True)[:limit]

        return HybridSearchResponse(
            query=query,
            results=top_results,
            total_results=len(top_results)
        )

    def _combine_and_rank(self, vector_results, keyword_results):
        """
        Combines results using weighted scores.
        """
        combined = {}

        # Process vector results
        for res in vector_results:
            if res.name not in combined:
                combined[res.name] = HybridSearchResult(name=res.name, score=0.0, docstring=res.docstring)
            combined[res.name].score += res.score * self.vector_weight

        # Process keyword results
        for res in keyword_results:
            if res['name'] not in combined:
                combined[res['name']] = HybridSearchResult(name=res['name'], score=0.0, docstring=res.get('docstring'))
            combined[res['name']].score += res['score'] * self.keyword_weight
            # Ensure docstring is carried over if not present from vector search
            if not combined[res['name']].docstring:
                combined[res['name']].docstring = res.get('docstring')


        return combined

hybrid_search_instance = HybridSearch()
