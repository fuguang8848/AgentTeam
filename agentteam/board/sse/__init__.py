"""SSE (Server-Sent Events) module for real-time streaming."""

from __future__ import annotations

from agentteam.board.sse.broadcast import (
    SSEBroadcaster,
    get_sse_broadcaster,
    _event_queue,
    _event_subscribers,
    _event_broadcaster_lock,
    _register_event_subscriber,
)
from agentteam.board.sse.agent_activity import (
    AgentActivityBroadcaster,
    get_agent_activity_broadcaster,
    _agent_activity_queue,
    _agent_activity_subscribers,
    _agent_activity_lock,
)

__all__ = [
    "SSEBroadcaster",
    "get_sse_broadcaster",
    "_event_queue",
    "_event_subscribers",
    "_event_broadcaster_lock",
    "_register_event_subscriber",
    "AgentActivityBroadcaster",
    "get_agent_activity_broadcaster",
    "_agent_activity_queue",
    "_agent_activity_subscribers",
    "_agent_activity_lock",
]
