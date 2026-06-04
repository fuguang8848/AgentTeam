"""
Metrics, Insights, and DAG Commands

Provides: cost_* commands, insights_* commands, dag_* commands.
"""

from __future__ import annotations

import datetime
import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from agentteam import __version__

app = typer.Typer(help="Metrics, insights, and DAG commands")
cost_app = typer.Typer(help="Cost tracking and budget management")
insights_app = typer.Typer(help="Team insights commands")
dag_app = typer.Typer(help="DAG (dependency graph) commands")

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
# Cost Commands
# ============================================================================


@cost_app.command("report")
def cost_report(
    team: str = typer.Argument(..., help="Team name"),
    input_tokens: int = typer.Option(0, "--input-tokens", help="Input tokens consumed"),
    output_tokens: int = typer.Option(0, "--output-tokens", help="Output tokens consumed"),
    cost_cents: float = typer.Option(0.0, "--cost-cents", help="Cost in cents"),
    provider: str = typer.Option("", "--provider", help="Provider name"),
    model: str = typer.Option("", "--model", help="Model name"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent name"),
    task_id: str = typer.Option("", "--task-id", help="Associated task ID"),
):
    """Report token usage and cost for an agent."""
    from agentteam.identity import AgentIdentity
    from agentteam.team.costs import CostStore
    from agentteam.team.manager import TeamManager

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
    _output(_dump(event), lambda d: console.print(f"[green]OK[/green] Cost reported: ${d.get('costCents', 0) / 100:.4f}"))


@cost_app.command("show")
def cost_show(
    team: str = typer.Argument(..., help="Team name"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Filter by agent"),
    by: Optional[str] = typer.Option(None, "--by", "-b", help="Breakdown: agent, task, or model"),
):
    """Show cost summary and event history."""
    from agentteam.team.costs import CostStore
    from agentteam.team.manager import TeamManager

    store = CostStore(team)
    summary = store.summary()
    events = store.list_events(agent_name=agent or "")
    config = TeamManager.get_team(team)
    budget = config.budget_cents if config else 0.0
    rate = store.cost_rate()

    data = {"summary": _dump(summary), "budget_cents": budget, "cost_rate_per_min": rate, "events": [_dump(e) for e in events]}

    def _human(d):
        s = d["summary"]
        total = s.get("totalCostCents", 0)
        console.print(f"\nCost Summary - [cyan]{team}[/cyan]")
        if budget > 0:
            console.print(f"  Total: ${total / 100:.4f} / ${budget / 100:.2f}")
        else:
            console.print(f"  Total: ${total / 100:.4f}")
        console.print(f"  Events: {s.get('eventCount', 0)}")

    _output(data, _human)


@cost_app.command("budget")
def cost_budget(
    team: str = typer.Argument(..., help="Team name"),
    amount: Optional[float] = typer.Argument(None, help="Budget in dollars (omit to show current)"),
):
    """Set or show team cost budget."""
    from agentteam.team.manager import TeamManager

    config = TeamManager.get_team(team)
    if not config:
        console.print(f"[red]Team '{team}' not found[/red]")
        raise typer.Exit(1)

    if amount is None:
        budget = config.budget_cents
        _output({"budget_cents": budget, "budget_dollars": budget / 100},
                lambda d: console.print(f"Current budget: ${d['budget_dollars']:.2f}"))
    else:
        budget_cents = int(amount * 100)
        TeamManager.update_team(team, budget_cents=budget_cents)
        _output({"status": "updated", "budget_cents": budget_cents},
                lambda d: console.print(f"[green]OK[/green] Budget set to ${d['budget_cents'] / 100:.2f}"))


# ============================================================================
# Insights Commands
# ============================================================================


@insights_app.command("show")
def insights_show(
    team: str = typer.Argument(..., help="Team name"),
):
    """Show team insights summary."""
    from agentteam.team.insights import InsightsEngine

    engine = InsightsEngine(team)
    insights = engine.get_summary()

    def _human(d):
        console.print(f"\n[bold]Insights - {team}[/bold]")
        console.print(f"  Active agents: {d.get('active_agents', 0)}")
        console.print(f"  Completed tasks: {d.get('completed_tasks', 0)}")
        console.print(f"  Total cost: ${d.get('total_cost', 0):.4f}")

    _output(insights, _human)


@insights_app.command("tools")
def insights_tools(
    team: str = typer.Argument(..., help="Team name"),
):
    """Show tool usage insights."""
    from agentteam.team.insights import InsightsEngine

    engine = InsightsEngine(team)
    tools = engine.get_tool_usage()

    def _human(t):
        if not t:
            console.print("[dim]No tool usage data[/dim]")
            return
        table = Table(title=f"Tool Usage - {team}")
        table.add_column("Tool", style="cyan")
        table.add_column("Calls", justify="right")
        for tool, count in t.items():
            table.add_row(tool, str(count))
        console.print(table)

    _output(tools, _human)


@insights_app.command("skills")
def insights_skills(
    team: str = typer.Argument(..., help="Team name"),
):
    """Show skill usage insights."""
    from agentteam.team.insights import InsightsEngine

    engine = InsightsEngine(team)
    skills = engine.get_skill_usage()

    def _human(s):
        if not s:
            console.print("[dim]No skill usage data[/dim]")
            return
        table = Table(title=f"Skill Usage - {team}")
        table.add_column("Skill", style="cyan")
        table.add_column("Uses", justify="right")
        for skill, count in s.items():
            table.add_row(skill, str(count))
        console.print(table)

    _output(skills, _human)


@insights_app.command("memory")
def insights_memory(
    team: str = typer.Argument(..., help="Team name"),
):
    """Show memory usage insights."""
    from agentteam.team.insights import InsightsEngine

    engine = InsightsEngine(team)
    memory = engine.get_memory_stats()

    def _human(m):
        console.print(f"\n[bold]Memory Stats - {team}[/bold]")
        console.print(f"  Entries: {m.get('entry_count', 0)}")
        console.print(f"  Size: {m.get('size_bytes', 0) / 1024:.1f} KB")

    _output(memory, _human)


# ============================================================================
# DAG Commands
# ============================================================================


@dag_app.command("sort")
def dag_sort(
    team: str = typer.Argument(..., help="Team name"),
):
    """Show tasks sorted by dependency order (topological sort)."""
    from agentteam.team.tasks import TaskStore
    from agentteam.team.models import TaskStatus

    store = TaskStore(team)
    tasks = store.list_tasks()

    # Simple topological sort
    sorted_ids = []
    remaining = {t.id: t for t in tasks}
    completed = set()

    while remaining:
        ready = [tid for tid, t in remaining.items() if not any(b in remaining for b in (t.blocked_by or []))]
        if not ready:
            break
        for tid in ready:
            sorted_ids.append(tid)
            del remaining[tid]

    def _human(ids):
        console.print(f"\n[bold]Task Order - {team}[/bold]")
        for i, tid in enumerate(ids):
            console.print(f"  {i + 1}. {tid}")

    _output({"order": sorted_ids}, _human)


@dag_app.command("check")
def dag_check(
    team: str = typer.Argument(..., help="Team name"),
):
    """Check for cycles and blocked tasks."""
    from agentteam.team.tasks import TaskStore

    store = TaskStore(team)
    tasks = store.list_tasks()

    # Check for cycles
    graph = {t.id: (t.blocks or []) for t in tasks}
    visited = set()
    rec_stack = set()
    has_cycle = False

    def dfs(node):
        nonlocal has_cycle
        visited.add(node)
        rec_stack.add(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                has_cycle = True
                return True
        rec_stack.remove(node)
        return False

    for task_id in graph:
        if task_id not in visited:
            dfs(task_id)

    blocked = [t.id for t in tasks if t.status == TaskStatus.blocked]

    _output({"has_cycle": has_cycle, "blocked_tasks": blocked},
            lambda d: console.print(f"[{'red' if d['has_cycle'] else 'green'}]{'Cycle detected!' if d['has_cycle'] else 'No cycles found'}[/] Blocked: {len(d['blocked_tasks'])}"))


@dag_app.command("ready")
def dag_ready(
    team: str = typer.Argument(..., help="Team name"),
):
    """Show tasks that are ready to execute (all dependencies satisfied)."""
    from agentteam.team.tasks import TaskStore
    from agentteam.team.models import TaskStatus

    store = TaskStore(team)
    tasks = store.list_tasks()

    blocked_map = {t.id: set(t.blocked_by or []) for t in tasks}
    completed = {t.id for t in tasks if t.status == TaskStatus.completed}
    ready = [t.id for t in tasks if t.status == TaskStatus.pending and not (blocked_map.get(t.id, set()) - completed)]

    def _human(ids):
        if not ids:
            console.print("[dim]No tasks ready[/dim]")
        else:
            console.print("[bold]Ready tasks:[/bold]")
            for tid in ids:
                console.print(f"  - {tid}")

    _output({"ready": ready}, _human)


if __name__ == "__main__":
    app()
