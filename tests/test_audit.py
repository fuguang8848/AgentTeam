"""Tests for the audit logging module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from clawteam.audit import (
    AuditEvent,
    AuditEventType,
    get_audit_summary,
    log_audit_event,
    read_audit_log,
    _audit_log_path,
)


@pytest.fixture
def temp_team_data():
    """Create a temporary team data directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Mock get_data_dir from team.models to use our temp directory
        with patch("clawteam.team.models.get_data_dir", return_value=Path(tmpdir)):
            yield tmpdir


def test_audit_event_creation():
    """Test that AuditEvent can be created and serialized."""
    event = AuditEvent(
        event_id="test-123",
        event_type=AuditEventType.TASK_CREATED,
        timestamp="2026-04-26T12:00:00Z",
        actor="test-agent",
        team="test-team",
        details={"task_subject": "Test task"}
    )
    
    # Test serialization
    json_str = event.to_json()
    parsed = json.loads(json_str)
    
    assert parsed["event_id"] == "test-123"
    assert parsed["event_type"] == "task_created"
    assert parsed["actor"] == "test-agent"
    assert parsed["team"] == "test-team"
    assert parsed["details"]["task_subject"] == "Test task"


def test_log_audit_event_append_only(temp_team_data):
    """Test that log_audit_event appends to existing log without modifying history."""
    team_name = "test-team"
    
    # Log first event
    event_id1 = log_audit_event(
        team=team_name,
        event_type=AuditEventType.TASK_CREATED,
        actor="agent1",
        details={"subject": "First task"}
    )
    
    # Check log file exists and has one line
    log_path = _audit_log_path(team_name)
    assert log_path.exists()
    
    content = log_path.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    assert len(lines) == 1
    
    # Parse the first event
    first_event = json.loads(lines[0])
    assert first_event["event_id"] == event_id1
    assert first_event["event_type"] == "task_created"
    
    # Log second event
    event_id2 = log_audit_event(
        team=team_name,
        event_type=AuditEventType.TASK_COMPLETED,
        actor="agent2",
        details={"result": "success"}
    )
    
    # Check log file now has two lines
    content = log_path.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    assert len(lines) == 2
    
    # First event should be unchanged
    first_event_again = json.loads(lines[0])
    assert first_event_again == first_event
    
    # Second event should be new
    second_event = json.loads(lines[1])
    assert second_event["event_id"] == event_id2
    assert second_event["event_type"] == "task_completed"


def test_read_audit_log(temp_team_data):
    """Test reading audit log entries."""
    team_name = "test-team"
    
    # Log some events
    event_id1 = log_audit_event(
        team=team_name,
        event_type=AuditEventType.TASK_CREATED,
        actor="agent1",
        details={"subject": "Task 1"}
    )
    
    event_id2 = log_audit_event(
        team=team_name,
        event_type=AuditEventType.TASK_ASSIGNED,
        actor="system",
        target="agent2",
        details={"task_id": event_id1}
    )
    
    # Read all events
    events = read_audit_log(team_name)
    assert len(events) == 2
    assert events[0].event_id == event_id1
    assert events[1].event_id == event_id2
    
    # Read with limit
    limited_events = read_audit_log(team_name, limit=1)
    assert len(limited_events) == 1
    assert limited_events[0].event_id == event_id2  # Most recent first


def test_get_audit_summary(temp_team_data):
    """Test getting audit summary."""
    team_name = "test-team"
    
    # No events
    summary = get_audit_summary(team_name)
    assert summary["total_events"] == 0
    assert summary["event_types"] == {}
    assert summary["active_agents"] == []
    assert summary["first_event"] is None
    assert summary["last_event"] is None
    
    # Add some events
    log_audit_event(
        team=team_name,
        event_type=AuditEventType.TASK_CREATED,
        actor="agent1"
    )
    
    log_audit_event(
        team=team_name,
        event_type=AuditEventType.TASK_COMPLETED,
        actor="agent2"
    )
    
    # Get summary
    summary = get_audit_summary(team_name)
    assert summary["total_events"] == 2
    assert summary["event_types"][AuditEventType.TASK_CREATED] == 1
    assert summary["event_types"][AuditEventType.TASK_COMPLETED] == 1
    assert set(summary["active_agents"]) == {"agent1", "agent2"}
    assert summary["first_event"] is not None
    assert summary["last_event"] is not None


def test_log_audit_event_with_optional_fields(temp_team_data):
    """Test logging events with optional target, details, and context."""
    team_name = "test-team"
    
    # Log with all optional fields
    event_id = log_audit_event(
        team=team_name,
        event_type=AuditEventType.MESSAGE_SENT,
        actor="agent1",
        target="agent2",
        details={"message_type": "task_update"},
        context={"session_id": "sess-123"}
    )
    
    # Read back and verify
    events = read_audit_log(team_name)
    assert len(events) == 1
    event = events[0]
    assert event.event_id == event_id
    assert event.target == "agent2"
    assert event.details["message_type"] == "task_update"
    assert event.context["session_id"] == "sess-123"


def test_audit_log_path_validation(temp_team_data):
    """Test that audit log paths are properly validated."""
    from clawteam.paths import validate_identifier
    
    # Valid team name
    valid_team = "my-team_123"
    assert validate_identifier(valid_team, "team name") == valid_team
    
    # Invalid team name (contains slash)
    with pytest.raises(ValueError):
        validate_identifier("invalid/team", "team name")
    
    # Empty team name
    with pytest.raises(ValueError):
        validate_identifier("", "team name")


def test_timestamp_format(temp_team_data):
    """Test that timestamps are in ISO 8601 format."""
    from datetime import datetime, timezone
    
    team_name = "test-team"
    event_id = log_audit_event(
        team=team_name,
        event_type=AuditEventType.TASK_CREATED,
        actor="test"
    )
    
    log_path = _audit_log_path(team_name)
    content = log_path.read_text(encoding="utf-8")
    event = json.loads(content.strip())
    
    # Should be parseable as ISO 8601
    timestamp = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
    
    # Should be timezone aware
    assert timestamp.tzinfo is not None
    
    # Should be roughly current time
    now = datetime.now(timezone.utc)
    diff = abs((now - timestamp).total_seconds())
    assert diff < 10  # Within 10 seconds