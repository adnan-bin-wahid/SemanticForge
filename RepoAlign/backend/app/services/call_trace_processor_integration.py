"""
Integration wrapper for call trace processor (Phase 7.5).
"""

import logging
from typing import Dict, Any
from app.services.dynamic_profiler_integration import get_dynamic_profiling
from app.services.call_trace_processor import process_dynamic_trace

logger = logging.getLogger(__name__)


def get_processed_trace(repo_path: str) -> Dict[str, Any]:
    """
    Run dynamic profiling and process the trace data.
    
    Args:
        repo_path: Path to the repository
        
    Returns:
        Processed trace data with call graph and call list
    """
    logger.info(f"[PHASE 7.5] Starting trace processing for {repo_path}")
    
    try:
        # First, run dynamic profiling from Phase 7.4
        logger.info("[PHASE 7.5] Running dynamic profiling...")
        trace_data = get_dynamic_profiling(repo_path)
        
        # Then process the trace
        logger.info("[PHASE 7.5] Processing trace data...")
        result = process_dynamic_trace(trace_data)
        
        logger.info(f"[PHASE 7.5] Trace processing completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"[PHASE 7.5] Error during trace processing: {str(e)}", exc_info=True)
        raise


def process_trace_only(trace_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process already-captured trace data without re-running profiling.
    Useful for reprocessing existing trace data.
    
    Args:
        trace_data: Pre-captured trace data from Phase 7.4
        
    Returns:
        Processed trace data
    """
    logger.info("[PHASE 7.5] Processing existing trace data")
    
    try:
        result = process_dynamic_trace(trace_data)
        logger.info("[PHASE 7.5] Trace processing completed")
        return result
    except Exception as e:
        logger.error(f"[PHASE 7.5] Error during trace processing: {str(e)}", exc_info=True)
        raise
