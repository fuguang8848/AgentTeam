"""
ClawTeam Performance Profiler

Provides profiling utilities for analyzing latency, throughput, memory, and resource usage.
"""

import time
import asyncio
import psutil
import threading
from typing import Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from contextlib import contextmanager
from functools import wraps
import json
from pathlib import Path


@dataclass
class ProfileResult:
    """Result of a profiling run"""

    name: str
    start_time: str
    end_time: str
    duration_ms: float
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    throughput: Optional[float] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "cpu_percent": self.cpu_percent,
            "memory_mb": self.memory_mb,
            "memory_percent": self.memory_percent,
            "throughput": self.throughput,
            "metadata": self.metadata,
        }


@dataclass
class LatencyResult:
    """Latency measurement result"""

    operation: str
    count: int
    total_ms: float
    min_ms: float
    max_ms: float
    avg_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float

    def to_dict(self) -> dict:
        return {
            "operation": self.operation,
            "count": self.count,
            "total_ms": self.total_ms,
            "min_ms": self.min_ms,
            "max_ms": self.max_ms,
            "avg_ms": self.avg_ms,
            "p50_ms": self.p50_ms,
            "p95_ms": self.p95_ms,
            "p99_ms": self.p99_ms,
        }


class Profiler:
    """
    Performance profiler for ClawTeam operations.

    Usage:
        profiler = Profiler()

        # Context manager
        with profiler.profile("my_operation"):
            # do work
            pass

        # Decorator
        @profiler.profile_func()
        def my_function():
            pass

        # Manual
        profiler.start("my_task")
        # ... work ...
        result = profiler.stop("my_task")
    """

    def __init__(self):
        self._profiles: dict[str, ProfileResult] = {}
        self._latencies: dict[str, list[float]] = {}
        self._start_times: dict[str, float] = {}
        self._start_cpu: dict[str, float] = {}
        self._lock = threading.Lock()

    def start(self, name: str) -> None:
        """Start profiling an operation"""
        with self._lock:
            self._start_times[name] = time.perf_counter()
            self._start_cpu[name] = psutil.cpu_percent()

    def stop(self, name: str, **metadata) -> ProfileResult:
        """Stop profiling and return result"""
        with self._lock:
            if name not in self._start_times:
                raise ValueError(f"Profile '{name}' was not started")

            start = self._start_times.pop(name)
            start_cpu = self._start_cpu.pop(name, 0)
            end = time.perf_counter()

            duration_ms = (end - start) * 1000
            end_cpu = psutil.cpu_percent()
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            memory_percent = process.memory_percent()

            result = ProfileResult(
                name=name,
                start_time=datetime.fromtimestamp(start, tz=timezone.utc).isoformat(),
                end_time=datetime.now(timezone.utc).isoformat(),
                duration_ms=duration_ms,
                cpu_percent=(start_cpu + end_cpu) / 2,
                memory_mb=memory_mb,
                memory_percent=memory_percent,
                metadata=metadata,
            )

            self._profiles[name] = result
            return result

    @contextmanager
    def profile(self, name: str, **metadata):
        """Context manager for profiling"""
        self.start(name)
        try:
            yield self.stop(name, **metadata)
        except Exception as e:
            metadata["error"] = str(e)
            self.stop(name, **metadata)
            raise

    def profile_func(self, name: Optional[str] = None):
        """Decorator for profiling functions"""

        def decorator(func: Callable) -> Callable:
            profile_name = name or func.__name__

            @wraps(func)
            def wrapper(*args, **kwargs):
                with self.profile(profile_name):
                    return func(*args, **kwargs)

            return wrapper

        return decorator

    def measure_latency(self, name: str, func: Callable, *args, **kwargs) -> Any:
        """Measure function latency"""
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            elapsed = (time.perf_counter() - start) * 1000
            if name not in self._latencies:
                self._latencies[name] = []
            self._latencies[name].append(elapsed)

    async def measure_latency_async(self, name: str, coro) -> Any:
        """Measure async function latency"""
        start = time.perf_counter()
        try:
            result = await coro
            return result
        finally:
            elapsed = (time.perf_counter() - start) * 1000
            if name not in self._latencies:
                self._latencies[name] = []
            self._latencies[name].append(elapsed)

    def get_latency_stats(self, name: str) -> Optional[LatencyResult]:
        """Get latency statistics for an operation"""
        if name not in self._latencies or not self._latencies[name]:
            return None

        latencies = sorted(self._latencies[name])
        count = len(latencies)
        total = sum(latencies)

        return LatencyResult(
            operation=name,
            count=count,
            total_ms=total,
            min_ms=latencies[0],
            max_ms=latencies[-1],
            avg_ms=total / count,
            p50_ms=latencies[int(count * 0.50)],
            p95_ms=latencies[int(count * 0.95)] if count > 20 else latencies[-1],
            p99_ms=latencies[int(count * 0.99)] if count > 100 else latencies[-1],
        )

    def get_all_latency_stats(self) -> list[LatencyResult]:
        """Get all latency statistics"""
        return [
            stats for name in self._latencies if (stats := self.get_latency_stats(name)) is not None
        ]

    def get_profile(self, name: str) -> Optional[ProfileResult]:
        """Get a specific profile result"""
        return self._profiles.get(name)

    def get_all_profiles(self) -> list[ProfileResult]:
        """Get all profile results"""
        return list(self._profiles.values())

    def clear(self) -> None:
        """Clear all profiling data"""
        with self._lock:
            self._profiles.clear()
            self._latencies.clear()
            self._start_times.clear()
            self._start_cpu.clear()

    def export_json(self, filepath: str) -> None:
        """Export profiling data to JSON file"""
        data = {
            "profiles": [p.to_dict() for p in self._profiles.values()],
            "latencies": [s.to_dict() for s in self.get_all_latency_stats()],
        }
        Path(filepath).write_text(json.dumps(data, indent=2, ensure_ascii=False))


