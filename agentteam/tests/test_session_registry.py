"""Tests for Session Registry (Cross-Session Awareness)."""

import json
import os
import tempfile
from pathlib import Path
from datetime import datetime, timezone

import pytest

from agentteam.session.registry import (
    SessionRegistry,
    SessionInfo,
    SessionStatus,
    SessionActivity,
    get_session_registry,
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


class TestSessionInfo:
    """Tests for SessionInfo model."""

    def test_session_info_creation(self):
        """Test creating a SessionInfo instance."""
        session = SessionInfo(
            session_name="test-session",
            work_dir="/tmp/work",
            team_name="team-1",
            agent_name="agent-1",
            agent_id="abc123",
            role="worker",
            provider="claude-code",
        )
        
        assert session.session_name == "test-session"
        assert session.work_dir == "/tmp/work"
        assert session.team_name == "team-1"
        assert session.agent_name == "agent-1"
        assert session.agent_id == "abc123"
        assert session.role == "worker"
        assert session.provider == "claude-code"
        assert session.status == SessionStatus.active
        assert len(session.session_id) == 12

    def test_session_info_serialization(self):
        """Test SessionInfo serialization with aliases."""
        session = SessionInfo(
            session_name="test",
            team_name="team-1",
        )
        
        data = session.model_dump(by_alias=True, exclude_none=True)
        
        assert "sessionId" in data
        assert "sessionName" in data
        assert "teamName" in data
        assert "createdAt" in data
        assert "updatedAt" in data

    def test_session_info_defaults(self):
        """Test SessionInfo default values."""
        session = SessionInfo()
        
        assert session.status == SessionStatus.active
        assert session.role == "worker"
        assert session.files_modified == []
        assert session.commands_executed == []
        assert session.tasks_completed == 0


class TestSessionRegistry:
    """Tests for SessionRegistry."""

    def test_register_session(self, registry):
        """Test registering a new session."""
        session = registry.register(
            session_name="test-session",
            work_dir="/tmp/work",
            team_name="team-1",
            agent_name="agent-1",
            agent_id="abc123",
            role="leader",
            provider="claude-code",
        )
        
        assert session.session_name == "test-session"
        assert session.team_name == "team-1"
        assert session.role == "leader"
        assert session.status == SessionStatus.active
        
        # Verify saved to disk
        path = registry._session_path(session.session_id)
        assert path.exists()

    def test_unregister_session(self, registry):
        """Test unregistering a session."""
        session = registry.register(session_name="test")
        
        success = registry.unregister(session.session_id)
        assert success
        
        # Verify marked as shutdown
        loaded = registry.get_session(session.session_id)
        assert loaded.status == SessionStatus.shutdown

    def test_unregister_nonexistent(self, registry):
        """Test unregistering a nonexistent session."""
        success = registry.unregister("nonexistent")
        assert not success

    def test_get_session(self, registry):
        """Test getting a session by ID."""
        session = registry.register(session_name="test")
        
        loaded = registry.get_session(session.session_id)
        assert loaded is not None
        assert loaded.session_name == "test"

    def test_get_session_not_found(self, registry):
        """Test getting a nonexistent session."""
        loaded = registry.get_session("nonexistent")
        assert loaded is None

    def test_get_session_by_name(self, registry):
        """Test getting a session by name."""
        session = registry.register(session_name="my-session")
        
        loaded = registry.get_session_by_name("my-session")
        assert loaded is not None
        assert loaded.session_id == session.session_id

    def test_update_session(self, registry):
        """Test updating session fields."""
        session = registry.register(session_name="test")
        
        updated = registry.update_session(
            session.session_id,
            status=SessionStatus.idle,
            current_task="task-123",
        )
        
        assert updated is not None
        assert updated.status == SessionStatus.idle
        assert updated.current_task == "task-123"

    def test_heartbeat(self, registry):
        """Test updating session heartbeat."""
        session = registry.register(session_name="test")
        
        success = registry.heartbeat(session.session_id)
        assert success
        
        loaded = registry.get_session(session.session_id)
        assert loaded.last_heartbeat != session.created_at

    def test_list_sessions(self, registry):
        """Test listing sessions."""
        registry.register(session_name="session-1", team_name="team-1")
        registry.register(session_name="session-2", team_name="team-2")
        registry.register(session_name="session-3", team_name="team-1")
        
        sessions = registry.list_sessions()
        assert len(sessions) == 3

    def test_list_sessions_filter_status(self, registry):
        """Test listing sessions with status filter."""
        s1 = registry.register(session_name="active-1")
        s2 = registry.register(session_name="active-2")
        s3 = registry.register(session_name="idle-1")
        registry.update_session(s3.session_id, status=SessionStatus.idle)
        
        sessions = registry.list_sessions(status=SessionStatus.active)
        assert len(sessions) == 2

    def test_list_sessions_filter_team(self, registry):
        """Test listing sessions with team filter."""
        registry.register(session_name="s1", team_name="team-1")
        registry.register(session_name="s2", team_name="team-2")
        registry.register(session_name="s3", team_name="team-1")
        
        sessions = registry.list_sessions(team_name="team-1")
        assert len(sessions) == 2

    def test_list_sessions_filter_role(self, registry):
        """Test listing sessions with role filter."""
        registry.register(session_name="s1", role="leader")
        registry.register(session_name="s2", role="worker")
        registry.register(session_name="s3", role="leader")
        
        sessions = registry.list_sessions(role="leader")
        assert len(sessions) == 2

    def test_list_sessions_limit(self, registry):
        """Test listing sessions with limit."""
        for i in range(10):
            registry.register(session_name=f"session-{i}")
        
        sessions = registry.list_sessions(limit=5)
        assert len(sessions) == 5

    def test_get_session_summary(self, registry):
        """Test getting session summary."""
        session = registry.register(
            session_name="test",
            team_name="team-1",
            agent_name="agent-1",
        )
        
        summary = registry.get_session_summary(session_id=session.session_id)
        
        assert "session" in summary
        assert "recentActivities" in summary
        assert "statistics" in summary
        assert summary["session"]["sessionId"] == session.session_id

    def test_get_session_summary_by_name(self, registry):
        """Test getting session summary by name."""
        session = registry.register(session_name="my-session")
        
        summary = registry.get_session_summary(session_name="my-session")
        
        assert "session" in summary
        assert summary["session"]["sessionId"] == session.session_id

    def test_get_session_summary_not_found(self, registry):
        """Test getting summary for nonexistent session."""
        summary = registry.get_session_summary(session_id="nonexistent")
        
        assert "error" in summary

    def test_log_activity(self, registry):
        """Test logging an activity."""
        session = registry.register(session_name="test")
        
        activity = registry.log_activity(
            session_id=session.session_id,
            activity_type="file_write",
            description="Modified file.py",
            details={"file": "/path/to/file.py"},
        )
        
        assert activity is not None
        assert activity.activity_type == "file_write"
        assert activity.description == "Modified file.py"
        
        # Verify activity saved
        activities = registry._get_recent_activities(session.session_id)
        assert len(activities) == 1
        
        # Verify session updated
        loaded = registry.get_session(session.session_id)
        assert "/path/to/file.py" in loaded.files_modified

    def test_log_activity_command(self, registry):
        """Test logging a command activity."""
        session = registry.register(session_name="test")
        
        registry.log_activity(
            session_id=session.session_id,
            activity_type="command",
            description="Ran pytest",
            details={"command": "pytest tests/"},
        )
        
        loaded = registry.get_session(session.session_id)
        assert "pytest tests/" in loaded.commands_executed

    def test_log_activity_task_complete(self, registry):
        """Test logging a task completion activity."""
        session = registry.register(session_name="test")
        
        registry.log_activity(
            session_id=session.session_id,
            activity_type="task_complete",
            description="Completed task-123",
        )
        
        loaded = registry.get_session(session.session_id)
        assert loaded.tasks_completed == 1

    def test_search_sessions(self, registry):
        """Test searching sessions."""
        registry.register(
            session_name="backend-session",
            agent_name="backend-agent",
            team_name="team-1",
        )
        registry.register(
            session_name="frontend-session",
            agent_name="frontend-agent",
            team_name="team-2",
        )
        
        results = registry.search_sessions("backend")
        
        assert len(results) == 1
        assert results[0]["session"]["sessionName"] == "backend-session"

    def test_search_sessions_files(self, registry):
        """Test searching sessions by file path."""
        session = registry.register(session_name="test")
        registry.log_activity(
            session_id=session.session_id,
            activity_type="file_write",
            description="Modified file",
            details={"file": "/src/api.py"},
        )
        
        results = registry.search_sessions("api.py")
        
        assert len(results) == 1

    def test_search_sessions_no_results(self, registry):
        """Test searching with no results."""
        registry.register(session_name="test")
        
        results = registry.search_sessions("nonexistent")
        
        assert len(results) == 0

    def test_cleanup_stale_sessions(self, registry):
        """Test cleaning up stale sessions."""
        # Create sessions
        s1 = registry.register(session_name="active")
        s2 = registry.register(session_name="stale")
        
        # Manually set stale session's heartbeat to old time
        old_time = "2020-01-01T00:00:00+00:00"
        registry.update_session(s2.session_id, last_heartbeat=old_time)
        
        cleaned = registry.cleanup_stale_sessions(max_age_hours=1)
        
        assert cleaned == 1
        
        # Verify stale session marked as shutdown
        loaded = registry.get_session(s2.session_id)
        assert loaded.status == SessionStatus.shutdown


class TestSessionActivity:
    """Tests for SessionActivity model."""

    def test_activity_creation(self):
        """Test creating a SessionActivity."""
        activity = SessionActivity(
            session_id="abc123",
            activity_type="file_write",
            description="Modified file.py",
            details={"file": "/path/to/file.py"},
        )
        
        assert activity.session_id == "abc123"
        assert activity.activity_type == "file_write"
        assert activity.description == "Modified file.py"

    def test_activity_serialization(self):
        """Test SessionActivity serialization."""
        activity = SessionActivity(
            session_id="abc",
            activity_type="command",
            description="Test",
        )
        
        data = activity.model_dump(by_alias=True, exclude_none=True)
        
        assert "sessionId" in data
        assert "activityType" in data
        assert "timestamp" in data


class TestGetSessionRegistry:
    """Tests for singleton registry."""

    def test_singleton(self, temp_data_dir):
        """Test that get_session_registry returns singleton."""
        # Reset singleton
        import agentteam.session.registry as reg_module
        reg_module._registry = None
        
        # Set env var for data dir
        os.environ["AGENTTEAM_DATA_DIR"] = str(temp_data_dir)
        
        r1 = get_session_registry()
        r2 = get_session_registry()
        
        assert r1 is r2
        
        # Cleanup
        del os.environ["AGENTTEAM_DATA_DIR"]
        reg_module._registry = None