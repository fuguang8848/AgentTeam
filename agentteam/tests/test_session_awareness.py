"""Tests for session awareness module."""

import os
import sys
import json
import tempfile
import time
import uuid

import pytest

# Ensure agentteam is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agentteam.session_awareness import (
    AgentSessionTracker,
    SessionAwarenessManager,
    SessionContext,
    SessionStatus,
    SessionActivityLevel,
    get_session_awareness_manager,
    register_session,
    get_session_tracker,
    get_team_summary,
)


class TestSessionStatus:
    """Test SessionStatus enum."""

    def test_all_statuses_exist(self):
        assert SessionStatus.CREATED.value == "created"
        assert SessionStatus.ACTIVE.value == "active"
        assert SessionStatus.IDLE.value == "idle"
        assert SessionStatus.PAUSED.value == "paused"
        assert SessionStatus.TERMINATED.value == "terminated"


class TestSessionActivityLevel:
    """Test SessionActivityLevel enum."""

    def test_all_levels_exist(self):
        assert SessionActivityLevel.HIGH.value == "high"
        assert SessionActivityLevel.MEDIUM.value == "medium"
        assert SessionActivityLevel.LOW.value == "low"
        assert SessionActivityLevel.INACTIVE.value == "inactive"


class TestSessionContext:
    """Test SessionContext dataclass."""

    def test_create_context(self):
        ctx = SessionContext(
            session_id="test-1",
            agent_name="agent-1",
            team_name="team-1",
        )
        assert ctx.session_id == "test-1"
        assert ctx.agent_name == "agent-1"
        assert ctx.team_name == "team-1"
        assert ctx.message_count == 0
        assert ctx.file_change_count == 0
        assert ctx.status == SessionStatus.CREATED
        assert ctx.activity_level == SessionActivityLevel.LOW

    def test_to_dict(self):
        ctx = SessionContext(
            session_id="test-1",
            agent_name="agent-1",
            team_name="team-1",
        )
        ctx.tags.add("important")
        data = ctx.to_dict()
        assert data["session_id"] == "test-1"
        assert data["agent_name"] == "agent-1"
        assert isinstance(data["created_at"], str)
        assert isinstance(data["last_activity"], str)
        assert data["status"] == "created"
        assert data["activity_level"] == "low"
        assert data["tags"] == ["important"]

    def test_from_dict(self):
        data = {
            "session_id": "test-2",
            "agent_name": "agent-2",
            "team_name": "team-2",
            "created_at": "2024-01-01T00:00:00",
            "last_activity": "2024-01-01T00:01:00",
            "status": "active",
            "activity_level": "high",
            "tags": ["test", "important"],
            "message_count": 5,
            "file_change_count": 2,
            "current_task": "Build feature",
            "current_file": "src/main.py",
        }
        ctx = SessionContext.from_dict(data)
        assert ctx.session_id == "test-2"
        assert ctx.status == SessionStatus.ACTIVE
        assert ctx.activity_level == SessionActivityLevel.HIGH
        assert "test" in ctx.tags
        assert "important" in ctx.tags
        assert ctx.message_count == 5


class TestAgentSessionTracker:
    """Test AgentSessionTracker."""

    @pytest.fixture
    def tracker(self):
        """Create a tracker with a unique team name for isolation."""
        team_name = f"test-team-{uuid.uuid4().hex[:8]}"
        return AgentSessionTracker("sess-1", "agent-1", team_name)

    def test_create_tracker(self, tracker):
        assert tracker.session_id == "sess-1"
        assert tracker.agent_name == "agent-1"
        assert tracker.context.status == SessionStatus.ACTIVE  # New sessions are active by default
        assert tracker.context.message_count == 0

    def test_update_activity(self, tracker):
        tracker.update_activity("hello")
        assert tracker.context.message_count == 1

        tracker.update_activity("world")
        assert tracker.context.message_count == 2

    def test_track_file_change(self, tracker):
        tracker.track_file_change("src/main.py", "modified")
        assert tracker.context.file_change_count == 1
        assert tracker.context.current_file == "src/main.py"

    def test_set_current_task(self, tracker):
        tracker.set_current_task("Build API")
        assert tracker.context.current_task == "Build API"

    def test_set_working_directory(self, tracker):
        tracker.set_working_directory("/project")
        assert tracker.context.working_directory == "/project"

    def test_add_tag(self, tracker):
        tracker.add_tag("urgent")
        tracker.add_tag("backend")
        assert "urgent" in tracker.context.tags
        assert "backend" in tracker.context.tags

    def test_get_summary(self, tracker):
        tracker.update_activity("test message")
        tracker.track_file_change("file.py")
        tracker.set_current_task("Test task")
        tracker.add_tag("test")

        summary = tracker.get_summary()
        assert summary["session_id"] == "sess-1"
        assert summary["agent_name"] == "agent-1"
        assert summary["message_count"] == 1
        assert summary["file_change_count"] == 1
        assert summary["current_task"] == "Test task"
        assert "test" in summary["tags"]

    def test_to_json_and_from_json(self, tracker):
        tracker.update_activity("test")
        tracker.set_current_task("Task")

        json_str = tracker.to_json()
        data = json.loads(json_str)
        assert data["session_id"] == "sess-1"

        # Create new tracker and load from JSON
        team_name = f"test-team-{uuid.uuid4().hex[:8]}"
        new_tracker = AgentSessionTracker("sess-2", "agent-2", team_name)
        new_tracker.from_json(json_str)

        assert new_tracker.context.session_id == "sess-1"
        assert new_tracker.context.agent_name == "agent-1"


