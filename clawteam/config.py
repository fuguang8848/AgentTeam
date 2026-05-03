"""
Configuration management for ClawTeam

Provides centralized configuration with validation and environment variable support.
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional, TypeVar

import yaml

from clawteam.exceptions import ConfigError
from clawteam.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound="BaseConfig")


class ConfigSource(str, Enum):
    """Configuration source"""

    DEFAULT = "default"
    FILE = "file"
    ENVIRONMENT = "environment"
    COMMAND_LINE = "command_line"


@dataclass
class ConfigField:
    """Metadata for a configuration field"""

    name: str
    field_type: type
    default: Any = None
    description: str = ""
    env_var: Optional[str] = None
    required: bool = False
    validator: Optional[callable] = None


class BaseConfig:
    """
    Base configuration class with validation and environment variable support

    Example:
        class AgentConfig(BaseConfig):
            max_concurrent: int = 10
            spawn_timeout: float = 60.0
            retry_attempts: int = 3

        class AppConfig(BaseConfig):
            agents: AgentConfig = AgentConfig()
            debug: bool = False

        # Load from file
        config = AppConfig.load("config.yaml")

        # Load from environment
        config = AppConfig.load_from_env(prefix="CLAWTEAM_")
    """

    _fields: dict[str, ConfigField] = {}

    def __init__(self, **kwargs):
        # Set defaults
        for name, field_info in self._get_fields().items():
            if hasattr(field_info.field_type, "__dataclass_fields__"):
                # Nested config
                value = kwargs.get(name, field_info.default)
                if value is None and field_info.default is None:
                    value = field_info.field_type()
                setattr(self, name, value)
            else:
                setattr(self, name, kwargs.get(name, field_info.default))

    @classmethod
    def _get_fields(cls) -> dict[str, ConfigField]:
        """Get configuration fields from class"""
        if cls not in _config_fields_cache:
            fields = {}
            for name in dir(cls):
                if name.startswith("_"):
                    continue
                value = getattr(cls, name, None)
                if isinstance(value, ConfigField):
                    fields[name] = value
                elif not callable(value) and not name.startswith("_"):
                    # Infer field from type annotation or default value
                    pass  # Will be handled by dataclass-like processing
            _config_fields_cache[cls] = fields
        return _config_fields_cache.get(cls, {})

    @classmethod
    def load(cls: type[T], path: str, **overrides) -> T:
        """
        Load configuration from YAML file

        Args:
            path: Path to YAML configuration file
            **overrides: Field values to override

        Returns:
            Config instance
        """
        config_path = Path(path)

        if not config_path.exists():
            logger.warning(f"Config file not found: {path}, using defaults")
            instance = cls(**overrides)
            return instance

        try:
            with open(config_path) as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            raise ConfigError(f"Failed to load config from {path}: {e}")

        # Merge with overrides
        data.update(overrides)

        # Create instance
        instance = cls(**data)
        instance._source = ConfigSource.FILE
        instance._source_path = str(config_path)

        return instance

    @classmethod
    def load_from_env(cls: type[T], prefix: str = "", **overrides) -> T:
        """
        Load configuration from environment variables

        Environment variables should be named like:
        {PREFIX}{SECTION}_{FIELD}

        Example:
            CLAWTEAM_AGENTS_MAX_CONCURRENT=10
            CLAWTEAM_DEBUG=true

        Args:
            prefix: Environment variable prefix
            **overrides: Field values to override

        Returns:
            Config instance
        """
        data = {}

        for name, field_info in cls._get_fields().items():
            if not field_info.env_var:
                env_var = f"{prefix}{name}".upper()
            else:
                env_var = field_info.env_var

            env_value = os.environ.get(env_var)
            if env_value is not None:
                # Convert to appropriate type
                if field_info.field_type == bool:
                    data[name] = env_value.lower() in ("true", "1", "yes")
                elif field_info.field_type in (int, float):
                    data[name] = field_info.field_type(env_value)
                else:
                    data[name] = env_value

        # Merge with overrides
        data.update(overrides)

        # Create instance
        instance = cls(**data)
        instance._source = ConfigSource.ENVIRONMENT

        return instance

    def validate(self) -> list[str]:
        """
        Validate configuration

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        for name, field_info in self._get_fields().items():
            value = getattr(self, name)

            # Required check
            if field_info.required and value is None:
                errors.append(f"{name}: required field is missing")
                continue

            # Type check
            if value is not None and not isinstance(value, field_info.field_type):
                errors.append(f"{name}: expected {field_info.field_type.__name__}, got {type(value).__name__}")
                continue

            # Custom validator
            if field_info.validator and value is not None:
                try:
                    field_info.validator(value)
                except Exception as e:
                    errors.append(f"{name}: validation failed: {e}")

        return errors

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        result = {}
        for name in dir(self):
            if name.startswith("_"):
                continue
            value = getattr(self, name)
            if callable(value):
                continue
            result[name] = value
        return result

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.to_dict()})"


