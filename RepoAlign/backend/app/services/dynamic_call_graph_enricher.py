"""
Phase 7.6: Dynamic Call Graph Edges
Create DYNAMICALLY_CALLS edges in Neo4j graph based on processed trace data.
Links Function nodes based on actual runtime function call relationships.
"""

import json
import logging
from typing import Dict, List, Set, Tuple, Any, Optional
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


class DynamicCallGraphEnricher:
    """
    Enriches the Neo4j knowledge graph with DYNAMICALLY_CALLS edges
    linking Functions based on actual runtime call relationships.
    """
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        """
        Initialize the dynamic call graph enricher.
        
        Args:
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
        """
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.edges_created = 0
        self.edges_updated = 0
        self.failed_edges = 0
        self.missing_nodes = []
        
        logger.info("[PHASE 7.6] DynamicCallGraphEnricher initialized")
    
    def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()
    
    def enrich_dynamic_call_graph(self, trace_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main orchestration method to enrich the graph with dynamic call edges.
        
        Args:
            trace_data: Output from Phase 7.5 (call_trace_processor) containing:
                - calls: List of {caller, callee, count} dicts
                - call_graph: Dict with call relationships
                - statistics: Aggregated statistics
        
        Returns:
            Summary of enrichment results
        """
        logger.info("[PHASE 7.6] Starting dynamic call graph enrichment")
        
        try:
            # Extract call pairs from trace data
            call_pairs = self._extract_call_pairs(trace_data)
            logger.info(f"[PHASE 7.6] Extracted {len(call_pairs)} unique call pairs")
            
            # Verify Function nodes exist in graph
            existing_functions = self._get_existing_functions()
            logger.info(f"[PHASE 7.6] Found {len(existing_functions)} Function nodes in graph")
            
            # Create DYNAMICALLY_CALLS edges
            edge_results = self._create_dynamic_edges(call_pairs, existing_functions)
            
            result = {
                "phase": "7.6",
                "title": "Dynamic Call Graph Enrichment",
                "status": "success",
                "summary": {
                    "unique_call_pairs": len(call_pairs),
                    "edges_created": self.edges_created,
                    "edges_updated": self.edges_updated,
                    "failed_edges": self.failed_edges,
                    "missing_nodes": len(self.missing_nodes),
                    "existing_function_nodes": len(existing_functions)
                },
                "missing_nodes_list": self.missing_nodes[:100],  # Return first 100
                "edge_creation_details": edge_results
            }
            
            logger.info(f"[PHASE 7.6] Enrichment complete: {self.edges_created} edges created, "
                       f"{self.edges_updated} updated, {self.failed_edges} failed")
            return result
            
        except Exception as e:
            logger.error(f"[PHASE 7.6] Error during graph enrichment: {str(e)}", exc_info=True)
            raise
    
    def _extract_call_pairs(self, trace_data: Dict[str, Any]) -> List[Tuple[str, str, int]]:
        """
        Extract unique (caller, callee, count) tuples from trace data.
        
        Args:
            trace_data: Output from Phase 7.5
        
        Returns:
            List of (caller, callee, count) tuples
        """
        logger.info("[PHASE 7.6] Extracting call pairs from trace data")
        
        call_pairs = []
        
        # Extract from 'calls' array (list of {caller, callee, count})
        if "calls" in trace_data and isinstance(trace_data["calls"], list):
            for call in trace_data["calls"]:
                caller = call.get("caller")
                callee = call.get("callee")
                count = call.get("count", 1)
                
                # Filter out internal markers
                if caller and callee and not self._is_internal_marker(caller) and not self._is_internal_marker(callee):
                    call_pairs.append((caller, callee, count))
        
        logger.info(f"[PHASE 7.6] Extracted {len(call_pairs)} valid call pairs")
        return call_pairs
    
    def _is_internal_marker(self, function_name: str) -> bool:
        """
        Check if function name is an internal Python marker that should be filtered.
        
        Args:
            function_name: Name to check
        
        Returns:
            True if function should be filtered out
        """
        internal_markers = {
            "<module>",
            "<genexpr>",
            "<setcomp>",
            "<dictcomp>",
            "<listcomp>",
            "<lambda>",
            "<comprehension>",
        }
        return function_name in internal_markers
    
    def _get_existing_functions(self) -> Set[str]:
        """
        Fetch all Function node names from Neo4j.
        
        Returns:
            Set of function names that exist in the graph
        """
        logger.info("[PHASE 7.6] Fetching existing Function nodes from graph")
        
        existing_functions = set()
        
        try:
            with self.driver.session() as session:
                result = session.run("MATCH (f:Function) RETURN f.name as name")
                for record in result:
                    function_name = record.get("name")
                    if function_name:
                        existing_functions.add(function_name)
        except Exception as e:
            logger.error(f"[PHASE 7.6] Error fetching Function nodes: {str(e)}")
            raise
        
        return existing_functions
    
    def _create_dynamic_edges(self, call_pairs: List[Tuple[str, str, int]], 
                             existing_functions: Set[str]) -> Dict[str, Any]:
        """
        Create DYNAMICALLY_CALLS edges in Neo4j for each call pair.
        
        Args:
            call_pairs: List of (caller, callee, count) tuples
            existing_functions: Set of function names that exist in graph
        
        Returns:
            Dictionary with edge creation statistics
        """
        logger.info(f"[PHASE 7.6] Creating DYNAMICALLY_CALLS edges for {len(call_pairs)} pairs")
        
        edge_results = {
            "total_pairs_processed": len(call_pairs),
            "created": [],
            "updated": [],
            "failed": []
        }
        
        with self.driver.session() as session:
            for caller, callee, count in call_pairs:
                try:
                    # Check if both nodes exist
                    if caller not in existing_functions:
                        self.failed_edges += 1
                        if caller not in self.missing_nodes:
                            self.missing_nodes.append(caller)
                        edge_results["failed"].append({
                            "caller": caller,
                            "callee": callee,
                            "reason": f"caller '{caller}' not found"
                        })
                        continue
                    
                    if callee not in existing_functions:
                        self.failed_edges += 1
                        if callee not in self.missing_nodes:
                            self.missing_nodes.append(callee)
                        edge_results["failed"].append({
                            "caller": caller,
                            "callee": callee,
                            "reason": f"callee '{callee}' not found"
                        })
                        continue
                    
                    # Create or update DYNAMICALLY_CALLS edge
                    # Using coalesce to handle null count on first MATCH
                    query = """
                    MATCH (caller:Function {name: $caller})
                    MATCH (callee:Function {name: $callee})
                    MERGE (caller)-[edge:DYNAMICALLY_CALLS]->(callee)
                    SET edge.count = coalesce(edge.count, 0) + $count
                    RETURN caller.name as caller_name, callee.name as callee_name, edge.count as total_count
                    """
                    
                    result = session.run(
                        query,
                        caller=caller,
                        callee=callee,
                        count=count
                    )
                    
                    record = result.single()
                    if record:
                        total_count = record.get("total_count", count)
                        # Check if this was a fresh creation by seeing if total_count == count
                        # (if it's an update, it would be > count)
                        if total_count == count:
                            self.edges_created += 1
                            edge_results["created"].append({
                                "caller": caller,
                                "callee": callee,
                                "count": count
                            })
                        else:
                            self.edges_updated += 1
                            edge_results["updated"].append({
                                "caller": caller,
                                "callee": callee,
                                "count": total_count
                            })
                        
                        logger.debug(f"[PHASE 7.6] Edge {caller} -> {callee}: count = {total_count}")
                    
                except Exception as e:
                    self.failed_edges += 1
                    logger.error(f"[PHASE 7.6] Error creating edge {caller} -> {callee}: {str(e)}")
                    edge_results["failed"].append({
                        "caller": caller,
                        "callee": callee,
                        "reason": str(e)
                    })
        
        logger.info(f"[PHASE 7.6] Edge creation complete: {self.edges_created} created, "
                   f"{self.edges_updated} updated, {self.failed_edges} failed")
        
        return edge_results
    
    def get_edge_statistics(self) -> Dict[str, Any]:
        """
        Retrieve statistics about DYNAMICALLY_CALLS edges from the graph.
        
        Returns:
            Dictionary with edge statistics
        """
        logger.info("[PHASE 7.6] Calculating edge statistics")
        
        stats = {
            "total_dynamically_calls_edges": 0,
            "total_call_count": 0,
            "top_called_functions": [],
            "top_calling_functions": [],
            "functions_with_dynamic_calls": 0
        }
        
        try:
            with self.driver.session() as session:
                # Count total edges and call count
                result = session.run("""
                    MATCH (f1:Function)-[edge:DYNAMICALLY_CALLS]->(f2:Function)
                    RETURN count(edge) as edge_count, coalesce(sum(edge.count), 0) as total_count
                """)
                
                record = result.single()
                if record:
                    stats["total_dynamically_calls_edges"] = record.get("edge_count", 0)
                    stats["total_call_count"] = record.get("total_count", 0)
                
                # Top called functions
                result = session.run("""
                    MATCH (f1:Function)-[edge:DYNAMICALLY_CALLS]->(f2:Function)
                    RETURN f2.name as function, coalesce(sum(edge.count), 0) as total_calls
                    ORDER BY total_calls DESC
                    LIMIT 10
                """)
                
                stats["top_called_functions"] = [
                    {"function": record.get("function"), "total_calls": record.get("total_calls")}
                    for record in result
                ]
                
                # Top calling functions
                result = session.run("""
                    MATCH (f1:Function)-[edge:DYNAMICALLY_CALLS]->(f2:Function)
                    RETURN f1.name as function, count(edge) as num_callees
                    ORDER BY num_callees DESC
                    LIMIT 10
                """)
                
                stats["top_calling_functions"] = [
                    {"function": record.get("function"), "num_callees": record.get("num_callees")}
                    for record in result
                ]
                
                # Functions with at least one dynamic call
                result = session.run("""
                    MATCH (f:Function) WHERE (f)-[:DYNAMICALLY_CALLS]->()
                    RETURN count(f) as count
                """)
                
                record = result.single()
                if record:
                    stats["functions_with_dynamic_calls"] = record.get("count", 0)
        
        except Exception as e:
            logger.error(f"[PHASE 7.6] Error calculating statistics: {str(e)}")
        
        return stats
