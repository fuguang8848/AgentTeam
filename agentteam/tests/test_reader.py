"""Tests for output reader system."""

import pytest
import tempfile
from pathlib import Path

from agentteam.reader import (
    OutputReaderManager, 
    OutputEvent, 
    OutputEventType,
    TokenUsage
)


class MockReader:
    """Mock reader for testing."""
    
    def __init__(self, provider_id: str = "test-provider"):
        self._provider_id = provider_id
        self._watching = {}
    
    @property
    def provider_id(self) -> str:
        return self._provider_id
    
    def start_watching(self, session_id: str, work_dir: str) -> None:
        self._watching[session_id] = work_dir
    
    def bind_conversation_id(self, session_id: str, conversation_id: str) -> None:
        pass
    
    def stop_watching(self, session_id: str) -> None:
        self._watching.pop(session_id, None)
    
    def cleanup(self) -> None:
        self._watching.clear()


def test_output_reader_manager_initialization():
    """Test OutputReaderManager initialization."""
    manager = OutputReaderManager()
    assert manager._readers == {}
    assert manager._session_provider_map == {}


def test_register_reader():
    """Test reader registration."""
    manager = OutputReaderManager()
    reader = MockReader("test-provider")
    
    manager.register_reader(reader)
    
    assert "test-provider" in manager._readers
    assert manager._readers["test-provider"] is reader


def test_start_watching_with_reader():
    """Test start watching when reader exists."""
    manager = OutputReaderManager()
    reader = MockReader("test-provider")
    manager.register_reader(reader)
    
    manager.start_watching("session-1", "test-provider", "/tmp/workdir")
    
    assert "session-1" in manager._session_provider_map
    assert manager._session_provider_map["session-1"] == "test-provider"
    assert "session-1" in reader._watching


def test_start_watching_without_reader():
    """Test start watching when no reader exists (should silently skip)."""
    manager = OutputReaderManager()
    
    # Should not raise exception
    manager.start_watching("session-1", "unknown-provider", "/tmp/workdir")
    
    assert "session-1" not in manager._session_provider_map


def test_has_active_reader():
    """Test has_active_reader method."""
    manager = OutputReaderManager()
    reader = MockReader("test-provider")
    manager.register_reader(reader)
    
    # No active reader yet
    assert not manager.has_active_reader("session-1")
    
    # Start watching
    manager.start_watching("session-1", "test-provider", "/tmp/workdir")
    assert manager.has_active_reader("session-1")
    
    # Different session
    assert not manager.has_active_reader("session-2")


def test_stop_watching():
    """Test stop watching."""
    manager = OutputReaderManager()
    reader = MockReader("test-provider")
    manager.register_reader(reader)
    
    # Start watching
    manager.start_watching("session-1", "test-provider", "/tmp/workdir")
    assert "session-1" in manager._session_provider_map
    
    # Stop watching
    manager.stop_watching("session-1")
    assert "session-1" not in manager._session_provider_map
    assert "session-1" not in reader._watching


def test_stop_watching_unknown_session():
    """Test stop watching unknown session (should not raise)."""
    manager = OutputReaderManager()
    
    # Should not raise exception
    manager.stop_watching("unknown-session")


def test_on_conversation_id_detected():
    """Test conversation ID detection."""
    manager = OutputReaderManager()
    reader = MockReader("test-provider")
    manager.register_reader(reader)
    
    # Start watching first
    manager.start_watching("session-1", "test-provider", "/tmp/workdir")
    
    # Should not raise when called
    manager.on_conversation_id_detected("session-1", "conversation-123")


def test_on_conversation_id_detected_no_session():
    """Test conversation ID detection for unknown session."""
    manager = OutputReaderManager()
    
    # Should not raise
    manager.on_conversation_id_detected("unknown-session", "conversation-123")


def test_cleanup():
    """Test manager cleanup."""
    manager = OutputReaderManager()
    reader1 = MockReader("provider-1")
    reader2 = MockReader("provider-2")
    
    manager.register_reader(reader1)
    manager.register_reader(reader2)
    
    manager.start_watching("session-1", "provider-1", "/tmp/workdir1")
    manager.start_watching("session-2", "provider-2", "/tmp/workdir2")
    
    # Add a callback
    callback_called = []
    manager.register_callback(lambda event: callback_called.append(event))
    
    # Cleanup
    manager.cleanup()
    
    # All should be cleared
    assert manager._readers == {}
    assert manager._session_provider_map == {}
    assert manager._callbacks == []


def test_output_event_creation():
    """Test OutputEvent creation."""
    event = OutputEvent(
        session_id="session-1",
        event_type=OutputEventType.MESSAGE,
        timestamp=1234567890.0,
        content="Hello, world!"
    )
    
    assert event.session_id == "session-1"
    assert event.event_type == OutputEventType.MESSAGE
    assert event.timestamp == 1234567890.0
    assert event.content == "Hello, world!"
    assert event.metadata == {}
    assert event.token_usage is None


def test_output_event_with_metadata():
    """Test OutputEvent with metadata."""
    metadata = {"tool": "bash", "duration": 1.5}
    token_usage = TokenUsage(input_tokens=100, output_tokens=50)
    
    event = OutputEvent(
        session_id="session-1",
        event_type=OutputEventType.TOOL_CALL,
        timestamp=1234567890.0,
        content="Running command",
        metadata=metadata,
        token_usage=token_usage
    )
    
    assert event.metadata == metadata
    assert event.token_usage == token_usage


def test_output_event_default_timestamp():
    """Test OutputEvent with default timestamp."""
    event = OutputEvent(
        session_id="session-1",
        event_type=OutputEventType.MESSAGE,
        content="Test"
    )
    
    # Should have current timestamp
    assert event.timestamp is not None
    assert isinstance(event.timestamp, float)


def test_token_usage():
    """Test TokenUsage dataclass."""
    usage = TokenUsage(
        input_tokens=1000,
        output_tokens=500,
        total_tokens=1500,
        input_cost=0.01,
        output_cost=0.02,
        total_cost=0.03
    )
    
    assert usage.input_tokens == 1000
    assert usage.output_tokens == 500
    assert usage.total_tokens == 1500
    assert usage.input_cost == 0.01
    assert usage.output_cost == 0.02
    assert usage.total_cost == 0.03


def test_token_usage_defaults():
    """Test TokenUsage with defaults."""
    usage = TokenUsage()
    
    assert usage.input_tokens == 0
    assert usage.output_tokens == 0
    assert usage.total_tokens == 0
    assert usage.input_cost == 0.0
    assert usage.output_cost == 0.0
    assert usage.total_cost == 0.0


def test_emit_event_with_callbacks():
    """Test emit_event with registered callbacks."""
    manager = OutputReaderManager()
    
    received_events = []
    
    def callback(event: OutputEvent):
        received_events.append(event)
    
    manager.register_callback(callback)
    
    event = OutputEvent(
        session_id="session-1",
        event_type=OutputEventType.MESSAGE,
        content="Test event"
    )
    
    manager.emit_event(event)
    
    assert len(received_events) == 1
    assert received_events[0] == event


def test_emit_event_callback_error():
    """Test emit_event with callback that raises error."""
    manager = OutputReaderManager()
    
    def bad_callback(event: OutputEvent):
        raise ValueError("Callback error")
    
    manager.register_callback(bad_callback)
    
    # Should not raise
    event = OutputEvent(
        session_id="session-1",
        event_type=OutputEventType.MESSAGE,
        content="Test"
    )
    
    manager.emit_event(event)