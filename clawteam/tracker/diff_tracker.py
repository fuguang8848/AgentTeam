"""Diff generation and storage for tracking file content changes.

This module provides:
- Unified diff generation for text files
- Diff storage with compression for large changes
- Diff retrieval and reconstruction
- Integration with change attribution
"""

from __future__ import annotations

import difflib
import gzip
import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from clawteam.fileutil import atomic_write_text
from clawteam.paths import ensure_within_root, validate_identifier
from clawteam.team.models import get_data_dir

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _diff_root(team_name: str) -> Path:
    """Get the diff storage directory for a team."""
    d = ensure_within_root(get_data_dir() / "diffs", validate_identifier(team_name, "team name"))
    d.mkdir(parents=True, exist_ok=True)
    return d


class DiffEntry(BaseModel):
    """A single diff entry with metadata."""

    model_config = {"populate_by_name": True}

    id: str = Field(default_factory=lambda: f"diff_{int(time.time() * 1000)}_{os.urandom(4).hex()}")
    path: str
    timestamp: str = Field(default_factory=_now_iso)
    change_type: str = "modified"  # created, modified, deleted

    # Attribution
    agent_name: str = ""
    session_id: str = ""
    team_name: str = ""

    # Diff content
    diff: str = ""
    old_content: str | None = None  # For created files, this is None
    new_content: str | None = None  # For deleted files, this is None
    is_binary: bool = False
    is_compressed: bool = False

    # Statistics
    lines_added: int = 0
    lines_removed: int = 0
    lines_changed: int = 0

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)


@dataclass
class FileSnapshot:
    """A snapshot of file content at a point in time."""

    path: str
    content: str | None = None
    checksum: str | None = None
    timestamp: str = field(default_factory=_now_iso)
    size: int | None = None
    is_binary: bool = False


