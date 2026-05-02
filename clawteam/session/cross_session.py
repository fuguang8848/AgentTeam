"""Cross-Session Message Bus for inter-session communication.

This module provides a message bus for cross-session communication, enabling:
- Broadcast messages to all sessions
- Direct messages between sessions
- Task completion notifications
- File conflict notifications

Inspired by SpectrAI's supervisorPrompt.ts awareness layer.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from clawteam.team.models import get_data_dir


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class NotificationType(str, Enum):
    """Types of cross-session notifications."""

    task_complete = "task_complete"
    task_started = "task_started"
    file_conflict = "file_conflict"
    file_modified = "file_modified"
    broadcast = "broadcast"
    direct_message = "direct_message"
    session_joined = "session_joined"
    session_left = "session_left"
    status_update = "status_update"
    alert = "alert"


class CrossSessionMessage(BaseModel):
    """A message in the cross-session bus."""

    model_config = {"populate_by_name": True}

    message_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12], alias="messageId")
    from_session: str = Field(default="", alias="fromSession")
    from_agent: str = Field(default="", alias="fromAgent")
    to_session: str | None = Field(default=None, alias="toSession")  # None = broadcast
    to_agent: str | None = Field(default=None, alias="toAgent")
    notification_type: NotificationType = Field(
        default=NotificationType.broadcast, alias="notificationType"
    )
    content: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=_now_iso)
    priority: str = Field(default="normal")  # low, normal, high, urgent
    read: bool = False
    read_at: str | None = Field(default=None, alias="readAt")
    idempotency_key: str | None = Field(default=None, alias="idempotencyKey")


class CrossSessionBus:
    """Message bus for cross-session communication.

    Provides:
    - broadcast: Send message to all sessions
    - send: Send message to specific session
    - notify_completion: Notify about task completion
    - notify_conflict: Notify about file conflict
    - receive: Get messages for a session
    """

    def __init__(self, data_dir: Path | None = None):
        self._data_dir = data_dir or get_data_dir()
        self._bus_dir = self._data_dir / "cross_session_bus"
        self._bus_dir.mkdir(parents=True, exist_ok=True)

    def _inbox_path(self, session_id: str) -> Path:
        """Get the inbox directory for a session."""
        return self._bus_dir / session_id

    def _message_path(self, session_id: str, message_id: str) -> Path:
        """Get the path to a message file."""
        return self._inbox_path(session_id) / f"msg-{message_id}.json"

    def _deliver(self, to_session: str, message: CrossSessionMessage) -> None:
        """Deliver a message to a session's inbox."""
        inbox = self._inbox_path(to_session)
        inbox.mkdir(parents=True, exist_ok=True)

        path = self._message_path(to_session, message.message_id)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(
            message.model_dump_json(indent=2, by_alias=True, exclude_none=True),
            encoding="utf-8",
        )
        os.replace(str(tmp), str(path))

    def broadcast(
        self,
        from_session: str,
        from_agent: str,
        content: str,
        payload: dict[str, Any] | None = None,
        priority: str = "normal",
        exclude_sessions: list[str] | None = None,
        notification_type: NotificationType = NotificationType.broadcast,
        idempotency_key: str | None = None,
        target_sessions: list[str] | None = None,
    ) -> list[CrossSessionMessage]:
        """Broadcast a message to all active sessions.

        Args:
            from_session: Sender session ID
            from_agent: Sender agent name
            content: Message content
            payload: Additional data
            priority: Message priority (low, normal, high, urgent)
            exclude_sessions: Session IDs to exclude from broadcast
            notification_type: Type of notification
            idempotency_key: Optional key for deduplication
            target_sessions: Optional list of target session IDs (bypasses registry lookup)

        Returns:
            List of delivered messages
        """
        # Get target sessions
        if target_sessions is None:
            from clawteam.session.registry import get_session_registry

            registry = get_session_registry()
            sessions = registry.list_sessions()
            target_session_ids = [s.session_id for s in sessions]
        else:
            target_session_ids = target_sessions

        exclude = set(exclude_sessions or [])
        exclude.add(from_session)  # Don't send to self

        messages = []
        for session_id in target_session_ids:
            if session_id in exclude:
                continue

            msg = CrossSessionMessage(
                from_session=from_session,
                from_agent=from_agent,
                to_session=session_id,
                notification_type=notification_type,
                content=content,
                payload=payload or {},
                priority=priority,
                idempotency_key=idempotency_key,
            )
            self._deliver(session_id, msg)
            messages.append(msg)

        return messages

    def send(
        self,
        from_session: str,
        from_agent: str,
        to_session: str,
        content: str,
        to_agent: str | None = None,
        payload: dict[str, Any] | None = None,
        priority: str = "normal",
        notification_type: NotificationType = NotificationType.direct_message,
        idempotency_key: str | None = None,
    ) -> CrossSessionMessage:
        """Send a message to a specific session.

        Args:
            from_session: Sender session ID
            from_agent: Sender agent name
            to_session: Recipient session ID
            content: Message content
            to_agent: Specific agent to receive (optional)
            payload: Additional data
            priority: Message priority
            notification_type: Type of notification
            idempotency_key: Optional key for deduplication

        Returns:
            The delivered message
        """
        msg = CrossSessionMessage(
            from_session=from_session,
            from_agent=from_agent,
            to_session=to_session,
            to_agent=to_agent,
            notification_type=notification_type,
            content=content,
            payload=payload or {},
            priority=priority,
            idempotency_key=idempotency_key,
        )
        self._deliver(to_session, msg)
        return msg

    def notify_completion(
        self,
        from_session: str,
        from_agent: str,
        task_id: str,
        task_name: str,
        summary: str,
        files_modified: list[str] | None = None,
        success: bool = True,
        broadcast: bool = True,
        target_sessions: list[str] | None = None,
    ) -> CrossSessionMessage | list[CrossSessionMessage]:
        """Notify about task completion.

        Args:
            from_session: Sender session ID
            from_agent: Sender agent name
            task_id: Completed task ID
            task_name: Task name
            summary: Completion summary
            files_modified: List of files modified during task
            success: Whether task completed successfully
            broadcast: If True, broadcast to all sessions; else send to leader
            target_sessions: Optional list of target session IDs

        Returns:
            The delivered message(s)
        """
        content = f"Task '{task_name}' completed: {summary}"
        if not success:
            content = f"Task '{task_name}' failed: {summary}"

        payload = {
            "taskId": task_id,
            "taskName": task_name,
            "summary": summary,
            "filesModified": files_modified or [],
            "success": success,
        }

        if broadcast:
            return self.broadcast(
                from_session=from_session,
                from_agent=from_agent,
                content=content,
                payload=payload,
                notification_type=NotificationType.task_complete,
                priority="high",
                target_sessions=target_sessions,
            )
        else:
            # Send to team leader
            if target_sessions:
                # Use first target as leader
                leader_session_id = target_sessions[0]
            else:
                from clawteam.session.registry import get_session_registry

                registry = get_session_registry()

                # Find leader session
                sessions = registry.list_sessions()
                leader_session = None
                for s in sessions:
                    if s.role == "leader" and s.status.value == "active":
                        leader_session = s
                        break

                if leader_session:
                    leader_session_id = leader_session.session_id
                else:
                    # Fallback to broadcast
                    return self.broadcast(
                        from_session=from_session,
                        from_agent=from_agent,
                        content=content,
                        payload=payload,
                        notification_type=NotificationType.task_complete,
                        priority="high",
                        target_sessions=target_sessions,
                    )

            return self.send(
                from_session=from_session,
                from_agent=from_agent,
                to_session=leader_session_id,
                content=content,
                payload=payload,
                notification_type=NotificationType.task_complete,
                priority="high",
            )

    def notify_conflict(
        self,
        from_session: str,
        from_agent: str,
        file_path: str,
        conflict_type: str,
        description: str,
        conflicting_sessions: list[str] | None = None,
    ) -> list[CrossSessionMessage]:
        """Notify about file conflict.

        Args:
            from_session: Sender session ID
            from_agent: Sender agent name
            file_path: Path to the conflicting file
            conflict_type: Type of conflict (write, delete, lock)
            description: Conflict description
            conflicting_sessions: Other sessions involved in conflict

        Returns:
            List of delivered messages
        """
        content = f"File conflict on '{file_path}': {description}"

        payload = {
            "filePath": file_path,
            "conflictType": conflict_type,
            "description": description,
            "conflictingSessions": conflicting_sessions or [],
        }

        # Send to all conflicting sessions
        messages = []
        target_sessions = set(conflicting_sessions or [])
        target_sessions.discard(from_session)  # Don't send to self

        for session_id in target_sessions:
            msg = self.send(
                from_session=from_session,
                from_agent=from_agent,
                to_session=session_id,
                content=content,
                payload=payload,
                notification_type=NotificationType.file_conflict,
                priority="urgent",
            )
            messages.append(msg)

        # Also broadcast alert to team
        alert_msgs = self.broadcast(
            from_session=from_session,
            from_agent=from_agent,
            content=content,
            payload=payload,
            notification_type=NotificationType.alert,
            priority="high",
            exclude_sessions=list(target_sessions),
        )
        messages.extend(alert_msgs)

        return messages

    def notify_file_modified(
        self,
        from_session: str,
        from_agent: str,
        file_path: str,
        operation: str = "write",
        broadcast: bool = True,
        target_sessions: list[str] | None = None,
    ) -> CrossSessionMessage | list[CrossSessionMessage]:
        """Notify about file modification.

        Args:
            from_session: Sender session ID
            from_agent: Sender agent name
            file_path: Path to the modified file
            operation: Operation type (write, delete, create)
            broadcast: If True, broadcast to all sessions
            target_sessions: Optional list of target session IDs

        Returns:
            The delivered message(s)
        """
        content = f"File {operation}: {file_path}"

        payload = {
            "filePath": file_path,
            "operation": operation,
        }

        if broadcast:
            return self.broadcast(
                from_session=from_session,
                from_agent=from_agent,
                content=content,
                payload=payload,
                notification_type=NotificationType.file_modified,
                priority="normal",
                target_sessions=target_sessions,
            )
        else:
            # Just log, no specific recipient
            return CrossSessionMessage(
                from_session=from_session,
                from_agent=from_agent,
                notification_type=NotificationType.file_modified,
                content=content,
                payload=payload,
            )

    def receive(
        self,
        session_id: str,
        limit: int = 10,
        unread_only: bool = False,
        mark_read: bool = True,
    ) -> list[CrossSessionMessage]:
        """Receive messages for a session.

        Args:
            session_id: Session ID to receive messages for
            limit: Maximum number of messages to return
            unread_only: If True, only return unread messages
            mark_read: If True, mark returned messages as read

        Returns:
            List of messages (newest first)
        """
        inbox = self._inbox_path(session_id)
        if not inbox.exists():
            return []

        messages = []
        files = sorted(inbox.glob("msg-*.json"), reverse=True)[: limit * 2]

        for path in files:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                msg = CrossSessionMessage.model_validate(data)

                if unread_only and msg.read:
                    continue

                if mark_read and not msg.read:
                    msg.read = True
                    msg.read_at = _now_iso()
                    # Update the file
                    tmp = path.with_suffix(".tmp")
                    tmp.write_text(
                        msg.model_dump_json(indent=2, by_alias=True, exclude_none=True),
                        encoding="utf-8",
                    )
                    os.replace(str(tmp), str(path))

                messages.append(msg)

                if len(messages) >= limit:
                    break
            except Exception:
                continue

        return messages

    def peek(
        self,
        session_id: str,
        limit: int = 10,
    ) -> list[CrossSessionMessage]:
        """Peek at messages without marking them as read.

        Args:
            session_id: Session ID
            limit: Maximum messages to return

        Returns:
            List of messages (newest first)
        """
        return self.receive(session_id, limit=limit, unread_only=False, mark_read=False)

    def count_unread(self, session_id: str) -> int:
        """Count unread messages for a session.

        Args:
            session_id: Session ID

        Returns:
            Number of unread messages
        """
        messages = self.receive(session_id, limit=1000, unread_only=True, mark_read=False)
        return len(messages)

    def clear_read(self, session_id: str) -> int:
        """Clear read messages for a session.

        Args:
            session_id: Session ID

        Returns:
            Number of messages cleared
        """
        inbox = self._inbox_path(session_id)
        if not inbox.exists():
            return 0

        cleared = 0
        for path in inbox.glob("msg-*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                msg = CrossSessionMessage.model_validate(data)
                if msg.read:
                    path.unlink()
                    cleared += 1
            except Exception:
                continue

        return cleared

    def get_message(self, session_id: str, message_id: str) -> CrossSessionMessage | None:
        """Get a specific message.

        Args:
            session_id: Session ID
            message_id: Message ID

        Returns:
            The message or None if not found
        """
        path = self._message_path(session_id, message_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return CrossSessionMessage.model_validate(data)
        except Exception:
            return None

    def delete_message(self, session_id: str, message_id: str) -> bool:
        """Delete a specific message.

        Args:
            session_id: Session ID
            message_id: Message ID

        Returns:
            True if deleted, False if not found
        """
        path = self._message_path(session_id, message_id)
        if path.exists():
            path.unlink()
            return True
        return False


# Singleton instance
_bus: CrossSessionBus | None = None


def get_cross_session_bus() -> CrossSessionBus:
    """Get the singleton CrossSessionBus instance."""
    global _bus
    if _bus is None:
        _bus = CrossSessionBus()
    return _bus
