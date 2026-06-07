"""Tests for ProviderCapability module (P9)."""

import pytest

from agentteam.orchestrator.provider_capability import (
    ProviderCapability,
    ProviderCapabilityRegistry,
    ProviderMcpCapability,
    ProviderSkillCapability,
    McpFallbackType,
    PROVIDER_CAPABILITIES,
)


class TestProviderCapability:
    """Tests for ProviderCapability model."""

    def test_capability_creation(self):
        """Test creating provider capability."""
        cap = ProviderCapability(
            provider_id="claude-code",
        )
        assert cap.provider_id == "claude-code"

    def test_capability_streaming(self):
        """Test streaming capability."""
        cap = ProviderCapability(
            provider_id="claude-code",
            supports_streaming=True,
        )
        assert cap.supports_streaming is True

    def test_capability_tools(self):
        """Test tools capability."""
        cap = ProviderCapability(
            provider_id="claude-code",
            supports_tools=True,
        )
        assert cap.supports_tools is True

    def test_capability_images(self):
        """Test image capability."""
        cap = ProviderCapability(
            provider_id="claude-code",
            supports_images=True,
        )
        assert cap.supports_images is True

    def test_capability_long_context(self):
        """Test long context capability."""
        cap = ProviderCapability(
            provider_id="claude-code",
            supports_long_context=True,
            max_context_tokens=200000,
        )
        assert cap.supports_long_context is True
        assert cap.max_context_tokens == 200000

    def test_capability_mcp_support(self):
        """Test MCP capability via mcp_support object."""
        mcp_support = ProviderMcpCapability(
            native=True,
            config_flag="--mcp-config",
            config_format="json",
            fallback=McpFallbackType.NONE,
        )
        cap = ProviderCapability(
            provider_id="claude-code",
            mcp_support=mcp_support,
        )
        assert cap.mcp_support.native is True
        assert cap.mcp_support.config_flag == "--mcp-config"

    def test_capability_skill_support(self):
        """Test skill capability via skill_support object."""
        skill_support = ProviderSkillCapability(
            slash_commands=True,
            system_prompt=True,
            native_skill_dir=".claude/commands",
        )
        cap = ProviderCapability(
            provider_id="claude-code",
            skill_support=skill_support,
        )
        assert cap.skill_support.slash_commands is True
        assert cap.skill_support.system_prompt is True

    def test_capability_default_values(self):
        """Test default values - source defaults streaming/tools to True."""
        cap = ProviderCapability(provider_id="test")
        assert cap.supports_streaming is True  # Default is True
        assert cap.supports_tools is True  # Default is True
        assert cap.supports_images is False  # Default is False

    def test_capability_to_dict(self):
        """Test capability serialization."""
        cap = ProviderCapability(
            provider_id="claude-code",
            supports_streaming=True,
        )
        d = cap.to_dict()
        assert d["providerId"] == "claude-code"
        assert d["supportsStreaming"] is True


class TestProviderCapabilityRegistry:
    """Tests for ProviderCapabilityRegistry static class."""

    def test_registry_has_predefined_providers(self):
        """Test registry has predefined providers."""
        # Registry is static and has predefined providers
        ids = ProviderCapabilityRegistry.get_registered_ids()
        assert len(ids) > 0  # Has predefined providers
        assert "claude-code" in ids

    def test_get_capability(self):
        """Test getting predefined capability."""
        cap = ProviderCapabilityRegistry.get("claude-code")
        assert cap is not None
        assert cap.provider_id == "claude-code"

    def test_get_nonexistent(self):
        """Test getting nonexistent capability."""
        cap = ProviderCapabilityRegistry.get("nonexistent-provider")
        assert cap is None

    def test_register_capability(self):
        """Test dynamically registering new capability."""
        # Save original state
        original_count = len(ProviderCapabilityRegistry.get_registered_ids())

        cap = ProviderCapability(
            provider_id="test-provider-new",
            supports_streaming=True,
        )
        ProviderCapabilityRegistry.register(cap)

        # Should be added
        assert "test-provider-new" in ProviderCapabilityRegistry.get_registered_ids()

        # Cleanup
        ProviderCapabilityRegistry.unregister("test-provider-new")
        assert len(ProviderCapabilityRegistry.get_registered_ids()) == original_count

    def test_unregister_capability(self):
        """Test unregistering capability."""
        # Register then unregister
        cap = ProviderCapability(provider_id="temp-provider")
        ProviderCapabilityRegistry.register(cap)
        assert ProviderCapabilityRegistry.has("temp-provider")

        result = ProviderCapabilityRegistry.unregister("temp-provider")
        assert result is True
        assert not ProviderCapabilityRegistry.has("temp-provider")

    def test_unregister_nonexistent(self):
        """Test unregistering nonexistent returns False."""
        result = ProviderCapabilityRegistry.unregister("nonexistent-provider")
        assert result is False

    def test_has_capability(self):
        """Test checking if capability exists."""
        assert ProviderCapabilityRegistry.has("claude-code") is True
        assert ProviderCapabilityRegistry.has("nonexistent") is False

    def test_supports_native_mcp(self):
        """Test checking native MCP support."""
        assert ProviderCapabilityRegistry.supports_native_mcp("claude-code") is True
        assert ProviderCapabilityRegistry.supports_native_mcp("codex") is False

    def test_supports_mcp_fallback(self):
        """Test checking MCP fallback support."""
        assert ProviderCapabilityRegistry.supports_mcp_fallback("codex") is True
        assert ProviderCapabilityRegistry.supports_mcp_fallback("claude-code") is False

    def test_get_summary(self):
        """Test getting registry summary."""
        summary = ProviderCapabilityRegistry.get_summary()
        assert "totalProviders" in summary
        assert summary["totalProviders"] > 0
        assert "nativeMcpProviders" in summary
        assert "fallbackMcpProviders" in summary

    def test_get_all(self):
        """Test getting all capabilities."""
        all_caps = ProviderCapabilityRegistry.get_all()
        assert len(all_caps) > 0
        assert all(isinstance(cap, ProviderCapability) for cap in all_caps)


