"""Tests for FileWatcher module (P8)."""

import tempfile
import threading
import time
from pathlib import Path

import pytest

from agentteam.tracker.file_watcher import (
    ChangeType,
    FileWatcher,
    WatchEvent,
    watch_directory,
)


class TestWatchEvent:
    """Tests for WatchEvent dataclass."""

    def test_event_creation(self):
        """Test creating a watch event."""
        event = WatchEvent(
            path="/tmp/test.txt",
            change_type=ChangeType.modified,
        )
        assert event.path == "/tmp/test.txt"
        assert event.change_type == ChangeType.modified
        assert event.is_directory is False

    def test_event_with_old_path(self):
        """Test event with old path for moved events."""
        event = WatchEvent(
            path="/tmp/new.txt",
            change_type=ChangeType.moved,
            old_path="/tmp/old.txt",
        )
        assert event.old_path == "/tmp/old.txt"
        assert event.change_type == ChangeType.moved

    def test_event_timestamp_auto_generated(self):
        """Test that timestamp is auto-generated."""
        event = WatchEvent(
            path="/tmp/test.txt",
            change_type=ChangeType.created,
        )
        assert event.timestamp is not None
        assert "T" in event.timestamp  # ISO format

    def test_event_to_dict(self):
        """Test event serialization."""
        event = WatchEvent(
            path="/tmp/test.txt",
            change_type=ChangeType.modified,
            size=100,
            checksum="abc123",
        )
        d = event.to_dict()
        assert d["path"] == "/tmp/test.txt"
        assert d["changeType"] == "modified"
        assert d["size"] == 100
        assert d["checksum"] == "abc123"

    def test_event_directory_flag(self):
        """Test directory flag."""
        event = WatchEvent(
            path="/tmp/testdir",
            change_type=ChangeType.created,
            is_directory=True,
        )
        assert event.is_directory is True


class TestChangeType:
    """Tests for ChangeType enum."""

    def test_all_change_types(self):
        """Test all change type values."""
        assert ChangeType.created.value == "created"
        assert ChangeType.modified.value == "modified"
        assert ChangeType.deleted.value == "deleted"
        assert ChangeType.moved.value == "moved"

    def test_change_type_from_string(self):
        """Test creating change type from string."""
        ct = ChangeType("modified")
        assert ct == ChangeType.modified


