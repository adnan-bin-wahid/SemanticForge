"""
Constraint Checker Service

Orchestrates all static analysis validators (Basic Rules, Ruff, Mypy) to provide
comprehensive validation of generated patches.
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from pathlib import Path

from app.services.basic_rules_checker import BasicCheckReport
from app.services.ruff_validator import RuffReport
from app.services.mypy_validator import MypyReport
from app.services.temporary_environment import TemporaryEnvironmentService

logger = logging.getLogger(__name__)


@dataclass
class ConstraintCheckResult:
    """Represents the result from a single validation stage."""
    stage_name: str  # "syntax", "ruff", "mypy"
    passed: bool
    report_type: str  # "BasicCheckReport", "RuffReport", "MypyReport"
    error_count: int
    warning_count: int
    summary: str
    details: Dict  # Raw report data

    def to_dict(self) -> Dict:
        """Convert result to dictionary."""
        return asdict(self)


@dataclass
class AggregateConstraintReport:
    """
    Comprehensive constraint checking report combining all validation stages.
    
    This report aggregates results from:
    1. Basic Rules Checker (syntax validation)
    2. Ruff (code style and complexity)
    3. Mypy (type checking)
    """
    file_path: str
    passed: bool = False  # True only if all stages pass (default: False until verified)
    
    # Individual stage results
    basic_rules_result: Optional[ConstraintCheckResult] = None
    ruff_result: Optional[ConstraintCheckResult] = None
    mypy_result: Optional[ConstraintCheckResult] = None
    
    # Aggregate statistics
    total_errors: int = 0
    total_warnings: int = 0
    total_issues: int = 0
    
    # Stage tracking
    stages_run: List[str] = field(default_factory=list)
    stages_passed: List[str] = field(default_factory=list)
    stages_failed: List[str] = field(default_factory=list)
    
    # Summary
    summary: str = ""
    details: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert report to dictionary."""
        return {
            "file_path": self.file_path,
            "passed": self.passed,
            "basic_rules_result": self.basic_rules_result.to_dict() if self.basic_rules_result else None,
            "ruff_result": self.ruff_result.to_dict() if self.ruff_result else None,
            "mypy_result": self.mypy_result.to_dict() if self.mypy_result else None,
            "total_errors": self.total_errors,
            "total_warnings": self.total_warnings,
            "total_issues": self.total_issues,
            "stages_run": self.stages_run,
            "stages_passed": self.stages_passed,
            "stages_failed": self.stages_failed,
            "summary": self.summary,
        }


