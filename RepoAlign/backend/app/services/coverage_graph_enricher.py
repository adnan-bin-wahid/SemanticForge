"""
Phase 7.3: Coverage Graph Edges
Process coverage reports and create COVERED_BY edges in Neo4j graph.
Links Function nodes to Test nodes based on code coverage data.
"""

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


class CoverageGraphEnricher:
    """
    Enriches the Neo4j knowledge graph with COVERED_BY edges
    linking Functions to Tests based on coverage data.
    """
    
    def __init__(self, repo_path: str, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        """
        Initialize the coverage graph enricher.
        
        Args:
            repo_path: Path to the repository
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
        """
        self.repo_path = repo_path
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.coverage_data = {}
        self.test_files = []
        self.functions_by_file = {}
        self.edges_created = 0
        
        logger.info(f"[PHASE 7.3] CoverageGraphEnricher initialized for {repo_path}")
    
    def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()
    
    def enrich_coverage_graph(self) -> Dict[str, Any]:
        """
        Main orchestration method to enrich the graph with coverage data.
        
        Returns:
            Summary of enrichment results
        """
        logger.info("[PHASE 7.3] Starting coverage graph enrichment")
        
        try:
            # Step 1: Fetch all Function nodes from Neo4j
            self._fetch_functions_from_graph()
            
            # Step 2: Run coverage analysis
            self._run_coverage_analysis()
            
            # Step 3: Identify test files
            self._identify_test_files()
            
            # Step 4: Map coverage data to functions
            coverage_mapping = self._map_coverage_to_functions()
            
            # Step 5: Create COVERED_BY edges in graph
            self._create_coverage_edges(coverage_mapping)
            
            result = {
                "phase": "7.3",
                "title": "Coverage Graph Enrichment",
                "status": "success",
                "functions_processed": len(self.functions_by_file),
                "edges_created": self.edges_created,
                "coverage_data": self.coverage_data
            }
            
            logger.info(f"[PHASE 7.3] Enrichment complete: {self.edges_created} edges created")
            return result
            
        except Exception as e:
            logger.error(f"[PHASE 7.3] Error during graph enrichment: {str(e)}")
            raise
    
    def _fetch_functions_from_graph(self) -> None:
        """
        Fetch all Function nodes from Neo4j with their file paths and line ranges.
        """
        logger.info("[PHASE 7.3] Fetching Function nodes from graph")
        
        query = """
        MATCH (f:Function) 
        OPTIONAL MATCH (file:File)-[:DEFINES]->(f)
        RETURN f.name as function_name, f.start_line as start_line, f.end_line as end_line, 
               file.path as file_path
        """
        
        with self.driver.session() as session:
            result = session.run(query)
            
            for record in result:
                func_name = record["function_name"]
                start_line = record["start_line"]
                end_line = record["end_line"]
                file_path = record["file_path"]
                
                if not file_path:
                    logger.warning(f"[PHASE 7.3] Function {func_name} has no associated file")
                    continue
                
                # Normalize file path
                normalized_path = os.path.normpath(file_path)
                
                if normalized_path not in self.functions_by_file:
                    self.functions_by_file[normalized_path] = []
                
                self.functions_by_file[normalized_path].append({
                    "name": func_name,
                    "start_line": start_line,
                    "end_line": end_line,
                    "file_path": file_path
                })
        
        logger.info(f"[PHASE 7.3] Found {len(self.functions_by_file)} files with functions")
    
    def _run_coverage_analysis(self) -> None:
        """
        Run pytest with coverage.py to collect coverage data.
        """
        logger.info("[PHASE 7.3] Running coverage analysis")
        
        with tempfile.TemporaryDirectory(prefix="coverage_") as tmpdir:
            coverage_db = os.path.join(tmpdir, "coverage.db")
            coverage_json = os.path.join(tmpdir, "coverage.json")
            
            # Run pytest with coverage
            cmd = [
                "python",
                "-m",
                "coverage",
                "run",
                f"--data-file={coverage_db}",
                "-m",
                "pytest",
                self.repo_path,
                "-v",
                "--tb=short",
                "-q"
            ]
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=self.repo_path,
                    timeout=300
                )
                
                logger.info(f"[PHASE 7.3] Pytest output: {result.stdout}")
                
                # Export coverage to JSON
                export_cmd = [
                    "python",
                    "-m",
                    "coverage",
                    "json",
                    f"--data-file={coverage_db}",
                    "-o",
                    coverage_json
                ]
                
                export_result = subprocess.run(
                    export_cmd,
                    capture_output=True,
                    text=True,
                    cwd=self.repo_path,
                    timeout=60
                )
                
                if not os.path.exists(coverage_json):
                    raise FileNotFoundError(f"Coverage JSON not generated: {coverage_json}")
                
                # Load coverage data
                with open(coverage_json, 'r') as f:
                    coverage_obj = json.load(f)
                
                self.coverage_data = coverage_obj.get("files", {})
                logger.info(f"[PHASE 7.3] Coverage data loaded for {len(self.coverage_data)} files")
                
            except subprocess.TimeoutExpired:
                logger.error("[PHASE 7.3] Coverage analysis timed out")
                raise
            except Exception as e:
                logger.error(f"[PHASE 7.3] Error running coverage: {str(e)}")
                raise
    
    def _identify_test_files(self) -> None:
        """
        Identify all test files in the repository.
        """
        logger.info("[PHASE 7.3] Identifying test files")
        
        for root, dirs, files in os.walk(self.repo_path):
            for file in files:
                # Match pytest conventions: test_*.py or *_test.py
                if file.endswith('.py') and (file.startswith('test_') or file.endswith('_test.py')):
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, self.repo_path)
                    self.test_files.append(relative_path)
        
        logger.info(f"[PHASE 7.3] Found {len(self.test_files)} test files")
    
    def _map_coverage_to_functions(self) -> Dict[str, Set[str]]:
        """
        Map coverage data to functions.
        
        Returns:
            Dictionary mapping function identifiers to sets of test files
        """
        logger.info("[PHASE 7.3] Mapping coverage to functions")
        
        coverage_mapping = {}
        
        # For each file in coverage data
        for file_path_in_coverage, coverage_info in self.coverage_data.items():
            executed_lines = coverage_info.get("executed_lines", [])
            
            # Normalize the file path for comparison
            normalized_coverage_path = os.path.normpath(file_path_in_coverage)
            
            # Find matching file in our functions
            for repo_file_path, functions in self.functions_by_file.items():
                normalized_repo_path = os.path.normpath(repo_file_path)
                
                # Check if paths match (by basename or full path)
                if (normalized_coverage_path.endswith(normalized_repo_path) or 
                    normalized_repo_path.endswith(normalized_coverage_path) or
                    os.path.basename(normalized_coverage_path) == os.path.basename(normalized_repo_path)):
                    
                    # Check which functions have lines in executed_lines
                    for func in functions:
                        func_start = func["start_line"]
                        func_end = func["end_line"]
                        func_name = func["name"]
                        
                        # Check if any line of this function was executed
                        is_covered = any(
                            func_start <= line <= func_end
                            for line in executed_lines
                        )
                        
                        if is_covered:
                            func_id = f"{os.path.basename(repo_file_path)}::{func_name}"
                            if func_id not in coverage_mapping:
                                coverage_mapping[func_id] = set()
                            # For now, map to all test files (simplified)
                            coverage_mapping[func_id].update(self.test_files)
                            
                            logger.info(f"[PHASE 7.3] Function {func_id} is covered")
        
        logger.info(f"[PHASE 7.3] Mapped {len(coverage_mapping)} covered functions")
        return coverage_mapping
    
    def _create_coverage_edges(self, coverage_mapping: Dict[str, Set[str]]) -> None:
        """
        Create COVERED_BY edges in Neo4j.
        
        Args:
            coverage_mapping: Mapping of function identifiers to test files
        """
        logger.info("[PHASE 7.3] Creating COVERED_BY edges in graph")
        
        with self.driver.session() as session:
            for func_id, test_files in coverage_mapping.items():
                # Parse function identifier
                parts = func_id.split("::")
                if len(parts) != 2:
                    continue
                
                file_name, func_name = parts
                
                # Create edge for each test file
                for test_file in test_files:
                    # Extract test name from file (e.g., test_utils.py -> test_utils)
                    test_name = os.path.splitext(os.path.basename(test_file))[0]
                    
                    # Create COVERED_BY edge
                    query = """
                    MATCH (f:Function {name: $func_name})
                    MATCH (t:Test {name: $test_name})
                    MERGE (f)-[:COVERED_BY]->(t)
                    RETURN f.name, t.name
                    """
                    
                    try:
                        result = session.run(query, func_name=func_name, test_name=test_name)
                        if result.peek():
                            self.edges_created += 1
                            logger.info(f"[PHASE 7.3] Created edge: {func_name} <- COVERED_BY <- {test_name}")
                    except Exception as e:
                        logger.warning(f"[PHASE 7.3] Could not create edge for {func_name} and {test_name}: {str(e)}")


def enrich_coverage_graph(
    repo_path: str,
    neo4j_uri: str = "bolt://neo4j:7687",
    neo4j_user: str = "neo4j",
    neo4j_password: str = "password"
) -> Dict[str, Any]:
    """
    Standalone function to enrich coverage graph.
    
    Args:
        repo_path: Path to repository
        neo4j_uri: Neo4j connection URI
        neo4j_user: Neo4j username
        neo4j_password: Neo4j password
        
    Returns:
        Enrichment results
    """
    enricher = CoverageGraphEnricher(repo_path, neo4j_uri, neo4j_user, neo4j_password)
    try:
        return enricher.enrich_coverage_graph()
    finally:
        enricher.close()
