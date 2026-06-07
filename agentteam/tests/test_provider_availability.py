"""Tests for ProviderAvailability module (P9)."""

import subprocess
import tempfile
from pathlib import Path

import pytest

from agentteam.orchestrator.provider_availability import (
    ProviderAvailability,
    ProviderConfig,
    check_all_providers_availability,
    check_provider_availability,
    clear_availability_cache,
    get_availability_summary,
    get_available_providers,
    is_provider_available,
    register_provider_config,
    unregister_provider_config,
    PROVIDER_CONFIGS,
)


class TestProviderAvailability:
    """Tests for ProviderAvailability dataclass."""

    def test_availability_creation(self):
        """Test creating availability result."""
        avail = ProviderAvailability(
            id="claude-code",
            name="Claude Code",
            command="claude",
            available=True,
        )
        assert avail.id == "claude-code"
        assert avail.name == "Claude Code"
        assert avail.command == "claude"
        assert avail.available is True

    def test_availability_with_version(self):
        """Test availability with version."""
        avail = ProviderAvailability(
            id="claude-code",
            name="Claude Code",
            command="claude",
            available=True,
            version="1.0.0",
        )
        assert avail.version == "1.0.0"

    def test_availability_unavailable(self):
        """Test unavailable provider."""
        avail = ProviderAvailability(
            id="claude-code",
            name="Claude Code",
            command="claude",
            available=False,
            error="Not found",
        )
        assert avail.available is False
        assert avail.error == "Not found"

    def test_availability_timestamp(self):
        """Test availability timestamp."""
        avail = ProviderAvailability(
            id="claude-code",
            name="Claude Code",
            command="claude",
            available=True,
            last_checked="2024-01-01T00:00:00Z",
        )
        assert avail.last_checked is not None

    def test_availability_to_dict(self):
        """Test availability serialization."""
        avail = ProviderAvailability(
            id="claude-code",
            name="Claude Code",
            command="claude",
            available=True,
            version="1.0.0",
        )
        d = avail.to_dict()
        assert d["id"] == "claude-code"
        assert d["available"] is True
        assert d["version"] == "1.0.0"


class TestProviderConfig:
    """Tests for ProviderConfig dataclass."""

    def test_config_creation(self):
        """Test creating provider config."""
        config = ProviderConfig(
            id="claude-code",
            name="Claude Code",
            command="claude",
        )
        assert config.id == "claude-code"
        assert config.name == "Claude Code"
        assert config.command == "claude"

    def test_config_with_check_args(self):
        """Test config with check arguments."""
        config = ProviderConfig(
            id="claude-code",
            name="Claude Code",
            command="claude",
            check_args=["--version"],
        )
        assert config.check_args == ["--version"]

    def test_config_with_node_version(self):
        """Test config with Node version."""
        config = ProviderConfig(
            id="claude-code",
            name="Claude Code",
            command="claude",
            node_version="18",
        )
        assert config.node_version == "18"

    def test_config_to_dict(self):
        """Test config serialization."""
        config = ProviderConfig(
            id="claude-code",
            name="Claude Code",
            command="claude",
            check_args=["--version"],
        )
        d = config.to_dict()
        assert d["id"] == "claude-code"
        assert d["checkArgs"] == ["--version"]


