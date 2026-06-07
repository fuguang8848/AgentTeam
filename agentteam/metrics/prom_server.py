"""
AgentTeam Prometheus Metrics Server

Provides HTTP endpoint for Prometheus to scrape metrics.
Implements the Prometheus text format for metrics exposition.

Usage:
    from agentteam.metrics.prom_server import MetricsServer

    server = MetricsServer(port=9090)
    server.start()

    # Or use CLI:
    # agentteam metrics serve --port 9090
"""

from __future__ import annotations

import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Optional

try:
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    PROMETHEUS_CLIENT_AVAILABLE = True
except ImportError:
    PROMETHEUS_CLIENT_AVAILABLE = False

from agentteam.utils.logger import get_logger

logger = get_logger(__name__)


class MetricsCollector:
    """
    Collects and formats metrics in Prometheus format.

    Provides methods to register and expose metrics.
    """

    def __init__(self):
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def inc_counter(self, name: str, value: float = 1, labels: Optional[dict[str, str]] = None) -> None:
        """Increment a counter metric."""
        with self._lock:
            key = self._make_key(name, labels)
            self._counters[key] = self._counters.get(key, 0) + value

    def set_gauge(self, name: str, value: float, labels: Optional[dict[str, str]] = None) -> None:
        """Set a gauge metric."""
        with self._lock:
            key = self._make_key(name, labels)
            self._gauges[key] = value

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: Optional[dict[str, str]] = None,
        buckets: Optional[list[float]] = None,
    ) -> None:
        """Observe a value for histogram."""
        with self._lock:
            key = self._make_key(name, labels)
            if key not in self._histograms:
                self._histograms[key] = {
                    "sum": 0,
                    "count": 0,
                    "buckets": {
                        b: 0 for b in (buckets or [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0])
                    },
                }
            self._histograms[key]["sum"] += value
            self._histograms[key]["count"] += 1
            for bucket in self._histograms[key]["buckets"]:
                if value <= bucket:
                    self._histograms[key]["buckets"][bucket] += 1

    def _make_key(self, name: str, labels: Optional[dict[str, str]]) -> str:
        """Create a unique key for a metric with labels."""
        if not labels:
            return name
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def _parse_key(self, key: str) -> tuple[str, dict[str, str]]:
        """Parse a metric key back into name and labels."""
        if "{" not in key:
            return key, {}
        name, labels_str = key.split("{", 1)
        labels_str = labels_str.rstrip("}")
        labels = {}
        for part in labels_str.split(","):
            k, v = part.split("=", 1)
            labels[k.strip()] = v.strip('"')
        return name, labels

    def generate_prometheus_format(self) -> str:
        """Generate metrics in Prometheus text format."""
        lines = []

        # Output counters
        for key, value in self._counters.items():
            name, labels = self._parse_key(key)
            lines.append(f"# HELP {name} Counter metric")
            lines.append(f"# TYPE {name} counter")
            if labels:
                label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
                lines.append(f"{name}{{{label_str}}} {value}")
            else:
                lines.append(f"{name} {value}")

        # Output gauges
        for key, value in self._gauges.items():
            name, labels = self._parse_key(key)
            lines.append(f"# HELP {name} Gauge metric")
            lines.append(f"# TYPE {name} gauge")
            if labels:
                label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
                lines.append(f"{name}{{{label_str}}} {value}")
            else:
                lines.append(f"{name} {value}")

        # Output histograms
        for key, hist_data in self._histograms.items():
            name, labels = self._parse_key(key)
            lines.append(f"# HELP {name} Histogram metric")
            lines.append(f"# TYPE {name} histogram")

            # Buckets
            for bucket, count in sorted(hist_data["buckets"].items()):
                bucket_labels = dict(labels) if labels else {}
                bucket_labels["le"] = str(bucket)
                label_str = ",".join(f'{k}="{v}"' for k, v in sorted(bucket_labels.items()))
                lines.append(f"{name}_bucket{{{label_str}}} {count}")

            # +Inf bucket
            if labels:
                label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
                label_str += ',le="+Inf"'
                lines.append(f"{name}_bucket{{{label_str}}} {hist_data['count']}")
            else:
                lines.append(f'{name}_bucket{{le="+Inf"}} {hist_data["count"]}')

            # Sum and count
            if labels:
                label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
                lines.append(f"{name}_sum{{{label_str}}} {hist_data['sum']}")
                lines.append(f"{name}_count{{{label_str}}} {hist_data['count']}")
            else:
                lines.append(f"{name}_sum {hist_data['sum']}")
                lines.append(f"{name}_count {hist_data['count']}")

        return "\n".join(lines) + "\n"


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler for serving Prometheus metrics."""

    collector: Optional[MetricsCollector] = None

    def do_GET(self) -> None:
        """Handle GET requests."""
        if self.path == "/metrics":
            self._serve_metrics()
        elif self.path == "/health":
            self._serve_health()
        elif self.path == "/":
            self._serve_index()
        else:
            self._serve_not_found()

    def _serve_metrics(self) -> None:
        """Serve metrics in Prometheus format."""
        try:
            if self.collector:
                metrics_output = self.collector.generate_prometheus_format()
            else:
                metrics_output = "# No metrics collected\n"

            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Content-Length", str(len(metrics_output)))
            self.end_headers()
            self.wfile.write(metrics_output.encode("utf-8"))
        except Exception as e:
            logger.error(f"Error serving metrics: {e}")
            self.send_error(500, str(e))

    def _serve_health(self) -> None:
        """Serve health check endpoint."""
        response = json.dumps({"status": "healthy"})
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response.encode("utf-8"))

    def _serve_index(self) -> None:
        """Serve index page."""
        html = """<!DOCTYPE html>
