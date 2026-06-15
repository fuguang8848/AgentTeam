"""Chat command handlers for the chat feature."""

from __future__ import annotations

import json
from typing import Optional

from agentteam.board.chat.ai_assistant import call_ai_assistant, generate_simple_response
from agentteam.board.utils import _now_iso


def handle_chat_command(message: str, user: str = "User") -> dict:
    """Handle a chat command from the user.

    Returns a dict with 'role', 'content', and 'timestamp' keys.
    """
    message_lower = message.lower().strip()

    # /help command
    if message_lower.startswith("/help"):
        return _handle_help_command()

    # /members command
    if message_lower.startswith("/members"):
        return _handle_members_command()

    # /status command
    if message_lower.startswith("/status"):
        return _handle_status_command()

    # /tasks command
    if message_lower.startswith("/tasks"):
        return _handle_tasks_command()

    # /clear command
    if message_lower.startswith("/clear"):
        return _handle_clear_command()

    # Regular message - call AI for response
    return call_ai_assistant(message, user)


def _handle_help_command() -> dict:
    """Handle the /help command."""
    help_text = """AgentTeam AI 助手命令：

通用命令：
/help - 显示此帮助信息
/members - 查看团队成员
/status - 查看团队状态
/tasks - 查看任务列表
/clear - 清除对话历史

你也可以直接发送消息，我会尽力帮助你！"""

    return {
        "role": "system",
        "content": help_text,
        "timestamp": _now_iso(),
    }


def _handle_members_command() -> dict:
    """Handle the /members command - list active team members."""
    try:
        from agentteam.session.registry import get_session_registry

        registry = get_session_registry()
        sessions = registry.list_sessions()

        active_sessions = [s for s in sessions if s.status == "active"]

        if not active_sessions:
            return {
                "role": "system",
                "content": "No active team members.",
                "timestamp": _now_iso(),
            }

        response = "Active Team Members:\n"
        for session in active_sessions[:20]:  # Show first 20
            role = session.role or "unknown"
            name = session.name or role
            response += (
                f"• {name} ({role}) - Active since {session.created_at[:16] if session.created_at else 'unknown'}\n"
            )

        return {"role": "system", "content": response, "timestamp": _now_iso()}
    except Exception as e:
        return {
            "role": "system",
            "content": f"Error listing members: {str(e)}",
            "timestamp": _now_iso(),
        }


def _handle_status_command() -> dict:
    """Handle the /status command - show team status."""
    try:
        from agentteam.team.manager import TeamManager

        teams = TeamManager.list_teams()

        if not teams:
            return {
                "role": "system",
                "content": "No active teams.",
                "timestamp": _now_iso(),
            }

        response = "Team Status:\n"
        for team_name in teams[:10]:  # Show first 10
            team = TeamManager.get_team(team_name)
            if team:
                status = "active" if team.members else "idle"
                member_count = len(team.members)
                response += f"• {team_name}: {status} ({member_count} members)\n"

        return {"role": "system", "content": response, "timestamp": _now_iso()}
    except Exception as e:
        return {
            "role": "system",
            "content": f"Error getting status: {str(e)}",
            "timestamp": _now_iso(),
        }


def _handle_tasks_command() -> dict:
    """Handle the /tasks command - list pending tasks."""
    try:
        from agentteam.team.tasks import TaskStore

        # Get all tasks from all teams
        all_tasks = []
        try:
            from agentteam.team.manager import TeamManager

            teams = TeamManager.list_teams()
            for team_name in teams:
                try:
                    store = TaskStore(team_name)
                    tasks = store.list()
                    all_tasks.extend(tasks)
                except Exception:
                    pass
        except Exception:
            pass

        if not all_tasks:
            return {
                "role": "system",
                "content": "No active tasks.",
                "timestamp": _now_iso(),
            }

        # Group by status
        pending = [t for t in all_tasks if t.status == "pending"]
        in_progress = [t for t in all_tasks if t.status == "in_progress"]
        completed = [t for t in all_tasks if t.status == "completed"]

        response = "Tasks Summary:\n"
        if pending:
            response += f"Pending ({len(pending)}):\n"
            for t in pending[:5]:
                response += f"  • {t.subject}\n"
            if len(pending) > 5:
                response += f"  ... and {len(pending) - 5} more\n"

        if in_progress:
            response += f"\nIn Progress ({len(in_progress)}):\n"
            for t in in_progress[:5]:
                response += f"  • {t.subject}\n"
            if len(in_progress) > 5:
                response += f"  ... and {len(in_progress) - 5} more\n"

        if completed:
            response += f"\nCompleted ({len(completed)} total)\n"

        return {"role": "system", "content": response, "timestamp": _now_iso()}
    except Exception as e:
        return {
            "role": "system",
            "content": f"Error listing tasks: {str(e)}",
            "timestamp": _now_iso(),
        }


def _handle_clear_command() -> dict:
    """Handle the /clear command."""
    return {
        "role": "system",
        "content": "CLEAR_CHAT_HISTORY",
        "timestamp": _now_iso(),
    }


def process_chat_message(message: str, user: str = "User") -> dict:
    """Process a chat message and return a response.

    This is the main entry point for chat message processing.
    """
    return handle_chat_command(message, user)
