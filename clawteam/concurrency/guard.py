"""
ConcurrencyGuard - 并发控制和资源检查

参考 SpectrAI/src/main/session/ConcurrencyGuard.ts 实现
支持 Windows/macOS/Linux 跨平台

功能：
- 最大会话数限制
- 内存检查
- CPU检查（可选）
- 系统资源状态监控

@author ClawTeam
"""

import logging
import os
import platform
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class ConcurrencyConfig:
    """并发控制配置"""

    max_sessions: int = 9
    min_memory_mb: int = 512  # 最小可用内存要求（MB）
    max_cpu_percent: float = 90.0  # 最大CPU使用率阈值
    warn_memory_percent: float = 85.0  # 内存警告阈值
    warn_session_percent: float = 0.8  # 会话数警告阈值（80%）

    # macOS 特殊配置（内存计算更精确）
    darwin_min_memory_mb: int = 256


@dataclass
class ResourceStatus:
    """资源状态检查结果"""

    can_create: bool
    reason: Optional[str] = None
    current_sessions: int = 0
    max_sessions: int = 0
    memory_usage_percent: float = 0.0
    available_memory_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    platform: str = ""
    arch: str = ""
    cpu_count: int = 0
    total_memory_mb: float = 0.0
    uptime_seconds: float = 0.0


