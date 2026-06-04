"""
Async Executor for AgentTeam SDK

提供异步任务执行器，支持任务队列、超时、重试等。
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional, Any, Callable, Dict, List
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from .types import (
    AsyncTaskResult,
    AsyncTaskOptions,
    TaskStatusAsync,
)

logger = logging.getLogger(__name__)


@dataclass
class TaskContext:
    """任务上下文"""
    
    task_id: str
    awaitable: Callable[[], Any]
    options: AsyncTaskOptions
    status: TaskStatusAsync = TaskStatusAsync.PENDING
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    _future: Optional[asyncio.Future] = None


class AsyncExecutor:
    """
    异步任务执行器
    
    提供：
    - 任务队列管理
    - 超时控制
    - 重试机制
    - 并发限制
    """
    
    def __init__(
        self,
        max_workers: int = 10,
        default_timeout: Optional[float] = None,
    ):
        self._max_workers = max_workers
        self._default_timeout = default_timeout
        self._semaphore = asyncio.Semaphore(max_workers)
        self._tasks: Dict[str, TaskContext] = {}
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def max_workers(self) -> int:
        return self._max_workers
    
    @property
    def active_count(self) -> int:
        return len([t for t in self._tasks.values() if t.status == TaskStatusAsync.RUNNING])
    
    @property
    def pending_count(self) -> int:
        return self._queue.qsize()
    
    async def start(self) -> None:
        """启动执行器"""
        if self._running:
            return
        
        self._running = True
        self._worker_task = asyncio.create_task(self._run_worker())
        logger.info(f"AsyncExecutor started with {self._max_workers} workers")
    
    async def stop(self, wait: bool = True, timeout: Optional[float] = 30.0) -> None:
        """停止执行器"""
        if not self._running:
            return
        
        self._running = False
        
        if not wait:
            for task in self._tasks.values():
                if task._future and not task._future.done():
                    task._future.cancel()
        
        if self._worker_task:
            try:
                await asyncio.wait_for(self._worker_task, timeout=timeout)
            except asyncio.TimeoutError:
                self._worker_task.cancel()
        
        self._tasks.clear()
        logger.info("AsyncExecutor stopped")
    
    async def submit(
        self,
        task_id: str,
        awaitable: Callable[[], Any],
        options: Optional[AsyncTaskOptions] = None,
    ) -> asyncio.Future:
        """提交任务"""
        if not self._running:
            raise RuntimeError("Executor is not running")
        
        options = options or AsyncTaskOptions()
        if self._default_timeout and options.timeout is None:
            options.timeout = self._default_timeout
        
        context = TaskContext(
            task_id=task_id,
            awaitable=awaitable,
            options=options,
            status=TaskStatusAsync.QUEUED,
        )
        
        self._tasks[task_id] = context
        await self._queue.put((options.priority, task_id))
        
        return context._future or asyncio.create_task(self._execute_task(context))
    
    async def get_result(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """获取任务结果"""
        context = self._tasks.get(task_id)
        if not context:
            raise ValueError(f"Task {task_id} not found")
        
        if context._future is None:
            raise RuntimeError(f"Task {task_id} not started")
        
        return await asyncio.wait_for(context._future, timeout=timeout)
    
    async def cancel(self, task_id: str) -> bool:
        """取消任务"""
        context = self._tasks.get(task_id)
        if not context:
            return False
        
        if context._future and not context._future.done():
            context._future.cancel()
            context.status = TaskStatusAsync.CANCELLED
            return True
        
        return False
    
    def get_status(self, task_id: str) -> Optional[AsyncTaskResult]:
        """获取任务状态"""
        context = self._tasks.get(task_id)
        if not context:
            return None
        
        return AsyncTaskResult(
            task_id=task_id,
            status=context.status,
            result=context.result,
            error=context.error,
            started_at=context.started_at,
            completed_at=context.completed_at,
        )
    
    async def _run_worker(self) -> None:
        """Worker 循环"""
        while self._running:
            try:
                try:
                    _, task_id = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=0.1,
                    )
                except asyncio.TimeoutError:
                    continue
                
                context = self._tasks.get(task_id)
                if context and context.status == TaskStatusAsync.QUEUED:
                    asyncio.create_task(self._execute_task(context))
                    
            except Exception as e:
                logger.error(f"Worker error: {e}")
    
    async def _execute_task(self, context: TaskContext) -> Any:
        """执行任务"""
        async with self._semaphore:
            context.status = TaskStatusAsync.RUNNING
            context.started_at = time.time()
            
            timeout_task = None
            if context.options.timeout:
                timeout_task = asyncio.create_task(asyncio.sleep(context.options.timeout))
            
            try:
                coro = context.awaitable() if asyncio.iscoroutinefunction(context.awaitable) else context.awaitable()
                task = asyncio.create_task(coro)
                context._future = task
                
                done, pending = await asyncio.wait(
                    [task, timeout_task] if timeout_task else [task],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                
                for p in pending:
                    p.cancel()
                    try:
                        await p
                    except asyncio.CancelledError:
                        pass
                
                if task in done:
                    context.result = task.result()
                    context.status = TaskStatusAsync.COMPLETED
                elif timeout_task and timeout_task in done:
                    task.cancel()
                    context.status = TaskStatusAsync.TIMEOUT
                    context.error = "Task timed out"
                
                if context.options.on_complete:
                    context.options.on_complete(context.result)
                
            except asyncio.CancelledError:
                context.status = TaskStatusAsync.CANCELLED
                raise
            except Exception as e:
                context.status = TaskStatusAsync.FAILED
                context.error = str(e)
                logger.error(f"Task {context.task_id} failed: {e}")
                
                if context.options.on_error:
                    context.options.on_error(e)
            finally:
                context.completed_at = time.time()
                if timeout_task:
                    timeout_task.cancel()
        
        return context.result
    
    @asynccontextmanager
    async def managed(self):
        """上下文管理器"""
        await self.start()
        try:
            yield self
        finally:
            await self.stop()


# Global executor
_executor: Optional[AsyncExecutor] = None


def get_executor() -> AsyncExecutor:
    """获取全局执行器"""
    global _executor
    if _executor is None:
        _executor = AsyncExecutor()
    return _executor


async def shutdown_executor() -> None:
    """关闭全局执行器"""
    global _executor
    if _executor:
        await _executor.stop()
        _executor = None
