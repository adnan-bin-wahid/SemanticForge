"""
Test Runner Integration

High-level functions for integrating test execution with the validation pipeline.
"""

from typing import Dict, Tuple, Optional
from app.services.test_runner import TestRunner, TestReport
from app.services.temporary_environment import TemporaryEnvironmentService


def run_tests_on_patch(
    repo_path: str,
    patches: Optional[Dict[str, str]] = None,
    test_directory: str = "tests",
    timeout: int = 60,
    stop_on_first_failure: bool = False
) -> Tuple[TestReport, str]:
    """
    Run test suite on a repository with optional patches applied.
    
    This function:
    1. Creates a sandbox copy of the repository
    2. Applies patches if provided
    3. Runs pytest on the test directory
    4. Returns test results
    
    Args:
        repo_path (str): Path to source repository
        patches (Optional[Dict[str, str]]): Patches to apply {file_relative_path: code}
        test_directory (str): Path to tests relative to repo (default: "tests")
        timeout (int): Test execution timeout in seconds
        stop_on_first_failure (bool): Stop at first test failure
    
    Returns:
        Tuple[TestReport, str]:
            - report: Test execution results
            - temp_repo_path: Path to temporary repository copy
    
    Example:
        >>> report, temp_dir = run_tests_on_patch(
        ...     "/path/to/repo",
        ...     {"src/helpers.py": "def new_func():\n    pass"}
        ... )
        >>> print(f"Tests passed: {report.passed}")
    """
    temp_env = TemporaryEnvironmentService()
    temp_repo_path = None
    
    try:
        # Create sandbox repository
        temp_repo_path = temp_env.create_sandbox_for_repository(repo_path)
        
        # Apply patches if provided
        if patches:
            for file_relative_path, generated_code in patches.items():
                temp_env.apply_patch_to_sandbox(
                    temp_repo_path,
                    file_relative_path,
                    generated_code
                )
        
        # Run tests
        from pathlib import Path
        test_path = str(Path(temp_repo_path) / test_directory)
        
        report = TestRunner.run_tests(
            test_path,
            timeout=timeout,
            stop_on_first_failure=stop_on_first_failure
        )
        
        return report, temp_repo_path
        
    finally:
        # Cleanup
        if temp_repo_path:
            temp_env.cleanup_all_sandboxes()


def run_tests_directly(
    repo_path: str,
    test_directory: str = "tests",
    timeout: int = 60
) -> TestReport:
    """
    Run test suite directly on a repository (without patches).
    
    Args:
        repo_path (str): Path to repository
        test_directory (str): Path to tests relative to repo
        timeout (int): Test execution timeout
    
    Returns:
        TestReport: Test execution results
    
    Example:
        >>> report = run_tests_directly("/path/to/repo")
        >>> print(f"Passed: {report.total_passed}/{report.total_tests}")
    """
    from pathlib import Path
    test_path = str(Path(repo_path) / test_directory)
    
    return TestRunner.run_tests(test_path, timeout=timeout)


def generate_test_report(report: TestReport) -> Dict:
    """
    Generate an API-friendly test report.
    
    Args:
        report (TestReport): The test execution report
    
    Returns:
        Dict: Structured test report for API responses
    """
    return {
        "validation_type": "test_execution",
        "status": "passed" if report.passed else "failed",
        "summary": TestRunner.get_quick_summary(report),
        "statistics": {
            "total_tests": report.total_tests,
            "passed": report.total_passed,
            "failed": report.total_failed,
            "skipped": report.total_skipped,
            "errors": report.total_errors,
            "duration_seconds": report.total_duration,
        },
        "results": report.to_dict(),
        "text_report": TestRunner.format_report_text(report)
    }


def generate_test_summary(report: TestReport) -> Dict:
    """
    Generate a compact test summary.
    
    Args:
        report (TestReport): The test execution report
    
    Returns:
        Dict: Compact summary
    """
    return {
        "status": "passed" if report.passed else "failed",
        "summary": TestRunner.get_quick_summary(report),
        "total": report.total_tests,
        "passed": report.total_passed,
        "failed": report.total_failed,
        "errors": report.total_errors,
        "duration": f"{report.total_duration:.2f}s"
    }


def did_tests_pass(
    repo_path: str,
    patches: Optional[Dict[str, str]] = None,
    test_directory: str = "tests"
) -> bool:
    """
    Quick check to determine if tests pass with patches applied.
    
    Args:
        repo_path (str): Path to repository
        patches (Optional[Dict[str, str]]): Patches to apply
        test_directory (str): Path to tests
    
    Returns:
        bool: True if all tests pass, False otherwise
    """
    report, _ = run_tests_on_patch(repo_path, patches, test_directory)
    return report.passed


def get_test_failures(
    repo_path: str,
    patches: Optional[Dict[str, str]] = None,
    test_directory: str = "tests"
) -> Dict:
    """
    Get detailed information about test failures.
    
    Args:
        repo_path (str): Path to repository
        patches (Optional[Dict[str, str]]): Patches to apply
        test_directory (str): Path to tests
    
    Returns:
        Dict: Information about failed tests
    """
    report, _ = run_tests_on_patch(repo_path, patches, test_directory)
    
    return {
        "total_failures": report.total_failed + report.total_errors,
        "failed_tests": report.total_failed,
        "errors": report.total_errors,
        "passed": report.total_passed,
        "raw_output": report.raw_output,
        "summary": report.summary
    }
