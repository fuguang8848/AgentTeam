"""Tests for Message TTL (Time-To-Live) functionality."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
class TestTTLConfig:
    """Test TTL configuration from environment."""

    def test_default_ttl_is_24_hours(self):
        """Default TTL should be 24 hours (86400 seconds)."""
        from agentteam.utils.ttl import DEFAULT_TTL_SECONDS, get_message_ttl

        with patch.dict(os.environ, {}, clear=True):
            ttl = get_message_ttl()
            assert ttl == DEFAULT_TTL_SECONDS
            assert ttl == 86400

    def test_custom_ttl_from_environment(self):
        """TTL can be set via AGENTTEAM_MESSAGE_TTL environment variable."""
        from agentteam.utils.ttl import get_message_ttl

        with patch.dict(os.environ, {"AGENTTEAM_MESSAGE_TTL": "3600"}):
            ttl = get_message_ttl()
            assert ttl == 3600

    def test_ttl_disabled_with_zero(self):
        """TTL can be disabled by setting to 0."""
        from agentteam.utils.ttl import get_message_ttl, is_ttl_enabled

        with patch.dict(os.environ, {"AGENTTEAM_MESSAGE_TTL": "0"}):
            ttl = get_message_ttl()
            assert ttl == 0
            assert not is_ttl_enabled()

    def test_invalid_ttl_falls_back_to_default(self):
        """Invalid TTL values fall back to default."""
        from agentteam.utils.ttl import get_message_ttl, DEFAULT_TTL_SECONDS

        with patch.dict(os.environ, {"AGENTTEAM_MESSAGE_TTL": "invalid"}):
            ttl = get_message_ttl()
            assert ttl == DEFAULT_TTL_SECONDS


class TestIsMessageExpired:
    """Test message expiration checking."""

    def test_recent_message_not_expired(self):
        """A recent message should not be expired."""
        from agentteam.utils.ttl import is_message_expired

        current_ms = int(time.time() * 1000)
        recent_ts = current_ms - 1000

        assert not is_message_expired(recent_ts, ttl_seconds=3600)

    def test_old_message_is_expired(self):
        """An old message should be expired."""
        from agentteam.utils.ttl import is_message_expired

        current_ms = int(time.time() * 1000)
        old_ts = current_ms - (2 * 3600 * 1000)

        assert is_message_expired(old_ts, ttl_seconds=3600)

    def test_expired_check_disabled_with_zero_ttl(self):
        """Expiration check returns False when TTL is 0."""
        from agentteam.utils.ttl import is_message_expired

        old_ts = 1000

        assert not is_message_expired(old_ts, ttl_seconds=0)


class TestTTLConfigClass:
    """Test TTLConfig dataclass."""

    def test_from_env_creates_config(self):
        """TTLConfig.from_env() creates config from environment."""
        from agentteam.utils.ttl import TTLConfig

        with patch.dict(os.environ, {"AGENTTEAM_MESSAGE_TTL": "7200"}):
            config = TTLConfig.from_env()
            assert config.ttl_seconds == 7200
            assert config.enabled

    def test_is_expired_method(self):
        """TTLConfig.is_expired() checks message expiration."""
        from agentteam.utils.ttl import TTLConfig

        config = TTLConfig(ttl_seconds=3600, enabled=True)

        current_ms = int(time.time() * 1000)
        recent_ts = current_ms - 1000
        old_ts = current_ms - (2 * 3600 * 1000)

        assert not config.is_expired(recent_ts)
        assert config.is_expired(old_ts)

    def test_disabled_config_never_expired(self):
        """Disabled TTLConfig never reports expired."""
        from agentteam.utils.ttl import TTLConfig

        config = TTLConfig(ttl_seconds=0, enabled=False)

        old_ts = 1000

        assert not config.is_expired(old_ts)

class TestFileTransportTTL:
    """Test FileTransport TTL cleanup functionality."""

    def test_cleanup_expired_messages_removes_old_files(self, tmp_path, monkeypatch):
        """cleanup_expired_messages removes files older than TTL."""
        from agentteam.transport.file import FileTransport

        monkeypatch.setenv("AGENTTEAM_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("AGENTTEAM_MESSAGE_TTL", "10")

        transport = FileTransport("test-team")

        old_ts = int(time.time() * 1000) - 15000
        old_msg = tmp_path / "teams" / "test-team" / "inboxes" / "agent1" / f"msg-{old_ts}-abc123.json"
        old_msg.parent.mkdir(parents=True, exist_ok=True)
        old_msg.write_text(json.dumps({"test": "old"}))

        recent_ts = int(time.time() * 1000)
        recent_msg = tmp_path / "teams" / "test-team" / "inboxes" / "agent1" / f"msg-{recent_ts}-def456.json"
        recent_msg.write_text(json.dumps({"test": "recent"}))

        time.sleep(0.5)

        expired_count = transport.cleanup_expired_messages("agent1")

        assert expired_count >= 1
        assert not old_msg.exists()
        assert recent_msg.exists()

    def test_cleanup_returns_zero_when_ttl_disabled(self, tmp_path, monkeypatch):
        """cleanup_expired_messages returns 0 when TTL is disabled."""
        from agentteam.transport.file import FileTransport

        monkeypatch.setenv("AGENTTEAM_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("AGENTTEAM_MESSAGE_TTL", "0")

        transport = FileTransport("test-team")

        old_ts = 1000
        old_msg = tmp_path / "teams" / "test-team" / "inboxes" / "agent1" / f"msg-{old_ts}-abc.json"
        old_msg.parent.mkdir(parents=True, exist_ok=True)
        old_msg.write_text(json.dumps({"test": "old"}))

        expired_count = transport.cleanup_expired_messages("agent1")
        assert expired_count == 0
        assert old_msg.exists()


class TestRedisTransportTTL:
    """Test RedisTransport TTL functionality."""

    def test_deliver_sets_ttl_on_inbox_key(self):
        """deliver() sets EXPIRE on inbox key when TTL is enabled."""
        from agentteam.transport.redis import RedisTransport

        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.lpush.return_value = 1
        mock_client.expire.return_value = True

        with patch("agentteam.transport.redis.RedisTransport._connect"):
            with patch.dict(os.environ, {"AGENTTEAM_MESSAGE_TTL": "3600"}):
                transport = RedisTransport("test-team")
                transport._client = mock_client

                transport.deliver("agent1", b"test message")

                assert mock_client.expire.called
                call_args = mock_client.expire.call_args
                assert call_args[0][1] == 3600

    def test_deliver_skips_ttl_when_disabled(self):
        """deliver() does not set EXPIRE when TTL is disabled."""
        from agentteam.transport.redis import RedisTransport

        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.lpush.return_value = 1

        with patch("agentteam.transport.redis.RedisTransport._connect"):
            with patch.dict(os.environ, {"AGENTTEAM_MESSAGE_TTL": "0"}):
                transport = RedisTransport("test-team")
                transport._client = mock_client

                transport.deliver("agent1", b"test message")

                assert not mock_client.expire.called

    def test_set_inbox_ttl(self):
        """set_inbox_ttl() sets TTL on existing inbox key."""
        from agentteam.transport.redis import RedisTransport

        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.exists.return_value = True
        mock_client.expire.return_value = True

        with patch("agentteam.transport.redis.RedisTransport._connect"):
            with patch.dict(os.environ, {"AGENTTEAM_MESSAGE_TTL": "7200"}):
                transport = RedisTransport("test-team")
                transport._client = mock_client

                result = transport.set_inbox_ttl("agent1")

                assert result
                assert mock_client.expire.called

    def test_cleanup_expired_messages(self):
        """cleanup_expired_messages removes expired messages from list."""
        from agentteam.transport.redis import RedisTransport

        mock_client = MagicMock()
        mock_client.ping.return_value = True

        current_ms = int(time.time() * 1000)
        expired_ts = current_ms - (2 * 3600 * 1000)
        fresh_ts = current_ms - 1000

        expired_msg = json.dumps({"timestamp": expired_ts, "uid": "abc", "data": "old"}).encode()
        fresh_msg = json.dumps({"timestamp": fresh_ts, "uid": "def", "data": "fresh"}).encode()

        mock_client.lrange.return_value = [expired_msg, fresh_msg]
        mock_client.lrem.return_value = 1

        with patch("agentteam.transport.redis.RedisTransport._connect"):
            with patch.dict(os.environ, {"AGENTTEAM_MESSAGE_TTL": "3600"}):
                transport = RedisTransport("test-team")
                transport._client = mock_client

                expired_count = transport.cleanup_expired_messages("agent1")

                assert expired_count == 1
                assert mock_client.lrem.called

    def test_cleanup_returns_zero_when_ttl_disabled(self):
        """cleanup_expired_messages returns 0 when TTL is disabled."""
        from agentteam.transport.redis import RedisTransport

        mock_client = MagicMock()
        mock_client.ping.return_value = True

        with patch("agentteam.transport.redis.RedisTransport._connect"):
            with patch.dict(os.environ, {"AGENTTEAM_MESSAGE_TTL": "0"}):
                transport = RedisTransport("test-team")
                transport._client = mock_client

                expired_count = transport.cleanup_expired_messages("agent1")

                assert expired_count == 0
                assert not mock_client.lrange.called
