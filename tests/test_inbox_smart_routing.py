"""Tests for inbox smart routing - direct delivery to running SDK agents."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from clawteam.team.models import get_data_dir


class TestDeliverToRunningAgent:
    """Tests for _deliver_to_running_agent function."""

    def test_delivers_to_running_agent_via_gateway(self, tmp_path, monkeypatch):
        """When agent is running, message is sent via Gateway API."""
        from clawteam.cli.commands import _deliver_to_running_agent

        # Setup: Create a fake running_agents.json
        data_dir = tmp_path / ".clawteam"
        data_dir.mkdir(exist_ok=True)
        monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(data_dir))

        running_agents_file = data_dir / "running_agents.json"
        running_agents_file.write_text(
            json.dumps(
                {
                    "agents": {
                        "test-agent": {
                            "session_key": "agent:main:dashboard:test-session-123",
                            "session_id": "test-session-123",
                            "team_name": "test-team",
                            "agent_type": "specialist",
                            "started_at": time.time(),
                        }
                    }
                }
            )
        )

        # Mock subprocess.run for Gateway API call
        mock_subprocess = MagicMock()
        mock_subprocess.return_value = MagicMock(returncode=0, stdout=b'{"ok": true}', stderr=b'')
        monkeypatch.setattr("subprocess.run", mock_subprocess)

        # Mock activity broadcast
        mock_broadcast = MagicMock()
        monkeypatch.setattr(
            "clawteam.cli.commands._broadcast_activity_to_board", mock_broadcast
        )

        # Call the function
        result = _deliver_to_running_agent(
            agent_name="test-agent", team_name="test-team", content="Hello!", from_agent="leader"
        )

        # Assert
        assert result is True
        mock_subprocess.assert_called_once()
        mock_broadcast.assert_called_once()

    def test_falls_back_to_file_when_agent_not_running(self, tmp_path, monkeypatch):
        """When agent is not running, function returns False to fall back to file."""
        from clawteam.cli.commands import _deliver_to_running_agent

        # Setup: Empty running_agents.json
        data_dir = tmp_path / ".clawteam"
        data_dir.mkdir(exist_ok=True)
        monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(data_dir))

        running_agents_file = data_dir / "running_agents.json"
        running_agents_file.write_text(json.dumps({}))  # No agents running

        # No Gateway API call should be made
        mock_urlopen = MagicMock()
        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

        # Call the function
        result = _deliver_to_running_agent(
            agent_name="unknown-agent", team_name="test-team", content="Hello!", from_agent="leader"
        )

        # Assert: Should return False to indicate fallback to file
        assert result is False
        mock_urlopen.assert_not_called()

    def test_falls_back_on_gateway_error(self, tmp_path, monkeypatch):
        """When Gateway API fails, function returns False."""
        from clawteam.cli.commands import _deliver_to_running_agent

        # Setup: Running agent exists
        data_dir = tmp_path / ".clawteam"
        data_dir.mkdir(exist_ok=True)
        monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(data_dir))

        running_agents_file = data_dir / "running_agents.json"
        running_agents_file.write_text(
            json.dumps(
                {
                    "agents": {
                        "test-agent": {
                            "session_key": "agent:main:dashboard:test-session-123",
                            "session_id": "test-session-123",
                            "team_name": "test-team",
                            "agent_type": "specialist",
                            "started_at": time.time(),
                        }
                    }
                }
            )
        )

        # Mock Gateway API to raise exception
        mock_urlopen = MagicMock(side_effect=Exception("Gateway timeout"))
        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

        # Call the function
        result = _deliver_to_running_agent(
            agent_name="test-agent", team_name="test-team", content="Hello!", from_agent="leader"
        )

        # Assert: Should return False on error
        assert result is False


class TestBroadcastActivityToBoard:
    """Tests for _broadcast_activity_to_board function."""

    def test_broadcasts_activity_to_board_server(self, tmp_path, monkeypatch):
        """Activity is broadcast to Board server via HTTP POST."""
        from clawteam.cli.commands import _broadcast_activity_to_board

        # Mock HTTP request
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'{"ok": true}'

        mock_urlopen = MagicMock(return_value=mock_response)
        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

        # Call the function (returns None, but should not raise)
        _broadcast_activity_to_board(
            agent_name="test-agent",
            team_name="test-team",
            status="task_assigned",
            message="New task assigned",
        )

        # Assert
        mock_urlopen.assert_called_once()

        # Verify the request
        call_args = mock_urlopen.call_args
        request = call_args[0][0]

        assert request.full_url == "http://127.0.0.1:8080/api/agents/activity"
        assert request.method == "POST"

        # Parse body
        body = json.loads(request.data.decode())
        assert body["team_name"] == "test-team"
        assert body["agent_name"] == "test-agent"
        assert body["status"] == "task_assigned"
        assert body["message"] == "New task assigned"
        # timestamp is added by board server, not by CLI

    def test_returns_false_on_board_server_error(self, tmp_path, monkeypatch):
        """Returns False when Board server is unavailable."""
        from clawteam.cli.commands import _broadcast_activity_to_board

        # Mock HTTP request to fail
        mock_urlopen = MagicMock(side_effect=Exception("Connection refused"))
        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

        # Call the function - it silently fails (returns None)
        result = _broadcast_activity_to_board(
            agent_name="test-agent",
            team_name="test-team",
            status="task_assigned",
            message="New task",
        )

        # Assert - function returns None (void), but should not raise
        assert result is None


class TestActivityEventTypes:
    """Tests for different activity event types."""

    def test_completed_event(self, tmp_path, monkeypatch):
        """Completed event is broadcast correctly."""
        from clawteam.cli.commands import _broadcast_activity_to_board

        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'{"ok": true}'
        mock_urlopen = MagicMock(return_value=mock_response)
        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

        _broadcast_activity_to_board(
            agent_name="test-agent",
            team_name="test-team",
            status="completed",
            message="Task completed successfully",
        )

        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        body = json.loads(request.data.decode())

        assert body["status"] == "completed"

    def test_started_event(self, tmp_path, monkeypatch):
        """Started event is broadcast correctly."""
        from clawteam.cli.commands import _broadcast_activity_to_board

        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'{"ok": true}'
        mock_urlopen = MagicMock(return_value=mock_response)
        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

        _broadcast_activity_to_board(
            agent_name="test-agent",
            team_name="test-team",
            status="started",
            message="Agent started",
        )

        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        body = json.loads(request.data.decode())

        assert body["status"] == "started"

    def test_terminated_event(self, tmp_path, monkeypatch):
        """Terminated event is broadcast correctly."""
        from clawteam.cli.commands import _broadcast_activity_to_board

        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'{"ok": true}'
        mock_urlopen = MagicMock(return_value=mock_response)
        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

        _broadcast_activity_to_board(
            agent_name="test-agent",
            team_name="test-team",
            status="terminated",
            message="Agent terminated by leader",
        )

        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        body = json.loads(request.data.decode())

        assert body["status"] == "terminated"


class TestSmartRoutingIntegration:
    """Integration tests for smart routing with file fallback."""

    def test_routing_skips_non_sdk_agents(self, tmp_path, monkeypatch):
        """Non-SDK agents (tmux, subprocess) are not routed via Gateway."""
        from clawteam.cli.commands import _deliver_to_running_agent

        # Setup: Agent registered but with tmux backend type
        data_dir = tmp_path / ".clawteam"
        data_dir.mkdir(exist_ok=True)
        monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(data_dir))

        running_agents_file = data_dir / "running_agents.json"
        running_agents_file.write_text(
            json.dumps(
                {
                    "tmux-agent": {
                        "session_key": "tmux/test-session",
                        "session_id": "test-session",
                        "team_name": "test-team",
                        "agent_type": "tmux",  # tmux backend, not SDK
                        "started_at": time.time(),
                    }
                }
            )
        )

        mock_urlopen = MagicMock()
        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

        # Should return False (fall back to file) because tmux agents
        # don't have SDK session keys
        result = _deliver_to_running_agent(
            agent_name="tmux-agent", team_name="test-team", content="Hello!", from_agent="leader"
        )

        assert result is False
        mock_urlopen.assert_not_called()
