"""
Phase 8.8: Maintenance Worker

An autonomous worker process that continuously pulls changed file paths from the queue
and runs the full diff, invalidate, and update cycle to keep the knowledge graph
synchronized with code changes in real-time.

Architecture:
1. Change Detection → ChangeQueue (Phases 8.1-8.3)
2. Pull from queue → Maintenance Worker (Phase 8.8)
3. AST Diff to find changes (Phase 8.4)
4. Invalidate old nodes (Phase 8.5)
5. Re-analyze changed symbols (Phase 8.6)
6. Update graph (Phase 8.7)

The worker runs in a background thread and processes changes continuously.
"""

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum
from pathlib import Path

from app.services.change_queue import ChangeQueue, FileChangeRequest, FileChangeType
from app.services.ast_differ import ASTDiffer, SymbolChange, SymbolChangeType
from app.services.invalidation_service import InvalidationService
from app.services.re_analyzer import ReAnalyzer
from app.services.targeted_graph_updater import TargetedGraphUpdater
from app.db.neo4j_driver import get_neo4j_driver

logger = logging.getLogger(__name__)


class WorkerState(str, Enum):
    """States of the maintenance worker"""
    IDLE = "idle"
    PROCESSING = "processing"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class ProcessingResult:
    """Result of processing a single file change"""
    file_path: str
    change_type: FileChangeType
    success: bool = False
    symbol_changes: List[SymbolChange] = field(default_factory=list)
    invalidated_symbols: List[str] = field(default_factory=list)
    updated_symbols: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses"""
        return {
            "file_path": self.file_path,
            "change_type": self.change_type.value,
            "success": self.success,
            "symbol_changes": [sc.to_dict() for sc in self.symbol_changes],
            "invalidated_symbols": self.invalidated_symbols,
            "updated_symbols": self.updated_symbols,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class WorkerMetrics:
    """Metrics for the maintenance worker"""
    files_processed: int = 0
    files_failed: int = 0
    total_symbols_invalidated: int = 0
    total_symbols_updated: int = 0
    total_processing_time_ms: float = 0.0
    last_processed_file: Optional[str] = None
    last_processed_time: Optional[datetime] = None
    uptime_seconds: float = 0.0
    started_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses"""
        return {
            "files_processed": self.files_processed,
            "files_failed": self.files_failed,
            "total_symbols_invalidated": self.total_symbols_invalidated,
            "total_symbols_updated": self.total_symbols_updated,
            "total_processing_time_ms": self.total_processing_time_ms,
            "last_processed_file": self.last_processed_file,
            "last_processed_time": self.last_processed_time.isoformat() if self.last_processed_time else None,
            "uptime_seconds": self.uptime_seconds,
            "started_at": self.started_at.isoformat() if self.started_at else None
        }


