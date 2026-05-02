"""Session awareness for ClawTeam: track agent sessions, activity, and context.

This module provides real-time awareness of:
 and status
- Session activity tracking (heartbeats, recent messages)
- File change attribution across sessions
- Session grouping and team context
- Cross-session coordination primitives
"""

import time
import threading
import json
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any
from pathlib import Path

from .tracker.diff_tracker import DiffTracker
from .tracker.file_tracker import FileChangeTracker


class SessionStatus(Enum):
    """Session lifecycle status."""

    CREATED = "created"  # Session created but not yet active
    ACTIVE = "active"  # Actively processing messages
    IDLE = "idle"  # No recent activity
    PAUSED = "paused"  # Manually paused by user/admin
    TERMINATED = "terminated"  # Session ended


class SessionActivityLevel(Enum):
    """Activity level based on recent interactions."""

    HIGH = "high"  # Multiple messages in last minute
    MEDIUM = "medium"  # Recent activity within 5 minutes
    LOW = "low"  # Some activity within 30 minutes
    INACTIVE = "inactive"  # No activity in over 30 minutes


@dataclass
class SessionContext:
    """Contextual information about a session."""

    session_id: str
    agent_name: str
    team_name: str

    # Activity tracking
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    message_count: int = 0
    file_change_count: int = 0

    # Status
    status: SessionStatus = SessionStatus.CREATED
    activity_level: SessionActivityLevel = SessionActivityLevel.LOW

    # Context
    current_task: Optional[str] = None
    current_file: Optional[str] = None
    working_directory: Optional[str] = None

    # Metadata
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        data["last_activity"] = self.last_activity.isoformat()
        data["status"] = self.status.value
        data["activity_level"] = self.activity_level.value
        data["tags"] = list(self.tags)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionContext":
        """Create from dictionary."""
        # Convert string dates back to datetime
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if isinstance(data.get("last_activity"), str):
            data["last_activity"] = datetime.fromisoformat(data["last_activity"])

        # Convert enums
        if isinstance(data.get("status"), str):
            data["status"] = SessionStatus(data["status"])
        if isinstance(data.get("activity_level"), str):
            data["activity_level"] = SessionActivityLevel(data["activity_level"])

        # Convert tags
        if isinstance(data.get("tags"), list):
            data["tags"] = set(data["tags"])

        return cls(**data)


