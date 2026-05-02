"""Alerting system for ClawTeam multi-agent teams.

Detects and manages alerts for task timeouts, agent failure rates, and other
critical conditions. Alerts are stored as append-only JSON files per team.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from clawteam.fileutil import atomic_write_text
from clawteam.paths import ensure_within_root, validate_identifier


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _alerts_root(team_name: str) -> Path:
    """Get the alerts directory path for a team."""
    from clawteam.team.models import get_data_dir

    root = ensure_within_root(
        get_data_dir() / "alerts", validate_identifier(team_name, "team name")
    )
    root.mkdir(parents=True, exist_ok=True)
    return root


class AlertType(str, Enum):
    """Types of alert events in ClawTeam."""

    TASK_TIMEOUT = "task_timeout"
    AGENT_FAILURE_RATE_HIGH = "agent_failure_rate_high"
    TEAM_INACTIVITY = "team_inactivity"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    CONFIGURATION_ERROR = "configuration_error"


class AlertSeverity(str, Enum):
    """Severity levels for alerts."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Alert:
    """A single alert entry."""

    alert_id: str
    event_type: AlertType
    severity: AlertSeverity
    message: str
    timestamp: str
    team: str
    source: str  # Agent or system component that triggered the alert
    target: str | None = None  # Optional target entity (e.g., task ID, agent name)
    details: dict[str, Any] | None = None
    acknowledged: bool = False
    acknowledged_by: str | None = None
    acknowledged_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "alert_id": self.alert_id,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "timestamp": self.timestamp,
            "team": self.team,
            "source": self.source,
        }
        if self.target is not None:
            result["target"] = self.target
        if self.details is not None:
            result["details"] = self.details
        result["acknowledged"] = self.acknowledged
        if self.acknowledged_by is not None:
            result["acknowledged_by"] = self.acknowledged_by
        if self.acknowledged_at is not None:
            result["acknowledged_at"] = self.acknowledged_at
        return result

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":"))


def create_alert(
    team: str,
    event_type: AlertType,
    severity: AlertSeverity,
    message: str,
    source: str,
    target: str | None = None,
    details: dict[str, Any] | None = None,
) -> str:
    """Create and store a new alert.

    Args:
        team: Team name
        event_type: Type of alert event
        severity: Severity level
        message: Human-readable alert message
        source: Agent or system component that triggered the alert
        target: Optional target entity (e.g., task ID, agent name)
        details: Optional alert-specific details

    Returns:
        The alert ID of the created alert
    """
    alert_id = uuid.uuid4().hex

    alert = Alert(
        alert_id=alert_id,
        event_type=event_type,
        severity=severity,
        message=message,
        timestamp=_now_iso(),
        team=team,
        source=source,
        target=target,
        details=details or {},
    )

    # Store alert as a separate JSON file (append-only, never modify existing)
    alerts_dir = _alerts_root(team)
    alert_file = (
        alerts_dir / f"alert-{alert.timestamp.split('.')[0].replace(':', '-')}-{alert_id}.json"
    )
    atomic_write_text(alert_file, alert.to_json())

    return alert_id


def list_alerts(
    team: str, acknowledged: bool | None = None, limit: int | None = None
) -> list[Alert]:
    """List alerts for a team.

    Args:
        team: Team name
        acknowledged: Filter by acknowledgment status (None = all)
        limit: Maximum number of alerts to return (None = no limit)

    Returns:
        List of Alert objects, sorted by timestamp (newest first)
    """
    alerts_dir = _alerts_root(team)
    alert_files = list(alerts_dir.glob("alert-*.json"))

    # Sort by timestamp (newest first)
    alert_files.sort(key=lambda f: f.name, reverse=True)

    alerts: list[Alert] = []
    for alert_file in alert_files:
        try:
            data = json.loads(alert_file.read_text(encoding="utf-8"))
            # Convert string values back to enum instances
            event_type = AlertType(data["event_type"])
            severity = AlertSeverity(data["severity"])

            alert = Alert(
                alert_id=data["alert_id"],
                event_type=event_type,
                severity=severity,
                message=data["message"],
                timestamp=data["timestamp"],
                team=data["team"],
                source=data["source"],
                target=data.get("target"),
                details=data.get("details"),
                acknowledged=data["acknowledged"],
                acknowledged_by=data.get("acknowledged_by"),
                acknowledged_at=data.get("acknowledged_at"),
            )

            if acknowledged is None or alert.acknowledged == acknowledged:
                alerts.append(alert)
                if limit is not None and len(alerts) >= limit:
                    break
        except (json.JSONDecodeError, KeyError, ValueError):
            # Skip malformed alert files
            continue

    return alerts


