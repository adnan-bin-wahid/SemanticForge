"""
Phase 8.6: Targeted Re-Analysis Service

Runs the static analysis pipeline (Phase 2) selectively on changed symbols.
Instead of re-analyzing the entire file, this service focuses only on symbols
that were added or modified, generating updated structured data for them.

Key Pattern:
1. Phase 8.4 identifies which symbols changed (added/modified)
2. Phase 8.6 re-analyzes ONLY those symbols
3. Phase 8.7 updates the graph with the new analysis data

This avoids expensive full-file re-analysis and targets surgical updates.
"""

import ast
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum
from pathlib import Path
import inspect

logger = logging.getLogger(__name__)


class ImportType(Enum):
    """Types of imports in Python."""
    DIRECT = "direct"  # import x
    FROM = "from"      # from x import y
    RELATIVE = "relative"


@dataclass
class ImportInfo:
    """Information about an imported module or symbol."""
    module_name: str
    symbol_name: Optional[str] = None  # For 'from x import y'
    alias: Optional[str] = None  # For 'import x as y'
    import_type: ImportType = ImportType.DIRECT
    
    def to_dict(self) -> Dict:
        return {
            "module_name": self.module_name,
            "symbol_name": self.symbol_name,
            "alias": self.alias,
            "import_type": self.import_type.value
        }


@dataclass
class CallInfo:
    """Information about a function call."""
    function_name: str
    arguments: List[str] = field(default_factory=list)
    is_method_call: bool = False
    object_name: Optional[str] = None  # For obj.method() calls
    
    def to_dict(self) -> Dict:
        return {
            "function_name": self.function_name,
            "arguments": self.arguments,
            "is_method_call": self.is_method_call,
            "object_name": self.object_name
        }


@dataclass
class ParameterInfo:
    """Information about a function parameter."""
    name: str
    annotation: Optional[str] = None
    default_value: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "annotation": self.annotation,
            "default_value": self.default_value
        }


@dataclass
class ReAnalyzedSymbol:
    """Structured data for a re-analyzed symbol (function or class)."""
    symbol_name: str
    symbol_type: str  # "function" or "class"
    file_path: str
    start_line: int
    end_line: int
    
    # Symbol-specific metadata
    signature: str
    docstring: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    
    # Function-specific
    parameters: List[ParameterInfo] = field(default_factory=list)
    return_type: Optional[str] = None
    
    # Class-specific
    base_classes: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    
    # Code analysis
    imports_used: List[ImportInfo] = field(default_factory=list)
    functions_called: List[CallInfo] = field(default_factory=list)
    
    # Metrics
    cyclomatic_complexity: int = 1
    lines_of_code: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "symbol_name": self.symbol_name,
            "symbol_type": self.symbol_type,
            "file_path": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "signature": self.signature,
            "docstring": self.docstring,
            "decorators": self.decorators,
            "parameters": [p.to_dict() for p in self.parameters],
            "return_type": self.return_type,
            "base_classes": self.base_classes,
            "methods": self.methods,
            "imports_used": [i.to_dict() for i in self.imports_used],
            "functions_called": [c.to_dict() for c in self.functions_called],
            "cyclomatic_complexity": self.cyclomatic_complexity,
            "lines_of_code": self.lines_of_code
        }