class AgentSessionTracker:
    """Tracks a single agent session lifecycle and activity."""

    def __init__(self, session_id: str, agent_name: str, team_name: str):
        self.session_id = session_id
        self.agent_name = agent_name
        self.team_name = team_name

        # Core context
        self.context = SessionContext(
            session_id=session_id,
            agent_name=agent_name,
            team_name=team_name,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            status=SessionStatus.ACTIVE,  # New sessions are active by default
        )

        # Dependencies
        # Note: FileChangeTracker and DiffTracker are optional
        # They can be lazily initialized if needed
        self.file_tracker = None
        self.diff_tracker = None

        # State
        self._lock = threading.RLock()
        self._activity_timeout = timedelta(minutes=30)
        self._high_activity_window = timedelta(minutes=1)

    def update_activity(self, message: Optional[str] = None) -> None:
        """Update session activity timestamp."""
        with self._lock:
            self.context.last_activity = datetime.now()
            if message:
                self.context.message_count += 1

            # Update activity level
            self._update_activity_level()

    def _update_activity_level(self) -> None:
        """Update activity level based on recent activity."""
        now = datetime.now()
        time_since_activity = now - self.context.last_activity

        # Check for high activity (multiple messages in last minute)
        recent_messages = self._get_recent_message_count(self._high_activity_window)

        if time_since_activity < timedelta(minutes=1) and recent_messages >= 3:
            self.context.activity_level = SessionActivityLevel.HIGH
        elif time_since_activity < timedelta(minutes=5):
            self.context.activity_level = SessionActivityLevel.MEDIUM
        elif time_since_activity < timedelta(minutes=30):
            self.context.activity_level = SessionActivityLevel.LOW
        else:
            self.context.activity_level = SessionActivityLevel.INACTIVE

        # Update status based on activity
        if self.context.activity_level == SessionActivityLevel.INACTIVE:
            self.context.status = SessionStatus.IDLE
        elif self.context.status == SessionStatus.IDLE:
            self.context.status = SessionStatus.ACTIVE

    def _get_recent_message_count(self, window: timedelta) -> int:
        """Get number of messages in recent window."""
        # TODO: Implement message history tracking
        # For now, return a simple estimate
        with self._lock:
            if window <= self._high_activity_window:
                # Assume high activity if we just got a message
                return 1 if self.context.message_count > 0 else 0
            return self.context.message_count

    def track_file_change(
        self,
        path: str,
        change_type: str = "modified",
        diff: Optional[str] = None,
    ) -> None:
        """Track a file change from this session."""
        with self._lock:
            self.context.file_change_count += 1
            self.context.current_file = path

            # Track via file tracker if available
            if self.file_tracker:
                self.file_tracker.track_manual_change(
                    file_path=path,
                    change_type=change_type,
                    agent_name=self.agent_name,
                    session_id=self.session_id,
                )

            # Update activity
            self.update_activity()

    def set_current_task(self, task: str) -> None:
        """Set the current task being worked on."""
        with self._lock:
            self.context.current_task = task
            self.update_activity()

    def set_working_directory(self, directory: str) -> None:
        """Set the current working directory."""
        with self._lock:
            self.context.working_directory = directory

    def add_tag(self, tag: str) -> None:
        """Add a tag to the session."""
        with self._lock:
            self.context.tags.add(tag)

    def get_context(self) -> SessionContext:
        """Get current session context."""
        with self._lock:
            return self.context

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of session activity."""
        with self._lock:
            return {
                "session_id": self.session_id,
                "agent_name": self.agent_name,
                "status": self.context.status.value,
                "activity_level": self.context.activity_level.value,
                "message_count": self.context.message_count,
                "file_change_count": self.context.file_change_count,
                "current_task": self.context.current_task,
                "current_file": self.context.current_file,
                "tags": list(self.context.tags),
                "active_minutes": int(
                    (datetime.now() - self.context.created_at).total_seconds() / 60
                ),
                "minutes_inactive": int(
                    (datetime.now() - self.context.last_activity).total_seconds() / 60
                ),
            }

    def to_json(self) -> str:
        """Serialize session to JSON."""
        with self._lock:
            return json.dumps(self.context.to_dict(), indent=2)

    def from_json(self, data: str) -> None:
        """Load session from JSON."""
        with self._lock:
            self.context = SessionContext.from_dict(json.loads(data))


class SessionAwarenessManager:
    """Manages awareness of all active sessions."""

    def __init__(
        self,
        team_name: str,
    ):
        self.team_name = team_name

        # Session tracking
        self._sessions: Dict[str, AgentSessionTracker] = {}
        self._lock = threading.RLock()

    def register_session(
        self,
        session_id: str,
        agent_name: str,
        initial_context: Optional[Dict[str, Any]] = None,
    ) -> AgentSessionTracker:
        """Register a new session."""
        with self._lock:
            if session_id in self._sessions:
                return self._sessions[session_id]

            tracker = AgentSessionTracker(session_id, agent_name, self.team_name)

            # Apply initial context
            if initial_context:
                if "current_task" in initial_context:
                    tracker.set_current_task(initial_context["current_task"])
                if "working_directory" in initial_context:
                    tracker.set_working_directory(initial_context["working_directory"])
                if "tags" in initial_context:
                    for tag in initial_context["tags"]:
                        tracker.add_tag(tag)

            self._sessions[session_id] = tracker
            return tracker

    def unregister_session(self, session_id: str) -> bool:
        """Unregister a session."""
        with self._lock:
            if session_id in self._sessions:
                tracker = self._sessions[session_id]
                tracker.context.status = SessionStatus.TERMINATED
                del self._sessions[session_id]
                return True
            return False

    def get_session_tracker(self, session_id: str) -> Optional[AgentSessionTracker]:
        """Get session tracker by ID."""
        with self._lock:
            return self._sessions.get(session_id)

    def get_active_sessions(self) -> List[AgentSessionTracker]:
        """Get all active (non-terminated) sessions."""
        with self._lock:
            return [
                tracker
                for tracker in self._sessions.values()
                if tracker.context.status != SessionStatus.TERMINATED
            ]

    def get_sessions_by_agent(self, agent_name: str) -> List[AgentSessionTracker]:
        """Get all sessions for a specific agent."""
        with self._lock:
            return [
                tracker
                for tracker in self._sessions.values()
                if tracker.agent_name == agent_name
                and tracker.context.status != SessionStatus.TERMINATED
            ]

    def get_sessions_by_activity(
        self, min_level: SessionActivityLevel
    ) -> List[AgentSessionTracker]:
        """Get sessions with at least specified activity level."""
        with self._lock:
            return [
                tracker
                for tracker in self._sessions.values()
                if tracker.context.activity_level.value >= min_level.value
                and tracker.context.status != SessionStatus.TERMINATED
            ]

    def get_team_summary(self) -> Dict[str, Any]:
        """Get summary of all sessions in team."""
        with self._lock:
            sessions = list(self._sessions.values())

            active = [
                s
                for s in sessions
                if s.context.status in [SessionStatus.ACTIVE, SessionStatus.CREATED]
            ]
            idle = [s for s in sessions if s.context.status == SessionStatus.IDLE]

            return {
                "team_name": self.team_name,
                "total_sessions": len(sessions),
                "active_sessions": len(active),
                "idle_sessions": len(idle),
                "agents": list(set(s.agent_name for s in sessions)),
                "total_messages": sum(s.context.message_count for s in sessions),
                "total_file_changes": sum(s.context.file_change_count for s in sessions),
                "sessions": [s.get_summary() for s in sessions],
            }

    def find_collaborators(
        self,
        session_id: str,
        max_sessions: int = 3,
    ) -> List[Dict[str, Any]]:
        """Find potential collaborators for a session.

        Looks for sessions:
        1. Working on similar files
        2. With similar tasks/tags
        3. Currently active
        """
        current_tracker = self.get_session_tracker(session_id)
        if not current_tracker:
            return []

        current_context = current_tracker.get_context()

        candidates = []
        with self._lock:
            for tracker in self._sessions.values():
                if tracker.session_id == session_id:
                    continue

                if tracker.context.status == SessionStatus.TERMINATED:
                    continue

                context = tracker.get_context()

                # Calculate similarity score
                score = 0

                # File similarity
                if current_context.current_file and context.current_file:
                    if (
                        Path(current_context.current_file).parent
                        == Path(context.current_file).parent
                    ):
                        score += 2
                    elif current_context.current_file == context.current_file:
                        score += 5

                # Task similarity
                if current_context.current_task and context.current_task:
                    if current_context.current_task.lower() in context.current_task.lower():
                        score += 3
                    elif context.current_task.lower() in current_context.current_task.lower():
                        score += 3

                # Tag overlap
                tag_overlap = len(current_context.tags & context.tags)
                score += tag_overlap

                # Activity bonus
                if tracker.context.activity_level == SessionActivityLevel.HIGH:
                    score += 2
                elif tracker.context.activity_level == SessionActivityLevel.MEDIUM:
                    score += 1

                if score > 0:
                    candidates.append(
                        {
                            "session_id": tracker.session_id,
                            "agent_name": tracker.agent_name,
                            "score": score,
                            "current_task": context.current_task,
                            "current_file": context.current_file,
                            "activity_level": context.activity_level.value,
                            "tags": list(context.tags),
                        }
                    )

        # Sort by score and limit
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:max_sessions]

    def broadcast_to_team(
        self,
        message: str,
        source_session_id: str,
        message_type: str = "team_announcement",
    ) -> Dict[str, Any]:
        """Broadcast a message to all sessions in team.

        Returns a dict of session_ids to delivery status.
        """
        results = {}
        with self._lock:
            for tracker in self._sessions.values():
                if tracker.session_id == source_session_id:
                    continue
                results[tracker.session_id] = {
                    "agent_name": tracker.agent_name,
                    "status": "queued",
                    "message": message,
                    "message_type": message_type,
                    "timestamp": datetime.now().isoformat(),
                }
        return results

    def cleanup_inactive_sessions(self, max_inactive_minutes: int = 60) -> int:
        """Clean up sessions inactive for too long.

        Returns number of sessions cleaned up.
        """
        cleaned = 0
        now = datetime.now()

        with self._lock:
            to_remove = []

            for session_id, tracker in self._sessions.items():
                inactive_minutes = (now - tracker.context.last_activity).total_seconds() / 60

                if inactive_minutes > max_inactive_minutes:
                    to_remove.append(session_id)

            for session_id in to_remove:
                self.unregister_session(session_id)
                cleaned += 1

        return cleaned

    def save_state(self, filepath: str) -> None:
        """Save session state to file."""
        with self._lock:
            state = {
                "team_name": self.team_name,
                "sessions": {
                    session_id: tracker.to_json() for session_id, tracker in self._sessions.items()
                },
            }

            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)

    def load_state(self, filepath: str) -> None:
        """Load session state from file."""
        if not Path(filepath).exists():
            return

        with self._lock:
            with open(filepath, "r", encoding="utf-8") as f:
                state = json.load(f)

            # Clear existing sessions
            self._sessions.clear()

            # Load sessions
            for session_id, session_json in state.get("sessions", {}).items():
                try:
                    data = json.loads(session_json)
                    tracker = AgentSessionTracker(
                        data["session_id"],
                        data["agent_name"],
                        data["team_name"],
                    )
                    tracker.from_json(session_json)
                    self._sessions[session_id] = tracker
                except Exception as e:
                    print(f"Failed to load session {session_id}: {e}")


# Global manager instance
_global_manager: Optional[SessionAwarenessManager] = None


def get_session_awareness_manager(
    team_name: str = "default",
) -> SessionAwarenessManager:
    """Get or create global session awareness manager."""
    global _global_manager

    if _global_manager is None:
        _global_manager = SessionAwarenessManager(team_name=team_name)
    elif _global_manager.team_name != team_name:
        # Reset if team name changed
        _global_manager = SessionAwarenessManager(team_name=team_name)

    return _global_manager


def register_session(
    session_id: str,
    agent_name: str,
    team_name: str = "default",
    initial_context: Optional[Dict[str, Any]] = None,
) -> AgentSessionTracker:
    """Register a session with global manager."""
    manager = get_session_awareness_manager(team_name)
    return manager.register_session(session_id, agent_name, initial_context)


def get_session_tracker(
    session_id: str,
    team_name: str = "default",
) -> Optional[AgentSessionTracker]:
    """Get session tracker from global manager."""
    manager = get_session_awareness_manager(team_name)
    return manager.get_session_tracker(session_id)


def get_team_summary(team_name: str = "default") -> Dict[str, Any]:
    """Get team summary from global manager."""
    manager = get_session_awareness_manager(team_name)
    return manager.get_team_summary()
