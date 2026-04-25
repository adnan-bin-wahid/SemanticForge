"""
Coverage Analyzer Integration (Phase 7.2)

High-level API for coverage analysis functionality.
"""

from app.services.coverage_analyzer import CoverageAnalyzer
import logging

logger = logging.getLogger(__name__)


def get_coverage_analysis(repo_path: str):
    """
    Get the coverage analysis for a repository.
    
    Runs pytest with coverage.py to generate line-by-line execution data.

    Args:
        repo_path: Path to the repository

    Returns:
        Coverage report dictionary with:
        - statistics: Overall coverage metrics
        - test_summary: Test execution results
        - coverage_by_file: Per-file coverage details
    """
    logger.info(f"[PHASE 7.2] Starting coverage analysis for: {repo_path}")

    analyzer = CoverageAnalyzer(repo_path)
    analyzer.run_coverage_analysis()

    report = analyzer.get_coverage_report()

    logger.info(f"[PHASE 7.2] ✓ Analysis complete")
    return report