class CallExtractor(ast.NodeVisitor):
    """Extract function calls from a code block."""
    
    def __init__(self):
        self.calls: List[CallInfo] = []
    
    def visit_Call(self, node: ast.Call) -> None:
        """Extract function call information."""
        call_info = self._extract_call(node)
        if call_info:
            self.calls.append(call_info)
        self.generic_visit(node)
    
    def _extract_call(self, node: ast.Call) -> Optional[CallInfo]:
        """Extract details from a Call node."""
        func = node.func
        
        # Handle simple function calls: func()
        if isinstance(func, ast.Name):
            args = [self._arg_to_str(arg) for arg in node.args]
            return CallInfo(
                function_name=func.id,
                arguments=args,
                is_method_call=False
            )
        
        # Handle method calls: obj.method()
        elif isinstance(func, ast.Attribute):
            args = [self._arg_to_str(arg) for arg in node.args]
            obj_name = self._node_to_str(func.value)
            return CallInfo(
                function_name=func.attr,
                arguments=args,
                is_method_call=True,
                object_name=obj_name
            )
        
        return None
    
    @staticmethod
    def _arg_to_str(arg: ast.expr) -> str:
        """Convert an argument node to a string."""
        if isinstance(arg, ast.Name):
            return arg.id
        elif isinstance(arg, ast.Constant):
            return repr(arg.value)
        elif isinstance(arg, ast.Attribute):
            return ast.unparse(arg)
        else:
            return ast.unparse(arg)
    
    @staticmethod
    def _node_to_str(node: ast.expr) -> str:
        """Convert a node to a string."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return ast.unparse(node)
        else:
            return ast.unparse(node)


class ImportExtractor(ast.NodeVisitor):
    """Extract import statements from a code block."""
    
    def __init__(self):
        self.imports: List[ImportInfo] = []
    
    def visit_Import(self, node: ast.Import) -> None:
        """Handle 'import x' statements."""
        for alias in node.names:
            self.imports.append(ImportInfo(
                module_name=alias.name,
                alias=alias.asname,
                import_type=ImportType.DIRECT
            ))
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Handle 'from x import y' statements."""
        module_name = node.module or ""
        import_type = ImportType.RELATIVE if node.level > 0 else ImportType.FROM
        
        for alias in node.names:
            self.imports.append(ImportInfo(
                module_name=module_name,
                symbol_name=alias.name,
                alias=alias.asname,
                import_type=import_type
            ))
        self.generic_visit(node)


