"""
Tests for OpenClaw SDK Backend - AgentTeam's native multi-agent coordination backend.

This module tests the openclaw_sdk_backend which provides:
1. Gateway Sessions API integration
2. Continuous running mode for agents
3. Activity broadcasting to Board server
4. Smart routing for inbox messages
"""

import queue
import subprocess
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from agentteam.spawn.openclaw_sdk_backend import (
    OpenClawSDKBackend,
    OCAProcess,
)


class TestOCAProcess:
    """Tests for OCAProcess dataclass."""

    def test_process_creation(self):
        """Test OCAProcess can be created with basic fields."""
        proc = OCAProcess(
            name="test-agent",
            session_key="test-key",
            session_id="test-session-id",
            team_name="test-team",
        )

        assert proc.name == "test-agent"
        assert proc.session_key == "test-key"
        assert proc.session_id == "test-session-id"
        assert proc.team_name == "test-team"
        assert proc.done is False
        assert proc.agent_type == "specialist"  # default value

    def test_process_with_agent_id(self):
        """Test OCAProcess with custom agent_id."""
        proc = OCAProcess(
            name="test-agent",
            session_key="test-key",
            session_id="test-session-id",
            team_name="test-team",
            agent_id="custom-agent-id",
        )

        assert proc.agent_id == "custom-agent-id"

    def test_process_task_queue(self):
        """Test OCAProcess has task queue."""
        proc = OCAProcess(
            name="test-agent",
            session_key="key",
            session_id="session",
            team_name="test-team",
        )

        assert hasattr(proc, "task_queue")
        assert isinstance(proc.task_queue, queue.Queue)

    def test_process_shutdown_event(self):
        """Test OCAProcess has shutdown event."""
        proc = OCAProcess(
            name="test-agent",
            session_key="key",
            session_id="session",
            team_name="test-team",
        )

        assert hasattr(proc, "shutdown_event")
        assert isinstance(proc.shutdown_event, threading.Event)

    def test_process_heartbeat_counter(self):
        """Test OCAProcess has heartbeat counter."""
        proc = OCAProcess(
            name="test-agent",
            session_key="key",
            session_id="session",
            team_name="test-team",
        )

        assert hasattr(proc, "heartbeat_count")
        assert proc.heartbeat_count == 0


class TestOpenClawSDKBackend:
    """Tests for OpenClawSDKBackend class."""

    def test_backend_initialization(self, tmp_path):
        """Test backend initializes with correct defaults."""
        backend = OpenClawSDKBackend()

        assert backend._processes == {}
        assert hasattr(backend._lock, "acquire")
        assert hasattr(backend._lock, "release")
        assert backend._gateway_cmd == "openclaw"  # default

    def test_backend_loads_running_agents(self, tmp_path):
        """Test backend loads running agents from registry on init."""
        # Backend should initialize without errors even if registry doesn't exist
        backend = OpenClawSDKBackend()
        assert isinstance(backend._running_agents, dict)


class TestGatewayCommunication:
    """Tests for Gateway API communication."""

    def test_gateway_call_success(self):
        """Test gateway_call returns parsed JSON response."""
        backend = OpenClawSDKBackend()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = b'{"ok": true, "key": "test-key"}'
        mock_result.stderr = b""

        with patch.object(subprocess, "run", return_value=mock_result):
            result = backend._gateway_call("test.method", params={"foo": "bar"})
            assert result["ok"] is True
            assert result["key"] == "test-key"

    def test_gateway_call_with_no_params(self):
        """Test gateway_call works with no params."""
        backend = OpenClawSDKBackend()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = b'{"ok": true}'
        mock_result.stderr = b""

        with patch.object(subprocess, "run", return_value=mock_result):
            result = backend._gateway_call("sessions.list")
            assert result["ok"] is True

    def test_gateway_call_failure(self):
        """Test gateway_call raises on failure."""
        backend = OpenClawSDKBackend()

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = b""
        mock_result.stderr = b"Gateway error"

        with patch.object(subprocess, "run", return_value=mock_result):
            with pytest.raises(RuntimeError, match="Gateway call failed"):
                backend._gateway_call("test.method")

    def test_gateway_call_timeout(self):
        """Test gateway_call handles timeout."""
        backend = OpenClawSDKBackend()

        with patch.object(subprocess, "run", side_effect=subprocess.TimeoutExpired("cmd", 1)):
            with pytest.raises(RuntimeError, match="Gateway call exception"):
                backend._gateway_call("test.method", timeout=1)


