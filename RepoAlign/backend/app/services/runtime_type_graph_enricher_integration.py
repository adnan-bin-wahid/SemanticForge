"""
Phase 7.8 Integration Wrapper
High-level interface for runtime type graph enrichment.
Orchestrates Phase 7.7 type collection followed by Phase 7.8 graph enrichment.
"""

import logging
import os
from typing import Dict, Any

from app.services.runtime_type_graph_enricher import RuntimeTypeGraphEnricher
from app.services.runtime_type_collector_integration import collect_runtime_types

logger = logging.getLogger(__name__)


def enrich_function_types(repo_path: str) -> Dict[str, Any]:
    """
    Run Phase 7.7 (if needed) and Phase 7.8 to enrich Function nodes with runtime type properties.
    
    This is the main entry point for runtime type graph enrichment.
    It orchestrates:
    1. Phase 7.4: Dynamic profiling (if not already done)
    2. Phase 7.7: Runtime type collection
    3. Phase 7.8: Add type properties to Function nodes in Neo4j
    
    Args:
        repo_path: Path to the repository to analyze
    
    Returns:
        Structured response with phase information and results
    """
    logger.info(f"[PHASE 7.8] Starting runtime type graph enrichment pipeline for {repo_path}")
    
    try:
        # Get Neo4j credentials from environment
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
        
        # Step 1: Run Phase 7.7 to collect runtime types
        logger.info("[PHASE 7.8] Running Phase 7.7 (Runtime Type Collection)...")
        type_response = collect_runtime_types(repo_path)
        
        if type_response.get("status") != "success":
            logger.error(f"[PHASE 7.8] Phase 7.7 failed: {type_response}")
            return {
                "phase": "7.8",
                "status": "failed",
                "error": f"Phase 7.7 type collection failed: {type_response.get('error', 'Unknown error')}"
            }
        
        type_data = type_response
        logger.info(f"[PHASE 7.8] Phase 7.7 completed: {len(type_data.get('function_types', {}))} functions with types")
        
        # Step 2: Create runtime type graph enricher
        logger.info("[PHASE 7.8] Initializing RuntimeTypeGraphEnricher...")
        enricher = RuntimeTypeGraphEnricher(neo4j_uri, neo4j_user, neo4j_password)
        
        try:
            # Step 3: Enrich the graph with function types
            logger.info("[PHASE 7.8] Enriching Function nodes with type properties...")
            result = enricher.enrich_function_types(type_data)
            
            # Step 4: Get statistics about enriched functions
            enriched_stats = enricher.get_enriched_functions()
            result["enriched_functions_statistics"] = enriched_stats
            
            logger.info(f"[PHASE 7.8] ✓ Enrichment complete: {result['summary']['functions_updated']} functions updated")
            
            return result
            
        finally:
            enricher.close()
        
    except Exception as e:
        logger.error(f"[PHASE 7.8] Error during type graph enrichment: {str(e)}", exc_info=True)
        return {
            "phase": "7.8",
            "status": "failed",
            "error": str(e)
        }
