"""
[PHASE 8.2] Git Diff Polling Service
Provides an alternative file change detection mechanism using git diff.
Offers a robust, Git-based strategy for monitoring repository changes.
"""

import subprocess
import threading
import logging
import time
from pathlib import Path
from queue import Queue, Empty
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@dataclass
class GitChangeEvent:
    """Represents a file change detected by git diff"""
    event_type: str  # 'modified', 'added', 'deleted', 'renamed'
    file_path: str
    timestamp: str
    git_status_code: str  # M (modified), A (added), D (deleted), R (renamed), etc.


class GitDiffPoller:
    """
    Monitors repository changes using git diff.
    Periodically polls git diff and git status to detect file changes.
    
    Thread-safe with a change queue for consuming detected changes.
    """
    
    def __init__(self, repo_path: str, poll_interval: int = 2, 
                 filter_extensions: Optional[List[str]] = None,
                 ignore_dirs: Optional[List[str]] = None):
        """
        Initialize the Git Diff Poller.
        
        Args:
            repo_path: Path to the Git repository to monitor
            poll_interval: Seconds between git diff polls (default: 2)
            filter_extensions: Only track these file extensions, e.g., ['.py', '.pyi']
            ignore_dirs: Directories to ignore when detecting changes
        """
        self.repo_path = Path(repo_path)
        self.poll_interval = poll_interval
        self.filter_extensions = filter_extensions or ['.py', '.pyi']
        self.ignore_dirs = ignore_dirs or [
            '__pycache__', '.git', '.pytest_cache', '.mypy_cache',
            '.venv', 'venv', 'node_modules'
        ]
        
        self._is_running = False
        self._poller_thread: Optional[threading.Thread] = None
        self._change_queue: Queue[GitChangeEvent] = Queue()
        self._lock = threading.Lock()
        self._start_time: Optional[datetime] = None
        self._event_counts = {'modified': 0, 'added': 0, 'deleted': 0, 'renamed': 0}
        self._last_commit_hash: Optional[str] = None
        self._tracked_files: set = set()
        
        # Initialize tracking of currently tracked files
        self._refresh_tracked_files()
    
    def start(self) -> Dict:
        """
        Start the Git Diff Poller polling thread.
        
        Returns:
            Dictionary with status, message, repo_path, and start_time
        """
        with self._lock:
            if self._is_running:
                return {
                    'status': 'already_running',
                    'message': 'Git diff poller is already running',
                    'repo_path': str(self.repo_path),
                    'start_time': self._start_time.isoformat() if self._start_time else None
                }
            
            try:
                # Verify it's a git repository
                if not (self.repo_path / '.git').exists():
                    return {
                        'status': 'failed',
                        'error': f'{self.repo_path} is not a Git repository'
                    }
                
                self._is_running = True
                self._start_time = datetime.utcnow()
                self._event_counts = {'modified': 0, 'added': 0, 'deleted': 0, 'renamed': 0}
                self._last_commit_hash = self._get_current_commit_hash()
                self._tracked_files.clear()
                self._refresh_tracked_files()
                
                self._poller_thread = threading.Thread(
                    target=self._polling_loop,
                    name='GitDiffPoller',
                    daemon=True
                )
                self._poller_thread.start()
                
                logger.info(f'[PHASE 8.2] Git diff poller started for {self.repo_path}')
                
                return {
                    'status': 'started',
                    'message': 'Git diff poller started successfully',
                    'repo_path': str(self.repo_path),
                    'start_time': self._start_time.isoformat()
                }
            
            except Exception as e:
                self._is_running = False
                logger.error(f'[PHASE 8.2] Failed to start git diff poller: {e}')
                return {
                    'status': 'failed',
                    'error': str(e)
                }
    
    def stop(self) -> Dict:
        """
        Stop the Git Diff Poller.
        
        Returns:
            Dictionary with status, message, and event statistics
        """
        with self._lock:
            if not self._is_running:
                return {
                    'status': 'not_running',
                    'message': 'Git diff poller is not running'
                }
            
            self._is_running = False
        
        # Wait for thread to finish (with timeout)
        if self._poller_thread and self._poller_thread.is_alive():
            self._poller_thread.join(timeout=5)
        
        logger.info(f'[PHASE 8.2] Git diff poller stopped. Total events: {sum(self._event_counts.values())}')
        
        return {
            'status': 'stopped',
            'message': 'Git diff poller stopped successfully',
            'events_detected': sum(self._event_counts.values()),
            'events_by_type': self._event_counts.copy()
        }
    
    def get_status(self) -> Dict:
        """
        Get current status of the Git Diff Poller.
        
        Returns:
            Dictionary with is_running, uptime, and event statistics
        """
        with self._lock:
            uptime_seconds = (datetime.utcnow() - self._start_time).total_seconds() \
                if self._start_time else 0
            
            return {
                'is_running': self._is_running,
                'repo_path': str(self.repo_path),
                'start_time': self._start_time.isoformat() if self._start_time else None,
                'uptime_seconds': uptime_seconds,
                'poll_interval_seconds': self.poll_interval,
                'events_detected': sum(self._event_counts.values()),
                'events_by_type': self._event_counts.copy(),
                'queue_size': self._change_queue.qsize(),
                'current_commit': self._last_commit_hash[:8] if self._last_commit_hash else None
            }
    
    def get_pending_changes(self, max_changes: int = 100) -> List[Dict]:
        """
        Peek at pending changes without removing them from the queue.
        
        Args:
            max_changes: Maximum number of changes to retrieve
        
        Returns:
            List of change dictionaries (event_type, file_path, timestamp)
        """
        if not self._is_running:
            return []
        
        changes = []
        temp_queue = []
        
        # Extract items temporarily
        for _ in range(max_changes):
            try:
                event = self._change_queue.get_nowait()
                temp_queue.append(event)
                changes.append({
                    'event_type': event.event_type,
                    'file_path': event.file_path,
                    'timestamp': event.timestamp,
                    'git_status': event.git_status_code
                })
            except Empty:
                break
        
        # Put them back
        for event in temp_queue:
            self._change_queue.put(event)
        
        return changes
    
    def consume_changes(self, max_changes: int = 100) -> List[Dict]:
        """
        Get and remove pending changes from the queue.
        
        Args:
            max_changes: Maximum number of changes to retrieve
        
        Returns:
            List of change dictionaries (event_type, file_path, timestamp)
        """
        if not self._is_running:
            return []
        
        changes = []
        for _ in range(max_changes):
            try:
                event = self._change_queue.get_nowait()
                changes.append({
                    'event_type': event.event_type,
                    'file_path': event.file_path,
                    'timestamp': event.timestamp,
                    'git_status': event.git_status_code
                })
            except Empty:
                break
        
        logger.debug(f'[PHASE 8.2] Consumed {len(changes)} changes from queue')
        return changes
    
    def clear_queue(self) -> Dict:
        """Clear all pending changes from the queue."""
        cleared_count = 0
        while True:
            try:
                self._change_queue.get_nowait()
                cleared_count += 1
            except Empty:
                break
        
        logger.info(f'[PHASE 8.2] Cleared {cleared_count} changes from queue')
        return {
            'status': 'cleared',
            'changes_cleared': cleared_count
        }
    
    # ========== Private Methods ==========
    
    def _polling_loop(self):
        """Main polling loop that runs in the poller thread."""
        logger.info(f'[PHASE 8.2] Polling loop started with {self.poll_interval}s interval')
        
        while self._is_running:
            try:
                changes = self._detect_changes()
                
                for change in changes:
                    self._change_queue.put(change)
                    with self._lock:
                        self._event_counts[change.event_type] += 1
                
                if changes:
                    logger.debug(f'[PHASE 8.2] Detected {len(changes)} changes in poll cycle')
                
            except Exception as e:
                logger.error(f'[PHASE 8.2] Error during polling: {e}')
            
            # Sleep with early exit capability
            for _ in range(self.poll_interval * 10):
                if not self._is_running:
                    break
                time.sleep(0.1)
    
    def _detect_changes(self) -> List[GitChangeEvent]:
        """
        Detect changes using git diff and git status.
        
        Returns:
            List of detected change events
        """
        changes = []
        
        try:
            # Get git diff to find modified files
            diff_output = self._run_git_command(['diff', '--name-status', 'HEAD'])
            
            # Get git status for untracked/new files
            status_output = self._run_git_command(['status', '--porcelain'])
            
            # Parse diff output (for committed changes)
            for line in diff_output.strip().split('\n'):
                if not line.strip():
                    continue
                
                parts = line.split('\t')
                if len(parts) >= 2:
                    status_code = parts[0]
                    file_path = parts[1]
                    
                    if self._should_track(file_path):
                        event_type = self._map_git_status_to_event(status_code)
                        changes.append(GitChangeEvent(
                            event_type=event_type,
                            file_path=file_path,
                            timestamp=datetime.utcnow().isoformat(),
                            git_status_code=status_code
                        ))
            
            # Parse status output (for working directory changes)
            for line in status_output.strip().split('\n'):
                if not line.strip():
                    continue
                
                status_code = line[:2]
                file_path = line[3:].strip()
                
                # Skip already handled files and non-tracked files
                if file_path.startswith('.') or not self._should_track(file_path):
                    continue
                
                # Only consider modified/added files from status
                if status_code.strip() in ['M', 'A', '??', 'AM', 'AA']:
                    if not any(c.file_path == file_path for c in changes):
                        event_type = 'added' if '?' in status_code else 'modified'
                        changes.append(GitChangeEvent(
                            event_type=event_type,
                            file_path=file_path,
                            timestamp=datetime.utcnow().isoformat(),
                            git_status_code=status_code
                        ))
            
        except Exception as e:
            logger.warning(f'[PHASE 8.2] Error detecting changes: {e}')
        
        return changes
    
    def _run_git_command(self, args: List[str]) -> str:
        """
        Run a git command and return the output.
        
        Args:
            args: Git command arguments (e.g., ['diff', '--name-status', 'HEAD'])
        
        Returns:
            Command output as string
        """
        try:
            result = subprocess.run(
                ['git'] + args,
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout
        except subprocess.TimeoutExpired:
            logger.warning(f'[PHASE 8.2] Git command timed out: {args}')
            return ''
        except Exception as e:
            logger.warning(f'[PHASE 8.2] Failed to run git {args[0]}: {e}')
            return ''
    
    def _get_current_commit_hash(self) -> Optional[str]:
        """Get the current commit hash."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip()
        except Exception:
            return None
    
    def _refresh_tracked_files(self):
        """Refresh the set of currently tracked files in the repository."""
        try:
            result = subprocess.run(
                ['git', 'ls-files'],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                timeout=10
            )
            self._tracked_files = set(result.stdout.strip().split('\n'))
        except Exception:
            self._tracked_files = set()
    
    def _should_track(self, file_path: str) -> bool:
        """Check if a file should be tracked based on extension and directory filters."""
        path = Path(file_path)
        
        # Check extension filter
        if self.filter_extensions and path.suffix not in self.filter_extensions:
            return False
        
        # Check ignore directories
        for ignore_dir in self.ignore_dirs:
            if ignore_dir in path.parts:
                return False
        
        return True
    
    @staticmethod
    def _map_git_status_to_event(status_code: str) -> str:
        """Map git status code to event type."""
        code_map = {
            'M': 'modified',
            'A': 'added',
            'D': 'deleted',
            'R': 'renamed',
            'C': 'modified',  # copied (treat as modified)
            'T': 'modified',  # type change (treat as modified)
        }
        return code_map.get(status_code[0], 'modified')


# Global poller instance (singleton pattern)
_git_diff_poller: Optional[GitDiffPoller] = None
_poller_lock = threading.Lock()


def get_git_diff_poller(repo_path: str = '/app/test-project',
                        poll_interval: int = 2) -> GitDiffPoller:
    """
    Get or create the global Git Diff Poller instance.
    
    Args:
        repo_path: Path to the repository to monitor
        poll_interval: Seconds between polls
    
    Returns:
        GitDiffPoller instance
    """
    global _git_diff_poller
    
    with _poller_lock:
        if _git_diff_poller is None:
            _git_diff_poller = GitDiffPoller(
                repo_path=repo_path,
                poll_interval=poll_interval
            )
        return _git_diff_poller
