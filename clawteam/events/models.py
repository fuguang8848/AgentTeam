"""Event models for ClawTeam Event Tracking System (SpectrAI-inspired).

This module defines the core event types and schemas for tracking
team activities in an event-driven architecture.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


def _now_iso() -> str:
    """Return current time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


class EventType(str, Enum):
    """Core event types for ClawTeam.

    Inspired by SpectrAI's turn_complete event-driven approach,
    these events track all meaningful state changes in the system.
    """

    # Team lifecycle events
    TEAM_CREATED = "team_created"
    TEAM_DESTROYED = "team_destroyed"
    MEMBER_JOINED = "member_joined"
    MEMBER_LEFT = "member_left"
    MEMBER_ALIVE = "member_alive"  # Heartbeat/keepalive

    # Task lifecycle events
    TASK_CREATED = "task_created"
    TASK_STATUS_CHANGED = "task_status_changed"
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"
    TASK_BLOCKED = "task_blocked"

    # Agent/session lifecycle events
    AGENT_SPAWNED = "agent_spawned"
    AGENT_TERMINATED = "agent_terminated"
    AGENT_IDLE = "agent_idle"
    AGENT_ACTIVE = "agent_active"
    TURN_COMPLETE = "turn_complete"  # SpectrAI-inspired: marks end of agent turn
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"

    # Messaging events
    MESSAGE_SENT = "message_sent"
    MESSAGE_RECEIVED = "message_received"
    INBOX_NOTIFICATION = "inbox_notification"

    # Alert events
    ALERT_TRIGGERED = "alert_triggered"
    ALERT_ACKNOWLEDGED = "alert_acknowledged"
    ALERT_RESOLVED = "alert_resolved"

    # Cost/usage events
    USAGE_RECORDED = "usage_recorded"

    # Command events
    COMMAND_EXECUTED = "command_executed"

    # Error events
    ERROR_OCCURRED = "error_occurred"


