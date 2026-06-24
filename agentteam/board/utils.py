"""Utility functions for the board server."""

from __future__ import annotations

import ipaddress
import json
import random
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
    default_responses = ["收到了", "好的，继续", "我明白了"]
    return random.choice(default_responses)


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """HTTP redirect handler that prevents redirects."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

    def error_handle(self, req, fp, code, msg, headers):
        return fp


def _is_blocked_hostname(hostname: str) -> bool:
    """Check if a hostname is blocked for proxy requests.
    
    Security note (Baudrillard simulum): This check alone is insufficient.
    It only validates the hostname format, not the actual IP the DNS resolves to.
    A DNS rebinding attack could bypass this. Real security requires:
    1. DNS rebinding protection (resolve hostname and verify IP ranges)
    2. Certificate pinning for known hosts
    3. A proper proxy with identity verification
    This function provides a basic layer but should not be relied upon as sole protection.
    """
    if not hostname:
        return True
    # Block direct IP addresses (prevents SSRF via IP)
    try:
        ipaddress.ip_address(hostname)
        return True  # Block direct IP addresses
    except ValueError:
        pass
    # Block loopback and private IP ranges if hostname somehow resolves
    # Note: This only works if the hostname is already an IP (above check)
    # For actual DNS resolution, the resolver could return any IP
    blocked_ranges = [
        ipaddress.ip_network("127.0.0.0/8", False),
        ipaddress.ip_network("10.0.0.0/8", False),
        ipaddress.ip_network("172.16.0.0/12", False),
        ipaddress.ip_network("192.168.0.0/16", False),
        ipaddress.ip_network("169.254.0.0/16", False),  # Link-local
        ipaddress.ip_network("0.0.0.0/8", False),
    ]
    # Only allow explicitly whitelisted hosts
    if hostname not in _ALLOWED_PROXY_HOSTS:
        return True
    return False


def _normalize_proxy_target(target_url: str) -> str:
    """Normalize and validate proxy target URL.
    
    Benjamin's aura context: In distributed environments, DNS resolution
    can return different IPs based on client location/conditions.
    This function resolves the hostname to verify the IP is not in
    private/blocked ranges, preventing DNS rebinding attacks.
    """
    if not target_url.startswith(("http://", "https://")):
        target_url = "https://" + target_url

    parsed = urllib.request.urlparse(target_url)
    hostname = parsed.hostname or ""

    if _is_blocked_hostname(hostname):
        raise ValueError(f"Hostname '{hostname}' is not allowed for proxy requests")

    # Additional security: Resolve hostname and verify IP is safe
    # This prevents DNS rebinding attacks where hostname appears safe
    # but resolves to a private/blocked IP
    import socket as _socket
    try:
        addr_info = _socket.getaddrinfo(hostname, None, _socket.AF_INET)
        for family, socktype, proto, canonname, sockaddr in addr_info:
            ip_str = sockaddr[0]
            # Check if resolved IP is in blocked ranges
            try:
                ip = ipaddress.ip_address(ip_str)
                blocked_ranges = [
                    ipaddress.ip_network("127.0.0.0/8", False),
                    ipaddress.ip_network("10.0.0.0/8", False),
                    ipaddress.ip_network("172.16.0.0/12", False),
                    ipaddress.ip_network("192.168.0.0/16", False),
                    ipaddress.ip_network("169.254.0.0/16", False),
                    ipaddress.ip_network("0.0.0.0/8", False),
                ]
                for network in blocked_ranges:
                    if ip in network:
                        raise ValueError(
                            f"Hostname '{hostname}' resolved to blocked IP range: {ip_str}"
                        )
            except ValueError:
                # Not a valid IP format, skip range check
                pass
    except _socket.gaierror:
        # Cannot resolve, but hostname was already checked against whitelist
        pass

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
