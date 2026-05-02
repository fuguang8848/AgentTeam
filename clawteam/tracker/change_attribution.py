"""Change attribution for tracking which agent made which file changes.

This module provides:
- Attribution of file changes to specific agents/sessions
- Change record storage and retrieval
- Integration with the file watcher for real-time attribution
"""

from __future__ import annotations

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
from clawteam.tracker.file_watcher import WatchEvent, ChangeType

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _attribution_root(team_name: str) -> Path:
    """Get the attribution data directory for a team."""
    d = ensure_within_root(
        get_data_dir() / "attribution", validate_identifier(team_name, "team name")
    )
    d.mkdir(parents=True, exist_ok=True)
    return d


class ChangeRecord(BaseModel):
    """A single change record with attribution."""

    model_config = {"populate_by_name": True}

    id: str = Field(default_factory=lambda: f"chg_{int(time.time() * 1000)}_{os.urandom(4).hex()}")
    path: str
    change_type: str  # created, modified, deleted, moved
    timestamp: str = Field(default_factory=_now_iso)
    old_path: str | None = None
    is_directory: bool = False
    size: int | None = None
    checksum: str | None = None

    # Attribution fields
    agent_name: str = ""
    session_id: str = ""
    team_name: str = ""
    task_id: str = ""

    # Content diff (for text files)
    diff: str | None = None

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)


class AttributionResult(BaseModel):
    """Result of attributing a change to an agent."""

    model_config = {"populate_by_name": True}

    success: bool
    agent_name: str | None = None
    session_id: str | None = None
    confidence: float = 0.0  # 0.0 - 1.0
    method: str = ""  # "explicit", "inferred", "unknown"
    reason: str = ""


class ActiveSession(BaseModel):
    """Information about an active agent session."""

    model_config = {"populate_by_name": True}

    session_id: str
    agent_name: str
    team_name: str
    task_id: str = ""
    working_directory: str = ""
    started_at: str = Field(default_factory=_now_iso)
    last_activity_at: str = Field(default_factory=_now_iso)
    files_modified: list[str] = Field(default_factory=list)
    status: str = "active"


