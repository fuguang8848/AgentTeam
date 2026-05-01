"""Session awareness CLI commands for ClawTeam (Typer)."""

import json
import typer
from datetime import datetime
from typing import Optional
from pathlib import Path

session_app = typer.Typer(
    name="session",
    help="Session awareness commands",
    add_completion=False,
)


@session_app.command("list")
def list_sessions(
    team: str = typer.Option("default", help="Team name"),
    active_only: bool = typer.Option(False, "--active-only", help="Show only active sessions"),
    agent: Optional[str] = typer.Option(None, help="Filter by agent name"),
    min_activity: Optional[str] = typer.Option(
        None,
        "--min-activity",
        help="Minimum activity level: high, medium, low, inactive",
    ),
):
    """List all sessions."""
    from ..session_awareness import (
        get_session_awareness_manager,
        SessionActivityLevel,
    )

    manager = get_session_awareness_manager(team)

    if active_only:
        sessions = manager.get_active_sessions()
    elif agent:
        sessions = manager.get_sessions_by_agent(agent)
    elif min_activity:
        activity_level = SessionActivityLevel(min_activity)
        sessions = manager.get_sessions_by_activity(activity_level)
    else:
        sessions = list(manager.get_active_sessions())

    if not sessions:
        typer.echo("No sessions found.")
        return

    # Format output
    headers = ["Session ID", "Agent", "Status", "Activity", "Messages", "Files", "Task", "Inactive"]
    rows = []

    for tracker in sessions:
        context = tracker.get_context()
        inactive_minutes = int((datetime.now() - context.last_activity).total_seconds() / 60)

        rows.append([
            tracker.session_id[:8] + "...",
            tracker.agent_name,
            context.status.value,
            context.activity_level.value,
            str(context.message_count),
            str(context.file_change_count),
            (context.current_task[:20] + "...") if context.current_task else "None",
            f"{inactive_minutes}m",
        ])

    # Print table
    typer.echo(f"\nSessions in team '{team}':")
    typer.echo("-" * 120)
    typer.echo("  ".join(f"{h:<15}" for h in headers))
    typer.echo("-" * 120)
    for row in rows:
        typer.echo("  ".join(f"{cell:<15}" for cell in row))
    typer.echo("-" * 120)
    typer.echo(f"Total: {len(sessions)} sessions")


@session_app.command("info")
def session_info(
    session_id: str = typer.Argument(..., help="Session ID"),
    team: str = typer.Option("default", help="Team name"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Get detailed information about a session."""
    from ..session_awareness import get_session_tracker

    tracker = get_session_tracker(session_id, team)

    if not tracker:
        typer.echo(f"Session '{session_id}' not found in team '{team}'.")
        return

    summary = tracker.get_summary()

    if json_output:
        typer.echo(json.dumps(summary, indent=2, ensure_ascii=False))
        return

    # Pretty output
    typer.echo(f"\nSession: {session_id}")
    typer.echo("=" * 60)
    typer.echo(f"Agent:          {summary['agent_name']}")
    typer.echo(f"Status:         {summary['status']}")
    typer.echo(f"Activity:       {summary['activity_level']}")
    typer.echo(f"Created:        {summary['active_minutes']} minutes ago")
    typer.echo(f"Last activity:  {summary['minutes_inactive']} minutes ago")
    typer.echo(f"Messages:       {summary['message_count']}")
    typer.echo(f"File changes:   {summary['file_change_count']}")
    typer.echo(f"Current task:   {summary['current_task'] or 'None'}")
    typer.echo(f"Current file:   {summary['current_file'] or 'None'}")

    if summary['tags']:
        typer.echo(f"Tags:           {', '.join(summary['tags'])}")

    typer.echo("=" * 60)


@session_app.command("team")
def team_summary_cmd(
    team: str = typer.Option("default", help="Team name"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Get team summary."""
    from ..session_awareness import get_team_summary

    summary = get_team_summary(team)

    if json_output:
        typer.echo(json.dumps(summary, indent=2, ensure_ascii=False))
        return

    # Pretty output
    typer.echo(f"\nTeam: {summary['team_name']}")
    typer.echo("=" * 60)
    typer.echo(f"Total sessions:    {summary['total_sessions']}")
    typer.echo(f"Active sessions:   {summary['active_sessions']}")
    typer.echo(f"Idle sessions:     {summary['idle_sessions']}")
    typer.echo(f"Agents:            {', '.join(summary['agents'])}")
    typer.echo(f"Total messages:    {summary['total_messages']}")
    typer.echo(f"File changes:      {summary['total_file_changes']}")
    typer.echo("=" * 60)

    if summary['sessions']:
        typer.echo("\nActive sessions:")
        for session in summary['sessions']:
            if session['status'] == 'active':
                typer.echo(f"  * {session['agent_name']}: {session['current_task'] or 'No task'}")


@session_app.command("collaborators")
def find_collaborators(
    session_id: str = typer.Argument(..., help="Session ID"),
    team: str = typer.Option("default", help="Team name"),
    limit: int = typer.Option(3, help="Max collaborators to show"),
):
    """Find potential collaborators for a session."""
    from ..session_awareness import get_session_awareness_manager

    manager = get_session_awareness_manager(team)
    candidates = manager.find_collaborators(session_id, max_sessions=limit)

    if not candidates:
        typer.echo(f"No collaborators found for session '{session_id}'.")
        return

    typer.echo(f"\nCollaborators for session '{session_id}':")
    typer.echo("-" * 80)
    for i, c in enumerate(candidates, 1):
        typer.echo(f"  {i}. {c['agent_name']} (session: {c['session_id'][:8]}...)")
        typer.echo(f"     Score: {c['score']} | Activity: {c['activity_level']}")
        typer.echo(f"     Task: {c['current_task'] or 'None'}")
        typer.echo(f"     File: {c['current_file'] or 'None'}")
        if c['tags']:
            typer.echo(f"     Tags: {', '.join(c['tags'])}")
        typer.echo()


@session_app.command("cleanup")
def cleanup_sessions(
    team: str = typer.Option("default", help="Team name"),
    max_inactive: int = typer.Option(60, help="Max inactive minutes before cleanup"),
):
    """Clean up inactive sessions."""
    from ..session_awareness import get_session_awareness_manager

    manager = get_session_awareness_manager(team)
    cleaned = manager.cleanup_inactive_sessions(max_inactive)
    typer.echo(f"Cleaned up {cleaned} inactive sessions (>{max_inactive} minutes).")


@session_app.command("save")
def save_state(
    filepath: Path = typer.Argument(..., help="Output file path"),
    team: str = typer.Option("default", help="Team name"),
):
    """Save session state to file."""
    from ..session_awareness import get_session_awareness_manager

    manager = get_session_awareness_manager(team)
    manager.save_state(str(filepath))
    typer.echo(f"Session state saved to {filepath}")


@session_app.command("load")
def load_state(
    filepath: Path = typer.Argument(..., help="Input file path"),
    team: str = typer.Option("default", help="Team name"),
):
    """Load session state from file."""
    from ..session_awareness import get_session_awareness_manager

    manager = get_session_awareness_manager(team)
    manager.load_state(str(filepath))
    typer.echo(f"Session state loaded from {filepath}")
