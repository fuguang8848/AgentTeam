"""Event API integration for ClawTeam Board Server.

This module provides API handlers for the event tracking system,
integrating with the existing board server endpoints.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from clawteam.events.tracker import EventTracker, get_tracker
from clawteam.events.models import ClawTeamEvent, EventType, EventSeverity, EventCategory


class EventAPI:
    """API for event tracking system."""

    def __init__(self, tracker: Optional[EventTracker] = None):
        """Initialize the Event API.

        Args:
            tracker: Optional EventTracker instance. Uses global tracker if not provided.
        """
        self.tracker = tracker or get_tracker()

    def get_events(
        self,
        team_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        event_types: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        severity: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Get events with filters.

        Returns:
            Dictionary with events list and metadata.
        """
        events = self.tracker.query(
            team_name=team_name,
            agent_name=agent_name,
            event_types=event_types,
            categories=categories,
            severity=severity,
            since=since,
            until=until,
            session_id=session_id,
            task_id=task_id,
            limit=limit,
            offset=offset,
        )

        return {
            "events": events,
            "count": len(events),
            "limit": limit,
            "offset": offset,
            "has_more": len(events) == limit,
        }

    def get_dashboard_events(
        self,
        team_name: str,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Get events for team dashboard.

        Returns:
            Dictionary with events list for dashboard display.
        """
        events = self.tracker.get_events_for_dashboard(team_name, limit)

        # Group by time buckets for display
        return {
            "events": events,
            "count": len(events),
            "team_name": team_name,
        }

    def get_agent_timeline(
        self,
        agent_name: str,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Get event timeline for an agent.

        Returns:
            Dictionary with agent timeline events.
        """
        events = self.tracker.get_agent_timeline(agent_name, limit)

        return {
            "events": events,
            "count": len(events),
            "agent_name": agent_name,
        }

    def get_task_history(
        self,
        task_id: str,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Get event history for a task.

        Returns:
            Dictionary with task history events.
        """
        events = self.tracker.get_task_events(task_id, limit)

        return {
            "events": events,
            "count": len(events),
            "task_id": task_id,
        }

    def get_stats(
        self,
        team_name: Optional[str] = None,
        since: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get event statistics.

        Returns:
            Dictionary with event statistics.
        """
        return self.tracker.get_event_stats(team_name, since)

    def record_event(
        self,
        event: ClawTeamEvent,
    ) -> Dict[str, Any]:
        """Record a new event.

        Args:
            event: The event to record.

        Returns:
            Dictionary with recorded event info.
        """
        self.tracker.track(event)

        return {
            "success": True,
            "event_id": event.id,
        }

    def record_team_created(
        self,
        team_name: str,
        agent_name: Optional[str] = None,
        message: str = "",
    ) -> Dict[str, Any]:
        """Record a team creation event."""
        event = ClawTeamEvent(
            event_type=EventType.TEAM_CREATED,
            category=EventCategory.TEAM,
            team_name=team_name,
            agent_name=agent_name,
            message=message or f"Team '{team_name}' created",
        )
        return self.record_event(event)

    def record_member_joined(
        self,
        team_name: str,
        agent_name: str,
        agent_id: Optional[str] = None,
        message: str = "",
    ) -> Dict[str, Any]:
        """Record a member joined event."""
        event = ClawTeamEvent(
            event_type=EventType.MEMBER_JOINED,
            category=EventCategory.TEAM,
            team_name=team_name,
            agent_name=agent_name,
            agent_id=agent_id,
            message=message or f"Agent '{agent_name}' joined team",
        )
        return self.record_event(event)

    def record_task_created(
        self,
        task_id: str,
        team_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        message: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record a task creation event."""
        event = ClawTeamEvent(
            event_type=EventType.TASK_CREATED,
            category=EventCategory.TASK,
            task_id=task_id,
            team_name=team_name,
            agent_name=agent_name,
            message=message or f"Task '{task_id}' created",
            data=data or {},
        )
        return self.record_event(event)

    def record_task_completed(
        self,
        task_id: str,
        team_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        message: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record a task completion event."""
        event = ClawTeamEvent(
            event_type=EventType.TASK_COMPLETED,
            category=EventCategory.TASK,
            task_id=task_id,
            team_name=team_name,
            agent_name=agent_name,
            message=message or f"Task '{task_id}' completed",
            data=data or {},
        )
        return self.record_event(event)

    def record_turn_complete(
        self,
        agent_name: str,
        session_id: str,
        team_name: Optional[str] = None,
        duration_ms: Optional[float] = None,
        message: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record a turn_complete event (SpectrAI-inspired).

        This event marks the completion of an agent's turn,
        enabling real-time tracking of agent activity.
        """
        event = ClawTeamEvent(
            event_type=EventType.TURN_COMPLETE,
            category=EventCategory.AGENT,
            team_name=team_name,
            agent_name=agent_name,
            session_id=session_id,
            message=message or f"Agent '{agent_name}' completed turn",
            duration_ms=duration_ms,
            data=data or {},
        )
        return self.record_event(event)

    def record_agent_spawned(
        self,
        agent_name: str,
        agent_id: str,
        team_name: Optional[str] = None,
        session_id: Optional[str] = None,
        message: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record an agent spawn event."""
        event = ClawTeamEvent(
            event_type=EventType.AGENT_SPAWNED,
            category=EventCategory.AGENT,
            team_name=team_name,
            agent_name=agent_name,
            agent_id=agent_id,
            session_id=session_id,
            message=message or f"Agent '{agent_name}' spawned",
            data=data or {},
        )
        return self.record_event(event)

    def record_agent_terminated(
        self,
        agent_name: str,
        agent_id: Optional[str] = None,
        team_name: Optional[str] = None,
        session_id: Optional[str] = None,
        message: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record an agent termination event."""
        event = ClawTeamEvent(
            event_type=EventType.AGENT_TERMINATED,
            category=EventCategory.AGENT,
            team_name=team_name,
            agent_name=agent_name,
            agent_id=agent_id,
            session_id=session_id,
            message=message or f"Agent '{agent_name}' terminated",
            data=data or {},
        )
        return self.record_event(event)

    def record_session_started(
        self,
        session_id: str,
        agent_name: Optional[str] = None,
        team_name: Optional[str] = None,
        message: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record a session start event."""
        event = ClawTeamEvent(
            event_type=EventType.SESSION_STARTED,
            category=EventCategory.SESSION,
            session_id=session_id,
            agent_name=agent_name,
            team_name=team_name,
            message=message or f"Session '{session_id}' started",
            data=data or {},
        )
        return self.record_event(event)

    def record_session_ended(
        self,
        session_id: str,
        agent_name: Optional[str] = None,
        team_name: Optional[str] = None,
        message: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record a session end event."""
        event = ClawTeamEvent(
            event_type=EventType.SESSION_ENDED,
            category=EventCategory.SESSION,
            session_id=session_id,
            agent_name=agent_name,
            team_name=team_name,
            message=message or f"Session '{session_id}' ended",
            data=data or {},
        )
        return self.record_event(event)

    def record_alert(
        self,
        team_name: Optional[str],
        agent_name: Optional[str],
        alert_type: str,
        message: str,
        severity: EventSeverity = EventSeverity.WARNING,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record an alert event."""
        event = ClawTeamEvent(
            event_type=EventType.ALERT_TRIGGERED,
            category=EventCategory.ALERT,
            team_name=team_name,
            agent_name=agent_name,
            message=message,
            severity=severity,
            data=data or {"alert_type": alert_type},
        )
        return self.record_event(event)

    def record_usage(
        self,
        team_name: str,
        session_id: str,
        input_tokens: int,
        output_tokens: int,
        estimated_cost: float,
        provider_id: str = "unknown",
    ) -> Dict[str, Any]:
        """Record a usage/cost tracking event."""
        event = ClawTeamEvent(
            event_type=EventType.USAGE_RECORDED,
            category=EventCategory.USAGE,
            team_name=team_name,
            session_id=session_id,
            message=f"Usage: {input_tokens} in / {output_tokens} out / ${estimated_cost:.4f}",
            data={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "estimated_cost": estimated_cost,
                "provider_id": provider_id,
            },
        )
        return self.record_event(event)


# Global API instance
_event_api: Optional[EventAPI] = None


def get_event_api() -> EventAPI:
    """Get the global EventAPI instance."""
    global _event_api
    if _event_api is None:
        _event_api = EventAPI()
    return _event_api


__all__ = [
    "EventAPI",
    "get_event_api",
]
