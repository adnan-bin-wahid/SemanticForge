"""
Phase 8.10: Full Maintenance Loop

Coordinates production-style incremental graph maintenance from workspace file
events sent by the VS Code extension. The backend does not need direct access to
the user's filesystem; it receives relative paths and file content from the
extension, then invalidates and updates graph state in near real time.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from app.services.invalidation_service import InvalidationService
from app.services.re_analyzer import ReAnalyzer
from app.services.targeted_graph_updater import TargetedGraphUpdater

logger = logging.getLogger(__name__)


@dataclass
class FullMaintenanceMetrics:
    """Runtime counters for extension-driven graph synchronization."""

    files_synced: int = 0
    files_deleted: int = 0
    files_failed: int = 0
    symbols_updated: int = 0
    last_file_path: Optional[str] = None
    last_change_type: Optional[str] = None
    last_sync_time: Optional[datetime] = None
    last_error: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        uptime = (datetime.utcnow() - self.started_at).total_seconds()
        return {
            "files_synced": self.files_synced,
            "files_deleted": self.files_deleted,
            "files_failed": self.files_failed,
            "symbols_updated": self.symbols_updated,
            "last_file_path": self.last_file_path,
            "last_change_type": self.last_change_type,
            "last_sync_time": self.last_sync_time.isoformat()
            if self.last_sync_time
            else None,
            "last_error": self.last_error,
            "uptime_seconds": uptime,
            "started_at": self.started_at.isoformat(),
        }


class FullMaintenanceLoop:
    """
    Maintains a living knowledge graph from extension-supplied file events.

    Flow:
    1. Extension notices a Python file save/create/delete.
    2. Extension sends relative path, change type, and current content.
    3. Backend invalidates stale graph nodes for that file.
    4. Backend re-analyzes current content.
    5. Backend writes fresh nodes and relationships.
    """

    def __init__(self, driver):
        self.driver = driver
        self.metrics = FullMaintenanceMetrics()

    async def process_file_change(
        self,
        file_path: str,
        change_type: str,
        content: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        normalized_change_type = change_type.lower()
        self._validate_change(normalized_change_type, content)

        try:
            invalidator = InvalidationService(self.driver)

            if normalized_change_type == "deleted":
                invalidation = await invalidator.invalidate_file(file_path)
                self._record_success(file_path, normalized_change_type, symbols_updated=0)
                self.metrics.files_deleted += 1
                return {
                    "status": "success",
                    "phase": "8.10",
                    "mode": "extension-driven",
                    "workspace_id": workspace_id,
                    "file_path": file_path,
                    "change_type": normalized_change_type,
                    "invalidation": invalidation,
                    "metrics": self.metrics.to_dict(),
                }

            re_analyzer = ReAnalyzer()
            file_report = re_analyzer.analyze_file(file_path, content or "")
            if file_report is None:
                raise ValueError(f"Could not analyze Python file: {file_path}")

            updater = TargetedGraphUpdater(self.driver)
            result = await updater.invalidate_and_update_file(
                file_path=file_path,
                file_report=file_report,
                invalidation_service=invalidator,
            )

            symbols_updated = len(file_report.functions) + len(file_report.classes)
            self._record_success(file_path, normalized_change_type, symbols_updated)

            return {
                "status": "success",
                "phase": "8.10",
                "mode": "extension-driven",
                "workspace_id": workspace_id,
                "file_path": file_path,
                "change_type": normalized_change_type,
                "symbols_updated": symbols_updated,
                "data": result,
                "metrics": self.metrics.to_dict(),
            }
        except Exception as e:
            self._record_failure(file_path, normalized_change_type, str(e))
            logger.error(
                "Full maintenance loop failed for %s: %s",
                file_path,
                e,
                exc_info=True,
            )
            raise

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "phase": "8.10",
            "mode": "extension-driven",
            "description": "VS Code saves create near-real-time graph updates.",
            "metrics": self.metrics.to_dict(),
        }

    @staticmethod
    def _validate_change(change_type: str, content: Optional[str]) -> None:
        if change_type not in {"added", "modified", "deleted"}:
            raise ValueError("change_type must be one of: added, modified, deleted")
        if change_type in {"added", "modified"} and content is None:
            raise ValueError("content is required for added or modified files")

    def _record_success(
        self,
        file_path: str,
        change_type: str,
        symbols_updated: int,
    ) -> None:
        self.metrics.files_synced += 1
        self.metrics.symbols_updated += symbols_updated
        self.metrics.last_file_path = file_path
        self.metrics.last_change_type = change_type
        self.metrics.last_sync_time = datetime.utcnow()
        self.metrics.last_error = None

    def _record_failure(self, file_path: str, change_type: str, error: str) -> None:
        self.metrics.files_failed += 1
        self.metrics.last_file_path = file_path
        self.metrics.last_change_type = change_type
        self.metrics.last_sync_time = datetime.utcnow()
        self.metrics.last_error = error


_full_maintenance_loop: Optional[FullMaintenanceLoop] = None


def get_full_maintenance_loop(driver) -> FullMaintenanceLoop:
    """Get or create the process-wide Phase 8.10 loop service."""
    global _full_maintenance_loop

    if _full_maintenance_loop is None:
        _full_maintenance_loop = FullMaintenanceLoop(driver)

    return _full_maintenance_loop
