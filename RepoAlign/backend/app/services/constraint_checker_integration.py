"""
Constraint Checker Integration

High-level functions for integrating the ConstraintChecker service with the API layer.
"""

from typing import Dict, Tuple
from app.services.constraint_checker import ConstraintChecker, AggregateConstraintReport


def validate_patch_completely(
    original_file_path: str,
    file_relative_path: str,
    generated_code: str,
    ruff_config: str = None,
    mypy_config: str = None,
    mypy_strict: bool = False,
    continue_on_errors: bool = False
) -> Tuple[AggregateConstraintReport, str]:
    """
    Perform comprehensive validation of a generated patch.
    
    This is the primary integration point for the constraint checker. It runs:
    1. Basic syntax validation
    2. Ruff linting
    3. Mypy type checking
    
    Args:
        original_file_path (str): Path to the original file
        file_relative_path (str): Relative path in sandbox
        generated_code (str): The generated/patched code
        ruff_config (str): Optional path to Ruff config
        mypy_config (str): Optional path to Mypy config
        mypy_strict (bool): Enable Mypy strict mode
        continue_on_errors (bool): Run all checks even if one fails
    
    Returns:
        Tuple[AggregateConstraintReport, str]: (Report, temp_dir_path)
    
    Example:
        >>> report, temp_dir = validate_patch_completely(
        ...     "/path/to/original.py",
        ...     "src/helpers.py",
        ...     "def new_func():\n    return 42\n"
        ... )
        >>> print(f"Valid: {report.passed}")
    """
    return ConstraintChecker.check_patch(
        original_file_path,
        file_relative_path,
        generated_code,
        ruff_config=ruff_config,
        mypy_config=mypy_config,
        mypy_strict=mypy_strict,
        continue_on_errors=continue_on_errors
    )


def validate_patch_completely_from_content(
    file_relative_path: str,
    original_content: str,
    generated_code: str,
    ruff_config: str = None,
    mypy_config: str = None,
    mypy_strict: bool = False,
    continue_on_errors: bool = False
) -> Tuple[AggregateConstraintReport, str]:
    """
    Perform comprehensive validation of a generated patch using content (no file system access).
    
    This is the PREFERRED integration point for the API layer. It uses the file content
    that's already provided in the request, avoiding filesystem dependency.
    
    This is the recommended method for:
    - API-based code generation
    - Sandboxed environments
    - Stateless deployments
    - Production scenarios where repo filesystem may not be accessible
    
    Args:
        file_relative_path (str): Relative path in sandbox (e.g., "src/helpers.py")
        original_content (str): Original file content
        generated_code (str): The generated/patched code
        ruff_config (str): Optional path to Ruff config
        mypy_config (str): Optional path to Mypy config
        mypy_strict (bool): Enable Mypy strict mode
        continue_on_errors (bool): Run all checks even if one fails
    
    Returns:
        Tuple[AggregateConstraintReport, str]: (Report, temp_dir_path)
    
    Example:
        >>> report, temp_dir = validate_patch_completely_from_content(
        ...     "src/helpers.py",
        ...     "def old_func():\n    pass\n",
        ...     "def new_func():\n    return 42\n"
        ... )
        >>> print(f"Valid: {report.passed}")
    """
    return ConstraintChecker.check_patch_from_content(
        file_relative_path,
        original_content,
        generated_code,
        ruff_config=ruff_config,
        mypy_config=mypy_config,
        mypy_strict=mypy_strict,
        continue_on_errors=continue_on_errors
    )


def generate_validation_report(report: AggregateConstraintReport) -> Dict:
    """
    Generate an API-friendly summary of validation results.
    
    Args:
        report (AggregateConstraintReport): The constraint check report
    
    Returns:
        Dict: Structured validation report for API responses
    """
    return {
        "validation_type": "comprehensive_constraint_check",
        "status": "passed" if report.passed else "failed",
        "summary": report.summary,
        "file": report.file_path,
        "statistics": {
            "total_issues": report.total_issues,
            "errors": report.total_errors,
            "warnings": report.total_warnings,
        },
        "stages": {
            "run": report.stages_run,
            "passed": report.stages_passed,
            "failed": report.stages_failed,
        },
        "results": report.to_dict(),
        "text_report": ConstraintChecker.format_full_report(report)
    }


def generate_validation_summary(report: AggregateConstraintReport) -> Dict:
    """
    Generate a compact one-line summary of validation results.
    
    Args:
        report (AggregateConstraintReport): The constraint check report
    
    Returns:
        Dict: Compact summary suitable for quick display
    """
    return {
        "status": "passed" if report.passed else "failed",
        "summary": report.summary,
        "errors": report.total_errors,
        "warnings": report.total_warnings,
        "stages": {
            "passed": report.stages_passed,
            "failed": report.stages_failed,
        }
    }


def is_patch_valid(
    original_file_path: str,
    file_relative_path: str,
    generated_code: str,
    strict: bool = False
) -> bool:
    """
    Quick check to determine if a patch is valid across all constraints.
    
    Args:
        original_file_path (str): Path to original file
        file_relative_path (str): Relative path in sandbox
        generated_code (str): The generated/patched code
        strict (bool): If True, enable Mypy strict mode
    
    Returns:
        bool: True if patch passes all checks, False otherwise
    """
    report, _ = ConstraintChecker.check_patch(
        original_file_path,
        file_relative_path,
        generated_code,
        mypy_strict=strict,
        continue_on_errors=True  # Run all checks for comprehensive result
    )
    return report.passed


def get_validation_issues(
    original_file_path: str,
    file_relative_path: str,
    generated_code: str
) -> Dict[str, list]:
    """
    Get detailed list of all validation issues found in a patch.
    
    Args:
        original_file_path (str): Path to original file
        file_relative_path (str): Relative path in sandbox
        generated_code (str): The generated/patched code
    
    Returns:
        Dict[str, list]: Issues organized by stage
            {
                "syntax": [...],
                "style": [...],
                "types": [...]
            }
    """
    report, _ = ConstraintChecker.check_patch(
        original_file_path,
        file_relative_path,
        generated_code,
        continue_on_errors=True
    )
    
    issues = {
        "syntax": [],
        "style": [],
        "types": [],
    }
    
    # Extract issues from basic rules
    if report.basic_rules_result and report.basic_rules_result.details.get("issues"):
        issues["syntax"] = report.basic_rules_result.details.get("issues", [])
    
    # Extract issues from Ruff
    if report.ruff_result and report.ruff_result.details.get("violations"):
        issues["style"] = [
            {
                "line": v.get("line"),
                "column": v.get("column"),
                "code": v.get("code"),
                "message": v.get("message")
            }
            for v in report.ruff_result.details.get("violations", [])
        ]
    
    # Extract issues from Mypy
    if report.mypy_result and report.mypy_result.details.get("errors"):
        issues["types"] = [
            {
                "line": e.get("line"),
                "column": e.get("column"),
                "code": e.get("error_code"),
                "message": e.get("message")
            }
            for e in report.mypy_result.details.get("errors", [])
        ]
    
    return issues
