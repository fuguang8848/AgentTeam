"""
AgentTeam OpenTelemetry Exporter Module

Provides exporters for:
- OTLP (OpenTelemetry Protocol)
- Prometheus
- Console (debugging)
- In-memory (testing)
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

# Try to import OpenTelemetry exporters
try:
    from opentelemetry import trace, metrics
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = None
    metrics = None
    OTLPSpanExporter = None
    OTLPMetricExporter = None
    TracerProvider = None
    BatchSpanProcessor = None
    MeterProvider = None
    Resource = None
    SERVICE_NAME = None
    SERVICE_VERSION = None
    PeriodicExportingMetricReader = None

# Try to import Prometheus
try:
    from prometheus_client import start_http_server, CollectorRegistry
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    start_http_server = None
    CollectorRegistry = None

from agentteam.utils.logger import get_logger as get_basic_logger

logger = get_basic_logger(__name__)


class ExporterType(Enum):
    """Types of exporters supported."""
    CONSOLE = "console"
    OTLP = "otlp"
    PROMETHEUS = "prometheus"
    IN_MEMORY = "in_memory"


# Global state
_tracer_provider: Optional[Any] = None
_meter_provider: Optional[Any] = None
_service_name: str = "agentteam"
_service_version: str = "0.5.1"


def get_tracer_provider() -> Optional[Any]:
    """Get the global tracer provider."""
    global _tracer_provider
    return _tracer_provider


def get_meter_provider() -> Optional[Any]:
    """Get the global meter provider."""
    global _meter_provider
    return _meter_provider


def create_resource(service_name: str, service_version: str) -> Optional[Any]:
    """Create an OpenTelemetry resource."""
    if not OTEL_AVAILABLE:
        return None

    return Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
    })


def setup_console_exporter() -> None:
    """
    Setup console exporter for debugging.

    Prints spans and metrics to stdout.
    """
    if not OTEL_AVAILABLE:
        logger.warning("OpenTelemetry not available, skipping console exporter setup")
        return

    try:
        resource = create_resource(_service_name, _service_version)

        # Setup tracer provider with console exporter
        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(
            BatchSpanProcessor(ConsoleSpanExporter())
        )
        trace.set_tracer_provider(tracer_provider)
        global _tracer_provider
        _tracer_provider = tracer_provider

        # Setup meter provider
        reader = PeriodicExportingMetricReader(ConsoleMetricExporter())
        meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
        metrics.set_meter_provider(meter_provider)
        global _meter_provider
        _meter_provider = meter_provider

        logger.info("Console exporter setup complete")
    except Exception as e:
        logger.error(f"Failed to setup console exporter: {e}")


def setup_otlp_exporter(
    endpoint: str = "http://localhost:4317",
    insecure: bool = True,
) -> None:
    """
    Setup OTLP exporter for production use.

    Args:
        endpoint: OTLP collector endpoint
        insecure: Use insecure (no TLS) connection
    """
    if not OTEL_AVAILABLE:
        logger.warning("OpenTelemetry not available, skipping OTLP exporter setup")
        return

    try:
        resource = create_resource(_service_name, _service_version)

        # Setup tracer provider with OTLP exporter
        span_exporter = OTLPSpanExporter(endpoint=endpoint, insecure=insecure)
        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
        trace.set_tracer_provider(tracer_provider)
        global _tracer_provider
        _tracer_provider = tracer_provider

        # Setup meter provider with OTLP exporter
        metric_exporter = OTLPMetricExporter(endpoint=endpoint, insecure=insecure)
        reader = PeriodicExportingMetricReader(metric_exporter)
        meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
        metrics.set_meter_provider(meter_provider)
        global _meter_provider
        _meter_provider = meter_provider

        logger.info(f"OTLP exporter setup complete (endpoint: {endpoint})")
    except Exception as e:
        logger.error(f"Failed to setup OTLP exporter: {e}")


def setup_prometheus_exporter(port: int = 9090) -> None:
    """
    Setup Prometheus exporter.

    Args:
        port: Port for Prometheus metrics endpoint
    """
    if not PROMETHEUS_AVAILABLE:
        logger.warning("Prometheus client not available, skipping setup")
        return

    try:
        start_http_server(port)
        logger.info(f"Prometheus exporter started on port {port}")
    except Exception as e:
        logger.error(f"Failed to start Prometheus exporter: {e}")


def setup_in_memory_exporter() -> tuple[Any, Any]:
    """
    Setup in-memory exporter for testing.

    Returns:
        Tuple of (span_exporter, metric_exporter)
    """
    span_exporter = None
    metric_exporter = None

    if OTEL_AVAILABLE:
        try:
            from opentelemetry.sdk.trace.export import InMemorySpanExporter
            from opentelemetry.sdk.metrics.export import InMemoryMetricReader

            resource = create_resource(_service_name, _service_version)

            span_exporter = InMemorySpanExporter()

            # Setup tracer provider with in-memory exporter
            tracer_provider = TracerProvider(resource=resource)
            tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
            trace.set_tracer_provider(tracer_provider)
            global _tracer_provider
            _tracer_provider = tracer_provider

            # Setup meter provider with in-memory exporter
            metric_reader = InMemoryMetricReader()
            meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
            metrics.set_meter_provider(meter_provider)
            global _meter_provider
            _meter_provider = meter_provider

            logger.info("In-memory exporter setup complete")
            return span_exporter, metric_reader
        except Exception as e:
            logger.error(f"Failed to setup in-memory exporter: {e}")

    return span_exporter, metric_exporter


def setup_exporter(
    exporter_type: ExporterType = ExporterType.CONSOLE,
    **kwargs: Any,
) -> None:
    """
    Setup exporter based on type.

    Args:
        exporter_type: Type of exporter to setup
        **kwargs: Additional arguments for the exporter

    Usage:
        setup_exporter(ExporterType.CONSOLE)
        setup_exporter(ExporterType.OTLP, endpoint="http://collector:4317")
        setup_exporter(ExporterType.PROMETHEUS, port=9090)
        span_exporter, metric_exporter = setup_exporter(ExporterType.IN_MEMORY)
    """
    if exporter_type == ExporterType.CONSOLE:
        setup_console_exporter()
    elif exporter_type == ExporterType.OTLP:
        endpoint = kwargs.get("endpoint", "http://localhost:4317")
        insecure = kwargs.get("insecure", True)
        setup_otlp_exporter(endpoint=endpoint, insecure=insecure)
    elif exporter_type == ExporterType.PROMETHEUS:
        port = kwargs.get("port", 9090)
        setup_prometheus_exporter(port=port)
    elif exporter_type == ExporterType.IN_MEMORY:
        return setup_in_memory_exporter()
    else:
        logger.warning(f"Unknown exporter type: {exporter_type}")


# Console exporters for when OTel is not fully available
class ConsoleSpanExporter:
    """Simple console span exporter for debugging."""

    def export(self, spans: list) -> None:
        """Export spans to console."""
        for span in spans:
            print(f"[SPAN] {span.name} - {span.span_id}")

    def shutdown(self) -> None:
        pass


class ConsoleMetricExporter:
    """Simple console metric exporter for debugging."""

    def export(self, metrics: list) -> None:
        """Export metrics to console."""
        for metric in metrics:
            print(f"[METRIC] {metric.name} - {metric.descriptor}")

    def shutdown(self) -> None:
        pass
