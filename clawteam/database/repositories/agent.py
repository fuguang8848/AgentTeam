"""Agent repository."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
import json

from .base import BaseRepository
from ..types import DatabaseAgent


class AgentRepository(BaseRepository[DatabaseAgent]):
    """Agent repository."""

    def _table_name(self) -> str:
        return "agents"

    def _id_field(self) -> str:
        return "id"

    def _to_model(self, row: Dict[str, Any]) -> DatabaseAgent:
        """Convert database row to DatabaseAgent."""
        # Parse result_data
        result_data = None
        if row.get("result_data"):
            try:
                result_data = json.loads(row["result_data"])
            except:
                pass

        # Parse datetimes
        last_seen_at = self._parse_datetime(row.get("last_seen_at"))
        created_at = self._parse_datetime(row.get("created_at"))

        return DatabaseAgent(
            id=row["id"],
            name=row["name"],
            team_id=row.get("team_id"),
            role=row.get("role"),
            status=row.get("status", "idle"),
            current_task_id=row.get("current_task_id"),
            last_seen_at=last_seen_at or datetime.now(),
            created_at=created_at or datetime.now(),
            result_data=result_data,
        )

    def _from_model(self, model: DatabaseAgent) -> Dict[str, Any]:
        """Convert DatabaseAgent to database row."""
        return {
            "id": model.id,
            "name": model.name,
            "team_id": model.team_id,
            "role": model.role,
            "status": model.status,
            "current_task_id": model.current_task_id,
            "last_seen_at": self._serialize_datetime(model.last_seen_at),
            "created_at": self._serialize_datetime(model.created_at),
            "result_data": self._serialize_json_field(model.result_data),
        }

    def list(
        self, team_id: Optional[str] = None, status: Optional[str] = None
    ) -> List[DatabaseAgent]:
        """Get agents with optional filters."""
        filters = {}
        if team_id is not None:
            filters["team_id"] = team_id
        if status is not None:
            filters["status"] = status

        return super().list(**filters)

    def update_last_seen(self, agent_id: str) -> bool:
        """Update agent's last_seen_at timestamp."""
        updates = {
            "last_seen_at": datetime.now().isoformat(),
        }
        result = self.update(agent_id, updates)
        return result is not None

    def get_agents_by_role(self, role: str, team_id: Optional[str] = None) -> List[DatabaseAgent]:
        """Get agents by role."""
        filters = {"role": role}
        if team_id:
            filters["team_id"] = team_id
        return super().list(**filters)

    def get_idle_agents(self, team_id: Optional[str] = None) -> List[DatabaseAgent]:
        """Get idle agents."""
        filters = {"status": "idle"}
        if team_id:
            filters["team_id"] = team_id
        return super().list(**filters)
