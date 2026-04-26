"""
Phase 8.3: Change Queue Integration Layer

High-level integration functions for managing the change queue via API endpoints.
Provides error handling and structured responses for queue operations.
"""

import logging
from typing import Dict, Any, Optional

from app.services.change_queue import get_change_queue, FileChangeType

logger = logging.getLogger(__name__)


def enqueue_file_change(
    file_path: str,
    change_type: str,
    old_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Add a file change to the processing queue.
    
    Args:
        file_path: Path to the changed file
        change_type: Type of change (modified, added, deleted, renamed)
        old_path: Original path for renamed files
        
    Returns:
        Dictionary with status and details
    """
    try:
        logger.info(
            f"[PHASE 8.3] Enqueue request: {change_type} - {file_path}"
        )
        
        # Validate change type
        try:
            ct = FileChangeType(change_type.lower())
        except ValueError:
            return {
                "status": "failed",
                "error": f"Invalid change_type: {change_type}. Must be one of: modified, added, deleted, renamed"
            }
        
        queue = get_change_queue()
        queue.add_change(file_path, ct, old_path)
        
        return {
            "status": "success",
            "message": "File change queued for processing",
            "file_path": file_path,
            "change_type": change_type
        }
    except Exception as e:
        logger.error(f"[PHASE 8.3] Error enqueueing change: {str(e)}")
        return {
            "status": "failed",
            "error": str(e)
        }


def get_pending_changes(max_changes: int = 100) -> Dict[str, Any]:
    """
    Get pending changes without removing them from queue.
    
    Args:
        max_changes: Maximum number of changes to retrieve
        
    Returns:
        Dictionary with status and changes list
    """
    try:
        queue = get_change_queue()
        changes = queue.get_pending_changes(max_changes)
        
        return {
            "status": "success",
            "changes": [
                {
                    "file_path": c.file_path,
                    "change_type": c.change_type.value,
                    "timestamp": c.timestamp.isoformat(),
                    "old_path": c.old_path
                }
                for c in changes
            ],
            "count": len(changes)
        }
    except Exception as e:
        logger.error(f"[PHASE 8.3] Error getting pending changes: {str(e)}")
        return {
            "status": "failed",
            "error": str(e)
        }


def consume_queue_changes(max_changes: int = 100) -> Dict[str, Any]:
    """
    Get and remove pending changes from queue.
    
    Args:
        max_changes: Maximum number of changes to retrieve
        
    Returns:
        Dictionary with status and consumed changes
    """
    try:
        logger.info(f"[PHASE 8.3] Consuming up to {max_changes} changes")
        
        queue = get_change_queue()
        changes = queue.consume_changes(max_changes)
        
        return {
            "status": "success",
            "changes": [
                {
                    "file_path": c.file_path,
                    "change_type": c.change_type.value,
                    "timestamp": c.timestamp.isoformat(),
                    "old_path": c.old_path
                }
                for c in changes
            ],
            "count": len(changes)
        }
    except Exception as e:
        logger.error(f"[PHASE 8.3] Error consuming changes: {str(e)}")
        return {
            "status": "failed",
            "error": str(e)
        }


def mark_change_processed(
    file_path: str,
    success: bool = True,
    error: Optional[str] = None
) -> Dict[str, Any]:
    """
    Mark a file change as processed.
    
    Args:
        file_path: Path to the file that was processed
        success: Whether processing was successful
        error: Error message if processing failed
        
    Returns:
        Dictionary with status
    """
    try:
        logger.info(
            f"[PHASE 8.3] Marking processed: {file_path} (success={success})"
        )
        
        queue = get_change_queue()
        queue.mark_processed(file_path, success, error)
        
        return {
            "status": "success",
            "message": "Change marked as processed",
            "file_path": file_path
        }
    except Exception as e:
        logger.error(f"[PHASE 8.3] Error marking change: {str(e)}")
        return {
            "status": "failed",
            "error": str(e)
        }


def get_queue_status() -> Dict[str, Any]:
    """
    Get current status of the change queue.
    
    Returns:
        Dictionary with queue statistics
    """
    try:
        queue = get_change_queue()
        stats = queue.get_queue_status()
        
        return {
            "status": "success",
            **stats
        }
    except Exception as e:
        logger.error(f"[PHASE 8.3] Error getting queue status: {str(e)}")
        return {
            "status": "failed",
            "error": str(e)
        }


def clear_all_changes() -> Dict[str, Any]:
    """
    Clear all pending changes from the queue.
    
    Returns:
        Dictionary with number of changes cleared
    """
    try:
        logger.warning("[PHASE 8.3] Clearing all changes from queue")
        
        queue = get_change_queue()
        count = queue.clear_queue()
        
        return {
            "status": "cleared",
            "changes_cleared": count
        }
    except Exception as e:
        logger.error(f"[PHASE 8.3] Error clearing queue: {str(e)}")
        return {
            "status": "failed",
            "error": str(e)
        }
