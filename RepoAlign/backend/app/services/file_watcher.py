"""
Phase 8.1: File Watcher
Background process to monitor repository directory for file system events.
Uses watchdog library to detect file creation, deletion, and modification events.
"""

import logging
import threading
import time
from typing import Dict, List, Optional, Set
from pathlib import Path
from queue import Queue, Empty
from datetime import datetime

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = object  # Dummy base class for graceful degradation

logger = logging.getLogger(__name__)


class FileSystemChangeEvent:
    """Represents a detected file system change."""
    
    def __init__(self, event_type: str, file_path: str, timestamp: str = None):
        """
        Initialize a file system change event.
        
        Args:
            event_type: Type of event ('created', 'deleted', 'modified')
            file_path: Path to the file that changed
            timestamp: ISO format timestamp of the event
        """
        self.event_type = event_type
        self.file_path = file_path
        self.timestamp = timestamp or datetime.now().isoformat()
    
    def __repr__(self):
        return f"FileSystemChangeEvent({self.event_type}, {self.file_path})"
    
    def to_dict(self) -> Dict:
        """Convert event to dictionary."""
        return {
            "event_type": self.event_type,
            "file_path": self.file_path,
            "timestamp": self.timestamp
        }


class RepositoryFileSystemEventHandler(FileSystemEventHandler if WATCHDOG_AVAILABLE else object):
    """Handles file system events and queues them for processing."""
    
    def __init__(self, change_queue: Queue, repo_path: str):
        """
        Initialize the event handler.
        
        Args:
            change_queue: Queue to store detected changes
            repo_path: Root path of the repository being monitored
        """
        if WATCHDOG_AVAILABLE:
            super().__init__()
        self.change_queue = change_queue
        self.repo_path = repo_path
        self.python_extensions = {'.py', '.pyi'}
        self.ignored_patterns = {
            '__pycache__',
            '.git',
            '.pytest_cache',
            '.mypy_cache',
            '*.pyc',
            '*.pyo',
            '.venv',
            'venv',
            'node_modules'
        }
        
        logger.debug(f"[PHASE 8.1] RepositoryFileSystemEventHandler initialized for {repo_path}")
    
    def _should_process_path(self, path: str) -> bool:
        """
        Check if a file path should be processed.
        
        Args:
            path: File path to check
        
        Returns:
            True if the file should be processed, False otherwise
        """
        # Check if it's a Python file
        file_path = Path(path)
        if file_path.suffix not in self.python_extensions:
            return False
        
        # Check for ignored patterns
        parts = file_path.parts
        for pattern in self.ignored_patterns:
            if pattern in parts:
                return False
        
        return True
    
    def on_created(self, event):
        """Handle file creation event."""
        if event.is_directory:
            logger.debug(f"[PHASE 8.1] Directory created: {event.src_path}")
            return
        
        if self._should_process_path(event.src_path):
            change_event = FileSystemChangeEvent('created', event.src_path)
            self.change_queue.put(change_event)
            logger.info(f"[PHASE 8.1] File created: {event.src_path}")
    
    def on_deleted(self, event):
        """Handle file deletion event."""
        if event.is_directory:
            logger.debug(f"[PHASE 8.1] Directory deleted: {event.src_path}")
            return
        
        if self._should_process_path(event.src_path):
            change_event = FileSystemChangeEvent('deleted', event.src_path)
            self.change_queue.put(change_event)
            logger.info(f"[PHASE 8.1] File deleted: {event.src_path}")
    
    def on_modified(self, event):
        """Handle file modification event."""
        if event.is_directory:
            logger.debug(f"[PHASE 8.1] Directory modified: {event.src_path}")
            return
        
        if self._should_process_path(event.src_path):
            change_event = FileSystemChangeEvent('modified', event.src_path)
            self.change_queue.put(change_event)
            logger.debug(f"[PHASE 8.1] File modified: {event.src_path}")