<html>
<head><title>AgentTeam Metrics</title></head>
<body>
<h1>AgentTeam Metrics</h1>
<p><a href="/metrics">Metrics</a></p>
<p><a href="/health">Health</a></p>
</body>
</html>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _serve_not_found(self) -> None:
        """Serve 404 page."""
        self.send_error(404, "Not Found")

    def log_message(self, format: str, *args) -> None:
        """Override to customize logging."""
        logger.debug(f"{self.address_string()} - {format % args}")


class MetricsServer:
    """
    HTTP server for exposing Prometheus metrics.

    Usage:
        server = MetricsServer(port=9090)
        server.start()
        # ...
        server.stop()
    """

    def __init__(
        self,
        port: int = 9090,
        host: str = "0.0.0.0",
    ):
        self.port = port
        self.host = host
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self.collector = MetricsCollector()

    @property
    def running(self) -> bool:
        """Check if server is running."""
        return self._running

    def start(self) -> None:
        """Start the metrics server in a background thread."""
        if self._running:
            logger.warning("Server already running")
            return

        MetricsHandler.collector = self.collector

        self._server = HTTPServer((self.host, self.port), MetricsHandler)
        self._running = True

        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

        logger.info(f"Metrics server started on {self.host}:{self.port}")

    def _serve(self) -> None:
        """Serve requests until stopped."""
        while self._running and self._server:
            try:
                self._server.handle_request()
            except Exception as e:
                if self._running:
                    logger.error(f"Server error: {e}")

    def stop(self) -> None:
        """Stop the metrics server."""
        self._running = False
        if self._server:
            self._server.server_close()
            self._server = None
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("Metrics server stopped")

    def inc_counter(self, name: str, value: float = 1, labels: Optional[dict[str, str]] = None) -> None:
        """Increment a counter (convenience method)."""
        self.collector.inc_counter(name, value, labels)

    def set_gauge(self, name: str, value: float, labels: Optional[dict[str, str]] = None) -> None:
        """Set a gauge (convenience method)."""
        self.collector.set_gauge(name, value, labels)

    def observe_histogram(self, name: str, value: float, labels: Optional[dict[str, str]] = None) -> None:
        """Observe a histogram value (convenience method)."""
        self.collector.observe_histogram(name, value, labels)


# Global server instance
_metrics_server: Optional[MetricsServer] = None


def get_metrics_server() -> MetricsServer:
    """Get the global metrics server instance."""
    global _metrics_server
    if _metrics_server is None:
        _metrics_server = MetricsServer()
    return _metrics_server


def start_metrics_server(port: int = 9090, host: str = "0.0.0.0") -> MetricsServer:
    """Start the global metrics server."""
    server = get_metrics_server()
    if not server.running:
        server.port = port
        server.host = host
        server.start()
    return server


def stop_metrics_server() -> None:
    """Stop the global metrics server."""
    global _metrics_server
    if _metrics_server:
        _metrics_server.stop()
        _metrics_server = None
