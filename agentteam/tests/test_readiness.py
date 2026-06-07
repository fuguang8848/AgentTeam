"""Tests for AgentReadinessDetector."""

import pytest
import asyncio
import time
from typing import List

from agentteam.readiness import AgentReadinessDetector, DetectorConfig


@pytest.fixture
def detector():
    """Create a fresh detector for testing."""
    return AgentReadinessDetector("test-agent")


@pytest.fixture
def async_detector():
    """Create a fresh detector for async testing."""
    return AgentReadinessDetector("test-agent")


@pytest.mark.asyncio
async def test_detector_initial_state(detector):
    """Test detector initial state."""
    assert detector.agent_id == "test-agent"
    assert not detector.fast_path_disabled
    assert not detector.destroyed


@pytest.mark.asyncio
async def test_detector_fast_path_disabled():
    """Test Fast Path disabled setting."""
    detector = AgentReadinessDetector("test-agent")
    assert not detector.fast_path_disabled

    detector.fast_path_disabled = True
    assert detector.fast_path_disabled

    # Reset should preserve disabled state
    detector.reset()
    assert detector.fast_path_disabled


@pytest.mark.asyncio
async def test_on_screen_update_with_fast_path():
    """Test screen update detection with Fast Path enabled."""
    detector = AgentReadinessDetector("test-agent")
    detector.fast_path_disabled = False

    # Simulate startup detection
    task = asyncio.create_task(detector.wait_ready())
    await asyncio.sleep(0.1)  # Let detection start

    # Send lines with prompt marker
    lines = ["", "", ">>>", "Waiting for input"]
    detector.on_screen_update(lines, total_appended=100)

    # Wait a bit and cancel
    await asyncio.sleep(0.2)
    task.cancel()

    # Check prompt detection
    assert detector.prompt_detected


@pytest.mark.asyncio
async def test_on_screen_update_fast_path_disabled():
    """Test screen update detection with Fast Path disabled."""
    detector = AgentReadinessDetector("test-agent")
    detector.fast_path_disabled = True

    task = asyncio.create_task(detector.wait_ready())
    await asyncio.sleep(0.1)

    # Send lines - should be ignored for prompt detection
    lines = ["", "", ">>>", "Prompt marker"]
    detector.on_screen_update(lines, total_appended=100)

    await asyncio.sleep(0.2)
    task.cancel()

    # Prompt should not be detected
    assert not detector.prompt_detected


@pytest.mark.asyncio
async def test_notify_task_complete():
    """Test structured signal notification."""
    detector = AgentReadinessDetector("test-agent")

    # Start waiting
    task = asyncio.create_task(detector.wait_ready())
    await asyncio.sleep(0.1)

    # Notify task complete
    detector.notify_task_complete()

    # Should be ready
    result = await task
    assert result is True


@pytest.mark.asyncio
async def test_timeout():
    """Test detector timeout."""
    config = DetectorConfig(max_wait_ms=100)  # Very short timeout
    detector = AgentReadinessDetector("test-agent", config)

    start_time = time.time()
    result = await detector.wait_ready()
    elapsed = time.time() - start_time

    assert result is False
    assert elapsed >= 0.1  # Should time out around 100ms


@pytest.mark.asyncio
async def test_reset():
    """Test detector reset."""
    detector = AgentReadinessDetector("test-agent")

    # Trigger some state
    detector.prompt_detected = True
    detector.stable_since = time.time() * 1000

    # Reset
    detector.reset()

    # Check reset state
    assert not detector.prompt_detected
    assert detector.stable_since == 0
    assert not detector.is_first_wait


@pytest.mark.asyncio
async def test_destroy():
    """Test detector destroy."""
    detector = AgentReadinessDetector("test-agent")

    # Start waiting
    task = asyncio.create_task(detector.wait_ready())
    await asyncio.sleep(0.1)

    # Destroy
    detector.destroy()

    # Should return False
    result = await task
    assert result is False
    assert detector.destroyed


def test_config_defaults():
    """Test default configuration values."""
    config = DetectorConfig()
    assert config.max_wait_ms == 180_000
    assert config.quiescence_threshold_ms == 3_000
    assert config.post_reset_cooldown_ms == 2_000


def test_config_custom():
    """Test custom configuration values."""
    config = DetectorConfig(max_wait_ms=5000, quiescence_threshold_ms=1000, post_reset_cooldown_ms=500)
    assert config.max_wait_ms == 5000
    assert config.quiescence_threshold_ms == 1000
    assert config.post_reset_cooldown_ms == 500


@pytest.mark.asyncio
async def test_multiple_wait_calls():
    """Test multiple wait_ready calls."""
    detector = AgentReadinessDetector("test-agent")

    # First call
    task1 = asyncio.create_task(detector.wait_ready())
    await asyncio.sleep(0.1)

    # Second call should wait on same future
    task2 = asyncio.create_task(detector.wait_ready())
    await asyncio.sleep(0.1)

    # Complete
    detector.notify_task_complete()

    # Both should complete
    result1 = await task1
    result2 = await task2

    assert result1 is True
    assert result2 is True
