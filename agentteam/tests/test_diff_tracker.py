"""Tests for DiffTracker module (P8)."""

import os
import tempfile
import gzip
from pathlib import Path

import pytest

from agentteam.tracker.diff_tracker import (
    DiffEntry,
    DiffStore,
    DiffTracker,
    FileSnapshot,
    create_diff_handler,
)


class TestDiffEntry:
    """Tests for DiffEntry model."""

    def test_entry_creation(self):
        """Test creating a diff entry."""
        entry = DiffEntry(
            path="/tmp/test.txt",
            change_type="modified",
        )
        assert entry.path == "/tmp/test.txt"
        assert entry.change_type == "modified"
        assert entry.id.startswith("diff_")

    def test_entry_with_diff_content(self):
        """Test entry with diff content."""
        entry = DiffEntry(
            path="/tmp/test.txt",
            change_type="modified",
            diff="--- a/test.txt\n+++ b/test.txt\n",
        )
        assert entry.diff is not None
        assert "--- a/" in entry.diff

    def test_entry_with_attribution(self):
        """Test entry with attribution fields."""
        entry = DiffEntry(
            path="/tmp/test.txt",
            change_type="modified",
            agent_name="test-agent",
            session_id="session-123",
            team_name="test-team",
        )
        assert entry.agent_name == "test-agent"
        assert entry.session_id == "session-123"
        assert entry.team_name == "test-team"

    def test_entry_statistics(self):
        """Test entry statistics."""
        entry = DiffEntry(
            path="/tmp/test.txt",
            change_type="modified",
            lines_added=10,
            lines_removed=5,
            lines_changed=3,
        )
        assert entry.lines_added == 10
        assert entry.lines_removed == 5
        assert entry.lines_changed == 3

    def test_entry_binary_flag(self):
        """Test binary file flag."""
        entry = DiffEntry(
            path="/tmp/image.png",
            change_type="created",
            is_binary=True,
        )
        assert entry.is_binary is True

    def test_entry_compressed_flag(self):
        """Test compressed flag."""
        entry = DiffEntry(
            path="/tmp/large.txt",
            change_type="modified",
            is_compressed=True,
        )
        assert entry.is_compressed is True

    def test_entry_auto_id_generation(self):
        """Test automatic ID generation."""
        entry1 = DiffEntry(path="/tmp/test1.txt", change_type="modified")
        entry2 = DiffEntry(path="/tmp/test2.txt", change_type="modified")
        assert entry1.id != entry2.id

    def test_entry_timestamp_auto(self):
        """Test automatic timestamp."""
        entry = DiffEntry(path="/tmp/test.txt", change_type="modified")
        assert entry.timestamp is not None
        assert "T" in entry.timestamp


class TestFileSnapshot:
    """Tests for FileSnapshot dataclass."""

    def test_snapshot_creation(self):
        """Test creating a file snapshot."""
        snapshot = FileSnapshot(
            path="/tmp/test.txt",
            content="Hello World",
        )
        assert snapshot.path == "/tmp/test.txt"
        assert snapshot.content == "Hello World"

    def test_snapshot_with_checksum(self):
        """Test snapshot with checksum."""
        snapshot = FileSnapshot(
            path="/tmp/test.txt",
            checksum="abc123",
        )
        assert snapshot.checksum == "abc123"

    def test_snapshot_binary_flag(self):
        """Test binary flag."""
        snapshot = FileSnapshot(
            path="/tmp/image.png",
            is_binary=True,
        )
        assert snapshot.is_binary is True

    def test_snapshot_size(self):
        """Test snapshot size."""
        snapshot = FileSnapshot(
            path="/tmp/test.txt",
            size=1024,
        )
        assert snapshot.size == 1024

    def test_snapshot_none_content(self):
        """Test snapshot with None content."""
        snapshot = FileSnapshot(
            path="/tmp/deleted.txt",
            content=None,
        )
        assert snapshot.content is None


