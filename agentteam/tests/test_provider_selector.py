"""Tests for ProviderSelector module (P9)."""

import tempfile
from pathlib import Path

import pytest

from agentteam.orchestrator.provider_selector import (
    ProviderInfo,
    ProviderSelector,
    ProviderStatus,
    QuotaInfo,
    SelectionResult,
    TaskType,
    get_provider_selector,
)


class TestProviderStatus:
    """Tests for ProviderStatus enum."""

    def test_all_statuses(self):
        """Test all status values."""
        assert ProviderStatus.available.value == "available"
        assert ProviderStatus.degraded.value == "degraded"
        assert ProviderStatus.unavailable.value == "unavailable"
        assert ProviderStatus.quota_exceeded.value == "quota_exceeded"
        assert ProviderStatus.cooldown.value == "cooldown"

    def test_status_from_string(self):
        """Test creating status from string."""
        status = ProviderStatus("available")
        assert status == ProviderStatus.available


class TestTaskType:
    """Tests for TaskType enum."""

    def test_all_task_types(self):
        """Test all task type values."""
        assert TaskType.architecture.value == "architecture"
        assert TaskType.code_generation.value == "code_generation"
        assert TaskType.code_review.value == "code_review"
        assert TaskType.debugging.value == "debugging"
        assert TaskType.documentation.value == "documentation"
        assert TaskType.analysis.value == "analysis"
        assert TaskType.testing.value == "testing"
        assert TaskType.refactoring.value == "refactoring"
        assert TaskType.research.value == "research"
        assert TaskType.general.value == "general"

    def test_task_type_from_string(self):
        """Test creating task type from string."""
        tt = TaskType("code_generation")
        assert tt == TaskType.code_generation


class TestProviderInfo:
    """Tests for ProviderInfo dataclass."""

    def test_info_creation(self):
        """Test creating provider info."""
        info = ProviderInfo(
            name="claude-code",
            adapter_type="claude",
        )
        assert info.name == "claude-code"
        assert info.adapter_type == "claude"
        assert info.status == ProviderStatus.available

    def test_info_with_priority(self):
        """Test provider info with priority."""
        info = ProviderInfo(
            name="claude-code",
            adapter_type="claude",
            priority=100,
        )
        assert info.priority == 100

    def test_info_capabilities(self):
        """Test provider capabilities."""
        info = ProviderInfo(
            name="claude-code",
            adapter_type="claude",
            supports_streaming=True,
            supports_tools=True,
            supports_images=True,
        )
        assert info.supports_streaming is True
        assert info.supports_tools is True
        assert info.supports_images is True

    def test_info_task_scores(self):
        """Test task type scores."""
        info = ProviderInfo(
            name="claude-code",
            adapter_type="claude",
            task_scores={"code_generation": 90, "architecture": 80},
        )
        assert info.get_task_score(TaskType.code_generation) == 90
        assert info.get_task_score(TaskType.architecture) == 80

    def test_info_default_task_score(self):
        """Test default task score."""
        info = ProviderInfo(
            name="claude-code",
            adapter_type="claude",
        )
        # Default score is 50
        assert info.get_task_score(TaskType.code_generation) == 50

    def test_info_health_metrics(self):
        """Test health metrics."""
        info = ProviderInfo(
            name="claude-code",
            adapter_type="claude",
            success_rate=0.95,
            avg_latency_ms=500,
        )
        assert info.success_rate == 0.95
        assert info.avg_latency_ms == 500

    def test_info_quota_info(self):
        """Test quota information."""
        info = ProviderInfo(
            name="claude-code",
            adapter_type="claude",
            quota_remaining=100,
        )
        assert info.quota_remaining == 100


class TestQuotaInfo:
    """Tests for QuotaInfo model."""

    def test_quota_info_creation(self):
        """Test creating quota info."""
        quota = QuotaInfo(
            provider_name="claude-code",
            quota_limit=1000,
            quota_used=500,
            quota_remaining=500,
        )
        assert quota.provider_name == "claude-code"
        assert quota.quota_limit == 1000
        assert quota.quota_used == 500
        assert quota.quota_remaining == 500

    def test_quota_info_unlimited(self):
        """Test unlimited quota."""
        quota = QuotaInfo(
            provider_name="test",
            quota_limit=-1,
        )
        assert quota.quota_limit == -1


