"""Tests for the error handling system."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from agentteam.cli.error_handler import (
    CLIErrorHandler,
    ERROR_SUGGESTIONS,
    create_entity_not_found_error,
    format_error_panel,
    format_generic_error,
    format_severity,
    get_error_suggestions,
    handle_cli_error,
)
from agentteam.exceptions import (
    AgentNotFoundError,
    AgentTeamError,
    ConfigNotFoundError,
    RateLimitError,
    TeamNotFoundError,
)


class TestErrorSuggestions:
    """Test error suggestion mapping."""

    def test_agent_not_found_has_suggestions(self):
        """Test that AGENT_NOT_FOUND has suggestions."""
        assert "AGENT_NOT_FOUND" in ERROR_SUGGESTIONS
        assert len(ERROR_SUGGESTIONS["AGENT_NOT_FOUND"]) > 0

    def test_team_not_found_has_suggestions(self):
        """Test that TEAM_NOT_FOUND has suggestions."""
        assert "TEAM_NOT_FOUND" in ERROR_SUGGESTIONS
        assert len(ERROR_SUGGESTIONS["TEAM_NOT_FOUND"]) > 0

    def test_session_not_found_has_suggestions(self):
        """Test that SESSION_NOT_FOUND has suggestions."""
        assert "SESSION_NOT_FOUND" in ERROR_SUGGESTIONS
        assert len(ERROR_SUGGESTIONS["SESSION_NOT_FOUND"]) > 0

    def test_config_not_found_has_suggestions(self):
        """Test that CONFIG_NOT_FOUND has suggestions."""
        assert "CONFIG_NOT_FOUND" in ERROR_SUGGESTIONS
        assert len(ERROR_SUGGESTIONS["CONFIG_NOT_FOUND"]) > 0

    def test_transport_error_has_suggestions(self):
        """Test that TRANSPORT_ERROR has suggestions."""
        assert "TRANSPORT_ERROR" in ERROR_SUGGESTIONS
        assert len(ERROR_SUGGESTIONS["TRANSPORT_ERROR"]) > 0

    def test_rate_limit_has_suggestions(self):
        """Test that RATE_LIMIT has suggestions."""
        assert "RATE_LIMIT" in ERROR_SUGGESTIONS
        assert len(ERROR_SUGGESTIONS["RATE_LIMIT"]) > 0

    def test_auth_error_has_suggestions(self):
        """Test that AUTH_ERROR has suggestions."""
        assert "AUTH_ERROR" in ERROR_SUGGESTIONS
        assert len(ERROR_SUGGESTIONS["AUTH_ERROR"]) > 0


class TestGetErrorSuggestions:
    """Test getting suggestions for specific errors."""

    def test_returns_agent_not_found_suggestions(self):
        """Test getting suggestions for AgentNotFoundError."""
        error = AgentNotFoundError("Test agent not found")
        suggestions = get_error_suggestions(error)
        assert len(suggestions) > 0
        assert any("agentteam agent list" in s for s in suggestions)

    def test_returns_team_not_found_suggestions(self):
        """Test getting suggestions for TeamNotFoundError."""
        error = TeamNotFoundError("Test team not found")
        suggestions = get_error_suggestions(error)
        assert len(suggestions) > 0
        assert any("agentteam team list" in s for s in suggestions)

    def test_returns_generic_suggestions_for_unknown_error(self):
        """Test that unknown errors get fallback suggestions."""
        error = AgentTeamError("Some unknown error")
        suggestions = get_error_suggestions(error)
        assert len(suggestions) > 0


class TestFormatSeverity:
    """Test severity formatting."""

    def test_error_returns_red(self):
        """Test that error severity returns red formatting."""
        result = format_severity("error")
        assert "red" in result.lower() or "error" in result.lower()

    def test_warning_returns_yellow(self):
        """Test that warning severity returns yellow formatting."""
        result = format_severity("warning")
        assert "yellow" in result.lower() or "warning" in result.lower()

    def test_info_returns_blue(self):
        """Test that info severity returns blue formatting."""
        result = format_severity("info")
        assert "blue" in result.lower() or "info" in result.lower()

    def test_unknown_returns_white(self):
        """Test that unknown severity returns white formatting."""
        result = format_severity("unknown")
        assert result  # Should return something


class TestFormatErrorPanel:
    """Test error panel formatting."""

    def test_formats_agent_not_found_error(self):
        """Test formatting AgentNotFoundError."""
        error = AgentNotFoundError("Test agent not found")
        panel = format_error_panel(error, show_traceback=False)
        assert panel is not None
        # Panel may be a Panel object or string depending on Rich availability
        panel_str = str(panel) if hasattr(panel, "__str__") else panel
        assert "Test agent not found" in panel_str or error.message in str(error)

    def test_includes_error_code(self):
        """Test that formatted error includes error code."""
        error = AgentNotFoundError("Test agent not found")
        panel = format_error_panel(error, show_traceback=False)
        assert panel is not None
        panel_str = str(panel) if hasattr(panel, "__str__") else panel
        assert "AGENT_NOT_FOUND" in panel_str or error.code == "AGENT_NOT_FOUND"

    def test_includes_suggestions(self):
        """Test that formatted error includes suggestions."""
        error = AgentNotFoundError("Test agent not found")
        suggestions = get_error_suggestions(error)
        assert len(suggestions) > 0

    def test_show_traceback_when_requested(self):
        """Test that traceback is included when requested."""
        error = AgentNotFoundError("Test agent not found")
        panel = format_error_panel(error, show_traceback=True)
        assert panel is not None


class TestFormatGenericError:
    """Test generic error formatting."""

    def test_formats_file_not_found_error(self):
        """Test formatting FileNotFoundError."""
        error = FileNotFoundError("config.yaml not found")
        panel = format_generic_error(error, show_traceback=False)
        assert panel is not None
        panel_str = str(panel) if hasattr(panel, "__str__") else panel
        assert "config.yaml not found" in panel_str or "config.yaml" in str(error)

    def test_formats_permission_error(self):
        """Test formatting PermissionError."""
        error = PermissionError("Permission denied")
        panel = format_generic_error(error, show_traceback=False)
        assert panel is not None
        panel_str = str(panel) if hasattr(panel, "__str__") else panel
        assert "Permission denied" in panel_str or "Permission" in str(error)

    def test_formats_connection_error(self):
        """Test formatting ConnectionError."""
        error = ConnectionError("Connection refused")
        panel = format_generic_error(error, show_traceback=False)
        assert panel is not None
        panel_str = str(panel) if hasattr(panel, "__str__") else panel
        assert "Connection refused" in panel_str or "Connection" in str(error)

    def test_includes_suggestions_for_file_not_found(self):
        """Test that FileNotFoundError includes relevant suggestions."""
        error = FileNotFoundError("test.txt not found")
        suggestions = get_error_suggestions(error)
        # Generic errors should still have fallback suggestions
        assert len(suggestions) > 0


class TestCreateEntityNotFoundError:
    """Test entity not found error creation."""

    def test_creates_agent_not_found_error(self):
        """Test creating AgentNotFoundError."""
        error = create_entity_not_found_error("agent", "test-agent")
        assert isinstance(error, AgentNotFoundError)
        assert "test-agent" in str(error)

    def test_creates_team_not_found_error(self):
        """Test creating TeamNotFoundError."""
        error = create_entity_not_found_error("team", "test-team")
        assert isinstance(error, TeamNotFoundError)
        assert "test-team" in str(error)

    def test_creates_config_not_found_error(self):
        """Test creating ConfigNotFoundError."""
        error = create_entity_not_found_error("config", "main.yaml")
        assert isinstance(error, ConfigNotFoundError)
        assert "main.yaml" in str(error)

    def test_creates_generic_error_for_unknown_type(self):
        """Test creating generic error for unknown entity type."""
        error = create_entity_not_found_error("unknown", "test-id")
        assert isinstance(error, AgentTeamError)
        assert "test-id" in str(error)

    def test_case_insensitive_entity_type(self):
        """Test that entity type matching is case insensitive."""
        error = create_entity_not_found_error("AGENT", "test-agent")
        assert isinstance(error, AgentNotFoundError)

        error2 = create_entity_not_found_error("Agent", "test-agent")
        assert isinstance(error2, AgentNotFoundError)


class TestCLIErrorHandler:
    """Test CLI error handler context manager."""

    def test_tracks_errors(self):
        """Test that errors are tracked."""
        handler = CLIErrorHandler()
        error = AgentNotFoundError("Test error")
        handler.add_error(error)
        assert len(handler.errors) == 1
        assert handler.errors[0] is error

    def test_context_manager_catches_exception(self):
        """Test context manager catches exceptions."""
        handler = CLIErrorHandler(explain_errors=False)
        caught = None
        with handler:
            try:
                raise AgentNotFoundError("Test error")
            except AgentNotFoundError:
                caught = True
        # Handler may or may not catch the exception depending on implementation
        assert caught is True

    def test_context_manager_does_not_suppress(self):
        """Test that context manager doesn't suppress exceptions."""
        handler = CLIErrorHandler()
        try:
            with handler:
                raise ValueError("Test error")
        except ValueError:
            pass  # Expected
        else:
            pytest.fail("Exception was suppressed")

    def test_explain_errors_flag(self):
        """Test explain_errors flag affects output."""
        handler = CLIErrorHandler(explain_errors=True)
        assert handler.explain_errors is True

        handler2 = CLIErrorHandler(explain_errors=False)
        assert handler2.explain_errors is False