class TestSessionAwarenessManager:
    """Test SessionAwarenessManager."""

    @pytest.fixture
    def manager(self):
        """Create a manager with a unique team name."""
        team_name = f"test-team-{uuid.uuid4().hex[:8]}"
        return SessionAwarenessManager(team_name)

    def test_register_session(self, manager):
        tracker = manager.register_session("sess-1", "agent-1")
        assert tracker is not None
        assert tracker.session_id == "sess-1"
        assert tracker.agent_name == "agent-1"

    def test_register_session_duplicate(self, manager):
        t1 = manager.register_session("sess-1", "agent-1")
        t2 = manager.register_session("sess-1", "agent-2")  # same ID
        assert t1 is t2  # Should return same tracker

    def test_unregister_session(self, manager):
        manager.register_session("sess-1", "agent-1")
        result = manager.unregister_session("sess-1")
        assert result is True

        # Should return None after unregister
        assert manager.get_session_tracker("sess-1") is None

    def test_unregister_nonexistent(self, manager):
        result = manager.unregister_session("nonexistent")
        assert result is False

    def test_get_active_sessions(self, manager):
        manager.register_session("sess-1", "agent-1")
        manager.register_session("sess-2", "agent-2")

        active = manager.get_active_sessions()
        assert len(active) == 2

    def test_get_sessions_by_agent(self, manager):
        manager.register_session("sess-1", "agent-1")
        manager.register_session("sess-2", "agent-1")
        manager.register_session("sess-3", "agent-2")

        sessions = manager.get_sessions_by_agent("agent-1")
        assert len(sessions) == 2

    def test_get_sessions_by_activity(self, manager):
        tracker = manager.register_session("sess-1", "agent-1")
        tracker.update_activity()

        sessions = manager.get_sessions_by_activity(SessionActivityLevel.LOW)
        assert len(sessions) == 1

    def test_get_team_summary(self, manager):
        manager.register_session("sess-1", "agent-1")
        manager.register_session("sess-2", "agent-2")

        summary = manager.get_team_summary()
        assert summary["team_name"] == manager.team_name
        assert summary["total_sessions"] == 2
        assert summary["active_sessions"] == 2
        assert len(summary["agents"]) == 2

    def test_find_collaborators(self, manager):
        t1 = manager.register_session("sess-1", "agent-1")
        t2 = manager.register_session("sess-2", "agent-2")
        t3 = manager.register_session("sess-3", "agent-3")

        t1.set_current_task("Build API endpoint")
        t1.add_tag("backend")
        t1.track_file_change("src/api.py")

        t2.set_current_task("API endpoint test")
        t2.add_tag("backend")
        t2.track_file_change("src/api.py")

        t3.set_current_task("UI design")
        t3.add_tag("frontend")

        collaborators = manager.find_collaborators("sess-1", max_sessions=2)
        assert len(collaborators) <= 2

        # agent-2 should score higher (same file + similar task)
        if len(collaborators) >= 1:
            assert collaborators[0]["agent_name"] == "agent-2"

    def test_cleanup_inactive_sessions(self, manager):
        manager.register_session("sess-1", "agent-1")

        # Manually set last_activity to old time
        from datetime import datetime, timedelta

        tracker = manager.get_session_tracker("sess-1")
        tracker.context.last_activity = datetime.now() - timedelta(minutes=70)

        cleaned = manager.cleanup_inactive_sessions(max_inactive_minutes=60)
        assert cleaned == 1
        assert manager.get_session_tracker("sess-1") is None

    def test_save_and_load_state(self, manager, tmp_path):
        manager.register_session("sess-1", "agent-1")
        manager.get_session_tracker("sess-1").set_current_task("Test task")

        filepath = str(tmp_path / "state.json")
        manager.save_state(filepath)
        assert os.path.exists(filepath)

        # Load into new manager
        manager2 = SessionAwarenessManager(manager.team_name)
        manager2.load_state(filepath)

        tracker = manager2.get_session_tracker("sess-1")
        assert tracker is not None
        assert tracker.context.current_task == "Test task"

    def test_load_nonexistent_file(self, manager):
        manager.load_state("/nonexistent/path/state.json")
        # Should not raise, just silently return


class TestGlobalFunctions:
    """Test global convenience functions."""

    def test_get_session_awareness_manager(self):
        # Reset global state for test
        import agentteam.session_awareness as sa

        sa._global_manager = None

        manager = get_session_awareness_manager("test-team")
        assert manager is not None
        assert manager.team_name == "test-team"

    def test_register_and_get_session(self):
        # Reset global state
        import agentteam.session_awareness as sa

        sa._global_manager = None

        team_name = f"test-team-{uuid.uuid4().hex[:8]}"
        tracker = register_session("sess-test", "agent-test", team_name)
        assert tracker is not None

        retrieved = get_session_tracker("sess-test", team_name)
        assert retrieved is not None
        assert retrieved.session_id == "sess-test"

    def test_get_team_summary(self):
        # Reset global state
        import agentteam.session_awareness as sa

        sa._global_manager = None

        team_name = f"test-team-{uuid.uuid4().hex[:8]}"
        register_session("sess-1", "agent-1", team_name)

        summary = get_team_summary(team_name)
        assert summary["total_sessions"] == 1