class TestSelectionResult:
    """Tests for SelectionResult model."""

    def test_result_success(self):
        """Test successful selection result."""
        result = SelectionResult(
            success=True,
            provider_name="claude",
            adapter_type="claude",
            reason="Selected based on task score",
            confidence=0.9,
        )
        assert result.success is True
        assert result.provider_name == "claude"

    def test_result_failure(self):
        """Test failed selection result."""
        result = SelectionResult(
            success=False,
            reason="No providers available",
        )
        assert result.success is False
        assert result.provider_name is None


class TestProviderSelector:
    """Tests for ProviderSelector class."""

    def test_selector_initialization_with_defaults(self):
        """Test selector initialization uses default providers."""
        selector = ProviderSelector("test-team")
        # Default providers are loaded automatically
        assert len(selector.providers) > 0

    def test_selector_initialization_empty(self):
        """Test selector initialization with empty providers."""
        selector = ProviderSelector("test-team", providers={})
        assert len(selector.providers) == 0

    def test_add_provider(self):
        """Test adding a provider."""
        selector = ProviderSelector("test-team", providers={})
        selector.add_provider(ProviderInfo(
            name="claude-code",
            adapter_type="claude",
        ))
        assert len(selector.providers) == 1
        assert "claude-code" in selector.providers

    def test_remove_provider(self):
        """Test removing a provider."""
        selector = ProviderSelector("test-team", providers={})
        selector.add_provider(ProviderInfo(name="claude-code", adapter_type="claude"))
        selector.remove_provider("claude-code")
        assert len(selector.providers) == 0

    def test_select_provider(self):
        """Test selecting a provider."""
        selector = ProviderSelector("test-team", providers={})
        selector.add_provider(ProviderInfo(
            name="claude-code",
            adapter_type="claude",
            priority=100,
        ))
        result = selector.select(TaskType.general)
        assert result.success is True
        assert result.provider_name == "claude-code"

    def test_select_no_providers(self):
        """Test selecting with no providers."""
        selector = ProviderSelector("test-team", providers={})
        result = selector.select(TaskType.general)
        assert result.success is False
        assert "No available provider" in result.reason

    def test_select_by_priority(self):
        """Test selecting by priority."""
        selector = ProviderSelector("test-team", providers={})
        selector.add_provider(ProviderInfo(
            name="low-priority",
            adapter_type="test",
            priority=10,
        ))
        selector.add_provider(ProviderInfo(
            name="high-priority",
            adapter_type="test",
            priority=100,
        ))
        result = selector.select(TaskType.general)
        assert result.success is True
        assert result.provider_name == "high-priority"

    def test_update_provider_status(self):
        """Test updating provider status."""
        selector = ProviderSelector("test-team", providers={})
        selector.add_provider(ProviderInfo(
            name="claude-code",
            adapter_type="claude",
        ))
        selector.update_provider_status("claude-code", ProviderStatus.unavailable)
        assert selector.providers["claude-code"].status == ProviderStatus.unavailable

    def test_record_success(self):
        """Test recording success."""
        selector = ProviderSelector("test-team", providers={})
        selector.add_provider(ProviderInfo(
            name="claude-code",
            adapter_type="claude",
            consecutive_failures=2,
        ))
        selector.record_success("claude-code")
        assert selector.providers["claude-code"].consecutive_failures == 0

    def test_record_failure(self):
        """Test recording failure."""
        selector = ProviderSelector("test-team", providers={})
        selector.add_provider(ProviderInfo(
            name="claude-code",
            adapter_type="claude",
        ))
        selector.record_failure("claude-code")
        assert selector.providers["claude-code"].consecutive_failures == 1

    def test_get_available_providers(self):
        """Test getting available providers."""
        selector = ProviderSelector("test-team", providers={})
        selector.add_provider(ProviderInfo(
            name="available",
            adapter_type="test",
            status=ProviderStatus.available,
        ))
        selector.add_provider(ProviderInfo(
            name="unavailable",
            adapter_type="test",
            status=ProviderStatus.unavailable,
        ))
        available = selector.get_available_providers()
        assert len(available) == 1
        assert available[0] == "available"

    def test_get_all_providers(self):
        """Test getting all providers."""
        selector = ProviderSelector("test-team", providers={})
        selector.add_provider(ProviderInfo(name="p1", adapter_type="test"))
        selector.add_provider(ProviderInfo(name="p2", adapter_type="test"))
        all_providers = selector.providers
        assert len(all_providers) == 2

    def test_set_quota_with_quota_info(self):
        """Test setting quota using QuotaInfo object."""
        selector = ProviderSelector("test-team", providers={})
        selector.add_provider(ProviderInfo(
            name="claude-code",
            adapter_type="claude",
        ))
        quota = QuotaInfo(
            provider_name="claude-code",
            quota_limit=1000,
            quota_used=500,
            quota_remaining=500,
        )
        selector.set_quota("claude-code", quota)
        retrieved = selector.get_quota("claude-code")
        assert retrieved is not None
        assert retrieved.quota_limit == 1000
        assert retrieved.quota_used == 500

    def test_get_quota(self):
        """Test getting quota."""
        selector = ProviderSelector("test-team", providers={})
        selector.add_provider(ProviderInfo(name="claude-code", adapter_type="claude"))
        quota = QuotaInfo(
            provider_name="claude-code",
            quota_limit=1000,
            quota_used=500,
            quota_remaining=500,
        )
        selector.set_quota("claude-code", quota)
        retrieved = selector.get_quota("claude-code")
        assert retrieved.quota_remaining == 500

    def test_get_summary(self):
        """Test getting selector summary."""
        selector = ProviderSelector("test-team", providers={})
        selector.add_provider(ProviderInfo(
            name="claude-code",
            adapter_type="claude",
        ))
        summary = selector.get_summary()
        assert summary["totalProviders"] == 1

    def test_fallback(self):
        """Test fallback mechanism."""
        selector = ProviderSelector("test-team", providers={})
        selector.add_provider(ProviderInfo(
            name="claude-code",
            adapter_type="claude",
            priority=100,
        ))
        selector.add_provider(ProviderInfo(
            name="codex",
            adapter_type="codex",
            priority=50,
        ))
        # Make first provider unavailable
        selector.update_provider_status("claude-code", ProviderStatus.quota_exceeded)
        
        # Should fallback to codex
        result = selector.select(TaskType.general)
        assert result.success is True


