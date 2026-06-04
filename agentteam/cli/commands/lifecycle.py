"""
Lifecycle Management Commands

Provides agent lifecycle operations: request_shutdown, approve_shutdown, reject_shutdown, idle, on_exit, check_zombies, terminate_children, terminate_tree, list_children, show_parent, register_child.
"""

from __future__ import annotations

import json
from typing import Optional

import typer
from rich.console import Console

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


# ============================================================================
# Lifecycle Commands
# ============================================================================


@app.command("request-shutdown")
def lifecycle_request_shutdown(
    team: str = typer.Argument(..., help="Team name"),
    reason: str = typer.Option("", "--reason", "-r", help="Shutdown reason"),
):
    """Request graceful shutdown of the current agent."""
    from agentteam.team.lifecycle import LifecycleManager

    lifecycle = LifecycleManager(team)
    lifecycle.request_shutdown(reason=reason)
    _output({"status": "shutdown_requested"}, lambda d: console.print("[yellow]Shutdown requested[/yellow]"))


@app.command("approve-shutdown")
def lifecycle_approve_shutdown(
    team: str = typer.Argument(..., help="Team name"),
    agent: str = typer.Argument(..., help="Agent name to approve shutdown for"),
):
    """Approve a shutdown request from an agent."""
    from agentteam.team.lifecycle import LifecycleManager

    lifecycle = LifecycleManager(team)
    lifecycle.approve_shutdown(agent)
    _output({"status": "shutdown_approved", "agent": agent}, lambda d: console.print(f"[green]Shutdown approved for {agent}[/green]"))


@app.command("reject-shutdown")
def lifecycle_reject_shutdown(
    team: str = typer.Argument(..., help="Team name"),
    agent: str = typer.Argument(..., help="Agent name"),
    reason: str = typer.Option("", "--reason", "-r", help="Rejection reason"),
):
    """Reject a shutdown request."""
    from agentteam.team.lifecycle import LifecycleManager

    lifecycle = LifecycleManager(team)
    lifecycle.reject_shutdown(agent, reason=reason)
    _output({"status": "shutdown_rejected", "agent": agent}, lambda d: console.print(f"[yellow]Shutdown rejected for {agent}[/yellow]"))


@app.command("idle")
def lifecycle_idle(
    team: str = typer.Argument(..., help="Team name"),
):
    """Mark current agent as idle (ready for new tasks)."""
    from agentteam.identity import AgentIdentity
    from agentteam.team.lifecycle import LifecycleManager

    identity = AgentIdentity.from_env()
    lifecycle = LifecycleManager(team)
    lifecycle.mark_idle(identity.agent_name)
    _output({"status": "idle", "agent": identity.agent_name}, lambda d: console.print(f"[green]Agent {identity.agent_name} marked idle[/green]"))


@app.command("on-exit")
def lifecycle_on_exit(
    team: str = typer.Argument(..., help="Team name"),
    cleanup: bool = typer.Option(True, "--cleanup/--no-cleanup", help="Cleanup workspace on exit"),
):
    """Handle cleanup when agent exits."""
    from agentteam.identity import AgentIdentity
    from agentteam.team.lifecycle import LifecycleManager

    identity = AgentIdentity.from_env()
    lifecycle = LifecycleManager(team)
    lifecycle.on_exit(identity.agent_name, cleanup=cleanup)
    _output({"status": "exited", "agent": identity.agent_name}, lambda d: console.print(f"[dim]Agent {identity.agent_name} exited[/dim]"))


@app.command("check-zombies")
def lifecycle_check_zombies(
    team: str = typer.Argument(..., help="Team name"),
):
    """Check for zombie processes belonging to dead agents."""
    from agentteam.team.lifecycle import LifecycleManager

    lifecycle = LifecycleManager(team)
    zombies = lifecycle.check_zombies()

    if zombies:
        def _human(z):
            console.print("[yellow]Zombie processes found:[/yellow]")
            for z_name, z_pid in z:
                console.print(f"  - {z_name} (PID: {z_pid})")
        _output({"zombies": zombies, "count": len(zombies)}, _human)
    else:
        _output({"zombies": [], "count": 0}, lambda d: console.print("[green]No zombie processes found[/green]"))


@app.command("terminate-children")
def lifecycle_terminate_children(
    team: str = typer.Argument(..., help="Team name"),
    agent: str = typer.Argument(..., help="Parent agent name"),
):
    """Terminate all child agents of an agent."""
    from agentteam.team.lifecycle import LifecycleManager

    lifecycle = LifecycleManager(team)
    terminated = lifecycle.terminate_children(agent)

    _output({"status": "terminated", "parent": agent, "count": len(terminated)}, 
            lambda d: console.print(f"[green]Terminated {d['count']} child agents of {d['parent']}[/green]"))


@app.command("terminate-tree")
def lifecycle_terminate_tree(
    team: str = typer.Argument(..., help="Team name"),
    agent: str = typer.Argument(..., help="Root agent name"),
    force: bool = typer.Option(False, "--force", "-f", help="Force kill"),
):
    """Terminate an agent and all its descendants."""
    from agentteam.team.lifecycle import LifecycleManager

    lifecycle = LifecycleManager(team)
    terminated = lifecycle.terminate_tree(agent, force=force)

    _output({"status": "terminated", "root": agent, "count": len(terminated)},
            lambda d: console.print(f"[green]Terminated {d['count']} agents in tree rooted at {d['root']}[/green]"))


@app.command("list-children")
def lifecycle_list_children(
    team: str = typer.Argument(..., help="Team name"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Parent agent name"),
):
    """List child agents of an agent."""
    from agentteam.identity import AgentIdentity
    from agentteam.team.lifecycle import LifecycleManager

    parent = agent or AgentIdentity.from_env().agent_name
    lifecycle = LifecycleManager(team)
    children = lifecycle.list_children(parent)

    def _human(c):
        if not c:
            console.print(f"[dim]No children for {parent}[/dim]")
        else:
            console.print(f"[cyan]Children of {parent}:[/cyan]")
            for child in c:
                console.print(f"  - {child}")

    _output({"parent": parent, "children": children}, _human)


@app.command("show-parent")
def lifecycle_show_parent(
    team: str = typer.Argument(..., help="Team name"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent name"),
):
    """Show the parent of an agent."""
    from agentteam.identity import AgentIdentity
    from agentteam.team.lifecycle import LifecycleManager

    name = agent or AgentIdentity.from_env().agent_name
    lifecycle = LifecycleManager(team)
    parent = lifecycle.get_parent(name)

    if parent:
        _output({"agent": name, "parent": parent}, lambda d: console.print(f"Parent of {d['agent']}: {d['parent']}"))
    else:
        _output({"agent": name, "parent": None}, lambda d: console.print(f"[dim]{d['agent']} has no parent[/dim]"))


@app.command("register-child")
def lifecycle_register_child(
    team: str = typer.Argument(..., help="Team name"),
    child: str = typer.Argument(..., help="Child agent name"),
    parent: Optional[str] = typer.Option(None, "--parent", "-p", help="Parent agent name"),
):
    """Register a child-parent relationship."""
    from agentteam.identity import AgentIdentity
    from agentteam.team.lifecycle import LifecycleManager

    actual_parent = parent or AgentIdentity.from_env().agent_name
    lifecycle = LifecycleManager(team)
    lifecycle.register_child(actual_parent, child)

    _output({"status": "registered", "parent": actual_parent, "child": child},
            lambda d: console.print(f"[green]Registered {d['child']} as child of {d['parent']}[/green]"))


if __name__ == "__main__":
    app()
