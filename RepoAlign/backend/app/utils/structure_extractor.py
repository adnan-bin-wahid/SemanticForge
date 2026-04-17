import ast
from typing import List, Dict, Any, Optional

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
    def __init__(self):
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
        # Start collecting calls for this new function context
        original_calls_context = self._current_function_calls
        self._current_function_calls = []

        # Visit children to find calls within this function
        self.generic_visit(node)

        function_data = {
            "name": node.name,
            "lineno": node.lineno,
            "end_lineno": node.end_lineno,
            "args": [arg.arg for arg in node.args.args],
            "calls": self._current_function_calls
        }

        if self._current_class_methods is not None:
             self._current_class_methods.append(function_data)
        else:
            self.functions.append(function_data)

        # Restore previous call context
        self._current_function_calls = original_calls_context

    def visit_ClassDef(self, node: ast.ClassDef):
        original_methods_context = self._current_class_methods
        self._current_class_methods = []
        
        # Visit the body of the class to find methods
        for child in node.body:
            if isinstance(child, ast.FunctionDef):
                self.visit_FunctionDef(child)

        self.classes.append({
            "name": node.name,
            "lineno": node.lineno,
            "end_lineno": node.end_lineno,
            "bases": [base.id for base in node.bases if isinstance(base, ast.Name)],
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
