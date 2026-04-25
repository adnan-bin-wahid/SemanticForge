"""
Phase 7.7: Runtime Type Collection
Analyze and aggregate runtime type information from dynamic profiling.
"""

import logging
from typing import Dict, List, Set, Any, Optional, Tuple
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)


class RuntimeTypeCollector:
    """
    Collects and aggregates runtime type information from profiling traces.
    Analyzes function signatures based on observed argument types.
    """
    
    def __init__(self):
        """Initialize the runtime type collector."""
        # Map: function_name -> (argument_index) -> List[type_names]
        self.function_arg_types: Dict[str, Dict[int, List[str]]] = defaultdict(lambda: defaultdict(list))
        
        # Map: function_name -> Counter of observed type signatures
        self.function_signatures: Dict[str, Counter] = defaultdict(Counter)
        
        # Map: function_name -> observed types (set)
        self.function_types: Dict[str, Set[str]] = defaultdict(set)
        
        # Summary statistics
        self.total_call_events = 0
        self.functions_with_types = set()
        
        logger.info("[PHASE 7.7] RuntimeTypeCollector initialized")
    
    def collect_from_trace(self, trace_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect type information from trace data.
        
        Args:
            trace_data: Output from Phase 7.4 profiler containing events with arg_types
        
        Returns:
            Structured type analysis results
        """
        logger.info("[PHASE 7.7] Collecting runtime type information from trace")
        
        try:
            # Extract events from trace
            events = trace_data.get("events", [])
            logger.info(f"[PHASE 7.7] Processing {len(events)} trace events")
            
            # Process call events
            call_events = [e for e in events if isinstance(e, dict) and e.get("event") == "call"]
            logger.info(f"[PHASE 7.7] Found {len(call_events)} call events with type information")
            
            for event in call_events:
                self._process_call_event(event)
            
            # Generate analysis
            analysis = self._generate_type_analysis()
            
            logger.info(f"[PHASE 7.7] Type collection complete: {len(self.functions_with_types)} functions with types")
            return analysis
            
        except Exception as e:
            logger.error(f"[PHASE 7.7] Error collecting types: {str(e)}", exc_info=True)
            raise
    
    def _process_call_event(self, event: Dict[str, Any]) -> None:
        """
        Process a single call event to extract type information.
        
        Args:
            event: Call event from trace
        """
        func_name = event.get("func")
        arg_types = event.get("arg_types", [])
        
        if not func_name:
            return
        
        self.total_call_events += 1
        self.functions_with_types.add(func_name)
        
        # Record raw argument types
        for idx, arg_type in enumerate(arg_types):
            if arg_type:
                self.function_arg_types[func_name][idx].append(arg_type)
                self.function_types[func_name].add(arg_type)
        
        # Create type signature (tuple of observed types)
        if arg_types:
            signature = tuple(arg_types)
            self.function_signatures[func_name][signature] += 1
        
        logger.debug(f"[PHASE 7.7] Function {func_name}: types = {arg_types}")
    
    def _generate_type_analysis(self) -> Dict[str, Any]:
        """
        Generate structured type analysis from collected data.
        
        Returns:
            Dictionary with type analysis results
        """
        logger.info("[PHASE 7.7] Generating type analysis")
        
        # Aggregate types per function
        function_types_list = {}
        
        for func_name in self.functions_with_types:
            arg_types_by_index = self.function_arg_types.get(func_name, {})
            signatures = self.function_signatures.get(func_name, Counter())
            
            # Get most common type per argument position
            type_info = {}
            for idx, types_list in sorted(arg_types_by_index.items()):
                type_counter = Counter(types_list)
                most_common = type_counter.most_common(5)  # Top 5 types
                
                type_info[f"arg_{idx}"] = {
                    "observed_types": [
                        {"type": t, "count": c} 
                        for t, c in most_common
                    ],
                    "total_observations": len(types_list)
                }
            
            # Get most common signatures
            most_common_sigs = signatures.most_common(3)
            
            function_types_list[func_name] = {
                "argument_types": type_info,
                "observed_signatures": [
                    {
                        "signature": f"({', '.join(sig)})" if sig else "()",
                        "count": count
                    }
                    for sig, count in most_common_sigs
                ],
                "call_count": len(self.function_arg_types.get(func_name, {}).get(0, [])) 
                              if arg_types_by_index else 0
            }
        
        # Find most common types overall
        all_type_counts = Counter()
        for types_set in self.function_types.values():
            all_type_counts.update(types_set)
        
        most_common_types = all_type_counts.most_common(10)
        
        result = {
            "phase": "7.7",
            "title": "Runtime Type Collection",
            "status": "success",
            "summary": {
                "total_call_events_processed": self.total_call_events,
                "functions_with_types": len(self.functions_with_types),
                "unique_types_observed": len(all_type_counts),
                "total_type_observations": sum(all_type_counts.values())
            },
            "function_types": function_types_list,
            "most_common_types": [
                {"type": t, "count": c}
                for t, c in most_common_types
            ],
            "type_usage_statistics": self._calculate_type_statistics()
        }
        
        return result
    
    def _calculate_type_statistics(self) -> Dict[str, Any]:
        """
        Calculate statistics about type usage patterns.
        
        Returns:
            Dictionary with type statistics
        """
        # Count functions by number of distinct argument types
        type_diversity = defaultdict(int)
        for func_name, type_set in self.function_types.items():
            type_diversity[len(type_set)] += 1
        
        # Identify polymorphic functions (functions with many type combinations)
        polymorphic = []
        for func_name, sig_counter in self.function_signatures.items():
            if len(sig_counter) > 1:
                polymorphic.append({
                    "function": func_name,
                    "signature_variants": len(sig_counter),
                    "total_calls": sum(sig_counter.values())
                })
        
        # Sort by signature variants descending
        polymorphic.sort(key=lambda x: x["signature_variants"], reverse=True)
        
        return {
            "type_diversity": dict(type_diversity),
            "functions_with_polymorphic_types": len(polymorphic),
            "top_polymorphic_functions": polymorphic[:10],
            "functions_with_consistent_types": len(
                [f for f, sigs in self.function_signatures.items() if len(sigs) == 1]
            )
        }
    
    def get_function_types(self, func_name: str) -> Optional[Dict[str, Any]]:
        """
        Get type information for a specific function.
        
        Args:
            func_name: Name of the function
        
        Returns:
            Type information for the function, or None if not found
        """
        if func_name not in self.functions_with_types:
            return None
        
        arg_types_by_index = self.function_arg_types.get(func_name, {})
        signatures = self.function_signatures.get(func_name, Counter())
        
        type_info = {}
        for idx, types_list in sorted(arg_types_by_index.items()):
            type_counter = Counter(types_list)
            most_common = type_counter.most_common(5)
            
            type_info[f"arg_{idx}"] = {
                "observed_types": [
                    {"type": t, "count": c}
                    for t, c in most_common
                ],
                "total_observations": len(types_list)
            }
        
        return {
            "function": func_name,
            "argument_types": type_info,
            "observed_signatures": [
                {
                    "signature": f"({', '.join(sig)})" if sig else "()",
                    "count": count
                }
                for sig, count in signatures.most_common(3)
            ]
        }
