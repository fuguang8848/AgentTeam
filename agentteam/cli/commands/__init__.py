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
]
