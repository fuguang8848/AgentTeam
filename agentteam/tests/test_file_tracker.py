"""Tests for FileChangeTracker module (P8)."""

import tempfile
import time
from pathlib import Path

import pytest

from agentteam.tracker.file_tracker import (
    FileChange,
    FileChangeTracker,
    FileChangeTrackerConfig,
    get_file_change_tracker,
    track_file_change,
    get_recent_file_changes,
)


class TestFileChange:
    """Tests for FileChange model."""

    def test_file_change_creation(self):
        """Test creating a file change record."""
        change = FileChange(
            file_path="/tmp/test.txt",
            agent_name="test-agent",
            session_id="session-123",
            change_type="modified",
            diff="--- a/test.txt\n+++ b/test.txt\n",
            team_name="test-team",
            task_id="task-456",
        )
        
        assert change.file_path == "/tmp/test.txt"
        assert change.agent_name == "test-agent"
        assert change.session_id == "session-123"
        assert change.change_type == "modified"
        assert "--- a/" in change.diff
        assert change.team_name == "test-team"
        assert change.task_id == "task-456"
        assert change.timestamp > 0

    def test_file_change_to_dict(self):
        """Test converting file change to dictionary."""
        change = FileChange(
            file_path="/tmp/test.txt",
            agent_name="test-agent",
            session_id="session-123",
            change_type="created",
        )
        
        data = change.to_dict()
        
        assert data["file_path"] == "/tmp/test.txt"
        assert data["agent_name"] == "test-agent"
        assert data["session_id"] == "session-123"
        assert data["change_type"] == "created"
        assert "timestamp" in data


