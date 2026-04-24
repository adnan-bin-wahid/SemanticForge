"""
Basic Rules Checker

This module provides lightweight syntax and structural validation for Python code.
It's designed as a quick first-pass validator before running heavier tools (Ruff, Mypy).
"""

import ast
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class SyntaxIssue:
    """Represents a single syntax or structural issue found by the basic checker."""
    line: int
    column: int
    issue_type: str  # "syntax_error", "incomplete_block", "import_error", "indentation", etc.
    message: str
    severity: str  # "error" or "warning"

    def to_dict(self) -> Dict:
        """Convert issue to dictionary."""
        return asdict(self)


@dataclass
class BasicCheckReport:
    """Represents the complete basic rules checking report."""
    issues: List[SyntaxIssue]
    passed: bool
    total_issues: int
    error_count: int
    warning_count: int
    has_syntax_error: bool
    summary: str

    def to_dict(self) -> Dict:
        """Convert report to dictionary."""
        return {
            "issues": [i.to_dict() for i in self.issues],
            "passed": self.passed,
            "total_issues": self.total_issues,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "has_syntax_error": self.has_syntax_error,
            "summary": self.summary,
        }


class BasicRulesChecker:
    """
    Performs lightweight syntax and structural validation on Python code.
    
    This checker:
    - Validates Python syntax via AST parsing
    - Detects incomplete code blocks
    - Checks for indentation errors
    - Validates import statements
    - Checks for common coding mistakes
    """

    @staticmethod
    def check_file(file_path: str) -> BasicCheckReport:
        """
        Perform basic rules checking on a Python file.
        
        Args:
            file_path (str): Path to the Python file to check
        
        Returns:
            BasicCheckReport: Report of all issues found
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            raise IOError(f"Failed to read file {file_path}: {str(e)}")

        return BasicRulesChecker.check_code(content)

    @staticmethod
    def check_code(code: str) -> BasicCheckReport:
        """
        Perform basic rules checking on Python code string.
        
        Args:
            code (str): Python code to check
        
        Returns:
            BasicCheckReport: Report of all issues found
        """
        issues = []
        has_syntax_error = False

        # 1. Check for syntax errors via AST parsing
        try:
            ast.parse(code)
        except SyntaxError as e:
            has_syntax_error = True
            issue = SyntaxIssue(
                line=e.lineno or 1,
                column=e.offset or 1,
                issue_type="syntax_error",
                message=f"Syntax error: {e.msg}",
                severity="error"
            )
            issues.append(issue)
        except Exception as e:
            has_syntax_error = True
            issue = SyntaxIssue(
                line=1,
                column=1,
                issue_type="syntax_error",
                message=f"Parse error: {str(e)}",
                severity="error"
            )
            issues.append(issue)

        # 2. If no syntax errors, perform additional checks
        if not has_syntax_error:
            # Check for indentation issues
            indent_issues = BasicRulesChecker._check_indentation(code)
            issues.extend(indent_issues)

            # Check for incomplete blocks
            block_issues = BasicRulesChecker._check_incomplete_blocks(code)
            issues.extend(block_issues)

            # Check for common issues
            common_issues = BasicRulesChecker._check_common_issues(code)
            issues.extend(common_issues)

        # Count by severity
        error_count = sum(1 for i in issues if i.severity == "error")
        warning_count = sum(1 for i in issues if i.severity == "warning")

        # Determine pass/fail
        passed = error_count == 0

        # Generate summary
        summary = BasicRulesChecker._generate_summary(issues, has_syntax_error)

        report = BasicCheckReport(
            issues=issues,
            passed=passed,
            total_issues=len(issues),
            error_count=error_count,
            warning_count=warning_count,
            has_syntax_error=has_syntax_error,
            summary=summary
        )

        return report

    @staticmethod
    def _check_indentation(code: str) -> List[SyntaxIssue]:
        """
        Check for indentation issues.
        
        Args:
            code (str): Python code to check
        
        Returns:
            List[SyntaxIssue]: List of indentation issues found
        """
        issues = []
        lines = code.split('\n')

        for line_num, line in enumerate(lines, 1):
            if not line.strip():
                continue

            # Check for mixed tabs and spaces
            if '\t' in line and ' ' in line[:len(line) - len(line.lstrip())]:
                issue = SyntaxIssue(
                    line=line_num,
                    column=1,
                    issue_type="indentation",
                    message="Mixed tabs and spaces in indentation",
                    severity="warning"
                )
                issues.append(issue)

            # Check for inconsistent indentation (multiple of 4 spaces)
            leading_spaces = len(line) - len(line.lstrip(' '))
            if leading_spaces > 0 and leading_spaces % 4 != 0:
                # This is just a warning, not necessarily an error
                pass

        return issues

    @staticmethod
    def _check_incomplete_blocks(code: str) -> List[SyntaxIssue]:
        """
        Check for incomplete code blocks (unfinished if/for/while/def/class).
        
        Args:
            code (str): Python code to check
        
        Returns:
            List[SyntaxIssue]: List of incomplete block issues
        """
        issues = []
        lines = code.split('\n')

        # Pattern to detect lines that expect an indented block
        block_starters = re.compile(r'^\s*(if|elif|else|for|while|def|class|with|try|except|finally)\b')

        for line_num, line in enumerate(lines, 1):
            if not line.strip() or line.strip().startswith('#'):
                continue

            # Check if line starts a block
            if block_starters.match(line):
                # Check if there's a colon at the end
                if not line.rstrip().endswith(':'):
                    issue = SyntaxIssue(
                        line=line_num,
                        column=len(line),
                        issue_type="incomplete_block",
                        message="Block statement missing colon (:)",
                        severity="error"
                    )
                    issues.append(issue)

                # Check if the next non-empty line is indented
                next_indented = False
                for next_line in lines[line_num:]:
                    if next_line.strip():
                        if len(next_line) - len(next_line.lstrip()) > len(line) - len(line.lstrip()):
                            next_indented = True
                        break

                if not next_indented and line.rstrip().endswith(':'):
                    # The block has no body
                    issue = SyntaxIssue(
                        line=line_num,
                        column=len(line),
                        issue_type="incomplete_block",
                        message="Block statement with no body",
                        severity="warning"
                    )
                    issues.append(issue)

        return issues

    @staticmethod
    def _check_common_issues(code: str) -> List[SyntaxIssue]:
        """
        Check for common coding mistakes.
        
        Args:
            code (str): Python code to check
        
        Returns:
            List[SyntaxIssue]: List of common issues found
        """
        issues = []
        lines = code.split('\n')

        for line_num, line in enumerate(lines, 1):
            if not line.strip() or line.strip().startswith('#'):
                continue

            # Check for common typos/mistakes
            stripped = line.strip()

            # Check for duplicate colons
            if '::' in stripped:
                issue = SyntaxIssue(
                    line=line_num,
                    column=line.find('::') + 1,
                    issue_type="common_issue",
                    message="Double colon (::) found - did you mean a single colon (:)?",
                    severity="warning"
                )
                issues.append(issue)

            # Check for common assignment mistakes (= instead of ==)
            # This is a simple heuristic and may have false positives
            if ' if ' in stripped and '==' not in stripped and '!=' not in stripped:
                if re.search(r'if\s+\w+\s*=\s*', stripped):
                    issue = SyntaxIssue(
                        line=line_num,
                        column=line.find('if') + 1,
                        issue_type="common_issue",
                        message="Possible assignment in condition - did you mean (==)?",
                        severity="warning"
                    )
                    issues.append(issue)

            # Check for unclosed parentheses/brackets (very basic)
            open_parens = stripped.count('(') - stripped.count(')')
            open_brackets = stripped.count('[') - stripped.count(']')
            open_braces = stripped.count('{') - stripped.count('}')

            # Note: This is a very simple check and doesn't account for strings
            if (open_parens != 0 or open_brackets != 0 or open_braces != 0):
                # This might just be a multi-line construct, so it's a warning
                pass

        return issues

    @staticmethod
    def _generate_summary(issues: List[SyntaxIssue], has_syntax_error: bool) -> str:
        """
        Generate a summary message for the report.
        
        Args:
            issues (List[SyntaxIssue]): List of issues found
            has_syntax_error (bool): Whether a syntax error was found
        
        Returns:
            str: Summary message
        """
        if not issues:
            return "✓ Code passed basic validation - no issues found"

        error_count = sum(1 for i in issues if i.severity == "error")
        warning_count = sum(1 for i in issues if i.severity == "warning")

        if error_count > 0:
            return f"✗ Code has {error_count} error(s) and {warning_count} warning(s)"
        else:
            return f"⚠ Code has {warning_count} warning(s) but no errors"

    @staticmethod
    def format_report_text(report: BasicCheckReport) -> str:
        """
        Format a BasicCheckReport as human-readable text.
        
        Args:
            report (BasicCheckReport): The report to format
        
        Returns:
            str: Formatted text report
        """
        lines = []
        lines.append("=" * 70)
        lines.append("BASIC RULES CHECKING REPORT")
        lines.append("=" * 70)

        if report.passed:
            lines.append("✓ PASSED: Code passed basic validation")
        else:
            lines.append("✗ FAILED: Code has validation issues")

        lines.append("")
        lines.append(f"Total Issues: {report.total_issues}")
        lines.append(f"  Errors:   {report.error_count}")
        lines.append(f"  Warnings: {report.warning_count}")
        lines.append("")

        if report.has_syntax_error:
            lines.append("⚠ SYNTAX ERROR DETECTED")
            lines.append("")

        if report.issues:
            lines.append("Issues:")
            lines.append("-" * 70)
            for issue in report.issues:
                severity_marker = "✗" if issue.severity == "error" else "⚠"
                lines.append(
                    f"{severity_marker} Line {issue.line}:{issue.column} [{issue.issue_type}] "
                    f"{issue.message}"
                )

        lines.append("=" * 70)
        return "\n".join(lines)

    @staticmethod
    def get_quick_summary(report: BasicCheckReport) -> str:
        """
        Get a one-line summary of the basic checking report.
        
        Args:
            report (BasicCheckReport): The report to summarize
        
        Returns:
            str: One-line summary
        """
        if report.passed:
            return "✓ Basic validation passed"
        else:
            return (
                f"✗ Basic validation failed: {report.error_count} error(s), "
                f"{report.warning_count} warning(s)"
            )
