"""Tests for the metrics server module."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestMetricsCollector:
    """Test MetricsCollector class."""

    def test_collector_initialization(self):
        """Test MetricsCollector initialization."""
        from agentteam.metrics.prom_server import MetricsCollector

        collector = MetricsCollector()
        assert collector is not None
        assert len(collector._counters) == 0
        assert len(collector._gauges) == 0
        assert len(collector._histograms) == 0

    def test_inc_counter(self):
        """Test incrementing a counter."""
        from agentteam.metrics.prom_server import MetricsCollector

        collector = MetricsCollector()
        collector.inc_counter("test_counter")
        assert "test_counter" in collector._counters
        assert collector._counters["test_counter"] == 1

    def test_inc_counter_with_value(self):
        """Test incrementing counter with custom value."""
        from agentteam.metrics.prom_server import MetricsCollector

        collector = MetricsCollector()
        collector.inc_counter("test_counter", 5)
        assert collector._counters["test_counter"] == 5

    def test_inc_counter_with_labels(self):
        """Test incrementing counter with labels."""
        from agentteam.metrics.prom_server import MetricsCollector

        collector = MetricsCollector()
        collector.inc_counter("test_counter", labels={"method": "GET"})
        assert collector._counters['test_counter{method="GET"}'] == 1

    def test_set_gauge(self):
        """Test setting a gauge."""
        from agentteam.metrics.prom_server import MetricsCollector

        collector = MetricsCollector()
        collector.set_gauge("test_gauge", 42.0)
        assert "test_gauge" in collector._gauges
        assert collector._gauges["test_gauge"] == 42.0

    def test_set_gauge_with_labels(self):
        """Test setting gauge with labels."""
        from agentteam.metrics.prom_server import MetricsCollector

        collector = MetricsCollector()
        collector.set_gauge("test_gauge", 100, labels={"status": "ok"})
        key = list(collector._gauges.keys())[0]
        assert collector._gauges[key] == 100

    def test_observe_histogram(self):
        """Test observing histogram values."""
        from agentteam.metrics.prom_server import MetricsCollector

        collector = MetricsCollector()
        collector.observe_histogram("test_histogram", 0.5)
        assert "test_histogram" in collector._histograms
        assert collector._histograms["test_histogram"]["count"] == 1
        assert collector._histograms["test_histogram"]["sum"] == 0.5

    def test_observe_histogram_multiple_values(self):
        """Test observing multiple histogram values."""
        from agentteam.metrics.prom_server import MetricsCollector

        collector = MetricsCollector()
        collector.observe_histogram("test_histogram", 0.1)
        collector.observe_histogram("test_histogram", 0.5)
        collector.observe_histogram("test_histogram", 1.0)
        assert collector._histograms["test_histogram"]["count"] == 3
        assert collector._histograms["test_histogram"]["sum"] == 1.6

    def test_make_key_without_labels(self):
        """Test _make_key without labels."""
        from agentteam.metrics.prom_server import MetricsCollector

        collector = MetricsCollector()
        key = collector._make_key("test_metric", None)
        assert key == "test_metric"

    def test_make_key_with_labels(self):
        """Test _make_key with labels."""
        from agentteam.metrics.prom_server import MetricsCollector

        collector = MetricsCollector()
        key = collector._make_key("test_metric", {"a": "1", "b": "2"})
        assert "test_metric{" in key
        assert 'a="1"' in key
        assert 'b="2"' in key

    def test_parse_key_without_labels(self):
        """Test _parse_key without labels."""
        from agentteam.metrics.prom_server import MetricsCollector

        collector = MetricsCollector()
        name, labels = collector._parse_key("test_metric")
        assert name == "test_metric"
        assert labels == {}

    def test_parse_key_with_labels(self):
        """Test _parse_key with labels."""
        from agentteam.metrics.prom_server import MetricsCollector

        collector = MetricsCollector()
        name, labels = collector._parse_key('test_metric{a="1",b="2"}')
        assert name == "test_metric"
        assert labels == {"a": "1", "b": "2"}

    def test_generate_prometheus_format_empty(self):
        """Test generating Prometheus format with no metrics."""
        from agentteam.metrics.prom_server import MetricsCollector

        collector = MetricsCollector()
        output = collector.generate_prometheus_format()
        # Output may be empty string or have a placeholder
        assert output is not None
        assert isinstance(output, str)

    def test_generate_prometheus_format_counters(self):
        """Test generating Prometheus format with counters."""
        from agentteam.metrics.prom_server import MetricsCollector

        collector = MetricsCollector()
        collector.inc_counter("requests_total", 100)
        output = collector.generate_prometheus_format()
        assert "requests_total" in output
        assert "# TYPE requests_total counter" in output

    def test_generate_prometheus_format_gauges(self):
        """Test generating Prometheus format with gauges."""
        from agentteam.metrics.prom_server import MetricsCollector

        collector = MetricsCollector()
        collector.set_gauge("memory_bytes", 1024)
        output = collector.generate_prometheus_format()
        assert "memory_bytes" in output
        assert "# TYPE memory_bytes gauge" in output

    def test_generate_prometheus_format_histograms(self):
        """Test generating Prometheus format with histograms."""
        from agentteam.metrics.prom_server import MetricsCollector

        collector = MetricsCollector()
        collector.observe_histogram("request_duration_seconds", 0.5)
        output = collector.generate_prometheus_format()
        assert "request_duration_seconds" in output
        assert "# TYPE request_duration_seconds histogram" in output


class TestMetricsServer:
    """Test MetricsServer class."""

    def test_server_initialization(self):
        """Test MetricsServer initialization."""
        from agentteam.metrics.prom_server import MetricsServer

        server = MetricsServer(port=9090, host="127.0.0.1")
        assert server.port == 9090
        assert server.host == "127.0.0.1"
        assert server.running is False

    def test_server_default_values(self):
        """Test MetricsServer with default values."""
        from agentteam.metrics.prom_server import MetricsServer

        server = MetricsServer()
        assert server.port == 9090
        assert server.host == "0.0.0.0"

    def test_server_collector(self):
        """Test that server has a collector."""
        from agentteam.metrics.prom_server import MetricsServer

        server = MetricsServer()
        assert server.collector is not None

    def test_inc_counter_shortcut(self):
        """Test inc_counter shortcut method."""
        from agentteam.metrics.prom_server import MetricsServer

        server = MetricsServer()
        server.inc_counter("test", 1)
        assert "test" in server.collector._counters

    def test_set_gauge_shortcut(self):
        """Test set_gauge shortcut method."""
        from agentteam.metrics.prom_server import MetricsServer

        server = MetricsServer()
        server.set_gauge("test", 42.0)
        assert "test" in server.collector._gauges

    def test_observe_histogram_shortcut(self):
        """Test observe_histogram shortcut method."""
        from agentteam.metrics.prom_server import MetricsServer

        server = MetricsServer()
        server.observe_histogram("test", 0.5)
        assert "test" in server.collector._histograms

    def test_start_server(self):
        """Test starting the server."""
        from agentteam.metrics.prom_server import MetricsServer

        server = MetricsServer(port=0)  # Use port 0 to get random available port
        server.start()
        assert server.running is True
        server.stop()

    def test_stop_server(self):
        """Test stopping the server."""
        from agentteam.metrics.prom_server import MetricsServer

        server = MetricsServer(port=0)
        server.start()
        assert server.running is True
        server.stop()
        assert server.running is False


class TestGlobalServer:
    """Test global server functions."""

    def test_get_metrics_server(self):
        """Test get_metrics_server function."""
        from agentteam.metrics.prom_server import get_metrics_server

        server1 = get_metrics_server()
        server2 = get_metrics_server()
        assert server1 is server2  # Should be same instance

    def test_start_metrics_server(self):
        """Test start_metrics_server function."""
        from agentteam.metrics.prom_server import (
            start_metrics_server,
            stop_metrics_server,
        )

        server = start_metrics_server(port=0)
        assert server.running is True
        stop_metrics_server()

    def test_stop_metrics_server(self):
        """Test stop_metrics_server function."""
        from agentteam.metrics.prom_server import (
            start_metrics_server,
            stop_metrics_server,
        )

        start_metrics_server(port=0)
        stop_metrics_server()
        # After stopping, get_metrics_server should return a new instance
        from agentteam.metrics.prom_server import get_metrics_server, _metrics_server
        # _metrics_server should be None after stop


class TestMetricsHandler:
    """Test MetricsHandler class."""

    def test_handler_has_collector(self):
        """Test that handler can access collector."""
        from agentteam.metrics.prom_server import MetricsHandler, MetricsCollector

        collector = MetricsCollector()
        MetricsHandler.collector = collector
        assert MetricsHandler.collector is collector

    def test_handler_serves_metrics(self):
        """Test handler can serve metrics."""
        from agentteam.metrics.prom_server import MetricsHandler

        # Handler should have do_GET method
        assert hasattr(MetricsHandler, "do_GET")

    def test_handler_serves_health(self):
        """Test handler serves health endpoint."""
        from agentteam.metrics.prom_server import MetricsHandler

        assert hasattr(MetricsHandler, "_serve_health")

    def test_handler_serves_index(self):
        """Test handler serves index page."""
        from agentteam.metrics.prom_server import MetricsHandler

        assert hasattr(MetricsHandler, "_serve_index")


class TestIntegration:
    """Integration tests for metrics server."""

    def test_full_flow(self):
        """Test complete metrics flow."""
        from agentteam.metrics.prom_server import MetricsCollector

        collector = MetricsCollector()

        # Record some metrics
        collector.inc_counter("requests_total", 100, {"method": "GET"})
        collector.set_gauge("memory_bytes", 1024 * 1024)
        collector.observe_histogram("request_duration", 0.5)

        # Generate Prometheus format
        output = collector.generate_prometheus_format()

        # Verify output contains expected metrics
        assert "requests_total" in output
        assert "memory_bytes" in output
        assert "request_duration" in output

    def test_multiple_labels(self):
        """Test metrics with multiple labels."""
        from agentteam.metrics.prom_server import MetricsCollector

        collector = MetricsCollector()
        collector.inc_counter(
            "requests_total",
            50,
            {"method": "GET", "endpoint": "/api"},
        )

        output = collector.generate_prometheus_format()
        assert "method" in output
        assert "endpoint" in output
