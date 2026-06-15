"""
Task Management Commands

Provides task lifecycle operations: create, get, update, list, stats, wait, route.
"""

from __future__ import annotations

import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from agentteam import __version__

app = typer.Typer(help="Task management commands")
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
# Task Commands
# ============================================================================


@app.command("create")
def task_create(
    team: str = typer.Argument(..., help="Team name"),
    subject: str = typer.Argument(..., help="Task subject"),
    description: str = typer.Option("", "--description", "-d", help="Task description"),
    owner: Optional[str] = typer.Option(None, "--owner", "-o", help="Owner agent name"),
    blocks: Optional[str] = typer.Option(None, "--blocks", help="Comma-separated task IDs this blocks"),
    blocked_by: Optional[str] = typer.Option(None, "--blocked-by", help="Comma-separated task IDs this is blocked by"),
):
    """Create a new task (TaskCreate)."""
    from agentteam.team.tasks import TaskStore

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


@app.command("get")
def task_get(
    team: str = typer.Argument(..., help="Team name"),
    task_id: str = typer.Argument(..., help="Task ID"),
):
    """Get a single task (TaskGet)."""
    from agentteam.team.tasks import TaskStore

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


@app.command("update")
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
    from agentteam.identity import AgentIdentity
    from agentteam.team.models import TaskStatus
    from agentteam.team.tasks import TaskLockError, TaskStore

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


@app.command("list")
def task_list(
    team: str = typer.Argument(..., help="Team name"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    owner: Optional[str] = typer.Option(None, "--owner", "-o", help="Filter by owner"),
):
    """List tasks for a team (TaskList)."""
    from agentteam.team.models import TaskStatus
    from agentteam.team.tasks import TaskStore

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


@app.command("stats")
def task_stats(
    team: str = typer.Argument(..., help="Team name"),
):
    """Show task timing statistics for a team."""
    from agentteam.team.tasks import TaskStore

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


@app.command("wait")
def task_wait(
    team: str = typer.Argument(..., help="Team name"),
    task_id: str = typer.Argument(..., help="Task ID to wait for"),
    timeout: int = typer.Option(300, "--timeout", "-t", help="Timeout in seconds"),
):
    """Wait for a task to complete (blocking)."""
    from agentteam.team.models import TaskStatus
    from agentteam.team.tasks import TaskStore

    store = TaskStore(team)
    start = __import__("time").time()

    with console.status(f"[cyan]Waiting for task {task_id}..."):
        while __import__("time").time() - start < timeout:
            task = store.get(task_id)
            if not task:
                console.print(f"[red]Task '{task_id}' not found[/red]")
                raise typer.Exit(1)
            if task.status == TaskStatus.completed:
                _output(
                    _dump(task),
                    lambda d: console.print(f"[green]✓ Task {task_id} completed![/green]"),
                )
                return
            elif task.status == TaskStatus.blocked:
                _output(
                    _dump(task),
                    lambda d: console.print(f"[yellow]⚠ Task {task_id} is blocked[/yellow]"),
                )
                raise typer.Exit(1)
            __import__("time").sleep(2)

    _output(
        {"error": "timeout", "taskId": task_id},
        lambda d: console.print(f"[yellow]Timeout waiting for task {task_id}[/yellow]"),
    )
    raise typer.Exit(1)


@app.command("route")
def task_route(
    team: str = typer.Argument(..., help="Team name"),
    subject: str = typer.Option(..., "--subject", "-s", help="Task subject"),
    description: str = typer.Option("", "--description", "-d", help="Task description"),
    candidates: Optional[str] = typer.Option(None, "--candidates", "-c", help="Comma-separated agent names"),
):
    """Find the best agent for a task using intelligent routing."""
    from agentteam.team.router import get_router

    router = get_router(team)
    router.update_load(team)

    cand_list = [c.strip() for c in candidates.split(",")] if candidates else None
    all_candidates = router.get_all_candidates(subject, description, cand_list)

    if not all_candidates:
        _output(
            {"error": "No available agents found"},
            lambda d: console.print(f"[red]{d['error']}[/red]"),
        )
        raise typer.Exit(1)

    best = router.select_best(all_candidates, subject, description)

    data = {
        "task": {"subject": subject, "description": description},
        "selectedAgent": best,
        "candidates": all_candidates,
    }

    def _human(d):
        console.print(f"\n[bold]Task Routing Result[/bold]")
        console.print(f"  Subject: {d['task']['subject']}")
        console.print(f"  Selected: [green]{d['selectedAgent']}[/green]")
        if d["candidates"]:
            console.print(f"  Other candidates: {', '.join(d['candidates'])}")

    _output(data, _human)


if __name__ == "__main__":
    app()
