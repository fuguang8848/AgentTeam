"""Notifications mixin for the board handler."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentteam.board.handlers.base import BaseHandler


class NotificationsMixin:
    """Mixin for notifications functionality."""

    def handle_get_notifications(self) -> None:
        """Handle GET /api/notifications.

        Returns all notifications.
        """
        try:
            from agentteam.notification.manager import get_notification_manager

            mgr = get_notification_manager()
            notifications = mgr.list_notifications()

            # Convert to list format
            notification_list = []
            icon_map = {
                "task_created": "📋",
                "task_completed": "✅",
                "agent_started": "🚀",
                "agent_failed": "❌",
                "error": "⚠️",
                "info": "ℹ️",
                "warning": "⚡",
            }

            for n in notifications:
                notification_list.append(
                    {
                        "id": str(getattr(n, "id", "")),
                        "type": getattr(n, "notification_type", "info"),
                        "title": getattr(n, "title", ""),
                        "message": getattr(n, "message", ""),
                        "sessionId": getattr(n, "session_id", ""),
                        "timestamp": getattr(n, "timestamp", ""),
                        "unread": not getattr(n, "acknowledged", False),
                        "icon": icon_map.get(getattr(n, "notification_type", "info"), "ℹ️"),
                        "image_url": getattr(n, "image_url", None),
                    }
                )

            self._serve_json({"notifications": notification_list})

        except Exception as e:
            # Fallback: return empty list on any error
            self._serve_json({"notifications": []})

    def handle_mark_notifications_read(self) -> None:
        """Handle POST /api/notifications/mark-read.

        Marks all notifications as read.
        """
        try:
            from agentteam.notification.manager import get_notification_manager

            mgr = get_notification_manager()
            # Acknowledge all session notifications (empty session_id acknowledges all)
            mgr.acknowledge(session_id=None)
            self._serve_json({"success": True})

        except Exception as e:
            self._serve_json({"success": False, "error": str(e)})
