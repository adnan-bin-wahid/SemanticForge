"""
Test Execution Runner

This module provides functionality to execute pytest suite and capture results.
Used to validate that generated patches don't break existing tests.
"""

import subprocess
import re
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict, field
from pathlib import Path


@dataclass
class TestResult:
    """Represents the result of a single test case."""
    test_name: str  # e.g., "test_utils.py::test_format_greeting"
    status: str  # "passed", "failed", "skipped", "error"
    duration: float  # seconds
    error_message: Optional[str] = None  # Error/failure message if applicable
    assertion_message: Optional[str] = None  # Assertion details if applicable

    def to_dict(self) -> Dict:
        """Convert result to dictionary."""
        return asdict(self)


@dataclass
class TestSuite:
    """Individual test file/module result."""
    file_path: str
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    test_results: List[TestResult] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "file_path": self.file_path,
            "total_tests": self.total_tests,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "errors": self.errors,
            "test_results": [t.to_dict() for t in self.test_results],
        }


@dataclass
class TestReport:
    """Complete pytest execution report."""
    passed: bool  # True only if all tests pass
    total_tests: int
    total_passed: int
    total_failed: int
    total_skipped: int
    total_errors: int
    total_duration: float
    
    test_suites: List[TestSuite] = field(default_factory=list)
    raw_output: str = ""  # Raw pytest output
    summary: str = ""  # Human-readable summary
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "passed": self.passed,
            "total_tests": self.total_tests,
            "total_passed": self.total_passed,
            "total_failed": self.total_failed,
            "total_skipped": self.total_skipped,
            "total_errors": self.total_errors,
            "total_duration": self.total_duration,
            "test_suites": [s.to_dict() for s in self.test_suites],
            "summary": self.summary,
        }