class TestPredefinedProviderConfigs:
    """Tests for predefined provider configurations."""

    def test_claude_code_config(self):
        """Test Claude Code config."""
        assert "claude-code" in PROVIDER_CONFIGS
        config = PROVIDER_CONFIGS["claude-code"]
        assert config.command == "claude"

    def test_codex_config(self):
        """Test Codex config."""
        assert "codex" in PROVIDER_CONFIGS
        config = PROVIDER_CONFIGS["codex"]
        assert config.command == "codex"

    def test_gemini_config(self):
        """Test Gemini CLI config."""
        assert "gemini-cli" in PROVIDER_CONFIGS
        config = PROVIDER_CONFIGS["gemini-cli"]
        assert config.command == "gemini"

    def test_opencode_config(self):
        """Test OpenCode config."""
        assert "opencode" in PROVIDER_CONFIGS
        config = PROVIDER_CONFIGS["opencode"]
        assert config.command == "opencode"

    def test_kimi_config(self):
        """Test Kimi config."""
        assert "kimi" in PROVIDER_CONFIGS
        config = PROVIDER_CONFIGS["kimi"]
        assert config.command == "kimi"

    def test_qwen_config(self):
        """Test Qwen config."""
        assert "qwen" in PROVIDER_CONFIGS
        config = PROVIDER_CONFIGS["qwen"]
        assert config.command == "qwen"

    def test_openclaw_config(self):
        """Test OpenClaw config."""
        assert "openclaw" in PROVIDER_CONFIGS
        config = PROVIDER_CONFIGS["openclaw"]
        assert config.command == "openclaw"

    def test_all_configs_have_check_args(self):
        """Test all configs have check args."""
        for provider_id, config in PROVIDER_CONFIGS.items():
            assert len(config.check_args) > 0


class TestCheckProviderAvailability:
    """Tests for check_provider_availability function."""

    def test_check_known_provider(self):
        """Test checking known provider."""
        clear_availability_cache()
        result = check_provider_availability("claude-code")
        assert result.id == "claude-code"
        assert result.name == "Claude Code"

    def test_check_unknown_provider(self):
        """Test checking unknown provider."""
        result = check_provider_availability("unknown-provider")
        assert result.id == "unknown-provider"
        assert result.available is False
        assert "Unknown provider" in result.error

    def test_check_returns_availability_object(self):
        """Test check returns ProviderAvailability."""
        result = check_provider_availability("claude-code")
        assert isinstance(result, ProviderAvailability)

    def test_check_updates_timestamp(self):
        """Test check updates timestamp."""
        clear_availability_cache()
        result = check_provider_availability("claude-code")
        assert result.last_checked is not None


class TestCheckAllProvidersAvailability:
    """Tests for check_all_providers_availability function."""

    def test_check_all_returns_list(self):
        """Test check all returns list."""
        clear_availability_cache()
        results = check_all_providers_availability()
        assert isinstance(results, list)

    def test_check_all_includes_all_configs(self):
        """Test check all includes all configs."""
        clear_availability_cache()
        results = check_all_providers_availability()
        assert len(results) == len(PROVIDER_CONFIGS)

    def test_check_all_returns_availability_objects(self):
        """Test check all returns availability objects."""
        clear_availability_cache()
        results = check_all_providers_availability()
        for result in results:
            assert isinstance(result, ProviderAvailability)


class TestGetAvailableProviders:
    """Tests for get_available_providers function."""

    def test_get_available_returns_list(self):
        """Test get available returns list."""
        clear_availability_cache()
        results = get_available_providers()
        assert isinstance(results, list)

    def test_get_available_only_available(self):
        """Test get available only returns available."""
        clear_availability_cache()
        results = get_available_providers()
        for result in results:
            assert result.available is True


class TestIsProviderAvailable:
    """Tests for is_provider_available function."""

    def test_is_available_returns_bool(self):
        """Test is available returns bool."""
        clear_availability_cache()
        result = is_provider_available("claude-code")
        assert isinstance(result, bool)

    def test_is_available_unknown_provider(self):
        """Test is available for unknown provider."""
        result = is_provider_available("unknown-provider")
        assert result is False


class TestGetAvailabilitySummary:
    """Tests for get_availability_summary function."""

    def test_summary_returns_dict(self):
        """Test summary returns dict."""
        clear_availability_cache()
        summary = get_availability_summary()
        assert isinstance(summary, dict)

    def test_summary_has_required_fields(self):
        """Test summary has required fields."""
        clear_availability_cache()
        summary = get_availability_summary()
        assert "totalProviders" in summary
        assert "availableCount" in summary
        assert "unavailableCount" in summary
        assert "availableProviders" in summary
        assert "unavailableProviders" in summary
        assert "lastChecked" in summary

    def test_summary_counts_match(self):
        """Test summary counts match."""
        clear_availability_cache()
        summary = get_availability_summary()
        total = summary["totalProviders"]
        available = summary["availableCount"]
        unavailable = summary["unavailableCount"]
        assert total == available + unavailable


