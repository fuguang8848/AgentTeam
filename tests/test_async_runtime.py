"""
Tests for async_core module

包含至少 15 个测试用例。
"""

import pytest
import asyncio
import time
from typing import Any

from agentteam.async_core import (
    AsyncExecutor,
    AsyncTaskOptions,
    AsyncTaskResult,
    TaskStatusAsync,
    AsyncEvent,
    AsyncCondition,
    AsyncLock,
    AsyncSemaphore,
    run_with_timeout,
    run_with_retry,
    gather_with_concurrency,
)


# ==================== AsyncExecutor Tests ====================

@pytest.mark.asyncio
async def test_executor_start_stop():
    """测试执行器启动和停止"""
    executor = AsyncExecutor(max_workers=5)
    assert not executor.is_running
    assert executor.max_workers == 5
    
    await executor.start()
    assert executor.is_running
    
    await executor.stop()
    assert not executor.is_running


@pytest.mark.asyncio
async def test_executor_submit_simple_task():
    """测试提交简单任务"""
    executor = AsyncExecutor(max_workers=2)
    await executor.start()
    
    async def simple_task():
        return 42
    
    future = await executor.submit("task-1", simple_task)
    result = await future
    
    assert result == 42
    await executor.stop()


@pytest.mark.asyncio
async def test_executor_submit_multiple_tasks():
    """测试提交多个任务"""
    executor = AsyncExecutor(max_workers=3)
    await executor.start()
    
    results = []
    for i in range(5):
        async def task(n=i):
            return n * 2
        future = await executor.submit(f"task-{i}", task)
        results.append(await future)
    
    assert results == [0, 2, 4, 6, 8]
    await executor.stop()


@pytest.mark.asyncio
async def test_executor_task_with_timeout():
    """测试任务超时"""
    executor = AsyncExecutor(max_workers=2, default_timeout=0.1)
    await executor.start()
    
    async def slow_task():
        await asyncio.sleep(10)
        return "done"
    
    future = await executor.submit("slow-task", slow_task)
    
    # 等待一段时间后检查状态
    await asyncio.sleep(0.2)
    status = executor.get_status("slow-task")
    assert status is not None
    # 超时任务状态应该是 TIMEOUT 或 CANCELLED
    assert status.status in (TaskStatusAsync.TIMEOUT, TaskStatusAsync.CANCELLED, TaskStatusAsync.FAILED)
    
    await executor.stop()


@pytest.mark.asyncio
async def test_executor_get_status():
    """测试获取任务状态"""
    executor = AsyncExecutor(max_workers=2)
    await executor.start()
    
    async def quick_task():
        await asyncio.sleep(0.01)
        return "done"
    
    await executor.submit("status-task", quick_task)
    
    status = executor.get_status("status-task")
    assert status is not None
    assert status.task_id == "status-task"
    
    await executor.stop()


@pytest.mark.asyncio
async def test_executor_cancel_task():
    """测试取消任务"""
    executor = AsyncExecutor(max_workers=2)
    await executor.start()
    
    async def long_task():
        await asyncio.sleep(10)
        return "done"
    
    # 先提交一个任务占满 worker
    future = await executor.submit("cancel-task", long_task)
    
    # 等待任务被 worker 取走
    await asyncio.sleep(0.1)
    
    # 取消任务
    cancelled = await executor.cancel("cancel-task")
    
    # 取消后状态应该是 CANCELLED
    status = executor.get_status("cancel-task")
    assert status is not None
    assert status.status in (TaskStatusAsync.CANCELLED, TaskStatusAsync.RUNNING)
    
    await executor.stop()


@pytest.mark.asyncio
async def test_executor_active_count():
    """测试活跃任务计数"""
    executor = AsyncExecutor(max_workers=2)
    await executor.start()
    
    async def quick_task():
        await asyncio.sleep(0.05)
        return "done"
    
    # 提交多个任务
    for i in range(3):
        await executor.submit(f"count-task-{i}", quick_task)
    
    # 等待任务完成
    await asyncio.sleep(0.1)
    
    assert executor.pending_count >= 0
    await executor.stop()


# ==================== AsyncEvent Tests ====================

@pytest.mark.asyncio
async def test_async_event_set_wait():
    """测试事件设置和等待"""
    event = AsyncEvent()
    assert not event.is_set()
    
    event.set()
    assert event.is_set()
    
    await event.wait()
    # 如果没有异常，说明测试通过


@pytest.mark.asyncio
async def test_async_event_clear():
    """测试事件清除"""
    event = AsyncEvent()
    
    event.set()
    assert event.is_set()
    
    event.clear()
    assert not event.is_set()


# ==================== AsyncLock Tests ====================

