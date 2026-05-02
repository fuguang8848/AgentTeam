"""
Metrics collection system for ClawTeam

Provides metrics collection and export capabilities for monitoring
system health, performance, and usage patterns.
"""

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

from clawteam.utils.logger import get_logger

logger = get_logger(__name__)


class MetricType(Enum):
    """Metric types supported by the collector"""

    COUNTER = "counter"  # Cumulative count
    GAUGE = "gauge"  # Point-in-time value
    HISTOGRAM = "histogram"  # Distribution
    SUMMARY = "summary"  # Aggregated percentiles


@dataclass
class Metric:
    """A single metric data point"""

    name: str
    value: float
    metric_type: MetricType
    tags: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_prometheus(self) -> str:
        """Export as Prometheus format"""
        tags_str = ",".join(f'{k}="{v}"' for k, v in sorted(self.tags.items()))
        if tags_str:
            return f"{self.name}{{{tags_str}}} {self.value} {int(self.timestamp * 1000)}"
        return f"{self.name} {self.value} {int(self.timestamp * 1000)}"


@dataclass
class Counter:
    """Counter metric - only increments"""

    name: str
    value: float = 0.0
    tags: dict[str, str] = field(default_factory=dict)

    def inc(self, value: float = 1.0) -> None:
        """Increment counter"""
        self.value += value

    def get(self) -> float:
        """Get current value"""
        return self.value


@dataclass
class Gauge:
    """Gauge metric - can go up or down"""

    name: str
    value: float = 0.0
    tags: dict[str, str] = field(default_factory=dict)

    def set(self, value: float) -> None:
        """Set gauge value"""
        self.value = value

    def inc(self, value: float = 1.0) -> None:
        """Increment gauge"""
        self.value += value

    def dec(self, value: float = 1.0) -> None:
        """Decrement gauge"""
        self.value -= value

    def get(self) -> float:
        """Get current value"""
        return self.value


@dataclass
class Histogram:
    """Histogram metric - tracks distributions"""

    name: str
    buckets: list[float] = field(
        default_factory=lambda: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
    )
    tags: dict[str, str] = field(default_factory=dict)

    _counts: dict[float, int] = field(default_factory=lambda: defaultdict(int))
    _sum: float = 0.0
    _count: int = 0

    def observe(self, value: float) -> None:
        """Record an observation"""
        self._sum += value
        self._count += 1
        for bucket in self.buckets:
            if value <= bucket:
                self._counts[bucket] += 1

    def get_stats(self) -> dict[str, Any]:
        """Get histogram statistics"""
        return {
            "count": self._count,
            "sum": self._sum,
            "mean": self._sum / self._count if self._count > 0 else 0,
            "buckets": dict(self._counts),
        }