class TestRegisterProviderConfig:
    """Tests for register_provider_config function."""

    def test_register_new_config(self):
        """Test registering new config."""
        config = ProviderConfig(
            id="custom-provider",
            name="Custom Provider",
            command="custom",
            check_args=["--version"],
        )
        register_provider_config(config)

        assert "custom-provider" in PROVIDER_CONFIGS
        # Cleanup
        unregister_provider_config("custom-provider")

    def test_register_overwrites_existing(self):
        """Test register overwrites existing."""
        original = PROVIDER_CONFIGS.get("claude-code")

        config = ProviderConfig(
            id="claude-code",
            name="Modified Claude",
            command="claude-modified",
        )
        register_provider_config(config)

        assert PROVIDER_CONFIGS["claude-code"].name == "Modified Claude"

        # Restore original
        if original:
            register_provider_config(original)


class TestUnregisterProviderConfig:
    """Tests for unregister_provider_config function."""

    def test_unregister_existing(self):
        """Test unregistering existing config."""
        config = ProviderConfig(
            id="temp-provider",
            name="Temp Provider",
            command="temp",
        )
        register_provider_config(config)

        result = unregister_provider_config("temp-provider")
        assert result is True
        assert "temp-provider" not in PROVIDER_CONFIGS

    def test_unregister_nonexistent(self):
        """Test unregistering nonexistent config."""
        result = unregister_provider_config("nonexistent-provider")
        assert result is False


class TestClearAvailabilityCache:
    """Tests for clear_availability_cache function."""

    def test_clear_cache(self):
        """Test clearing cache."""
        # First check to populate cache
        check_provider_availability("claude-code")

        # Clear cache
        clear_availability_cache()

        # Cache should be empty
        from agentteam.orchestrator.provider_availability import _cache

        assert len(_cache) == 0

    def test_clear_cache_forces_recheck(self):
        """Test clear cache forces recheck."""
        clear_availability_cache()

        # First check
        result1 = check_provider_availability("claude-code")

        # Second check (cached)
        result2 = check_provider_availability("claude-code")

        # Timestamps should be same (cached)
        assert result1.last_checked == result2.last_checked

        # Clear and recheck
        clear_availability_cache()
        result3 = check_provider_availability("claude-code")

        # Timestamp should be different
        assert result3.last_checked != result1.last_checked


class TestProviderAvailabilityEdgeCases:
    """Edge case tests for ProviderAvailability."""

    def test_check_with_timeout(self):
        """Test check with timeout scenario."""
        # This tests the timeout handling in the implementation
        clear_availability_cache()
        result = check_provider_availability("claude-code")
        # Should not raise even if timeout occurs
        assert result is not None

    def test_check_absolute_path(self):
        """Test check with absolute path."""
        config = ProviderConfig(
            id="absolute-test",
            name="Absolute Test",
            command="/usr/bin/test",
        )
        register_provider_config(config)

        result = check_provider_availability("absolute-test")
        assert result is not None

        unregister_provider_config("absolute-test")

    def test_check_with_node_version(self):
        """Test check with Node version."""
        config = ProviderConfig(
            id="node-test",
            name="Node Test",
            command="node",
            node_version="18",
        )
        register_provider_config(config)

        result = check_provider_availability("node-test")
        assert result is not None

        unregister_provider_config("node-test")

    def test_multiple_checks_same_provider(self):
        """Test multiple checks for same provider."""
        clear_availability_cache()

        results = [check_provider_availability("claude-code") for _ in range(5)]

        # All should return same result (cached)
        for result in results:
            assert result.id == "claude-code"

    def test_check_all_after_register(self):
        """Test check all after registering new provider."""
        config = ProviderConfig(
            id="new-provider",
            name="New Provider",
            command="new",
            check_args=["--version"],
        )
        register_provider_config(config)

        clear_availability_cache()
        results = check_all_providers_availability()

        # Should include new provider
        ids = [r.id for r in results]
        assert "new-provider" in ids

        unregister_provider_config("new-provider")
