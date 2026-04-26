"""
Phase 8.5: Graph Invalidation Integration Layer

High-level functions for invalidating symbols in the Neo4j graph.
Bridges the gap between AST diffing results and graph operations.
"""

import logging
from typing import List, Dict, Any, Optional

from app.services.graph_invalidator import GraphInvalidator, InvalidationScope
from app.db.neo4j_driver import get_neo4j_session

logger = logging.getLogger(__name__)

# Global invalidator instance
_invalidator: Optional[GraphInvalidator] = None
_invalidator_lock = __import__('threading').Lock()


def get_invalidator() -> GraphInvalidator:
    """Get or create singleton GraphInvalidator"""
    global _invalidator
    
    if _invalidator is None:
        with _invalidator_lock:
            if _invalidator is None:
                session = get_neo4j_session()
                _invalidator = GraphInvalidator(session)
                logger.info("[PHASE 8.5] GraphInvalidator singleton created")
    
    return _invalidator


def invalidate_removed_symbol(
    file_path: str,
    symbol_name: str,
    symbol_type: str
) -> Dict[str, Any]:
    """
    Invalidate (delete) a removed symbol from the graph.
    
    Args:
        file_path: Path to the file
        symbol_name: Name of the symbol
        symbol_type: Type (function or class)
        
    Returns:
        {
            "status": "success" | "error",
            "symbol_name": str,
            "nodes_deleted": int,
            "relationships_deleted": int,
            "message": str
        }
    """
    try:
        invalidator = get_invalidator()
        report = invalidator.invalidate_removed_symbol(
            file_path=file_path,
            symbol_name=symbol_name,
            symbol_type=symbol_type
        )
        
        if report.error:
            return {
                "status": "error",
                "error": report.error,
                "symbol_name": symbol_name
            }
        
        return {
            "status": "success",
            "symbol_name": symbol_name,
            "nodes_deleted": report.nodes_deleted,
            "relationships_deleted": report.relationships_deleted,
            "message": f"Deleted {symbol_type} '{symbol_name}' and {report.relationships_deleted} relationships"
        }
        
    except Exception as e:
        logger.error(f"[PHASE 8.5] Error invalidating removed symbol: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "symbol_name": symbol_name
        }


def invalidate_modified_symbol(
    file_path: str,
    symbol_name: str,
    symbol_type: str,
    new_signature: str,
    new_docstring: Optional[str] = None
) -> Dict[str, Any]:
    """
    Invalidate (update) a modified symbol in the graph.
    
    Args:
        file_path: Path to the file
        symbol_name: Name of the symbol
        symbol_type: Type (function or class)
        new_signature: Updated signature
        new_docstring: Updated docstring (optional)
        
    Returns:
        {
            "status": "success" | "error",
            "symbol_name": str,
            "new_signature": str,
            "message": str
        }
    """
    try:
        invalidator = get_invalidator()
        report = invalidator.invalidate_modified_symbol(
            file_path=file_path,
            symbol_name=symbol_name,
            symbol_type=symbol_type,
            new_signature=new_signature,
            new_docstring=new_docstring
        )
        
        if report.error:
            return {
                "status": "error",
                "error": report.error,
                "symbol_name": symbol_name
            }
        
        return {
            "status": "success",
            "symbol_name": symbol_name,
            "symbol_type": symbol_type,
            "new_signature": new_signature,
            "message": f"Updated {symbol_type} '{symbol_name}' with new signature"
        }
        
    except Exception as e:
        logger.error(f"[PHASE 8.5] Error invalidating modified symbol: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "symbol_name": symbol_name
        }


def invalidate_file_changes(
    file_path: str,
    removed_symbols: List[Dict[str, str]],
    modified_symbols: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Invalidate all removed and modified symbols in a file.
    
    Args:
        file_path: Path to the file
        removed_symbols: List of {symbol_name, symbol_type}
        modified_symbols: List of {symbol_name, symbol_type, new_signature, new_docstring}
        
    Returns:
        {
            "status": "success" | "error",
            "file_path": str,
            "removed_count": int,
            "modified_count": int,
            "total_nodes_deleted": int,
            "total_relationships_deleted": int,
            "error_count": int,
            "reports": [...]
        }
    """
    try:
        invalidator = get_invalidator()
        result = invalidator.invalidate_file_symbols(
            file_path=file_path,
            removed_symbols=removed_symbols,
            modified_symbols=modified_symbols
        )
        
        return {
            "status": "success",
            "file_path": file_path,
            "removed_count": result["summary"]["total_removed"],
            "modified_count": result["summary"]["total_modified"],
            "total_nodes_deleted": result["summary"]["total_nodes_deleted"],
            "total_relationships_deleted": result["summary"]["total_relationships_deleted"],
            "error_count": result["summary"]["error_count"],
            "reports": result["reports"]
        }
        
    except Exception as e:
        logger.error(f"[PHASE 8.5] Error invalidating file changes: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "file_path": file_path
        }


def get_invalidation_impact(
    file_path: str,
    symbol_name: str,
    symbol_type: str
) -> Dict[str, Any]:
    """
    Preview the impact of invalidating a symbol (dry-run).
    
    Args:
        file_path: Path to the file
        symbol_name: Name of the symbol
        symbol_type: Type (function or class)
        
    Returns:
        {
            "status": "success" | "error",
            "symbol_name": str,
            "would_delete": 1 | 0,
            "relationship_count": int,
            "connected_node_count": int,
            "relationship_types": [str],
            "connected_labels": [[str]]
        }
    """
    try:
        invalidator = get_invalidator()
        result = invalidator.get_invalidation_impact(
            file_path=file_path,
            symbol_name=symbol_name,
            symbol_type=symbol_type
        )
        
        if "error" in result:
            return {
                "status": "error",
                "error": result["error"],
                "symbol_name": symbol_name
            }
        
        return {
            "status": "success",
            **result
        }
        
    except Exception as e:
        logger.error(f"[PHASE 8.5] Error getting invalidation impact: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "symbol_name": symbol_name
        }
