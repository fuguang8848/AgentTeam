"""
Helper functions extracted from the original commands.py.

These functions are used by both CLI commands and tests.
"""

from __future__ import annotations

import json
import locale
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional


def _deliver_to_running_agent(
    agent_name: str,
    team_name: str,
    content: str,
    from_agent: str
) -> bool:
    """
    Try to deliver a message directly to a running OpenClaw SDK agent.

    This enables immediate message delivery to agents spawned via the OpenClaw SDK backend,
    bypassing the file-based inbox for real-time communication.

    Also broadcasts a task_assigned activity to the board server for real-time monitoring.

    Args:
        agent_name: Target agent name
        team_name: Team name
        content: Message content
        from_agent: Sender name

    Returns:
        True if the agent was found and message was delivered,
        False if the agent is not a running SDK agent (caller should fall back to file inbox).
    """
    # Read the running agents registry
    data_dir = Path(os.environ.get("AGENTTEAM_DATA_DIR", "~/.agentteam")).expanduser()
    registry_file = data_dir / "running_agents.json"

    if not registry_file.exists():
        return False

    try:
        registry = json.loads(registry_file.read_text(encoding="utf-8"))
        agents = registry.get("agents", {})

        if agent_name not in agents:
            return False

        agent_info = agents[agent_name]
        session_key = agent_info.get("session_key")

        if not session_key:
            return False

        # Build the task message
        task_msg = (
            f"## New Task from {from_agent}\n\n{content}\n\n"
            f"Execute this task and report completion to your leader when done.\n"
            f'After completing, ask your leader: "Task done. Should I exit or await new tasks?"'
        )

        # Escape < > for cmd.exe (redirection operators)
        task_msg_escaped = task_msg.replace("<", "^<").replace(">", "^>")

        # Get Gateway token
        gateway_token = os.environ.get("OPENCLAW_GATEWAY_TOKEN", "")

        # Use openclaw gateway call CLI to send message
        encoding = locale.getpreferredencoding(False) or "utf-8"
        cmd = ["cmd", "/c", "openclaw", "gateway", "call", "sessions.send"]
        params = json.dumps({"key": session_key, "message": task_msg}, ensure_ascii=False)
        params_escaped = params.replace("<", "^<").replace(">", "^>")
        cmd.extend(["--params", params_escaped])
        if gateway_token:
            cmd.extend(["--token", gateway_token])

        result = subprocess.run(cmd, capture_output=True, timeout=30)

        if result.returncode != 0:
            import logging
            logger = logging.getLogger("agentteam")
            stderr = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
            logger.warning(f"Gateway sessions.send failed: {stderr}")
            return False

        # Broadcast task_assigned activity to board server
        _broadcast_activity_to_board(
            agent_name=agent_name,
            team_name=team_name,
            status="task_assigned",
            message=f"Task assigned to {agent_name} by {from_agent}",
        )

        return True

    except subprocess.TimeoutExpired:
        import logging
        logger = logging.getLogger("agentteam")
        logger.warning(f"Gateway sessions.send timed out for agent {agent_name}")
        return False
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        import logging
        logger = logging.getLogger("agentteam")
        logger.warning(f"Failed to deliver message to agent {agent_name}: {e}")
        return False


def _broadcast_activity_to_board(
    agent_name: str,
    team_name: str,
    status: str,
    message: str
) -> None:
    """
    Broadcast an activity event to the board server.

    This allows the CLI to send activity events that will be picked up by the board monitor.
    """
    board_port = os.environ.get("AGENTTEAM_BOARD_PORT", "8080")
    board_url = f"http://127.0.0.1:{board_port}/api/agents/activity"

    activity_data = {
        "team_name": team_name,
        "agent_name": agent_name,
        "status": status,
        "message": message,
    }

    try:
        req = urllib.request.Request(
            board_url,
            data=json.dumps(activity_data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5):
            pass  # Success
    except (urllib.error.URLError, Exception):
        pass  # Silently fail if board server is not running
