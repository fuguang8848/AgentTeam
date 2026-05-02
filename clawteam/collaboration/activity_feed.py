"""Activity Feed for ClawTeam collaboration.

Provides a real-time feed of team activities that agents can subscribe to.
Tracks actions like task updates, messages sent, file changes, etc.
"""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path


class ActivityType(str, Enum):
    """Types of activities in the feed."""

    # Task activities
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_BLOCKED = "task_blocked"
    TASK_COMMENT = "task_comment"

    # Messaging activities
    MESSAGE_SENT = "message_sent"
    MESSAGE_RECEIVED = "message_received"
    BROADCAST_SENT = "broadcast_sent"

    # Collaboration activities
    CONTEXT_POSTED = "context_posted"
    CONTEXT_UPDATED = "context_updated"
    PRESENCE_CHANGED = "presence_changed"

    # Code activities
    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    FILE_DELETED = "file_deleted"

    # Team activities
    AGENT_JOINED = "agent_joined"
    AGENT_LEFT = "agent_left"
    PLAN_SUBMITTED = "plan_submitted"
    PLAN_APPROVED = "plan_approved"
    PLAN_REJECTED = "plan_rejected"

    # System activities
    ALERT_TRIGGERED = "alert_triggered"
    ERROR_OCCURRED = "error_occurred"
    SYSTEM_UPDATE = "system_update"


@dataclass
class ActivityEntry:
    """An activity entry in the feed.

    Represents something that happened in the team that others might want to know about.
    """

    id: str
    type: ActivityType
    agent_name: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Activity details
    title: str = ""
    description: Optional[str] = None

    # References
    task_id: Optional[str] = None
    message_id: Optional[str] = None
    file_path: Optional[str] = None
    target_agent: Optional[str] = None  # For @mentions, etc.

    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Visibility
    is_private: bool = False  # Only visible to mentioned parties

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["type"] = self.type.value if isinstance(self.type, ActivityType) else self.type
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActivityEntry":
        """Create from dictionary."""
        if isinstance(data.get("type"), str):
            data["type"] = ActivityType(data["type"])
        return cls(**data)


