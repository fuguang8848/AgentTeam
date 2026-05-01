"""Task repository."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
import json

from .base import BaseRepository
from ..types import DatabaseTask


class TaskRepository(BaseRepository[DatabaseTask]):
    """Task repository."""
    
    def _table_name(self) -> str:
        return "tasks"
    
    def _id_field(self) -> str:
        return "id"
    
    def _to_model(self, row: Dict[str, Any]) -> DatabaseTask:
        """Convert database row to DatabaseTask."""
        # Parse tags
        tags = []
        if row.get("tags"):
            try:
                tags = json.loads(row["tags"])
            except:
                tags = []
        
        # Parse datetimes
        created_at = self._parse_datetime(row.get("created_at"))
        updated_at = self._parse_datetime(row.get("updated_at"))
        completed_at = self._parse_datetime(row.get("completed_at"))
        
        return DatabaseTask(
            id=row["id"],
            title=row["title"],
            description=row.get("description", ""),
            status=row.get("status", "pending"),
            priority=row.get("priority", "medium"),
            tags=tags,
            parent_task_id=row.get("parent_task_id"),
            team_id=row.get("team_id"),
            created_at=created_at or datetime.now(),
            updated_at=updated_at or datetime.now(),
            completed_at=completed_at,
        )
    
    def _from_model(self, model: DatabaseTask) -> Dict[str, Any]:
        """Convert DatabaseTask to database row."""
        return {
            "id": model.id,
            "title": model.title,
            "description": model.description,
            "status": model.status,
            "priority": model.priority,
            "tags": self._serialize_json_field(model.tags),
            "parent_task_id": model.parent_task_id,
            "team_id": model.team_id,
            "created_at": self._serialize_datetime(model.created_at),
            "updated_at": self._serialize_datetime(model.updated_at),
            "completed_at": self._serialize_datetime(model.completed_at),
        }
    
    def list(self, team_id: Optional[str] = None, 
             status: Optional[str] = None,
             limit: int = 100) -> List[DatabaseTask]:
        """Get tasks with optional filters."""
        filters = {}
        if team_id is not None:
            filters["team_id"] = team_id
        if status is not None:
            filters["status"] = status
        
        tasks = super().list(**filters)
        return tasks[:limit]
    
    def count_by_status(self, team_id: Optional[str] = None) -> Dict[str, int]:
        """Count tasks by status."""
        if self.using_sqlite and self.db:
            query = "SELECT status, COUNT(*) as count FROM tasks"
            params = []
            if team_id:
                query += " WHERE team_id = ?"
                params.append(team_id)
            query += " GROUP BY status"
            
            cursor = self.db.execute(query, params)
            result = {}
            for row in cursor.fetchall():
                result[row["status"]] = row["count"]
            return result
        else:
            # Count in memory
            result = {}
            for task in self.mem_storage.values():
                if team_id and task.team_id != team_id:
                    continue
                result[task.status] = result.get(task.status, 0) + 1
            return result
    
    def get_tasks_by_parent(self, parent_task_id: str) -> List[DatabaseTask]:
        """Get child tasks of a parent task."""
        filters = {"parent_task_id": parent_task_id}
        return super().list(**filters)
