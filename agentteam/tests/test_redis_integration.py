"""Integration tests for RedisTransport with MailboxManager."""

from __future__ import annotations

import json
import os
import pytest
from unittest.mock import MagicMock, patch

pytest.importorskip("redis")


class TestRedisTransportMailboxIntegration:
    """Test RedisTransport integration with MailboxManager."""

    def test_mailbox_uses_redis_transport_when_configured(self, tmp_path):
        """Test that MailboxManager uses RedisTransport when AGENTTEAM_TRANSPORT=redis."""
        from agentteam.team.mailbox import MailboxManager

        os.environ["AGENTTEAM_TRANSPORT"] = "redis"
        os.environ["AGENTTEAM_DATA_DIR"] = str(tmp_path / "data")

        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.lpush.return_value = 1
        mock_client.scan.return_value = (0, [])

        def mock_get_transport(name, team_name, **kwargs):
            from agentteam.transport.redis import RedisTransport
            transport = RedisTransport(team_name)
            transport._client = mock_client
            return transport

        with patch("agentteam.transport.get_transport", mock_get_transport):
            with patch("agentteam.transport.redis.RedisTransport._connect"):
                mailbox = MailboxManager("test-team")
                from agentteam.transport.redis import RedisTransport
                assert isinstance(mailbox._transport, RedisTransport)

        del os.environ["AGENTTEAM_TRANSPORT"]
        if "AGENTTEAM_DATA_DIR" in os.environ:
            del os.environ["AGENTTEAM_DATA_DIR"]

    def test_send_message_via_redis(self, tmp_path):
        """Test sending a message through RedisTransport."""
        from agentteam.team.mailbox import MailboxManager
        from agentteam.team.models import MessageType

        os.environ["AGENTTEAM_DATA_DIR"] = str(tmp_path / "data")

        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.lpush.return_value = 1

        with patch("agentteam.transport.redis.RedisTransport._connect"):
            from agentteam.transport.redis import RedisTransport
            transport = RedisTransport("test-team")
            transport._client = mock_client

            mailbox = MailboxManager("test-team", transport=transport)
            msg = mailbox.send(
                from_agent="alice",
                to="bob",
                content="Hello via Redis!",
                msg_type=MessageType.message,
            )

            assert mock_client.lpush.called
            assert msg.from_agent == "alice"
            assert msg.content == "Hello via Redis!"

        if "AGENTTEAM_DATA_DIR" in os.environ:
            del os.environ["AGENTTEAM_DATA_DIR"]

    def test_receive_message_via_redis(self, tmp_path):
        """Test receiving messages through RedisTransport."""
        from agentteam.team.mailbox import MailboxManager
        from agentteam.team.models import TeamMessage, MessageType

        os.environ["AGENTTEAM_DATA_DIR"] = str(tmp_path / "data")

        mock_msg = TeamMessage(
            type=MessageType.message,
            from_agent="alice",
            to="bob",
            content="Test message",
        )
        envelope = json.dumps({
            "timestamp": 1000,
            "uid": "abc",
            "data": mock_msg.model_dump_json(),
        }).encode("utf-8")

        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.rpop.side_effect = [envelope, None]

        with patch("agentteam.transport.redis.RedisTransport._connect"):
            from agentteam.transport.redis import RedisTransport
            transport = RedisTransport("test-team")
            transport._client = mock_client

            mailbox = MailboxManager("test-team", transport=transport)
            messages = mailbox.receive("bob", limit=10)

            assert len(messages) == 1
            assert messages[0].from_agent == "alice"

        if "AGENTTEAM_DATA_DIR" in os.environ:
            del os.environ["AGENTTEAM_DATA_DIR"]


