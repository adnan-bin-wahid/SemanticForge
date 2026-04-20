"""
Diff Generation Module for Sub-phase 5.5

Produces standard `.diff` format patches comparing original code with LLM-generated code.
"""

import difflib
from typing import Optional
from pathlib import Path


class DiffGenerator:
    """
    Generates unified diffs between original and generated code.
    
    Produces standard `.diff` format suitable for patch files and version control.
    """
    
    def __init__(self):
        """Initialize the diff generator."""
        pass
    
    def generate_unified_diff(
        self,
        original_content: str,
        generated_content: str,
        file_path: str = "code.py",
        original_label: str = "original",
        generated_label: str = "generated"
    ) -> str:
        """
        Generate a unified diff between original and generated code.
        
        Args:
            original_content (str): The original source code
            generated_content (str): The LLM-generated code
            file_path (str): Path/name of the file being compared
            original_label (str): Label for original version (default: "original")
            generated_label (str): Label for generated version (default: "generated")
        
        Returns:
            str: Unified diff format as string
        
        Example:
            >>> generator = DiffGenerator()
            >>> diff = generator.generate_unified_diff(
            ...     "def hello():\\n    return 'world'",
            ...     "def hello_world():\\n    return 'Hello, World!'",
            ...     "utils/greeting.py"
            ... )
        """
        # Split content into lines for comparison
        original_lines = original_content.splitlines(keepends=True)
        generated_lines = generated_content.splitlines(keepends=True)
        
        # Generate unified diff
        diff = difflib.unified_diff(
            original_lines,
            generated_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            fromfiledate=original_label,
            tofiledate=generated_label,
            lineterm=""
        )
        
        # Convert to string
        diff_text = '\n'.join(diff)
        
        return diff_text
    
    def generate_context_diff(
        self,
        original_content: str,
        generated_content: str,
        file_path: str = "code.py",
        num_lines: int = 3
    ) -> str:
        """
        Generate a context diff (shows surrounding lines for context).
        
        More verbose than unified diff but easier to read manually.
        
        Args:
            original_content (str): The original source code
            generated_content (str): The LLM-generated code
            file_path (str): Path/name of the file being compared
            num_lines (int): Number of context lines to show (default: 3)
        
        Returns:
            str: Context diff format as string
        """
        original_lines = original_content.splitlines(keepends=True)
        generated_lines = generated_content.splitlines(keepends=True)
        
        diff = difflib.context_diff(
            original_lines,
            generated_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm=""
        )
        
        diff_text = '\n'.join(diff)
        return diff_text
    
    def get_diff_stats(
        self,
        original_content: str,
        generated_content: str
    ) -> dict:
        """
        Get statistics about the differences.
        
        Args:
            original_content (str): The original source code
            generated_content (str): The LLM-generated code
        
        Returns:
            dict: Statistics including:
                - lines_added: Number of lines added
                - lines_removed: Number of lines removed
                - lines_modified: Number of lines modified
                - total_changes: Total number of changed lines
                - similarity_ratio: Similarity ratio (0.0 to 1.0)
        """
        original_lines = original_content.splitlines()
        generated_lines = generated_content.splitlines()
        
        # Calculate similarity
        matcher = difflib.SequenceMatcher(None, original_lines, generated_lines)
        similarity_ratio = matcher.ratio()
        
        # Get opcodes to count changes
        opcodes = matcher.get_opcodes()
        
        lines_added = 0
        lines_removed = 0
        lines_modified = 0
        
        for tag, i1, i2, j1, j2 in opcodes:
            if tag == 'insert':
                lines_added += (j2 - j1)
            elif tag == 'delete':
                lines_removed += (i2 - i1)
            elif tag == 'replace':
                lines_modified += max(i2 - i1, j2 - j1)
        
        return {
            "lines_added": lines_added,
            "lines_removed": lines_removed,
            "lines_modified": lines_modified,
            "total_changes": lines_added + lines_removed + lines_modified,
            "similarity_ratio": round(similarity_ratio, 4),
            "original_lines": len(original_lines),
            "generated_lines": len(generated_lines),
            "identical": original_content == generated_content
        }
    
    def generate_side_by_side_diff(
        self,
        original_content: str,
        generated_content: str,
        width: int = 80
    ) -> str:
        """
        Generate a side-by-side diff (human-readable).
        
        Args:
            original_content (str): The original source code
            generated_content (str): The LLM-generated code
            width (int): Width of each side (default: 80 chars)
        
        Returns:
            str: Formatted side-by-side comparison
        """
        original_lines = original_content.splitlines()
        generated_lines = generated_content.splitlines()
        
        output = []
        output.append("SIDE-BY-SIDE COMPARISON".center(width * 2 + 5))
        output.append("=" * (width * 2 + 5))
        output.append(f"{'ORIGINAL' : <{width}} | {'GENERATED' : <{width}}")
        output.append("-" * (width * 2 + 5))
        
        max_lines = max(len(original_lines), len(generated_lines))
        
        for i in range(max_lines):
            orig_line = original_lines[i][:width] if i < len(original_lines) else ""
            gen_line = generated_lines[i][:width] if i < len(generated_lines) else ""
            
            # Pad lines to width
            orig_line = f"{orig_line:<{width}}"
            gen_line = f"{gen_line:<{width}}"
            
            # Mark changes
            if orig_line.rstrip() != gen_line.rstrip():
                marker = " * "
            else:
                marker = " | "
            
            output.append(f"{orig_line}{marker}{gen_line}")
        
        return "\n".join(output)
    
    def is_significant_diff(
        self,
        original_content: str,
        generated_content: str,
        threshold: float = 0.85
    ) -> bool:
        """
        Determine if the difference is significant.
        
        Args:
            original_content (str): The original source code
            generated_content (str): The LLM-generated code
            threshold (float): Similarity threshold (0.0-1.0). 
                              Returns True if similarity < threshold (default: 0.85)
        
        Returns:
            bool: True if difference is significant
        """
        if original_content == generated_content:
            return False
        
        stats = self.get_diff_stats(original_content, generated_content)
        return stats["similarity_ratio"] < threshold
    
    def save_patch_file(
        self,
        patch_content: str,
        output_path: str
    ) -> bool:
        """
        Save patch content to a file.
        
        Args:
            patch_content (str): The diff/patch content
            output_path (str): Path where to save the patch file
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text(patch_content, encoding='utf-8')
            return True
        except Exception as e:
            print(f"Error saving patch file: {str(e)}")
            return False
    
    def load_patch_file(self, patch_path: str) -> Optional[str]:
        """
        Load patch content from a file.
        
        Args:
            patch_path (str): Path to the patch file
        
        Returns:
            Optional[str]: Patch content or None if error
        """
        try:
            return Path(patch_path).read_text(encoding='utf-8')
        except Exception as e:
            print(f"Error loading patch file: {str(e)}")
            return None
