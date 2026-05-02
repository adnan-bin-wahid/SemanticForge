"""
Phase 8.9: Agent Control Endpoints

Advanced administrative control over the maintenance agent including:
- Start/stop/pause/resume control
- Configuration management
- Health monitoring
- Event logging
- Metrics export
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter

from app.services.maintenance_worker import get_maintenance_worker
from app.services.change_queue import get_change_queue
from app.services.file_watcher import get_file_watcher

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Configuration Models
# ============================================================================

class AgentConfig(BaseModel):
    """Agent configuration parameters"""
    repo_path: str = "/app/test-project"
    change_detection: str = "watchdog"
    max_queue_size: int = 1000
    processing_batch_size: int = 1
    processing_interval_ms: int = 500
    max_parallel_jobs: int = 1
    auto_resume_on_error: bool = True
    error_retry_count: int = 3
    log_level: str = "INFO"


class AgentControlResponse(BaseModel):
    """Standard response from agent control operations"""
    status: str
    message: str
    timestamp: str
    data: Optional[Dict[str, Any]] = None


# ============================================================================
# Global Agent Control State
# ============================================================================

class AgentControlState:
    """Manages agent control state and configuration"""
    
    def __init__(self):
        self.paused = False
        self.config = AgentConfig()
        self.last_error: Optional[str] = None
        self.last_error_time: Optional[datetime] = None
        self.event_log: list = []
        self.max_events = 100
        
    def log_event(self, event_type: str, message: str, data: Optional[Dict] = None):
        """Log an agent event"""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": event_type,
            "message": message,
            "data": data
        }
        self.event_log.append(event)
        if len(self.event_log) > self.max_events:
            self.event_log.pop(0)
        logger.info(f"Agent event: {event_type} - {message}")
    
    def get_events(self, limit: int = 50) -> list:
        """Get recent events"""
        return self.event_log[-limit:]
    
    def set_error(self, error: str):
        """Record an error"""
        self.last_error = error
        self.last_error_time = datetime.utcnow()
        self.log_event("ERROR", error)
    
    def clear_error(self):
        """Clear error state"""
        self.last_error = None
        self.last_error_time = None


# Global control state
_control_state = AgentControlState()


def get_control_state() -> AgentControlState:
    """Get the global agent control state"""
    return _control_state


# ============================================================================
# Helper Functions
# ============================================================================

def _make_response(status: str, message: str, data: Optional[Dict] = None) -> Dict:
    """Create a standard agent control response"""
    return {
        "status": status,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
        "data": data
    }


# ============================================================================
# FastAPI Endpoints
# ============================================================================

@router.post("/agent-control/start", tags=["Agent Control"])
async def agent_start():
    """Start the maintenance agent"""
    try:
        control_state = get_control_state()
        queue = get_change_queue()
        worker = get_maintenance_worker(queue, repo_root=control_state.config.repo_path)
        watcher = get_file_watcher(control_state.config.repo_path, queue)

        watcher_result = watcher.start()
        result = worker.start()
        control_state.paused = False
        control_state.log_event("START", "Full maintenance loop started")
        return _make_response(
            "started",
            "Maintenance loop started successfully",
            {"worker": result, "watcher": watcher_result},
        )
    except Exception as e:
        control_state = get_control_state()
        control_state.set_error(f"Failed to start agent: {str(e)}")
        return _make_response("error", f"Failed to start agent: {str(e)}")


@router.post("/agent-control/stop", tags=["Agent Control"])
async def agent_stop():
    """Stop the maintenance agent"""
    try:
        worker = get_maintenance_worker()
        watcher = get_file_watcher(get_control_state().config.repo_path)
        watcher_result = watcher.stop() if watcher.is_running else {
            "status": "not_running",
            "message": "File watcher is not running",
        }
        result = worker.stop()
        control_state = get_control_state()
        control_state.paused = False
        control_state.log_event("STOP", "Full maintenance loop stopped")
        return _make_response(
            "stopped",
            "Maintenance loop stopped successfully",
            {"worker": result, "watcher": watcher_result},
        )
    except Exception as e:
        control_state = get_control_state()
        control_state.set_error(f"Failed to stop agent: {str(e)}")
        return _make_response("error", f"Failed to stop agent: {str(e)}")


@router.post("/agent-control/pause", tags=["Agent Control"])
async def agent_pause():
    """Pause the agent (without stopping it)"""
    try:
        control_state = get_control_state()
        control_state.paused = True
        control_state.log_event("PAUSE", "Agent paused")
        return _make_response(
            "paused",
            "Agent paused - will not process new items until resumed",
            {"paused": True}
        )
    except Exception as e:
        control_state = get_control_state()
        control_state.set_error(f"Failed to pause agent: {str(e)}")
        return _make_response("error", f"Failed to pause agent: {str(e)}")


@router.post("/agent-control/resume", tags=["Agent Control"])
async def agent_resume():
    """Resume the agent from pause"""
    try:
        control_state = get_control_state()
        if not control_state.paused:
            return _make_response("warning", "Agent is not paused")
        control_state.paused = False
        control_state.log_event("RESUME", "Agent resumed")
        return _make_response(
            "resumed",
            "Agent resumed successfully",
            {"paused": False}
        )
    except Exception as e:
        control_state = get_control_state()
        control_state.set_error(f"Failed to resume agent: {str(e)}")
        return _make_response("error", f"Failed to resume agent: {str(e)}")


@router.get("/agent-control/status", tags=["Agent Control"])
async def agent_status():
    """Get comprehensive agent status"""
    try:
        control_state = get_control_state()
        worker = get_maintenance_worker()
        queue = get_change_queue()
        watcher = get_file_watcher(control_state.config.repo_path, queue)
        
        worker_status = worker.get_status()
        queue_status = queue.get_queue_status()
        watcher_status = watcher.get_status()
        
        status_data = {
            "worker": worker_status,
            "watcher": watcher_status,
            "queue": queue_status,
            "control": {
                "paused": control_state.paused,
                "last_error": control_state.last_error,
                "last_error_time": control_state.last_error_time.isoformat() if control_state.last_error_time else None
            }
        }
        
        return _make_response("ok", "Agent status retrieved", status_data)
    except Exception as e:
        return _make_response("error", f"Failed to get agent status: {str(e)}")


@router.get("/agent-control/health", tags=["Agent Control"])
async def agent_health():
    """Health check for the agent"""
    try:
        worker = get_maintenance_worker()
        control_state = get_control_state()
        watcher = get_file_watcher(control_state.config.repo_path, get_change_queue())
        
        health = {
            "agent_running": worker.running,
            "watcher_running": watcher.is_running,
            "agent_state": worker.state.value,
            "agent_paused": control_state.paused,
            "queue_size": get_change_queue().get_queue_status()["queue_size"],
            "error_state": control_state.last_error is not None,
            "uptime_seconds": worker.metrics.uptime_seconds,
            "healthy": (
                worker.running
                and watcher.is_running
                and not control_state.paused
                and control_state.last_error is None
            )
        }
        
        status = "healthy" if health["healthy"] else "degraded"
        return _make_response(status, "Agent health check", health)
    except Exception as e:
        return _make_response("error", f"Failed to check agent health: {str(e)}")


@router.get("/agent-control/config", tags=["Agent Control"])
async def get_agent_config():
    """Get current agent configuration"""
    try:
        control_state = get_control_state()
        return _make_response(
            "ok",
            "Agent configuration retrieved",
            control_state.config.model_dump()
        )
    except Exception as e:
        return _make_response("error", f"Failed to get configuration: {str(e)}")


@router.post("/agent-control/config", tags=["Agent Control"])
async def set_agent_config(config: AgentConfig):
    """Update agent configuration"""
    try:
        control_state = get_control_state()
        control_state.config = config
        control_state.log_event("CONFIG_UPDATE", "Agent configuration updated", config.model_dump())
        return _make_response(
            "ok",
            "Agent configuration updated",
            config.model_dump()
        )
    except Exception as e:
        control_state = get_control_state()
        control_state.set_error(f"Failed to update configuration: {str(e)}")
        return _make_response("error", f"Failed to update configuration: {str(e)}")


@router.get("/agent-control/events", tags=["Agent Control"])
async def get_agent_events(limit: int = 50):
    """Get recent agent events"""
    try:
        control_state = get_control_state()
        events = control_state.get_events(limit)
        return _make_response(
            "ok",
            f"Retrieved {len(events)} recent events",
            {"events": events, "total_events": len(control_state.event_log)}
        )
    except Exception as e:
        return _make_response("error", f"Failed to get events: {str(e)}")


@router.post("/agent-control/restart", tags=["Agent Control"])
async def restart_agent():
    """Restart the agent (stop and start)"""
    try:
        worker = get_maintenance_worker()
        control_state = get_control_state()
        
        # Stop
        watcher = get_file_watcher(control_state.config.repo_path, get_change_queue())
        watcher.stop()
        worker.stop()
        control_state.log_event("RESTART", "Stopping agent for restart")
        
        # Clear pause state
        control_state.paused = False
        
        # Start
        watcher_result = watcher.start()
        result = worker.start()
        control_state.log_event("RESTART", "Agent restarted")
        
        return _make_response(
            "restarted",
            "Agent restarted successfully",
            {"worker": result, "watcher": watcher_result}
        )
    except Exception as e:
        control_state = get_control_state()
        control_state.set_error(f"Failed to restart agent: {str(e)}")
        return _make_response("error", f"Failed to restart agent: {str(e)}")


@router.post("/agent-control/clear-error", tags=["Agent Control"])
async def clear_agent_error():
    """Clear error state"""
    try:
        control_state = get_control_state()
        control_state.clear_error()
        control_state.log_event("ERROR_CLEARED", "Agent error state cleared")
        return _make_response("ok", "Error state cleared")
    except Exception as e:
        return _make_response("error", f"Failed to clear error: {str(e)}")


@router.get("/agent-control/metrics", tags=["Agent Control"])
async def get_agent_metrics():
    """Get detailed agent metrics"""
    try:
        control_state = get_control_state()
        worker = get_maintenance_worker()
        queue = get_change_queue()
        watcher = get_file_watcher(control_state.config.repo_path, queue)
        
        metrics = {
            "worker_metrics": worker.metrics.to_dict(),
            "watcher_metrics": watcher.get_status(),
            "queue_metrics": queue.get_queue_status(),
            "control_metrics": {
                "paused": control_state.paused,
                "total_events_logged": len(control_state.event_log),
                "has_error": control_state.last_error is not None
            }
        }
        
        return _make_response("ok", "Agent metrics retrieved", metrics)
    except Exception as e:
        return _make_response("error", f"Failed to get metrics: {str(e)}")


@router.post("/agent-control/clear-queue", tags=["Agent Control"])
async def clear_agent_queue():
    """Clear the change queue"""
    try:
        queue = get_change_queue()
        control_state = get_control_state()
        count = queue.clear_queue()
        control_state.log_event("QUEUE_CLEARED", f"Cleared {count} items from queue")
        return _make_response(
            "ok",
            f"Queue cleared ({count} items removed)",
            {"cleared_count": count}
        )
    except Exception as e:
        control_state = get_control_state()
        control_state.set_error(f"Failed to clear queue: {str(e)}")
        return _make_response("error", f"Failed to clear queue: {str(e)}")


@router.get("/agent-control/summary", tags=["Agent Control"])
async def get_agent_summary():
    """Get a quick summary of agent state"""
    try:
        control_state = get_control_state()
        worker = get_maintenance_worker()
        queue = get_change_queue()
        watcher = get_file_watcher(control_state.config.repo_path, queue)
        
        summary = {
            "running": worker.running,
            "watcher_running": watcher.is_running,
            "state": worker.state.value,
            "paused": control_state.paused,
            "queue_size": queue.get_queue_status()["queue_size"],
            "files_processed": worker.metrics.files_processed,
            "files_failed": worker.metrics.files_failed,
            "symbols_updated": worker.metrics.total_symbols_updated,
            "uptime_minutes": round(worker.metrics.uptime_seconds / 60, 2),
            "healthy": worker.running and watcher.is_running and not control_state.paused
        }
        
        return _make_response("ok", "Agent summary retrieved", summary)
    except Exception as e:
        return _make_response("error", f"Failed to get summary: {str(e)}")
