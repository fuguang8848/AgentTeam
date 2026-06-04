"""Agent management mixin for the board handler."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentteam.board.handlers.base import BaseHandler


class AgentMixin:
    """Mixin for agent management functionality."""

    def handle_get_agents(self, team_name: str) -> None:
        """Handle GET /api/team/{team_name}/agents.

        Returns agents for a team.
        """
        if not team_name:
            self.send_error(400, "Team name required")
            return

        try:
            from agentteam.board.utils import _get_collector

            collector = _get_collector()
            team_data = collector.collect_team(team_name)
            if team_data:
                agents = team_data.get("agents", [])
                self._serve_json({"agents": agents})
            else:
                self._serve_json({"agents": []})

        except Exception as e:
            self.send_error(500, str(e))

    def handle_get_agent_state(self, agent_id: str) -> None:
        """Handle GET /api/agents/{agent_id}/state.

        Returns the state of a specific agent.
        """
        if not agent_id:
            self.send_error(400, "Agent ID required")
            return

        try:
            from agentteam.session.registry import get_session_registry

            registry = get_session_registry()
            session = registry.get_session(agent_id)

            if session:
                self._serve_json({
                    "agentId": session.agent_id,
                    "name": session.name,
                    "role": session.role,
                    "status": session.status,
                    "createdAt": session.created_at,
                    "workDir": getattr(session, "work_dir", ""),
                })
            else:
                self.send_error(404, f"Agent '{agent_id}' not found")

        except Exception as e:
            self.send_error(500, str(e))

    def handle_agent_activity(self) -> None:
        """Handle POST /api/agents/activity.

        Emit an agent activity event.
        """
        payload = self._parse_json_body()
        if payload is None:
            return

        try:
            from agentteam.board.sse.agent_activity import _broadcast_agent_activity

            # Add timestamp if not present
            if "timestamp" not in payload:
                from agentteam.board.utils import _now_iso

                payload["timestamp"] = _now_iso()

            _broadcast_agent_activity(payload)
            self._serve_json({"status": "ok"})

        except Exception as e:
            self.send_error(400, str(e))

    def handle_get_agent_readiness(self, agent_id: str) -> None:
        """Handle GET /api/agents/{agent_id}/readiness.

        Returns the readiness status of an agent.
        """
        if not agent_id:
            self.send_error(400, "Agent ID required")
            return

        try:
            from agentteam.readiness.manager import get_readiness_manager

            mgr = get_readiness_manager()
            readiness = mgr.get_agent_readiness(agent_id)

            self._serve_json({
                "agentId": agent_id,
                "ready": readiness.is_ready if hasattr(readiness, "is_ready") else False,
                "checks": readiness.checks if hasattr(readiness, "checks") else [],
            })

        except Exception as e:
            # Fallback: assume ready
            self._serve_json({
                "agentId": agent_id,
                "ready": True,
                "checks": [],
            })
