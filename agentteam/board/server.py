"""Lightweight HTTP server for the Web UI dashboard (stdlib only)."""

from __future__ import annotations

from agentteam.board.utils import _fetch_proxy_content, _normalize_proxy_target

import ipaddress
import json
import threading
from collections import deque
from http.server import ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

# Import from modular components
from agentteam.board.handlers.base import BaseHandler
from agentteam.board.handlers.auth import AuthMixin
from agentteam.board.handlers.static import StaticMixin
from agentteam.board.handlers.team import TeamMixin
from agentteam.board.handlers.agent import AgentMixin
from agentteam.board.handlers.session import SessionMixin
from agentteam.board.handlers.settings import SettingsMixin
from agentteam.board.handlers.transport import TransportMixin
from agentteam.board.handlers.notifications import NotificationsMixin
from agentteam.board.handlers.providers import ProvidersMixin
from agentteam.board.handlers.tasks import TasksMixin
from agentteam.board.handlers.overview import OverviewMixin
from agentteam.board.handlers.sse import SSEHandlersMixin
from agentteam.board.handlers.chat import ChatHandlersMixin
from agentteam.board.utils import _get_collector, _now_iso, _generate_simple_response

__all__ = ["serve", "BoardHandler"]


class BoardHandler(
    BaseHandler,
    AuthMixin,
    StaticMixin,
    TeamMixin,
    AgentMixin,
    SessionMixin,
    SettingsMixin,
    TransportMixin,
    NotificationsMixin,
    ProvidersMixin,
    TasksMixin,
    OverviewMixin,
    SSEHandlersMixin,
    ChatHandlersMixin,
):
    """HTTP handler combining all handler mixins."""

    collector = None
    default_team = ""
    interval = 2.0
    team_cache = {}

    # ==================== GET ====================
    def do_GET(self):
        path = self.path.split("?")[0]
        if not self.is_public_endpoint(path) and not self.check_auth():
            return

        if path in ("/", "/index.html"):
            return self.serve_static_file("index.html")
        elif path == "/chat.html":
            return self.serve_static_file("chat.html")
        elif path == "/api/health":
            return self._serve_json({"status": "ok", "timestamp": _now_iso()})
        elif path == "/api/overview":
            return self.handle_get_overview()
        elif path.startswith("/api/team/"):
            return self._route_team_get(path)
        elif path.startswith("/api/events"):
            return self._sse_events()
        elif path in ("/api/agents/events", "/api/agents/activity"):
            return self._sse_activity()
        elif path == "/api/transport/status":
            return self.handle_get_transport_status()
        elif path == "/api/transport/stats":
            return self.handle_get_transport_stats()
        elif path == "/api/usage/summary":
            return self.handle_get_usage_summary()
        elif path == "/api/usage/trend":
            return self.handle_get_usage_trend()
        elif path == "/api/usage/providers":
            return self.handle_get_provider_stats()
        elif path == "/api/profiler/stats":
            return self.handle_get_profiler_stats()
        elif path == "/api/sessions":
            return self.handle_get_sessions()
        elif path.startswith("/api/sessions/"):
            return self._route_session_get(path)
        elif path.startswith("/api/agents/"):
            return self._route_agent_get(path)
        elif path == "/api/notifications":
            return self.handle_get_notifications()
        elif path == "/api/skills":
            return self._serve_skills()
        elif path == "/api/chat/events":
            return self._sse_chat()
        elif path == "/api/chat/history":
            return self._serve_chat_history()
        elif path == "/api/tasks":
            return self.handle_get_all_tasks()
        elif path == "/api/concurrency/limits":
            return self.handle_get_concurrency_limits()
        elif path == "/api/providers":
            return self.handle_get_providers()
        elif path == "/api/settings":
            return self.handle_get_settings()
        elif path == "/api/teams":
            return self.handle_list_teams()
        elif not self.serve_files(path.lstrip("/")):
            self.send_error(404)

    def _route_team_get(self, path):
        r = path[len("/api/team/") :].strip("/")
        if not r:
            return self.send_error(400, "Team name required")
        if r.endswith("/agents"):
            return self.handle_get_agents(r[:-7].strip("/"))
        if r.endswith("/tasks"):
            return self.handle_get_tasks(r[:-6].strip("/"))
        return self.handle_get_team(r)

    def _route_session_get(self, path):
        sid = path[len("/api/sessions/") :].strip("/")
        return self.handle_get_session_state(sid[:-6]) if sid.endswith("/state") else self.handle_get_session(sid)

    def _route_agent_get(self, path):
        parts = path[len("/api/agents/") :].split("/")
        if len(parts) < 2:
            return self.send_error(400, "Invalid path")
        aid, action = parts[0], parts[1]
        return (
            self.handle_get_agent_readiness(aid)
            if action == "readiness"
            else self.handle_get_agent_state(aid)
            if action == "state"
            else self.send_error(404)
        )

    # ==================== POST ====================
    def do_POST(self):
        path = self.path.split("?")[0]
        if not self.check_auth():
            return
        routes = {
            "/api/providers": self.handle_save_providers,
            "/api/providers/import": self.handle_import_provider,
            "/api/agents/activity": self._emit_activity,
            "/api/templates/import": self._import_tmpl,
            "/api/transport/switch": self.handle_switch_transport,
            "/api/teams": self.handle_create_team,
            "/api/settings": self.handle_save_settings,
            "/api/settings/reset": self.handle_reset_settings,
            "/api/notifications/mark-read": self.handle_mark_notifications_read,
            "/api/chat/send": self._chat_send,
            "/api/chat/message": self._chat_save,
            "/api/chat/clear": self._chat_clear,
            "/api/login": self.handle_login,
            "/api/logout": self.handle_logout,
            "/api/register": self.handle_register,
            "/api/password/change": self.handle_change_password,
        }
        if path in routes:
            return routes[path]()
        if "/api/teams/" in path and "/members" in path:
            return self.handle_add_member(path.split("/api/teams/")[1].split("/members")[0])
        if path.startswith("/api/teams/") and path.endswith("/task"):
            return self.handle_create_task(path.split("/api/teams/")[1].split("/task")[0])
        self.send_error(404)

    # ==================== PATCH ====================
    def do_PATCH(self):
        path = self.path.split("?")[0]
        if not self.check_auth():
            return
        if path.startswith("/api/team/") and "/tasks/" in path:
            parts = path.strip("/").split("/")
            if len(parts) >= 5 and parts[3] == "tasks":
                return self.handle_update_task(parts[2], parts[4])
        if path.startswith("/api/providers/"):
            return self.handle_delete_provider(path[len("/api/providers/") :])
        self.send_error(404)

    # ==================== DELETE ====================
    def do_DELETE(self):
        path = self.path.split("?")[0]
        if not self.check_auth():
            return
        if path.startswith("/api/teams/"):
            parts = path.strip("/").split("/")
            tn = parts[2] if len(parts) >= 3 else ""
            if not tn:
                return self.send_error(400, "Team name required")
            if "/members/" in path:
                return self.handle_remove_member(tn, parts[4] if len(parts) >= 5 else "")
            if "/tasks/" in path:
                return self.handle_delete_task(tn, parts[4] if len(parts) >= 5 else "")
            return self.handle_delete_team(tn)
        if path.startswith("/api/providers/"):
            return self.handle_delete_provider(path[len("/api/providers/") :])
        self.send_error(404)

    def log_message(self, format, *args):
        print(f"[Board] {self.address_string()} - {format % args}")


def serve(host="0.0.0.0", port=8080, interval=2.0, default_team=""):
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass

    class H(BoardHandler):
        pass

    H.interval, H.default_team, H.collector = interval, default_team, _get_collector()
    ThreadingHTTPServer((host, port), H).serve_forever()


# Backward compatibility alias: board.py CLI expects run_server, actual function is serve.
# This alias ensures CLI commands work without depending on internal implementation naming.
run_server = serve


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="AgentTeam Board")
    p.add_argument("--host", default="0.0.0.0").add_argument("--port", type=int, default=8080)
    p.add_argument("--interval", type=float, default=2.0).add_argument("--team", default="")
    args = p.parse_args()
    serve(args.host, args.port, args.interval, args.team)