class TestDiffStore:
    """Tests for DiffStore class."""

    def test_store_creation(self):
        """Test creating a diff store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Use environment variable to set data dir
            old_env = os.environ.get("AGENTTEAM_DATA_DIR")
            os.environ["AGENTTEAM_DATA_DIR"] = tmpdir
            try:
                store = DiffStore("test-team")
                assert store.team_name == "test-team"
            finally:
                if old_env:
                    os.environ["AGENTTEAM_DATA_DIR"] = old_env
                else:
                    os.environ.pop("AGENTTEAM_DATA_DIR", None)

    def test_store_save_and_load(self):
        """Test saving and loading diff entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_env = os.environ.get("AGENTTEAM_DATA_DIR")
            os.environ["AGENTTEAM_DATA_DIR"] = tmpdir
            try:
                store = DiffStore("test-team")

                entry = DiffEntry(
                    path="/tmp/test.txt",
                    change_type="modified",
                    diff="--- a/test.txt\n+++ b/test.txt\n@@ -1 +1 @@\n-old\n+new",
                )
                store.save_diff(entry)

                # Load back
                loaded = store.load_diff(entry.id)
                assert loaded is not None
                assert loaded.path == "/tmp/test.txt"
                assert loaded.change_type == "modified"
            finally:
                if old_env:
                    os.environ["AGENTTEAM_DATA_DIR"] = old_env
                else:
                    os.environ.pop("AGENTTEAM_DATA_DIR", None)

    def test_store_list_diffs(self):
        """Test listing diff entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_env = os.environ.get("AGENTTEAM_DATA_DIR")
            os.environ["AGENTTEAM_DATA_DIR"] = tmpdir
            try:
                store = DiffStore("test-team")

                entry1 = DiffEntry(path="/tmp/test1.txt", change_type="modified")
                entry2 = DiffEntry(path="/tmp/test2.txt", change_type="created")
                store.save_diff(entry1)
                store.save_diff(entry2)

                diffs = store.list_diffs()
                assert len(diffs) == 2
            finally:
                if old_env:
                    os.environ["AGENTTEAM_DATA_DIR"] = old_env
                else:
                    os.environ.pop("AGENTTEAM_DATA_DIR", None)

    def test_store_delete_diff(self):
        """Test deleting a diff entry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_env = os.environ.get("AGENTTEAM_DATA_DIR")
            os.environ["AGENTTEAM_DATA_DIR"] = tmpdir
            try:
                store = DiffStore("test-team")

                entry = DiffEntry(path="/tmp/test.txt", change_type="modified")
                store.save_diff(entry)
                assert len(store.list_diffs()) == 1

                store.delete_diff(entry.id)
                assert len(store.list_diffs()) == 0
            finally:
                if old_env:
                    os.environ["AGENTTEAM_DATA_DIR"] = old_env
                else:
                    os.environ.pop("AGENTTEAM_DATA_DIR", None)


