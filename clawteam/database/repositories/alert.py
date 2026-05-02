"""Alert repository."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime

from .base import BaseRepository
from ..types import DatabaseAlert


class AlertRepository(BaseRepository[DatabaseAlert]):
    """Alert repository."""

    def _table_name(self) -> str:
        return "alerts"

    def _id_field(self) -> str:
        return "id"

    def _to_model(self, row: Dict[str, Any]) -> DatabaseAlert:
        """Convert database row to DatabaseAlert."""
        # Parse datetimes
        created_at = self._parse_datetime(row.get("created_at"))
        acknowledged_at = self._parse_datetime(row.get("acknowledged_at"))
        resolved_at = self._parse_datetime(row.get("resolved_at"))

        return DatabaseAlert(
            id=row["id"],
            title=row["title"],
            message=row["message"],
            level=row.get("level", "info"),
            team_id=row.get("team_id"),
            task_id=row.get("task_id"),
            session_id=row.get("session_id"),
            created_at=created_at or datetime.now(),
            acknowledged_at=acknowledged_at,
            resolved_at=resolved_at,
        )

    def _from_model(self, model: DatabaseAlert) -> Dict[str, Any]:
        """Convert DatabaseAlert to database row."""
        return {
            "id": model.id,
            "title": model.title,
            "message": model.message,
            "level": model.level,
            "team_id": model.team_id,
            "task_id": model.task_id,
            "session_id": model.session_id,
            "created_at": self._serialize_datetime(model.created_at),
            "acknowledged_at": self._serialize_datetime(model.acknowledged_at),
            "resolved_at": self._serialize_datetime(model.resolved_at),
        }

    def list(
        self,
        team_id: Optional[str] = None,
        level: Optional[str] = None,
        resolved: Optional[bool] = None,
    ) -> List[DatabaseAlert]:
        """Get alerts with optional filters."""
        filters = {}
        if team_id is not None:
            filters["team_id"] = team_id
        if level is not None:
            filters["level"] = level

        # Handle resolved filter
        if resolved is not None:
            # This will be handled in custom logic
            pass

        alerts = super().list(**filters)

        # Apply resolved filter if specified
        if resolved is not None:
            if resolved:
                alerts = [alert for alert in alerts if alert.resolved_at is not None]
            else:
                alerts = [alert for alert in alerts if alert.resolved_at is None]

        return alerts

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        updates = {
            "acknowledged_at": datetime.now().isoformat(),
        }
        result = self.update(alert_id, updates)
        return result is not None

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        updates = {
            "resolved_at": datetime.now().isoformat(),
        }
        result = self.update(alert_id, updates)
        return result is not None

    def get_unresolved_alerts(self, team_id: Optional[str] = None) -> List[DatabaseAlert]:
        """Get unresolved alerts."""
        alerts = self.list(team_id=team_id, resolved=False)
        return alerts

    def get_critical_alerts(self, team_id: Optional[str] = None) -> List[DatabaseAlert]:
        """Get critical (error) level alerts."""
        filters = {"level": "error"}
        if team_id:
            filters["team_id"] = team_id
        return super().list(**filters)

    def get_alert_stats(self, team_id: Optional[str] = None) -> Dict[str, int]:
        """Get alert statistics."""
        if self.using_sqlite and self.db:
            query = "SELECT level, COUNT(*) as count FROM alerts"
            params = []
            if team_id:
                query += " WHERE team_id = ?"
                params.append(team_id)
            query += " GROUP BY level"

            cursor = self.db.execute(query, params)
            result = {}
            for row in cursor.fetchall():
                result[row["level"]] = row["count"]
            return result
        else:
            # Count in memory
            result = {}
            for alert in self.mem_storage.values():
                if team_id and alert.team_id != team_id:
                    continue
                result[alert.level] = result.get(alert.level, 0) + 1
            return result
