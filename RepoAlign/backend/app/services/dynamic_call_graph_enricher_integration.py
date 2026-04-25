"""
Phase 7.6 Integration Wrapper
High-level interface for dynamic call graph enrichment.
Orchestrates Phase 7.5 processing followed by Phase 7.6 edge creation.
"""

import logging
import os
from typing import Dict, Any

from app.services.dynamic_call_graph_enricher import DynamicCallGraphEnricher
from app.services.call_trace_processor_integration import get_processed_trace

logger = logging.getLogger(__name__)


def enrich_dynamic_call_graph(repo_path: str) -> Dict[str, Any]:
    """
    Run Phase 7.5 (if needed) and Phase 7.6 to enrich the graph with dynamic call edges.
    
    This is the main entry point for dynamic call graph enrichment.
    It orchestrates:
    1. Phase 7.4: Dynamic profiling (if not already done)
    2. Phase 7.5: Call trace processing
    3. Phase 7.6: Create DYNAMICALLY_CALLS edges in Neo4j
    
    Args:
        repo_path: Path to the repository to analyze
    
    Returns:
        Structured response with phase information and results
    """
    logger.info(f"[PHASE 7.6] Starting dynamic call graph enrichment pipeline for {repo_path}")
    
    try:
        # Get Neo4j credentials from environment
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
        
        # Step 1: Run Phase 7.5 to get processed trace data
        logger.info("[PHASE 7.6] Running Phase 7.5 processing...")
        trace_response = get_processed_trace(repo_path)
        
        if trace_response.get("status") != "success":
            logger.error(f"[PHASE 7.6] Phase 7.5 failed: {trace_response}")
            return {
                "phase": "7.6",
                "status": "failed",
                "error": f"Phase 7.5 processing failed: {trace_response.get('error', 'Unknown error')}"
            }
        
        # The trace_response itself is the trace_data (already processed)
        trace_data = trace_response
        logger.info(f"[PHASE 7.6] Phase 7.5 completed with {len(trace_data.get('calls', []))} call pairs")
        
        # Step 2: Create dynamic call graph enricher
        logger.info("[PHASE 7.6] Initializing DynamicCallGraphEnricher...")
        enricher = DynamicCallGraphEnricher(neo4j_uri, neo4j_user, neo4j_password)
        
        try:
            # Step 3: Enrich the graph with DYNAMICALLY_CALLS edges
            logger.info("[PHASE 7.6] Creating DYNAMICALLY_CALLS edges...")
            enrichment_result = enricher.enrich_dynamic_call_graph(trace_data)
            
            # Step 4: Get edge statistics
            logger.info("[PHASE 7.6] Calculating edge statistics...")
            edge_stats = enricher.get_edge_statistics()
            
            # Step 5: Return combined result
            result = {
                "phase": "7.6",
                "status": "success",
                "summary": enrichment_result.get("summary", {}),
                "statistics": edge_stats,
                "phase_5_data": {
                    "unique_call_pairs": trace_data.get("summary", {}).get("total_unique_pairs", 0),
                    "unique_functions": trace_data.get("summary", {}).get("total_unique_functions", 0),
                    "total_invocations": trace_data.get("summary", {}).get("total_call_invocations", 0)
                }
            }
            
            logger.info(f"[PHASE 7.6] Dynamic call graph enrichment completed successfully")
            return result
            
        finally:
            enricher.close()
        
    except Exception as e:
        logger.error(f"[PHASE 7.6] Error during enrichment: {str(e)}", exc_info=True)
        return {
            "phase": "7.6",
            "status": "failed",
            "error": str(e)
        }


def enrich_dynamic_call_graph_from_trace(trace_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create DYNAMICALLY_CALLS edges directly from already-processed trace data.
    
    This is useful if you already have Phase 7.5 output and just want to create
    the edges without re-running the profiling and processing.
    
    Args:
        trace_data: Output from Phase 7.5 (call_trace_processor)
    
    Returns:
        Structured response with enrichment results
    """
    logger.info("[PHASE 7.6] Starting dynamic call graph enrichment from existing trace data")
    
    try:
        # Get Neo4j credentials from environment
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
        
        # Create enricher and process
        enricher = DynamicCallGraphEnricher(neo4j_uri, neo4j_user, neo4j_password)
        
        try:
            enrichment_result = enricher.enrich_dynamic_call_graph(trace_data)
            edge_stats = enricher.get_edge_statistics()
            
            result = {
                "phase": "7.6",
                "status": "success",
                "summary": enrichment_result.get("summary", {}),
                "statistics": edge_stats
            }
            
            logger.info("[PHASE 7.6] Enrichment from trace data completed successfully")
            return result
            
        finally:
            enricher.close()
        
    except Exception as e:
        logger.error(f"[PHASE 7.6] Error during enrichment: {str(e)}", exc_info=True)
        return {
            "phase": "7.6",
            "status": "failed",
            "error": str(e)
        }
