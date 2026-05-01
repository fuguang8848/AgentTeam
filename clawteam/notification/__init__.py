"""Notification management for ClawTeam multi-agent teams.

Manages system notifications, do-not-disturb periods, and notification deduplication.
Supports WebSocket push for real-time notifications.

Inspired by SpectrAI's NotificationManager.ts.
"""

from clawteam.notification.manager import (
    NotificationManager,
    get_notification_manager,
    notify_confirmation,
    notify_error,
    notify_task_complete,
    notify_stuck,
)
from clawteam.notification.types import (
    Notification,
    NotificationType,
    NotificationPriority,
    NotificationEvent,
    NotificationConfig,
)

__all__ = [
    # Manager
    "NotificationManager",
    "get_notification_manager",
    "notify_confirmation",
    "notify_error",
    "notify_task_complete",
    "notify_stuck",
    # Types
    "Notification",
    "NotificationType",
    "NotificationPriority",
    "NotificationEvent",
    "NotificationConfig",
]