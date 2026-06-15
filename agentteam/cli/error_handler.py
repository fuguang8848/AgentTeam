"""
AgentTeam Error Handler - User-Friendly Error Display

Provides:
- Structured error formatting with Rich panels
- Recovery suggestions for common errors
- Traceback display with --explain-errors flag
"""

from __future__ import annotations

import sys
import traceback
from typing import Any, Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from agentteam.exceptions import (
    AgentTeamError,
    AgentNotFoundError,
    ConfigError,
    ConfigNotFoundError,
    TeamNotFoundError,
    SessionNotFoundError,
    TransportError,
    RateLimitError,
    AuthError,
    PermissionDeniedError,
)

console = Console()

# Error code to suggestion mapping
ERROR_SUGGESTIONS: dict[str, list[str]] = {
    "AGENT_NOT_FOUND": [
        "Run `agentteam agent list` to see available agents",
        "Check if the agent was spelled correctly",
        "Ensure the agent is in the correct team",
    ],
    "TEAM_NOT_FOUND": [
        "Run `agentteam team list` to see available teams",
        "Check if the team name was spelled correctly",
        "Create a new team with `agentteam team create`",
    ],
    "SESSION_NOT_FOUND": [
        "Run `agentteam session list` to see active sessions",
        "The session may have expired",
        "Start a new session with `agentteam session start`",
    ],
    "CONFIG_NOT_FOUND": [
        "Run `agentteam init` to create a new configuration",
        "Check if the config file path is correct",
        "Try: agentteam config show to see current config",
    ],
    "CONFIG_ERROR": [
        "Check your config file syntax (YAML format)",
        "Run `agentteam config validate` to check config",
        "Try: cat ~/.agentteam/config.yaml",
    ],
    "TRANSPORT_ERROR": [
        "Check network connectivity",
        "Verify the transport service is running",
        "Try restarting with `agentteam daemon restart`",
    ],
    "RATE_LIMIT": [
        "Wait a moment and retry",
        "Check API quotas in your dashboard",
        "Consider reducing request frequency",
    ],
    "AUTH_ERROR": [
        "Check your API credentials",
        "Run `agentteam auth login` to re-authenticate",
        "Verify the API key is still valid",
    ],
    "PERMISSION_DENIED": [
        "Check your permissions",
        "Contact team admin for access",
        "Verify you have the required role",
    ],
}

# Generic fallback suggestions
FALLBACK_SUGGESTIONS = [
    "Run `agentteam --help` for usage information",
    "Check the documentation at https://github.com/YintaTriss/AgentTeam",
    "Try running with `--verbose` for more details",
]


def get_error_suggestions(error: AgentTeamError) -> list[str]:
    """Get recovery suggestions for an error."""
    code = getattr(error, "code", None)
    if code and code in ERROR_SUGGESTIONS:
        return ERROR_SUGGESTIONS[code]
    return FALLBACK_SUGGESTIONS


def format_error_code(error: AgentTeamError) -> str:
    """Format error with its code."""
    code = getattr(error, "code", "UNKNOWN")
    return f"[{code}]"


def format_severity(severity: str) -> str:
    """Format severity level with color."""
    colors = {
        "error": "red",
        "warning": "yellow",
        "info": "blue",
        "debug": "dim",
    }
    return f"[{colors.get(severity, 'white')}]{severity.upper()}[/]"


def format_error_panel(
    error: AgentTeamError,
    show_traceback: bool = False,
) -> Optional[str]:
    """Format an AgentTeamError as a Rich panel string."""
    if not RICH_AVAILABLE:
        return str(error)

    code = getattr(error, "code", "UNKNOWN")
    severity = getattr(error, "severity", "error")
    message = error.message or str(error)

    # Build the error content
    content_lines = [
        f"[bold]{message}[/bold]",
        "",
        f"Error Code: [cyan]{code}[/cyan]",
        f"Severity: {format_severity(severity)}",
    ]

    # Add context if available
    context = getattr(error, "context", None)
    if context and (context.team_name or context.agent_id or context.session_id or context.task_id):
        content_lines.append("")
        content_lines.append("[bold]Context:[/bold]")
        if context.team_name:
            content_lines.append(f"  Team: [yellow]{context.team_name}[/yellow]")
        if context.agent_id:
            content_lines.append(f"  Agent: [yellow]{context.agent_id}[/yellow]")
        if context.session_id:
            content_lines.append(f"  Session: [yellow]{context.session_id}[/yellow]")
        if context.task_id:
            content_lines.append(f"  Task: [yellow]{context.task_id}[/yellow]")

    # Add suggestions
    suggestions = get_error_suggestions(error)
    content_lines.append("")
    content_lines.append("[bold]Suggestions:[/bold]")
    for i, suggestion in enumerate(suggestions, 1):
        content_lines.append(f"  {i}. {suggestion}")

    # Add traceback if requested
    if show_traceback:
        content_lines.append("")
        content_lines.append("[bold]Traceback:[/bold]")
        tb_str = traceback.format_exc()
        if tb_str and tb_str != "NoneType: None\n":
            syntax = Syntax(tb_str, "python", theme="monokai", line_numbers=True)
            content_lines.append(syntax)

    content = "\n".join(content_lines)

    # Choose border style based on severity
    border_styles = {
        "error": "red",
        "warning": "yellow",
        "info": "blue",
    }
    border_style = border_styles.get(severity, "red")

    panel = Panel(
        content,
        title=f"[bold]Error - {code}[/bold]",
        border_style=border_style,
        padding=(1, 2),
    )

    return panel


