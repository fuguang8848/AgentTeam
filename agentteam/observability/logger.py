"""
AgentTeam Structured Logger Module

Provides structured logging with:
- JSON output option
- Correlation IDs
- Context propagation
- Log levels with colors
"""

from __future__ import annotations

import json
import logging
import sys
import traceback
from datetime import datetime
from typing import Any, Optional

try:
    from rich.console import Console
    from rich.logging import RichHandler
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from agentteam.utils.logger import get_logger as get_basic_logger

# Try to get existing logger setup
try:
    from agentteam.utils.logger import setup_logging, LoggerSetup
    LOGGER_UTILS_AVAILABLE = True
except ImportError:
    LOGGER_UTILS_AVAILABLE = False


class StructuredLogger:
    """
    Structured logger for AgentTeam.

    Provides:
    - Structured (JSON) output
    - Correlation ID tracking
    - Context enrichment
    - Rich console output option
    """

    def __init__(
        self,
        name: str,
        structured: bool = False,
        correlation_id: Optional[str] = None,
    ):
        self.name = name
        self.structured = structured
        self.correlation_id = correlation_id
        self._base_logger = logging.getLogger(name)
        self._context: dict[str, Any] = {}

    def set_correlation_id(self, correlation_id: str) -> None:
        """Set correlation ID for request tracing."""
        self.correlation_id = correlation_id

    def add_context(self, **kwargs: Any) -> None:
        """Add context fields to all subsequent log messages."""
        self._context.update(kwargs)

    def clear_context(self) -> None:
        """Clear all context fields."""
        self._context.clear()

    def _build_record(
        self,
        level: str,
        message: str,
        extra: Optional[dict[str, Any]] = None,
        exc_info: bool = False,
    ) -> dict[str, Any]:
        """Build a structured log record."""
        record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "logger": self.name,
            "message": message,
        }

        if self.correlation_id:
            record["correlation_id"] = self.correlation_id

        if self._context:
            record["context"] = self._context

        if extra:
            record["extra"] = extra

        if exc_info:
            record["exception"] = traceback.format_exc()

        return record

    def _format_message(self, record: dict[str, Any]) -> str:
        """Format log record for output."""
        if self.structured:
            return json.dumps(record, default=str)
        else:
            # Human-readable format
            parts = [
                f"[{record['timestamp']}]",
                f"[{record['level']}]",
                f"[{record['logger']}]",
                record["message"],
            ]
            if "context" in record:
                parts.append(f"({record['context']})")
            return " ".join(parts)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log a debug message."""
        record = self._build_record("DEBUG", message, kwargs.get("extra"))
        self._base_logger.debug(self._format_message(record))

    def info(self, message: str, **kwargs: Any) -> None:
        """Log an info message."""
        record = self._build_record("INFO", message, kwargs.get("extra"))
        self._base_logger.info(self._format_message(record))

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log a warning message."""
        record = self._build_record("WARNING", message, kwargs.get("extra"))
        self._base_logger.warning(self._format_message(record))

    def error(self, message: str, **kwargs: Any) -> None:
        """Log an error message."""
        exc_info = kwargs.get("exc_info", False)
        record = self._build_record("ERROR", message, kwargs.get("extra"), exc_info)
        self._base_logger.error(self._format_message(record))

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log a critical message."""
        exc_info = kwargs.get("exc_info", False)
        record = self._build_record("CRITICAL", message, kwargs.get("extra"), exc_info)
        self._base_logger.critical(self._format_message(record))

    def log(self, level: int, message: str, **kwargs: Any) -> None:
        """Log at the specified level."""
        record = self._build_record(
            logging.getLevelName(level),
            message,
            kwargs.get("extra"),
        )
        self._base_logger.log(level, self._format_message(record))


class ContextLogger:
    """
    Logger context manager for adding temporary context.

    Usage:
        logger = get_logger(__name__)
        with logger.context(user_id="123"):
            logger.info("Processing request")  # Includes user_id
        # user_id no longer in context
    """

    def __init__(self, logger: StructuredLogger, **context):
        self.logger = logger
        self.context = context
        self._old_context: dict[str, Any] = {}

    def __enter__(self) -> "ContextLogger":
        self._old_context = dict(self.logger._context)
        self.logger.add_context(**self.context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.logger._context = self._old_context
        return False


# Cache for loggers
_loggers: dict[str, StructuredLogger] = {}
_structured_mode: bool = False


def set_structured_mode(enabled: bool) -> None:
    """Enable or disable structured (JSON) logging."""
    global _structured_mode
    _structured_mode = enabled


def get_logger(name: str, structured: Optional[bool] = None) -> StructuredLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)
        structured: Override global structured mode

    Returns:
        StructuredLogger instance
    """
    if name in _loggers:
        return _loggers[name]

    if structured is None:
        structured = _structured_mode

    logger = StructuredLogger(name, structured=structured)
    _loggers[name] = logger
    return logger


def setup_structured_logging(
    level: str = "INFO",
    structured: bool = False,
    use_rich: bool = True,
) -> None:
    """
    Setup structured logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        structured: Enable JSON output
        use_rich: Use Rich for colored console output
    """
    global _structured_mode
    _structured_mode = structured

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create handler
    if use_rich and RICH_AVAILABLE:
        handler = RichHandler(
            console=Console(stderr=True),
            show_time=True,
            show_path=False,
            markup=True,
            rich_tracebacks=True,
        )
    else:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        )

    root_logger.addHandler(handler)

    # Set structured mode for new loggers
    if structured:
        set_structured_mode(True)
