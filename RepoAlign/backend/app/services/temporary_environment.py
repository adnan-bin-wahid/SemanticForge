"""
Temporary Environment Service

This service manages the lifecycle of temporary sandboxed environments
where patches can be safely applied and tested without affecting the original repository.
"""

import os
from typing import Optional, Tuple
from pathlib import Path
from app.utils.patch_applier import PatchApplier


class TemporaryEnvironmentService:
    """
    Manages temporary sandboxed environments for patch testing.
    
    This service:
    1. Creates isolated temporary directories
    2. Copies repository files to the sandbox
    3. Applies patches safely
    4. Provides cleanup mechanisms
    """

    def __init__(self):
        """Initialize the temporary environment service."""
        self.temp_directories = []

    def create_sandbox_for_patch(
        self,
        source_file_path: str,
        file_relative_path: str,
        generated_code: str
    ) -> Tuple[str, str]:
        """
        Create a temporary sandbox environment with a patched file.
        
        This method:
        1. Creates a temporary directory
        2. Copies the file to the temporary directory
        3. Applies the generated code to the temporary copy
        4. Tracks the temporary directory for cleanup
        
        Args:
            source_file_path (str): Path to the original file
            file_relative_path (str): Relative path to preserve in temporary structure
                                     (e.g., "src/utils/helpers.py")
            generated_code (str): The generated/patched code
        
        Returns:
            Tuple[str, str]: (temp_directory_path, temp_file_path)
                           - temp_directory_path: Root of the sandbox
                           - temp_file_path: Path to the patched file
        
        Raises:
            FileNotFoundError: If source file doesn't exist
            IOError: If copy or patch operations fail
        """
        # Create temporary directory
        temp_dir = PatchApplier.create_temp_directory()
        self.temp_directories.append(temp_dir)

        try:
            # Copy file to temporary directory with relative path preservation
            temp_file_path = PatchApplier.copy_file_to_temp(
                source_file_path,
                temp_dir,
                relative_path=file_relative_path
            )

            # Apply the generated code
            PatchApplier.apply_patch_to_file(temp_file_path, generated_code)

            return temp_dir, temp_file_path

        except Exception as e:
            # Cleanup on failure
            PatchApplier.cleanup_temp_directory(temp_dir)
            self.temp_directories.remove(temp_dir)
            raise e

    def create_sandbox_for_patch_from_content(
        self,
        file_relative_path: str,
        original_content: str,
        generated_code: str
    ) -> Tuple[str, str]:
        """
        Create a temporary sandbox environment with content (no file read needed).
        
        This method:
        1. Creates a temporary directory
        2. Writes the original content to a file in the temporary directory
        3. Applies the generated code to the temporary copy
        4. Tracks the temporary directory for cleanup
        
        Args:
            file_relative_path (str): Relative path to preserve in temporary structure
                                     (e.g., "src/utils/helpers.py")
            original_content (str): Original file content
            generated_code (str): The generated/patched code
        
        Returns:
            Tuple[str, str]: (temp_directory_path, temp_file_path)
                           - temp_directory_path: Root of the sandbox
                           - temp_file_path: Path to the patched file
        
        Raises:
            IOError: If write or patch operations fail
        """
        # Create temporary directory
        temp_dir = PatchApplier.create_temp_directory()
        self.temp_directories.append(temp_dir)

        try:
            # Create directory structure and write original content
            temp_file_path = os.path.join(temp_dir, file_relative_path)
            os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)
            
            with open(temp_file_path, 'w', encoding='utf-8') as f:
                f.write(original_content)

            # Apply the generated code
            PatchApplier.apply_patch_to_file(temp_file_path, generated_code)

            return temp_dir, temp_file_path

        except Exception as e:
            # Cleanup on failure
            PatchApplier.cleanup_temp_directory(temp_dir)
            self.temp_directories.remove(temp_dir)
            raise e

    def create_sandbox_for_repository(
        self,
        source_repo_path: str,
        ignore_patterns: Optional[list] = None
    ) -> str:
        """
        Create a temporary sandbox copy of an entire repository.
        
        This is useful for running tests or validators on the complete codebase.
        
        Args:
            source_repo_path (str): Path to the source repository
            ignore_patterns (Optional[list]): Additional patterns to ignore during copy
        
        Returns:
            str: Path to the temporary repository copy
            
        Raises:
            FileNotFoundError: If source repository doesn't exist
        """
        temp_dir = PatchApplier.create_temp_directory()
        self.temp_directories.append(temp_dir)

        try:
            repo_copy = PatchApplier.copy_directory_to_temp(
                source_repo_path,
                temp_dir,
                ignore_patterns=ignore_patterns
            )
            return repo_copy

        except Exception as e:
            PatchApplier.cleanup_temp_directory(temp_dir)
            self.temp_directories.remove(temp_dir)
            raise e

    def apply_patch_to_sandbox(
        self,
        sandbox_path: str,
        target_file_relative_path: str,
        generated_code: str
    ) -> str:
        """
        Apply a patch to a file within an existing sandbox.
        
        Args:
            sandbox_path (str): Path to the sandbox directory
            target_file_relative_path (str): Relative path to the target file within sandbox
            generated_code (str): The generated code to apply
        
        Returns:
            str: Path to the patched file
            
        Raises:
            IOError: If patch operation fails
        """
        target_file_path = os.path.join(sandbox_path, target_file_relative_path)

        # Create parent directories if needed
        os.makedirs(os.path.dirname(target_file_path), exist_ok=True)

        # Apply the patch
        PatchApplier.apply_patch_to_file(target_file_path, generated_code)

        return target_file_path

    def cleanup_single_sandbox(self, sandbox_path: str) -> bool:
        """
        Clean up a single temporary sandbox.
        
        Args:
            sandbox_path (str): Path to the sandbox to clean up
        
        Returns:
            bool: True if successful, False otherwise
        """
        success = PatchApplier.cleanup_temp_directory(sandbox_path)
        if success and sandbox_path in self.temp_directories:
            self.temp_directories.remove(sandbox_path)
        return success

    def cleanup_all_sandboxes(self) -> bool:
        """
        Clean up all tracked temporary sandboxes.
        
        Returns:
            bool: True if all cleanups were successful, False if any failed
        """
        all_success = True
        for temp_dir in self.temp_directories[:]:
            success = PatchApplier.cleanup_temp_directory(temp_dir)
            if success:
                self.temp_directories.remove(temp_dir)
            else:
                all_success = False
        return all_success

    def get_sandbox_size_mb(self, sandbox_path: str) -> float:
        """
        Get the total size of a sandbox in megabytes.
        
        Args:
            sandbox_path (str): Path to the sandbox
        
        Returns:
            float: Size in megabytes
        """
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(sandbox_path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
        return total_size / (1024 * 1024)

    def list_active_sandboxes(self) -> list:
        """
        List all currently active (uncleanedUp) sandboxes.
        
        Returns:
            list: List of paths to active temporary directories
        """
        return self.temp_directories.copy()

    def __del__(self):
        """Cleanup all sandboxes on service destruction."""
        self.cleanup_all_sandboxes()
