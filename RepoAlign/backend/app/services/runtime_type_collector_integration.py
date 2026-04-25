"""
Phase 7.7 Integration Wrapper
High-level interface for runtime type collection.
Orchestrates Phase 7.4 profiling followed by Phase 7.7 type analysis.
"""

import logging
import os
from typing import Dict, Any

from app.services.dynamic_profiler_integration import get_dynamic_profiling
from app.services.runtime_type_collector import RuntimeTypeCollector

logger = logging.getLogger(__name__)


def collect_runtime_types(repo_path: str) -> Dict[str, Any]:
    """
    Run Phase 7.4 and Phase 7.7 to collect and analyze runtime type information.
    
    This is the main entry point for runtime type collection.
    It orchestrates:
    1. Phase 7.4: Dynamic profiling with type capture
    2. Phase 7.7: Type analysis and aggregation
    
    Args:
        repo_path: Path to the repository to analyze
    
    Returns:
        Structured response with phase information and type analysis results
    """
    logger.info(f"[PHASE 7.7] Starting runtime type collection for {repo_path}")
    
    try:
        # Step 1: Run Phase 7.4 to get profiling data with type information
        logger.info("[PHASE 7.7] Running Phase 7.4 profiling...")
        profile_response = get_dynamic_profiling(repo_path)
        
        if profile_response.get("status") != "success":
            logger.error(f"[PHASE 7.7] Phase 7.4 failed: {profile_response}")
            return {
                "phase": "7.7",
                "status": "failed",
                "error": f"Phase 7.4 profiling failed"
            }
        
        # Extract trace data
        trace_data = profile_response.get("trace", {})
        logger.info(f"[PHASE 7.7] Phase 7.4 completed with trace data")
        
        # Step 2: Collect runtime types from trace
        logger.info("[PHASE 7.7] Analyzing runtime types...")
        collector = RuntimeTypeCollector()
        type_analysis = collector.collect_from_trace(trace_data)
        
        # Step 3: Combine results with profiling info
        result = {
            "phase": "7.7",
            "status": "success",
            "summary": type_analysis.get("summary", {}),
            "function_types": type_analysis.get("function_types", {}),
            "most_common_types": type_analysis.get("most_common_types", []),
            "type_statistics": type_analysis.get("type_usage_statistics", {}),
            "phase_4_data": {
                "total_events": profile_response.get("summary", {}).get("total_events", 0),
                "call_events": profile_response.get("summary", {}).get("call_events", 0),
                "return_events": profile_response.get("summary", {}).get("return_events", 0),
                "unique_call_pairs": profile_response.get("summary", {}).get("unique_call_pairs", 0),
                "max_call_depth": profile_response.get("summary", {}).get("max_call_depth", 0)
            }
        }
        
        logger.info("[PHASE 7.7] Runtime type collection completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"[PHASE 7.7] Error during type collection: {str(e)}", exc_info=True)
        return {
            "phase": "7.7",
            "status": "failed",
            "error": str(e)
        }


def collect_runtime_types_from_trace(trace_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze runtime types directly from already-captured trace data.
    
    This is useful if you already have Phase 7.4 output and just want to analyze
    the type information without re-running profiling.
    
    Args:
        trace_data: Output from Phase 7.4 (dynamic profiler)
    
    Returns:
        Structured response with type analysis results
    """
    logger.info("[PHASE 7.7] Starting runtime type analysis from existing trace data")
    
    try:
        collector = RuntimeTypeCollector()
        type_analysis = collector.collect_from_trace(trace_data)
        
        result = {
            "phase": "7.7",
            "status": "success",
            "summary": type_analysis.get("summary", {}),
            "function_types": type_analysis.get("function_types", {}),
            "most_common_types": type_analysis.get("most_common_types", []),
            "type_statistics": type_analysis.get("type_usage_statistics", {})
        }
        
        logger.info("[PHASE 7.7] Type analysis completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"[PHASE 7.7] Error during type analysis: {str(e)}", exc_info=True)
        return {
            "phase": "7.7",
            "status": "failed",
            "error": str(e)
        }
