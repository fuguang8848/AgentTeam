"""
Async Types for AgentTeam SDK

定义异步运行时所需的类型和枚举。
"""

from __future__ import annotations

import asyncio
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Any, Callable


class AsyncAgentState(Enum):
    """异步 Agent 状态"""
    
    IDLE = "idle"
    INITIALIZING = "initializing"
    RUNNING = "running"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatusAsync(Enum):
    """异步任务状态"""
    
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class AsyncTaskResult:
    """异步任务结果"""
    
    task_id: str
    status: TaskStatusAsync
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    duration: Optional[float] = None
    metadata: dict = field(default_factory=dict)
    
    @property
    def is_success(self) -> bool:
        return self.status == TaskStatusAsync.COMPLETED
    
    @property
    def is_failure(self) -> bool:
        return self.status in (TaskStatusAsync.FAILED, TaskStatusAsync.TIMEOUT)
    
    @property
    def is_done(self) -> bool:
        return self.status in (
            TaskStatusAsync.COMPLETED,
            TaskStatusAsync.FAILED,
            TaskStatusAsync.CANCELLED,
            TaskStatusAsync.TIMEOUT,
        )


@dataclass
class AsyncTaskOptions:
    """异步任务选项"""
    
    timeout: Optional[float] = None
    retry_count: int = 0
    retry_delay: float = 1.0
    priority: int = 0
    on_start: Optional[Callable[[], None]] = None
    on_complete: Optional[Callable[[Any], None]] = None
    on_error: Optional[Callable[[Exception], None]] = None


class AsyncEvent:
    """异步事件"""
    
    def __init__(self):
        self._event = asyncio.Event()
        self._set = False
    
    def set(self) -> None:
        if not self._set:
            self._event.set()
            self._set = True
    
    def clear(self) -> None:
        self._event.clear()
        self._set = False
    
    async def wait(self) -> None:
        await self._event.wait()
    
    def is_set(self) -> bool:
        return self._set


class AsyncCondition:
    """异步条件变量"""
    
    def __init__(self):
        self._condition = asyncio.Condition()
    
    async def acquire(self) -> None:
        await self._condition.acquire()
    
    def release(self) -> None:
        self._condition.release()
    
    async def wait(self) -> bool:
        return await self._condition.wait()
    
    async def notify(self, n: int = 1) -> None:
        self._condition.notify(n)
    
    async def notify_all(self) -> None:
        self._condition.notify_all()


class AsyncLock:
    """异步锁"""
    
    def __init__(self):
        self._lock = asyncio.Lock()
    
    async def __aenter__(self) -> "AsyncLock":
        await self._lock.acquire()
        return self
    
    async def __aexit__(self, *args) -> None:
        self._lock.release()


class AsyncSemaphore:
    """异步信号量"""
    
    def __init__(self, value: int = 1):
        self._semaphore = asyncio.Semaphore(value)
    
    async def __aenter__(self) -> "AsyncSemaphore":
        await self._semaphore.acquire()
        return self
    
    async def __aexit__(self, *args) -> None:
        self._semaphore.release()


# Re-export
TaskResult = AsyncTaskResult
TaskOptions = AsyncTaskOptions