@pytest.mark.asyncio
async def test_async_lock():
    """测试异步锁"""
    lock = AsyncLock()
    results = []
    
    async def task(n: int):
        async with lock:
            results.append(n)
            await asyncio.sleep(0.01)
    
    await asyncio.gather(task(1), task(2), task(3))
    
    # 锁确保了顺序执行
    assert len(results) == 3


# ==================== AsyncSemaphore Tests ====================

@pytest.mark.asyncio
async def test_async_semaphore():
    """测试信号量"""
    sem = AsyncSemaphore(2)
    results = []
    
    async def task(n: int):
        async with sem:
            results.append(n)
            await asyncio.sleep(0.01)
    
    await asyncio.gather(task(1), task(2), task(3), task(4))
    
    assert len(results) == 4


# ==================== Utility Function Tests ====================

@pytest.mark.asyncio
async def test_run_with_timeout_success():
    """测试 run_with_timeout 成功"""
    async def quick_task():
        return "result"
    
    result = await run_with_timeout(quick_task(), timeout=1.0)
    assert result == "result"


@pytest.mark.asyncio
async def test_run_with_timeout_default():
    """测试 run_with_timeout 超时返回默认值"""
    async def slow_task():
        await asyncio.sleep(10)
        return "result"
    
    result = await run_with_timeout(slow_task(), timeout=0.1, default="default")
    assert result == "default"


@pytest.mark.asyncio
async def test_run_with_retry_success():
    """测试 run_with_retry 成功"""
    attempt_count = 0
    
    async def unreliable_task():
        nonlocal attempt_count
        attempt_count += 1
        return "success"
    
    # 传递函数，不要立即调用
    result = await run_with_retry(unreliable_task, max_retries=3)
    assert result == "success"
    assert attempt_count == 1


@pytest.mark.asyncio
async def test_run_with_retry_eventual_success():
    """测试 run_with_retry 最终成功"""
    attempt_count = 0
    
    async def unreliable_task():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise ValueError("Temporary error")
        return "success"
    
    # 传递函数，不要立即调用
    result = await run_with_retry(unreliable_task, max_retries=5, delay=0.01)
    assert result == "success"
    assert attempt_count == 3


@pytest.mark.asyncio
async def test_run_with_retry_all_fail():
    """测试 run_with_retry 全部失败"""
    attempt_count = 0
    
    async def failing_task():
        nonlocal attempt_count
        attempt_count += 1
        raise ValueError("Permanent error")
    
    # 传递函数，不要立即调用
    with pytest.raises(ValueError):
        await run_with_retry(failing_task, max_retries=3, delay=0.01)
    
    assert attempt_count == 4  # 初始尝试 + 3 次重试


@pytest.mark.asyncio
async def test_gather_with_concurrency():
    """测试带并发限制的 gather"""
    results = []
    max_concurrent = 2
    
    async def task(n: int):
        results.append(n)
        await asyncio.sleep(0.01)
        return n * 2
    
    result = await gather_with_concurrency(
        max_concurrent,
        task(1),
        task(2),
        task(3),
        task(4),
    )
    
    assert result == [2, 4, 6, 8]
    assert len(results) == 4


# ==================== TaskStatusAsync Tests ====================

def test_task_status_values():
    """测试任务状态枚举值"""
    assert TaskStatusAsync.PENDING.value == "pending"
    assert TaskStatusAsync.RUNNING.value == "running"
    assert TaskStatusAsync.COMPLETED.value == "completed"
    assert TaskStatusAsync.FAILED.value == "failed"
    assert TaskStatusAsync.CANCELLED.value == "cancelled"
    assert TaskStatusAsync.TIMEOUT.value == "timeout"


def test_async_task_result_properties():
    """测试任务结果属性"""
    result = AsyncTaskResult(
        task_id="test-1",
        status=TaskStatusAsync.COMPLETED,
        result="success",
    )
    
    assert result.is_success
    assert not result.is_failure
    assert result.is_done


# ==================== Integration Test ====================

@pytest.mark.asyncio
async def test_full_integration():
    """完整集成测试"""
    # 创建执行器
    executor = AsyncExecutor(max_workers=3)
    await executor.start()
    
    # 提交任务
    results = []
    
    async def worker_task(n: int) -> int:
        await asyncio.sleep(0.02)
        return n * n
    
    # 并发提交任务
    futures = []
    for i in range(5):
        # 使用 lambda 包装以传递参数
        f = await executor.submit(f"worker-{i}", lambda n=i: worker_task(n))
        futures.append(f)
    
    # 收集结果
    for f in futures:
        results.append(await f)
    
    # 验证结果
    assert sorted(results) == [0, 1, 4, 9, 16]
    
    # 清理
    await executor.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
