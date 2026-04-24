"""
Ruff Validation Integration Example

This module demonstrates how to use RuffValidator with TemporaryEnvironmentService
to validate patched code in a sandboxed environment.
"""

from typing import Dict, Tuple
from app.services.ruff_validator import RuffValidator, RuffReport
from app.services.temporary_environment import TemporaryEnvironmentService


def validate_patch_with_ruff(
    original_file_path: str,
    file_relative_path: str,
    generated_code: str
) -> Tuple[RuffReport, str]:
    """
    Validate a generated patch using Ruff linting.
    
    This high-level function:
    1. Creates a temporary sandbox with the patched file
    2. Runs Ruff on the patched file
    3. Cleans up the sandbox
    4. Returns the validation report
    
    Args:
        original_file_path (str): Path to original file
        file_relative_path (str): Relative path in sandbox (e.g., "src/utils/helpers.py")
        generated_code (str): The generated/patched code
    
    Returns:
        Tuple[RuffReport, str]:
            - report: RuffReport with validation results
            - temp_dir: Path to temporary directory (for debugging if needed)
    
    Example:
        >>> report, temp_dir = validate_patch_with_ruff(
        ...     "/path/to/original.py",
        ...     "src/helpers.py",
        ...     "def new_func():\n    pass\n"
        ... )
        >>> if report.passed:
        ...     print("✓ Code passed linting!")
        ... else:
        ...     print(f"✗ Found {report.error_count} errors")
    """
    temp_env = TemporaryEnvironmentService()
    
    try:
        # Create sandbox with patched file
        temp_dir, temp_file_path = temp_env.create_sandbox_for_patch(
            original_file_path,
            file_relative_path,
            generated_code
        )
        
        # Lint the patched file
        report = RuffValidator.lint_file(temp_file_path)
        
        return report, temp_dir
        
    finally:
        # Cleanup
        temp_env.cleanup_all_sandboxes()


def validate_repository_patch_with_ruff(
    repo_path: str,
    patches: Dict[str, str]
) -> Tuple[RuffReport, Dict[str, RuffReport], str]:
    """
    Validate multiple patches across a repository using Ruff.
    
    This function:
    1. Creates a sandbox copy of the repository
    2. Applies multiple patches to different files
    3. Runs Ruff on the entire repository
    4. Returns both aggregate and per-file reports
    
    Args:
        repo_path (str): Path to source repository
        patches (Dict[str, str]): Dictionary of {file_relative_path: generated_code}
    
    Returns:
        Tuple[RuffReport, Dict[str, RuffReport], str]:
            - aggregate_report: Combined report for all files
            - per_file_reports: Individual reports per file
            - temp_repo_path: Path to temporary repository copy
    
    Example:
        >>> patches = {
        ...     "src/utils.py": "def new_func():\n    pass\n",
        ...     "src/helpers.py": "def helper():\n    return 42\n"
        ... }
        >>> agg_report, per_file, temp_path = validate_repository_patch_with_ruff(
        ...     "/path/to/repo",
        ...     patches
        ... )
        >>> print(f"Total violations: {agg_report.total_violations}")
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
        
        # Lint entire repository
        aggregate_report, per_file_reports = RuffValidator.lint_directory(temp_repo_path)
        
        return aggregate_report, per_file_reports, temp_repo_path
        
    finally:
        # Cleanup
        temp_env.cleanup_all_sandboxes()


def generate_validation_summary(report: RuffReport) -> Dict:
    """
    Generate a summary of validation results suitable for API responses.
    
    Args:
        report (RuffReport): The validation report
    
    Returns:
        Dict: Structured summary of validation results
    """
    return {
        "validation_type": "ruff_linting",
        "status": "passed" if report.passed else "failed",
        "summary": {
            "total_violations": report.total_violations,
            "errors": report.error_count,
            "warnings": report.warning_count,
            "notes": report.note_count,
        },
        "violations": [v.to_dict() for v in report.violations],
        "text_report": RuffValidator.format_report_text(report)
    }