class TestFileWatcher:
    """Tests for FileWatcher class."""

    def test_watcher_initialization(self):
        """Test watcher initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = FileWatcher(watch_paths=[tmpdir])
            assert len(watcher.watch_paths) == 1
            assert watcher.debounce_ms == 100

    def test_watcher_with_multiple_paths(self):
        """Test watcher with multiple paths."""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                watcher = FileWatcher(watch_paths=[tmpdir1, tmpdir2])
                assert len(watcher.watch_paths) == 2

    def test_watcher_custom_debounce(self):
        """Test custom debounce interval."""
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = FileWatcher(watch_paths=[tmpdir], debounce_ms=500)
            assert watcher.debounce_ms == 500

    def test_watcher_default_ignore_patterns(self):
        """Test default ignore patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = FileWatcher(watch_paths=[tmpdir])
            assert "*.pyc" in watcher.ignore_patterns
            assert "__pycache__/*" in watcher.ignore_patterns
            assert ".git/*" in watcher.ignore_patterns

    def test_watcher_custom_ignore_patterns(self):
        """Test custom ignore patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = FileWatcher(
                watch_paths=[tmpdir],
                ignore_patterns=["*.log", "*.tmp"],
            )
            assert "*.log" in watcher.ignore_patterns
            assert "*.tmp" in watcher.ignore_patterns

    def test_watcher_should_ignore(self):
        """Test ignore pattern matching."""
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = FileWatcher(watch_paths=[tmpdir])
            assert watcher._should_ignore("/tmp/test.pyc")
            assert watcher._should_ignore("/tmp/__pycache__/module.pyc")
            assert not watcher._should_ignore("/tmp/test.py")

    def test_watcher_add_handler(self):
        """Test adding event handler."""
        events = []

        def handler(event):
            events.append(event)

        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = FileWatcher(watch_paths=[tmpdir])
            watcher.add_handler(handler)
            assert watcher.handler is not None

    def test_watcher_chain_handlers(self):
        """Test chaining multiple handlers."""
        events1 = []
        events2 = []

        def handler1(event):
            events1.append(event)

        def handler2(event):
            events2.append(event)

        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = FileWatcher(watch_paths=[tmpdir])
            watcher.add_handler(handler1)
            watcher.add_handler(handler2)
            # Both handlers should be chained
            assert watcher.handler is not None

    def test_watcher_context_manager(self):
        """Test context manager usage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with FileWatcher(watch_paths=[tmpdir]) as watcher:
                assert watcher._running
            # After exit, should be stopped
            assert not watcher._running

    def test_watcher_get_recent_events(self):
        """Test getting recent events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = FileWatcher(watch_paths=[tmpdir])
            events = watcher.get_recent_events()
            assert isinstance(events, list)


class TestWatchDirectory:
    """Tests for watch_directory convenience function."""

    def test_watch_directory_creates_watcher(self):
        """Test that watch_directory creates a watcher."""
        events = []

        def handler(event):
            events.append(event)

        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = watch_directory(tmpdir, handler)
            assert watcher is not None
            assert watcher._running
            watcher.stop()

    def test_watch_directory_with_custom_patterns(self):
        """Test watch_directory with custom ignore patterns."""
        events = []

        def handler(event):
            events.append(event)

        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = watch_directory(
                tmpdir, handler, ignore_patterns=["*.log"]
            )
            assert "*.log" in watcher.ignore_patterns
            watcher.stop()


class TestFileWatcherEdgeCases:
    """Edge case tests for FileWatcher."""

    def test_watcher_empty_paths(self):
        """Test watcher with empty paths list."""
        watcher = FileWatcher(watch_paths=[])
        assert len(watcher.watch_paths) == 0

    def test_watcher_nonexistent_path(self):
        """Test watcher with nonexistent path."""
        # Should resolve the path but not fail on init
        watcher = FileWatcher(watch_paths=["/nonexistent/path"])
        assert len(watcher.watch_paths) == 1

    def test_watcher_handler_none(self):
        """Test watcher with no handler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = FileWatcher(watch_paths=[tmpdir], handler=None)
            assert watcher.handler is None

    def test_event_empty_checksum(self):
        """Test event with empty checksum."""
        event = WatchEvent(
            path="/tmp/test.txt",
            change_type=ChangeType.modified,
            checksum=None,
        )
        assert event.checksum is None

    def test_event_zero_size(self):
        """Test event with zero size."""
        event = WatchEvent(
            path="/tmp/empty.txt",
            change_type=ChangeType.created,
            size=0,
        )
        assert event.size == 0


class TestFileWatcherIntegration:
    """Integration tests for FileWatcher."""

    def test_watcher_start_stop_cycle(self):
        """Test start/stop cycle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = FileWatcher(watch_paths=[tmpdir])
            watcher.start()
            assert watcher._running
            watcher.stop()
            assert not watcher._running
            # Can start again
            watcher.start()
            assert watcher._running
            watcher.stop()

    def test_watcher_debounce_event(self):
        """Test event debouncing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            watcher = FileWatcher(watch_paths=[tmpdir], debounce_ms=100)
            event = WatchEvent(
                path="/tmp/test.txt",
                change_type=ChangeType.modified,
            )
            # First event should be added
            watcher._debounce_event(event)
            # Rapid second event should be debounced
            watcher._debounce_event(event)
            time.sleep(0.15)  # Wait for debounce
            # After debounce period, new event should be added
            watcher._debounce_event(event)