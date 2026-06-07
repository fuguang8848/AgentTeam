"""
Session Management Commands

Provides session persistence operations: save, show, clear.
"""

from __future__ import annotations

import json
from typing import Optional

import typer
from rich.console import Console

from agentteam import __version__

app = typer.Typer(help="Session persistence commands")
console = Console()

# Global state (set by parent module)
_json_output = False


def _init_json_output(json_flag: bool):
    """Initialize JSON output flag from parent module."""
    global _json_output
    _json_output = json_flag


def _dump(model) -> dict:
    """Dump a pydantic model to dict."""
    return json.loads(model.model_dump_json(by_alias=True, exclude_none=True))


def _output(data: dict | list, human_fn=None):
    """Output data as JSON or human-readable."""
    if _json_output:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    elif human_fn:
        human_fn(data)
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))


# ============================================================================
# Session Commands
# ============================================================================


@app.command("save")
def session_save(
    team: str = typer.Argument(..., help="Team name"),
    session_id: str = typer.Option("", "--session-id", "-s", help="Claude Code session ID"),
    last_task: str = typer.Option("", "--last-task", help="Last task ID worked on"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent name"),
):
    """Save agent session for later resume."""
    from agentteam.identity import AgentIdentity
    from agentteam.spawn.sessions import SessionStore

    agent_name = agent or AgentIdentity.from_env().agent_name
    store = SessionStore(team)
    session = store.save(
        agent_name=agent_name,
        session_id=session_id,
        last_task_id=last_task,
    )
    _output(_dump(session), lambda d: console.print(f"[green]OK[/green] Session saved for '{agent_name}'"))


@app.command("show")
def session_show(
    team: str = typer.Argument(..., help="Team name"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent name"),
):
    """Show saved session information."""
    from agentteam.identity import AgentIdentity
    from agentteam.spawn.sessions import SessionStore

    agent_name = agent or AgentIdentity.from_env().agent_name
    store = SessionStore(team)
    session = store.get(agent_name)

    if session:

        def _human(s):
            console.print(f"\n[bold]Session - {agent_name}[/bold]")
            console.print(f"  Session ID: {s.get('session_id', 'N/A')}")
            console.print(f"  Last task: {s.get('last_task_id', 'N/A')}")
            console.print(f"  Saved at: {s.get('saved_at', 'N/A')[:19]}")

        _output(_dump(session), _human)
    else:
        _output(
            {"error": "No session found"},
            lambda d: console.print(f"[yellow]No saved session for '{agent_name}'[/yellow]"),
        )


@app.command("clear")
def session_clear(
    team: str = typer.Argument(..., help="Team name"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent name"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Clear saved session data."""
    from agentteam.identity import AgentIdentity
    from agentteam.spawn.sessions import SessionStore

    agent_name = agent or AgentIdentity.from_env().agent_name

    if not force and not _json_output:
        if not typer.confirm(f"Clear session for '{agent_name}'?"):
            raise typer.Abort()

    store = SessionStore(team)
    store.delete(agent_name)

    _output(
        {"status": "cleared", "agent": agent_name},
        lambda d: console.print(f"[green]OK[/green] Session cleared for '{agent_name}'"),
    )


if __name__ == "__main__":
    app()
