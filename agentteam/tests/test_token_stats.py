"""Tests for TokenStats module (P11)."""

import tempfile
from pathlib import Path

import pytest

from agentteam.tracker.token_stats import (
    DailyUsage,
    ProviderUsageStats,
    SessionUsage,
    TrendAnalysis,
    UsageEstimator,
    UsageSummary,
    accumulate_usage,
    estimate_tokens,
    get_provider_stats,
    get_usage_estimator,
    get_usage_summary,
    get_usage_trend,
    mark_session_ended,
    record_request,
)


class TestUsageSummary:
    """Tests for UsageSummary dataclass."""

    def test_summary_creation(self):
        """Test creating usage summary."""
        summary = UsageSummary()
        assert summary.total_tokens == 0
        assert summary.total_minutes == 0

    def test_summary_with_values(self):
        """Test summary with values."""
        summary = UsageSummary(
            total_tokens=10000,
            total_minutes=60,
            today_tokens=500,
            today_minutes=10,
        )
        assert summary.total_tokens == 10000
        assert summary.today_tokens == 500

    def test_summary_session_breakdown(self):
        """Test summary session breakdown."""
        summary = UsageSummary(
            session_breakdown={"session-1": 5000, "session-2": 3000},
        )
        assert len(summary.session_breakdown) == 2

    def test_summary_provider_breakdown(self):
        """Test summary provider breakdown."""
        summary = UsageSummary(
            provider_breakdown={"claude": 8000, "codex": 2000},
        )
        assert len(summary.provider_breakdown) == 2

    def test_summary_active_sessions(self):
        """Test summary active sessions."""
        summary = UsageSummary(active_sessions=5)
        assert summary.active_sessions == 5

    def test_summary_to_dict(self):
        """Test summary serialization."""
        summary = UsageSummary(total_tokens=1000)
        d = summary.to_dict()
        assert d["totalTokens"] == 1000


class TestDailyUsage:
    """Tests for DailyUsage dataclass."""

    def test_daily_creation(self):
        """Test creating daily usage."""
        daily = DailyUsage(date="2024-01-01")
        assert daily.date == "2024-01-01"
        assert daily.tokens == 0

    def test_daily_with_values(self):
        """Test daily with values."""
        daily = DailyUsage(
            date="2024-01-01",
            tokens=5000,
            minutes=30,
            sessions=10,
        )
        assert daily.tokens == 5000
        assert daily.sessions == 10

    def test_daily_providers(self):
        """Test daily providers."""
        daily = DailyUsage(
            date="2024-01-01",
            providers={"claude": 3000, "codex": 2000},
        )
        assert len(daily.providers) == 2

    def test_daily_to_dict(self):
        """Test daily serialization."""
        daily = DailyUsage(date="2024-01-01", tokens=1000)
        d = daily.to_dict()
        assert d["date"] == "2024-01-01"
        assert d["tokens"] == 1000


class TestSessionUsage:
    """Tests for SessionUsage dataclass."""

    def test_session_creation(self):
        """Test creating session usage."""
        session = SessionUsage(session_id="session-123")
        assert session.session_id == "session-123"
        assert session.tokens == 0

    def test_session_with_values(self):
        """Test session with values."""
        session = SessionUsage(
            session_id="session-123",
            tokens=5000,
            minutes=30,
            provider="claude",
        )
        assert session.tokens == 5000
        assert session.provider == "claude"

    def test_session_task_type(self):
        """Test session task type."""
        session = SessionUsage(
            session_id="session-123",
            task_type="code_generation",
        )
        assert session.task_type == "code_generation"

    def test_session_timestamps(self):
        """Test session timestamps."""
        session = SessionUsage(
            session_id="session-123",
            start_time=1000.0,
            last_update=2000.0,
        )
        assert session.start_time == 1000.0
        assert session.last_update == 2000.0

    def test_session_to_dict(self):
        """Test session serialization."""
        session = SessionUsage(session_id="session-123", tokens=1000)
        d = session.to_dict()
        assert d["sessionId"] == "session-123"
        assert d["tokens"] == 1000


