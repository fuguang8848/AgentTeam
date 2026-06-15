"""
AgentTeam OpenTelemetry Meter Module

Provides metrics collection capabilities with:
- Counters, Gauges, Histograms
- Optional OpenTelemetry (graceful degradation if not available)
"""

from __future__ import annotations

from typing import Any, Callable, Optional

# Try to import OpenTelemetry, but make it optional
try:
    from opentelemetry import metrics
    from opentelemetry.metrics import (
        Counter,
        Gauge,
        Histogram,
        Meter,
        ObservableGauge,
        get_meter,
    )

    OTEL_METRICS_AVAILABLE = True
except ImportError:
    OTEL_METRICS_AVAILABLE = False
    metrics = None
    Counter = None
    Gauge = None
    Histogram = None
    Meter = None
    get_meter = None

from agentteam.utils.logger import get_logger as get_basic_logger

logger = get_basic_logger(__name__)


class NoOpCounter:
    """No-operation counter for when OpenTelemetry is not available."""

    def __init__(self, name: str, description: str = "", unit: str = ""):
        self.name = name
        self.description = description
        self.unit = unit
        self._value = 0.0

    def add(self, amount: float = 1, attributes: Optional[dict[str, str]] = None) -> None:
        self._value += amount

    def get(self) -> float:
        return self._value


class NoOpGauge:
    """No-operation gauge for when OpenTelemetry is not available."""

    def __init__(self, name: str, description: str = "", unit: str = ""):
        self.name = name
        self.description = description
        self.unit = unit
        self._value = 0.0

    def set(self, value: float, attributes: Optional[dict[str, str]] = None) -> None:
        self._value = value

    def get(self) -> float:
        return self._value


class NoOpHistogram:
    """No-operation histogram for when OpenTelemetry is not available."""

    def __init__(self, name: str, description: str = "", unit: str = ""):
        self.name = name
        self.description = description
        self.unit = unit
        self._values: list[float] = []

    def record(self, value: float, attributes: Optional[dict[str, str]] = None) -> None:
        self._values.append(value)

    def get_values(self) -> list[float]:
        return self._values


class NoOpMeter:
    """No-operation meter for when OpenTelemetry is not available."""

    def __init__(self, name: str):
        self.name = name

    def create_counter(
        self,
        name: str,
        description: str = "",
        unit: str = "",
    ) -> NoOpCounter:
        return NoOpCounter(name, description, unit)

    def create_gauge(
        self,
        name: str,
        description: str = "",
        unit: str = "",
    ) -> NoOpGauge:
        return NoOpGauge(name, description, unit)

    def create_histogram(
        self,
        name: str,
        description: str = "",
        unit: str = "",
    ) -> NoOpHistogram:
        return NoOpHistogram(name, description, unit)


