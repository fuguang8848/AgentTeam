"""Presence status management for ClawTeam collaboration.

Provides enhanced presence tracking with custom status messages,
availability indicators, and real-time status updates.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
from pathlib import Path


class PresenceStatus(str, Enum):
    """Agent presence status values."""

    ONLINE = "online"  # Active and available
    BUSY = "busy"  # Working on a task, prefer not to be interrupted
    IDLE = "idle"  # Available but not actively working
    AWAY = "away"  # Temporarily unavailable
    OFFLINE = "offline"  # Not connected


class PresenceManager:
    """Manages presence status for all team agents.

    Features:
    - Custom status messages (e.g., "Working on auth module")
    - Status duration tracking (for away status auto-expiry)
    - Availability indicators
    - Real-time status updates via callbacks

    Example:
        manager = PresenceManager(team_name="dev-team")
        manager.set_status("alice", PresenceStatus.ONLINE, "Implementing login flow")
        status = manager.get_status("alice")
        # => {"status": "online", "message": "Implementing login flow", ...}
    """

    def __init__(
        self,
        team_name: str,
        persist_dir: Optional[Path] = None,
    ):
        self.team_name = team_name
        self._persist_dir = persist_dir

        # In-memory presence data: agent_name -> PresenceData
        self._presence: Dict[str, Dict[str, Any]] = {}

        # Status update callbacks
        self._status_callbacks: List[callable] = []

        # Lock for thread safety
        self._lock = threading.RLock()

        if persist_dir:
            persist_dir.mkdir(parents=True, exist_ok=True)

    def set_status(
        self,
        agent_name: str,
        status: PresenceStatus,
        status_message: Optional[str] = None,
        duration_minutes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Set presence status for an agent.

        Args:
            agent_name: Name of the agent
            status: New presence status
            status_message: Optional custom status message
            duration_minutes: For AWAY status, auto-return after this many minutes

        Returns:
            The updated presence data
        """
        with self._lock:
            now = datetime.now(timezone.utc)

            data = {
                "agent_name": agent_name,
                "status": status.value,
                "status_message": status_message,
                "updated_at": now.isoformat(),
                "expires_at": None,
            }

            # Set expiry for AWAY status
            if status == PresenceStatus.AWAY and duration_minutes:
                from datetime import timedelta

                expires = now + timedelta(minutes=duration_minutes)
                data["expires_at"] = expires.isoformat()

            self._presence[agent_name] = data

            # Persist if enabled
            if self._persist_dir:
                self._persist_presence(agent_name, data)

            # Notify callbacks
            self._notify_status_change(agent_name, data)

            return data

    def get_status(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get current presence status for an agent.

        Returns None if agent has no presence data.
        """
        with self._lock:
            data = self._presence.get(agent_name)

            if data and data.get("expires_at"):
                # Check if AWAY status has expired
                expires_at = datetime.fromisoformat(data["expires_at"])
                if datetime.now(timezone.utc) > expires_at:
                    # Auto-expire: set back to ONLINE
                    data = self.set_status(
                        agent_name, PresenceStatus.ONLINE, status_message="Returned (was away)"
                    )

            return data

    def clear_status(self, agent_name: str) -> bool:
        """Clear presence status for an agent (sets to OFFLINE).

        Returns True if an entry was cleared.
        """
        with self._lock:
            if agent_name in self._presence:
                del self._presence[agent_name]
                if self._persist_dir:
                    self._clear_persisted_presence(agent_name)
                self._notify_status_change(agent_name, None)
                return True
            return False

    def get_team_presence(self) -> List[Dict[str, Any]]:
        """Get presence status for all agents on the team.

        Returns list sorted by status priority (ONLINE first).
        """
        with self._lock:
            # Filter out expired AWAY statuses
            result = []
            for agent_name, data in self._presence.items():
                if data.get("expires_at"):
                    expires_at = datetime.fromisoformat(data["expires_at"])
                    if datetime.now(timezone.utc) > expires_at:
                        # Skip expired
                        continue
                result.append(data)

            # Sort by status priority
            status_order = {
                PresenceStatus.ONLINE.value: 0,
                PresenceStatus.BUSY.value: 1,
                PresenceStatus.IDLE.value: 2,
                PresenceStatus.AWAY.value: 3,
                PresenceStatus.OFFLINE.value: 4,
            }
            result.sort(key=lambda x: status_order.get(x.get("status", ""), 5))

            return result

    def is_available(self, agent_name: str) -> bool:
        """Check if an agent is available (ONLINE or IDLE).

        Returns False for BUSY, AWAY, or OFFLINE.
        """
        status = self.get_status(agent_name)
        if not status:
            return False
        return status["status"] in [PresenceStatus.ONLINE.value, PresenceStatus.IDLE.value]

    def add_status_callback(self, callback: callable) -> None:
        """Add a callback for status changes.

        Callback receives (agent_name: str, presence_data: Optional[Dict]).
        """
        self._status_callbacks.append(callback)

    def remove_status_callback(self, callback: callable) -> None:
        """Remove a status change callback."""
        if callback in self._status_callbacks:
            self._status_callbacks.remove(callback)

    def _notify_status_change(self, agent_name: str, data: Optional[Dict[str, Any]]) -> None:
        """Notify all callbacks of a status change."""
        for callback in self._status_callbacks:
            try:
                callback(agent_name, data)
            except Exception:
                import logging

                logging.getLogger(__name__).error(f"Presence callback error: {callback}")

    def _persist_presence(self, agent_name: str, data: Dict[str, Any]) -> None:
        """Persist presence data to disk."""
        if not self._persist_dir:
            return
        try:
            file_path = self._persist_dir / f"presence-{agent_name}.json"
            file_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            import logging

            logging.getLogger(__name__).warning(f"Failed to persist presence for {agent_name}")

    def _clear_persisted_presence(self, agent_name: str) -> None:
        """Clear persisted presence data."""
        if not self._persist_dir:
            return
        try:
            file_path = self._persist_dir / f"presence-{agent_name}.json"
            if file_path.exists():
                file_path.unlink()
        except Exception:
            pass

    def load_persisted_presence(self) -> None:
        """Load persisted presence data from disk."""
        if not self._persist_dir or not self._persist_dir.exists():
            return

        with self._lock:
            for file_path in self._persist_dir.glob("presence-*.json"):
                try:
                    agent_name = file_path.stem.replace("presence-", "")
                    data = json.loads(file_path.read_text(encoding="utf-8"))
                    self._presence[agent_name] = data
                except Exception:
                    import logging

                    logging.getLogger(__name__).warning(f"Failed to load presence from {file_path}")
