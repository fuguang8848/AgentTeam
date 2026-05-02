"""Base repository class."""

from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic
from datetime import datetime
import json

T = TypeVar("T")


class BaseRepository(Generic[T], ABC):
    """Base repository with common CRUD operations."""

    def __init__(self, db: Optional[sqlite3.Connection], using_sqlite: bool):
        self.db = db
        self.using_sqlite = using_sqlite
        self.mem_storage: Dict[str, T] = {}

    @abstractmethod
    def _table_name(self) -> str:
        """Return table name."""
        pass

    @abstractmethod
    def _id_field(self) -> str:
        """Return ID field name."""
        pass

    @abstractmethod
    def _to_model(self, row: Dict[str, Any]) -> T:
        """Convert database row to model."""
        pass

    @abstractmethod
    def _from_model(self, model: T) -> Dict[str, Any]:
        """Convert model to database row."""
        pass

    def create(self, model: T) -> T:
        """Create a new record."""
        data = self._from_model(model)

        if self.using_sqlite and self.db:
            # Build SQL query
            columns = ", ".join(data.keys())
            placeholders = ", ".join(["?"] * len(data))
            values = list(data.values())

            query = f"INSERT INTO {self._table_name()} ({columns}) VALUES ({placeholders})"
            self.db.execute(query, values)
            self.db.commit()

        # Store in memory
        model_id = data.get(self._id_field())
        if model_id:
            self.mem_storage[model_id] = model

        return model

    def get(self, id: str) -> Optional[T]:
        """Get record by ID."""
        if self.using_sqlite and self.db:
            query = f"SELECT * FROM {self._table_name()} WHERE {self._id_field()} = ?"
            cursor = self.db.execute(query, (id,))
            row = cursor.fetchone()
            if row:
                return self._to_model(dict(row))

        # Check memory storage
        return self.mem_storage.get(id)

    def list(self, **filters) -> List[T]:
        """List records with optional filters."""
        results: List[T] = []

        if self.using_sqlite and self.db:
            # Build WHERE clause
            where_clause = ""
            params = []
            if filters:
                conditions = []
                for key, value in filters.items():
                    if value is None:
                        continue
                    if isinstance(value, bool):
                        conditions.append(f"{key} = ?")
                        params.append(1 if value else 0)
                    else:
                        conditions.append(f"{key} = ?")
                        params.append(value)
                if conditions:
                    where_clause = "WHERE " + " AND ".join(conditions)

            query = f"SELECT * FROM {self._table_name()} {where_clause} ORDER BY created_at DESC"
            cursor = self.db.execute(query, params)
            for row in cursor.fetchall():
                results.append(self._to_model(dict(row)))
        else:
            # Filter in memory
            for model in self.mem_storage.values():
                match = True
                data = self._from_model(model)
                for key, value in filters.items():
                    if value is None:
                        continue
                    if data.get(key) != value:
                        match = False
                        break
                if match:
                    results.append(model)

        return results

    def update(self, id: str, updates: Dict[str, Any]) -> Optional[T]:
        """Update record."""
        existing = self.get(id)
        if not existing:
            return None

        # Serialize datetime objects for database storage
        db_updates = {}
        for key, value in updates.items():
            if isinstance(value, datetime):
                db_updates[key] = self._serialize_datetime(value)
            else:
                db_updates[key] = value

        # Update in SQLite
        if self.using_sqlite and self.db:
            if db_updates:
                set_clause = ", ".join([f"{k} = ?" for k in db_updates.keys()])
                params = list(db_updates.values()) + [id]
                query = f"UPDATE {self._table_name()} SET {set_clause} WHERE {self._id_field()} = ?"
                self.db.execute(query, params)
                self.db.commit()

        # Update in memory
        if id in self.mem_storage:
            # Create updated model
            existing_data = self._from_model(existing)
            existing_data.update(updates)
            updated_model = self._to_model(existing_data)
            self.mem_storage[id] = updated_model
            return updated_model

        return None

    def delete(self, id: str) -> bool:
        """Delete record."""
        if self.using_sqlite and self.db:
            query = f"DELETE FROM {self._table_name()} WHERE {self._id_field()} = ?"
            self.db.execute(query, (id,))
            self.db.commit()

        # Remove from memory
        if id in self.mem_storage:
            del self.mem_storage[id]
            return True

        return False

    def count(self, **filters) -> int:
        """Count records with optional filters."""
        if self.using_sqlite and self.db:
            where_clause = ""
            params = []
            if filters:
                conditions = []
                for key, value in filters.items():
                    if value is None:
                        continue
                    if isinstance(value, bool):
                        conditions.append(f"{key} = ?")
                        params.append(1 if value else 0)
                    else:
                        conditions.append(f"{key} = ?")
                        params.append(value)
                if conditions:
                    where_clause = "WHERE " + " AND ".join(conditions)

            query = f"SELECT COUNT(*) FROM {self._table_name()} {where_clause}"
            cursor = self.db.execute(query, params)
            return cursor.fetchone()[0]
        else:
            # Count in memory
            count = 0
            for model in self.mem_storage.values():
                match = True
                data = self._from_model(model)
                for key, value in filters.items():
                    if value is None:
                        continue
                    if data.get(key) != value:
                        match = False
                        break
                if match:
                    count += 1
            return count

    def _parse_json_field(self, value: Optional[str]) -> Any:
        """Parse JSON field."""
        if not value:
            return None
        try:
            return json.loads(value)
        except:
            return None

    def _serialize_json_field(self, value: Any) -> Optional[str]:
        """Serialize value to JSON."""
        if value is None:
            return None
        try:
            return json.dumps(value)
        except:
            return None

    def _parse_datetime(self, value: Optional[str]) -> Optional[datetime]:
        """Parse datetime string."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            # Try ISO format
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except:
            try:
                # Try SQLite format
                return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            except:
                return None

    def _serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        """Serialize datetime to ISO string."""
        if not value:
            return None
        return value.isoformat()
