"""
ClawTeam Exception System

Hierarchical exception classes with error codes, recovery strategies, and context tracking.
"""
from typing import Optional, Any
from dataclasses import dataclass, field
import asyncio
import traceback


@dataclass
class ErrorContext:
    """Context information for an error"""
    team_name: Optional[str] = None
    agent_id: Optional[str] = None
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    cause: Optional[Exception] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "team_name": self.team_name,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "cause": str(self.cause) if self.cause else None,
            "traceback": traceback.format_exc() if self.cause else None,
            "metadata": self.metadata,
        }


class ClawTeamError(Exception):
    """Base exception for all ClawTeam errors"""
    code: str = "CLAWTEAM_ERROR"
    is_retryable: bool = False
    severity: str = "error"

    def __init__(
        self,
        message: str = "",
        context: Optional[ErrorContext] = None,
        code: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.context = context or ErrorContext()
        if code:
            self.code = code

    def to_dict(self) -> dict:
        return {
            "type": self.__class__.__name__,
            "code": self.code,
            "message": self.message,
            "is_retryable": self.is_retryable,
            "severity": self.severity,
            "context": self.context.to_dict() if self.context else {},
        }

    def __str__(self) -> str:
        if self.context and self.context.team_name:
            return f"[{self.code}] {self.message} (team={self.context.team_name})"
        return f"[{self.code}] {self.message}"


# Agent-related errors
class AgentError(ClawTeamError):
    """Agent operation errors"""
    code = "AGENT_ERROR"
    severity = "error"


class AgentNotFoundError(AgentError):
    """Agent not found"""
    code = "AGENT_NOT_FOUND"


class AgentSpawnError(AgentError):
    """Failed to spawn agent"""
    code = "AGENT_SPAWN_ERROR"
    is_retryable = True


class AgentTimeoutError(AgentError):
    """Agent operation timed out"""
    code = "AGENT_TIMEOUT"
    is_retryable = True


class AgentCrashedError(AgentError):
    """Agent process crashed"""
    code = "AGENT_CRASHED"


# Team-related errors
class TeamError(ClawTeamError):
    """Team operation errors"""
    code = "TEAM_ERROR"
    severity = "error"


class TeamNotFoundError(TeamError):
    """Team not found"""
    code = "TEAM_NOT_FOUND"


class TeamFullError(TeamError):
    """Team has reached maximum capacity"""
    code = "TEAM_FULL"


class MemberNotFoundError(TeamError):
    """Team member not found"""
    code = "MEMBER_NOT_FOUND"


# Session-related errors
class SessionError(ClawTeamError):
    """Session operation errors"""
    code = "SESSION_ERROR"


class SessionNotFoundError(SessionError):
    """Session not found"""
    code = "SESSION_NOT_FOUND"


class SessionExpiredError(SessionError):
    """Session has expired"""
    code = "SESSION_EXPIRED"


# Transport/Mailbox errors
class TransportError(ClawTeamError):
    """Transport layer errors"""
    code = "TRANSPORT_ERROR"
    is_retryable = True


class MailboxError(TransportError):
    """Mailbox operation errors"""
    code = "MAILBOX_ERROR"


class MailboxFullError(MailboxError):
    """Mailbox is full"""
    code = "MAILBOX_FULL"


# Config errors
class ConfigError(ClawTeamError):
    """Configuration errors"""
    code = "CONFIG_ERROR"


class ConfigNotFoundError(ConfigError):
    """Config file not found"""
    code = "CONFIG_NOT_FOUND"


class ConfigValidationError(ConfigError):
    """Config validation failed"""
    code = "CONFIG_VALIDATION"


# Retryable errors mixin
class RetryableError(ClawTeamError):
    """Marker for errors that can be retried"""
    is_retryable = True


# Rate limiting
class RateLimitError(ClawTeamError):
    """Rate limit exceeded"""
    code = "RATE_LIMIT"
    is_retryable = True


# Authentication/Authorization
class AuthError(ClawTeamError):
    """Authentication/Authorization errors"""
    code = "AUTH_ERROR"


class PermissionDeniedError(AuthError):
    """Permission denied"""
    code = "PERMISSION_DENIED"


# Error Recovery Strategy
class ErrorRecovery:
    """Error recovery handler with exponential backoff"""

    def __init__(self):
        self.max_retries = 3
        self.base_delay = 1.0
        self.max_delay = 60.0

    async def recover(
        self,
        error: Exception,
        context: dict,
        retry_count: int = 0,
    ) -> tuple[bool, Any]:
        """
        Attempt to recover from an error.

        Returns:
            (success, result) tuple
        """
        if isinstance(error, ClawTeamError) and not error.is_retryable:
            if retry_count >= self.max_retries:
                return False, f"Max retries ({self.max_retries}) exceeded for non-retryable error"
            return False, None

        if retry_count >= self.max_retries:
            return False, f"Max retries ({self.max_retries}) exceeded"

        delay = min(self.base_delay * (2 ** retry_count), self.max_delay)

        if isinstance(error, AgentSpawnError):
            return await self._recover_agent_spawn(context, retry_count, delay)
        elif isinstance(error, AgentTimeoutError):
            return await self._recover_timeout(context, retry_count, delay)
        elif isinstance(error, TransportError):
            return await self._recover_transport(context, retry_count, delay)
        elif isinstance(error, RateLimitError):
            return await self._recover_rate_limit(context, retry_count, delay)
        else:
            return await self._recover_generic(context, retry_count, delay)

    async def _recover_agent_spawn(
        self, context: dict, retry_count: int, delay: float
    ) -> tuple[bool, Any]:
        """Recover from agent spawn failure"""
        await asyncio.sleep(delay)
        return True, {"action": "retry_spawn", "retry_count": retry_count + 1}

    async def _recover_timeout(
        self, context: dict, retry_count: int, delay: float
    ) -> tuple[bool, Any]:
        """Recover from timeout"""
        await asyncio.sleep(delay)
        return True, {"action": "retry", "retry_count": retry_count + 1}

    async def _recover_transport(
        self, context: dict, retry_count: int, delay: float
    ) -> tuple[bool, Any]:
        """Recover from transport error"""
        await asyncio.sleep(delay)
        return True, {"action": "reconnect", "retry_count": retry_count + 1}

    async def _recover_rate_limit(
        self, context: dict, retry_count: int, delay: float
    ) -> tuple[bool, Any]:
        """Recover from rate limit"""
        await asyncio.sleep(delay * 2)
        return True, {"action": "backoff", "retry_count": retry_count + 1}

    async def _recover_generic(
        self, context: dict, retry_count: int, delay: float
    ) -> tuple[bool, Any]:
        """Generic recovery"""
        await asyncio.sleep(delay)
        return True, {"action": "retry", "retry_count": retry_count + 1}


def format_error(error: Exception) -> str:
    """Format an exception for logging"""
    if isinstance(error, ClawTeamError):
        return str(error)
    return f"[{error.__class__.__name__}] {str(error)}"


__all__ = [
    "ErrorContext",
    "ClawTeamError",
    "AgentError",
    "AgentNotFoundError",
    "AgentSpawnError",
    "AgentTimeoutError",
    "AgentCrashedError",
    "TeamError",
    "TeamNotFoundError",
    "TeamFullError",
    "MemberNotFoundError",
    "SessionError",
    "SessionNotFoundError",
    "SessionExpiredError",
    "TransportError",
    "MailboxError",
    "MailboxFullError",
    "ConfigError",
    "ConfigNotFoundError",
    "ConfigValidationError",
    "RetryableError",
    "RateLimitError",
    "AuthError",
    "PermissionDeniedError",
    "ErrorRecovery",
    "format_error",
]
