"""
Phase 8.3: Change Queue Service

A decoupled in-memory queue system for file changes that separates detection
from processing. File changes detected by the git poller or file watcher are
added to this queue for later processing by the maintenance worker (Phase 8.8+).

This allows for asynchronous, non-blocking change processing.
"""

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from queue import Queue, Empty
from typing import List, Optional, Dict
from enum import Enum

logger = logging.getLogger(__name__)


class FileChangeType(str, Enum):
    """Types of file changes"""
    MODIFIED = "modified"
    ADDED = "added"
    DELETED = "deleted"
    RENAMED = "renamed"


@dataclass
class FileChangeRequest:
    """Represents a file change that needs processing"""
    file_path: str
    change_type: FileChangeType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    old_path: Optional[str] = None  # For renamed files
    processed: bool = False
    processing_error: Optional[str] = None


class ChangeQueue:
    """
    Decoupled queue for file changes requiring processing.
    
    Separates change detection (Phase 8.2) from change processing (Phase 8.4+).
    Provides thread-safe queueing with status tracking.
    """

    def __init__(self):
        """Initialize the change queue"""
        self._queue: Queue[FileChangeRequest] = Queue()
        self._processed_count = 0
        self._error_count = 0
        self._lock = threading.Lock()
        self._start_time = datetime.utcnow()
        logger.info("[PHASE 8.3] ChangeQueue initialized")

    def add_change(self, file_path: str, change_type: FileChangeType, old_path: Optional[str] = None) -> None:
        """
        Add a file change to the processing queue.
        
        Args:
            file_path: Path to the changed file
            change_type: Type of change (modified, added, deleted, renamed)
            old_path: Original path (for renamed files)
        """
        request = FileChangeRequest(
            file_path=file_path,
            change_type=change_type,
            old_path=old_path
        )
        self._queue.put(request)
        logger.info(
            f"[PHASE 8.3] Change queued: {change_type} - {file_path}"
        )

    def get_pending_changes(self, max_changes: int = 100) -> List[FileChangeRequest]:
        """
        Peek at pending changes without removing them from queue.
        
        Args:
            max_changes: Maximum number of changes to retrieve
            
        Returns:
            List of pending FileChangeRequest objects
        """
        changes = []
        temp_queue = Queue()

        # Extract up to max_changes items and put them back
        for _ in range(max_changes):
            try:
                item = self._queue.get_nowait()
                changes.append(item)
                temp_queue.put(item)
            except Empty:
                break

        # Restore all items to original queue
        while not temp_queue.empty():
            self._queue.put(temp_queue.get())

        logger.debug(
            f"[PHASE 8.3] Retrieved {len(changes)} pending changes (peek)"
        )
        return changes

    def consume_changes(self, max_changes: int = 100) -> List[FileChangeRequest]:
        """
        Get and remove pending changes from queue.
        
        Args:
            max_changes: Maximum number of changes to retrieve
            
        Returns:
            List of FileChangeRequest objects (removed from queue)
        """
        changes = []
        for _ in range(max_changes):
            try:
                item = self._queue.get_nowait()
                changes.append(item)
            except Empty:
                break

        logger.info(
            f"[PHASE 8.3] Consumed {len(changes)} changes from queue"
        )
        return changes

    def mark_processed(self, file_path: str, success: bool = True, error: Optional[str] = None) -> None:
        """
        Mark a file change as processed (for statistics).
        
        Args:
            file_path: Path to the file that was processed
            success: Whether processing was successful
            error: Error message if processing failed
        """
        with self._lock:
            if success:
                self._processed_count += 1
                logger.debug(
                    f"[PHASE 8.3] Marked as processed: {file_path}"
                )
            else:
                self._error_count += 1
                logger.warning(
                    f"[PHASE 8.3] Processing error for {file_path}: {error}"
                )

    def get_queue_status(self) -> Dict:
        """
        Get current status of the change queue.
        
        Returns:
            Dictionary with queue statistics
        """
        uptime = (datetime.utcnow() - self._start_time).total_seconds()
        return {
            "queue_size": self._queue.qsize(),
            "processed_count": self._processed_count,
            "error_count": self._error_count,
            "uptime_seconds": uptime,
            "total_processed": self._processed_count + self._error_count,
        }

    def clear_queue(self) -> int:
        """
        Clear all pending changes from the queue.
        
        Returns:
            Number of changes cleared
        """
        count = 0
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                count += 1
            except Empty:
                break

        logger.info(f"[PHASE 8.3] Cleared {count} changes from queue")
        return count


# Global singleton instance
_change_queue: Optional[ChangeQueue] = None
_queue_lock = threading.Lock()


def get_change_queue() -> ChangeQueue:
    """
    Get or create the global ChangeQueue singleton.
    
    Returns:
        Global ChangeQueue instance
    """
    global _change_queue
    if _change_queue is None:
        with _queue_lock:
            if _change_queue is None:
                _change_queue = ChangeQueue()
    return _change_queue