class FileWatcher:
    """
    Background file system watcher for monitoring repository changes.
    Uses watchdog to detect file creation, deletion, and modification events.
    """
    
    def __init__(self, repo_path: str):
        """
        Initialize the file watcher.
        
        Args:
            repo_path: Root path of the repository to monitor
        """
        self.repo_path = repo_path
        self.observer = None
        self.change_queue = Queue()
        self.is_running = False
        self.start_time = None
        self.events_detected = 0
        self.events_by_type = {'created': 0, 'deleted': 0, 'modified': 0}
        
        logger.info(f"[PHASE 8.1] FileWatcher initialized for {repo_path}")
    
    def start(self) -> Dict[str, any]:
        """
        Start the file system watcher.
        
        Returns:
            Status dictionary with start information
        """
        if not WATCHDOG_AVAILABLE:
            logger.error("[PHASE 8.1] watchdog library not available. Install with: pip install watchdog")
            return {
                "status": "failed",
                "error": "watchdog library not installed. Run: pip install watchdog"
            }
        
        if self.is_running:
            logger.warning("[PHASE 8.1] File watcher is already running")
            return {
                "status": "already_running",
                "message": "File watcher is already running",
                "start_time": self.start_time.isoformat() if self.start_time else None
            }
        
        try:
            logger.info("[PHASE 8.1] Starting file system watcher...")
            
            # Create observer
            self.observer = Observer()
            
            # Create event handler
            event_handler = RepositoryFileSystemEventHandler(self.change_queue, self.repo_path)
            
            # Schedule observer to watch the repository
            self.observer.schedule(event_handler, self.repo_path, recursive=True)
            
            # Start observing
            self.observer.start()
            
            self.is_running = True
            self.start_time = datetime.now()
            
            logger.info(f"[PHASE 8.1] ✓ File watcher started successfully, monitoring {self.repo_path}")
            
            return {
                "status": "started",
                "message": "File watcher started successfully",
                "repo_path": self.repo_path,
                "start_time": self.start_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"[PHASE 8.1] Error starting file watcher: {str(e)}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def stop(self) -> Dict[str, any]:
        """
        Stop the file system watcher.
        
        Returns:
            Status dictionary with stop information
        """
        if not self.is_running:
            logger.warning("[PHASE 8.1] File watcher is not running")
            return {
                "status": "not_running",
                "message": "File watcher is not running"
            }
        
        try:
            logger.info("[PHASE 8.1] Stopping file system watcher...")
            
            if self.observer:
                self.observer.stop()
                self.observer.join(timeout=5)
            
            self.is_running = False
            
            logger.info(f"[PHASE 8.1] ✓ File watcher stopped")
            
            return {
                "status": "stopped",
                "message": "File watcher stopped successfully",
                "events_detected": self.events_detected,
                "events_by_type": self.events_by_type
            }
            
        except Exception as e:
            logger.error(f"[PHASE 8.1] Error stopping file watcher: {str(e)}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def get_status(self) -> Dict[str, any]:
        """
        Get the current status of the file watcher.
        
        Returns:
            Status dictionary with watcher information
        """
        uptime = None
        if self.start_time:
            uptime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "is_running": self.is_running,
            "repo_path": self.repo_path,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "uptime_seconds": round(uptime, 2) if uptime else None,
            "events_detected": self.events_detected,
            "events_by_type": self.events_by_type,
            "queue_size": self.change_queue.qsize()
        }
    
    def get_pending_changes(self, max_changes: int = 100) -> List[Dict]:
        """
        Retrieve pending changes from the queue.
        
        Does not remove them from the queue - use consume_changes() to remove.
        
        Args:
            max_changes: Maximum number of changes to retrieve
        
        Returns:
            List of change event dictionaries
        """
        changes = []
        
        # Peek at queue without removing
        for _ in range(min(max_changes, self.change_queue.qsize())):
            try:
                change = self.change_queue.get_nowait()
                changes.append(change.to_dict())
                # Put it back for now
                self.change_queue.put(change)
            except Empty:
                break
        
        return changes
    
    def consume_changes(self, max_changes: int = 100) -> List[Dict]:
        """
        Consume (remove from queue) pending changes.
        
        Args:
            max_changes: Maximum number of changes to consume
        
        Returns:
            List of change event dictionaries
        """
        changes = []
        
        for _ in range(max_changes):
            try:
                change = self.change_queue.get_nowait()
                changes.append(change.to_dict())
                
                # Update statistics
                self.events_detected += 1
                self.events_by_type[change.event_type] += 1
                
            except Empty:
                break
        
        logger.debug(f"[PHASE 8.1] Consumed {len(changes)} changes from queue")
        return changes
    
    def clear_queue(self) -> int:
        """
        Clear all pending changes from the queue.
        
        Returns:
            Number of changes that were cleared
        """
        count = 0
        while True:
            try:
                self.change_queue.get_nowait()
                count += 1
            except Empty:
                break
        
        logger.info(f"[PHASE 8.1] Cleared {count} changes from queue")
        return count


# Global file watcher instance (for singleton pattern)
_file_watcher_instance: Optional[FileWatcher] = None


def get_file_watcher(repo_path: str) -> FileWatcher:
    """
    Get or create a global file watcher instance.
    
    Args:
        repo_path: Repository path to monitor
    
    Returns:
        FileWatcher instance
    """
    global _file_watcher_instance
    
    if _file_watcher_instance is None:
        _file_watcher_instance = FileWatcher(repo_path)
    
    return _file_watcher_instance
