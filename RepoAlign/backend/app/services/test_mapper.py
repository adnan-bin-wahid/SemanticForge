"""
Test-to-Code Mapping Service (Phase 7.1)

This module analyzes the repository's test suite to determine which test files
cover which source code files. It uses AST analysis to identify imports and
creates a comprehensive mapping.

Author: RepoAlign Phase 7.1
Date: 2026-04-24
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Optional
import logging

logger = logging.getLogger(__name__)


class TestToCodeMapper:
    """Maps test files to the source code they cover."""

    def __init__(self, repo_path: str):
        """
        Initialize the mapper with a repository path.

        Args:
            repo_path: Path to the repository root
        """
        self.repo_path = Path(repo_path)
        self.source_files: Dict[str, Path] = {}
        self.test_files: Dict[str, Path] = {}
        self.mapping: Dict[str, List[str]] = {}  # test_file -> [source_files]
        self.reverse_mapping: Dict[str, List[str]] = {}  # source_file -> [test_files]

    def discover_files(self) -> None:
        """Discover all Python source and test files in the repository."""
        logger.info("[PHASE 7.1] Discovering source and test files...")

        for py_file in self.repo_path.rglob("*.py"):
            relative_path = str(py_file.relative_to(self.repo_path))

            # Classify as test or source based on naming conventions
            if self._is_test_file(py_file):
                self.test_files[relative_path] = py_file
                logger.info(f"[PHASE 7.1] Found test file: {relative_path}")
            elif self._is_source_file(py_file):
                self.source_files[relative_path] = py_file
                logger.info(f"[PHASE 7.1] Found source file: {relative_path}")

        logger.info(
            f"[PHASE 7.1] Discovered {len(self.source_files)} source files "
            f"and {len(self.test_files)} test files"
        )

    def _is_test_file(self, file_path: Path) -> bool:
        """
        Determine if a file is a test file.

        Conventions:
        - Filename ends with '_test.py' or starts with 'test_'
        - Located in a 'tests' directory
        """
        name = file_path.name
        parts = file_path.parts

        return (
            name.endswith("_test.py")
            or name.startswith("test_")
            or "tests" in parts
            or "test" in parts
        )

    def _is_source_file(self, file_path: Path) -> bool:
        """
        Determine if a file is a source file.

        Source files are not tests and not __init__ files in special directories.
        """
        name = file_path.name
        parts = file_path.parts

        # Exclude tests
        if "tests" in parts or "test" in parts or self._is_test_file(file_path):
            return False

        # Exclude __pycache__ and other special dirs
        if "__pycache__" in parts or name == "__init__.py":
            return False

        return True

    def extract_imports_from_test(self, test_file_path: Path) -> Set[str]:
        """
        Extract imported modules from a test file using AST analysis.

        Returns:
            Set of module names imported (e.g., {'helpers', 'utils.validators'})
        """
        imports = set()

        try:
            with open(test_file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    # import module1, module2
                    for alias in node.names:
                        module_name = alias.name.split(".")[0]
                        imports.add(module_name)

                elif isinstance(node, ast.ImportFrom):
                    # from module import name1, name2
                    if node.module:
                        module_name = node.module.split(".")[0]
                        imports.add(module_name)

        except Exception as e:
            logger.warning(f"[PHASE 7.1] Error parsing {test_file_path}: {str(e)}")

        return imports

    def match_imports_to_sources(self, imports: Set[str]) -> List[str]:
        """
        Match imported module names to actual source files.

        Args:
            imports: Set of imported module names

        Returns:
            List of source file paths that match the imports
        """
        matched_sources = []

        for source_file in self.source_files.keys():
            # Extract module name from file path
            # e.g., 'utils/helpers.py' -> 'helpers', 'utils/validators.py' -> 'validators'
            module_name = source_file.replace(".py", "").split("/")[-1]

            if module_name in imports:
                matched_sources.append(source_file)
                logger.info(
                    f"[PHASE 7.1] Matched import '{module_name}' "
                    f"to source '{source_file}'"
                )

        return matched_sources

    def build_mapping(self) -> Dict[str, List[str]]:
        """
        Build the complete test-to-source mapping.

        Returns:
            Dict mapping test files to their covered source files
        """
        logger.info("[PHASE 7.1] Building test-to-code mapping...")

        for test_file_rel in self.test_files.keys():
            test_file_path = self.test_files[test_file_rel]

            # Extract imports
            imports = self.extract_imports_from_test(test_file_path)
            logger.info(
                f"[PHASE 7.1] Test file '{test_file_rel}' imports: {imports}"
            )

            # Match to sources
            matched_sources = self.match_imports_to_sources(imports)

            self.mapping[test_file_rel] = matched_sources

            logger.info(
                f"[PHASE 7.1] Test '{test_file_rel}' covers {len(matched_sources)} "
                f"source file(s): {matched_sources}"
            )

        # Build reverse mapping
        for source_file in self.source_files.keys():
            covering_tests = [
                test_file
                for test_file, sources in self.mapping.items()
                if source_file in sources
            ]
            self.reverse_mapping[source_file] = covering_tests

        logger.info(f"[PHASE 7.1] ✓ Mapping complete")
        return self.mapping

    def get_mapping_report(self) -> Dict:
        """
        Generate a comprehensive report of the test-to-code mapping.

        Returns:
            Dict containing mapping statistics and details
        """
        total_tests = len(self.test_files)
        total_sources = len(self.source_files)
        total_mappings = sum(len(sources) for sources in self.mapping.values())

        covered_sources = len(
            [s for s in self.source_files if self.reverse_mapping.get(s)]
        )
        uncovered_sources = total_sources - covered_sources

        report = {
            "phase": "7.1",
            "title": "Test-to-Code Mapping",
            "summary": f"Mapped {total_tests} test files to {total_sources} source files",
            "statistics": {
                "total_test_files": total_tests,
                "total_source_files": total_sources,
                "total_mappings": total_mappings,
                "covered_source_files": covered_sources,
                "uncovered_source_files": uncovered_sources,
                "coverage_percentage": (
                    100 * covered_sources / total_sources if total_sources > 0 else 0
                ),
            },
            "test_to_source_mapping": self.mapping,
            "source_to_test_mapping": self.reverse_mapping,
            "uncovered_sources": [
                source
                for source in self.source_files.keys()
                if not self.reverse_mapping.get(source)
            ],
            "details": {
                "test_files": list(self.test_files.keys()),
                "source_files": list(self.source_files.keys()),
            },
        }

        return report

    def print_mapping_report(self) -> None:
        """Print a human-readable mapping report."""
        report = self.get_mapping_report()

        print("\n" + "=" * 80)
        print(f"PHASE 7.1: TEST-TO-CODE MAPPING REPORT")
        print("=" * 80)
        print(f"\n{report['summary']}")

        print(f"\n{'-' * 80}")
        print("STATISTICS")
        print(f"{'-' * 80}")
        for key, value in report["statistics"].items():
            if key == "coverage_percentage":
                print(f"  {key}: {value:.1f}%")
            else:
                print(f"  {key}: {value}")

        print(f"\n{'-' * 80}")
        print("TEST-TO-SOURCE MAPPING")
        print(f"{'-' * 80}")
        for test_file, source_files in self.mapping.items():
            status = "✓" if source_files else "✗"
            print(f"\n{status} {test_file}")
            if source_files:
                for source_file in source_files:
                    print(f"    → {source_file}")
            else:
                print("    (No direct source coverage)")

        if report["uncovered_sources"]:
            print(f"\n{'-' * 80}")
            print("UNCOVERED SOURCE FILES")
            print(f"{'-' * 80}")
            for source_file in report["uncovered_sources"]:
                print(f"  ✗ {source_file}")

        print("\n" + "=" * 80 + "\n")


def analyze_test_to_code_mapping(repo_path: str) -> Dict:
    """
    Analyze repository and create test-to-code mapping.

    Args:
        repo_path: Path to the repository

    Returns:
        Mapping report dictionary
    """
    logger.info(f"[PHASE 7.1] Starting test-to-code mapping for: {repo_path}")

    mapper = TestToCodeMapper(repo_path)
    mapper.discover_files()
    mapper.build_mapping()

    report = mapper.get_mapping_report()

    logger.info(f"[PHASE 7.1] ✓ Mapping complete: {report['statistics']}")

    return report


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) > 1:
        repo_path = sys.argv[1]
    else:
        repo_path = "/app/test-project"

    mapper = TestToCodeMapper(repo_path)
    mapper.discover_files()
    mapper.build_mapping()
    mapper.print_mapping_report()
