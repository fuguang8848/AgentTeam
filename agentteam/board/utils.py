"""Utility functions for the board server."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentteam.board.collector import BoardCollector

_STATIC_DIR = Path(__file__).parent / "static"
_ALLOWED_PROXY_HOSTS = {
    "api.github.com",
    "github.com",
    "raw.githubusercontent.com",
}

# Lazy-loaded collector - created on first request
_collector = None


def _get_collector() -> "BoardCollector":
    """Lazily create BoardCollector on first access to avoid heavy import at startup."""
    global _collector
    if _collector is None:
        from agentteam.board.collector import BoardCollector

        _collector = BoardCollector()
    return _collector


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

    # Team management
    if "团队" in message or "team" in msg_lower:
        return "我可以帮你管理团队。使用命令：\\n/members - 查看团队成员 \\n/status - 查看团队状态 \\n/tasks - 查看任务列表"

    # Default response
    return "我理解你的意思，但我需要更多信息来帮助你。你可以试试：\\n1. 使用 /help 查看帮助 \\n2. 使用 /members 查看团队成员 \\n3. 直接描述你需要的帮助"


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """HTTP redirect handler that prevents redirects."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

    def error_handle(self, req, fp, code, msg, headers):
        return fp


def _is_blocked_hostname(hostname: str) -> bool:
    """Check if a hostname is blocked for proxy requests."""
    if not hostname:
        return True
    try:
        ipaddress.ip_address(hostname)
        return True  # Block direct IP addresses
    except ValueError:
        pass
    return hostname not in _ALLOWED_PROXY_HOSTS


def _normalize_proxy_target(target_url: str) -> str:
    """Normalize and validate proxy target URL."""
    if not target_url.startswith(("http://", "https://")):
        target_url = "https://" + target_url

    parsed = urllib.request.urlparse(target_url)
    hostname = parsed.hostname or ""

    if _is_blocked_hostname(hostname):
        raise ValueError(f"Hostname '{hostname}' is not allowed for proxy requests")

    return target_url


def _fetch_proxy_content(target_url: str) -> bytes:
    """Fetch content from a proxied URL."""
    normalized = _normalize_proxy_target(target_url)

    try:
        handler = _NoRedirectHandler()
        opener = urllib.request.build_opener(handler)
        req = urllib.request.Request(normalized, headers={"User-Agent": "AgentTeam/1.0"})

        with opener.open(req, timeout=30) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if "text/html" in content_type:
                raise ValueError("HTML content is not allowed through proxy")

            return resp.read()

    except urllib.error.HTTPError as e:
        raise ValueError(f"HTTP error: {e.code}")
    except urllib.error.URLError as e:
        raise ValueError(f"URL error: {e.reason}")
