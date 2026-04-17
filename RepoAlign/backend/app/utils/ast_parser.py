import ast
from pathlib import Path
from typing import Optional

def parse_file_to_ast(file_path: Path) -> Optional[ast.AST]:
    """
    Reads a Python file and parses it into an Abstract Syntax Tree (AST).

    Args:
        file_path: The path to the Python file.

    Returns:
        An ast.AST object if parsing is successful, otherwise None.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as source_file:
            source_code = source_file.read()
            return ast.parse(source_code, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError) as e:
        print(f"Error parsing {file_path}: {e}")
        return None
