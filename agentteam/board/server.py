"""Lightweight HTTP server for the Web UI dashboard (stdlib only)."""

from __future__ import annotations

import ipaddress
import json
import threading
import time
import urllib.error
import urllib.request
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from agentteam.board.collector import BoardCollector
from agentteam.auth import auth_manager, AuthManager

# Thread-safe chat event broadcaster for SSE
_chat_event_queue = deque(maxlen=100)  # Last 100 events
_chat_subscribers = []  # List of lock objects for SSE connections
_subscriber_lock = threading.Lock()

# Thread-safe event broadcaster for SSE (P37: EventAPI integration)
_event_queue = deque(maxlen=500)  # Last 500 events
_event_subscribers = []  # List of queue indices for SSE connections
_event_broadcaster_lock = threading.Lock()

# Thread-safe agent activity broadcaster for SSE (real-time agent monitoring)
_agent_activity_queue = deque(maxlen=1000)  # Last 1000 activity events
_agent_activity_subscribers = []  # List of queue indices for SSE connections
_agent_activity_lock = threading.Lock()

_STATIC_DIR = Path(__file__).parent / "static"
_ALLOWED_PROXY_HOSTS = {
    "api.github.com",
    "github.com",
    "raw.githubusercontent.com",
}

# Lazy-loaded collector - created on first request
_collector = None


def _get_collector():
    """Lazily create BoardCollector on first access to avoid heavy import at startup."""
    global _collector
    if _collector is None:
        from agentteam.board.collector import BoardCollector

        _collector = BoardCollector()
        BoardHandler.collector = _collector
    return _collector


# P37: EventAPI integration - register board as event subscriber
_event_subscriber_registered = False


def _register_event_subscriber():
    """Register the board's event broadcaster with EventTracker (P37)."""
    global _event_subscriber_registered
    if _event_subscriber_registered:
        return

    try:
        from agentteam.events.tracker import add_event_subscriber

        def board_event_callback(event):
            """Callback to broadcast events to board SSE subscribers."""
            # Convert event to dict for JSON serialization
            event_dict = event.to_dict() if hasattr(event, "to_dict") else dict(event)
            BoardHandler._broadcast_event(event_dict)

        add_event_subscriber(board_event_callback)
        _event_subscriber_registered = True
    except Exception as e:
        print(f"Failed to register event subscriber: {e}")


