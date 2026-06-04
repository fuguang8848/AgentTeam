"""SSE broadcasting mechanism for real-time event streaming."""

from __future__ import annotations

import json
import threading
from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentteam.board.handlers.base import BaseHandler

# Thread-safe event broadcaster for SSE (P37: EventAPI integration)
_event_queue: deque[dict] = deque(maxlen=500)  # Last 500 events
_event_subscribers: list[threading.Lock] = []  # List of queue indices for SSE connections
_event_broadcaster_lock = threading.Lock()

# P37: EventAPI integration - register board as event subscriber
_event_subscriber_registered = False


def _register_event_subscriber() -> None:
    """Register the board's event broadcaster with EventTracker (P37)."""
    global _event_subscriber_registered
    if _event_subscriber_registered:
        return

    try:
        from agentteam.board.sse.broadcast import _broadcast_event

        def board_event_callback(event):
            """Callback to broadcast events to board SSE subscribers."""
            # Convert event to dict for JSON serialization
            event_dict = event.to_dict() if hasattr(event, "to_dict") else dict(event)
            _broadcast_event(event_dict)

        from agentteam.events.tracker import add_event_subscriber

        add_event_subscriber(board_event_callback)
        _event_subscriber_registered = True
    except Exception as e:
        print(f"Failed to register event subscriber: {e}")


def _broadcast_event(event_data: dict) -> None:
    """Broadcast an event to all SSE subscribers (P37: EventAPI integration)."""
    from agentteam.board.utils import _now_iso

    # Add timestamp if not present
    if "timestamp" not in event_data:
        event_data["timestamp"] = _now_iso()

    # Add to queue
    _event_queue.append(event_data)

    # Notify all subscribers
    with _event_broadcaster_lock:
        for lock in _event_subscribers[:]:
            try:
                lock.release()
            except RuntimeError:
                # Lock not held by this thread, ignore
                pass


class SSEBroadcaster:
    """Manages SSE connections and broadcasting for a specific event type."""

    def __init__(self, max_queue_size: int = 500):
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

    def broadcast(self, event_data: dict) -> None:
        """Broadcast an event to all subscribers."""
        # Add to queue
        self.queue.append(event_data)

        # Notify all subscribers
        with self.lock:
            for lock in self.subscribers[:]:
                try:
                    lock.release()
                except RuntimeError:
                    pass

    def get_events_since(self, start_idx: int) -> list[dict]:
        """Get all events since the given index."""
        with self.lock:
            # deque doesn't support slicing, so we need to iterate
            result = []
            for i, event in enumerate(self.queue):
                if i >= start_idx:
                    result.append(event)
            return result

    def get_queue_size(self) -> int:
        """Get current queue size."""
        return len(self.queue)


# Global SSE broadcaster instance
_sse_broadcaster: SSEBroadcaster | None = None


def get_sse_broadcaster() -> SSEBroadcaster:
    """Get or create the global SSE broadcaster instance."""
    global _sse_broadcaster
    if _sse_broadcaster is None:
        _sse_broadcaster = SSEBroadcaster()
    return _sse_broadcaster