class ConstraintChecker:
    """
    Service that orchestrates all static analysis validators.
    
    Validation Pipeline Order:
    1. Basic Rules Checker (syntax) - fastest, catches fundamental errors
    2. Ruff (linting) - medium speed, code style/complexity
    3. Mypy (type checking) - slowest, type safety
    
    This ordering ensures fast feedback for broken code and expensive checks
    only run on syntactically valid code.
    """

    @staticmethod
    def check_patch(
        original_file_path: str,
        file_relative_path: str,
        generated_code: str,
        ruff_config: Optional[str] = None,
        mypy_config: Optional[str] = None,
        mypy_strict: bool = False,
        continue_on_errors: bool = False
    ) -> Tuple[AggregateConstraintReport, str]:
        """
        Perform comprehensive constraint checking on a generated patch.
        
        This method:
        1. Creates a temporary sandbox with the patched file
        2. Runs all validators in sequence (basic → ruff → mypy)
        3. Aggregates results into a comprehensive report
        4. Cleans up the sandbox
        
        Args:
            original_file_path (str): Path to the original file
            file_relative_path (str): Relative path for sandbox (e.g., "src/utils/helpers.py")
            generated_code (str): The generated/patched code
            ruff_config (Optional[str]): Path to Ruff config file
            mypy_config (Optional[str]): Path to Mypy config file
            mypy_strict (bool): Enable Mypy strict mode
            continue_on_errors (bool): If False, stop at first failure. If True, run all checks.
        
        Returns:
            Tuple[AggregateConstraintReport, str]:
                - report: Comprehensive validation report
                - temp_dir: Path to temporary directory (for debugging)
        
        Example:
            >>> report, temp_dir = ConstraintChecker.check_patch(
            ...     "/path/to/original.py",
            ...     "src/helpers.py",
            ...     "def new_func():\n    return 42\n"
            ... )
            >>> if report.passed:
            ...     print("✓ All validation passed!")
            ... else:
            ...     print(f"✗ Found issues: {report.total_errors} errors, {report.total_warnings} warnings")
        """
        temp_env = TemporaryEnvironmentService()
        temp_dir = None
        
        try:
            # PHASE 6.1: Create sandbox with patched file
            logger.info(f"[PHASE 6.1] Starting validation pipeline for: {file_relative_path}")
            logger.info(f"[PHASE 6.1] Original file path: {original_file_path}")
            logger.info(f"[PHASE 6.1] Creating temporary sandbox environment...")
            
            temp_dir, temp_file_path = temp_env.create_sandbox_for_patch(
                original_file_path,
                file_relative_path,
                generated_code
            )
            logger.info(f"[PHASE 6.1] Sandbox created at: {temp_dir}")
            logger.info(f"[PHASE 6.1] Patched file copied to: {temp_file_path}")
            
            # Initialize aggregate report
            report = AggregateConstraintReport(file_path=file_relative_path)
            
            # PHASE 6.4: Basic Rules Checker (syntax validation)
            logger.info(f"[PHASE 6.4] Starting basic syntax rules check...")
            basic_result = ConstraintChecker._run_basic_rules_check(temp_file_path)
            report.basic_rules_result = basic_result
            report.stages_run.append("basic_rules")
            if basic_result.passed:
                report.stages_passed.append("basic_rules")
                logger.info(f"[PHASE 6.4] ✓ Basic rules PASSED (0 errors, {basic_result.warning_count} warnings)")
            else:
                report.stages_failed.append("basic_rules")
                logger.warning(f"[PHASE 6.4] ✗ Basic rules FAILED ({basic_result.error_count} errors, {basic_result.warning_count} warnings)")
                logger.warning(f"[PHASE 6.4] Summary: {basic_result.summary}")
            
            # If basic rules failed and we're not continuing, finalize report
            if not basic_result.passed and not continue_on_errors:
                logger.info(f"[PHASE 6.4] Stopping validation - basic rules failed and continue_on_errors=False")
                ConstraintChecker._finalize_report(report)
                return report, temp_dir
            
            # PHASE 6.2: Ruff (linting)
            logger.info(f"[PHASE 6.2] Starting Ruff code linting check...")
            ruff_result = ConstraintChecker._run_ruff_check(
                temp_file_path,
                ruff_config
            )
            report.ruff_result = ruff_result
            report.stages_run.append("ruff")
            if ruff_result.passed:
                report.stages_passed.append("ruff")
                logger.info(f"[PHASE 6.2] ✓ Ruff linting PASSED (0 errors, {ruff_result.warning_count} warnings)")
            else:
                report.stages_failed.append("ruff")
                logger.warning(f"[PHASE 6.2] ✗ Ruff linting FAILED ({ruff_result.error_count} errors, {ruff_result.warning_count} warnings)")
                logger.warning(f"[PHASE 6.2] Summary: {ruff_result.summary}")
            
            # If Ruff failed and we're not continuing, finalize report
            if not ruff_result.passed and not continue_on_errors:
                logger.info(f"[PHASE 6.2] Stopping validation - Ruff failed and continue_on_errors=False")
                ConstraintChecker._finalize_report(report)
                return report, temp_dir
            
            # PHASE 6.3: Mypy (type checking)
            logger.info(f"[PHASE 6.3] Starting Mypy type checking...")
            mypy_result = ConstraintChecker._run_mypy_check(
                temp_file_path,
                mypy_config,
                mypy_strict
            )
            report.mypy_result = mypy_result
            report.stages_run.append("mypy")
            if mypy_result.passed:
                report.stages_passed.append("mypy")
                logger.info(f"[PHASE 6.3] ✓ Mypy type check PASSED (0 errors, {mypy_result.warning_count} warnings)")
            else:
                report.stages_failed.append("mypy")
                logger.warning(f"[PHASE 6.3] ✗ Mypy type check FAILED ({mypy_result.error_count} errors, {mypy_result.warning_count} warnings)")
                logger.warning(f"[PHASE 6.3] Summary: {mypy_result.summary}")
            
            # PHASE 6.5: Finalize aggregated report (Constraint Checker Orchestration)
            logger.info(f"[PHASE 6.5] Finalizing constraint checker report...")
            ConstraintChecker._finalize_report(report)
            
            if report.passed:
                logger.info(f"[PHASE 6.5] ✓ OVERALL VALIDATION PASSED - All checks successful")
                logger.info(f"[PHASE 6.5] Stages passed: {', '.join(report.stages_passed)}")
            else:
                logger.warning(f"[PHASE 6.5] ✗ OVERALL VALIDATION FAILED")
                logger.warning(f"[PHASE 6.5] Stages passed: {', '.join(report.stages_passed)}")
                logger.warning(f"[PHASE 6.5] Stages failed: {', '.join(report.stages_failed)}")
                logger.warning(f"[PHASE 6.5] Total issues: {report.total_errors} errors, {report.total_warnings} warnings")
            
            logger.info(f"[PHASE 6.5] Report summary: {report.summary}")
            
            return report, temp_dir
            
        except Exception as e:
            logger.error(f"[PHASE 6.5] Validation pipeline error: {str(e)}", exc_info=True)
            raise
        finally:
            # Cleanup
            if temp_dir:
                logger.info(f"[PHASE 6.1] Cleaning up temporary sandbox: {temp_dir}")
                temp_env.cleanup_all_sandboxes()

    @staticmethod
    def check_patch_from_content(
        file_relative_path: str,
        original_content: str,
        generated_code: str,
        ruff_config: Optional[str] = None,
        mypy_config: Optional[str] = None,
        mypy_strict: bool = False,
        continue_on_errors: bool = False
    ) -> Tuple[AggregateConstraintReport, str]:
        """
        Perform comprehensive constraint checking on a generated patch using content.
        
        This method is similar to check_patch but doesn't require file system access.
        Instead, it uses the provided original_content directly.
        
        This is the preferred method for API-based validation where the client
        already has the file content.
        
        Args:
            file_relative_path (str): Relative path for sandbox (e.g., "src/utils/helpers.py")
            original_content (str): Original file content
            generated_code (str): The generated/patched code
            ruff_config (Optional[str]): Path to Ruff config file
            mypy_config (Optional[str]): Path to Mypy config file
            mypy_strict (bool): Enable Mypy strict mode
            continue_on_errors (bool): If False, stop at first failure. If True, run all checks.
        
        Returns:
            Tuple[AggregateConstraintReport, str]:
                - report: Comprehensive validation report
                - temp_dir: Path to temporary directory (for debugging)
        
        Example:
            >>> report, temp_dir = ConstraintChecker.check_patch_from_content(
            ...     "src/helpers.py",
            ...     "def old_func():\n    pass\n",
            ...     "def new_func():\n    return 42\n"
            ... )
            >>> if report.passed:
            ...     print("✓ All validation passed!")
        """
        temp_env = TemporaryEnvironmentService()
        temp_dir = None
        
        try:
            # PHASE 6.1: Create sandbox with patched file from content
            logger.info(f"[PHASE 6.1] Starting validation pipeline for: {file_relative_path}")
            logger.info(f"[PHASE 6.1] Using content-based validation (no file system access needed)")
            logger.info(f"[PHASE 6.1] Creating temporary sandbox environment...")
            
            temp_dir, temp_file_path = temp_env.create_sandbox_for_patch_from_content(
                file_relative_path,
                original_content,
                generated_code
            )
            logger.info(f"[PHASE 6.1] Sandbox created at: {temp_dir}")
            logger.info(f"[PHASE 6.1] Patched file written to: {temp_file_path}")
            
            # Initialize aggregate report
            report = AggregateConstraintReport(file_path=file_relative_path)
            
            # PHASE 6.4: Basic Rules Checker (syntax validation)
            logger.info(f"[PHASE 6.4] Starting basic syntax rules check...")
            basic_result = ConstraintChecker._run_basic_rules_check(temp_file_path)
            report.basic_rules_result = basic_result
            report.stages_run.append("basic_rules")
            if basic_result.passed:
                report.stages_passed.append("basic_rules")
                logger.info(f"[PHASE 6.4] ✓ Basic rules PASSED (0 errors, {basic_result.warning_count} warnings)")
            else:
                report.stages_failed.append("basic_rules")
                logger.warning(f"[PHASE 6.4] ✗ Basic rules FAILED ({basic_result.error_count} errors, {basic_result.warning_count} warnings)")
                logger.warning(f"[PHASE 6.4] Summary: {basic_result.summary}")
            
            # If basic rules failed and we're not continuing, finalize report
            if not basic_result.passed and not continue_on_errors:
                logger.info(f"[PHASE 6.4] Stopping validation - basic rules failed and continue_on_errors=False")
                ConstraintChecker._finalize_report(report)
                return report, temp_dir
            
            # PHASE 6.2: Ruff (linting)
            logger.info(f"[PHASE 6.2] Starting Ruff code linting check...")
            ruff_result = ConstraintChecker._run_ruff_check(
                temp_file_path,
                ruff_config
            )
            report.ruff_result = ruff_result
            report.stages_run.append("ruff")
            if ruff_result.passed:
                report.stages_passed.append("ruff")
                logger.info(f"[PHASE 6.2] ✓ Ruff linting PASSED (0 errors, {ruff_result.warning_count} warnings)")
            else:
                report.stages_failed.append("ruff")
                logger.warning(f"[PHASE 6.2] ✗ Ruff linting FAILED ({ruff_result.error_count} errors, {ruff_result.warning_count} warnings)")
                logger.warning(f"[PHASE 6.2] Summary: {ruff_result.summary}")
            
            # If Ruff failed and we're not continuing, finalize report
            if not ruff_result.passed and not continue_on_errors:
                logger.info(f"[PHASE 6.2] Stopping validation - Ruff failed and continue_on_errors=False")
                ConstraintChecker._finalize_report(report)
                return report, temp_dir
            
            # PHASE 6.3: Mypy (type checking)
            logger.info(f"[PHASE 6.3] Starting Mypy type checking...")
            mypy_result = ConstraintChecker._run_mypy_check(
                temp_file_path,
                mypy_config,
                mypy_strict
            )
            report.mypy_result = mypy_result
            report.stages_run.append("mypy")
            if mypy_result.passed:
                report.stages_passed.append("mypy")
                logger.info(f"[PHASE 6.3] ✓ Mypy type check PASSED (0 errors, {mypy_result.warning_count} warnings)")
            else:
                report.stages_failed.append("mypy")
                logger.warning(f"[PHASE 6.3] ✗ Mypy type check FAILED ({mypy_result.error_count} errors, {mypy_result.warning_count} warnings)")
                logger.warning(f"[PHASE 6.3] Summary: {mypy_result.summary}")
            
            # PHASE 6.5: Finalize aggregated report (Constraint Checker Orchestration)
            logger.info(f"[PHASE 6.5] Finalizing constraint checker report...")
            ConstraintChecker._finalize_report(report)
            
            if report.passed:
                logger.info(f"[PHASE 6.5] ✓ OVERALL VALIDATION PASSED - All checks successful")
                logger.info(f"[PHASE 6.5] Stages passed: {', '.join(report.stages_passed)}")
            else:
                logger.warning(f"[PHASE 6.5] ✗ OVERALL VALIDATION FAILED")
                logger.warning(f"[PHASE 6.5] Stages passed: {', '.join(report.stages_passed)}")
                logger.warning(f"[PHASE 6.5] Stages failed: {', '.join(report.stages_failed)}")
                logger.warning(f"[PHASE 6.5] Total issues: {report.total_errors} errors, {report.total_warnings} warnings")
            
            logger.info(f"[PHASE 6.5] Report summary: {report.summary}")
            
            return report, temp_dir
            
        except Exception as e:
            logger.error(f"[PHASE 6.5] Validation pipeline error: {str(e)}", exc_info=True)
            raise
        finally:
            # Cleanup
            if temp_dir:
                logger.info(f"[PHASE 6.1] Cleaning up temporary sandbox: {temp_dir}")
                temp_env.cleanup_all_sandboxes()

    @staticmethod
    def _run_basic_rules_check(temp_file_path: str) -> ConstraintCheckResult:
        """
        Run basic rules (syntax) check on a file.
        
        Args:
            temp_file_path (str): Path to the file to check
        
        Returns:
            ConstraintCheckResult: Result from basic rules checker
        """
        try:
            from app.services.basic_rules_checker import BasicRulesChecker
            
            basic_report = BasicRulesChecker.check_file(temp_file_path)
            
            result = ConstraintCheckResult(
                stage_name="basic_rules",
                passed=basic_report.passed,
                report_type="BasicCheckReport",
                error_count=basic_report.error_count,
                warning_count=basic_report.warning_count,
                summary=BasicRulesChecker.get_quick_summary(basic_report),
                details=basic_report.to_dict()
            )
            return result
            
        except Exception as e:
            # If checker itself fails, treat as error
            result = ConstraintCheckResult(
                stage_name="basic_rules",
                passed=False,
                report_type="BasicCheckReport",
                error_count=1,
                warning_count=0,
                summary=f"Basic rules checker failed: {str(e)}",
                details={"error": str(e)}
            )
            return result

    @staticmethod
    def _run_ruff_check(temp_file_path: str, config_path: Optional[str] = None) -> ConstraintCheckResult:
        """
        Run Ruff linting check on a file.
        
        Args:
            temp_file_path (str): Path to the file to check
            config_path (Optional[str]): Path to Ruff config file
        
        Returns:
            ConstraintCheckResult: Result from Ruff validator
        """
        try:
            from app.services.ruff_validator import RuffValidator
            
            validator = RuffValidator()
            ruff_report = validator.lint_file(temp_file_path, config_path=config_path)
            
            result = ConstraintCheckResult(
                stage_name="ruff",
                passed=ruff_report.passed,
                report_type="RuffReport",
                error_count=ruff_report.error_count,
                warning_count=ruff_report.warning_count,
                summary=RuffValidator.format_report_text(ruff_report),
                details=asdict(ruff_report)
            )
            return result
            
        except Exception as e:
            result = ConstraintCheckResult(
                stage_name="ruff",
                passed=False,
                report_type="RuffReport",
                error_count=1,
                warning_count=0,
                summary=f"Ruff check failed: {str(e)}",
                details={"error": str(e)}
            )
            return result

    @staticmethod
    def _run_mypy_check(
        temp_file_path: str,
        config_path: Optional[str] = None,
        strict: bool = False
    ) -> ConstraintCheckResult:
        """
        Run Mypy type checking on a file.
        
        Args:
            temp_file_path (str): Path to the file to check
            config_path (Optional[str]): Path to Mypy config file
            strict (bool): Enable strict mode
        
        Returns:
            ConstraintCheckResult: Result from Mypy validator
        """
        try:
            from app.services.mypy_validator import MypyValidator
            
            validator = MypyValidator()
            mypy_report = validator.check_file(temp_file_path, config_path=config_path, strict=strict)
            
            result = ConstraintCheckResult(
                stage_name="mypy",
                passed=mypy_report.passed,
                report_type="MypyReport",
                error_count=mypy_report.error_count,
                warning_count=mypy_report.note_count,
                summary=MypyValidator.get_quick_summary(mypy_report),
                details=asdict(mypy_report)
            )
            return result
            
        except Exception as e:
            result = ConstraintCheckResult(
                stage_name="mypy",
                passed=False,
                report_type="MypyReport",
                error_count=1,
                warning_count=0,
                summary=f"Mypy check failed: {str(e)}",
                details={"error": str(e)}
            )
            return result

    @staticmethod
    def _finalize_report(report: AggregateConstraintReport) -> None:
        """
        Aggregate statistics and generate summary for the report.
        
        Args:
            report (AggregateConstraintReport): Report to finalize
        """
        # Aggregate statistics
        total_errors = 0
        total_warnings = 0
        
        if report.basic_rules_result:
            total_errors += report.basic_rules_result.error_count
            total_warnings += report.basic_rules_result.warning_count
        
        if report.ruff_result:
            total_errors += report.ruff_result.error_count
            total_warnings += report.ruff_result.warning_count
        
        if report.mypy_result:
            total_errors += report.mypy_result.error_count
            total_warnings += report.mypy_result.warning_count
        
        report.total_errors = total_errors
        report.total_warnings = total_warnings
        report.total_issues = total_errors + total_warnings
        report.passed = len(report.stages_failed) == 0
        
        # Generate summary
        if report.passed:
            stages_info = f"{len(report.stages_passed)} stages"
            report.summary = f"✓ All constraint checks passed ({stages_info})"
        else:
            failed_stages = ", ".join(report.stages_failed)
            report.summary = (
                f"✗ Constraint checks failed: {failed_stages} "
                f"({report.total_errors} errors, {report.total_warnings} warnings)"
            )

    @staticmethod
    def format_full_report(report: AggregateConstraintReport) -> str:
        """
        Format the aggregate constraint report as human-readable text.
        
        Args:
            report (AggregateConstraintReport): The report to format
        
        Returns:
            str: Formatted text report
        """
        lines = []
        lines.append("=" * 80)
        lines.append("AGGREGATE CONSTRAINT CHECKING REPORT")
        lines.append("=" * 80)
        lines.append("")
        
        # Overall status
        status = "✓ PASSED" if report.passed else "✗ FAILED"
        lines.append(f"Status: {status}")
        lines.append(f"File: {report.file_path}")
        lines.append("")
        
        # Summary statistics
        lines.append("Statistics:")
        lines.append(f"  Total Issues: {report.total_issues}")
        lines.append(f"  Errors:       {report.total_errors}")
        lines.append(f"  Warnings:     {report.total_warnings}")
        lines.append("")
        
        # Stages summary
        lines.append("Validation Stages:")
        lines.append(f"  Run:    {len(report.stages_run)} ({', '.join(report.stages_run)})")
        lines.append(f"  Passed: {len(report.stages_passed)} ({', '.join(report.stages_passed) if report.stages_passed else 'none'})")
        lines.append(f"  Failed: {len(report.stages_failed)} ({', '.join(report.stages_failed) if report.stages_failed else 'none'})")
        lines.append("")
        
        # Detailed results per stage
        if report.basic_rules_result:
            lines.append("─" * 80)
            lines.append("BASIC RULES CHECK (Syntax Validation)")
            lines.append("─" * 80)
            lines.append(f"Status: {'✓ PASSED' if report.basic_rules_result.passed else '✗ FAILED'}")
            lines.append(f"Errors: {report.basic_rules_result.error_count}")
            lines.append(f"Warnings: {report.basic_rules_result.warning_count}")
            lines.append("")
        
        if report.ruff_result:
            lines.append("─" * 80)
            lines.append("RUFF LINTING CHECK (Code Style & Complexity)")
            lines.append("─" * 80)
            lines.append(f"Status: {'✓ PASSED' if report.ruff_result.passed else '✗ FAILED'}")
            lines.append(f"Errors: {report.ruff_result.error_count}")
            lines.append(f"Warnings: {report.ruff_result.warning_count}")
            lines.append("")
        
        if report.mypy_result:
            lines.append("─" * 80)
            lines.append("MYPY TYPE CHECK (Type Safety)")
            lines.append("─" * 80)
            lines.append(f"Status: {'✓ PASSED' if report.mypy_result.passed else '✗ FAILED'}")
            lines.append(f"Errors: {report.mypy_result.error_count}")
            lines.append(f"Warnings: {report.mypy_result.warning_count}")
            lines.append("")
        
        lines.append("=" * 80)
        return "\n".join(lines)