class TestDiffTracker:
    """Tests for DiffTracker class."""

    def test_tracker_creation(self):
        """Test creating a diff tracker."""
        tracker = DiffTracker("test-team")
        assert tracker.team_name == "test-team"

    def test_tracker_get_snapshot(self):
        """Test getting a file snapshot."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Hello World")
            f.flush()
            f.close()  # Windows: must close before other processes can read

            tracker = DiffTracker("test-team")
            # take_snapshot reads the file and stores it
            snapshot = tracker.take_snapshot(f.name)
            assert snapshot is not None
            assert snapshot.path == f.name
            assert snapshot.content == "Hello World"

            Path(f.name).unlink()

    def test_tracker_get_snapshot_nonexistent(self):
        """Test getting snapshot for nonexistent file returns None."""
        tracker = DiffTracker("test-team")
        snapshot = tracker.get_snapshot("/tmp/nonexistent.txt")
        assert snapshot is None

    def test_tracker_track_change_created(self):
        """Test tracking created file change."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_env = os.environ.get("AGENTTEAM_DATA_DIR")
            os.environ["AGENTTEAM_DATA_DIR"] = tmpdir
            try:
                with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
                    f.write("New content")
                    f.flush()
                    f.close()  # Windows: must close before DiffTracker can read

                    tracker = DiffTracker("test-team")
                    entry = tracker.track_change(
                        path=f.name,
                        change_type="created",
                    )
                    assert entry is not None
                    assert entry.change_type == "created"

                    Path(f.name).unlink()
            finally:
                if old_env:
                    os.environ["AGENTTEAM_DATA_DIR"] = old_env
                else:
                    os.environ.pop("AGENTTEAM_DATA_DIR", None)

    def test_tracker_track_change_modified(self):
        """Test tracking modified file change."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_env = os.environ.get("AGENTTEAM_DATA_DIR")
            os.environ["AGENTTEAM_DATA_DIR"] = tmpdir
            try:
                # Create file first
                test_file = Path(tmpdir) / "test.txt"
                test_file.write_text("Old content")

                tracker = DiffTracker("test-team")
                # Take snapshot first
                tracker.take_snapshot(str(test_file))

                # Modify file
                test_file.write_text("New content")

                entry = tracker.track_change(
                    path=str(test_file),
                    change_type="modified",
                )
                assert entry is not None
                assert entry.change_type == "modified"
            finally:
                if old_env:
                    os.environ["AGENTTEAM_DATA_DIR"] = old_env
                else:
                    os.environ.pop("AGENTTEAM_DATA_DIR", None)

    def test_tracker_get_stats(self):
        """Test getting tracker statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_env = os.environ.get("AGENTTEAM_DATA_DIR")
            os.environ["AGENTTEAM_DATA_DIR"] = tmpdir
            try:
                tracker = DiffTracker("test-team")

                # Create some changes
                with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
                    f.write("Content")
                    f.flush()
                    f.close()  # Windows fix
                    tracker.track_change(path=f.name, change_type="created")
                    Path(f.name).unlink()

                stats = tracker.get_stats()
                assert stats is not None
                assert "totalEntries" in stats or "totalDiffs" in stats
            finally:
                if old_env:
                    os.environ["AGENTTEAM_DATA_DIR"] = old_env
                else:
                    os.environ.pop("AGENTTEAM_DATA_DIR", None)

    def test_tracker_take_snapshot(self):
        """Test taking a file snapshot."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Snapshot content")
            f.flush()
            f.close()  # Windows fix

            tracker = DiffTracker("test-team")
            tracker.take_snapshot(f.name)
            assert f.name in tracker._snapshots

            Path(f.name).unlink()


class TestDiffTrackerEdgeCases:
    """Edge case tests for DiffTracker."""

    def test_tracker_binary_file(self):
        """Test tracking binary file."""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".png", delete=False) as f:
            f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
            f.flush()
            f.close()  # Windows fix

            tracker = DiffTracker("test-team")
            entry = tracker.track_change(
                path=f.name,
                change_type="created",
            )
            # Binary files are skipped (returns None)
            assert entry is None

            Path(f.name).unlink()

    def test_tracker_empty_file(self):
        """Test tracking empty file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            # Empty file
            f.flush()
            f.close()  # Windows fix

            tracker = DiffTracker("test-team")
            entry = tracker.track_change(
                path=f.name,
                change_type="created",
            )
            assert entry is not None

            Path(f.name).unlink()

    def test_tracker_large_file_compression(self):
        """Test large file triggers compression."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_env = os.environ.get("AGENTTEAM_DATA_DIR")
            os.environ["AGENTTEAM_DATA_DIR"] = tmpdir
            try:
                store = DiffStore("test-team", compress_threshold=100)

                # Create large diff
                large_diff = "x" * 200
                entry = DiffEntry(
                    path="/tmp/large.txt",
                    change_type="modified",
                    diff=large_diff,
                )
                store.save_diff(entry)

                # Should be compressed
                assert entry.is_compressed is True
            finally:
                if old_env:
                    os.environ["AGENTTEAM_DATA_DIR"] = old_env
                else:
                    os.environ.pop("AGENTTEAM_DATA_DIR", None)

    def test_tracker_clear_snapshots(self):
        """Test clearing snapshots."""
        tracker = DiffTracker("test-team")
        tracker.clear_snapshots()
        assert len(tracker._snapshots) == 0


class TestCreateDiffHandler:
    """Tests for create_diff_handler factory."""

    def test_handler_creation(self):
        """Test creating diff handler."""
        handler = create_diff_handler("test-team")
        assert handler is not None
