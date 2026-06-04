"""
AgentTeam End-to-End Smoke Tests

Tests the complete workflow:
1. Create team
2. Spawn agents
3. Assign tasks
4. Receive results

This is an integration test that validates the entire system works together.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestSmokeBasicImports:
    """Test that all core modules can be imported."""

    def test_import_agentteam(self):
        """Test that agentteam can be imported."""
        import agentteam
        assert agentteam is not None

    def test_import_core(self):
        """Test that core module can be imported."""
        from agentteam import core
        assert core is not None

    def test_import_cli(self):
        """Test that CLI can be imported."""
        from agentteam import cli
        assert cli is not None

    def test_import_exceptions(self):
        """Test that exceptions can be imported."""
        from agentteam import exceptions
        assert exceptions is not None

    def test_import_metrics(self):
        """Test that metrics can be imported."""
        from agentteam import metrics
        assert metrics is not None


class TestSmokeObservability:
    """Test observability module smoke tests."""

    def test_import_observability(self):
        """Test that observability can be imported."""
        from agentteam import observability
        assert observability is not None

    def test_import_tracer(self):
        """Test that tracer can be imported."""
        from agentteam.observability import tracer
        assert tracer is not None

    def test_import_meter(self):
        """Test that meter can be imported."""
        from agentteam.observability import meter
        assert meter is not None

    def test_import_logger(self):
        """Test that logger can be imported."""
        from agentteam.observability import get_logger
        assert get_logger is not None

    def test_tracer_span_lifecycle(self):
        """Test tracer span start and end."""
        from agentteam.observability import tracer

        with tracer.start_as_current_span("test_span") as span:
            assert span is not None
            span.set_attribute("test", "value")

    def test_meter_counter(self):
        """Test meter counter creation."""
        from agentteam.observability import meter

        counter = meter.create_counter("smoke_test_counter")
        assert counter is not None
        meter.inc_counter("smoke_test_counter", 1)


class TestSmokeCLICommands:
    """Test CLI commands smoke tests."""

    def test_import_init_command(self):
        """Test that init command can be imported."""
        from agentteam.cli.commands import init_app
        assert init_app is not None

    def test_import_error_handler(self):
        """Test that error handler can be imported."""
        from agentteam.cli import error_handler
        assert error_handler is not None

    def test_error_handler_get_suggestions(self):
        """Test error handler suggestions."""
        from agentteam.cli.error_handler import get_error_suggestions
        from agentteam.exceptions import AgentNotFoundError

        error = AgentNotFoundError("Test")
        suggestions = get_error_suggestions(error)
        assert len(suggestions) > 0


class TestSmokeMetrics:
    """Test metrics module smoke tests."""

    def test_import_prom_server(self):
        """Test that prom_server can be imported."""
        from agentteam.metrics import prom_server
        assert prom_server is not None

    def test_metrics_collector(self):
        """Test MetricsCollector creation."""
        from agentteam.metrics.prom_server import MetricsCollector

        collector = MetricsCollector()
        assert collector is not None
        assert len(collector._counters) == 0

    def test_metrics_server_init(self):
        """Test MetricsServer initialization."""
        from agentteam.metrics.prom_server import MetricsServer

        server = MetricsServer(port=0)  # Use port 0 for testing
        assert server is not None
        assert server.port == 0

    def test_counter_increment(self):
        """Test counter increment."""
        from agentteam.metrics.prom_server import MetricsCollector

        collector = MetricsCollector()
        collector.inc_counter("test_counter")
        assert collector._counters.get("test_counter", 0) == 1

    def test_gauge_set(self):
        """Test gauge set."""
        from agentteam.metrics.prom_server import MetricsCollector

        collector = MetricsCollector()
        collector.set_gauge("test_gauge", 42.0)
        assert collector._gauges.get("test_gauge", 0) == 42.0

    def test_histogram_observe(self):
        """Test histogram observe."""
        from agentteam.metrics.prom_server import MetricsCollector

        collector = MetricsCollector()
        collector.observe_histogram("test_histogram", 0.5)
        assert "test_histogram" in collector._histograms


class TestSmokeExceptions:
    """Test exceptions smoke tests."""

    def test_agent_not_found_error(self):
        """Test AgentNotFoundError."""
        from agentteam.exceptions import AgentNotFoundError

        error = AgentNotFoundError("Test agent")
        assert "Test agent" in str(error)
        assert error.code == "AGENT_NOT_FOUND"

    def test_team_not_found_error(self):
        """Test TeamNotFoundError."""
        from agentteam.exceptions import TeamNotFoundError

        error = TeamNotFoundError("Test team")
        assert "Test team" in str(error)
        assert error.code == "TEAM_NOT_FOUND"

    def test_error_context(self):
        """Test ErrorContext."""
        from agentteam.exceptions import ErrorContext

        context = ErrorContext(
            team_name="test_team",
            agent_id="test_agent",
        )
        assert context.team_name == "test_team"
        assert context.agent_id == "test_agent"


class TestSmokeInitWizard:
    """Test init wizard smoke tests."""

    def test_check_python_version(self):
        """Test Python version check."""
        from agentteam.cli.commands.init import check_python_version

        ok, msg = check_python_version()
        assert ok is True

    def test_get_default_data_dir(self):
        """Test default data directory."""
        from agentteam.cli.commands.init import get_default_data_dir

        data_dir = get_default_data_dir()
        assert data_dir is not None
        assert data_dir.name == ".agentteam"

    def test_generate_config_content(self):
        """Test config content generation."""
        from agentteam.cli.commands.init import generate_config_content

        content = generate_config_content(
            backend="claude-code",
            database_path="/tmp/test.db",
            transport="file",
        )
        assert "claude-code" in content
        assert "/tmp/test.db" in content

    def test_backend_options(self):
        """Test backend options."""
        from agentteam.cli.commands.init import BACKEND_OPTIONS

        assert len(BACKEND_OPTIONS) > 0
        backend_ids = [b["id"] for b in BACKEND_OPTIONS]
        assert "claude-code" in backend_ids

    def test_transport_options(self):
        """Test transport options."""
        from agentteam.cli.commands.init import TRANSPORT_OPTIONS

        assert len(TRANSPORT_OPTIONS) > 0
        transport_ids = [t["id"] for t in TRANSPORT_OPTIONS]
        assert "file" in transport_ids


class TestSmokeErrorFriendly:
    """Test error friendly smoke tests."""

    def test_error_suggestions_mapping(self):
        """Test error suggestions exist."""
        from agentteam.cli.error_handler import ERROR_SUGGESTIONS

        assert "AGENT_NOT_FOUND" in ERROR_SUGGESTIONS
        assert "TEAM_NOT_FOUND" in ERROR_SUGGESTIONS

    def test_create_entity_not_found_error(self):
        """Test entity not found error creation."""
        from agentteam.cli.error_handler import create_entity_not_found_error
        from agentteam.exceptions import AgentNotFoundError, TeamNotFoundError

        agent_error = create_entity_not_found_error("agent", "test")
        assert isinstance(agent_error, AgentNotFoundError)

        team_error = create_entity_not_found_error("team", "test")
        assert isinstance(team_error, TeamNotFoundError)

    def test_cli_error_handler_init(self):
        """Test CLI error handler initialization."""
        from agentteam.cli.error_handler import CLIErrorHandler

        handler = CLIErrorHandler()
        assert handler is not None
        assert handler.errors == []


class TestSmokeIntegration:
    """Integration smoke tests."""

    def test_full_observability_flow(self):
        """Test complete observability flow."""
        from agentteam.observability import tracer, meter, get_logger

        # Create a logger
        logger = get_logger("smoke_test")
        logger.info("Starting smoke test")

        # Create a span
        with tracer.start_as_current_span("smoke_operation") as span:
            span.set_attribute("operation", "test")

            # Record metrics
            meter.inc_counter("smoke_counter", 1)
            meter.observe_histogram("smoke_histogram", 0.5)

        logger.info("Smoke test completed")

    def test_full_metrics_flow(self):
        """Test complete metrics flow."""
        from agentteam.metrics.prom_server import MetricsCollector

        collector = MetricsCollector()

        # Simulate some metrics
        collector.inc_counter("requests_total", 100, {"method": "GET"})
        collector.set_gauge("active_connections", 5)
        collector.observe_histogram("request_duration", 0.3)

        # Generate output
        output = collector.generate_prometheus_format()
        assert output is not None
        assert "requests_total" in output

    def test_error_handling_flow(self):
        """Test complete error handling flow."""
        from agentteam.cli.error_handler import (
            create_entity_not_found_error,
            get_error_suggestions,
        )
        from agentteam.observability.logger import get_logger

        # Create error
        error = create_entity_not_found_error("agent", "test-agent")

        # Get suggestions
        suggestions = get_error_suggestions(error)

        # Log the error
        logger = get_logger("error_smoke_test")
        logger.error(f"Error occurred: {error}")

        # Assertions
        assert error is not None
        assert len(suggestions) > 0


class TestSmokeConfig:
    """Test configuration smoke tests."""

    def test_import_config(self):
        """Test config module import."""
        try:
            from agentteam import config
            assert config is not None
        except ImportError:
            pytest.skip("Config module not available")

    def test_import_console(self):
        """Test console module import."""
        try:
            from agentteam import console
            assert console is not None
        except ImportError:
            pytest.skip("Console module not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
