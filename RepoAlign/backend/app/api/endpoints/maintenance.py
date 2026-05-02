"""
Endpoints for Phase 8: Incremental Maintenance Agent

These endpoints manage the graph invalidation and targeted re-analysis/update cycle.
- Sub-phase 8.5: Invalidation Logic
- Sub-phase 8.6: Targeted Re-Analysis  
- Sub-phase 8.7: Targeted Graph Update
- Sub-phase 8.8: Maintenance Worker (autonomous background process)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.services.targeted_graph_updater import TargetedGraphUpdater
from app.services.invalidation_service import InvalidationService
from app.services.maintenance_worker import get_maintenance_worker
from app.services.change_queue import ChangeQueue
from app.db.neo4j_driver import get_neo4j_driver
from app.models.code_structures import FileReport

router = APIRouter()


class TargetedUpdateRequest(BaseModel):
    """Request to update a file's symbols in the graph."""
    file_report: FileReport


class BatchUpdateRequest(BaseModel):
    """Request to update multiple files in the graph."""
    file_reports: List[FileReport]


class InvalidateAndUpdateRequest(BaseModel):
    """Request to invalidate old data and update with new data for a file."""
    file_path: str
    file_report: FileReport
    perform_invalidation: bool = True


class QueueFileChangeRequest(BaseModel):
    """Request to manually queue a file change for processing."""
    file_path: str
    change_type: str  # "modified", "added", or "deleted"


@router.post("/targeted-graph-update", tags=["Maintenance"])
async def targeted_graph_update(request: TargetedUpdateRequest):
    """
    Update a single file's symbols in the knowledge graph.
    
    This endpoint takes fresh analysis data for a modified file and:
    - Creates/updates Function and Class nodes
    - Updates all Call, Inheritance, and Import relationships
    
    This is part of the incremental maintenance cycle for Phase 8.7.
    
    Args:
        request: Contains the FileReport with fresh analysis data
        
    Returns:
        Statistics about nodes and relationships created/updated
    """
    try:
        driver = get_neo4j_driver()
        updater = TargetedGraphUpdater(driver)
        
        stats = await updater.update_file_in_graph(request.file_report)
        
        return {
            "status": "success",
            "data": stats,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update graph: {str(e)}",
        )


@router.post("/batch-targeted-update", tags=["Maintenance"])
async def batch_targeted_update(request: BatchUpdateRequest):
    """
    Update multiple files' symbols in the knowledge graph.
    
    This is useful when multiple files have been modified and need
    incremental updates to the graph.
    
    Args:
        request: Contains a list of FileReports with fresh analysis data
        
    Returns:
        Aggregated statistics across all files
    """
    try:
        driver = get_neo4j_driver()
        updater = TargetedGraphUpdater(driver)
        
        stats = await updater.update_multiple_files(request.file_reports)
        
        return {
            "status": "success",
            "data": stats,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to batch update graph: {str(e)}",
        )


@router.post("/invalidate-and-update", tags=["Maintenance"])
async def invalidate_and_update(request: InvalidateAndUpdateRequest):
    """
    Perform the complete invalidation and update cycle for a file.
    
    This orchestrates the full Phase 8.5-8.7 maintenance cycle:
    1. Invalidate old nodes for the file (Phase 8.5)
    2. Insert new nodes and relationships (Phase 8.7)
    
    Args:
        request: Contains file_path, fresh FileReport, and invalidation flag
        
    Returns:
        Statistics from both invalidation and update operations
    """
    try:
        driver = get_neo4j_driver()
        updater = TargetedGraphUpdater(driver)
        invalidator = InvalidationService(driver) if request.perform_invalidation else None
        
        result = await updater.invalidate_and_update_file(
            file_path=request.file_path,
            file_report=request.file_report,
            invalidation_service=invalidator,
        )
        
        return {
            "status": "success",
            "data": result,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to invalidate and update: {str(e)}",
        )