class ActivityFeed:
    """Real-time activity feed for team collaboration.

    Features:
    - Append-only feed of team activities
    - Subscribe to specific activity types
    - Filter by agent, time range, or type
    - Automatic cleanup of old entries
    - Real-time callbacks for new entries

    Example:
        feed = ActivityFeed(team_name="dev-team")

        # Record an activity
        feed.record(
            type=ActivityType.TASK_COMPLETED,
            agent_name="alice",
            title="Completed authentication module",
            task_id="task-123",
        )

        # Subscribe to activity
        def on_activity(entry):
            print(f"Activity: {entry.title}")

        feed.subscribe(on_activity, activity_types=[ActivityType.TASK_COMPLETED])

        # Get recent activities
        recent = feed.get_recent(limit=10)
    """

    MAX_FEED_ENTRIES = 1000  # Keep last 1000 entries in memory
    DEFAULT_RETENTION_DAYS = 7  # Keep entries for 7 days by default

    def __init__(
        self,
        team_name: str,
        persist_dir: Optional[Path] = None,
        retention_days: int = DEFAULT_RETENTION_DAYS,
    ):
        self.team_name = team_name
        self._persist_dir = persist_dir
        self._retention_days = retention_days

        # In-memory feed: list of ActivityEntry (ordered by time)
        self._feed: List[ActivityEntry] = []

        # Subscribers: callback -> list of activity types (empty = all)
        self._subscribers: Dict[Callable, List[Optional[ActivityType]]] = {}

        # Lock for thread safety
        self._lock = threading.RLock()

        if persist_dir:
            persist_dir.mkdir(parents=True, exist_ok=True)
            self._load_feed()

    def record(
        self,
        type: ActivityType,
        agent_name: str,
        title: str,
        description: Optional[str] = None,
        task_id: Optional[str] = None,
        message_id: Optional[str] = None,
        file_path: Optional[str] = None,
        target_agent: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        is_private: bool = False,
    ) -> ActivityEntry:
        """Record a new activity in the feed.

        Args:
            type: Type of activity
            agent_name: Who performed the activity
            title: Brief title for the activity
            description: Optional detailed description
            task_id: Optional related task
            message_id: Optional related message
            file_path: Optional related file
            target_agent: Optional agent this activity is directed at
            tags: Optional tags for filtering
            metadata: Optional additional metadata
            is_private: If True, only visible to target_agent (if specified)

        Returns:
            The created ActivityEntry
        """
        entry = ActivityEntry(
            id=f"act_{uuid.uuid4().hex[:12]}",
            type=type,
            agent_name=agent_name,
            title=title,
            description=description,
            task_id=task_id,
            message_id=message_id,
            file_path=file_path,
            target_agent=target_agent,
            tags=tags or [],
            metadata=metadata or {},
            is_private=is_private,
        )

        with self._lock:
            self._feed.append(entry)

            # Trim if too long
            if len(self._feed) > self.MAX_FEED_ENTRIES:
                self._feed = self._feed[-self.MAX_FEED_ENTRIES :]

            if self._persist_dir:
                self._save_entry(entry)

        # Notify subscribers
        self._notify_subscribers(entry)

        return entry

    def get_recent(
        self,
        limit: int = 50,
        agent_filter: Optional[str] = None,
        type_filter: Optional[List[ActivityType]] = None,
        viewer_name: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> List[ActivityEntry]:
        """Get recent activities with optional filters.

        Args:
            limit: Maximum number of entries to return
            agent_filter: Only show activities from this agent
            type_filter: Only show activities of these types
            viewer_name: Viewing agent (for private entry filtering)
            since: Only show activities after this time

        Returns:
            List of ActivityEntry objects (newest first)
        """
        with self._lock:
            result = []

            for entry in reversed(self._feed):
                # Skip private entries not directed at viewer
                if entry.is_private:
                    if entry.target_agent and entry.target_agent != viewer_name:
                        continue
                    if entry.agent_name != viewer_name and entry.target_agent != viewer_name:
                        continue

                # Apply filters
                if agent_filter and entry.agent_name != agent_filter:
                    continue

                if type_filter and entry.type not in type_filter:
                    continue

                if since:
                    entry_time = datetime.fromisoformat(entry.timestamp)
                    if entry_time < since:
                        continue

                result.append(entry)

                if len(result) >= limit:
                    break

            return result

    def get_by_task(self, task_id: str, viewer_name: Optional[str] = None) -> List[ActivityEntry]:
        """Get all activities related to a specific task."""
        with self._lock:
            return [
                entry
                for entry in reversed(self._feed)
                if entry.task_id == task_id
                and (
                    not entry.is_private
                    or entry.agent_name == viewer_name
                    or entry.target_agent == viewer_name
                )
            ]

    def get_by_agent(
        self,
        agent_name: str,
        viewer_name: Optional[str] = None,
        limit: int = 50,
    ) -> List[ActivityEntry]:
        """Get activities by a specific agent."""
        return self.get_recent(
            limit=limit,
            agent_filter=agent_name,
            viewer_name=viewer_name,
        )

    def get_mentions(
        self, agent_name: str, viewer_name: Optional[str] = None
    ) -> List[ActivityEntry]:
        """Get all activities that mention an agent (as target_agent)."""
        with self._lock:
            return [
                entry
                for entry in reversed(self._feed)
                if entry.target_agent == agent_name
                and (not entry.is_private or entry.agent_name == viewer_name)
            ]

    def subscribe(
        self,
        callback: Callable[[ActivityEntry], None],
        activity_types: Optional[List[ActivityType]] = None,
    ) -> None:
        """Subscribe to activity feed updates.

        Args:
            callback: Function to call when matching activity is recorded
            activity_types: If specified, only call callback for these types.
                          If None/empty, call for all types.
        """
        with self._lock:
            self._subscribers[callback] = activity_types or []

    def unsubscribe(self, callback: Callable) -> bool:
        """Unsubscribe from activity feed.

        Returns True if callback was found and removed.
        """
        with self._lock:
            if callback in self._subscribers:
                del self._subscribers[callback]
                return True
            return False

    def _notify_subscribers(self, entry: ActivityEntry) -> None:
        """Notify subscribers of a new entry."""
        for callback, types in list(self._subscribers.items()):
            try:
                if not types or entry.type in types:
                    callback(entry)
            except Exception:
                import logging

                logging.getLogger(__name__).error(f"Activity feed subscriber error: {callback}")

    def cleanup_old_entries(self) -> int:
        """Remove entries older than retention period.

        Returns number of entries removed.
        """
        with self._lock:
            cutoff = datetime.now(timezone.utc) - timedelta(days=self._retention_days)

            original_len = len(self._feed)

            self._feed = [
                entry for entry in self._feed if datetime.fromisoformat(entry.timestamp) >= cutoff
            ]

            # Also clean up persisted files
            if self._persist_dir:
                self._cleanup_persisted_entries(cutoff)

            return original_len - len(self._feed)

    def get_stats(self) -> Dict[str, Any]:
        """Get activity feed statistics."""
        with self._lock:
            if not self._feed:
                return {
                    "total_entries": 0,
                    "by_type": {},
                    "by_agent": {},
                }

            type_counts: Dict[str, int] = {}
            agent_counts: Dict[str, int] = {}

            for entry in self._feed:
                type_key = entry.type.value if isinstance(entry.type, ActivityType) else entry.type
                type_counts[type_key] = type_counts.get(type_key, 0) + 1
                agent_counts[entry.agent_name] = agent_counts.get(entry.agent_name, 0) + 1

            return {
                "total_entries": len(self._feed),
                "by_type": type_counts,
                "by_agent": agent_counts,
                "oldest_entry": self._feed[0].timestamp if self._feed else None,
                "newest_entry": self._feed[-1].timestamp if self._feed else None,
            }

    def _save_entry(self, entry: ActivityEntry) -> None:
        """Persist entry to disk."""
        if not self._persist_dir:
            return
        try:
            file_path = self._persist_dir / f"activity-{entry.id}.jsonl"
            file_path.write_text(json.dumps(entry.to_dict(), ensure_ascii=False), encoding="utf-8")
        except Exception:
            import logging

            logging.getLogger(__name__).warning(f"Failed to persist activity {entry.id}")

    def _cleanup_persisted_entries(self, cutoff: datetime) -> None:
        """Remove persisted entries older than cutoff."""
        if not self._persist_dir or not self._persist_dir.exists():
            return

        for file_path in self._persist_dir.glob("activity-*.jsonl"):
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                entry_time = datetime.fromisoformat(data["timestamp"])
                if entry_time < cutoff:
                    file_path.unlink()
            except Exception:
                pass

    def _load_feed(self) -> None:
        """Load feed from disk."""
        if not self._persist_dir or not self._persist_dir.exists():
            return

        with self._lock:
            for file_path in sorted(self._persist_dir.glob("activity-*.jsonl")):
                try:
                    data = json.loads(file_path.read_text(encoding="utf-8"))
                    entry = ActivityEntry.from_dict(data)
                    self._feed.append(entry)
                except Exception:
                    import logging

                    logging.getLogger(__name__).warning(f"Failed to load activity from {file_path}")

            # Sort by timestamp
            self._feed.sort(key=lambda e: e.timestamp)

            # Trim to max
            if len(self._feed) > self.MAX_FEED_ENTRIES:
                self._feed = self._feed[-self.MAX_FEED_ENTRIES :]
