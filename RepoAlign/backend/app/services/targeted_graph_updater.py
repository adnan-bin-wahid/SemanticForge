"""
Sub-phase 8.7: Targeted Graph Update Service

This module implements the logic to take new analysis data from targeted re-analysis
and write it back to the graph, creating new nodes and relationships for modified
or newly added code symbols.

The service works in conjunction with:
- invalidation_service.py (8.5): Removes stale nodes
- targeted_analysis_service.py (8.6): Re-analyzes changed symbols
"""

from typing import List, Optional, Dict, Any
from app.models.code_structures import (
    FileReport,
    FunctionDef,
    ClassDef,
    ImportDef,
    CallDef,
)
import json


class TargetedGraphUpdater:
    """
    Updates the Neo4j graph with new analysis data for modified or new symbols.
    This is incremental and does not clear the database.
    """

    def __init__(self, driver):
        self.driver = driver

    async def update_file_in_graph(self, file_report: FileReport) -> Dict[str, Any]:
        """
        Update a single file's symbols in the graph.
        
        This performs the following operations:
        1. Ensures the File node exists and is linked to the Repository
        2. Creates or updates Function nodes in the file
        3. Creates or updates Class nodes in the file
        4. Re-establishes Call relationships between functions
        5. Re-establishes Inheritance relationships for classes
        6. Re-establishes Import relationships from the file
        
        Args:
            file_report: The newly analyzed file structure
            
        Returns:
            Statistics about the update (nodes created, relationships created, etc.)
        """
        stats = {
            "file_path": file_report.file_path,
            "functions_created": 0,
            "classes_created": 0,
            "relationships_created": 0,
            "errors": [],
        }

        try:
            # Step 1: Ensure File node exists
            await self._ensure_file_node(file_report.file_path)
            
            # Step 2: Create/update Function nodes
            stats["functions_created"] = await self._create_function_nodes(
                file_report
            )

            # Step 3: Create/update Class nodes
            stats["classes_created"] = await self._create_class_nodes(
                file_report
            )

            # Step 4: Create Call relationships
            stats["relationships_created"] += await self._create_call_relationships(
                file_report
            )

            # Step 5: Create Inheritance relationships
            stats["relationships_created"] += (
                await self._create_inheritance_relationships(file_report)
            )

            # Step 6: Create Import relationships
            stats["relationships_created"] += await self._create_import_relationships(
                file_report
            )

        except Exception as e:
            stats["errors"].append(str(e))

        return stats

    async def update_multiple_files(
        self, file_reports: List[FileReport]
    ) -> Dict[str, Any]:
        """
        Update multiple files in the graph.
        
        Args:
            file_reports: List of newly analyzed file structures
            
        Returns:
            Aggregated statistics across all files
        """
        total_stats = {
            "files_updated": 0,
            "total_functions_created": 0,
            "total_classes_created": 0,
            "total_relationships_created": 0,
            "file_updates": [],
        }

        for file_report in file_reports:
            file_stats = await self.update_file_in_graph(file_report)
            total_stats["files_updated"] += 1
            total_stats["total_functions_created"] += file_stats["functions_created"]
            total_stats["total_classes_created"] += file_stats["classes_created"]
            total_stats["total_relationships_created"] += file_stats[
                "relationships_created"
            ]
            total_stats["file_updates"].append(file_stats)

        return total_stats

    async def _ensure_file_node(self, file_path: str) -> None:
        """Ensure the File node exists and is linked to the Repository."""
        async with self.driver.session() as session:
            cypher = """
            MERGE (r:Repository {name: "AnalyzedRepository"})
            MERGE (f:File {path: $file_path})
            SET f.name = $file_name
            MERGE (r)-[:CONTAINS]->(f)
            """
            await session.run(
                cypher,
                file_path=file_path,
                file_name=file_path.split("/")[-1],
            )

    async def _create_function_nodes(self, file_report: FileReport) -> int:
        """
        Create or update Function nodes for all functions in the file.
        Uses MERGE to idempotently create/update nodes.
        
        Returns:
            Count of functions created or updated
        """
        count = 0
        async with self.driver.session() as session:
            for func in file_report.functions:
                signature_str = json.dumps(
                    {
                        "parameters": [p.dict() for p in func.signature.parameters],
                        "return_annotation": func.signature.return_annotation,
                    }
                )

                cypher = """
                MATCH (f:File {path: $file_path})
                MERGE (func:Function {
                    name: $func_name,
                    path: $file_path
                })
                SET func.signature = $signature,
                    func.start_line = $start_line,
                    func.end_line = $end_line,
                    func.content = $content,
                    func.updated_at = timestamp()
                MERGE (f)-[:DEFINES]->(func)
                RETURN func
                """

                result = await session.run(
                    cypher,
                    file_path=file_report.file_path,
                    func_name=func.name,
                    signature=signature_str,
                    start_line=func.lineno,
                    end_line=func.end_lineno,
                    content=func.content,
                )

                # Consume the result to ensure the query executed
                await result.single()
                count += 1

        return count

    async def _create_class_nodes(self, file_report: FileReport) -> int:
        """
        Create or update Class nodes for all classes in the file.
        Uses MERGE to idempotently create/update nodes.
        
        Returns:
            Count of classes created or updated
        """
        count = 0
        async with self.driver.session() as session:
            for cls in file_report.classes:
                cypher = """
                MATCH (f:File {path: $file_path})
                MERGE (c:Class {
                    name: $class_name,
                    path: $file_path
                })
                SET c.bases = $bases,
                    c.start_line = $start_line,
                    c.end_line = $end_line,
                    c.content = $content,
                    c.updated_at = timestamp()
                MERGE (f)-[:DEFINES]->(c)
                RETURN c
                """

                result = await session.run(
                    cypher,
                    file_path=file_report.file_path,
                    class_name=cls.name,
                    bases=cls.bases,
                    start_line=cls.lineno,
                    end_line=cls.end_lineno,
                    content=cls.content,
                )

                # Consume the result to ensure the query executed
                await result.single()
                count += 1

        return count

    async def _create_call_relationships(self, file_report: FileReport) -> int:
        """
        Create CALLS relationships between functions based on the call data.
        
        Returns:
            Count of CALLS relationships created or updated
        """
        count = 0
        async with self.driver.session() as session:
            for func in file_report.functions:
                for call in func.calls:
                    cypher = """
                    MATCH (caller:Function {name: $caller_name})
                    MATCH (callee:Function {name: $callee_name})
                    MERGE (caller)-[r:CALLS]->(callee)
                    SET r.updated_at = timestamp()
                    RETURN r
                    """

                    try:
                        result = await session.run(
                            cypher,
                            caller_name=func.name,
                            callee_name=call.name,
                        )
                        await result.single()
                        count += 1
                    except Exception:
                        # Some callee functions may not be in the graph yet
                        # (e.g., external library calls), so we gracefully skip
                        pass

        return count

    async def _create_inheritance_relationships(self, file_report: FileReport) -> int:
        """
        Create INHERITS relationships between classes based on base class data.
        
        Returns:
            Count of INHERITS relationships created or updated
        """
        count = 0
        async with self.driver.session() as session:
            for cls in file_report.classes:
                if not cls.bases:
                    continue

                for base_class_name in cls.bases:
                    cypher = """
                    MATCH (child:Class {name: $child_name})
                    MATCH (parent:Class {name: $parent_name})
                    MERGE (child)-[r:INHERITS]->(parent)
                    SET r.updated_at = timestamp()
                    RETURN r
                    """

                    try:
                        result = await session.run(
                            cypher,
                            child_name=cls.name,
                            parent_name=base_class_name,
                        )
                        await result.single()
                        count += 1
                    except Exception:
                        # Base class may not be defined in this repository
                        pass

        return count

    async def _create_import_relationships(self, file_report: FileReport) -> int:
        """
        Create IMPORTS relationships from the file to the modules it imports.
        
        Returns:
            Count of IMPORTS relationships created or updated
        """
        count = 0
        async with self.driver.session() as session:
            for import_def in file_report.imports:
                if not import_def.module:
                    continue

                cypher = """
                MATCH (f:File {path: $file_path})
                MERGE (m:Module {name: $module_name})
                MERGE (f)-[r:IMPORTS]->(m)
                SET r.updated_at = timestamp()
                RETURN r
                """

                result = await session.run(
                    cypher,
                    file_path=file_report.file_path,
                    module_name=import_def.module,
                )
                await result.single()
                count += 1

        return count

    async def invalidate_and_update_file(
        self,
        file_path: str,
        file_report: FileReport,
        invalidation_service=None,
    ) -> Dict[str, Any]:
        """
        Complete cycle: Invalidate old nodes for a file, then update with new data.
        
        This orchestrates the full update cycle:
        1. Delete old nodes and relationships for symbols in this file
        2. Create new nodes and relationships from the fresh analysis
        
        Args:
            file_path: Path to the file being updated
            file_report: Fresh analysis data for the file
            invalidation_service: Optional service to handle invalidation (8.5)
            
        Returns:
            Combined statistics from both invalidation and update
        """
        result = {"file_path": file_path}

        # Step 1: Invalidate old data if service provided
        if invalidation_service:
            result["invalidation"] = await invalidation_service.invalidate_file(
                file_path
            )

        # Step 2: Insert new data
        result["update"] = await self.update_file_in_graph(file_report)

        return result