class DiffStore:
    """Storage backend for diff entries.

    Supports:
    - JSON storage for small diffs
    - Gzip compression for large diffs
    - Binary file detection and handling
    """

    def __init__(self, team_name: str, compress_threshold: int = 10000):
        """Initialize the diff store.

        Args:
            team_name: Name of the team
            compress_threshold: Size threshold for compression (bytes)
        """
        self.team_name = team_name
        self.compress_threshold = compress_threshold
        self._root = _diff_root(team_name)
        self._lock = threading.RLock()

    def _is_binary(self, content: bytes) -> bool:
        """Check if content is binary (non-text)."""
        # Check for null bytes (common in binary files)
        if b'\x00' in content[:8192]:
            return True

        # Check for high ratio of non-printable characters
        try:
            text = content[:8192].decode('utf-8')
            if len(text) == 0:
                return False  # Empty content is not binary
            non_printable = sum(1 for c in text if not c.isprintable() and c not in '\n\r\t')
            if non_printable / len(text) > 0.3:
                return True
        except UnicodeDecodeError:
            return True

        return False

    def _compress(self, content: str) -> bytes:
        """Compress content using gzip."""
        return gzip.compress(content.encode('utf-8'))

    def _decompress(self, data: bytes) -> str:
        """Decompress gzip content."""
        return gzip.decompress(data).decode('utf-8')

    def save_diff(self, entry: DiffEntry) -> str:
        """Save a diff entry to storage.

        Args:
            entry: The diff entry to save

        Returns:
            The ID of the saved entry
        """
        with self._lock:
            # Determine if we should compress
            if len(entry.diff) > self.compress_threshold:
                entry.is_compressed = True
                diff_data = self._compress(entry.diff)
            else:
                diff_data = entry.diff.encode('utf-8')

            # Save to file
            path = self._root / f"{entry.id}.json"
            data = entry.model_dump(by_alias=True)

            if entry.is_compressed:
                # Save compressed diff separately
                diff_path = self._root / f"{entry.id}.diff.gz"
                with open(diff_path, 'wb') as f:
                    f.write(diff_data)
                data['diff'] = None  # Don't include in JSON
                data['diffFile'] = f"{entry.id}.diff.gz"

            atomic_write_text(path, json.dumps(data, indent=2, ensure_ascii=False))
            logger.debug(f"Saved diff entry: {entry.id}")

            return entry.id

    def load_diff(self, diff_id: str) -> DiffEntry | None:
        """Load a diff entry by ID.

        Args:
            diff_id: The diff entry ID

        Returns:
            The loaded DiffEntry or None if not found
        """
        with self._lock:
            path = self._root / f"{diff_id}.json"
            if not path.exists():
                return None

            try:
                data = json.loads(path.read_text(encoding='utf-8'))
                entry = DiffEntry.model_validate(data)

                # Load compressed diff if needed
                if entry.is_compressed and 'diffFile' in data:
                    diff_path = self._root / data['diffFile']
                    if diff_path.exists():
                        with open(diff_path, 'rb') as f:
                            entry.diff = self._decompress(f.read())

                return entry
            except (json.JSONDecodeError, OSError, gzip.BadGzipFile) as e:
                logger.error(f"Failed to load diff {diff_id}: {e}")
                return None

    def list_diffs(
        self,
        path_prefix: str | None = None,
        agent_name: str | None = None,
        since: str | None = None,
        limit: int = 100,
    ) -> list[DiffEntry]:
        """List diff entries with optional filtering.

        Args:
            path_prefix: Filter by path prefix
            agent_name: Filter by agent name
            since: Filter by timestamp (ISO format)
            limit: Maximum number of entries

        Returns:
            List of matching DiffEntries
        """
        entries = []

        with self._lock:
            for file in self._root.glob("*.json"):
                try:
                    entry = self.load_diff(file.stem)
                    if entry:
                        entries.append(entry)
                except Exception as e:
                    logger.error(f"Failed to load diff from {file}: {e}")

        # Apply filters
        if path_prefix:
            entries = [e for e in entries if e.path.startswith(path_prefix)]
        if agent_name:
            entries = [e for e in entries if e.agent_name == agent_name]
        if since:
            entries = [e for e in entries if e.timestamp >= since]

        # Sort by timestamp descending
        entries.sort(key=lambda e: e.timestamp, reverse=True)

        return entries[:limit]

    def delete_diff(self, diff_id: str) -> bool:
        """Delete a diff entry.

        Args:
            diff_id: The diff entry ID

        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            path = self._root / f"{diff_id}.json"
            diff_path = self._root / f"{diff_id}.diff.gz"

            deleted = False
            if path.exists():
                path.unlink()
                deleted = True

            if diff_path.exists():
                diff_path.unlink()

            return deleted

    def get_stats(self) -> dict[str, Any]:
        """Get storage statistics."""
        with self._lock:
            total_size = 0
            total_entries = 0
            compressed_entries = 0

            for file in self._root.glob("*.json"):
                total_entries += 1
                total_size += file.stat().st_size

            for file in self._root.glob("*.diff.gz"):
                total_size += file.stat().st_size
                compressed_entries += 1

            return {
                "totalEntries": total_entries,
                "compressedEntries": compressed_entries,
                "totalSizeBytes": total_size,
                "totalSizeMB": round(total_size / (1024 * 1024), 2),
            }


class DiffTracker:
    """Tracks file content changes and generates diffs.

    Maintains a cache of file snapshots for efficient diff generation.
    Integrates with the change attribution system.
    """

    def __init__(self, team_name: str, store: DiffStore | None = None):
        """Initialize the diff tracker.

        Args:
            team_name: Name of the team
            store: Optional DiffStore instance (creates default if None)
        """
        self.team_name = team_name
        self.store = store or DiffStore(team_name)
        self._snapshots: dict[str, FileSnapshot] = {}
        self._lock = threading.Lock()

    def _read_file(self, path: str) -> tuple[str | None, bool]:
        """Read file content, detecting binary files.

        Args:
            path: File path to read

        Returns:
            Tuple of (content, is_binary)
        """
        try:
            with open(path, 'rb') as f:
                content_bytes = f.read()

            if self.store._is_binary(content_bytes):
                return None, True

            return content_bytes.decode('utf-8'), False
        except (OSError, IOError, UnicodeDecodeError) as e:
            logger.debug(f"Could not read file {path}: {e}")
            return None, True

    def _compute_checksum(self, content: str) -> str:
        """Compute MD5 checksum of content."""
        import hashlib
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def _generate_diff(self, old_content: str | None, new_content: str | None, path: str) -> str:
        """Generate a unified diff between old and new content.

        Args:
            old_content: Previous content (None for new files)
            new_content: Current content (None for deleted files)
            path: File path for diff header

        Returns:
            Unified diff string
        """
        if old_content is None and new_content is None:
            return ""

        old_lines = old_content.splitlines(keepends=True) if old_content else []
        new_lines = new_content.splitlines(keepends=True) if new_content else []

        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{path}" if old_content else f"/dev/null",
            tofile=f"b/{path}" if new_content else f"/dev/null",
            lineterm='',
        )

        return ''.join(diff)

    def _count_diff_stats(self, diff: str) -> tuple[int, int, int]:
        """Count lines added, removed, and changed in a diff.

        Args:
            diff: Unified diff string

        Returns:
            Tuple of (lines_added, lines_removed, lines_changed)
        """
        added = 0
        removed = 0

        for line in diff.splitlines():
            if line.startswith('+') and not line.startswith('+++'):
                added += 1
            elif line.startswith('-') and not line.startswith('---'):
                removed += 1

        # Approximate changed lines as min of added/removed
        changed = min(added, removed)
        added -= changed
        removed -= changed

        return added, removed, changed

    def take_snapshot(self, path: str) -> FileSnapshot:
        """Take a snapshot of a file's current content.

        Args:
            path: File path to snapshot

        Returns:
            FileSnapshot with current content
        """
        content, is_binary = self._read_file(path)
        size = os.path.getsize(path) if os.path.exists(path) else None

        snapshot = FileSnapshot(
            path=path,
            content=content,
            checksum=self._compute_checksum(content) if content else None,
            size=size,
            is_binary=is_binary,
        )

        with self._lock:
            self._snapshots[path] = snapshot

        return snapshot

    def track_change(
        self,
        path: str,
        change_type: str,
        agent_name: str = "",
        session_id: str = "",
    ) -> DiffEntry | None:
        """Track a file change and generate a diff.

        Args:
            path: File path that changed
            change_type: Type of change (created, modified, deleted)
            agent_name: Agent that made the change
            session_id: Session ID of the agent

        Returns:
            DiffEntry if diff was generated, None for binary files
        """
        # Get old snapshot
        with self._lock:
            old_snapshot = self._snapshots.get(path)

        # Get new content
        if change_type == "deleted":
            new_content = None
            is_binary = old_snapshot.is_binary if old_snapshot else False
        else:
            new_content, is_binary = self._read_file(path)

        # Skip binary files
        if is_binary:
            logger.debug(f"Skipping binary file: {path}")
            return None

        # Generate diff
        old_content = old_snapshot.content if old_snapshot else None
        diff = self._generate_diff(old_content, new_content, path)

        # Count stats
        lines_added, lines_removed, lines_changed = self._count_diff_stats(diff)

        # Create entry
        entry = DiffEntry(
            path=path,
            change_type=change_type,
            agent_name=agent_name,
            session_id=session_id,
            team_name=self.team_name,
            diff=diff,
            old_content=old_content[:10000] if old_content else None,  # Truncate for storage
            new_content=new_content[:10000] if new_content else None,
            is_binary=is_binary,
            lines_added=lines_added,
            lines_removed=lines_removed,
            lines_changed=lines_changed,
        )

        # Save to store
        self.store.save_diff(entry)

        # Update snapshot
        if change_type != "deleted":
            self.take_snapshot(path)
        else:
            with self._lock:
                if path in self._snapshots:
                    del self._snapshots[path]

        return entry

    def get_diff(self, diff_id: str) -> DiffEntry | None:
        """Get a diff entry by ID."""
        return self.store.load_diff(diff_id)

    def get_diffs_for_path(self, path: str, limit: int = 50) -> list[DiffEntry]:
        """Get all diffs for a specific path."""
        return self.store.list_diffs(path_prefix=path, limit=limit)

    def get_diffs_for_agent(self, agent_name: str, limit: int = 50) -> list[DiffEntry]:
        """Get all diffs made by a specific agent."""
        return self.store.list_diffs(agent_name=agent_name, limit=limit)

    def reconstruct_file(self, path: str, timestamp: str | None = None) -> str | None:
        """Reconstruct file content at a specific point in time.

        Args:
            path: File path to reconstruct
            timestamp: Target timestamp (ISO format), None for latest

        Returns:
            Reconstructed content or None if not possible
        """
        diffs = self.get_diffs_for_path(path)
        if not diffs:
            return None

        # Sort by timestamp ascending (oldest first)
        diffs.sort(key=lambda d: d.timestamp)

        # Start from the oldest known state
        content = diffs[0].old_content or ""

        # Apply diffs in order
        for diff_entry in diffs:
            if timestamp and diff_entry.timestamp > timestamp:
                break

            # For simplicity, use the stored new_content if available
            if diff_entry.new_content:
                content = diff_entry.new_content

        return content

    def get_change_summary(self, agent_name: str | None = None, since: str | None = None) -> dict[str, Any]:
        """Get a summary of changes.

        Args:
            agent_name: Optional filter by agent
            since: Optional filter by timestamp

        Returns:
            Summary dict with statistics
        """
        diffs = self.store.list_diffs(agent_name=agent_name, since=since, limit=1000)

        total_added = sum(d.lines_added for d in diffs)
        total_removed = sum(d.lines_removed for d in diffs)
        total_changed = sum(d.lines_changed for d in diffs)

        files_modified = set(d.path for d in diffs)

        return {
            "totalDiffs": len(diffs),
            "totalLinesAdded": total_added,
            "totalLinesRemoved": total_removed,
            "totalLinesChanged": total_changed,
            "filesModified": len(files_modified),
            "filesModifiedList": sorted(files_modified)[:20],  # Top 20
        }

    def clear_snapshots(self) -> None:
        """Clear the snapshot cache."""
        with self._lock:
            self._snapshots.clear()

    def get_snapshot(self, path: str) -> FileSnapshot | None:
        """Get an existing snapshot for a file path.

        Args:
            path: File path to look up

        Returns:
            FileSnapshot if found, None otherwise
        """
        with self._lock:
            return self._snapshots.get(path)

    def get_stats(self) -> dict[str, Any]:
        """Get diff tracker statistics (delegates to store)."""
        return self.store.get_stats()


def create_diff_handler(
    tracker: DiffTracker,
    agent_name: str = "",
    session_id: str = "",
) -> Callable[[WatchEvent], None]:
    """Create a file watcher handler that generates diffs.

    Args:
        tracker: The DiffTracker instance
        agent_name: Default agent name for attribution
        session_id: Default session ID for attribution

    Returns:
        A handler function for FileWatcher
    """
    def handler(event: WatchEvent) -> None:
        # Skip directory events
        if event.is_directory:
            return

        # Map change type
        change_type = event.change_type.value

        # Track the change
        entry = tracker.track_change(
            path=event.path,
            change_type=change_type,
            agent_name=agent_name,
            session_id=session_id,
        )

        if entry:
            logger.info(
                f"Generated diff for {event.path}: "
                f"+{entry.lines_added} -{entry.lines_removed} ~{entry.lines_changed}"
            )

    return handler


from typing import Callable