class TestProviderSelectorEdgeCases:
    """Edge case tests for ProviderSelector."""

    def test_all_providers_unavailable(self):
        """Test all providers unavailable."""
        selector = ProviderSelector("test-team", providers={})
        
        selector.add_provider(ProviderInfo(
            name="p1",
            adapter_type="test",
            status=ProviderStatus.unavailable,
        ))
        selector.add_provider(ProviderInfo(
            name="p2",
            adapter_type="test",
            status=ProviderStatus.unavailable,
        ))
        
        result = selector.select(TaskType.general)
        assert result.success is False

    def test_concurrent_selection(self):
        """Test concurrent selection."""
        selector = ProviderSelector("test-team", providers={})
        selector.add_provider(ProviderInfo(name="claude-code", adapter_type="claude"))
        
        # Multiple selections should work
        results = [selector.select(TaskType.general) for _ in range(5)]
        assert all(r.success for r in results)


class TestGetProviderSelector:
    """Tests for get_provider_selector factory."""

    def test_factory_returns_selector(self):
        """Test factory returns selector."""
        selector = get_provider_selector("test-team")
        assert selector is not None
        assert isinstance(selector, ProviderSelector)

    def test_factory_different_teams(self):
        """Test factory for different teams."""
        selector1 = get_provider_selector("team-1")
        selector2 = get_provider_selector("team-2")
        assert selector1.team_name != selector2.team_name


class TestFallbackChains:
    """Tests for fallback chain configurations."""

    def test_default_fallback_chain(self):
        """Test default fallback chain exists."""
        from agentteam.orchestrator.provider_selector import FallbackChain
        chain = FallbackChain.default_chain()
        assert chain.name == "default"
        assert len(chain.providers) > 0

    def test_code_generation_chain(self):
        """Test code generation fallback chain."""
        from agentteam.orchestrator.provider_selector import FallbackChain
        chain = FallbackChain.code_generation_chain()
        assert chain.task_type == "code_generation"
        assert "codex" in chain.providers