@router.get("/graph-update-status", tags=["Maintenance"])
async def graph_update_status():
    """
    Get the current status of the graph and recent updates.
    
    This endpoint provides diagnostics about the graph state,
    useful for monitoring the maintenance agent.
    
    Returns:
        Statistics about the current graph state
    """
    try:
        driver = get_neo4j_driver()
        
        async with driver.session() as session:
            # Get node counts by type
            stats_result = await session.run(
                """
                MATCH (n)
                RETURN labels(n)[0] as node_type, count(n) as count
                ORDER BY count DESC
                """
            )
            
            node_types = {}
            async for record in stats_result:
                node_type = record["node_type"]
                count = record["count"]
                node_types[node_type] = count
            
            # Get recent updates (nodes with recent timestamps)
            recent = await session.run(
                """
                MATCH (n)
                WHERE n.updated_at > (timestamp() - 3600000)
                RETURN count(n) AS recently_updated
                """
            )
            
            recent_record = await recent.single()
            recently_updated = (
                recent_record["recently_updated"] if recent_record else 0
            )
            
            # Get relationship counts
            rel_result = await session.run(
                """
                MATCH ()-[r]->()
                RETURN type(r) as rel_type, count(r) as count
                ORDER BY count DESC
                """
            )
            
            relationship_types = {}
            async for record in rel_result:
                rel_type = record["rel_type"]
                count = record["count"]
                relationship_types[rel_type] = count
            
            return {
                "status": "ok",
                "node_types": node_types,
                "relationship_types": relationship_types,
                "recently_updated_nodes": recently_updated,
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get graph status: {str(e)}",
        )


# ============================================================================
# Phase 8.8: Maintenance Worker Control Endpoints
# ============================================================================

@router.post("/start-maintenance-worker", tags=["Maintenance", "Phase 8.8"])
async def start_maintenance_worker():
    """
    Start the autonomous maintenance worker.
    
    The maintenance worker:
    1. Continuously pulls changed file paths from the queue
    2. Performs AST diff to identify symbol changes
    3. Invalidates removed/modified symbols from the graph
    4. Re-analyzes new/modified symbols
    5. Updates the graph with new data
    
    Returns:
        Status dictionary with worker state
    """
    try:
        change_queue = ChangeQueue()
        worker = get_maintenance_worker(change_queue)
        result = worker.start()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start maintenance worker: {str(e)}",
        )


@router.post("/stop-maintenance-worker", tags=["Maintenance", "Phase 8.8"])
async def stop_maintenance_worker():
    """
    Stop the maintenance worker gracefully.
    
    The worker will finish processing the current file (if any)
    and then shut down.
    
    Returns:
        Status dictionary with confirmation
    """
    try:
        worker = get_maintenance_worker()
        result = worker.stop()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop maintenance worker: {str(e)}",
        )


@router.get("/maintenance-worker-status", tags=["Maintenance", "Phase 8.8"])
async def maintenance_worker_status():
    """
    Get the current status of the maintenance worker.
    
    Returns detailed metrics including:
    - Worker state (idle, processing, error, stopped)
    - Number of files processed
    - Number of symbols updated
    - Queue size
    - Recent processing results
    
    Returns:
        Comprehensive status dictionary
    """
    try:
        worker = get_maintenance_worker()
        status = worker.get_status()
        return status
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get maintenance worker status: {str(e)}",
        )


@router.post("/queue-file-change", tags=["Maintenance", "Phase 8.8"])
async def queue_file_change(request: QueueFileChangeRequest):
    """
    Manually queue a file change for the maintenance worker to process.
    
    This endpoint is useful for:
    - Testing the maintenance cycle
    - Triggering updates from external sources
    - Manual maintenance triggers
    
    Args:
        request: Contains file_path and change_type (modified, added, or deleted)
        
    Returns:
        Queue status including queue size
    """
    try:
        worker = get_maintenance_worker()
        result = worker.queue_file_change(request.file_path, request.change_type)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue file change: {str(e)}",
        )


@router.post("/clear-maintenance-queue", tags=["Maintenance", "Phase 8.8"])
async def clear_maintenance_queue():
    """
    Clear all pending changes from the maintenance queue.
    
    Useful if the queue gets backed up with stale changes.
    
    Returns:
        Status with number of cleared items
    """
    try:
        worker = get_maintenance_worker()
        result = worker.clear_queue()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear maintenance queue: {str(e)}",
        )
