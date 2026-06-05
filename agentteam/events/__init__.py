"""AgentTeam Event Tracking System (SpectrAI-inspired).

This module provides event-driven tracking for AgentTeam,
inspired by SpectrAI's turn_complete event architecture.

Core Components:
- models: Event type definitions and schemas
- tracker: SQLite-based event storage and querying
- api: REST API integration for board server

Usage:
    from agentteam.events import track_event, create_agent_event, EventType

    # Track a simple event
    event = create_agent_event(
        EventType.TURN_COMPLETE,
        "worker-1",
        session_id="sess-123",
        duration_ms=1500.0,
    )
    track_event(event)

    # Query events
    from agentteam.events import get_tracker
    tracker = get_tracker()
    events = tracker.query(team_name="my-team", limit=50)
"""

from agentteam.events.api import (
    EventAPI,
    get_event_api,
)
from agentteam.events.models import (
    AgentTeamEvent,
    EventCategory,
    EventSeverity,
    EventType,
    create_agent_event,
    create_alert_event,
    create_message_event,
    create_session_event,
    create_task_event,
    create_team_event,
    create_usage_event,
)
from agentteam.events.tracker import (
    EventTracker,
    get_tracker,
    set_tracker,
    reset_tracker,
    track_batch,
    track_event,
)

__all__ = [
    # Models
    "EventType",
    "EventSeverity",
    "EventCategory",
    "AgentTeamEvent",
    "create_team_event",
    "create_task_event",
    "create_agent_event",
    "create_session_event",
    "create_message_event",
    "create_alert_event",
    "create_usage_event",
    # Tracker
    "EventTracker",
    "get_tracker",
    "set_tracker",
    "reset_tracker",
    "track_event",
    "track_batch",
    # API
    "EventAPI",
    "get_event_api",
]