class TestTrendAnalysis:
    """Tests for TrendAnalysis dataclass."""

    def test_trend_creation(self):
        """Test creating trend analysis."""
        trend = TrendAnalysis()
        assert len(trend.daily_data) == 0
        assert trend.avg_daily_tokens == 0

    def test_trend_with_values(self):
        """Test trend with values."""
        trend = TrendAnalysis(
            avg_daily_tokens=5000,
            avg_daily_minutes=30,
            peak_day="2024-01-15",
            peak_tokens=10000,
        )
        assert trend.avg_daily_tokens == 5000
        assert trend.peak_day == "2024-01-15"

    def test_trend_growth_rate(self):
        """Test trend growth rate."""
        trend = TrendAnalysis(growth_rate=0.15)
        assert trend.growth_rate == 0.15

    def test_trend_prediction(self):
        """Test trend prediction."""
        trend = TrendAnalysis(prediction_next_day=5500)
        assert trend.prediction_next_day == 5500

    def test_trend_with_daily_data(self):
        """Test trend with daily data."""
        daily = [DailyUsage(date="2024-01-01", tokens=1000)]
        trend = TrendAnalysis(daily_data=daily)
        assert len(trend.daily_data) == 1

    def test_trend_to_dict(self):
        """Test trend serialization."""
        trend = TrendAnalysis(avg_daily_tokens=1000)
        d = trend.to_dict()
        assert d["avgDailyTokens"] == 1000


class TestProviderUsageStats:
    """Tests for ProviderUsageStats dataclass."""

    def test_stats_creation(self):
        """Test creating provider stats."""
        stats = ProviderUsageStats(provider="claude")
        assert stats.provider == "claude"
        assert stats.total_tokens == 0

    def test_stats_with_values(self):
        """Test stats with values."""
        stats = ProviderUsageStats(
            provider="claude",
            total_tokens=50000,
            total_sessions=100,
        )
        assert stats.total_tokens == 50000
        assert stats.total_sessions == 100

    def test_stats_avg_tokens(self):
        """Test stats average tokens."""
        stats = ProviderUsageStats(
            provider="claude",
            total_tokens=5000,
            total_sessions=10,
            avg_tokens_per_session=500,
        )
        assert stats.avg_tokens_per_session == 500

    def test_stats_percentage(self):
        """Test stats percentage."""
        stats = ProviderUsageStats(
            provider="claude",
            percentage=80.0,
        )
        assert stats.percentage == 80.0

    def test_stats_to_dict(self):
        """Test stats serialization."""
        stats = ProviderUsageStats(provider="claude", total_tokens=1000)
        d = stats.to_dict()
        assert d["provider"] == "claude"
        assert d["totalTokens"] == 1000


