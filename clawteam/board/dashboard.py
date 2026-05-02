"""Command Center Dashboard - Global KPI aggregation for ClawTeam."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class GlobalKPI:
    """Global KPI snapshot."""

    total_teams: int = 0
    active_teams: int = 0
    total_tasks: int = 0
    pending_tasks: int = 0
    in_progress_tasks: int = 0
    completed_tasks: int = 0
    blocked_tasks: int = 0
    active_sessions: int = 0
    total_sessions: int = 0
    total_members: int = 0
    alive_members: int = 0
    total_messages: int = 0
    total_cost_cents: float = 0.0
    uptime_seconds: float = 0.0
    timestamp: str = ""


@dataclass
class LifecycleStats:
    """Session lifecycle distribution."""

    starting: int = 0
    running: int = 0
    waiting: int = 0
    paused: int = 0
    completed: int = 0
    error: int = 0


@dataclass
class EventDistribution:
    """Event type distribution."""

    start_events: int = 0
    activity_events: int = 0
    input_events: int = 0
    turn_events: int = 0
    message_events: int = 0
    completion_events: int = 0


@dataclass
class ActiveSession:
    """Active session info for dashboard."""

    session_id: str
    name: str
    role: str
    team: str
    status: str
    created_at: str
    last_activity: str
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class TeamSummary:
    """Team summary for dashboard."""

    name: str
    description: str
    leader: str
    member_count: int
    alive_count: int
    task_total: int
    task_completed: int
    task_in_progress: int
    task_pending: int
    task_blocked: int
    health: str  # healthy, degraded, critical


class CommandCenterDashboard:
    """Aggregates global KPIs across all teams for the Command Center dashboard."""

    _instance: Optional["CommandCenterDashboard"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._start_time = time.monotonic()
        self._cache: dict = {}
        self._cache_ttl = 2.0  # seconds
        self._cache_updated: float = 0.0
        self._stats_lock = threading.Lock()

        # Event counters (in-memory, reset on restart)
        self._event_counts: dict[str, int] = {
            "start": 0,
            "activity": 0,
            "input": 0,
            "turn": 0,
            "message": 0,
            "completion": 0,
            "error": 0,
        }

        # Lifecycle counters
        self._lifecycle_counts: dict[str, int] = {
            "starting": 0,
            "running": 0,
            "waiting": 0,
            "paused": 0,
            "completed": 0,
            "error": 0,
        }

    @classmethod
    def get_instance(cls) -> "CommandCenterDashboard":
        """Get singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def record_event(self, event_type: str, count: int = 1) -> None:
        """Record an event occurrence."""
        with self._stats_lock:
            if event_type in self._event_counts:
                self._event_counts[event_type] += count

    def record_lifecycle(self, state: str, count: int = 1) -> None:
        """Record a lifecycle state change."""
        with self._stats_lock:
            state_key = state.lower()
            if state_key in self._lifecycle_counts:
                self._lifecycle_counts[state_key] += count

    def get_global_kpis(self) -> GlobalKPI:
        """Get global KPI snapshot across all teams."""
        now = datetime.now(timezone.utc)
        uptime = time.monotonic() - self._start_time

        # Try to collect real data from teams
        total_teams = 0
        active_teams = 0
        total_tasks = 0
        pending_tasks = 0
        in_progress_tasks = 0
        completed_tasks = 0
        blocked_tasks = 0
        active_sessions = 0
        total_sessions = 0
        total_members = 0
        alive_members = 0
        total_messages = 0
        total_cost = 0.0

        try:
            from clawteam.board.collector import BoardCollector

            collector = BoardCollector()
            teams = collector.collect_overview()

            total_teams = len(teams)
            for team in teams:
                active_teams += 1 if team.get("active_sessions", 0) > 0 else 0
                total_tasks += team.get("tasks", 0)
                total_members += team.get("members", 0)
                alive_members += team.get("active_sessions", 0)
                active_sessions += team.get("active_sessions", 0)
                total_sessions += team.get("session_count", 0)
                total_messages += team.get("pendingMessages", 0)
        except Exception:
            # Fallback to stats lock data
            pass

        return GlobalKPI(
            total_teams=total_teams,
            active_teams=active_teams,
            total_tasks=total_tasks,
            pending_tasks=pending_tasks,
            in_progress_tasks=in_progress_tasks,
            completed_tasks=completed_tasks,
            blocked_tasks=blocked_tasks,
            active_sessions=active_sessions,
            total_sessions=total_sessions,
            total_members=total_members,
            alive_members=alive_members,
            total_messages=total_messages,
            total_cost_cents=total_cost,
            uptime_seconds=uptime,
            timestamp=now.isoformat(),
        )

    def get_lifecycle_stats(self) -> LifecycleStats:
        """Get lifecycle distribution stats."""
        with self._stats_lock:
            return LifecycleStats(
                starting=self._lifecycle_counts.get("starting", 0),
                running=self._lifecycle_counts.get("running", 0),
                waiting=self._lifecycle_counts.get("waiting", 0),
                paused=self._lifecycle_counts.get("paused", 0),
                completed=self._lifecycle_counts.get("completed", 0),
                error=self._lifecycle_counts.get("error", 0),
            )

    def get_event_distribution(self) -> EventDistribution:
        """Get event type distribution."""
        with self._stats_lock:
            return EventDistribution(
                start_events=self._event_counts.get("start", 0),
                activity_events=self._event_counts.get("activity", 0),
                input_events=self._event_counts.get("input", 0),
                turn_events=self._event_counts.get("turn", 0),
                message_events=self._event_counts.get("message", 0),
                completion_events=self._event_counts.get("completion", 0),
            )

    def get_active_sessions(self, limit: int = 50) -> list[ActiveSession]:
        """Get list of active sessions."""
        sessions = []
        try:
            from clawteam.session.registry import get_session_registry

            registry = get_session_registry()
            all_sessions = registry.list_sessions()

            for session in all_sessions[:limit]:
                sessions.append(
                    ActiveSession(
                        session_id=session.session_id
                        if hasattr(session, "session_id")
                        else str(session),
                        name=session.name if hasattr(session, "name") else "Unknown",
                        role=session.role if hasattr(session, "role") else "agent",
                        team=session.team if hasattr(session, "team") else "default",
                        status=session.status if hasattr(session, "status") else "unknown",
                        created_at=session.created_at if hasattr(session, "created_at") else "",
                        last_activity=session.last_activity
                        if hasattr(session, "last_activity")
                        else "",
                        input_tokens=getattr(session, "input_tokens", 0) or 0,
                        output_tokens=getattr(session, "output_tokens", 0) or 0,
                    )
                )
        except Exception:
            pass

        return sessions

    def get_team_summaries(self) -> list[TeamSummary]:
        """Get summary for all teams."""
        summaries = []
        try:
            from clawteam.board.collector import BoardCollector

            collector = BoardCollector()
            teams = collector.collect_overview()

            for team in teams:
                name = team.get("name", "unknown")
                alive = team.get("active_sessions", 0)
                members = team.get("members", 0)
                tasks = team.get("tasks", 0)

                # Determine health
                if alive == 0:
                    health = "stopped"
                elif alive < members:
                    health = "degraded"
                else:
                    health = "healthy"

                summaries.append(
                    TeamSummary(
                        name=name,
                        description=team.get("description", ""),
                        leader=team.get("leader", ""),
                        member_count=members,
                        alive_count=alive,
                        task_total=tasks,
                        task_completed=0,  # Would need per-team data
                        task_in_progress=0,
                        task_pending=tasks,
                        task_blocked=0,
                        health=health,
                    )
                )
        except Exception:
            pass

        return summaries

    def get_dashboard_data(self) -> dict:
        """Get complete dashboard data for the Command Center."""
        kpis = self.get_global_kpis()
        lifecycle = self.get_lifecycle_stats()
        events = self.get_event_distribution()
        sessions = self.get_active_sessions(limit=20)
        teams = self.get_team_summaries()

        return {
            "kpis": {
                "totalTeams": kpis.total_teams,
                "activeTeams": kpis.active_teams,
                "totalTasks": kpis.total_tasks,
                "pendingTasks": kpis.pending_tasks,
                "inProgressTasks": kpis.in_progress_tasks,
                "completedTasks": kpis.completed_tasks,
                "blockedTasks": kpis.blocked_tasks,
                "activeSessions": kpis.active_sessions,
                "totalSessions": kpis.total_sessions,
                "totalMembers": kpis.total_members,
                "aliveMembers": kpis.alive_members,
                "totalMessages": kpis.total_messages,
                "totalCostCents": kpis.total_cost_cents,
                "uptimeSeconds": round(kpis.uptime_seconds, 1),
                "timestamp": kpis.timestamp,
            },
            "lifecycle": {
                "starting": lifecycle.starting,
                "running": lifecycle.running,
                "waiting": lifecycle.waiting,
                "paused": lifecycle.paused,
                "completed": lifecycle.completed,
                "error": lifecycle.error,
            },
            "events": {
                "startEvents": events.start_events,
                "activityEvents": events.activity_events,
                "inputEvents": events.input_events,
                "turnEvents": events.turn_events,
                "messageEvents": events.message_events,
                "completionEvents": events.completion_events,
            },
            "activeSessions": [
                {
                    "sessionId": s.session_id,
                    "name": s.name,
                    "role": s.role,
                    "team": s.team,
                    "status": s.status,
                    "createdAt": s.created_at,
                    "lastActivity": s.last_activity,
                    "inputTokens": s.input_tokens,
                    "outputTokens": s.output_tokens,
                }
                for s in sessions
            ],
            "teams": [
                {
                    "name": t.name,
                    "description": t.description,
                    "leader": t.leader,
                    "memberCount": t.member_count,
                    "aliveCount": t.alive_count,
                    "taskTotal": t.task_total,
                    "taskCompleted": t.task_completed,
                    "taskInProgress": t.task_in_progress,
                    "taskPending": t.task_pending,
                    "taskBlocked": t.task_blocked,
                    "health": t.health,
                }
                for t in teams
            ],
        }

    def record_task_update(self, status: str) -> None:
        """Record a task status update."""
        with self._stats_lock:
            status_key = status.lower().replace("-", "_")
            # This could increment task counters if we tracked them
            pass

    def reset_stats(self) -> None:
        """Reset all statistics (for testing)."""
        with self._stats_lock:
            for key in self._event_counts:
                self._event_counts[key] = 0
            for key in self._lifecycle_counts:
                self._lifecycle_counts[key] = 0
