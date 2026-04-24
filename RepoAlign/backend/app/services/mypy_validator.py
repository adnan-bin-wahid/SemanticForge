"""
Mypy Type Checker Integration

This module integrates Mypy (a static type checker for Python) to validate
the type correctness of patched code. It runs Mypy as a subprocess and
captures all type violations.
"""

import subprocess
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class TypeCheckError:
    """Represents a single type checking error found by Mypy."""
    file: str
    line: int
    column: int
    error_code: str  # e.g., "error", "note"
    message: str
    category: str  # e.g., "no-redef", "assignment", "return-value", etc.

    def to_dict(self) -> Dict:
        """Convert error to dictionary."""
        return asdict(self)


@dataclass
class MypyReport:
    """Represents the complete Mypy type checking report."""
    errors: List[TypeCheckError]
    passed: bool
    total_errors: int
    error_count: int
    note_count: int
    summary: str  # Summary line from mypy output
    execution_time_ms: float

    def to_dict(self) -> Dict:
        """Convert report to dictionary."""
        return {
            "errors": [e.to_dict() for e in self.errors],
            "passed": self.passed,
            "total_errors": self.total_errors,
            "error_count": self.error_count,
            "note_count": self.note_count,
            "summary": self.summary,
            "execution_time_ms": self.execution_time_ms,
        }


