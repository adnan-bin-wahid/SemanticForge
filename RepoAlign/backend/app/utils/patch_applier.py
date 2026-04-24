"""
Temporary Patch Application Utility

This module provides functionality to safely apply patches to a temporary copy
of the repository in a sandboxed directory. It allows for non-destructive testing
and validation of generated patches without modifying the original codebase.
"""

import shutil
import tempfile
import os
from pathlib import Path
from typing import Tuple, Optional
import subprocess


class PatchApplier:
    """
    Applies patches to temporary copies of files/directories safely.
    
    This utility creates isolated sandboxes where patches can be tested
    without affecting the original repository.
    """

    @staticmethod
    def create_temp_directory() -> str:
        """
        Create a temporary directory for patch application.
        
        Returns:
            str: Path to the created temporary directory.
            
        Example:
            >>> temp_dir = PatchApplier.create_temp_directory()
            >>> print(temp_dir)
            /tmp/tmpabc123xyz
        """
        temp_dir = tempfile.mkdtemp(prefix="repoalign_patch_")
        return temp_dir

    @staticmethod
    def copy_file_to_temp(
        source_file: str,
        temp_directory: str,
        relative_path: Optional[str] = None
    ) -> str:
        """
        Copy a single file to the temporary directory.
        
        Args:
            source_file (str): Path to the source file to copy
            temp_directory (str): Destination temporary directory
            relative_path (Optional[str]): Relative path to preserve in temp dir.
                                          If None, uses just the filename.
        
        Returns:
            str: Path to the copied file in the temporary directory.
            
        Raises:
            FileNotFoundError: If source file doesn't exist
            IOError: If copy operation fails
        """
        if not os.path.exists(source_file):
            raise FileNotFoundError(f"Source file not found: {source_file}")

        if relative_path:
            temp_file_path = os.path.join(temp_directory, relative_path)
            os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)
        else:
            temp_file_path = os.path.join(temp_directory, os.path.basename(source_file))

        shutil.copy2(source_file, temp_file_path)
        return temp_file_path

    @staticmethod
    def copy_directory_to_temp(
        source_directory: str,
        temp_directory: str,
        ignore_patterns: Optional[list] = None
    ) -> str:
        """
        Copy an entire directory tree to the temporary directory.
        
        Args:
            source_directory (str): Path to the source directory
            temp_directory (str): Destination temporary directory
            ignore_patterns (Optional[list]): List of patterns to ignore
                                             (e.g., ['.git', '__pycache__', '*.pyc'])
        
        Returns:
            str: Path to the copied directory structure in temp location.
            
        Raises:
            FileNotFoundError: If source directory doesn't exist
            IOError: If copy operation fails
        """
        if not os.path.isdir(source_directory):
            raise FileNotFoundError(f"Source directory not found: {source_directory}")

        # Define ignore patterns for copying
        default_ignore_patterns = ['.git', '__pycache__', '.pytest_cache', '*.pyc', '.venv', 'venv', 'node_modules']
        patterns_to_ignore = default_ignore_patterns
        if ignore_patterns:
            patterns_to_ignore.extend(ignore_patterns)

        def ignore_patterns_func(directory, files):
            ignored = []
            for file in files:
                for pattern in patterns_to_ignore:
                    if pattern.startswith('*'):
                        if file.endswith(pattern[1:]):
                            ignored.append(file)
                            break
                    elif file == pattern:
                        ignored.append(file)
                        break
            return ignored

        repo_name = os.path.basename(source_directory.rstrip(os.sep))
        dest_path = os.path.join(temp_directory, repo_name)
        
        shutil.copytree(
            source_directory,
            dest_path,
            ignore=ignore_patterns_func,
            dirs_exist_ok=True
        )
        
        return dest_path

    @staticmethod
    def apply_patch_to_file(
        temp_file_path: str,
        generated_code: str
    ) -> bool:
        """
        Apply generated code directly to a file in the temporary directory.
        
        This replaces the entire file content with the generated code.
        
        Args:
            temp_file_path (str): Path to the file in the temporary directory
            generated_code (str): The generated code to write to the file
        
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            IOError: If write operation fails
            OSError: If file path is invalid
        """
        try:
            with open(temp_file_path, 'w', encoding='utf-8') as f:
                f.write(generated_code)
            return True
        except (IOError, OSError) as e:
            raise IOError(f"Failed to apply patch to {temp_file_path}: {str(e)}")

    @staticmethod
    def apply_unified_diff_patch(
        temp_directory: str,
        patch_content: str,
        strip_level: int = 1
    ) -> Tuple[bool, str]:
        """
        Apply a unified diff patch to the temporary directory using the 'patch' command.
        
        This is useful for traditional .patch files and maintains line-by-line changes.
        
        Args:
            temp_directory (str): Path to the temporary directory (root of patch)
            patch_content (str): The complete unified diff patch content
            strip_level (int): Number of leading path components to strip (default: 1)
        
        Returns:
            Tuple[bool, str]: (success: bool, output_message: str)
                             - If successful: (True, "Patch applied successfully")
                             - If failed: (False, error_message)
        """
        try:
            # Create a temporary patch file
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.patch',
                delete=False,
                encoding='utf-8'
            ) as patch_file:
                patch_file.write(patch_content)
                patch_file_path = patch_file.name

            try:
                # Apply the patch using the 'patch' command
                cmd = ['patch', f'-p{strip_level}', '-d', temp_directory, '-i', patch_file_path]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                os.unlink(patch_file_path)

                if result.returncode == 0:
                    return True, f"Patch applied successfully: {result.stdout}"
                else:
                    return False, f"Patch failed: {result.stderr}"

            except FileNotFoundError:
                os.unlink(patch_file_path)
                return False, "patch command not found. Ensure GNU patch is installed."
            except subprocess.TimeoutExpired:
                os.unlink(patch_file_path)
                return False, "Patch application timed out."

        except Exception as e:
            return False, f"Error applying patch: {str(e)}"

    @staticmethod
    def cleanup_temp_directory(temp_directory: str) -> bool:
        """
        Clean up and remove a temporary directory and all its contents.
        
        Args:
            temp_directory (str): Path to the temporary directory to remove
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if os.path.exists(temp_directory):
                shutil.rmtree(temp_directory)
            return True
        except Exception as e:
            print(f"Warning: Failed to cleanup temporary directory {temp_directory}: {str(e)}")
            return False

    @staticmethod
    def get_temp_file_path(
        temp_directory: str,
        original_file_path: str
    ) -> str:
        """
        Get the corresponding path in the temporary directory for an original file path.
        
        Args:
            temp_directory (str): Root of the temporary directory
            original_file_path (str): Original file path (relative or absolute)
        
        Returns:
            str: Corresponding path in the temporary directory
        """
        # If original_file_path is absolute, make it relative
        if os.path.isabs(original_file_path):
            original_file_path = os.path.relpath(original_file_path)

        return os.path.join(temp_directory, original_file_path)

    @staticmethod
    def verify_patch_application(
        temp_file_path: str,
        expected_content: str
    ) -> bool:
        """
        Verify that a patch was applied correctly by comparing file content.
        
        Args:
            temp_file_path (str): Path to the patched file
            expected_content (str): Expected content after patching
        
        Returns:
            bool: True if content matches, False otherwise
        """
        try:
            with open(temp_file_path, 'r', encoding='utf-8') as f:
                actual_content = f.read()
            return actual_content == expected_content
        except Exception:
            return False
