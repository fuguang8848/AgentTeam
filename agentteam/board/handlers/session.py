"""Session management mixin for the board handler."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentteam.board.handlers.base import BaseHandler


class SessionMixin:
    """Mixin for session management functionality."""

    def handle_get_sessions(self) -> None:
        """Handle GET /api/sessions.

        Returns all sessions from the session registry.
        """
        try:
            from agentteam.session.registry import get_session_registry

            registry = get_session_registry()
            sessions = registry.list_sessions()

            session_list = [
                {
                    "agentId": s.agent_id,
                    "name": s.name,
                    "role": s.role,
                    "status": s.status,
                    "createdAt": s.created_at,
                    "workDir": getattr(s, "work_dir", ""),
                }
                for s in sessions
            ]

            self._serve_json({"sessions": session_list})

        except Exception as e:
            self.send_error(500, str(e))

    def handle_get_session(self, session_id: str) -> None:
        """Handle GET /api/sessions/{session_id}.

        Returns details for a specific session.
        """
        if not session_id:
            self.send_error(400, "Session ID required")
            return

        try:
            from agentteam.session.registry import get_session_registry

            registry = get_session_registry()
            session = registry.get_session(session_id)

            if session:
                self._serve_json(
                    {
                        "agentId": session.agent_id,
                        "name": session.name,
                        "role": session.role,
                        "status": session.status,
                        "createdAt": session.created_at,
                        "endedAt": getattr(session, "ended_at", None),
                        "workDir": getattr(session, "work_dir", ""),
                    }
                )
            else:
                self.send_error(404, f"Session '{session_id}' not found")

        except Exception as e:
            self.send_error(500, str(e))

    def handle_get_session_state(self, session_id: str) -> None:
        """Handle GET /api/sessions/{session_id}/state.

        Returns the full state of a session including messages and context.
        """
        if not session_id:
            self.send_error(400, "Session ID required")
            return

        try:
            from agentteam.session.registry import get_session_registry

            registry = get_session_registry()
            session = registry.get_session(session_id)

            if not session:
                self.send_error(404, f"Session '{session_id}' not found")
                return

            # Build full state
            state = {
                "agentId": session.agent_id,
                "name": session.name,
                "role": session.role,
                "status": session.status,
                "createdAt": session.created_at,
                "endedAt": getattr(session, "ended_at", None),
                "workDir": getattr(session, "work_dir", ""),
                "messages": getattr(session, "messages", []),
                "context": getattr(session, "context", {}),
            }

            self._serve_json(state)

        except Exception as e:
            self.send_error(500, str(e))

    def handle_terminate_session(self, session_id: str) -> None:
        """Handle POST /api/sessions/{session_id}/terminate.

        Terminates a session.
        """
        if not session_id:
            self.send_error(400, "Session ID required")
            return

        try:
            from agentteam.session.registry import get_session_registry

            registry = get_session_registry()
            session = registry.get_session(session_id)

            if not session:
                self.send_error(404, f"Session '{session_id}' not found")
                return

            registry.terminate_session(session_id)
            self._serve_json({"status": "ok", "terminated": session_id})

        except Exception as e:
            self.send_error(500, str(e))
