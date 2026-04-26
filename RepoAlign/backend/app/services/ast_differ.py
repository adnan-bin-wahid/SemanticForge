"""
Phase 8.4: AST Diffing Logic

Compares old and new versions of Python files to identify which functions and
classes have been added, removed, or modified. Uses AST comparison to find
exactly what symbols changed.
"""

import ast
import logging
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Set, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class SymbolChangeType(str, Enum):
    """Types of symbol changes"""
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"


@dataclass
class SymbolInfo:
    """Information about a function or class"""
    name: str
    symbol_type: str  # "function" or "class"
    start_line: int
    end_line: int
    signature: str  # Function signature with parameters
    docstring: Optional[str] = None
    
    def __hash__(self):
        return hash((self.name, self.symbol_type))
    
    def __eq__(self, other):
        if not isinstance(other, SymbolInfo):
            return False
        return self.name == other.name and self.symbol_type == other.symbol_type


@dataclass
class SymbolChange:
    """Represents a change to a symbol"""
    change_type: SymbolChangeType
    symbol_name: str
    symbol_type: str  # "function" or "class"
    old_info: Optional[SymbolInfo] = None
    new_info: Optional[SymbolInfo] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "change_type": self.change_type.value,
            "symbol_name": self.symbol_name,
            "symbol_type": self.symbol_type,
            "old_start_line": self.old_info.start_line if self.old_info else None,
            "old_end_line": self.old_info.end_line if self.old_info else None,
            "new_start_line": self.new_info.start_line if self.new_info else None,
            "new_end_line": self.new_info.end_line if self.new_info else None,
            "old_signature": self.old_info.signature if self.old_info else None,
            "new_signature": self.new_info.signature if self.new_info else None,
            "timestamp": self.timestamp.isoformat()
        }


class ASTSymbolExtractor(ast.NodeVisitor):
    """Extracts function and class definitions from an AST"""
    
    def __init__(self, source_lines: List[str]):
        self.symbols: Dict[str, SymbolInfo] = {}
        self.source_lines = source_lines
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Extract function definition"""
        symbol = self._extract_function_info(node)
        self.symbols[symbol.name] = symbol
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Extract async function definition"""
        symbol = self._extract_function_info(node)
        self.symbols[symbol.name] = symbol
        self.generic_visit(node)
    
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Extract class definition"""
        symbol = self._extract_class_info(node)
        self.symbols[symbol.name] = symbol
        # Don't visit nested methods
    
    def _extract_function_info(self, node: ast.FunctionDef) -> SymbolInfo:
        """Extract function information"""
        signature = self._get_function_signature(node)
        docstring = ast.get_docstring(node)
        
        return SymbolInfo(
            name=node.name,
            symbol_type="function",
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            signature=signature,
            docstring=docstring
        )
    
    def _extract_class_info(self, node: ast.ClassDef) -> SymbolInfo:
        """Extract class information"""
        bases = ", ".join(self._get_base_name(base) for base in node.bases)
        if bases:
            signature = f"class {node.name}({bases})"
        else:
            signature = f"class {node.name}"
        
        docstring = ast.get_docstring(node)
        
        return SymbolInfo(
            name=node.name,
            symbol_type="class",
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            signature=signature,
            docstring=docstring
        )
    
    def _get_function_signature(self, node: ast.FunctionDef) -> str:
        """Build function signature from AST node"""
        args = node.args
        params = []
        
        # Regular positional arguments
        for arg in args.args:
            params.append(arg.arg)
        
        # *args
        if args.vararg:
            params.append(f"*{args.vararg.arg}")
        
        # Keyword-only arguments
        for arg in args.kwonlyargs:
            params.append(arg.arg)
        
        # **kwargs
        if args.kwarg:
            params.append(f"**{args.kwarg.arg}")
        
        params_str = ", ".join(params)
        return f"def {node.name}({params_str})"
    
    def _get_base_name(self, node: ast.expr) -> str:
        """Get base class name from AST node"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_base_name(node.value)}.{node.attr}"
        return "Unknown"