class TestContinuousRunningMode:
    """Tests for continuous running mode in SDK agents."""

    def test_continuous_mode_block_generated(self):
        """Test continuous running block is included in prompt."""
        from agentteam.spawn.openclaw_sdk_backend import _CONTINUOUS_RUN_BLOCK

        assert "Continuous Running Mode" in _CONTINUOUS_RUN_BLOCK
        assert "Do NOT exit after completing a task" in _CONTINUOUS_RUN_BLOCK

    def test_shutdown_detection_in_block(self):
        """Test shutdown detection is in continuous mode block."""
        from agentteam.spawn.openclaw_sdk_backend import _CONTINUOUS_RUN_BLOCK

        # Should detect shutdown command
        assert "shutdown" in _CONTINUOUS_RUN_BLOCK.lower()

    def test_inbox_check_in_block(self):
        """Test inbox checking is in continuous mode block."""
        from agentteam.spawn.openclaw_sdk_backend import _CONTINUOUS_RUN_BLOCK

        # Should check inbox
        assert "inbox" in _CONTINUOUS_RUN_BLOCK.lower()

    def test_await_new_tasks_in_block(self):
        """Test block mentions awaiting new tasks."""
        from agentteam.spawn.openclaw_sdk_backend import _CONTINUOUS_RUN_BLOCK

        assert "await" in _CONTINUOUS_RUN_BLOCK.lower()


class TestActivityBroadcasting:
    """Tests for activity broadcasting to Board server."""

    def test_broadcast_activity_runs_without_error(self):
        """Test activity broadcast runs without raising exceptions."""
        backend = OpenClawSDKBackend()

        # Should not raise even if board server is not running
        backend._broadcast_activity(
            agent_name="test-agent", team_name="test-team", status="started", message="Agent started"
        )

    def test_broadcast_activity_with_data(self):
        """Test activity broadcast with extra data."""
        backend = OpenClawSDKBackend()

        # Should not raise
        backend._broadcast_activity(
            agent_name="test-agent",
            team_name="test-team",
            status="task_assigned",
            message="New task",
            data={"task_id": "123"},
        )

    def test_broadcast_activity_handles_board_error(self):
        """Test broadcast handles board server errors gracefully."""
        backend = OpenClawSDKBackend()

        # Should not raise when board server is down
        with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
            backend._broadcast_activity(
                agent_name="test-agent", team_name="test-team", status="heartbeat", message="Heartbeat"
            )


class TestRunningAgentRegistry:
    """Tests for persistent running agent registry."""

    def test_register_running_agent(self, tmp_path):
        """Test registering a running agent."""
        backend = OpenClawSDKBackend()

        backend._running_agents = {}  # Start fresh
        backend._register_running_agent(
            agent_name="test-agent", session_key="test-key", team_name="test-team", agent_type="specialist"
        )

        assert "test-agent" in backend._running_agents
        assert backend._running_agents["test-agent"]["session_key"] == "test-key"
        assert backend._running_agents["test-agent"]["team_name"] == "test-team"

    def test_unregister_running_agent(self, tmp_path):
        """Test unregistering a running agent."""
        backend = OpenClawSDKBackend()

        backend._running_agents = {
            "test-agent": {
                "session_key": "test-key",
                "team_name": "test-team",
                "agent_type": "specialist",
                "registered_at": time.time(),
            }
        }

        backend._unregister_running_agent("test-agent")

        assert "test-agent" not in backend._running_agents

    def test_running_agents_file_path(self, tmp_path):
        """Test running agents file path is correct."""
        backend = OpenClawSDKBackend()

        path = backend._get_running_agents_file()
        assert path.name == "running_agents.json"


class TestSpawnProcess:
    """Tests for spawning SDK agents."""

    def test_spawn_checks_for_existing_agent(self):
        """Test spawn returns error if agent already running."""
        backend = OpenClawSDKBackend()

        # Register a running agent
        proc = OCAProcess(
            name="existing-agent",
            session_key="existing-key",
            session_id="existing-session",
            team_name="test-team",
        )
        backend._processes["existing-agent"] = proc

        result = backend.spawn(
            command=["openclaw"],
            agent_name="existing-agent",
            agent_id="agent-123",
            agent_type="specialist",
            team_name="test-team",
            prompt="Test task",
        )

        assert "already running" in result.lower()


