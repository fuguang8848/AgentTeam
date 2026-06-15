"""
Template Management Commands

Provides team template operations: list, show.
"""

from __future__ import annotations

import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from agentteam import __version__

app = typer.Typer(help="Team template management commands")
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
# Template Commands
# ============================================================================


@app.command("list")
def template_list():
    """List available team templates."""
    from agentteam.templates import list_templates

    templates = list_templates()

    def _human(templates):
        if not templates:
            console.print("[dim]No templates found[/dim]")
            return
        table = Table(title="Available Templates")
        table.add_column("Name", style="cyan")
        table.add_column("Description")
        for t in templates:
            table.add_row(t.get("name", ""), t.get("description", ""))
        console.print(table)

    _output(templates, _human)


@app.command("show")
def template_show(
    name: str = typer.Argument(..., help="Template name"),
):
    """Show detailed template information."""
    from agentteam.templates import load_template

    try:
        tmpl = load_template(name)
    except FileNotFoundError:
        console.print(f"[red]Template '{name}' not found[/red]")
        raise typer.Exit(1)

    data = {
        "name": name,
        "description": tmpl.description,
        "backend": tmpl.backend,
        "leader": {"name": tmpl.leader.name, "type": tmpl.leader.type},
        "agents": [{"name": a.name, "type": a.type} for a in tmpl.agents],
        "tasks": [{"subject": t.subject, "owner": t.owner} for t in tmpl.tasks],
    }

    def _human(d):
        console.print(f"\n[bold]Template: {d['name']}[/bold]")
        console.print(f"  Description: {d['description']}")
        console.print(f"  Backend: {d['backend']}")
        console.print(f"\n  [cyan]Leader:[/cyan] {d['leader']['name']} ({d['leader']['type']})")
        if d.get("agents"):
            console.print(f"\n  [cyan]Agents ({len(d['agents'])}):[/cyan]")
            for a in d["agents"]:
                console.print(f"    - {a['name']} ({a['type']})")
        if d.get("tasks"):
            console.print(f"\n  [cyan]Tasks ({len(d['tasks'])}):[/cyan]")
            for t in d["tasks"]:
                owner = f" (@ {t['owner']})" if t.get("owner") else ""
                console.print(f"    - {t['subject']}{owner}")

    _output(data, _human)


if __name__ == "__main__":
    app()
