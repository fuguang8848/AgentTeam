"""Shared Context Board for ClawTeam collaboration.

Provides a shared space where agents can publish their current context
(current task, file being worked on, notes, etc.) visible to all team members.
"""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path


class ContextCategory(str, Enum):
    """Categories for context entries."""

    TASK = "task"  # Currently working on a task
    REVIEW = "review"  # Reviewing code/documents
    MEETING = "meeting"  # In a meeting or discussion
    RESEARCH = "research"  # Researching something
    BREAK = "break"  # On a break
    OTHER = "other"  # Other activities


@dataclass
class ContextEntry:
    """A context entry on the shared board.

    Represents what an agent is currently working on or thinking about.
    """

    id: str
    agent_name: str
    category: ContextCategory
    title: str
    description: Optional[str] = None
    file_path: Optional[str] = None
    task_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_pinned: bool = False
    is_private: bool = False  # Private entries only visible to the author

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["category"] = (
            self.category.value if isinstance(self.category, ContextCategory) else self.category
        )
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextEntry":
        """Create from dictionary."""
        if isinstance(data.get("category"), str):
            data["category"] = ContextCategory(data["category"])
        return cls(**data)

    def update(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        file_path: Optional[str] = None,
        category: Optional[ContextCategory] = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        """Update the context entry."""
        if title is not None:
            self.title = title
        if description is not None:
            self.description = description
        if file_path is not None:
            self.file_path = file_path
        if category is not None:
            self.category = category
        if tags is not None:
            self.tags = tags
        self.updated_at = datetime.now(timezone.utc).isoformat()


class ContextBoard:
    """Shared context board for team collaboration.

    Features:
    - Agents can post context entries describing what they're working on
    - Entries are visible to all team members (unless marked private)
    - Supports pinning important entries
    - Filter by agent, category, or tags
    - Real-time updates via callbacks

    Example:
        board = ContextBoard(team_name="dev-team")

        # Agent posts what they're working on
        board.post(
            agent_name="alice",
            category=ContextCategory.TASK,
            title="Implementing OAuth2 flow",
            description="Working on the authentication module",
            file_path="/src/auth/oauth.py",
        )

        # Others can view the board
        entries = board.get_all(agent_name_filter="alice")
    """

    def __init__(
        self,
        team_name: str,
        persist_dir: Optional[Path] = None,
    ):
        self.team_name = team_name
        self._persist_dir = persist_dir

        # In-memory entries: entry_id -> ContextEntry
        self._entries: Dict[str, ContextEntry] = {}

        # Callbacks for entry changes
        self._change_callbacks: List[Callable] = []

        # Lock for thread safety
        self._lock = threading.RLock()

        if persist_dir:
            persist_dir.mkdir(parents=True, exist_ok=True)
            self._load_entries()

    def post(
        self,
        agent_name: str,
        category: ContextCategory,
        title: str,
        description: Optional[str] = None,
        file_path: Optional[str] = None,
        task_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_private: bool = False,
    ) -> ContextEntry:
        """Post a new context entry.

        Args:
            agent_name: Name of the agent posting
            category: What kind of activity
            title: Brief title (e.g., "Implementing auth flow")
            description: Optional detailed description
            file_path: Optional file being worked on
            task_id: Optional related task ID
            tags: Optional tags for filtering
            is_private: If True, only visible to the posting agent

        Returns:
            The created ContextEntry
        """
        entry_id = f"ctx_{uuid.uuid4().hex[:8]}"

        entry = ContextEntry(
            id=entry_id,
            agent_name=agent_name,
            category=category,
            title=title,
            description=description,
            file_path=file_path,
            task_id=task_id,
            tags=tags or [],
            is_private=is_private,
        )

        with self._lock:
            self._entries[entry_id] = entry
            if self._persist_dir:
                self._save_entry(entry)

        self._notify_change("post", entry)
        return entry

    def update_entry(
        self,
        entry_id: str,
        agent_name: str,
        **kwargs,
    ) -> Optional[ContextEntry]:
        """Update an existing context entry.

        Only the posting agent can update their entry.

        Returns the updated entry, or None if not found or unauthorized.
        """
        with self._lock:
            entry = self._entries.get(entry_id)

            if not entry:
                return None

            if entry.agent_name != agent_name:
                # Not the author
                return None

            entry.update(**kwargs)

            if self._persist_dir:
                self._save_entry(entry)

            self._notify_change("update", entry)
            return entry

    def delete_entry(self, entry_id: str, agent_name: str) -> bool:
        """Delete a context entry.

        Only the posting agent can delete their entry.

        Returns True if deleted.
        """
        with self._lock:
            entry = self._entries.get(entry_id)

            if not entry or entry.agent_name != agent_name:
                return False

            del self._entries[entry_id]

            if self._persist_dir:
                self._delete_entry(entry)

            self._notify_change("delete", entry_id)
            return True

    def pin_entry(self, entry_id: str, agent_name: str) -> bool:
        """Pin a context entry (requires author or team lead).

        Returns True if pinned.
        """
        with self._lock:
            entry = self._entries.get(entry_id)
            if not entry:
                return False
            entry.is_pinned = True
            if self._persist_dir:
                self._save_entry(entry)
            self._notify_change("pin", entry)
            return True

    def unpin_entry(self, entry_id: str, agent_name: str) -> bool:
        """Unpin a context entry."""
        with self._lock:
            entry = self._entries.get(entry_id)
            if not entry:
                return False
            entry.is_pinned = False
            if self._persist_dir:
                self._save_entry(entry)
            self._notify_change("unpin", entry)
            return True

    def get_entry(self, entry_id: str, viewer_name: Optional[str] = None) -> Optional[ContextEntry]:
        """Get a specific entry by ID.

        If viewer_name is provided and entry is private (not by viewer), returns None.
        """
        with self._lock:
            entry = self._entries.get(entry_id)

            if not entry:
                return None

            if entry.is_private and entry.agent_name != viewer_name:
                return None

            return entry

    def get_all(
        self,
        agent_name_filter: Optional[str] = None,
        category_filter: Optional[ContextCategory] = None,
        tag_filter: Optional[str] = None,
        viewer_name: Optional[str] = None,
        include_pinned_first: bool = True,
    ) -> List[ContextEntry]:
        """Get all visible context entries with optional filters.

        Args:
            agent_name_filter: Only show entries from this agent
            category_filter: Only show entries of this category
            tag_filter: Only show entries with this tag
            viewer_name: Name of the viewing agent (for private entry filtering)
            include_pinned_first: If True, pinned entries appear first

        Returns:
            List of ContextEntry objects
        """
        with self._lock:
            result = []

            for entry in self._entries.values():
                # Skip private entries from other agents
                if entry.is_private and entry.agent_name != viewer_name:
                    continue

                # Apply filters
                if agent_name_filter and entry.agent_name != agent_name_filter:
                    continue

                if category_filter and entry.category != category_filter:
                    continue

                if tag_filter and tag_filter not in entry.tags:
                    continue

                result.append(entry)

            # Sort: pinned first, then by updated_at
            if include_pinned_first:
                result.sort(key=lambda e: (not e.is_pinned, e.updated_at), reverse=True)
            else:
                result.sort(key=lambda e: e.updated_at, reverse=True)

            return result

    def get_by_agent(
        self, agent_name: str, viewer_name: Optional[str] = None
    ) -> List[ContextEntry]:
        """Get all entries for a specific agent."""
        return self.get_all(agent_name_filter=agent_name, viewer_name=viewer_name)

    def get_by_task(self, task_id: str, viewer_name: Optional[str] = None) -> List[ContextEntry]:
        """Get all entries related to a specific task."""
        with self._lock:
            result = []
            for entry in self._entries.values():
                if entry.is_private and entry.agent_name != viewer_name:
                    continue
                if entry.task_id == task_id:
                    result.append(entry)
            return result

    def get_active_workers(self) -> List[str]:
        """Get list of agent names who have posted recent context entries.

        Returns unique agent names with non-BREAK entries.
        """
        with self._lock:
            agents = set()
            for entry in self._entries.values():
                if entry.category != ContextCategory.BREAK:
                    agents.add(entry.agent_name)
            return sorted(list(agents))

    def clear_agent_entries(self, agent_name: str) -> int:
        """Clear all entries for an agent (e.g., when they go offline).

        Returns number of entries cleared.
        """
        with self._lock:
            to_remove = [
                entry_id
                for entry_id, entry in self._entries.items()
                if entry.agent_name == agent_name
            ]

            for entry_id in to_remove:
                entry = self._entries[entry_id]
                del self._entries[entry_id]
                if self._persist_dir:
                    self._delete_entry(entry)
                self._notify_change("delete", entry_id)

            return len(to_remove)

    def add_change_callback(self, callback: Callable) -> None:
        """Add a callback for board changes.

        Callback receives (action: str, data: Any).
        """
        self._change_callbacks.append(callback)

    def remove_change_callback(self, callback: Callable) -> None:
        """Remove a change callback."""
        if callback in self._change_callbacks:
            self._change_callbacks.remove(callback)

    def _notify_change(self, action: str, data: Any) -> None:
        """Notify callbacks of a change."""
        for callback in self._change_callbacks:
            try:
                callback(action, data)
            except Exception:
                import logging

                logging.getLogger(__name__).error(f"Context board callback error: {callback}")

    def _save_entry(self, entry: ContextEntry) -> None:
        """Persist entry to disk."""
        if not self._persist_dir:
            return
        try:
            file_path = self._persist_dir / f"entry-{entry.id}.json"
            file_path.write_text(
                json.dumps(entry.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            import logging

            logging.getLogger(__name__).warning(f"Failed to persist entry {entry.id}")

    def _delete_entry(self, entry: ContextEntry) -> None:
        """Delete persisted entry from disk."""
        if not self._persist_dir:
            return
        try:
            file_path = self._persist_dir / f"entry-{entry.id}.json"
            if file_path.exists():
                file_path.unlink()
        except Exception:
            import logging

            logging.getLogger(__name__).warning(f"Failed to delete entry {entry.id}")

    def _load_entries(self) -> None:
        """Load entries from disk."""
        if not self._persist_dir or not self._persist_dir.exists():
            return

        with self._lock:
            for file_path in self._persist_dir.glob("entry-*.json"):
                try:
                    data = json.loads(file_path.read_text(encoding="utf-8"))
                    entry = ContextEntry.from_dict(data)
                    self._entries[entry.id] = entry
                except Exception:
                    import logging

                    logging.getLogger(__name__).warning(f"Failed to load entry from {file_path}")
