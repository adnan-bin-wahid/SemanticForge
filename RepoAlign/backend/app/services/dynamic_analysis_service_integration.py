"""
Phase 7.9 Integration Wrapper
High-level interface for running the complete dynamic analysis pipeline.
Orchestrates all dynamic analysis phases (7.4 through 7.8) in a single call.
"""

import logging
from typing import Dict, Any

from app.services.dynamic_analysis_service import DynamicAnalysisService

logger = logging.getLogger(__name__)


def run_dynamic_analysis(repo_path: str) -> Dict[str, Any]:
    """
    Execute the complete dynamic analysis pipeline.
    
    This is the main entry point for dynamic analysis enrichment.
    It orchestrates all phases:
    1. Phase 7.4: Dynamic profiling with sys.setprofile
    2. Phase 7.5: Call trace processing
    3. Phase 7.6: Create DYNAMICALLY_CALLS edges in Neo4j
    4. Phase 7.7: Runtime type collection and analysis
    5. Phase 7.8: Add type properties to Function nodes in Neo4j
    
    The result is a fully enriched knowledge graph with:
    - Dynamic function call relationships
    - Observed runtime type information
    - Polymorphism analysis
    - Type signatures for each function
    
    Args:
        repo_path: Path to the repository to analyze
    
    Returns:
        Comprehensive summary of all pipeline phases and their results
    """
    logger.info(f"[PHASE 7.9] Starting complete dynamic analysis pipeline for {repo_path}")
    
    try:
        # Create and run the service
        service = DynamicAnalysisService()
        result = service.run_full_analysis(repo_path)
        
        logger.info(f"[PHASE 7.9] Pipeline execution complete with status: {result.get('status')}")
        
        return result
        
    except Exception as e:
        logger.error(f"[PHASE 7.9] Error in dynamic analysis pipeline: {str(e)}", exc_info=True)
        return {
            "phase": "7.9",
            "status": "failed",
            "error": str(e)
        }
