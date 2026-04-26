"""
Phase 8.4: AST Diff Integration Layer

High-level integration functions for AST diffing via API endpoints.
Provides error handling and structured responses.
"""

import logging
from typing import Dict, Any, List, Optional

from app.services.ast_differ import ASTDiffer, SymbolChangeType

logger = logging.getLogger(__name__)


def diff_file_against_version(
    file_path: str,
    old_version: str = "HEAD"
) -> Dict[str, Any]:
    """
    Compare a file with a previous version using AST diffing.
    
    Args:
        file_path: Path to the file to diff
        old_version: Git ref to compare against (default: HEAD)
        
    Returns:
        Dictionary with status and change details
    """
    try:
        logger.info(
            f"[PHASE 8.4] Diff request: {file_path} vs {old_version}"
        )
        
        differ = ASTDiffer(file_path)
        changes = differ.diff_file(old_version)
        summary = differ.get_change_summary(changes)
        
        return {
            "status": "success",
            "file_path": file_path,
            "compared_against": old_version,
            "changes": [change.to_dict() for change in changes],
            "summary": summary
        }
        
    except Exception as e:
        logger.error(
            f"[PHASE 8.4] Error diffing file: {str(e)}", 
            exc_info=True
        )
        return {
            "status": "failed",
            "error": str(e),
            "changes": [],
            "summary": {
                "total_changes": 0,
                "added": 0,
                "removed": 0,
                "modified": 0
            }
        }


def get_symbol_changes(
    file_path: str,
    old_version: str = "HEAD"
) -> Dict[str, Any]:
    """
    Get a detailed list of symbol changes for a file.
    
    Args:
        file_path: Path to the file
        old_version: Git ref to compare against
        
    Returns:
        Dictionary with changes grouped by type
    """
    try:
        differ = ASTDiffer(file_path)
        changes = differ.diff_file(old_version)
        
        # Group by change type
        added = [c for c in changes if c.change_type == SymbolChangeType.ADDED]
        removed = [c for c in changes if c.change_type == SymbolChangeType.REMOVED]
        modified = [c for c in changes if c.change_type == SymbolChangeType.MODIFIED]
        
        return {
            "status": "success",
            "file_path": file_path,
            "added": [
                {
                    "symbol": c.symbol_name,
                    "type": c.symbol_type,
                    "signature": c.new_info.signature if c.new_info else None,
                    "line": c.new_info.start_line if c.new_info else None
                }
                for c in added
            ],
            "removed": [
                {
                    "symbol": c.symbol_name,
                    "type": c.symbol_type,
                    "signature": c.old_info.signature if c.old_info else None,
                    "line": c.old_info.start_line if c.old_info else None
                }
                for c in removed
            ],
            "modified": [
                {
                    "symbol": c.symbol_name,
                    "type": c.symbol_type,
                    "old_signature": c.old_info.signature if c.old_info else None,
                    "new_signature": c.new_info.signature if c.new_info else None,
                    "old_line": c.old_info.start_line if c.old_info else None,
                    "new_line": c.new_info.start_line if c.new_info else None
                }
                for c in modified
            ]
        }
        
    except Exception as e:
        logger.error(f"[PHASE 8.4] Error getting symbol changes: {str(e)}")
        return {
            "status": "failed",
            "error": str(e),
            "added": [],
            "removed": [],
            "modified": []
        }


def get_file_symbols(file_path: str) -> Dict[str, Any]:
    """
    Get all symbols (functions/classes) in the current version of a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dictionary with all symbols
    """
    try:
        differ = ASTDiffer(file_path)
        content = differ.get_current_file_content()
        
        if content is None:
            return {
                "status": "failed",
                "error": f"Could not read {file_path}",
                "symbols": []
            }
        
        symbols = differ.extract_symbols_from_content(content)
        
        return {
            "status": "success",
            "file_path": file_path,
            "symbols": [
                {
                    "name": sym.name,
                    "type": sym.symbol_type,
                    "signature": sym.signature,
                    "start_line": sym.start_line,
                    "end_line": sym.end_line,
                    "docstring": sym.docstring[:100] if sym.docstring else None  # First 100 chars
                }
                for sym in symbols.values()
            ],
            "count": len(symbols)
        }
        
    except Exception as e:
        logger.error(f"[PHASE 8.4] Error getting file symbols: {str(e)}")
        return {
            "status": "failed",
            "error": str(e),
            "symbols": [],
            "count": 0
        }


def get_change_impact_summary(
    file_path: str,
    old_version: str = "HEAD"
) -> Dict[str, Any]:
    """
    Get a high-level summary of changes and their impact.
    
    Args:
        file_path: Path to the file
        old_version: Git ref to compare against
        
    Returns:
        Dictionary with impact summary
    """
    try:
        differ = ASTDiffer(file_path)
        changes = differ.diff_file(old_version)
        summary = differ.get_change_summary(changes)
        
        # Determine impact level
        if summary["total_changes"] == 0:
            impact_level = "none"
            impact_description = "No changes detected"
        elif summary["total_changes"] <= 2:
            impact_level = "low"
            impact_description = "Minor changes"
        elif summary["total_changes"] <= 5:
            impact_level = "medium"
            impact_description = "Moderate changes"
        else:
            impact_level = "high"
            impact_description = "Significant changes"
        
        # Check for breaking changes
        has_removals = summary["removed"] > 0 or summary["removed_functions"] > 0 or summary["removed_classes"] > 0
        has_signature_changes = summary["modified"] > 0
        
        return {
            "status": "success",
            "file_path": file_path,
            "impact_level": impact_level,
            "impact_description": impact_description,
            "has_removals": has_removals,
            "has_signature_changes": has_signature_changes,
            "summary": summary,
            "recommendations": [
                "Run tests to verify changes" if summary["total_changes"] > 0 else None,
                "Check dependent code for removed symbols" if has_removals else None,
                "Update call sites for modified signatures" if has_signature_changes else None
            ]
        }
        
    except Exception as e:
        logger.error(f"[PHASE 8.4] Error getting impact summary: {str(e)}")
        return {
            "status": "failed",
            "error": str(e)
        }
