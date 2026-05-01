"""
Alert system for ClawTeam

Provides alerting capabilities based on metrics thresholds
and system health checks.
"""
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

from clawteam.utils.logger import get_logger

logger = get_logger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# Alias for backward compatibility
AlertType = AlertSeverity


class AlertState(Enum):
    """Alert state"""
    INACTIVE = "inactive"
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


@dataclass
class Alert:
    """A single alert instance"""
    id: str
    name: str
    message: str
    severity: AlertSeverity
    state: AlertState = AlertState.INACTIVE
    tags: dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    triggered_at: Optional[float] = None
    resolved_at: Optional[float] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def trigger(self) -> None:
        """Mark alert as triggered"""
        self.state = AlertState.ACTIVE
        self.triggered_at = time.time()
        logger.warning(f"Alert triggered: {self.name} - {self.message}")
    
    def acknowledge(self) -> None:
        """Acknowledge the alert"""
        self.state = AlertState.ACKNOWLEDGED
    
    def resolve(self) -> None:
        """Resolve the alert"""
        self.state = AlertState.RESOLVED
        self.resolved_at = time.time()
        logger.info(f"Alert resolved: {self.name}")


@dataclass
class AlertRule:
    """
    A rule that defines when an alert should trigger
    
    Attributes:
        name: Unique identifier for the rule
        description: Human-readable description
        condition: Callable that takes metrics dict and returns True if alert should trigger
        severity: Alert severity level
        tags: Tags for the alert
        cooldown: Minimum time between alerts (seconds)
    """
    name: str
    description: str
    condition: Callable[[dict[str, Any]], bool]
    severity: AlertSeverity = AlertSeverity.WARNING
    tags: dict[str, str] = field(default_factory=dict)
    cooldown: float = 60.0  # 1 minute default cooldown
    
    _last_triggered: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    def should_fire(self, metrics: dict[str, Any]) -> bool:
        """Check if this rule should fire based on current metrics"""
        with self._lock:
            if time.time() - self._last_triggered < self.cooldown:
                return False
        
        try:
            should_fire = self.condition(metrics)
            if should_fire:
                with self._lock:
                    self._last_triggered = time.time()
            return should_fire
        except Exception as e:
            logger.error(f"Error evaluating alert rule {self.name}: {e}")
            return False


class AlertChannel:
    """Base class for alert channels"""
    
    def send(self, alert: Alert) -> None:
        """Send an alert through this channel"""
        raise NotImplementedError


class LogAlertChannel(AlertChannel):
    """Alert channel that logs alerts"""
    
    def send(self, alert: Alert) -> None:
        """Log the alert"""
        log_method = {
            AlertSeverity.INFO: logger.info,
            AlertSeverity.WARNING: logger.warning,
            AlertSeverity.ERROR: logger.error,
            AlertSeverity.CRITICAL: logger.critical,
        }.get(alert.severity, logger.info)
        
        log_method(f"[ALERT:{alert.severity.value.upper()}] {alert.name}: {alert.message}")


