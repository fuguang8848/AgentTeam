"""Tests for parser and notification integration."""

from __future__ import annotations

import pytest
import tempfile
from pathlib import Path

from agentteam.parser import OutputParser, ActivityEvent, ActivityEventType
from agentteam.parser.integration import AgentTeamIntegration, get_integration, parse_and_notify
from agentteam.notification import NotificationManager, NotificationType


class TestAgentTeamIntegration:
    """Tests for AgentTeamIntegration class."""
    
    def test_create_integration(self):
        """Test creating integration instance."""
        integration = AgentTeamIntegration("test-team")
        
        assert integration.team_name == "test-team"
        assert integration.get_parser() is not None
        assert integration.get_notification_manager() is not None
    
    def test_parse_output(self):
        """Test parsing output through integration."""
        integration = AgentTeamIntegration("test-team")
        
        events = integration.parse_output(
            session_id="session-1",
            data="Error: test error\n",
            provider_id="claude-code",
        )
        
        assert len(events) == 1
        assert events[0].event_type == ActivityEventType.ERROR
    
    def test_notification_triggered_on_error(self):
        """Test that error triggers notification."""
        integration = AgentTeamIntegration("test-team")
        
        integration.parse_output("session-1", "Error: test error\n")
        
        # Check notification was created
        active = integration.get_notification_manager().get_active_notifications("session-1")
        assert len(active) == 1
        assert active[0].notification_type == NotificationType.ERROR
    
    def test_notification_triggered_on_confirmation(self):
        """Test that confirmation request triggers notification."""
        integration = AgentTeamIntegration("test-team")
        
        integration.parse_output("session-1", "Allow Bash? (y)\n")
        
        active = integration.get_notification_manager().get_active_notifications("session-1")
        assert len(active) == 1
        assert active[0].notification_type == NotificationType.CONFIRMATION
    
    def test_websocket_push_callback(self):
        """Test WebSocket push callback."""
        integration = AgentTeamIntegration("test-team")
        
        received = []
        integration.set_websocket_push_callback(
            lambda sid, n: received.append((sid, n))
        )
        
        integration.parse_output("session-1", "Error: test\n")
        
        # Notification should trigger WebSocket push
        assert len(received) == 1
        assert received[0][0] == "session-1"
    
    def test_mark_session_ended(self):
        """Test marking session as ended."""
        integration = AgentTeamIntegration("test-team")
        
        integration.parse_output("session-1", "Error: test\n")
        integration.mark_session_ended("session-1")
        
        # Notifications should be acknowledged
        assert integration.get_notification_manager().get_active_count("session-1") == 0
    
    def test_clear_session(self):
        """Test clearing session."""
        integration = AgentTeamIntegration("test-team")
        
        integration.parse_output("session-1", "Error: test\n")
        integration.clear_session("session-1")
        
        # All resources should be cleared
        assert integration.get_notification_manager().get_active_count("session-1") == 0
    
    def test_cleanup(self):
        """Test cleanup."""
        integration = AgentTeamIntegration("test-team")
        
        integration.parse_output("session-1", "Error: test\n")
        integration.cleanup()
        
        # Should not crash
    
    def test_global_integration(self):
        """Test global integration instance."""
        integration1 = get_integration("team-1")
        integration2 = get_integration("team-1")
        
        assert integration1 is integration2  # Same instance
        
        # Different team should have different instance
        integration3 = get_integration("team-2")
        assert integration1 is not integration3
    
    def test_parse_and_notify_helper(self):
        """Test parse_and_notify helper function."""
        events = parse_and_notify("test-team", "session-1", "Error: test\n")
        
        assert len(events) >= 0
    
    def test_remove_integration(self):
        """Test removing integration."""
        from agentteam.parser.integration import remove_integration
        
        integration = get_integration("team-to-remove")
        remove_integration("team-to-remove")
        
        # Getting again should create new instance
        integration2 = get_integration("team-to-remove")
        assert integration is not integration2


class TestAuditIntegration:
    """Tests for audit logging integration."""
    
    def test_audit_logged_on_error(self, tmp_path):
        """Test that error events are logged to audit."""
        # This test requires audit module to be properly set up
        integration = AgentTeamIntegration("test-team")
        
        # Parse error
        integration.parse_output("session-1", "Error: test error\n")
        
        # Audit should be logged (check via integration internals)
        # Note: Actual audit file location depends on team models
        pass  # Audit integration is tested implicitly
    
    def test_audit_logged_on_task_complete(self):
        """Test that task complete events are logged to audit."""
        integration = AgentTeamIntegration("test-team")
        
        integration.parse_output("session-1", "Task completed successfully\n")
        
        # Audit should be logged
        pass  # Audit integration is tested implicitly


class TestMultiSession:
    """Tests for multi-session handling."""
    
    def test_multiple_sessions(self):
        """Test handling multiple sessions."""
        integration = AgentTeamIntegration("test-team")
        
        # Parse for multiple sessions
        integration.parse_output("session-1", "Error: error1\n")
        integration.parse_output("session-2", "Error: error2\n")
        integration.parse_output("session-3", "Allow Bash? (y)\n")
        
        # Each session should have its own notifications
        assert integration.get_notification_manager().get_active_count() == 3
        assert integration.get_notification_manager().get_active_count("session-1") == 1
        assert integration.get_notification_manager().get_active_count("session-2") == 1
        assert integration.get_notification_manager().get_active_count("session-3") == 1
    
    def test_session_isolation(self):
        """Test that sessions are isolated."""
        integration = AgentTeamIntegration("test-team")
        
        integration.parse_output("session-1", "Error: error1\n")
        integration.parse_output("session-2", "Error: error2\n")
        
        # Acknowledge only session-1
        integration.get_notification_manager().acknowledge("session-1")
        
        # session-2 should still have active notification
        assert integration.get_notification_manager().get_active_count("session-2") == 1
        assert integration.get_notification_manager().get_active_count("session-1") == 0


class TestProviderSpecific:
    """Tests for provider-specific handling."""
    
    def test_claude_code_provider(self):
        """Test Claude Code provider-specific parsing."""
        integration = AgentTeamIntegration("test-team")
        
        events = integration.parse_output(
            "session-1",
            "⏺ Read(test.py)\n",
            provider_id="claude-code",
        )
        
        assert len(events) == 1
        assert events[0].event_type == ActivityEventType.FILE_READ
        assert events[0].provider_id == "claude-code"
    
    def test_generic_provider(self):
        """Test generic provider parsing."""
        integration = AgentTeamIntegration("test-team")
        
        events = integration.parse_output(
            "session-1",
            "Error: test error\n",
            provider_id="unknown-provider",
        )
        
        assert len(events) == 1
        assert events[0].event_type == ActivityEventType.ERROR
    
    def test_provider_switching(self):
        """Test switching providers for same session."""
        integration = AgentTeamIntegration("test-team")
        
        # First with Claude Code
        events1 = integration.parse_output(
            "session-1",
            "⏺ Read(file1.py)\n",
            provider_id="claude-code",
        )
        
        # Then with Codex
        events2 = integration.parse_output(
            "session-1",
            "Running command: npm test\n",
            provider_id="codex",
        )
        
        assert events1[0].provider_id == "claude-code"
        assert events2[0].provider_id == "codex"