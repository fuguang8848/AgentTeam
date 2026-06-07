"""
Async Core Module for AgentTeam SDK

提供完整的异步运行时支持。
"""

from __future__ import annotations

# Types
from .types import (
    AsyncAgentState,
    TaskStatusAsync,
    AsyncTaskResult,
    AsyncTaskOptions,
    AsyncEvent,
    AsyncCondition,
    AsyncLock,
    AsyncSemaphore,
    TaskResult,
    TaskOptions,
)

# Executor
from .executor import (
    AsyncExecutor,
    TaskContext,
    get_executor,
    shutdown_executor,
)

# Utility functions
import asyncio
from typing import Awaitable, TypeVar, Optional

T = TypeVar("T")


async def run_async(awaitable: Awaitable[T]) -> T:
    """运行异步任务"""
    return await awaitable


async def run_with_timeout(
    awaitable: Awaitable[T],
    timeout: float,
    default: Optional[T] = None,
) -> T:
    """带超时的异步运行"""
    try:
        return await asyncio.wait_for(awaitable, timeout=timeout)
    except asyncio.TimeoutError:
        return default


async def run_with_retry(
    awaitable: Awaitable[T],
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
) -> T:
    """带重试的异步运行"""
    last_error = None
    current_delay = delay
    is_coro_func = asyncio.iscoroutinefunction(awaitable)

    for attempt in range(max_retries + 1):
        try:
            if is_coro_func:
                result = await awaitable()
            else:
                result = await awaitable
            return result
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                await asyncio.sleep(current_delay)
                current_delay *= backoff

    raise last_error


async def gather_with_concurrency(
    n: int,
    *awaitables: Awaitable,
) -> list:
    """带并发限制的 gather"""
    semaphore = asyncio.Semaphore(n)

    async def bounded_await(awaitable):
        async with semaphore:
            return await awaitable

    return await asyncio.gather(*[bounded_await(a) for a in awaitables])


# Re-export asyncio utilities
sleep = asyncio.sleep
create_task = asyncio.create_task
wait = asyncio.wait
wait_for = asyncio.wait_for
gather = asyncio.gather
shield = asyncio.shield
TimeoutError = asyncio.TimeoutError


__all__ = [
    # Types
    "AsyncAgentState",
    "TaskStatusAsync",
    "AsyncTaskResult",
    "AsyncTaskOptions",
    "AsyncEvent",
    "AsyncCondition",
    "AsyncLock",
    "AsyncSemaphore",
    "TaskResult",
    "TaskOptions",
    # Executor
    "AsyncExecutor",
    "TaskContext",
    "get_executor",
    "shutdown_executor",
    # Utilities
    "run_async",
    "run_with_timeout",
    "run_with_retry",
    "gather_with_concurrency",
    # Re-exports
    "sleep",
    "create_task",
    "wait",
    "wait_for",
    "gather",
    "shield",
    "TimeoutError",
]