class TestFileChangeTrackerConfig:
    """Tests for FileChangeTrackerConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = FileChangeTrackerConfig()
        
        assert config.watch_paths == []
        assert config.debounce_ms == 100
        assert config.auto_start is True
        assert config.team_name == "default"
        assert config.max_history == 1000
        assert "*.pyc" in config.ignore_patterns
        assert ".git/*" in config.ignore_patterns

    def test_custom_config(self):
        """Test custom configuration."""
        config = FileChangeTrackerConfig(
            watch_paths=["/tmp", "/home"],
            debounce_ms=200,
            auto_start=False,
            team_name="test-team",
            max_history=500,
            ignore_patterns=["*.log", "*.tmp"],
        )
        
        assert config.watch_paths == ["/tmp", "/home"]
        assert config.debounce_ms == 200
        assert config.auto_start is False
        assert config.team_name == "test-team"
        assert config.max_history == 500
        assert config.ignore_patterns == ["*.log", "*.tmp"]


class TestFileChangeTracker:
    """Tests for FileChangeTracker class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def tracker(self, temp_dir):
        """Create a FileChangeTracker instance for testing."""
        config = FileChangeTrackerConfig(
            watch_paths=[str(temp_dir)],
            auto_start=False,  # Don't start watcher automatically
            team_name="test-team",
        )
        return FileChangeTracker(config)

    def test_tracker_initialization(self, tracker):
        """Test tracker initialization."""
        assert tracker.config.team_name == "test-team"
        assert tracker.config.auto_start is False
        assert tracker.watcher is None
        assert tracker.change_history == []
        assert tracker.active_sessions == {}
        assert tracker.attributor is not None
        assert tracker.diff_tracker is not None

    def test_register_session(self, tracker):
        """Test registering a session."""
        tracker.register_session(
            session_id="session-123",
            agent_name="test-agent",
            team_name="test-team",
            task_id="task-456",
            working_directory="/tmp",
        )
        
        assert "session-123" in tracker.active_sessions
        session = tracker.active_sessions["session-123"]
        assert session.agent_name == "test-agent"
        assert session.team_name == "test-team"
        assert session.task_id == "task-456"
        assert session.working_directory == "/tmp"

    def test_unregister_session(self, tracker):
        """Test unregistering a session."""
        tracker.register_session(
            session_id="session-123",
            agent_name="test-agent",
        )
        
        assert "session-123" in tracker.active_sessions
        
        tracker.unregister_session("session-123")
        
        assert "session-123" not in tracker.active_sessions

    def test_update_session_activity(self, tracker):
        """Test updating session activity."""
        tracker.register_session(
            session_id="session-123",
            agent_name="test-agent",
        )
        
        original_activity = tracker.active_sessions["session-123"].last_activity_at
        
        time.sleep(0.01)  # Small delay to ensure timestamp changes
        tracker.update_session_activity("session-123", "/tmp/test.txt")
        
        updated_activity = tracker.active_sessions["session-123"].last_activity_at
        assert updated_activity != original_activity
        
        # Check file was added to modified list
        assert "/tmp/test.txt" in tracker.active_sessions["session-123"].files_modified

    def test_track_manual_change_with_attribution(self, tracker, temp_dir):
        """Test manually tracking a file change with attribution."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("Hello, world!")
        
        tracker.register_session(
            session_id="session-123",
            agent_name="test-agent",
        )
        
        change = tracker.track_manual_change(
            file_path=str(test_file),
            change_type="modified",
            agent_name="test-agent",
            session_id="session-123",
        )
        
        assert change.file_path == str(test_file)
        assert change.agent_name == "test-agent"
        assert change.session_id == "session-123"
        assert change.change_type == "modified"
        
        # Should be added to history
        changes = tracker.get_changes(limit=10)
        assert len(changes) == 1
        assert changes[0].file_path == str(test_file)

    def test_track_manual_change_without_attribution(self, tracker, temp_dir):
        """Test manually tracking a file change without attribution."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("Hello, world!")
        
        change = tracker.track_manual_change(
            file_path=str(test_file),
            change_type="modified",
        )
        
        assert change.file_path == str(test_file)
        assert change.change_type == "modified"
        # Attribution may be empty or inferred

    def test_get_changes_filtering(self, tracker, temp_dir):
        """Test filtering changes by various criteria."""
        # Create some test changes
        test_file1 = temp_dir / "test1.txt"
        test_file2 = temp_dir / "test2.txt"
        
        tracker.register_session(
            session_id="session-123",
            agent_name="agent-a",
        )
        
        tracker.register_session(
            session_id="session-456",
            agent_name="agent-b",
        )
        
        # Track changes
        tracker.track_manual_change(
            file_path=str(test_file1),
            change_type="created",
            agent_name="agent-a",
            session_id="session-123",
        )
        
        tracker.track_manual_change(
            file_path=str(test_file2),
            change_type="modified",
            agent_name="agent-b",
            session_id="session-456",
        )
        
        tracker.track_manual_change(
            file_path=str(test_file1),
            change_type="modified",
            agent_name="agent-a",
            session_id="session-123",
        )
        
        # Test filtering by file
        changes_by_file = tracker.get_changes(file_path=str(test_file1))
        assert len(changes_by_file) == 2
        assert all(c.file_path == str(test_file1) for c in changes_by_file)
        
        # Test filtering by agent
        changes_by_agent = tracker.get_changes(agent_name="agent-a")
        assert len(changes_by_agent) == 2
        assert all(c.agent_name == "agent-a" for c in changes_by_agent)
        
        # Test filtering by session
        changes_by_session = tracker.get_changes(session_id="session-456")
        assert len(changes_by_session) == 1
        assert all(c.session_id == "session-456" for c in changes_by_session)
        
        # Test filtering with limit
        all_changes = tracker.get_changes(limit=2)
        assert len(all_changes) == 2

    def test_get_agent_changes(self, tracker, temp_dir):
        """Test getting changes for a specific agent."""
        test_file = temp_dir / "test.txt"
        
        tracker.register_session(
            session_id="session-123",
            agent_name="agent-a",
        )
        
        tracker.track_manual_change(
            file_path=str(test_file),
            change_type="modified",
            agent_name="agent-a",
            session_id="session-123",
        )
        
        agent_changes = tracker.get_agent_changes("agent-a")
        assert len(agent_changes) == 1
        assert agent_changes[0].agent_name == "agent-a"

    def test_get_session_changes(self, tracker, temp_dir):
        """Test getting changes for a specific session."""
        test_file = temp_dir / "test.txt"
        
        tracker.register_session(
            session_id="session-123",
            agent_name="agent-a",
        )
        
        tracker.track_manual_change(
            file_path=str(test_file),
            change_type="modified",
            agent_name="agent-a",
            session_id="session-123",
        )
        
        session_changes = tracker.get_session_changes("session-123")
        assert len(session_changes) == 1
        assert session_changes[0].session_id == "session-123"

    def test_get_recent_changes(self, tracker, temp_dir):
        """Test getting recent changes."""
        test_file1 = temp_dir / "test1.txt"
        test_file2 = temp_dir / "test2.txt"
        
        tracker.register_session(
            session_id="session-123",
            agent_name="agent-a",
        )
        
        # Create multiple changes
        for i in range(5):
            test_file = temp_dir / f"test{i}.txt"
            tracker.track_manual_change(
                file_path=str(test_file),
                change_type="created",
                agent_name="agent-a",
                session_id="session-123",
            )
        
        recent_changes = tracker.get_recent_changes(limit=3)
        assert len(recent_changes) == 3

    def test_get_change_summary(self, tracker, temp_dir):
        """Test getting change summary."""
        tracker.register_session(
            session_id="session-123",
            agent_name="agent-a",
        )
        
        tracker.register_session(
            session_id="session-456",
            agent_name="agent-b",
        )
        
        # Create some changes
        for i in range(3):
            test_file = temp_dir / f"test{i}.txt"
            test_file.write_text(f"Content {i}")
            
            tracker.track_manual_change(
                file_path=str(test_file),
                change_type="created" if i == 0 else "modified",
                agent_name="agent-a" if i < 2 else "agent-b",
                session_id="session-123" if i < 2 else "session-456",
            )
        
        summary = tracker.get_change_summary()
        
        assert summary["total_changes"] == 3
        assert summary["unique_agents"] == 2
        assert summary["unique_sessions"] == 2
        assert summary["unique_files"] == 3
        assert "created" in summary["by_type"]
        assert "modified" in summary["by_type"]
        assert "agent-a" in summary["by_agent"]
        assert "agent-b" in summary["by_agent"]
        assert len(summary["recent_changes"]) <= 10

    def test_clear_history(self, tracker, temp_dir):
        """Test clearing change history."""
        test_file = temp_dir / "test.txt"
        
        tracker.track_manual_change(
            file_path=str(test_file),
            change_type="modified",
        )
        
        assert len(tracker.change_history) == 1
        
        tracker.clear_history()
        
        assert len(tracker.change_history) == 0

    def test_cleanup_old_sessions(self, tracker):
        """Test cleaning up old sessions."""
        # Register a session
        tracker.register_session(
            session_id="session-123",
            agent_name="test-agent",
        )
        
        # Manually set old activity time
        import datetime
        old_time = (datetime.datetime.now(datetime.timezone.utc) - 
                   datetime.timedelta(hours=25)).isoformat()
        tracker.active_sessions["session-123"].last_activity_at = old_time
        
        # Cleanup sessions older than 24 hours
        tracker.cleanup_old_sessions(max_age_hours=24)
        
        # Session should be removed
        assert "session-123" not in tracker.active_sessions

    def test_context_manager(self, temp_dir):
        """Test context manager usage."""
        config = FileChangeTrackerConfig(
            watch_paths=[str(temp_dir)],
            auto_start=True,
        )
        
        with FileChangeTracker(config) as tracker:
            assert tracker.config.auto_start is True
            # Watcher should be started
        
        # Watcher should be stopped after context exit
        # (This is hard to test without actually starting the watcher)

    def test_add_remove_watch_path(self, tracker):
        """Test adding and removing watch paths."""
        original_paths = tracker.config.watch_paths.copy()
        
        # Add a path
        tracker.add_watch_path("/tmp/test")
        assert "/tmp/test" in tracker.config.watch_paths
        
        # Remove the path
        tracker.remove_watch_path("/tmp/test")
        assert "/tmp/test" not in tracker.config.watch_paths
        
        # Original paths should remain
        assert tracker.config.watch_paths == original_paths


