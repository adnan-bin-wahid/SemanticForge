"""
[PHASE 8.2] Git Diff Poller Integration Layer
Provides high-level entry points for FastAPI endpoints.
Wraps git_diff_poller.py with error handling and logging.
"""

import logging
from typing import Dict, List, Optional

from app.services.git_diff_poller import get_git_diff_poller

logger = logging.getLogger(__name__)


def start_git_diff_poller(repo_path: str = '/app/test-project',
                          poll_interval: int = 2) -> Dict:
    """
    Start the Git Diff Poller for a repository.
    
    Args:
        repo_path: Path to the repository to monitor
        poll_interval: Seconds between polls (default: 2)
    
    Returns:
        Status dictionary
    """
    try:
        poller = get_git_diff_poller(repo_path, poll_interval)
        result = poller.start()
        logger.info(f'[PHASE 8.2] Git diff poller start request: {result["status"]}')
        return result
    except Exception as e:
        logger.error(f'[PHASE 8.2] Failed to start git diff poller: {e}')
        return {
            'status': 'failed',
            'error': str(e)
        }


def stop_git_diff_poller() -> Dict:
    """
    Stop the Git Diff Poller.
    
    Returns:
        Status dictionary with statistics
    """
    try:
        poller = get_git_diff_poller()
        result = poller.stop()
        logger.info(f'[PHASE 8.2] Git diff poller stopped: {result["status"]}')
        return result
    except Exception as e:
        logger.error(f'[PHASE 8.2] Failed to stop git diff poller: {e}')
        return {
            'status': 'failed',
            'error': str(e)
        }


def get_git_poller_status() -> Dict:
    """
    Get current status of the Git Diff Poller.
    
    Returns:
        Status dictionary
    """
    try:
        poller = get_git_diff_poller()
        result = poller.get_status()
        return result
    except Exception as e:
        logger.error(f'[PHASE 8.2] Failed to get git diff poller status: {e}')
        return {
            'status': 'failed',
            'error': str(e)
        }


def get_pending_git_changes(max_changes: int = 100) -> Dict:
    """
    Get pending changes without removing them from the queue.
    
    Args:
        max_changes: Maximum number of changes to retrieve
    
    Returns:
        Dictionary with status and changes list
    """
    try:
        poller = get_git_diff_poller()
        if not poller.get_status()['is_running']:
            return {
                'status': 'poller_not_running',
                'changes': []
            }
        
        changes = poller.get_pending_changes(max_changes)
        logger.debug(f'[PHASE 8.2] Retrieved {len(changes)} pending changes')
        return {
            'status': 'success',
            'changes': changes
        }
    except Exception as e:
        logger.error(f'[PHASE 8.2] Failed to get pending changes: {e}')
        return {
            'status': 'failed',
            'error': str(e),
            'changes': []
        }


def consume_git_changes(max_changes: int = 100) -> Dict:
    """
    Get and remove pending changes from the queue.
    
    Args:
        max_changes: Maximum number of changes to retrieve
    
    Returns:
        Dictionary with status and changes list
    """
    try:
        poller = get_git_diff_poller()
        if not poller.get_status()['is_running']:
            return {
                'status': 'poller_not_running',
                'changes': []
            }
        
        changes = poller.consume_changes(max_changes)
        logger.info(f'[PHASE 8.2] Consumed {len(changes)} changes from queue')
        return {
            'status': 'success',
            'changes': changes
        }
    except Exception as e:
        logger.error(f'[PHASE 8.2] Failed to consume changes: {e}')
        return {
            'status': 'failed',
            'error': str(e),
            'changes': []
        }


def clear_git_changes() -> Dict:
    """
    Clear all pending changes from the queue.
    
    Returns:
        Dictionary with status and number of cleared changes
    """
    try:
        poller = get_git_diff_poller()
        result = poller.clear_queue()
        logger.info(f'[PHASE 8.2] Cleared {result.get("changes_cleared", 0)} changes')
        return result
    except Exception as e:
        logger.error(f'[PHASE 8.2] Failed to clear changes: {e}')
        return {
            'status': 'failed',
            'error': str(e),
            'changes_cleared': 0
        }