class MeterWrapper:
    """
    Wrapper for OpenTelemetry meter with graceful degradation.

    Provides:
    - Automatic fallback to NoOp when OTel unavailable
    - Common metric patterns
    - Typed metric creators
    """

    def __init__(
        self,
        name: str = "agentteam",
        version: Optional[str] = None,
    ):
        self.name = name
        self.version = version
        self._meter: Optional[Any] = None
        self._initialized = False
        self._counters: dict[str, Any] = {}
        self._gauges: dict[str, Any] = {}
        self._histograms: dict[str, Any] = {}

    def _ensure_initialized(self) -> None:
        """Initialize the meter if not already done."""
        if self._initialized:
            return

        if OTEL_METRICS_AVAILABLE:
            try:
                self._meter = get_meter(self.name, self.version)
                self._initialized = True
                logger.debug(f"Initialized OpenTelemetry meter: {self.name}")
            except Exception as e:
                logger.warning(f"Failed to initialize OTel meter: {e}")
                self._meter = NoOpMeter(self.name)
                self._initialized = True
        else:
            self._meter = NoOpMeter(self.name)
            self._initialized = True
            logger.debug("OpenTelemetry metrics not available, using NoOp meter")

    def create_counter(
        self,
        name: str,
        description: str = "",
        unit: str = "",
    ) -> Any:
        """
        Create or get a counter metric.

        Args:
            name: Metric name
            description: Metric description
            unit: Metric unit

        Returns:
            Counter metric
        """
        self._ensure_initialized()

        if name in self._counters:
            return self._counters[name]

        if OTEL_METRICS_AVAILABLE and hasattr(self._meter, "create_counter"):
            counter = self._meter.create_counter(name, description, unit)
        else:
            counter = self._meter.create_counter(name, description, unit)

        self._counters[name] = counter
        return counter

    def create_gauge(
        self,
        name: str,
        description: str = "",
        unit: str = "",
    ) -> Any:
        """
        Create or get a gauge metric.

        Args:
            name: Metric name
            description: Metric description
            unit: Metric unit

        Returns:
            Gauge metric
        """
        self._ensure_initialized()

        if name in self._gauges:
            return self._gauges[name]

        if OTEL_METRICS_AVAILABLE and hasattr(self._meter, "create_gauge"):
            gauge = self._meter.create_gauge(name, description, unit)
        else:
            gauge = self._meter.create_gauge(name, description, unit)

        self._gauges[name] = gauge
        return gauge

    def create_histogram(
        self,
        name: str,
        description: str = "",
        unit: str = "",
    ) -> Any:
        """
        Create or get a histogram metric.

        Args:
            name: Metric name
            description: Metric description
            unit: Metric unit

        Returns:
            Histogram metric
        """
        self._ensure_initialized()

        if name in self._histograms:
            return self._histograms[name]

        if OTEL_METRICS_AVAILABLE and hasattr(self._meter, "create_histogram"):
            histogram = self._meter.create_histogram(name, description, unit)
        else:
            histogram = self._meter.create_histogram(name, description, unit)

        self._histograms[name] = histogram
        return histogram

    def inc_counter(
        self,
        name: str,
        value: float = 1,
        attributes: Optional[dict[str, str]] = None,
    ) -> None:
        """Convenience method to increment a counter."""
        counter = self.create_counter(name)
        counter.add(value, attributes)

    def set_gauge(
        self,
        name: str,
        value: float,
        attributes: Optional[dict[str, str]] = None,
    ) -> None:
        """Convenience method to set a gauge value."""
        gauge = self.create_gauge(name)
        gauge.set(value, attributes)

    def observe_histogram(
        self,
        name: str,
        value: float,
        attributes: Optional[dict[str, str]] = None,
    ) -> None:
        """Convenience method to record a histogram observation."""
        histogram = self.create_histogram(name)
        histogram.record(value, attributes)


# Global meter instance
meter = MeterWrapper(name="agentteam", version="0.5.1")


# Pre-defined metric helpers
def record_agent_spawn(team: str, agent_type: str, duration: float) -> None:
    """Record agent spawn metric."""
    meter.inc_counter(
        "agentteam_agents_total",
        1,
        {"team": team, "agent_type": agent_type, "state": "spawned"},
    )
    meter.observe_histogram(
        "agentteam_agent_spawn_duration_seconds",
        duration,
        {"team": team, "agent_type": agent_type},
    )


def record_task_execution(team: str, task_state: str) -> None:
    """Record task execution metric."""
    meter.inc_counter(
        "agentteam_tasks_total",
        1,
        {"team": team, "state": task_state},
    )


def record_message_sent(team: str, direction: str) -> None:
    """Record message metric."""
    meter.inc_counter(
        "agentteam_messages_total",
        1,
        {"team": team, "direction": direction},
    )


def record_tool_invocation(team: str, tool_name: str, success: bool) -> None:
    """Record tool invocation metric."""
    meter.inc_counter(
        "agentteam_tool_invocations_total",
        1,
        {"team": team, "tool": tool_name, "success": str(success).lower()},
    )
