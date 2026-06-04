"""
Agent Management Commands

Provides agent lifecycle operations: spawn, list, info, health, restart, pause, resume, kill.
"""

from __future__ import annotations

import datetime
import json
import os
import time
import uuid
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from agentteam import __version__

app = typer.Typer(help="Agent lifecycle management commands")
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


def _format_duration(duration: datetime.timedelta) -> str:
    """Format a duration as human-readable string."""
    total_seconds = int(duration.total_seconds())
    if total_seconds < 60:
        return f"{total_seconds}s"
    elif total_seconds < 3600:
        mins = total_seconds // 60
        secs = total_seconds % 60
        return f"{mins}m {secs}s"
    elif total_seconds < 86400:
        hours = total_seconds // 3600
        mins = (total_seconds % 3600) // 60
        return f"{hours}h {mins}m"
    else:
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        return f"{days}d {hours}h"


# ============================================================================
# Spawn Command
# ============================================================================


@app.command("spawn")
def spawn_agent(
    backend: Optional[str] = typer.Argument(
        None, help="Backend: auto (default), tmux, subprocess, openclaw_api, or openclaw_sdk"
    ),
    command: Optional[list[str]] = typer.Argument(None, help="Command and arguments to run (default: openclaw)"),
    team: Optional[str] = typer.Option(None, "--team", "-t", help="Team name"),
    agent_name: Optional[str] = typer.Option(None, "--agent-name", "-n", help="Agent name"),
    agent_type: str = typer.Option("general-purpose", "--agent-type", help="Agent type"),
    task: Optional[str] = typer.Option(None, "--task", help="Task to assign (becomes the agent's initial prompt)"),
    workspace: Optional[bool] = typer.Option(
        None,
        "--workspace/--no-workspace",
        "-w",
        help="Create isolated git worktree (default: auto)",
    ),
    repo: Optional[str] = typer.Option(None, "--repo", help="Git repo path (default: cwd)"),
    skip_permissions: Optional[bool] = typer.Option(
        None,
        "--skip-permissions/--no-skip-permissions",
        help="Skip tool approval for claude (default: from config, true)",
    ),
    resume: bool = typer.Option(False, "--resume", "-r", help="Resume previous session if available"),
    openclaw_agent: Optional[str] = typer.Option(
        None,
        "--openclaw-agent",
        help="OpenClaw agent id to use (routes to a specific agent config/model)",
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Suppress max-agent warnings"),
    model: Optional[str] = typer.Option(
        None, "--model", "-m", help="Model alias or ID (passed to backend via --model)"
    ),
    parent: Optional[str] = typer.Option(
        None, "--parent", "-p", help="Parent agent name (for parent-child lifecycle management)"
    ),
    on_ready: Optional[str] = typer.Option(
        None, "--on-ready", help="Command or message to execute after agent is ready (post-ready hook)"
    ),
):
    """Spawn a new agent process with identity + task as its initial prompt.

    Defaults: tmux backend, openclaw command, git worktree isolation, skip-permissions on.
    """
    from agentteam.config import get_effective
    from agentteam.spawn import get_backend

    # Resolve defaults from config
    if backend is None:
        backend, _ = get_effective("default_backend")
        backend = backend or "auto"
    if not command:
        command = ["openclaw"]

    _team = team or "default"
    _name = agent_name or f"agent-{uuid.uuid4().hex[:6]}"
    _id = uuid.uuid4().hex[:12]

    # Check agent count against recommended max
    if not force:
        from agentteam.spawn.registry import get_registry
        from agentteam.templates import DEFAULT_MAX_AGENTS, check_agent_count

        current_count = len(get_registry(_team))
        warning = check_agent_count(current_count, max_agents=DEFAULT_MAX_AGENTS)
        if warning:
            console.print(f"[yellow]{warning}[/yellow]")

    # Resolve skip_permissions from config
    if skip_permissions is None:
        sp_val, _ = get_effective("skip_permissions")
        skip_permissions = str(sp_val).lower() not in ("false", "0", "no", "")

    try:
        be = get_backend(backend)
    except ValueError as e:
        _output({"error": str(e)}, lambda d: console.print(f"[red]{d['error']}[/red]"))
        raise typer.Exit(1)

    # Workspace: resolve from flag or config
    _is_sdk_backend = backend in ("openclaw_sdk", "openclaw_api", "sdk")
    if _is_sdk_backend:
        workspace = False
        ws_mode = "never (SDK backend)"
    cwd = None
    ws_branch = ""
    ws_mgr = None
    if workspace is None:
        ws_mode, _ = get_effective("workspace")
        ws_mode = ws_mode or "auto"
        workspace = ws_mode in ("auto", "always")
    elif workspace is False:
        ws_mode = "never"
    else:
        ws_mode = "always"

    repo_path = Path(repo or os.getcwd()).expanduser().resolve()

    from agentteam.workspace.manager import WorkspaceManager
    ws_mgr = WorkspaceManager(repo_path)

    if workspace and ws_mgr.is_git_repo():
        try:
            ws_branch = f"agent-{_name.replace("/", "-")}"
            ws_mgr.create_worktree(ws_branch)
            cwd = ws_mgr.get_worktree_path(ws_branch)
        except Exception as e:
            if force:
                console.print(f"[yellow]Workspace creation failed: {e}[/yellow]")
                workspace = False
            else:
                console.print(f"[red]Workspace creation failed: {e}[/red]")
                raise typer.Exit(1)

    # Build spawn kwargs
    kwargs = dict(
        team=_team,
        agent_name=_name,
        agent_id=_id,
        agent_type=agent_type,
        backend=backend,
        skip_permissions=skip_permissions,
        workspace=cwd,
        parent=parent,
    )
    if model:
        kwargs["model"] = model
    if openclaw_agent:
        kwargs["openclaw_agent"] = openclaw_agent
    if task:
        kwargs["task"] = task
    if resume:
        kwargs["resume"] = True
    if on_ready:
        kwargs["on_ready"] = on_ready

    try:
        process = be.spawn(command, **kwargs)
    except Exception as e:
        console.print(f"[red]Spawn failed: {e}[/red]")
        raise typer.Exit(1)

    # Register in agent registry
    from agentteam.spawn.registry import register_agent
    register_agent(
        team=_team,
        name=_name,
        agent_type=agent_type,
        backend=backend,
        started_at=time.time(),
        workspace=cwd,
        parent=parent,
    )

    # Report
    result = {
        "status": "spawned",
        "agentId": _id,
        "agentName": _name,
        "team": _team,
        "backend": backend,
        "pid": process.pid if hasattr(process, "pid") else None,
        "workspace": str(cwd) if cwd else None,
    }

    def _human(d):
        console.print(f"[green]✓[/green] Agent spawned: {d['agentName']}")
        console.print(f"  Team: {d['team']}")
        console.print(f"  Backend: {d['backend']}")
        console.print(f"  Workspace: {d['workspace'] or 'none'}")
        if d.get("pid"):
            console.print(f"  PID: {d['pid']}")

    _output(result, _human)


# ============================================================================
# Agent Commands (list, info, health, restart, pause, resume, kill)
# ============================================================================


@app.command("list")
def agent_list(
    team: Optional[str] = typer.Option(None, "--team", "-t", help="Team name (default: all teams)"),
    show_dead: bool = typer.Option(False, "--all", "-a", help="Include dead/stopped agents"),
    json_out: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List all agents with their status and runtime."""
    from agentteam.spawn.registry import get_registry, is_agent_alive

    if team:
        teams = [team]
    else:
        data_dir = Path(os.environ.get("AGENTTEAM_DATA_DIR", "~/.agentteam")).expanduser()
        teams = [d.name for d in data_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]

    all_agents = []
    for t in teams:
        registry = get_registry(t)
        for name, info in registry.items():
            is_alive = is_agent_alive(t, name)
            if not show_dead and not is_alive:
                continue

            started_at = info.get("started_at")
            if started_at:
                try:
                    start_dt = datetime.datetime.fromtimestamp(started_at)
                    runtime = datetime.datetime.now() - start_dt
                    runtime_str = _format_duration(runtime)
                except:
                    runtime_str = "unknown"
            else:
                runtime_str = "unknown"

            agent_data = {
                "team": t,
                "name": name,
                "type": info.get("agent_type", "unknown"),
                "status": "running" if is_alive else "stopped",
                "runtime": runtime_str,
                "started_at": info.get("started_at"),
                "session_key": info.get("session_key", ""),
            }
            all_agents.append(agent_data)

    if json_out or _json_output:
        _output({"agents": all_agents, "total": len(all_agents)})
    else:
        if not all_agents:
            console.print("[yellow]No agents found.[/yellow]")
            return

        table = Table(title=f"[bold]Agent List ({len(all_agents)} agents)[/bold]", box=box.ROUNDED, show_lines=True)
        table.add_column("Team", style="cyan", no_wrap=True)
        table.add_column("Agent", style="bold", no_wrap=True)
        table.add_column("Type", style="dim")
        table.add_column("Status", justify="center")
        table.add_column("Runtime", justify="right", style="green")

        for i, a in enumerate(all_agents):
            status_style = "[bold green]" if a["status"] == "running" else "[bold red]"
            table.add_row(
                a["team"],
                a["name"],
                a["type"],
                f"{status_style}{a['status']}[/]",
                a["runtime"],
            )

        console.print(table)


@app.command("list-types")
def agent_list_types():
    """List available agent types."""
    from agentteam.spawn import AVAILABLE_BACKENDS

    types = [{"id": name, "description": be.__doc__ or name} for name, be in AVAILABLE_BACKENDS.items()]

    def _human(data):
        table = Table(title="Available Agent Types")
        table.add_column("Backend", style="cyan")
        table.add_column("Description")
        for t in data:
            table.add_row(t["id"], t["description"])
        console.print(table)

    _output(types, _human)


@app.command("info")
def agent_info(
    name: str = typer.Argument(..., help="Agent name"),
    team: Optional[str] = typer.Option(None, "--team", "-t", help="Team name"),
):
    """Show detailed agent information."""
    from agentteam.spawn.registry import get_agent_info, is_agent_alive

    actual_team = team
    if not actual_team:
        data_dir = Path(os.environ.get("AGENTTEAM_DATA_DIR", "~/.agentteam")).expanduser()
        for t_dir in data_dir.iterdir():
            if t_dir.is_dir() and not t_dir.name.startswith("."):
                info = get_agent_info(t_dir.name, name)
                if info:
                    actual_team = t_dir.name
                    break

    if not actual_team:
        console.print(f"[red]Agent '{name}' not found.[/red]")
        raise typer.Exit(1)

    info = get_agent_info(actual_team, name)
    if not info:
        console.print(f"[red]Agent '{name}' not found in team '{actual_team}'.[/red]")
        raise typer.Exit(1)

    is_alive = is_agent_alive(actual_team, name)

    data = {
        "name": name,
        "team": actual_team,
        "agentType": info.get("agent_type", "unknown"),
        "backend": info.get("backend", "unknown"),
        "status": "running" if is_alive else "stopped",
        "startedAt": datetime.datetime.fromtimestamp(info["started_at"]).isoformat() if info.get("started_at") else None,
        "workspace": info.get("workspace", ""),
        "parent": info.get("parent", ""),
    }

    def _human(d):
        console.print(Panel(f"[bold]{d['name']}[/bold] @ {d['team']}", expand=False))
        console.print(f"  Type:    {d['agentType']}")
        console.print(f"  Backend: {d['backend']}")
        console.print(f"  Status:  {d['status']}")
        if d.get("startedAt"):
            console.print(f"  Started: {d['startedAt']}")
        if d.get("workspace"):
            console.print(f"  Workspace: {d['workspace']}")
        if d.get("parent"):
            console.print(f"  Parent: {d['parent']}")

    _output(data, _human)


@app.command("health")
def agent_health(
    name: str = typer.Argument(..., help="Agent name"),
    team: Optional[str] = typer.Option(None, "--team", "-t", help="Team name"),
):
    """Check agent health status."""
    from agentteam.spawn.registry import get_agent_info, is_agent_alive

    actual_team = team
    if not actual_team:
        data_dir = Path(os.environ.get("AGENTTEAM_DATA_DIR", "~/.agentteam")).expanduser()
        for t_dir in data_dir.iterdir():
            if t_dir.is_dir() and not t_dir.name.startswith("."):
                info = get_agent_info(t_dir.name, name)
                if info:
                    actual_team = t_dir.name
                    break

    if not actual_team:
        console.print(f"[red]Agent '{name}' not found.[/red]")
        raise typer.Exit(1)

    is_alive = is_agent_alive(actual_team, name)
    status = "healthy" if is_alive else "unreachable"
    color = "green" if is_alive else "red"

    _output(
        {"name": name, "team": actual_team, "status": status, "alive": is_alive},
        lambda d: console.print(f"[{color}]{d['status'].upper()}[/{color}] - {d['name']} @ {d['team']}"),
    )


@app.command("restart")
def agent_restart(
    name: str = typer.Argument(..., help="Agent name"),
    team: Optional[str] = typer.Option(None, "--team", "-t", help="Team name"),
):
    """Restart an agent (kill and respawn)."""
    from agentteam.spawn.registry import get_agent_info, is_agent_alive

    actual_team = team
    if not actual_team:
        data_dir = Path(os.environ.get("AGENTTEAM_DATA_DIR", "~/.agentteam")).expanduser()
        for t_dir in data_dir.iterdir():
            if t_dir.is_dir() and not t_dir.name.startswith("."):
                info = get_agent_info(t_dir.name, name)
                if info:
                    actual_team = t_dir.name
                    break

    if not actual_team:
        console.print(f"[red]Agent '{name}' not found.[/red]")
        raise typer.Exit(1)

    info = get_agent_info(actual_team, name)
    if not info:
        console.print(f"[red]Agent '{name}' not found in team '{actual_team}'.[/red]")
        raise typer.Exit(1)

    console.print(f"[yellow]Restarting '{name}'...[/yellow]")

    # Kill first
    from agentteam.spawn import get_backend
    be = get_backend(info.get("backend", "auto"))
    be.terminate(actual_team, name)

    # Respawn
    import subprocess
    cmd = ["openclaw"]  # Default command
    from agentteam.spawn.registry import register_agent
    import time
    new_id = uuid.uuid4().hex[:12]
    register_agent(
        team=actual_team,
        name=name,
        agent_type=info.get("agent_type", "general-purpose"),
        backend=info.get("backend", "auto"),
        started_at=time.time(),
        workspace=info.get("workspace"),
    )

    _output(
        {"status": "restarted", "name": name, "team": actual_team, "agentId": new_id},
        lambda d: console.print(f"[green]✓[/green] Agent restarted: {d['name']} (id: {d['agentId']})"),
    )


@app.command("pause")
def agent_pause(
    name: str = typer.Argument(..., help="Agent name"),
    team: Optional[str] = typer.Option(None, "--team", "-t", help="Team name"),
):
    """Pause an agent (send SIGSTOP)."""
    import subprocess
    import locale

    actual_team = team
    if not actual_team:
        data_dir = Path(os.environ.get("AGENTTEAM_DATA_DIR", "~/.agentteam")).expanduser()
        for t_dir in data_dir.iterdir():
            if t_dir.is_dir() and not t_dir.name.startswith("."):
                from agentteam.spawn.registry import get_agent_info
                info = get_agent_info(t_dir.name, name)
                if info:
                    actual_team = t_dir.name
                    break

    if not actual_team:
        console.print(f"[red]Agent '{name}' not found.[/red]")
        raise typer.Exit(1)

    # Get session key for SDK agents
    from agentteam.spawn.registry import get_agent_info
    info = get_agent_info(actual_team, name)
    session_key = info.get("session_key") if info else None

    if session_key:
        # SDK agent - send pause signal via gateway
        import json
        params = json.dumps({"key": session_key, "message": "pause"}, ensure_ascii=False)
        cmd = ["cmd", "/c", "openclaw", "gateway", "call", "sessions.send", "--params", params]
        result = subprocess.run(cmd, capture_output=True, timeout=10)
        if result.returncode == 0:
            console.print(f"[green]✓[/green] Pause signal sent to '{name}'")
        else:
            console.print(f"[red]✗ Failed to send pause signal[/red]")
            raise typer.Exit(1)
    else:
        console.print(f"[yellow]Pause not supported for non-SDK agents[/yellow]")


@app.command("resume")
def agent_resume(
    name: str = typer.Argument(..., help="Agent name"),
    team: Optional[str] = typer.Option(None, "--team", "-t", help="Team name"),
):
    """Resume a paused agent (send SIGCONT)."""
    import subprocess
    import locale

    actual_team = team
    if not actual_team:
        data_dir = Path(os.environ.get("AGENTTEAM_DATA_DIR", "~/.agentteam")).expanduser()
        for t_dir in data_dir.iterdir():
            if t_dir.is_dir() and not t_dir.name.startswith("."):
                from agentteam.spawn.registry import get_agent_info
                info = get_agent_info(t_dir.name, name)
                if info:
                    actual_team = t_dir.name
                    break

    if not actual_team:
        console.print(f"[red]Agent '{name}' not found.[/red]")
        raise typer.Exit(1)

    from agentteam.spawn.registry import get_agent_info
    info = get_agent_info(actual_team, name)
    session_key = info.get("session_key") if info else None

    if session_key:
        import json
        params = json.dumps({"key": session_key, "message": "resume"}, ensure_ascii=False)
        cmd = ["cmd", "/c", "openclaw", "gateway", "call", "sessions.send", "--params", params]
        result = subprocess.run(cmd, capture_output=True, timeout=10)
        if result.returncode == 0:
            console.print(f"[green]✓[/green] Resume signal sent to '{name}'")
        else:
            console.print(f"[red]✗ Failed to send resume signal[/red]")
            raise typer.Exit(1)
    else:
        console.print(f"[yellow]Resume not supported for non-SDK agents[/yellow]")


@app.command("kill")
def agent_kill(
    name: str = typer.Argument(..., help="Agent name"),
    team: Optional[str] = typer.Option(None, "--team", "-t", help="Team name"),
    force: bool = typer.Option(False, "--force", "-f", help="Force kill without graceful shutdown"),
):
    """Kill an agent immediately (ungraceful termination)."""
    from agentteam.spawn.registry import unregister_agent, get_agent_info, is_agent_alive
    from agentteam.spawn import get_backend

    actual_team = team
    if not actual_team:
        data_dir = Path(os.environ.get("AGENTTEAM_DATA_DIR", "~/.agentteam")).expanduser()
        for t_dir in data_dir.iterdir():
            if t_dir.is_dir() and not t_dir.name.startswith("."):
                info = get_agent_info(t_dir.name, name)
                if info:
                    actual_team = t_dir.name
                    break

    if not actual_team:
        console.print(f"[red]Agent '{name}' not found.[/red]")
        raise typer.Exit(1)

    info = get_agent_info(actual_team, name)
    if not info:
        console.print(f"[red]Agent '{name}' not found in team '{actual_team}'.[/red]")
        raise typer.Exit(1)

    if not is_agent_alive(actual_team, name) and not force:
        console.print(f"[yellow]Agent '{name}' is not running. Use --force to kill anyway.[/yellow]")
        return

    console.print(f"[yellow]Killing agent '{name}'...[/yellow]")

    be = get_backend(info.get("backend", "auto"))
    be.terminate(actual_team, name)
    unregister_agent(actual_team, name)

    _output(
        {"status": "killed", "name": name, "team": actual_team},
        lambda d: console.print(f"[green]✓[/green] Agent killed: {d['name']}"),
    )


if __name__ == "__main__":
    app()
