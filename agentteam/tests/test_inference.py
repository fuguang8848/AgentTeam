"""Tests for StateInference."""

import pytest
import time

from agentteam.parser.inference import StateInference, SessionStatus, ProviderStateConfig


@pytest.fixture
def inference():
    """Create a fresh inference engine."""
    return StateInference()


@pytest.fixture
def session_config():
    """Create session configuration."""
    return ProviderStateConfig(
        startup_pattern=r"Welcome to CLI",
        idle_timeout_ms=10_000,
        possible_stuck_ms=5_000,
        stuck_intervention_ms=15_000,
        startup_stuck_ms=3_000,
    )


def test_state_inference_initialization(inference):
    """Test StateInference initialization."""
    assert inference._session_status == {}
    assert inference._startup_phase == set()
    assert inference._removed_sessions == set()


def test_register_session_config(inference, session_config):
    """Test registering session configuration."""
    inference.register_session_config("session-1", session_config)

    config = inference.get_config("session-1")
    assert config.startup_pattern == "Welcome to CLI"
    assert config.idle_timeout_ms == 10_000
    assert config.possible_stuck_ms == 5_000
    assert config.stuck_intervention_ms == 15_000
    assert config.startup_stuck_ms == 3_000


def test_register_session_config_default(inference):
    """Test registering session with default configuration."""
    inference.register_session_config("session-1")

    config = inference.get_config("session-1")
    assert config == ProviderStateConfig()


def test_set_session_status(inference):
    """Test manually setting session status."""
    inference.set_session_status("session-1", SessionStatus.RUNNING)

    assert inference.get_session_status("session-1") == SessionStatus.RUNNING
    assert "session-1" not in inference._awaiting_user_input


def test_set_session_status_waiting_input(inference):
    """Test setting session status to WAITING_INPUT."""
    inference.set_session_status("session-1", SessionStatus.WAITING_INPUT)

    assert inference.get_session_status("session-1") == SessionStatus.WAITING_INPUT
    assert "session-1" in inference._awaiting_user_input


def test_mark_awaiting_user_input(inference):
    """Test marking session as awaiting user input."""
    inference.set_session_status("session-1", SessionStatus.RUNNING)
    inference.mark_awaiting_user_input("session-1")

    assert inference.get_session_status("session-1") == SessionStatus.WAITING_INPUT
    assert "session-1" in inference._awaiting_user_input


def test_mark_work_started(inference):
    """Test marking work started."""
    inference.set_session_status("session-1", SessionStatus.WAITING_INPUT)
    inference.mark_work_started("session-1")

    assert inference.get_session_status("session-1") == SessionStatus.RUNNING
    assert "session-1" not in inference._awaiting_user_input


def test_mark_work_started_resets_notifications(inference):
    """Test mark_work_started resets stuck notifications."""
    inference.set_session_status("session-1", SessionStatus.STUCK)
    inference._notified_stuck.add("session-1")
    inference._notified_possible_stuck.add("session-1")

    inference.mark_work_started("session-1")

    assert "session-1" not in inference._notified_stuck
    assert "session-1" not in inference._notified_possible_stuck
    assert inference.get_session_status("session-1") == SessionStatus.RUNNING


def test_check_startup_pattern(inference, session_config):
    """Test checking startup pattern."""
    inference.register_session_config("session-1", session_config)
    inference._startup_phase.add("session-1")

    # Match pattern
    result = inference.check_startup_pattern("session-1", "Welcome to CLI v1.0")
    assert result is True
    assert "session-1" not in inference._startup_phase
    assert inference.get_session_status("session-1") == SessionStatus.RUNNING


def test_check_startup_pattern_no_match(inference, session_config):
    """Test checking startup pattern with no match."""
    inference.register_session_config("session-1", session_config)
    inference._startup_phase.add("session-1")

    # No match
    result = inference.check_startup_pattern("session-1", "Some other text")
    assert result is False
    assert "session-1" in inference._startup_phase


def test_check_startup_pattern_no_startup_phase(inference, session_config):
    """Test checking startup pattern when not in startup phase."""
    inference.register_session_config("session-1", session_config)
    # Not in startup phase
    result = inference.check_startup_pattern("session-1", "Welcome to CLI")
    assert result is False


def test_receive_output(inference):
    """Test receiving output."""
    inference.receive_output("session-1", "Hello world")

    assert "session-1" in inference._last_output_time
    assert inference._last_output_time["session-1"] > 0


def test_receive_output_removed_session(inference):
    """Test receiving output for removed session."""
    inference._removed_sessions.add("session-1")

    # Should not update last output time
    inference.receive_output("session-1", "Hello world")
    assert "session-1" not in inference._last_output_time


