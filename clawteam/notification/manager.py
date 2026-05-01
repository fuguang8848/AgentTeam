"""Notification manager for ClawTeam multi-agent teams.

Manages system notifications, do-not-disturb periods, notification deduplication,
and WebSocket push for real-time notifications.

Inspired by SpectrAI's NotificationManager.ts.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from clawteam.notification.types import (
    Notification,
    NotificationType,
    NotificationPriority,
    NotificationEvent,
    NotificationConfig,
)


logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_current_time() -> str:
    """Get current time in HH:MM format."""
    now = datetime.now(timezone.utc)
    return f"{now.hour:02d}:{now.minute:02d}"


class NotificationManager:
    """Manages notifications for ClawTeam sessions.
    
    Features:
    - Do-not-disturb periods
    - Notification deduplication (active notifications)
    - WebSocket push support
    - Event handlers for notification lifecycle
    """
    
    def __init__(self, config: NotificationConfig | None = None):
        self._config = config or NotificationConfig()
        
        # Active notifications: session_id -> Set[NotificationType]
        # Used to prevent duplicate notifications for the same session/type
        self._active_notifications: dict[str, set[NotificationType]] = defaultdict(set)
        
        # Notification history: session_id -> list[Notification]
        self._notification_history: dict[str, list[Notification]] = defaultdict(list)
        
        # Event handlers
        self._event_handlers: list[Callable[[NotificationEvent], None]] = []
        
        # WebSocket push handlers
        self._websocket_handlers: list[Callable[[str, dict[str, Any]], None]] = []
        
        # Lock for thread safety
        self._lock = threading.Lock()
        
        # Persistence directory (optional)
        self._persist_dir: Path | None = None
    
    def set_persist_dir(self, dir_path: Path | None) -> None:
        """Set directory for notification persistence."""
        self._persist_dir = dir_path
        if dir_path:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def update_config(self, config: NotificationConfig | None = None, **kwargs) -> None:
        """Update notification configuration."""
        if config:
            self._config = config
        else:
            # Update individual fields
            for key, value in kwargs.items():
                if hasattr(self._config, key):
                    setattr(self._config, key, value)
    
    def get_config(self) -> NotificationConfig:
        """Get current configuration."""
        return self._config
    
    def add_event_handler(self, handler: Callable[[NotificationEvent], None]) -> None:
        """Add an event handler for notification events."""
        self._event_handlers.append(handler)
    
    def add_websocket_handler(self, handler: Callable[[str, dict[str, Any]], None]) -> None:
        """Add a WebSocket push handler.
        
        Handler will be called with (session_id, notification_dict) when
        a notification is sent.
        """
        self._websocket_handlers.append(handler)
    
    def _is_do_not_disturb_active(self) -> bool:
        """Check if current time is within do-not-disturb period."""
        if not self._config.do_not_disturb.get("enabled", False):
            return False
        
        current_time = _get_current_time()
        start = self._config.do_not_disturb.get("start", "22:00")
        end = self._config.do_not_disturb.get("end", "08:00")
        
        # Handle overnight period (e.g., 22:00 - 08:00)
        if start > end:
            return current_time >= start or current_time < end
        
        return current_time >= start and current_time < end
    
    def _is_notification_active(self, session_id: str, notification_type: NotificationType) -> bool:
        """Check if a notification type is already active for a session."""
        with self._lock:
            return notification_type in self._active_notifications[session_id]
    
    def _mark_notification_active(self, session_id: str, notification_type: NotificationType) -> None:
        """Mark a notification as active (unacknowledged)."""
        with self._lock:
            self._active_notifications[session_id].add(notification_type)
    
    def _is_type_enabled(self, notification_type: NotificationType) -> bool:
        """Check if a notification type is enabled in config."""
        type_config = self._config.types.get(notification_type.value, {})
        return type_config.get("enabled", True)
    
    def _emit_event(self, event: NotificationEvent) -> None:
        """Emit a notification event to all handlers."""
        for handler in self._event_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Notification event handler error: {e}")
    
    def _push_via_websocket(self, session_id: str, notification: Notification) -> None:
        """Push notification via WebSocket handlers."""
        if not self._config.websocket_push:
            return
        
        notification_dict = notification.to_dict()
        for handler in self._websocket_handlers:
            try:
                handler(session_id, notification_dict)
            except Exception as e:
                logger.error(f"WebSocket push handler error: {e}")
    
    def _persist_notification(self, notification: Notification) -> None:
        """Persist notification to disk."""
        if self._persist_dir is None:
            return
        
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_file = self._persist_dir / f"notifications-{today}.jsonl"
        
        with log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(notification.to_dict(), ensure_ascii=False))
            f.write("\n")
    
    def _send_notification(
        self,
        notification_type: NotificationType,
        title: str,
        body: str,
        session_id: str,
        session_name: str | None = None,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        details: dict[str, Any] | None = None,
    ) -> Notification | None:
        """Internal method to create and send a notification."""
        # Check if notifications are enabled
        if not self._config.enabled:
            return None
        
        # Check do-not-disturb
        if self._is_do_not_disturb_active():
            logger.debug(f"Do-not-disturb active, skipping notification: {title}")
            return None
        
        # Check if type is enabled
        if not self._is_type_enabled(notification_type):
            return None
        
        # Check for duplicate active notification
        if self._is_notification_active(session_id, notification_type):
            logger.debug(f"Notification already active for session {session_id}: {notification_type}")
            return None
        
        # Create notification
        notification = Notification.create(
            notification_type=notification_type,
            title=title,
            body=body,
            session_id=session_id,
            session_name=session_name,
            priority=priority,
            details=details,
        )
        
        # Mark as active
        self._mark_notification_active(session_id, notification_type)
        
        # Store in history
        with self._lock:
            self._notification_history[session_id].append(notification)
        
        # Persist
        self._persist_notification(notification)
        
        # Push via WebSocket
        self._push_via_websocket(session_id, notification)
        
        # Emit event
        self._emit_event(NotificationEvent(
            event_type="notification-sent",
            notification_type=notification_type,
            session_id=session_id,
            session_name=session_name,
            notification_id=notification.notification_id,
        ))
        
        logger.info(f"Notification sent: {title} - {body}")
        return notification
    
    # =========================================================================
    # Public notification methods
    # =========================================================================
    
    def on_confirmation_needed(
        self,
        session_id: str,
        session_name: str | None = None,
        prompt_text: str | None = None,
    ) -> Notification | None:
        """Send notification when a session needs confirmation."""
        body = f"会话 \"{session_name or session_id}\" 正在等待您的确认"
        if prompt_text:
            body += f": {prompt_text[:50]}"
        
        return self._send_notification(
            notification_type=NotificationType.CONFIRMATION,
            title="ClawTeam 需要确认",
            body=body,
            session_id=session_id,
            session_name=session_name,
            priority=NotificationPriority.HIGH,
            details={"prompt_text": prompt_text} if prompt_text else None,
        )
    
    def on_task_completed(
        self,
        session_id: str,
        session_name: str | None = None,
        task_summary: str | None = None,
    ) -> Notification | None:
        """Send notification when a task is completed."""
        body = f"会话 \"{session_name or session_id}\" 已完成任务"
        if task_summary:
            body += f": {task_summary[:50]}"
        
        return self._send_notification(
            notification_type=NotificationType.TASK_COMPLETE,
            title="任务已完成",
            body=body,
            session_id=session_id,
            session_name=session_name,
            priority=NotificationPriority.MEDIUM,
            details={"task_summary": task_summary} if task_summary else None,
        )
    
    def on_error(
        self,
        session_id: str,
        session_name: str | None = None,
        error_msg: str | None = None,
    ) -> Notification | None:
        """Send notification when an error occurs."""
        body = f"会话 \"{session_name or session_id}\""
        if error_msg:
            body += f": {error_msg[:100]}"
        else:
            body += " 遇到错误"
        
        return self._send_notification(
            notification_type=NotificationType.ERROR,
            title="ClawTeam 遇到错误",
            body=body,
            session_id=session_id,
            session_name=session_name,
            priority=NotificationPriority.HIGH,
            details={"error_msg": error_msg} if error_msg else None,
        )
    
    def on_session_stuck(
        self,
        session_id: str,
        session_name: str | None = None,
        stuck_duration: int | None = None,
    ) -> Notification | None:
        """Send notification when a session appears stuck."""
        body = f"会话 \"{session_name or session_id}\" 长时间无响应，可能需要干预"
        if stuck_duration:
            body += f" (已等待 {stuck_duration} 秒)"
        
        return self._send_notification(
            notification_type=NotificationType.STUCK,
            title="ClawTeam 可能卡住",
            body=body,
            session_id=session_id,
            session_name=session_name,
            priority=NotificationPriority.CRITICAL,
            details={"stuck_duration": stuck_duration} if stuck_duration else None,
        )
    
    def on_info(
        self,
        session_id: str,
        title: str,
        body: str,
        session_name: str | None = None,
    ) -> Notification | None:
        """Send an informational notification."""
        return self._send_notification(
            notification_type=NotificationType.INFO,
            title=title,
            body=body,
            session_id=session_id,
            session_name=session_name,
            priority=NotificationPriority.LOW,
        )
    
    def on_warning(
        self,
        session_id: str,
        title: str,
        body: str,
        session_name: str | None = None,
    ) -> Notification | None:
        """Send a warning notification."""
        return self._send_notification(
            notification_type=NotificationType.WARNING,
            title=title,
            body=body,
            session_id=session_id,
            session_name=session_name,
            priority=NotificationPriority.MEDIUM,
        )
    
    # =========================================================================
    # Acknowledgment and management
    # =========================================================================
    
    def acknowledge(
        self,
        session_id: str,
        notification_type: NotificationType | None = None,
    ) -> bool:
        """Acknowledge (clear) a notification.
        
        Args:
            session_id: The session ID
            notification_type: Optional specific type to acknowledge.
                              If None, acknowledges all for the session.
        
        Returns:
            True if a notification was acknowledged, False otherwise.
        """
        with self._lock:
            active = self._active_notifications.get(session_id)
            if not active:
                return False
            
            if notification_type:
                had = notification_type in active
                if had:
                    active.discard(notification_type)
                    # Update history
                    for n in self._notification_history[session_id]:
                        if n.notification_type == notification_type and not n.acknowledged:
                            n.acknowledged = True
                            n.acknowledged_at = _now_iso()
                            break
                if not active:
                    del self._active_notifications[session_id]
                return had
            
            # Acknowledge all for session
            had = len(active) > 0
            del self._active_notifications[session_id]
            for n in self._notification_history[session_id]:
                if not n.acknowledged:
                    n.acknowledged = True
                    n.acknowledged_at = _now_iso()
            return had
    
    def get_active_count(self, session_id: str | None = None) -> int:
        """Get count of active (unacknowledged) notifications."""
        with self._lock:
            if session_id:
                return len(self._active_notifications.get(session_id, set()))
            
            total = 0
            for types_set in self._active_notifications.values():
                total += len(types_set)
            return total
    
    def get_active_notifications(self, session_id: str | None = None) -> list[Notification]:
        """Get list of active notifications."""
        with self._lock:
            if session_id:
                active_types = self._active_notifications.get(session_id, set())
                return [
                    n for n in self._notification_history.get(session_id, [])
                    if n.notification_type in active_types and not n.acknowledged
                ]
            
            # All sessions
            result = []
            for sid, active_types in self._active_notifications.items():
                for n in self._notification_history.get(sid, []):
                    if n.notification_type in active_types and not n.acknowledged:
                        result.append(n)
            return result
    
    def get_history(self, session_id: str | None = None, limit: int = 100) -> list[Notification]:
        """Get notification history."""
        with self._lock:
            if session_id:
                return list(self._notification_history.get(session_id, []))[-limit:]
            
            # All sessions
            all_notifications = []
            for notifications in self._notification_history.values():
                all_notifications.extend(notifications)
            return sorted(all_notifications, key=lambda n: n.timestamp)[-limit:]
    
    def clear_session(self, session_id: str) -> None:
        """Clear all notifications for a session."""
        with self._lock:
            self._active_notifications.pop(session_id, None)
            self._notification_history.pop(session_id, None)
    
    def cleanup(self) -> None:
        """Clean up all resources."""
        with self._lock:
            self._active_notifications.clear()
            self._notification_history.clear()
        self._event_handlers.clear()
        self._websocket_handlers.clear()


# Singleton instance
_manager_instance: NotificationManager | None = None
_manager_lock = threading.Lock()


def get_notification_manager() -> NotificationManager:
    """Get the global notification manager instance."""
    global _manager_instance
    with _manager_lock:
        if _manager_instance is None:
            _manager_instance = NotificationManager()
        return _manager_instance


def notify_confirmation(session_id: str, session_name: str | None = None) -> Notification | None:
    """Send confirmation notification using global manager."""
    return get_notification_manager().on_confirmation_needed(session_id, session_name)


def notify_task_complete(session_id: str, session_name: str | None = None) -> Notification | None:
    """Send task complete notification using global manager."""
    return get_notification_manager().on_task_completed(session_id, session_name)


def notify_error(session_id: str, error_msg: str, session_name: str | None = None) -> Notification | None:
    """Send error notification using global manager."""
    return get_notification_manager().on_error(session_id, session_name, error_msg)


def notify_stuck(session_id: str, session_name: str | None = None) -> Notification | None:
    """Send stuck notification using global manager."""
    return get_notification_manager().on_session_stuck(session_id, session_name)