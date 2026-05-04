"""Base repository class."""

from __future__ import annotations

import json
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

T = TypeVar("T")


class BaseRepository(Generic[T], ABC):
    """Base repository with common CRUD operations and batch support."""

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

    def create_batch(self, models: List[T]) -> List[T]:
        """Create multiple records in a single transaction."""
        if not models:
            return []

        if self.using_sqlite and self.db:
            # Collect all data
            data_list = [self._from_model(model) for model in models]

            # Build batch INSERT query
            columns = ", ".join(data_list[0].keys())
            placeholders = ", ".join(["?"] * len(data_list[0]))
            query = f"INSERT INTO {self._table_name()} ({columns}) VALUES ({placeholders})"

            # Execute all in one transaction
            cursor = self.db.cursor()
            try:
                cursor.executemany(query, [tuple(d.values()) for d in data_list])
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise

        # Store in memory
        for model in models:
            model_id = self._from_model(model).get(self._id_field())
            if model_id:
                self.mem_storage[model_id] = model

        return models

    def update_batch(self, ids: List[str], updates: Dict[str, Any]) -> int:
        """Update multiple records by ID in a single transaction.

        Args:
            ids: List of record IDs to update
            updates: Dictionary of field updates

        Returns:
            Number of records updated
        """
        if not ids or not updates:
            return 0

        # Serialize datetime objects for database storage
        db_updates = {}
        for key, value in updates.items():
            if isinstance(value, datetime):
                db_updates[key] = self._serialize_datetime(value)
            else:
                db_updates[key] = value

        updated_count = 0

        if self.using_sqlite and self.db:
            set_clause = ", ".join([f"{k} = ?" for k in db_updates.keys()])
            params = list(db_updates.values())

            cursor = self.db.cursor()
            try:
                for id_val in ids:
                    query = f"UPDATE {self._table_name()} SET {set_clause} WHERE {self._id_field()} = ?"
                    cursor.execute(query, params + [id_val])
                    updated_count += cursor.rowcount
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise

        # Update memory storage
        for id_val in ids:
            if id_val in self.mem_storage:
                existing_data = self._from_model(self.mem_storage[id_val])
                existing_data.update(updates)
                self.mem_storage[id_val] = self._to_model(existing_data)
                updated_count += 1

        return updated_count

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

    def get_batch(self, ids: List[str]) -> List[T]:
        """Get multiple records by ID.

        Args:
            ids: List of record IDs to retrieve

        Returns:
            List of records found (in same order as input)
        """
        if not ids:
            return []

        results = []

        if self.using_sqlite and self.db:
            placeholders = ", ".join(["?"] * len(ids))
            query = f"SELECT * FROM {self._table_name()} WHERE {self._id_field()} IN ({placeholders})"
            cursor = self.db.execute(query, tuple(ids))
            rows = {row[self._id_field()]: self._to_model(dict(row)) for row in cursor.fetchall()}

            # Maintain order
            for id_val in ids:
                if id_val in rows:
                    results.append(rows[id_val])
        else:
            for id_val in ids:
                if id_val in self.mem_storage:
                    results.append(self.mem_storage[id_val])

        return results

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

    def delete_batch(self, ids: List[str]) -> int:
        """Delete multiple records by ID in a single transaction.

        Args:
            ids: List of record IDs to delete

        Returns:
            Number of records deleted
        """
        if not ids:
            return 0

        deleted_count = 0

        if self.using_sqlite and self.db:
            placeholders = ", ".join(["?"] * len(ids))
            query = f"DELETE FROM {self._table_name()} WHERE {self._id_field()} IN ({placeholders})"
            cursor = self.db.cursor()
            try:
                cursor.execute(query, tuple(ids))
                deleted_count = cursor.rowcount
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise

        # Remove from memory
        for id_val in ids:
            if id_val in self.mem_storage:
                del self.mem_storage[id_val]
                deleted_count += 1

        return deleted_count

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
