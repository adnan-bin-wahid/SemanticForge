import ast
from typing import List, Dict, Any, Optional

def _unparse_annotation(annotation: Optional[ast.expr]) -> Optional[str]:
    """Safely unparses a type annotation node."""
    if annotation is None:
        return None
    return ast.unparse(annotation)

def get_call_name(call_node: ast.Call) -> Optional[str]:
    """
    Extracts a string representation of a call from an ast.Call node.
    e.g., 'my_module.my_func' from my_module.my_func().
    """
    func = call_node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        parts = []
        while isinstance(func, ast.Attribute):
            parts.append(func.attr)
            func = func.value
        if isinstance(func, ast.Name):
            parts.append(func.id)
            return ".".join(reversed(parts))
    return None

class StructureExtractor(ast.NodeVisitor):
    """
    An AST visitor to extract top-level function, class, import, and call statements.
    """
    def __init__(self, root_path: str = ""):
        self.root_path = root_path
        self.functions: List[Dict[str, Any]] = []
        self.classes: List[Dict[str, Any]] = []
        self.imports: List[Dict[str, Any]] = []
        self._current_function_calls: Optional[List[Dict[str, Any]]] = None
        self._current_class_methods: Optional[List[Dict[str, Any]]] = None

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append({
                "type": "import",
                "lineno": node.lineno,
                "module": alias.name,
                "alias": alias.asname
            })
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        for alias in node.names:
            self.imports.append({
                "type": "from_import",
                "lineno": node.lineno,
                "module": node.module,
                "name": alias.name,
                "alias": alias.asname,
                "level": node.level
            })
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        original_calls_context = self._current_function_calls
        self._current_function_calls = []

        self.generic_visit(node)

        # Extract full signature details
        args = node.args
        defaults = [ast.unparse(d) for d in args.defaults]
        kw_defaults = [ast.unparse(d) if d else None for d in args.kw_defaults]
        
        num_pos_only = len(args.posonlyargs)
        num_kw_only = len(args.kwonlyargs)
        num_with_defaults = len(defaults)

        parameters = []
        # Positional-only args
        for i, arg in enumerate(args.posonlyargs):
            param = {"name": arg.arg, "kind": "positional_only", "annotation": _unparse_annotation(arg.annotation)}
            parameters.append(param)

        # Positional-or-keyword args
        for i, arg in enumerate(args.args):
            param = {"name": arg.arg, "kind": "positional_or_keyword", "annotation": _unparse_annotation(arg.annotation)}
            # Match default values from the end
            default_index = i - (len(args.args) - num_with_defaults)
            if default_index >= 0:
                param["default"] = defaults[default_index]
            parameters.append(param)

        # Vararg (*args)
        if args.vararg:
            parameters.append({"name": args.vararg.arg, "kind": "var_positional", "annotation": _unparse_annotation(args.vararg.annotation)})

        # Keyword-only args
        for i, arg in enumerate(args.kwonlyargs):
            param = {"name": arg.arg, "kind": "keyword_only", "annotation": _unparse_annotation(arg.annotation)}
            if kw_defaults[i] is not None:
                param["default"] = kw_defaults[i]
            parameters.append(param)
        
        # Kwarg (**kwargs)
        if args.kwarg:
            parameters.append({"name": args.kwarg.arg, "kind": "var_keyword", "annotation": _unparse_annotation(args.kwarg.annotation)})

        signature = {
            "parameters": parameters,
            "return_annotation": _unparse_annotation(node.returns)
        }

        function_data = {
            "name": node.name,
            "lineno": node.lineno,
            "end_lineno": node.end_lineno,
            "signature": signature,
            "calls": self._current_function_calls
        }

        if self._current_class_methods is not None:
             self._current_class_methods.append(function_data)
        else:
            self.functions.append(function_data)

        self._current_function_calls = original_calls_context

    def visit_ClassDef(self, node: ast.ClassDef):
        original_methods_context = self._current_class_methods
        self._current_class_methods = []
        
        # Manually visit function definitions to control context
        for child in node.body:
            if isinstance(child, ast.FunctionDef):
                self.visit_FunctionDef(child)
            else:
                self.visit(child)

        self.classes.append({
            "name": node.name,
            "lineno": node.lineno,
            "end_lineno": node.end_lineno,
            "bases": [_unparse_annotation(b) for b in node.bases],
            "methods": self._current_class_methods
        })
        
        self._current_class_methods = original_methods_context

    def visit_Call(self, node: ast.Call):
        if self._current_function_calls is not None:
            call_name = get_call_name(node)
            if call_name:
                self._current_function_calls.append({
                    "name": call_name,
                    "lineno": node.lineno
                })
        self.generic_visit(node)

def extract_structures(tree: ast.AST) -> Dict[str, List[Dict[str, Any]]]:
    """
    Extracts function, class, and import definitions from an AST.

    Args:
        tree: The AST to analyze.

    Returns:
        A dictionary containing lists of extracted functions, classes, and imports.
    """
    extractor = StructureExtractor()
    extractor.visit(tree)
    return {
        "functions": extractor.functions,
        "classes": extractor.classes,
        "imports": extractor.imports
    }
