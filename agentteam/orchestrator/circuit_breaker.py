"""
CircuitBreaker - 生产级断路器实现

参考 Microsoft AutoGen 0.4 + Harness-MU 论文 (arXiv:2606.21856)
实现三态模式: CLOSED / OPEN / HALF_OPEN

用途:
- 模型调用失败率过高时快速失败，避免雪崩
- 自动恢复：HALF_OPEN 探测成功后重新启用 provider
- 统计信息公开：可通过 REST API 查询健康状态
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, TypeVar

T = TypeVar("T")


class CircuitState(Enum):
    CLOSED = "closed"       # 正常，允许请求通过
    OPEN = "open"           # 熔断，拒绝所有请求
    HALF_OPEN = "half_open" # 半开，只允许少量探测请求


class CircuitOpenError(Exception):
    """断路器处于 OPEN 状态时调用抛出此异常"""
    def __init__(self, provider: str, remaining_timeout: float):
        self.provider = provider
        self.remaining_timeout = remaining_timeout
        super().__init__(
            f"CircuitBreaker for '{provider}' is OPEN. "
            f"Retry in {remaining_timeout:.1f}s. "
            f"Service unavailable due to recent failures."
        )


@dataclass
class CircuitStats:
    """断路器统计信息"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0  # OPEN 状态下被拒绝的调用
    consecutive_successes: int = 0  # HALF_OPEN 状态下的连续成功
    consecutive_failures: int = 0   # CLOSED 状态下的连续失败
    last_failure_at: str = ""
    last_success_at: str = ""
    opened_at: str = ""
    closed_at: str = ""

    def success(self):
        self.total_calls += 1
        self.successful_calls += 1
        self.consecutive_successes += 1
        self.consecutive_failures = 0
        self.last_success_at = _now_iso()

    def failure(self):
        self.total_calls += 1
        self.failed_calls += 1
        self.consecutive_failures += 1
        self.consecutive_successes = 0
        self.last_failure_at = _now_iso()

    def rejected(self):
        self.rejected_calls += 1


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CircuitBreaker:
    """线程安全的生产级断路器"""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 3,  # HALF_OPEN 下连续成功次数阈值
        recovery_timeout: float = 60.0,  # 秒，OPEN 后等待多久进入 HALF_OPEN
        half_open_max_calls: int = 3,  # HALF_OPEN 状态下允许的最大并发调用
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitState.CLOSED
        self._lock = threading.RLock()
        self._half_open_semaphore = threading.Semaphore(half_open_max_calls)
        self._half_open_calls_active = 0
        self._half_open_calls_lock = threading.Lock()

        self.stats = CircuitStats()

        # OPEN 状态的打开时间（用于计算 remaining_timeout）
        self._opened_at: float = 0.0

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                elapsed = time.time() - self._opened_at
                if elapsed >= self.recovery_timeout:
                    # 时间到，自动转换到 HALF_OPEN
                    self._state = CircuitState.HALF_OPEN
                    self.stats.closed_at = _now_iso()
            return self._state

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """同步调用，受断路器保护"""
        if self.state == CircuitState.OPEN:
            elapsed = time.time() - self._opened_at
            remaining = self.recovery_timeout - elapsed
            self.stats.rejected()
            raise CircuitOpenError(self.name, max(0, remaining))

        # HALF_OPEN 状态：限制并发数
        if self._state == CircuitState.HALF_OPEN:
            acquired = self._half_open_semaphore.acquire(
                blocking=True, timeout=self.recovery_timeout
            )
            if not acquired:
                self.stats.rejected()
                raise CircuitOpenError(
                    self.name, max(0, self.recovery_timeout - (time.time() - self._opened_at))
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

        finally:
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_semaphore.release()

    async def call_async(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """异步调用，受断路器保护"""
        if self.state == CircuitState.OPEN:
            elapsed = time.time() - self._opened_at
            remaining = self.recovery_timeout - elapsed
            self.stats.rejected()
            raise CircuitOpenError(self.name, max(0, remaining))

        if self._state == CircuitState.HALF_OPEN:
            with self._half_open_calls_lock:
                if self._half_open_calls_active >= self.half_open_max_calls:
                    self.stats.rejected()
                    raise CircuitOpenError(self.name, max(0, self.recovery_timeout))
                self._half_open_calls_active += 1

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise
        finally:
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_semaphore.release()

    def _on_success(self):
        with self._lock:
            self.stats.success()

            if self._state == CircuitState.HALF_OPEN:
                if self.stats.consecutive_successes >= self.success_threshold:
                    # HALF_OPEN 连续成功达到阈值，关闭断路器
                    self._transition_to(CircuitState.CLOSED)

            elif self._state == CircuitState.CLOSED:
                # CLOSED 状态下重置连续失败计数（这里已经在 stats.failure() 里处理了）
                pass

    def _on_failure(self):
        with self._lock:
            self.stats.failure()

            if self._state == CircuitState.HALF_OPEN:
                # HALF_OPEN 状态下任何失败都立即 OPEN
                self._transition_to(CircuitState.OPEN)

            elif self._state == CircuitState.CLOSED:
                if self.stats.consecutive_failures >= self.failure_threshold:
                    # 达到阈值，打开断路器
                    self._transition_to(CircuitState.OPEN)

    def _transition_to(self, new_state: CircuitState):
        old_state = self._state
        self._state = new_state

        if new_state == CircuitState.OPEN:
            self._opened_at = time.time()
            self.stats.opened_at = _now_iso()
        elif new_state == CircuitState.CLOSED:
            self.stats.closed_at = _now_iso()
            # 重置所有计数
            self.stats.consecutive_failures = 0
            self.stats.consecutive_successes = 0
            self._opened_at = 0.0
        elif new_state == CircuitState.HALF_OPEN:
            self.stats.consecutive_successes = 0

        logger.debug(
            f"CircuitBreaker '{self.name}': {old_state.value} → {new_state.value}"
        )

    def force_open(self):
        """强制打开断路器（用于管理操作）"""
        with self._lock:
            self._transition_to(CircuitState.OPEN)

    def force_close(self):
        """强制关闭断路器（用于管理操作）"""
        with self._lock:
            self._transition_to(CircuitState.CLOSED)

    def is_available(self) -> bool:
        """断路器是否允许请求通过"""
        return self.state != CircuitState.OPEN

    def health_report(self) -> dict:
        """返回健康报告，用于监控和调试"""
        with self._lock:
            report = {
                "name": self.name,
                "state": self.state.value,
                "stats": {
                    "total_calls": self.stats.total_calls,
                    "success_rate": (
                        self.stats.successful_calls / self.stats.total_calls
                        if self.stats.total_calls > 0 else 0.0
                    ),
                    "failure_rate": (
                        self.stats.failed_calls / self.stats.total_calls
                        if self.stats.total_calls > 0 else 0.0
                    ),
                    "rejected_calls": self.stats.rejected_calls,
                    "consecutive_failures": self.stats.consecutive_failures,
                    "consecutive_successes": self.stats.consecutive_successes,
                    "last_failure_at": self.stats.last_failure_at,
                    "last_success_at": self.stats.last_success_at,
                },
            }
            if self._state == CircuitState.OPEN:
                elapsed = time.time() - self._opened_at
                report["recovery_in_seconds"] = max(
                    0.0, self.recovery_timeout - elapsed
                )
            return report


# ── 全局断路器注册表 ───────────────────────────────────────────────────────

_cb_registry: dict[str, CircuitBreaker] = {}
_registry_lock = threading.RLock()


def get_circuit_breaker(name: str, **kwargs) -> CircuitBreaker:
    """获取或创建命名的断路器（全局单例）"""
    with _registry_lock:
        if name not in _cb_registry:
            _cb_registry[name] = CircuitBreaker(name, **kwargs)
        return _cb_registry[name]


def list_circuit_breakers() -> dict[str, dict]:
    """列出所有断路器的健康状态"""
    with _registry_lock:
        return {name: cb.health_report() for name, cb in _cb_registry.items()}


logger = logging.getLogger(__name__)