class WebhookAlertChannel(AlertChannel):
    """Alert channel that sends alerts to a webhook"""
    
    def __init__(self, webhook_url: str, headers: Optional[dict[str, str]] = None):
        self.webhook_url = webhook_url
        self.headers = headers or {}
    
    def send(self, alert: Alert) -> None:
        """Send alert to webhook"""
        import json
        import urllib.request
        
        payload = {
            "alert_id": alert.id,
            "name": alert.name,
            "message": alert.message,
            "severity": alert.severity.value,
            "state": alert.state.value,
            "tags": alert.tags,
            "created_at": datetime.fromtimestamp(alert.created_at).isoformat(),
            "triggered_at": datetime.fromtimestamp(alert.triggered_at).isoformat() if alert.triggered_at else None,
        }
        
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={**self.headers, "Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                logger.info(f"Alert sent to webhook: {alert.name}")
        except Exception as e:
            logger.error(f"Failed to send alert to webhook: {e}")


class AlertManager:
    """
    Central alert manager for ClawTeam
    
    Manages alert rules, evaluates conditions, and dispatches alerts
    to configured channels.
    
    Example:
        # Create alert manager
        manager = AlertManager()
        
        # Add an alert rule
        manager.add_rule(AlertRule(
            name="high_agent_count",
            description="Alert when active agents > 10",
            condition=lambda m: m.get("clawteam.agents.active", 0) > 10,
            severity=AlertSeverity.WARNING,
        ))
        
        # Add a channel
        manager.add_channel(LogAlertChannel())
        
        # Evaluate all rules with current metrics
        alerts = manager.evaluate(metrics)
        
        # Get active alerts
        active = manager.get_active_alerts()
    """
    
    def __init__(self):
        self._rules: dict[str, AlertRule] = {}
        self._channels: list[AlertChannel] = []
        self._alerts: dict[str, Alert] = {}
        self._alerts_lock = threading.Lock()
        
        # Add default log channel
        self.add_channel(LogAlertChannel())
    
    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule"""
        self._rules[rule.name] = rule
        logger.info(f"Added alert rule: {rule.name}")
    
    def remove_rule(self, name: str) -> None:
        """Remove an alert rule"""
        if name in self._rules:
            del self._rules[name]
            logger.info(f"Removed alert rule: {name}")
    
    def get_rule(self, name: str) -> Optional[AlertRule]:
        """Get an alert rule by name"""
        return self._rules.get(name)
    
    def add_channel(self, channel: AlertChannel) -> None:
        """Add an alert channel"""
        self._channels.append(channel)
        logger.info(f"Added alert channel: {channel.__class__.__name__}")
    
    def remove_channel(self, channel_type: type) -> None:
        """Remove an alert channel by type"""
        self._channels = [c for c in self._channels if not isinstance(c, channel_type)]
    
    def evaluate(self, metrics: dict[str, Any]) -> list[Alert]:
        """
        Evaluate all rules against the given metrics
        
        Returns list of alerts that were triggered
        """
        triggered_alerts = []
        
        for rule in self._rules.values():
            if rule.should_fire(metrics):
                alert = self._create_alert(rule)
                triggered_alerts.append(alert)
                self._dispatch_alert(alert)
        
        return triggered_alerts
    
    def _create_alert(self, rule: AlertRule) -> Alert:
        """Create an alert from a triggered rule"""
        alert_id = f"{rule.name}_{int(time.time() * 1000)}"
        
        alert = Alert(
            id=alert_id,
            name=rule.name,
            message=f"[{rule.name}] {rule.description}",
            severity=rule.severity,
            tags=rule.tags,
        )
        alert.trigger()
        
        with self._alerts_lock:
            self._alerts[alert_id] = alert
        
        return alert
    
    def _dispatch_alert(self, alert: Alert) -> None:
        """Send alert to all channels"""
        for channel in self._channels:
            try:
                channel.send(alert)
            except Exception as e:
                logger.error(f"Error sending alert to {channel.__class__.__name__}: {e}")
    
    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get an alert by ID"""
        with self._alerts_lock:
            return self._alerts.get(alert_id)
    
    def get_active_alerts(self) -> list[Alert]:
        """Get all active (unresolved) alerts"""
        with self._alerts_lock:
            return [a for a in self._alerts.values() if a.state == AlertState.ACTIVE]
    
    def get_alerts_by_state(self, state: AlertState) -> list[Alert]:
        """Get all alerts in a specific state"""
        with self._alerts_lock:
            return [a for a in self._alerts.values() if a.state == state]
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        with self._alerts_lock:
            if alert_id in self._alerts:
                self._alerts[alert_id].acknowledge()
                return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        with self._alerts_lock:
            if alert_id in self._alerts:
                self._alerts[alert_id].resolve()
                return True
        return False
    
    def resolve_all(self) -> int:
        """Resolve all active alerts"""
        count = 0
        with self._alerts_lock:
            for alert in self._alerts.values():
                if alert.state == AlertState.ACTIVE:
                    alert.resolve()
                    count += 1
        return count
    
    def clear_resolved(self) -> int:
        """Remove all resolved alerts"""
        count = 0
        with self._alerts_lock:
            resolved_ids = [aid for aid, a in self._alerts.items() if a.state == AlertState.RESOLVED]
            for aid in resolved_ids:
                del self._alerts[aid]
                count += 1
        return count


# Built-in alert rules
def create_builtin_rules() -> dict[str, AlertRule]:
    """Create the standard set of alert rules"""
    from clawteam.metrics import get_metrics_collector
    
    rules = {}
    
    # High agent count
    rules["high_agent_count"] = AlertRule(
        name="high_agent_count",
        description="Active agent count exceeds 10",
        condition=lambda m: m.get("clawteam.agents.active", 0) > 10,
        severity=AlertSeverity.WARNING,
        tags={"category": "agents"},
    )
    
    # Very high agent count
    rules["critical_agent_count"] = AlertRule(
        name="critical_agent_count",
        description="Active agent count exceeds 20",
        condition=lambda m: m.get("clawteam.agents.active", 0) > 20,
        severity=AlertSeverity.CRITICAL,
        tags={"category": "agents"},
    )
    
    # High API latency
    rules["high_api_latency"] = AlertRule(
        name="high_api_latency",
        description="API p99 latency exceeds 1 second",
        condition=lambda m: m.get("clawteam.api.latency.p99", 0) > 1.0,
        severity=AlertSeverity.ERROR,
        tags={"category": "api"},
        cooldown=120.0,  # 2 minutes
    )
    
    # High token usage rate
    rules["high_token_usage"] = AlertRule(
        name="high_token_usage",
        description="Token usage rate exceeds 100k/hour",
        condition=lambda m: m.get("clawteam.token.usage_rate", 0) > 100000,
        severity=AlertSeverity.WARNING,
        tags={"category": "cost"},
        cooldown=300.0,  # 5 minutes
    )
    
    # No active sessions
    rules["no_active_sessions"] = AlertRule(
        name="no_active_sessions",
        description="No active sessions for extended period",
        condition=lambda m: m.get("clawteam.sessions.active", 0) == 0,
        severity=AlertSeverity.INFO,
        tags={"category": "sessions"},
        cooldown=600.0,  # 10 minutes
    )
    
    # High task queue depth
    rules["high_task_queue"] = AlertRule(
        name="high_task_queue",
        description="Task queue depth exceeds 100",
        condition=lambda m: m.get("clawteam.tasks.queued", 0) > 100,
        severity=AlertSeverity.WARNING,
        tags={"category": "tasks"},
    )
    
    return rules


# Global alert manager instance
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get the global alert manager instance"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
        # Add built-in rules
        for rule in create_builtin_rules().values():
            _alert_manager.add_rule(rule)
    return _alert_manager


# Convenience functions
def add_alert_rule(rule: AlertRule) -> None:
    """Add an alert rule to the global manager"""
    get_alert_manager().add_rule(rule)


def evaluate_alerts(metrics: dict[str, Any]) -> list[Alert]:
    """Evaluate all rules and return triggered alerts"""
    return get_alert_manager().evaluate(metrics)


def get_active_alerts() -> list[Alert]:
    """Get all active alerts"""
    return get_alert_manager().get_active_alerts()


def acknowledge_alert(alert_id: str) -> bool:
    """Acknowledge an alert by ID"""
    return get_alert_manager().acknowledge_alert(alert_id)


# Additional convenience functions expected by clawteam/__init__.py

def create_alert(
    name: str,
    message: str,
    severity: AlertSeverity = AlertSeverity.WARNING,
    tags: Optional[dict[str, str]] = None,
) -> Alert:
    """Create and dispatch a new alert directly"""
    manager = get_alert_manager()
    
    # Create alert directly
    alert = Alert(
        id=f"{name}_{int(time.time() * 1000)}",
        name=name,
        message=message,
        severity=severity,
        tags=tags or {},
    )
    alert.trigger()
    manager._dispatch_alert(alert)
    
    # Also add to the manager's alert list
    with manager._alerts_lock:
        manager._alerts[alert.id] = alert
    
    return alert


def check_agent_failure_rates(
    failure_threshold: float = 0.5,
    window_seconds: float = 300.0,
) -> Optional[Alert]:
    """
    Check agent failure rates and create alert if too high
    
    Args:
        failure_threshold: Maximum acceptable failure rate (0.0-1.0)
        window_seconds: Time window to check
    
    Returns:
        Alert if failure rate exceeds threshold, None otherwise
    """
    from clawteam.metrics import get_metrics_collector
    
    metrics = get_metrics_collector()
    total = metrics.get_counter("clawteam.agents.total")
    failed = metrics.get_counter("clawteam.agents.failed")
    
    if total == 0:
        return None
    
    failure_rate = failed / total if total > 0 else 0.0
    
    if failure_rate > failure_threshold:
        return create_alert(
            name="high_agent_failure_rate",
            message=f"Agent failure rate {failure_rate:.1%} exceeds threshold {failure_threshold:.1%}",
            severity=AlertSeverity.ERROR,
            tags={"category": "agents", "type": "failure_rate"},
        )
    
    return None


def check_task_timeouts(
    timeout_threshold_seconds: float = 300.0,
) -> Optional[Alert]:
    """
    Check for task timeouts and create alert if too many
    
    Args:
        timeout_threshold_seconds: Maximum acceptable task duration
    
    Returns:
        Alert if timeout count is high, None otherwise
    """
    from clawteam.metrics import get_metrics_collector
    
    metrics = get_metrics_collector()
    timeouts = metrics.get_counter("clawteam.tasks.timeouts")
    total = metrics.get_counter("clawteam.tasks.completed")
    
    if total == 0:
        return None
    
    timeout_rate = timeouts / total if total > 0 else 0.0
    
    # More than 10% timeouts is concerning
    if timeout_rate > 0.1:
        return create_alert(
            name="high_task_timeout_rate",
            message=f"Task timeout rate {timeout_rate:.1%} is concerning",
            severity=AlertSeverity.WARNING,
            tags={"category": "tasks", "type": "timeout"},
        )
    
    return None
