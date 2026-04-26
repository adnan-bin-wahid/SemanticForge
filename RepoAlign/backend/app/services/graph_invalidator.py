"""
Phase 8.5: Graph Invalidation Service

Surgically removes stale nodes and relationships from Neo4j based on 
detected symbol changes (removals and modifications).

This service:
1. Identifies Function/Class nodes that were removed or modified
2. Deletes those nodes from Neo4j
3. Handles cascade deletion of all connected relationships
4. Tracks invalidation metrics for monitoring
"""

import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from neo4j import Session

logger = logging.getLogger(__name__)


class InvalidationScope(Enum):
    """Scope of invalidation operation"""
    REMOVED = "removed"  # Delete node completely
    MODIFIED = "modified"  # Keep node but remove stale relationships


@dataclass
class InvalidationReport:
    """Report of nodes and relationships invalidated"""
    file_path: str
    scope: InvalidationScope
    symbol_name: str
    symbol_type: str  # "function" or "class"
    nodes_deleted: int = 0
    relationships_deleted: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "file_path": self.file_path,
            "scope": self.scope.value,
            "symbol_name": self.symbol_name,
            "symbol_type": self.symbol_type,
            "nodes_deleted": self.nodes_deleted,
            "relationships_deleted": self.relationships_deleted,
            "timestamp": self.timestamp.isoformat(),
            "error": self.error
        }


