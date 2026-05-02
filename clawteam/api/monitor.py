"""Monitor API endpoints for the Command Center dashboard."""

from __future__ import annotations

import json
from datetime import datetime, timezone


def _now_iso() -> str:
    """Return current time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def _get_dashboard():
    """Get the CommandCenterDashboard instance."""
    from clawteam.board.dashboard import CommandCenterDashboard

    return CommandCenterDashboard.get_instance()


def handle_monitor_stats() -> dict:
    """GET /api/monitor/stats - Full dashboard statistics."""
    dashboard = _get_dashboard()
    return dashboard.get_dashboard_data()


def handle_monitor_kpis() -> dict:
    """GET /api/monitor/kpis - Global KPIs only."""
    dashboard = _get_dashboard()
    kpis = dashboard.get_global_kpis()
    return {
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
    }


def handle_monitor_sessions() -> dict:
    """GET /api/monitor/sessions - Active sessions list."""
    dashboard = _get_dashboard()
    sessions = dashboard.get_active_sessions(limit=50)
    return {
        "sessions": [
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
        "count": len(sessions),
    }


def handle_monitor_lifecycle() -> dict:
    """GET /api/monitor/lifecycle - Lifecycle distribution."""
    dashboard = _get_dashboard()
    stats = dashboard.get_lifecycle_stats()
    return {
        "starting": stats.starting,
        "running": stats.running,
        "waiting": stats.waiting,
        "paused": stats.paused,
        "completed": stats.completed,
        "error": stats.error,
    }


def handle_monitor_events() -> dict:
    """GET /api/monitor/events - Event distribution."""
    dashboard = _get_dashboard()
    events = dashboard.get_event_distribution()
    return {
        "startEvents": events.start_events,
        "activityEvents": events.activity_events,
        "inputEvents": events.input_events,
        "turnEvents": events.turn_events,
        "messageEvents": events.message_events,
        "completionEvents": events.completion_events,
    }


def handle_monitor_teams() -> dict:
    """GET /api/monitor/teams - Team summaries."""
    dashboard = _get_dashboard()
    teams = dashboard.get_team_summaries()
    return {
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
        "count": len(teams),
    }


def handle_monitor_record_event(body: dict) -> dict:
    """POST /api/monitor/events - Record an event."""
    event_type = body.get("type", "")
    count = body.get("count", 1)
    dashboard = _get_dashboard()
    dashboard.record_event(event_type, count)
    return {"status": "ok", "type": event_type, "count": count}


def handle_monitor_record_lifecycle(body: dict) -> dict:
    """POST /api/monitor/lifecycle - Record a lifecycle state."""
    state = body.get("state", "")
    count = body.get("count", 1)
    dashboard = _get_dashboard()
    dashboard.record_lifecycle(state, count)
    return {"status": "ok", "state": state, "count": count}


# Route table: path -> (handler, method)
MONITOR_ROUTES = {
    "/api/monitor/stats": (handle_monitor_stats, "GET"),
    "/api/monitor/kpis": (handle_monitor_kpis, "GET"),
    "/api/monitor/sessions": (handle_monitor_sessions, "GET"),
    "/api/monitor/lifecycle": (handle_monitor_lifecycle, "GET"),
    "/api/monitor/events": (handle_monitor_events, "GET"),
    "/api/monitor/teams": (handle_monitor_teams, "GET"),
}


def dispatch_monitor(path: str, method: str, body: dict | None = None) -> tuple[dict, int]:
    """Dispatch a monitor API request.

    Returns (response_dict, http_status_code).
    """
    handler = MONITOR_ROUTES.get(path)
    if not handler:
        return {"error": "Not found", "path": path}, 404

    func, expected_method = handler
    if method != expected_method:
        return {"error": f"Method not allowed, use {expected_method}"}, 405

    try:
        if method == "POST" and body:
            result = func(body)
        else:
            result = func()
        return result, 200
    except Exception as e:
        return {"error": str(e)}, 500
