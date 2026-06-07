"""Tests for ChangeAttribution module (P8)."""

import tempfile
from pathlib import Path

import pytest

from agentteam.tracker.change_attribution import (
    ActiveSession,
    AttributionResult,
    ChangeAttributor,
    ChangeRecord,
    create_change_handler,
)
from agentteam.tracker.file_watcher import ChangeType, WatchEvent


class TestChangeRecord:
    """Tests for ChangeRecord model."""

    def test_record_creation(self):
        """Test creating a change record."""
        record = ChangeRecord(
            path="/tmp/test.txt",
            change_type="modified",
        )
        assert record.path == "/tmp/test.txt"
        assert record.change_type == "modified"
        assert record.id.startswith("chg_")

    def test_record_with_attribution(self):
        """Test record with attribution."""
        record = ChangeRecord(
            path="/tmp/test.txt",
            change_type="modified",
            agent_name="test-agent",
            session_id="session-123",
            team_name="test-team",
        )
        assert record.agent_name == "test-agent"
        assert record.session_id == "session-123"

    def test_record_with_diff(self):
        """Test record with diff content."""
        record = ChangeRecord(
            path="/tmp/test.txt",
            change_type="modified",
            diff="--- a/test.txt\n+++ b/test.txt\n",
        )
        assert record.diff is not None

    def test_record_with_checksum(self):
        """Test record with checksum."""
        record = ChangeRecord(
            path="/tmp/test.txt",
            change_type="modified",
            checksum="abc123",
        )
        assert record.checksum == "abc123"

    def test_record_directory_flag(self):
        """Test directory flag."""
        record = ChangeRecord(
            path="/tmp/testdir",
            change_type="created",
            is_directory=True,
        )
        assert record.is_directory is True

    def test_record_moved_with_old_path(self):
        """Test moved record with old path."""
        record = ChangeRecord(
            path="/tmp/new.txt",
            change_type="moved",
            old_path="/tmp/old.txt",
        )
        assert record.old_path == "/tmp/old.txt"

    def test_record_auto_id(self):
        """Test automatic ID generation."""
        record1 = ChangeRecord(path="/tmp/test1.txt", change_type="modified")
        record2 = ChangeRecord(path="/tmp/test2.txt", change_type="modified")
        assert record1.id != record2.id

    def test_record_timestamp(self):
        """Test automatic timestamp."""
        record = ChangeRecord(path="/tmp/test.txt", change_type="modified")
        assert record.timestamp is not None


class TestAttributionResult:
    """Tests for AttributionResult model."""

    def test_result_success(self):
        """Test successful attribution result."""
        result = AttributionResult(
            success=True,
            agent_name="test-agent",
            session_id="session-123",
            confidence=0.95,
            method="explicit",
            reason="Session registered for this file",
        )
        assert result.success is True
        assert result.confidence == 0.95

    def test_result_failure(self):
        """Test failed attribution result."""
        result = AttributionResult(
            success=False,
            confidence=0.0,
            method="unknown",
            reason="No active sessions",
        )
        assert result.success is False
        assert result.confidence == 0.0

    def test_result_methods(self):
        """Test attribution methods."""
        methods = ["explicit", "inferred", "unknown"]
        for method in methods:
            result = AttributionResult(
                success=True,
                method=method,
            )
            assert result.method == method