class TestRedisMixedMode:
    """Test mixed mode: messages via Redis, config/tasks via file."""

    def test_mixed_mode_messages_redis_tasks_file(self, tmp_path):
        """Test that messages go through Redis while tasks use FileTaskStore."""
        from agentteam.team.tasks import TaskStore
        from agentteam.team.mailbox import MailboxManager

        os.environ["AGENTTEAM_TRANSPORT"] = "redis"
        os.environ["AGENTTEAM_DATA_DIR"] = str(tmp_path / "data")

        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.lpush.return_value = 1
        mock_client.scan.return_value = (0, [])

        def mock_get_transport(name, team_name, **kwargs):
            from agentteam.transport.redis import RedisTransport
            transport = RedisTransport(team_name)
            transport._client = mock_client
            return transport

        with patch("agentteam.transport.get_transport", mock_get_transport):
            with patch("agentteam.transport.redis.RedisTransport._connect"):
                mailbox = MailboxManager("test-team")
                task_store = TaskStore("test-team")
                task = task_store.create(subject="Test task", description="Mixed mode test")

                assert task.id is not None
                from agentteam.transport.redis import RedisTransport
                assert isinstance(mailbox._transport, RedisTransport)

        del os.environ["AGENTTEAM_TRANSPORT"]
        if "AGENTTEAM_DATA_DIR" in os.environ:
            del os.environ["AGENTTEAM_DATA_DIR"]


class TestRedisReconnection:
    """Test Redis connection reconnection scenarios."""

    def test_reconnect_on_ping_failure(self):
        """Test that transport attempts reconnection when ping fails."""
        from agentteam.transport.redis import RedisTransport

        mock_client = MagicMock()
        mock_client.ping.side_effect = [Exception("Connection lost"), True]

        with patch("agentteam.transport.redis.RedisTransport._connect"):
            transport = RedisTransport("test-team")
            transport._client = mock_client
            transport._reconnect_on_error()
            assert mock_client.ping.call_count >= 1

    def test_deliver_after_reconnect(self):
        """Test that deliver works after reconnection."""
        from agentteam.transport.redis import RedisTransport

        mock_client = MagicMock()
        mock_client.ping.side_effect = [Exception("Connection lost"), True]
        mock_client.lpush.return_value = 1

        with patch("agentteam.transport.redis.RedisTransport._connect"):
            transport = RedisTransport("test-team")
            transport._client = mock_client
            transport.deliver("agent1", b"test message")
            assert mock_client.lpush.called


class TestRedisDeadLetterQueue:
    """Test dead letter queue functionality."""

    def test_quarantine_malformed_message(self):
        """Test quarantining a malformed message."""
        from agentteam.transport.redis import RedisTransport

        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.lpush.return_value = 1

        with patch("agentteam.transport.redis.RedisTransport._connect"):
            transport = RedisTransport("test-team")
            transport._client = mock_client
            transport.quarantine("agent1", b"bad data", "Invalid JSON format")
            assert mock_client.lpush.called

    def test_get_dead_letters(self):
        """Test retrieving dead letters."""
        from agentteam.transport.redis import RedisTransport

        dead_entry = json.dumps({
            "timestamp": 1000,
            "uid": "abc",
            "data": "malformed",
            "error": "Invalid JSON",
        }).encode("utf-8")

        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.lrange.return_value = [dead_entry]

        with patch("agentteam.transport.redis.RedisTransport._connect"):
            transport = RedisTransport("test-team")
            transport._client = mock_client
            letters = transport.get_dead_letters("agent1", limit=10)
            assert len(letters) == 1
            assert letters[0]["error"] == "Invalid JSON"


class TestRedisPeerManagement:
    """Test peer registration and heartbeat."""

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

    def test_send_heartbeat(self):
        """Test sending heartbeat."""
        from agentteam.transport.redis import RedisTransport

        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.hset.return_value = 1

        with patch("agentteam.transport.redis.RedisTransport._connect"):
            transport = RedisTransport("test-team")
            transport._client = mock_client
            transport.send_heartbeat("agent1")
            assert mock_client.hset.called


class TestRedisEnvironmentConfig:
    """Test Redis configuration from environment."""

    def test_redis_url_from_env(self):
        """Test Redis URL configuration from environment."""
        from agentteam.transport.redis import RedisTransport

        os.environ["AGENTTEAM_REDIS_URL"] = "redis://custom-host:7000"

        with patch("agentteam.transport.redis.RedisTransport._connect"):
            transport = RedisTransport("test-team")
            assert transport._redis_url == "redis://custom-host:7000"

        del os.environ["AGENTTEAM_REDIS_URL"]

    def test_transport_factory_redis(self):
        """Test get_transport factory with redis."""
        from agentteam.transport import get_transport

        with patch("agentteam.transport.redis.RedisTransport._connect"):
            transport = get_transport("redis", "test-team")
            from agentteam.transport.redis import RedisTransport
            assert isinstance(transport, RedisTransport)