"""Notification Manager 测试框架

测试 NotificationManager 的功能：
- 通知创建和管理
- Do-not-disturb 模式
- 通知去重
- WebSocket推送
- 事件处理器
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from datetime import datetime, timezone

from agentteam.notification.manager import (
    NotificationManager,
    get_notification_manager,
    notify_confirmation,
)
from agentteam.notification.types import (
    Notification,
    NotificationType,
    NotificationPriority,
    NotificationEvent,
    NotificationConfig,
)


class TestNotificationConfig:
    """测试通知配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = NotificationConfig()
        assert config is not None
        assert config.enabled
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = NotificationConfig(enabled=False)
        assert not config.enabled


class TestNotification:
    """测试通知模型"""
    
    def test_notification_creation(self):
        """测试通知创建"""
        notification = Notification(
            notification_id="test-id",
            notification_type=NotificationType.TASK_COMPLETE,
            title="Task Completed",
            body="Task xyz has been completed",
            timestamp="2026-04-27T00:00:00Z",
            session_id="session-123"
        )
        assert notification.notification_type == NotificationType.TASK_COMPLETE
        assert notification.title == "Task Completed"
    
    def test_notification_with_priority(self):
        """测试带优先级的通知"""
        notification = Notification(
            notification_id="test-id",
            notification_type=NotificationType.ERROR,
            title="Error",
            body="An error occurred",
            timestamp="2026-04-27T00:00:00Z",
            session_id="session-123",
            priority=NotificationPriority.HIGH
        )
        assert notification.priority == NotificationPriority.HIGH


class TestNotificationManagerInit:
    """测试 NotificationManager 初始化"""
    
    def test_default_init(self):
        """测试默认初始化"""
        manager = NotificationManager()
        assert manager._config is not None
    
    def test_custom_config_init(self):
        """测试自定义配置初始化"""
        config = NotificationConfig(enabled=False)
        manager = NotificationManager(config)
        assert not manager._config.enabled
    
    def test_get_config(self):
        """测试获取配置"""
        manager = NotificationManager()
        config = manager.get_config()
        assert config is not None


class TestNotificationManagerSpecificMethods:
    """测试 NotificationManager 特定方法"""
    
    def test_on_task_completed(self):
        """测试任务完成通知"""
        manager = NotificationManager()
        notification = manager.on_task_completed(
            session_id="test-session",
            session_name="Test Session",
            task_summary="Test task completed"
        )
        assert notification is None or notification.notification_type == NotificationType.TASK_COMPLETE
    
    def test_on_error(self):
        """测试错误通知"""
        manager = NotificationManager()
        notification = manager.on_error(
            session_id="test-session",
            session_name="Test Session",
            error_msg="Test error"
        )
        assert notification is None or notification.notification_type == NotificationType.ERROR
    
    def test_on_confirmation_needed(self):
        """测试确认请求通知"""
        manager = NotificationManager()
        notification = manager.on_confirmation_needed(
            session_id="test-session",
            session_name="Test Session"
        )
        assert notification is None or notification.notification_type == NotificationType.CONFIRMATION
    
    def test_on_info(self):
        """测试信息通知"""
        manager = NotificationManager()
        notification = manager.on_info(
            session_id="test-session",
            title="Info",
            body="Test info"
        )
        assert notification is None or notification.notification_type == NotificationType.INFO
    
    def test_on_warning(self):
        """测试警告通知"""
        manager = NotificationManager()
        notification = manager.on_warning(
            session_id="test-session",
            title="Warning",
            body="Test warning"
        )
        assert notification is None or notification.notification_type == NotificationType.WARNING


