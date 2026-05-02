"""
Error recovery module for ClawTeam

Provides retry logic, fallback strategies, and error recovery.
"""

import asyncio
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

from clawteam.exceptions import ClawTeamError
from clawteam.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class RetryStrategy(str, Enum):
    """Retry strategy types"""

    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIXED = "fixed"
    FIBONACCI = "fibonacci"


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""

    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    multiplier: float = 2.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    jitter: bool = True

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt"""
        if self.strategy == RetryStrategy.FIXED:
            delay = self.initial_delay
        elif self.strategy == RetryStrategy.LINEAR:
            delay = self.initial_delay * attempt
        elif self.strategy == RetryStrategy.FIBONACCI:
            delay = self._fibonacci(attempt) * self.initial_delay
        else:  # EXPONENTIAL
            delay = self.initial_delay * (self.multiplier ** (attempt - 1))

        # Cap at max_delay
        delay = min(delay, self.max_delay)

        # Add jitter
        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)

        return delay

    def _fibonacci(self, n: int) -> float:
        """Fibonacci sequence for fibonacci backoff"""
        if n <= 1:
            return 1
        a, b = 1, 1
        for _ in range(n - 1):
            a, b = b, a + b
        return b


@dataclass
class FallbackResult:
    """Result of fallback action"""

    success: bool
    value: Any = None
    error: Optional[Exception] = None
    fallback_used: bool = False


class FallbackHandler(ABC):
    """Abstract base for fallback handlers"""

    @abstractmethod
    async def execute(self) -> FallbackResult:
        """Execute fallback action"""
        pass


class RetryableError(Exception):
    """Marker exception for errors that can be retried"""

    pass


class ErrorRecoveryManager:
    """
    Central error recovery manager

    Manages retry policies, fallback handlers, and recovery strategies.

    Example:
        manager = ErrorRecoveryManager()

        # Configure retry
        config = RetryConfig(
            max_attempts=3,
            strategy=RetryStrategy.EXPONENTIAL,
        )

        # Execute with retry
        result = await manager.execute_with_retry(
            func=some_operation,
            config=config,
            error_types=[RetryableError, TimeoutError],
        )
    """

    def __init__(self):
        self._fallback_handlers: dict[str, FallbackHandler] = {}
        self._retry_stats: dict[str, dict[str, int]] = {}

    def register_fallback(self, name: str, handler: FallbackHandler) -> None:
        """Register a fallback handler"""
        self._fallback_handlers[name] = handler
        logger.info(f"Registered fallback handler: {name}")

    def unregister_fallback(self, name: str) -> None:
        """Unregister a fallback handler"""
        if name in self._fallback_handlers:
            del self._fallback_handlers[name]
            logger.info(f"Unregistered fallback handler: {name}")

    async def execute_with_retry(
        self,
        func: Callable[..., Any],
        *args,
        config: Optional[RetryConfig] = None,
        error_types: tuple = (RetryableError, ClawTeamError),
        fallback_name: Optional[str] = None,
        **kwargs,
    ) -> FallbackResult:
        """
        Execute a function with retry logic

        Args:
            func: Function to execute
            *args: Positional arguments for func
            config: Retry configuration
            error_types: Exception types that trigger retry
            fallback_name: Name of fallback handler to use on final failure
            **kwargs: Keyword arguments for func

        Returns:
            FallbackResult with outcome
        """
        config = config or RetryConfig()
        last_error: Optional[Exception] = None

        for attempt in range(1, config.max_attempts + 1):
            try:
                # Handle both sync and async functions
                result = func(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    result = await result

                # Track success
                self._record_attempt(func.__name__, success=True)

                return FallbackResult(success=True, value=result)

            except error_types as e:
                last_error = e
                self._record_attempt(func.__name__, success=False)

                if attempt < config.max_attempts:
                    delay = config.get_delay(attempt)
                    logger.warning(
                        f"Retry attempt {attempt}/{config.max_attempts} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {config.max_attempts} attempts failed: {e}")

        # All retries failed - try fallback if configured
        if fallback_name and fallback_name in self._fallback_handlers:
            logger.info(f"Attempting fallback: {fallback_name}")
            try:
                fallback_result = await self._fallback_handlers[fallback_name].execute()
                fallback_result.error = last_error
                fallback_result.fallback_used = True
                return fallback_result
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                return FallbackResult(
                    success=False,
                    error=fallback_error,
                    fallback_used=True,
                )

        return FallbackResult(success=False, error=last_error)

    async def execute_with_fallback(
        self,
        primary: Callable,
        fallback: Callable,
        *args,
        **kwargs,
    ) -> FallbackResult:
        """
        Execute primary function, fall back to secondary on failure

        Args:
            primary: Primary function to execute
            fallback: Fallback function to execute on primary failure
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            FallbackResult with outcome
        """
        try:
            result = primary(*args, **kwargs)
            return FallbackResult(success=True, value=result)
        except Exception as e:
            logger.warning(f"Primary failed ({e}), attempting fallback...")
            try:
                fallback_result = fallback(*args, **kwargs)
                return FallbackResult(
                    success=True,
                    value=fallback_result,
                    fallback_used=True,
                )
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                return FallbackResult(
                    success=False,
                    error=fallback_error,
                    fallback_used=True,
                )

    def _record_attempt(self, func_name: str, success: bool) -> None:
        """Record attempt statistics"""
        if func_name not in self._retry_stats:
            self._retry_stats[func_name] = {"success": 0, "failure": 0}

        if success:
            self._retry_stats[func_name]["success"] += 1
        else:
            self._retry_stats[func_name]["failure"] += 1

    def get_stats(self) -> dict[str, dict[str, int]]:
        """Get retry statistics"""
        return dict(self._retry_stats)


def retry(
    config: Optional[RetryConfig] = None,
    error_types: tuple = (RetryableError, ClawTeamError),
):
    """
    Decorator to add retry logic to a function

    Example:
        @retry(config=RetryConfig(max_attempts=3))
        async def my_function():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            manager = ErrorRecoveryManager()
            result = await manager.execute_with_retry(
                func=func,
                *args,
                config=config,
                error_types=error_types,
                **kwargs,
            )
            if not result.success:
                if result.error:
                    raise result.error
            return result.value

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            manager = ErrorRecoveryManager()
            result = asyncio.run(
                manager.execute_with_retry(
                    func=func,
                    *args,
                    config=config,
                    error_types=error_types,
                    **kwargs,
                )
            )
            if not result.success:
                if result.error:
                    raise result.error
            return result.value

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return wrapper
        else:
            return sync_wrapper

    return decorator


# Global error recovery manager
_recovery_manager: Optional[ErrorRecoveryManager] = None


def get_recovery_manager() -> ErrorRecoveryManager:
    """Get the global error recovery manager"""
    global _recovery_manager
    if _recovery_manager is None:
        _recovery_manager = ErrorRecoveryManager()
    return _recovery_manager


__all__ = [
    "RetryConfig",
    "RetryStrategy",
    "RetryableError",
    "FallbackResult",
    "FallbackHandler",
    "ErrorRecoveryManager",
    "retry",
    "get_recovery_manager",
]
