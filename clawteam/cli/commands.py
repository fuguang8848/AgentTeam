"""CLI commands for clawteam - framework-agnostic multi-agent coordination."""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from clawteam import __version__
from clawteam.team.models import _now_iso

app = typer.Typer(
    name="clawteam",
    help="Framework-agnostic multi-agent coordination CLI",
    no_args_is_help=True,
)
console = Console()


# ---------------------------------------------------------------------------
# Global options via callback
# ---------------------------------------------------------------------------

_json_output: bool = False
_data_dir: str | None = None


def _version_callback(value: bool):
    if value:
        console.print(f"clawteam v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Output JSON instead of human-readable text.",
    ),
    data_dir: Optional[str] = typer.Option(
        None,
        "--data-dir",
        help="Override data directory (default: ~/.clawteam).",
    ),
    transport: Optional[str] = typer.Option(
        None,
        "--transport",
        help="Transport backend: file or p2p.",
    ),
):
    """clawteam - Framework-agnostic multi-agent coordination CLI."""
    global _json_output, _data_dir
    _json_output = json_out
    if data_dir:
        import os

        os.environ["CLAWTEAM_DATA_DIR"] = data_dir
        _data_dir = data_dir
    if transport:
        import os

        os.environ["CLAWTEAM_TRANSPORT"] = transport


def _dump(model) -> dict:
    """Dump a pydantic model to dict with by_alias and exclude_none."""
    return json.loads(model.model_dump_json(by_alias=True, exclude_none=True))


def _output(data: dict | list, human_fn=None):
    """Output data as JSON or human-readable."""
    if _json_output:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    elif human_fn:
        human_fn(data)
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))


def _deliver_to_running_agent(agent_name: str, team_name: str, content: str, from_agent: str) -> bool:
    """
    Try to deliver a message directly to a running OpenClaw SDK agent.

    This enables immediate message delivery to agents spawned via the OpenClaw SDK backend,
    bypassing the file-based inbox for real-time communication.

    Also broadcasts a task_assigned activity to the board server for real-time monitoring.

    Args:
        agent_name: Target agent name
        team_name: Team name
        content: Message content
        from_agent: Sender name

    Returns:
        True if the agent was found and message was delivered,
        False if the agent is not a running SDK agent (caller should fall back to file inbox).
    """
    import locale
    import os
    import json
    import subprocess
    from pathlib import Path
    import urllib.request
    import urllib.error

    # Read the running agents registry
    data_dir = Path(os.environ.get("CLAWTEAM_DATA_DIR", "~/.clawteam")).expanduser()
    registry_file = data_dir / "running_agents.json"

    if not registry_file.exists():
        return False

    try:
        registry = json.loads(registry_file.read_text(encoding="utf-8"))
        agents = registry.get("agents", {})

        if agent_name not in agents:
            return False

        agent_info = agents[agent_name]
        session_key = agent_info.get("session_key")

        if not session_key:
            return False

        # Build the task message
        task_msg = (
            f"## New Task from {from_agent}\n\n{content}\n\n"
            f"Execute this task and report completion to your leader when done.\n"
            f'After completing, ask your leader: "Task done. Should I exit or await new tasks?"'
        )

        # Escape < > for cmd.exe (redirection operators)
        task_msg_escaped = task_msg.replace("<", "^<").replace(">", "^>")

        # Get Gateway token
        gateway_token = os.environ.get("OPENCLAW_GATEWAY_TOKEN", "")

        # Use openclaw gateway call CLI to send message
        encoding = locale.getpreferredencoding(False) or "utf-8"
        cmd = ["cmd", "/c", "openclaw", "gateway", "call", "sessions.send"]
        params = json.dumps({"key": session_key, "message": task_msg}, ensure_ascii=False)
        params_escaped = params.replace("<", "^<").replace(">", "^>")
        cmd.extend(["--params", params_escaped])
        if gateway_token:
            cmd.extend(["--token", gateway_token])

        result = subprocess.run(cmd, capture_output=True, timeout=30)

        if result.returncode != 0:
            # Log error for debugging
            import logging
            logger = logging.getLogger("clawteam")
            stderr = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
            logger.warning(f"Gateway sessions.send failed: {stderr}")
            return False

        # Broadcast task_assigned activity to board server
        _broadcast_activity_to_board(
            agent_name=agent_name,
            team_name=team_name,
            status="task_assigned",
            message=f"Task assigned to {agent_name} by {from_agent}",
        )

        return True

    except subprocess.TimeoutExpired:
        import logging
        logger = logging.getLogger("clawteam")
        logger.warning(f"Gateway sessions.send timed out for agent {agent_name}")
        return False
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        import logging
        logger = logging.getLogger("clawteam")
        logger.warning(f"Failed to deliver message to agent {agent_name}: {e}")
        return False


def _broadcast_activity_to_board(agent_name: str, team_name: str, status: str, message: str) -> None:
    """
    Broadcast an activity event to the board server.

    This allows the CLI to send activity events that will be picked up by the board monitor.
    """
    import os
    import urllib.request
    import urllib.error

    board_port = os.environ.get("CLAWTEAM_BOARD_PORT", "8080")
    board_url = f"http://127.0.0.1:{board_port}/api/agents/activity"

    activity_data = {
        "team_name": team_name,
        "agent_name": agent_name,
        "status": status,
        "message": message,
    }

    try:
        req = urllib.request.Request(
            board_url,
            data=json.dumps(activity_data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5):
            pass  # Success
    except (urllib.error.URLError, Exception):
        pass  # Silently fail if board server is not running


# ============================================================================
# Config Commands
# ============================================================================

config_app = typer.Typer(help="Configuration management")
app.add_typer(config_app, name="config")


@config_app.command("show")
def config_show():
    """Show all configuration settings and their sources."""
    from clawteam.config import get_effective

    keys = [
        "data_dir",
        "user",
        "default_team",
        "transport",
        "workspace",
        "default_backend",
        "skip_permissions",
    ]
    data = {}
    for k in keys:
        val, source = get_effective(k)
        data[k] = {"value": val, "source": source}

    def _human(d):
        table = Table(title="Configuration")
        table.add_column("Key", style="cyan")
        table.add_column("Value")
        table.add_column("Source", style="dim")
        for k in keys:
            v = d[k]["value"]
            table.add_row(k, str(v) if v != "" else "(empty)", d[k]["source"])
        console.print(table)

    _output(data, _human)


@config_app.command("init")
def config_init(
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing config"),
):
    """Create a default configuration file in ~/.clawteam/config.yaml."""
    from pathlib import Path
    import yaml

    config_dir = Path.home() / ".clawteam"
    config_file = config_dir / "config.yaml"

    if config_file.exists() and not force:
        console.print(f"[yellow]Config file already exists at {config_file}[/yellow]")
        console.print("Use --force to overwrite.")
        raise typer.Exit(1)

    # Default configuration
    default_config = {
        "# ClawTeam Configuration": None,
        "# Version": "0.6.0",
        "# Documentation": "https://github.com/YintaTriss/ClawTeam-OpenClaw",
        "# Default settings": None,
        "data_dir": "~/.clawteam",
        "default_team": None,  # No default team
        "default_backend": "auto",
        "# Agent settings": None,
        "agents": {
            "max_concurrent": 10,
            "spawn_timeout": 60,
            "heartbeat_interval": 30,
        },
        "# Gateway settings": None,
        "gateway": {
            "host": "127.0.0.1",
            "port": 18789,
            "timeout": 30,
        },
        "# Board server settings": None,
        "board": {
            "host": "127.0.0.1",
            "port": 8080,
        },
    }

    # Create directory if needed
    config_dir.mkdir(parents=True, exist_ok=True)

    # Write config file
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)

    console.print(f"[green]✓[/green] Created default config at {config_file}")
    console.print(f"[dim]Edit this file to customize your ClawTeam settings.[/dim]")


@config_app.command("set")
def config_set(
    key: str = typer.Argument(
        ...,
        help="Config key (e.g. data_dir, user, transport, workspace, default_backend, skip_permissions)",
    ),
    value: str = typer.Argument(..., help="Config value"),
):
    """Persistently set a configuration value."""
    from clawteam.config import ClawTeamConfig, load_config, save_config

    valid_keys = set(ClawTeamConfig.model_fields.keys())
    if key not in valid_keys:
        console.print(f"[red]Invalid key '{key}'. Valid: {', '.join(sorted(valid_keys))}[/red]")
        raise typer.Exit(1)

    cfg = load_config()
    # Handle boolean fields (skip_permissions)
    field_info = ClawTeamConfig.model_fields[key]
    if field_info.annotation is bool:
        setattr(cfg, key, value.lower() in ("true", "1", "yes"))
    else:
        setattr(cfg, key, value)
    save_config(cfg)

    _output(
        {"status": "saved", "key": key, "value": value},
        lambda d: console.print(f"[green]OK[/green] {key} = {value}"),
    )


@config_app.command("get")
def config_get(
    key: str = typer.Argument(
        ...,
        help="Config key (e.g. data_dir, user, transport, workspace, default_backend, skip_permissions)",
    ),
):
    """Get the effective value of a config key."""
    from clawteam.config import ClawTeamConfig, get_effective

    valid_keys = set(ClawTeamConfig.model_fields.keys())
    if key not in valid_keys:
        console.print(f"[red]Invalid key '{key}'. Valid: {', '.join(sorted(valid_keys))}[/red]")
        raise typer.Exit(1)

    val, source = get_effective(key)
    _output(
        {"key": key, "value": val, "source": source},
        lambda d: console.print(f"{key} = {val or '(empty)'}  [dim]({source})[/dim]"),
    )


@config_app.command("health")
def config_health():
    """Health check for the data directory (shared directory diagnostics)."""
    import os
    import time as _time

    from clawteam.config import get_effective
    from clawteam.team.manager import TeamManager
    from clawteam.team.models import get_data_dir

    checks = {}

    # Data directory
    data_dir = get_data_dir()
    val, source = get_effective("data_dir")
    checks["data_dir"] = str(data_dir)
    checks["data_dir_source"] = source

    # Exists
    checks["exists"] = data_dir.exists()

    # Writable
    try:
        test_file = data_dir / ".health-check"
        start = _time.monotonic()
        test_file.write_text("ok", encoding="utf-8")
        content = test_file.read_text(encoding="utf-8")
        elapsed = (_time.monotonic() - start) * 1000
        test_file.unlink()
        checks["writable"] = content == "ok"
        checks["latency_ms"] = round(elapsed, 2)
    except Exception as e:
        checks["writable"] = False
        checks["latency_ms"] = -1
        checks["write_error"] = str(e)

    # Mount point check
    try:
        checks["is_mount"] = os.path.ismount(str(data_dir))
    except Exception:
        checks["is_mount"] = False

    # Teams count
    try:
        teams = TeamManager.discover_teams()
        checks["teams_count"] = len(teams)
    except Exception:
        checks["teams_count"] = 0

    # User
    user_val, user_source = get_effective("user")
    checks["user"] = user_val
    checks["user_source"] = user_source

    def _human(d):
        console.print(f"\nData Directory: [cyan]{d['data_dir']}[/cyan]  [dim]({d['data_dir_source']})[/dim]")
        console.print(f"  Exists:     {'[green]yes[/green]' if d['exists'] else '[red]no[/red]'}")
        console.print(f"  Writable:   {'[green]yes[/green]' if d['writable'] else '[red]no[/red]'}")
        if d["latency_ms"] >= 0:
            color = "green" if d["latency_ms"] < 50 else "yellow" if d["latency_ms"] < 200 else "red"
            console.print(f"  Latency:    [{color}]{d['latency_ms']:.1f} ms[/{color}]")
        console.print(
            f"  Mount point: {'[yellow]yes (remote/shared)[/yellow]' if d['is_mount'] else '[dim]no (local)[/dim]'}"
        )
        console.print(f"  Teams:      {d['teams_count']}")
        console.print(f"  User:       {d['user'] or '(not set)'}  [dim]({d['user_source']})[/dim]")

    _output(checks, _human)


# ============================================================================
# Template Commands
# ============================================================================

template_app = typer.Typer(help="Team template management")
app.add_typer(template_app, name="template")


@template_app.command("list")
def template_list():
    """List all available team templates."""
    from clawteam.templates import list_templates

    templates = list_templates()

    def _human(data):
        table = Table(title="Available Templates")
        table.add_column("Name", style="cyan")
        table.add_column("Description")
        table.add_column("Source", style="dim")
        for t in data:
            table.add_row(t["name"], t["description"], t["source"])
        console.print(table)
        console.print("\n[dim]Run `clawteam template show <name>` for details.[/dim]")

    _output(templates, _human)


@template_app.command("show")
def template_show(
    name: str = typer.Argument(..., help="Template name"),
):
    """Show detailed information about a template."""
    from clawteam.templates import load_template

    try:
        tmpl = load_template(name)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    def _human(t):
        console.print(f"\n[bold cyan]{t.name}[/bold cyan]")
        console.print(f"{t.description}\n")

        # Leader
        console.print(f"[bold]Leader:[/bold] {t.leader.name} ({t.leader.type})")
        if t.leader.model:
            console.print(f"  Model: {t.leader.model}")
        console.print(
            f"  [dim]{t.leader.task[:80]}...[/dim]" if len(t.leader.task) > 80 else f"  [dim]{t.leader.task}[/dim]"
        )
        console.print()

        # Agents
        console.print(f"[bold]Agents ({len(t.agents)}):[/bold]")
        for i, agent in enumerate(t.agents, 1):
            console.print(f"  {i}. {agent.name} ({agent.type})")
            if agent.model:
                console.print(f"     Model: {agent.model}")
            if hasattr(agent, "task_type") and agent.task_type:
                console.print(f"     Task Type: {agent.task_type}")
            task_preview = agent.task[:60] + "..." if len(agent.task) > 60 else agent.task
            console.print(f"     [dim]{task_preview}[/dim]")
        console.print()

        # Tasks
        if t.tasks:
            console.print(f"[bold]Tasks ({len(t.tasks)}):[/bold]")
            for i, task in enumerate(t.tasks, 1):
                console.print(f"  {i}. {task.subject} - {task.description}")
        console.print()

        # Meta
        console.print(f"[dim]Backend: {t.backend} | Command: {' '.join(t.command)} | Max Agents: {t.max_agents}[/dim]")

    _output(_dump(tmpl), _human)


# ============================================================================
# Team Commands
# ============================================================================

team_app = typer.Typer(help="Team management commands")
app.add_typer(team_app, name="team")


@team_app.command("spawn-team")
def team_spawn_team(
    name: str = typer.Argument(..., help="Team name"),
    description: str = typer.Option("", "--description", "-d", help="Team description"),
    agent_name: str = typer.Option("leader", "--agent-name", "-n", help="Leader agent name"),
    agent_type: str = typer.Option("leader", "--agent-type", help="Leader agent type"),
):
    """Create a new team and register the leader (spawnTeam)."""
    from clawteam.identity import AgentIdentity
    from clawteam.team.manager import TeamManager

    identity = AgentIdentity.from_env()
    leader_id = identity.agent_id
    leader_name = agent_name or identity.agent_name

    try:
        TeamManager.create_team(
            name=name,
            leader_name=leader_name,
            leader_id=leader_id,
            description=description,
            user=identity.user,
        )
        result = {
            "status": "created",
            "team": name,
            "leadAgentId": leader_id,
            "leaderName": leader_name,
        }
        if identity.user:
            result["user"] = identity.user
        _output(
            result,
            lambda d: (
                console.print(f"[green]OK[/green] Team '{name}' created"),
                console.print(f"  Leader: {leader_name} (id: {leader_id})"),
            ),
        )
    except ValueError as e:
        if _json_output:
            print(json.dumps({"error": str(e)}))
        else:
            console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@team_app.command("create")
def team_create(
    name: str = typer.Argument(..., help="Team name"),
    template: str = typer.Option("", "--template", "-t", help="Template name to use"),
    description: str = typer.Option("", "--description", "-d", help="Team description"),
):
    """Create a new team, optionally from a template (createTeam)."""
    from clawteam.identity import AgentIdentity
    from clawteam.team.manager import TeamManager
    from clawteam.templates import load_template

    identity = AgentIdentity.from_env()
    leader_id = identity.agent_id

    # Load template if specified
    tmpl = None
    if template:
        try:
            tmpl = load_template(template)
        except FileNotFoundError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    # Determine leader name and description
    if tmpl:
        leader_name = tmpl.leader.name
        desc = description or tmpl.description
        backend = tmpl.backend
        command = tmpl.command
    else:
        leader_name = identity.agent_name or "leader"
        desc = description
        backend = "auto"  # Auto-detect best backend (tmux on Unix, subprocess/OpenClaw SDK on Windows)
        command = ["openclaw"]

    try:
        TeamManager.create_team(
            name=name,
            leader_name=leader_name,
            leader_id=leader_id,
            description=desc,
            user=identity.user,
        )

        result = {
            "status": "created",
            "team": name,
            "leaderName": leader_name,
            "leadAgentId": leader_id,
            "backend": backend,
            "command": command,
        }
        if tmpl:
            result["template"] = template
            result["agents"] = [{"name": a.name, "type": a.type} for a in tmpl.agents]
            result["tasks"] = [{"subject": t.subject, "owner": t.owner} for t in tmpl.tasks]

        def _human(d):
            console.print(f"[green]OK[/green] Team '{name}' created")
            console.print(f"  Leader: {d['leaderName']} (id: {d['leadAgentId']})")
            console.print(f"  Backend: {d['backend']}")
            if d.get("template"):
                console.print(f"  Template: {d['template']}")
            if d.get("agents"):
                console.print(f"  Agents: {', '.join(a['name'] for a in d['agents'])}")
            if d.get("tasks"):
                console.print(f"  Tasks: {len(d['tasks'])} defined")

        _output(result, _human)

    except ValueError as e:
        if _json_output:
            print(json.dumps({"error": str(e)}))
        else:
            console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@team_app.command("discover")
def team_discover():
    """List all teams (discoverTeams)."""
    from clawteam.team.manager import TeamManager

    teams = TeamManager.discover_teams()

    def _human(data):
        if not data:
            console.print("[dim]No teams found[/dim]")
            return
        table = Table(title="Teams")
        table.add_column("Name", style="cyan")
        table.add_column("Description")
        table.add_column("Members", justify="right")
        for t in data:
            table.add_row(t["name"], t["description"], str(t["memberCount"]))
        console.print(table)

    _output(teams, _human)


@team_app.command("request-join")
def team_request_join(
    team: str = typer.Argument(..., help="Team name"),
    proposed_name: str = typer.Argument(..., help="Proposed agent name"),
    capabilities: str = typer.Option("", "--capabilities", "-c", help="Agent capabilities"),
    timeout: int = typer.Option(60, "--timeout", "-t", help="Timeout in seconds"),
):
    """Request to join a team (requestJoin). Blocks waiting for leader response."""
    from clawteam.identity import AgentIdentity
    from clawteam.team.mailbox import MailboxManager
    from clawteam.team.manager import TeamManager
    from clawteam.team.models import MessageType

    AgentIdentity.from_env()
    config = TeamManager.get_team(team)
    if not config:
        _output(
            {"error": f"Team '{team}' not found"},
            lambda d: console.print(f"[red]{d['error']}[/red]"),
        )
        raise typer.Exit(1)

    leader_inbox = TeamManager.get_leader_inbox(team)
    leader_name = TeamManager.get_leader_name(team)
    if not leader_name or not leader_inbox:
        _output({"error": "No leader found"}, lambda d: console.print(f"[red]{d['error']}[/red]"))
        raise typer.Exit(1)

    mailbox = MailboxManager(team)
    request_id = f"join-{uuid.uuid4().hex[:12]}"
    temp_inbox_name = f"_pending_{proposed_name}"

    mailbox.send(
        from_agent=proposed_name,
        to=leader_inbox,
        msg_type=MessageType.join_request,
        request_id=request_id,
        proposed_name=proposed_name,
        capabilities=capabilities or None,
    )

    if not _json_output:
        console.print(f"Join request sent to leader '{leader_name}'. Waiting for response...")

    start = time.time()
    while time.time() - start < timeout:
        messages = mailbox.receive(temp_inbox_name, limit=10)
        for msg in messages:
            if msg.request_id == request_id:
                if msg.type == MessageType.join_approved:
                    result = {
                        "status": "approved",
                        "requestId": request_id,
                        "assignedName": msg.assigned_name or proposed_name,
                        "agentId": msg.agent_id or "",
                        "teamName": team,
                    }
                    _output(
                        result,
                        lambda d: console.print(f"[green]Approved![/green] Joined as '{d['assignedName']}'"),
                    )
                    return
                elif msg.type == MessageType.join_rejected:
                    reason = msg.reason or msg.content or ""
                    _output(
                        {"status": "rejected", "requestId": request_id, "reason": reason},
                        lambda d: console.print(f"[red]Rejected.[/red] {reason}"),
                    )
                    raise typer.Exit(1)
        time.sleep(1.0)

    _output(
        {"status": "timeout", "requestId": request_id},
        lambda d: console.print("[yellow]Timeout waiting for response.[/yellow]"),
    )
    raise typer.Exit(1)