class GraphInvalidator:
    """Handles surgical removal of stale nodes from Neo4j"""
    
    def __init__(self, neo4j_session: Session):
        self.session = neo4j_session
        logger.info("[PHASE 8.5] GraphInvalidator initialized")
    
    def invalidate_removed_symbol(
        self, 
        file_path: str, 
        symbol_name: str, 
        symbol_type: str
    ) -> InvalidationReport:
        """
        Delete a node for a removed symbol completely.
        
        Args:
            file_path: Path to the file containing the symbol
            symbol_name: Name of the symbol (function or class)
            symbol_type: Type of symbol ("function" or "class")
            
        Returns:
            InvalidationReport with deletion metrics
        """
        report = InvalidationReport(
            file_path=file_path,
            scope=InvalidationScope.REMOVED,
            symbol_name=symbol_name,
            symbol_type=symbol_type
        )
        
        try:
            # Normalize node type
            node_label = "Function" if symbol_type == "function" else "Class"
            
            # Find and delete the node and all connected relationships
            query = f"""
            MATCH (node:{node_label} {{name: $symbol_name}})
            WHERE node.file_path = $file_path
            
            // Delete all relationships connected to this node
            WITH node, 
                 size([(node)-[r]-() | r]) as rel_count
            
            DETACH DELETE node
            
            RETURN rel_count as relationships_deleted
            """
            
            result = self.session.run(
                query,
                symbol_name=symbol_name,
                file_path=file_path
            )
            
            record = result.single()
            if record:
                report.relationships_deleted = record.get("relationships_deleted", 0) or 0
                report.nodes_deleted = 1
                
                logger.info(
                    f"[PHASE 8.5] Removed {symbol_type} node: {symbol_name} "
                    f"({report.relationships_deleted} relationships deleted)"
                )
            else:
                logger.warning(
                    f"[PHASE 8.5] Symbol not found for removal: {symbol_name} in {file_path}"
                )
            
            return report
            
        except Exception as e:
            report.error = str(e)
            logger.error(
                f"[PHASE 8.5] Error invalidating removed symbol {symbol_name}: {str(e)}"
            )
            return report
    
    def invalidate_modified_symbol(
        self,
        file_path: str,
        symbol_name: str,
        symbol_type: str,
        new_signature: str,
        new_docstring: Optional[str] = None
    ) -> InvalidationReport:
        """
        Update a node for a modified symbol. Keeps the node but updates its properties.
        Optionally removes stale relationships (e.g., outdated CALLS edges).
        
        Args:
            file_path: Path to the file containing the symbol
            symbol_name: Name of the symbol
            symbol_type: Type of symbol ("function" or "class")
            new_signature: Updated signature
            new_docstring: Updated docstring
            
        Returns:
            InvalidationReport with update metrics
        """
        report = InvalidationReport(
            file_path=file_path,
            scope=InvalidationScope.MODIFIED,
            symbol_name=symbol_name,
            symbol_type=symbol_type
        )
        
        try:
            # Normalize node type
            node_label = "Function" if symbol_type == "function" else "Class"
            
            # Update the node with new properties
            # For modified symbols, we keep the node but update signature
            query = f"""
            MATCH (node:{node_label} {{name: $symbol_name}})
            WHERE node.file_path = $file_path
            
            SET node.signature = $new_signature,
                node.modified_at = timestamp(),
                node.invalidated = true
            
            RETURN count(node) as updated_count
            """
            
            result = self.session.run(
                query,
                symbol_name=symbol_name,
                file_path=file_path,
                new_signature=new_signature
            )
            
            record = result.single()
            if record and record.get("updated_count", 0) > 0:
                report.nodes_deleted = 0  # Node wasn't deleted
                
                # Optionally update docstring
                if new_docstring:
                    doc_query = f"""
                    MATCH (node:{node_label} {{name: $symbol_name}})
                    WHERE node.file_path = $file_path
                    SET node.docstring = $new_docstring
                    """
                    self.session.run(
                        doc_query,
                        symbol_name=symbol_name,
                        file_path=file_path,
                        new_docstring=new_docstring
                    )
                
                logger.info(
                    f"[PHASE 8.5] Updated {symbol_type} node: {symbol_name} "
                    f"(new signature: {new_signature})"
                )
            else:
                logger.warning(
                    f"[PHASE 8.5] Symbol not found for modification: {symbol_name}"
                )
            
            return report
            
        except Exception as e:
            report.error = str(e)
            logger.error(
                f"[PHASE 8.5] Error invalidating modified symbol {symbol_name}: {str(e)}"
            )
            return report
    
    def invalidate_file_symbols(
        self,
        file_path: str,
        removed_symbols: List[Dict[str, str]],
        modified_symbols: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Invalidate multiple symbols in a file.
        
        Args:
            file_path: Path to the modified file
            removed_symbols: List of dicts with {symbol_name, symbol_type}
            modified_symbols: List of dicts with {symbol_name, symbol_type, new_signature, new_docstring}
            
        Returns:
            Summary of invalidation operations
        """
        logger.info(
            f"[PHASE 8.5] Starting file invalidation for {file_path}: "
            f"{len(removed_symbols)} removed, {len(modified_symbols)} modified"
        )
        
        reports = []
        
        # Process removed symbols
        for symbol in removed_symbols:
            report = self.invalidate_removed_symbol(
                file_path=file_path,
                symbol_name=symbol["symbol_name"],
                symbol_type=symbol["symbol_type"]
            )
            reports.append(report)
        
        # Process modified symbols
        for symbol in modified_symbols:
            report = self.invalidate_modified_symbol(
                file_path=file_path,
                symbol_name=symbol["symbol_name"],
                symbol_type=symbol["symbol_type"],
                new_signature=symbol.get("new_signature"),
                new_docstring=symbol.get("new_docstring")
            )
            reports.append(report)
        
        # Calculate summary
        total_nodes_deleted = sum(r.nodes_deleted for r in reports if r.error is None)
        total_rels_deleted = sum(r.relationships_deleted for r in reports if r.error is None)
        error_count = sum(1 for r in reports if r.error is not None)
        
        logger.info(
            f"[PHASE 8.5] Invalidation complete: {total_nodes_deleted} nodes deleted, "
            f"{total_rels_deleted} relationships deleted, {error_count} errors"
        )
        
        return {
            "file_path": file_path,
            "reports": [r.to_dict() for r in reports],
            "summary": {
                "total_removed": len(removed_symbols),
                "total_modified": len(modified_symbols),
                "total_nodes_deleted": total_nodes_deleted,
                "total_relationships_deleted": total_rels_deleted,
                "error_count": error_count,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    
    def get_invalidation_impact(
        self,
        file_path: str,
        symbol_name: str,
        symbol_type: str
    ) -> Dict[str, Any]:
        """
        Analyze the impact of invalidating a symbol.
        Shows what would be deleted without actually deleting.
        
        Args:
            file_path: Path to file
            symbol_name: Name of symbol
            symbol_type: Type of symbol
            
        Returns:
            Impact analysis (connected nodes, relationships, etc.)
        """
        try:
            node_label = "Function" if symbol_type == "function" else "Class"
            
            # Find connected nodes and relationships
            query = f"""
            MATCH (node:{node_label} {{name: $symbol_name}})
            WHERE node.file_path = $file_path
            
            MATCH (node)-[rel]-(connected)
            
            RETURN 
                count(DISTINCT rel) as relationship_count,
                count(DISTINCT connected) as connected_node_count,
                collect(DISTINCT type(rel)) as relationship_types,
                collect(DISTINCT labels(connected)) as connected_labels
            """
            
            result = self.session.run(
                query,
                symbol_name=symbol_name,
                file_path=file_path
            )
            
            record = result.single()
            if record:
                return {
                    "symbol_name": symbol_name,
                    "symbol_type": symbol_type,
                    "would_delete": 1,
                    "relationship_count": record.get("relationship_count", 0) or 0,
                    "connected_node_count": record.get("connected_node_count", 0) or 0,
                    "relationship_types": record.get("relationship_types", []) or [],
                    "connected_labels": record.get("connected_labels", []) or []
                }
            else:
                return {
                    "symbol_name": symbol_name,
                    "symbol_type": symbol_type,
                    "would_delete": 0,
                    "found": False,
                    "message": "Symbol not found in graph"
                }
                
        except Exception as e:
            logger.error(f"[PHASE 8.5] Error analyzing invalidation impact: {str(e)}")
            return {"error": str(e)}
