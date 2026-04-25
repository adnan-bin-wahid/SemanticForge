"""
Phase 7.5: Dynamic Call Trace Processing
Parse and aggregate raw trace data into structured function call lists.
"""

import logging
from typing import Dict, List, Set, Tuple, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class FunctionCall:
    """Represents a single function-to-function call."""
    caller: str
    callee: str
    count: int = 1
    call_pairs: List[Tuple[str, str]] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "caller": self.caller,
            "callee": self.callee,
            "count": self.count
        }


@dataclass
class CallGraphNode:
    """Represents a function node in the call graph."""
    name: str
    outgoing_calls: Set[str] = field(default_factory=set)  # Functions this calls
    incoming_calls: Set[str] = field(default_factory=set)  # Functions that call this
    call_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))  # count per callee
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "calls_to": sorted(list(self.outgoing_calls)),
            "called_by": sorted(list(self.incoming_calls)),
            "call_frequency": dict(self.call_counts)
        }


class CallTraceProcessor:
    """
    Processes raw trace data into structured call information.
    """
    
    def __init__(self):
        """Initialize the trace processor."""
        self.call_graph: Dict[str, CallGraphNode] = {}
        self.call_pairs: Set[Tuple[str, str]] = set()
        self.call_counts: Dict[str, int] = defaultdict(int)
        self.unique_functions: Set[str] = set()
        
        logger.info("[PHASE 7.5] CallTraceProcessor initialized")
    
    def process_trace(self, trace_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process raw trace data from the profiler.
        
        Args:
            trace_data: Raw trace data from Phase 7.4 profiler
            
        Returns:
            Processed call graph and call list
        """
        logger.info("[PHASE 7.5] Processing raw trace data")
        
        # Extract call pairs from raw trace
        self._extract_call_pairs(trace_data)
        
        # Build call graph
        self._build_call_graph()
        
        # Generate structured output
        return self._generate_output()
    
    def _extract_call_pairs(self, trace_data: Dict[str, Any]) -> None:
        """
        Extract call pairs from raw trace events.
        
        Args:
            trace_data: Raw trace data from profiler
        """
        logger.info("[PHASE 7.5] Extracting call pairs from events")
        
        call_counts = trace_data.get('call_counts', {})
        
        # Process call_counts dict (pairs are already processed by profiler)
        for pair_str, count in call_counts.items():
            if '->' in pair_str:
                parts = pair_str.split('->')
                if len(parts) == 2:
                    caller = parts[0].strip()
                    callee = parts[1].strip()
                    
                    # Skip internal markers like '<module>', '<genexpr>'
                    if caller and callee and not caller.startswith('<') and not callee.startswith('<'):
                        self.call_pairs.add((caller, callee))
                        self.call_counts[pair_str] = count
                        self.unique_functions.add(caller)
                        self.unique_functions.add(callee)
        
        logger.info(f"[PHASE 7.5] Extracted {len(self.call_pairs)} unique call pairs")
        logger.info(f"[PHASE 7.5] Found {len(self.unique_functions)} unique functions")
    
    def _build_call_graph(self) -> None:
        """
        Build a call graph from extracted pairs.
        """
        logger.info("[PHASE 7.5] Building call graph")
        
        # Create nodes for all functions
        for func in self.unique_functions:
            if func not in self.call_graph:
                self.call_graph[func] = CallGraphNode(name=func)
        
        # Add edges
        for caller, callee in self.call_pairs:
            if caller in self.call_graph and callee in self.call_graph:
                self.call_graph[caller].outgoing_calls.add(callee)
                self.call_graph[callee].incoming_calls.add(caller)
                
                # Track call frequency
                pair_key = f"{caller}->{callee}"
                count = self.call_counts.get(pair_key, 1)
                self.call_graph[caller].call_counts[callee] = count
        
        logger.info(f"[PHASE 7.5] Built call graph with {len(self.call_graph)} nodes")
    
    def _generate_output(self) -> Dict[str, Any]:
        """
        Generate structured output from processed data.
        
        Returns:
            Processed call trace data
        """
        logger.info("[PHASE 7.5] Generating structured output")
        
        # Sort by frequency
        sorted_pairs = sorted(
            self.call_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Convert to structured format
        calls_list = []
        for pair_str, count in sorted_pairs:
            if '->' in pair_str:
                caller, callee = pair_str.split('->')
                calls_list.append({
                    "caller": caller.strip(),
                    "callee": callee.strip(),
                    "count": count
                })
        
        # Calculate statistics
        most_called = self._get_most_called_functions()
        most_called_by = self._get_functions_most_called()
        
        return {
            "phase": "7.5",
            "title": "Dynamic Call Trace Processing",
            "status": "success",
            "summary": {
                "total_unique_pairs": len(self.call_pairs),
                "total_unique_functions": len(self.unique_functions),
                "total_call_invocations": sum(self.call_counts.values()),
                "call_graph_nodes": len(self.call_graph),
                "call_graph_edges": len(self.call_pairs)
            },
            "calls": calls_list,
            "call_graph": {
                name: node.to_dict()
                for name, node in self.call_graph.items()
            },
            "statistics": {
                "most_called_functions": most_called,
                "functions_with_most_callers": most_called_by,
                "average_callees_per_function": round(
                    sum(len(node.outgoing_calls) for node in self.call_graph.values()) 
                    / max(len(self.call_graph), 1), 
                    2
                ),
                "average_callers_per_function": round(
                    sum(len(node.incoming_calls) for node in self.call_graph.values()) 
                    / max(len(self.call_graph), 1), 
                    2
                )
            }
        }
    
    def _get_most_called_functions(self) -> List[Dict[str, Any]]:
        """
        Get functions that are called the most.
        
        Returns:
            List of (function_name, call_count) tuples
        """
        func_call_counts = defaultdict(int)
        
        for pair_str, count in self.call_counts.items():
            if '->' in pair_str:
                _, callee = pair_str.split('->')
                callee = callee.strip()
                func_call_counts[callee] += count
        
        sorted_funcs = sorted(
            func_call_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return [
            {"function": func, "total_calls": count}
            for func, count in sorted_funcs
        ]
    
    def _get_functions_most_called(self) -> List[Dict[str, Any]]:
        """
        Get functions that have the most callers.
        
        Returns:
            List of (function_name, caller_count) tuples
        """
        func_caller_counts = {}
        
        for func, node in self.call_graph.items():
            func_caller_counts[func] = len(node.incoming_calls)
        
        sorted_funcs = sorted(
            func_caller_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return [
            {"function": func, "num_callers": count}
            for func, count in sorted_funcs
        ]


def process_dynamic_trace(trace_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process raw trace data into structured call information.
    
    Args:
        trace_data: Raw trace data from Phase 7.4
        
    Returns:
        Processed call trace data
    """
    processor = CallTraceProcessor()
    return processor.process_trace(trace_data)
