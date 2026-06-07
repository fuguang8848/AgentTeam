"""Tests for RedisTransport."""

from __future__ import annotations

import json
import os
import pytest
from unittest.mock import MagicMock, patch

# Skip all tests if redis is not installed
pytest.importorskip("redis")


class TestRedisTransportInit:
    """Test RedisTransport initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default settings."""
        from agentteam.transport.redis import RedisTransport

        with patch("agentteam.transport.redis.RedisTransport._connect"):
            transport = RedisTransport("test-team")
            assert transport.team_name == "test-team"
            assert transport._redis_url == "redis://localhost:6379"

    def test_init_with_custom_url(self):
        """Test initialization with custom Redis URL."""
        from agentteam.transport.redis import RedisTransport

        with patch("agentteam.transport.redis.RedisTransport._connect"):
            transport = RedisTransport(
                "test-team",
                redis_url="redis://192.168.1.100:6379",
                password="secret",
                db=2,
            )
            assert transport._redis_url == "redis://192.168.1.100:6379"
            assert transport._password == "secret"
            assert transport._db == 2


class TestRedisTransportURLParsing:
    """Test Redis URL parsing."""

    def test_parse_host_simple(self):
        """Test parsing host from simple URL."""
        from agentteam.transport.redis import RedisTransport

        with patch("agentteam.transport.redis.RedisTransport._connect"):
            transport = RedisTransport("test-team", redis_url="redis://localhost:6379")
            assert transport._parse_host() == "localhost"

    def test_parse_port_simple(self):
        """Test parsing port from simple URL."""
        from agentteam.transport.redis import RedisTransport

        with patch("agentteam.transport.redis.RedisTransport._connect"):
            transport = RedisTransport("test-team", redis_url="redis://localhost:6379")
            assert transport._parse_port() == 6379


class TestRedisTransportDeliver:
    """Test message delivery."""

    def test_deliver_single_message(self):
        """Test delivering a single message."""
        from agentteam.transport.redis import RedisTransport

        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.lpush.return_value = 1

        with patch("agentteam.transport.redis.RedisTransport._connect"):
            transport = RedisTransport("test-team")
            transport._client = mock_client

            transport.deliver("agent1", b"test message")

            # Verify lpush was called
            assert mock_client.lpush.called


class TestRedisTransportFetch:
    """Test message fetching."""

    def test_fetch_consume_messages(self):
        """Test fetching and consuming messages."""
        from agentteam.transport.redis import RedisTransport

        mock_client = MagicMock()
        mock_client.ping.return_value = True

        # Simulate two messages in queue
        msg1 = json.dumps({"timestamp": 1000, "uid": "abc", "data": "hello"}).encode()
        msg2 = json.dumps({"timestamp": 1001, "uid": "def", "data": "world"}).encode()
        mock_client.rpop.side_effect = [msg1, msg2, None]

        with patch("agentteam.transport.redis.RedisTransport._connect"):
            transport = RedisTransport("test-team")
            transport._client = mock_client

            messages = transport.fetch("agent1", limit=10, consume=True)

            assert len(messages) == 2

    def test_fetch_empty_queue(self):
        """Test fetching from empty queue."""
        from agentteam.transport.redis import RedisTransport

        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.rpop.return_value = None

        with patch("agentteam.transport.redis.RedisTransport._connect"):
            transport = RedisTransport("test-team")
            transport._client = mock_client

            messages = transport.fetch("agent1", limit=10, consume=True)

            assert len(messages) == 0


class TestRedisTransportCount:
    """Test message counting."""

    def test_count_messages(self):
        """Test counting messages in queue."""
        from agentteam.transport.redis import RedisTransport

        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.llen.return_value = 5

        with patch("agentteam.transport.redis.RedisTransport._connect"):
            transport = RedisTransport("test-team")
            transport._client = mock_client

            count = transport.count("agent1")

            assert count == 5


class TestRedisTransportListRecipients:
    """Test listing recipients."""

    def test_list_recipients(self):
        """Test listing recipients with existing queues."""
        from agentteam.transport.redis import RedisTransport

        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.scan.side_effect = [
            (0, [b"agentteam:test-team:inbox:agent1", b"agentteam:test-team:inbox:agent2"]),
        ]

        with patch("agentteam.transport.redis.RedisTransport._connect"):
            transport = RedisTransport("test-team")
            transport._client = mock_client

            recipients = transport.list_recipients()

            assert "agent1" in recipients
            assert "agent2" in recipients


class TestRedisTransportBroadcast:
    """Test broadcast functionality."""

    def test_broadcast_to_all(self):
        """Test broadcasting to all recipients."""
        from agentteam.transport.redis import RedisTransport

        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.scan.side_effect = [
            (0, [b"agentteam:test-team:inbox:agent1", b"agentteam:test-team:inbox:agent2"]),
        ]
        mock_client.lpush.return_value = 1

        with patch("agentteam.transport.redis.RedisTransport._connect"):
            transport = RedisTransport("test-team")
            transport._client = mock_client

            count = transport.broadcast(b"broadcast message")

            assert count == 2


class TestRedisTransportPeers:
    """Test peer registration."""

    def test_register_peer(self):
        """Test registering a peer."""
        from agentteam.transport.redis import RedisTransport

        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.hset.return_value = 1

        with patch("agentteam.transport.redis.RedisTransport._connect"):
            transport = RedisTransport("test-team")
            transport._client = mock_client

            transport.register_peer("agent1", {"host": "192.168.1.100"})

            assert mock_client.hset.called

    def test_deregister_peer(self):
        """Test deregistering a peer."""
        from agentteam.transport.redis import RedisTransport

        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.delete.return_value = 1
        mock_client.hdel.return_value = 1

        with patch("agentteam.transport.redis.RedisTransport._connect"):
            transport = RedisTransport("test-team")
            transport._client = mock_client

            transport.deregister_peer("agent1")

            assert mock_client.delete.called


class TestRedisTransportClose:
    """Test connection close."""

    def test_close(self):
        """Test closing connection."""
        from agentteam.transport.redis import RedisTransport

        mock_client = MagicMock()
        mock_pool = MagicMock()

        with patch("agentteam.transport.redis.RedisTransport._connect"):
            transport = RedisTransport("test-team")
            transport._client = mock_client
            transport._pool = mock_pool

            transport.close()

            assert mock_client.close.called
            assert transport._client is None


class TestGetTransportFactory:
    """Test transport factory."""

    def test_get_redis_transport(self):
        """Test getting Redis transport."""
        from agentteam.transport import get_transport

        with patch("agentteam.transport.redis.RedisTransport._connect"):
            transport = get_transport("redis", "test-team")
            assert transport.team_name == "test-team"

    def test_get_file_transport_default(self):
        """Test getting file transport as default."""
        from agentteam.transport import get_transport

        transport = get_transport("unknown", "test-team")
        assert transport.team_name == "test-team"


class TestRedisKeyFunctions:
    """Test Redis key helper functions."""

    def test_key_prefix(self):
        """Test key prefix generation."""
        from agentteam.transport.redis import _key_prefix

        assert _key_prefix("myteam") == "agentteam:myteam"

    def test_inbox_key(self):
        """Test inbox key generation."""
        from agentteam.transport.redis import _inbox_key

        assert _inbox_key("myteam", "agent1") == "agentteam:myteam:inbox:agent1"
