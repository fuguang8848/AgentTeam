"""Tests for Cross-Session Message Bus."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from agentteam.session.cross_session import (
    CrossSessionBus,
    CrossSessionMessage,
    NotificationType,
    get_cross_session_bus,
)
from agentteam.session.registry import (
    SessionRegistry,
    SessionStatus,
)


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def registry(temp_data_dir):
    """Create a SessionRegistry with temporary data directory."""
    return SessionRegistry(data_dir=temp_data_dir)


@pytest.fixture
def bus(temp_data_dir):
    """Create a CrossSessionBus with temporary data directory."""
    return CrossSessionBus(data_dir=temp_data_dir)


@pytest.fixture
def setup_sessions(registry):
    """Create test sessions."""
    leader = registry.register(
        session_name="leader-session",
        team_name="team-1",
        agent_name="leader",
        role="leader",
    )
    worker1 = registry.register(
        session_name="worker-1",
        team_name="team-1",
        agent_name="worker-1",
        role="worker",
    )
    worker2 = registry.register(
        session_name="worker-2",
        team_name="team-1",
        agent_name="worker-2",
        role="worker",
    )
    return {"leader": leader, "worker1": worker1, "worker2": worker2}


class TestCrossSessionMessage:
    """Tests for CrossSessionMessage model."""

    def test_message_creation(self):
        """Test creating a CrossSessionMessage."""
        msg = CrossSessionMessage(
            from_session="session-1",
            from_agent="agent-1",
            to_session="session-2",
            notification_type=NotificationType.direct_message,
            content="Hello",
        )
        
        assert msg.from_session == "session-1"
        assert msg.from_agent == "agent-1"
        assert msg.to_session == "session-2"
        assert msg.notification_type == NotificationType.direct_message
        assert msg.content == "Hello"
        assert not msg.read
        assert len(msg.message_id) == 12

    def test_message_serialization(self):
        """Test CrossSessionMessage serialization."""
        msg = CrossSessionMessage(
            from_session="s1",
            to_session="s2",
            content="Test",
            payload={"key": "value"},
        )
        
        data = msg.model_dump(by_alias=True, exclude_none=True)
        
        assert "messageId" in data
        assert "fromSession" in data
        assert "toSession" in data
        assert "notificationType" in data
        assert "payload" in data

    def test_notification_types(self):
        """Test all notification types."""
        types = [
            NotificationType.task_complete,
            NotificationType.task_started,
            NotificationType.file_conflict,
            NotificationType.file_modified,
            NotificationType.broadcast,
            NotificationType.direct_message,
            NotificationType.session_joined,
            NotificationType.session_left,
            NotificationType.status_update,
            NotificationType.alert,
        ]
        
        for t in types:
            msg = CrossSessionMessage(notification_type=t)
            assert msg.notification_type == t


class TestCrossSessionBus:
    """Tests for CrossSessionBus."""

    def test_send_message(self, bus, setup_sessions):
        """Test sending a direct message."""
        sender = setup_sessions["worker1"]
        receiver = setup_sessions["worker2"]
        
        msg = bus.send(
            from_session=sender.session_id,
            from_agent=sender.agent_name,
            to_session=receiver.session_id,
            content="Hello from worker1",
        )
        
        assert msg.to_session == receiver.session_id
        assert msg.content == "Hello from worker1"
        
        # Verify message saved
        path = bus._message_path(receiver.session_id, msg.message_id)
        assert path.exists()

    def test_send_with_payload(self, bus, setup_sessions):
        """Test sending a message with payload."""
        sender = setup_sessions["worker1"]
        receiver = setup_sessions["worker2"]
        
        msg = bus.send(
            from_session=sender.session_id,
            from_agent=sender.agent_name,
            to_session=receiver.session_id,
            content="Task update",
            payload={"taskId": "task-123", "status": "completed"},
        )
        
        assert msg.payload["taskId"] == "task-123"

    def test_broadcast(self, bus, setup_sessions):
        """Test broadcasting a message."""
        sender = setup_sessions["leader"]
        worker1 = setup_sessions["worker1"]
        worker2 = setup_sessions["worker2"]
        
        messages = bus.broadcast(
            from_session=sender.session_id,
            from_agent=sender.agent_name,
            content="Team announcement",
            target_sessions=[worker1.session_id, worker2.session_id],
        )
        
        # Should send to worker1 and worker2 (excluding sender)
        assert len(messages) == 2
        
        for msg in messages:
            assert msg.from_session == sender.session_id
            assert msg.to_session != sender.session_id
            assert msg.notification_type == NotificationType.broadcast

    def test_broadcast_exclude(self, bus, setup_sessions):
        """Test broadcasting with exclusions."""
        sender = setup_sessions["leader"]
        worker1 = setup_sessions["worker1"]
        worker2 = setup_sessions["worker2"]
        exclude = [worker2.session_id]
        
        messages = bus.broadcast(
            from_session=sender.session_id,
            from_agent=sender.agent_name,
            content="Message",
            exclude_sessions=exclude,
            target_sessions=[worker1.session_id, worker2.session_id],
        )
        
        # Should only send to worker1
        assert len(messages) == 1
        assert messages[0].to_session == worker1.session_id

    def test_receive_messages(self, bus, setup_sessions):
        """Test receiving messages."""
        sender = setup_sessions["worker1"]
        receiver = setup_sessions["worker2"]
        
        # Send multiple messages
        bus.send(
            from_session=sender.session_id,
            from_agent=sender.agent_name,
            to_session=receiver.session_id,
            content="Message 1",
        )
        bus.send(
            from_session=sender.session_id,
            from_agent=sender.agent_name,
            to_session=receiver.session_id,
            content="Message 2",
        )
        
        messages = bus.receive(receiver.session_id, limit=10)
        
        assert len(messages) == 2
        
        # Verify messages marked as read
        for msg in messages:
            assert msg.read

    def test_receive_unread_only(self, bus, setup_sessions):
        """Test receiving only unread messages."""
        sender = setup_sessions["worker1"]
        receiver = setup_sessions["worker2"]
        
        # Send messages
        bus.send(
            from_session=sender.session_id,
            from_agent=sender.agent_name,
            to_session=receiver.session_id,
            content="Message 1",
        )
        bus.send(
            from_session=sender.session_id,
            from_agent=sender.agent_name,
            to_session=receiver.session_id,
            content="Message 2",
        )
        
        # Receive first message (marks as read)
        first = bus.receive(receiver.session_id, limit=1)
        assert len(first) == 1
        
        # Receive unread only - should get the remaining message
        unread = bus.receive(receiver.session_id, limit=10, unread_only=True)
        assert len(unread) == 1
        # The content could be either Message 1 or Message 2 depending on order
        assert unread[0].content in ["Message 1", "Message 2"]

    def test_peek_messages(self, bus, setup_sessions):
        """Test peeking at messages without marking read."""
        sender = setup_sessions["worker1"]
        receiver = setup_sessions["worker2"]
        
        bus.send(
            from_session=sender.session_id,
            from_agent=sender.agent_name,
            to_session=receiver.session_id,
            content="Test",
        )
        
        messages = bus.peek(receiver.session_id)
        
        assert len(messages) == 1
        assert not messages[0].read
        
        # Verify still unread after peek
        unread_count = bus.count_unread(receiver.session_id)
        assert unread_count == 1

    def test_count_unread(self, bus, setup_sessions):
        """Test counting unread messages."""
        sender = setup_sessions["worker1"]
        receiver = setup_sessions["worker2"]
        
        # Send 3 messages
        for i in range(3):
            bus.send(
                from_session=sender.session_id,
                from_agent=sender.agent_name,
                to_session=receiver.session_id,
                content=f"Message {i}",
            )
        
        count = bus.count_unread(receiver.session_id)
        assert count == 3
        
        # Read one message
        bus.receive(receiver.session_id, limit=1)
        
        count = bus.count_unread(receiver.session_id)
        assert count == 2

    def test_clear_read(self, bus, setup_sessions):
        """Test clearing read messages."""
        sender = setup_sessions["worker1"]
        receiver = setup_sessions["worker2"]
        
        # Send and read messages
        bus.send(
            from_session=sender.session_id,
            from_agent=sender.agent_name,
            to_session=receiver.session_id,
            content="Message 1",
        )
        bus.send(
            from_session=sender.session_id,
            from_agent=sender.agent_name,
            to_session=receiver.session_id,
            content="Message 2",
        )
        bus.receive(receiver.session_id, limit=10)
        
        cleared = bus.clear_read(receiver.session_id)
        assert cleared == 2
        
        # Verify inbox empty
        messages = bus.peek(receiver.session_id)
        assert len(messages) == 0

    def test_get_message(self, bus, setup_sessions):
        """Test getting a specific message."""
        sender = setup_sessions["worker1"]
        receiver = setup_sessions["worker2"]
        
        msg = bus.send(
            from_session=sender.session_id,
            from_agent=sender.agent_name,
            to_session=receiver.session_id,
            content="Test",
        )
        
        loaded = bus.get_message(receiver.session_id, msg.message_id)
        
        assert loaded is not None
        assert loaded.content == "Test"

    def test_delete_message(self, bus, setup_sessions):
        """Test deleting a specific message."""
        sender = setup_sessions["worker1"]
        receiver = setup_sessions["worker2"]
        
        msg = bus.send(
            from_session=sender.session_id,
            from_agent=sender.agent_name,
            to_session=receiver.session_id,
            content="Test",
        )
        
        success = bus.delete_message(receiver.session_id, msg.message_id)
        assert success
        
        # Verify deleted
        loaded = bus.get_message(receiver.session_id, msg.message_id)
        assert loaded is None


class TestNotifications:
    """Tests for notification methods."""

    def test_notify_completion_broadcast(self, bus, setup_sessions):
        """Test task completion notification (broadcast)."""
        sender = setup_sessions["worker1"]
        leader = setup_sessions["leader"]
        worker2 = setup_sessions["worker2"]
        
        messages = bus.notify_completion(
            from_session=sender.session_id,
            from_agent=sender.agent_name,
            task_id="task-123",
            task_name="Implement feature",
            summary="Completed successfully",
            files_modified=["/src/api.py"],
            success=True,
            broadcast=True,
            target_sessions=[leader.session_id, worker2.session_id],
        )
        
        # Check that messages were sent (may be list or single message)
        if isinstance(messages, list):
            assert len(messages) >= 1
            for msg in messages:
                assert msg.notification_type == NotificationType.task_complete
                assert msg.payload["taskId"] == "task-123"
                assert msg.payload["success"]
        else:
            assert messages.notification_type == NotificationType.task_complete

    def test_notify_completion_failed(self, bus, setup_sessions):
        """Test task failure notification."""
        sender = setup_sessions["worker1"]
        
        messages = bus.notify_completion(
            from_session=sender.session_id,
            from_agent=sender.agent_name,
            task_id="task-123",
            task_name="Implement feature",
            summary="Failed due to error",
            success=False,
            broadcast=True,
        )
        
        for msg in messages:
            assert "failed" in msg.content.lower()

    def test_notify_conflict(self, bus, setup_sessions):
        """Test file conflict notification."""
        sender = setup_sessions["worker1"]
        conflicting = [setup_sessions["worker2"].session_id]
        
        messages = bus.notify_conflict(
            from_session=sender.session_id,
            from_agent=sender.agent_name,
            file_path="/src/api.py",
            conflict_type="write",
            description="Both sessions modifying same file",
            conflicting_sessions=conflicting,
        )
        
        # Should send to worker2 and broadcast alert
        assert len(messages) >= 1
        
        # Check conflict message
        conflict_msgs = [m for m in messages if m.notification_type == NotificationType.file_conflict]
        assert len(conflict_msgs) == 1
        assert conflict_msgs[0].payload["filePath"] == "/src/api.py"

    def test_notify_file_modified(self, bus, setup_sessions):
        """Test file modification notification."""
        sender = setup_sessions["worker1"]
        leader = setup_sessions["leader"]
        worker2 = setup_sessions["worker2"]
        
        messages = bus.notify_file_modified(
            from_session=sender.session_id,
            from_agent=sender.agent_name,
            file_path="/src/api.py",
            operation="write",
            broadcast=True,
            target_sessions=[leader.session_id, worker2.session_id],
        )
        
        # Check that messages were sent
        if isinstance(messages, list):
            assert len(messages) >= 1
            for msg in messages:
                assert msg.notification_type == NotificationType.file_modified
                assert msg.payload["filePath"] == "/src/api.py"
        else:
            assert messages.notification_type == NotificationType.file_modified


class TestGetCrossSessionBus:
    """Tests for singleton bus."""

    def test_singleton(self, temp_data_dir):
        """Test that get_cross_session_bus returns singleton."""
        import agentteam.session.cross_session as bus_module
        bus_module._bus = None
        
        os.environ["AGENTTEAM_DATA_DIR"] = str(temp_data_dir)
        
        b1 = get_cross_session_bus()
        b2 = get_cross_session_bus()
        
        assert b1 is b2
        
        del os.environ["AGENTTEAM_DATA_DIR"]
        bus_module._bus = None


class TestIntegration:
    """Integration tests for session registry and bus."""

    def test_full_workflow(self, registry, bus):
        """Test full workflow: register, send, receive, search."""
        # Register sessions
        leader = registry.register(
            session_name="leader",
            team_name="team-1",
            agent_name="leader",
            role="leader",
        )
        worker = registry.register(
            session_name="worker",
            team_name="team-1",
            agent_name="worker",
            role="worker",
        )
        
        # Send message
        bus.send(
            from_session=leader.session_id,
            from_agent=leader.agent_name,
            to_session=worker.session_id,
            content="Start task-123",
            notification_type=NotificationType.task_started,
        )
        
        # Worker receives
        messages = bus.receive(worker.session_id)
        assert len(messages) == 1
        
        # Log activity
        registry.log_activity(
            session_id=worker.session_id,
            activity_type="task_started",
            description="Started task-123",
        )
        
        # Search for session
        results = registry.search_sessions("task-123")
        assert len(results) == 1
        
        # Notify completion
        bus.notify_completion(
            from_session=worker.session_id,
            from_agent=worker.agent_name,
            task_id="task-123",
            task_name="Task",
            summary="Done",
            broadcast=True,
            target_sessions=[leader.session_id],
        )
        
        # Leader receives completion
        leader_msgs = bus.receive(leader.session_id)
        assert len(leader_msgs) == 1
        assert leader_msgs[0].notification_type == NotificationType.task_complete