class ResourceMonitor:
    """Monitor system resource usage over time"""

    def __init__(self, interval: float = 1.0):
        self.interval = interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._samples: list[dict] = []
        self._lock = threading.Lock()

    def start(self) -> None:
        """Start monitoring"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self) -> list[dict]:
        """Stop monitoring and return samples"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        with self._lock:
            samples = self._samples.copy()
            self._samples.clear()
        return samples

    def _monitor_loop(self) -> None:
        """Main monitoring loop"""
        process = psutil.Process()
        while self._running:
            try:
                sample = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_mb": process.memory_info().rss / (1024 * 1024),
                    "memory_percent": process.memory_percent(),
                    "threads": process.num_threads(),
                    "open_files": len(process.open_files()),
                }
                with self._lock:
                    self._samples.append(sample)
            except Exception:
                pass
            time.sleep(self.interval)

    def get_current_usage(self) -> dict:
        """Get current resource usage"""
        process = psutil.Process()
        return {
            "cpu_percent": psutil.cpu_percent(),
            "memory_mb": process.memory_info().rss / (1024 * 1024),
            "memory_percent": process.memory_percent(),
            "threads": process.num_threads(),
            "open_files": len(process.open_files()),
        }


# Global profiler instance
_profiler = Profiler()


def get_profiler() -> Profiler:
    """Get the global profiler instance"""
    return _profiler


def profile(name: Optional[str] = None):
    """Convenience decorator"""
    return _profiler.profile_func(name)


@contextmanager
def profile_block(name: str, **metadata):
    """Convenience context manager"""
    yield _profiler.profile(name, **metadata)


__all__ = [
    "Profiler",
    "ProfileResult",
    "LatencyResult",
    "ResourceMonitor",
    "get_profiler",
    "profile",
    "profile_block",
]
