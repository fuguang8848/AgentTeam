"""Session repository."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime

from .base import BaseRepository
from ..types import DatabaseSession


class SessionRepository(BaseRepository[DatabaseSession]):
    """Session repository."""

    def _table_name(self) -> str:
        return "sessions"

    def _id_field(self) -> str:
        return "id"

    def _to_model(self, row: Dict[str, Any]) -> DatabaseSession:
        """Convert database row to DatabaseSession."""
        # Parse datetimes
        created_at = self._parse_datetime(row.get("created_at"))
        updated_at = self._parse_datetime(row.get("updated_at"))
        terminated_at = self._parse_datetime(row.get("terminated_at"))

        return DatabaseSession(
            id=row["id"],
            name=row["name"],
            task_id=row.get("task_id"),
            working_directory=row.get("working_directory", ""),
            status=row.get("status", "running"),
            provider_id=row.get("provider_id"),
            team_id=row.get("team_id"),
            created_at=created_at or datetime.now(),
            updated_at=updated_at or datetime.now(),
            terminated_at=terminated_at,
        )

    def _from_model(self, model: DatabaseSession) -> Dict[str, Any]:
        """Convert DatabaseSession to database row."""
        return {
            "id": model.id,
            "name": model.name,
            "task_id": model.task_id,
            "working_directory": model.working_directory,
            "status": model.status,
            "provider_id": model.provider_id,
            "team_id": model.team_id,
            "created_at": self._serialize_datetime(model.created_at),
            "updated_at": self._serialize_datetime(model.updated_at),
            "terminated_at": self._serialize_datetime(model.terminated_at),
        }

    def list(
        self, team_id: Optional[str] = None, status: Optional[str] = None
    ) -> List[DatabaseSession]:
        """Get sessions with optional filters."""
        filters = {}
        if team_id is not None:
            filters["team_id"] = team_id
        if status is not None:
            filters["status"] = status

        return super().list(**filters)

    def get_active_sessions(self, team_id: Optional[str] = None) -> List[DatabaseSession]:
        """Get active (running) sessions."""
        filters = {"status": "running"}
        if team_id:
            filters["team_id"] = team_id
        return super().list(**filters)

    def terminate_session(self, session_id: str) -> bool:
        """Terminate a session."""
        updates = {
            "status": "terminated",
            "terminated_at": datetime.now().isoformat(),
        }
        result = self.update(session_id, updates)
        return result is not None
