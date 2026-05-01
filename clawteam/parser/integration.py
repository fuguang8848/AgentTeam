"""Integration module for output parser and notification manager with ClawTeam.

Provides integration with:
- TeamBus (mailbox system)
- Audit logging
- WebSocket push
- Board server
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any, Callable, Optional

from clawteam.parser import OutputParser, ActivityEvent, ActivityEventType
from clawteam.parser.output_parser import get_parser
from clawteam.notification import NotificationManager, NotificationType
from clawteam.notification.manager import get_notification_manager
from clawteam.audit import AuditEventType, log_audit_event


logger = logging.getLogger(__name__)


class ClawTeamIntegration:
    """Integration hub for parser and notification with ClawTeam systems."""
    
    def __init__(
        self,
        team_name: str,
        parser: OutputParser | None = None,
        notification_manager: NotificationManager | None = None,
    ):
        self.team_name = team_name
        self._parser = parser or OutputParser()
        self._notification_manager = notification_manager or NotificationManager()
        
        # Set up event handlers
        self._setup_handlers()
        
        # WebSocket push callback
        self._websocket_push_callback: Callable[[str, dict[str, Any]], None] | None = None
    
    def _setup_handlers(self) -> None:
        """Set up event handlers for parser and notification manager."""
        # Parser event handler
        self._parser.add_event_handler(self._on_parser_event)
        
        # Notification event handler
        self._notification_manager.add_event_handler(self._on_notification_event)
        
        # WebSocket push handler
        self._notification_manager.add_websocket_handler(self._on_websocket_push)
    
    def _on_parser_event(self, event: ActivityEvent) -> None:
        """Handle activity events from the parser."""
        # Log to audit
        try:
            audit_event_type = self._map_to_audit_event_type(event.event_type)
            if audit_event_type:
                log_audit_event(
                    team=self.team_name,
                    event_type=audit_event_type,
                    actor=event.session_id,
                    target=event.provider_id,
                    details={
                        "detail": event.detail,
                        "confidence": event.confidence,
                        "raw_line": event.raw_line,
                    },
                )
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
        
        # Trigger notifications for important events
        self._trigger_notification_from_event(event)
    
    def _map_to_audit_event_type(self, event_type: ActivityEventType) -> AuditEventType | None:
        """Map parser event type to audit event type."""
        mapping = {
            ActivityEventType.FILE_READ: AuditEventType.MESSAGE_SENT,
            ActivityEventType.FILE_WRITE: AuditEventType.MESSAGE_SENT,
            ActivityEventType.FILE_CREATED: AuditEventType.MESSAGE_SENT,
            ActivityEventType.FILE_MODIFIED: AuditEventType.MESSAGE_SENT,
            ActivityEventType.FILE_DELETED: AuditEventType.MESSAGE_SENT,
            ActivityEventType.COMMAND_EXECUTED: AuditEventType.MESSAGE_SENT,
            ActivityEventType.ERROR: AuditEventType.ALERT_TRIGGERED,
            ActivityEventType.TASK_COMPLETE: AuditEventType.TASK_COMPLETED,
            ActivityEventType.WAITING_CONFIRMATION: AuditEventType.TASK_BLOCKED,
        }
        return mapping.get(event_type)
    
    def _trigger_notification_from_event(self, event: ActivityEvent) -> None:
        """Trigger notification based on parser event."""
        if event.event_type == ActivityEventType.WAITING_CONFIRMATION:
            self._notification_manager.on_confirmation_needed(
                session_id=event.session_id,
                session_name=event.session_id,
                prompt_text=event.detail,
            )
        elif event.event_type == ActivityEventType.ERROR:
            self._notification_manager.on_error(
                session_id=event.session_id,
                session_name=event.session_id,
                error_msg=event.detail,
            )
        elif event.event_type == ActivityEventType.TASK_COMPLETE:
            self._notification_manager.on_task_completed(
                session_id=event.session_id,
                session_name=event.session_id,
                task_summary=event.detail,
            )
    
    def _on_notification_event(self, event) -> None:
        """Handle notification events."""
        logger.info(f"Notification event: {event.event_type} for session {event.session_id}")
    
    def _on_websocket_push(self, session_id: str, notification_dict: dict[str, Any]) -> None:
        """Handle WebSocket push from notification manager."""
        if self._websocket_push_callback:
            try:
                self._websocket_push_callback(session_id, notification_dict)
            except Exception as e:
                logger.error(f"WebSocket push callback error: {e}")
    
    def set_websocket_push_callback(self, callback: Callable[[str, dict[str, Any]], None]) -> None:
        """Set callback for WebSocket push."""
        self._websocket_push_callback = callback
    
    def parse_output(self, session_id: str, data: str, provider_id: str | None = None) -> list[ActivityEvent]:
        """Parse output data and trigger notifications."""
        if provider_id:
            self._parser.set_provider(session_id, provider_id)
        return self._parser.parse(session_id, data)
    
    def get_parser(self) -> OutputParser:
        """Get the parser instance."""
        return self._parser
    
    def get_notification_manager(self) -> NotificationManager:
        """Get the notification manager instance."""
        return self._notification_manager
    
    def mark_session_ended(self, session_id: str) -> None:
        """Mark a session as ended."""
        self._parser.mark_session_ended(session_id)
        self._notification_manager.acknowledge(session_id)
    
    def clear_session(self, session_id: str) -> None:
        """Clear all session resources."""
        self._parser.clear_session(session_id)
        self._notification_manager.clear_session(session_id)
    
    def cleanup(self) -> None:
        """Clean up all resources."""
        self._parser.cleanup()
        self._notification_manager.cleanup()


# Global integration instances per team
_integration_instances: dict[str, ClawTeamIntegration] = {}
_integration_lock = threading.Lock()


def get_integration(team_name: str) -> ClawTeamIntegration:
    """Get or create integration instance for a team."""
    global _integration_instances
    with _integration_lock:
        if team_name not in _integration_instances:
            _integration_instances[team_name] = ClawTeamIntegration(team_name)
        return _integration_instances[team_name]


def remove_integration(team_name: str) -> None:
    """Remove integration instance for a team."""
    global _integration_instances
    with _integration_lock:
        integration = _integration_instances.pop(team_name, None)
        if integration:
            integration.cleanup()


# Convenience functions
def parse_and_notify(team_name: str, session_id: str, data: str, provider_id: str | None = None) -> list[ActivityEvent]:
    """Parse output and trigger notifications using global integration."""
    integration = get_integration(team_name)
    return integration.parse_output(session_id, data, provider_id)