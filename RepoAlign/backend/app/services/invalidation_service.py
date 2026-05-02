"""
Sub-phase 8.5: Graph Invalidation Service

This module implements the logic to delete stale nodes and relationships
from the Neo4j graph when code symbols are removed or modified.

The invalidation process:
1. Identifies which nodes need to be removed (based on file changes)
2. Safely deletes nodes and their relationships
3. Preserves the integrity of the graph
"""

from typing import List, Dict, Any, Set
from app.models.code_structures import FileReport


class InvalidationService:
    """
    Handles the deletion of stale nodes and relationships from the Neo4j graph
    when code symbols are removed or significantly modified.
    """

    def __init__(self, driver):
        self.driver = driver

    async def invalidate_file(self, file_path: str) -> Dict[str, Any]:
        """
        Invalidate all nodes associated with a file.
        This is called before re-analyzing and re-inserting data for a modified file.
        
        The invalidation process:
        1. Deletes all Function and Class nodes defined in the file
        2. Deletes all relationships from those nodes
        3. Preserves the File node itself for reconnection
        
        Args:
            file_path: Path to the file to invalidate
            
        Returns:
            Statistics about deleted nodes and relationships
        """
        stats = {
            "file_path": file_path,
            "functions_deleted": 0,
            "classes_deleted": 0,
            "relationships_deleted": 0,
            "errors": [],
        }

        try:
            async with self.driver.session() as session:
                # Delete all Function nodes defined in this file
                func_result = await session.run(
                    """
                    MATCH (f:File {path: $file_path})-[:DEFINES]->(func:Function)
                    DETACH DELETE func
                    RETURN count(func) as deleted_count
                    """,
                    file_path=file_path,
                )
                
                func_record = await func_result.single()
                stats["functions_deleted"] = (
                    func_record["deleted_count"] if func_record else 0
                )

                # Delete all Class nodes defined in this file
                class_result = await session.run(
                    """
                    MATCH (f:File {path: $file_path})-[:DEFINES]->(cls:Class)
                    DETACH DELETE cls
                    RETURN count(cls) as deleted_count
                    """,
                    file_path=file_path,
                )
                
                class_record = await class_result.single()
                stats["classes_deleted"] = (
                    class_record["deleted_count"] if class_record else 0
                )

                # Count relationships that would be affected
                rel_result = await session.run(
                    """
                    MATCH (f:File {path: $file_path})
                    MATCH (f)-[r]-()
                    RETURN count(r) as relationship_count
                    """,
                    file_path=file_path,
                )
                
                rel_record = await rel_result.single()
                stats["relationships_deleted"] = (
                    rel_record["relationship_count"] if rel_record else 0
                )

        except Exception as e:
            stats["errors"].append(str(e))

        return stats

    async def invalidate_symbol(
        self, file_path: str, symbol_name: str, symbol_type: str = "Function"
    ) -> Dict[str, Any]:
        """
        Invalidate a specific symbol (function or class) within a file.
        
        Used when a single symbol is added, removed, or significantly modified.
        
        Args:
            file_path: Path to the file containing the symbol
            symbol_name: Name of the symbol to invalidate
            symbol_type: Type of symbol ("Function" or "Class")
            
        Returns:
            Statistics about deleted nodes and relationships
        """
        stats = {
            "file_path": file_path,
            "symbol_name": symbol_name,
            "symbol_type": symbol_type,
            "deleted": False,
            "errors": [],
        }

        try:
            async with self.driver.session() as session:
                # Delete the specific node and its relationships
                result = await session.run(
                    f"""
                    MATCH (n:{symbol_type} {{name: $symbol_name, path: $file_path}})
                    DETACH DELETE n
                    RETURN true as deleted
                    """,
                    symbol_name=symbol_name,
                    file_path=file_path,
                )

                record = await result.single()
                stats["deleted"] = bool(record) if record else False

        except Exception as e:
            stats["errors"].append(str(e))

        return stats

    async def invalidate_symbols(
        self, file_path: str, symbols: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Invalidate multiple specific symbols within a file.
        
        Used when AST diffing identifies multiple changed symbols.
        
        Args:
            file_path: Path to the file containing the symbols
            symbols: List of dicts with "name" and "type" keys
            
        Returns:
            Aggregated statistics about deleted nodes
        """
        total_stats = {
            "file_path": file_path,
            "symbols_invalidated": 0,
            "symbol_details": [],
        }

        for symbol in symbols:
            symbol_stats = await self.invalidate_symbol(
                file_path=file_path,
                symbol_name=symbol["name"],
                symbol_type=symbol["type"],
            )
            total_stats["symbols_invalidated"] += 1
            total_stats["symbol_details"].append(symbol_stats)

        return total_stats

    async def cleanup_orphaned_nodes(self) -> Dict[str, Any]:
        """
        Clean up orphaned nodes in the graph (nodes with no relationships).
        
        This can happen if invalid deletes occur or if there are inconsistencies.
        
        Returns:
            Statistics about cleaned up nodes
        """
        stats = {
            "orphaned_deleted": 0,
            "errors": [],
        }

        try:
            async with self.driver.session() as session:
                # Find and delete nodes with no relationships (except Repository)
                result = await session.run(
                    """
                    MATCH (n)
                    WHERE NOT (n:Repository)
                    AND NOT (()--(n))
                    DETACH DELETE n
                    RETURN count(n) as deleted_count
                    """
                )

                record = await result.single()
                stats["orphaned_deleted"] = (
                    record["deleted_count"] if record else 0
                )

        except Exception as e:
            stats["errors"].append(str(e))

        return stats

    async def validate_graph_integrity(self) -> Dict[str, Any]:
        """
        Validate the integrity of the graph after invalidation/updates.
        
        Returns:
            Report of any inconsistencies found
        """
        report = {
            "valid": True,
            "issues": [],
        }

        try:
            async with self.driver.session() as session:
                # Check for orphaned nodes
                orphaned_result = await session.run(
                    """
                    MATCH (n)
                    WHERE NOT (n:Repository)
                    AND NOT (()--(n))
                    RETURN count(n) as orphaned_count
                    """
                )

                orphaned_record = await orphaned_result.single()
                orphaned_count = (
                    orphaned_record["orphaned_count"] if orphaned_record else 0
                )

                if orphaned_count > 0:
                    report["valid"] = False
                    report["issues"].append(
                        f"Found {orphaned_count} orphaned nodes"
                    )

                # Check for dangling relationships
                dangling_result = await session.run(
                    """
                    MATCH (n)-[r]->(m)
                    WHERE n IS NULL OR m IS NULL
                    RETURN count(r) as dangling_count
                    """
                )

                dangling_record = await dangling_result.single()
                dangling_count = (
                    dangling_record["dangling_count"] if dangling_record else 0
                )

                if dangling_count > 0:
                    report["valid"] = False
                    report["issues"].append(
                        f"Found {dangling_count} dangling relationships"
                    )

        except Exception as e:
            report["valid"] = False
            report["issues"].append(f"Error during validation: {str(e)}")

        return report