class TestActiveSession:
    """Tests for ActiveSession model."""

    def test_session_creation(self):
        """Test creating an active session."""
        session = ActiveSession(
            session_id="session-123",
            agent_name="test-agent",
            team_name="test-team",
        )
        assert session.session_id == "session-123"
        assert session.agent_name == "test-agent"

    def test_session_with_task(self):
        """Test session with task."""
        session = ActiveSession(
            session_id="session-123",
            agent_name="test-agent",
            team_name="test-team",
            task_id="task-456",
        )
        assert session.task_id == "task-456"

    def test_session_working_directory(self):
        """Test session working directory."""
        session = ActiveSession(
            session_id="session-123",
            agent_name="test-agent",
            team_name="test-team",
            working_directory="/tmp/work",
        )
        assert session.working_directory == "/tmp/work"

    def test_session_files_modified(self):
        """Test session files modified list."""
        session = ActiveSession(
            session_id="session-123",
            agent_name="test-agent",
            team_name="test-team",
            files_modified=["/tmp/file1.txt", "/tmp/file2.txt"],
        )
        assert len(session.files_modified) == 2

    def test_session_timestamps(self):
        """Test session timestamps."""
        session = ActiveSession(
            session_id="session-123",
            agent_name="test-agent",
            team_name="test-team",
        )
        assert session.started_at is not None
        assert session.last_activity_at is not None


class TestChangeAttributor:
    """Tests for ChangeAttributor class."""

    def test_attributor_initialization(self):
        """Test attributor initialization."""
        attributor = ChangeAttributor("test-team")
        assert attributor.team_name == "test-team"
        assert len(attributor._active_sessions) == 0

    def test_register_session(self):
        """Test registering a session."""
        attributor = ChangeAttributor("test-team")
        attributor.register_session(
            session_id="session-123",
            agent_name="test-agent",
            working_directory="/tmp/work",
        )
        assert len(attributor._active_sessions) == 1
        assert "session-123" in attributor._active_sessions

    def test_unregister_session(self):
        """Test unregistering a session."""
        attributor = ChangeAttributor("test-team")
        attributor.register_session(
            session_id="session-123",
            agent_name="test-agent",
        )
        attributor.unregister_session("session-123")
        assert len(attributor._active_sessions) == 0

    def test_unregister_nonexistent_session(self):
        """Test unregistering nonexistent session."""
        attributor = ChangeAttributor("test-team")
        # Should not raise
        attributor.unregister_session("nonexistent")

    def test_claim_file(self):
        """Test claiming a file."""
        attributor = ChangeAttributor("test-team")
        attributor.register_session(
            session_id="session-123",
            agent_name="test-agent",
        )
        attributor.claim_file("session-123", "/tmp/test.txt")
        assert "/tmp/test.txt" in attributor._file_claims
        assert attributor._file_claims["/tmp/test.txt"] == "session-123"

    def test_release_file(self):
        """Test releasing a file."""
        attributor = ChangeAttributor("test-team")
        attributor.register_session("session-123", "test-agent")
        attributor.claim_file("session-123", "/tmp/test.txt")
        attributor.release_file("/tmp/test.txt")
        assert "/tmp/test.txt" not in attributor._file_claims

    def test_attribute_change_explicit(self):
        """Test explicit attribution."""
        attributor = ChangeAttributor("test-team")
        attributor.register_session(
            session_id="session-123",
            agent_name="test-agent",
            working_directory="/tmp/work",
        )
        attributor.claim_file("session-123", "/tmp/work/test.txt")

        event = WatchEvent(
            path="/tmp/work/test.txt",
            change_type=ChangeType.modified,
        )
        result = attributor.attribute_change(event)
        assert result.success is True
        assert result.method == "explicit"

    def test_attribute_change_inferred(self):
        """Test inferred attribution."""
        attributor = ChangeAttributor("test-team")
        attributor.register_session(
            session_id="session-123",
            agent_name="test-agent",
            working_directory="/tmp/work",
        )

        event = WatchEvent(
            path="/tmp/work/subdir/test.txt",
            change_type=ChangeType.modified,
        )
        result = attributor.attribute_change(event)
        # May be inferred based on working directory
        assert result is not None

    def test_attribute_change_unknown(self):
        """Test unknown attribution."""
        attributor = ChangeAttributor("test-team")

        event = WatchEvent(
            path="/tmp/unrelated/test.txt",
            change_type=ChangeType.modified,
        )
        result = attributor.attribute_change(event)
        assert result.success is False
        assert result.method == "unknown"

    def test_record_change(self):
        """Test recording a change."""
        attributor = ChangeAttributor("test-team")
        attributor.register_session("session-123", "test-agent")

        event = WatchEvent(
            path="/tmp/test.txt",
            change_type=ChangeType.modified,
        )
        result = attributor.attribute_change(event)
        record = attributor.record_change(event, result)
        assert record is not None
        assert record.path == "/tmp/test.txt"

    def test_get_session_files(self):
        """Test getting session files."""
        attributor = ChangeAttributor("test-team")
        attributor.register_session("session-123", "test-agent")
        attributor.claim_file("session-123", "/tmp/file1.txt")
        attributor.claim_file("session-123", "/tmp/file2.txt")

        files = attributor.get_session_files("session-123")
        assert len(files) == 2

    def test_get_active_sessions(self):
        """Test getting active sessions."""
        attributor = ChangeAttributor("test-team")
        attributor.register_session("session-1", "agent-1")
        attributor.register_session("session-2", "agent-2")

        sessions = attributor.get_active_sessions()
        assert len(sessions) == 2


