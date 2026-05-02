"""Redis-based transport for cross-machine message delivery.

Provides a Redis-backed transport for distributed ClawTeam deployments:
- Messages are stored in Redis lists (per-agent queues)
- Supports connection pooling and automatic reconnection
- Mixed mode: messages via Redis, config/tasks via file (optional)
- SSL/TLS support for secure connections

Configuration:
    export CLAWTEAM_TRANSPORT=redis
    export CLAWTEAM_REDIS_URL=redis://192.168.1.100:6379
    export CLAWTEAM_REDIS_PASSWORD=secret  # optional
    export CLAWTEAM_REDIS_SSL=true  # enable SSL/TLS
    export CLAWTEAM_REDIS_CA_CERTS=/path/to/ca.pem  # optional CA certs
"""

from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any

from clawteam.transport.base import Transport
from clawteam.transport.claimed import ClaimedMessage
from clawteam.utils.ttl import get_message_ttl, is_ttl_enabled


def _get_redis_url() -> str:
    """Get Redis URL from environment or default."""
    return os.environ.get("CLAWTEAM_REDIS_URL", "redis://localhost:6379")


def _get_redis_password() -> str | None:
    """Get Redis password from environment."""
    return os.environ.get("CLAWTEAM_REDIS_PASSWORD")


def _get_redis_db() -> int:
    """Get Redis database number from environment."""
    db_str = os.environ.get("CLAWTEAM_REDIS_DB", "0")
    try:
        return int(db_str)
    except ValueError:
        return 0


def _get_redis_ssl() -> bool:
    """Get Redis SSL/TLS setting from environment.

    Returns:
        True if CLAWTEAM_REDIS_SSL is set to 'true', '1', or 'yes' (case-insensitive).
    """
    ssl_value = os.environ.get("CLAWTEAM_REDIS_SSL", "").lower()
    return ssl_value in ("true", "1", "yes")


def _get_redis_ca_certs() -> str | None:
    """Get Redis CA certificates path from environment.

    Returns:
        Path to CA certificates file, or None if not set.
    """
    ca_certs = os.environ.get("CLAWTEAM_REDIS_CA_CERTS")
    if ca_certs and os.path.isfile(ca_certs):
        return ca_certs
    return None


def _key_prefix(team_name: str) -> str:
    """Redis key prefix for a team."""
    return f"clawteam:{team_name}"


def _inbox_key(team_name: str, agent_name: str) -> str:
    """Redis key for an agent's inbox (list)."""
    return f"{_key_prefix(team_name)}:inbox:{agent_name}"


def _dead_letter_key(team_name: str, agent_name: str) -> str:
    """Redis key for an agent's dead letter queue."""
    return f"{_key_prefix(team_name)}:dead:{agent_name}"


def _peers_key(team_name: str) -> str:
    """Redis key for team peers registry (hash)."""
    return f"{_key_prefix(team_name)}:peers"


def _peer_key(team_name: str, agent_name: str) -> str:
    """Redis key for a single peer's metadata."""
    return f"{_key_prefix(team_name)}:peer:{agent_name}"


