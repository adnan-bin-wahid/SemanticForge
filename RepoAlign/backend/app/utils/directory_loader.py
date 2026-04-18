import os
from pathlib import Path
from typing import List
from app.models.ingestion import FileContent, IngestionRequest


class DirectoryLoader:
    """Utility to load Python files from a directory."""
    
    @staticmethod
    def load_directory(directory_path: str) -> IngestionRequest:
        """
        Load all Python files from a directory recursively.
        
        Args:
            directory_path: Path to the root directory to load
            
        Returns:
            IngestionRequest with all Python files
        """
        files: List[FileContent] = []
        path = Path(directory_path)
        
        if not path.exists():
            raise ValueError(f"Directory does not exist: {directory_path}")
        
        # Find all Python files recursively
        for py_file in path.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Use relative path from the root directory
                relative_path = str(py_file.relative_to(path))
                
                files.append(FileContent(
                    path=relative_path,
                    content=content
                ))
            except Exception as e:
                print(f"Error reading file {py_file}: {e}")
        
        if not files:
            raise ValueError(f"No Python files found in {directory_path}")
        
        return IngestionRequest(files=files)