class MaintenanceWorker:
    """
    Autonomous worker that keeps the knowledge graph synchronized with code changes.
    
    Runs in a background thread and continuously:
    1. Pulls changed file paths from the change queue
    2. Performs AST diff to identify symbol changes
    3. Invalidates removed/modified symbols from the graph
    4. Re-analyzes new/modified symbols
    5. Updates the graph with new data
    
    This creates a "living" knowledge graph that stays in sync with the codebase
    in near real-time.
    """
    
    def __init__(self, change_queue: ChangeQueue, repo_root: str = "/app/test-project"):
        """
        Initialize the maintenance worker.
        
        Args:
            change_queue: The queue to pull file changes from
            repo_root: Root path of the repository to monitor
        """
        self.change_queue = change_queue
        self.repo_root = repo_root
        self.state = WorkerState.STOPPED
        self.worker_thread: Optional[threading.Thread] = None
        self.running = False
        self.metrics = WorkerMetrics()
        self.recent_results: List[ProcessingResult] = []
        self.max_recent_results = 100  # Keep last 100 results for monitoring
        
        # Initialize services (these will be created per-file as needed)
        self.invalidator = InvalidationService(get_neo4j_driver())
        self.re_analyzer = ReAnalyzer()
        self.graph_updater = TargetedGraphUpdater(get_neo4j_driver())
    
    def start(self) -> Dict:
        """
        Start the maintenance worker as a background thread.
        
        Returns:
            Status dictionary
        """
        if self.running:
            return {
                "status": "already_running",
                "message": "Maintenance worker is already running"
            }
        
        self.running = True
        self.state = WorkerState.IDLE
        self.metrics.started_at = datetime.utcnow()
        
        # Start background thread
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="MaintenanceWorker"
        )
        self.worker_thread.start()
        
        logger.info("Maintenance worker started")
        
        return {
            "status": "started",
            "message": "Maintenance worker started successfully",
            "worker_state": self.state.value
        }
    
    def stop(self) -> Dict:
        """
        Stop the maintenance worker gracefully.
        
        Returns:
            Status dictionary
        """
        if not self.running:
            return {
                "status": "not_running",
                "message": "Maintenance worker is not running"
            }
        
        self.running = False
        self.state = WorkerState.STOPPED
        
        # Wait for thread to finish (with timeout)
        if self.worker_thread:
            self.worker_thread.join(timeout=5.0)
        
        logger.info("Maintenance worker stopped")
        
        return {
            "status": "stopped",
            "message": "Maintenance worker stopped successfully"
        }
    
    def get_status(self) -> Dict:
        """
        Get the current status of the maintenance worker.
        
        Returns:
            Status dictionary with worker state and metrics
        """
        uptime = 0.0
        if self.metrics.started_at:
            uptime = (datetime.utcnow() - self.metrics.started_at).total_seconds()
        
        self.metrics.uptime_seconds = uptime
        queue_status = self.change_queue.get_queue_status()
        
        return {
            "status": "ok",
            "worker_state": self.state.value,
            "running": self.running,
            "queue_size": queue_status.get("queue_size", 0),
            "metrics": self.metrics.to_dict(),
            "recent_results": [r.to_dict() for r in self.recent_results[-10:]],  # Last 10
        }
    
    def _worker_loop(self):
        """Main worker loop that processes changes continuously."""
        logger.info("Worker loop started")
        
        while self.running:
            try:
                # Get next batch of changes from queue (non-blocking)
                changes = self.change_queue.consume_changes(max_changes=1)
                
                if not changes:
                    # Queue empty, stay idle
                    self.state = WorkerState.IDLE
                    time.sleep(0.5)
                    continue
                
                # Process each change
                for change_request in changes:
                    self.state = WorkerState.PROCESSING
                    result = asyncio.run(self._process_file_change(change_request))
                    
                    # Track result
                    self.recent_results.append(result)
                    if len(self.recent_results) > self.max_recent_results:
                        self.recent_results.pop(0)
                    
                    # Update metrics
                    if result.success:
                        self.metrics.files_processed += 1
                        self.metrics.total_symbols_invalidated += len(result.invalidated_symbols)
                        self.metrics.total_symbols_updated += len(result.updated_symbols)
                        self.metrics.last_processed_file = result.file_path
                        self.metrics.last_processed_time = result.timestamp
                    else:
                        self.metrics.files_failed += 1
                    
                    self.metrics.total_processing_time_ms += result.duration_ms
                    
                    # Mark as processed in queue
                    self.change_queue.mark_processed(
                        file_path=change_request.file_path,
                        success=result.success,
                        error=result.error_message
                    )
                    
                    logger.info(
                        f"Processed {result.file_path}: {result.change_type} "
                        f"({len(result.symbol_changes)} changes, {result.duration_ms:.1f}ms)"
                    )
                
                self.state = WorkerState.IDLE
                
            except Exception as e:
                self.state = WorkerState.ERROR
                logger.error(f"Worker loop error: {str(e)}", exc_info=True)
                time.sleep(1.0)  # Backoff on error
    
    async def _process_file_change(self, change_request: FileChangeRequest) -> ProcessingResult:
        """
        Process a single file change through the full cycle.
        
        Cycle:
        1. AST Diff - Find what symbols changed
        2. Invalidate - Remove old symbols from graph
        3. Re-analyze - Analyze new/modified symbols
        4. Update - Insert into graph
        
        Args:
            change_request: The file change to process
            
        Returns:
            ProcessingResult with details of what was done
        """
        start_time = datetime.utcnow()
        result = ProcessingResult(
            file_path=change_request.file_path,
            change_type=change_request.change_type
        )
        
        try:
            file_path = change_request.file_path
            
            # Special handling for deleted files
            if change_request.change_type == FileChangeType.DELETED:
                # Just invalidate the entire file
                await self.invalidator.invalidate_file(file_path)
                result.invalidated_symbols = ["<all symbols in file>"]
                result.success = True
                return result
            
            # Get file content from disk
            full_path = Path(self.repo_root) / file_path
            if not full_path.exists():
                result.error_message = f"File not found: {full_path}"
                result.success = False
                return result
            
            new_content = full_path.read_text()
            
            # Create AST differ for this specific file
            ast_differ = ASTDiffer(str(full_path))
            
            # Run AST diff to find symbol changes
            symbol_changes = ast_differ.diff_file("HEAD")
            result.symbol_changes = symbol_changes
            
            # Process symbol changes
            added_or_modified = [
                sc for sc in symbol_changes
                if sc.change_type in (SymbolChangeType.ADDED, SymbolChangeType.MODIFIED)
            ]
            removed = [
                sc for sc in symbol_changes
                if sc.change_type == SymbolChangeType.REMOVED
            ]
            
            # Step 1: Invalidate removed and modified symbols
            for symbol_change in removed:
                try:
                    await self.invalidator.invalidate_symbol(
                        file_path,
                        symbol_change.symbol_name,
                        symbol_change.symbol_type
                    )
                    result.invalidated_symbols.append(symbol_change.symbol_name)
                except Exception as e:
                    logger.warning(f"Failed to invalidate {symbol_change.symbol_name}: {e}")
            
            for symbol_change in added_or_modified:
                if symbol_change.change_type == SymbolChangeType.MODIFIED:
                    try:
                        await self.invalidator.invalidate_symbol(
                            file_path,
                            symbol_change.symbol_name,
                            symbol_change.symbol_type
                        )
                        result.invalidated_symbols.append(symbol_change.symbol_name)
                    except Exception as e:
                        logger.warning(f"Failed to invalidate {symbol_change.symbol_name}: {e}")
            
            # Step 2: Re-analyze new/modified symbols
            file_report = None
            try:
                file_report = self.re_analyzer.analyze_file(file_path, new_content)
                if file_report:
                    result.updated_symbols = [
                        f.name for f in file_report.functions
                    ] + [
                        c.name for c in file_report.classes
                    ]
            except Exception as e:
                logger.error(f"Failed to re-analyze {file_path}: {e}")
                result.error_message = f"Re-analysis failed: {str(e)}"
                result.success = False
                return result
            
            # Step 3: Update graph with new data
            if file_report:
                try:
                    await self.graph_updater.update_file_in_graph(file_report)
                except Exception as e:
                    logger.error(f"Failed to update graph for {file_path}: {e}")
                    result.error_message = f"Graph update failed: {str(e)}"
                    result.success = False
                    return result
            
            result.success = True
            
        except Exception as e:
            logger.error(f"Error processing {change_request.file_path}: {e}", exc_info=True)
            result.error_message = str(e)
            result.success = False
        
        finally:
            # Calculate duration
            duration = (datetime.utcnow() - start_time).total_seconds() * 1000
            result.duration_ms = duration
        
        return result
    
    def queue_file_change(self, file_path: str, change_type: str) -> Dict:
        """
        Manually queue a file change for processing.
        
        Useful for testing or triggering maintenance from external sources.
        
        Args:
            file_path: Path of the changed file
            change_type: Type of change (modified, added, deleted)
            
        Returns:
            Queue status dictionary
        """
        try:
            change_type_enum = FileChangeType(change_type.lower())
            self.change_queue.add_change(file_path, change_type_enum)
            queue_status = self.change_queue.get_queue_status()
            return {
                "status": "queued",
                "file_path": file_path,
                "change_type": change_type,
                "queue_size": queue_status.get("queue_size", 0)
            }
        except ValueError as e:
            return {
                "status": "error",
                "message": f"Invalid change type: {change_type}",
                "valid_types": [t.value for t in FileChangeType]
            }
    
    def clear_queue(self) -> Dict:
        """
        Clear all pending changes from the queue.
        
        Returns:
            Status dictionary
        """
        count = self.change_queue.clear_queue()
        return {
            "status": "cleared",
            "cleared_count": count
        }


# Global worker instance
_maintenance_worker: Optional[MaintenanceWorker] = None


def get_maintenance_worker(change_queue: Optional[ChangeQueue] = None) -> MaintenanceWorker:
    """
    Get or create the global maintenance worker instance.
    
    Args:
        change_queue: Optional change queue instance
        
    Returns:
        MaintenanceWorker instance
    """
    global _maintenance_worker
    
    if _maintenance_worker is None:
        if change_queue is None:
            change_queue = ChangeQueue()
        _maintenance_worker = MaintenanceWorker(change_queue)
    
    return _maintenance_worker