@team_app.command("approve-join")
def team_approve_join(
    team: str = typer.Argument(..., help="Team name"),
    request_id: str = typer.Argument(..., help="Join request ID"),
    assigned_name: Optional[str] = typer.Option(None, "--assigned-name", help="Override proposed name"),
):
    """Approve a join request (approveJoin)."""
    from clawteam.identity import AgentIdentity
    from clawteam.team.mailbox import MailboxManager
    from clawteam.team.manager import TeamManager
    from clawteam.team.models import MessageType

    identity = AgentIdentity.from_env()
    mailbox = MailboxManager(team)

    leader_inbox = TeamManager.get_leader_inbox(team) or identity.agent_name
    messages = mailbox.peek(leader_inbox)
    join_req = None
    for msg in messages:
        if msg.request_id == request_id and msg.type == MessageType.join_request:
            join_req = msg
            break

    proposed_name = join_req.proposed_name if join_req else f"agent-{request_id[:6]}"
    final_name = assigned_name or proposed_name
    new_agent_id = uuid.uuid4().hex[:12]

    try:
        TeamManager.add_member(
            team_name=team,
            member_name=final_name,
            agent_id=new_agent_id,
            agent_type="general-purpose",
            user=identity.user,
        )
    except ValueError:
        pass  # already a member

    temp_inbox_name = f"_pending_{proposed_name}"
    mailbox.send(
        from_agent=identity.agent_name,
        to=temp_inbox_name,
        msg_type=MessageType.join_approved,
        request_id=request_id,
        assigned_name=final_name,
        agent_id=new_agent_id,
        team_name=team,
    )

    # Schedule cleanup of the _pending_ inbox directory after the joining agent
    # has had time to consume the approval message. We do a best-effort immediate
    # cleanup here since the message was just delivered; the joining agent will
    # pick it up from the permanent inbox if it misses the temp one.
    import shutil

    from clawteam.team.models import get_data_dir

    pending_dir = get_data_dir() / "teams" / team / "inboxes" / temp_inbox_name
    if pending_dir.exists():
        try:
            shutil.rmtree(pending_dir)
        except OSError:
            pass

    _output(
        {
            "status": "approved",
            "requestId": request_id,
            "assignedName": final_name,
            "agentId": new_agent_id,
            "teamName": team,
        },
        lambda d: console.print(f"[green]OK[/green] Approved '{final_name}' (id: {new_agent_id})"),
    )


@team_app.command("reject-join")
def team_reject_join(
    team: str = typer.Argument(..., help="Team name"),
    request_id: str = typer.Argument(..., help="Join request ID"),
    reason: str = typer.Option("", "--reason", "-r", help="Rejection reason"),
):
    """Reject a join request (rejectJoin)."""
    from clawteam.identity import AgentIdentity
    from clawteam.team.mailbox import MailboxManager
    from clawteam.team.manager import TeamManager
    from clawteam.team.models import MessageType

    identity = AgentIdentity.from_env()
    mailbox = MailboxManager(team)

    leader_inbox = TeamManager.get_leader_inbox(team) or identity.agent_name
    messages = mailbox.peek(leader_inbox)
    proposed_name = None
    for msg in messages:
        if msg.request_id == request_id and msg.type == MessageType.join_request:
            proposed_name = msg.proposed_name
            break

    proposed_name = proposed_name or f"agent-{request_id[:6]}"
    temp_inbox_name = f"_pending_{proposed_name}"

    mailbox.send(
        from_agent=identity.agent_name,
        to=temp_inbox_name,
        msg_type=MessageType.join_rejected,
        request_id=request_id,
        reason=reason or None,
    )

    # Clean up the _pending_ inbox directory
    import shutil

    from clawteam.team.models import get_data_dir

    pending_dir = get_data_dir() / "teams" / team / "inboxes" / temp_inbox_name
    if pending_dir.exists():
        try:
            shutil.rmtree(pending_dir)
        except OSError:
            pass

    _output(
        {"status": "rejected", "requestId": request_id, "reason": reason},
        lambda d: console.print(f"[green]OK[/green] Rejected request {request_id}"),
    )


