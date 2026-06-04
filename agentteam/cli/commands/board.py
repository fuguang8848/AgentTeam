"""
Board (Dashboard) Commands

Provides team dashboard and kanban operations: show, overview, live, monitor, serve, attach.
"""

from __future__ import annotations

import json
from typing import Optional

import typer
from rich.console import Console

from agentteam import __version__

app = typer.Typer(help="Team dashboard and kanban board commands")
console = Console()

# Global state (set by parent module)
_json_output = False


def _init_json_output(json_flag: bool):
    """Initialize JSON output flag from parent module."""
    global _json_output
    _json_output = json_flag


def _output(data: dict | list, human_fn=None):
    """Output data as JSON or human-readable."""
    if _json_output:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    elif human_fn:
        human_fn(data)
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))


# ============================================================================
# Board Commands
# ============================================================================


@app.command("show")
def board_show(
    team: str = typer.Argument(..., help="Team name"),
):
    """Show detailed kanban board for a single team."""
    from agentteam.board.collector import BoardCollector
    from agentteam.board.renderer import BoardRenderer

    collector = BoardCollector()
    try:
        data = collector.collect_team(team)
    except ValueError as e:
        _output({"error": str(e)}, lambda d: console.print(f"[red]{d['error']}[/red]"))
        raise typer.Exit(1)

    _output(data, lambda d: BoardRenderer(console).render_team_board(d))


@app.command("overview")
def board_overview():
    """Show overview of all teams."""
    from agentteam.board.collector import BoardCollector
    from agentteam.board.renderer import BoardRenderer

    collector = BoardCollector()
    teams = collector.collect_overview()

    _output(teams, lambda d: BoardRenderer(console).render_overview(d))


@app.command("live")
def board_live(
    team: str = typer.Argument(..., help="Team name"),
    interval: float = typer.Option(2.0, "--interval", "-i", help="Refresh interval in seconds"),
):
    """Live-refreshing kanban board. Ctrl+C to stop."""
    from agentteam.board.collector import BoardCollector
    from agentteam.board.renderer import BoardRenderer

    collector = BoardCollector()

    # Validate team exists before starting live mode
    try:
        collector.collect_team(team)
    except ValueError as e:
        _output({"error": str(e)}, lambda d: console.print(f"[red]{d['error']}[/red]"))
        raise typer.Exit(1)

    if not _json_output:
        console.print(f"Live board for '{team}' (interval: {interval}s). Ctrl+C to stop.")

    renderer = BoardRenderer(console)
    renderer.render_team_board_live(collector, team, interval=interval)


@app.command("monitor")
def board_monitor(
    team: Optional[str] = typer.Argument(None, help="Team name (optional, monitors all teams if omitted)"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Filter by agent name"),
    status_filter: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status type"),
    port: int = typer.Option(8080, "--port", "-p", help="Board server port"),
    reconnect: bool = typer.Option(False, "--reconnect", "-r", help="Auto-reconnect on disconnect"),
    count: bool = typer.Option(False, "--count", "-c", help="Show event counts by status"),
    no_color: bool = typer.Option(False, "--no-color", help="Disable colored output"),
    tail: int = typer.Option(0, "--tail", "-t", help="Show last N events on connect"),
):
    """Real-time agent activity monitor - stream agent events as they happen."""
    import urllib.request
    import urllib.parse

    base_url = f"http://127.0.0.1:{port}"
    event_counts = {"started": 0, "completed": 0, "terminated": 0, "error": 0, "task_assigned": 0, "heartbeat": 0, "message": 0, "other": 0} if count else None

    params = {}
    if team:
        params["team"] = team
    if agent:
        params["agent"] = agent
    query = urllib.parse.urlencode(params)
    url = f"{base_url}/api/agents/events"
    if query:
        url += "?" + query

    if not _json_output:
        console.print(f"[dim]Connecting to {url}...[/dim]")

    try:
        while True:
            try:
                req = urllib.request.Request(url, headers={"Accept": "text/event-stream"})
                with urllib.request.urlopen(req, timeout=30) as response:
                    for line in response:
                        line = line.decode("utf-8").strip()
                        if line.startswith("data:"):
                            data = json.loads(line[5:])
                            if count and event_counts:
                                status = data.get("status", "other")
                                if status in event_counts:
                                    event_counts[status] += 1
                                else:
                                    event_counts["other"] += 1
                            else:
                                _print_agent_activity(data)
            except KeyboardInterrupt:
                break
            except Exception as e:
                if not _json_output:
                    console.print(f"[yellow]Connection error: {e}[/yellow]")
                if not reconnect:
                    break
                import time
                time.sleep(2)
    finally:
        if count and event_counts:
            console.print("\n[bold]Event Summary:[/bold]")
            for status, cnt in event_counts.items():
                console.print(f"  {status}: {cnt}")


def _print_agent_activity(activity: dict):
    """Print a single agent activity event."""
    status = activity.get("status", "unknown")
    agent = activity.get("agent_name", "unknown")
    team = activity.get("team_name", "")
    message = activity.get("message", "")

    colors = {
        "started": "green",
        "completed": "cyan",
        "terminated": "red",
        "error": "bold red",
        "task_assigned": "yellow",
        "heartbeat": "dim",
        "message": "blue",
    }
    color = colors.get(status, "white")

    if team:
        console.print(f"[{color}]{status}[/{color}] [{agent}@{team}] {message}")
    else:
        console.print(f"[{color}]{status}[/{color}] [{agent}] {message}")


@app.command("serve")
def board_serve(
    port: int = typer.Option(8080, "--port", "-p", help="Server port"),
    host: str = typer.Option("127.0.0.1", "--host", help="Server host"),
):
    """Start the board web server (dashboard)."""
    import subprocess
    import sys

    try:
        from agentteam.board.server import run_server
        import threading

        server_thread = threading.Thread(target=lambda: run_server(host, port), daemon=True)
        server_thread.start()
        console.print(f"[green]Board server started at http://{host}:{port}[/green]")
        console.print("[dim]Press Ctrl+C to stop[/dim]")

        import time
        while True:
            time.sleep(1)
    except ImportError:
        console.print("[red]Board server not available[/red]")
        raise typer.Exit(1)


@app.command("attach")
def board_attach(
    team: str = typer.Argument(..., help="Team name"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent name"),
):
    """Attach to an agent's terminal session (tmux attach)."""
    import subprocess

    if not agent:
        from agentteam.identity import AgentIdentity
        agent = AgentIdentity.from_env().agent_name

    try:
        subprocess.run(["tmux", "attach-session", "-t", f"agentteam-{team}-{agent}"], check=True)
    except subprocess.CalledProcessError:
        console.print(f"[red]No tmux session found for agent '{agent}'[/red]")
        raise typer.Exit(1)
    except FileNotFoundError:
        console.print("[red]tmux not found. Install tmux to use attach.[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