class SelectiveSymbolAnalyzer(ast.NodeVisitor):
    """
    Analyzes specific symbols (functions/classes) in a file.
    
    Instead of analyzing the entire file (Phase 2), this targets specific
    symbols that were changed, extracting their updated structure and metadata.
    """
    
    def __init__(self, file_path: str, file_content: str):
        self.file_path = file_path
        self.file_content = file_content
        self.lines = file_content.split('\n')
        
        # Parse the entire file
        try:
            self.tree = ast.parse(file_content)
        except SyntaxError as e:
            logger.error(f"[PHASE 8.6] Syntax error parsing {file_path}: {e}")
            self.tree = None
        
        # Track all top-level definitions
        self.functions: Dict[str, ast.FunctionDef] = {}
        self.classes: Dict[str, ast.ClassDef] = {}
        self._map_definitions()
    
    def _map_definitions(self) -> None:
        """Build a map of all function and class definitions."""
        if not self.tree:
            return
        
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                self.functions[node.name] = node
            elif isinstance(node, ast.ClassDef):
                self.classes[node.name] = node
    
    def analyze_function(self, function_name: str) -> Optional[ReAnalyzedSymbol]:
        """Re-analyze a specific function."""
        if function_name not in self.functions:
            logger.warning(f"[PHASE 8.6] Function '{function_name}' not found in {self.file_path}")
            return None
        
        func_node = self.functions[function_name]
        logger.debug(f"[PHASE 8.6] Re-analyzing function: {function_name}")
        
        try:
            # Extract signature
            signature = self._build_signature(func_node)
            
            # Extract docstring
            docstring = ast.get_docstring(func_node)
            
            # Extract decorators
            decorators = [ast.unparse(dec) for dec in func_node.decorator_list]
            
            # Extract parameters
            parameters = self._extract_parameters(func_node.args)
            
            # Extract return type
            return_type = None
            if func_node.returns:
                return_type = ast.unparse(func_node.returns)
            
            # Extract body analysis
            imports_used = self._extract_imports_in_scope(func_node)
            functions_called = self._extract_calls_in_scope(func_node)
            
            # Metrics
            cyclomatic_complexity = self._calculate_complexity(func_node)
            lines_of_code = func_node.end_lineno - func_node.lineno + 1
            
            return ReAnalyzedSymbol(
                symbol_name=function_name,
                symbol_type="function",
                file_path=self.file_path,
                start_line=func_node.lineno,
                end_line=func_node.end_lineno or func_node.lineno,
                signature=signature,
                docstring=docstring,
                decorators=decorators,
                parameters=parameters,
                return_type=return_type,
                imports_used=imports_used,
                functions_called=functions_called,
                cyclomatic_complexity=cyclomatic_complexity,
                lines_of_code=lines_of_code
            )
        except Exception as e:
            logger.error(f"[PHASE 8.6] Error analyzing function {function_name}: {e}", exc_info=True)
            return None
    
    def analyze_class(self, class_name: str) -> Optional[ReAnalyzedSymbol]:
        """Re-analyze a specific class."""
        if class_name not in self.classes:
            logger.warning(f"[PHASE 8.6] Class '{class_name}' not found in {self.file_path}")
            return None
        
        class_node = self.classes[class_name]
        logger.debug(f"[PHASE 8.6] Re-analyzing class: {class_name}")
        
        try:
            # Extract signature (class declaration with base classes)
            signature = self._build_class_signature(class_node)
            
            # Extract docstring
            docstring = ast.get_docstring(class_node)
            
            # Extract decorators
            decorators = [ast.unparse(dec) for dec in class_node.decorator_list]
            
            # Extract base classes
            base_classes = [ast.unparse(base) for base in class_node.bases]
            
            # Extract methods
            methods = [node.name for node in class_node.body
                      if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
            
            # Extract body analysis
            imports_used = self._extract_imports_in_scope(class_node)
            functions_called = self._extract_calls_in_scope(class_node)
            
            # Metrics
            cyclomatic_complexity = self._calculate_complexity(class_node)
            lines_of_code = class_node.end_lineno - class_node.lineno + 1
            
            return ReAnalyzedSymbol(
                symbol_name=class_name,
                symbol_type="class",
                file_path=self.file_path,
                start_line=class_node.lineno,
                end_line=class_node.end_lineno or class_node.lineno,
                signature=signature,
                docstring=docstring,
                decorators=decorators,
                base_classes=base_classes,
                methods=methods,
                imports_used=imports_used,
                functions_called=functions_called,
                cyclomatic_complexity=cyclomatic_complexity,
                lines_of_code=lines_of_code
            )
        except Exception as e:
            logger.error(f"[PHASE 8.6] Error analyzing class {class_name}: {e}", exc_info=True)
            return None
    
    def _build_signature(self, func_node: ast.FunctionDef) -> str:
        """Build a function signature string."""
        args_str = self._args_to_str(func_node.args)
        return f"def {func_node.name}({args_str})"
    
    def _build_class_signature(self, class_node: ast.ClassDef) -> str:
        """Build a class signature string."""
        if class_node.bases:
            bases_str = ", ".join(ast.unparse(base) for base in class_node.bases)
            return f"class {class_node.name}({bases_str})"
        else:
            return f"class {class_node.name}"
    
    def _args_to_str(self, args: ast.arguments) -> str:
        """Convert function arguments to a string."""
        parts = []
        
        # Positional arguments
        for arg in args.args:
            parts.append(arg.arg)
        
        # *args
        if args.vararg:
            parts.append(f"*{args.vararg.arg}")
        
        # Keyword-only arguments
        for arg in args.kwonlyargs:
            parts.append(arg.arg)
        
        # **kwargs
        if args.kwarg:
            parts.append(f"**{args.kwarg.arg}")
        
        return ", ".join(parts)
    
    def _extract_parameters(self, args: ast.arguments) -> List[ParameterInfo]:
        """Extract parameter information."""
        params = []
        
        for arg in args.args:
            annotation = None
            if arg.annotation:
                annotation = ast.unparse(arg.annotation)
            params.append(ParameterInfo(
                name=arg.arg,
                annotation=annotation
            ))
        
        if args.vararg:
            params.append(ParameterInfo(name=f"*{args.vararg.arg}"))
        
        for arg in args.kwonlyargs:
            annotation = None
            if arg.annotation:
                annotation = ast.unparse(arg.annotation)
            params.append(ParameterInfo(
                name=arg.arg,
                annotation=annotation
            ))
        
        if args.kwarg:
            params.append(ParameterInfo(name=f"**{args.kwarg.arg}"))
        
        return params
    
    def _extract_imports_in_scope(self, node: ast.AST) -> List[ImportInfo]:
        """Extract import statements used within a specific scope."""
        # Get all imports from the module level
        module_imports = []
        
        if self.tree:
            for item in self.tree.body:
                if isinstance(item, ast.Import):
                    for alias in item.names:
                        module_imports.append(ImportInfo(
                            module_name=alias.name,
                            alias=alias.asname,
                            import_type=ImportType.DIRECT
                        ))
                elif isinstance(item, ast.ImportFrom):
                    module_name = item.module or ""
                    import_type = ImportType.RELATIVE if item.level > 0 else ImportType.FROM
                    for alias in item.names:
                        module_imports.append(ImportInfo(
                            module_name=module_name,
                            symbol_name=alias.name,
                            alias=alias.asname,
                            import_type=import_type
                        ))
        
        # TODO: For now, return module-level imports
        # Could be enhanced to track which imports are actually used
        return module_imports
    
    def _extract_calls_in_scope(self, node: ast.AST) -> List[CallInfo]:
        """Extract function calls within a specific scope."""
        extractor = CallExtractor()
        extractor.visit(node)
        return extractor.calls
    
    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity."""
        # Simple implementation: count decision points
        complexity = 1
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                if isinstance(child.op, ast.And) or isinstance(child.op, ast.Or):
                    complexity += len(child.values) - 1
        
        return complexity


class ReAnalyzer:
    """
    Main service for targeted re-analysis.
    
    Orchestrates the re-analysis of changed symbols, producing updated
    structured data ready for Phase 8.7 to write to the graph.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def re_analyze_symbols(
        self,
        file_path: str,
        file_content: str,
        added_symbols: List[Dict] = None,
        modified_symbols: List[Dict] = None
    ) -> Dict:
        """
        Re-analyze added and modified symbols in a file.
        
        Args:
            file_path: Path to the file
            file_content: Current content of the file
            added_symbols: List of dicts with symbol_name, symbol_type
            modified_symbols: List of dicts with symbol_name, symbol_type
        
        Returns:
            Dictionary with re-analyzed data:
            {
                "status": "success" or "failed",
                "file_path": file_path,
                "added_symbols": [ReAnalyzedSymbol, ...],
                "modified_symbols": [ReAnalyzedSymbol, ...],
                "error_count": N,
                "errors": [list of error messages]
            }
        """
        logger.info(f"[PHASE 8.6] Re-analyzing symbols for {file_path}")
        
        added_symbols = added_symbols or []
        modified_symbols = modified_symbols or []
        
        logger.info(f"[PHASE 8.6] Symbols to re-analyze:")
        logger.info(f"  - Added: {len(added_symbols)}")
        logger.info(f"  - Modified: {len(modified_symbols)}")
        
        analyzer = SelectiveSymbolAnalyzer(file_path, file_content)
        
        re_analyzed_added = []
        re_analyzed_modified = []
        errors = []
        
        # Re-analyze added symbols
        for symbol_info in added_symbols:
            symbol_name = symbol_info.get("symbol_name")
            symbol_type = symbol_info.get("symbol_type", "function")
            
            logger.debug(f"[PHASE 8.6] Re-analyzing added {symbol_type}: {symbol_name}")
            
            try:
                if symbol_type == "class":
                    result = analyzer.analyze_class(symbol_name)
                else:
                    result = analyzer.analyze_function(symbol_name)
                
                if result:
                    re_analyzed_added.append(result)
                    logger.info(f"[PHASE 8.6] ✓ Re-analyzed added {symbol_type}: {symbol_name}")
                else:
                    error_msg = f"Failed to analyze added {symbol_type}: {symbol_name}"
                    errors.append(error_msg)
                    logger.warning(f"[PHASE 8.6] {error_msg}")
            except Exception as e:
                error_msg = f"Exception analyzing added {symbol_type} {symbol_name}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"[PHASE 8.6] {error_msg}", exc_info=True)
        
        # Re-analyze modified symbols
        for symbol_info in modified_symbols:
            symbol_name = symbol_info.get("symbol_name")
            symbol_type = symbol_info.get("symbol_type", "function")
            
            logger.debug(f"[PHASE 8.6] Re-analyzing modified {symbol_type}: {symbol_name}")
            
            try:
                if symbol_type == "class":
                    result = analyzer.analyze_class(symbol_name)
                else:
                    result = analyzer.analyze_function(symbol_name)
                
                if result:
                    re_analyzed_modified.append(result)
                    logger.info(f"[PHASE 8.6] ✓ Re-analyzed modified {symbol_type}: {symbol_name}")
                else:
                    error_msg = f"Failed to analyze modified {symbol_type}: {symbol_name}"
                    errors.append(error_msg)
                    logger.warning(f"[PHASE 8.6] {error_msg}")
            except Exception as e:
                error_msg = f"Exception analyzing modified {symbol_type} {symbol_name}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"[PHASE 8.6] {error_msg}", exc_info=True)
        
        # Build response
        error_count = len(errors)
        status = "success" if error_count == 0 else "partial"
        
        logger.info(f"[PHASE 8.6] Re-analysis complete")
        logger.info(f"[PHASE 8.6] Successfully analyzed: {len(re_analyzed_added) + len(re_analyzed_modified)}")
        logger.info(f"[PHASE 8.6] Errors: {error_count}")
        
        return {
            "status": status,
            "file_path": file_path,
            "added_symbols": [s.to_dict() for s in re_analyzed_added],
            "modified_symbols": [s.to_dict() for s in re_analyzed_modified],
            "error_count": error_count,
            "errors": errors
        }
    
    def re_analyze_symbol(
        self,
        file_path: str,
        file_content: str,
        symbol_name: str,
        symbol_type: str = "function"
    ) -> Dict:
        """
        Re-analyze a single symbol.
        
        Args:
            file_path: Path to the file
            file_content: Current content of the file
            symbol_name: Name of the symbol to analyze
            symbol_type: "function" or "class"
        
        Returns:
            Dictionary with re-analyzed data or error information
        """
        logger.info(f"[PHASE 8.6] Re-analyzing single {symbol_type}: {symbol_name}")
        
        try:
            analyzer = SelectiveSymbolAnalyzer(file_path, file_content)
            
            if symbol_type == "class":
                result = analyzer.analyze_class(symbol_name)
            else:
                result = analyzer.analyze_function(symbol_name)
            
            if result:
                logger.info(f"[PHASE 8.6] ✓ Re-analysis successful")
                return {
                    "status": "success",
                    "symbol": result.to_dict()
                }
            else:
                error_msg = f"Symbol not found or could not be analyzed: {symbol_name}"
                logger.warning(f"[PHASE 8.6] {error_msg}")
                return {
                    "status": "failed",
                    "error": error_msg
                }
        except Exception as e:
            error_msg = f"Error re-analyzing {symbol_type} {symbol_name}: {str(e)}"
            logger.error(f"[PHASE 8.6] {error_msg}", exc_info=True)
            return {
                "status": "failed",
                "error": error_msg
            }
