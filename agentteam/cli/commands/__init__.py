"""
CLI Commands Module - Modularized from commands.py

This module contains all CLI sub-commands organized into separate files:
- init: Interactive onboarding wizard
- team: Team management (create, discover, join, status, cleanup)
- agent: Agent lifecycle (spawn, list, info, health, restart, pause, resume, kill)
- task: Task management (create, get, update, list, stats, wait, route)
- message: Inter-agent messaging (send, broadcast, receive, peek, log, watch)
- board: Dashboard and kanban (show, overview, live, monitor, serve, attach)
- config: Configuration management (show, init, set, get, health)
- lifecycle: Lifecycle management (shutdown, idle, exit, zombie check, etc.)
- workspace: Git worktree management (list, checkpoint, merge, cleanup, status)
- template: Team templates (list, show)
- metrics: Metrics and insights (cost, insights, dag)
- alert: Alert and audit (alert, audit, drift, role, review)
- session: Session persistence (save, show, clear)
"""

from agentteam.cli.commands.init import app as init_app
from agentteam.cli.commands.team import app as team_app
from agentteam.cli.commands.agent import app as agent_app
from agentteam.cli.commands.task import app as task_app
from agentteam.cli.commands.message import app as message_app
from agentteam.cli.commands.board import app as board_app
from agentteam.cli.commands.config import app as config_app, doctor_app
from agentteam.cli.commands.lifecycle import app as lifecycle_app
from agentteam.cli.commands.workspace import app as workspace_app
from agentteam.cli.commands.template import app as template_app
from agentteam.cli.commands.metrics import app as metrics_app, cost_app, insights_app, dag_app
from agentteam.cli.commands.alert import app as alert_app, alert_app, audit_app, drift_app, role_app, review_app
from agentteam.cli.commands.session import app as session_app

# Re-export helper functions for backward compatibility
from agentteam.cli.commands.helpers import _deliver_to_running_agent, _broadcast_activity_to_board

# Top-level app: combines all sub-apps for legacy `from agentteam.cli.commands import app`
# (Python prefers this package over the commands.py shim, so we must expose app here.)
# 2026-06-18 fix: 8080 DOWN, ImportError: cannot import name 'app' from 'agentteam.cli.commands'
import typer
app = typer.Typer(name="agentteam", help="Framework-agnostic multi-agent CLI", no_args_is_help=True)
for _name, _sub in [
    ("init", init_app),
    ("team", team_app),
    ("agent", agent_app),
    ("task", task_app),
    ("message", message_app),
    ("board", board_app),
    ("config", config_app),
    ("lifecycle", lifecycle_app),
    ("workspace", workspace_app),
    ("template", template_app),
    ("metrics", metrics_app),
    ("session", session_app),
    ("alert", alert_app),
    ("audit", audit_app),
    ("drift", drift_app),
    ("role", role_app),
    ("review", review_app),
]:
    app.add_typer(_sub, name=_name)

__all__ = [
    # Main apps
    "init_app",
    "team_app",
    "agent_app",
    "task_app",
    "message_app",
    "board_app",
    "config_app",
    "doctor_app",
    "lifecycle_app",
    "workspace_app",
    "template_app",
    "metrics_app",
    "alert_app",
    "session_app",
    # Sub-apps
    "cost_app",
    "insights_app",
    "dag_app",
    "audit_app",
    "drift_app",
    "role_app",
    "review_app",
    # Helper functions (backward compatibility)
    "_deliver_to_running_agent",
    "_broadcast_activity_to_board",
]
