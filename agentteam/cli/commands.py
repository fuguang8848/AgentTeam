"""CLI shim - commands split into agentteam/cli/commands/*.py"""

from __future__ import annotations
import os
from typing import Optional
import typer
from rich.console import Console
from agentteam import __version__
from agentteam.cli.commands import *

app = typer.Typer(name="agentteam", help="Framework-agnostic multi-agent CLI", no_args_is_help=True)
console = Console()

for name, sub in [
    ("init", init_app),
    ("team", team_app),
    ("agent", agent_app),
    ("task", task_app),
    ("message", message_app),
    ("board", board_app),
    ("config", config_app),
    ("doctor", doctor_app),
    ("lifecycle", lifecycle_app),
    ("workspace", workspace_app),
    ("template", template_app),
    ("metrics", metrics_app),
    ("cost", cost_app),
    ("insights", insights_app),
    ("dag", dag_app),
    ("alert", alert_app),
    ("audit", audit_app),
    ("drift", drift_app),
    ("role", role_app),
    ("review", review_app),
    ("session", session_app),
]:
    app.add_typer(sub, name=name)

_json_output = False


def _version_callback(value: bool):
    if value:
        console.print(f"agentteam v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(None, "--version", "-v", callback=_version_callback, is_eager=True),
    json_out: bool = typer.Option(False, "--json"),
    data_dir: Optional[str] = typer.Option(None, "--data-dir"),
    transport: Optional[str] = typer.Option(None, "--transport"),
):
    global _json_output
    _json_output = json_out
    if data_dir:
        os.environ["AGENTTEAM_DATA_DIR"] = data_dir
    if transport:
        os.environ["AGENTTEAM_TRANSPORT"] = transport


if __name__ == "__main__":
    app()
