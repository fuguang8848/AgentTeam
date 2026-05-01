"""File system watcher for monitoring file changes in real-time.

Uses watchdog library for cross-platform file system monitoring.
Provides event-driven notifications for file creations, modifications, and deletions.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)


class ChangeType(str, Enum):
    """Type of file system change."""

    created = "created"
    modified = "modified"
    deleted = "deleted"
    moved = "moved"


@dataclass
class WatchEvent:
    """A single file system change event."""

    path: str
    change_type: ChangeType
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    old_path: str | None = None  # For moved events
    is_directory: bool = False
    size: int | None = None
    checksum: str | None = None  # MD5 hash for content verification

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "path": self.path,
            "changeType": self.change_type.value,
            "timestamp": self.timestamp,
            "oldPath": self.old_path,
            "isDirectory": self.is_directory,
            "size": self.size,
            "checksum": self.checksum,
        }


# Type alias for event handlers
WatchEventHandler = Callable[[WatchEvent], None]


def _compute_checksum(path: str) -> str | None:
    """Compute MD5 checksum of a file."""
    try:
        import hashlib

        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except (OSError, IOError):
        return None


def _get_file_size(path: str) -> int | None:
    """Get file size in bytes."""
    try:
        return os.path.getsize(path)
    except OSError:
        return None


class FileWatcher:
    """Cross-platform file system watcher using watchdog.

    Monitors specified directories for file changes and notifies handlers.
    Supports debouncing to avoid duplicate events and filtering by patterns.
    """

    def __init__(
        self,
        watch_paths: list[str],
        handler: WatchEventHandler | None = None,
        ignore_patterns: list[str] | None = None,
        debounce_ms: int = 100,
    ):
        """Initialize the file watcher.

        Args:
            watch_paths: List of directory paths to watch
            handler: Optional handler for change events
            ignore_patterns: Glob patterns to ignore (e.g., ["*.pyc", "__pycache__/*"])
            debounce_ms: Debounce interval in milliseconds
        """
        self.watch_paths = [Path(p).resolve() for p in watch_paths]
        self.handler = handler
        self.ignore_patterns = ignore_patterns or [
            "*.pyc",
            "*.pyo",
            "__pycache__/*",
            ".git/*",
            "*.swp",
            "*.swo",
            ".DS_Store",
            "node_modules/*",
            "*.log",
        ]
        self.debounce_ms = debounce_ms

        self._observer: object | None = None
        self._running = False
        self._event_queue: list[WatchEvent] = []
        self._debounce_thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._last_event_times: dict[str, float] = {}

    def _should_ignore(self, path: str) -> bool:
        """Check if a path should be ignored based on patterns."""
        from fnmatch import fnmatch

        path_str = path.replace("\\", "/")
        for pattern in self.ignore_patterns:
            if fnmatch(path_str, pattern) or fnmatch(os.path.basename(path), pattern):
                return True
        return False

    def _debounce_event(self, event: WatchEvent) -> None:
        """Add event to debounce queue."""
        with self._lock:
            now = time.time()
            key = f"{event.path}:{event.change_type.value}"

            # Check if we've seen this event recently
            if key in self._last_event_times:
                elapsed_ms = (now - self._last_event_times[key]) * 1000
                if elapsed_ms < self.debounce_ms:
                    logger.debug(f"Debouncing duplicate event: {key}")
                    return

            self._last_event_times[key] = now
            self._event_queue.append(event)

    def _process_events(self) -> None:
        """Process queued events and call handler."""
        with self._lock:
            events = self._event_queue.copy()
            self._event_queue.clear()

        for event in events:
            if self.handler:
                try:
                    self.handler(event)
                except Exception as e:
                    logger.error(f"Error in watch event handler: {e}")

    def _on_file_created(self, path: str) -> None:
        """Handle file creation event."""
        if self._should_ignore(path):
            return

        event = WatchEvent(
            path=path,
            change_type=ChangeType.created,
            is_directory=os.path.isdir(path),
            size=_get_file_size(path),
            checksum=_compute_checksum(path) if os.path.isfile(path) else None,
        )
        self._debounce_event(event)

    def _on_file_modified(self, path: str) -> None:
        """Handle file modification event."""
        if self._should_ignore(path):
            return

        event = WatchEvent(
            path=path,
            change_type=ChangeType.modified,
            is_directory=os.path.isdir(path),
            size=_get_file_size(path),
            checksum=_compute_checksum(path) if os.path.isfile(path) else None,
        )
        self._debounce_event(event)

    def _on_file_deleted(self, path: str) -> None:
        """Handle file deletion event."""
        if self._should_ignore(path):
            return

        event = WatchEvent(
            path=path,
            change_type=ChangeType.deleted,
            is_directory=False,  # Can't check if deleted
        )
        self._debounce_event(event)

    def _on_file_moved(self, old_path: str, new_path: str) -> None:
        """Handle file move event."""
        if self._should_ignore(old_path) or self._should_ignore(new_path):
            return

        event = WatchEvent(
            path=new_path,
            change_type=ChangeType.moved,
            old_path=old_path,
            is_directory=os.path.isdir(new_path),
            size=_get_file_size(new_path),
            checksum=_compute_checksum(new_path) if os.path.isfile(new_path) else None,
        )
        self._debounce_event(event)

    def start(self) -> None:
        """Start watching the configured paths."""
        if self._running:
            logger.warning("FileWatcher is already running")
            return

        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent, FileDeletedEvent, FileMovedEvent

            class Handler(FileSystemEventHandler):
                def __init__(self, watcher: FileWatcher):
                    self.watcher = watcher

                def on_created(self, event):
                    if not event.is_directory:
                        self.watcher._on_file_created(event.src_path)

                def on_modified(self, event):
                    if not event.is_directory:
                        self.watcher._on_file_modified(event.src_path)

                def on_deleted(self, event):
                    if not event.is_directory:
                        self.watcher._on_file_deleted(event.src_path)

                def on_moved(self, event):
                    if not event.is_directory:
                        self.watcher._on_file_moved(event.src_path, event.dest_path)

            self._observer = Observer()
            handler = Handler(self)

            for watch_path in self.watch_paths:
                if watch_path.exists():
                    self._observer.schedule(handler, str(watch_path), recursive=True)
                    logger.info(f"Watching path: {watch_path}")
                else:
                    logger.warning(f"Watch path does not exist: {watch_path}")

            self._observer.start()
            self._running = True
            logger.info(f"FileWatcher started, monitoring {len(self.watch_paths)} paths")

        except ImportError:
            logger.warning("watchdog library not installed, using polling fallback")
            self._start_polling()

    def _start_polling(self) -> None:
        """Fallback polling-based watching when watchdog is not available."""

        def poll_loop():
            file_states: dict[str, tuple[float, int, str | None]] = {}

            # Initial scan
            for watch_path in self.watch_paths:
                if watch_path.exists():
                    for root, _dirs, files in os.walk(str(watch_path)):
                        for f in files:
                            path = os.path.join(root, f)
                            if not self._should_ignore(path):
                                mtime = os.path.getmtime(path)
                                size = _get_file_size(path)
                                checksum = _compute_checksum(path)
                                file_states[path] = (mtime, size, checksum)

            while self._running:
                time.sleep(1.0)  # Poll interval

                for watch_path in self.watch_paths:
                    if not watch_path.exists():
                        continue

                    current_files = set()
                    for root, _dirs, files in os.walk(str(watch_path)):
                        for f in files:
                            path = os.path.join(root, f)
                            if self._should_ignore(path):
                                continue

                            current_files.add(path)
                            mtime = os.path.getmtime(path)
                            size = _get_file_size(path)
                            checksum = _compute_checksum(path)

                            if path not in file_states:
                                # New file
                                self._on_file_created(path)
                            else:
                                old_mtime, old_size, old_checksum = file_states[path]
                                if mtime > old_mtime or checksum != old_checksum:
                                    # Modified file
                                    self._on_file_modified(path)

                            file_states[path] = (mtime, size, checksum)

                    # Check for deleted files
                    deleted = set(file_states.keys()) - current_files
                    for path in deleted:
                        self._on_file_deleted(path)
                        del file_states[path]

                self._process_events()

        self._running = True
        self._debounce_thread = threading.Thread(target=poll_loop, daemon=True)
        self._debounce_thread.start()
        logger.info("FileWatcher started in polling mode")

    def stop(self) -> None:
        """Stop watching."""
        self._running = False

        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5.0)
            self._observer = None
            logger.info("FileWatcher stopped (observer)")

        if self._debounce_thread and self._debounce_thread.is_alive():
            self._debounce_thread.join(timeout=2.0)
            logger.info("FileWatcher stopped (polling)")

    def add_handler(self, handler: WatchEventHandler) -> None:
        """Add an event handler."""
        old_handler = self.handler
        if old_handler is None:
            self.handler = handler
        else:
            # Chain handlers
            def chained(event: WatchEvent) -> None:
                old_handler(event)
                handler(event)

            self.handler = chained

    def get_recent_events(self, limit: int = 100) -> list[WatchEvent]:
        """Get recent events from the queue (for debugging)."""
        with self._lock:
            return list(self._event_queue[-limit:])

    def __enter__(self) -> "FileWatcher":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()


def watch_directory(
    path: str,
    handler: WatchEventHandler,
    ignore_patterns: list[str] | None = None,
) -> FileWatcher:
    """Convenience function to create and start a watcher for a single directory.

    Args:
        path: Directory path to watch
        handler: Event handler function
        ignore_patterns: Optional patterns to ignore

    Returns:
        Running FileWatcher instance
    """
    watcher = FileWatcher(
        watch_paths=[path],
        handler=handler,
        ignore_patterns=ignore_patterns,
    )
    watcher.start()
    return watcher