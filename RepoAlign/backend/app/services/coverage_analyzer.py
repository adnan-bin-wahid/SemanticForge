"""
Coverage Analysis Service (Phase 7.2)

Runs pytest with coverage.py to generate line-by-line execution data.
"""

import subprocess
import json
import os
import tempfile
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class CoverageAnalyzer:
    """
    Analyzes test coverage using pytest and coverage.py.
    
    Provides line-by-line execution data for all tested files.
    """
    
    def __init__(self, repo_path: str):
        """
        Initialize the coverage analyzer.
        
        Args:
            repo_path: Path to the repository
        """
        self.repo_path = repo_path
        self.coverage_data = {}
        self.test_results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": 0
        }
        self.coverage_report = {}
    
    def run_coverage_analysis(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Run pytest with coverage.py and collect results.
        
        Returns:
            Tuple of (coverage_data, test_results) where:
            - coverage_data: Line-by-line coverage info per file
            - test_results: Test execution summary
        """
        logger.info(f"[PHASE 7.2] Starting coverage analysis for: {self.repo_path}")
        
        # Create temporary coverage database file
        temp_dir = tempfile.mkdtemp(prefix="coverage_")
        coverage_db = os.path.join(temp_dir, ".coverage")
        coverage_json = os.path.join(temp_dir, "coverage.json")
        
        try:
            logger.info(f"[PHASE 7.2] Temporary coverage database: {coverage_db}")
            
            # Run pytest with coverage.py
            logger.info(f"[PHASE 7.2] Running pytest with coverage...")
            test_result = self._run_pytest_with_coverage(coverage_db)
            self.test_results = test_result
            
            # Export coverage to JSON
            logger.info(f"[PHASE 7.2] Exporting coverage data...")
            self._export_coverage_json(coverage_db, coverage_json)
            
            # Parse coverage JSON
            logger.info(f"[PHASE 7.2] Parsing coverage report...")
            self.coverage_data = self._parse_coverage_json(coverage_json)
            
            # Generate structured report
            logger.info(f"[PHASE 7.2] Generating coverage report...")
            self.coverage_report = self._generate_coverage_report()
            
            logger.info(f"[PHASE 7.2] ✓ Coverage analysis complete")
            logger.info(f"[PHASE 7.2] Test Results: {self.test_results['passed']}/{self.test_results['total']} passed")
            logger.info(f"[PHASE 7.2] Files with coverage data: {len(self.coverage_data)}")
            
            return self.coverage_data, self.test_results
            
        except Exception as e:
            logger.error(f"[PHASE 7.2] Error during coverage analysis: {str(e)}", exc_info=True)
            raise
        finally:
            # Cleanup
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(f"[PHASE 7.2] Cleaned up temporary directory: {temp_dir}")
    
    def _run_pytest_with_coverage(self, coverage_db: str) -> Dict[str, int]:
        """
        Run pytest with coverage.py using subprocess.
        
        Args:
            coverage_db: Path to coverage database file
            
        Returns:
            Test results summary
        """
        # Build pytest command with coverage using python -m for better portability
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
        
        logger.info(f"[PHASE 7.2] Running command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                timeout=300  # 5 minute timeout
            )
            
            # Parse pytest output
            stdout = result.stdout
            stderr = result.stderr
            
            logger.info(f"[PHASE 7.2] Pytest stdout:\n{stdout}")
            if stderr:
                logger.info(f"[PHASE 7.2] Pytest stderr:\n{stderr}")
            
            # Extract test counts from output
            test_results = self._parse_pytest_output(stdout, stderr)
            
            return test_results
            
        except subprocess.TimeoutExpired:
            logger.error(f"[PHASE 7.2] Coverage analysis timed out after 300 seconds")
            return {"total": 0, "passed": 0, "failed": 0, "errors": 1}
        except FileNotFoundError:
            logger.error(f"[PHASE 7.2] 'python' command not found or coverage module not installed. Install with: pip install coverage pytest")
            raise
    
    def _parse_pytest_output(self, stdout: str, stderr: str) -> Dict[str, int]:
        """
        Parse pytest output to extract test counts.
        
        Args:
            stdout: Pytest standard output
            stderr: Pytest standard error
            
        Returns:
            Dictionary with test counts
        """
        import re
        
        results = {"total": 0, "passed": 0, "failed": 0, "errors": 0}
        
        # Look for pytest summary line: "X passed in Y.YYs"
        summary_match = re.search(r'(\d+) passed', stdout + stderr)
        if summary_match:
            results["passed"] = int(summary_match.group(1))
            results["total"] += results["passed"]
        
        # Look for failures
        failed_match = re.search(r'(\d+) failed', stdout + stderr)
        if failed_match:
            results["failed"] = int(failed_match.group(1))
            results["total"] += results["failed"]
        
        # Look for errors
        error_match = re.search(r'(\d+) error', stdout + stderr)
        if error_match:
            results["errors"] = int(error_match.group(1))
            results["total"] += results["errors"]
        
        # If no tests found in output, return 0
        if results["total"] == 0:
            logger.warning(f"[PHASE 7.2] Could not parse test count from pytest output")
        
        return results
    
    def _export_coverage_json(self, coverage_db: str, output_file: str) -> None:
        """
        Export coverage data to JSON format.
        
        Args:
            coverage_db: Path to coverage database
            output_file: Path to output JSON file
        """
        # Use python -m for better portability
        cmd = [
            "python",
            "-m",
            "coverage",
            "json",
            f"--data-file={coverage_db}",
            "-o",
            output_file
        ]
        
        logger.info(f"[PHASE 7.2] Exporting coverage to JSON...")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=self.repo_path,
            timeout=60
        )
        
        if result.returncode != 0:
            logger.warning(f"[PHASE 7.2] Coverage export returned code {result.returncode}")
            if result.stderr:
                logger.warning(f"[PHASE 7.2] Error: {result.stderr}")
        
        if not os.path.exists(output_file):
            logger.error(f"[PHASE 7.2] Coverage JSON file not created: {output_file}")
            raise FileNotFoundError(f"Coverage JSON export failed: {output_file}")
    
    def _parse_coverage_json(self, coverage_json: str) -> Dict[str, Any]:
        """
        Parse coverage JSON file.
        
        Args:
            coverage_json: Path to coverage JSON file
            
        Returns:
            Parsed coverage data
        """
        if not os.path.exists(coverage_json):
            logger.warning(f"[PHASE 7.2] Coverage JSON not found: {coverage_json}")
            return {}
        
        try:
            with open(coverage_json, 'r') as f:
                coverage_data = json.load(f)
            
            # coverage.json format:
            # {
            #   "files": {
            #     "/path/to/file.py": {
            #       "executed_lines": [1, 2, 3, 5],
            #       "missing_lines": [4, 6, 7],
            #       "excluded_lines": []
            #     }
            #   },
            #   ...
            # }
            
            return coverage_data.get("files", {})
            
        except Exception as e:
            logger.error(f"[PHASE 7.2] Error parsing coverage JSON: {str(e)}")
            return {}
    
    def _generate_coverage_report(self) -> Dict[str, Any]:
        """
        Generate a structured coverage report.
        
        Returns:
            Comprehensive coverage report
        """
        report = {
            "phase": "7.2",
            "title": "Coverage Analysis Report",
            "test_summary": self.test_results,
            "coverage_by_file": {},
            "statistics": {
                "total_files": 0,
                "total_lines": 0,
                "covered_lines": 0,
                "missing_lines": 0,
                "overall_coverage": 0.0
            }
        }
        
        total_lines = 0
        total_covered = 0
        
        # Process coverage data per file
        for file_path, file_coverage in self.coverage_data.items():
            executed_lines = file_coverage.get("executed_lines", [])
            missing_lines = file_coverage.get("missing_lines", [])
            excluded_lines = file_coverage.get("excluded_lines", [])
            
            file_total = len(executed_lines) + len(missing_lines)
            file_covered = len(executed_lines)
            
            total_lines += file_total
            total_covered += file_covered
            
            coverage_pct = (file_covered / file_total * 100) if file_total > 0 else 0.0
            
            # Make file path relative to repo and clean up
            try:
                rel_path = os.path.relpath(file_path, self.repo_path)
                # Clean up relative path markers like "../"
                rel_path = rel_path.lstrip(".")
                rel_path = rel_path.lstrip("/").lstrip("\\")
                if not rel_path:
                    rel_path = os.path.basename(file_path)
            except ValueError:
                rel_path = os.path.basename(file_path)
            
            report["coverage_by_file"][rel_path] = {
                "total_lines": file_total,
                "covered_lines": file_covered,
                "missing_lines": len(missing_lines),
                "excluded_lines": len(excluded_lines),
                "coverage_percent": round(coverage_pct, 2),
                "executed_lines": sorted(executed_lines),
                "missing_lines": sorted(missing_lines)
            }
        
        # Update statistics
        report["statistics"]["total_files"] = len(self.coverage_data)
        report["statistics"]["total_lines"] = total_lines
        report["statistics"]["covered_lines"] = total_covered
        report["statistics"]["missing_lines"] = total_lines - total_covered
        report["statistics"]["overall_coverage"] = round(
            (total_covered / total_lines * 100) if total_lines > 0 else 0.0,
            2
        )
        
        return report
    
    def get_coverage_report(self) -> Dict[str, Any]:
        """
        Get the generated coverage report.
        
        Returns:
            Coverage report dictionary
        """
        return self.coverage_report
    
    def get_file_coverage(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get coverage data for a specific file.
        
        Args:
            file_path: Relative path to file
            
        Returns:
            Coverage data for file or None if not found
        """
        return self.coverage_report.get("coverage_by_file", {}).get(file_path)
    
    def get_coverage_statistics(self) -> Dict[str, Any]:
        """
        Get coverage statistics summary.
        
        Returns:
            Dictionary with overall coverage stats
        """
        return self.coverage_report.get("statistics", {})


def analyze_coverage_with_pytest(repo_path: str) -> Dict[str, Any]:
    """
    Standalone function to run coverage analysis on a repository.
    
    Args:
        repo_path: Path to the repository
        
    Returns:
        Complete coverage report
    """
    analyzer = CoverageAnalyzer(repo_path)
    analyzer.run_coverage_analysis()
    return analyzer.get_coverage_report()
