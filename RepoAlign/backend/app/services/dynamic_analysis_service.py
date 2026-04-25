"""
Phase 7.9: Dynamic Analysis Service
Orchestrates the entire dynamic analysis pipeline: runs profiling, processes traces,
creates edges, collects types, and enriches the knowledge graph.
"""

import logging
from typing import Dict, Any, List, Optional
import time
from datetime import datetime

logger = logging.getLogger(__name__)


class DynamicAnalysisService:
    """
    Orchestrates the complete dynamic analysis pipeline.
    Coordinates Phases 7.4 through 7.8 to provide comprehensive runtime enrichment.
    """
    
    def __init__(self):
        """Initialize the dynamic analysis service."""
        self.start_time = None
        self.phase_results = {}
        self.phase_timings = {}
        
        logger.info("[PHASE 7.9] DynamicAnalysisService initialized")
    
    def run_full_analysis(self, repo_path: str) -> Dict[str, Any]:
        """
        Execute the complete dynamic analysis pipeline.
        
        Orchestrates:
        1. Phase 7.4: Dynamic profiling with sys.setprofile
        2. Phase 7.5: Call trace processing
        3. Phase 7.6: Dynamic call graph edges (DYNAMICALLY_CALLS)
        4. Phase 7.7: Runtime type collection
        5. Phase 7.8: Runtime type graph enrichment
        
        Args:
            repo_path: Path to the repository to analyze
        
        Returns:
            Comprehensive summary of all phases and their results
        """
        logger.info(f"[PHASE 7.9] Starting complete dynamic analysis pipeline for {repo_path}")
        
        self.start_time = time.time()
        self.phase_results = {}
        self.phase_timings = {}
        
        try:
            # Import services here to avoid circular imports
            from app.services.dynamic_profiler_integration import get_dynamic_profiling
            from app.services.call_trace_processor_integration import get_processed_trace
            from app.services.dynamic_call_graph_enricher_integration import enrich_dynamic_call_graph
            from app.services.runtime_type_collector_integration import collect_runtime_types
            from app.services.runtime_type_graph_enricher_integration import enrich_function_types
            
            # Phase 7.4: Dynamic Profiling
            logger.info("[PHASE 7.9] Executing Phase 7.4: Dynamic Profiling")
            phase_7_4_start = time.time()
            result_7_4 = self._safe_execute_phase(
                "7.4",
                get_dynamic_profiling,
                repo_path
            )
            phase_7_4_time = time.time() - phase_7_4_start
            self.phase_timings["7.4"] = phase_7_4_time
            self.phase_results["7.4"] = result_7_4
            
            if not self._is_success(result_7_4):
                return self._build_failure_response(result_7_4)
            
            # Phase 7.5: Call Trace Processing
            logger.info("[PHASE 7.9] Executing Phase 7.5: Call Trace Processing")
            phase_7_5_start = time.time()
            result_7_5 = self._safe_execute_phase(
                "7.5",
                get_processed_trace,
                repo_path
            )
            phase_7_5_time = time.time() - phase_7_5_start
            self.phase_timings["7.5"] = phase_7_5_time
            self.phase_results["7.5"] = result_7_5
            
            if not self._is_success(result_7_5):
                return self._build_failure_response(result_7_5)
            
            # Phase 7.6: Dynamic Call Graph Edges
            logger.info("[PHASE 7.9] Executing Phase 7.6: Dynamic Call Graph Enrichment")
            phase_7_6_start = time.time()
            result_7_6 = self._safe_execute_phase(
                "7.6",
                enrich_dynamic_call_graph,
                repo_path
            )
            phase_7_6_time = time.time() - phase_7_6_start
            self.phase_timings["7.6"] = phase_7_6_time
            self.phase_results["7.6"] = result_7_6
            
            if not self._is_success(result_7_6):
                return self._build_failure_response(result_7_6)
            
            # Phase 7.7: Runtime Type Collection
            logger.info("[PHASE 7.9] Executing Phase 7.7: Runtime Type Collection")
            phase_7_7_start = time.time()
            result_7_7 = self._safe_execute_phase(
                "7.7",
                collect_runtime_types,
                repo_path
            )
            phase_7_7_time = time.time() - phase_7_7_start
            self.phase_timings["7.7"] = phase_7_7_time
            self.phase_results["7.7"] = result_7_7
            
            if not self._is_success(result_7_7):
                return self._build_failure_response(result_7_7)
            
            # Phase 7.8: Runtime Type Graph Enrichment
            logger.info("[PHASE 7.9] Executing Phase 7.8: Runtime Type Graph Enrichment")
            phase_7_8_start = time.time()
            result_7_8 = self._safe_execute_phase(
                "7.8",
                enrich_function_types,
                repo_path
            )
            phase_7_8_time = time.time() - phase_7_8_start
            self.phase_timings["7.8"] = phase_7_8_time
            self.phase_results["7.8"] = result_7_8
            
            if not self._is_success(result_7_8):
                return self._build_failure_response(result_7_8)
            
            # All phases completed successfully
            total_time = time.time() - self.start_time
            
            logger.info(f"[PHASE 7.9] ✓ Complete dynamic analysis pipeline finished in {total_time:.2f}s")
            
            return self._build_success_response(total_time)
            
        except Exception as e:
            logger.error(f"[PHASE 7.9] Fatal error in dynamic analysis pipeline: {str(e)}", exc_info=True)
            return {
                "phase": "7.9",
                "status": "failed",
                "error": str(e),
                "phase_results": self.phase_results,
                "phase_timings": self.phase_timings
            }
    
    def _safe_execute_phase(self, phase_name: str, phase_func, repo_path: str) -> Dict[str, Any]:
        """
        Safely execute a phase function with error handling.
        
        Args:
            phase_name: Name of the phase (e.g., "7.4")
            phase_func: Function to execute
            repo_path: Repository path to pass to the function
        
        Returns:
            Result from the phase function or error dict
        """
        try:
            logger.debug(f"[PHASE 7.9] Calling phase {phase_name} function")
            result = phase_func(repo_path)
            
            if self._is_success(result):
                logger.info(f"[PHASE 7.9] Phase {phase_name} completed successfully")
            else:
                logger.warning(f"[PHASE 7.9] Phase {phase_name} returned error: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"[PHASE 7.9] Exception executing phase {phase_name}: {str(e)}", exc_info=True)
            return {
                "phase": phase_name,
                "status": "failed",
                "error": str(e)
            }
    
    def _is_success(self, result: Dict[str, Any]) -> bool:
        """
        Check if a phase result indicates success.
        
        Args:
            result: Result dictionary from a phase
        
        Returns:
            True if status is "success", False otherwise
        """
        return isinstance(result, dict) and result.get("status") == "success"
    
    def _build_success_response(self, total_time: float) -> Dict[str, Any]:
        """
        Build a comprehensive success response from all phase results.
        
        Args:
            total_time: Total execution time in seconds
        
        Returns:
            Aggregated response with all phase data
        """
        # Extract key statistics from each phase
        response = {
            "phase": "7.9",
            "title": "Dynamic Analysis Service",
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "total_execution_time_seconds": round(total_time, 2),
            "execution_summary": {
                "phase_7_4_dynamic_profiling": {
                    "title": self.phase_results.get("7.4", {}).get("title", "Dynamic Profiling"),
                    "status": self.phase_results.get("7.4", {}).get("status"),
                    "execution_time_seconds": round(self.phase_timings.get("7.4", 0), 2)
                },
                "phase_7_5_call_trace_processing": {
                    "title": self.phase_results.get("7.5", {}).get("title", "Call Trace Processing"),
                    "status": self.phase_results.get("7.5", {}).get("status"),
                    "execution_time_seconds": round(self.phase_timings.get("7.5", 0), 2)
                },
                "phase_7_6_dynamic_call_graph_edges": {
                    "title": self.phase_results.get("7.6", {}).get("title", "Dynamic Call Graph Edges"),
                    "status": self.phase_results.get("7.6", {}).get("status"),
                    "execution_time_seconds": round(self.phase_timings.get("7.6", 0), 2)
                },
                "phase_7_7_runtime_type_collection": {
                    "title": self.phase_results.get("7.7", {}).get("title", "Runtime Type Collection"),
                    "status": self.phase_results.get("7.7", {}).get("status"),
                    "execution_time_seconds": round(self.phase_timings.get("7.7", 0), 2)
                },
                "phase_7_8_runtime_type_graph_enrichment": {
                    "title": self.phase_results.get("7.8", {}).get("title", "Runtime Type Graph Enrichment"),
                    "status": self.phase_results.get("7.8", {}).get("status"),
                    "execution_time_seconds": round(self.phase_timings.get("7.8", 0), 2)
                }
            },
            "detailed_results": {
                "phase_7_4": self._extract_summary(self.phase_results.get("7.4", {})),
                "phase_7_5": self._extract_summary(self.phase_results.get("7.5", {})),
                "phase_7_6": self._extract_summary(self.phase_results.get("7.6", {})),
                "phase_7_7": self._extract_summary(self.phase_results.get("7.7", {})),
                "phase_7_8": self._extract_summary(self.phase_results.get("7.8", {}))
            },
            "pipeline_metrics": self._calculate_pipeline_metrics()
        }
        
        return response
    
    def _build_failure_response(self, failed_phase_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build a failure response when a phase fails.
        
        Args:
            failed_phase_result: Result from the failed phase
        
        Returns:
            Failure response with phase results up to failure
        """
        failed_phase = failed_phase_result.get("phase", "unknown")
        
        response = {
            "phase": "7.9",
            "status": "failed",
            "failed_at_phase": failed_phase,
            "error": f"Pipeline failed at Phase {failed_phase}",
            "failure_details": failed_phase_result.get("error", "Unknown error"),
            "completed_phases": [p for p in self.phase_results.keys()],
            "phase_results": self.phase_results,
            "phase_timings": {k: round(v, 2) for k, v in self.phase_timings.items()}
        }
        
        logger.error(f"[PHASE 7.9] Pipeline failed at Phase {failed_phase}")
        
        return response
    
    def _extract_summary(self, phase_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract key summary information from a phase result.
        
        Args:
            phase_result: Result dictionary from a phase
        
        Returns:
            Extracted summary information
        """
        if not phase_result:
            return {}
        
        summary = {
            "status": phase_result.get("status"),
            "summary": phase_result.get("summary", {})
        }
        
        # Include phase-specific statistics if available
        if "type_statistics" in phase_result:
            summary["type_statistics"] = phase_result["type_statistics"]
        
        if "statistics" in phase_result:
            summary["call_graph_statistics"] = phase_result["statistics"]
        
        if "enriched_functions_statistics" in phase_result:
            summary["enriched_functions_statistics"] = phase_result["enriched_functions_statistics"]
        
        return summary
    
    def _calculate_pipeline_metrics(self) -> Dict[str, Any]:
        """
        Calculate aggregate metrics across the entire pipeline.
        
        Returns:
            Dictionary with pipeline-wide metrics
        """
        metrics = {
            "total_phases": 5,
            "successful_phases": sum(1 for r in self.phase_results.values() if self._is_success(r)),
            "failed_phases": sum(1 for r in self.phase_results.values() if not self._is_success(r))
        }
        
        # Extract key numbers from results
        if self._is_success(self.phase_results.get("7.4", {})):
            metrics["total_call_events_captured"] = (
                self.phase_results["7.4"].get("summary", {}).get("total_events", 0)
            )
        
        if self._is_success(self.phase_results.get("7.5", {})):
            metrics["unique_call_pairs"] = (
                self.phase_results["7.5"].get("summary", {}).get("unique_pairs", 0)
            )
        
        if self._is_success(self.phase_results.get("7.6", {})):
            metrics["dynamically_calls_edges_created"] = (
                self.phase_results["7.6"].get("summary", {}).get("edges_created", 0)
            )
        
        if self._is_success(self.phase_results.get("7.7", {})):
            metrics["functions_with_runtime_types"] = (
                self.phase_results["7.7"].get("summary", {}).get("functions_with_types", 0)
            )
            metrics["unique_types_observed"] = (
                self.phase_results["7.7"].get("summary", {}).get("unique_types_observed", 0)
            )
        
        if self._is_success(self.phase_results.get("7.8", {})):
            metrics["function_nodes_updated_with_types"] = (
                self.phase_results["7.8"].get("summary", {}).get("functions_updated", 0)
            )
            metrics["polymorphic_functions_identified"] = (
                self.phase_results["7.8"].get("summary", {}).get("polymorphic_functions_identified", 0)
            )
        
        return metrics
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """
        Get the current status of the pipeline.
        
        Returns:
            Dictionary with pipeline status and phase results
        """
        return {
            "phase_results": self.phase_results,
            "phase_timings": {k: round(v, 2) for k, v in self.phase_timings.items()},
            "total_execution_time_seconds": (
                round(time.time() - self.start_time, 2) if self.start_time else 0
            )
        }