def format_generic_error(error: Exception, show_traceback: bool = False) -> Optional[str]:
    """Format a generic exception as a Rich panel."""
    if not RICH_AVAILABLE:
        return f"[{error.__class__.__name__}] {str(error)}"

    error_type = error.__class__.__name__
    error_msg = str(error)

    content_lines = [
        f"[bold]{error_msg}[/bold]",
        "",
        f"Error Type: [red]{error_type}[/red]",
    ]

    # Add suggestions based on error type
    if isinstance(error, FileNotFoundError):
        content_lines.append("")
        content_lines.append("[bold]Suggestions:[/bold]")
        content_lines.append("  1. Check if the file path is correct")
        content_lines.append("  2. Create the file if needed")
        content_lines.append("  3. Use absolute paths to avoid confusion")
    elif isinstance(error, PermissionError):
        content_lines.append("")
        content_lines.append("[bold]Suggestions:[/bold]")
        content_lines.append("  1. Check file/directory permissions")
        content_lines.append("  2. Try running with elevated privileges")
        content_lines.append("  3. Contact admin if issue persists")
    elif isinstance(error, ConnectionError):
        content_lines.append("")
        content_lines.append("[bold]Suggestions:[/bold]")
        content_lines.append("  1. Check network connectivity")
        content_lines.append("  2. Verify the service is running")
        content_lines.append("  3. Check firewall/proxy settings")
    else:
        for suggestion in FALLBACK_SUGGESTIONS:
            if "Suggestions" not in content_lines[-1]:
                content_lines.append("")
                content_lines.append("[bold]Suggestions:[/bold]")
            content_lines.append(f"  • {suggestion}")

    # Add traceback if requested
    if show_traceback:
        content_lines.append("")
        content_lines.append("[bold]Traceback:[/bold]")
        tb_str = traceback.format_exc()
        if tb_str and tb_str != "NoneType: None\n":
            syntax = Syntax(tb_str, "python", theme="monokai", line_numbers=True)
            content_lines.append(syntax)

    content = "\n".join(content_lines)
    panel = Panel(
        content,
        title=f"[bold]Error - {error_type}[/bold]",
        border_style="red",
        padding=(1, 2),
    )

    return panel


def handle_cli_error(
    error: Exception,
    explain: bool = False,
    ctx: Optional[Any] = None,
) -> None:
    """
    Handle CLI errors with user-friendly output.

    Args:
        error: The exception to handle
        explain: Whether to show detailed traceback and suggestions
        ctx: Typer context (optional)
    """
    if isinstance(error, AgentTeamError):
        formatted = format_error_panel(error, show_traceback=explain)
    else:
        formatted = format_generic_error(error, show_traceback=explain)

    if formatted:
        console.print(formatted)
    else:
        # Fallback if Rich is not available
        console.print(f"[red]Error:[/red] {error}")

    # Print retry info if error is retryable
    if isinstance(error, AgentTeamError) and getattr(error, "is_retryable", False):
        console.print("")
        console.print("[yellow]This operation can be retried.[/yellow]")


def create_entity_not_found_error(entity_type: str, entity_id: str) -> AgentTeamError:
    """Create an appropriate NotFoundError based on entity type."""
    error_map = {
        "agent": AgentNotFoundError,
        "team": TeamNotFoundError,
        "session": SessionNotFoundError,
        "config": ConfigNotFoundError,
    }

    error_class = error_map.get(entity_type.lower(), AgentTeamError)
    return error_class(f"{entity_type.capitalize()} '{entity_id}' not found")


class CLIErrorHandler:
    """Context manager for handling CLI errors gracefully."""

    def __init__(self, explain_errors: bool = False):
        self.explain_errors = explain_errors
        self.errors: list[Exception] = []

    def __enter__(self) -> "CLIErrorHandler":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            self.errors.append(exc_val)
            handle_cli_error(exc_val, explain=self.explain_errors)
        return False  # Don't suppress exceptions

    def add_error(self, error: Exception) -> None:
        """Manually add an error to track."""
        self.errors.append(error)
        handle_cli_error(error, explain=self.explain_errors)


def install_excepthook(explain_errors: bool = False) -> None:
    """
    Install a global exception hook for unhandled exceptions.

    This provides user-friendly error messages for any uncaught exception.
    """
    original_excepthook = sys.excepthook

    def custom_excepthook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            # Don't format keyboard interrupts
            original_excepthook(exc_type, exc_value, exc_tb)
            return

        # Format and display the error
        handle_cli_error(exc_value, explain=explain_errors)

    sys.excepthook = custom_excepthook
