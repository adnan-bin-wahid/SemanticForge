"""
Integration wrapper for dynamic profiler (Phase 7.4).
"""

import logging
from typing import Dict, Any
from app.services.dynamic_profiler import run_dynamic_profiling

logger = logging.getLogger(__name__)


def get_dynamic_profiling(repo_path: str) -> Dict[str, Any]:
    """
    Run dynamic profiling on a repository and return results.
    
    Args:
        repo_path: Path to the repository
        
    Returns:
        Profiling results containing call traces and call graph
    """
    logger.info(f"[PHASE 7.4] Starting dynamic profiling for {repo_path}")
    
    try:
        result = run_dynamic_profiling(repo_path)
        logger.info(f"[PHASE 7.4] Dynamic profiling completed successfully")
        return result
    except Exception as e:
        logger.error(f"[PHASE 7.4] Error during dynamic profiling: {str(e)}", exc_info=True)
        raise