def get_alert(team: str, alert_id: str) -> Alert | None:
    """Get a specific alert by ID.

    Args:
        team: Team name
        alert_id: Alert ID

    Returns:
        Alert object if found, None otherwise
    """
    alerts_dir = _alerts_root(team)
    for alert_file in alerts_dir.glob(f"alert-*-{alert_id}.json"):
        try:
            data = json.loads(alert_file.read_text(encoding="utf-8"))
            event_type = AlertType(data["event_type"])
            severity = AlertSeverity(data["severity"])

            return Alert(
                alert_id=data["alert_id"],
                event_type=event_type,
                severity=severity,
                message=data["message"],
                timestamp=data["timestamp"],
                team=data["team"],
                source=data["source"],
                target=data.get("target"),
                details=data.get("details"),
                acknowledged=data["acknowledged"],
                acknowledged_by=data.get("acknowledged_by"),
                acknowledged_at=data.get("acknowledged_at"),
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            # Skip malformed alert file
            continue

    return None


def acknowledge_alert(team: str, alert_id: str, by: str) -> bool:
    """Acknowledge an alert.

    Args:
        team: Team name
        alert_id: Alert ID to acknowledge
        by: Agent or user acknowledging the alert

    Returns:
        True if alert was found and acknowledged, False otherwise
    """
    alerts_dir = _alerts_root(team)
    for alert_file in alerts_dir.glob(f"alert-*-{alert_id}.json"):
        try:
            alert_data = json.loads(alert_file.read_text(encoding="utf-8"))
            if alert_data.get("acknowledged", False):
                # Already acknowledged
                return True

            # Update acknowledgment fields
            alert_data["acknowledged"] = True
            alert_data["acknowledged_by"] = by
            alert_data["acknowledged_at"] = _now_iso()

            # Write back the updated alert (this is the only case where we modify an existing file)
            atomic_write_text(
                alert_file, json.dumps(alert_data, ensure_ascii=False, separators=(",", ":"))
            )
            return True

        except (json.JSONDecodeError, KeyError, ValueError):
            # Skip malformed files
            continue

    return False


def check_task_timeouts(team: str, timeout_threshold_minutes: int = 60) -> list[str]:
    """Check for tasks that have exceeded the timeout threshold.

    Args:
        team: Team name
        timeout_threshold_minutes: Timeout threshold in minutes

    Returns:
        List of alert IDs created for timed out tasks
    """
    from clawteam.team.models import TaskItem, TaskStatus, TaskStore

    store = TaskStore(team)
    tasks = store.list_all()

    alert_ids = []
    now = datetime.now(timezone.utc)
    timeout_threshold = timeout_threshold_minutes * 60  # Convert to seconds

    for task in tasks:
        if task.status in (TaskStatus.completed, TaskStatus.failed):
            continue

        # Calculate task age
        created_at = datetime.fromisoformat(task.created_at.replace("Z", "+00:00"))
        task_age_seconds = (now - created_at).total_seconds()

        if task_age_seconds > timeout_threshold:
            # Create alert for timed out task
            alert_id = create_alert(
                team=team,
                event_type=AlertType.TASK_TIMEOUT,
                severity=AlertSeverity.HIGH,
                message=f"Task '{task.subject}' has exceeded timeout threshold",
                source="system",
                target=task.id,
                details={
                    "task_subject": task.subject,
                    "task_age_minutes": int(task_age_seconds // 60),
                    "timeout_threshold_minutes": timeout_threshold_minutes,
                    "owner": task.owner,
                },
            )
            alert_ids.append(alert_id)

    return alert_ids


def check_agent_failure_rates(
    team: str, failure_rate_threshold: float = 0.3, min_tasks: int = 5
) -> list[str]:
    """Check for agents with high failure rates.

    Args:
        team: Team name
        failure_rate_threshold: Failure rate threshold (0.0 to 1.0)
        min_tasks: Minimum number of tasks required to calculate failure rate

    Returns:
        List of alert IDs created for high failure rate agents
    """
    from clawteam.team.models import TaskItem, TaskStatus, TaskStore

    store = TaskStore(team)
    tasks = store.list_all()

    # Group tasks by agent
    agent_tasks = {}
    for task in tasks:
        if not task.owner:
            continue
        if task.owner not in agent_tasks:
            agent_tasks[task.owner] = []
        agent_tasks[task.owner].append(task)

    alert_ids = []

    for agent, agent_task_list in agent_tasks.items():
        if len(agent_task_list) < min_tasks:
            continue

        completed_tasks = [t for t in agent_task_list if t.status == TaskStatus.completed]
        failed_tasks = [t for t in agent_task_list if t.status == TaskStatus.failed]
        total_completed_or_failed = len(completed_tasks) + len(failed_tasks)

        if total_completed_or_failed < min_tasks:
            continue

        failure_rate = (
            len(failed_tasks) / total_completed_or_failed if total_completed_or_failed > 0 else 0.0
        )

        if failure_rate >= failure_rate_threshold:
            # Determine severity based on failure rate
            if failure_rate >= 0.7:
                severity = AlertSeverity.CRITICAL
            elif failure_rate >= 0.5:
                severity = AlertSeverity.HIGH
            else:
                severity = AlertSeverity.MEDIUM

            # Create alert for high failure rate agent
            alert_id = create_alert(
                team=team,
                event_type=AlertType.AGENT_FAILURE_RATE_HIGH,
                severity=severity,
                message=f"Agent '{agent}' has high failure rate ({failure_rate:.1%})",
                source="system",
                target=agent,
                details={
                    "agent": agent,
                    "failure_rate": round(failure_rate, 3),
                    "failure_rate_threshold": failure_rate_threshold,
                    "total_tasks": len(agent_task_list),
                    "failed_tasks": len(failed_tasks),
                    "completed_tasks": len(completed_tasks),
                },
            )
            alert_ids.append(alert_id)

    return alert_ids