class ConcurrencyGuard:
    """
    并发控制器

    管理 Agent/Session 的并发数量限制，检查系统资源状态。
    支持 Windows/macOS/Linux 跨平台。

    使用示例：
        guard = ConcurrencyGuard()

        # 检查是否可以创建新会话
        status = guard.check_resources()
        if status.can_create:
            guard.register_session()
            # ... 创建会话
        else:
            print(f"无法创建: {status.reason}")

        # 会话结束时注销
        guard.unregister_session()
    """

    def __init__(self, config: Optional[ConcurrencyConfig] = None):
        """初始化并发控制器"""
        self.config = config or ConcurrencyConfig()
        self._active_sessions: int = 0
        self._session_registry: Dict[str, float] = {}  # session_id -> start_time

        # 根据平台调整最小内存要求
        if platform.system() == "Darwin":
            self.config.min_memory_mb = self.config.darwin_min_memory_mb

    def _get_memory_snapshot(self) -> Dict[str, float]:
        """
        获取内存快照

        Returns:
            dict: 包含 total_mem_mb, available_mem_mb, memory_usage_percent
        """
        total_mem_mb = self._get_total_memory()
        free_mem_mb = self._get_free_memory()

        # macOS 使用 vm_stat 获取更精确的可用内存
        if platform.system() == "Darwin":
            try:
                vm_stat_output = subprocess.run(["/usr/bin/vm_stat"], capture_output=True, text=True, timeout=2).stdout

                available_mb = self._parse_darwin_vm_stat(vm_stat_output, total_mem_mb)
                if available_mb > 0:
                    free_mem_mb = max(free_mem_mb, available_mb)
            except Exception as e:
                logger.debug(f"vm_stat 解析失败: {e}")

        memory_usage_percent = ((total_mem_mb - free_mem_mb) / total_mem_mb) * 100 if total_mem_mb > 0 else 0

        return {
            "total_mem_mb": total_mem_mb,
            "available_mem_mb": free_mem_mb,
            "memory_usage_percent": memory_usage_percent,
        }

    def _get_total_memory(self) -> float:
        """获取总内存（MB）"""
        try:
            import psutil

            return psutil.virtual_memory().total / (1024 * 1024)
        except ImportError:
            # Windows: 使用 WMI
            if platform.system() == "Windows":
                try:
                    output = subprocess.run(
                        ["wmic", "OS", "get", "TotalVisibleMemorySize", "/value"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    ).stdout
                    for line in output.split("\n"):
                        if "TotalVisibleMemorySize=" in line:
                            kb = int(line.split("=")[1])
                            return kb / 1024  # KB to MB
                except Exception:
                    pass

            # Linux: 读取 /proc/meminfo
            if platform.system() == "Linux":
                try:
                    with open("/proc/meminfo", "r") as f:
                        for line in f:
                            if "MemTotal:" in line:
                                kb = int(line.split()[1])
                                return kb / 1024
                except Exception:
                    pass

            # Fallback: 使用 os 模块（不精确）
            return (
                os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / (1024 * 1024)
                if hasattr(os, "sysconf")
                else 8192
            )

    def _get_free_memory(self) -> float:
        """获取可用内存（MB）"""
        try:
            import psutil

            return psutil.virtual_memory().available / (1024 * 1024)
        except ImportError:
            # Windows
            if platform.system() == "Windows":
                try:
                    output = subprocess.run(
                        ["wmic", "OS", "get", "FreePhysicalMemory", "/value"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    ).stdout
                    for line in output.split("\n"):
                        if "FreePhysicalMemory=" in line:
                            kb = int(line.split("=")[1])
                            return kb / 1024
                except Exception:
                    pass

            # Linux
            if platform.system() == "Linux":
                try:
                    with open("/proc/meminfo", "r") as f:
                        meminfo = {}
                        for line in f:
                            parts = line.split()
                            key = parts[0].rstrip(":")
                            value = int(parts[1])
                            meminfo[key] = value

                        # MemAvailable 是更准确的可用内存指标
                        if "MemAvailable" in meminfo:
                            return meminfo["MemAvailable"] / 1024
                        # 否则使用 MemFree + Buffers + Cached
                        free = meminfo.get("MemFree", 0)
                        buffers = meminfo.get("Buffers", 0)
                        cached = meminfo.get("Cached", 0)
                        return (free + buffers + cached) / 1024
                except Exception:
                    pass

            # Fallback
            return 1024  # 默认1GB可用

    def _parse_darwin_vm_stat(self, output: str, total_mem_mb: float) -> float:
        """
        解析 macOS vm_stat 输出

        vm_stat 输出格式：
        Pages free: 123456.
        Pages inactive: 78901.
        Pages speculative: 12345.
        Pages purgeable: 5678.
        """
        try:
            # 获取 page size
            page_size_match = output.lower().split("page size of")
            if len(page_size_match) > 1:
                page_size_str = page_size_match[1].split()[0]
                page_size = int(page_size_str)
            else:
                page_size = 4096  # 默认 4KB

            # 解析各类页面数
            def parse_pages(label: str) -> int:
                import re

                pattern = re.escape(label) + r":\s*(\d+)\."
                match = re.search(pattern, output, re.IGNORECASE)
                return int(match.group(1)) if match else 0

            free_pages = parse_pages("Pages free")
            inactive_pages = parse_pages("Pages inactive")
            speculative_pages = parse_pages("Pages speculative")
            purgeable_pages = parse_pages("Pages purgeable")

            # 可回收页面总数
            reclaimable_pages = free_pages + inactive_pages + speculative_pages + purgeable_pages
            available_mb = (reclaimable_pages * page_size) / (1024 * 1024)

            return available_mb if available_mb > 0 else 0
        except Exception as e:
            logger.debug(f"vm_stat 解析错误: {e}")
            return 0

    def _get_cpu_usage(self) -> float:
        """获取CPU使用率"""
        try:
            import psutil

            return psutil.cpu_percent(interval=0.5)
        except ImportError:
            # Windows: 使用 wmic
            if platform.system() == "Windows":
                try:
                    output = subprocess.run(
                        ["wmic", "cpu", "get", "LoadPercentage", "/value"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    ).stdout
                    for line in output.split("\n"):
                        if "LoadPercentage=" in line:
                            return float(line.split("=")[1])
                except Exception:
                    pass

            # Linux: 读取 /proc/stat
            if platform.system() == "Linux":
                try:
                    with open("/proc/stat", "r") as f:
                        line = f.readline()
                        parts = line.split()
                        if parts[0] == "cpu":
                            # cpu  user nice system idle iowait irq softirq
                            user = int(parts[1])
                            nice = int(parts[2])
                            system = int(parts[3])
                            idle = int(parts[4])
                            total = user + nice + system + idle
                            if total > 0:
                                return ((total - idle) / total) * 100
                except Exception:
                    pass

            return 50.0  # 默认50%

    def can_create_session(self) -> bool:
        """检查是否可以创建新会话（仅检查数量限制）"""
        return self._active_sessions < self.config.max_sessions

    def check_resources(self) -> ResourceStatus:
        """
        全面检查系统资源状态

        Returns:
            ResourceStatus: 包含是否可创建、原因、资源详情
        """
        memory_snapshot = self._get_memory_snapshot()
        cpu_usage = self._get_cpu_usage()

        # 获取系统信息
        system_info = self.get_system_info()

        # 检查会话数限制
        if self._active_sessions >= self.config.max_sessions:
            return ResourceStatus(
                can_create=False,
                reason=f"Maximum session limit reached ({self.config.max_sessions})",
                current_sessions=self._active_sessions,
                max_sessions=self.config.max_sessions,
                memory_usage_percent=memory_snapshot["memory_usage_percent"],
                available_memory_mb=memory_snapshot["available_mem_mb"],
                cpu_usage_percent=cpu_usage,
                **system_info,
            )

        # 检查内存
        if memory_snapshot["available_mem_mb"] < self.config.min_memory_mb:
            return ResourceStatus(
                can_create=False,
                reason=f"Insufficient memory ({int(memory_snapshot['available_mem_mb'])}MB available, {self.config.min_memory_mb}MB required)",
                current_sessions=self._active_sessions,
                max_sessions=self.config.max_sessions,
                memory_usage_percent=memory_snapshot["memory_usage_percent"],
                available_memory_mb=memory_snapshot["available_mem_mb"],
                cpu_usage_percent=cpu_usage,
                **system_info,
            )

        # 检查CPU（可选，仅警告）
        # CPU过高不阻止创建，但记录在状态中

        return ResourceStatus(
            can_create=True,
            current_sessions=self._active_sessions,
            max_sessions=self.config.max_sessions,
            memory_usage_percent=memory_snapshot["memory_usage_percent"],
            available_memory_mb=memory_snapshot["available_mem_mb"],
            cpu_usage_percent=cpu_usage,
            **system_info,
        )

    def register_session(self, session_id: Optional[str] = None) -> str:
        """
        注册新会话

        Args:
            session_id: 可选的会话ID，不提供则自动生成

        Returns:
            str: 会话ID
        """
        import uuid

        sid = session_id or str(uuid.uuid4())
        self._active_sessions += 1
        self._session_registry[sid] = time.time()
        logger.info(f"Session registered: {sid}, active sessions: {self._active_sessions}")
        return sid

    def unregister_session(self, session_id: str) -> bool:
        """
        注销会话

        Args:
            session_id: 要注销的会话ID

        Returns:
            bool: 是否成功注销
        """
        if session_id in self._session_registry:
            del self._session_registry[session_id]
            if self._active_sessions > 0:
                self._active_sessions -= 1
            logger.info(f"Session unregistered: {session_id}, active sessions: {self._active_sessions}")
            return True
        return False

    def get_active_session_count(self) -> int:
        """获取当前活跃会话数"""
        return self._active_sessions

    def get_max_sessions(self) -> int:
        """获取最大会话数"""
        return self.config.max_sessions

    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        return {
            "platform": platform.system(),
            "arch": platform.machine(),
            "cpu_count": os.cpu_count() or 1,
            "total_memory_mb": self._get_total_memory(),
            "uptime_seconds": time.time() - (time.time() % 86400),  # 简化的uptime
        }

    def should_warn_resources(self) -> Dict[str, Any]:
        """
        检查是否应该警告用户资源不足

        Returns:
            dict: {warn: bool, message: str}
        """
        memory_snapshot = self._get_memory_snapshot()

        # 会话数警告（优先检查，会话超限比内存高更紧急）
        if self._active_sessions >= self.config.max_sessions * self.config.warn_session_percent:
            return {
                "warn": True,
                "message": f"Approaching session limit: {self._active_sessions}/{self.config.max_sessions}",
            }

        # 内存警告
        if memory_snapshot["memory_usage_percent"] > self.config.warn_memory_percent:
            return {
                "warn": True,
                "message": f"High memory usage: {int(memory_snapshot['memory_usage_percent'])}%",
            }

        return {"warn": False}

    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        for key, value in config.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

    def get_session_duration(self, session_id: str) -> float:
        """获取会话持续时间（秒）"""
        if session_id in self._session_registry:
            return time.time() - self._session_registry[session_id]
        return 0.0

    def cleanup(self) -> None:
        """清理所有会话记录"""
        self._session_registry.clear()
        self._active_sessions = 0
        logger.info("ConcurrencyGuard cleanup completed")


# 类型提示辅助（已移除，使用 Dict[str, Any] 替代）
