"""
Alert, Audit, Drift, and Role Commands

Provides: alert_* commands, audit_* commands, drift_* commands, role_* commands.
"""

from __future__ import annotations

import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from agentteam import __version__

app = typer.Typer(help="Alert, audit, drift, and role commands")
alert_app = typer.Typer(help="Alert management commands")
audit_app = typer.Typer(help="Audit log commands")
drift_app = typer.Typer(help="Drift detection commands")
role_app = typer.Typer(help="Role assignment commands")
review_app = typer.Typer(help="Code review commands")

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
# Alert Commands
# ============================================================================


@alert_app.command("check")
def alert_check(
    team: str = typer.Argument(..., help="Team name"),
):
    """Check for active alerts."""
    from agentteam.alerts import AlertManager

    manager = AlertManager(team)
    alerts = manager.check_alerts()

    def _human(a):
        if not a:
            console.print("[green]No active alerts[/green]")
        else:
            table = Table(title=f"Alerts - {team}")
            table.add_column("ID", style="dim")
            table.add_column("Severity", style="red")
            table.add_column("Message")
            for alert in a:
                table.add_row(alert.get("id", ""), alert.get("severity", ""), alert.get("message", ""))
            console.print(table)

    _output(alerts, _human)


@alert_app.command("list")
def alert_list(
    team: str = typer.Argument(..., help="Team name"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
):
    """List all alerts for a team."""
    from agentteam.alerts import AlertManager

    manager = AlertManager(team)
    alerts = manager.list_alerts(status=status)

    def _human(a):
        if not a:
            console.print("[dim]No alerts[/dim]")
            return
        table = Table(title=f"Alerts - {team}")
        table.add_column("ID", style="dim")
        table.add_column("Severity")
        table.add_column("Message")
        table.add_column("Status")
        for alert in a:
            table.add_row(
                alert.get("id", ""), alert.get("severity", ""), alert.get("message", "")[:50], alert.get("status", "")
            )
        console.print(table)

    _output(alerts, _human)


@alert_app.command("acknowledge")
def alert_acknowledge(
    team: str = typer.Argument(..., help="Team name"),
    alert_id: str = typer.Argument(..., help="Alert ID"),
):
    """Acknowledge an alert."""
    from agentteam.alerts import AlertManager

    manager = AlertManager(team)
    manager.acknowledge(alert_id)

    _output(
        {"status": "acknowledged", "alertId": alert_id},
        lambda d: console.print(f"[green]Alert {d['alertId']} acknowledged[/green]"),
    )


@alert_app.command("config")
def alert_config(
    team: str = typer.Argument(..., help="Team name"),
    enable: bool = typer.Option(True, "--enable/--disable", help="Enable or disable alerts"),
):
    """Configure alert settings."""
    from agentteam.alerts import AlertManager

    manager = AlertManager(team)
    manager.configure(enabled=enable)

    _output(
        {"status": "configured", "enabled": enable},
        lambda d: console.print(f"[green]Alerts {'enabled' if d['enabled'] else 'disabled'}[/green]"),
    )


# ============================================================================
# Audit Commands
# ============================================================================


@audit_app.command("query")
def audit_query(
    team: str = typer.Argument(..., help="Team name"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Filter by agent"),
    action: Optional[str] = typer.Option(None, "--action", help="Filter by action"),
    limit: int = typer.Option(50, "--limit", "-n", help="Max results"),
):
    """Query audit logs."""
    from agentteam.audit import AuditLog

    log = AuditLog(team)
    entries = log.query(agent=agent, action=action, limit=limit)

    def _human(e):
        if not e:
            console.print("[dim]No audit entries[/dim]")
            return
        table = Table(title=f"Audit Log - {team}")
        table.add_column("Time", style="dim")
        table.add_column("Agent")
        table.add_column("Action")
        table.add_column("Details")
        for entry in e:
            table.add_row(
                entry.get("timestamp", "")[:19],
                entry.get("agent", ""),
                entry.get("action", ""),
                str(entry.get("details", ""))[:40],
            )
        console.print(table)

    _output(entries, _human)


@audit_app.command("summary")
def audit_summary(
    team: str = typer.Argument(..., help="Team name"),
):
    """Show audit summary."""
    from agentteam.audit import AuditLog

    log = AuditLog(team)
    summary = log.summary()

    def _human(s):
        console.print(f"\n[bold]Audit Summary - {team}[/bold]")
        console.print(f"  Total events: {s.get('total_events', 0)}")
        console.print(f"  Unique agents: {s.get('unique_agents', 0)}")

    _output(summary, _human)


@audit_app.command("log")
def audit_log(
    team: str = typer.Argument(..., help="Team name"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file"),
):
    """Export audit log to file."""
    from agentteam.audit import AuditLog

    log = AuditLog(team)
    entries = log.get_all()

    if output:
        with open(output, "w") as f:
            json.dump(entries, f, indent=2)
        console.print(f"[green]Audit log exported to {output}[/green]")
    else:
        _output(entries)


# ============================================================================
# Drift Commands
# ============================================================================


@drift_app.command("check")
def drift_check(
    team: str = typer.Argument(..., help="Team name"),
):
    """Check for configuration drift."""
    from agentteam.drift import DriftDetector

    detector = DriftDetector(team)
    drifts = detector.check()

    def _human(d):
        if not d:
            console.print("[green]No drift detected[/green]")
        else:
            console.print("[yellow]Configuration drift detected:[/yellow]")
            for drift in d:
                console.print(f"  - {drift.get('path', '')}: {drift.get('expected', '')} -> {drift.get('actual', '')}")

    _output(drifts, _human)


@drift_app.command("list")
def drift_list(
    team: str = typer.Argument(..., help="Team name"),
):
    """List all known drift records."""
    from agentteam.drift import DriftDetector

    detector = DriftDetector(team)
    records = detector.list_records()

    def _human(r):
        if not r:
            console.print("[dim]No drift records[/dim]")
            return
        table = Table(title=f"Drift Records - {team}")
        table.add_column("Path")
        table.add_column("Expected")
        table.add_column("Actual")
        table.add_column("Detected", style="dim")
        for rec in r:
            table.add_row(
                rec.get("path", ""),
                str(rec.get("expected", ""))[:30],
                str(rec.get("actual", ""))[:30],
                rec.get("detected_at", "")[:19],
            )
        console.print(table)

    _output(records, _human)


@drift_app.command("ack")
def drift_ack(
    team: str = typer.Argument(..., help="Team name"),
    path: str = typer.Argument(..., help="Configuration path"),
):
    """Acknowledge and accept current drift for a path."""
    from agentteam.drift import DriftDetector

    detector = DriftDetector(team)
    detector.acknowledge(path)

    _output(
        {"status": "acknowledged", "path": path},
        lambda d: console.print(f"[green]Drift for {d['path']} acknowledged[/green]"),
    )


@drift_app.command("record")
def drift_record(
    team: str = typer.Argument(..., help="Team name"),
):
    """Record current state as the baseline for drift detection."""
    from agentteam.drift import DriftDetector

    detector = DriftDetector(team)
    detector.record_baseline()

    _output({"status": "recorded"}, lambda d: console.print("[green]Baseline recorded[/green]"))


@drift_app.command("scan")
def drift_scan(
    team: str = typer.Argument(..., help="Team name"),
):
    """Scan all configurations for drift."""
    from agentteam.drift import DriftDetector

    detector = DriftDetector(team)
    results = detector.scan_all()

    def _human(r):
        console.print(f"\n[bold]Drift Scan - {team}[/bold]")
        console.print(f"  Configurations checked: {r.get('checked', 0)}")
        console.print(f"  Drift detected: {r.get('drift_count', 0)}")

    _output(results, _human)


# ============================================================================
# Role Commands
# ============================================================================


@role_app.command("assign")
def role_assign(
    team: str = typer.Argument(..., help="Team name"),
    agent: str = typer.Argument(..., help="Agent name"),
    role: str = typer.Argument(..., help="Role name"),
):
    """Assign a role to an agent."""
    from agentteam.team.roles import RoleManager

    manager = RoleManager(team)
    manager.assign(agent, role)

    _output(
        {"status": "assigned", "agent": agent, "role": role},
        lambda d: console.print(f"[green]{d['agent']} assigned role '{d['role']}'[/green]"),
    )


@role_app.command("unassign")
def role_unassign(
    team: str = typer.Argument(..., help="Team name"),
    agent: str = typer.Argument(..., help="Agent name"),
    role: str = typer.Argument(..., help="Role name"),
):
    """Remove a role from an agent."""
    from agentteam.team.roles import RoleManager

    manager = RoleManager(team)
    manager.unassign(agent, role)

    _output(
        {"status": "unassigned", "agent": agent, "role": role},
        lambda d: console.print(f"[green]Role '{d['role']}' removed from {d['agent']}[/green]"),
    )


@role_app.command("list")
def role_list(
    team: str = typer.Argument(..., help="Team name"),
):
    """List all role assignments."""
    from agentteam.team.roles import RoleManager

    manager = RoleManager(team)
    assignments = manager.list_all()

    def _human(a):
        if not a:
            console.print("[dim]No role assignments[/dim]")
            return
        table = Table(title=f"Role Assignments - {team}")
        table.add_column("Agent", style="cyan")
        table.add_column("Roles")
        for agent, roles in a.items():
            table.add_row(agent, ", ".join(roles))
        console.print(table)

    _output(assignments, _human)


@role_app.command("suggest")
def role_suggest(
    team: str = typer.Argument(..., help="Team name"),
    agent: str = typer.Argument(..., help="Agent name"),
):
    """Suggest appropriate roles for an agent based on capabilities."""
    from agentteam.team.roles import RoleManager

    manager = RoleManager(team)
    suggestions = manager.suggest(agent)

    def _human(s):
        if not s:
            console.print("[dim]No role suggestions[/dim]")
        else:
            console.print(f"[bold]Suggested roles for {agent}:[/bold]")
            for role, score in s:
                console.print(f"  - {role} (score: {score:.2f})")

    _output(suggestions, _human)


# ============================================================================
# Review Commands
# ============================================================================


@review_app.command("score")
def review_score(
    team: str = typer.Argument(..., help="Team name"),
    agent: str = typer.Argument(..., help="Agent name"),
):
    """Calculate review score for an agent."""
    from agentteam.review import ReviewEngine

    engine = ReviewEngine(team)
    score = engine.calculate_score(agent)

    _output({"agent": agent, "score": score}, lambda d: console.print(f"Score for {d['agent']}: {d['score']:.2f}"))


@review_app.command("show")
def review_show(
    team: str = typer.Argument(..., help="Team name"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent name"),
):
    """Show review history."""
    from agentteam.review import ReviewEngine

    engine = ReviewEngine(team)
    reviews = engine.get_reviews(agent=agent)

    def _human(r):
        if not r:
            console.print("[dim]No reviews[/dim]")
            return
        for review in r:
            console.print(f"\n[cyan]{review.get('agent', '')}[/cyan] - Score: {review.get('score', 0):.2f}")
            console.print(f"  {review.get('summary', '')[:100]}")

    _output(reviews, _human)


@review_app.command("compare")
def review_compare(
    team: str = typer.Argument(..., help="Team name"),
    agent1: str = typer.Argument(..., help="First agent"),
    agent2: str = typer.Argument(..., help="Second agent"),
):
    """Compare two agents' performance."""
    from agentteam.review import ReviewEngine

    engine = ReviewEngine(team)
    comparison = engine.compare(agent1, agent2)

    def _human(c):
        console.print(f"\n[bold]Comparison: {c['agent1']} vs {c['agent2']}[/bold]")
        console.print(f"  Scores: {c['score1']:.2f} vs {c['score2']:.2f}")
        winner = c["agent1"] if c["score1"] > c["score2"] else c["agent2"]
        console.print(f"  Winner: {winner}")

    _output(comparison, _human)


if __name__ == "__main__":
    app()
