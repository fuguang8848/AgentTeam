"""Type definitions for the notification system."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class NotificationType(str, Enum):
    """Types of notifications."""
    
    CONFIRMATION = "confirmation"
    TASK_COMPLETE = "taskComplete"
    ERROR = "error"
    STUCK = "stuck"
    INFO = "info"
    WARNING = "warning"


class NotificationPriority(str, Enum):
    """Priority levels for notifications."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Notification:
    """A single notification entry."""
    
    notification_id: str
    notification_type: NotificationType
    title: str
    body: str
    timestamp: str
    session_id: str
    session_name: str | None = None
    priority: NotificationPriority = NotificationPriority.MEDIUM
    acknowledged: bool = False
    acknowledged_at: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.notification_id:
            self.notification_id = uuid.uuid4().hex
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "notification_id": self.notification_id,
            "notification_type": self.notification_type.value,
            "title": self.title,
            "body": self.body,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "priority": self.priority.value,
            "acknowledged": self.acknowledged,
        }
        if self.session_name:
            result["session_name"] = self.session_name
        if self.acknowledged_at:
            result["acknowledged_at"] = self.acknowledged_at
        if self.details:
            result["details"] = self.details
        return result
    
    @classmethod
    def create(
        cls,
        notification_type: NotificationType,
        title: str,
        body: str,
        session_id: str,
        session_name: str | None = None,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        details: dict[str, Any] | None = None,
    ) -> Notification:
        """Create a new notification with auto-generated ID and timestamp."""
        return cls(
            notification_id=uuid.uuid4().hex,
            notification_type=notification_type,
            title=title,
            body=body,
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=session_id,
            session_name=session_name,
            priority=priority,
            details=details or {},
        )


@dataclass
class NotificationEvent:
    """Event emitted when a notification is sent or acknowledged."""
    
    event_type: str  # "notification-sent", "notification-acknowledged"
    notification_type: NotificationType
    session_id: str
    session_name: str | None = None
    notification_id: str | None = None
    error_msg: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "event_type": self.event_type,
            "notification_type": self.notification_type.value,
            "session_id": self.session_id,
        }
        if self.session_name:
            result["session_name"] = self.session_name
        if self.notification_id:
            result["notification_id"] = self.notification_id
        if self.error_msg:
            result["error_msg"] = self.error_msg
        return result


@dataclass
class NotificationConfig:
    """Configuration for the notification manager."""
    
    enabled: bool = True
    sound: bool = True
    websocket_push: bool = True
    
    # Do-not-disturb period
    do_not_disturb: dict[str, Any] = field(default_factory=lambda: {
        "enabled": False,
        "start": "22:00",
        "end": "08:00",
    })
    
    # Per-type configuration
    types: dict[str, Any] = field(default_factory=lambda: {
        "confirmation": {"enabled": True},
        "taskComplete": {"enabled": True},
        "error": {"enabled": True},
        "stuck": {"enabled": True},
        "info": {"enabled": True},
        "warning": {"enabled": True},
    })
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "enabled": self.enabled,
            "sound": self.sound,
            "websocket_push": self.websocket_push,
            "do_not_disturb": self.do_not_disturb,
            "types": self.types,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NotificationConfig:
        """Create from dictionary."""
        return cls(
            enabled=data.get("enabled", True),
            sound=data.get("sound", True),
            websocket_push=data.get("websocket_push", True),
            do_not_disturb=data.get("do_not_disturb", {
                "enabled": False,
                "start": "22:00",
                "end": "08:00",
            }),
            types=data.get("types", {
                "confirmation": {"enabled": True},
                "taskComplete": {"enabled": True},
                "error": {"enabled": True},
                "stuck": {"enabled": True},
                "info": {"enabled": True},
                "warning": {"enabled": True},
            }),
        )