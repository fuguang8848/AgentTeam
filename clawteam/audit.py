"""Audit logging for ClawTeam multi-agent teams.

Records all significant events in append-only log files for compliance,
debugging, and historical analysis. Each team has its own audit log directory.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from clawteam.fileutil import atomic_write_text
from clawteam.paths import ensure_within_root, validate_identifier


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _audit_log_path(team_name: str) -> Path:
    """Get the audit log file path for a team."""
    from clawteam.team.models import get_data_dir

    root = ensure_within_root(get_data_dir() / "audit", validate_identifier(team_name, "team name"))
    root.mkdir(parents=True, exist_ok=True)
    return root / "audit.log"


class AuditEventType(str, Enum):
    """Types of auditable events in ClawTeam."""

    TASK_CREATED = "task_created"
    TASK_ASSIGNED = "task_assigned"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_BLOCKED = "task_blocked"
    TASK_UNBLOCKED = "task_unblocked"
    AGENT_JOINED = "agent_joined"
    AGENT_LEFT = "agent_left"
    AGENT_IDLE = "agent_idle"
    AGENT_SHUTDOWN = "agent_shutdown"
    TEAM_CREATED = "team_created"
    TEAM_CONFIG_UPDATED = "team_config_updated"
    MESSAGE_SENT = "message_sent"
    DRIFT_ALERT_CREATED = "drift_alert_created"
    DRIFT_ALERT_ACKNOWLEDGED = "drift_alert_acknowledged"
    QUALITY_SCORE_ADDED = "quality_score_added"
    ROUTING_DECISION = "routing_decision"
    ALERT_TRIGGERED = "alert_triggered"
    ALERT_ACKNOWLEDGED = "alert_acknowledged"


@dataclass
class AuditEvent:
    """A single audit log entry."""

    event_id: str
    event_type: AuditEventType
    timestamp: str
    team: str
    actor: str
    target: str | None = None
    details: dict[str, Any] | None = None
    context: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "team": self.team,
            "actor": self.actor,
        }
        if self.target is not None:
            result["target"] = self.target
        if self.details is not None:
            result["details"] = self.details
        if self.context is not None:
            result["context"] = self.context
        return result

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":"))


def log_audit_event(
    team: str,
    event_type: AuditEventType,
    actor: str,
    target: str | None = None,
    details: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> str:
    """Log an audit event to the team's audit log file.

    This function uses append-only mode - it never modifies existing log entries.
    Each event is written as a separate JSON line.

    Args:
        team: Team name
        event_type: Type of audit event
        actor: Agent or system component that triggered the event
        target: Optional target entity (e.g., task ID, agent name)
        details: Optional event-specific details
        context: Optional additional contextual information

    Returns:
        The event ID of the logged event
    """
    import uuid

    event_id = uuid.uuid4().hex

    event = AuditEvent(
        event_id=event_id,
        event_type=event_type,
        timestamp=_now_iso(),
        team=team,
        actor=actor,
        target=target,
        details=details or {},
        context=context or {},
    )

    # Append to audit log file (never modify existing content)
    log_path = _audit_log_path(team)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(event.to_json())
        f.write("\n")

    return event_id


def read_audit_log(team: str, limit: int | None = None) -> list[AuditEvent]:
    """Read audit log entries for a team.

    Args:
        team: Team name
        limit: Optional maximum number of entries to return (most recent first)

    Returns:
        List of audit events, most recent first if limit is specified
    """
    log_path = _audit_log_path(team)
    if not log_path.exists():
        return []

    events = []
    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    event_data = json.loads(line)
                    event = AuditEvent(
                        event_id=event_data["event_id"],
                        event_type=AuditEventType(event_data["event_type"]),
                        timestamp=event_data["timestamp"],
                        team=event_data["team"],
                        actor=event_data["actor"],
                        target=event_data.get("target"),
                        details=event_data.get("details"),
                        context=event_data.get("context"),
                    )
                    events.append(event)
                except (json.JSONDecodeError, KeyError, ValueError):
                    # Skip malformed lines
                    continue

    if limit is not None:
        events = events[-limit:]
        events.reverse()  # Most recent first

    return events


def get_audit_summary(team: str) -> dict[str, Any]:
    """Get a summary of audit activity for a team."""
    events = read_audit_log(team)

    if not events:
        return {
            "total_events": 0,
            "event_types": {},
            "active_agents": [],
            "first_event": None,
            "last_event": None,
        }

    event_types = {}
    active_agents = set()

    for event in events:
        event_types[event.event_type] = event_types.get(event.event_type, 0) + 1
        active_agents.add(event.actor)

    return {
        "total_events": len(events),
        "event_types": event_types,
        "active_agents": list(active_agents),
        "first_event": events[0].timestamp,
        "last_event": events[-1].timestamp,
    }