class MetricsCollector:
    """
    Central metrics collector for ClawTeam

    Thread-safe metrics collection with support for:
    - Counters (cumulative counts)
    - Gauges (point-in-time values)
    - Histograms (distributions)

    Example:
        metrics = MetricsCollector()

        # Increment a counter
        metrics.inc_counter("clawteam.agents.created", tags={"team": "dev"})

        # Set a gauge
        metrics.set_gauge("clawteam.agents.active", 5)

        # Observe a histogram value
        metrics.observe_histogram("clawteam.api.latency", 0.123)

        # Export metrics
        print(metrics.export_prometheus())
    """

    _instance: Optional["MetricsCollector"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "MetricsCollector":
        """Singleton pattern for global metrics collection"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._counters: dict[str, Counter] = {}
        self._gauges: dict[str, Gauge] = {}
        self._histograms: dict[str, Histogram] = {}
        self._metrics_history: list[Metric] = []
        self._max_history = 10000  # Keep last 10k metrics
        self._export_lock = threading.Lock()

    def _make_key(self, name: str, tags: dict[str, str]) -> str:
        """Create a unique key for a metric"""
        if tags:
            sorted_tags = sorted(tags.items())
            tags_str = ",".join(f"{k}={v}" for k, v in sorted_tags)
            return f"{name}{{{tags_str}}}"
        return name

    # Counter operations
    def inc_counter(
        self, name: str, value: float = 1.0, tags: Optional[dict[str, str]] = None
    ) -> None:
        """Increment a counter metric"""
        tags = tags or {}
        key = self._make_key(name, tags)

        with self._export_lock:
            if key not in self._counters:
                self._counters[key] = Counter(name=name, value=value, tags=tags)
            else:
                self._counters[key].inc(value)

    def get_counter(self, name: str, tags: Optional[dict[str, str]] = None) -> float:
        """Get current counter value"""
        tags = tags or {}
        key = self._make_key(name, tags)

        with self._export_lock:
            if key in self._counters:
                return self._counters[key].get()
        return 0.0

    # Gauge operations
    def set_gauge(self, name: str, value: float, tags: Optional[dict[str, str]] = None) -> None:
        """Set a gauge metric value"""
        tags = tags or {}
        key = self._make_key(name, tags)

        with self._export_lock:
            if key not in self._gauges:
                self._gauges[key] = Gauge(name=name, value=value, tags=tags)
            else:
                self._gauges[key].set(value)

    def inc_gauge(
        self, name: str, value: float = 1.0, tags: Optional[dict[str, str]] = None
    ) -> None:
        """Increment a gauge"""
        tags = tags or {}
        key = self._make_key(name, tags)

        with self._export_lock:
            if key not in self._gauges:
                self._gauges[key] = Gauge(name=name, value=value, tags=tags)
            else:
                self._gauges[key].inc(value)

    def dec_gauge(
        self, name: str, value: float = 1.0, tags: Optional[dict[str, str]] = None
    ) -> None:
        """Decrement a gauge"""
        tags = tags or {}
        key = self._make_key(name, tags)

        with self._export_lock:
            if key not in self._gauges:
                self._gauges[key] = Gauge(name=name, value=-value, tags=tags)
            else:
                self._gauges[key].dec(value)

    def get_gauge(self, name: str, tags: Optional[dict[str, str]] = None) -> float:
        """Get current gauge value"""
        tags = tags or {}
        key = self._make_key(name, tags)

        with self._export_lock:
            if key in self._gauges:
                return self._gauges[key].get()
        return 0.0

    # Histogram operations
    def observe_histogram(
        self, name: str, value: float, tags: Optional[dict[str, str]] = None
    ) -> None:
        """Observe a value for histogram"""
        tags = tags or {}
        key = self._make_key(name, tags)

        with self._export_lock:
            if key not in self._histograms:
                self._histograms[key] = Histogram(name=name, tags=tags)
            self._histograms[key].observe(value)

    def get_histogram_stats(
        self, name: str, tags: Optional[dict[str, str]] = None
    ) -> dict[str, Any]:
        """Get histogram statistics"""
        tags = tags or {}
        key = self._make_key(name, tags)

        with self._export_lock:
            if key in self._histograms:
                return self._histograms[key].get_stats()
        return {"count": 0, "sum": 0, "mean": 0, "buckets": {}}

    # Bulk operations
    def timing(self, name: str, tags: Optional[dict[str, str]] = None):
        """Context manager for timing operations"""
        return _TimingContext(self, name, tags)

    def count_calls(self, name: str, tags: Optional[dict[str, str]] = None):
        """Decorator to count function calls"""

        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                self.inc_counter(name, tags=tags)
                return func(*args, **kwargs)

            return wrapper

        return decorator

    # Export operations
    def export_prometheus(self) -> str:
        """Export all metrics in Prometheus format"""
        lines = []

        with self._export_lock:
            # Export counters
            for counter in self._counters.values():
                key = self._make_key(counter.name, counter.tags)
                lines.append(f"{counter.name}{{{self._format_tags(counter.tags)}}} {counter.value}")

            # Export gauges
            for gauge in self._gauges.values():
                lines.append(f"{gauge.name}{{{self._format_tags(gauge.tags)}}} {gauge.value}")

            # Export histograms
            for histogram in self._histograms.values():
                stats = histogram.get_stats()
                # Export as multiple metrics (one per bucket + _sum and _count)
                for bucket, count in stats["buckets"].items():
                    bucket_tags = dict(histogram.tags)
                    bucket_tags["le"] = str(bucket)
                    lines.append(
                        f"{histogram.name}_bucket{{{self._format_tags(bucket_tags)}}} {count}"
                    )
                # +Inf bucket
                inf_tags = dict(histogram.tags)
                inf_tags["le"] = "+Inf"
                lines.append(
                    f"{histogram.name}_bucket{{{self._format_tags(inf_tags)}}} {stats['count']}"
                )
                lines.append(
                    f"{histogram.name}_sum{{{self._format_tags(histogram.tags)}}} {stats['sum']}"
                )
                lines.append(
                    f"{histogram.name}_count{{{self._format_tags(histogram.tags)}}} {stats['count']}"
                )

        return "\n".join(lines)

    def _format_tags(self, tags: dict[str, str]) -> str:
        """Format tags for Prometheus"""
        return ",".join(f'{k}="{v}"' for k, v in sorted(tags.items()))

    def export_json(self) -> dict[str, Any]:
        """Export all metrics as JSON"""
        with self._export_lock:
            return {
                "timestamp": datetime.now().isoformat(),
                "counters": {
                    c.name: {"value": c.value, "tags": c.tags} for c in self._counters.values()
                },
                "gauges": {
                    g.name: {"value": g.value, "tags": g.tags} for g in self._gauges.values()
                },
                "histograms": {
                    h.name: {**h.get_stats(), "tags": h.tags} for h in self._histograms.values()
                },
            }

    def get_all_metrics(self) -> list[Metric]:
        """Get all current metric values as Metric objects"""
        metrics = []

        with self._export_lock:
            for counter in self._counters.values():
                metrics.append(
                    Metric(
                        name=counter.name,
                        value=counter.value,
                        metric_type=MetricType.COUNTER,
                        tags=counter.tags,
                    )
                )

            for gauge in self._gauges.values():
                metrics.append(
                    Metric(
                        name=gauge.name,
                        value=gauge.value,
                        metric_type=MetricType.GAUGE,
                        tags=gauge.tags,
                    )
                )

            for histogram in self._histograms.values():
                stats = histogram.get_stats()
                metrics.append(
                    Metric(
                        name=f"{histogram.name}_count",
                        value=stats["count"],
                        metric_type=MetricType.HISTOGRAM,
                        tags=histogram.tags,
                    )
                )

        return metrics

    def reset(self) -> None:
        """Reset all metrics (use with caution!)"""
        with self._export_lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._metrics_history.clear()

    def snapshot(self) -> dict[str, Any]:
        """Take a snapshot of current metrics state"""
        return self.export_json()


class _TimingContext:
    """Context manager for timing operations"""

    def __init__(self, collector: MetricsCollector, name: str, tags: Optional[dict[str, str]]):
        self.collector = collector
        self.name = name
        self.tags = tags
        self.start_time: float = 0.0

    def __enter__(self) -> "_TimingContext":
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        duration = time.time() - self.start_time
        self.collector.observe_histogram(self.name, duration, self.tags)


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


# Convenience functions
def inc_counter(name: str, value: float = 1.0, tags: Optional[dict[str, str]] = None) -> None:
    """Increment a counter metric"""
    get_metrics_collector().inc_counter(name, value, tags)


def set_gauge(name: str, value: float, tags: Optional[dict[str, str]] = None) -> None:
    """Set a gauge metric value"""
    get_metrics_collector().set_gauge(name, value, tags)


def observe_histogram(name: str, value: float, tags: Optional[dict[str, str]] = None) -> None:
    """Observe a value for histogram"""
    get_metrics_collector().observe_histogram(name, value, tags)


def timing(name: str, tags: Optional[dict[str, str]] = None) -> _TimingContext:
    """Context manager for timing operations"""
    return get_metrics_collector().timing(name, tags)
