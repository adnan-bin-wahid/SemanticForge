import os
from pathlib import Path
from typing import List

def discover_python_files(root_path: Path) -> List[Path]:
    """
    Recursively discovers all Python files (`.py`) in a given directory.

    Args:
        root_path: The root directory to start the search from.

    Returns:
        A list of Path objects for all discovered Python files.
    """
    python_files = []
    for root, _, files in os.walk(root_path):
        for file in files:
            if file.endswith(".py"):
                python_files.append(Path(root) / file)
    return python_files