class ChangeAttributor:
    """Attribution engine for tracking which agent made which changes.

    Uses multiple strategies for attribution:
    1. Explicit registration: Agent explicitly registers files it's working on
    2. Session tracking: Active sessions claim changes in their working directory
    3. Time-based inference: Match change time to session activity time
    4. File ownership: Track file ownership based on first modification
    """

    def __init__(self, team_name: str, buffer_size: int = 1000):
        """Initialize the attributor for a team.

        Args:
            team_name: Name of the team
            buffer_size: Maximum number of change records to keep in memory
        """
        self.team_name = team_name
        self._active_sessions: dict[str, ActiveSession] = {}
        self._file_claims: dict[str, str] = {}  # path -> session_id
        self._lock = threading.Lock()
        self._change_buffer: list[ChangeRecord] = []
        self._buffer_size = buffer_size

    def register_session(
        self,
        session_id: str,
        agent_name: str,
        working_directory: str = "",
        task_id: str = "",
    ) -> None:
        """Register an active agent session.

        Args:
            session_id: Unique session identifier
            agent_name: Name of the agent
            working_directory: Directory the agent is working in
            task_id: Optional task ID the agent is working on
        """
        with self._lock:
            session = ActiveSession(
                session_id=session_id,
                agent_name=agent_name,
                team_name=self.team_name,
                working_directory=working_directory,
                task_id=task_id,
            )
            self._active_sessions[session_id] = session
            logger.info(f"Registered session: {agent_name} ({session_id})")

    def unregister_session(self, session_id: str) -> None:
        """Unregister a session when it ends."""
        with self._lock:
            if session_id in self._active_sessions:
                session = self._active_sessions.pop(session_id)
                # Clear file claims for this session
                self._file_claims = {p: s for p, s in self._file_claims.items() if s != session_id}
                logger.info(f"Unregistered session: {session.agent_name} ({session_id})")

    def claim_file(self, session_id: str, file_path: str) -> None:
        """Explicitly claim a file for a session.

        Args:
            session_id: Session claiming the file
            file_path: Path to the file being claimed
        """
        with self._lock:
            if session_id in self._active_sessions:
                self._file_claims[file_path] = session_id
                session = self._active_sessions[session_id]
                if file_path not in session.files_modified:
                    session.files_modified.append(file_path)
                logger.debug(f"Session {session_id} claimed file: {file_path}")

    def release_file(self, file_path: str) -> None:
        """Release a file claim.

        Args:
            file_path: Path to the file to release
        """
        with self._lock:
            if file_path in self._file_claims:
                session_id = self._file_claims.pop(file_path)
                if session_id in self._active_sessions:
                    session = self._active_sessions[session_id]
                    if file_path in session.files_modified:
                        session.files_modified.remove(file_path)
                logger.debug(f"Released file claim: {file_path}")

    def get_session_files(self, session_id: str) -> list[str]:
        """Get all files claimed by a session.

        Args:
            session_id: Session ID to look up

        Returns:
            List of file paths claimed by the session
        """
        with self._lock:
            session = self._active_sessions.get(session_id)
            if session:
                return list(session.files_modified)
            return []

    def update_session_activity(self, session_id: str) -> None:
        """Update the last activity time for a session."""
        with self._lock:
            if session_id in self._active_sessions:
                self._active_sessions[session_id].last_activity_at = _now_iso()

    def attribute_change(self, event: WatchEvent) -> AttributionResult:
        """Attribute a file change to an agent.

        Uses multiple strategies in order of confidence:
        1. Explicit claim: File was explicitly claimed by a session
        2. Working directory: Change is in a session's working directory
        3. Recent activity: Session was recently active
        4. Unknown: Cannot attribute

        Args:
            event: The file change event

        Returns:
            AttributionResult with attribution information
        """
        with self._lock:
            path = event.path

            # Strategy 1: Check explicit claims
            if path in self._file_claims:
                session_id = self._file_claims[path]
                if session_id in self._active_sessions:
                    session = self._active_sessions[session_id]
                    return AttributionResult(
                        success=True,
                        agent_name=session.agent_name,
                        session_id=session_id,
                        confidence=1.0,
                        method="explicit",
                        reason=f"File explicitly claimed by session {session_id}",
                    )

            # Strategy 2: Check working directory matches
            for session_id, session in self._active_sessions.items():
                if session.working_directory:
                    work_dir = Path(session.working_directory).resolve()
                    try:
                        file_path = Path(path).resolve()
                        if str(file_path).startswith(str(work_dir)):
                            return AttributionResult(
                                success=True,
                                agent_name=session.agent_name,
                                session_id=session_id,
                                confidence=0.9,
                                method="inferred",
                                reason=f"File in working directory of session {session_id}",
                            )
                    except (OSError, ValueError):
                        pass

            # Strategy 3: Check recent activity (within 5 seconds)
            recent_threshold = time.time() - 5
            for session_id, session in self._active_sessions.items():
                try:
                    last_activity = datetime.fromisoformat(
                        session.last_activity_at.replace("Z", "+00:00")
                    )
                    if last_activity.timestamp() > recent_threshold:
                        return AttributionResult(
                            success=True,
                            agent_name=session.agent_name,
                            session_id=session_id,
                            confidence=0.5,
                            method="inferred",
                            reason=f"Session {session_id} was recently active",
                        )
                except (ValueError, TypeError):
                    pass

            # Strategy 4: Unknown attribution
            return AttributionResult(
                success=False,
                confidence=0.0,
                method="unknown",
                reason="No active session could be attributed to this change",
            )

    def record_change(self, event: WatchEvent, attribution: AttributionResult) -> ChangeRecord:
        """Record a change with attribution.

        Args:
            event: The file change event
            attribution: The attribution result

        Returns:
            The created ChangeRecord
        """
        record = ChangeRecord(
            path=event.path,
            change_type=event.change_type.value,
            timestamp=event.timestamp,
            old_path=event.old_path,
            is_directory=event.is_directory,
            size=event.size,
            checksum=event.checksum,
            agent_name=attribution.agent_name or "",
            session_id=attribution.session_id or "",
            team_name=self.team_name,
        )

        with self._lock:
            self._change_buffer.append(record)
            # Trim buffer if too large
            if len(self._change_buffer) > self._buffer_size:
                self._change_buffer = self._change_buffer[-self._buffer_size :]

        return record

    def get_changes(
        self,
        agent_name: str | None = None,
        session_id: str | None = None,
        path_prefix: str | None = None,
        since: str | None = None,
        limit: int = 100,
    ) -> list[ChangeRecord]:
        """Get change records with optional filtering.

        Args:
            agent_name: Filter by agent name
            session_id: Filter by session ID
            path_prefix: Filter by path prefix
            since: Filter by timestamp (ISO format)
            limit: Maximum number of records to return

        Returns:
            List of matching ChangeRecords
        """
        with self._lock:
            records = list(self._change_buffer)

        # Apply filters
        if agent_name:
            records = [r for r in records if r.agent_name == agent_name]
        if session_id:
            records = [r for r in records if r.session_id == session_id]
        if path_prefix:
            records = [r for r in records if r.path.startswith(path_prefix)]
        if since:
            records = [r for r in records if r.timestamp >= since]

        # Sort by timestamp descending
        records.sort(key=lambda r: r.timestamp, reverse=True)

        return records[:limit]

    def get_active_sessions(self) -> list[ActiveSession]:
        """Get all active sessions."""
        with self._lock:
            return list(self._active_sessions.values())

    def get_session(self, session_id: str) -> ActiveSession | None:
        """Get a specific session by ID."""
        with self._lock:
            return self._active_sessions.get(session_id)

    def save_changes(self) -> None:
        """Save buffered changes to disk."""
        with self._lock:
            if not self._change_buffer:
                return

            records = [r.model_dump(by_alias=True) for r in self._change_buffer]

        path = _attribution_root(self.team_name) / "changes.json"
        existing = []
        if path.exists():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                existing = []

        # Merge and deduplicate
        existing_ids = {r.get("id") for r in existing}
        for record in records:
            if record.get("id") not in existing_ids:
                existing.append(record)

        atomic_write_text(path, json.dumps(existing, indent=2, ensure_ascii=False))
        logger.info(f"Saved {len(records)} change records to {path}")

    def load_changes(self) -> None:
        """Load change records from disk."""
        path = _attribution_root(self.team_name) / "changes.json"
        if not path.exists():
            return

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            with self._lock:
                self._change_buffer = [ChangeRecord.model_validate(r) for r in data]
            logger.info(f"Loaded {len(self._change_buffer)} change records from {path}")
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to load change records: {e}")

    def clear_buffer(self) -> None:
        """Clear the in-memory change buffer."""
        with self._lock:
            self._change_buffer.clear()


def create_change_handler(
    attributor: ChangeAttributor,
    on_change: Callable[[ChangeRecord], None] | None = None,
) -> Callable[[WatchEvent], None]:
    """Create a file watcher handler that attributes changes.

    Args:
        attributor: The ChangeAttributor instance
        on_change: Optional callback for when a change is recorded

    Returns:
        A handler function for FileWatcher
    """

    def handler(event: WatchEvent) -> None:
        # Skip directory events
        if event.is_directory:
            return

        # Attribute the change
        attribution = attributor.attribute_change(event)

        # Record the change
        record = attributor.record_change(event, attribution)

        # Call optional callback
        if on_change:
            try:
                on_change(record)
            except Exception as e:
                logger.error(f"Error in change callback: {e}")

        # Log the attribution
        if attribution.success:
            logger.info(
                f"Change attributed: {event.path} -> {attribution.agent_name} "
                f"(confidence: {attribution.confidence:.2f}, method: {attribution.method})"
            )
        else:
            logger.debug(f"Unattributed change: {event.path}")

    return handler


# Type alias for callback
from typing import Callable
