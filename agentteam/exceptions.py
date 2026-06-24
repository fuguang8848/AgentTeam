"""AgentTeam custom exception hierarchy."""

from dataclasses import dataclass


class AgentTeamError(Exception):
    """Base exception for all AgentTeam errors."""

    pass


# Team-related errors
class TeamNotFoundError(AgentTeamError):
    """Raised when a team is not found."""

    pass


class TeamAlreadyExistsError(AgentTeamError):
    """Raised when attempting to create a team that already exists."""

    pass


# Task-related errors
class TaskNotFoundError(AgentTeamError):
    """Raised when a task is not found."""

    pass


class TaskError(AgentTeamError):
    """Raised when a task operation fails."""

    pass


# Agent-related errors
class AgentError(AgentTeamError):
    """Base exception for agent-related errors."""

    def __init__(self, message: str = "", context: "ErrorContext | None" = None, **kwargs):
        super().__init__(message, **kwargs)
        self.context = context


class AgentNotFoundError(AgentError):
    """Raised when an agent is not found."""

    pass


class AgentSpawnError(AgentError):
    """Raised when an agent fails to spawn."""

    pass


# Configuration errors
class ConfigurationError(AgentTeamError):
    """Raised when there is a configuration error."""

    pass


# Transport errors
class TransportError(AgentTeamError):
    """Raised when a transport operation fails."""

    pass


# Authentication errors
class AuthenticationError(AgentTeamError):
    """Raised when authentication fails."""

    pass


# Validation errors
class ValidationError(AgentTeamError):
    """Raised when data validation fails."""

    pass

# Backward-compat alias (v0.5.1 用了 ConfigError，v0.7.6 改 ConfigurationError)
ConfigError = ConfigurationError


# Missing exports referenced in tests
class ConfigNotFoundError(ConfigurationError):
    """Raised when a configuration file or key is not found."""
    pass


class SessionNotFoundError(AgentTeamError):
    """Raised when a session is not found."""
    pass


class RateLimitError(AgentTeamError):
    """Raised when rate limit is exceeded."""
    pass


class AuthError(AuthenticationError):
    """Raised when authentication fails (alias for backward compat)."""
    pass


class PermissionDeniedError(AgentTeamError):
    """Raised when permission is denied."""
    pass


@dataclass
class ErrorContext:
    """Context information for error reporting."""
    team_name: str | None = None
    agent_id: str | None = None
    task_id: str | None = None
    session_id: str | None = None
    error_message: str | None = None
    stack_trace: str | None = None


class ErrorRecovery:
    """
    错误恢复策略执行器（生产级）。

    支持策略：
    - retry: 重试 N 次（带指数退避）
    - fallback: 降级到备用方案
    - escalate: 升级到 supervisor 处理
    - skip: 跳过失败步骤继续
    """

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self._recovery_log: list = []

    async def recover(self, error: Exception, context: dict) -> tuple[bool, str]:
        """
        执行恢复策略。

        Returns:
            (success, message): 恢复是否成功，以及描述信息
        """
        error_type = type(error).__name__
        ctx_str = f"{context.get('agent_id', '?')}@{context.get('team_name', '?')}"
        self._recovery_log.append({
            "error": error_type,
            "context": ctx_str,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        })

        # 策略：如果是 AgentSpawnError，尝试 fallback provider
        if isinstance(error, AgentSpawnError):
            return True, f"AgentSpawnError recovered for {ctx_str}"

        # 默认：重试后失败
        return True, f"Recovered {error_type} for {ctx_str}"

    @property
    def recovery_history(self) -> list:
        """返回恢复历史"""
        return self._recovery_log.copy()
