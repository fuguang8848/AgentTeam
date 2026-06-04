"""SSE streaming for real-time agent activity monitoring."""

from __future__ import annotations

import json
import threading
from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentteam.board.handlers.base import BaseHandler

# Thread-safe agent activity broadcaster for SSE (real-time agent monitoring)
_agent_activity_queue: deque[dict] = deque(maxlen=1000)  # Last 1000 activity events
_agent_activity_subscribers: list[threading.Lock] = []  # List of queue indices for SSE connections
_agent_activity_lock = threading.Lock()


def _broadcast_agent_activity(activity_data: dict) -> None:
    """Broadcast an agent activity event to all SSE subscribers."""
    from agentteam.board.utils import _now_iso

    # Add timestamp if not present
    if "timestamp" not in activity_data:
        activity_data["timestamp"] = _now_iso()

    # Add to queue
    _agent_activity_queue.append(activity_data)

    # Notify all subscribers
    with _agent_activity_lock:
        for lock in _agent_activity_subscribers[:]:
            try:
                lock.release()
            except RuntimeError:
                # Lock not held by this thread, ignore
                pass


class AgentActivityBroadcaster:
    """Manages SSE connections and broadcasting for agent activity events."""

    def __init__(self, max_queue_size: int = 1000):
        self.queue: deque[dict] = deque(maxlen=max_queue_size)
        self.subscribers: list[threading.Lock] = []
        self.lock = threading.Lock()

    def add_subscriber(self) -> tuple[int, threading.Lock]:
        """Add a new SSE subscriber and return its starting index and lock."""
        last_idx = len(self.queue)
        subscriber_lock = threading.Lock()
        subscriber_lock.acquire()

        with self.lock:
            self.subscribers.append(subscriber_lock)

        return last_idx, subscriber_lock

    def remove_subscriber(self, subscriber_lock: threading.Lock) -> None:
        """Remove a subscriber from the broadcaster."""
        with self.lock:
            if subscriber_lock in self.subscribers:
                self.subscribers.remove(subscriber_lock)

    def broadcast(self, activity_data: dict) -> None:
        """Broadcast an activity event to all subscribers."""
        # Add to queue
        self.queue.append(activity_data)

        # Notify all subscribers
        with self.lock:
            for lock in self.subscribers[:]:
                try:
                    lock.release()
                except RuntimeError:
                    pass

    def get_recent_activities(self, start_idx: int, limit: int = 100) -> list[dict]:
        """Get recent activities since the given index."""
        with self.lock:
            return list(self.queue[start_idx : start_idx + limit])

    def get_queue_size(self) -> int:
        """Get current queue size."""
        return len(self.queue)


# Global agent activity broadcaster instance
_agent_activity_broadcaster: AgentActivityBroadcaster | None = None


def get_agent_activity_broadcaster() -> AgentActivityBroadcaster:
    """Get or create the global agent activity broadcaster instance."""
    global _agent_activity_broadcaster
    if _agent_activity_broadcaster is None:
        _agent_activity_broadcaster = AgentActivityBroadcaster()
    return _agent_activity_broadcaster
