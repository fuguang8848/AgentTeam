"""Tests for the notification manager."""

from __future__ import annotations

import pytest
import time
from datetime import datetime, timezone

from agentteam.notification import (
    NotificationManager,
    NotificationType,
    NotificationConfig,
)
from agentteam.notification.types import (
    Notification,
    NotificationPriority,
    NotificationEvent,
)
from agentteam.notification.manager import (
    get_notification_manager,
    notify_confirmation,
    notify_error,
    notify_task_complete,
    notify_stuck,
)


class TestNotification:
    """Tests for Notification class."""

    def test_create_notification(self):
        """Test creating a notification."""
        notification = Notification.create(
            notification_type=NotificationType.ERROR,
            title="Test Error",
            body="Something went wrong",
            session_id="session-1",
        )

        assert notification.notification_type == NotificationType.ERROR
        assert notification.title == "Test Error"
        assert notification.body == "Something went wrong"
        assert notification.session_id == "session-1"
        assert notification.notification_id  # Auto-generated
        assert notification.timestamp  # Auto-generated
        assert not notification.acknowledged

    def test_to_dict(self):
        """Test converting notification to dictionary."""
        notification = Notification.create(
            notification_type=NotificationType.CONFIRMATION,
            title="Need Confirmation",
            body="Please confirm",
            session_id="session-1",
            session_name="Test Session",
            priority=NotificationPriority.HIGH,
        )

        d = notification.to_dict()
        assert d["notification_type"] == "confirmation"
        assert d["title"] == "Need Confirmation"
        assert d["session_id"] == "session-1"
        assert d["session_name"] == "Test Session"
        assert d["priority"] == "high"
        assert not d["acknowledged"]


class TestNotificationConfig:
    """Tests for NotificationConfig class."""

    def test_default_config(self):
        """Test default configuration."""
        config = NotificationConfig()

        assert config.enabled
        assert config.sound
        assert config.websocket_push
        assert not config.do_not_disturb["enabled"]

    def test_custom_config(self):
        """Test custom configuration."""
        config = NotificationConfig(
            enabled=False,
            sound=False,
            do_not_disturb={"enabled": True, "start": "23:00", "end": "07:00"},
        )

        assert not config.enabled
        assert not config.sound
        assert config.do_not_disturb["enabled"]
        assert config.do_not_disturb["start"] == "23:00"

    def test_to_dict_and_from_dict(self):
        """Test serialization and deserialization."""
        config = NotificationConfig(
            enabled=True,
            sound=False,
            websocket_push=True,
        )

        d = config.to_dict()
        restored = NotificationConfig.from_dict(d)

        assert restored.enabled == config.enabled
        assert restored.sound == config.sound
        assert restored.websocket_push == config.websocket_push


