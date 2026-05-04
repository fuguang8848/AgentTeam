"""Event tracker for ClawTeam Event Tracking System (SpectrAI-inspired).

This module provides the core event tracking functionality,
storing events in a SQLite database for efficient querying.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from clawteam.team.models import get_data_dir


# Global event subscribers for SSE streaming
_event_subscribers: list[Callable[["ClawTeamEvent"], None]] = []
_subscriber_lock = threading.Lock()


class EventTracker:
    """Tracks and stores ClawTeam events in SQLite.

    Inspired by SpectrAI's event-driven approach, this tracker
    provides persistent event storage with efficient querying.
    """

    def __init__(self, db_path: Optional[str] = None):
        """Initialize the event tracker.

        Args:
            db_path: Path to the SQLite database file.
                     If None, uses CLAWTEAM_EVENTS_DB_PATH env var or default location.
        """
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = _get_default_db_path()

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = threading.Lock()

        # Initialize database schema
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_db(self) -> None:
        """Initialize the database schema."""
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                category TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                duration_ms REAL,
                team_name TEXT,
                agent_name TEXT,
                agent_id TEXT,
                session_id TEXT,
                task_id TEXT,
                severity TEXT NOT NULL DEFAULT 'info',
                message TEXT,
                data TEXT,
                source TEXT DEFAULT 'clawteam',
                correlation_id TEXT,
                created_at TEXT NOT NULL
            );
            
            CREATE INDEX IF NOT EXISTS idx_events_team ON events(team_name);
            CREATE INDEX IF NOT EXISTS idx_events_agent ON events(agent_name);
            CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
            CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
            CREATE INDEX IF NOT EXISTS idx_events_category ON events(category);
            CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);
            CREATE INDEX IF NOT EXISTS idx_events_task ON events(task_id);
        """)
        conn.commit()

    def track(self, event: "ClawTeamEvent") -> None:
        """Track a single event.

        Args:
            event: The ClawTeamEvent to track.
        """
        with self._lock:
            conn = self._get_conn()
            conn.execute(
                """
                INSERT INTO events (
                    id, event_type, category, timestamp, duration_ms,
                    team_name, agent_name, agent_id, session_id, task_id,
                    severity, message, data, source, correlation_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.event_type.value,
                    event.category.value,
                    event.timestamp,
                    event.duration_ms,
                    event.team_name,
                    event.agent_name,
                    event.agent_id,
                    event.session_id,
                    event.task_id,
                    event.severity.value,
                    event.message,
                    json.dumps(event.data),
                    event.source,
                    event.correlation_id,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
        # Notify subscribers (outside the lock to avoid deadlock)
        _notify_event_subscribers(event)

    def track_batch(self, events: List["ClawTeamEvent"]) -> None:
        """Track multiple events in a batch.

        Args:
            events: List of ClawTeamEvents to track.
        """
        if not events:
            return

        with self._lock:
            conn = self._get_conn()
            rows = [
                (
                    e.id,
                    e.event_type.value,
                    e.category.value,
                    e.timestamp,
                    e.duration_ms,
                    e.team_name,
                    e.agent_name,
                    e.agent_id,
                    e.session_id,
                    e.task_id,
                    e.severity.value,
                    e.message,
                    json.dumps(e.data),
                    e.source,
                    e.correlation_id,
                    datetime.now(timezone.utc).isoformat(),
                )
                for e in events
            ]
            conn.executemany(
                """
                INSERT INTO events (
                    id, event_type, category, timestamp, duration_ms,
                    team_name, agent_name, agent_id, session_id, task_id,
                    severity, message, data, source, correlation_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()
        # Notify subscribers for all events (outside the lock)
        for event in events:
            _notify_event_subscribers(event)

    def query(
        self,
        team_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        event_types: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        severity: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        order: str = "DESC",
    ) -> List[Dict[str, Any]]:
        """Query events with filters.

        Args:
            team_name: Filter by team name.
            agent_name: Filter by agent name.
            event_types: Filter by event types.
            categories: Filter by event categories.
            severity: Filter by severity level.
            since: Filter events after this ISO timestamp.
            until: Filter events before this ISO timestamp.
            session_id: Filter by session ID.
            task_id: Filter by task ID.
            limit: Maximum number of events to return.
            offset: Number of events to skip.
            order: Sort order - "ASC" for oldest first, "DESC" for newest first (default).

        Returns:
            List of event dictionaries.
        """
        conditions = []
        params = []

        if team_name:
            conditions.append("team_name = ?")
            params.append(team_name)

        if agent_name:
            conditions.append("agent_name = ?")
            params.append(agent_name)

        if event_types:
            placeholders = ",".join("?" * len(event_types))
            conditions.append(f"event_type IN ({placeholders})")
            params.extend(event_types)

        if categories:
            placeholders = ",".join("?" * len(categories))
            conditions.append(f"category IN ({placeholders})")
            params.extend(categories)

        if severity:
            conditions.append("severity = ?")
            params.append(severity)

        if since:
            conditions.append("timestamp >= ?")
            params.append(since)

        if until:
            conditions.append("timestamp <= ?")
            params.append(until)

        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)

        if task_id:
            conditions.append("task_id = ?")
            params.append(task_id)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
            SELECT * FROM events
            WHERE {where_clause}
            ORDER BY timestamp {order}
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        conn = self._get_conn()
        cursor = conn.execute(query, params)

        events = []
        for row in cursor.fetchall():
            event = dict(row)
            event["data"] = json.loads(event["data"]) if event["data"] else {}
            events.append(event)

        return events

    def get_events_for_dashboard(
        self,
        team_name: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get recent events for a team's dashboard.

        Args:
            team_name: The team name.
            limit: Maximum number of events.

        Returns:
            List of event dictionaries.
        """
        return self.query(team_name=team_name, limit=limit)

    def get_agent_timeline(
        self,
        agent_name: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get event timeline for an agent.

        Args:
            agent_name: The agent name.
            limit: Maximum number of events.

        Returns:
            List of event dictionaries sorted by timestamp (oldest first).
        """
        # Override the default DESC order to get chronological timeline
        return self.query(agent_name=agent_name, limit=limit, order="ASC")

    def get_task_events(
        self,
        task_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get all events related to a task.

        Args:
            task_id: The task ID.
            limit: Maximum number of events.

        Returns:
            List of event dictionaries.
        """
        return self.query(task_id=task_id, limit=limit)

    def get_event_stats(
        self,
        team_name: Optional[str] = None,
        since: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get event statistics.

        Args:
            team_name: Optional team name to filter by.
            since: Optional ISO timestamp to filter from.

        Returns:
            Dictionary with event statistics.
        """
        conditions = []
        params = []

        if team_name:
            conditions.append("team_name = ?")
            params.append(team_name)

        if since:
            conditions.append("timestamp >= ?")
            params.append(since)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        conn = self._get_conn()

        # Total count
        cursor = conn.execute(
            f"SELECT COUNT(*) as total FROM events WHERE {where_clause}",
            params,
        )
        total = cursor.fetchone()["total"]

        # By category
        cursor = conn.execute(
            f"""
            SELECT category, COUNT(*) as count 
            FROM events 
            WHERE {where_clause}
            GROUP BY category
            """,
            params,
        )
        by_category = {row["category"]: row["count"] for row in cursor.fetchall()}

        # By type
        cursor = conn.execute(
            f"""
            SELECT event_type, COUNT(*) as count 
            FROM events 
            WHERE {where_clause}
            GROUP BY event_type
            """,
            params,
        )
        by_type = {row["event_type"]: row["count"] for row in cursor.fetchall()}

        # By severity
        cursor = conn.execute(
            f"""
            SELECT severity, COUNT(*) as count 
            FROM events 
            WHERE {where_clause}
            GROUP BY severity
            """,
            params,
        )
        by_severity = {row["severity"]: row["count"] for row in cursor.fetchall()}

        # Recent activity (last 24 hours)
        last_24h = datetime.now(timezone.utc).timestamp() - 86400
        cursor = conn.execute(
            """
            SELECT DATE(timestamp) as day, COUNT(*) as count
            FROM events
            WHERE timestamp >= ?
            GROUP BY DATE(timestamp)
            ORDER BY day DESC
            LIMIT 7
            """,
            [datetime.fromtimestamp(last_24h, timezone.utc).isoformat()],
        )
        recent_activity = [{"day": row["day"], "count": row["count"]} for row in cursor.fetchall()]

        return {
            "total_events": total,
            "by_category": by_category,
            "by_type": by_type,
            "by_severity": by_severity,
            "recent_activity": recent_activity,
        }

    def clear_old_events(self, days: int = 30) -> int:
        """Clear events older than specified days.

        Args:
            days: Number of days to retain.

        Returns:
            Number of events deleted.
        """
        cutoff = datetime.now(timezone.utc).timestamp() - (days * 86400)
        cutoff_iso = datetime.fromtimestamp(cutoff, timezone.utc).isoformat()

        conn = self._get_conn()
        cursor = conn.execute(
            "DELETE FROM events WHERE timestamp < ?",
            [cutoff_iso],
        )
        conn.commit()

        return cursor.rowcount

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None


# Global tracker instance (lazy initialization)
_tracker: Optional[EventTracker] = None
_tracker_lock = threading.Lock()


def _get_default_db_path() -> Path:
    """Get default database path from environment or use default location."""
    import os
    env_path = os.environ.get("CLAWTEAM_EVENTS_DB_PATH")
    if env_path:
        return Path(env_path)
    return get_data_dir() / "events" / "clawteam_events.db"


def get_tracker() -> EventTracker:
    """Get the global event tracker instance.
    
    Returns:
        The global EventTracker instance.
    """
    global _tracker
    if _tracker is None:
        with _tracker_lock:
            if _tracker is None:
                _tracker = EventTracker()
    return _tracker


def set_tracker(tracker: EventTracker) -> None:
    """Set the global event tracker instance (for testing/dependency injection).
    
    Args:
        tracker: The EventTracker instance to use as the global instance.
    """
    global _tracker
    with _tracker_lock:
        _tracker = tracker


def reset_tracker() -> None:
    """Reset the global tracker instance (for testing)."""
    global _tracker
    with _tracker_lock:
        if _tracker is not None:
            _tracker.close()
            _tracker = None


def track_event(event: "ClawTeamEvent") -> None:
    """Convenience function to track a single event."""
    get_tracker().track(event)


def track_batch(events: List["ClawTeamEvent"]) -> None:
    """Convenience function to track multiple events."""
    get_tracker().track_batch(events)


def _notify_event_subscribers(event: "ClawTeamEvent") -> None:
    """Notify all subscribers of a new event (called after track/track_batch)."""
    with _subscriber_lock:
        for callback in _event_subscribers[:]:
            try:
                callback(event)
            except Exception:
                pass  # Don't let subscriber errors break event tracking


def add_event_subscriber(callback: Callable[["ClawTeamEvent"], None]) -> None:
    """Add an event subscriber callback.

    Args:
        callback: Function to call when a new event is tracked.
                  Will be called with the ClawTeamEvent as argument.
    """
    with _subscriber_lock:
        if callback not in _event_subscribers:
            _event_subscribers.append(callback)


def remove_event_subscriber(callback: Callable[["ClawTeamEvent"], None]) -> None:
    """Remove an event subscriber callback.

    Args:
        callback: The callback to remove.
    """
    with _subscriber_lock:
        if callback in _event_subscribers:
            _event_subscribers.remove(callback)


def get_event_subscriber_count() -> int:
    """Get the number of registered event subscribers."""
    with _subscriber_lock:
        return len(_event_subscribers)


__all__ = [
    "EventTracker",
    "get_tracker",
    "set_tracker",
    "reset_tracker",
    "track_event",
    "track_batch",
    "add_event_subscriber",
    "remove_event_subscriber",
    "get_event_subscriber_count",
]
