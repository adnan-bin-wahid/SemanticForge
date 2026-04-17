import ast
from typing import List, Dict, Any, Union

class StructureExtractor(ast.NodeVisitor):
    """
    An AST visitor to extract top-level function and class definitions.
    """
    def __init__(self):
        self.functions: List[Dict[str, Any]] = []
        self.classes: List[Dict[str, Any]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """
        Visit a function definition and extract its details.
        """
        self.functions.append({
            "name": node.name,
            "lineno": node.lineno,
            "end_lineno": node.end_lineno,
            "args": [arg.arg for arg in node.args.args]
        })
        # Do not visit children of functions to only get top-level ones for now
        # self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        """
        Visit a class definition and extract its details.
        """
        self.classes.append({
            "name": node.name,
            "lineno": node.lineno,
            "end_lineno": node.end_lineno,
            "bases": [base.id for base in node.bases if isinstance(base, ast.Name)],
            "methods": [
                n.name for n in node.body if isinstance(n, ast.FunctionDef)
            ]
        })
        # Do not visit children of classes to only get top-level ones for now
        # self.generic_visit(node)

def extract_structures(tree: ast.AST) -> Dict[str, List[Dict[str, Any]]]:
    """
    Extracts function and class definitions from an AST.

    Args:
        tree: The AST to analyze.

    Returns:
        A dictionary containing lists of extracted functions and classes.
    """
    extractor = StructureExtractor()
    extractor.visit(tree)
    return {
        "functions": extractor.functions,
        "classes": extractor.classes
    }
