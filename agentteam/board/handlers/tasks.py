"""Tasks management mixin for the board handler."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentteam.board.handlers.base import BaseHandler


class TasksMixin:
    """Mixin for tasks management functionality."""

    def handle_get_tasks(self, team_name: str) -> None:
        """Handle GET /api/team/{team_name}/tasks.

        Returns tasks for a team.
        """
        if not team_name:
            self.send_error(400, "Team name required")
            return

        try:
            from agentteam.team.tasks import TaskStore

            store = TaskStore(team_name)
            tasks = store.list()

            task_list = [
                {
                    "id": t.id,
                    "subject": t.subject,
                    "description": t.description,
                    "status": t.status,
                    "owner": t.owner,
                    "createdAt": getattr(t, "created_at", ""),
                }
                for t in tasks
            ]

            self._serve_json({"tasks": task_list})

        except Exception as e:
            self.send_error(500, str(e))

    def handle_create_task(self, team_name: str) -> None:
        """Handle POST /api/team/{team_name}/task.

        Creates a new task for a team.
        """
        if not team_name:
            self.send_error(400, "Team name required")
            return

        payload = self._parse_json_body()
        if payload is None:
            return

        subject = payload.get("subject", "")
        description = payload.get("description", "")
        owner = payload.get("owner", "")

        if not subject:
            self.send_error(400, "Task subject is required")
            return

        try:
            from agentteam.team.tasks import TaskStore

            store = TaskStore(team_name)
            task = store.create(
                subject=subject,
                description=description,
                owner=owner,
            )

            self._serve_json(
                {
                    "status": "ok",
                    "task_id": task.id,
                    "task": {
                        "id": task.id,
                        "subject": task.subject,
                        "description": task.description,
                        "status": task.status,
                        "owner": task.owner,
                    },
                }
            )

        except Exception as e:
            self.send_error(400, str(e))

    def handle_update_task(self, team_name: str, task_id: str) -> None:
        """Handle PATCH /api/team/{team_name}/tasks/{task_id}.

        Updates a task.
        """
        if not team_name or not task_id:
            self.send_error(400, "Team name and task ID required")
            return

        payload = self._parse_json_body()
        if payload is None:
            return

        try:
            from agentteam.team.tasks import TaskStore

            store = TaskStore(team_name)
            task = store.get(task_id)

            if not task:
                self.send_error(404, f"Task '{task_id}' not found")
                return

            # Update fields
            if "subject" in payload:
                task.subject = payload["subject"]
            if "description" in payload:
                task.description = payload["description"]
            if "status" in payload:
                task.status = payload["status"]
            if "owner" in payload:
                task.owner = payload["owner"]

            store.save(task)

            self._serve_json(
                {
                    "status": "ok",
                    "task": {
                        "id": task.id,
                        "subject": task.subject,
                        "description": task.description,
                        "status": task.status,
                        "owner": task.owner,
                    },
                }
            )

        except Exception as e:
            self.send_error(400, str(e))

    def handle_delete_task(self, team_name: str, task_id: str) -> None:
        """Handle DELETE /api/team/{team_name}/tasks/{task_id}.

        Deletes a task.
        """
        if not team_name or not task_id:
            self.send_error(400, "Team name and task ID required")
            return

        try:
            from agentteam.team.tasks import TaskStore

            store = TaskStore(team_name)
            store.delete(task_id)

            self._serve_json({"status": "ok", "deleted": task_id})

        except Exception as e:
            self.send_error(400, str(e))

    def handle_get_all_tasks(self) -> None:
        """Handle GET /api/tasks.

        Returns all tasks from all teams.
        """
        try:
            from agentteam.team.manager import TeamManager
            from agentteam.team.tasks import TaskStore

            all_tasks = []
            teams = TeamManager.list_teams()

            for team_name in teams:
                try:
                    store = TaskStore(team_name)
                    tasks = store.list()
                    for t in tasks:
                        all_tasks.append(
                            {
                                "id": t.id,
                                "team": team_name,
                                "subject": t.subject,
                                "description": t.description,
                                "status": t.status,
                                "owner": t.owner,
                                "createdAt": getattr(t, "created_at", ""),
                            }
                        )
                except Exception:
                    pass

            self._serve_json({"tasks": all_tasks})

        except Exception as e:
            self.send_error(500, str(e))
