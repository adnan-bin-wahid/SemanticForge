"""
Utility to populate Test nodes in Neo4j from discovered test files.
"""

import logging
import os
from neo4j import GraphDatabase
from typing import List

logger = logging.getLogger(__name__)


def create_test_nodes(
    repo_path: str,
    neo4j_uri: str = "bolt://neo4j:7687",
    neo4j_user: str = "neo4j",
    neo4j_password: str = "password"
) -> int:
    """
    Discover test files and create Test nodes in Neo4j.
    
    Args:
        repo_path: Path to repository
        neo4j_uri: Neo4j connection URI
        neo4j_user: Neo4j username
        neo4j_password: Neo4j password
        
    Returns:
        Number of Test nodes created
    """
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    try:
        # Find all test files
        test_files = _discover_test_files(repo_path)
        
        if not test_files:
            logger.warning("[PHASE 7.3] No test files found in repository")
            return 0
        
        # Create Test nodes in Neo4j
        count = 0
        with driver.session() as session:
            for test_file in test_files:
                # Extract test name from file (e.g., test_utils.py -> test_utils)
                test_name = os.path.splitext(os.path.basename(test_file))[0]
                
                # Create Test node
                query = """
                MERGE (t:Test {name: $name})
                SET t.path = $path, t.file_name = $file_name
                RETURN t.name
                """
                
                result = session.run(
                    query,
                    name=test_name,
                    path=test_file,
                    file_name=os.path.basename(test_file)
                )
                
                if result.peek():
                    count += 1
                    logger.info(f"[PHASE 7.3] Created Test node: {test_name}")
        
        logger.info(f"[PHASE 7.3] Created {count} Test nodes")
        return count
        
    finally:
        driver.close()


def _discover_test_files(repo_path: str) -> List[str]:
    """
    Discover all test files in the repository.
    
    Args:
        repo_path: Path to repository
        
    Returns:
        List of test file paths
    """
    test_files = []
    
    for root, dirs, files in os.walk(repo_path):
        # Skip hidden directories and common non-code directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]
        
        for file in files:
            # Match pytest conventions: test_*.py or *_test.py
            if file.endswith('.py') and (file.startswith('test_') or file.endswith('_test.py')):
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, repo_path)
                test_files.append(relative_path)
    
    return test_files