def test_check_stuck_status_startup_stuck(inference, session_config):
    """Test checking stuck status for startup stuck."""
    inference.register_session_config("session-1", session_config)
    inference.set_session_status("session-1", SessionStatus.RUNNING)
    inference._startup_phase.add("session-1")
    inference._last_output_time["session-1"] = time.time() - 4  # 4 seconds ago

    # Set short startup stuck time for test
    config = inference.get_config("session-1")
    config.startup_stuck_ms = 100

    updated = inference.check_stuck_status()

    assert "session-1" in updated
    assert updated["session-1"] == SessionStatus.STUCK
    assert "session-1" in inference._notified_startup_stuck


def test_check_stuck_status_possible_stuck(inference, session_config):
    """Test checking stuck status for possible stuck."""
    inference.register_session_config("session-1", session_config)
    inference.set_session_status("session-1", SessionStatus.RUNNING)
    inference._last_output_time["session-1"] = time.time() - 3  # 3 seconds ago

    # Set thresholds: possible_stuck_ms < idle_duration < stuck_intervention_ms
    config = inference.get_config("session-1")
    config.possible_stuck_ms = 100
    config.stuck_intervention_ms = 5000

    updated = inference.check_stuck_status()

    assert "session-1" in updated
    assert updated["session-1"] == SessionStatus.POSSIBLE_STUCK
    assert "session-1" in inference._notified_possible_stuck


def test_check_stuck_status_stuck(inference, session_config):
    """Test checking stuck status for stuck."""
    inference.register_session_config("session-1", session_config)
    inference.set_session_status("session-1", SessionStatus.RUNNING)
    inference._last_output_time["session-1"] = time.time() - 3  # 3 seconds ago

    # Set short thresholds for test
    config = inference.get_config("session-1")
    config.stuck_intervention_ms = 100

    updated = inference.check_stuck_status()

    assert "session-1" in updated
    assert updated["session-1"] == SessionStatus.STUCK
    assert "session-1" in inference._notified_stuck


def test_check_stuck_status_idle_timeout(inference, session_config):
    """Test checking stuck status for idle timeout."""
    inference.register_session_config("session-1", session_config)
    inference.set_session_status("session-1", SessionStatus.RUNNING)
    inference._last_output_time["session-1"] = time.time() - 3  # 3 seconds ago

    # Set short idle timeout for test
    config = inference.get_config("session-1")
    config.idle_timeout_ms = 100

    updated = inference.check_stuck_status()

    assert "session-1" in updated
    assert updated["session-1"] == SessionStatus.WAITING_INPUT
    assert "session-1" in inference._awaiting_user_input


def test_check_stuck_status_completed_session(inference):
    """Test checking stuck status for completed session."""
    inference.set_session_status("session-1", SessionStatus.COMPLETE)
    inference._last_output_time["session-1"] = time.time() - 10

    updated = inference.check_stuck_status()

    assert "session-1" not in updated


def test_remove_session(inference):
    """Test removing session."""
    inference.set_session_status("session-1", SessionStatus.RUNNING)
    inference._last_output_time["session-1"] = time.time()
    inference._notified_stuck.add("session-1")
    inference._startup_phase.add("session-1")
    inference._awaiting_user_input.add("session-1")

    inference.remove_session("session-1")

    assert inference.get_session_status("session-1") is None
    assert "session-1" not in inference._last_output_time
    assert "session-1" not in inference._notified_stuck
    assert "session-1" not in inference._startup_phase
    assert "session-1" not in inference._awaiting_user_input
    assert "session-1" in inference._removed_sessions


def test_status_callback(inference):
    """Test status change callbacks."""
    callbacks_received = []

    def callback(session_id: str, status: SessionStatus):
        callbacks_received.append((session_id, status))

    inference.add_status_callback(callback)

    inference.set_session_status("session-1", SessionStatus.RUNNING)

    assert len(callbacks_received) == 1
    assert callbacks_received[0] == ("session-1", SessionStatus.RUNNING)


def test_status_callback_error(inference):
    """Test status callback with error."""

    def bad_callback(session_id: str, status: SessionStatus):
        raise ValueError("Callback error")

    inference.add_status_callback(bad_callback)

    # Should not raise
    inference.set_session_status("session-1", SessionStatus.RUNNING)


def test_default_provider_config():
    """Test default provider configuration."""
    config = ProviderStateConfig()

    assert config.startup_pattern == ""
    assert config.idle_timeout_ms == 300_000
    assert config.possible_stuck_ms == 120_000
    assert config.stuck_intervention_ms == 300_000
    assert config.startup_stuck_ms == 60_000


def test_custom_provider_config():
    """Test custom provider configuration."""
    config = ProviderStateConfig(
        startup_pattern="CLI Ready",
        idle_timeout_ms=5000,
        possible_stuck_ms=2000,
        stuck_intervention_ms=10000,
        startup_stuck_ms=1000,
    )

    assert config.startup_pattern == "CLI Ready"
    assert config.idle_timeout_ms == 5000
    assert config.possible_stuck_ms == 2000
    assert config.stuck_intervention_ms == 10000
    assert config.startup_stuck_ms == 1000
