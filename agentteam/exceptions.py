"""AgentTeam custom exception hierarchy."""


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

    pass


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
