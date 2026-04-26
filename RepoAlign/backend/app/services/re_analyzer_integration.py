"""
Phase 8.6: Targeted Re-Analysis Integration Layer

Provides thread-safe wrapper functions for the re-analysis service.
Handles resource management, error handling, and logging coordination.

Pattern: Global singleton ReAnalyzer with threading.Lock for concurrency
"""

import threading
import logging
from typing import Dict, List, Optional
from app.services.re_analyzer import ReAnalyzer

logger = logging.getLogger(__name__)

# Global singleton
_re_analyzer: Optional[ReAnalyzer] = None
_re_analyzer_lock = threading.Lock()


def get_re_analyzer() -> ReAnalyzer:
    """
    Get or create the singleton ReAnalyzer instance.
    
    Thread-safe initialization using double-checked locking pattern.
    """
    global _re_analyzer
    
    if _re_analyzer is None:
        with _re_analyzer_lock:
            if _re_analyzer is None:
                logger.info("[PHASE 8.6] Initializing ReAnalyzer singleton")
                _re_analyzer = ReAnalyzer()
    
    return _re_analyzer


def re_analyze_file_changes(
    file_path: str,
    file_content: str,
    added_symbols: List[Dict] = None,
    modified_symbols: List[Dict] = None
) -> Dict:
    """
    Re-analyze changed symbols in a file.
    
    Generates updated structured data for added and modified symbols
    using the Phase 2 static analysis pipeline.
    
    Args:
        file_path: Path to the file being analyzed
        file_content: Current file content as string
        added_symbols: List of dicts with symbol_name, symbol_type for new symbols
        modified_symbols: List of dicts with symbol_name, symbol_type for modified symbols
    
    Returns:
        Dictionary with:
        - status: "success", "partial", or "failed"
        - file_path: The file that was analyzed
        - added_symbols: List of re-analyzed added symbols
        - modified_symbols: List of re-analyzed modified symbols
        - error_count: Number of symbols that failed to analyze
        - errors: List of error messages
        
    Example Response (success):
    {
        "status": "success",
        "file_path": "/path/to/file.py",
        "added_symbols": [
            {
                "symbol_name": "new_function",
                "symbol_type": "function",
                "signature": "def new_function(x, y)",
                "parameters": [...],
                "functions_called": [...],
                ...
            }
        ],
        "modified_symbols": [
            {
                "symbol_name": "updated_function",
                "symbol_type": "function",
                "signature": "def updated_function(x, y, z)",
                ...
            }
        ],
        "error_count": 0,
        "errors": []
    }
    """
    logger.info(f"[PHASE 8.6] Integration: Re-analyzing file changes for {file_path}")
    
    try:
        analyzer = get_re_analyzer()
        
        result = analyzer.re_analyze_symbols(
            file_path=file_path,
            file_content=file_content,
            added_symbols=added_symbols,
            modified_symbols=modified_symbols
        )
        
        logger.info(f"[PHASE 8.6] Integration: ✓ Re-analysis complete")
        return result
        
    except Exception as e:
        logger.error(f"[PHASE 8.6] Integration: Error during re-analysis: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "file_path": file_path,
            "added_symbols": [],
            "modified_symbols": [],
            "error_count": 1,
            "errors": [str(e)]
        }


