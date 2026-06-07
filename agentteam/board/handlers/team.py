"""Team management mixin for the board handler."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from agentteam.board.handlers.base import BaseHandler


class TeamMixin:
    """Mixin for team management functionality."""

    def handle_get_team(self, team_name: str) -> None:
        """Handle GET /api/team/{team_name}.

        Returns team information and overview.
        """
        if not team_name:
            self.send_error(400, "Team name required")
            return

        try:
            from agentteam.board.utils import _get_collector

            collector = _get_collector()
            team_data = collector.collect_team(team_name)
            if team_data:
                self._serve_json(team_data)
            else:
                self.send_error(404, f"Team '{team_name}' not found")
        except Exception as e:
            self.send_error(500, str(e))

    def handle_create_team(self) -> None:
        """Handle POST /api/teams.

        Creates a new team.
        """
        payload = self._parse_json_body()
        if payload is None:
            return

        team_name = payload.get("name", "").strip()
        description = payload.get("description", "")
        template_name = payload.get("template", "")

        if not team_name:
            self.send_error(400, "Team name is required")
            return

        try:
            from agentteam.team.manager import TeamManager

            # Check if team already exists
            existing = TeamManager.get_team(team_name)
            if existing:
                self.send_error(400, f"Team '{team_name}' already exists")
                return

            # Load template if specified
            leader_name = "leader"
            leader_id = payload.get("leadAgentId", "agent")
            agents_data = []
            tasks_data = []

            if template_name:
                try:
                    from agentteam.templates import load_template

                    tmpl = load_template(template_name)
                    leader_name = tmpl.leader.name
                    description = description or tmpl.description
                    agents_data = [{"name": a.name, "type": a.type, "task": a.task} for a in tmpl.agents]
                    tasks_data = [
                        {"subject": t.subject, "description": t.description} for t in getattr(tmpl, "tasks", [])
                    ]
                except Exception:
                    pass

            # Create the team
            team = TeamManager.create_team(
                name=team_name,
                description=description,
                leader_name=leader_name,
                leader_id=leader_id,
            )

            # Add agents if specified
            for agent_data in agents_data:
                TeamManager.add_member(
                    team_name=team_name,
                    name=agent_data["name"],
                    agent_type=agent_data["type"],
                    task=agent_data.get("task"),
                )

            self._serve_json(
                {
                    "status": "ok",
                    "team": team_name,
                    "description": description,
                    "member_count": len(agents_data) + 1,
                    "template": template_name,
                }
            )

        except Exception as e:
            self.send_error(400, str(e))

    def handle_delete_team(self, team_name: str) -> None:
        """Handle DELETE /api/teams/{team_name}.

        Deletes a team.
        """
        if not team_name:
            self.send_error(400, "Team name required")
            return

        try:
            from agentteam.team.manager import TeamManager

            existing = TeamManager.get_team(team_name)
            if not existing:
                self.send_error(404, f"Team '{team_name}' not found")
                return

            TeamManager.delete_team(team_name)
            self._serve_json({"status": "ok", "deleted": team_name})

        except Exception as e:
            self.send_error(400, str(e))

    def handle_add_member(self, team_name: str) -> None:
        """Handle POST /api/teams/{team_name}/members.

        Adds a member to a team.
        """
        payload = self._parse_json_body()
        if payload is None:
            return

        member_name = payload.get("name", "").strip()
        agent_type = payload.get("agentType", "general-purpose")
        task = payload.get("task", "")

        if not member_name:
            self.send_error(400, "Member name is required")
            return

        try:
            from agentteam.team.manager import TeamManager

            existing = TeamManager.get_team(team_name)
            if not existing:
                self.send_error(404, f"Team '{team_name}' not found")
                return

            new_member = TeamManager.add_member(
                team_name=team_name,
                name=member_name,
                agent_type=agent_type,
                task=task,
            )

            self._serve_json(
                {
                    "success": True,
                    "member": {
                        "name": new_member.name,
                        "agentId": new_member.agent_id,
                        "agentType": new_member.agent_type,
                    },
                }
            )

        except Exception as e:
            self.send_error(400, str(e))

    def handle_remove_member(self, team_name: str, member_name: str) -> None:
        """Handle DELETE /api/teams/{team_name}/members/{member_name}.

        Removes a member from a team.
        """
        if not team_name or not member_name:
            self.send_error(400, "Team name and member name required")
            return

        try:
            from agentteam.team.manager import TeamManager

            config = TeamManager.get_team(team_name)
            if not config:
                self.send_error(404, f"Team '{team_name}' not found")
                return

            # Check if member exists
            member_found = None
            for m in config.members:
                if m.name == member_name:
                    member_found = m
                    break

            if not member_found:
                self.send_error(404, f"Member '{member_name}' not found")
                return

            # Cannot remove the leader
            if member_found.agent_id == config.lead_agent_id:
                self.send_error(400, "Cannot remove the team leader")
                return

            TeamManager.remove_member(team_name, member_name)
            self._serve_json({"status": "ok", "removed": member_name})

        except Exception as e:
            self.send_error(400, str(e))

    def handle_list_teams(self) -> None:
        """Handle GET /api/teams.

        Lists all teams.
        """
        try:
            from agentteam.team.manager import TeamManager

            teams = TeamManager.list_teams()
            self._serve_json({"teams": teams})

        except Exception as e:
            self.send_error(500, str(e))