class TestUsageEstimator:
    """Tests for UsageEstimator class."""

    def test_estimator_initialization(self):
        """Test estimator initialization."""
        estimator = UsageEstimator()
        assert len(estimator._session_usage) == 0
        assert len(estimator._daily_history) == 0

    def test_estimate_tokens(self):
        """Test token estimation."""
        estimator = UsageEstimator()
        # 4 characters ≈ 1 token
        tokens = estimator.estimate_tokens("Hello World")
        assert tokens > 0
        assert tokens == 3  # 11 chars / 4 = 2.75 -> ceil = 3

    def test_estimate_tokens_empty(self):
        """Test empty string estimation."""
        estimator = UsageEstimator()
        tokens = estimator.estimate_tokens("")
        assert tokens == 0

    def test_estimate_tokens_long(self):
        """Test long string estimation."""
        estimator = UsageEstimator()
        long_text = "x" * 1000
        tokens = estimator.estimate_tokens(long_text)
        assert tokens == 250  # 1000 / 4 = 250

    def test_accumulate_usage(self):
        """Test accumulating usage."""
        estimator = UsageEstimator()
        tokens = estimator.accumulate_usage(
            session_id="session-123",
            text="Hello World",
            provider="claude",
        )
        assert tokens > 0
        assert "session-123" in estimator._session_usage

    def test_record_request(self):
        """Test recording request."""
        estimator = UsageEstimator()
        total = estimator.record_request(
            session_id="session-123",
            input_tokens=100,
            output_tokens=50,
            provider="claude",
        )
        assert total == 150

    def test_mark_session_ended(self):
        """Test marking session ended."""
        estimator = UsageEstimator()
        estimator.accumulate_usage("session-123", "test", "claude")
        estimator.mark_session_ended("session-123")
        # Session should be marked as ended

    def test_get_summary(self):
        """Test getting summary."""
        estimator = UsageEstimator()
        estimator.accumulate_usage("session-123", "Hello World", "claude")
        summary = estimator.get_summary()
        assert summary.total_tokens > 0

    def test_get_trend(self):
        """Test getting trend."""
        estimator = UsageEstimator()
        trend = estimator.get_trend(days=30)
        assert isinstance(trend, TrendAnalysis)

    def test_get_provider_stats(self):
        """Test getting provider stats."""
        estimator = UsageEstimator()
        estimator.accumulate_usage("session-1", "test", "claude")
        estimator.accumulate_usage("session-2", "test", "codex")
        stats = estimator.get_provider_stats()
        assert isinstance(stats, list)

    def test_reset_all(self):
        """Test resetting all."""
        estimator = UsageEstimator()
        estimator.accumulate_usage("session-123", "test", "claude")
        estimator.reset_all()
        assert len(estimator._session_usage) == 0


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_get_usage_estimator(self):
        """Test getting estimator."""
        estimator = get_usage_estimator()
        assert estimator is not None
        assert isinstance(estimator, UsageEstimator)

    def test_get_usage_summary(self):
        """Test getting summary."""
        summary = get_usage_summary()
        assert isinstance(summary, UsageSummary)

    def test_get_usage_trend(self):
        """Test getting trend."""
        trend = get_usage_trend(days=30)
        assert isinstance(trend, TrendAnalysis)

    def test_get_provider_stats(self):
        """Test getting provider stats."""
        stats = get_provider_stats()
        assert isinstance(stats, list)

    def test_estimate_tokens(self):
        """Test estimate tokens function."""
        tokens = estimate_tokens("Hello World")
        assert tokens == 3  # 11 chars / 4 = 2.75 -> ceil = 3

    def test_accumulate_usage(self):
        """Test accumulate usage function."""
        tokens = accumulate_usage("session-123", "test", "claude")
        assert tokens > 0

    def test_record_request(self):
        """Test record request function."""
        total = record_request("session-123", 100, 50, "claude")
        assert total == 150

    def test_mark_session_ended(self):
        """Test mark session ended function."""
        mark_session_ended("session-123")
        # Should not raise


class TestUsageEstimatorPersistence:
    """Tests for UsageEstimator persistence."""

    def test_save_and_load(self):
        """Test saving and loading."""
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            # 通过环境变量设置数据目录
            original_env = os.environ.get("AGENTTEAM_DATA_DIR")
            os.environ["AGENTTEAM_DATA_DIR"] = tmpdir

            try:
                estimator = UsageEstimator()
                estimator.accumulate_usage("session-123", "test", "claude")
                estimator.mark_session_ended("session-123")  # 结束会话以flush到历史
                estimator._save_to_file()

                # Create new estimator and load
                estimator2 = UsageEstimator()
                estimator2._load_from_file()

                # Should have saved daily history data
                from datetime import datetime, timezone

                today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                assert today in estimator2._daily_history
                assert estimator2._daily_history[today].tokens > 0
            finally:
                if original_env:
                    os.environ["AGENTTEAM_DATA_DIR"] = original_env
                else:
                    os.environ.pop("AGENTTEAM_DATA_DIR", None)


