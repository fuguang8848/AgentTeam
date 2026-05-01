"""
ClawTeam Structured Logging

Provides structured JSON logging with context propagation and log aggregation support.
"""
import os
import sys
import json
import logging
import threading
from datetime import datetime, timezone
from typing import Optional, Any
from dataclasses import dataclass, field
from contextvars import ContextVar
from pathlib import Path


# Context variables for request/session tracking
request_id: ContextVar[str] = ContextVar("request_id", default="")
session_id: ContextVar[str] = ContextVar("session_id", default="")
team_name: ContextVar[str] = ContextVar("team_name", default="")
agent_id: ContextVar[str] = ContextVar("agent_id", default="")


@dataclass
class LogEntry:
    """Structured log entry"""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    level: str = "INFO"
    message: str = ""
    logger: str = ""
    request_id: str = ""
    session_id: str = ""
    team_name: str = ""
    agent_id: str = ""
    duration_ms: Optional[float] = None
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        result = {
            "timestamp": self.timestamp,
            "level": self.level,
            "message": self.message,
            "logger": self.logger,
        }
        if self.request_id:
            result["request_id"] = self.request_id
        if self.session_id:
            result["session_id"] = self.session_id
        if self.team_name:
            result["team_name"] = self.team_name
        if self.agent_id:
            result["agent_id"] = self.agent_id
        if self.duration_ms is not None:
            result["duration_ms"] = self.duration_ms
        if self.error:
            result["error"] = self.error
        if self.metadata:
            result["metadata"] = self.metadata
        return result

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


class StructuredLogger:
    """
    Structured logger with context propagation and JSON output.
    """

    def __init__(self, name: str, level: str = "INFO", json_output: bool = False):
        self.name = name
        self.level = getattr(logging, level.upper(), logging.INFO)
        self.json_output = json_output or os.environ.get("CLAWTEAM_LOG_JSON", "") == "1"
        self._local = threading.local()

    def _get_context(self) -> dict:
        """Get current logging context"""
        return {
            "request_id": request_id.get(),
            "session_id": session_id.get(),
            "team_name": team_name.get(),
            "agent_id": agent_id.get(),
        }

    def _log(
        self,
        level: str,
        message: str,
        error: Optional[Exception] = None,
        duration_ms: Optional[float] = None,
        **metadata,
    ):
        """Internal log method"""
        entry = LogEntry(
            level=level,
            message=message,
            logger=self.name,
            error=str(error) if error else None,
            duration_ms=duration_ms,
            metadata=metadata,
            **self._get_context(),
        )

        if self.json_output:
            output = entry.to_json()
        else:
            parts = [f"[{entry.timestamp}]", f"[{level}]", f"[{self.name}]"]
            if entry.team_name:
                parts.append(f"[team={entry.team_name}]")
            if entry.agent_id:
                parts.append(f"[agent={entry.agent_id}]")
            parts.append(message)
            if entry.error:
                parts.append(f"error={entry.error}")
            if entry.duration_ms is not None:
                parts.append(f"duration={entry.duration_ms}ms")
            if metadata:
                parts.append(f"meta={metadata}")
            output = " ".join(parts)

        if level == "ERROR":
            sys.stderr.write(output + "\n")
            sys.stderr.flush()
        else:
            sys.stdout.write(output + "\n")
            sys.stdout.flush()

    def debug(self, message: str, **metadata):
        if self.level <= logging.DEBUG:
            self._log("DEBUG", message, **metadata)

    def info(self, message: str, **metadata):
        if self.level <= logging.INFO:
            self._log("INFO", message, **metadata)

    def warning(self, message: str, **metadata):
        if self.level <= logging.WARNING:
            self._log("WARNING", message, **metadata)

    def error(self, message: str, error: Optional[Exception] = None, **metadata):
        if self.level <= logging.ERROR:
            self._log("ERROR", message, error=error, **metadata)

    def critical(self, message: str, error: Optional[Exception] = None, **metadata):
        if self.level <= logging.CRITICAL:
            self._log("CRITICAL", message, error=error, **metadata)

    # Convenience methods for common logging patterns
    def agent_spawned(self, agent_id: str, team: str, **metadata):
        self.info(f"Agent {agent_id} spawned in team {team}", agent_id=agent_id, team=team, **metadata)

    def agent_completed(self, agent_id: str, duration_ms: float, **metadata):
        self.info(f"Agent {agent_id} completed", agent_id=agent_id, duration_ms=duration_ms, **metadata)

    def agent_failed(self, agent_id: str, error: Exception, **metadata):
        self.error(f"Agent {agent_id} failed", error=error, agent_id=agent_id, **metadata)

    def task_started(self, task_id: str, action: str, **metadata):
        self.info(f"Task {task_id} started: {action}", task_id=task_id, action=action, **metadata)

    def task_completed(self, task_id: str, duration_ms: float, **metadata):
        self.info(f"Task {task_id} completed", task_id=task_id, duration_ms=duration_ms, **metadata)

    def task_failed(self, task_id: str, error: Exception, **metadata):
        self.error(f"Task {task_id} failed", error=error, task_id=task_id, **metadata)


class LoggerFactory:
    """Factory for creating structured loggers"""

    _loggers: dict = {}
    _default_level = "INFO"
    _json_output = False

    @classmethod
    def configure(cls, level: str = "INFO", json_output: bool = False):
        """Configure the logger factory"""
        cls._default_level = level
        cls._json_output = json_output

    @classmethod
    def get_logger(cls, name: str) -> StructuredLogger:
        """Get or create a logger"""
        if name not in cls._loggers:
            cls._loggers[name] = StructuredLogger(
                name=name,
                level=cls._default_level,
                json_output=cls._json_output,
            )
        return cls._loggers[name]

    @classmethod
    def clear(cls):
        """Clear all loggers (useful for testing)"""
        cls._loggers.clear()


# Convenience function
def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger"""
    return LoggerFactory.get_logger(name)


# Global logger for clawteam module
logger = get_logger("clawteam")


__all__ = [
    "StructuredLogger",
    "LoggerFactory",
    "LogEntry",
    "get_logger",
    "logger",
    "request_id",
    "session_id",
    "team_name",
    "agent_id",
]