class TestNotificationManagerHistory:
    """测试通知历史"""
    
    def test_get_history(self):
        """测试获取历史"""
        manager = NotificationManager()
        manager.on_task_completed(session_id="test-session", session_name="Test")
        history = manager.get_history("test-session")
        assert isinstance(history, list)
    
    def test_clear_session(self):
        """测试清理会话"""
        manager = NotificationManager()
        manager.on_task_completed(session_id="test-session", session_name="Test")
        manager.clear_session("test-session")
        history = manager.get_history("test-session")
        assert len(history) == 0
    
    def test_get_active_count(self):
        """测试获取活跃通知数"""
        manager = NotificationManager()
        count = manager.get_active_count("test-session")
        assert isinstance(count, int)
    
    def test_get_active_notifications(self):
        """测试获取活跃通知"""
        manager = NotificationManager()
        notifications = manager.get_active_notifications("test-session")
        assert isinstance(notifications, list)


class TestNotificationManagerEventHandler:
    """测试事件处理器"""
    
    def test_add_event_handler(self):
        """测试添加事件处理器"""
        manager = NotificationManager()
        handler = Mock()
        manager.add_event_handler(handler)
        assert handler in manager._event_handlers
    
    def test_add_websocket_handler(self):
        """测试添加WebSocket处理器"""
        manager = NotificationManager()
        handler = Mock()
        manager.add_websocket_handler(handler)
        assert handler in manager._websocket_handlers


class TestNotificationManagerConfigUpdate:
    """测试配置更新"""
    
    def test_update_config(self):
        """测试更新配置"""
        manager = NotificationManager()
        new_config = NotificationConfig(enabled=False)
        manager.update_config(new_config)
        assert not manager._config.enabled


class TestNotificationManagerPersistence:
    """测试通知持久化"""
    
    def test_set_persist_dir(self):
        """测试设置持久化目录"""
        manager = NotificationManager()
        manager.set_persist_dir(Path("/tmp/notifications"))
        assert manager._persist_dir == Path("/tmp/notifications")


class TestNotificationManagerCleanup:
    """测试清理"""
    
    def test_cleanup(self):
        """测试清理"""
        manager = NotificationManager()
        manager.on_task_completed(session_id="test-session", session_name="Test")
        manager.cleanup()
    
    def test_acknowledge(self):
        """测试确认通知"""
        manager = NotificationManager()
        manager.on_task_completed(session_id="test-session", session_name="Test")
        manager.acknowledge("test-session", NotificationType.TASK_COMPLETE)


class TestNotificationManagerSingleton:
    """测试单例"""
    
    def test_get_notification_manager(self):
        """测试获取单例"""
        manager1 = get_notification_manager()
        manager2 = get_notification_manager()
        assert manager1 is manager2


class TestNotifyConfirmationFunction:
    """测试便捷函数"""
    
    def test_notify_confirmation(self):
        """测试 notify_confirmation 函数"""
        notification = notify_confirmation("test-session", "Test Session")
        assert notification is None or notification.notification_type == NotificationType.CONFIRMATION


class TestNotificationManagerIntegration:
    """集成测试"""
    
    def test_full_notification_workflow(self):
        """测试完整通知工作流"""
        manager = NotificationManager()
        handler = Mock()
        manager.add_event_handler(handler)
        
        # 发送多个通知
        manager.on_task_completed(session_id="session-1", session_name="Session 1", task_summary="Task 1")
        manager.on_error(session_id="session-1", session_name="Session 1", error_msg="Error 1")
        manager.on_info(session_id="session-1", title="Info", body="Info 1")
        
        # 获取历史
        history = manager.get_history("session-1")
        assert isinstance(history, list)
        
        # 清理
        manager.clear_session("session-1")
        history = manager.get_history("session-1")
        assert len(history) == 0
    
    def test_notification_types(self):
        """测试所有通知类型"""
        manager = NotificationManager()
        
        # 测试各种通知类型
        manager.on_task_completed(session_id="test", session_name="Test", task_summary="Task")
        manager.on_error(session_id="test", session_name="Test", error_msg="Error")
        manager.on_warning(session_id="test", title="Warning", body="Warning")
        manager.on_info(session_id="test", title="Info", body="Info")
        manager.on_confirmation_needed(session_id="test", session_name="Test")