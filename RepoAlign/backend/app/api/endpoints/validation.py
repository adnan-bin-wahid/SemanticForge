"""
Validation Endpoint

Provides comprehensive validation of generated patches through:
- Constraint checking (syntax, linting, type checking)
- Test execution
- Aggregated reporting
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
import os
from pathlib import Path

from app.services.constraint_checker_integration import (
    validate_patch_completely,
    generate_validation_report
)
from app.services.test_runner_integration import (
    run_tests_on_patch,
    generate_test_report
)

router = APIRouter()


class ValidatePatchRequest(BaseModel):
    """Request model for patch validation."""
    repo_path: str  # Path to source repository
    file_relative_path: str  # Relative path in repo (e.g., "src/utils.py")
    generated_code: str  # The generated/patched code
    run_tests: bool = True  # Whether to run tests (default True)
    test_directory: str = "tests"  # Path to tests relative to repo
    strict: bool = False  # Use strict mode for type checking
    timeout: int = 60  # Timeout for tests in seconds


class ValidationDetail(BaseModel):
    """Detail of validation stage result."""
    stage_name: str
    passed: bool
    error_count: int
    warning_count: int
    summary: str


class ValidatePatchResponse(BaseModel):
    """Response model for patch validation."""
    overall_status: str  # "passed" or "failed"
    overall_summary: str
    
    # Constraint checking results
    constraint_check: Optional[Dict] = None
    
    # Test execution results
    test_results: Optional[Dict] = None
    
    # Overall statistics
    total_issues: int
    total_errors: int
    total_warnings: int
    
    # All validation stages
    validation_stages: Dict[str, ValidationDetail]


@router.post("/validate-patch", response_model=ValidatePatchResponse, tags=["Validation"])
async def validate_patch(request: ValidatePatchRequest):
    """
    Validate a generated patch through comprehensive checks.
    
    This endpoint:
    1. Runs constraint checking (syntax, linting, type checking)
    2. Optionally runs test suite
    3. Aggregates all results
    4. Returns comprehensive validation report
    
    Args:
        request (ValidatePatchRequest): Patch validation request
            - repo_path: Source repository path
            - file_relative_path: File path relative to repo
            - generated_code: The patched code
            - run_tests: Whether to run tests
            - test_directory: Path to tests
            - strict: Strict type checking mode
            - timeout: Test timeout
    
    Returns:
        ValidatePatchResponse: Comprehensive validation report
        
    Raises:
        HTTPException: If validation fails or paths are invalid
        
    Example:
        POST /api/v1/validate-patch
        {
            "repo_path": "/path/to/repo",
            "file_relative_path": "src/utils.py",
            "generated_code": "def new_func():\n    return 42",
            "run_tests": true
        }
    """
    
    # Validate input paths
    if not Path(request.repo_path).exists():
        raise HTTPException(
            status_code=400,
            detail=f"Repository path not found: {request.repo_path}"
        )
    
    if not request.file_relative_path:
        raise HTTPException(
            status_code=400,
            detail="file_relative_path cannot be empty"
        )
    
    if not request.generated_code:
        raise HTTPException(
            status_code=400,
            detail="generated_code cannot be empty"
        )
    
    try:
        # Step 1: Run constraint checks (syntax, lint, types)
        constraint_report, temp_dir = validate_patch_completely(
            request.repo_path,
            request.file_relative_path,
            request.generated_code,
            mypy_strict=request.strict,
            continue_on_errors=True  # Run all checks even if some fail
        )
        
        constraint_api_report = generate_validation_report(constraint_report)
        
        # Step 2: Run tests if requested
        test_api_report = None
        if request.run_tests:
            test_report, _ = run_tests_on_patch(
                request.repo_path,
                {request.file_relative_path: request.generated_code},
                request.test_directory,
                timeout=request.timeout
            )
            test_api_report = generate_test_report(test_report)
        
        # Step 3: Aggregate results
        validation_stages = {}
        
        # Add constraint checking stages
        if constraint_report.basic_rules_result:
            validation_stages["syntax"] = ValidationDetail(
                stage_name="basic_rules",
                passed=constraint_report.basic_rules_result.passed,
                error_count=constraint_report.basic_rules_result.error_count,
                warning_count=constraint_report.basic_rules_result.warning_count,
                summary=constraint_report.basic_rules_result.summary
            )
        
        if constraint_report.ruff_result:
            validation_stages["linting"] = ValidationDetail(
                stage_name="ruff",
                passed=constraint_report.ruff_result.passed,
                error_count=constraint_report.ruff_result.error_count,
                warning_count=constraint_report.ruff_result.warning_count,
                summary=constraint_report.ruff_result.summary
            )
        
        if constraint_report.mypy_result:
            validation_stages["type_checking"] = ValidationDetail(
                stage_name="mypy",
                passed=constraint_report.mypy_result.passed,
                error_count=constraint_report.mypy_result.error_count,
                warning_count=constraint_report.mypy_result.warning_count,
                summary=constraint_report.mypy_result.summary
            )
        
        # Add test results stage if tests were run
        if test_api_report:
            validation_stages["tests"] = ValidationDetail(
                stage_name="test_execution",
                passed=test_api_report["status"] == "passed",
                error_count=test_api_report["statistics"]["errors"],
                warning_count=0,
                summary=test_api_report["summary"]
            )
        
        # Calculate overall statistics
        total_errors = constraint_report.total_errors
        total_warnings = constraint_report.total_warnings
        
        if test_api_report:
            total_errors += test_api_report["statistics"]["errors"]
            # Tests don't have warnings, but track failures
            total_errors += test_api_report["statistics"]["failed"]
        
        # Determine overall status
        overall_passed = (constraint_report.passed and 
                         (not request.run_tests or (test_api_report and test_api_report["status"] == "passed")))
        
        # Build response
        response = ValidatePatchResponse(
            overall_status="passed" if overall_passed else "failed",
            overall_summary=_build_overall_summary(
                constraint_report, test_api_report, overall_passed
            ),
            constraint_check=constraint_api_report,
            test_results=test_api_report,
            total_issues=total_errors + total_warnings,
            total_errors=total_errors,
            total_warnings=total_warnings,
            validation_stages=validation_stages
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Validation failed: {str(e)}"
        )


def _build_overall_summary(constraint_report, test_report, passed: bool) -> str:
    """Build a comprehensive summary message."""
    if passed:
        return "✓ All validation checks passed"
    
    issues = []
    
    if constraint_report.total_errors > 0:
        issues.append(f"{constraint_report.total_errors} static analysis error(s)")
    
    if constraint_report.total_warnings > 0:
        issues.append(f"{constraint_report.total_warnings} warning(s)")
    
    if test_report and test_report["status"] == "failed":
        issues.append(f"{test_report['statistics']['failed']} test failure(s)")
        if test_report['statistics']['errors'] > 0:
            issues.append(f"{test_report['statistics']['errors']} test error(s)")
    
    issue_str = ", ".join(issues) if issues else "unknown issues"
    return f"✗ Validation failed: {issue_str}"


@router.get("/validate-patch/help", tags=["Validation"])
async def validate_patch_help():
    """
    Get help documentation for the validate-patch endpoint.
    
    Returns usage examples and schema information.
    """
    return {
        "endpoint": "/api/v1/validate-patch",
        "method": "POST",
        "description": "Comprehensive patch validation through constraint checking and tests",
        "request_model": {
            "repo_path": "str - Path to source repository",
            "file_relative_path": "str - Relative path in repo (e.g., 'src/utils.py')",
            "generated_code": "str - The generated/patched code",
            "run_tests": "bool - Whether to run tests (default: true)",
            "test_directory": "str - Path to tests (default: 'tests')",
            "strict": "bool - Use strict type checking (default: false)",
            "timeout": "int - Test timeout in seconds (default: 60)"
        },
        "response_model": {
            "overall_status": "str - 'passed' or 'failed'",
            "overall_summary": "str - Human-readable summary",
            "constraint_check": "object - Constraint checking results",
            "test_results": "object - Test execution results (if run_tests=true)",
            "total_issues": "int - Total issues found",
            "total_errors": "int - Total errors",
            "total_warnings": "int - Total warnings",
            "validation_stages": "object - Per-stage validation results"
        },
        "validation_stages": {
            "syntax": "Basic syntax validation",
            "linting": "Code style and quality (Ruff)",
            "type_checking": "Type checking (Mypy)",
            "tests": "Test suite execution (pytest)"
        },
        "example_request": {
            "repo_path": "/path/to/repo",
            "file_relative_path": "src/helpers.py",
            "generated_code": "def new_function(x: int) -> int:\n    return x * 2",
            "run_tests": True,
            "test_directory": "tests",
            "strict": False,
            "timeout": 60
        }
    }
