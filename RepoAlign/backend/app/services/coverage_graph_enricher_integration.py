"""Integration wrapper for coverage graph enrichment service."""

import logging
from typing import Dict, Any
from app.services.coverage_graph_enricher import enrich_coverage_graph as enrich_graph

logger = logging.getLogger(__name__)


def get_coverage_graph_enrichment(
    repo_path: str,
    neo4j_uri: str = "bolt://neo4j:7687",
    neo4j_user: str = "neo4j",
    neo4j_password: str = "password"
) -> Dict[str, Any]:
    """
    Execute coverage graph enrichment.
    
    Args:
        repo_path: Path to repository
        neo4j_uri: Neo4j connection URI
        neo4j_user: Neo4j username
        neo4j_password: Neo4j password
        
    Returns:
        Enrichment results
    """
    logger.info(f"[PHASE 7.3] Starting coverage graph enrichment for {repo_path}")
    
    result = enrich_graph(repo_path, neo4j_uri, neo4j_user, neo4j_password)
    
    logger.info(f"[PHASE 7.3] Coverage graph enrichment completed: {result.get('edges_created', 0)} edges created")
    
    return result