class RedisTransport(Transport):
    """Redis-backed transport for distributed message delivery.

    Uses Redis lists as message queues:
    - LPUSH for delivering messages (left push)
    - RPOP for consuming messages (right pop, FIFO order)
    - LLEN for counting pending messages
    - LRANGE for peeking (non-consuming read)

    Features:
    - Connection pooling via redis-py
    - Automatic reconnection on connection errors
    - Optional mixed mode (Redis for messages, file for tasks)
    """

    def __init__(
        self,
        team_name: str,
        redis_url: str | None = None,
        password: str | None = None,
        db: int | None = None,
        max_connections: int = 10,
        ssl: bool | None = None,
        ca_certs: str | None = None,
    ):
        self.team_name = team_name
        self._redis_url = redis_url or _get_redis_url()
        self._password = password or _get_redis_password()
        self._db = db if db is not None else _get_redis_db()
        self._max_connections = max_connections
        self._ssl = ssl if ssl is not None else _get_redis_ssl()
        self._ca_certs = ca_certs or _get_redis_ca_certs()
        self._client = None
        self._pool = None
        self._connect()

    def _connect(self) -> None:
        """Establish Redis connection with pooling."""
        try:
            import redis
        except ImportError:
            raise ImportError(
                "Redis transport requires 'redis' package. "
                "Install with: pip install clawteam[redis]"
            )

        self._pool = redis.ConnectionPool(
            host=self._parse_host(),
            port=self._parse_port(),
            db=self._db,
            password=self._password,
            max_connections=self._max_connections,
            decode_responses=False,  # Keep as bytes for consistency
            socket_timeout=5.0,
            socket_connect_timeout=5.0,
            retry_on_timeout=True,
        )
        self._client = redis.Redis(connection_pool=self._pool)

    def _parse_host(self) -> str:
        """Parse host from Redis URL."""
        url = self._redis_url
        if url.startswith("redis://"):
            url = url[8:]
        if "/" in url:
            url = url.split("/")[0]
        if "@" in url:
            # Handle auth in URL: user:pass@host:port
            url = url.split("@")[-1]
        if ":" in url:
            return url.split(":")[0]
        return url or "localhost"

    def _parse_port(self) -> int:
        """Parse port from Redis URL."""
        url = self._redis_url
        if url.startswith("redis://"):
            url = url[8:]
        if "/" in url:
            url = url.split("/")[0]
        if "@" in url:
            url = url.split("@")[-1]
        if ":" in url:
            try:
                return int(url.split(":")[1])
            except ValueError:
                pass
        return 6379

    def _reconnect_on_error(self) -> None:
        """Attempt to reconnect if connection is broken."""
        try:
            # Test connection with a simple ping
            self._client.ping()
        except Exception:
            # Connection is broken, try to reconnect
            try:
                self._connect()
            except Exception:
                pass  # Will retry on next operation

    def deliver(self, recipient: str, data: bytes) -> None:
        """Deliver message bytes to a recipient's Redis inbox.

        Uses LPUSH to add message to the left of the list.
        Messages are consumed from the right (RPOP) for FIFO order.

        TTL Support:
        If CLAWTEAM_MESSAGE_TTL is set (>0), the inbox key will be set to
        expire after the TTL duration. This ensures old messages are
        automatically cleaned up by Redis.
        """
        self._reconnect_on_error()
        key = _inbox_key(self.team_name, recipient)
        # Add timestamp prefix for ordering verification
        ts = int(time.time() * 1000)
        uid = uuid.uuid4().hex[:8]
        envelope = json.dumps(
            {
                "timestamp": ts,
                "uid": uid,
                "data": data.decode("utf-8", errors="replace") if isinstance(data, bytes) else data,
            }
        ).encode("utf-8")
        self._client.lpush(key, envelope)

        # Set TTL on the inbox key if enabled
        ttl = get_message_ttl()
        if ttl > 0:
            self._client.expire(key, ttl)

    def fetch(self, agent_name: str, limit: int = 10, consume: bool = True) -> list[bytes]:
        """Fetch messages from agent's Redis inbox.

        Args:
            agent_name: Agent to fetch messages for.
            limit: Maximum number of messages to fetch.
            consume: If True, remove messages from queue (RPOP).
                     If False, just peek (LRANGE).

        Returns:
            List of raw message bytes.
        """
        self._reconnect_on_error()
        key = _inbox_key(self.team_name, agent_name)

        if consume:
            messages: list[bytes] = []
            for _ in range(limit):
                envelope = self._client.rpop(key)
                if envelope is None:
                    break
                try:
                    data = json.loads(envelope)
                    raw = data.get("data", "")
                    if isinstance(raw, str):
                        messages.append(raw.encode("utf-8"))
                    else:
                        messages.append(raw)
                except json.JSONDecodeError:
                    # Raw bytes, not wrapped
                    messages.append(envelope)
            return messages
        else:
            # Peek mode: LRANGE from right side (oldest messages)
            envelopes = self._client.lrange(key, -limit, -1)
            messages: list[bytes] = []
            for envelope in envelopes:
                try:
                    data = json.loads(envelope)
                    raw = data.get("data", "")
                    if isinstance(raw, str):
                        messages.append(raw.encode("utf-8"))
                    else:
                        messages.append(raw)
                except json.JSONDecodeError:
                    messages.append(envelope)
            return messages

    def peek(self, agent_name: str, limit: int = 10) -> list[bytes]:
        """Peek at messages without consuming them."""
        return self.fetch(agent_name, limit, consume=False)

    def count(self, agent_name: str) -> int:
        """Return the number of pending messages in Redis inbox."""
        self._reconnect_on_error()
        key = _inbox_key(self.team_name, agent_name)
        return self._client.llen(key)

    def list_recipients(self) -> list[str]:
        """List all agents with non-empty inboxes.

        Uses SCAN to find all inbox keys for this team.
        """
        self._reconnect_on_error()
        pattern = f"{_key_prefix(self.team_name)}:inbox:*"
        recipients: list[str] = []
        cursor = 0
        while True:
            cursor, keys = self._client.scan(cursor, match=pattern, count=100)
            for key in keys:
                # Extract agent name from key: clawteam:team:inbox:agent
                if isinstance(key, bytes):
                    key = key.decode("utf-8")
                parts = key.split(":")
                if len(parts) >= 4:
                    recipients.append(parts[3])
            if cursor == 0:
                break
        return recipients

    def broadcast(self, data: bytes) -> int:
        """Broadcast message to all known recipients.

        Returns the number of recipients that received the message.
        """
        recipients = self.list_recipients()
        for recipient in recipients:
            self.deliver(recipient, data)
        return len(recipients)

    def register_peer(self, agent_name: str, metadata: dict[str, Any]) -> None:
        """Register a peer agent's connection metadata.

        Used for P2P discovery when agents need to connect directly.
        """
        self._reconnect_on_error()
        key = _peer_key(self.team_name, agent_name)
        self._client.hset(
            key,
            mapping={
                k: json.dumps(v) if not isinstance(v, str) else v for k, v in metadata.items()
            },
        )

    def deregister_peer(self, agent_name: str) -> None:
        """Deregister a peer agent."""
        self._reconnect_on_error()
        key = _peer_key(self.team_name, agent_name)
        self._client.delete(key)

    def get_peer(self, agent_name: str) -> dict[str, Any] | None:
        """Get a peer agent's connection metadata."""
        self._reconnect_on_error()
        key = _peer_key(self.team_name, agent_name)
        data = self._client.hgetall(key)
        if not data:
            return None
        result = {}
        for k, v in data.items():
            if isinstance(k, bytes):
                k = k.decode("utf-8")
            if isinstance(v, bytes):
                v = v.decode("utf-8")
            try:
                result[k] = json.loads(v)
            except json.JSONDecodeError:
                result[k] = v
        return result

    def close(self) -> None:
        """Close Redis connection and release resources."""
        if self._client:
            self._client.close()
            self._client = None
        if self._pool:
            self._pool.disconnect()
            self._pool = None

    def send_heartbeat(self, agent_name: str) -> None:
        """Update heartbeat timestamp for an agent."""
        self._reconnect_on_error()
        key = _peer_key(self.team_name, agent_name)
        now_ms = int(time.time() * 1000)
        self._client.hset(key, "heartbeatAtMs", str(now_ms))

    def list_peers(self) -> list[dict[str, Any]]:
        """List all registered peers for the team."""
        self._reconnect_on_error()
        peers_key = _peers_key(self.team_name)
        data = self._client.hgetall(peers_key)
        peers: list[dict[str, Any]] = []
        for agent, meta in data.items():
            if isinstance(agent, bytes):
                agent = agent.decode("utf-8")
            if isinstance(meta, bytes):
                meta = meta.decode("utf-8")
            try:
                peer_data = json.loads(meta)
                peer_data["agent"] = agent
                peers.append(peer_data)
            except json.JSONDecodeError:
                peers.append({"agent": agent, "raw": meta})
        return peers

    def quarantine(self, agent_name: str, data: bytes, error: str) -> None:
        """Move a malformed message to dead letter queue."""
        self._reconnect_on_error()
        key = _dead_letter_key(self.team_name, agent_name)
        ts = int(time.time() * 1000)
        uid = uuid.uuid4().hex[:8]
        dead_entry = json.dumps(
            {
                "timestamp": ts,
                "uid": uid,
                "data": data.decode("utf-8", errors="replace") if isinstance(data, bytes) else data,
                "error": error,
                "quarantinedAtMs": ts,
            }
        ).encode("utf-8")
        self._client.lpush(key, dead_entry)

    def get_dead_letters(self, agent_name: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get quarantined messages for an agent."""
        self._reconnect_on_error()
        key = _dead_letter_key(self.team_name, agent_name)
        entries = self._client.lrange(key, 0, limit - 1)
        letters: list[dict[str, Any]] = []
        for entry in entries:
            try:
                data = json.loads(entry)
                letters.append(data)
            except json.JSONDecodeError:
                letters.append({"raw": entry})
        return letters

    def clear_inbox(self, agent_name: str) -> int:
        """Clear all messages from an agent inbox."""
        self._reconnect_on_error()
        key = _inbox_key(self.team_name, agent_name)
        count = self._client.llen(key)
        self._client.delete(key)
        return count

    def set_inbox_ttl(self, agent_name: str, ttl_seconds: int | None = None) -> bool:
        """Set TTL on an agent's inbox key.

        Args:
            agent_name: Agent whose inbox to set TTL on.
            ttl_seconds: TTL in seconds. If None, uses CLAWTEAM_MESSAGE_TTL.

        Returns:
            True if TTL was set, False if key doesn't exist or TTL disabled.
        """
        self._reconnect_on_error()
        if ttl_seconds is None:
            ttl_seconds = get_message_ttl()
        if ttl_seconds <= 0:
            return False
        key = _inbox_key(self.team_name, agent_name)
        if self._client.exists(key):
            self._client.expire(key, ttl_seconds)
            return True
        return False

    def cleanup_expired_messages(self, agent_name: str) -> int:
        """Clean up expired messages from an agent's inbox.

        Note: Redis automatically handles TTL expiration, but this method
        can be used to manually check and remove expired messages based on
        their internal timestamp.

        Args:
            agent_name: Agent whose inbox to clean up.

        Returns:
            Number of expired messages removed.
        """
        self._reconnect_on_error()
        ttl = get_message_ttl()
        if ttl <= 0:
            return 0  # TTL disabled

        key = _inbox_key(self.team_name, agent_name)
        messages = self._client.lrange(key, 0, -1)
        expired_count = 0

        for msg in messages:
            try:
                data = json.loads(msg)
                timestamp = data.get("timestamp", 0)
                if timestamp > 0:
                    # Check if message is expired based on its timestamp
                    current_ms = int(time.time() * 1000)
                    age_seconds = (current_ms - timestamp) / 1000
                    if age_seconds > ttl:
                        # Remove this specific message (LREM)
                        self._client.lrem(key, 1, msg)
                        expired_count += 1
            except (json.JSONDecodeError, KeyError):
                continue

        return expired_count

    def __enter__(self) -> "RedisTransport":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
