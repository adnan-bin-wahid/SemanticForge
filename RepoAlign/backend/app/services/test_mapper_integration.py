"""
Test-to-Code Mapping API Integration (Phase 7.1)

Provides API endpoints for test-to-code mapping analysis.
"""

from app.services.test_mapper import TestToCodeMapper
import logging

logger = logging.getLogger(__name__)


def get_test_to_code_mapping(repo_path: str):
    """
    Get the test-to-code mapping for a repository.

    Args:
        repo_path: Path to the repository

    Returns:
        Mapping report dictionary
    """
    logger.info(f"[PHASE 7.1] Analyzing test-to-code mapping for: {repo_path}")

    mapper = TestToCodeMapper(repo_path)
    mapper.discover_files()
    mapper.build_mapping()

    report = mapper.get_mapping_report()

    logger.info(f"[PHASE 7.1] ✓ Analysis complete")
    return report