class TestTermination:
    """Tests for agent termination."""

    def test_terminate_agent(self):
        """Test terminate marks agent as done."""
        backend = OpenClawSDKBackend()

        proc = OCAProcess(
            name="test-agent",
            session_key="test-key",
            session_id="test-session",
            team_name="test-team",
        )
        backend._processes["test-agent"] = proc

        # Mock gateway call to succeed
        with patch.object(backend, "_gateway_call", return_value={"ok": True}):
            with patch.object(backend, "_broadcast_activity"):
                result = backend.terminate("test-agent")

                assert result is True
                assert proc.done is True

    def test_terminate_nonexistent_agent(self):
        """Test terminate returns False for nonexistent agent."""
        backend = OpenClawSDKBackend()

        result = backend.terminate("nonexistent-agent")
        assert result is False


class TestSessionKeeper:
    """Tests for session keeper thread."""

    def test_keeper_sends_heartbeat(self):
        """Test keeper loop sends heartbeat to agent."""
        backend = OpenClawSDKBackend()

        proc = OCAProcess(
            name="test-agent",
            session_key="test-key",
            session_id="test-session",
            team_name="test-team",
        )

        with patch.object(backend, "_gateway_call", return_value={"ok": True}) as mock_call:
            backend._send_heartbeat(proc)

            # Should call sessions.send
            mock_call.assert_called()
            call_args = mock_call.call_args
            assert call_args[0][0] == "sessions.send"

    def test_keeper_injects_task(self):
        """Test keeper can inject task to agent."""
        backend = OpenClawSDKBackend()

        proc = OCAProcess(
            name="test-agent",
            session_key="test-key",
            session_id="test-session",
            team_name="test-team",
        )

        with patch.object(backend, "_gateway_call", return_value={"ok": True}) as mock_call:
            backend._inject_task(proc, "New task description")

            # Should call sessions.send with task
            mock_call.assert_called()
            call_args = mock_call.call_args
            assert call_args[0][0] == "sessions.send"

    def test_heartbeat_increments_count(self):
        """Test heartbeat increments the counter."""
        backend = OpenClawSDKBackend()

        proc = OCAProcess(
            name="test-agent",
            session_key="test-key",
            session_id="test-session",
            team_name="test-team",
        )
        initial_count = proc.heartbeat_count

        with patch.object(backend, "_gateway_call", return_value={"ok": True}):
            with patch.object(backend, "_broadcast_activity"):
                backend._send_heartbeat(proc)

                assert proc.heartbeat_count == initial_count + 1


class TestBackendGetProcesses:
    """Tests for backend process management."""

    def test_list_processes_empty(self):
        """Test listing processes when none exist."""
        backend = OpenClawSDKBackend()
        backend._processes = {}

        # Backend should have a way to list processes
        assert backend._processes == {}

    def test_processes_dict(self):
        """Test backend uses dict for processes."""
        backend = OpenClawSDKBackend()

        assert isinstance(backend._processes, dict)

    def test_processes_thread_safe_with_lock(self):
        """Test backend uses lock for thread safety."""
        backend = OpenClawSDKBackend()

        assert hasattr(backend, "_lock")
        assert hasattr(backend._lock, "acquire")
        assert hasattr(backend._lock, "release")


class TestGatewayCmdDetection:
    """Tests for gateway command detection."""

    def test_detect_gateway_cmd_default(self):
        """Test gateway cmd detection returns default on failure."""
        backend = OpenClawSDKBackend()

        # When health check fails, should still return "openclaw"
        with patch.object(subprocess, "run", side_effect=Exception("Failed")):
            cmd = backend._detect_gateway_cmd()
            assert cmd == "openclaw"

    def test_detect_gateway_cmd_success(self):
        """Test gateway cmd detection finds working command."""
        backend = OpenClawSDKBackend()

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch.object(subprocess, "run", return_value=mock_result):
            cmd = backend._detect_gateway_cmd()
            assert cmd == "openclaw"
