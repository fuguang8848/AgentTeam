"""
Workspace Management Commands

Provides git worktree-based workspace operations: list, checkpoint, merge, cleanup, status.
"""

from __future__ import annotations

import json
from typing import Optional

import typer
from rich.console import Console

from agentteam import __version__

app = typer.Typer(help="Workspace (git worktree) management commands")
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
# Workspace Commands
# ============================================================================


@app.command("list")
def workspace_list(
    repo: Optional[str] = typer.Option(None, "--repo", "-r", help="Git repo path"),
):
    """List all worktrees in a git repository."""
    from agentteam.workspace import get_workspace_manager

    ws_mgr = get_workspace_manager(repo)
    if ws_mgr is None:
        console.print("[red]Not in a git repo.[/red]")
        raise typer.Exit(1)

    worktrees = ws_mgr.list_worktrees()

    def _human(trees):
        if not trees:
            console.print("[dim]No worktrees found[/dim]")
        else:
            from rich.table import Table
            table = Table(title="Worktrees")
            table.add_column("Branch", style="cyan")
            table.add_column("Path", style="dim")
            table.add_column("Head", style="dim")
            for wt in trees:
                table.add_row(wt.get("branch", ""), wt.get("path", ""), wt.get("head", ""))
            console.print(table)

    _output(worktrees, _human)


@app.command("checkpoint")
def workspace_checkpoint(
    team: str = typer.Argument(..., help="Team name"),
    agent: str = typer.Argument(..., help="Agent name"),
    repo: Optional[str] = typer.Option(None, "--repo", "-r", help="Git repo path"),
    message: Optional[str] = typer.Option(None, "--message", "-m", help="Commit message"),
):
    """Create a checkpoint (auto-commit) for an agent's workspace."""
    from agentteam.workspace import get_workspace_manager

    ws_mgr = get_workspace_manager(repo)
    if ws_mgr is None:
        console.print("[red]Not in a git repo.[/red]")
        raise typer.Exit(1)

    committed = ws_mgr.checkpoint(team, agent, message)
    if committed:
        _output({"status": "checkpoint_created", "team": team, "agent": agent},
                lambda d: console.print(f"[green]OK[/green] Checkpoint created for '{agent}'."))
    else:
        _output({"status": "no_changes", "team": team, "agent": agent},
                lambda d: console.print(f"[dim]No changes to checkpoint for '{agent}'.[/dim]"))


@app.command("merge")
def workspace_merge(
    team: str = typer.Argument(..., help="Team name"),
    agent: str = typer.Argument(..., help="Agent name"),
    repo: Optional[str] = typer.Option(None, "--repo", "-r", help="Git repo path"),
    target: Optional[str] = typer.Option(None, "--target", "-t", help="Target branch"),
    no_cleanup: bool = typer.Option(False, "--no-cleanup", help="Keep worktree after merge"),
):
    """Merge an agent's workspace branch back to the base branch."""
    from agentteam.workspace import get_workspace_manager

    ws_mgr = get_workspace_manager(repo)
    if ws_mgr is None:
        console.print("[red]Not in a git repo.[/red]")
        raise typer.Exit(1)

    success, output = ws_mgr.merge_workspace(team, agent, target, cleanup_after=not no_cleanup)

    if success:
        _output({"status": "merged", "team": team, "agent": agent, "output": output},
                lambda d: console.print(f"[green]OK[/green] Workspace merged for '{agent}'"))
    else:
        _output({"status": "merge_failed", "team": team, "agent": agent, "error": output},
                lambda d: console.print(f"[red]Merge failed: {output}[/red]"))


@app.command("cleanup")
def workspace_cleanup(
    team: str = typer.Argument(..., help="Team name"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent name"),
    repo: Optional[str] = typer.Option(None, "--repo", "-r", help="Git repo path"),
    force: bool = typer.Option(False, "--force", "-f", help="Force cleanup even if uncommitted changes"),
):
    """Remove worktrees for agents that are no longer running."""
    from agentteam.workspace import get_workspace_manager

    ws_mgr = get_workspace_manager(repo)
    if ws_mgr is None:
        console.print("[red]Not in a git repo.[/red]")
        raise typer.Exit(1)

    removed = ws_mgr.cleanup_worktrees(team, agent, force=force)

    _output({"status": "cleaned", "team": team, "removed": removed},
            lambda d: console.print(f"[green]Removed {d['removed']} worktree(s)[/green]"))


@app.command("status")
def workspace_status(
    team: str = typer.Argument(..., help="Team name"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent name"),
    repo: Optional[str] = typer.Option(None, "--repo", "-r", help="Git repo path"),
):
    """Show git status for agent workspaces."""
    from agentteam.workspace import get_workspace_manager

    ws_mgr = get_workspace_manager(repo)
    if ws_mgr is None:
        console.print("[red]Not in a git repo.[/red]")
        raise typer.Exit(1)

    status = ws_mgr.get_status(team, agent)

    def _human(s):
        if not s:
            console.print("[dim]No workspace status[/dim]")
        else:
            for agent_name, ws_status in s.items():
                console.print(f"\n[cyan]{agent_name}:[/cyan]")
                console.print(f"  Branch: {ws_status.get('branch', 'N/A')}")
                console.print(f"  Changes: {ws_status.get('changes', 'clean')}")

    _output(status, _human)


if __name__ == "__main__":
    app()
