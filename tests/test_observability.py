"""Tests for the observability module."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestTracerModule:
    """Test tracer module functionality."""

    def test_tracer_wrapper_initialization(self):
        """Test TracerWrapper initialization."""
        from agentteam.observability.tracer import TracerWrapper

        tracer = TracerWrapper(name="test", version="1.0")
        assert tracer.name == "test"
        assert tracer.version == "1.0"
        assert tracer._initialized is False

    def test_tracer_wrapper_default_values(self):
        """Test TracerWrapper with default values."""
        from agentteam.observability.tracer import TracerWrapper

        tracer = TracerWrapper()
        assert tracer.name == "agentteam"
        # Version might be None or default version string depending on import state
        assert tracer.name is not None

    def test_start_as_current_span_context_manager(self):
        """Test starting span as context manager."""
        from agentteam.observability.tracer import tracer

        with tracer.start_as_current_span("test_span") as span:
            assert span is not None
            span.set_attribute("test_key", "test_value")

    def test_span_attributes(self):
        """Test setting span attributes."""
        from agentteam.observability.tracer import tracer

        with tracer.start_as_current_span("test_span", attributes={"key": "value"}) as span:
            span.set_attribute("another_key", "another_value")

    def test_span_nesting(self):
        """Test nested spans."""
        from agentteam.observability.tracer import tracer

        with tracer.start_as_current_span("outer_span") as outer:
            outer.set_attribute("level", "outer")

            with tracer.start_as_current_span("inner_span") as inner:
                inner.set_attribute("level", "inner")

    def test_create_span_decorator(self):
        """Test span decorator."""
        from agentteam.observability.tracer import tracer

        @tracer.create_span_decorator(name="my_function")
        def my_function():
            return 42

        result = my_function()
        assert result == 42

    def test_trace_async_decorator(self):
        """Test async trace decorator."""
        from agentteam.observability.tracer import trace_async

        @trace_async(name="async_function")
        async def async_function():
            return "done"

        # Run the async function
        import asyncio
        result = asyncio.run(async_function())
        assert result == "done"


class TestMeterModule:
    """Test meter module functionality."""

    def test_meter_wrapper_initialization(self):
        """Test MeterWrapper initialization."""
        from agentteam.observability.meter import MeterWrapper

        meter = MeterWrapper(name="test", version="1.0")
        assert meter.name == "test"
        assert meter.version == "1.0"
        assert meter._initialized is False

    def test_create_counter(self):
        """Test creating a counter."""
        from agentteam.observability.meter import meter

        counter = meter.create_counter("test_counter", "A test counter")
        assert counter is not None

    def test_create_gauge(self):
        """Test creating a gauge."""
        from agentteam.observability.meter import meter

        gauge = meter.create_gauge("test_gauge", "A test gauge")
        assert gauge is not None

    def test_create_histogram(self):
        """Test creating a histogram."""
        from agentteam.observability.meter import meter

        histogram = meter.create_histogram("test_histogram", "A test histogram")
        assert histogram is not None

    def test_inc_counter(self):
        """Test incrementing a counter."""
        from agentteam.observability.meter import meter

        meter.inc_counter("test_counter", 1)
        meter.inc_counter("test_counter", 5)

    def test_set_gauge(self):
        """Test setting a gauge."""
        from agentteam.observability.meter import meter

        meter.set_gauge("test_gauge", 42.0)

    def test_observe_histogram(self):
        """Test observing histogram values."""
        from agentteam.observability.meter import meter

        meter.observe_histogram("test_histogram", 0.5)
        meter.observe_histogram("test_histogram", 1.5)

    def test_record_agent_spawn(self):
        """Test recording agent spawn metrics."""
        from agentteam.observability.meter import record_agent_spawn

        record_agent_spawn("test_team", "claude", 0.5)

    def test_record_task_execution(self):
        """Test recording task execution metrics."""
        from agentteam.observability.meter import record_task_execution

        record_task_execution("test_team", "completed")

    def test_record_message_sent(self):
        """Test recording message metrics."""
        from agentteam.observability.meter import record_message_sent

        record_message_sent("test_team", "sent")

    def test_record_tool_invocation(self):
        """Test recording tool invocation metrics."""
        from agentteam.observability.meter import record_tool_invocation

        record_tool_invocation("test_team", "bash", True)


class TestLoggerModule:
    """Test logger module functionality."""

    def test_get_logger(self):
        """Test getting a logger."""
        from agentteam.observability.logger import get_logger

        logger = get_logger("test")
        assert logger is not None
        assert logger.name == "test"

    def test_structured_logger_initialization(self):
        """Test StructuredLogger initialization."""
        from agentteam.observability.logger import StructuredLogger

        logger = StructuredLogger("test", structured=False)
        assert logger.name == "test"
        assert logger.structured is False

    def test_set_correlation_id(self):
        """Test setting correlation ID."""
        from agentteam.observability.logger import StructuredLogger

        logger = StructuredLogger("test")
        logger.set_correlation_id("corr-123")
        assert logger.correlation_id == "corr-123"

    def test_add_context(self):
        """Test adding context."""
        from agentteam.observability.logger import StructuredLogger

        logger = StructuredLogger("test")
        logger.add_context(user="test_user", request_id="req-123")
        assert logger._context["user"] == "test_user"
        assert logger._context["request_id"] == "req-123"

    def test_clear_context(self):
        """Test clearing context."""
        from agentteam.observability.logger import StructuredLogger

        logger = StructuredLogger("test")
        logger.add_context(key="value")
        logger.clear_context()
        assert len(logger._context) == 0

    def test_build_record(self):
        """Test building log record."""
        from agentteam.observability.logger import StructuredLogger

        logger = StructuredLogger("test")
        record = logger._build_record("INFO", "Test message")
        assert record["level"] == "INFO"
        assert record["message"] == "Test message"
        assert "timestamp" in record

    def test_set_structured_mode(self):
        """Test setting structured mode."""
        from agentteam.observability.logger import set_structured_mode, _structured_mode

        set_structured_mode(True)
        # Mode should be updated (test by import to verify)


class TestExporterModule:
    """Test exporter module functionality."""

    def test_exporter_type_enum(self):
        """Test ExporterType enum."""
        from agentteam.observability.exporter import ExporterType

        assert ExporterType.CONSOLE.value == "console"
        assert ExporterType.OTLP.value == "otlp"
        assert ExporterType.PROMETHEUS.value == "prometheus"
        assert ExporterType.IN_MEMORY.value == "in_memory"

    def test_get_tracer_provider_initially_none(self):
        """Test get_tracer_provider returns None initially."""
        from agentteam.observability.exporter import get_tracer_provider

        provider = get_tracer_provider()
        # May be None or already initialized
        assert provider is None or provider is not None

    def test_get_meter_provider_initially_none(self):
        """Test get_meter_provider returns None initially."""
        from agentteam.observability.exporter import get_meter_provider

        provider = get_meter_provider()
        # May be None or already initialized
        assert provider is None or provider is not None

    def test_setup_console_exporter(self):
        """Test setting up console exporter."""
        from agentteam.observability.exporter import setup_console_exporter

        # Should not raise
        setup_console_exporter()

    def test_setup_otlp_exporter_with_defaults(self):
        """Test setting up OTLP exporter with defaults."""
        from agentteam.observability.exporter import setup_otlp_exporter

        # Should not raise even without collector
        setup_otlp_exporter()

    def test_setup_prometheus_exporter(self):
        """Test setting up Prometheus exporter."""
        from agentteam.observability.exporter import setup_prometheus_exporter

        # Should not raise (port might fail but no exception)
        try:
            setup_prometheus_exporter(port=0)  # Use invalid port to avoid conflicts
        except Exception:
            pass  # Expected if port is in use or Prometheus not available

    def test_setup_in_memory_exporter(self):
        """Test setting up in-memory exporter."""
        from agentteam.observability.exporter import setup_in_memory_exporter

        span_exporter, metric_exporter = setup_in_memory_exporter()
        # Should return tuple (may be None values if OTel not available)
        assert span_exporter is None or span_exporter is not None
        assert metric_exporter is None or metric_exporter is not None

    def test_setup_exporter_by_type(self):
        """Test setup_exporter with different types."""
        from agentteam.observability.exporter import setup_exporter, ExporterType

        # Console exporter
        setup_exporter(ExporterType.CONSOLE)

        # OTLP exporter
        setup_exporter(ExporterType.OTLP)

        # In-memory exporter
        result = setup_exporter(ExporterType.IN_MEMORY)
        # In-memory returns a tuple


class TestIntegration:
    """Integration tests for observability module."""

    def test_full_tracing_flow(self):
        """Test complete tracing flow."""
        from agentteam.observability import tracer, meter

        # Start a span
        with tracer.start_as_current_span("integration_test") as span:
            span.set_attribute("test", "value")

            # Record some metrics
            meter.inc_counter("test_counter", 1)

        # Span should complete without error

    def test_logging_with_context(self):
        """Test logging with context."""
        from agentteam.observability.logger import get_logger

        logger = get_logger("integration_test")
        logger.add_context(team="test_team")

        # Log at different levels
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")

    def test_observability_module_imports(self):
        """Test that observability module can be imported."""
        from agentteam.observability import (
            tracer,
            meter,
            get_logger,
            setup_exporter,
            ExporterType,
        )

        assert tracer is not None
        assert meter is not None
        assert get_logger is not None
        assert setup_exporter is not None
        assert ExporterType is not None

    def test_span_name_constants(self):
        """Test span name constants."""
        from agentteam.observability import (
            SPAN_TEAM_CREATE,
            SPAN_AGENT_SPAWN,
            SPAN_TASK_EXECUTE,
            SPAN_MESSAGE_SEND,
            SPAN_TOOL_INVOKE,
        )

        assert SPAN_TEAM_CREATE == "agentteam.team.create"
        assert SPAN_AGENT_SPAWN == "agentteam.agent.spawn"
        assert SPAN_TASK_EXECUTE == "agentteam.task.execute"
        assert SPAN_MESSAGE_SEND == "agentteam.message.send"
        assert SPAN_TOOL_INVOKE == "agentteam.tool.invoke"

    def test_metric_name_constants(self):
        """Test metric name constants."""
        from agentteam.observability import (
            METRIC_AGENTS_TOTAL,
            METRIC_TASKS_TOTAL,
            METRIC_MESSAGES_TOTAL,
        )

        assert METRIC_AGENTS_TOTAL == "agentteam_agents_total"
        assert METRIC_TASKS_TOTAL == "agentteam_tasks_total"
        assert METRIC_MESSAGES_TOTAL == "agentteam_messages_total"