# Cache for config fields
_config_fields_cache: dict[type, dict[str, ConfigField]] = {}


# Common configuration classes


@dataclass
class DatabaseConfig(BaseConfig):
    """Database configuration"""

    path: str = "clawteam.db"
    pool_size: int = 5
    timeout: float = 30.0
    backup_enabled: bool = True
    backup_interval: int = 3600  # seconds


@dataclass
class AgentConfig(BaseConfig):
    """Agent configuration"""

    max_concurrent: int = 10
    spawn_timeout: float = 60.0
    retry_attempts: int = 3
    health_check_interval: float = 30.0


@dataclass
class LogConfig(BaseConfig):
    """Logging configuration"""

    level: str = "INFO"
    json_output: bool = False
    file_path: Optional[str] = None
    max_size_mb: int = 100
    backup_count: int = 5


@dataclass
class MetricsConfig(BaseConfig):
    """Metrics configuration"""

    enabled: bool = True
    export_interval: float = 60.0
    prometheus_port: int = 9090


@dataclass
class AlertConfig(BaseConfig):
    """Alert configuration"""

    enabled: bool = True
    channels: list[str] = field(default_factory=lambda: ["log"])
    webhook_url: Optional[str] = None


@dataclass
class AppConfig(BaseConfig):
    """Main application configuration"""

    # User identity fields (for backward compatibility)
    user: str = ""
    data_dir: str = ""
    workspace: str = "auto"
    default_backend: str = "tmux"
    skip_permissions: bool = True
    default_team: str = ""

    # Transport and debug
    transport: str = "file"  # Transport backend: file, redis, etc.
    debug: bool = False

    # Task store (for backward compatibility with task store abstraction)
    task_store: str = ""  # "file" (default) — extensible for redis/sql later

    # Spawn settings
    spawn_ready_timeout: float = 30.0  # max seconds to poll for TUI readiness before fallback

    # Model resolution (per-agent model selection)
    default_model: str = ""  # Fallback model when no other config applies
    model_tiers: dict = field(default_factory=dict)  # Model tier aliases, e.g. {"strong": "claude-opus"}

    # Nested configs
    database: Optional[DatabaseConfig] = None
    agents: Optional[AgentConfig] = None
    logging: Optional[LogConfig] = None
    metrics: Optional[MetricsConfig] = None
    alerts: Optional[AlertConfig] = None

    def __post_init__(self):
        # Set defaults for nested configs if not provided
        if self.database is None:
            self.database = DatabaseConfig()
        if self.agents is None:
            self.agents = AgentConfig()
        if self.logging is None:
            self.logging = LogConfig()
        if self.metrics is None:
            self.metrics = MetricsConfig()
        if self.alerts is None:
            self.alerts = AlertConfig()


# Global config instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get global configuration instance"""
    global _config
    if _config is None:
        _config = AppConfig()
    return _config


def load_config(path: str = "config.yaml") -> AppConfig:
    """Load configuration from file"""
    global _config
    # Check if path exists, otherwise check default config locations
    config_path_obj = Path(path)
    if not config_path_obj.exists():
        # Try fallback locations
        fallback = Path.home() / ".config" / "clawteam" / "config.json"
        if fallback.exists():
            config_path_obj = fallback
    _config = AppConfig.load(str(config_path_obj))
    return _config


def load_config_from_env(prefix: str = "CLAWTEAM_") -> AppConfig:
    """Load configuration from environment variables"""
    global _config
    _config = AppConfig.load_from_env(prefix)
    return _config


# Backward compatibility aliases
ClawTeamConfig = AppConfig


def save_config(cfg: AppConfig) -> None:
    """Save configuration to file (for backward compatibility)"""
    import json

    config_file = Path.home() / ".config" / "clawteam" / "config.json"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    data = cfg.to_dict()
    # Remove nested configs from top-level for old format
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def config_path() -> Path:
    """Get config file path (for backward compatibility)"""
    return Path.home() / ".config" / "clawteam" / "config.json"


def get_effective(key: str) -> tuple:
    """Get effective config value (for backward compatibility)

    Returns (value, source) tuple where source is 'env', 'file', or 'default'
    """
    # Check environment first
    env_key = f"CLAWTEAM_{key.upper()}"
    if env_key in os.environ:
        return os.environ[env_key], "env"

    # Check config file
    cfg = load_config()
    if hasattr(cfg, key):
        value = getattr(cfg, key)
        if value:
            return value, "file"

    # Return default
    if hasattr(cfg, key):
        return getattr(cfg, key), "default"
    return "", "default"


__all__ = [
    "ConfigSource",
    "ConfigField",
    "BaseConfig",
    "DatabaseConfig",
    "AgentConfig",
    "LogConfig",
    "MetricsConfig",
    "AlertConfig",
    "AppConfig",
    # Backward compatibility
    "ClawTeamConfig",
    "save_config",
    "config_path",
    "get_effective",
    "get_config",
    "load_config",
    "load_config_from_env",
]