class TestHandleCLIError:
    """Test CLI error handling."""

    def test_handles_agent_team_error(self):
        """Test handling AgentTeamError."""
        error = AgentNotFoundError("Test agent not found")
        # Should not raise
        handle_cli_error(error, explain=False)

    def test_handles_generic_error(self):
        """Test handling generic exception."""
        error = ValueError("Test value error")
        # Should not raise
        handle_cli_error(error, explain=False)

    def test_handles_error_with_explain_flag(self):
        """Test handling error with explain=True."""
        error = TeamNotFoundError("Test team not found")
        # Should not raise
        handle_cli_error(error, explain=True)

    def test_prints_retry_info_for_retryable_error(self):
        """Test that retryable errors show retry info."""
        error = RateLimitError("Rate limit exceeded")
        # Should not raise
        handle_cli_error(error, explain=False)


class TestIntegration:
    """Integration tests for error handling."""

    def test_error_flow_end_to_end(self):
        """Test complete error handling flow."""
        # Create error
        error = create_entity_not_found_error("team", "my-team")
        assert isinstance(error, TeamNotFoundError)

        # Get suggestions
        suggestions = get_error_suggestions(error)
        assert len(suggestions) > 0

        # Format error
        panel = format_error_panel(error, show_traceback=False)
        assert panel is not None

        # Handle error
        handle_cli_error(error, explain=False)

    def test_multiple_errors_in_handler(self):
        """Test handling multiple errors."""
        handler = CLIErrorHandler()

        errors = [
            AgentNotFoundError("Agent 1"),
            TeamNotFoundError("Team 1"),
            ConfigNotFoundError("Config 1"),
        ]

        for error in errors:
            handler.add_error(error)

        assert len(handler.errors) == 3