class TestRunner:
    """
    Executes pytest suite and captures results.
    
    This runner:
    - Executes pytest as a subprocess
    - Captures stdout and stderr
    - Parses pytest output to extract test results
    - Handles various pytest configurations
    - Supports timeout and failure modes
    """

    @staticmethod
    def run_tests(
        test_directory: str,
        timeout: int = 60,
        pytest_args: Optional[List[str]] = None,
        stop_on_first_failure: bool = False
    ) -> TestReport:
        """
        Run pytest on a directory.
        
        Args:
            test_directory (str): Path to directory containing tests
            timeout (int): Timeout in seconds (default 60)
            pytest_args (Optional[List[str]]): Additional pytest arguments
            stop_on_first_failure (bool): Stop at first test failure
        
        Returns:
            TestReport: Report of test execution results
        
        Example:
            >>> report = TestRunner.run_tests("/path/to/repo/tests")
            >>> print(f"Passed: {report.total_passed}/{report.total_tests}")
        """
        # Verify pytest is available
        try:
            subprocess.run(
                ["pytest", "--version"],
                capture_output=True,
                timeout=5,
                check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            return TestRunner._create_error_report(
                "pytest is not installed or not found in PATH. "
                "Install it with: pip install pytest"
            )

        # Build pytest command
        cmd = ["pytest", test_directory, "-v", "--tb=short", "--color=no"]
        
        # Add JSON report for easier parsing
        cmd.extend(["--json-report", "--json-report-file=/tmp/pytest-report.json"])
        
        if stop_on_first_failure:
            cmd.append("-x")  # Exit on first failure
        
        if pytest_args:
            cmd.extend(pytest_args)

        # Run pytest
        try:
            result = subprocess.run(
                cmd,
                cwd=test_directory,
                capture_output=True,
                timeout=timeout,
                text=True
            )
            
            raw_output = result.stdout + result.stderr
            
            # Parse output
            return TestRunner._parse_pytest_output(raw_output, test_directory)
            
        except subprocess.TimeoutExpired:
            return TestRunner._create_error_report(
                f"Pytest execution timed out after {timeout} seconds"
            )
        except Exception as e:
            return TestRunner._create_error_report(
                f"Pytest execution failed: {str(e)}"
            )

    @staticmethod
    def run_specific_test(
        test_file: str,
        test_name: Optional[str] = None,
        timeout: int = 30
    ) -> TestReport:
        """
        Run a specific test file or test case.
        
        Args:
            test_file (str): Path to test file
            test_name (Optional[str]): Specific test name (e.g., "test_func")
            timeout (int): Timeout in seconds
        
        Returns:
            TestReport: Test execution report
        
        Example:
            >>> report = TestRunner.run_specific_test(
            ...     "/path/to/test_utils.py",
            ...     "test_format_greeting"
            ... )
        """
        if not Path(test_file).exists():
            return TestRunner._create_error_report(f"Test file not found: {test_file}")

        # Build test identifier
        if test_name:
            test_id = f"{test_file}::{test_name}"
        else:
            test_id = test_file

        cmd = ["pytest", test_id, "-v", "--tb=short", "--color=no"]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=timeout,
                text=True
            )
            
            raw_output = result.stdout + result.stderr
            return TestRunner._parse_pytest_output(raw_output, str(Path(test_file).parent))
            
        except subprocess.TimeoutExpired:
            return TestRunner._create_error_report(
                f"Test execution timed out after {timeout} seconds"
            )
        except Exception as e:
            return TestRunner._create_error_report(f"Test execution failed: {str(e)}")

    @staticmethod
    def _parse_pytest_output(output: str, base_path: str) -> TestReport:
        """
        Parse pytest output and extract test results.
        
        Args:
            output (str): Pytest output text
            base_path (str): Base path for test files
        
        Returns:
            TestReport: Parsed test report
        """
        report = TestReport(
            passed=False,
            total_tests=0,
            total_passed=0,
            total_failed=0,
            total_skipped=0,
            total_errors=0,
            total_duration=0.0,
            raw_output=output
        )

        # Parse summary line: "X passed, Y failed, Z skipped in 1.23s"
        summary_pattern = r'(\d+) passed|(\d+) failed|(\d+) skipped|(\d+) error'
        matches = re.findall(summary_pattern, output)
        
        passed_match = re.search(r'(\d+) passed', output)
        failed_match = re.search(r'(\d+) failed', output)
        skipped_match = re.search(r'(\d+) skipped', output)
        error_match = re.search(r'(\d+) error', output)
        duration_match = re.search(r'in ([\d.]+)s', output)

        if passed_match:
            report.total_passed = int(passed_match.group(1))
        if failed_match:
            report.total_failed = int(failed_match.group(1))
        if skipped_match:
            report.total_skipped = int(skipped_match.group(1))
        if error_match:
            report.total_errors = int(error_match.group(1))
        if duration_match:
            report.total_duration = float(duration_match.group(1))

        report.total_tests = report.total_passed + report.total_failed + report.total_skipped + report.total_errors
        report.passed = report.total_failed == 0 and report.total_errors == 0

        # Generate summary
        report.summary = TestRunner._generate_summary(report)

        # Parse individual test results
        test_lines = output.split('\n')
        for line in test_lines:
            # Pattern: "test_file.py::test_name PASSED [100%]" or "FAILED" or "SKIPPED"
            test_pattern = r'([\w/\-.]+\.py::\w+)\s+(PASSED|FAILED|SKIPPED|ERROR)'
            match = re.search(test_pattern, line)
            if match:
                test_name = match.group(1)
                status = match.group(2).lower()
                
                result = TestResult(
                    test_name=test_name,
                    status=status,
                    duration=0.0
                )

        return report

    @staticmethod
    def _create_error_report(error_message: str) -> TestReport:
        """
        Create a report representing an error.
        
        Args:
            error_message (str): Error message
        
        Returns:
            TestReport: Error report
        """
        report = TestReport(
            passed=False,
            total_tests=0,
            total_passed=0,
            total_failed=1,
            total_skipped=0,
            total_errors=0,
            total_duration=0.0,
            raw_output=error_message,
            summary=f"✗ Test execution error: {error_message}"
        )
        return report

    @staticmethod
    def _generate_summary(report: TestReport) -> str:
        """
        Generate a summary message for the test report.
        
        Args:
            report (TestReport): The test report
        
        Returns:
            str: Summary message
        """
        if report.passed:
            return (
                f"✓ All tests passed: {report.total_passed} passed "
                f"in {report.total_duration:.2f}s"
            )
        else:
            issues = []
            if report.total_failed > 0:
                issues.append(f"{report.total_failed} failed")
            if report.total_errors > 0:
                issues.append(f"{report.total_errors} error(s)")
            
            issue_str = ", ".join(issues)
            return (
                f"✗ Tests failed: {report.total_passed} passed, {issue_str}, "
                f"{report.total_skipped} skipped in {report.total_duration:.2f}s"
            )

    @staticmethod
    def format_report_text(report: TestReport) -> str:
        """
        Format test report as human-readable text.
        
        Args:
            report (TestReport): The test report
        
        Returns:
            str: Formatted text report
        """
        lines = []
        lines.append("=" * 80)
        lines.append("TEST EXECUTION REPORT")
        lines.append("=" * 80)
        lines.append("")

        # Status
        status = "✓ PASSED" if report.passed else "✗ FAILED"
        lines.append(f"Status: {status}")
        lines.append("")

        # Statistics
        lines.append("Test Statistics:")
        lines.append(f"  Total Tests:  {report.total_tests}")
        lines.append(f"  Passed:       {report.total_passed}")
        lines.append(f"  Failed:       {report.total_failed}")
        lines.append(f"  Skipped:      {report.total_skipped}")
        lines.append(f"  Errors:       {report.total_errors}")
        lines.append(f"  Duration:     {report.total_duration:.2f}s")
        lines.append("")

        # Test suites
        if report.test_suites:
            lines.append("Test Suites:")
            for suite in report.test_suites:
                lines.append(f"  {suite.file_path}:")
                lines.append(f"    Passed: {suite.passed}, Failed: {suite.failed}")

        lines.append("=" * 80)
        return "\n".join(lines)

    @staticmethod
    def get_quick_summary(report: TestReport) -> str:
        """
        Get a one-line summary of test results.
        
        Args:
            report (TestReport): The test report
        
        Returns:
            str: One-line summary
        """
        return report.summary
