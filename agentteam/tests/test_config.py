"""Tests for agentteam.config — new AppConfig-based configuration."""

from agentteam.config import (
    AppConfig,
    DatabaseConfig,
    AgentConfig,
    LogConfig,
    get_config,
    load_config,
    load_config_from_env,
)


class TestAppConfig:
    def test_defaults(self):
        cfg = AppConfig()
        assert cfg.debug is False
        assert cfg.transport == "file"
        assert cfg.database is not None
        assert cfg.database.path == "agentteam.db"
        assert cfg.agents is not None
        assert cfg.agents.max_concurrent == 10

    def test_custom_values(self):
        cfg = AppConfig(debug=True, transport="redis")
        assert cfg.debug is True
        assert cfg.transport == "redis"

    def test_nested_configs(self):
        cfg = AppConfig()
        cfg.database.path = "test.db"
        cfg.database.pool_size = 20
        assert cfg.database.path == "test.db"
        assert cfg.database.pool_size == 20

    def test_validate_default_valid(self):
        cfg = AppConfig()
        errors = cfg.validate()
        assert len(errors) == 0

    def test_to_dict(self):
        cfg = AppConfig()
        d = cfg.to_dict()
        assert "debug" in d
        assert "transport" in d
        assert "database" in d


class TestDatabaseConfig:
    def test_defaults(self):
        db = DatabaseConfig()
        assert db.path == "agentteam.db"
        assert db.pool_size == 5
        assert db.timeout == 30.0
        assert db.backup_enabled is True


class TestAgentConfig:
    def test_defaults(self):
        agents = AgentConfig()
        assert agents.max_concurrent == 10
        assert agents.spawn_timeout == 60.0
        assert agents.retry_attempts == 3


class TestGetConfig:
    def test_get_config_singleton(self):
        """get_config returns the same instance"""
        cfg1 = get_config()
        cfg2 = get_config()
        assert cfg1 is cfg2

    def test_load_config_returns_app_config(self):
        """load_config returns an AppConfig instance"""
        cfg = load_config()
        assert isinstance(cfg, AppConfig)

    def test_load_config_from_nonexistent_file(self):
        """load_config handles missing files gracefully"""
        cfg = load_config("nonexistent_config_file.yaml")
        assert isinstance(cfg, AppConfig)
        assert cfg.debug is False


class TestLoadConfigFromEnv:
    def test_load_from_env(self):
        """load_config_from_env runs without error"""
        cfg = load_config_from_env()
        assert isinstance(cfg, AppConfig)
