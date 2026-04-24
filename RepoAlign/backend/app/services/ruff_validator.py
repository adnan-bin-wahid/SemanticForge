"""
Ruff Linting Validator

This module integrates Ruff (a fast Python linter) to validate patched code.
It runs Ruff as a subprocess on Python files and captures all linting violations.
"""

import subprocess
import json
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class RuffViolation:
    """Represents a single linting violation found by Ruff."""
    file: str
    line: int
    column: int
    code: str
    message: str
    severity: str  # "error", "warning", "note"

    def to_dict(self) -> Dict:
        """Convert violation to dictionary."""
        return asdict(self)


@dataclass
class RuffReport:
    """Represents the complete Ruff linting report."""
    violations: List[RuffViolation]
    passed: bool
    total_violations: int
    error_count: int
    warning_count: int
    note_count: int
    execution_time_ms: float

    def to_dict(self) -> Dict:
        """Convert report to dictionary."""
        return {
            "violations": [v.to_dict() for v in self.violations],
            "passed": self.passed,
            "total_violations": self.total_violations,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "note_count": self.note_count,
            "execution_time_ms": self.execution_time_ms,
        }


class RuffValidator:
    """
    Runs Ruff linter on Python files and captures violations.
    
    This validator:
    - Runs Ruff on individual files or directories
    - Parses Ruff output to extract violations
    - Classifies violations by severity
    - Returns structured validation reports
    """

    # Ruff rule severity mapping (based on common conventions)
    RULE_SEVERITY = {
        # Error rules (E)
        "E": "error",
        # Warning rules (W)
        "W": "warning",
        # Info/style rules (others)
    }

    @staticmethod
    def _get_rule_severity(rule_code: str) -> str:
        """
        Determine severity level based on rule code.
        
        Args:
            rule_code (str): Ruff rule code (e.g., "E501", "W292")
        
        Returns:
            str: Severity level ("error", "warning", or "note")
        """
        if not rule_code:
            return "note"
        
        prefix = rule_code[0]
        
        if prefix == "E":
            return "error"
        elif prefix == "W":
            return "warning"
        elif prefix in ["F", "N", "D", "C", "B", "S"]:
            return "warning"
        else:
            return "note"

    @staticmethod
    def lint_file(
        file_path: str,
        config_path: Optional[str] = None,
        timeout: int = 30
    ) -> RuffReport:
        """
        Lint a single Python file with Ruff.
        
        Args:
            file_path (str): Path to the Python file to lint
            config_path (Optional[str]): Path to Ruff config file (pyproject.toml, etc.)
            timeout (int): Subprocess timeout in seconds (default: 30)
        
        Returns:
            RuffReport: Complete linting report
            
        Raises:
            FileNotFoundError: If file doesn't exist
            subprocess.TimeoutExpired: If linting times out
            RuntimeError: If ruff is not installed or fails to run
        """
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            # Build ruff command
            cmd = ["ruff", "check", file_path, "--output-format", "json"]
            
            if config_path:
                cmd.extend(["--config", config_path])

            # Run ruff
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            # Parse violations from JSON output
            violations = []
            if result.stdout:
                try:
                    violations_data = json.loads(result.stdout)
                    if isinstance(violations_data, list):
                        for item in violations_data:
                            violation = RuffViolation(
                                file=item.get("filename", file_path),
                                line=item.get("location", {}).get("row", 0),
                                column=item.get("location", {}).get("column", 0),
                                code=item.get("code", "UNKNOWN"),
                                message=item.get("message", ""),
                                severity=RuffValidator._get_rule_severity(item.get("code", ""))
                            )
                            violations.append(violation)
                except json.JSONDecodeError:
                    # If JSON parsing fails, parse text output
                    violations = RuffValidator._parse_text_output(result.stdout, file_path)

            # Count violations by severity
            error_count = sum(1 for v in violations if v.severity == "error")
            warning_count = sum(1 for v in violations if v.severity == "warning")
            note_count = sum(1 for v in violations if v.severity == "note")

            # Determine pass/fail
            passed = error_count == 0

            report = RuffReport(
                violations=violations,
                passed=passed,
                total_violations=len(violations),
                error_count=error_count,
                warning_count=warning_count,
                note_count=note_count,
                execution_time_ms=0  # Would need to measure actual time
            )

            return report

        except FileNotFoundError:
            raise RuntimeError(
                "Ruff is not installed or not found in PATH. "
                "Please install it with: pip install ruff"
            )
        except subprocess.TimeoutExpired:
            raise subprocess.TimeoutExpired(
                cmd="ruff",
                timeout=timeout,
                output="Ruff linting exceeded timeout"
            )

    @staticmethod
    def lint_directory(
        directory_path: str,
        config_path: Optional[str] = None,
        timeout: int = 60,
        exclude_patterns: Optional[List[str]] = None
    ) -> Tuple[RuffReport, Dict[str, RuffReport]]:
        """
        Lint all Python files in a directory.
        
        Args:
            directory_path (str): Path to directory to lint
            config_path (Optional[str]): Path to Ruff config file
            timeout (int): Subprocess timeout in seconds (default: 60)
            exclude_patterns (Optional[List[str]]): Patterns to exclude
        
        Returns:
            Tuple[RuffReport, Dict[str, RuffReport]]:
                - aggregate_report: Combined report for all files
                - per_file_reports: Individual reports per file
        """
        directory_path_obj = Path(directory_path)
        if not directory_path_obj.is_dir():
            raise FileNotFoundError(f"Directory not found: {directory_path}")

        try:
            # Build ruff command for entire directory
            cmd = ["ruff", "check", directory_path, "--output-format", "json"]
            
            if config_path:
                cmd.extend(["--config", config_path])
            
            if exclude_patterns:
                for pattern in exclude_patterns:
                    cmd.extend(["--exclude", pattern])

            # Run ruff
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            # Parse violations
            all_violations = []
            per_file_reports = {}

            if result.stdout:
                try:
                    violations_data = json.loads(result.stdout)
                    if isinstance(violations_data, list):
                        # Group by file
                        by_file = {}
                        for item in violations_data:
                            file_name = item.get("filename", "unknown")
                            violation = RuffViolation(
                                file=file_name,
                                line=item.get("location", {}).get("row", 0),
                                column=item.get("location", {}).get("column", 0),
                                code=item.get("code", "UNKNOWN"),
                                message=item.get("message", ""),
                                severity=RuffValidator._get_rule_severity(item.get("code", ""))
                            )
                            all_violations.append(violation)
                            
                            if file_name not in by_file:
                                by_file[file_name] = []
                            by_file[file_name].append(violation)

                        # Create per-file reports
                        for file_name, file_violations in by_file.items():
                            error_count = sum(1 for v in file_violations if v.severity == "error")
                            warning_count = sum(1 for v in file_violations if v.severity == "warning")
                            note_count = sum(1 for v in file_violations if v.severity == "note")
                            
                            per_file_reports[file_name] = RuffReport(
                                violations=file_violations,
                                passed=error_count == 0,
                                total_violations=len(file_violations),
                                error_count=error_count,
                                warning_count=warning_count,
                                note_count=note_count,
                                execution_time_ms=0
                            )

                except json.JSONDecodeError:
                    pass

            # Create aggregate report
            error_count = sum(1 for v in all_violations if v.severity == "error")
            warning_count = sum(1 for v in all_violations if v.severity == "warning")
            note_count = sum(1 for v in all_violations if v.severity == "note")

            aggregate_report = RuffReport(
                violations=all_violations,
                passed=error_count == 0,
                total_violations=len(all_violations),
                error_count=error_count,
                warning_count=warning_count,
                note_count=note_count,
                execution_time_ms=0
            )

            return aggregate_report, per_file_reports

        except FileNotFoundError:
            raise RuntimeError(
                "Ruff is not installed or not found in PATH. "
                "Please install it with: pip install ruff"
            )
        except subprocess.TimeoutExpired:
            raise subprocess.TimeoutExpired(
                cmd="ruff",
                timeout=timeout,
                output="Ruff linting exceeded timeout"
            )

    @staticmethod
    def _parse_text_output(output: str, file_path: str) -> List[RuffViolation]:
        """
        Parse Ruff text output when JSON parsing fails.
        
        Expected format:
        filename:line:column: CODE message
        
        Args:
            output (str): Ruff text output
            file_path (str): Original file path for context
        
        Returns:
            List[RuffViolation]: Parsed violations
        """
        violations = []
        pattern = r"(.+?):(\d+):(\d+):\s+(\w+)\s+(.+)"

        for line in output.strip().split('\n'):
            match = re.match(pattern, line)
            if match:
                file_part, line_num, col_num, code, message = match.groups()
                violation = RuffViolation(
                    file=file_part or file_path,
                    line=int(line_num),
                    column=int(col_num),
                    code=code,
                    message=message,
                    severity=RuffValidator._get_rule_severity(code)
                )
                violations.append(violation)

        return violations

    @staticmethod
    def format_report_text(report: RuffReport) -> str:
        """
        Format a RuffReport as human-readable text.
        
        Args:
            report (RuffReport): The report to format
        
        Returns:
            str: Formatted text report
        """
        lines = []
        lines.append("=" * 70)
        lines.append("RUFF LINTING REPORT")
        lines.append("=" * 70)
        
        if report.passed:
            lines.append("✓ PASSED: No linting errors found")
        else:
            lines.append("✗ FAILED: Linting errors detected")
        
        lines.append("")
        lines.append(f"Total Violations: {report.total_violations}")
        lines.append(f"  Errors:   {report.error_count}")
        lines.append(f"  Warnings: {report.warning_count}")
        lines.append(f"  Notes:    {report.note_count}")
        lines.append("")

        if report.violations:
            lines.append("Violations:")
            lines.append("-" * 70)
            for v in report.violations:
                severity_marker = "✗" if v.severity == "error" else "⚠" if v.severity == "warning" else "ℹ"
                lines.append(
                    f"{severity_marker} [{v.code}] {v.file}:{v.line}:{v.column} - {v.message}"
                )
        
        lines.append("=" * 70)
        return "\n".join(lines)