class TestGlobalFunctions:
    """Tests for global helper functions."""

    @pytest.fixture(autouse=True)
    def reset_global_tracker(self):
        """Reset the global tracker before each test."""
        # 清除全局追踪器
        import agentteam.tracker.file_tracker as ft_module
        ft_module._default_tracker = None
        yield

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_get_file_change_tracker(self):
        """Test getting the global file change tracker."""
        tracker1 = get_file_change_tracker()
        tracker2 = get_file_change_tracker()
        
        # Should be the same instance (singleton)
        assert tracker1 is tracker2

    def test_get_file_change_tracker_with_config(self):
        """Test getting tracker with custom config."""
        config = FileChangeTrackerConfig(
            team_name="custom-team",
            auto_start=False,
        )
        
        tracker = get_file_change_tracker(config)
        assert tracker.config.team_name == "custom-team"

        # Second call should ignore config (already initialized)
        config2 = FileChangeTrackerConfig(team_name="different-team")
        tracker2 = get_file_change_tracker(config2)
        assert tracker2.config.team_name == "custom-team"  # Not changed

    def test_track_file_change(self, temp_dir):
        """Test track_file_change helper function."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("Hello")
        
        change = track_file_change(
            file_path=str(test_file),
            agent_name="test-agent",
            session_id="session-123",
        )
        
        assert change.file_path == str(test_file)
        assert change.agent_name == "test-agent"
        assert change.session_id == "session-123"

    def test_get_recent_file_changes(self, temp_dir):
        """Test get_recent_file_changes helper function."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("Hello")
        
        # Track a change
        track_file_change(
            file_path=str(test_file),
            agent_name="test-agent",
            session_id="session-123",
        )
        
        changes = get_recent_file_changes(limit=10)
        
        assert len(changes) >= 1
        assert isinstance(changes[0], dict)
        assert "file_path" in changes[0]
        assert "agent_name" in changes[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])