class TestUsageEstimatorEdgeCases:
    """Edge case tests for UsageEstimator."""

    def test_accumulate_empty_text(self):
        """Test accumulating empty text."""
        estimator = UsageEstimator()
        tokens = estimator.accumulate_usage("session-123", "", "claude")
        assert tokens == 0

    def test_accumulate_unicode(self):
        """Test accumulating unicode text."""
        estimator = UsageEstimator()
        tokens = estimator.accumulate_usage("session-123", "你好世界", "claude")
        assert tokens > 0

    def test_accumulate_no_provider(self):
        """Test accumulating without provider."""
        estimator = UsageEstimator()
        tokens = estimator.accumulate_usage("session-123", "test")
        assert tokens > 0

    def test_record_request_no_provider(self):
        """Test recording request without provider."""
        estimator = UsageEstimator()
        total = estimator.record_request("session-123", 100, 50)
        assert total == 150

    def test_get_trend_empty_history(self):
        """Test getting trend with empty history."""
        estimator = UsageEstimator()
        estimator._daily_history.clear()
        trend = estimator.get_trend(days=30)
        assert trend.avg_daily_tokens == 0

    def test_get_provider_stats_empty(self):
        """Test getting provider stats empty."""
        estimator = UsageEstimator()
        estimator.reset_all()
        stats = estimator.get_provider_stats()
        assert len(stats) == 0

    def test_multiple_sessions_same_provider(self):
        """Test multiple sessions same provider."""
        estimator = UsageEstimator()
        estimator.accumulate_usage("session-1", "test", "claude")
        estimator.accumulate_usage("session-2", "test", "claude")

        stats = estimator.get_provider_stats()
        # Should have one provider entry
        claude_stats = [s for s in stats if s.provider == "claude"]
        assert len(claude_stats) == 1

    def test_session_already_ended(self):
        """Test marking already ended session."""
        estimator = UsageEstimator()
        estimator.accumulate_usage("session-123", "test", "claude")
        estimator.mark_session_ended("session-123")
        # Second call should not raise
        estimator.mark_session_ended("session-123")

    def test_nonexistent_session_operations(self):
        """Test operations on nonexistent session."""
        estimator = UsageEstimator()
        # Should not raise
        estimator.mark_session_ended("nonexistent-session")


class TestUsageEstimatorIntegration:
    """Integration tests for UsageEstimator."""

    def test_full_usage_workflow(self):
        """Test full usage workflow."""
        estimator = UsageEstimator()

        # Accumulate usage
        estimator.accumulate_usage("session-1", "Hello World", "claude")
        estimator.accumulate_usage("session-2", "Another message", "codex")

        # Record requests
        estimator.record_request("session-1", 100, 50, "claude")
        estimator.record_request("session-2", 200, 100, "codex")

        # Get summary
        summary = estimator.get_summary()
        assert summary.total_tokens > 0
        assert summary.active_sessions >= 2

        # Get provider stats
        stats = estimator.get_provider_stats()
        assert len(stats) >= 2

        # End sessions
        estimator.mark_session_ended("session-1")
        estimator.mark_session_ended("session-2")

        # Get final summary
        final_summary = estimator.get_summary()
        assert final_summary.active_sessions == 0

    def test_daily_aggregation(self):
        """Test daily aggregation."""
        estimator = UsageEstimator()

        # Accumulate usage
        estimator.accumulate_usage("session-1", "test", "claude")

        # Get trend (should aggregate daily)
        trend = estimator.get_trend(days=7)
        assert isinstance(trend, TrendAnalysis)


class TestSingletonBehavior:
    """Tests for singleton behavior."""

    def test_estimator_singleton(self):
        """Test estimator is singleton."""
        estimator1 = get_usage_estimator()
        estimator2 = get_usage_estimator()
        assert estimator1 is estimator2

    def test_estimator_state_shared(self):
        """Test estimator state is shared."""
        estimator1 = get_usage_estimator()
        estimator2 = get_usage_estimator()

        estimator1.accumulate_usage("session-test", "test", "claude")

        # estimator2 should see the same state
        summary2 = estimator2.get_summary()
        assert summary2.total_tokens > 0