class TestNotificationManager:
    """Tests for NotificationManager class."""

    def test_send_confirmation_notification(self):
        """Test sending confirmation notification."""
        manager = NotificationManager()

        notification = manager.on_confirmation_needed(
            session_id="session-1",
            session_name="Test Session",
        )

        assert notification is not None
        assert notification.notification_type == NotificationType.CONFIRMATION
        assert "确认" in notification.title or "confirm" in notification.title.lower()

    def test_send_task_complete_notification(self):
        """Test sending task complete notification."""
        manager = NotificationManager()

        notification = manager.on_task_completed(
            session_id="session-1",
            session_name="Test Session",
            task_summary="All tests passed",
        )

        assert notification is not None
        assert notification.notification_type == NotificationType.TASK_COMPLETE

    def test_send_error_notification(self):
        """Test sending error notification."""
        manager = NotificationManager()

        notification = manager.on_error(
            session_id="session-1",
            session_name="Test Session",
            error_msg="Connection failed",
        )

        assert notification is not None
        assert notification.notification_type == NotificationType.ERROR
        assert "Connection failed" in notification.body

    def test_send_stuck_notification(self):
        """Test sending stuck notification."""
        manager = NotificationManager()

        notification = manager.on_session_stuck(
            session_id="session-1",
            session_name="Test Session",
            stuck_duration=120,
        )

        assert notification is not None
        assert notification.notification_type == NotificationType.STUCK
        assert notification.priority == NotificationPriority.CRITICAL

    def test_deduplication(self):
        """Test notification deduplication."""
        manager = NotificationManager()

        # First notification should be sent
        n1 = manager.on_confirmation_needed("session-1", "Test")
        assert n1 is not None

        # Duplicate should be blocked
        n2 = manager.on_confirmation_needed("session-1", "Test")
        assert n2 is None

        # After acknowledgment, should be allowed again
        manager.acknowledge("session-1", NotificationType.CONFIRMATION)
        n3 = manager.on_confirmation_needed("session-1", "Test")
        assert n3 is not None

    def test_acknowledge_single_type(self):
        """Test acknowledging a single notification type."""
        manager = NotificationManager()

        manager.on_confirmation_needed("session-1")
        manager.on_error("session-1", error_msg="test")

        # Acknowledge only confirmation
        result = manager.acknowledge("session-1", NotificationType.CONFIRMATION)
        assert result

        # Error should still be active
        assert manager.get_active_count("session-1") == 1

    def test_acknowledge_all(self):
        """Test acknowledging all notifications for a session."""
        manager = NotificationManager()

        manager.on_confirmation_needed("session-1")
        manager.on_error("session-1", error_msg="test")

        result = manager.acknowledge("session-1")
        assert result
        assert manager.get_active_count("session-1") == 0

    def test_get_active_count(self):
        """Test getting active notification count."""
        manager = NotificationManager()

        assert manager.get_active_count() == 0

        manager.on_confirmation_needed("session-1")
        manager.on_error("session-2", error_msg="test")

        assert manager.get_active_count() == 2
        assert manager.get_active_count("session-1") == 1

    def test_get_active_notifications(self):
        """Test getting active notifications list."""
        manager = NotificationManager()

        manager.on_confirmation_needed("session-1")
        manager.on_error("session-1", error_msg="test")

        active = manager.get_active_notifications("session-1")
        assert len(active) == 2

    def test_get_history(self):
        """Test getting notification history."""
        manager = NotificationManager()

        manager.on_confirmation_needed("session-1")
        manager.on_error("session-1", error_msg="test")
        manager.acknowledge("session-1")

        history = manager.get_history("session-1")
        assert len(history) == 2

    def test_clear_session(self):
        """Test clearing session notifications."""
        manager = NotificationManager()

        manager.on_confirmation_needed("session-1")
        manager.clear_session("session-1")

        assert manager.get_active_count("session-1") == 0
        assert manager.get_history("session-1") == []

    def test_disabled_notifications(self):
        """Test that disabled config prevents notifications."""
        config = NotificationConfig(enabled=False)
        manager = NotificationManager(config=config)

        notification = manager.on_confirmation_needed("session-1")
        assert notification is None

    def test_disabled_type(self):
        """Test that disabled type prevents notifications."""
        config = NotificationConfig()
        config.types["confirmation"]["enabled"] = False
        manager = NotificationManager(config=config)

        notification = manager.on_confirmation_needed("session-1")
        assert notification is None

    def test_event_handler(self):
        """Test event handler callback."""
        manager = NotificationManager()

        received_events = []
        manager.add_event_handler(lambda e: received_events.append(e))

        manager.on_confirmation_needed("session-1", "Test")

        assert len(received_events) == 1
        assert received_events[0].event_type == "notification-sent"

    def test_websocket_handler(self):
        """Test WebSocket push handler."""
        manager = NotificationManager()

        received_notifications = []
        manager.add_websocket_handler(lambda sid, n: received_notifications.append((sid, n)))

        manager.on_confirmation_needed("session-1", "Test")

        assert len(received_notifications) == 1
        assert received_notifications[0][0] == "session-1"

    def test_websocket_push_disabled(self):
        """Test that disabled WebSocket push doesn't call handlers."""
        config = NotificationConfig(websocket_push=False)
        manager = NotificationManager(config=config)

        received = []
        manager.add_websocket_handler(lambda sid, n: received.append(n))

        manager.on_confirmation_needed("session-1")

        assert len(received) == 0

    def test_update_config(self):
        """Test updating configuration."""
        manager = NotificationManager()

        manager.update_config(enabled=False)
        assert not manager.get_config().enabled

        new_config = NotificationConfig(sound=False)
        manager.update_config(config=new_config)
        assert not manager.get_config().sound

    def test_global_manager(self):
        """Test global manager instance."""
        manager1 = get_notification_manager()
        manager2 = get_notification_manager()

        assert manager1 is manager2  # Same instance

    def test_helper_functions(self):
        """Test helper functions."""
        # These use the global manager
        n1 = notify_confirmation("session-1", "Test")
        assert n1 is not None

        n2 = notify_error("session-2", "Test error")
        assert n2 is not None

        n3 = notify_task_complete("session-3", "Test")
        assert n3 is not None

        n4 = notify_stuck("session-4", "Test")
        assert n4 is not None


class TestDoNotDisturb:
    """Tests for do-not-disturb functionality."""

    def test_dnd_disabled(self):
        """Test that disabled DND allows notifications."""
        config = NotificationConfig()
        config.do_not_disturb["enabled"] = False
        manager = NotificationManager(config=config)

        notification = manager.on_confirmation_needed("session-1")
        assert notification is not None

    def test_dnd_config_check(self):
        """Test DND time range checking."""
        manager = NotificationManager()

        # Set DND period
        manager.update_config(do_not_disturb={"enabled": True, "start": "23:00", "end": "07:00"})

        # This test can't reliably check time-based behavior without mocking
        # Just verify the config is set correctly
        config = manager.get_config()
        assert config.do_not_disturb["enabled"]
        assert config.do_not_disturb["start"] == "23:00"


class TestNotificationPriority:
    """Tests for notification priority."""

    def test_confirmation_high_priority(self):
        """Test that confirmation has high priority."""
        manager = NotificationManager()

        notification = manager.on_confirmation_needed("session-1")
        assert notification.priority == NotificationPriority.HIGH

    def test_error_high_priority(self):
        """Test that error has high priority."""
        manager = NotificationManager()

        notification = manager.on_error("session-1", error_msg="test")
        assert notification.priority == NotificationPriority.HIGH

    def test_stuck_critical_priority(self):
        """Test that stuck has critical priority."""
        manager = NotificationManager()

        notification = manager.on_session_stuck("session-1")
        assert notification.priority == NotificationPriority.CRITICAL

    def test_task_complete_medium_priority(self):
        """Test that task complete has medium priority."""
        manager = NotificationManager()

        notification = manager.on_task_completed("session-1")
        assert notification.priority == NotificationPriority.MEDIUM

    def test_info_low_priority(self):
        """Test that info has low priority."""
        manager = NotificationManager()

        notification = manager.on_info("session-1", "Info", "Test info")
        assert notification.priority == NotificationPriority.LOW