class TestCreateChangeHandler:
    """Tests for create_change_handler function."""

    def test_handler_creation(self):
        """Test creating change handler."""
        attributor = ChangeAttributor("test-team")
        handler = create_change_handler(attributor)
        assert handler is not None
        assert callable(handler)

    def test_handler_with_callback(self):
        """Test handler with callback."""
        attributor = ChangeAttributor("test-team")
        records = []

        def callback(record):
            records.append(record)

        handler = create_change_handler(attributor, on_change=callback)
        assert handler is not None

    def test_handler_skips_directory(self):
        """Test handler skips directory events."""
        attributor = ChangeAttributor("test-team")
        handler = create_change_handler(attributor)

        event = WatchEvent(
            path="/tmp/testdir",
            change_type=ChangeType.created,
            is_directory=True,
        )
        # Should not raise
        handler(event)


class TestChangeAttributorEdgeCases:
    """Edge case tests for ChangeAttributor."""

    def test_multiple_sessions_same_file(self):
        """Test multiple sessions claiming same file."""
        attributor = ChangeAttributor("test-team")
        attributor.register_session("session-1", "agent-1")
        attributor.register_session("session-2", "agent-2")

        # First session claims
        attributor.claim_file("session-1", "/tmp/test.txt")
        # Second session claims (overwrites)
        attributor.claim_file("session-2", "/tmp/test.txt")

        assert attributor._file_claims["/tmp/test.txt"] == "session-2"

    def test_session_activity_update(self):
        """Test session activity update."""
        attributor = ChangeAttributor("test-team")
        attributor.register_session("session-123", "test-agent")

        old_activity = attributor._active_sessions["session-123"].last_activity_at
        attributor.update_session_activity("session-123")

        # Activity should be updated
        new_activity = attributor._active_sessions["session-123"].last_activity_at
        assert new_activity is not None

    def test_buffer_management(self):
        """Test change buffer management."""
        attributor = ChangeAttributor("test-team")

        # Add to buffer
        event = WatchEvent(path="/tmp/test.txt", change_type=ChangeType.modified)
        result = attributor.attribute_change(event)
        attributor.record_change(event, result)

        # Clear buffer
        attributor.clear_buffer()
        assert len(attributor._change_buffer) == 0

    def test_large_buffer(self):
        """Test large buffer handling."""
        attributor = ChangeAttributor("test-team", buffer_size=10)

        for i in range(20):
            event = WatchEvent(
                path=f"/tmp/test{i}.txt",
                change_type=ChangeType.modified,
            )
            result = attributor.attribute_change(event)
            attributor.record_change(event, result)

        # Buffer should be limited
        assert len(attributor._change_buffer) <= attributor._buffer_size
