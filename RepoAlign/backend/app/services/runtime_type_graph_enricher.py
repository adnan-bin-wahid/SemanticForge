"""
Phase 7.8: Runtime Type Graph Enrichment
Add collected runtime type information as properties on Function nodes in Neo4j.
"""

import json
import logging
from typing import Dict, List, Set, Any, Optional
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


class RuntimeTypeGraphEnricher:
    """
    Enriches the Neo4j knowledge graph with runtime type properties
    on Function nodes based on Phase 7.7 type collection results.
    """
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        """
        Initialize the runtime type graph enricher.
        
        Args:
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
        """
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.functions_updated = 0
        self.functions_skipped = 0
        self.properties_added = 0
        self.polymorphic_functions_identified = 0
        
        logger.info("[PHASE 7.8] RuntimeTypeGraphEnricher initialized")
    
    def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()
    
    def enrich_function_types(self, type_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main orchestration method to enrich Function nodes with runtime type information.
        
        Args:
            type_data: Output from Phase 7.7 (runtime_type_collector) containing:
                - function_types: Dict mapping function names to their type information
                - summary: Statistics about collected types
                - type_statistics: Polymorphism analysis
        
        Returns:
            Summary of enrichment results
        """
        logger.info("[PHASE 7.8] Starting runtime type graph enrichment")
        
        try:
            # Extract function type information from Phase 7.7 output
            function_types = type_data.get("function_types", {})
            type_stats = type_data.get("type_statistics", {})
            
            logger.info(f"[PHASE 7.8] Processing {len(function_types)} functions with type information")
            
            # Get polymorphic function names for quick lookup
            polymorphic_functions = {}
            if "top_polymorphic_functions" in type_stats:
                for poly_func in type_stats["top_polymorphic_functions"]:
                    func_name = poly_func.get("function")
                    polymorphic_functions[func_name] = poly_func.get("signature_variants", 0)
            
            # Update each function with type properties
            self._update_function_types(function_types, polymorphic_functions)
            
            result = {
                "phase": "7.8",
                "title": "Runtime Type Graph Enrichment",
                "status": "success",
                "summary": {
                    "functions_processed": len(function_types),
                    "functions_updated": self.functions_updated,
                    "functions_skipped": self.functions_skipped,
                    "properties_added": self.properties_added,
                    "polymorphic_functions_identified": self.polymorphic_functions_identified
                },
                "type_statistics": type_stats
            }
            
            logger.info(f"[PHASE 7.8] Enrichment complete: {self.functions_updated} functions updated, "
                       f"{self.polymorphic_functions_identified} polymorphic functions identified")
            return result
            
        except Exception as e:
            logger.error(f"[PHASE 7.8] Error during type graph enrichment: {str(e)}", exc_info=True)
            raise
    
    def _update_function_types(self, function_types: Dict[str, Any], 
                               polymorphic_functions: Dict[str, int]) -> None:
        """
        Update Function nodes with type information.
        
        Args:
            function_types: Dict mapping function names to their type information
            polymorphic_functions: Dict mapping function names to signature variant counts
        """
        logger.info(f"[PHASE 7.8] Updating {len(function_types)} Function nodes with type properties")
        
        with self.driver.session() as session:
            for func_name, type_info in function_types.items():
                try:
                    # Extract type data
                    arg_types = type_info.get("argument_types", {})
                    observed_sigs = type_info.get("observed_signatures", [])
                    
                    # Build observed_types list from argument_types
                    observed_types = set()
                    for arg_info in arg_types.values():
                        if isinstance(arg_info, dict) and "observed_types" in arg_info:
                            for type_obj in arg_info["observed_types"]:
                                if isinstance(type_obj, dict):
                                    observed_types.add(type_obj.get("type"))
                    
                    # Extract signature strings
                    type_signatures = [sig.get("signature") for sig in observed_sigs if sig.get("signature")]
                    
                    # Check if polymorphic
                    is_polymorphic = func_name in polymorphic_functions
                    signature_variants = polymorphic_functions.get(func_name, 0)
                    
                    # Build the properties to set
                    properties = {
                        "observed_types": sorted(list(filter(None, observed_types))),
                        "type_signatures": type_signatures,
                        "is_polymorphic": is_polymorphic,
                        "signature_variants": signature_variants
                    }
                    
                    # Update the Function node
                    query = """
                    MATCH (f:Function {name: $func_name})
                    SET f.observed_types = $observed_types,
                        f.type_signatures = $type_signatures,
                        f.is_polymorphic = $is_polymorphic,
                        f.signature_variants = $signature_variants
                    RETURN f.name as name
                    """
                    
                    result = session.run(
                        query,
                        func_name=func_name,
                        observed_types=properties["observed_types"],
                        type_signatures=properties["type_signatures"],
                        is_polymorphic=properties["is_polymorphic"],
                        signature_variants=properties["signature_variants"]
                    )
                    
                    record = result.single()
                    if record:
                        self.functions_updated += 1
                        # Count properties added (excluding name which already exists)
                        self.properties_added += 4  # observed_types, type_signatures, is_polymorphic, signature_variants
                        
                        if is_polymorphic:
                            self.polymorphic_functions_identified += 1
                        
                        logger.debug(f"[PHASE 7.8] Updated {func_name}: {len(properties['observed_types'])} types, "
                                   f"{len(type_signatures)} signatures, polymorphic={is_polymorphic}")
                    else:
                        self.functions_skipped += 1
                        logger.warning(f"[PHASE 7.8] Function node '{func_name}' not found in graph")
                    
                except Exception as e:
                    self.functions_skipped += 1
                    logger.error(f"[PHASE 7.8] Error updating Function '{func_name}': {str(e)}")
        
        logger.info(f"[PHASE 7.8] Update complete: {self.functions_updated} updated, {self.functions_skipped} skipped")
    
    def get_enriched_functions(self) -> Dict[str, Any]:
        """
        Retrieve information about functions that have been enriched with type data.
        
        Returns:
            Dictionary with enriched function information
        """
        logger.info("[PHASE 7.8] Retrieving enriched function information")
        
        stats = {
            "functions_with_types": 0,
            "functions_with_polymorphic_types": 0,
            "all_observed_types": set(),
            "functions_by_polymorphism": {
                "polymorphic": [],
                "consistent": []
            }
        }
        
        try:
            with self.driver.session() as session:
                # Get all functions with type properties
                result = session.run("""
                    MATCH (f:Function)
                    WHERE f.observed_types IS NOT NULL
                    RETURN f.name as name, 
                           f.observed_types as types,
                           f.type_signatures as signatures,
                           f.is_polymorphic as is_polymorphic,
                           f.signature_variants as variants
                    ORDER BY f.name
                """)
                
                for record in result:
                    func_name = record.get("name")
                    types = record.get("types", [])
                    is_polymorphic = record.get("is_polymorphic", False)
                    
                    stats["functions_with_types"] += 1
                    
                    if is_polymorphic:
                        stats["functions_with_polymorphic_types"] += 1
                        stats["functions_by_polymorphism"]["polymorphic"].append({
                            "name": func_name,
                            "variants": record.get("variants", 0)
                        })
                    else:
                        stats["functions_by_polymorphism"]["consistent"].append(func_name)
                    
                    # Collect all observed types
                    if types:
                        stats["all_observed_types"].update(types)
                
                stats["all_observed_types"] = sorted(list(stats["all_observed_types"]))
                
        except Exception as e:
            logger.error(f"[PHASE 7.8] Error retrieving enriched functions: {str(e)}")
        
        return stats