class ASTDiffer:
    """Compares ASTs of old and new file versions to find changes"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        logger.info(f"[PHASE 8.4] ASTDiffer initialized for {file_path}")
    
    def get_git_file_content(self, commit: str = "HEAD") -> Optional[str]:
        """
        Get file content from git repository at specific commit.
        
        Args:
            commit: Git commit reference (default: HEAD)
            
        Returns:
            File content or None if not found
        """
        try:
            # Convert absolute path to relative path for git
            repo_path = "/app/test-project"  # TODO: Make configurable
            
            # Get relative path from repo root
            if self.file_path.startswith(repo_path):
                relative_path = self.file_path[len(repo_path):].lstrip('/')
            else:
                relative_path = self.file_path
            
            result = subprocess.run(
                ["git", "show", f"{commit}:{relative_path}"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                logger.debug(
                    f"[PHASE 8.4] Retrieved {relative_path} from {commit}"
                )
                return result.stdout
            else:
                logger.warning(
                    f"[PHASE 8.4] Could not get {relative_path} from {commit}: {result.stderr}"
                )
                return None
                
        except subprocess.TimeoutExpired:
            logger.error(f"[PHASE 8.4] Timeout getting file from git")
            return None
        except Exception as e:
            logger.error(f"[PHASE 8.4] Error getting file from git: {str(e)}")
            return None
    
    def extract_symbols_from_content(self, content: str) -> Dict[str, SymbolInfo]:
        """
        Extract symbols (functions/classes) from file content.
        
        Args:
            content: Python source code
            
        Returns:
            Dictionary of symbol_name -> SymbolInfo
        """
        try:
            tree = ast.parse(content)
            lines = content.split('\n')
            extractor = ASTSymbolExtractor(lines)
            extractor.visit(tree)
            
            logger.debug(
                f"[PHASE 8.4] Extracted {len(extractor.symbols)} symbols"
            )
            return extractor.symbols
            
        except SyntaxError as e:
            logger.error(f"[PHASE 8.4] Syntax error parsing {self.file_path}: {str(e)}")
            return {}
        except Exception as e:
            logger.error(f"[PHASE 8.4] Error extracting symbols: {str(e)}")
            return {}
    
    def get_current_file_content(self) -> Optional[str]:
        """Read current file content from disk"""
        try:
            with open(self.file_path, 'r') as f:
                return f.read()
        except Exception as e:
            logger.error(f"[PHASE 8.4] Error reading file {self.file_path}: {str(e)}")
            return None
    
    def compare_symbols(
        self, 
        old_symbols: Dict[str, SymbolInfo],
        new_symbols: Dict[str, SymbolInfo]
    ) -> List[SymbolChange]:
        """
        Compare two symbol sets and find changes.
        
        Args:
            old_symbols: Symbols from old version
            new_symbols: Symbols from new version
            
        Returns:
            List of SymbolChange objects
        """
        changes: List[SymbolChange] = []
        
        # Find added and modified symbols
        for name, new_info in new_symbols.items():
            if name not in old_symbols:
                # Added
                changes.append(SymbolChange(
                    change_type=SymbolChangeType.ADDED,
                    symbol_name=name,
                    symbol_type=new_info.symbol_type,
                    new_info=new_info
                ))
                logger.info(f"[PHASE 8.4] Added: {new_info.symbol_type} {name}")
            else:
                old_info = old_symbols[name]
                # Check if modified
                if self._is_symbol_modified(old_info, new_info):
                    changes.append(SymbolChange(
                        change_type=SymbolChangeType.MODIFIED,
                        symbol_name=name,
                        symbol_type=new_info.symbol_type,
                        old_info=old_info,
                        new_info=new_info
                    ))
                    logger.info(f"[PHASE 8.4] Modified: {new_info.symbol_type} {name}")
        
        # Find removed symbols
        for name, old_info in old_symbols.items():
            if name not in new_symbols:
                changes.append(SymbolChange(
                    change_type=SymbolChangeType.REMOVED,
                    symbol_name=name,
                    symbol_type=old_info.symbol_type,
                    old_info=old_info
                ))
                logger.info(f"[PHASE 8.4] Removed: {old_info.symbol_type} {name}")
        
        return changes
    
    def _is_symbol_modified(self, old_info: SymbolInfo, new_info: SymbolInfo) -> bool:
        """
        Check if a symbol has been modified.
        Considers signature changes and line number changes.
        """
        # Check signature changes
        if old_info.signature != new_info.signature:
            return True
        
        # Check docstring changes
        if old_info.docstring != new_info.docstring:
            return True
        
        # Note: We don't consider line number changes as modification
        # since code can be reformatted without functional changes
        return False
    
    def diff_file(self, old_version: str = "HEAD") -> List[SymbolChange]:
        """
        Compare file with a previous version and return changes.
        
        Args:
            old_version: Git commit/ref to compare against (default: HEAD)
            
        Returns:
            List of SymbolChange objects
        """
        logger.info(
            f"[PHASE 8.4] Diffing {self.file_path} against {old_version}"
        )
        
        # Get old version
        old_content = self.get_git_file_content(old_version)
        if old_content is None:
            logger.warning(f"[PHASE 8.4] Could not get old version, assuming file is new")
            old_symbols = {}
        else:
            old_symbols = self.extract_symbols_from_content(old_content)
        
        # Get current version
        new_content = self.get_current_file_content()
        if new_content is None:
            logger.error(f"[PHASE 8.4] Could not read current file content")
            return []
        
        new_symbols = self.extract_symbols_from_content(new_content)
        
        # Compare
        changes = self.compare_symbols(old_symbols, new_symbols)
        
        logger.info(
            f"[PHASE 8.4] Found {len(changes)} symbol changes in {self.file_path}"
        )
        return changes
    
    def get_change_summary(self, changes: List[SymbolChange]) -> Dict:
        """Get summary statistics of changes"""
        added = sum(1 for c in changes if c.change_type == SymbolChangeType.ADDED)
        removed = sum(1 for c in changes if c.change_type == SymbolChangeType.REMOVED)
        modified = sum(1 for c in changes if c.change_type == SymbolChangeType.MODIFIED)
        
        return {
            "total_changes": len(changes),
            "added": added,
            "removed": removed,
            "modified": modified,
            "added_functions": sum(1 for c in changes if c.change_type == SymbolChangeType.ADDED and c.symbol_type == "function"),
            "added_classes": sum(1 for c in changes if c.change_type == SymbolChangeType.ADDED and c.symbol_type == "class"),
            "removed_functions": sum(1 for c in changes if c.change_type == SymbolChangeType.REMOVED and c.symbol_type == "function"),
            "removed_classes": sum(1 for c in changes if c.change_type == SymbolChangeType.REMOVED and c.symbol_type == "class"),
            "modified_functions": sum(1 for c in changes if c.change_type == SymbolChangeType.MODIFIED and c.symbol_type == "function"),
            "modified_classes": sum(1 for c in changes if c.change_type == SymbolChangeType.MODIFIED and c.symbol_type == "class"),
        }
