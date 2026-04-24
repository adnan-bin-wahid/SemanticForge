"""
Mypy Type Checking Integration Example

This module demonstrates how to use MypyValidator with TemporaryEnvironmentService
to type-check patched code in a sandboxed environment.
"""

from typing import Dict, Tuple
from app.services.mypy_validator import MypyValidator, MypyReport
from app.services.temporary_environment import TemporaryEnvironmentService


def type_check_patch_with_mypy(
    original_file_path: str,
    file_relative_path: str,
    generated_code: str,
    strict: bool = False
) -> Tuple[MypyReport, str]:
    """
    Type-check a generated patch using Mypy.
    
    This high-level function:
    1. Creates a temporary sandbox with the patched file
    2. Runs Mypy on the patched file
    3. Cleans up the sandbox
    4. Returns the validation report
    
    Args:
        original_file_path (str): Path to original file
        file_relative_path (str): Relative path in sandbox (e.g., "src/utils/helpers.py")
        generated_code (str): The generated/patched code
        strict (bool): Enable Mypy strict mode (default: False)
    
    Returns:
        Tuple[MypyReport, str]:
            - report: MypyReport with validation results
            - temp_dir: Path to temporary directory (for debugging if needed)
    
    Example:
        >>> report, temp_dir = type_check_patch_with_mypy(
        ...     "/path/to/original.py",
        ...     "src/helpers.py",
        ...     "def new_func() -> int:\n    return 42\n"
        ... )
        >>> if report.passed:
        ...     print("✓ Code passed type checking!")
        ... else:
        ...     print(f"✗ Found {report.error_count} type errors")
    """
    temp_env = TemporaryEnvironmentService()
    
    try:
        # Create sandbox with patched file
        temp_dir, temp_file_path = temp_env.create_sandbox_for_patch(
            original_file_path,
            file_relative_path,
            generated_code
        )
        
        # Type-check the patched file
        report = MypyValidator.check_file(temp_file_path, strict=strict)
        
        return report, temp_dir
        
    finally:
        # Cleanup
        temp_env.cleanup_all_sandboxes()


def type_check_repository_patch_with_mypy(
    repo_path: str,
    patches: Dict[str, str],
    strict: bool = False
) -> Tuple[MypyReport, Dict[str, MypyReport], str]:
    """
    Type-check multiple patches across a repository using Mypy.
    
    This function:
    1. Creates a sandbox copy of the repository
    2. Applies multiple patches to different files
    3. Runs Mypy on the entire repository
    4. Returns both aggregate and per-file reports
    
    Args:
        repo_path (str): Path to source repository
        patches (Dict[str, str]): Dictionary of {file_relative_path: generated_code}
        strict (bool): Enable Mypy strict mode (default: False)
    
    Returns:
        Tuple[MypyReport, Dict[str, MypyReport], str]:
            - aggregate_report: Combined report for all files
            - per_file_reports: Individual reports per file
            - temp_repo_path: Path to temporary repository copy
    
    Example:
        >>> patches = {
        ...     "src/utils.py": "def new_func() -> str:\n    return 'hello'\n",
        ...     "src/helpers.py": "def helper(x: int) -> int:\n    return x * 2\n"
        ... }
        >>> agg_report, per_file, temp_path = type_check_repository_patch_with_mypy(
        ...     "/path/to/repo",
        ...     patches
        ... )
        >>> print(f"Type errors: {agg_report.error_count}")
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
        
        # Type-check entire repository
        aggregate_report, per_file_reports = MypyValidator.check_directory(
            temp_repo_path,
            strict=strict
        )
        
        return aggregate_report, per_file_reports, temp_repo_path
        
    finally:
        # Cleanup
        temp_env.cleanup_all_sandboxes()


def generate_type_check_summary(report: MypyReport) -> Dict:
    """
    Generate a summary of type checking results suitable for API responses.
    
    Args:
        report (MypyReport): The type checking report
    
    Returns:
        Dict: Structured summary of type checking results
    """
    return {
        "validation_type": "mypy_type_check",
        "status": "passed" if report.passed else "failed",
        "summary": MypyValidator.get_quick_summary(report),
        "details": {
            "total_errors": report.total_errors,
            "errors": report.error_count,
            "notes": report.note_count,
        },
        "violations": [e.to_dict() for e in report.errors],
        "text_report": MypyValidator.format_report_text(report)
    }


def combine_type_checks(
    reports: Dict[str, MypyReport]
) -> MypyReport:
    """
    Combine multiple Mypy reports into a single aggregate report.
    
    Args:
        reports (Dict[str, MypyReport]): Dictionary of file -> report
    
    Returns:
        MypyReport: Combined aggregate report
    """
    all_errors = []
    total_error_count = 0
    total_note_count = 0
    
    for file_name, report in reports.items():
        all_errors.extend(report.errors)
        total_error_count += report.error_count
        total_note_count += report.note_count
    
    return MypyReport(
        errors=all_errors,
        passed=total_error_count == 0,
        total_errors=len(all_errors),
        error_count=total_error_count,
        note_count=total_note_count,
        summary=f"Combined report: {total_error_count} errors, {total_note_count} notes",
        execution_time_ms=0
    )
