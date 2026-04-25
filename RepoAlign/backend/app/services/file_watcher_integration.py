"""
Phase 8.1 Integration Wrapper
High-level interface for file system monitoring.
Provides simple functions for starting, stopping, and managing file watcher.
"""

import logging
from typing import Dict, List, Any

from app.services.file_watcher import get_file_watcher, FileWatcher

logger = logging.getLogger(__name__)


def start_file_watcher(repo_path: str) -> Dict[str, Any]:
    """
    Start the file system watcher for a repository.
    
    This initializes a background process that monitors the repository directory
    for file creation, deletion, and modification events.
    
    Args:
        repo_path: Path to the repository to monitor
    
    Returns:
        Status dictionary indicating success or failure
    """
    logger.info(f"[PHASE 8.1] Starting file watcher for {repo_path}")
    
    try:
        watcher = get_file_watcher(repo_path)
        result = watcher.start()
        
        if result.get("status") == "started":
            logger.info(f"[PHASE 8.1] ✓ File watcher started successfully")
        elif result.get("status") == "already_running":
            logger.info(f"[PHASE 8.1] File watcher already running")
        
        return result
        
    except Exception as e:
        logger.error(f"[PHASE 8.1] Error starting file watcher: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e)
        }


def stop_file_watcher() -> Dict[str, Any]:
    """
    Stop the file system watcher.
    
    Returns:
        Status dictionary with stop information and statistics
    """
    logger.info("[PHASE 8.1] Stopping file watcher")
    
    try:
        # Get the global watcher instance
        watcher = get_file_watcher("/")  # Dummy path, just to get instance
        
        if not watcher.is_running:
            logger.warning("[PHASE 8.1] File watcher is not running")
            return {
                "status": "not_running",
                "message": "File watcher is not running"
            }
        
        result = watcher.stop()
        
        if result.get("status") == "stopped":
            logger.info(f"[PHASE 8.1] ✓ File watcher stopped")
        
        return result
        
    except Exception as e:
        logger.error(f"[PHASE 8.1] Error stopping file watcher: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e)
        }


def get_watcher_status() -> Dict[str, Any]:
    """
    Get the current status of the file watcher.
    
    Returns:
        Status dictionary with watcher information
    """
    try:
        watcher = get_file_watcher("/")  # Dummy path, just to get instance
        return watcher.get_status()
        
    except Exception as e:
        logger.error(f"[PHASE 8.1] Error getting watcher status: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


def get_pending_changes(max_changes: int = 100) -> Dict[str, Any]:
    """
    Retrieve pending file system changes without consuming them.
    
    Args:
        max_changes: Maximum number of changes to retrieve
    
    Returns:
        Dictionary with pending changes list
    """
    try:
        watcher = get_file_watcher("/")  # Dummy path, just to get instance
        
        if not watcher.is_running:
            return {
                "status": "watcher_not_running",
                "changes": []
            }
        
        changes = watcher.get_pending_changes(max_changes)
        
        return {
            "status": "success",
            "pending_changes": len(changes),
            "changes": changes
        }
        
    except Exception as e:
        logger.error(f"[PHASE 8.1] Error getting pending changes: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e)
        }


def consume_changes(max_changes: int = 100) -> Dict[str, Any]:
    """
    Consume (remove from queue) pending file system changes.
    
    Args:
        max_changes: Maximum number of changes to consume
    
    Returns:
        Dictionary with consumed changes
    """
    try:
        watcher = get_file_watcher("/")  # Dummy path, just to get instance
        
        if not watcher.is_running:
            return {
                "status": "watcher_not_running",
                "changes": []
            }
        
        changes = watcher.consume_changes(max_changes)
        
        logger.info(f"[PHASE 8.1] Consumed {len(changes)} changes")
        
        return {
            "status": "success",
            "consumed_changes": len(changes),
            "changes": changes
        }
        
    except Exception as e:
        logger.error(f"[PHASE 8.1] Error consuming changes: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e)
        }


def clear_changes() -> Dict[str, Any]:
    """
    Clear all pending file system changes from the queue.
    
    Returns:
        Dictionary with number of changes cleared
    """
    try:
        watcher = get_file_watcher("/")  # Dummy path, just to get instance
        
        if not watcher.is_running:
            return {
                "status": "watcher_not_running",
                "changes_cleared": 0
            }
        
        count = watcher.clear_queue()
        
        logger.info(f"[PHASE 8.1] Cleared {count} changes")
        
        return {
            "status": "success",
            "changes_cleared": count
        }
        
    except Exception as e:
        logger.error(f"[PHASE 8.1] Error clearing changes: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e)
        }