@team_app.command("cleanup")
def team_cleanup(
    team: str = typer.Argument(..., help="Team name"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete a team and all its data (cleanup)."""
    from clawteam.team.manager import TeamManager

    if not force and not _json_output:
        if not typer.confirm(f"Delete team '{team}' and all its data?"):
            raise typer.Abort()

    if TeamManager.cleanup(team):
        _output(
            {"status": "cleaned", "team": team},
            lambda d: console.print(f"[green]OK[/green] Team '{team}' deleted"),
        )
    else:
        _output(
            {"status": "not_found", "team": team},
            lambda d: console.print(f"[yellow]Team '{team}' not found[/yellow]"),
        )


def _workspace_cwd_from_info(repo: str | None, ws_info) -> str:
    from pathlib import Path as _Path

    cwd = ws_info.worktree_path
    subpath = getattr(ws_info, "repo_subpath", "") or ""
    if subpath:
        return str((_Path(ws_info.worktree_path) / subpath).resolve())
    if repo:
        requested_repo = _Path(repo).expanduser().resolve()
        repo_root = _Path(ws_info.repo_root).resolve()
        try:
            relative_repo = requested_repo.relative_to(repo_root)
        except ValueError:
            relative_repo = None
        if relative_repo and str(relative_repo) != ".":
            return str((_Path(ws_info.worktree_path) / relative_repo).resolve())
    return cwd


@team_app.command("status")
def team_status(
    team: str = typer.Argument(..., help="Team name"),
):
    """Show team status and members."""
    from clawteam.spawn.registry import is_agent_alive
    from clawteam.team.manager import TeamManager

    config = TeamManager.get_team(team)
    if not config:
        _output(
            {"error": f"Team '{team}' not found"},
            lambda d: console.print(f"[red]{d['error']}[/red]"),
        )
        raise typer.Exit(1)

    data = {
        "name": config.name,
        "description": config.description,
        "leadAgentId": config.lead_agent_id,
        "createdAt": config.created_at,
        "members": [
            {
                **m.model_dump(by_alias=True),
                "alive": is_agent_alive(team, m.name),
            }
            for m in config.members
        ],
    }

    def _human(d):
        console.print(f"\nTeam: [cyan]{d['name']}[/cyan]")
        if d["description"]:
            console.print(f"  {d['description']}")
        console.print(f"  Created: {d['createdAt'][:19]}")
        has_user = any(m.get("user") for m in d["members"])
        table = Table(title="Members")
        table.add_column("Name", style="cyan")
        if has_user:
            table.add_column("User", style="magenta")
        table.add_column("ID", style="dim")
        table.add_column("Type")
        table.add_column("Alive")
        table.add_column("Joined", style="dim")
        for m in d["members"]:
            row = [m.get("name", "")]
            if has_user:
                row.append(m.get("user", ""))
            alive = m.get("alive")
            alive_label = "yes" if alive is True else "no" if alive is False else "unknown"
            row.extend(
                [
                    m.get("agentId", ""),
                    m.get("agentType", ""),
                    alive_label,
                    (m.get("joinedAt") or "")[:19],
                ]
            )
            table.add_row(*row)
        console.print(table)

    _output(data, _human)


# ============================================================================
# Inbox Commands
# ============================================================================

inbox_app = typer.Typer(help="Inbox / messaging commands")
app.add_typer(inbox_app, name="inbox")


@inbox_app.command("send")
def inbox_send(
    team: str = typer.Argument(..., help="Team name"),
    to: str = typer.Argument(..., help="Recipient agent name"),
    content: str = typer.Argument(..., help="Message content"),
    key: Optional[str] = typer.Option(None, "--key", "-k", help="Optional routing key"),
    msg_type: str = typer.Option("message", "--type", help="Message type"),
    from_agent: Optional[str] = typer.Option(
        None, "--from", "-f", help="Override sender name (default: from env identity)"
    ),
):
    """Send a point-to-point message (write).

    Smart routing: If the recipient is a running OpenClaw SDK agent,
    the message is delivered directly via Gateway Sessions API for immediate receipt.
    Otherwise, it falls back to file-based inbox delivery.
    """
    from clawteam.identity import AgentIdentity
    from clawteam.team.mailbox import MailboxManager
    from clawteam.team.models import MessageType

    sender = from_agent or AgentIdentity.from_env().agent_name

    # Try to deliver directly to a running SDK agent first
    if _deliver_to_running_agent(to, team, content, sender):
        _output({}, lambda d: console.print(f"[green]OK[/green] Message sent directly to running agent '{to}'"))
        return

    # Fallback: deliver via file inbox
    mailbox = MailboxManager(team)
    mt = MessageType(msg_type)
    msg = mailbox.send(
        from_agent=sender,
        to=to,
        content=content,
        msg_type=mt,
        key=key,
    )
    data = _dump(msg)
    _output(data, lambda d: console.print(f"[green]OK[/green] Message sent to '{to}'"))


@inbox_app.command("broadcast")
def inbox_broadcast(
    team: str = typer.Argument(..., help="Team name"),
    content: str = typer.Argument(..., help="Message content"),
    key: Optional[str] = typer.Option(None, "--key", "-k", help="Optional routing key"),
    msg_type: str = typer.Option("broadcast", "--type", help="Message type"),
    from_agent: Optional[str] = typer.Option(
        None, "--from", "-f", help="Override sender name (default: from env identity)"
    ),
):
    """Broadcast a message to all team members (broadcast)."""
    from clawteam.identity import AgentIdentity
    from clawteam.team.mailbox import MailboxManager
    from clawteam.team.models import MessageType

    sender = from_agent or AgentIdentity.from_env().agent_name
    mailbox = MailboxManager(team)
    mt = MessageType(msg_type)
    messages = mailbox.broadcast(
        from_agent=sender,
        content=content,
        msg_type=mt,
        key=key,
    )
    data = {"count": len(messages), "recipients": [m.to for m in messages]}
    _output(data, lambda d: console.print(f"[green]OK[/green] Broadcast to {d['count']} agents"))


@inbox_app.command("receive")
def inbox_receive(
    team: str = typer.Argument(..., help="Team name"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent name (default: from env)"),
    limit: int = typer.Option(10, "--limit", "-l", help="Max messages to receive"),
):
    """Receive and consume messages from inbox."""
    from clawteam.identity import AgentIdentity
    from clawteam.team.mailbox import MailboxManager
    from clawteam.team.manager import TeamManager

    identity = AgentIdentity.from_env()
    agent_name = TeamManager.resolve_inbox(team, agent or identity.agent_name, identity.user)
    mailbox = MailboxManager(team)
    messages = mailbox.receive(agent_name, limit=limit)

    data = [_dump(m) for m in messages]

    def _human(msgs):
        if not msgs:
            console.print("[dim]No messages[/dim]")
            return
        for m in msgs:
            console.print(
                f"[{m.get('timestamp', '')[:19]}] "
                f"[cyan]{m.get('type', '')}[/cyan] "
                f"from={m.get('from', '')} : {m.get('content', '')}"
            )

    _output(data, _human)


@inbox_app.command("peek")
def inbox_peek(
    team: str = typer.Argument(..., help="Team name"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent name (default: from env)"),
):
    """Peek at messages without consuming them."""
    from clawteam.identity import AgentIdentity
    from clawteam.team.mailbox import MailboxManager
    from clawteam.team.manager import TeamManager

    identity = AgentIdentity.from_env()
    agent_name = TeamManager.resolve_inbox(team, agent or identity.agent_name, identity.user)
    mailbox = MailboxManager(team)
    messages = mailbox.peek(agent_name)

    data = {"count": len(messages), "messages": [_dump(m) for m in messages]}

    def _human(d):
        console.print(f"Pending messages: {d['count']}")
        for m in d["messages"]:
            console.print(
                f"  [{m.get('timestamp', '')[:19]}] "
                f"[cyan]{m.get('type', '')}[/cyan] "
                f"from={m.get('from', '')} : {(m.get('content') or '')[:80]}"
            )

    _output(data, _human)


@inbox_app.command("log")
def inbox_log(
    team: str = typer.Argument(..., help="Team name"),
    limit: int = typer.Option(50, "--limit", "-l", help="Max messages to show"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Filter by sender agent name"),
):
    """View message history (event log). Non-destructive, shows all sent messages."""
    from clawteam.team.mailbox import MailboxManager

    mailbox = MailboxManager(team)
    messages = mailbox.get_event_log(limit=limit)

    if agent:
        messages = [m for m in messages if m.from_agent == agent]

    # Reverse to show oldest first (event log returns newest first)
    messages.reverse()

    data = {"count": len(messages), "messages": [_dump(m) for m in messages]}

    def _human(d):
        console.print(f"Message history: {d['count']} message(s)")
        for m in d["messages"]:
            fr = m.get("from", "?")
            to = m.get("to", "all")
            ts = (m.get("timestamp") or "")[:19]
            mtype = m.get("type", "message")
            content = (m.get("content") or "")[:120]
            console.print(f"  [{ts}] [cyan]{fr}[/cyan] → {to} ({mtype}): {content}")

    _output(data, _human)


@inbox_app.command("watch")
def inbox_watch(
    team: str = typer.Argument(..., help="Team name"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent name (default: from env)"),
    poll_interval: float = typer.Option(1.0, "--poll-interval", "-p", help="Poll interval in seconds"),
    exec_cmd: Optional[str] = typer.Option(
        None,
        "--exec",
        "-e",
        help="Shell command to run for each new message (msg data in env vars)",
    ),
):
    """Watch inbox for new messages (blocking, Ctrl+C to stop).

    With --exec, runs a shell command for each message. Message data is passed
    via env vars: CLAWTEAM_MSG_FROM, CLAWTEAM_MSG_TO, CLAWTEAM_MSG_CONTENT,
    CLAWTEAM_MSG_TYPE, CLAWTEAM_MSG_TIMESTAMP, CLAWTEAM_MSG_JSON.
    """
    from clawteam.identity import AgentIdentity
    from clawteam.team.mailbox import MailboxManager
    from clawteam.team.manager import TeamManager
    from clawteam.team.watcher import InboxWatcher

    identity = AgentIdentity.from_env()
    agent_name = TeamManager.resolve_inbox(team, agent or identity.agent_name, identity.user)
    mailbox = MailboxManager(team)

    if not _json_output:
        console.print(f"Watching inbox for '{agent_name}' in team '{team}'... (Ctrl+C to stop)")
        if exec_cmd:
            console.print(f"  exec: {exec_cmd}")

    watcher = InboxWatcher(
        team_name=team,
        agent_name=agent_name,
        mailbox=mailbox,
        poll_interval=poll_interval,
        json_output=_json_output,
        exec_cmd=exec_cmd,
    )
    watcher.watch()


# ============================================================================
# Runtime Commands
# ============================================================================

runtime_app = typer.Typer(help="Tmux-only runtime routing and live injection")
app.add_typer(runtime_app, name="runtime")


@runtime_app.command("inject")
def runtime_inject(
    team: str = typer.Argument(..., help="Team name"),
    agent: str = typer.Argument(..., help="Target agent name"),
    source: str = typer.Option("system", "--source", "-s", help="Runtime notification source"),
    channel: str = typer.Option("direct", "--channel", help="Runtime notification channel"),
    priority: str = typer.Option("medium", "--priority", help="Runtime notification priority"),
    summary: str = typer.Option(..., "--summary", help="Summary text for the injected notification"),
    evidence: list[str] = typer.Option([], "--evidence", "-e", help="Repeatable evidence line"),
    recommended_next_action: Optional[str] = typer.Option(
        None,
        "--recommended-next-action",
        help="Optional recommended next action",
    ),
):
    """Inject a structured runtime notification into a running tmux agent."""
    from clawteam.spawn.tmux_backend import TmuxBackend
    from clawteam.team.routing_policy import RuntimeEnvelope

    envelope = RuntimeEnvelope(
        source=source,
        target=agent,
        channel=channel,
        priority=priority,
        message_type="manual",
        summary=summary,
        evidence=list(evidence),
        recommended_next_action=recommended_next_action,
    )
    ok, status = TmuxBackend().inject_runtime_message(team, agent, envelope)
    if not ok:
        console.print(f"[red]{status}[/red]")
        raise typer.Exit(1)

    _output(
        {"team": team, "agent": agent, "status": status},
        lambda data: console.print(f"[green]OK[/green] {data['status']}"),
    )


@runtime_app.command("watch")
def runtime_watch(
    team: str = typer.Argument(..., help="Team name"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent name (default: from env)"),
    poll_interval: float = typer.Option(1.0, "--poll-interval", "-p", help="Poll interval in seconds"),
    exec_cmd: Optional[str] = typer.Option(
        None,
        "--exec",
        "-e",
        help="Shell command to run for each new message (msg data in env vars)",
    ),
):
    """Watch an inbox and route new messages into the running tmux session."""
    from clawteam.identity import AgentIdentity
    from clawteam.team.mailbox import MailboxManager
    from clawteam.team.manager import TeamManager
    from clawteam.team.runtime_router import RuntimeRouter
    from clawteam.team.watcher import InboxWatcher

    identity = AgentIdentity.from_env()
    agent_name = TeamManager.resolve_inbox(team, agent or identity.agent_name, identity.user)
    mailbox = MailboxManager(team)
    router = RuntimeRouter(
        team_name=team,
        agent_name=agent_name,
        session_agent_name=agent or identity.agent_name,
    )

    if not _json_output:
        console.print(f"Watching runtime routes for '{agent_name}' in team '{team}'... (Ctrl+C to stop)")
        if exec_cmd:
            console.print(f"  exec: {exec_cmd}")

    watcher = InboxWatcher(
        team_name=team,
        agent_name=agent_name,
        mailbox=mailbox,
        poll_interval=poll_interval,
        json_output=_json_output,
        exec_cmd=exec_cmd,
        runtime_router=router,
    )
    watcher.watch()


@runtime_app.command("state")
def runtime_state(
    team: str = typer.Argument(..., help="Team name"),
):
    """Show persisted Phase 1 runtime throttle and dispatch state."""
    from clawteam.team.routing_policy import DefaultRoutingPolicy

    state = DefaultRoutingPolicy(team_name=team).read_state()

    def _human(data):
        console.print(f"Runtime state for '{data['team']}' (throttle={data['throttleSeconds']}s)")
        routes = data.get("routes", {})
        if not routes:
            console.print("[dim]No runtime route state.[/dim]")
            return
        for key in sorted(routes):
            route = routes[key]
            console.print(
                f"  {route.get('source', '?')} -> {route.get('target', '?')} "
                f"pending={route.get('pendingCount', 0)} "
                f"status={route.get('lastDispatchStatus', 'idle')} "
                f"flushAfter={route.get('flushAfter', '') or '-'}"
            )

    _output(state, _human)


# ============================================================================
# Task Commands
# ============================================================================

task_app = typer.Typer(help="Task management commands")
app.add_typer(task_app, name="task")


@task_app.command("create")
def task_create(
    team: str = typer.Argument(..., help="Team name"),
    subject: str = typer.Argument(..., help="Task subject"),
    description: str = typer.Option("", "--description", "-d", help="Task description"),
    owner: Optional[str] = typer.Option(None, "--owner", "-o", help="Owner agent name"),
    blocks: Optional[str] = typer.Option(None, "--blocks", help="Comma-separated task IDs this blocks"),
    blocked_by: Optional[str] = typer.Option(None, "--blocked-by", help="Comma-separated task IDs this is blocked by"),
):
    """Create a new task (TaskCreate)."""
    from clawteam.team.tasks import TaskStore

    store = TaskStore(team)
    blocks_list = [b.strip() for b in blocks.split(",") if b.strip()] if blocks else []
    blocked_by_list = [b.strip() for b in blocked_by.split(",") if b.strip()] if blocked_by else []

    task = store.create(
        subject=subject,
        description=description,
        owner=owner or "",
        blocks=blocks_list,
        blocked_by=blocked_by_list,
    )

    data = _dump(task)
    _output(
        data,
        lambda d: (
            console.print(f"[green]OK[/green] Task created: {d['id']}"),
            console.print(f"  Subject: {d['subject']}"),
            console.print(f"  Status: {d['status']}"),
            console.print(f"  Owner: {d.get('owner', '')}") if d.get("owner") else None,
        ),
    )


@task_app.command("get")
def task_get(
    team: str = typer.Argument(..., help="Team name"),
    task_id: str = typer.Argument(..., help="Task ID"),
):
    """Get a single task (TaskGet)."""
    from clawteam.team.tasks import TaskStore

    store = TaskStore(team)
    task = store.get(task_id)
    if not task:
        _output(
            {"error": f"Task '{task_id}' not found"},
            lambda d: console.print(f"[red]{d['error']}[/red]"),
        )
        raise typer.Exit(1)

    data = _dump(task)

    def _human(d):
        console.print(f"Task: [cyan]{d['id']}[/cyan]")
        console.print(f"  Subject: {d['subject']}")
        console.print(f"  Status: {d['status']}")
        if d.get("owner"):
            console.print(f"  Owner: {d['owner']}")
        if d.get("lockedBy"):
            console.print(f"  Locked by: [yellow]{d['lockedBy']}[/yellow] (since {d.get('lockedAt', '')[:19]})")
        if d.get("description"):
            console.print(f"  Description: {d['description']}")
        if d.get("blocks"):
            console.print(f"  Blocks: {', '.join(d['blocks'])}")
        if d.get("blockedBy"):
            console.print(f"  Blocked by: {', '.join(d['blockedBy'])}")

    _output(data, _human)


@task_app.command("update")
def task_update(
    team: str = typer.Argument(..., help="Team name"),
    task_id: str = typer.Argument(..., help="Task ID"),
    status: Optional[str] = typer.Option(
        None, "--status", "-s", help="New status: pending, in_progress, completed, blocked"
    ),
    owner: Optional[str] = typer.Option(None, "--owner", "-o", help="New owner"),
    subject: Optional[str] = typer.Option(None, "--subject", help="New subject"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="New description"),
    add_blocks: Optional[str] = typer.Option(None, "--add-blocks", help="Comma-separated task IDs this blocks"),
    add_blocked_by: Optional[str] = typer.Option(
        None, "--add-blocked-by", help="Comma-separated task IDs blocking this"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Force override task lock"),
):
    """Update a task (TaskUpdate)."""
    from clawteam.identity import AgentIdentity
    from clawteam.team.models import TaskStatus
    from clawteam.team.tasks import TaskLockError, TaskStore

    store = TaskStore(team)
    ts = TaskStatus(status) if status else None
    blocks_list = [b.strip() for b in add_blocks.split(",") if b.strip()] if add_blocks else None
    blocked_by_list = [b.strip() for b in add_blocked_by.split(",") if b.strip()] if add_blocked_by else None

    caller = AgentIdentity.from_env().agent_name

    try:
        task = store.update(
            task_id,
            status=ts,
            owner=owner,
            subject=subject,
            description=description,
            add_blocks=blocks_list,
            add_blocked_by=blocked_by_list,
            caller=caller,
            force=force,
        )
    except TaskLockError as e:
        _output({"error": str(e)}, lambda d: console.print(f"[red]Lock conflict: {d['error']}[/red]"))
        raise typer.Exit(1)

    if not task:
        _output(
            {"error": f"Task '{task_id}' not found"},
            lambda d: console.print(f"[red]{d['error']}[/red]"),
        )
        raise typer.Exit(1)

    data = _dump(task)
    _output(data, lambda d: console.print(f"[green]OK[/green] Task {d['id']} updated"))


@task_app.command("list")
def task_list(
    team: str = typer.Argument(..., help="Team name"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    owner: Optional[str] = typer.Option(None, "--owner", "-o", help="Filter by owner"),
):
    """List tasks for a team (TaskList)."""
    from clawteam.team.models import TaskStatus
    from clawteam.team.tasks import TaskStore

    store = TaskStore(team)
    ts = TaskStatus(status) if status else None
    tasks = store.list_tasks(status=ts, owner=owner)

    data = [_dump(t) for t in tasks]

    def _human(items):
        if not items:
            console.print("[dim]No tasks found[/dim]")
            return
        table = Table(title=f"Tasks - {team}")
        table.add_column("ID", style="dim")
        table.add_column("Subject", style="cyan")
        table.add_column("Status")
        table.add_column("Owner")
        table.add_column("Lock", style="yellow")
        table.add_column("Blocked By", style="dim")
        for t in items:
            st = t.get("status", "")
            style = {
                "pending": "white",
                "in_progress": "yellow",
                "completed": "green",
                "blocked": "red",
            }.get(st, "")
            table.add_row(
                t["id"],
                t["subject"],
                f"[{style}]{st}[/{style}]" if style else st,
                t.get("owner") or "",
                t.get("lockedBy") or "",
                ", ".join(t.get("blockedBy", [])),
            )
        console.print(table)

    _output(data, _human)


@task_app.command("stats")
def task_stats(
    team: str = typer.Argument(..., help="Team name"),
):
    """Show task timing statistics for a team."""
    from clawteam.team.tasks import TaskStore

    store = TaskStore(team)
    stats = store.get_stats()

    def _human(d):
        table = Table(title=f"Task Stats - {team}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")
        table.add_row("Total tasks", str(d["total"]))
        table.add_row("Completed", str(d["completed"]))
        table.add_row("In progress", str(d["in_progress"]))
        table.add_row("Pending", str(d["pending"]))
        table.add_row("Blocked", str(d["blocked"]))
        table.add_row("With timing data", str(d["timed_completed"]))
        avg = d["avg_duration_seconds"]
        if avg > 0:
            # Show in a readable format
            if avg < 60:
                table.add_row("Avg completion time", f"{avg:.1f}s")
            elif avg < 3600:
                table.add_row("Avg completion time", f"{avg / 60:.1f}m")
            else:
                table.add_row("Avg completion time", f"{avg / 3600:.1f}h")
        else:
            table.add_row("Avg completion time", "-")
        console.print(table)

    _output(stats, _human)


# ============================================================================
# Cost Commands
# ============================================================================

cost_app = typer.Typer(help="Cost tracking and budget management")
app.add_typer(cost_app, name="cost")


@cost_app.command("report")
def cost_report(
    team: str = typer.Argument(..., help="Team name"),
    input_tokens: int = typer.Option(0, "--input-tokens", help="Input tokens consumed"),
    output_tokens: int = typer.Option(0, "--output-tokens", help="Output tokens consumed"),
    cost_cents: float = typer.Option(0.0, "--cost-cents", help="Cost in cents"),
    provider: str = typer.Option("", "--provider", help="Provider name (e.g. anthropic)"),
    model: str = typer.Option("", "--model", help="Model name"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent name (default: from env)"),
    task_id: str = typer.Option("", "--task-id", help="Associated task ID"),
):
    """Report token usage and cost for an agent."""
    from clawteam.identity import AgentIdentity
    from clawteam.team.costs import CostStore
    from clawteam.team.manager import TeamManager

    agent_name = agent or AgentIdentity.from_env().agent_name
    store = CostStore(team)
    event = store.report(
        agent_name=agent_name,
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_cents=cost_cents,
        task_id=task_id,
    )
    data = _dump(event)

    def _human(d):
        console.print(f"[green]OK[/green] Cost reported: ${d.get('costCents', 0) / 100:.4f}")

    _output(data, _human)

    # Check budget
    config = TeamManager.get_team(team)
    if config and config.budget_cents > 0:
        summary = store.summary()
        if summary.total_cost_cents > config.budget_cents:
            budget_dollars = config.budget_cents / 100
            spent_dollars = summary.total_cost_cents / 100
            if not _json_output:
                console.print(
                    f"[yellow]WARNING: Budget exceeded! Spent ${spent_dollars:.2f} / ${budget_dollars:.2f}[/yellow]"
                )


@cost_app.command("show")
def cost_show(
    team: str = typer.Argument(..., help="Team name"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Filter by agent"),
    by: Optional[str] = typer.Option(None, "--by", "-b", help="Breakdown dimension: agent, task, or model"),
):
    """Show cost summary and event history."""
    from clawteam.team.costs import CostStore
    from clawteam.team.manager import TeamManager

    store = CostStore(team)
    summary = store.summary()
    events = store.list_events(agent_name=agent or "")
    config = TeamManager.get_team(team)
    budget = config.budget_cents if config else 0.0
    rate = store.cost_rate()

    data = {
        "summary": _dump(summary),
        "budget_cents": budget,
        "cost_rate_per_min": rate,
        "events": [_dump(e) for e in events],
    }

    def _human(d):
        s = d["summary"]
        total = s.get("totalCostCents", 0)
        console.print(f"\nCost Summary — [cyan]{team}[/cyan]")
        if budget > 0:
            console.print(f"  Total: ${total / 100:.4f} / ${budget / 100:.2f}")
        else:
            console.print(f"  Total: ${total / 100:.4f}")
        console.print(f"  Input tokens:  {s.get('totalInputTokens', 0):,}")
        console.print(f"  Output tokens: {s.get('totalOutputTokens', 0):,}")
        console.print(f"  Events: {s.get('eventCount', 0)}")
        if rate > 0:
            console.print(f"  Rate: ${rate / 100:.4f}/min")

        # Dimension breakdown
        dimension = by or "agent"
        dimension_key = {
            "agent": "byAgent",
            "model": "byModel",
            "task": "byTask",
        }.get(dimension, "byAgent")
        breakdown = s.get(dimension_key, {})
        if breakdown:
            console.print(f"  By {dimension}:")
            for k, c in sorted(breakdown.items()):
                console.print(f"    {k}: ${c / 100:.4f}")

        evts = d["events"]
        if evts:
            table = Table(title="Recent Events")
            table.add_column("Time", style="dim")
            table.add_column("Agent", style="cyan")
            table.add_column("In Tokens", justify="right")
            table.add_column("Out Tokens", justify="right")
            table.add_column("Cost", justify="right")
            table.add_column("Model", style="dim")
            table.add_column("Task", style="dim")
            for e in evts[-20:]:  # show last 20
                table.add_row(
                    (e.get("reportedAt") or "")[:19],
                    e.get("agentName", ""),
                    f"{e.get('inputTokens', 0):,}",
                    f"{e.get('outputTokens', 0):,}",
                    f"${e.get('costCents', 0) / 100:.4f}",
                    e.get("model", ""),
                    e.get("taskId", ""),
                )
            console.print(table)

    _output(data, _human)


@cost_app.command("budget")
def cost_budget(
    team: str = typer.Argument(..., help="Team name"),
    dollars: float = typer.Argument(..., help="Budget in dollars (0 = unlimited)"),
):
    """Set team budget in dollars."""
    from clawteam.team.manager import TeamManager

    config = TeamManager.get_team(team)
    if not config:
        _output(
            {"error": f"Team '{team}' not found"},
            lambda d: console.print(f"[red]{d['error']}[/red]"),
        )
        raise typer.Exit(1)

    config.budget_cents = dollars * 100
    # Save config back
    from clawteam.team.manager import _save_config

    _save_config(config)

    _output(
        {"status": "set", "team": team, "budgetDollars": dollars},
        lambda d: console.print(
            f"[green]OK[/green] Budget set to ${dollars:.2f}"
            if dollars > 0
            else "[green]OK[/green] Budget removed (unlimited)"
        ),
    )


@task_app.command("wait")
def task_wait(
    team: str = typer.Argument(..., help="Team name"),
    agent: Optional[str] = typer.Option(
        None, "--agent", "-a", help="Agent inbox to monitor (default: leader from team config)"
    ),
    poll_interval: float = typer.Option(5.0, "--poll-interval", "-p", help="Seconds between polls"),
    timeout: Optional[float] = typer.Option(None, "--timeout", "-t", help="Max seconds to wait (default: no limit)"),
):
    """Block until all tasks in a team are completed."""
    from clawteam.team.mailbox import MailboxManager
    from clawteam.team.manager import TeamManager
    from clawteam.team.tasks import TaskStore
    from clawteam.team.waiter import TaskWaiter

    # Resolve agent name for inbox monitoring
    agent_name = agent
    if not agent_name:
        agent_name = TeamManager.get_leader_inbox(team)
    if not agent_name:
        from clawteam.identity import AgentIdentity

        identity = AgentIdentity.from_env()
        agent_name = TeamManager.resolve_inbox(team, identity.agent_name, identity.user)
    elif agent:
        from clawteam.identity import AgentIdentity

        identity = AgentIdentity.from_env()
        agent_name = TeamManager.resolve_inbox(team, agent_name, identity.user)

    mailbox = MailboxManager(team)
    store = TaskStore(team)

    def _on_message(msg):
        ts = msg.timestamp
        if ts and "T" in ts:
            ts = ts.split("T")[1][:8]
        from_agent = msg.from_agent or "?"
        content = msg.content or ""
        if _json_output:
            print(
                json.dumps(
                    {
                        "event": "message",
                        "from": from_agent,
                        "content": content,
                        "timestamp": msg.timestamp,
                    }
                ),
                flush=True,
            )
        else:
            console.print(f"  {ts}  message from={from_agent}: {content}")

    last_progress = ""

    def _on_progress(completed, total, in_progress, pending, blocked):
        nonlocal last_progress
        summary = f"{completed}/{total}"
        if summary == last_progress:
            return
        last_progress = summary
        if _json_output:
            print(
                json.dumps(
                    {
                        "event": "progress",
                        "completed": completed,
                        "total": total,
                        "in_progress": in_progress,
                        "pending": pending,
                        "blocked": blocked,
                    }
                ),
                flush=True,
            )
        else:
            console.print(
                f"  {completed}/{total} tasks completed"
                f"  ({in_progress} in progress, {pending} pending, {blocked} blocked)"
            )

    if not _json_output:
        timeout_str = f"{timeout:.0f}s" if timeout else "none"
        console.print(f"Waiting for all tasks in team '[cyan]{team}[/cyan]' to complete...")
        console.print(f"  Agent inbox: {agent_name}  |  Poll interval: {poll_interval}s  |  Timeout: {timeout_str}")
        console.print()

    def _on_agent_dead(dead_agent, abandoned_tasks):
        task_subjects = ", ".join(t.subject for t in abandoned_tasks)
        if _json_output:
            print(
                json.dumps(
                    {
                        "event": "agent_dead",
                        "agent": dead_agent,
                        "abandoned_tasks": [{"id": t.id, "subject": t.subject} for t in abandoned_tasks],
                    }
                ),
                flush=True,
            )
        else:
            console.print(
                f"  [yellow]Agent '{dead_agent}' is dead.[/yellow]"
                f" Reset {len(abandoned_tasks)} task(s) to pending: {task_subjects}"
            )

    waiter = TaskWaiter(
        team_name=team,
        agent_name=agent_name,
        mailbox=mailbox,
        task_store=store,
        poll_interval=poll_interval,
        timeout=timeout,
        on_message=_on_message,
        on_progress=_on_progress,
        on_agent_dead=_on_agent_dead,
    )
    result = waiter.wait()

    if _json_output:
        print(
            json.dumps(
                {
                    "event": "result",
                    "status": result.status,
                    "elapsed": round(result.elapsed, 1),
                    "total": result.total,
                    "completed": result.completed,
                    "in_progress": result.in_progress,
                    "pending": result.pending,
                    "blocked": result.blocked,
                    "messages_received": result.messages_received,
                    "task_details": result.task_details,
                }
            ),
            flush=True,
        )
    else:
        console.print()
        if result.status == "completed":
            console.print(
                f"[green]All {result.total} tasks completed![/green]"
                f" ({result.elapsed:.1f}s, {result.messages_received} messages)"
            )
        elif result.status == "timeout":
            console.print(
                f"[yellow]Timeout[/yellow] after {result.elapsed:.1f}s. {result.completed}/{result.total} completed."
            )
            _print_incomplete_tasks(result.task_details)
        else:
            console.print(
                f"[yellow]Interrupted[/yellow] after {result.elapsed:.1f}s."
                f" {result.completed}/{result.total} completed."
            )
            _print_incomplete_tasks(result.task_details)

    if result.status != "completed":
        raise typer.Exit(1)


def _print_incomplete_tasks(task_details: list[dict]):
    """Print tasks that are not completed."""
    incomplete = [t for t in task_details if t["status"] != "completed"]
    if incomplete:
        console.print("  Incomplete tasks:")
        for t in incomplete:
            console.print(f"    [{t['status']}] {t['id']}  {t['subject']}  (owner: {t['owner'] or '-'})")


# ============================================================================
# Session Commands
# ============================================================================

session_app = typer.Typer(help="Session persistence for agent resume")
app.add_typer(session_app, name="session")


@session_app.command("save")
def session_save(
    team: str = typer.Argument(..., help="Team name"),
    session_id: str = typer.Option("", "--session-id", "-s", help="Claude Code session ID"),
    last_task: str = typer.Option("", "--last-task", help="Last task ID worked on"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent name (default: from env)"),
):
    """Save agent session for later resume."""
    from clawteam.identity import AgentIdentity
    from clawteam.spawn.sessions import SessionStore

    agent_name = agent or AgentIdentity.from_env().agent_name
    store = SessionStore(team)
    session = store.save(
        agent_name=agent_name,
        session_id=session_id,
        last_task_id=last_task,
    )
    data = _dump(session)
    _output(data, lambda d: console.print(f"[green]OK[/green] Session saved for '{agent_name}'"))


@task_app.command("route")
def task_route(
    team: str = typer.Argument(...),
    subject: str = typer.Option(..., "--subject", "-s"),
    description: str = typer.Option("", "--description", "-d"),
    candidates: str = typer.Option(None, "--candidates", "-c", help="Comma-separated list of agent names"),
):
    """Find the best agent for a task using intelligent routing."""
    from clawteam.team.router import get_router

    router = get_router(team)
    router.update_load(team)

    cand_list = [c.strip() for c in candidates.split(",")] if candidates else None

    # Get all candidates
    all_candidates = router.get_all_candidates(subject, description, cand_list)

    if not all_candidates:
        console.print("[yellow]No agents available for routing.[/yellow]")
        return

    best = all_candidates[0]

    def _human(_data):
        console.print(f"[bold]Task Route — '{subject}'[/bold]")
        console.print(f"  [green]Recommended: {best.name}[/green] (score: {best.match_score})")
        console.print(
            f"  Success rate: {best.success_rate:.0%}  Avg score: {best.avg_score:.1f}/10  Load: {best.current_load}"
        )
        if best.matching_topics:
            console.print(f"  Matching topics: {', '.join(best.matching_topics[:5])}")

        if len(all_candidates) > 1:
            console.print()
            console.print("[dim]Other candidates:[/dim]")
            for c in all_candidates[1:]:
                console.print(
                    f"  {c.name}: score={c.match_score} (success={c.success_rate:.0%}, load={c.current_load})"
                )

    _output(
        {
            "best": best.__dict__,
            "all_candidates": [c.__dict__ for c in all_candidates],
        },
        _human,
    )


@session_app.command("show")
def session_show(
    team: str = typer.Argument(..., help="Team name"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Filter by agent"),
):
    """Show saved sessions."""
    from clawteam.spawn.sessions import SessionStore

    store = SessionStore(team)
    if agent:
        session = store.load(agent)
        if not session:
            _output(
                {"error": f"No session for '{agent}'"},
                lambda d: console.print(f"[dim]{d['error']}[/dim]"),
            )
            return
        data = _dump(session)
        _output(
            data,
            lambda d: (
                console.print(f"Session: [cyan]{d.get('agentName', '')}[/cyan]"),
                console.print(f"  Session ID: {d.get('sessionId', '')}"),
                console.print(f"  Last task:  {d.get('lastTaskId', '')}"),
                console.print(f"  Saved at:   {d.get('savedAt', '')[:19]}"),
            ),
        )
    else:
        sessions = store.list_sessions()
        data = [_dump(s) for s in sessions]

        def _human(items):
            if not items:
                console.print("[dim]No saved sessions[/dim]")
                return
            table = Table(title=f"Sessions — {team}")
            table.add_column("Agent", style="cyan")
            table.add_column("Session ID")
            table.add_column("Last Task", style="dim")
            table.add_column("Saved At", style="dim")
            for s in items:
                table.add_row(
                    s.get("agentName", ""),
                    s.get("sessionId", ""),
                    s.get("lastTaskId", ""),
                    (s.get("savedAt") or "")[:19],
                )
            console.print(table)

        _output(data, _human)


@session_app.command("clear")
def session_clear(
    team: str = typer.Argument(..., help="Team name"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent name (default: all)"),
):
    """Clear saved sessions."""
    from clawteam.spawn.sessions import SessionStore

    store = SessionStore(team)
    if agent:
        if store.clear(agent):
            _output(
                {"status": "cleared", "agent": agent},
                lambda d: console.print(f"[green]OK[/green] Session cleared for '{agent}'"),
            )
        else:
            _output(
                {"status": "not_found", "agent": agent},
                lambda d: console.print(f"[dim]No session for '{agent}'[/dim]"),
            )
    else:
        sessions = store.list_sessions()
        count = 0
        for s in sessions:
            if store.clear(s.agent_name):
                count += 1
        _output(
            {"status": "cleared", "count": count},
            lambda d: console.print(f"[green]OK[/green] Cleared {count} session(s)"),
        )


# ============================================================================
# Plan Commands
# ============================================================================

plan_app = typer.Typer(help="Plan management commands")
app.add_typer(plan_app, name="plan")


@plan_app.command("submit")
def plan_submit(
    team: str = typer.Argument(..., help="Team name"),
    agent: str = typer.Argument(..., help="Agent name submitting the plan"),
    plan: str = typer.Argument(..., help="Plan content or path to a file"),
    summary: str = typer.Option("", "--summary", "-s", help="Brief plan summary"),
):
    """Submit a plan for leader approval (triggers plan_approval_request)."""
    from clawteam.team.mailbox import MailboxManager
    from clawteam.team.manager import TeamManager
    from clawteam.team.plan import PlanManager

    plan_content = plan
    p = Path(plan)
    if p.exists() and p.is_file():
        plan_content = p.read_text(encoding="utf-8")

    leader_name = TeamManager.get_leader_name(team)
    if not leader_name:
        _output({"error": "No leader found"}, lambda d: console.print(f"[red]{d['error']}[/red]"))
        raise typer.Exit(1)

    mailbox = MailboxManager(team)
    pm = PlanManager(team, mailbox)
    plan_id = pm.submit_plan(agent_name=agent, leader_name=leader_name, plan_content=plan_content, summary=summary)

    _output(
        {"status": "submitted", "planId": plan_id, "agent": agent},
        lambda d: console.print(f"[green]OK[/green] Plan {d['planId']} submitted by {d['agent']}"),
    )


@plan_app.command("approve")
def plan_approve(
    team: str = typer.Argument(..., help="Team name"),
    plan_id: str = typer.Argument(..., help="Plan ID (requestId from plan_approval_request)"),
    agent: str = typer.Argument(..., help="Agent who submitted the plan (target_agent_id)"),
    feedback: str = typer.Option("", "--feedback", "-f", help="Optional feedback"),
):
    """Approve a submitted plan (approvePlan)."""
    from clawteam.identity import AgentIdentity
    from clawteam.team.mailbox import MailboxManager
    from clawteam.team.plan import PlanManager

    identity = AgentIdentity.from_env()
    mailbox = MailboxManager(team)
    pm = PlanManager(team, mailbox)
    pm.approve_plan(leader_name=identity.agent_name, plan_id=plan_id, agent_name=agent, feedback=feedback)

    _output(
        {"status": "approved", "planId": plan_id},
        lambda d: console.print(f"[green]OK[/green] Plan {plan_id} approved"),
    )


@plan_app.command("reject")
def plan_reject(
    team: str = typer.Argument(..., help="Team name"),
    plan_id: str = typer.Argument(..., help="Plan ID (requestId from plan_approval_request)"),
    agent: str = typer.Argument(..., help="Agent who submitted the plan (target_agent_id)"),
    feedback: str = typer.Option("", "--feedback", "-f", help="Rejection feedback"),
):
    """Reject a submitted plan (rejectPlan)."""
    from clawteam.identity import AgentIdentity
    from clawteam.team.mailbox import MailboxManager
    from clawteam.team.plan import PlanManager

    identity = AgentIdentity.from_env()
    mailbox = MailboxManager(team)
    pm = PlanManager(team, mailbox)
    pm.reject_plan(leader_name=identity.agent_name, plan_id=plan_id, agent_name=agent, feedback=feedback)

    _output(
        {"status": "rejected", "planId": plan_id},
        lambda d: console.print(f"[green]OK[/green] Plan {plan_id} rejected"),
    )


# ============================================================================
# Lifecycle Commands
# ============================================================================

lifecycle_app = typer.Typer(help="Agent lifecycle commands (shutdown protocol)")
app.add_typer(lifecycle_app, name="lifecycle")


@lifecycle_app.command("request-shutdown")
def lifecycle_request_shutdown(
    team: str = typer.Argument(..., help="Team name"),
    from_agent: str = typer.Argument(..., help="Requesting agent name"),
    to_agent: str = typer.Argument(..., help="Target agent name"),
    reason: str = typer.Option("", "--reason", "-r", help="Shutdown reason"),
):
    """Request an agent to shut down (requestShutdown)."""
    from clawteam.team.lifecycle import LifecycleManager
    from clawteam.team.mailbox import MailboxManager

    mailbox = MailboxManager(team)
    lm = LifecycleManager(team, mailbox)
    request_id = lm.request_shutdown(from_agent=from_agent, to_agent=to_agent, reason=reason)

    _output(
        {"status": "requested", "requestId": request_id, "from": from_agent, "to": to_agent},
        lambda d: console.print(f"[green]OK[/green] Shutdown request sent to '{to_agent}' (id: {request_id})"),
    )


@lifecycle_app.command("approve-shutdown")
def lifecycle_approve_shutdown(
    team: str = typer.Argument(..., help="Team name"),
    request_id: str = typer.Argument(..., help="Shutdown request ID"),
    agent: str = typer.Argument(..., help="Agent approving shutdown (self)"),
):
    """Approve a shutdown request (approveShutdown). Agent agrees to shut down."""
    from clawteam.identity import AgentIdentity
    from clawteam.team.lifecycle import LifecycleManager
    from clawteam.team.mailbox import MailboxManager

    identity = AgentIdentity.from_env()
    mailbox = MailboxManager(team)
    lm = LifecycleManager(team, mailbox)
    leader_name = identity.agent_name
    lm.approve_shutdown(agent_name=agent, request_id=request_id, requester_name=leader_name)

    _output(
        {"status": "approved", "requestId": request_id, "agent": agent},
        lambda d: console.print(f"[green]OK[/green] {agent} approved shutdown"),
    )


@lifecycle_app.command("reject-shutdown")
def lifecycle_reject_shutdown(
    team: str = typer.Argument(..., help="Team name"),
    request_id: str = typer.Argument(..., help="Shutdown request ID"),
    agent: str = typer.Argument(..., help="Agent rejecting shutdown"),
    reason: str = typer.Option("", "--reason", "-r", help="Rejection reason"),
):
    """Reject a shutdown request (rejectShutdown)."""
    from clawteam.identity import AgentIdentity
    from clawteam.team.lifecycle import LifecycleManager
    from clawteam.team.mailbox import MailboxManager

    identity = AgentIdentity.from_env()
    mailbox = MailboxManager(team)
    lm = LifecycleManager(team, mailbox)
    lm.reject_shutdown(agent_name=agent, request_id=request_id, requester_name=identity.agent_name, reason=reason)

    _output(
        {"status": "rejected", "requestId": request_id, "agent": agent, "reason": reason},
        lambda d: console.print(f"[green]OK[/green] {agent} rejected shutdown"),
    )


@lifecycle_app.command("idle")
def lifecycle_idle(
    team: str = typer.Argument(..., help="Team name"),
    last_task: Optional[str] = typer.Option(None, "--last-task", help="Last task ID worked on"),
    task_status: Optional[str] = typer.Option(None, "--task-status", help="Status of last task"),
):
    """Send idle notification to leader."""
    from clawteam.identity import AgentIdentity
    from clawteam.team.lifecycle import LifecycleManager
    from clawteam.team.mailbox import MailboxManager
    from clawteam.team.manager import TeamManager

    identity = AgentIdentity.from_env()
    team_name = team
    leader_name = TeamManager.get_leader_name(team_name)
    if not leader_name:
        _output({"error": "No leader found"}, lambda d: console.print(f"[red]{d['error']}[/red]"))
        raise typer.Exit(1)

    mailbox = MailboxManager(team_name)
    lm = LifecycleManager(team_name, mailbox)
    lm.send_idle(
        agent_name=identity.agent_name,
        agent_id=identity.agent_id,
        leader_name=leader_name,
        last_task=last_task or "",
        task_status=task_status or "",
    )

    _output(
        {"status": "idle_sent", "agent": identity.agent_name, "leader": leader_name},
        lambda d: console.print(f"[green]OK[/green] Idle notification sent to '{leader_name}'"),
    )


@lifecycle_app.command("on-exit")
def lifecycle_on_exit(
    team: str = typer.Option(..., "--team", "-t", help="Team name"),
    agent: str = typer.Option(..., "--agent", "-n", help="Agent name"),
    cascade: bool = typer.Option(True, "--cascade/--no-cascade", help="Terminate child agents on exit (default: true)"),
):
    """Handle agent process exit: clean up session and reset in_progress tasks.

    This is called automatically as a post-exit hook when an agent process terminates.
    By default, also terminates all child agents (cascade cleanup).
    """
    import subprocess

    from clawteam.spawn.registry import (
        get_agent_info,
        is_agent_alive,
        list_dead_agents,
        terminate_agent_tree,
        unregister_agent,
    )
    from clawteam.spawn.sessions import SessionStore
    from clawteam.team.mailbox import MailboxManager
    from clawteam.team.manager import TeamManager
    from clawteam.team.models import TaskStatus
    from clawteam.team.parent_child import ParentChildRegistry
    from clawteam.team.tasks import TaskStore

    # Always clean up the agent's session file, regardless of task status.
    # Without this, session files accumulate indefinitely under
    # ~/.clawteam/sessions/{team}/ after every agent exit.
    SessionStore(team).clear(agent)

    # --- Cascade child cleanup: terminate all descendants before we exit ---
    # This ensures child agents don't become orphaned zombies.
    # get_descendants includes direct children (and their children), so we
    # terminate the full list bottom-up (leaves first) to avoid double-kills.
    children_cleaned: list[str] = []
    if cascade:
        descendants = ParentChildRegistry.get_descendants(team, agent)
        for descendant in reversed(descendants):
            try:
                terminate_agent_tree(team, descendant)
            except Exception:
                pass
            try:
                ParentChildRegistry.unregister(team, descendant)
            except Exception:
                pass
            children_cleaned.append(descendant)
        # Unregister this agent from parent-child registry
        try:
            ParentChildRegistry.unregister(team, agent)
        except Exception:
            pass

    store = TaskStore(team)

    # Release locks held by this agent FIRST — must happen before unregister
    # to avoid a race where is_agent_alive returns None (no registry entry)
    # and causes _acquire_lock to refuse overwriting a stale lock.
    store.release_stale_locks()

    # Find this agent's in_progress tasks and reset them
    tasks = store.list_tasks()
    abandoned = [t for t in tasks if t.owner == agent and t.status == TaskStatus.in_progress]

    # Unregister from spawn registry so is_agent_alive returns None for this agent.
    # Guard: only unregister if the agent is already dead (avoids removing a live entry
    # if the hook fires before the process actually exits).
    if is_agent_alive(team, agent) is False:
        unregister_agent(team, agent)

        # Garbage-collect any other dead agents in the same team while we're here.
        for dead in list_dead_agents(team):
            unregister_agent(team, dead)

    if not abandoned:
        # Agent exited cleanly (all tasks already completed or pending)
        # Registry cleanup has already happened above.
        if children_cleaned:
            _output(
                {
                    "status": "agent_exited",
                    "agent": agent,
                    "children_terminated": children_cleaned,
                },
                lambda d: console.print(
                    f"[yellow]Agent '{agent}' exited.[/yellow] "
                    f"Terminated {len(d['children_terminated'])} child agent(s)."
                ),
            )
        return

    for t in abandoned:
        store.update(t.id, status=TaskStatus.pending)

    exit_detail = ""
    info = get_agent_info(team, agent)
    if info and info.get("backend") == "tmux" and info.get("tmux_target"):
        try:
            pane = subprocess.run(
                ["tmux", "capture-pane", "-p", "-t", info["tmux_target"], "-S", "-80"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if pane.returncode == 0 and pane.stdout.strip():
                lines = [line.rstrip() for line in pane.stdout.splitlines() if line.strip()]
                tail = " | ".join(lines[-6:])
                if tail:
                    exit_detail = f" Last output: {tail[:700]}"
        except (subprocess.TimeoutExpired, OSError):
            exit_detail = ""

    # Notify leader
    leader_name = TeamManager.get_leader_name(team)
    if leader_name:
        mailbox = MailboxManager(team)
        task_subjects = ", ".join(t.subject for t in abandoned)
        mailbox.send(
            from_agent=agent,
            to=leader_name,
            content=f"Agent '{agent}' exited unexpectedly. "
            f"Reset {len(abandoned)} task(s) to pending: {task_subjects}.{exit_detail}",
        )

    _output(
        {
            "status": "agent_exited",
            "agent": agent,
            "abandoned_tasks": [{"id": t.id, "subject": t.subject} for t in abandoned],
            "children_terminated": children_cleaned,
        },
        lambda d: console.print(
            f"[yellow]Agent '{agent}' exited.[/yellow] "
            f"Reset {len(d['abandoned_tasks'])} task(s) to pending."
            + (f" Terminated {len(d['children_terminated'])} child agent(s)." if d["children_terminated"] else "")
        ),
    )


@lifecycle_app.command("check-zombies")
def lifecycle_check_zombies(
    team: str = typer.Option(..., "--team", "-t", help="Team name"),
    max_hours: float = typer.Option(
        2.0, "--max-hours", help="Warn if agent has been running longer than this many hours"
    ),
):
    """Warn about agents that have been running unusually long (possible zombies).

    Agents that never called on-exit will accumulate as background processes.
    This command helps identify them so you can decide whether to stop them manually.
    """
    from clawteam.spawn.registry import list_zombie_agents

    zombies = list_zombie_agents(team, max_hours=max_hours)

    if not zombies:
        _output(
            {"team": team, "zombies": []},
            lambda d: console.print(f"[green]*[/green] No zombie agents detected for team '{team}'"),
        )
        return

    def _fmt(d: dict) -> None:
        console.print(f"[bold yellow]! {len(d['zombies'])} zombie agent(s) detected in team '{team}':[/bold yellow]")
        for z in d["zombies"]:
            console.print(
                f"  [yellow]• {z['agent_name']}[/yellow]  "
                f"pid={z['pid']}  backend={z['backend']}  "
                f"running={z['running_hours']}h"
            )
        console.print(
            "\n[dim]These processes did not call lifecycle on-exit. "
            "Inspect them manually or run: clawteam lifecycle stop-agent --team <team> --agent <name>[/dim]"
        )

    _output({"team": team, "zombies": zombies}, _fmt)
    raise typer.Exit(1)


@lifecycle_app.command("terminate-children")
def lifecycle_terminate_children(
    team: str = typer.Option(..., "--team", "-t", help="Team name"),
    parent: str = typer.Option(..., "--parent", "-p", help="Parent agent name"),
    cascade: bool = typer.Option(
        False, "--cascade/--no-cascade", help="Also terminate grandchildren and deeper descendants"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Force terminate even if agent is alive"),
):
    """Terminate child agents of a parent agent.

    By default only direct children are terminated. Use --cascade to also
    terminate grandchildren, great-grandchildren, etc.
    """
    from clawteam.spawn.registry import get_agent_info, is_agent_alive
    from clawteam.team.lifecycle import LifecycleManager
    from clawteam.team.mailbox import MailboxManager

    mailbox = MailboxManager(team)
    lm = LifecycleManager(team, mailbox)

    if not cascade:
        children = lm.get_children(parent)
        if not children:
            _output(
                {"status": "no_children", "parent": parent, "children": []},
                lambda d: console.print(f"[dim]No children found for agent '{parent}'[/dim]"),
            )
            return

        terminated: list[str] = []
        for child in children:
            alive = is_agent_alive(team, child)
            if alive is True and not force:
                info = get_agent_info(team, child)
                backend = info.get("backend", "?") if info else "?"
                console.print(
                    f"[yellow]! Skipping '{child}' (still alive, backend={backend}). "
                    f"Use --force to terminate anyway.[/yellow]"
                )
                continue
            try:
                from clawteam.spawn.registry import terminate_agent_tree

                terminate_agent_tree(team, child)
            except Exception:
                pass
            lm.terminate_children(parent, cascade=False)
            terminated.append(child)

        _output(
            {"status": "terminated", "parent": parent, "cascade": False, "terminated": terminated},
            lambda d: console.print(
                f"[green]Terminated {len(d['terminated'])} child agent(s) of '{d['parent']}'[/green]"
            ),
        )
    else:
        # Cascade: terminate entire tree
        descendants = lm.get_tree(parent)
        if not descendants.get("children"):
            _output(
                {"status": "no_children", "parent": parent, "children": []},
                lambda d: console.print(f"[dim]No descendants found for agent '{parent}'[/dim]"),
            )
            return

        try:
            terminated = lm.terminate_tree(parent)
        except Exception as e:
            _output(
                {"status": "error", "error": str(e)},
                lambda d: console.print(f"[red]Error: {d['error']}[/red]"),
            )
            raise typer.Exit(1)

        _output(
            {"status": "terminated", "parent": parent, "cascade": True, "terminated": terminated},
            lambda d: console.print(
                f"[green]Terminated tree rooted at '{d['parent']}': {len(d['terminated'])} agent(s)[/green]"
            ),
        )


@lifecycle_app.command("terminate-tree")
def lifecycle_terminate_tree(
    team: str = typer.Option(..., "--team", "-t", help="Team name"),
    root: str = typer.Option(..., "--root", "-r", help="Root agent name (tree is terminated from this agent downward)"),
):
    """Terminate an entire agent tree (root + all descendants).

    This sends SIGTERM to all processes in the tree and removes registry entries.
    Use this when a parent agent exits and its children need to be cleaned up.
    """
    from clawteam.team.lifecycle import LifecycleManager
    from clawteam.team.mailbox import MailboxManager

    mailbox = MailboxManager(team)
    lm = LifecycleManager(team, mailbox)

    try:
        terminated = lm.terminate_tree(root)
    except Exception as e:
        _output(
            {"status": "error", "error": str(e)},
            lambda d: console.print(f"[red]Error: {d['error']}[/red]"),
        )
        raise typer.Exit(1)

    _output(
        {"status": "terminated", "root": root, "terminated": terminated},
        lambda d: console.print(
            f"[green]Terminated tree rooted at '{d['root']}': {len(d['terminated'])} agent(s)[/green]"
        ),
    )


@lifecycle_app.command("list-children")
def lifecycle_list_children(
    team: str = typer.Option(..., "--team", "-t", help="Team name"),
    agent: str = typer.Option(..., "--agent", "-a", help="Agent name"),
    recursive: bool = typer.Option(False, "--recursive/-r", help="Show full descendant tree"),
):
    """List child agents of a given agent.

    By default shows only direct children. Use --recursive to show
    the full descendant tree.
    """
    from clawteam.team.lifecycle import LifecycleManager
    from clawteam.team.mailbox import MailboxManager

    mailbox = MailboxManager(team)
    lm = LifecycleManager(team, mailbox)

    if not recursive:
        children = lm.get_children(agent)
        _output(
            {"agent": agent, "children": children},
            lambda d: console.print(f"[dim]Children of '{d['agent']}': {d['children'] or '(none)'}[/dim]"),
        )
    else:
        tree = lm.get_tree(agent)

        def _fmt_tree(t: dict, indent: int = 0) -> str:
            prefix = "  " * indent
            result = f"{prefix}├── {t['agent']}\n"
            for child in t.get("children", []):
                result += _fmt_tree(child, indent + 1)
            return result

        tree_str = _fmt_tree(tree)
        _output(
            {"agent": agent, "tree": tree},
            lambda d: console.print(f"[dim]Tree for '{d['agent']}':\n{tree_str}[/dim]"),
        )


@lifecycle_app.command("show-parent")
def lifecycle_show_parent(
    team: str = typer.Option(..., "--team", "-t", help="Team name"),
    agent: str = typer.Option(..., "--agent", "-a", help="Agent name"),
):
    """Show the parent of an agent, and optionally its full ancestor chain."""
    from clawteam.team.lifecycle import LifecycleManager
    from clawteam.team.mailbox import MailboxManager

    mailbox = MailboxManager(team)
    lm = LifecycleManager(team, mailbox)

    parent = lm.get_parent(agent)
    ancestors = lm.get_ancestors(agent)

    _output(
        {
            "agent": agent,
            "parent": parent,
            "ancestors": ancestors,
        },
        lambda d: console.print(
            f"[dim]Agent '{d['agent']}'\n"
            f"  Parent: {d['parent'] or '(none)'}\n"
            f"  Ancestors: {d['ancestors'] or '(none)'}[/dim]"
        ),
    )


@lifecycle_app.command("register-child")
def lifecycle_register_child(
    team: str = typer.Option(..., "--team", "-t", help="Team name"),
    parent: str = typer.Option(..., "--parent", "-p", help="Parent agent name"),
    child: str = typer.Option(..., "--child", "-c", help="Child agent name"),
):
    """Register a child relationship between parent and child agents.

    This should be called when an agent spawns a child so that the
    parent-child relationship is tracked for cascade cleanup.
    """
    from clawteam.team.lifecycle import LifecycleManager
    from clawteam.team.mailbox import MailboxManager

    mailbox = MailboxManager(team)
    lm = LifecycleManager(team, mailbox)

    try:
        lm.register_child(parent, child)
    except Exception as e:
        _output(
            {"status": "error", "error": str(e)},
            lambda d: console.print(f"[red]Error: {d['error']}[/red]"),
        )
        raise typer.Exit(1)

    _output(
        {"status": "registered", "parent": parent, "child": child},
        lambda d: console.print(f"[green]Registered '{d['child']}' as child of '{d['parent']}'[/green]"),
    )


# ============================================================================
# Spawn Command
# ============================================================================


@app.command("spawn")
def spawn_agent(
    backend: Optional[str] = typer.Argument(
        None, help="Backend: auto (default), tmux, subprocess, openclaw_api, or openclaw_sdk"
    ),
    command: list[str] = typer.Argument(None, help="Command and arguments to run (default: openclaw)"),
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
):
    """Spawn a new agent process with identity + task as its initial prompt.

    Defaults: tmux backend, openclaw command, git worktree isolation, skip-permissions on.
    """
    from clawteam.config import get_effective
    from clawteam.spawn import get_backend

    # Resolve defaults from config
    if backend is None:
        backend, _ = get_effective("default_backend")
        backend = backend or "auto"
    if not command:
        command = ["openclaw"]

    _team = team or "default"
    _name = agent_name or f"agent-{uuid.uuid4().hex[:6]}"
    _id = uuid.uuid4().hex[:12]

    # Check agent count against recommended max (arXiv:2512.08296)
    if not force:
        from clawteam.spawn.registry import get_registry
        from clawteam.templates import DEFAULT_MAX_AGENTS, check_agent_count

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

    # Workspace: resolve from flag or config (default: auto)
    # SDK backends (openclaw_sdk, openclaw_api) don't need git worktrees
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

    if workspace and not _is_sdk_backend:
        from clawteam.workspace import get_workspace_manager

        ws_mgr = get_workspace_manager(repo)
        if ws_mgr is None:
            if ws_mode not in ("auto", ""):
                console.print("[red]Not in a git repository. Use --repo or cd into a repo.[/red]")
                raise typer.Exit(1)
        else:
            ws_info = ws_mgr.create_workspace(team_name=_team, agent_name=_name, agent_id=_id)
            cwd = _workspace_cwd_from_info(repo, ws_info)
            ws_branch = ws_info.branch_name
            console.print(f"[dim]Workspace: {cwd} (branch: {ws_branch})[/dim]")

    # Build prompt: identity + task + clawteam coordination guide
    prompt = None
    if task:
        import os as _os

        from clawteam.spawn.prompt import build_agent_prompt
        from clawteam.team.manager import TeamManager

        leader_name = TeamManager.get_leader_name(_team) or "leader"
        prompt = build_agent_prompt(
            agent_name=_name,
            agent_id=_id,
            agent_type=agent_type,
            team_name=_team,
            leader_name=leader_name,
            task=task,
            user=_os.environ.get("CLAWTEAM_USER", ""),
            workspace_dir=cwd or "",
            workspace_branch=ws_branch,
            memory_scope=f"custom:team-{_team}",
        )

    # Session resume: inject --resume flag for claude commands
    if resume:
        from clawteam.spawn.sessions import SessionStore

        session_store = SessionStore(_team)
        session = session_store.load(_name)
        if session and session.session_id:
            # Add --resume to claude command
            if command and command[0] in ("claude",):
                command = list(command) + ["--resume", session.session_id]
                console.print(f"[dim]Resuming session: {session.session_id}[/dim]")
            if prompt:
                prompt += "\nYou are resuming a previous session."

    # Auto-register agent as team member
    import os as _os2

    from clawteam.team.manager import TeamManager

    member_added = False
    try:
        TeamManager.add_member(
            team_name=_team,
            member_name=_name,
            agent_id=_id,
            agent_type=agent_type,
            user=_os2.environ.get("CLAWTEAM_USER", ""),
        )
        member_added = True
    except ValueError:
        pass  # already a member, ignore

    result = be.spawn(
        command=command,
        agent_name=_name,
        agent_id=_id,
        agent_type=agent_type,
        team_name=_team,
        prompt=prompt,
        cwd=cwd,
        skip_permissions=skip_permissions,
        openclaw_agent=openclaw_agent,
        model=model,
        parent_agent=parent or "",
    )

    if result.startswith("Error"):
        if member_added:
            TeamManager.remove_member(_team, _name)
        if ws_mgr is not None and cwd:
            try:
                ws_mgr.cleanup_workspace(_team, _name, auto_checkpoint=False)
            except Exception:
                pass
        _output({"error": result}, lambda d: console.print(f"[red]{d['error']}[/red]"))
        raise typer.Exit(1)

    # Register parent-child relationship if --parent was specified
    child_registered = False
    if parent:
        try:
            from clawteam.team.parent_child import ParentChildRegistry

            ParentChildRegistry.register(_team, _name, parent)
            child_registered = True
            console.print(f"[dim]Registered '{_name}' as child of '{parent}'[/dim]")
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to register parent-child relationship: {e}[/yellow]")

    spawn_data = {
        "status": "spawned",
        "backend": backend,
        "agentName": _name,
        "agentId": _id,
        "message": result,
    }
    if parent:
        spawn_data["parent"] = parent
        spawn_data["childRegistered"] = child_registered

    _output(
        spawn_data,
        lambda d: console.print(f"[green]OK[/green] {d['message']}"),
    )


# ============================================================================
# Identity Commands
# ============================================================================

identity_app = typer.Typer(help="Agent identity commands")
app.add_typer(identity_app, name="identity")


@identity_app.command("show")
def identity_show():
    """Show current agent identity (from environment variables)."""
    from clawteam.identity import AgentIdentity

    identity = AgentIdentity.from_env()
    data = {
        "agentId": identity.agent_id,
        "agentName": identity.agent_name,
        "user": identity.user,
        "agentType": identity.agent_type,
        "teamName": identity.team_name,
        "isLeader": identity.is_leader,
        "planModeRequired": identity.plan_mode_required,
    }

    def _human(d):
        console.print(f"Agent ID:   {d['agentId']}")
        console.print(f"Agent Name: {d['agentName']}")
        console.print(f"User:       {d['user'] or '(none)'}")
        console.print(f"Agent Type: {d['agentType']}")
        console.print(f"Team:       {d['teamName'] or '(none)'}")
        console.print(f"Is Leader:  {d['isLeader']}")
        console.print(f"Plan Mode:  {d['planModeRequired']}")

    _output(data, _human)


@identity_app.command("set")
def identity_set(
    agent_id: Optional[str] = typer.Option(None, "--agent-id", help="Agent ID"),
    agent_name: Optional[str] = typer.Option(None, "--agent-name", help="Agent name"),
    agent_type: Optional[str] = typer.Option(None, "--agent-type", help="Agent type"),
    team: Optional[str] = typer.Option(None, "--team", help="Team name"),
):
    """Print shell export commands to set identity environment variables."""
    lines = []
    if agent_id:
        lines.append(f'export CLAWTEAM_AGENT_ID="{agent_id}"')
    if agent_name:
        lines.append(f'export CLAWTEAM_AGENT_NAME="{agent_name}"')
    if agent_type:
        lines.append(f'export CLAWTEAM_AGENT_TYPE="{agent_type}"')
    if team:
        lines.append(f'export CLAWTEAM_TEAM_NAME="{team}"')

    if not lines:
        console.print("[yellow]No options specified. Use --agent-id, --agent-name, --agent-type, --team[/yellow]")
        raise typer.Exit(1)

    output = "\n".join(lines)
    if _json_output:
        print(json.dumps({"exports": lines}))
    else:
        console.print("Run the following to set your identity:\n")
        console.print(output)
        console.print(f"\nOr use: eval $(clawteam identity set {' '.join(sys.argv[3:])})")


# ============================================================================
# Board Commands
# ============================================================================

board_app = typer.Typer(help="Team dashboard and kanban board.")
app.add_typer(board_app, name="board")


@board_app.command("show")
def board_show(
    team: str = typer.Argument(..., help="Team name"),
):
    """Show detailed kanban board for a single team."""
    from clawteam.board.collector import BoardCollector
    from clawteam.board.renderer import BoardRenderer

    collector = BoardCollector()
    try:
        data = collector.collect_team(team)
    except ValueError as e:
        _output({"error": str(e)}, lambda d: console.print(f"[red]{d['error']}[/red]"))
        raise typer.Exit(1)

    _output(data, lambda d: BoardRenderer(console).render_team_board(d))


@board_app.command("overview")
def board_overview():
    """Show overview of all teams."""
    from clawteam.board.collector import BoardCollector
    from clawteam.board.renderer import BoardRenderer

    collector = BoardCollector()
    teams = collector.collect_overview()

    _output(teams, lambda d: BoardRenderer(console).render_overview(d))


@board_app.command("live")
def board_live(
    team: str = typer.Argument(..., help="Team name"),
    interval: float = typer.Option(2.0, "--interval", "-i", help="Refresh interval in seconds"),
):
    """Live-refreshing kanban board. Ctrl+C to stop."""
    from clawteam.board.collector import BoardCollector
    from clawteam.board.renderer import BoardRenderer

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


@board_app.command("monitor")
def board_monitor(
    team: str = typer.Argument(None, help="Team name (optional, monitors all teams if omitted)"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Filter by agent name"),
    status_filter: Optional[str] = typer.Option(
        None, "--status", "-s", help="Filter by status type (started/completed/terminated/error)"
    ),
    port: int = typer.Option(8080, "--port", "-p", help="Board server port"),
    reconnect: bool = typer.Option(False, "--reconnect", "-r", help="Auto-reconnect on disconnect"),
    count: bool = typer.Option(False, "--count", "-c", help="Show event counts by status"),
    no_color: bool = typer.Option(False, "--no-color", help="Disable colored output"),
    tail: int = typer.Option(0, "--tail", "-t", help="Show last N events on connect"),
):
    """Real-time agent activity monitor - stream agent events as they happen.

    Shows live agent activities including:
    - Agent started/stopped
    - Task started/completed
    - Heartbeats
    - Errors

    Requires the board server to be running (`clawteam board serve`).
    """
    import urllib.request
    import urllib.parse
    import datetime

    base_url = f"http://127.0.0.1:{port}"

    # Event counters for --count mode
    event_counts = (
        {
            "started": 0,
            "completed": 0,
            "terminated": 0,
            "error": 0,
            "task_assigned": 0,
            "heartbeat": 0,
            "message": 0,
            "other": 0,
        }
        if count
        else None
    )

    # Build SSE URL
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
        console.print("[dim]Press Ctrl+C to stop.[/dim]")
        if reconnect:
            console.print("[dim]Auto-reconnect enabled.[/dim]")
        if tail > 0:
            console.print(f"[dim]Showing last {tail} events on connect.[/dim]")
        console.print()

    def process_event(activity: dict) -> bool:
        """Process an activity event. Returns True if it should be displayed."""
        # Status filter
        if status_filter and activity.get("status") != status_filter:
            return False

        # Update counts
        if event_counts is not None:
            s = activity.get("status", "other")
            if s in event_counts:
                event_counts[s] += 1
            else:
                event_counts["other"] += 1

        return True

    def print_activity(activity: dict):
        """Print an agent activity in a formatted way."""
        ts = activity.get("timestamp", "")
        team = activity.get("team_name", "?")
        agent = activity.get("agent_name", "?")
        status = activity.get("status", "?")
        message = activity.get("message", "")

        # Format timestamp
        try:
            dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
            time_str = dt.strftime("%H:%M:%S")
        except:
            time_str = ts[11:19] if len(ts) > 19 else ts

        if _json_output:
            _output(activity)
        elif no_color:
            # No color mode
            print(f"[{time_str}] [{team}/{agent}] [{status}]: {message}")
        else:
            # Color by status
            status_colors = {
                "started": "green",
                "heartbeat": "blue",
                "completed": "cyan",
                "error": "red",
                "idle": "yellow",
                "message": "white",
                "terminated": "magenta",
                "task_assigned": "green",
            }
            color = status_colors.get(status, "white")
            header = f"[dim][{time_str}][/dim] [{team}/{agent}]"
            status_str = f"[{status}]"
            if message:
                console.print(f"{header} [bold {color}]{status_str}[/bold {color}]: {message}")
            else:
                console.print(f"{header} [bold {color}]{status_str}[/bold {color}]")

    def connect_and_stream():
        """Connect to SSE endpoint and stream events."""
        try:
            req = urllib.request.Request(url, headers={"Accept": "text/event-stream"})
            with urllib.request.urlopen(req, timeout=30) as response:
                for line in response:
                    line = line.decode("utf-8").strip()
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if data.get("type") == "connected":
                            if not _json_output:
                                console.print("[green]Connected![/green] Waiting for agent activity...")
                                console.print("-" * 60)
                        elif data.get("type") == "activity":
                            activity = data["data"]
                            if process_event(activity):
                                print_activity(activity)
                        elif data.get("type") == "heartbeat":
                            pass  # Skip heartbeat comments
                return True  # Connection closed normally
        except Exception as e:
            return str(e)  # Return error message

    # Main loop with optional reconnect
    while True:
        result = connect_and_stream()

        if isinstance(result, bool):
            # Normal exit
            break

        # Error occurred
        if not reconnect:
            _output({"error": result}, lambda d: console.print(f"[red]Error: {d['error']}[/red]"))
            break

        # Reconnect mode
        if not _json_output:
            console.print(f"[yellow]Connection lost: {result}[/yellow]")
            console.print("[dim]Reconnecting in 3 seconds...[/dim]")
        import time

        time.sleep(3)
        if not _json_output:
            console.print(f"[dim]Reconnecting to {url}...[/dim]")

    # Print counts if requested
    if event_counts and not _json_output:
        console.print()
        console.print("[bold]Event Summary:[/bold]")
        for status_name, cnt in event_counts.items():
            if cnt > 0:
                console.print(f"  {status_name}: {cnt}")

    if not _json_output:
        console.print("\n[dim]Disconnected.[/dim]")


def _print_agent_activity(activity: dict):
    """Print an agent activity in a formatted way."""
    import datetime

    ts = activity.get("timestamp", "")
    team = activity.get("team_name", "?")
    agent = activity.get("agent_name", "?")
    status = activity.get("status", "?")
    message = activity.get("message", "")

    # Format timestamp
    try:
        dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        time_str = dt.strftime("%H:%M:%S")
    except:
        time_str = ts[11:19] if len(ts) > 19 else ts

    # Color by status
    status_colors = {
        "started": "green",
        "heartbeat": "blue",
        "completed": "cyan",
        "error": "red",
        "idle": "yellow",
        "message": "white",
    }
    color = status_colors.get(status, "white")

    if _json_output:
        _output(activity)
    else:
        # Format: [HH:MM:SS] [team/agent] STATUS: message
        header = f"[dim][{time_str}][/dim] [{team}/{agent}]"
        status_str = f"[{status}]"
        if message:
            console.print(f"{header} [bold {color}]{status_str}[/bold {color}]: {message}")
        else:
            console.print(f"{header} [bold {color}]{status_str}[/bold {color}]")


@board_app.command("serve")
def board_serve(
    team: Optional[str] = typer.Argument(None, help="Team name (optional, shows all if omitted)"),
    port: int = typer.Option(8080, "--port", "-p", help="HTTP server port"),
    host: str = typer.Option("127.0.0.1", "--host", help="Bind address"),
    interval: float = typer.Option(2.0, "--interval", "-i", help="SSE push interval in seconds"),
):
    """Start Web UI dashboard server."""
    from clawteam.board.server import serve

    console.print(f"Starting Web UI on http://{host}:{port}")
    if team:
        console.print(f"Default team: {team}")
    console.print("Press Ctrl+C to stop.")
    serve(host=host, port=port, default_team=team or "", interval=interval)


@board_app.command("attach")
def board_attach(
    team: str = typer.Argument(..., help="Team name"),
):
    """Attach to tmux session with all agent windows tiled side by side.

    Merges all agent tmux windows into a single tiled view so you can
    watch every agent working simultaneously.
    """
    from clawteam.spawn.tmux_backend import TmuxBackend

    result = TmuxBackend.attach_all(team)
    if result.startswith("Error"):
        console.print(f"[red]{result}[/red]")
        raise typer.Exit(1)
    console.print(f"[green]OK[/green] {result}")


# ============================================================================
# Workspace Commands
# ============================================================================

workspace_app = typer.Typer(help="Git worktree workspace management")
app.add_typer(workspace_app, name="workspace")


@workspace_app.command("list")
def workspace_list(
    team: str = typer.Argument(..., help="Team name"),
    repo: Optional[str] = typer.Option(None, "--repo", help="Git repo path"),
):
    """List all active worktree workspaces for a team."""
    from clawteam.workspace import get_workspace_manager

    ws_mgr = get_workspace_manager(repo)
    if ws_mgr is None:
        _output({"error": "Not in a git repo"}, lambda d: console.print(f"[red]{d['error']}[/red]"))
        raise typer.Exit(1)

    workspaces = ws_mgr.list_workspaces(team)
    if _json_output:
        _output(
            {"workspaces": [w.model_dump() for w in workspaces]},
            lambda d: None,
        )
        return

    if not workspaces:
        console.print(f"No active workspaces for team '{team}'.")
        return

    table = Table(title=f"Workspaces — {team}")
    table.add_column("Agent")
    table.add_column("Branch")
    table.add_column("Path")
    table.add_column("Created")
    for ws in workspaces:
        table.add_row(ws.agent_name, ws.branch_name, ws.worktree_path, ws.created_at[:19])
    console.print(table)


@workspace_app.command("checkpoint")
def workspace_checkpoint(
    team: str = typer.Argument(..., help="Team name"),
    agent: str = typer.Argument(..., help="Agent name"),
    repo: Optional[str] = typer.Option(None, "--repo", help="Git repo path"),
    message: Optional[str] = typer.Option(None, "--message", "-m", help="Commit message"),
):
    """Create a checkpoint (auto-commit) for an agent's workspace."""
    from clawteam.workspace import get_workspace_manager

    ws_mgr = get_workspace_manager(repo)
    if ws_mgr is None:
        console.print("[red]Not in a git repo.[/red]")
        raise typer.Exit(1)

    committed = ws_mgr.checkpoint(team, agent, message)
    if committed:
        _output(
            {"status": "checkpoint_created", "team": team, "agent": agent},
            lambda d: console.print(f"[green]OK[/green] Checkpoint created for '{agent}'."),
        )
    else:
        _output(
            {"status": "no_changes", "team": team, "agent": agent},
            lambda d: console.print(f"[dim]No changes to checkpoint for '{agent}'.[/dim]"),
        )


@workspace_app.command("merge")
def workspace_merge(
    team: str = typer.Argument(..., help="Team name"),
    agent: str = typer.Argument(..., help="Agent name"),
    repo: Optional[str] = typer.Option(None, "--repo", help="Git repo path"),
    target: Optional[str] = typer.Option(None, "--target", help="Target branch (default: base branch)"),
    no_cleanup: bool = typer.Option(False, "--no-cleanup", help="Keep worktree after merge"),
):
    """Merge an agent's workspace branch back to the base branch."""
    from clawteam.workspace import get_workspace_manager

    ws_mgr = get_workspace_manager(repo)
    if ws_mgr is None:
        console.print("[red]Not in a git repo.[/red]")
        raise typer.Exit(1)

    success, output = ws_mgr.merge_workspace(team, agent, target, cleanup_after=not no_cleanup)
    if success:
        _output(
            {"status": "merged", "team": team, "agent": agent, "output": output},
            lambda d: console.print(f"[green]OK[/green] Merged '{agent}' workspace.\n{output}"),
        )
    else:
        _output(
            {"status": "merge_failed", "team": team, "agent": agent, "output": output},
            lambda d: console.print(f"[red]Merge failed[/red] for '{agent}':\n{output}"),
        )
        raise typer.Exit(1)


@workspace_app.command("cleanup")
def workspace_cleanup(
    team: str = typer.Argument(..., help="Team name"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent name (all if omitted)"),
    repo: Optional[str] = typer.Option(None, "--repo", help="Git repo path"),
):
    """Clean up worktree workspace(s) — removes worktree and branch."""
    from clawteam.workspace import get_workspace_manager

    ws_mgr = get_workspace_manager(repo)
    if ws_mgr is None:
        console.print("[red]Not in a git repo.[/red]")
        raise typer.Exit(1)

    if agent:
        ok = ws_mgr.cleanup_workspace(team, agent)
        if ok:
            console.print(f"[green]OK[/green] Cleaned up workspace for '{agent}'.")
        else:
            console.print(f"[yellow]No workspace found for '{agent}'.[/yellow]")
    else:
        count = ws_mgr.cleanup_team(team)
        console.print(f"[green]OK[/green] Cleaned up {count} workspace(s) for team '{team}'.")


@workspace_app.command("status")
def workspace_status(
    team: str = typer.Argument(..., help="Team name"),
    agent: str = typer.Argument(..., help="Agent name"),
    repo: Optional[str] = typer.Option(None, "--repo", help="Git repo path"),
):
    """Show git diff stat for an agent's workspace."""
    from clawteam.workspace import get_workspace_manager, git

    ws_mgr = get_workspace_manager(repo)
    if ws_mgr is None:
        console.print("[red]Not in a git repo.[/red]")
        raise typer.Exit(1)

    ws = ws_mgr.get_workspace(team, agent)
    if ws is None:
        console.print(f"[yellow]No workspace found for '{agent}'.[/yellow]")
        raise typer.Exit(1)

    stat = git.diff_stat(Path(ws.worktree_path))
    console.print(f"[bold]Workspace status — {agent}[/bold] (branch: {ws.branch_name})")
    console.print(stat)


# ============================================================================
# Template Commands
# ============================================================================

template_app = typer.Typer(help="Template management")
app.add_typer(template_app, name="template")


@template_app.command("list")
def template_list():
    """List all available templates (builtin + user)."""
    from clawteam.templates import list_templates

    templates = list_templates()

    def _human(data):
        if not data:
            console.print("[dim]No templates found[/dim]")
            return
        table = Table(title="Templates")
        table.add_column("Name", style="cyan")
        table.add_column("Description")
        table.add_column("Source", style="dim")
        for t in data:
            table.add_row(t["name"], t["description"], t["source"])
        console.print(table)

    _output(templates, _human)


@template_app.command("show")
def template_show(
    name: str = typer.Argument(..., help="Template name"),
):
    """Show details of a template."""
    from clawteam.templates import load_template

    try:
        tmpl = load_template(name)
    except FileNotFoundError as e:
        _output({"error": str(e)}, lambda d: console.print(f"[red]{d['error']}[/red]"))
        raise typer.Exit(1)

    data = json.loads(tmpl.model_dump_json(by_alias=True))

    def _human(_data):
        console.print(f"[bold cyan]{tmpl.name}[/bold cyan] — {tmpl.description}")
        console.print(f"  Command: {' '.join(tmpl.command)}")
        console.print(f"  Backend: {tmpl.backend}")
        console.print()

        console.print("[bold]Leader:[/bold]")
        console.print(f"  {tmpl.leader.name} (type: {tmpl.leader.type})")
        console.print()

        if tmpl.agents:
            table = Table(title="Agents")
            table.add_column("Name", style="cyan")
            table.add_column("Type")
            for a in tmpl.agents:
                table.add_row(a.name, a.type)
            console.print(table)

        if tmpl.tasks:
            table = Table(title="Tasks")
            table.add_column("Subject")
            table.add_column("Owner", style="cyan")
            for t in tmpl.tasks:
                table.add_row(t.subject, t.owner)
            console.print(table)

    _output(data, _human)


# ============================================================================
# Launch Command
# ============================================================================


@app.command("launch")
def launch_team(
    template: str = typer.Argument(..., help="Template name (e.g., hedge-fund)"),
    goal: str = typer.Option("", "--goal", "-g", help="Project goal injected into agent prompts"),
    backend: Optional[str] = typer.Option(None, "--backend", "-b", help="Override backend"),
    team_name: Optional[str] = typer.Option(None, "--team-name", "-t", help="Override team name"),
    workspace: bool = typer.Option(False, "--workspace/--no-workspace", "-w"),
    repo: Optional[str] = typer.Option(None, "--repo", help="Git repo path"),
    command_override: Optional[list[str]] = typer.Option(None, "--command", help="Override agent command"),
    force: bool = typer.Option(False, "--force", "-f", help="Suppress max-agent warnings"),
    model_override: Optional[str] = typer.Option(None, "--model", help="Override model for ALL agents"),
    model_strategy_override: Optional[str] = typer.Option(None, "--model-strategy", help="Model strategy: auto | none"),
):
    """Launch a full agent team from a template with one command."""
    import os as _os

    from clawteam.model_resolution import resolve_model
    from clawteam.spawn import get_backend
    from clawteam.spawn.prompt import build_agent_prompt
    from clawteam.team.manager import TeamManager
    from clawteam.team.tasks import TaskStore
    from clawteam.templates import TemplateDef, load_template, render_task

    # 1. Load template
    try:
        tmpl: TemplateDef = load_template(template)
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    # Check agent count against template max_agents
    if not force:
        from clawteam.templates import check_agent_count

        total_agents = len(tmpl.agents) + 1  # agents + leader
        warning = check_agent_count(total_agents - 1, tmpl.max_agents)
        if warning:
            console.print(f"[yellow]{warning}[/yellow]")

    # 2. Determine team name
    t_name = team_name or f"{tmpl.name}-{uuid.uuid4().hex[:6]}"
    be_name = backend or tmpl.backend
    cmd = command_override or tmpl.command

    # 3. Create team
    leader_id = uuid.uuid4().hex[:12]
    try:
        TeamManager.create_team(
            name=t_name,
            leader_name=tmpl.leader.name,
            leader_id=leader_id,
            description=tmpl.description,
            user=_os.environ.get("CLAWTEAM_USER", ""),
        )
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    # 4. Add members
    agent_ids: dict[str, str] = {tmpl.leader.name: leader_id}
    for agent in tmpl.agents:
        aid = uuid.uuid4().hex[:12]
        agent_ids[agent.name] = aid
        TeamManager.add_member(
            team_name=t_name,
            member_name=agent.name,
            agent_id=aid,
            agent_type=agent.type,
            user=_os.environ.get("CLAWTEAM_USER", ""),
        )

    # 5. Create tasks
    ts = TaskStore(t_name)
    for task_def in tmpl.tasks:
        ts.create(
            subject=task_def.subject,
            description=task_def.description,
            owner=task_def.owner,
        )

    # 6. Get backend
    try:
        be = get_backend(be_name)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    # 7. Workspace setup (optional)
    ws_mgr = None
    if workspace:
        from clawteam.workspace import get_workspace_manager

        ws_mgr = get_workspace_manager(repo)
        if ws_mgr is None:
            console.print("[red]Not in a git repository. Use --repo or cd into a repo.[/red]")
            raise typer.Exit(1)

    # 8. Spawn all agents (leader first, then workers)
    # Load config once for model resolution (avoid re-reading per agent)
    from clawteam.config import load_config as _load_config

    _model_cfg = _load_config()

    all_agents = [tmpl.leader] + list(tmpl.agents)
    spawned: list[dict[str, str]] = []

    for agent in all_agents:
        a_id = agent_ids[agent.name]
        a_cmd = agent.command or cmd

        # Variable substitution
        rendered = render_task(
            agent.task,
            goal=goal,
            team_name=t_name,
            agent_name=agent.name,
        )

        # Workspace
        cwd = None
        ws_branch = ""
        if ws_mgr:
            ws_info = ws_mgr.create_workspace(
                team_name=t_name,
                agent_name=agent.name,
                agent_id=a_id,
            )
            cwd = _workspace_cwd_from_info(repo, ws_info)
            ws_branch = ws_info.branch_name

        # Build prompt
        prompt = build_agent_prompt(
            agent_name=agent.name,
            agent_id=a_id,
            agent_type=agent.type,
            team_name=t_name,
            leader_name=tmpl.leader.name,
            task=rendered,
            user=_os.environ.get("CLAWTEAM_USER", ""),
            workspace_dir=cwd or "",
            workspace_branch=ws_branch,
            memory_scope=f"custom:team-{t_name}",
            intent=agent.intent or "",
            end_state=agent.end_state or "",
            constraints=agent.constraints,
            team_size=len(all_agents),
        )

        # Resolve skip_permissions from config
        from clawteam.config import get_effective

        sp_val, _ = get_effective("skip_permissions")
        _skip = str(sp_val).lower() not in ("false", "0", "no", "")

        # Resolve model for this agent (CLI override > agent > tier > strategy > template > config)
        resolved_model = resolve_model(
            cli_model=model_override,
            agent_model=agent.model,
            agent_model_tier=agent.model_tier,
            template_model_strategy=model_strategy_override or tmpl.model_strategy,
            template_model=tmpl.model,
            config_default_model=_model_cfg.default_model,
            agent_type=agent.type,
            tier_overrides=_model_cfg.model_tiers or None,
        )

        spawn_kwargs = dict(
            command=a_cmd,
            agent_name=agent.name,
            agent_id=a_id,
            agent_type=agent.type,
            team_name=t_name,
            prompt=prompt,
            cwd=cwd,
            skip_permissions=_skip,
            model=resolved_model,
        )
        if agent.retry:
            from clawteam.spawn import spawn_with_retry

            result = spawn_with_retry(
                be,
                max_retries=agent.retry.max_retries,
                backoff_base=agent.retry.backoff_base_seconds,
                backoff_max=agent.retry.backoff_max_seconds,
                **spawn_kwargs,
            )
        else:
            result = be.spawn(**spawn_kwargs)
        spawned.append({"name": agent.name, "id": a_id, "type": agent.type, "result": result})

    # 9. Output summary
    out = {
        "status": "launched",
        "team": t_name,
        "template": tmpl.name,
        "backend": be_name,
        "agents": [{"name": s["name"], "id": s["id"], "type": s["type"]} for s in spawned],
    }

    def _human(_data):
        console.print(f"\n[green bold]Team '{t_name}' launched from template '{tmpl.name}'[/green bold]\n")
        table = Table(title="Agents")
        table.add_column("Name", style="cyan")
        table.add_column("Type")
        table.add_column("ID", style="dim")
        for s in spawned:
            table.add_row(s["name"], s["type"], s["id"])
        console.print(table)
        console.print()
        if be_name == "tmux":
            console.print(f"[bold]Attach:[/bold] tmux attach -t clawteam-{t_name}")
        console.print(f"[bold]Board:[/bold]  clawteam board show {t_name}")
        console.print(f"[bold]Inbox:[/bold]  clawteam inbox peek {t_name} --agent <name>")

    _output(out, _human)


# ============================================================================
# Review Commands (P0 Quality Scoring)
# ============================================================================

review_app = typer.Typer(help="Quality review and scoring for completed tasks")
app.add_typer(review_app, name="review")


@review_app.command("score")
def review_score(
    team: str = typer.Argument(..., help="Team name"),
    task_id: str = typer.Argument(..., help="Task ID to score"),
    completeness: int = typer.Option(0, "--completeness", "-c", min=0, max=10, help="Completeness score (0-10)"),
    accuracy: int = typer.Option(0, "--accuracy", "-a", min=0, max=10, help="Accuracy score (0-10)"),
    quality: int = typer.Option(0, "--quality", "-q", min=0, max=10, help="Quality score (0-10)"),
    规范性: int = typer.Option(0, "--规范性", "-n", min=0, max=10, help="规范性 score (0-10)"),
    innovation: int = typer.Option(0, "--innovation", "-i", min=0, max=10, help="Innovation score (0-10)"),
    scorer: str = typer.Option("leader", "--scorer", "-s", help="Who is scoring (agent name)"),
    feedback: str = typer.Option("", "--feedback", "-f", help="Free-text feedback"),
):
    """Score a completed task on 5 dimensions."""
    from clawteam.store.file import FileTaskStore
    from clawteam.team.models import QualityScore

    store = FileTaskStore(team)
    task = store.get(task_id)
    if task is None:
        console.print(f"[red]Task '{task_id}' not found in team '{team}'.[/red]")
        raise typer.Exit(1)

    score = QualityScore(
        completeness=completeness,
        accuracy=accuracy,
        quality=quality,
        规范性=规范性,
        innovation=innovation,
        scorer=scorer,
        feedback=feedback,
    )
    task.scores.append(score)
    with store._write_lock():
        store._save_unlocked(task)

    def _human(_data):
        console.print(f"[green]Scored task '{task_id}' ({task.subject})[/green]")
        console.print(f"  完整性: {completeness}/10  准确性: {accuracy}/10  质量: {quality}/10")
        console.print(f"  规范性: {规范性}/10  创新性: {innovation}/10")
        console.print(f"  [bold]总分: {score.total}/100[/bold]")
        if feedback:
            console.print(f"  [dim]反馈: {feedback}[/dim]")

    _output(
        {"task_id": task_id, "subject": task.subject, "score": score.model_dump(by_alias=True)},
        _human,
    )


@review_app.command("show")
def review_show(
    team: str = typer.Argument(..., help="Team name"),
    owner: str = typer.Option(None, "--owner", "-o", help="Filter by owner (agent name)"),
    sort_by_score: bool = typer.Option(False, "--sort", "-S", help="Sort by total score (highest first)"),
):
    """Show all task scores for a team."""
    from clawteam.store.file import FileTaskStore
    from clawteam.team.models import TaskStatus

    store = FileTaskStore(team)
    tasks = store.list_tasks(status=TaskStatus.completed)

    if owner:
        tasks = [t for t in tasks if t.owner == owner]

    scored_tasks = [t for t in tasks if t.scores]
    if not scored_tasks:
        console.print(f"[yellow]No scored tasks found for team '{team}'.[/yellow]")
        return

    if sort_by_score:
        scored_tasks.sort(key=lambda t: max((s.total for s in t.scores), default=0), reverse=True)

    def _human(_data):
        table = Table(title=f"Task Scores — Team '{team}'")
        table.add_column("Task", style="cyan")
        table.add_column("Owner")
        table.add_column("完整性", justify="right")
        table.add_column("准确性", justify="right")
        table.add_column("质量", justify="right")
        table.add_column("规范性", justify="right")
        table.add_column("创新性", justify="right")
        table.add_column("总分", justify="right", style="bold")

        for t in scored_tasks:
            best = max(t.scores, key=lambda s: s.total) if t.scores else None
            if best:
                table.add_row(
                    t.subject[:30],
                    t.owner or "-",
                    str(best.completeness),
                    str(best.accuracy),
                    str(best.quality),
                    str(best.规范性),
                    str(best.innovation),
                    f"{best.total}",
                )
        console.print(table)
        console.print(f"\n[dim]{len(scored_tasks)} scored task(s)[/dim]")

    _output(
        [
            {
                "task_id": t.id,
                "subject": t.subject,
                "owner": t.owner,
                "best_score": max(t.scores, key=lambda s: s.total).model_dump(by_alias=True) if t.scores else None,
            }
            for t in scored_tasks
        ],
        _human,
    )


@review_app.command("compare")
def review_compare(
    team: str = typer.Argument(..., help="Team name"),
    subject_keyword: str = typer.Argument(..., help="Keyword to match task subjects for comparison"),
):
    """Compare scores for tasks with similar subjects (multi-agent same-task comparison)."""
    from clawteam.store.file import FileTaskStore
    from clawteam.team.models import TaskStatus

    store = FileTaskStore(team)
    tasks = store.list_tasks(status=TaskStatus.completed)

    # Filter by subject keyword
    matched = [t for t in tasks if subject_keyword.lower() in t.subject.lower() and t.scores]
    if not matched:
        console.print(f"[yellow]No scored tasks matching '{subject_keyword}' found.[/yellow]")
        return

    def _human(_data):
        table = Table(title=f"Comparison — '{subject_keyword}'")
        table.add_column("Task", style="cyan")
        table.add_column("Owner", style="magenta")
        table.add_column("完整性", justify="right")
        table.add_column("准确性", justify="right")
        table.add_column("质量", justify="right")
        table.add_column("规范性", justify="right")
        table.add_column("创新性", justify="right")
        table.add_column("总分", justify="right", style="bold")
        table.add_column("推荐", justify="center")

        best_task = max(matched, key=lambda t: max((s.total for s in t.scores), default=0))
        for t in matched:
            best = max(t.scores, key=lambda s: s.total) if t.scores else None
            if best:
                is_best = "*" if t.id == best_task.id else ""
                table.add_row(
                    t.subject[:30],
                    t.owner or "-",
                    str(best.completeness),
                    str(best.accuracy),
                    str(best.quality),
                    str(best.规范性),
                    str(best.innovation),
                    f"{best.total}",
                    is_best,
                )
        console.print(table)
        console.print(
            f"\n[green bold]推荐: {best_task.subject} (Owner: {best_task.owner}, Score: {max(best_task.scores, key=lambda s: s.total).total})[/green bold]"
        )

    _output(
        [
            {
                "task_id": t.id,
                "subject": t.subject,
                "owner": t.owner,
                "best_score": max(t.scores, key=lambda s: s.total).model_dump(by_alias=True) if t.scores else None,
            }
            for t in matched
        ],
        _human,
    )


drift_app = typer.Typer(help="Drift detection — detect when agent output diverges from task intent.")
app.add_typer(drift_app, name="drift")


@drift_app.command("check")
def drift_check(
    team: str = typer.Argument(..., help="Team name"),
    task_id: str = typer.Argument(..., help="Task ID to check"),
    output: str = typer.Option(..., "--output", "-o", help="Agent's completion report or deliverable description"),
    threshold: float = typer.Option(0.5, "--threshold", "-t", min=0.0, max=1.0, help="Drift threshold (below = alert)"),
):
    """Check a task for drift between original intent and actual output."""
    from clawteam.store.file import FileTaskStore
    from clawteam.team.drift import check_task_drift

    store = FileTaskStore(team)
    task = store.get(task_id)
    if task is None:
        console.print(f"[red]Task '{task_id}' not found in team '{team}'.[/red]")
        raise typer.Exit(1)

    result = check_task_drift(task, output, threshold)

    def _human(_data):
        status_icon = "[green]* Aligned[/green]" if result["aligned"] else "[red]! DRIFT DETECTED[/red]"
        console.print(f"[bold]Drift Check: {task.subject}[/bold] {status_icon}")
        console.print(f"  Task ID: {task.id}")
        console.print(f"  Drift Score: {result['drift_score']:.3f} (threshold: {threshold})")
        console.print(f"  Keyword Overlap (Jaccard): {result['jaccard_similarity']:.3f}")

        if result["missing_key_terms"]:
            console.print(f"  [yellow]Missing key terms:[/yellow] {', '.join(result['missing_key_terms'])}")
        if result["extra_key_terms"]:
            console.print(f"  [dim]Extra terms in output:[/dim] {', '.join(result['extra_key_terms'])}")

        if result["alert"]:
            alert = result["alert"]
            severity_icon = {
                "low": "[yellow]![/yellow]",
                "medium": "[orange3]!![/orange3]",
                "high": "[red]!!![/red]",
                "critical": "[red bold]XXXX[/red bold]",
            }.get(alert["severity"], "!")
            console.print(
                f"  {severity_icon} Alert severity: [bold]{alert['severity']}[/bold] (score: {alert['driftScore']:.3f})"
            )
            console.print(f"  [dim]Original: {alert['originalSubject']}[/dim]")
            console.print(f"  [dim]Actual: {alert['actualOutput'][:100]}...[/dim]")

    _output(result, _human)


@drift_app.command("list")
def drift_list(
    team: str = typer.Argument(..., help="Team name"),
    severity: str = typer.Option("", "--severity", "-s", help="Filter by severity: low/medium/high/critical"),
    unacked: bool = typer.Option(False, "--unacked", "-u", help="Show only unacknowledged alerts"),
):
    """List all drift alerts for a team."""
    from clawteam.store.file import FileTaskStore
    from clawteam.team.models import TaskStatus

    store = FileTaskStore(team)
    tasks = store.list_tasks(status=TaskStatus.completed)

    alerts = []
    for task in tasks:
        for alert in task.drift_alerts:
            if severity and alert.severity != severity:
                continue
            if unacked and alert.acknowledged:
                continue
            alerts.append(
                {
                    "task_id": task.id,
                    "subject": task.subject,
                    "owner": task.owner,
                    **alert.model_dump(by_alias=True),
                }
            )

    def _human(_data):
        if not alerts:
            console.print("[dim]No drift alerts found.[/dim]")
            return

        from rich.table import Table

        table = Table(title=f"Drift Alerts — Team '{team}'")
        table.add_column("Task", style="cyan")
        table.add_column("Owner", style="blue")
        table.add_column("Score", justify="right")
        table.add_column("Severity")
        table.add_column("Ack")

        severity_icon = {
            "low": "[yellow]![/yellow]",
            "medium": "[orange3]!![/orange3]",
            "high": "[red]!!![/red]",
            "critical": "[red bold]XXXX[/red bold]",
        }
        for a in sorted(alerts, key=lambda x: x["driftScore"]):
            table.add_row(
                a["originalSubject"][:30],
                a.get("owner", ""),
                f"{a['driftScore']:.2f}",
                f"{severity_icon.get(a['severity'], '!')} {a['severity']}",
                "*" if a["acknowledged"] else "-",
            )
        console.print(table)
        console.print(f"\n[dim]{len(alerts)} alert(s)[/dim]")

    _output(alerts, _human)


@drift_app.command("ack")
def drift_ack(
    team: str = typer.Argument(..., help="Team name"),
    task_id: str = typer.Argument(..., help="Task ID containing the alert"),
    alert_index: int = typer.Argument(..., help="Index of alert in task.drift_alerts (0-based)"),
    notes: str = typer.Option("", "--notes", "-n", help="Acknowledgment notes"),
):
    """Acknowledge a drift alert."""
    from clawteam.store.file import FileTaskStore

    store = FileTaskStore(team)
    task = store.get(task_id)
    if task is None:
        console.print(f"[red]Task '{task_id}' not found.[/red]")
        raise typer.Exit(1)

    if alert_index < 0 or alert_index >= len(task.drift_alerts):
        console.print(f"[red]Alert index {alert_index} out of range (0-{len(task.drift_alerts) - 1}).[/red]")
        raise typer.Exit(1)

    alert = task.drift_alerts[alert_index]
    alert.acknowledged = True
    alert.acknowledged_by = "leader"
    alert.notes = notes
    task.updated_at = _now_iso()

    with store._write_lock():
        store._save_unlocked(task)

    def _human(_data):
        console.print(f"[green]* Acknowledged drift alert #{alert_index} for task '{task_id}'[/green]")
        if notes:
            console.print(f"  [dim]Notes: {notes}[/dim]")

    _output({"task_id": task_id, "alert_index": alert_index, "acknowledged": True}, _human)


@drift_app.command("record")
def drift_record(
    team: str = typer.Argument(..., help="Team name"),
    task_id: str = typer.Argument(..., help="Task ID"),
    output: str = typer.Option(..., "--output", "-o", help="Agent's completion report"),
    threshold: float = typer.Option(0.5, "--threshold", "-t", help="Drift threshold"),
):
    """Run drift check and auto-record alert on the task (for automated workflows)."""
    from clawteam.store.file import FileTaskStore
    from clawteam.team.drift import detect_drift

    store = FileTaskStore(team)
    task = store.get(task_id)
    if task is None:
        console.print(f"[red]Task '{task_id}' not found.[/red]")
        raise typer.Exit(1)

    alert = detect_drift(task, output)

    def _human(_data):
        if alert is None:
            console.print(f"[green]* No drift detected for '{task.subject}' (score: above threshold)[/green]")
        else:
            severity_icon = {
                "low": "[yellow]![/yellow]",
                "medium": "[orange3]!![/orange3]",
                "high": "[red]!!![/red]",
                "critical": "[red bold]XXXX[/red bold]",
            }.get(alert.severity, "!")
            console.print(f"{severity_icon} [bold]{alert.severity.upper()}[/bold] drift detected for '{task.subject}'")
            console.print(f"  Score: {alert.drift_score:.3f} (threshold: {threshold})")

    _output({"task_id": task_id, "alert": alert.model_dump(by_alias=True) if alert else None}, _human)

    if alert:
        task.drift_alerts.append(alert)
        task.updated_at = _now_iso()
        with store._write_lock():
            store._save_unlocked(task)


@drift_app.command("scan")
def drift_scan(
    team: str = typer.Argument(..., help="Team name"),
    threshold: float = typer.Option(0.5, "--threshold", "-t", help="Drift threshold"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """Scan all completed tasks that have output in metadata but no drift alerts yet.

    This is useful for retroactively running drift detection on tasks that
    were completed before drift detection was enabled, or after algorithm updates.
    """
    from clawteam.store.file import FileTaskStore
    from clawteam.team.drift import detect_drift
    from clawteam.team.models import TaskStatus

    store = FileTaskStore(team)
    tasks = store.list_tasks(status=TaskStatus.completed)

    scanned = 0
    new_alerts = 0
    results = []

    for task in tasks:
        # Skip tasks that already have drift alerts
        if task.drift_alerts:
            continue

        # Look for output in metadata
        actual_output = (
            task.metadata.get("output", "")
            or task.metadata.get("result", "")
            or task.metadata.get("completion_text", "")
        )
        if not actual_output:
            continue

        scanned += 1
        alert = detect_drift(task, actual_output)

        if alert is not None:
            new_alerts += 1
            task.drift_alerts.append(alert)
            task.updated_at = _now_iso()
            with store._write_lock():
                store._save_unlocked(task)
            results.append(
                {
                    "task_id": task.id,
                    "subject": task.subject,
                    "drift_score": alert.drift_score,
                    "severity": alert.severity,
                }
            )

    def _human(_data):
        console.print(f"[bold]Drift Scan — Team '{team}'[/bold]")
        console.print(f"  Completed tasks: {len(tasks)}")
        console.print(f"  Scanned: {scanned}")
        console.print(f"  New alerts: {new_alerts}")
        if results:
            console.print()
            for r in results:
                severity_icon = {
                    "low": "[yellow]![/yellow]",
                    "medium": "[orange3]!![/orange3]",
                    "high": "[red]!!![/red]",
                    "critical": "[red bold]XXXX[/red bold]",
                }.get(r["severity"], "!")
                console.print(
                    f"  {severity_icon} [{r['task_id']}] {r['subject']} — score: {r['drift_score']:.3f} ({r['severity']})"
                )
        else:
            console.print("[green]* No drift detected on any completed task.[/green]")

    _output({"scanned": scanned, "new_alerts": new_alerts, "results": results}, _human)


# ============================================================================
# Alert Commands
# ============================================================================

alert_app = typer.Typer(help="Alert management commands")
app.add_typer(alert_app, name="alert")


@alert_app.command("check")
def alert_check(
    team: str = typer.Argument(..., help="Team name"),
):
    """Check for new alerts based on current team activity."""
    from clawteam.alerts import check_all_alerts

    alerts = check_all_alerts(team)

    def _human(_data):
        if not alerts:
            console.print("[green]* No new alerts detected.[/green]")
        else:
            console.print(f"[bold]New Alerts — Team '{team}'[/bold]")
            for alert in alerts:
                severity_icon = {
                    "low": "[yellow]![/yellow]",
                    "medium": "[orange3]!![/orange3]",
                    "high": "[red]!!![/red]",
                    "critical": "[red bold]XXXX[/red bold]",
                }.get(alert.severity, "!")
                console.print(f"  {severity_icon} [{alert.alert_id[:8]}] {alert.message}")

    _output({"team": team, "alerts": [a.model_dump(by_alias=True) for a in alerts]}, _human)


@alert_app.command("list")
def alert_list(
    team: str = typer.Argument(..., help="Team name"),
    acknowledged: bool = typer.Option(
        None, "--acknowledged/--unacknowledged", "-a/-u", help="Filter by acknowledgment status"
    ),
    alert_type: str = typer.Option(None, "--type", "-t", help="Filter by alert type"),
    severity: str = typer.Option(None, "--severity", "-s", help="Filter by severity"),
):
    """List all alerts for a team."""
    from clawteam.alerts import AlertSeverity, AlertType, list_alerts

    # Convert string filters to enums if provided
    type_enum = AlertType(alert_type) if alert_type else None
    severity_enum = AlertSeverity(severity) if severity else None

    alerts = list_alerts(
        team=team,
        acknowledged=acknowledged,
        alert_type=type_enum,
        severity=severity_enum,
    )

    def _human(_data):
        if not alerts:
            console.print(f"[green]* No alerts found for team '{team}'.[/green]")
        else:
            console.print(f"[bold]Alerts — Team '{team}' ({len(alerts)} total)[/bold]")
            table = Table(show_header=True, header_style="bold")
            table.add_column("ID", style="dim", width=8)
            table.add_column("Type")
            table.add_column("Severity")
            table.add_column("Acknowledged")
            table.add_column("Message")

            for alert in alerts:
                ack_status = "[green]✓[/green]" if alert.acknowledged else "[red]✗[/red]"
                severity_color = {
                    "low": "yellow",
                    "medium": "orange3",
                    "high": "red",
                    "critical": "red bold",
                }.get(alert.severity, "white")
                table.add_row(
                    alert.alert_id[:8],
                    alert.alert_type,
                    f"[{severity_color}]{alert.severity.upper()}[/{severity_color}]",
                    ack_status,
                    alert.message,
                )

            console.print(table)

    _output({"team": team, "alerts": [a.model_dump(by_alias=True) for a in alerts]}, _human)


@alert_app.command("ack")
def alert_acknowledge(
    team: str = typer.Argument(..., help="Team name"),
    alert_id: str = typer.Argument(..., help="Alert ID to acknowledge"),
    by: str = typer.Option("cli-user", "--by", "-b", help="Who is acknowledging the alert"),
):
    """Acknowledge an alert."""
    from clawteam.alerts import acknowledge_alert, get_alert

    success = acknowledge_alert(team, alert_id, by)
    alert = get_alert(team, alert_id)

    def _human(_data):
        if success:
            console.print(f"[green]* Acknowledged alert '{alert_id}' by {by}[/green]")
        else:
            console.print(f"[red]* Failed to acknowledge alert '{alert_id}'[/red]")

    _output({"alert_id": alert_id, "acknowledged": success, "by": by}, _human)


@alert_app.command("config")
def alert_config(
    team: str = typer.Argument(..., help="Team name"),
    task_timeout: float = typer.Option(None, "--task-timeout", "-t", help="Task timeout threshold in hours"),
    failure_rate: float = typer.Option(None, "--failure-rate", "-f", help="Agent failure rate threshold (0.0-1.0)"),
    inactivity: float = typer.Option(None, "--inactivity", "-i", help="Team inactivity threshold in hours"),
    show: bool = typer.Option(False, "--show", "-s", help="Show current configuration"),
):
    """Configure alert thresholds for a team."""
    from clawteam.alerts import get_alert_config, save_alert_config

    if show:
        config = get_alert_config(team)

        def _human(_data):
            console.print(f"[bold]Alert Configuration — Team '{team}'[/bold]")
            console.print(f"  Task timeout: {config.task_timeout_hours} hours")
            console.print(f"  Agent failure rate: {config.agent_failure_rate_threshold:.1%}")
            console.print(f"  Team inactivity: {config.team_inactivity_hours} hours")
            console.print(f"  Enabled alert types: {', '.join(t.value for t in config.enabled_alert_types)}")

        _output(config.__dict__, _human)
        return

    # Update configuration
    config = get_alert_config(team)
    if task_timeout is not None:
        config.task_timeout_hours = task_timeout
    if failure_rate is not None:
        config.agent_failure_rate_threshold = failure_rate
    if inactivity is not None:
        config.team_inactivity_hours = inactivity

    save_alert_config(team, config)

    def _human(_data):
        console.print(f"[green]* Updated alert configuration for team '{team}'[/green]")

    _output({"team": team, "config": config.__dict__}, _human)


# ============================================================================
# Alert Commands
# ============================================================================

alert_app = typer.Typer(help="Alert management commands")
app.add_typer(alert_app, name="alert")


@alert_app.command("check")
def alert_check(
    team: str = typer.Argument(..., help="Team name"),
    timeout_threshold: int = typer.Option(60, "--timeout-threshold", "-t", help="Task timeout threshold in minutes"),
    failure_rate_threshold: float = typer.Option(
        0.3, "--failure-rate-threshold", "-f", help="Agent failure rate threshold (0.0-1.0)"
    ),
    min_tasks: int = typer.Option(5, "--min-tasks", "-m", help="Minimum tasks for failure rate calculation"),
):
    """Check for and create alerts based on current team state.

    Creates alerts for:
    - Tasks that have exceeded the timeout threshold
    - Agents with failure rates above the threshold
    """
    from clawteam.alerts import check_agent_failure_rates, check_task_timeouts

    # Check task timeouts
    timeout_alerts = check_task_timeouts(team, timeout_threshold)

    # Check agent failure rates
    failure_alerts = check_agent_failure_rates(team, failure_rate_threshold, min_tasks)

    total_alerts = len(timeout_alerts) + len(failure_alerts)

    def _human(_data):
        console.print(f"[bold]Alert Check — Team '{team}'[/bold]")
        console.print(f"  Task timeout alerts created: {len(timeout_alerts)}")
        console.print(f"  Agent failure rate alerts created: {len(failure_alerts)}")
        console.print(f"  Total alerts created: {total_alerts}")
        if total_alerts > 0:
            console.print("[yellow]* New alerts have been created. Use 'clawteam alert list' to view them.[/yellow]")
        else:
            console.print("[green]* No new alerts created.[/green]")

    _output(
        {
            "timeout_alerts": timeout_alerts,
            "failure_alerts": failure_alerts,
            "total_alerts": total_alerts,
        },
        _human,
    )


@alert_app.command("list")
def alert_list(
    team: str = typer.Argument(..., help="Team name"),
    acknowledged: bool = typer.Option(None, "--acknowledged/--unacknowledged", help="Filter by acknowledgment status"),
    limit: int = typer.Option(None, "--limit", "-l", help="Maximum number of alerts to show"),
):
    """List alerts for a team."""
    from clawteam.alerts import list_alerts

    alerts = list_alerts(team, acknowledged=acknowledged, limit=limit)

    def _human(_data):
        if not alerts:
            console.print(f"[green]* No alerts found for team '{team}'.[/green]")
            return

        console.print(f"[bold]Alerts — Team '{team}'[/bold]")
        console.print(f"  Total alerts: {len(alerts)}")
        console.print()

        for alert in alerts:
            severity_icon = {
                "low": "[yellow]![/yellow]",
                "medium": "[orange3]!![/orange3]",
                "high": "[red]!!![/red]",
                "critical": "[red bold]XXXX[/red bold]",
            }.get(alert.severity, "!")

            ack_status = "[dim](acknowledged)[/dim]" if alert.acknowledged else ""
            target_info = f" → {alert.target}" if alert.target else ""

            console.print(f"  {severity_icon} [{alert.alert_id[:8]}] {alert.event_type}{target_info} {ack_status}")
            console.print(f"    {alert.timestamp} | {alert.source}")
            if alert.details:
                details_str = ", ".join(f"{k}: {v}" for k, v in alert.details.items() if k not in ["task_subject"])
                if details_str:
                    console.print(f"    Details: {details_str}")

    _output(
        [
            {
                "alert_id": a.alert_id,
                "event_type": a.event_type,
                "severity": a.severity,
                "timestamp": a.timestamp,
                "source": a.source,
                "target": a.target,
                "details": a.details,
                "acknowledged": a.acknowledged,
                "acknowledged_by": a.acknowledged_by,
                "acknowledged_at": a.acknowledged_at,
            }
            for a in alerts
        ],
        _human,
    )


@alert_app.command("ack")
def alert_ack(
    team: str = typer.Argument(..., help="Team name"),
    alert_id: str = typer.Argument(..., help="Alert ID to acknowledge"),
):
    """Acknowledge an alert."""
    from clawteam.alerts import acknowledge_alert
    from clawteam.identity import AgentIdentity

    identity = AgentIdentity.from_env()
    ack_by = identity.agent_name or "unknown"

    success = acknowledge_alert(team, alert_id, ack_by)

    def _human(_data):
        if success:
            console.print(f"[green]* Acknowledged alert '{alert_id}' by {ack_by}[/green]")
        else:
            console.print(f"[red]Error: Alert '{alert_id}' not found or already acknowledged[/red]")

    _output({"alert_id": alert_id, "acknowledged": success, "by": ack_by}, _human)


# ============================================================================
# Audit commands
# ============================================================================

audit_app = typer.Typer(help="Audit logging commands")
app.add_typer(audit_app, name="audit")


@audit_app.command("query")
def audit_query(
    team: str = typer.Argument(..., help="Team name"),
    action: str = typer.Option(None, "--action", "-a", help="Filter by event type (e.g. task_created, agent_spawned)"),
    actor: str = typer.Option("", "--actor", "-o", help="Filter by actor name"),
    target: str = typer.Option("", "--target", "-t", help="Filter by target entity"),
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum number of entries to show"),
):
    """Query audit log entries for a team."""
    from clawteam.audit import read_audit_log

    events = read_audit_log(team, limit=limit)

    # Apply filters
    if action:
        events = [e for e in events if e.event_type.value == action]
    if actor:
        events = [e for e in events if e.actor == actor]
    if target:
        events = [e for e in events if e.target == target]

    def _human(_data):
        if not events:
            console.print("[dim]No audit entries found.[/dim]")
            return
        table = Table(title=f"Audit Log — {team}")
        table.add_column("Time", style="dim", no_wrap=True)
        table.add_column("Type", style="cyan")
        table.add_column("Actor", style="green")
        table.add_column("Target", style="yellow")
        table.add_column("Details")
        for e in events:
            table.add_row(
                e.timestamp[:19],
                e.event_type.value,
                e.actor,
                e.target or "—",
                json.dumps(e.details, ensure_ascii=False) if e.details else "",
            )
        console.print(table)

    _output(
        [
            {
                "event_id": e.event_id,
                "event_type": e.event_type.value,
                "timestamp": e.timestamp,
                "actor": e.actor,
                "target": e.target,
                "details": e.details,
            }
            for e in events
        ],
        _human,
    )


@audit_app.command("summary")
def audit_summary(
    team: str = typer.Argument(..., help="Team name"),
):
    """Show audit activity summary for a team."""
    from clawteam.audit import get_audit_summary

    summary = get_audit_summary(team)

    def _human(_data):
        if summary["total_events"] == 0:
            console.print(f"[dim]No audit entries for team '{team}'.[/dim]")
            return
        table = Table(title=f"Audit Summary — {team}")
        table.add_row("Total Events", str(summary["total_events"]))
        table.add_row("First Event", summary["first_event"][:19] if summary["first_event"] else "—")
        table.add_row("Last Event", summary["last_event"][:19] if summary["last_event"] else "—")
        table.add_row("Active Agents", ", ".join(summary["active_agents"]) or "—")
        types_str = ", ".join(
            f"{k.value if hasattr(k, 'value') else k}={v}"
            for k, v in sorted(summary["event_types"].items(), key=lambda x: -x[1])
        )
        table.add_row("Event Types", types_str)
        console.print(table)

    _output(summary, _human)


@audit_app.command("log")
def audit_log(
    team: str = typer.Argument(..., help="Team name"),
    event_type: str = typer.Option(..., "--type", "-T", help="Event type (e.g. task_created, agent_spawned)"),
    actor: str = typer.Option("system", "--actor", "-o", help="Actor name"),
    target: str = typer.Option("", "--target", "-t", help="Target entity"),
    details: str = typer.Option("", "--details", "-d", help="Details as JSON string"),
):
    """Manually log an audit event (for testing/debugging)."""
    from clawteam.audit import AuditEventType, log_audit_event

    try:
        et = AuditEventType(event_type)
    except ValueError:
        console.print(f"[red]Unknown event type: {event_type}[/red]")
        console.print(f"Valid types: {', '.join(e.value for e in AuditEventType)}")
        raise typer.Exit(1)

    parsed_details = {}
    if details:
        try:
            parsed_details = json.loads(details)
        except json.JSONDecodeError:
            parsed_details = {"raw": details}

    event_id = log_audit_event(team, et, actor, target or None, parsed_details or None)

    def _human(_data):
        console.print(f"[green]* Logged audit event {event_id}[/green]")

    _output({"event_id": event_id, "event_type": event_type, "team": team}, _human)


# ============================================================================
# DAG Commands
# ============================================================================

dag_app = typer.Typer(help="DAG dependency management for tasks")
app.add_typer(dag_app, name="dag")


@dag_app.command("sort")
def dag_sort(
    team: str = typer.Argument(..., help="Team name"),
):
    """Show tasks in topological (dependency-respecting) order."""
    from clawteam.team.dag import CycleDetectedError, topological_sort
    from clawteam.team.tasks import TaskStore

    store = TaskStore(team)
    tasks = store.list_tasks()

    if not tasks:
        _output({"team": team, "tasks": []}, lambda d: console.print("[dim]No tasks found.[/dim]"))
        return

    try:
        ordered = topological_sort(tasks)
    except CycleDetectedError as e:
        _output({"error": str(e)}, lambda d: console.print(f"[red]Cycle detected: {d['error']}[/red]"))
        raise typer.Exit(1)

    def _human(_data):
        table = Table(title=f"Topological Order — {team}")
        table.add_column("#", style="dim", justify="right")
        table.add_column("ID", style="cyan")
        table.add_column("Subject")
        table.add_column("Status")
        table.add_column("Depends On", style="dim")
        for i, t in enumerate(ordered, 1):
            status_style = {
                "pending": "white",
                "in_progress": "yellow",
                "completed": "green",
                "blocked": "red",
            }.get(t.status.value, "")
            status_text = f"[{status_style}]{t.status.value}[/{status_style}]" if status_style else t.status.value
            deps = ", ".join(t.depends_on) if t.depends_on else "—"
            table.add_row(str(i), t.id, t.subject[:40], status_text, deps)
        console.print(table)

    _output(
        {
            "team": team,
            "order": [
                {
                    "id": t.id,
                    "subject": t.subject,
                    "status": t.status.value,
                    "depends_on": t.depends_on,
                }
                for t in ordered
            ],
        },
        _human,
    )


@dag_app.command("check")
def dag_check(
    team: str = typer.Argument(..., help="Team name"),
):
    """Check for circular dependencies in tasks."""
    from clawteam.team.dag import detect_cycle
    from clawteam.team.tasks import TaskStore

    store = TaskStore(team)
    tasks = store.list_tasks()

    if not tasks:
        _output(
            {"team": team, "has_cycle": False},
            lambda d: console.print("[dim]No tasks to check.[/dim]"),
        )
        return

    has_cycle = detect_cycle(tasks)

    def _human(_data):
        if has_cycle:
            console.print("[red]⚠ Cycle detected in task dependencies![/red]")
            console.print("  Tasks involved in the cycle cannot be executed.")
        else:
            console.print("[green]✓ No cycles detected. Dependency graph is valid.[/green]")
        console.print(f"  Total tasks: {len(tasks)}")
        with_deps = [t for t in tasks if t.depends_on]
        if with_deps:
            console.print(f"  Tasks with dependencies: {len(with_deps)}")

    _output({"team": team, "has_cycle": has_cycle, "total_tasks": len(tasks)}, _human)
    if has_cycle:
        raise typer.Exit(1)


@dag_app.command("ready")
def dag_ready(
    team: str = typer.Argument(..., help="Team name"),
):
    """Show tasks that are ready to execute (all dependencies met)."""
    from clawteam.team.dag import get_ready_tasks
    from clawteam.team.tasks import TaskStore

    store = TaskStore(team)
    tasks = store.list_tasks()

    if not tasks:
        _output({"team": team, "ready_tasks": []}, lambda d: console.print("[dim]No tasks found.[/dim]"))
        return

    ready = get_ready_tasks(tasks)

    def _human(_data):
        if not ready:
            console.print("[dim]No tasks ready to execute.[/dim]")
            # Show what's blocking
            from clawteam.team.dag import get_blocking_tasks

            pending = [t for t in tasks if t.status.value == "pending"]
            if pending:
                console.print("\nPending tasks and their blockers:")
                for t in pending:
                    blockers = get_blocking_tasks(t, tasks)
                    if blockers:
                        blocker_names = ", ".join(f"{b.id} ({b.subject[:20]})" for b in blockers)
                        console.print(f"  [{t.id}] {t.subject[:30]} — blocked by: {blocker_names}")
                    else:
                        console.print(f"  [{t.id}] {t.subject[:30]} — no blockers (should be ready?)")
            return

        table = Table(title=f"Ready Tasks — {team}")
        table.add_column("ID", style="cyan")
        table.add_column("Subject")
        table.add_column("Owner")
        table.add_column("Priority")
        for t in ready:
            priority_style = {
                "urgent": "red bold",
                "high": "red",
                "medium": "yellow",
                "low": "dim",
            }.get(t.priority.value, "")
            priority_text = (
                f"[{priority_style}]{t.priority.value}[/{priority_style}]" if priority_style else t.priority.value
            )
            table.add_row(t.id, t.subject[:40], t.owner or "—", priority_text)
        console.print(table)

    _output(
        {
            "team": team,
            "ready_tasks": [
                {"id": t.id, "subject": t.subject, "owner": t.owner, "priority": t.priority.value} for t in ready
            ],
        },
        _human,
    )


# ============================================================================
# Role Commands
# ============================================================================

role_app = typer.Typer(help="Dynamic role assignment for agents")
app.add_typer(role_app, name="role")


@role_app.command("assign")
def role_assign(
    team: str = typer.Argument(..., help="Team name"),
    agent: str = typer.Argument(..., help="Agent name"),
    role: str = typer.Argument(..., help="Role: developer, reviewer, tester, architect, coordinator"),
    expires_at: str = typer.Option(None, "--expires-at", "-e", help="Expiration timestamp (ISO format)"),
):
    """Assign a role to an agent."""
    from clawteam.team.roles import AgentRole, assign_role

    try:
        role_enum = AgentRole(role)
    except ValueError:
        valid = ", ".join(r.value for r in AgentRole)
        console.print(f"[red]Invalid role '{role}'. Valid roles: {valid}[/red]")
        raise typer.Exit(1)

    assignment = assign_role(team, agent, role_enum, expires_at=expires_at)

    def _human(_data):
        console.print(
            f"[green]✓[/green] Assigned [cyan]{role_enum.value}[/cyan] to [bold]{agent}[/bold] in team '{team}'"
        )
        if expires_at:
            console.print(f"  Expires: {expires_at}")

    _output(
        {
            "team": team,
            "agent": agent,
            "role": role_enum.value,
            "assigned_at": assignment.assigned_at,
            "expires_at": assignment.expires_at,
        },
        _human,
    )


@role_app.command("unassign")
def role_unassign(
    team: str = typer.Argument(..., help="Team name"),
    agent: str = typer.Argument(..., help="Agent name"),
    role: str = typer.Argument(..., help="Role to remove"),
):
    """Remove a role from an agent."""
    from clawteam.team.roles import AgentRole, unassign_role

    try:
        role_enum = AgentRole(role)
    except ValueError:
        valid = ", ".join(r.value for r in AgentRole)
        console.print(f"[red]Invalid role '{role}'. Valid roles: {valid}[/red]")
        raise typer.Exit(1)

    removed = unassign_role(team, agent, role_enum)

    def _human(_data):
        if removed:
            console.print(f"[green]✓[/green] Removed [cyan]{role_enum.value}[/cyan] from [bold]{agent}[/bold]")
        else:
            console.print(f"[yellow]Agent '{agent}' did not have role '{role_enum.value}'.[/yellow]")

    _output({"team": team, "agent": agent, "role": role_enum.value, "removed": removed}, _human)


@role_app.command("list")
def role_list(
    team: str = typer.Argument(..., help="Team name"),
):
    """List all role assignments for a team."""
    from clawteam.team.roles import get_all_assignments

    assignments = get_all_assignments(team)

    def _human(_data):
        if not assignments:
            console.print(f"[dim]No role assignments for team '{team}'.[/dim]")
            return

        table = Table(title=f"Role Assignments — {team}")
        table.add_column("Agent", style="cyan")
        table.add_column("Role")
        table.add_column("Assigned At", style="dim")
        table.add_column("Expires", style="dim")
        for agent_name, assigns in sorted(assignments.items()):
            for a in assigns:
                expires = a.expires_at or "—"
                if len(expires) > 19:
                    expires = expires[:19]
                table.add_row(agent_name, a.role.value, (a.assigned_at or "")[:19], expires)
        console.print(table)

    data = {agent: [a.model_dump() for a in assigns] for agent, assigns in assignments.items()}
    _output({"team": team, "assignments": data}, _human)


@role_app.command("suggest")
def role_suggest(
    team: str = typer.Argument(..., help="Team name"),
    task_id: str = typer.Argument(..., help="Task ID to suggest role for"),
):
    """Suggest the best role for a task based on its content."""
    from clawteam.team.roles import suggest_role
    from clawteam.team.tasks import TaskStore

    store = TaskStore(team)
    task = store.get(task_id)
    if not task:
        _output(
            {"error": f"Task '{task_id}' not found"},
            lambda d: console.print(f"[red]{d['error']}[/red]"),
        )
        raise typer.Exit(1)

    # Try to use router for history-based suggestion
    router = None
    try:
        from clawteam.team.router import get_router

        router = get_router(team)
    except Exception:
        pass

    suggested = suggest_role(task, task.owner or "unknown", router)

    def _human(_data):
        console.print(f"[bold]Role Suggestion for task '{task_id}'[/bold]")
        console.print(f"  Subject: {task.subject}")
        console.print(f"  Suggested role: [green bold]{suggested.value}[/green bold]")
        if task.owner:
            console.print(f"  For agent: {task.owner}")

    _output(
        {
            "task_id": task_id,
            "subject": task.subject,
            "suggested_role": suggested.value,
            "owner": task.owner,
        },
        _human,
    )


# ============================================================================
# Session Commands (Cross-Session Awareness)
# ============================================================================

from clawteam.cli.session import session_app
from clawteam.cli.daemon_cmd import daemon_app

app.add_typer(session_app, name="session", help="Session awareness commands")
app.add_typer(daemon_app, name="daemon", help="Daemon management for persistent agents")


# ============================================================================
# Insights Commands
# ============================================================================

insights_app = typer.Typer(help="Usage insights and statistics")
app.add_typer(insights_app, name="insights")


@insights_app.command("show")
def insights_show(
    days: int = typer.Option(30, "--days", "-d", help="Number of days to analyze"),
    team_id: Optional[str] = typer.Option(None, "--team", "-t", help="Filter by team ID"),
):
    """Show overall usage statistics."""
    from clawteam.insights import InsightsEngine

    engine = InsightsEngine()
    report = engine.generate_report(days=days, team_id=team_id, format="json")
    engine.close()

    def _human(d):
        console.print(f"\n[bold cyan]Insights Report[/cyan] — Last {d['time_range_days']} days")
        console.print(f"Generated: {d['generated_at'][:19]}")
        console.print()

        # Token usage summary
        tu = d.get("token_usage", {})
        console.print("[bold]Token Usage[/bold]")
        console.print(f"  Total:        {tu.get('total_tokens', 0):,}")
        console.print(f"  Input:        {tu.get('total_input_tokens', 0):,}")
        console.print(f"  Output:       {tu.get('total_output_tokens', 0):,}")
        console.print(f"  Est. Cost:    ${tu.get('estimated_cost', 0):.4f}")
        console.print()

        # Tool usage
        tool_u = d.get("tool_usage", {})
        console.print(f"[bold]Tool Usage[/bold] — {tool_u.get('total_tool_calls', 0)} total calls")
        top_tools = tool_u.get("top_tools", {})
        if top_tools:
            for tool, count in list(top_tools.items())[:5]:
                console.print(f"  {tool}: {count}")
        console.print()

        # Skill usage
        skill_u = d.get("skill_usage", {})
        console.print(f"[bold]Skill Usage[/bold] — {skill_u.get('total_skill_invocations', 0)} total invocations")
        top_skills = skill_u.get("top_skills", {})
        if top_skills:
            for skill, count in list(top_skills.items())[:5]:
                console.print(f"  {skill}: {count}")
        console.print()

        # Activity patterns
        ap = d.get("activity_patterns", {})
        console.print("[bold]Activity Patterns[/bold]")
        console.print(f"  Active days:  {ap.get('active_days', 0)}")
        console.print(f"  Total sessions: {ap.get('total_sessions', 0)}")
        summary = d.get("summary_metrics", {})
        console.print(f"  Most active hour: {summary.get('most_active_hour', 'N/A')}")
        console.print(f"  Most used tool:  {summary.get('most_used_tool', 'N/A')}")
        console.print(f"  Most used skill: {summary.get('most_used_skill', 'N/A')}")

    _output(report, _human)


@insights_app.command("tools")
def insights_tools(
    days: int = typer.Option(30, "--days", "-d", help="Number of days to analyze"),
    team_id: Optional[str] = typer.Option(None, "--team", "-t", help="Filter by team ID"),
):
    """Show tool usage ranking."""
    from clawteam.insights import InsightsEngine

    engine = InsightsEngine()
    stats = engine.get_tool_usage_stats(days=days, team_id=team_id)
    engine.close()

    def _human(d):
        console.print(f"\n[bold cyan]Tool Usage[/cyan] — Last {days} days")
        console.print(f"Total calls: {d.total_tool_calls}\n")

        table = Table(title="Tool Ranking")
        table.add_column("Rank", style="dim", justify="right")
        table.add_column("Tool", style="cyan")
        table.add_column("Calls", justify="right")

        sorted_tools = sorted(d.by_tool.items(), key=lambda x: x[1], reverse=True)
        for i, (tool, count) in enumerate(sorted_tools, 1):
            table.add_row(str(i), tool, str(count))

        console.print(table)

        if d.by_hour:
            console.print("\n[bold]Hourly Distribution[/bold]")
            for hour in sorted(d.by_hour.keys()):
                bar = "█" * min(d.by_hour[hour], 20)
                console.print(f"  {hour:02d}:00  {bar}  {d.by_hour[hour]}")

    _output(stats, _human)


@insights_app.command("skills")
def insights_skills(
    days: int = typer.Option(30, "--days", "-d", help="Number of days to analyze"),
    team_id: Optional[str] = typer.Option(None, "--team", "-t", help="Filter by team ID"),
):
    """Show skill usage ranking."""
    from clawteam.insights import InsightsEngine

    engine = InsightsEngine()
    stats = engine.get_skill_usage_stats(days=days, team_id=team_id)
    engine.close()

    def _human(d):
        console.print(f"\n[bold cyan]Skill Usage[/cyan] — Last {days} days")
        console.print(f"Total invocations: {d.total_skill_invocations}\n")

        table = Table(title="Skill Ranking")
        table.add_column("Rank", style="dim", justify="right")
        table.add_column("Skill", style="cyan")
        table.add_column("Invocations", justify="right")

        sorted_skills = sorted(d.by_skill.items(), key=lambda x: x[1], reverse=True)
        for i, (skill, count) in enumerate(sorted_skills, 1):
            table.add_row(str(i), skill, str(count))

        console.print(table)

    _output(stats, _human)


@insights_app.command("memory")
def insights_memory(
    days: int = typer.Option(30, "--days", "-d", help="Number of days to analyze"),
    team_id: Optional[str] = typer.Option(None, "--team", "-t", help="Filter by team ID"),
):
    """Show memory usage statistics."""
    from clawteam.insights import InsightsEngine

    engine = InsightsEngine()

    # Memory stats are tracked via session activity
    activity_stats = engine.get_activity_stats(days=days, team_id=team_id)
    engine.close()

    def _human(d):
        console.print(f"\n[bold cyan]Memory Usage[/cyan] — Last {days} days")
        console.print(f"Active days: {d.active_days}")
        console.print(f"Total sessions: {d.total_sessions}")
        console.print(f"Avg session duration: {d.avg_session_duration_minutes:.1f} min")

        if d.by_weekday:
            console.print("\n[bold]Weekly Distribution[/bold]")
            weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            for day, count in sorted(d.by_weekday.items()):
                bar = "█" * min(count, 20)
                name = weekday_names[int(day)] if int(day) < 7 else day
                console.print(f"  {name}:  {bar}  {count}")

    _output(activity_stats, _human)


# ============================================================================
# Agent Commands (Lifecycle Management)
# ============================================================================

agent_app = typer.Typer(help="Agent lifecycle management commands")
app.add_typer(agent_app, name="agent")


@agent_app.command("list")
def agent_list(
    team: Optional[str] = typer.Option(None, "--team", "-t", help="Team name (default: all teams)"),
    show_dead: bool = typer.Option(False, "--all", "-a", help="Include dead/stopped agents"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List all agents with their status and runtime."""
    from clawteam.spawn.registry import get_registry, is_agent_alive
    import datetime

    if team:
        teams = [team]
    else:
        # Get all teams from data dir
        data_dir = Path(os.environ.get("CLAWTEAM_DATA_DIR", "~/.clawteam")).expanduser()
        teams = [d.name for d in data_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]

    all_agents = []
    for t in teams:
        registry = get_registry(t)
        for name, info in registry.items():
            is_alive = is_agent_alive(t, name)
            if not show_dead and not is_alive:
                continue

            # Calculate runtime
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

    if json_output or _json_output:
        _output({"agents": all_agents, "total": len(all_agents)})
    else:
        if not all_agents:
            console.print("[yellow]No agents found.[/yellow]")
            return

        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        from rich import box

        # Create main table
        table = Table(title=f"[bold]Agent List ({len(all_agents)} agents)[/bold]", box=box.ROUNDED, show_lines=True)
        table.add_column("Team", style="cyan", no_wrap=True)
        table.add_column("Agent", style="bold", no_wrap=True)
        table.add_column("Type", style="dim")
        table.add_column("Status", justify="center")
        table.add_column("Runtime", justify="right", style="green")

        # Add rows grouped by team
        by_team = {}
        for a in all_agents:
            by_team.setdefault(a["team"], []).append(a)

        for team_name, agents in by_team.items():
            # Add team header as first row
            for i, a in enumerate(agents):
                status_style = "[bold green]" if a["status"] == "running" else "[bold red]"
                table.add_row(
                    team_name if i == 0 else "",  # Only show team on first row
                    a["name"],
                    a["type"],
                    f"{status_style}{a['status']}[/]",
                    a["runtime"],
                )

        console.print(table)


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


@agent_app.command("info")
def agent_info(
    name: str = typer.Argument(..., help="Agent name"),
    team: Optional[str] = typer.Option(None, "--team", "-t", help="Team name"),
):
    """Show detailed information about an agent."""
    from clawteam.spawn.registry import get_agent_info, is_agent_alive, get_agent_health
    from rich.console import Console as RichConsole
    from rich.table import Table
    from rich.panel import Panel
    import datetime

    if not team:
        # Search all teams
        data_dir = Path(os.environ.get("CLAWTEAM_DATA_DIR", "~/.clawteam")).expanduser()
        for t_dir in data_dir.iterdir():
            if t_dir.is_dir() and not t_dir.name.startswith("."):
                info = get_agent_info(t_dir.name, name)
                if info:
                    team = t_dir.name
                    break

    if not team:
        console.print(f"[red]Agent '{name}' not found.[/red]")
        raise typer.Exit(1)

    info = get_agent_info(team, name)
    if not info:
        console.print(f"[red]Agent '{name}' not found in team '{team}'.[/red]")
        raise typer.Exit(1)

    is_alive = is_agent_alive(team, name)
    health = get_agent_health(team, name)

    # Create status panel
    status_color = "green" if is_alive else "red"
    status_text = f"[bold {status_color}]{'● RUNNING' if is_alive else '○ STOPPED'}[/]"

    # Create info table
    info_table = Table(show_header=False, box=None, pad_edge=False)
    info_table.add_column("key", style="bold cyan")
    info_table.add_column("value")

    info_table.add_row("Team", f"[cyan]{team}[/cyan]")
    info_table.add_row("Status", status_text)
    info_table.add_row("Type", info.get('agent_type', 'unknown'))
    info_table.add_row("Backend", info.get('backend', 'unknown'))

    if info.get("started_at"):
        start_dt = datetime.datetime.fromtimestamp(info["started_at"])
        runtime = datetime.datetime.now() - start_dt
        info_table.add_row("Started", start_dt.strftime('%Y-%m-%d %H:%M:%S'))
        info_table.add_row("Runtime", _format_duration(runtime))

    if info.get("session_key"):
        info_table.add_row("Session", f"[dim]{info['session_key']}[/dim]")

    # Create health table
    health_table = Table(show_header=False, box=None, pad_edge=False)
    health_table.add_column("key", style="bold magenta")
    health_table.add_column("value")
    if health:
        health_table.add_row("Last Heartbeat", health.last_heartbeat or "never")
        health_table.add_row("Heartbeat Count", str(health.heartbeat_count))
        health_table.add_row("Restart Count", str(health.restart_count))
        if health.last_error:
            health_table.add_row("[red]Last Error[/red]", health.last_error)
    else:
        health_table.add_row("Health", "No health data")


    # Print with panels
    console.print(Panel(info_table, title=f"[bold]Agent: {name}[/bold]", border_style="cyan"))
    if health:
        console.print(Panel(health_table, title="[bold]Health[/bold]", border_style="magenta"))


@agent_app.command("health")
def agent_health(
    name: str = typer.Argument(..., help="Agent name"),
    team: Optional[str] = typer.Option(None, "--team", "-t", help="Team name"),
    watch: bool = typer.Option(False, "--watch", "-w", help="Watch mode (refresh every 5 seconds)"),
):
    """Check agent health status."""
    from clawteam.spawn.registry import get_agent_info, is_agent_alive, get_agent_health
    import datetime

    def check_health(t: str, n: str) -> bool:
        """Check and display health. Returns True if agent is healthy."""
        info = get_agent_info(t, n)
        if not info:
            console.print(f"[red]Agent '{n}' not found.[/red]")
            return False

        alive = is_agent_alive(t, n)
        health = get_agent_health(t, n)

        if not alive:
            console.print(f"[red]✗ Agent '{n}' is not running[/red]")
            return False

        console.print(f"[green]✓ Agent '{n}' is running[/green]")

        if health:
            if health.last_heartbeat:
                try:
                    hb_dt = datetime.datetime.fromisoformat(health.last_heartbeat.replace("Z", "+00:00"))
                    hb_age = (datetime.datetime.now() - hb_dt.replace(tzinfo=None)).total_seconds()
                    if hb_age < 60:
                        console.print(f"  Last heartbeat: {hb_age:.0f}s ago")
                    elif hb_age < 3600:
                        console.print(f"  Last heartbeat: {hb_age / 60:.1f}m ago")
                    else:
                        console.print(f"  Last heartbeat: {hb_age / 3600:.1f}h ago [yellow]⚠ stale[/yellow]")
                except:
                    console.print(f"  Last heartbeat: {health.last_heartbeat}")

            console.print(f"  Heartbeats: {health.heartbeat_count}")
            console.print(f"  Restarts: {health.restart_count}")

            if health.last_error:
                console.print(f"  [yellow]Last error: {health.last_error}[/yellow]")

        return True

    # Find team if not provided
    actual_team = team
    if not actual_team:
        data_dir = Path(os.environ.get("CLAWTEAM_DATA_DIR", "~/.clawteam")).expanduser()
        for t_dir in data_dir.iterdir():
            if t_dir.is_dir() and not t_dir.name.startswith("."):
                info = get_agent_info(t_dir.name, name)
                if info:
                    actual_team = t_dir.name
                    break

    if not actual_team:
        console.print(f"[red]Agent '{name}' not found.[/red]")
        raise typer.Exit(1)

    if watch:
        import time

        console.print("[dim]Watching agent health (Ctrl+C to stop)...[/dim]\n")
        while True:
            try:
                console.print(f"\n[dim]{datetime.datetime.now().strftime('%H:%M:%S')}[/dim]")
                check_health(actual_team, name)
                time.sleep(5)
            except KeyboardInterrupt:
                console.print("\n[dim]Stopped.[/dim]")
                break
    else:
        check_health(actual_team, name)


@agent_app.command("restart")
def agent_restart(
    name: str = typer.Argument(..., help="Agent name"),
    team: Optional[str] = typer.Option(None, "--team", "-t", help="Team name"),
    force: bool = typer.Option(False, "--force", "-f", help="Force kill if not responding"),
):
    """Restart an agent (terminate and respawn)."""
    from clawteam.spawn.registry import get_agent_info, is_agent_alive, unregister_agent
    from clawteam.spawn import get_backend
    import subprocess
    import json

    # Find team if not provided
    actual_team = team
    if not actual_team:
        data_dir = Path(os.environ.get("CLAWTEAM_DATA_DIR", "~/.clawteam")).expanduser()
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

    console.print(f"[yellow]Restarting agent '{name}'...[/yellow]")

    # Get backend
    backend_name = info.get("backend", "auto")
    try:
        backend = get_backend(backend_name)
    except ValueError:
        backend = get_backend("auto")

    # If agent is alive, try graceful shutdown first
    if is_agent_alive(actual_team, name) and not force:
        # Try sending shutdown message via gateway
        console.print(f"[dim]Sending shutdown signal...[/dim]")
        session_key = info.get("session_key", "")
        if session_key:
            try:
                _gateway_call("sessions.send", {"key": session_key, "message": "shutdown"}, timeout=10)
                import time

                time.sleep(2)
            except:
                pass

    # Terminate the agent using backend
    console.print(f"[dim]Terminating agent...[/dim]")
    try:
        backend.terminate(name)  # Note: only takes agent_name, not team_name
    except Exception as e:
        console.print(f"[yellow]Warning during termination: {e}[/yellow]")

    # Unregister
    try:
        unregister_agent(actual_team, name)
    except:
        pass

    # Respawn
    console.print(f"[dim]Respawning agent...[/dim]")
    try:
        new_info = backend.spawn(
            team_name=actual_team,
            agent_name=name,
            agent_type=info.get("agent_type", "general-purpose"),
            task=info.get("last_task", ""),
            parent_agent=info.get("parent_agent", ""),
        )
        console.print(f"[green]✓ Agent '{name}' restarted successfully[/green]")
        console.print(f"[dim]New session: {new_info.get('session_key', 'unknown')}[/dim]")
    except Exception as e:
        console.print(f"[red]✗ Failed to restart agent: {e}[/red]")
        raise typer.Exit(1)


@agent_app.command("pause")
def agent_pause(
    name: str = typer.Argument(..., help="Agent name"),
    team: Optional[str] = typer.Option(None, "--team", "-t", help="Team name"),
    reason: Optional[str] = typer.Option(None, "--reason", "-r", help="Reason for pausing"),
):
    """Pause an agent (asks it to stop processing and wait)."""
    from clawteam.spawn.registry import get_agent_info, is_agent_alive

    # Find team if not provided
    actual_team = team
    if not actual_team:
        data_dir = Path(os.environ.get("CLAWTEAM_DATA_DIR", "~/.clawteam")).expanduser()
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

    if not is_agent_alive(actual_team, name):
        console.print(f"[red]Agent '{name}' is not running.[/red]")
        raise typer.Exit(1)

    pause_msg = f"pause" + (f": {reason}" if reason else ": user requested")
    session_key = info.get("session_key", "")

    if not session_key:
        console.print(f"[red]No session key found for agent '{name}'.[/red]")
        raise typer.Exit(1)

    try:
        _gateway_call("sessions.send", {"key": session_key, "message": pause_msg}, timeout=10)
        console.print(f"[green]✓ Pause signal sent to '{name}'[/green]")
    except Exception as e:
        console.print(f"[red]✗ Failed to send pause signal: {e}[/red]")
        raise typer.Exit(1)


@agent_app.command("resume")
def agent_resume(
    name: str = typer.Argument(..., help="Agent name"),
    team: Optional[str] = typer.Option(None, "--team", "-t", help="Team name"),
):
    """Resume a paused agent."""
    from clawteam.spawn.registry import get_agent_info, is_agent_alive

    # Find team if not provided
    actual_team = team
    if not actual_team:
        data_dir = Path(os.environ.get("CLAWTEAM_DATA_DIR", "~/.clawteam")).expanduser()
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

    if not is_agent_alive(actual_team, name):
        console.print(f"[red]Agent '{name}' is not running.[/red]")
        raise typer.Exit(1)

    session_key = info.get("session_key", "")
    if not session_key:
        console.print(f"[red]No session key found for agent '{name}'.[/red]")
        raise typer.Exit(1)

    try:
        _gateway_call("sessions.send", {"key": session_key, "message": "resume"}, timeout=10)
        console.print(f"[green]✓ Resume signal sent to '{name}'[/green]")
    except Exception as e:
        console.print(f"[red]✗ Failed to send resume signal: {e}[/red]")
        raise typer.Exit(1)


@agent_app.command("kill")
def agent_kill(
    name: str = typer.Argument(..., help="Agent name"),
    team: Optional[str] = typer.Option(None, "--team", "-t", help="Team name"),
    force: bool = typer.Option(False, "--force", "-f", help="Force kill without graceful shutdown"),
):
    """Kill an agent immediately (ungraceful termination)."""
    from clawteam.spawn.registry import unregister_agent, get_agent_info, is_agent_alive
    from clawteam.spawn import get_backend

    # Find team if not provided
    actual_team = team
    if not actual_team:
        data_dir = Path(os.environ.get("CLAWTEAM_DATA_DIR", "~/.clawteam")).expanduser()
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

    # Get backend and terminate
    backend_name = info.get("backend", "auto")
    try:
        backend = get_backend(backend_name)
    except ValueError:
        backend = get_backend("auto")

    try:
        backend.terminate(name)  # Note: only takes agent_name
    except Exception as e:
        console.print(f"[yellow]Warning during termination: {e}[/yellow]")

    try:
        unregister_agent(actual_team, name)
    except:
        pass

    console.print(f"[green]✓ Agent '{name}' killed[/green]")


if __name__ == "__main__":
    app()
    app()