def re_analyze_single_symbol(
    file_path: str,
    file_content: str,
    symbol_name: str,
    symbol_type: str = "function"
) -> Dict:
    """
    Re-analyze a single symbol in isolation.
    
    Useful for understanding what changed in a single function or class.
    Returns the complete re-analyzed structure for that symbol.
    
    Args:
        file_path: Path to the file containing the symbol
        file_content: Current file content as string
        symbol_name: Name of the symbol to analyze
        symbol_type: "function" or "class"
    
    Returns:
        Dictionary with:
        - status: "success" or "failed"
        - symbol: Complete re-analyzed symbol data (if success)
        - error: Error message (if failed)
        
    Example Response (success):
    {
        "status": "success",
        "symbol": {
            "symbol_name": "my_function",
            "symbol_type": "function",
            "file_path": "/path/to/file.py",
            "start_line": 10,
            "end_line": 25,
            "signature": "def my_function(x: int, y: str) -> bool",
            "docstring": "Does something important",
            "parameters": [...],
            "imports_used": [...],
            "functions_called": [...],
            "cyclomatic_complexity": 2,
            "lines_of_code": 16
        }
    }
    """
    logger.info(f"[PHASE 8.6] Integration: Re-analyzing single {symbol_type}: {symbol_name}")
    
    try:
        analyzer = get_re_analyzer()
        
        result = analyzer.re_analyze_symbol(
            file_path=file_path,
            file_content=file_content,
            symbol_name=symbol_name,
            symbol_type=symbol_type
        )
        
        if result.get("status") == "success":
            logger.info(f"[PHASE 8.6] Integration: ✓ Single symbol re-analysis complete")
        else:
            logger.warning(f"[PHASE 8.6] Integration: Re-analysis failed: {result.get('error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"[PHASE 8.6] Integration: Error during single symbol analysis: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e)
        }


def re_analyze_batch(
    file_analyses: List[Dict]
) -> Dict:
    """
    Re-analyze multiple files' changed symbols in batch.
    
    Orchestrates re-analysis across multiple files. Each file_analysis dict
    should contain file_path, file_content, added_symbols, modified_symbols.
    
    Args:
        file_analyses: List of dicts, each with:
            - file_path: Path to file
            - file_content: File content
            - added_symbols: List of added symbols
            - modified_symbols: List of modified symbols
    
    Returns:
        Dictionary with batch results:
        - status: "success" or "failed"
        - total_files: Number of files processed
        - results: List of re-analysis results for each file
        - total_symbols_analyzed: Total symbols re-analyzed across all files
        - total_errors: Total errors across all files
        
    Example Response:
    {
        "status": "success",
        "total_files": 2,
        "results": [
            {
                "file_path": "/path/to/file1.py",
                "status": "success",
                "added_symbols": [...],
                "modified_symbols": [...],
                "error_count": 0
            },
            {
                "file_path": "/path/to/file2.py",
                "status": "success",
                "added_symbols": [...],
                "modified_symbols": [...],
                "error_count": 0
            }
        ],
        "total_symbols_analyzed": 5,
        "total_errors": 0
    }
    """
    logger.info(f"[PHASE 8.6] Integration: Batch re-analysis for {len(file_analyses)} files")
    
    try:
        results = []
        total_symbols = 0
        total_errors = 0
        
        for file_analysis in file_analyses:
            file_path = file_analysis.get("file_path")
            file_content = file_analysis.get("file_content")
            added_symbols = file_analysis.get("added_symbols", [])
            modified_symbols = file_analysis.get("modified_symbols", [])
            
            logger.debug(f"[PHASE 8.6] Integration: Processing {file_path}")
            
            result = re_analyze_file_changes(
                file_path=file_path,
                file_content=file_content,
                added_symbols=added_symbols,
                modified_symbols=modified_symbols
            )
            
            results.append(result)
            
            total_symbols += len(result.get("added_symbols", [])) + len(result.get("modified_symbols", []))
            total_errors += result.get("error_count", 0)
        
        logger.info(f"[PHASE 8.6] Integration: ✓ Batch re-analysis complete")
        logger.info(f"[PHASE 8.6] Integration: Total symbols analyzed: {total_symbols}")
        logger.info(f"[PHASE 8.6] Integration: Total errors: {total_errors}")
        
        return {
            "status": "success" if total_errors == 0 else "partial",
            "total_files": len(file_analyses),
            "results": results,
            "total_symbols_analyzed": total_symbols,
            "total_errors": total_errors
        }
        
    except Exception as e:
        logger.error(f"[PHASE 8.6] Integration: Error during batch re-analysis: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "total_files": len(file_analyses),
            "results": [],
            "total_symbols_analyzed": 0,
            "total_errors": len(file_analyses),
            "error": str(e)
        }
