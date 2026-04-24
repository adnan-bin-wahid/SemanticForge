"""
Basic Rules Checker Integration Example

This module demonstrates how to use BasicRulesChecker with TemporaryEnvironmentService
to validate patched code in a sandboxed environment.
"""

from typing import Dict, Tuple
from app.services.basic_rules_checker import BasicRulesChecker, BasicCheckReport
from app.services.temporary_environment import TemporaryEnvironmentService


def check_patch_syntax(
    original_file_path: str,
    file_relative_path: str,
    generated_code: str
) -> Tuple[BasicCheckReport, str]:
    """
    Perform basic syntax and structural checking on a generated patch.
    
    This high-level function:
    1. Creates a temporary sandbox with the patched file
    2. Runs basic checks on the patched file
    3. Cleans up the sandbox
    4. Returns the validation report
    
    Args:
        original_file_path (str): Path to original file
        file_relative_path (str): Relative path in sandbox (e.g., "src/utils/helpers.py")
        generated_code (str): The generated/patched code
    
    Returns:
        Tuple[BasicCheckReport, str]:
            - report: BasicCheckReport with validation results
            - temp_dir: Path to temporary directory (for debugging if needed)
    
    Example:
        >>> report, temp_dir = check_patch_syntax(
        ...     "/path/to/original.py",
        ...     "src/helpers.py",
        ...     "def new_func():\n    return 42\n"
        ... )
        >>> if report.passed:
        ...     print("✓ Code passed basic syntax check!")
        ... else:
        ...     print(f"✗ Found {report.error_count} syntax errors")
    """
    temp_env = TemporaryEnvironmentService()
    
    try:
        # Create sandbox with patched file
        temp_dir, temp_file_path = temp_env.create_sandbox_for_patch(
            original_file_path,
            file_relative_path,
            generated_code
        )
        
        # Perform basic checks
        report = BasicRulesChecker.check_file(temp_file_path)
        
        return report, temp_dir
        
    finally:
        # Cleanup
        temp_env.cleanup_all_sandboxes()


def check_code_directly(code: str) -> BasicCheckReport:
    """
    Perform basic syntax and structural checking directly on code string.
    
    This function bypasses temporary file creation and checks code in-memory.
    Useful for quick validation during code generation.
    
    Args:
        code (str): The code to check
    
    Returns:
        BasicCheckReport: Report of all issues found
    
    Example:
        >>> code = "def func():\n    return 42"
        >>> report = check_code_directly(code)
        >>> print(f"Passed: {report.passed}")
    """
    return BasicRulesChecker.check_code(code)


def check_repository_patches(
    repo_path: str,
    patches: Dict[str, str]
) -> Tuple[BasicCheckReport, Dict[str, BasicCheckReport], str]:
    """
    Perform basic syntax checking on multiple patches across a repository.
    
    This function:
    1. Creates a sandbox copy of the repository
    2. Applies multiple patches to different files
    3. Runs basic checks on all files
    4. Returns both aggregate and per-file reports
    
    Args:
        repo_path (str): Path to source repository
        patches (Dict[str, str]): Dictionary of {file_relative_path: generated_code}
    
    Returns:
        Tuple[BasicCheckReport, Dict[str, BasicCheckReport], str]:
            - aggregate_report: Combined report for all files
            - per_file_reports: Individual reports per file
            - temp_repo_path: Path to temporary repository copy
    
    Example:
        >>> patches = {
        ...     "src/utils.py": "def new_func():\n    pass",
        ...     "src/helpers.py": "def helper():\n    return 42"
        ... }
        >>> agg_report, per_file, temp_path = check_repository_patches(
        ...     "/path/to/repo",
        ...     patches
        ... )
        >>> print(f"Total syntax issues: {agg_report.total_issues}")
    """
    temp_env = TemporaryEnvironmentService()
    
    try:
        # Create sandbox repository
        temp_repo_path = temp_env.create_sandbox_for_repository(repo_path)
        
        # Apply all patches
        for file_relative_path, generated_code in patches.items():
            temp_env.apply_patch_to_sandbox(
                temp_repo_path,
                file_relative_path,
                generated_code
            )
        
        # Check all files in the repository
        per_file_reports = {}
        all_issues = []
        
        from pathlib import Path
        for py_file in Path(temp_repo_path).rglob('*.py'):
            try:
                report = BasicRulesChecker.check_file(str(py_file))
                per_file_reports[str(py_file.relative_to(temp_repo_path))] = report
                all_issues.extend(report.issues)
            except Exception:
                pass

        # Create aggregate report
        error_count = sum(1 for i in all_issues if i.severity == "error")
        warning_count = sum(1 for i in all_issues if i.severity == "warning")
        has_syntax_error = any(i.issue_type == "syntax_error" for i in all_issues)

        aggregate_report = BasicCheckReport(
            issues=all_issues,
            passed=error_count == 0,
            total_issues=len(all_issues),
            error_count=error_count,
            warning_count=warning_count,
            has_syntax_error=has_syntax_error,
            summary=f"Repository check: {error_count} errors, {warning_count} warnings"
        )

        return aggregate_report, per_file_reports, temp_repo_path
        
    finally:
        # Cleanup
        temp_env.cleanup_all_sandboxes()


def generate_basic_check_summary(report: BasicCheckReport) -> Dict:
    """
    Generate a summary of basic checking results suitable for API responses.
    
    Args:
        report (BasicCheckReport): The basic check report
    
    Returns:
        Dict: Structured summary of validation results
    """
    return {
        "validation_type": "basic_syntax_check",
        "status": "passed" if report.passed else "failed",
        "summary": BasicRulesChecker.get_quick_summary(report),
        "details": {
            "total_issues": report.total_issues,
            "errors": report.error_count,
            "warnings": report.warning_count,
            "has_syntax_error": report.has_syntax_error,
        },
        "issues": [i.to_dict() for i in report.issues],
        "text_report": BasicRulesChecker.format_report_text(report)
    }


def is_code_syntactically_valid(code: str) -> bool:
    """
    Quick check to determine if code is syntactically valid.
    
    Args:
        code (str): The code to check
    
    Returns:
        bool: True if code has no syntax errors, False otherwise
    
    Example:
        >>> valid = is_code_syntactically_valid("def func():\n    return 42")
        >>> print(valid)
        True
    """
    report = BasicRulesChecker.check_code(code)
    return report.passed and not report.has_syntax_error
