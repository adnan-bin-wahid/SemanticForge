import ast
from typing import Optional

def parse_content_to_ast(content: str, filename: str = "<unknown>") -> Optional[ast.AST]:
    """
    Parses Python code content into an Abstract Syntax Tree (AST).

    Args:
        content: The Python code as a string.
        filename: The name of the file being parsed, for error reporting.

    Returns:
        An ast.AST object if parsing is successful, otherwise None.
    """
    try:
        return ast.parse(content, filename=filename)
    except (SyntaxError, UnicodeDecodeError) as e:
        print(f"Error parsing {filename}: {e}")
        return None

