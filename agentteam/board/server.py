"""
Lightweight HTTP server for the Web UI dashboard (stdlib only).

This module has been refactored for modularity:
- handlers/: HTTP API handlers
- sse/: Server-Sent Events broadcasting
- chat/: Chat and AI assistant functionality
- utils.py: Utility functions
"""

from __future__ import annotations

import ipaddress
import json
import os
import sys
import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
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
from agentteam.board.sse.broadcast import (
    _event_queue,
    _event_subscribers,
    _event_broadcaster_lock,
    _register_event_subscriber,
    _broadcast_event,
)
from agentteam.board.sse.agent_activity import (
    _agent_activity_queue,
    _agent_activity_subscribers,
    _agent_activity_lock,
    _broadcast_agent_activity,
)
from agentteam.board.chat.commands import handle_chat_command
from agentteam.board.utils import _get_collector, _now_iso, _fetch_proxy_content
from agentteam.auth import auth_manager

# Backward compatibility exports
__all__ = ["serve", "BoardHandler"]


@dataclass
class TeamSnapshotCache:
    """Simple in-memory cache for team snapshots."""

    cache: dict = field(default_factory=dict)

    def get(self, team_name: str, loader) -> dict:
        """Get or load a team snapshot."""
        if team_name not in self.cache:
            self.cache[team_name] = loader()
        return self.cache[team_name]