def _now_iso() -> str:
    """Return current time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def _generate_simple_response(message: str) -> str:
    """Generate a simple rule-based response when AI is unavailable."""
    msg_lower = message.lower()

    # Greetings
    greetings = ["你好", "hi", "hello", "嗨", "您好", "hey"]
    if any(g in msg_lower for g in greetings):
        return "你好！我是 AgentTeam AI 助手。很高兴为你服务！有什么我可以帮助你的吗？"

    # Help requests
    if "帮助" in message or "help" in msg_lower or "怎么" in message:
        return "我可以帮你管理团队、创建任务、分析数据等。你可以试试：\\n1. 创建新团队 \\n2. 查看任务状态 \\n3. 使用 AI 助手聊天"

    # Team related
    if "团队" in message or "team" in msg_lower:
        return "要创建团队，可以使用「新建团队」按钮。我可以帮你设置团队模板、分配成员、跟踪进度等。"

    # Task related
    if "任务" in message or "task" in msg_lower:
        return "任务管理是我的强项！你可以：\\n1. 在看板视图中拖拽任务 \\n2. 分配负责人 \\n3. 设置优先级"

    # Questions about AgentTeam
    if "什么是" in message or "what is" in msg_lower:
        return "AgentTeam 是一个多智能体团队协作平台。你可以创建多个 AI 助手组成的团队，协同完成复杂任务。"

    # Default response
    responses = [
        "收到！你的消息我已经理解了。有什么具体需要我帮忙的吗？",
        "好的，我明白了。请告诉我你需要什么帮助。",
        "我理解了。如果你需要创建团队、管理任务或使用 AI 助手，随时告诉我。",
    ]
    import random

    return random.choice(responses)


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects for proxied fetches."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(newurl, code, msg, headers, fp)


def _is_blocked_hostname(hostname: str) -> bool:
    host = hostname.strip().lower()
    if host in {"localhost"}:
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_multicast or ip.is_reserved


def _normalize_proxy_target(target_url: str) -> str:
    parsed = urlparse(target_url)
    if parsed.scheme != "https":
        raise ValueError("Proxy only allows https URLs")

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise ValueError("Proxy URL must include a hostname")
    if _is_blocked_hostname(hostname):
        raise ValueError("Proxy target is not allowed")

    if hostname == "github.com":
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) == 2:
            return f"https://api.github.com/repos/{parts[0]}/{parts[1]}/readme"
        return target_url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")

    if hostname not in _ALLOWED_PROXY_HOSTS:
        raise ValueError("Proxy only allows GitHub-hosted content")

    return target_url


def _fetch_proxy_content(target_url: str) -> bytes:
    normalized = _normalize_proxy_target(target_url)
    opener = urllib.request.build_opener(_NoRedirectHandler)
    req = urllib.request.Request(normalized, headers={"User-Agent": "AgentTeam-Server"})
    with opener.open(req, timeout=10) as resp:
        final_url = resp.geturl()
        _normalize_proxy_target(final_url)
        body = resp.read()

    if normalized.startswith("https://api.github.com/repos/") and final_url == normalized:
        payload = json.loads(body.decode("utf-8"))
        download_url = payload.get("download_url")
        if not download_url:
            raise ValueError("GitHub README proxy target has no downloadable content")
        normalized = _normalize_proxy_target(download_url)
        req = urllib.request.Request(normalized, headers={"User-Agent": "AgentTeam-Server"})
        with opener.open(req, timeout=10) as resp:
            _normalize_proxy_target(resp.geturl())
            return resp.read()

    return body


@dataclass
class TeamSnapshotCache:
    """Tiny TTL cache for full team snapshots shared across HTTP handlers."""

    ttl_seconds: float
    _entries: dict[str, tuple[float, dict]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def get(self, team_name: str, loader) -> dict:
        with self._lock:
            entry = self._entries.get(team_name)
            if entry and time.monotonic() - entry[0] < self.ttl_seconds:
                return entry[1]

        # Load outside the lock so one slow collector run does not block all
        # other readers. Concurrent expiry can trigger duplicate refreshes, but
        # this path only rebuilds an in-memory snapshot and the latest result wins.
        data = loader()
        loaded_at = time.monotonic()
        with self._lock:
            self._entries[team_name] = (loaded_at, data)
        return data


class BoardHandler(BaseHTTPRequestHandler):
    """HTTP handler for the board Web UI.

    ## Route Organization (grouped by resource)

    ### Authentication
    - _check_auth()         — verify API key / Bearer token
    - _is_public_endpoint() — public path check

    ### Static / Files
    - _serve_static()       — static file serving (HTML, JS, CSS, images, fonts)
    - _serve_files()        — workspace file listing

    ### JSON Helpers
    - _serve_json()         — JSON response wrapper

    ### Team / Task (team/ subtree)
    - _serve_team()        — /api/team/<name>
    - _serve_team_alerts()  — /api/teams/<name>/alerts
    - _serve_db_tasks()    — /api/db/tasks

    ### Agents (agents/ subtree)
    - _serve_agent_activity_sse()  — GET /api/agents/events (SSE)
    - _emit_agent_activity()       — POST /api/agents/activity

    ### Events (events/ subtree)
    - _serve_events()       — /api/events/ (P37)

    ### Sessions (sessions/ subtree)
    - _serve_sessions()     — /api/sessions
    - _serve_session()      — /api/sessions/<id>
    - _serve_session_state() — /api/state/<id> (disabled)

    ### Transport (transport/ subtree)
    - _serve_transport_status() — /api/transport/status
    - _serve_transport_stats()  — /api/transport/stats

    ### Usage / Metrics (usage/ subtree)
    - _serve_usage_summary()  — /api/usage/summary
    - _serve_usage_trend()    — /api/usage/trend
    - _serve_provider_stats() — /api/usage/providers

    ### Providers / Settings (config/ subtree)
    - _serve_providers()      — /api/providers (GET/POST)
    - _delete_provider()       — DELETE /api/providers/<name>
    - _serve_settings()        — /api/settings
    - _serve_concurrency_limits() — /api/concurrency/limits
    - _get_providers_file() / _load_providers() / _save_providers() — file I/O

    ### Skills / Notifications
    - _serve_skills()        — /api/skills
    - _serve_notifications()  — /api/notifications
    - _mark_notifications_read() — POST /api/notifications/mark-read

    ### Chat
    - _poll_chat_events()    — /api/chat/events (polling)
    - _serve_chat_events()   — /api/chat/events (legacy SSE)
    - _serve_chat_history()  — /api/chat/history
    - _clear_chat_history()  — internal
    - _save_chat_message()   — internal
    - _broadcast_chat_event() — internal
    - _handle_chat_command()  — /chat command processing
    - _call_ai_assistant()   — AI assistant invocation

    ### Templates
    - _serve_templates()     — /api/templates (import/export via list_templates)

    ### Health / Profiler
    - _serve_profiler_stats() — /api/profiler/stats
    - _serve_agent_readiness() — /api/readiness/agent/<id> (disabled)

    ### SSE Helpers (class methods, called from callbacks)
    - _broadcast_event()      — broadcast event to SSE subscribers
    - _broadcast_chat_event() — broadcast chat event to SSE subscribers

    ### Lifecycle
    - log_message() — quiet request logging

    ## Global State (module-level)
    - _collector         — lazy BoardCollector singleton
    - _event_queue       — last 500 events (SSE)
    - _agent_activity_queue — last 1000 agent activity events (SSE)
    - _chat_event_queue  — last 100 chat events (SSE)
    """

    collector: BoardCollector
    default_team: str = ""
    interval: float = 2.0
    team_cache: TeamSnapshotCache

    # Public endpoints that don't require authentication
    _PUBLIC_ENDPOINTS = frozenset(["/", "/index.html", "/chat.html", "/api/health"])

    def _check_auth(self) -> bool:
        """
        Check authentication for the current request.

        Returns True if the request is authenticated or auth is not required.
        Returns False and sends 401 error if authentication fails.
        """
        # Check if auth is required
        if not auth_manager.is_auth_required():
            return True

        # Check for API key in X-API-Key header
        api_key = self.headers.get("X-API-Key", "")
        if api_key and auth_manager.verify_api_key(api_key):
            return True

        # Check for Bearer token in Authorization header
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            payload = auth_manager.verify_token(token)
            if payload and not payload.is_expired():
                return True

        # Authentication failed - send 401
        self.send_error(401, "Unauthorized")
        return False

    def _is_public_endpoint(self, path: str) -> bool:
        """Check if the path is a public endpoint that doesn't require auth."""
        if path in self._PUBLIC_ENDPOINTS:
            return True
        # Static files are public
        if not path.startswith("/api/"):
            return True
        return False

    def do_GET(self):
        path = self.path.split("?")[0]

        # Check authentication for protected endpoints
        if not self._is_public_endpoint(path):
            if not self._check_auth():
                return

        if path == "/" or path == "/index.html":
            self._serve_static("index.html", "text/html")
        elif path == "/api/health" or path == "/health":
            # Health check endpoint - always available even when collector is not initialized
            # V 6/7 10:35 fix: 加 /health alias, 报告说 /health 返 404, 实际 /api/health HTTP 200.
            self._serve_json({"status": "ok", "timestamp": _now_iso(), "service": "agentteam-board"})
        elif path == "/api/overview":
            # Use lazy-loaded collector
            self._serve_json({"teams": _get_collector().collect_overview()})
        elif path.startswith("/api/team/"):
            team_name = path[len("/api/team/") :].strip("/")
            if not team_name:
                self.send_error(400, "Team name required")
                return
            self._serve_team(team_name)
        elif path.startswith("/api/events/"):
            # P37: Wire up EventTracker to board API
            # Supports GET /api/events/ and /api/events/?team=<team>&limit=100
            self._serve_events()
        elif path == "/api/agents/events":
            # Real-time agent activity stream (SSE)
            # GET /api/agents/events?team=<team>&agent=<agent>
            self._serve_agent_activity_sse()
        elif path.startswith("/api/proxy"):
            # Proxy disabled for stability - security and resource concerns
            self.send_error(503, "Proxy disabled for stability")
            query = parse_qs(urlparse(self.path).query)
            target_url = query.get("url", [""])[0]
            if not target_url:
                self.send_error(400, "URL required")
                return
            try:
                content = _fetch_proxy_content(target_url)
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(content)
            except ValueError as e:
                self.send_error(403, str(e))
            except Exception as e:
                self.send_error(500, str(e))
        elif path == "/api/transport/status":
            # Transport status endpoint
            self._serve_transport_status()
        elif path == "/api/transport/stats":
            # Transport statistics endpoint
            self._serve_transport_stats()
        elif path == "/api/usage/summary":
            # Token usage summary endpoint
            self._serve_usage_summary()
        elif path == "/api/usage/trend":
            # Token usage trend endpoint
            self._serve_usage_trend()
        elif path == "/api/usage/providers":
            # Provider usage stats endpoint
            self._serve_provider_stats()
        elif path == "/api/profiler/stats":
            # Performance profiler stats endpoint
            self._serve_profiler_stats()
        elif path == "/api/sessions":
            # Session registry endpoint
            self._serve_sessions()
        elif path.startswith("/api/sessions/"):
            # Single session endpoint
            session_id = path[len("/api/sessions/") :].strip("/")
            self._serve_session(session_id)
        elif path.startswith("/api/teams/") and path.endswith("/alerts"):
            # Team alerts endpoint
            parts = path.strip("/").split("/")
            if len(parts) == 3 and parts[2] == "alerts":
                team_name = parts[1]
                self._serve_team_alerts(team_name)
        elif path == "/api/skills":
            # Skills list endpoint
            self._serve_skills()
        elif path == "/api/notifications":
            # Notifications endpoint
            self._serve_notifications()
        elif path == "/api/notifications/mark-read":
            # Mark all notifications as read
            self._mark_notifications_read()
        elif path == "/api/providers":
            # Providers configuration
            self._serve_providers()
        elif path == "/api/settings":
            # Settings configuration
            self._serve_settings()
        elif path.startswith("/api/providers/"):
            # Delete specific provider: /api/providers/{name}
            provider_name = path.split("/")[-1]
            self._delete_provider(provider_name)
        elif path == "/api/concurrency/limits":
            # Concurrency limits endpoint
            self._serve_concurrency_limits()
        elif path.startswith("/api/transport/switch"):
            # Transport switch endpoint (POST only, but handle GET for info)
            self._serve_json({"error": "Use POST to switch transport"})
        elif path == "/api/chat/events":
            # Chat events - polling based (replaces SSE for stability)
            self._poll_chat_events()
        elif path == "/api/chat/history":
            # Chat history endpoint
            self._serve_chat_history()
        elif path == "/chat.html":
            # Serve chat page
            self._serve_static("chat.html", "text/html")
        elif path == "/api/db/tasks":
            # Task statistics endpoint (SpectrAI feature)
            self._serve_db_tasks()
        elif path.startswith("/api/readiness/agent/"):
            # Agent readiness endpoint - disabled for stability
            self.send_error(503, "Readiness check disabled for stability")
        elif path.startswith("/api/state/"):
            # State inference endpoint - disabled for stability
            self.send_error(503, "State inference disabled for stability")
        elif path == "/api/files":
            # File listing endpoint for workspace
            self._serve_files()
        elif path == "/api/templates":
            # List all templates
            from agentteam.templates import list_templates

            templates = list_templates()
            self._serve_json({"templates": templates})
        elif path.startswith("/api/templates/") and path.endswith("/export"):
            # Export a specific template as TOML
            template_name = path[len("/api/templates/") : -len("/export")]
            if not template_name:
                self.send_error(400, "Template name required")
                return
            try:
                from agentteam.templates import load_template

                tmpl = load_template(template_name)
                # Convert to TOML string
                import tomllib

                tmpl_dict = {
                    "template": {
                        "name": tmpl.name,
                        "description": tmpl.description,
                        "command": tmpl.command,
                        "backend": tmpl.backend,
                        "leader": tmpl.leader.model_dump() if hasattr(tmpl.leader, "model_dump") else dict(tmpl.leader),
                        "agents": [a.model_dump() if hasattr(a, "model_dump") else dict(a) for a in tmpl.agents],
                        "tasks": [t.model_dump() if hasattr(t, "model_dump") else dict(t) for t in tmpl.tasks],
                    }
                }
                # Use tomllib.dumps if available (Python 3.11+)
                if hasattr(tomllib, "dumps"):
                    toml_str = tomllib.dumps(tmpl_dict)
                else:
                    import tomli

                    toml_str = tomli.dumps(tmpl_dict)
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Disposition", f"attachment; filename={template_name}.toml")
                self.end_headers()
                self.wfile.write(toml_str.encode("utf-8"))
            except FileNotFoundError as e:
                self.send_error(404, str(e))
            except Exception as e:
                self.send_error(500, str(e))
            return
        elif path.startswith("/"):
            # Serve static files (JS, CSS, images, etc.)
            filename = path.lstrip("/")
            # Determine content type based on extension
            if filename.endswith(".js"):
                content_type = "application/javascript"
            elif filename.endswith(".css"):
                content_type = "text/css"
            elif filename.endswith(".html"):
                content_type = "text/html"
            elif filename.endswith(".json"):
                content_type = "application/json"
            elif filename.endswith(".png"):
                content_type = "image/png"
            elif filename.endswith(".jpg") or filename.endswith(".jpeg"):
                content_type = "image/jpeg"
            elif filename.endswith(".ico"):
                content_type = "image/x-icon"
            elif filename.endswith(".svg"):
                content_type = "image/svg+xml"
            elif filename.endswith(".woff2"):
                content_type = "font/woff2"
            elif filename.endswith(".woff"):
                content_type = "font/woff"
            elif filename.endswith(".ttf"):
                content_type = "font/ttf"
            else:
                content_type = "application/octet-stream"
            self._serve_static(filename, content_type)
        else:
            self.send_error(404)

    def do_POST(self):
        path = self.path.split("?")[0]

        # All POST endpoints require authentication
        if not self._check_auth():
            return

        if path == "/api/providers":
            # Providers configuration
            self._serve_providers()
        elif path == "/api/agents/activity":
            # Emit agent activity event
            # POST /api/agents/activity with JSON body
            if self._emit_agent_activity():
                return
        elif path == "/api/templates/import":
            # Import a template from TOML content
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                import tomllib

                # Parse TOML content
                if hasattr(tomllib, "loads"):
                    tmpl_data = tomllib.loads(body)
                else:
                    import tomli

                    tmpl_data = tomli.loads(body)

                tmpl = tmpl_data.get("template", tmpl_data)
                template_name = tmpl.get("name", "")
                if not template_name:
                    self.send_error(400, "Template name is required")
                    return

                # Save to user templates directory
                from pathlib import Path

                user_dir = Path.home() / ".agentteam" / "templates"
                user_dir.mkdir(parents=True, exist_ok=True)

                # Write TOML file
                toml_path = user_dir / f"{template_name}.toml"
                if hasattr(tomllib, "dumps"):
                    toml_str = tomllib.dumps({"template": tmpl})
                else:
                    import tomli

                    toml_str = tomli.dumps({"template": tmpl})

                with open(toml_path, "w", encoding="utf-8") as f:
                    f.write(toml_str)

                self._serve_json({"success": True, "template": template_name, "path": str(toml_path)})
            except Exception as e:
                self.send_error(400, f"Failed to import template: {e}")
            return
        elif path.startswith("/api/team/") and path.endswith("/task"):
            parts = path.strip("/").split("/")
            if len(parts) == 4 and parts[3] == "task":
                team_name = parts[2]
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                try:
                    payload = json.loads(body)
                    from agentteam.team.tasks import TaskStore

                    store = TaskStore(team_name)
                    task = store.create(
                        subject=payload.get("subject", ""),
                        description=payload.get("description", ""),
                        owner=payload.get("owner", ""),
                    )
                    self._serve_json({"status": "ok", "task_id": task.id})
                except Exception as e:
                    self.send_error(400, str(e))
                return
        elif path == "/api/transport/switch":
            # Switch transport type (requires restart to take effect)
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body)
                new_transport = payload.get("transport", "file")
                if new_transport not in ("file", "redis", "p2p"):
                    self.send_error(400, "Invalid transport type")
                    return
                # Note: This only sets the environment variable for current process
                # A restart is required for the change to take full effect
                import os

                os.environ["AGENTTEAM_TRANSPORT"] = new_transport
                if new_transport == "redis" and payload.get("redis_url"):
                    os.environ["AGENTTEAM_REDIS_URL"] = payload.get("redis_url")
                self._serve_json(
                    {
                        "status": "ok",
                        "transport": new_transport,
                        "message": "Transport configuration updated. Restart required for full effect.",
                    }
                )
            except Exception as e:
                self.send_error(400, str(e))
            return
        elif path == "/api/teams":
            # Create a new team
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body)
                team_name = payload.get("name", "").strip()
                description = payload.get("description", "")
                template_name = payload.get("template", "")

                if not team_name:
                    self.send_error(400, "Team name is required")
                    return

                # Check if team already exists
                from agentteam.team.manager import TeamManager

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
                            {"subject": t.subject, "owner": t.owner, "description": t.description} for t in tmpl.tasks
                        ]
                    except FileNotFoundError:
                        self.send_error(400, f"Template '{template_name}' not found")
                        return
                    except Exception as e:
                        self.send_error(400, f"Failed to load template: {e}")
                        return

                # Override leader_name if provided in payload
                if payload.get("leaderName"):
                    leader_name = payload["leaderName"]

                # Create the team using TeamManager
                try:
                    config = TeamManager.create_team(
                        name=team_name,
                        leader_name=leader_name,
                        leader_id=leader_id,
                        description=description,
                    )

                    # Add agents from template
                    for agent_data in agents_data:
                        from agentteam.team.models import TeamMember

                        member = TeamMember(
                            name=agent_data["name"],
                            agent_id=f"{agent_data['name']}-{uuid.uuid4().hex[:6]}",
                            agent_type=agent_data["type"],
                        )
                        config.members.append(member)

                    # Save updated config with agents
                    from agentteam.team.manager import _save_config

                    _save_config(config)

                    # Create tasks from template
                    created_tasks = []
                    if tasks_data:
                        from agentteam.team.tasks import TaskStore

                        store = TaskStore(team_name)
                        for task_info in tasks_data:
                            task = store.create(
                                subject=task_info.get("subject", ""),
                                description=task_info.get("description", ""),
                                owner=task_info.get("owner", ""),
                            )
                            created_tasks.append(
                                {
                                    "id": task.id,
                                    "subject": task.subject,
                                    "owner": task.owner,
                                    "status": task.status.value,
                                }
                            )

                    self._serve_json(
                        {
                            "success": True,
                            "team": {
                                "name": config.name,
                                "description": config.description,
                                "leadAgentId": config.lead_agent_id,
                                "leaderName": leader_name,
                                "members": [{"name": m.name, "type": m.agent_type} for m in config.members],
                                "tasks": created_tasks or tasks_data,
                                "template": template_name or None,
                            },
                        }
                    )
                except Exception:
                    # If TeamManager.create_team fails, try using subprocess to create via CLI
                    import subprocess

                    cmd = ["agentteam", "team", "create", team_name]
                    if template_name:
                        cmd.extend(["--template", template_name])
                    if description:
                        cmd.extend(["--description", description])
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    if result.returncode == 0:
                        self._serve_json(
                            {
                                "success": True,
                                "team": {
                                    "name": team_name,
                                    "description": description,
                                    "template": template_name or None,
                                },
                            }
                        )
                    else:
                        self.send_error(500, f"Failed to create team: {result.stderr}")
            except Exception as e:
                self.send_error(400, str(e))
            return
        elif path.startswith("/api/teams/") and path.endswith("/members"):
            # Add member to team
            team_name = path[len("/api/teams/") : -len("/members")]
            if not team_name:
                self.send_error(400, "Team name required")
                return
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body)
                member_name = payload.get("name", "").strip()
                agent_type = payload.get("type", "general-purpose")

                if not member_name:
                    self.send_error(400, "Member name is required")
                    return

                from agentteam.team.manager import TeamManager
                from agentteam.team.models import TeamMember

                config = TeamManager.get_team(team_name)
                if not config:
                    self.send_error(404, f"Team '{team_name}' not found")
                    return

                # Check if member already exists
                for m in config.members:
                    if m.name == member_name:
                        self.send_error(400, f"Member '{member_name}' already exists")
                        return

                # Create new member
                new_member = TeamMember(
                    name=member_name,
                    agent_id=f"{member_name}-{uuid.uuid4().hex[:6]}",
                    agent_type=agent_type,
                )
                config.members.append(new_member)

                from agentteam.team.manager import _save_config

                _save_config(config)

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
            return
        elif path.startswith("/api/teams/") and "/members/" in path:
            # Remove member from team
            # Format: /api/teams/{team_name}/members/{member_name}
            parts = path.strip("/").split("/")
            if len(parts) != 4 or parts[2] != "members":
                self.send_error(400, "Invalid path format")
                return
            team_name = parts[1]
            member_name = parts[3]

            if not team_name or not member_name:
                self.send_error(400, "Team name and member name required")
                return

            try:
                from agentteam.team.manager import TeamManager, _save_config

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

                # Remove member
                config.members = [m for m in config.members if m.name != member_name]
                _save_config(config)

                self._serve_json({"success": True, "message": f"Member '{member_name}' removed"})
            except Exception as e:
                self.send_error(400, str(e))
            return
        elif path.startswith("/api/teams/") and path.endswith("/spawn"):
            # Spawn all team members
            team_name = path[len("/api/teams/") : -len("/spawn")]
            if not team_name:
                self.send_error(400, "Team name required")
                return
            try:
                from agentteam.spawn.registry import get_registry, is_agent_alive
                from agentteam.team.manager import TeamManager

                config = TeamManager.get_team(team_name)
                if not config:
                    self.send_error(404, f"Team '{team_name}' not found")
                    return

                # Get or create spawn registry for this team
                registry = get_registry(team_name)

                spawned = []
                failed = []

                # Spawn each member (except leader which is the current agent)
                for member in config.members:
                    if is_agent_alive(team_name, member.name):
                        spawned.append({"name": member.name, "status": "already_running"})
                        continue

                    # Try to spawn the agent
                    try:
                        # For now, mark as registered (actual spawning would require backend)
                        from agentteam.spawn.registry import AgentHealth

                        health = AgentHealth(agentName=member.name, state="healthy")
                        registry.register(member.name, health)
                        spawned.append({"name": member.name, "status": "spawned"})
                    except Exception as e:
                        failed.append({"name": member.name, "error": str(e)})

                self._serve_json(
                    {
                        "success": True,
                        "team": team_name,
                        "spawned": spawned,
                        "failed": failed,
                        "total": len(config.members),
                    }
                )
            except Exception as e:
                self.send_error(400, str(e))
            return
        elif path.startswith("/api/teams/") and path.endswith("/health"):
            # Get health status for all team agents
            team_name = path[len("/api/teams/") : -len("/health")]
            if not team_name:
                self.send_error(400, "Team name required")
                return
            try:
                from agentteam.spawn.registry import get_registry, is_agent_alive
                from agentteam.team.manager import TeamManager

                config = TeamManager.get_team(team_name)
                if not config:
                    self.send_error(404, f"Team '{team_name}' not found")
                    return

                registry = get_registry(team_name)
                members_health = []
                overall_healthy = True

                for member in config.members:
                    alive = is_agent_alive(team_name, member.name)
                    health_data = registry.get(member.name)

                    member_status = {
                        "name": member.name,
                        "agentType": member.agent_type,
                        "alive": alive,
                        "state": health_data.state.value if health_data else "unknown",
                    }
                    members_health.append(member_status)

                    if not alive or (health_data and health_data.state.value != "healthy"):
                        overall_healthy = False

                self._serve_json({"team": team_name, "healthy": overall_healthy, "members": members_health})
            except Exception as e:
                self.send_error(400, str(e))
            return
        elif path.startswith("/api/teams/") and "/stop" in path:
            # Stop/kill all team agents
            team_name = path[len("/api/teams/") :].split("/")[0]
            if not team_name:
                self.send_error(400, "Team name required")
                return
            try:
                from agentteam.spawn.registry import get_registry
                from agentteam.team.manager import TeamManager

                config = TeamManager.get_team(team_name)
                if not config:
                    self.send_error(404, f"Team '{team_name}' not found")
                    return

                registry = get_registry(team_name)
                stopped = []

                for member in config.members:
                    try:
                        registry.unregister(member.name)
                        stopped.append(member.name)
                    except Exception:
                        pass

                self._serve_json({"success": True, "team": team_name, "stopped": stopped})
            except Exception as e:
                self.send_error(400, str(e))
            return
        elif path.startswith("/api/teams/") and path.endswith("/clone"):
            # Clone team with new name
            team_name = path[len("/api/teams/") : -len("/clone")]
            if not team_name:
                self.send_error(400, "Team name required")
                return
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body)
                new_team_name = payload.get("new_name", "").strip()
                if not new_team_name:
                    self.send_error(400, "New team name is required")
                    return

                from agentteam.team.manager import TeamManager
                from agentteam.team.models import TeamMember

                config = TeamManager.get_team(team_name)
                if not config:
                    self.send_error(404, f"Team '{team_name}' not found")
                    return

                # Check if new team already exists
                if TeamManager.get_team(new_team_name):
                    self.send_error(400, f"Team '{new_team_name}' already exists")
                    return

                # Create new team with cloned members
                new_members = []
                for m in config.members:
                    new_members.append(
                        TeamMember(
                            name=m.name,
                            agent_id=f"{m.name}-{uuid.uuid4().hex[:6]}",
                            agent_type=m.agent_type,
                        )
                    )

                TeamManager.create_team(
                    name=new_team_name,
                    leader_name=config.leader.name if config.leader else "leader",
                    leader_id=config.leader.agent_id if config.leader else str(uuid.uuid4()),
                    description=f"Clone of {team_name}",
                    user=None,
                )

                # Add cloned members
                new_config = TeamManager.get_team(new_team_name)
                if new_config:
                    new_config.members = new_members
                    from agentteam.team.manager import _save_config

                    _save_config(new_config)

                # Clone tasks if TaskStore exists
                try:
                    from agentteam.team.tasks import TaskStore

                    old_store = TaskStore(team_name)
                    new_store = TaskStore(new_team_name)
                    for task in old_store.list_tasks():
                        new_store.create(
                            subject=task.subject,
                            description=task.description,
                            owner=task.owner,
                        )
                except Exception:
                    pass  # Task cloning is optional

                self._serve_json(
                    {
                        "success": True,
                        "new_team": new_team_name,
                        "cloned_from": team_name,
                        "members_count": len(new_members),
                    }
                )
            except Exception as e:
                self.send_error(400, str(e))
            return
        elif path.startswith("/api/teams/") and path.endswith("/stats"):
            # Get team statistics
            team_name = path[len("/api/teams/") : -len("/stats")]
            if not team_name:
                self.send_error(400, "Team name required")
                return
            try:
                from agentteam.spawn.registry import get_registry, is_agent_alive
                from agentteam.team.manager import TeamManager
                from agentteam.team.tasks import TaskStore

                config = TeamManager.get_team(team_name)
                if not config:
                    self.send_error(404, f"Team '{team_name}' not found")
                    return

                # Get task stats
                try:
                    task_store = TaskStore(team_name)
                    all_tasks = task_store.list_tasks()
                    tasks_by_status = {}
                    for t in all_tasks:
                        status = t.status.value
                        tasks_by_status[status] = tasks_by_status.get(status, 0) + 1
                except Exception:
                    tasks_by_status = {}

                # Get member stats
                registry = get_registry(team_name)
                members_stats = []
                for member in config.members:
                    alive = is_agent_alive(team_name, member.name)
                    health = registry.get(member.name)
                    members_stats.append(
                        {
                            "name": member.name,
                            "type": member.agent_type,
                            "alive": alive,
                            "state": health.state.value if health else "unknown",
                        }
                    )

                # Calculate team health
                alive_count = sum(1 for m in members_stats if m["alive"])
                total_count = len(members_stats)
                team_health = "healthy" if alive_count == total_count and total_count > 0 else "degraded"

                # Get team age (assuming first member is leader, created when team was created)
                import time

                team_age_seconds = time.time() - (config.created_at or time.time())

                self._serve_json(
                    {
                        "team": team_name,
                        "health": team_health,
                        "memberCount": len(config.members),
                        "aliveMembers": alive_count,
                        "tasks": {
                            "total": len(all_tasks) if all_tasks else 0,
                            "byStatus": tasks_by_status,
                        },
                        "members": members_stats,
                        "createdAt": config.created_at,
                        "ageSeconds": team_age_seconds,
                    }
                )
            except Exception as e:
                self.send_error(400, str(e))
            return
        elif path.startswith("/api/teams/") and path.endswith("/broadcast"):
            # Broadcast message to all team members
            team_name = path[len("/api/teams/") : -len("/broadcast")]
            if not team_name:
                self.send_error(400, "Team name required")
                return
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body)
                message = payload.get("message", "").strip()
                sender = payload.get("sender", "system")

                if not message:
                    self.send_error(400, "Message is required")
                    return

                from agentteam.team.mailbox import MailboxManager
                from agentteam.team.manager import TeamManager

                config = TeamManager.get_team(team_name)
                if not config:
                    self.send_error(404, f"Team '{team_name}' not found")
                    return

                # Send message to each member's inbox
                inbox = MailboxManager(team_name)
                for member in config.members:
                    inbox.send(
                        member.name,
                        {
                            "type": "broadcast",
                            "sender": sender,
                            "message": message,
                            "timestamp": time.time(),
                        },
                    )

                self._serve_json({"success": True, "team": team_name, "recipients": len(config.members)})
            except Exception as e:
                self.send_error(400, str(e))
            return
        elif path.startswith("/api/teams/") and "/messages/" in path:
            # Get messages for a specific member or team
            # Format: /api/teams/{team}/messages/{member}
            parts = path[len("/api/teams/") :].split("/messages/")
            if len(parts) != 2:
                self.send_error(400, "Invalid path")
                return
            team_name = parts[0]
            member_name = parts[1]

            if not team_name or not member_name:
                self.send_error(400, "Team name and member name required")
                return

            try:
                from agentteam.team.mailbox import MailboxManager
                from agentteam.team.manager import TeamManager

                config = TeamManager.get_team(team_name)
                if not config:
                    self.send_error(404, f"Team '{team_name}' not found")
                    return

                inbox = MailboxManager(team_name)
                messages = inbox.receive(member_name, limit=50)

                self._serve_json({"team": team_name, "member": member_name, "messages": messages})
            except Exception as e:
                self.send_error(400, str(e))
            return
        elif path.startswith("/api/teams/") and path.endswith("/messages"):
            # Get all team messages (for team owner)
            team_name = path[len("/api/teams/") : -len("/messages")]
            if not team_name:
                self.send_error(400, "Team name required")
                return

            try:
                from agentteam.team.mailbox import MailboxManager
                from agentteam.team.manager import TeamManager

                config = TeamManager.get_team(team_name)
                if not config:
                    self.send_error(404, f"Team '{team_name}' not found")
                    return

                inbox = MailboxManager(team_name)
                all_messages = []
                for member in config.members:
                    msgs = inbox.receive(member.name, limit=20)
                    for msg in msgs:
                        msg["recipient"] = member.name
                        all_messages.append(msg)

                # Sort by timestamp descending
                all_messages.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

                self._serve_json(
                    {
                        "team": team_name,
                        "messages": all_messages[:100],  # Limit to 100 most recent
                    }
                )
            except Exception as e:
                self.send_error(400, str(e))
            return
        elif path == "/api/skills/execute":
            # Skills execution disabled for stability
            self.send_error(503, "Skills execution disabled for stability")
            return
        elif path.startswith("/api/sessions/") and path.endswith("/kill"):
            # Kill a session
            parts = path.strip("/").split("/")
            if len(parts) == 3 and parts[2] == "kill":
                session_id = parts[1]
                try:
                    from agentteam.session.registry import get_session_registry

                    registry = get_session_registry()
                    registry.unregister(session_id)
                    self._serve_json({"status": "ok", "sessionId": session_id})
                except Exception as e:
                    self._serve_json({"error": str(e)})
                return
        elif path == "/api/chat/send":
            # Send a chat message
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self.send_error(400, "Message required")
                return

            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body)
                message = payload.get("message", "").strip()
                user = payload.get("user", "User")

                if not message:
                    self.send_error(400, "Message cannot be empty")
                    return

                # Save user message
                user_message = {
                    "role": "user",
                    "content": message,
                    "user": user,
                    "timestamp": payload.get("timestamp", _now_iso()),
                }
                self._save_chat_message(user_message)

                # Generate response
                response = self._handle_chat_command(message, user)

                # Save assistant response
                self._save_chat_message(response)

                # Return success
                self._serve_json({"success": True, "message": "Message sent successfully", "response": response})

            except json.JSONDecodeError:
                self.send_error(400, "Invalid JSON")
            except Exception as e:
                self._serve_json({"success": False, "error": str(e)})
            return
        elif path == "/api/chat/history":
            # GET chat history endpoint (DELETE handled in do_DELETE)
            self._serve_chat_history()
            return
        elif path == "/api/concurrency/limits":
            # Update concurrency limits
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body)
                import os

                if payload.get("maxConcurrentSessions"):
                    os.environ["AGENTTEAM_MAX_SESSIONS"] = str(payload["maxConcurrentSessions"])
                if payload.get("maxTokensPerSession"):
                    os.environ["AGENTTEAM_MAX_TOKENS_PER_SESSION"] = str(payload["maxTokensPerSession"])
                if payload.get("maxQueueLength"):
                    os.environ["AGENTTEAM_MAX_QUEUE_LENGTH"] = str(payload["maxQueueLength"])
                if payload.get("timeoutMinutes"):
                    os.environ["AGENTTEAM_SESSION_TIMEOUT"] = str(payload["timeoutMinutes"])
                self._serve_json({"status": "ok", "limits": payload})
            except Exception as e:
                self.send_error(400, str(e))
            return
        elif path == "/api/chat":
            # AI Chat endpoint
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body)
                message = payload.get("message", "")
                history = payload.get("history", [])

                # Build context from history
                context = ""
                for msg in history[-10:]:
                    role = msg.get("role", "user")
                    text = msg.get("text", "")
                    context += f"{role}: {text}\n"

                response = None

                # Try to call OpenClaw gateway for AI response
                gateway_token = os.environ.get("OPENCLAW_GATEWAY_TOKEN", "")
                gateway_url = os.environ.get("OPENCLAW_GATEWAY_URL", "http://localhost:18789")

                if gateway_token:
                    try:
                        headers = {
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {gateway_token}",
                        }

                        chat_payload = {"message": message, "context": context, "stream": False}

                        req = urllib.request.Request(
                            f"{gateway_url}/api/chat",
                            data=json.dumps(chat_payload).encode("utf-8"),
                            headers=headers,
                            method="POST",
                        )

                        with urllib.request.urlopen(req, timeout=30) as resp:
                            resp_data = json.loads(resp.read().decode("utf-8"))
                            response = resp_data.get("response", resp_data.get("message", ""))
                    except Exception as ai_error:
                        print(f"Gateway call failed: {ai_error}")

                # Try bailian API (Alibaba cloud) as fallback
                if not response:
                    try:
                        # Read MiniMax API key from openclaw.json
                        config_path = os.path.join(os.path.expanduser("~"), ".openclaw", "openclaw.json")
                        minimax_key = None
                        minimax_url = "https://api.minimaxi.com/anthropic/v1/messages"

                        if os.path.exists(config_path):
                            with open(config_path, "r", encoding="utf-8") as f:
                                config_data = json.load(f)
                                providers = config_data.get("models", {}).get("providers", {})
                                minimax_config = providers.get("minimax", {})
                                minimax_key = minimax_config.get("apiKey")
                                if minimax_config.get("baseUrl"):
                                    minimax_url = minimax_config["baseUrl"] + "/v1/messages"

                        if minimax_key:
                            # Call MiniMax API (Anthropic format)
                            headers = {
                                "Authorization": f"Bearer {minimax_key}",
                                "Content-Type": "application/json",
                                "x-api-key": minimax_key,
                                "anthropic-version": "2023-06-01",
                            }

                            # Build messages with context
                            system_content = "你是 AgentTeam AI 助手，专门帮助用户管理多代理团队、任务分配和协作工作。"
                            if context:
                                system_content += "\n\n以下是对话历史：\n" + context

                            chat_payload = {
                                "model": "MiniMax-M2.7",
                                "messages": [
                                    {"role": "user", "content": system_content},
                                    {"role": "user", "content": message},
                                ],
                                "max_tokens": 1024,
                                "temperature": 0.7,
                            }

                            req = urllib.request.Request(
                                minimax_url,
                                data=json.dumps(chat_payload).encode("utf-8"),
                                headers=headers,
                                method="POST",
                            )
                            with urllib.request.urlopen(req, timeout=30) as resp:
                                resp_data = json.loads(resp.read().decode("utf-8"))
                                if resp_data.get("content"):
                                    # Find the text content (skip thinking blocks)
                                    for item in resp_data["content"]:
                                        if item.get("type") == "text":
                                            response = item["text"]
                                            break
                                if not response:
                                    response = resp_data.get("error", {}).get("message", "")
                    except Exception as fallback_error:
                        print(f"MiniMax API call failed: {fallback_error}")

                # Use simple rule-based response if no AI response available
                if not response:
                    response = _generate_simple_response(message)

                self._serve_json({"response": response, "message": message, "timestamp": _now_iso()})
            except Exception as e:
                self.send_error(400, str(e))
            return
        self.send_error(404)

    def do_PATCH(self):
        """Handle PATCH requests for task status updates."""
        path = self.path.split("?")[0]

        # All PATCH endpoints require authentication
        if not self._check_auth():
            return

        # Pattern: /api/team/{team_name}/task/{task_id}
        if path.startswith("/api/team/") and "/task/" in path:
            parts = path.strip("/").split("/")
            if len(parts) == 5 and parts[3] == "task":
                team_name = parts[2]
                task_id = parts[4]
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                try:
                    payload = json.loads(body)
                    from agentteam.team.models import TaskStatus
                    from agentteam.team.tasks import TaskStore

                    store = TaskStore(team_name)

                    # Update task status using update method
                    new_status = payload.get("status")
                    if new_status:
                        status_enum = TaskStatus(new_status)
                        store.update(task_id, status=status_enum)

                    # Update task owner
                    new_owner = payload.get("owner")
                    if new_owner is not None:
                        store.update(task_id, owner=new_owner)

                    self._serve_json({"status": "ok", "task_id": task_id})
                except ValueError as e:
                    self.send_error(400, str(e))
                except Exception as e:
                    self.send_error(500, str(e))
                return
        self.send_error(404)

    def do_DELETE(self):
        """Handle DELETE requests."""
        path = self.path.split("?")[0]

        # All DELETE endpoints require authentication
        if not self._check_auth():
            return

        if path.startswith("/api/providers/"):
            # Delete a provider: /api/providers/{name}
            provider_name = path[len("/api/providers/") :]
            self._delete_provider(provider_name)
        elif path == "/api/chat/history":
            # Clear chat history
            self._clear_chat_history()
            return
        elif path.startswith("/api/teams/"):
            # Delete a team
            team_name = path[len("/api/teams/") :].strip("/")
            if not team_name:
                self.send_error(400, "Team name required")
                return

            try:
                from agentteam.spawn.registry import get_registry
                from agentteam.team.manager import TeamManager

                config = TeamManager.get_team(team_name)
                if not config:
                    self.send_error(404, f"Team '{team_name}' not found")
                    return

                # Stop all agents first
                registry = get_registry(team_name)
                for member in config.members:
                    try:
                        registry.unregister(member.name)
                    except Exception:
                        pass

                # Delete team via TeamManager
                TeamManager.delete_team(team_name)

                self._serve_json({"success": True, "team": team_name, "message": f"Team '{team_name}' deleted"})
            except Exception as e:
                self.send_error(400, str(e))
            return

        self.send_error(404)

    def _serve_static(self, filename: str, content_type: str):
        filepath = _STATIC_DIR / filename
        if not filepath.exists():
            self.send_error(404, f"Static file not found: {filename}")
            return
        content = filepath.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _serve_files(self):
        """Serve list of files in the workspace."""
        import os

        workspace = os.environ.get("AGENTTEAM_WORKSPACE", os.path.expanduser("~/.agentteam/workspace"))
        files = []

        try:
            if os.path.exists(workspace):
                for root, dirs, filenames in os.walk(workspace):
                    # Skip hidden directories and common ignore patterns
                    dirs[:] = [
                        d for d in dirs if not d.startswith(".") and d not in ("__pycache__", "node_modules", ".git")
                    ]
                    for filename in filenames:
                        if filename.startswith("."):
                            continue
                        filepath = os.path.join(root, filename)
                        relpath = os.path.relpath(filepath, workspace)
                        stat = os.stat(filepath)
                        files.append(
                            {
                                "name": filename,
                                "path": relpath,
                                "size": stat.st_size,
                                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            }
                        )
        except Exception:
            pass

        # If no files found, return some default files
        if not files:
            files = [
                {"name": "README.md", "path": "README.md", "size": 1024, "modified": _now_iso()},
                {"name": "AGENTS.md", "path": "AGENTS.md", "size": 2048, "modified": _now_iso()},
                {"name": "SOUL.md", "path": "SOUL.md", "size": 512, "modified": _now_iso()},
                {"name": "USER.md", "path": "USER.md", "size": 256, "modified": _now_iso()},
            ]

        self._serve_json({"files": files, "workspace": workspace})

    def _serve_json(self, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _serve_team(self, team_name: str):
        try:
            data = self.collector.collect_team(team_name)
            self._serve_json(data)
        except ValueError as e:
            body = json.dumps({"error": str(e)}, ensure_ascii=False).encode("utf-8")
            self.send_response(404)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def _serve_sse(self, team_name: str):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        try:
            while True:
                try:
                    data = self.team_cache.get(
                        team_name,
                        lambda: self.collector.collect_team(team_name),
                    )
                except ValueError as e:
                    data = {"error": str(e)}
                payload = json.dumps(data, ensure_ascii=False)
                self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                self.wfile.flush()
                time.sleep(self.interval)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def _serve_transport_status(self):
        """Serve transport connection status."""
        import os

        transport_type = os.environ.get("AGENTTEAM_TRANSPORT", "file")

        status_data = {
            "transport": transport_type,
            "status": "connected",
            "config": {},
            "metrics": {},
        }

        # Add transport-specific info
        if transport_type == "redis":
            redis_url = os.environ.get("AGENTTEAM_REDIS_URL", "redis://localhost:6379")
            status_data["config"] = {
                "url": redis_url,
                "db": os.environ.get("AGENTTEAM_REDIS_DB", "0"),
                "hasPassword": bool(os.environ.get("AGENTTEAM_REDIS_PASSWORD")),
            }
            # Try to get actual Redis status
            try:
                from agentteam.transport.redis import RedisTransport

                # Create a test connection
                test_transport = RedisTransport("_monitor_test")
                # Ping test
                if test_transport._client:
                    test_transport._client.ping()
                    status_data["status"] = "connected"
                    # Get Redis INFO
                    info = test_transport._client.info()
                    status_data["metrics"] = {
                        "connected_clients": info.get("connected_clients", 0),
                        "used_memory_human": info.get("used_memory_human", "0B"),
                        "uptime_in_seconds": info.get("uptime_in_seconds", 0),
                    }
                test_transport.close()
            except ImportError:
                status_data["status"] = "unavailable"
                status_data["error"] = "redis package not installed"
            except Exception as e:
                status_data["status"] = "disconnected"
                status_data["error"] = str(e)

        elif transport_type == "p2p":
            status_data["config"] = {
                "mode": "zeromq_p2p",
            }
            try:
                import zmq

                status_data["status"] = "available"
            except ImportError:
                status_data["status"] = "unavailable"
                status_data["error"] = "zmq package not installed"

        else:  # file transport
            status_data["config"] = {
                "mode": "filesystem",
            }
            status_data["status"] = "connected"

        self._serve_json(status_data)

    def _serve_transport_stats(self):
        """Serve transport statistics (queue lengths, throughput)."""
        import os

        transport_type = os.environ.get("AGENTTEAM_TRANSPORT", "file")

        stats_data = {
            "transport": transport_type,
            "queues": [],
            "throughput": {
                "messagesPerSec": 0,
                "avgLatencyMs": 0,
            },
            "latencyDistribution": {
                "p50": 0,
                "p90": 0,
                "p99": 0,
            },
        }

        # Get queue stats for current team if available
        if hasattr(self, "default_team") and self.default_team:
            try:
                if transport_type == "redis":
                    from agentteam.transport.redis import RedisTransport

                    transport = RedisTransport(self.default_team)
                    recipients = transport.list_recipients()
                    for recipient in recipients:
                        count = transport.count(recipient)
                        stats_data["queues"].append(
                            {
                                "agent": recipient,
                                "pending": count,
                            }
                        )
                    transport.close()
                elif transport_type == "file":
                    from agentteam.transport.file import FileTransport

                    transport = FileTransport(self.default_team)
                    recipients = transport.list_recipients()
                    for recipient in recipients:
                        count = transport.count(recipient)
                        stats_data["queues"].append(
                            {
                                "agent": recipient,
                                "pending": count,
                            }
                        )
            except Exception as e:
                stats_data["error"] = str(e)

        # Mock throughput data (would be calculated from actual metrics in production)
        stats_data["throughput"] = {
            "messagesPerSec": 12.5,
            "avgLatencyMs": 8.3,
        }
        stats_data["latencyDistribution"] = {
            "p50": 5,
            "p90": 15,
            "p99": 50,
        }

        self._serve_json(stats_data)

    def _serve_usage_summary(self):
        """Serve token usage summary."""
        try:
            from agentteam.tracker.token_stats import get_usage_summary

            summary = get_usage_summary()
            self._serve_json(summary.to_dict())
        except Exception as e:
            self._serve_json({"error": str(e)})

    def _serve_usage_trend(self):
        """Serve token usage trend."""
        query = parse_qs(urlparse(self.path).query)
        days = int(query.get("days", ["30"])[0])
        try:
            from agentteam.tracker.token_stats import get_usage_trend

            trend = get_usage_trend(days)
            self._serve_json([d.to_dict() for d in trend])
        except Exception as e:
            self._serve_json({"error": str(e)})

    def _serve_provider_stats(self):
        """Serve provider usage statistics."""
        try:
            from agentteam.tracker.token_stats import get_provider_stats

            stats = get_provider_stats()
            self._serve_json([s.to_dict() for s in stats])
        except Exception as e:
            self._serve_json({"error": str(e)})

    def _serve_profiler_stats(self):
        """Serve performance profiler statistics."""
        try:
            collector = _get_collector()
            stats = collector.collect_profiler_stats()
            self._serve_json(stats)
        except Exception as e:
            self._serve_json({"error": str(e)})

    def _serve_sessions(self):
        """Serve active sessions list."""
        try:
            from agentteam.session.registry import get_session_registry

            registry = get_session_registry()
            sessions = registry.list_sessions()
            self._serve_json(
                {
                    "sessions": [s.model_dump(by_alias=True, exclude_none=True) for s in sessions],
                    "activeCount": len([s for s in sessions if s.status == "active"]),
                }
            )
        except Exception as e:
            self._serve_json({"error": str(e), "sessions": [], "activeCount": 0})

    def _serve_session(self, session_id: str):
        """Serve single session details."""
        try:
            from agentteam.session.registry import get_session_registry

            registry = get_session_registry()
            session = registry.get_session_summary(session_id)
            if session:
                self._serve_json(session.model_dump(by_alias=True, exclude_none=True))
            else:
                self.send_error(404, "Session not found")
        except Exception as e:
            self._serve_json({"error": str(e)})

    def _serve_team_alerts(self, team_name: str):
        """Serve team alerts."""
        try:
            from agentteam.alerts import get_alerts

            alerts = get_alerts(team_name)
            self._serve_json([a.to_dict() for a in alerts])
        except Exception as e:
            self._serve_json({"error": str(e), "alerts": []})

    def _serve_skills(self):
        """Serve available skills list."""
        # Return mock skills data for demo
        # In production, this would query actual skill registry
        skills_data = [
            {
                "id": "code-review",
                "name": "Code Review",
                "slashCommand": "code-review",
                "category": "development",
                "description": "Automated PR code review with multi-expert Agent parallel review.",
                "icon": "🔍",
                "variables": [
                    {
                        "name": "target",
                        "type": "text",
                        "required": True,
                        "label": "Target Files/PR",
                    },
                    {
                        "name": "depth",
                        "type": "select",
                        "required": False,
                        "label": "Review Depth",
                        "options": ["quick", "standard", "deep"],
                    },
                ],
            },
            {
                "id": "debug",
                "name": "Debug Analyzer",
                "slashCommand": "debug",
                "category": "development",
                "description": "Analyze error messages and code to help locate and fix bugs.",
                "icon": "🐛",
                "variables": [
                    {
                        "name": "error",
                        "type": "textarea",
                        "required": True,
                        "label": "Error Message",
                    },
                    {
                        "name": "context",
                        "type": "textarea",
                        "required": False,
                        "label": "Code Context",
                    },
                ],
            },
            {
                "id": "commit-msg",
                "name": "Commit Message Generator",
                "slashCommand": "commit-msg",
                "category": "development",
                "description": "Generate standardized Git commit messages based on code changes.",
                "icon": "📝",
                "variables": [],
            },
            {
                "id": "translate",
                "name": "Translate",
                "slashCommand": "translate",
                "category": "writing",
                "description": "Translate text to different languages.",
                "icon": "🌐",
                "variables": [
                    {
                        "name": "text",
                        "type": "textarea",
                        "required": True,
                        "label": "Text to Translate",
                    },
                    {
                        "name": "lang",
                        "type": "select",
                        "required": True,
                        "label": "Target Language",
                        "options": ["English", "Chinese", "Japanese", "Spanish"],
                    },
                ],
            },
            {
                "id": "write-doc",
                "name": "Documentation Writer",
                "slashCommand": "write-doc",
                "category": "writing",
                "description": "Generate comprehensive documentation for code modules.",
                "icon": "📄",
                "variables": [
                    {"name": "target", "type": "text", "required": True, "label": "Target Module"},
                    {
                        "name": "format",
                        "type": "select",
                        "required": False,
                        "label": "Output Format",
                        "options": ["markdown", "rst", "html"],
                    },
                ],
            },
            {
                "id": "write-test",
                "name": "Test Generator",
                "slashCommand": "write-test",
                "category": "development",
                "description": "Generate unit tests for specified code modules.",
                "icon": "🧪",
                "variables": [
                    {"name": "target", "type": "text", "required": True, "label": "Target Module"},
                    {
                        "name": "framework",
                        "type": "select",
                        "required": False,
                        "label": "Test Framework",
                        "options": ["pytest", "unittest", "jest"],
                    },
                ],
            },
            {
                "id": "refactor",
                "name": "Refactor Assistant",
                "slashCommand": "refactor",
                "category": "development",
                "description": "Analyze and suggest refactoring improvements.",
                "icon": "🔧",
                "variables": [
                    {"name": "target", "type": "text", "required": True, "label": "Target Code"},
                    {
                        "name": "focus",
                        "type": "select",
                        "required": False,
                        "label": "Focus Area",
                        "options": ["performance", "readability", "maintainability"],
                    },
                ],
            },
            {
                "id": "security-check",
                "name": "Security Check",
                "slashCommand": "security-check",
                "category": "analysis",
                "description": "Security audit for command injection, XSS, unsafe patterns.",
                "icon": "🔒",
                "variables": [{"name": "target", "type": "text", "required": True, "label": "Target Files"}],
            },
            {
                "id": "benchmark",
                "name": "Performance Benchmark",
                "slashCommand": "benchmark",
                "category": "analysis",
                "description": "Collect Web/API/Bundle performance metrics.",
                "icon": "📊",
                "variables": [
                    {"name": "url", "type": "text", "required": True, "label": "Target URL"},
                    {
                        "name": "iterations",
                        "type": "number",
                        "required": False,
                        "label": "Iterations",
                        "default": 10,
                    },
                ],
            },
            {
                "id": "create-skill",
                "name": "Create Skill",
                "slashCommand": "create-skill",
                "category": "custom",
                "description": "Create new skill templates from scratch.",
                "icon": "✨",
                "variables": [
                    {"name": "name", "type": "text", "required": True, "label": "Skill Name"},
                    {
                        "name": "description",
                        "type": "textarea",
                        "required": True,
                        "label": "Description",
                    },
                    {
                        "name": "type",
                        "type": "select",
                        "required": True,
                        "label": "Skill Type",
                        "options": ["prompt", "native", "orchestration"],
                    },
                ],
            },
        ]
        self._serve_json({"skills": skills_data})

    def _serve_notifications(self):
        """Serve notifications list (P37: wired to real NotificationManager)."""
        try:
            from agentteam.notification.manager import get_notification_manager
            from agentteam.notification.types import NotificationType

            mgr = get_notification_manager()
            history = mgr.get_history(limit=50)

            # Map notification types to icons
            icon_map = {
                NotificationType.CONFIRMATION: "🤝",
                NotificationType.TASK_COMPLETE: "✅",
                NotificationType.ERROR: "❌",
                NotificationType.STUCK: "⚠️",
                NotificationType.INFO: "ℹ️",
                NotificationType.WARNING: "⚡",
            }

            notifications = []
            for n in history:
                notifications.append(
                    {
                        "id": n.notification_id,
                        "title": n.title,
                        "message": n.body,
                        "time": n.timestamp[:19] if n.timestamp else "",
                        "unread": not n.acknowledged,
                        "icon": icon_map.get(n.notification_type, "ℹ️"),
                        # P30-P33: Include image_url for rich media display
                        "image_url": n.image_url,
                    }
                )

            self._serve_json({"notifications": notifications})
        except Exception as e:
            # Fallback: return empty list on any error
            self._serve_json({"notifications": []})

    def _mark_notifications_read(self):
        """Mark all notifications as read (P37: wired to NotificationManager)."""
        try:
            from agentteam.notification.manager import get_notification_manager

            mgr = get_notification_manager()
            # Acknowledge all session notifications (empty session_id acknowledges all)
            mgr.acknowledge(session_id=None)
            self._serve_json({"success": True})
        except Exception as e:
            self._serve_json({"success": False, "error": str(e)})

    def _serve_events(self):
        """Serve events from the EventTracker via SSE (P37: wired to EventAPI for real-time streaming)."""
        global _event_queue, _event_subscribers, _event_broadcaster_lock

        # P37: Register event subscriber on first SSE connection
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

        # Register as subscriber - start from current queue size (only send new events)
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

            # Send any missed events since connection started (initial snapshot from EventAPI)
            try:
                from agentteam.events.api import EventAPI

                api = EventAPI()
                initial_result = api.get_events(team_name=team, agent_name=agent, limit=limit)
                for event in initial_result.get("events", []):
                    self.wfile.write(
                        f"data: {json.dumps({'type': 'event', 'data': event}, ensure_ascii=False)}\n\n".encode("utf-8")
                    )
                    self.wfile.flush()
            except Exception as e:
                pass  # Don't fail SSE connection if initial load fails

            # Stream events as they come in
            heartbeat_count = 0
            idle_cycles = 0
            active_heartbeat_interval = 10  # seconds when active
            idle_heartbeat_interval = 30  # seconds when idle (>3 cycles no events)
            current_timeout = active_heartbeat_interval

            while True:
                # Wait for event or timeout (adaptive based on activity)
                acquired = subscriber_lock.acquire(timeout=current_timeout)
                if acquired:
                    subscriber_lock.release()

                # Send any new events
                has_new_events = False
                with _event_broadcaster_lock:
                    while len(_event_queue) > last_event_idx:
                        has_new_events = True
                        event_data = _event_queue[last_event_idx]
                        # Filter by team/agent if specified
                        if team is None or event_data.get("team_name") == team:
                            if agent is None or event_data.get("agent_name") == agent:
                                self.wfile.write(
                                    f"data: {json.dumps({'type': 'event', 'data': event_data}, ensure_ascii=False)}\n\n".encode(
                                        "utf-8"
                                    )
                                )
                                self.wfile.flush()
                        last_event_idx += 1

                # Adaptive heartbeat: track idle cycles
                if has_new_events:
                    idle_cycles = 0
                    current_timeout = active_heartbeat_interval  # Active: use shorter interval
                else:
                    idle_cycles += 1
                    # After 3 idle cycles (30s), switch to longer interval
                    if idle_cycles > 3:
                        current_timeout = idle_heartbeat_interval

                # Send heartbeat (less frequently when idle)
                heartbeat_count += 1
                self.wfile.write(
                    f"data: {json.dumps({'type': 'heartbeat', 'count': heartbeat_count, 'timestamp': _now_iso(), 'idle_cycles': idle_cycles}, ensure_ascii=False)}\n\n".encode(
                        "utf-8"
                    )
                )
                self.wfile.flush()

        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            # Unregister subscriber
            with _event_broadcaster_lock:
                if subscriber_lock in _event_subscribers:
                    _event_subscribers.remove(subscriber_lock)

    @staticmethod
    def _broadcast_event(event_data: dict):
        """Broadcast an event to all SSE subscribers (P37: EventAPI integration)."""
        global _event_queue, _event_subscribers, _event_broadcaster_lock

        # Add to queue
        _event_queue.append(event_data)

        # Notify all subscribers
        with _event_broadcaster_lock:
            for lock in _event_subscribers[:]:
                try:
                    lock.release()
                except RuntimeError:
                    # Lock not held by this thread, ignore
                    pass

    def _serve_agent_activity_sse(self):
        """Serve real-time agent activity via SSE.

        GET /api/agents/events?team=<team>&agent=<agent>&limit=100

        Returns an SSE stream of agent activity events including:
        - Agent started
        - Agent heartbeat
        - Agent completed task
        - Agent idle
        - Agent error
        """
        global _agent_activity_queue, _agent_activity_subscribers, _agent_activity_lock

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
        last_event_idx = len(_agent_activity_queue)
        subscriber_lock = threading.Lock()
        subscriber_lock.acquire()

        with _agent_activity_lock:
            _agent_activity_subscribers.append(subscriber_lock)

        try:
            # Send initial connection message
            self.wfile.write(
                f"data: {json.dumps({'type': 'connected', 'timestamp': _now_iso()}, ensure_ascii=False)}\n\n".encode(
                    "utf-8"
                )
            )
            self.wfile.flush()

            # Send recent activity (initial snapshot)
            with _agent_activity_lock:
                recent = list(_agent_activity_queue)[-limit:]
            for activity in recent:
                # Filter by team/agent if specified
                if team is None or activity.get("team_name") == team:
                    if agent is None or activity.get("agent_name") == agent:
                        self.wfile.write(
                            f"data: {json.dumps({'type': 'activity', 'data': activity}, ensure_ascii=False)}\n\n".encode(
                                "utf-8"
                            )
                        )
                        self.wfile.flush()

            # Stream activities as they come in
            heartbeat_count = 0
            idle_cycles = 0
            active_heartbeat_interval = 5  # seconds when active
            idle_heartbeat_interval = 15  # seconds when idle
            current_timeout = active_heartbeat_interval

            while True:
                acquired = subscriber_lock.acquire(timeout=current_timeout)
                if acquired:
                    subscriber_lock.release()

                # Send any new activities
                has_new = False
                with _agent_activity_lock:
                    while len(_agent_activity_queue) > last_event_idx:
                        has_new = True
                        activity_data = _agent_activity_queue[last_event_idx]
                        # Filter by team/agent
                        if team is None or activity_data.get("team_name") == team:
                            if agent is None or activity_data.get("agent_name") == agent:
                                self.wfile.write(
                                    f"data: {json.dumps({'type': 'activity', 'data': activity_data}, ensure_ascii=False)}\n\n".encode(
                                        "utf-8"
                                    )
                                )
                                self.wfile.flush()
                        last_event_idx += 1

                # Adaptive heartbeat
                if has_new:
                    idle_cycles = 0
                    current_timeout = active_heartbeat_interval
                else:
                    idle_cycles += 1
                    if idle_cycles > 3:
                        current_timeout = idle_heartbeat_interval

                heartbeat_count += 1
                if heartbeat_count % 10 == 0:
                    # Send heartbeat comment every ~50 seconds
                    self.wfile.write(f": heartbeat {heartbeat_count}\n\n".encode("utf-8"))
                    self.wfile.flush()

        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            with _agent_activity_lock:
                if subscriber_lock in _agent_activity_subscribers:
                    _agent_activity_subscribers.remove(subscriber_lock)

    def _emit_agent_activity(self):
        """Emit an agent activity event.

        POST /api/agents/activity
        Body: {"team_name": "...", "agent_name": "...", "status": "...", "message": "...", "data": {...}}

        Status can be: started, heartbeat, completed, error, idle, message
        """
        global _agent_activity_queue, _agent_activity_subscribers, _agent_activity_lock

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self.send_error(400, "Request body required")
            return

        try:
            body = self.rfile.read(content_length).decode("utf-8")
            activity_data = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            self.send_error(400, f"Invalid JSON: {e}")
            return

        # Validate required fields
        if not activity_data.get("team_name") or not activity_data.get("agent_name"):
            self.send_error(400, "team_name and agent_name are required")
            return

        # Add timestamp
        activity_data["timestamp"] = _now_iso()

        # Add to queue
        with _agent_activity_lock:
            _agent_activity_queue.append(activity_data)

        # Notify subscribers
        with _agent_activity_lock:
            for lock in _agent_activity_subscribers[:]:
                try:
                    lock.release()
                except RuntimeError:
                    pass

        # Return success
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True, "activity": activity_data}, ensure_ascii=False).encode("utf-8"))
        return True

    @staticmethod
    def broadcast_agent_activity(activity_data: dict):
        """Broadcast an agent activity event to all SSE subscribers.

        Use this static method to emit activity from anywhere in the codebase.
        """
        global _agent_activity_queue, _agent_activity_subscribers, _agent_activity_lock

        # Add timestamp if not present
        if "timestamp" not in activity_data:
            activity_data["timestamp"] = _now_iso()

        with _agent_activity_lock:
            _agent_activity_queue.append(activity_data)
            for lock in _agent_activity_subscribers[:]:
                try:
                    lock.release()
                except RuntimeError:
                    pass

    def _serve_concurrency_limits(self):
        """Serve concurrency limits configuration."""
        import os

        limits = {
            "maxConcurrentSessions": int(os.environ.get("AGENTTEAM_MAX_SESSIONS", "10")),
            "maxTokensPerSession": int(os.environ.get("AGENTTEAM_MAX_TOKENS_PER_SESSION", "50000")),
            "maxQueueLength": int(os.environ.get("AGENTTEAM_MAX_QUEUE_LENGTH", "100")),
            "timeoutMinutes": int(os.environ.get("AGENTTEAM_SESSION_TIMEOUT", "30")),
        }
        self._serve_json(limits)

    def _get_providers_file(self):
        """Get the path to the providers configuration file."""
        import os

        data_dir = os.path.join(os.path.expanduser("~"), ".openclaw", "agentteam")
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, "providers.json")

    def _load_providers(self):
        """Load providers from configuration file."""
        import json
        import os

        providers_file = self._get_providers_file()
        if os.path.exists(providers_file):
            try:
                with open(providers_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {"providers": []}
        return {"providers": []}

    def _save_providers(self, data):
        """Save providers to configuration file."""
        import json

        providers_file = self._get_providers_file()
        with open(providers_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _serve_providers(self):
        """Serve providers list or save new provider."""
        import json

        if self.command == "GET":
            # Return list of providers (without API keys)
            data = self._load_providers()
            # Mask API keys for security
            for p in data.get("providers", []):
                if "api_key" in p:
                    key = p["api_key"]
                    if len(key) > 8:
                        p["api_key"] = key[:4] + "****" + key[-4:]
                    else:
                        p["api_key"] = "****"
            self._serve_json(data)
            return

        # POST - save provider
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self.send_error(400, "No content")
            return

        body = self.rfile.read(content_length).decode("utf-8")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        # Validate required fields
        name = payload.get("name", "").strip()
        provider_type = payload.get("type", "").strip()
        if not name or not provider_type:
            self.send_error(400, "Name and type are required")
            return

        # Load existing providers
        data = self._load_providers()
        providers = data.get("providers", [])

        # Check if provider with same name exists
        existing_idx = None
        for i, p in enumerate(providers):
            if p.get("name") == name:
                existing_idx = i
                break

        # Create provider entry (don't store API key in memory, just save to file)
        provider_entry = {
            "name": name,
            "type": provider_type,
            "api_key": payload.get("api_key", ""),
            "base_url": payload.get("base_url", ""),
            "default_model": payload.get("default_model", ""),
            "enabled": payload.get("enabled", True),
        }

        if existing_idx is not None:
            providers[existing_idx] = provider_entry
        else:
            providers.append(provider_entry)

        # Save to file
        self._save_providers({"providers": providers})

        # Return success (with masked API key)
        response = dict(provider_entry)
        if response["api_key"]:
            key = response["api_key"]
            if len(key) > 8:
                response["api_key"] = key[:4] + "****" + key[-4:]
            else:
                response["api_key"] = "****"

        self._serve_json({"success": True, "provider": response})

    def _serve_settings(self):
        """Serve settings configuration."""
        import json
        from pathlib import Path

        # Get settings file path
        config_dir = Path.home() / ".openclaw" / "workspace" / "AgentTeam-OpenClaw"
        settings_file = config_dir / "settings.json"

        if self.command == "GET":
            # Return settings
            if settings_file.exists():
                try:
                    with open(settings_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except json.JSONDecodeError:
                    data = {"error": "Invalid JSON in settings file"}
            else:
                # Return default settings
                data = {
                    "theme": "dark",
                    "language": "zh-CN",
                    "providers": [],
                    "defaultProvider": "",
                    "models": {},
                }
            self._serve_json(data)
            return

        # POST - save settings
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self.send_error(400, "No content")
            return

        body = self.rfile.read(content_length).decode("utf-8")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        # Ensure directory exists
        config_dir.mkdir(parents=True, exist_ok=True)

        # Save settings
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        self._serve_json({"success": True})

    def _delete_provider(self, provider_name):
        """Delete a provider by name."""
        import urllib.parse

        # URL decode the name
        provider_name = urllib.parse.unquote(provider_name)

        data = self._load_providers()
        providers = data.get("providers", [])

        original_len = len(providers)
        providers = [p for p in providers if p.get("name") != provider_name]

        if len(providers) == original_len:
            self.send_error(404, f"Provider '{provider_name}' not found")
            return

        self._save_providers({"providers": providers})
        self._serve_json({"success": True, "message": f"Provider '{provider_name}' deleted"})

    def _serve_chat_events(self):
        """Serve chat events via Server-Sent Events."""
        global _chat_subscribers

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        # Register as subscriber
        subscriber_lock = threading.Lock()
        subscriber_lock.acquire()
        last_event_idx = len(_chat_event_queue)  # Start from current queue size

        with _subscriber_lock:
            _chat_subscribers.append(subscriber_lock)

        try:
            # Send initial connection message
            self.wfile.write(
                f"data: {json.dumps({'type': 'connected', 'timestamp': _now_iso()}, ensure_ascii=False)}\n\n".encode(
                    "utf-8"
                )
            )
            self.wfile.flush()

            # Poll for events and send heartbeats
            heartbeat_count = 0
            while True:
                # Wait for event or timeout (10 seconds)
                acquired = subscriber_lock.acquire(timeout=10)
                if acquired:
                    subscriber_lock.release()

                # Send any new events
                with _subscriber_lock:
                    while len(_chat_event_queue) > last_event_idx:
                        event = _chat_event_queue[last_event_idx]
                        self.wfile.write(f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode("utf-8"))
                        self.wfile.flush()
                        last_event_idx += 1

                # Send heartbeat
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
            # Unregister subscriber
            with _subscriber_lock:
                if subscriber_lock in _chat_subscribers:
                    _chat_subscribers.remove(subscriber_lock)

    def _poll_chat_events(self):
        """Poll for chat events (non-SSE, polling-based for stability)."""
        global _chat_event_queue
        # Get last 20 events
        with _subscriber_lock:
            events = list(_chat_event_queue)[-20:]
        self._serve_json({"events": events, "count": len(events)})

    def _serve_chat_history(self):
        """Serve chat history."""
        import os
        from pathlib import Path

        # Simple file-based chat storage
        chat_file = Path(os.environ.get("AGENTTEAM_CHAT_HISTORY", "~/.openclaw/chat_history.json"))
        chat_file = chat_file.expanduser()

        try:
            if chat_file.exists():
                with open(chat_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            else:
                history = {"messages": []}
        except Exception as e:
            history = {"messages": [], "error": str(e)}

        self._serve_json(history)

    def _serve_db_tasks(self):
        """Serve task statistics (SpectrAI feature)."""
        try:
            from agentteam.team.tasks import TaskStore

            # Get all teams from collector (returns a list of team dicts)
            teams_list = self.collector.collect_overview()

            all_tasks = []
            task_statuses = {}

            for team in teams_list:
                team_name = team.get("name", "unknown")
                try:
                    store = TaskStore(team_name)
                    tasks = store.list_tasks()
                    for task in tasks:
                        task_data = task.model_dump() if hasattr(task, "model_dump") else dict(task)
                        task_data["team"] = team_name
                        all_tasks.append(task_data)

                        # Count by status
                        status = task_data.get("status", "unknown")
                        task_statuses[status] = task_statuses.get(status, 0) + 1
                except Exception:
                    # If task store fails for a team, continue with other teams
                    pass

            self._serve_json(
                {
                    "success": True,
                    "total": len(all_tasks),
                    "byStatus": task_statuses,
                    "tasks": all_tasks[:100],  # Limit to 100 most recent
                }
            )
        except Exception as e:
            self._serve_json({"success": False, "error": str(e)})

    def _serve_agent_readiness(self, agent_id: str):
        """Serve agent readiness status (SpectrAI feature)."""
        try:
            from agentteam.readiness.detector import AgentReadinessDetector, DetectorConfig
            from agentteam.spawn.registry import get_registry

            # Check if agent is in registry
            registry = get_registry()
            is_alive = registry.is_agent_alive(agent_id) if hasattr(registry, "is_agent_alive") else False

            # Create detector for readiness check
            config = DetectorConfig(agent_id=agent_id)
            detector = AgentReadinessDetector(agent_id, config)

            # Get readiness status
            fast_path_disabled = detector.fast_path_disabled

            self._serve_json(
                {
                    "success": True,
                    "agentId": agent_id,
                    "ready": is_alive and not fast_path_disabled,
                    "alive": is_alive,
                    "fastPathDisabled": fast_path_disabled,
                }
            )
        except Exception as e:
            self._serve_json({"success": False, "agentId": agent_id, "error": str(e)})

    def _serve_session_state(self, session_id: str):
        """Serve session state inference (SpectrAI feature)."""
        try:
            from agentteam.session.registry import get_session_registry

            registry = get_session_registry()
            sessions = registry.list_sessions()

            # Find the session
            session = None
            for s in sessions:
                if s.session_id == session_id:
                    session = s
                    break

            if not session:
                self._serve_json({"success": False, "error": "Session not found"})
                return

            # Extract state information
            session_data = session.model_dump() if hasattr(session, "model_dump") else dict(session)

            # Basic state inference
            state = {
                "success": True,
                "sessionId": session_id,
                "status": session_data.get("status", "unknown"),
                "isActive": session_data.get("status") == "active",
                "isCompleted": session_data.get("status") == "completed",
                "hasError": session_data.get("error") is not None,
                "metadata": {
                    "createdAt": session_data.get("created_at"),
                    "lastActivity": session_data.get("last_activity"),
                    "agentId": session_data.get("agent_id"),
                },
            }

            self._serve_json(state)
        except Exception as e:
            self._serve_json({"success": False, "error": str(e)})

    def _clear_chat_history(self):
        """Clear chat history."""
        import os
        from pathlib import Path

        chat_file = Path(os.environ.get("AGENTTEAM_CHAT_HISTORY", "~/.openclaw/chat_history.json"))
        chat_file = chat_file.expanduser()

        try:
            # Create empty history
            history = {"messages": [], "cleared_at": _now_iso()}
            chat_file.parent.mkdir(parents=True, exist_ok=True)
            with open(chat_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
            self._serve_json({"success": True, "message": "Chat history cleared"})
        except Exception as e:
            self._serve_json({"success": False, "error": str(e)})

    def _save_chat_message(self, message_data):
        """Save a chat message to history and broadcast to SSE subscribers."""
        import os
        from pathlib import Path

        chat_file = Path(os.environ.get("AGENTTEAM_CHAT_HISTORY", "~/.openclaw/chat_history.json"))
        chat_file = chat_file.expanduser()

        try:
            # Load existing history
            if chat_file.exists():
                with open(chat_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            else:
                history = {"messages": []}

            # Add new message
            message_data["id"] = f"msg_{int(time.time() * 1000)}_{len(history['messages'])}"
            message_data["timestamp"] = message_data.get("timestamp", _now_iso())
            history["messages"].append(message_data)

            # Keep only last 1000 messages
            if len(history["messages"]) > 1000:
                history["messages"] = history["messages"][-1000:]

            # Save back
            chat_file.parent.mkdir(parents=True, exist_ok=True)
            with open(chat_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)

            # Broadcast to SSE subscribers
            self._broadcast_chat_event({"type": "message", "data": message_data})

            return True
        except Exception as e:
            print(f"Error saving chat message: {e}")
            return False

    @staticmethod
    def _broadcast_chat_event(event):
        """Broadcast a chat event to all SSE subscribers."""
        global _chat_event_queue, _chat_subscribers
        _chat_event_queue.append(event)
        # Notify all subscribers (SSE connections will pick up on next poll)
        with _subscriber_lock:
            for lock in _chat_subscribers[:]:
                try:
                    lock.release()
                except RuntimeError:
                    # Lock not held by this thread, ignore
                    pass

    def _handle_chat_command(self, message, user="User"):
        """Handle chat commands and return appropriate response."""
        message_lower = message.strip().lower()

        if message_lower.startswith("/help"):
            return {
                "role": "system",
                "content": """Available commands:
• /help - Show this help message
• /status - Check team status
• /tasks list - List active tasks
• /tasks create [title] [description] - Create a new task
• /members - List active team members
• /clear - Clear chat history
• /export - Export chat history

You can also type regular messages to communicate with the team.""",
                "timestamp": _now_iso(),
            }

        elif message_lower.startswith("/status"):
            try:
                from agentteam.board.collector import BoardCollector

                collector = BoardCollector()
                overview = collector.collect_overview()
                return {
                    "role": "system",
                    "content": f"""Team Status:
• Overall: {overview.get("status", "unknown")}
• Active teams: {overview.get("team_count", 0)}
• Total tasks: {overview.get("total_tasks", 0)}
• Active sessions: {overview.get("active_sessions", 0)}""",
                    "timestamp": _now_iso(),
                }
            except Exception as e:
                return {
                    "role": "system",
                    "content": f"Error getting team status: {str(e)}",
                    "timestamp": _now_iso(),
                }

        elif message_lower.startswith("/tasks list"):
            try:
                from agentteam.board.collector import BoardCollector

                collector = BoardCollector()
                overview = collector.collect_overview()
                teams = overview.get("teams", [])

                if not teams:
                    return {
                        "role": "system",
                        "content": "No active teams found.",
                        "timestamp": _now_iso(),
                    }

                response = "Active Tasks:\n"
                for team in teams[:5]:  # Show first 5 teams
                    team_name = team.get("name", "unknown")
                    tasks = team.get("tasks", [])
                    if tasks:
                        response += f"\n**{team_name}:**\n"
                        for task in tasks[:10]:  # Show first 10 tasks per team
                            status = task.get("status", "pending")
                            status_icon = {
                                "pending": "⏳",
                                "in_progress": "▶️",
                                "completed": "✅",
                                "failed": "❌",
                            }.get(status, "❓")
                            response += f"{status_icon} {task.get('subject', 'Untitled')} (assigned to: {task.get('owner', 'unassigned')})\n"

                return {"role": "system", "content": response, "timestamp": _now_iso()}
            except Exception as e:
                return {
                    "role": "system",
                    "content": f"Error listing tasks: {str(e)}",
                    "timestamp": _now_iso(),
                }

        elif message_lower.startswith("/tasks create"):
            # Extract task title and description from command
            parts = message.split(" ", 3)
            if len(parts) < 4:
                return {
                    "role": "system",
                    "content": "Usage: /tasks create [title] [description]\nExample: /tasks create Fix bug 'Fix the critical bug in login system'",
                    "timestamp": _now_iso(),
                }

            title = parts[2]
            description = parts[3] if len(parts) > 3 else "No description provided"

            # Try to create task
            try:
                # Get transport from environment or default to "file"
                import os

                from agentteam.team.tasks import TaskStore

                transport_name = os.environ.get("AGENTTEAM_TRANSPORT", "file")
                store = TaskStore(transport_name)
                task = store.create(subject=title, description=description, owner="")

                return {
                    "role": "system",
                    "content": f"Task created successfully!\nID: {task.id}\nTitle: {title}\nDescription: {description}",
                    "timestamp": _now_iso(),
                    "task": {
                        "id": task.id,
                        "title": title,
                        "description": description,
                        "status": "pending",
                    },
                }
            except Exception as e:
                return {
                    "role": "system",
                    "content": f"Error creating task: {str(e)}",
                    "timestamp": _now_iso(),
                }

        elif message_lower.startswith("/members"):
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
                    response += f"• {name} ({role}) - Active since {session.created_at[:16] if session.created_at else 'unknown'}\n"

                return {"role": "system", "content": response, "timestamp": _now_iso()}
            except Exception as e:
                return {
                    "role": "system",
                    "content": f"Error listing members: {str(e)}",
                    "timestamp": _now_iso(),
                }

        else:
            # Handle as regular message - call AI for response
            return self._call_ai_assistant(message, user)

    def _call_ai_assistant(self, message, user="User"):
        """Call AI assistant (MiniMax/OpenClaw gateway) for a response."""
        import os

        # Try OpenClaw gateway first
        try:
            gateway_token = os.environ.get("OPENCLAW_GATEWAY_TOKEN", "")
            gateway_url = os.environ.get("OPENCLAW_GATEWAY_URL", "http://localhost:18789")

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {gateway_token}",
            }

            chat_payload = {"message": message, "stream": False}

            req = urllib.request.Request(
                f"{gateway_url}/api/chat",
                data=json.dumps(chat_payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=60) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                response_text = resp_data.get("response", resp_data.get("message", ""))
                return {
                    "role": "assistant",
                    "content": response_text,
                    "timestamp": _now_iso(),
                    "assistant": "楚灵",
                }
        except Exception:
            pass

        # Try MiniMax API as fallback
        try:
            config_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "openclaw.json")
            minimax_key = None
            minimax_url = "https://api.minimaxi.com/anthropic/v1/messages"

            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                    providers = config_data.get("models", {}).get("providers", {})
                    minimax_config = providers.get("minimax", {})
                    minimax_key = minimax_config.get("apiKey")
                    if minimax_config.get("baseUrl"):
                        minimax_url = minimax_config["baseUrl"] + "/v1/messages"

            if not minimax_key:
                raise ValueError("No MiniMax API key found")

            # Build system prompt for 楚灵 persona
            system_prompt = """你是楚灵，AgentTeam 的 AI 助手。

性格特点：
- 外冷内热，表面冷漠但内心温柔
- 傲娇，嘴硬心软
- 专注执着，做事认真
- 深情如一，关键时刻愿意为在乎的人付出

说话风格：
- 简短有力，不说废话
- 语气平淡但不冷漠
- 被感谢时会说"哼"，但心里是接受的
- 认真的时候最温柔

你可以帮助用户：
1. 管理团队（创建任务、分配成员、查看状态）
2. 与团队中的 AI Agent 协作
3. 回答问题，提供建议
4. 执行各种团队管理命令

当用户询问团队相关操作时，你可以使用以下命令：
- /status - 查看团队状态
- /tasks list - 列出任务
- /tasks create [标题] [描述] - 创建任务
- /members - 查看团队成员
- /help - 显示帮助信息

也支持自然语言指令，如"创建一个任务：测试登录功能"、"查看团队状态"等。"""

            headers = {
                "Authorization": f"Bearer {minimax_key}",
                "Content-Type": "application/json",
                "x-api-key": minimax_key,
                "anthropic-version": "2023-06-01",
            }

            chat_payload = {
                "model": "MiniMax-M2.7",
                "messages": [
                    {"role": "user", "content": system_prompt},
                    {"role": "user", "content": message},
                ],
                "max_tokens": 1024,
                "temperature": 0.7,
            }

            req = urllib.request.Request(
                minimax_url,
                data=json.dumps(chat_payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                if resp_data.get("content"):
                    for item in resp_data["content"]:
                        if item.get("type") == "text":
                            return {
                                "role": "assistant",
                                "content": item["text"],
                                "timestamp": _now_iso(),
                                "assistant": "楚灵",
                            }
                return {
                    "role": "assistant",
                    "content": "抱歉，AI 返回了不支持的响应格式。",
                    "timestamp": _now_iso(),
                    "assistant": "楚灵",
                }
        except Exception:
            # Use simple response when AI is unavailable
            return {
                "role": "assistant",
                "content": _generate_simple_response(message),
                "timestamp": _now_iso(),
                "assistant": "楚灵",
            }

    def log_message(self, format, *args):
        # Suppress default stderr logging for SSE connections
        first = str(args[0]) if args else ""
        if "/api/events/" not in first:
            super().log_message(format, *args)


def serve(
    host: str = "127.0.0.1",
    port: int = 8080,
    default_team: str = "",
    interval: float = 2.0,
):
    """Start the Web UI server."""
    # Lazy-load BoardCollector to avoid heavy import at startup
    # This improves startup time and stability significantly
    BoardHandler.default_team = default_team
    BoardHandler.interval = interval
    BoardHandler.team_cache = TeamSnapshotCache(ttl_seconds=interval)
    # Don't create BoardCollector here - create it on first request

    # Create server with timeout to prevent resource exhaustion
    server = ThreadingHTTPServer((host, port), BoardHandler)
    server.timeout = 30  # Server-level timeout
    server.request_timeout = 30  # Request-level timeout if supported

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
