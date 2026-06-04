"""Tests for retry utilities."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import patch

import pytest

from agentteam.utils.retry import (
    RetryConfig,
    _calculate_delay,
    retry,
    retry_async,
)


class TestRetryConfig:
    """Tests for RetryConfig dataclass."""

    def test_default_config(self) -> None:
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 0.5
        assert config.max_delay == 30.0
        assert config.jitter is True
        assert config.success_count == 0
        assert config.fail_count == 0

    def test_custom_config(self) -> None:
        config = RetryConfig(max_retries=5, base_delay=1.0, max_delay=60.0, jitter=False)
        assert config.max_retries == 5
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.jitter is False

    def test_record_success(self) -> None:
        config = RetryConfig()
        config.record_success()
        assert config.success_count == 1
        config.record_success()
        assert config.success_count == 2

    def test_record_failure(self) -> None:
        config = RetryConfig()
        config.record_failure()
        assert config.fail_count == 1
        config.record_failure()
        assert config.fail_count == 2

    def test_get_stats(self) -> None:
        config = RetryConfig()
        config.record_success()
        config.record_success()
        config.record_failure()
        stats = config.get_stats()
        assert stats == {
            "success_count": 2,
            "fail_count": 1,
            "total_attempts": 3,
        }


class TestCalculateDelay:
    """Tests for delay calculation."""

    def test_exponential_backoff(self) -> None:
        config = RetryConfig(base_delay=1.0, max_delay=100.0, jitter=False)
        assert _calculate_delay(config, 0) == 1.0
        assert _calculate_delay(config, 1) == 2.0
        assert _calculate_delay(config, 2) == 4.0
        assert _calculate_delay(config, 3) == 8.0

    def test_max_delay_cap(self) -> None:
        config = RetryConfig(base_delay=1.0, max_delay=5.0, jitter=False)
        assert _calculate_delay(config, 10) == 5.0

    def test_jitter_enabled(self) -> None:
        config = RetryConfig(base_delay=1.0, max_delay=100.0, jitter=True)
        # With jitter, delay should be between 0 and calculated value
        for _ in range(100):
            delay = _calculate_delay(config, 0)
            assert 0 <= delay <= 1.0

    def test_jitter_disabled(self) -> None:
        config = RetryConfig(base_delay=1.0, max_delay=100.0, jitter=False)
        delay = _calculate_delay(config, 0)
        assert delay == 1.0


class TestRetryDecorator:
    """Tests for @retry decorator."""

    def test_success_no_retry(self) -> None:
        call_count = 0

        @retry
        def success_func() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = success_func()
        assert result == "success"
        assert call_count == 1

    def test_retry_on_failure(self) -> None:
        call_count = 0

        @retry(config=RetryConfig(max_retries=3, base_delay=0.01, jitter=False))
        def flaky_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise OSError("Transient error")
            return "success"

        result = flaky_func()
        assert result == "success"
        assert call_count == 3

    def test_exhaust_retries(self) -> None:
        call_count = 0

        @retry(config=RetryConfig(max_retries=2, base_delay=0.01, jitter=False))
        def always_fail() -> str:
            nonlocal call_count
            call_count += 1
            raise OSError("Permanent error")

        with pytest.raises(OSError, match="Permanent error"):
            always_fail()
        assert call_count == 3  # 1 initial + 2 retries

    def test_non_retryable_exception(self) -> None:
        call_count = 0

        @retry(config=RetryConfig(max_retries=3, base_delay=0.01))
        def value_error_func() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("Non-retryable error")

        with pytest.raises(ValueError, match="Non-retryable error"):
            value_error_func()
        assert call_count == 1  # No retry for non-retryable exceptions

    def test_retry_config_attached(self) -> None:
        @retry
        def some_func() -> None:
            pass

        assert hasattr(some_func, "retry_config")
        assert isinstance(some_func.retry_config, RetryConfig)

    def test_on_retry_callback(self) -> None:
        call_count = 0
        retry_callbacks = []

        def on_retry(exc: Exception, attempt: int, delay: float) -> None:
            retry_callbacks.append((exc, attempt, delay))

        @retry(
            config=RetryConfig(max_retries=2, base_delay=0.01, jitter=False),
            on_retry=on_retry,
        )
        def flaky_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise OSError("Transient error")
            return "success"

        result = flaky_func()
        assert result == "success"
        assert len(retry_callbacks) == 2
        assert retry_callbacks[0][0].args[0] == "Transient error"
        assert retry_callbacks[0][1] == 0  # attempt 0
        assert retry_callbacks[1][1] == 1  # attempt 1


class TestRetryAsyncDecorator:
    """Tests for @retry_async decorator."""

    @pytest.mark.asyncio
    async def test_success_no_retry(self) -> None:
        call_count = 0

        @retry_async
        async def success_func() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = await success_func()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_failure(self) -> None:
        call_count = 0

        @retry_async(config=RetryConfig(max_retries=3, base_delay=0.01, jitter=False))
        async def flaky_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise OSError("Transient error")
            return "success"

        result = await flaky_func()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_exhaust_retries(self) -> None:
        call_count = 0

        @retry_async(config=RetryConfig(max_retries=2, base_delay=0.01, jitter=False))
        async def always_fail() -> str:
            nonlocal call_count
            call_count += 1
            raise OSError("Permanent error")

        with pytest.raises(OSError, match="Permanent error"):
            await always_fail()
        assert call_count == 3  # 1 initial + 2 retries

    @pytest.mark.asyncio
    async def test_non_retryable_exception(self) -> None:
        call_count = 0

        @retry_async(config=RetryConfig(max_retries=3, base_delay=0.01))
        async def value_error_func() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("Non-retryable error")

        with pytest.raises(ValueError, match="Non-retryable error"):
            await value_error_func()
        assert call_count == 1  # No retry for non-retryable exceptions

    @pytest.mark.asyncio
    async def test_retry_config_attached(self) -> None:
        @retry_async
        async def some_func() -> None:
            pass

        assert hasattr(some_func, "retry_config")
        assert isinstance(some_func.retry_config, RetryConfig)
