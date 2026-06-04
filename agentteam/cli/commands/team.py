"""
Team Management Commands

Provides team lifecycle operations: create, discover, join, status, cleanup.
"""

from __future__ import annotations

import shutil
import time
import uuid
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from agentteam import __version__

app = typer.Typer(help="Team management commands")
console = Console()

# Import helpers from parent (set by parent module)
_json_output = False


def _init_json_output(json_flag: bool):
    """Initialize JSON output flag from parent module."""
    global _json_output
    _json_output = json_flag


def _output(data: dict | list, human_fn=None):
    """Output data as JSON or human-readable."""
    if _json_output:
        print(__import__("json").dumps(data, indent=2, ensure_ascii=False))
    elif human_fn:
        human_fn(data)
    else:
        print(__import__("json").dumps(data, indent=2, ensure_ascii=False))


# ============================================================================
# Team Commands
# ============================================================================


@app.command("spawn-team")
def team_spawn_team(
    name: str = typer.Argument(..., help="Team name"),
    description: str = typer.Option("", "--description", "-d", help="Team description"),
    agent_name: str = typer.Option("leader", "--agent-name", "-n", help="Leader agent name"),
    agent_type: str = typer.Option("leader", "--agent-type", help="Leader agent type"),
):
    """Create a new team and register the leader (spawnTeam)."""
    from agentteam.identity import AgentIdentity
    from agentteam.team.manager import TeamManager

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
            print(__import__("json").dumps({"error": str(e)}))
        else:
            console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command("create")
def team_create(
    name: str = typer.Argument(..., help="Team name"),
    template: str = typer.Option("", "--template", "-t", help="Template name to use"),
    description: str = typer.Option("", "--description", "-d", help="Team description"),
):
    """Create a new team, optionally from a template (createTeam)."""
    from agentteam.identity import AgentIdentity
    from agentteam.team.manager import TeamManager
    from agentteam.templates import load_template

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
        backend = "auto"
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
            print(__import__("json").dumps({"error": str(e)}))
        else:
            console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command("discover")
def team_discover():
    """List all teams (discoverTeams)."""
    from agentteam.team.manager import TeamManager

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


@app.command("request-join")
def team_request_join(
    team: str = typer.Argument(..., help="Team name"),
    proposed_name: str = typer.Argument(..., help="Proposed agent name"),
    capabilities: str = typer.Option("", "--capabilities", "-c", help="Agent capabilities"),
    timeout: int = typer.Option(60, "--timeout", "-t", help="Timeout in seconds"),
):
    """Request to join a team (requestJoin). Blocks waiting for leader response."""
    from agentteam.identity import AgentIdentity
    from agentteam.team.mailbox import MailboxManager
    from agentteam.team.manager import TeamManager
    from agentteam.team.models import MessageType

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


@app.command("approve-join")
def team_approve_join(
    team: str = typer.Argument(..., help="Team name"),
    request_id: str = typer.Argument(..., help="Join request ID"),
    assigned_name: str | None = typer.Option(None, "--assigned-name", help="Override proposed name"),
):
    """Approve a join request (approveJoin)."""
    from agentteam.identity import AgentIdentity
    from agentteam.team.mailbox import MailboxManager
    from agentteam.team.manager import TeamManager
    from agentteam.team.models import MessageType, get_data_dir

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

    # Cleanup pending inbox
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


@app.command("reject-join")
def team_reject_join(
    team: str = typer.Argument(..., help="Team name"),
    request_id: str = typer.Argument(..., help="Join request ID"),
    reason: str = typer.Option("", "--reason", "-r", help="Rejection reason"),
):
    """Reject a join request (rejectJoin)."""
    from agentteam.identity import AgentIdentity
    from agentteam.team.mailbox import MailboxManager
    from agentteam.team.manager import TeamManager
    from agentteam.team.models import MessageType, get_data_dir

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

    # Clean up pending inbox
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


@app.command("cleanup")
def team_cleanup(
    team: str = typer.Argument(..., help="Team name"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete a team and all its data (cleanup)."""
    from agentteam.team.manager import TeamManager

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
    """Get workspace working directory from workspace info."""
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


@app.command("status")
def team_status(
    team: str = typer.Argument(..., help="Team name"),
):
    """Show team status and members."""
    from agentteam.spawn.registry import is_agent_alive
    from agentteam.team.manager import TeamManager

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
            row.extend([
                m.get("agentId", "")[:8],
                m.get("agentType", ""),
                "[green]✓[/green]" if alive else "[red]✗[/red]",
                m.get("joinedAt", "")[:19] if m.get("joinedAt") else "",
            ])
            table.add_row(*row)
        console.print(table)

    _output(data, _human)


if __name__ == "__main__":
    app()