class EventSeverity(str, Enum):
    """Severity levels for events."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class EventCategory(str, Enum):
    """Categories for organizing events."""

    TEAM = "team"
    TASK = "task"
    AGENT = "agent"
    SESSION = "session"
    MESSAGE = "message"
    ALERT = "alert"
    USAGE = "usage"
    SYSTEM = "system"


class ClawTeamEvent(BaseModel):
    """Base event model for all ClawTeam events.

    Inspired by SpectrAI's event-driven architecture, this model
    provides a consistent structure for all tracked events.
    """

    # Event identity
    id: str = Field(
        default_factory=lambda: (
            f"evt-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid_short()}"
        )
    )
    event_type: EventType
    category: EventCategory

    # Timing
    timestamp: str = Field(default_factory=_now_iso)
    duration_ms: Optional[float] = None  # For events with duration (e.g., turn_complete)

    # Source identification
    team_name: Optional[str] = None
    agent_name: Optional[str] = None
    agent_id: Optional[str] = None
    session_id: Optional[str] = None
    task_id: Optional[str] = None

    # Event data
    severity: EventSeverity = EventSeverity.INFO
    message: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)

    # Context
    source: str = "clawteam"  # Which component generated this event
    correlation_id: Optional[str] = None  # For linking related events

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "category": self.category.value,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "team_name": self.team_name,
            "agent_name": self.agent_name,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "severity": self.severity.value,
            "message": self.message,
            "data": self.data,
            "source": self.source,
            "correlation_id": self.correlation_id,
        }


def uuid_short() -> str:
    """Generate a short UUID for event IDs."""
    import uuid

    return uuid.uuid4().hex[:8]


# Convenience factory functions for common events


def create_team_event(
    event_type: EventType,
    team_name: str,
    agent_name: Optional[str] = None,
    message: str = "",
    data: Optional[Dict[str, Any]] = None,
) -> ClawTeamEvent:
    """Factory function for team-related events."""
    return ClawTeamEvent(
        event_type=event_type,
        category=EventCategory.TEAM,
        team_name=team_name,
        agent_name=agent_name,
        message=message,
        data=data or {},
    )


def create_task_event(
    event_type: EventType,
    task_id: str,
    team_name: Optional[str] = None,
    agent_name: Optional[str] = None,
    message: str = "",
    data: Optional[Dict[str, Any]] = None,
) -> ClawTeamEvent:
    """Factory function for task-related events."""
    return ClawTeamEvent(
        event_type=event_type,
        category=EventCategory.TASK,
        task_id=task_id,
        team_name=team_name,
        agent_name=agent_name,
        message=message,
        data=data or {},
    )


def create_agent_event(
    event_type: EventType,
    agent_name: str,
    agent_id: Optional[str] = None,
    team_name: Optional[str] = None,
    session_id: Optional[str] = None,
    message: str = "",
    data: Optional[Dict[str, Any]] = None,
    duration_ms: Optional[float] = None,
) -> ClawTeamEvent:
    """Factory function for agent-related events."""
    return ClawTeamEvent(
        event_type=event_type,
        category=EventCategory.AGENT,
        agent_name=agent_name,
        agent_id=agent_id,
        team_name=team_name,
        session_id=session_id,
        message=message,
        data=data or {},
        duration_ms=duration_ms,
    )


def create_session_event(
    event_type: EventType,
    session_id: str,
    agent_name: Optional[str] = None,
    team_name: Optional[str] = None,
    message: str = "",
    data: Optional[Dict[str, Any]] = None,
) -> ClawTeamEvent:
    """Factory function for session-related events."""
    return ClawTeamEvent(
        event_type=event_type,
        category=EventCategory.SESSION,
        session_id=session_id,
        agent_name=agent_name,
        team_name=team_name,
        message=message,
        data=data or {},
    )


def create_message_event(
    event_type: EventType,
    team_name: str,
    sender: Optional[str] = None,
    recipient: Optional[str] = None,
    message: str = "",
    data: Optional[Dict[str, Any]] = None,
) -> ClawTeamEvent:
    """Factory function for message-related events."""
    return ClawTeamEvent(
        event_type=event_type,
        category=EventCategory.MESSAGE,
        team_name=team_name,
        agent_name=sender,
        message=message,
        data=data or {},
    )


def create_alert_event(
    event_type: EventType,
    team_name: Optional[str] = None,
    agent_name: Optional[str] = None,
    message: str = "",
    severity: EventSeverity = EventSeverity.WARNING,
    data: Optional[Dict[str, Any]] = None,
) -> ClawTeamEvent:
    """Factory function for alert-related events."""
    return ClawTeamEvent(
        event_type=event_type,
        category=EventCategory.ALERT,
        team_name=team_name,
        agent_name=agent_name,
        message=message,
        severity=severity,
        data=data or {},
    )


def create_usage_event(
    team_name: str,
    session_id: str,
    input_tokens: int,
    output_tokens: int,
    estimated_cost: float,
    provider_id: str = "unknown",
    data: Optional[Dict[str, Any]] = None,
) -> ClawTeamEvent:
    """Factory function for usage/ cost tracking events."""
    return ClawTeamEvent(
        event_type=EventType.USAGE_RECORDED,
        category=EventCategory.USAGE,
        team_name=team_name,
        session_id=session_id,
        message=f"Usage: {input_tokens} in / {output_tokens} out / ${estimated_cost:.4f}",
        data=data
        or {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "estimated_cost": estimated_cost,
            "provider_id": provider_id,
        },
    )


__all__ = [
    "EventType",
    "EventSeverity",
    "EventCategory",
    "ClawTeamEvent",
    "create_team_event",
    "create_task_event",
    "create_agent_event",
    "create_session_event",
    "create_message_event",
    "create_alert_event",
    "create_usage_event",
]
