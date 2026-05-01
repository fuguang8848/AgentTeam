"""Tests for the alerts module - matching current AlertManager API."""

import pytest

from clawteam.alerts import (
    Alert,
    AlertSeverity,
    AlertState,
    AlertManager,
    AlertRule,
    AlertChannel,
    create_alert,
    get_active_alerts,
    acknowledge_alert,
    evaluate_alerts,
)


@pytest.fixture
def alert_manager():
    """Create a fresh AlertManager for testing."""
    manager = AlertManager()
    # Clear any existing alerts
    manager._alerts.clear()
    manager._rules.clear()
    return manager


def test_create_alert(alert_manager):
    """Test creating a basic alert."""
    alert = create_alert(
        name="test_alert",
        message="Test alert message",
        severity=AlertSeverity.WARNING,
    )
    
    assert isinstance(alert, Alert)
    assert alert.name == "test_alert"
    assert alert.message == "Test alert message"
    assert alert.severity == AlertSeverity.WARNING
    assert alert.state == AlertState.ACTIVE


def test_get_active_alerts(alert_manager):
    """Test getting active alerts."""
    # Create some alerts
    alert1 = create_alert(
        name="alert1",
        message="First alert",
        severity=AlertSeverity.INFO,
    )
    alert2 = create_alert(
        name="alert2",
        message="Second alert",
        severity=AlertSeverity.WARNING,
    )
    
    active = get_active_alerts()
    assert len(active) >= 2
    names = [a.name for a in active]
    assert "alert1" in names
    assert "alert2" in names


def test_acknowledge_alert(alert_manager):
    """Test acknowledging an alert."""
    alert = create_alert(
        name="ack_test",
        message="Alert to acknowledge",
        severity=AlertSeverity.ERROR,
    )
    
    assert alert.state == AlertState.ACTIVE
    
    success = acknowledge_alert(alert.id)
    assert success == True
    assert alert.state == AlertState.ACKNOWLEDGED


def test_alert_state_transitions(alert_manager):
    """Test alert state machine transitions."""
    alert = create_alert(
        name="state_test",
        message="Testing state transitions",
        severity=AlertSeverity.WARNING,
    )
    
    # Initial state
    assert alert.state == AlertState.ACTIVE
    
    # Acknowledge
    alert.acknowledge()
    assert alert.state == AlertState.ACKNOWLEDGED
    
    # Resolve
    alert.resolve()
    assert alert.state == AlertState.RESOLVED


def test_alert_rule_evaluation():
    """Test alert rule evaluation using global manager."""
    # Create a simple rule
    rule = AlertRule(
        name="eval_test_rule",
        description="Test rule for evaluation",
        condition=lambda m: m.get("test_value", 0) > 10,
        severity=AlertSeverity.ERROR,
    )
    
    from clawteam.alerts import get_alert_manager
    manager = get_alert_manager()
    manager.add_rule(rule)
    
    try:
        # Test with metrics that should trigger
        metrics = {"test_value": 15}
        alerts = evaluate_alerts(metrics)
        
        # Check our rule triggered
        triggered_names = [a.name for a in alerts]
        assert "eval_test_rule" in triggered_names, f"Expected 'eval_test_rule' in {triggered_names}"
    finally:
        # Cleanup: remove the test rule
        manager.remove_rule("eval_test_rule")


def test_alert_severity_levels():
    """Test different severity levels."""
    info_alert = create_alert(
        name="info_test",
        message="Info message",
        severity=AlertSeverity.INFO,
    )
    assert info_alert.severity == AlertSeverity.INFO
    
    warning_alert = create_alert(
        name="warning_test",
        message="Warning message",
        severity=AlertSeverity.WARNING,
    )
    assert warning_alert.severity == AlertSeverity.WARNING
    
    error_alert = create_alert(
        name="error_test",
        message="Error message",
        severity=AlertSeverity.ERROR,
    )
    assert error_alert.severity == AlertSeverity.ERROR
    
    critical_alert = create_alert(
        name="critical_test",
        message="Critical message",
        severity=AlertSeverity.CRITICAL,
    )
    assert critical_alert.severity == AlertSeverity.CRITICAL


def test_alert_with_tags(alert_manager):
    """Test creating alerts with tags."""
    alert = create_alert(
        name="tagged_alert",
        message="Alert with tags",
        severity=AlertSeverity.WARNING,
        tags={"category": "test", "source": "unit_test"},
    )
    
    assert alert.tags.get("category") == "test"
    assert alert.tags.get("source") == "unit_test"
