"""
CLI commands shim for agentteam - Framework-agnostic multi-agent coordination CLI.

This file has been modularized into separate command modules in agentteam/cli/commands/.
See agentteam/cli/commands/__init__.py for the full list of available commands.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from agentteam import __version__

# Re-export the main app from the new modular structure
# This shim maintains backward compatibility
app = typer.Typer(
    name="agentteam",
    help="Framework-agnostic multi-agent coordination CLI",
    no_args_is_help=True,
)
console = Console()

# Import all modular command apps
from agentteam.cli.commands import (
    init_app, team_app, agent_app, task_app, message_app,
    board_app, config_app, doctor_app, lifecycle_app, workspace_app,
    template_app, metrics_app, alert_app, session_app,
    cost_app, insights_app, dag_app, audit_app, drift_app, role_app, review_app,
)

# Register all sub-apps
app.add_typer(init_app, name="init")
app.add_typer(team_app, name="team")
app.add_typer(agent_app, name="agent")
app.add_typer(task_app, name="task")
app.add_typer(message_app, name="message")
app.add_typer(board_app, name="board")
app.add_typer(config_app, name="config")
app.add_typer(doctor_app, name="doctor")
app.add_typer(lifecycle_app, name="lifecycle")
app.add_typer(workspace_app, name="workspace")
app.add_typer(template_app, name="template")
app.add_typer(metrics_app, name="metrics")
app.add_typer(cost_app, name="cost")
app.add_typer(insights_app, name="insights")
app.add_typer(dag_app, name="dag")
app.add_typer(alert_app, name="alert")
app.add_typer(audit_app, name="audit")
app.add_typer(drift_app, name="drift")
app.add_typer(role_app, name="role")
app.add_typer(review_app, name="review")
app.add_typer(session_app, name="session")

# Global options
_json_output: bool = False


def _version_callback(value: bool):
    if value:
        console.print(f"agentteam v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(None, "--version", "-v", callback=_version_callback, is_eager=True, help="Show version and exit."),
    json_out: bool = typer.Option(False, "--json", help="Output JSON instead of human-readable text."),
    data_dir: Optional[str] = typer.Option(None, "--data-dir", help="Override data directory."),
    transport: Optional[str] = typer.Option(None, "--transport", help="Transport backend: file or p2p."),
):
    """agentteam - Framework-agnostic multi-agent coordination CLI."""
    global _json_output
    _json_output = json_out
    if data_dir:
        os.environ["AGENTTEAM_DATA_DIR"] = data_dir
    if transport:
        os.environ["AGENTTEAM_TRANSPORT"] = transport


if __name__ == "__main__":
    app()