class TestProviderCapabilityRegistryEdgeCases:
    """Edge case tests for ProviderCapabilityRegistry."""

    def test_summary_structure(self):
        """Test summary has correct structure."""
        summary = ProviderCapabilityRegistry.get_summary()
        assert "providers" in summary
        assert isinstance(summary["providers"], list)
        assert "nativeMcpProviders" in summary
        assert isinstance(summary["nativeMcpProviders"], list)


class TestProviderMcpCapability:
    """Tests for ProviderMcpCapability dataclass."""

    def test_mcp_creation_default(self):
        """Test creating MCP capability with defaults."""
        mcp = ProviderMcpCapability()
        assert mcp.native is False
        assert mcp.config_flag == ""
        assert mcp.config_format == "json"
        assert mcp.fallback == McpFallbackType.NONE

    def test_mcp_creation_with_native(self):
        """Test creating MCP capability with native support."""
        mcp = ProviderMcpCapability(
            native=True,
            config_flag="--mcp-config",
            config_format="json",
            config_env_var="MCP_CONFIG_PATH",
            fallback=McpFallbackType.NONE,
        )
        assert mcp.native is True
        assert mcp.config_flag == "--mcp-config"
        assert mcp.config_env_var == "MCP_CONFIG_PATH"

    def test_mcp_fallback_type(self):
        """Test MCP fallback types."""
        mcp = ProviderMcpCapability(
            native=False,
            fallback=McpFallbackType.PROMPT_INJECTION,
        )
        assert mcp.fallback == McpFallbackType.PROMPT_INJECTION


class TestProviderSkillCapability:
    """Tests for ProviderSkillCapability dataclass."""

    def test_skill_creation_default(self):
        """Test creating skill capability with defaults."""
        skill = ProviderSkillCapability()
        assert skill.slash_commands is False
        assert skill.system_prompt is False
        assert skill.native_skill_dir == ""

    def test_skill_creation_with_features(self):
        """Test creating skill capability with features."""
        skill = ProviderSkillCapability(
            slash_commands=True,
            system_prompt=True,
            native_skill_dir=".claude/commands",
        )
        assert skill.slash_commands is True
        assert skill.system_prompt is True
        assert skill.native_skill_dir == ".claude/commands"


class TestMcpFallbackType:
    """Tests for McpFallbackType enum."""

    def test_fallback_types(self):
        """Test fallback type values."""
        assert McpFallbackType.NONE.value == "none"
        assert McpFallbackType.PROMPT_INJECTION.value == "prompt-injection"


class TestPredefinedCapabilities:
    """Tests for predefined provider capabilities."""

    def test_claude_code_capability(self):
        """Test claude-code predefined capability."""
        cap = PROVIDER_CAPABILITIES.get("claude-code")
        assert cap is not None
        assert cap.mcp_support.native is True
        assert cap.skill_support.slash_commands is True
        assert cap.supports_images is True

    def test_codex_capability(self):
        """Test codex predefined capability."""
        cap = PROVIDER_CAPABILITIES.get("codex")
        assert cap is not None
        assert cap.mcp_support.native is False
        assert cap.mcp_support.fallback == McpFallbackType.PROMPT_INJECTION

    def test_gemini_capability(self):
        """Test gemini-cli predefined capability."""
        cap = PROVIDER_CAPABILITIES.get("gemini-cli")
        assert cap is not None
        assert cap.supports_long_context is True
        assert cap.max_context_tokens == 1000000