# Global chat event broadcaster for SSE
_chat_event_queue: deque = deque(maxlen=100)  # Last 100 events
_chat_subscribers: list = []  # List of lock objects for SSE connections
_subscriber_lock = threading.Lock()


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
):
    """HTTP handler for the board Web UI.

    This class combines all handler mixins to provide the full API surface.
    """

    collector: "BoardCollector"
    default_team: str = ""
    interval: float = 2.0
    team_cache: TeamSnapshotCache

    # Initialize the team cache
    team_cache = TeamSnapshotCache()

    # ============================================================
    # GET Handlers
    # ============================================================

    def do_GET(self):
        path = self.path.split("?")[0]

        # Check authentication for protected endpoints
        if not self.is_public_endpoint(path):
            if not self.check_auth():
                return

        # Static files
        if path == "/" or path == "/index.html":
            self.serve_static_file("index.html")
        elif path == "/chat.html":
            self.serve_static_file("chat.html")
        # Health check
        elif path == "/api/health":
            self._serve_json({"status": "ok", "timestamp": _now_iso()})
        # Overview
        elif path == "/api/overview":
            self.handle_get_overview()
        # Team endpoints
        elif path.startswith("/api/team/"):
            team_name = path[len("/api/team/") :].strip("/")
            if path.endswith("/agents"):
                team_name = path[len("/api/team/") : path.index("/agents")].strip("/")
                self.handle_get_agents(team_name)
            elif path.endswith("/tasks"):
                team_name = path[len("/api/team/") : path.index("/tasks")].strip("/")
                self.handle_get_tasks(team_name)
            else:
                self.handle_get_team(team_name)
        # Events SSE
        elif path.startswith("/api/events"):
            self._serve_events()
        # Agent activity SSE
        elif path == "/api/agents/events":
            self._serve_agent_activity_sse()
        # Proxy (disabled)
        elif path.startswith("/api/proxy"):
            self.send_error(503, "Proxy disabled for stability")
        # Transport
        elif path == "/api/transport/status":
            self.handle_get_transport_status()
        elif path == "/api/transport/stats":
            self.handle_get_transport_stats()
        # Usage
        elif path == "/api/usage/summary":
            self.handle_get_usage_summary()
        elif path == "/api/usage/trend":
            self.handle_get_usage_trend()
        elif path == "/api/usage/providers":
            self.handle_get_provider_stats()
        # Profiler
        elif path == "/api/profiler/stats":
            self.handle_get_profiler_stats()
        # Sessions
        elif path == "/api/sessions":
            self.handle_get_sessions()
        elif path.startswith("/api/sessions/"):
            session_id = path[len("/api/sessions/") :].strip("/")
            if session_id.endswith("/state"):
                session_id = session_id[:-6]
                self.handle_get_session_state(session_id)
            else:
                self.handle_get_session(session_id)
        # Agents
        elif path.startswith("/api/agents/"):
            parts = path[len("/api/agents/") :].split("/")
            if len(parts) >= 2:
                agent_id = parts[0]
                if parts[1] == "events":
                    self._serve_agent_activity_sse()
                elif parts[1] == "activity":
                    self._serve_agent_activity_sse()
                elif parts[1] == "readiness":
                    self.handle_get_agent_readiness(agent_id)
                elif parts[1] == "state":
                    self.handle_get_agent_state(agent_id)
        # Notifications
        elif path == "/api/notifications":
            self.handle_get_notifications()
        # Skills
        elif path == "/api/skills":
            self._serve_skills()
        # Chat
        elif path == "/api/chat/events":
            self._serve_chat_events()
        elif path == "/api/chat/history":
            self._serve_chat_history()
        # Tasks
        elif path == "/api/tasks":
            self.handle_get_all_tasks()
        # Concurrency
        elif path == "/api/concurrency/limits":
            self.handle_get_concurrency_limits()
        # Providers
        elif path == "/api/providers":
            self.handle_get_providers()
        # Settings
        elif path == "/api/settings":
            self.handle_get_settings()
        # Teams list
        elif path == "/api/teams":
            self.handle_list_teams()
        # Static files with path
        else:
            filename = path.lstrip("/")
            if self.serve_files(filename):
                return
            self.send_error(404)

    # ============================================================
    # POST Handlers
    # ============================================================

    def do_POST(self):
        path = self.path.split("?")[0]

        # All POST endpoints require authentication
        if not self.check_auth():
            return

        # Providers
        if path == "/api/providers":
            self.handle_save_providers()
        elif path == "/api/providers/import":
            self.handle_import_provider()
        # Agent activity
        elif path == "/api/agents/activity":
            self._emit_agent_activity()
        # Templates
        elif path == "/api/templates/import":
            self._import_template()
        # Transport switch
        elif path == "/api/transport/switch":
            self.handle_switch_transport()
        # Teams
        elif path == "/api/teams":
            self.handle_create_team()
        elif path.startswith("/api/teams/") and path.endswith("/members"):
            team_name = path[len("/api/teams/") : -len("/members")]
            self.handle_add_member(team_name)
        elif path.startswith("/api/teams/") and path.endswith("/task"):
            parts = path.strip("/").split("/")
            if len(parts) == 4 and parts[3] == "task":
                team_name = parts[2]
                self.handle_create_task(team_name)
        # Settings
        elif path == "/api/settings":
            self.handle_save_settings()
        elif path == "/api/settings/reset":
            self.handle_reset_settings()
        # Notifications
        elif path == "/api/notifications/mark-read":
            self.handle_mark_notifications_read()
        # Chat
        elif path == "/api/chat/send":
            self._serve_chat_send()
        elif path == "/api/chat/message":
            self._save_chat_message()
        # Login/Register
        elif path == "/api/login":
            self.handle_login()
        elif path == "/api/logout":
            self.handle_logout()
        elif path == "/api/register":
            self.handle_register()
        elif path == "/api/password/change":
            self.handle_change_password()
        # Clear chat
        elif path == "/api/chat/clear":
            self._clear_chat_history()
        else:
            self.send_error(404)

    # ============================================================
    # PATCH Handlers
    # ============================================================

    def do_PATCH(self):
        path = self.path.split("?")[0]

        if not self.check_auth():
            return

        # Update task
        if path.startswith("/api/team/") and "/tasks/" in path:
            parts = path.strip("/").split("/")
            # /api/team/{team_name}/tasks/{task_id}
            if len(parts) >= 5 and parts[3] == "tasks":
                team_name = parts[2]
                task_id = parts[4]
                self.handle_update_task(team_name, task_id)
                return

        # Update provider
        if path.startswith("/api/providers/"):
            provider_name = path[len("/api/providers/") :]
            self.handle_delete_provider(provider_name)
            return

        self.send_error(404)

    # ============================================================
    # DELETE Handlers
    # ============================================================

    def do_DELETE(self):
        path = self.path.split("?")[0]

        if not self.check_auth():
            return

        # Delete team
        if path.startswith("/api/teams/"):
            parts = path.strip("/").split("/")
            if len(parts) == 3 and parts[2] == "members":
                # /api/teams/{team_name}/members - not valid for DELETE
                self.send_error(400, "Member name required")
                return
            team_name = parts[2] if len(parts) >= 3 else ""
            if not team_name:
                self.send_error(400, "Team name required")
                return
            if "/members/" in path:
                # /api/teams/{team_name}/members/{member_name}
                member_name = parts[4] if len(parts) >= 5 else ""
                self.handle_remove_member(team_name, member_name)
            elif "/tasks/" in path:
                # /api/teams/{team_name}/tasks/{task_id}
                task_id = parts[4] if len(parts) >= 5 else ""
                self.handle_delete_task(team_name, task_id)
            else:
                self.handle_delete_team(team_name)
            return

        # Delete provider
        if path.startswith("/api/providers/"):
            provider_name = path[len("/api/providers/") :]
            self.handle_delete_provider(provider_name)
            return

        self.send_error(404)

    # ============================================================
    # SSE Handlers
    # ============================================================

    def _serve_events(self):
        """Serve events from the EventTracker via SSE."""
        _register_event_subscriber()

        params = parse_qs(urlparse(self.path).query)
        team = params.get("team", [None])[0]
        agent = params.get("agent", [None])[0]
        limit = int(params.get("limit", ["100"])[0])

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        # Register as subscriber
        last_event_idx = len(_event_queue)
        subscriber_lock = threading.Lock()
        subscriber_lock.acquire()

        with _event_broadcaster_lock:
            _event_subscribers.append(subscriber_lock)

        try:
            # Send initial connection message
            self.wfile.write(
                f"data: {json.dumps({'type': 'connected', 'timestamp': _now_iso()}, ensure_ascii=False)}\n\n".encode(
                    "utf-8"
                )
            )
            self.wfile.flush()

            # Send initial events from EventAPI
            try:
                from agentteam.events.api import EventAPI

                api = EventAPI()
                initial_result = api.get_events(team_name=team, agent_name=agent, limit=limit)
                for event in initial_result.get("events", []):
                    self.wfile.write(
                        f"data: {json.dumps({'type': 'event', 'data': event}, ensure_ascii=False)}\n\n".encode("utf-8")
                    )
                    self.wfile.flush()
            except Exception:
                pass

            # Stream events
            heartbeat_count = 0
            idle_cycles = 0
            active_heartbeat_interval = 10
            idle_heartbeat_interval = 30
            current_timeout = active_heartbeat_interval

            while True:
                acquired = subscriber_lock.acquire(timeout=current_timeout)
                if acquired:
                    subscriber_lock.release()

                has_new_events = False
                with _event_broadcaster_lock:
                    while len(_event_queue) > last_event_idx:
                        has_new_events = True
                        event_data = _event_queue[last_event_idx]
                        if team is None or event_data.get("team_name") == team:
                            if agent is None or event_data.get("agent_name") == agent:
                                self.wfile.write(
                                    f"data: {json.dumps({'type': 'event', 'data': event_data}, ensure_ascii=False)}\n\n".encode(
                                        "utf-8"
                                    )
                                )
                                self.wfile.flush()
                        last_event_idx += 1

                if has_new_events:
                    idle_cycles = 0
                    current_timeout = active_heartbeat_interval
                else:
                    idle_cycles += 1
                    if idle_cycles > 3:
                        current_timeout = idle_heartbeat_interval

                heartbeat_count += 1
                self.wfile.write(
                    f"data: {json.dumps({'type': 'heartbeat', 'count': heartbeat_count, 'timestamp': _now_iso()}, ensure_ascii=False)}\n\n".encode(
                        "utf-8"
                    )
                )
                self.wfile.flush()

        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            with _event_broadcaster_lock:
                if subscriber_lock in _event_subscribers:
                    _event_subscribers.remove(subscriber_lock)

    def _serve_agent_activity_sse(self):
        """Serve real-time agent activity via SSE."""
        params = parse_qs(urlparse(self.path).query)
        team = params.get("team", [None])[0]
        agent = params.get("agent", [None])[0]
        limit = int(params.get("limit", ["100"])[0])

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        last_event_idx = len(_agent_activity_queue)
        subscriber_lock = threading.Lock()
        subscriber_lock.acquire()

        with _agent_activity_lock:
            _agent_activity_subscribers.append(subscriber_lock)

        try:
            self.wfile.write(
                f"data: {json.dumps({'type': 'connected', 'timestamp': _now_iso()}, ensure_ascii=False)}\n\n".encode(
                    "utf-8"
                )
            )
            self.wfile.flush()

            # Send recent activity
            with _agent_activity_lock:
                recent = list(_agent_activity_queue)[-limit:]
            for activity in recent:
                if team is None or activity.get("team_name") == team:
                    if agent is None or activity.get("agent_name") == agent:
                        self.wfile.write(
                            f"data: {json.dumps({'type': 'activity', 'data': activity}, ensure_ascii=False)}\n\n".encode(
                                "utf-8"
                            )
                        )
                        self.wfile.flush()

            # Stream events
            heartbeat_count = 0
            while True:
                acquired = subscriber_lock.acquire(timeout=10)
                if acquired:
                    subscriber_lock.release()

                with _agent_activity_lock:
                    while len(_agent_activity_queue) > last_event_idx:
                        activity = _agent_activity_queue[last_event_idx]
                        if team is None or activity.get("team_name") == team:
                            if agent is None or activity.get("agent_name") == agent:
                                self.wfile.write(
                                    f"data: {json.dumps({'type': 'activity', 'data': activity}, ensure_ascii=False)}\n\n".encode(
                                        "utf-8"
                                    )
                                )
                                self.wfile.flush()
                        last_event_idx += 1

                heartbeat_count += 1
                self.wfile.write(
                    f"data: {json.dumps({'type': 'heartbeat', 'count': heartbeat_count}, ensure_ascii=False)}\n\n".encode(
                        "utf-8"
                    )
                )
                self.wfile.flush()

        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            with _agent_activity_lock:
                if subscriber_lock in _agent_activity_subscribers:
                    _agent_activity_subscribers.remove(subscriber_lock)

    def _emit_agent_activity(self) -> bool:
        """Emit an agent activity event."""
        payload = self._parse_json_body()
        if payload is None:
            return False

        try:
            if "timestamp" not in payload:
                payload["timestamp"] = _now_iso()
            _broadcast_agent_activity(payload)
            self._serve_json({"status": "ok"})
            return True
        except Exception as e:
            self.send_error(400, str(e))
            return False

    # ============================================================
    # Chat Handlers
    # ============================================================

    def _serve_skills(self):
        """Serve the list of available skills."""
        try:
            from agentteam.skills.manager import get_skill_manager

            mgr = get_skill_manager()
            skills = mgr.list_skills()

            self._serve_json({"skills": skills})

        except Exception as e:
            self._serve_json({"skills": [], "error": str(e)})

    def _serve_chat_events(self):
        """Serve chat events via SSE."""
        params = parse_qs(urlparse(self.path).query)
        team = params.get("team", [None])[0]

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        last_idx = len(_chat_event_queue)
        subscriber_lock = threading.Lock()
        subscriber_lock.acquire()

        with _subscriber_lock:
            _chat_subscribers.append(subscriber_lock)

        try:
            self.wfile.write(
                f"data: {json.dumps({'type': 'connected', 'timestamp': _now_iso()}, ensure_ascii=False)}\n\n".encode(
                    "utf-8"
                )
            )
            self.wfile.flush()

            # Send recent events
            with _subscriber_lock:
                recent = list(_chat_event_queue)[-50:]
            for event in recent:
                self.wfile.write(
                    f"data: {json.dumps({'type': 'chat_event', 'data': event}, ensure_ascii=False)}\n\n".encode("utf-8")
                )
                self.wfile.flush()

            # Stream events
            while True:
                acquired = subscriber_lock.acquire(timeout=10)
                if acquired:
                    subscriber_lock.release()

                with _subscriber_lock:
                    while len(_chat_event_queue) > last_idx:
                        event = _chat_event_queue[last_idx]
                        self.wfile.write(
                            f"data: {json.dumps({'type': 'chat_event', 'data': event}, ensure_ascii=False)}\n\n".encode(
                                "utf-8"
                            )
                        )
                        self.wfile.flush()
                        last_idx += 1

                self.wfile.write(
                    f"data: {json.dumps({'type': 'heartbeat'}, ensure_ascii=False)}\n\n".encode("utf-8")
                )
                self.wfile.flush()

        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            with _subscriber_lock:
                if subscriber_lock in _chat_subscribers:
                    _chat_subscribers.remove(subscriber_lock)

    def _serve_chat_history(self):
        """Serve chat history."""
        try:
            params = parse_qs(urlparse(self.path).query)
            team = params.get("team", [None])[0]
            limit = int(params.get("limit", ["100"])[0])

            with _subscriber_lock:
                history = list(_chat_event_queue)[-limit:]

            self._serve_json({"messages": history})

        except Exception as e:
            self._serve_json({"messages": [], "error": str(e)})

    def _serve_chat_send(self):
        """Handle chat message send."""
        payload = self._parse_json_body()
        if payload is None:
            return

        message = payload.get("message", "")
        user = payload.get("user", "User")
        team = payload.get("team")

        if not message:
            self.send_error(400, "Message required")
            return

        # Handle command
        response = handle_chat_command(message, user)

        # Broadcast if not a clear command
        if response.get("content") != "CLEAR_CHAT_HISTORY":
            event = {
                "type": "message",
                "role": response.get("role", "assistant"),
                "content": response.get("content", ""),
                "timestamp": response.get("timestamp", _now_iso()),
                "user": user,
                "assistant": response.get("assistant"),
            }
            _chat_event_queue.append(event)

            # Notify subscribers
            with _subscriber_lock:
                for lock in _chat_subscribers[:]:
                    try:
                        lock.release()
                    except RuntimeError:
                        pass

        self._serve_json(response)

    def _save_chat_message(self):
        """Save a chat message."""
        payload = self._parse_json_body()
        if payload is None:
            return

        event = {
            "type": "message",
            "role": payload.get("role", "user"),
            "content": payload.get("content", ""),
            "timestamp": payload.get("timestamp", _now_iso()),
            "user": payload.get("user", "User"),
        }

        _chat_event_queue.append(event)

        # Notify subscribers
        with _subscriber_lock:
            for lock in _chat_subscribers[:]:
                try:
                    lock.release()
                except RuntimeError:
                    pass

        self._serve_json({"status": "ok"})

    def _clear_chat_history(self):
        """Clear chat history."""
        global _chat_event_queue
        _chat_event_queue = deque(maxlen=100)
        self._serve_json({"status": "ok", "cleared": True})

    def _import_template(self):
        """Import a template from TOML content."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")

        try:
            try:
                import tomllib
            except ImportError:
                import tomli as tomllib

            tmpl_data = tomllib.loads(body)
            tmpl = tmpl_data.get("template", tmpl_data)
            template_name = tmpl.get("name", "")

            if not template_name:
                self.send_error(400, "Template name is required")
                return

            # Save to user templates directory
            from pathlib import Path

            user_dir = Path.home() / ".agentteam" / "templates"
            user_dir.mkdir(parents=True, exist_ok=True)

            toml_path = user_dir / f"{template_name}.toml"
            try:
                import tomllib

                toml_str = tomllib.dumps({"template": tmpl})
            except ImportError:
                import tomli as tomli

                toml_str = tomli.dumps({"template": tmpl})

            with open(toml_path, "w", encoding="utf-8") as f:
                f.write(toml_str)

            self._serve_json({"success": True, "template": template_name, "path": str(toml_path)})

        except Exception as e:
            self.send_error(400, f"Failed to import template: {e}")

    # ============================================================
    # Utility Methods
    # ============================================================

    def log_message(self, format: str, *args):
        """Log an HTTP request."""
        print(f"[Board] {self.address_string()} - {format % args}")


# ============================================================
# Server Entry Point
# ============================================================


def serve(
    host: str = "0.0.0.0",
    port: int = 8080,
    interval: float = 2.0,
    default_team: str = "",
) -> None:
    """Start the board HTTP server.

    Args:
        host: Host to bind to
        port: Port to listen on
        interval: Refresh interval in seconds
        default_team: Default team name
    """
    # Validate host
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass  # Allow hostnames

    # Create handler class with settings
    class ConfiguredHandler(BoardHandler):
        pass

    ConfiguredHandler.interval = interval
    ConfiguredHandler.default_team = default_team
    ConfiguredHandler.collector = _get_collector()

    # Create server
    server = ThreadingHTTPServer((host, port), ConfiguredHandler)

    print(f"Starting AgentTeam Board on {host}:{port}")
    print(f"Open http://localhost:{port} in your browser")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AgentTeam Board Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    parser.add_argument("--interval", type=float, default=2.0, help="Refresh interval in seconds")
    parser.add_argument("--team", default="", help="Default team name")

    args = parser.parse_args()
    serve(args.host, args.port, args.interval, args.team)