class MypyValidator:
    """
    Runs Mypy type checker on Python files and captures type violations.
    
    This validator:
    - Runs Mypy on individual files or directories
    - Parses Mypy output to extract type errors
    - Classifies errors by type (error, note, etc.)
    - Returns structured validation reports
    """

    # Mypy error code patterns
    ERROR_CODE_PATTERNS = {
        "error": r"error:",
        "note": r"note:",
        "warning": r"warning:",
    }

    @staticmethod
    def _extract_error_code(message: str) -> str:
        """
        Extract error category from Mypy message.
        
        Args:
            message (str): Mypy error message
        
        Returns:
            str: Error category (e.g., "assignment", "return-value", "no-redef")
        """
        # Try to extract code from square brackets
        match = re.search(r'\[([a-z\-]+)\]', message)
        if match:
            return match.group(1)
        
        # Try to extract from message patterns
        if "Incompatible types in assignment" in message:
            return "assignment"
        elif "Return type" in message:
            return "return-value"
        elif "already defined" in message:
            return "no-redef"
        elif "is not defined" in message:
            return "name-defined"
        elif "Argument" in message:
            return "call-arg"
        else:
            return "unknown"

    @staticmethod
    def check_file(
        file_path: str,
        config_path: Optional[str] = None,
        timeout: int = 30,
        strict: bool = False
    ) -> MypyReport:
        """
        Type-check a single Python file with Mypy.
        
        Args:
            file_path (str): Path to the Python file to check
            config_path (Optional[str]): Path to mypy.ini or setup.cfg
            timeout (int): Subprocess timeout in seconds (default: 30)
            strict (bool): Enable strict mode (default: False)
        
        Returns:
            MypyReport: Complete type checking report
            
        Raises:
            FileNotFoundError: If file doesn't exist
            subprocess.TimeoutExpired: If checking times out
            RuntimeError: If mypy is not installed or fails to run
        """
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            # Build mypy command
            cmd = ["mypy", file_path, "--show-column-numbers"]
            
            if config_path:
                cmd.extend(["--config-file", config_path])
            
            if strict:
                cmd.append("--strict")

            # Run mypy
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            # Parse output
            errors = MypyValidator._parse_mypy_output(result.stdout, file_path)

            # Extract summary from stderr or stdout
            summary = ""
            output_lines = (result.stdout + result.stderr).strip().split('\n')
            for line in output_lines:
                if "error:" in line or "success:" in line or "errors" in line:
                    summary = line

            # Count errors and notes
            error_count = sum(1 for e in errors if e.error_code == "error")
            note_count = sum(1 for e in errors if e.error_code == "note")

            # Determine pass/fail
            passed = error_count == 0

            report = MypyReport(
                errors=errors,
                passed=passed,
                total_errors=len(errors),
                error_count=error_count,
                note_count=note_count,
                summary=summary,
                execution_time_ms=0
            )

            return report

        except FileNotFoundError:
            raise RuntimeError(
                "Mypy is not installed or not found in PATH. "
                "Please install it with: pip install mypy"
            )
        except subprocess.TimeoutExpired:
            raise subprocess.TimeoutExpired(
                cmd="mypy",
                timeout=timeout,
                output="Mypy type checking exceeded timeout"
            )

    @staticmethod
    def check_directory(
        directory_path: str,
        config_path: Optional[str] = None,
        timeout: int = 60,
        strict: bool = False,
        ignore_patterns: Optional[List[str]] = None
    ) -> Tuple[MypyReport, Dict[str, MypyReport]]:
        """
        Type-check all Python files in a directory.
        
        Args:
            directory_path (str): Path to directory to check
            config_path (Optional[str]): Path to mypy configuration file
            timeout (int): Subprocess timeout in seconds (default: 60)
            strict (bool): Enable strict mode
            ignore_patterns (Optional[List[str]]): Patterns to exclude
        
        Returns:
            Tuple[MypyReport, Dict[str, MypyReport]]:
                - aggregate_report: Combined report for all files
                - per_file_reports: Individual reports per file
        """
        directory_path_obj = Path(directory_path)
        if not directory_path_obj.is_dir():
            raise FileNotFoundError(f"Directory not found: {directory_path}")

        try:
            # Build mypy command for entire directory
            cmd = ["mypy", directory_path, "--show-column-numbers"]
            
            if config_path:
                cmd.extend(["--config-file", config_path])
            
            if strict:
                cmd.append("--strict")

            # Add exclude patterns
            if ignore_patterns:
                for pattern in ignore_patterns:
                    cmd.extend(["--exclude", pattern])

            # Run mypy
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            # Parse output
            all_errors = MypyValidator._parse_mypy_output(
                result.stdout + result.stderr,
                directory_path
            )

            # Group by file
            by_file = {}
            for error in all_errors:
                if error.file not in by_file:
                    by_file[error.file] = []
                by_file[error.file].append(error)

            # Create per-file reports
            per_file_reports = {}
            for file_name, file_errors in by_file.items():
                error_count = sum(1 for e in file_errors if e.error_code == "error")
                note_count = sum(1 for e in file_errors if e.error_code == "note")
                
                per_file_reports[file_name] = MypyReport(
                    errors=file_errors,
                    passed=error_count == 0,
                    total_errors=len(file_errors),
                    error_count=error_count,
                    note_count=note_count,
                    summary="",
                    execution_time_ms=0
                )

            # Create aggregate report
            error_count = sum(1 for e in all_errors if e.error_code == "error")
            note_count = sum(1 for e in all_errors if e.error_code == "note")

            # Extract summary
            summary = ""
            for line in (result.stdout + result.stderr).split('\n'):
                if "error:" in line or "success:" in line:
                    summary = line
                    break

            aggregate_report = MypyReport(
                errors=all_errors,
                passed=error_count == 0,
                total_errors=len(all_errors),
                error_count=error_count,
                note_count=note_count,
                summary=summary,
                execution_time_ms=0
            )

            return aggregate_report, per_file_reports

        except FileNotFoundError:
            raise RuntimeError(
                "Mypy is not installed or not found in PATH. "
                "Please install it with: pip install mypy"
            )
        except subprocess.TimeoutExpired:
            raise subprocess.TimeoutExpired(
                cmd="mypy",
                timeout=timeout,
                output="Mypy type checking exceeded timeout"
            )

    @staticmethod
    def _parse_mypy_output(output: str, default_file: str) -> List[TypeCheckError]:
        """
        Parse Mypy output and extract type errors.
        
        Expected format:
        filename:line:column: error: error message [error-code]
        
        Args:
            output (str): Mypy output text
            default_file (str): Default file path if not in output
        
        Returns:
            List[TypeCheckError]: Parsed type errors
        """
        errors = []
        
        # Pattern to match mypy output lines
        # Format: file:line:column: error: message [code]
        pattern = r"(.+?):(\d+):(\d+):\s+(\w+):\s+(.+?)(?:\s+\[([a-z\-]+)\])?"

        for line in output.strip().split('\n'):
            if not line or "==" in line or "Success:" in line:
                continue
            
            match = re.match(pattern, line)
            if match:
                file_part, line_num, col_num, error_type, message, code = match.groups()
                
                error = TypeCheckError(
                    file=file_part or default_file,
                    line=int(line_num),
                    column=int(col_num),
                    error_code=error_type.lower(),
                    message=message.strip() if message else "",
                    category=code or MypyValidator._extract_error_code(message or "")
                )
                errors.append(error)

        return errors

    @staticmethod
    def format_report_text(report: MypyReport) -> str:
        """
        Format a MypyReport as human-readable text.
        
        Args:
            report (MypyReport): The report to format
        
        Returns:
            str: Formatted text report
        """
        lines = []
        lines.append("=" * 70)
        lines.append("MYPY TYPE CHECKING REPORT")
        lines.append("=" * 70)
        
        if report.passed:
            lines.append("✓ PASSED: No type checking errors found")
        else:
            lines.append("✗ FAILED: Type checking errors detected")
        
        lines.append("")
        lines.append(f"Total Errors: {report.total_errors}")
        lines.append(f"  Errors: {report.error_count}")
        lines.append(f"  Notes:  {report.note_count}")
        
        if report.summary:
            lines.append(f"\nSummary: {report.summary}")
        
        lines.append("")

        if report.errors:
            lines.append("Type Errors:")
            lines.append("-" * 70)
            for error in report.errors:
                severity_marker = "✗" if error.error_code == "error" else "ℹ"
                lines.append(
                    f"{severity_marker} [{error.category}] {error.file}:{error.line}:{error.column}"
                )
                lines.append(f"   {error.message}")
        
        lines.append("=" * 70)
        return "\n".join(lines)

    @staticmethod
    def get_quick_summary(report: MypyReport) -> str:
        """
        Get a one-line summary of the type checking report.
        
        Args:
            report (MypyReport): The report to summarize
        
        Returns:
            str: One-line summary
        """
        if report.passed:
            return f"✓ Type check passed ({report.total_errors} issues found)"
        else:
            return (
                f"✗ Type check failed: {report.error_count} error(s), "
                f"{report.note_count} note(s)"
            )
