"""Usage repository."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from .base import BaseRepository
from ..types import DatabaseUsage


class UsageRepository(BaseRepository[DatabaseUsage]):
    """Usage repository."""
    
    def _table_name(self) -> str:
        return "usage_stats"
    
    def _id_field(self) -> str:
        return "id"
    
    def _to_model(self, row: Dict[str, Any]) -> DatabaseUsage:
        """Convert database row to DatabaseUsage."""
        # Parse datetime
        timestamp = self._parse_datetime(row.get("timestamp"))
        
        return DatabaseUsage(
            id=row["id"],
            session_id=row["session_id"],
            team_id=row.get("team_id"),
            task_id=row.get("task_id"),
            provider_id=row["provider_id"],
            input_tokens=row.get("input_tokens", 0),
            output_tokens=row.get("output_tokens", 0),
            total_tokens=row.get("total_tokens", 0),
            estimated_cost=row.get("estimated_cost", 0.0),
            timestamp=timestamp or datetime.now(),
        )
    
    def _from_model(self, model: DatabaseUsage) -> Dict[str, Any]:
        """Convert DatabaseUsage to database row."""
        return {
            "id": model.id,
            "session_id": model.session_id,
            "team_id": model.team_id,
            "task_id": model.task_id,
            "provider_id": model.provider_id,
            "input_tokens": model.input_tokens,
            "output_tokens": model.output_tokens,
            "total_tokens": model.total_tokens,
            "estimated_cost": model.estimated_cost,
            "timestamp": self._serialize_datetime(model.timestamp),
        }
    
    def list(self, team_id: Optional[str] = None,
             provider_id: Optional[str] = None,
             start_date: Optional[str] = None,
             end_date: Optional[str] = None) -> List[DatabaseUsage]:
        """Get usage statistics with optional filters."""
        # Build WHERE clause for SQLite
        if self.using_sqlite and self.db:
            where_parts = []
            params = []
            
            if team_id is not None:
                where_parts.append("team_id = ?")
                params.append(team_id)
            
            if provider_id is not None:
                where_parts.append("provider_id = ?")
                params.append(provider_id)
            
            if start_date is not None:
                where_parts.append("timestamp >= ?")
                params.append(start_date)
            
            if end_date is not None:
                where_parts.append("timestamp <= ?")
                params.append(end_date)
            
            where_clause = ""
            if where_parts:
                where_clause = "WHERE " + " AND ".join(where_parts)
            
            query = f"SELECT * FROM {self._table_name()} {where_clause} ORDER BY timestamp DESC"
            cursor = self.db.execute(query, params)
            
            results = []
            for row in cursor.fetchall():
                results.append(self._to_model(dict(row)))
            return results
        else:
            # Filter in memory
            results = []
            for usage in self.mem_storage.values():
                match = True
                
                if team_id is not None and usage.team_id != team_id:
                    match = False
                
                if provider_id is not None and usage.provider_id != provider_id:
                    match = False
                
                if start_date is not None:
                    try:
                        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                        if usage.timestamp < start_dt:
                            match = False
                    except:
                        pass
                
                if end_date is not None:
                    try:
                        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                        if usage.timestamp > end_dt:
                            match = False
                    except:
                        pass
                
                if match:
                    results.append(usage)
            
            # Sort by timestamp descending
            results.sort(key=lambda x: x.timestamp, reverse=True)
            return results
    
    def get_total_usage(self, team_id: Optional[str] = None) -> Dict[str, Any]:
        """Get aggregated usage statistics."""
        if self.using_sqlite and self.db:
            query = """
                SELECT 
                    SUM(input_tokens) as total_input,
                    SUM(output_tokens) as total_output,
                    SUM(total_tokens) as total_tokens,
                    SUM(estimated_cost) as total_cost,
                    COUNT(*) as record_count
                FROM usage_stats
            """
            params = []
            if team_id:
                query += " WHERE team_id = ?"
                params.append(team_id)
            
            cursor = self.db.execute(query, params)
            row = cursor.fetchone()
            
            return {
                "total_input_tokens": row["total_input"] or 0,
                "total_output_tokens": row["total_output"] or 0,
                "total_tokens": row["total_tokens"] or 0,
                "total_cost": row["total_cost"] or 0.0,
                "record_count": row["record_count"] or 0,
            }
        else:
            # Aggregate in memory
            total_input = 0
            total_output = 0
            total_cost = 0.0
            record_count = 0
            
            for usage in self.mem_storage.values():
                if team_id and usage.team_id != team_id:
                    continue
                
                total_input += usage.input_tokens
                total_output += usage.output_tokens
                total_cost += usage.estimated_cost
                record_count += 1
            
            return {
                "total_input_tokens": total_input,
                "total_output_tokens": total_output,
                "total_tokens": total_input + total_output,
                "total_cost": total_cost,
                "record_count": record_count,
            }
    
    def get_usage_by_provider(self, team_id: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Get usage statistics grouped by provider."""
        if self.using_sqlite and self.db:
            query = """
                SELECT 
                    provider_id,
                    SUM(input_tokens) as total_input,
                    SUM(output_tokens) as total_output,
                    SUM(total_tokens) as total_tokens,
                    SUM(estimated_cost) as total_cost,
                    COUNT(*) as record_count
                FROM usage_stats
            """
            params = []
            if team_id:
                query += " WHERE team_id = ?"
                params.append(team_id)
            query += " GROUP BY provider_id"
            
            cursor = self.db.execute(query, params)
            
            result = {}
            for row in cursor.fetchall():
                result[row["provider_id"]] = {
                    "total_input_tokens": row["total_input"] or 0,
                    "total_output_tokens": row["total_output"] or 0,
                    "total_tokens": row["total_tokens"] or 0,
                    "total_cost": row["total_cost"] or 0.0,
                    "record_count": row["record_count"] or 0,
                }
            return result
        else:
            # Group in memory
            result = {}
            for usage in self.mem_storage.values():
                if team_id and usage.team_id != team_id:
                    continue
                
                if usage.provider_id not in result:
                    resu
