"""Provider 可用性检测

检测本地是否安装了对应的 CLI 工具。
参考 SpectrAI providerAvailability.ts 实现。

@author ClawTeam
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ProviderAvailability:
    """可用性检测结果"""

    id: str
    name: str
    command: str
    available: bool
    version: str = ""
    last_checked: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "command": self.command,
            "available": self.available,
            "version": self.version,
            "lastChecked": self.last_checked,
            "error": self.error,
        }


@dataclass
class ProviderConfig:
    """Provider 配置"""

    id: str
    name: str
    command: str
    node_version: str = ""  # 用于 PATH 检测的 Node 版本
    check_args: list[str] = field(default_factory=list)  # 检测命令参数

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "command": self.command,
            "nodeVersion": self.node_version,
            "checkArgs": self.check_args,
        }


# 缓存：cacheKey → available（避免频繁 spawn 进程）
_cache: dict[str, dict] = {}
_cache_lock = threading.Lock()
CACHE_TTL_SECONDS = 60  # 缓存 60 秒


# 预定义的 Provider 配置
PROVIDER_CONFIGS: dict[str, ProviderConfig] = {
    "claude-code": ProviderConfig(
        id="claude-code",
        name="Claude Code",
        command="claude",
        check_args=["--version"],
    ),
    "codex": ProviderConfig(
        id="codex",
        name="Codex",
        command="codex",
        check_args=["--version"],
    ),
    "gemini-cli": ProviderConfig(
        id="gemini-cli",
        name="Gemini CLI",
        command="gemini",
        check_args=["--version"],
    ),
    "iflow": ProviderConfig(
        id="iflow",
        name="IFlow",
        command="iflow",
        check_args=["--version"],
    ),
    "opencode": ProviderConfig(
        id="opencode",
        name="OpenCode",
        command="opencode",
        check_args=["--version"],
    ),
    "kimi": ProviderConfig(
        id="kimi",
        name="Kimi",
        command="kimi",
        check_args=["--version"],
    ),
    "qwen": ProviderConfig(
        id="qwen",
        name="Qwen",
        command="qwen",
        check_args=["--version"],
    ),
    "openclaw": ProviderConfig(
        id="openclaw",
        name="OpenClaw",
        command="openclaw",
        check_args=["--version"],
    ),
}


def _get_cache_key(command: str, node_version: str = "") -> str:
    """生成缓存键"""
    if node_version:
        return f"{command}@node{node_version}"
    return command


def _check_command_available(
    command: str, node_version: str = ""
) -> tuple[bool, str, str, float | None]:
    """检测单个命令是否在 PATH 中可用

    Returns:
        (available, version, error, checked_at) - checked_at is None if not from cache
    """
    cache_key = _get_cache_key(command, node_version)

    # 先查缓存
    with _cache_lock:
        cached = _cache.get(cache_key)
        if cached:
            elapsed = time.time() - cached.get("checked_at", 0)
            if elapsed < CACHE_TTL_SECONDS:
                return (
                    cached.get("available", False),
                    cached.get("version", ""),
                    cached.get("error", ""),
                    cached.get("checked_at"),
                )

    # 检测命令是否可用
    available = False
    version = ""
    error = ""

    try:
        # 如果是绝对路径，直接检查文件是否存在
        if os.path.isabs(command):
            available = os.path.exists(command)
            if available and os.name != "nt":
                # Unix 系统检查执行权限
                if not os.access(command, os.X_OK):
                    available = False
        else:
            # 使用 which/where 查找命令
            checker = "where" if os.name == "nt" else "which"
            result = subprocess.run(
                [checker, command],
                capture_output=True,
                text=True,
                timeout=5,
                windowsHide=True,
            )
            available = result.returncode == 0

        # 如果可用，尝试获取版本
        if available:
            config = PROVIDER_CONFIGS.get(command, None)
            if config and config.check_args:
                try:
                    result = subprocess.run(
                        [command] + config.check_args,
                        capture_output=True,
                        text=True,
                        timeout=5,
                        windowsHide=True,
                    )
                    if result.returncode == 0:
                        version = result.stdout.strip().split("\n")[0]
                except Exception as e:
                    logger.debug(f"Failed to get version for {command}: {e}")

    except subprocess.TimeoutExpired:
        error = "Timeout"
        available = False
    except FileNotFoundError:
        error = "Not found"
        available = False
    except Exception as e:
        error = str(e)
        available = False

    # 更新缓存
    checked_at = time.time()
    with _cache_lock:
        _cache[cache_key] = {
            "available": available,
            "version": version,
            "error": error,
            "checked_at": checked_at,
        }

    return available, version, error, checked_at


def check_provider_availability(provider_id: str) -> ProviderAvailability:
    """检测单个 Provider 的可用性"""
    config = PROVIDER_CONFIGS.get(provider_id)
    if not config:
        return ProviderAvailability(
            id=provider_id,
            name=provider_id,
            command=provider_id,
            available=False,
            error="Unknown provider",
        )

    available, version, error, checked_at = _check_command_available(
        config.command, config.node_version
    )

    # Use cached timestamp if available
    if checked_at is not None:
        last_checked = datetime.fromtimestamp(checked_at, tz=timezone.utc).isoformat()
    else:
        last_checked = datetime.now(timezone.utc).isoformat()

    return ProviderAvailability(
        id=config.id,
        name=config.name,
        command=config.command,
        available=available,
        version=version,
        last_checked=last_checked,
        error=error if not available else "",
    )


def check_all_providers_availability() -> list[ProviderAvailability]:
    """批量检测所有 Provider 的可用性"""
    results = []
    for provider_id in PROVIDER_CONFIGS:
        results.append(check_provider_availability(provider_id))
    return results


def get_available_providers() -> list[ProviderAvailability]:
    """获取所有可用的 Provider 列表"""
    results = check_all_providers_availability()
    return [r for r in results if r.available]


def is_provider_available(provider_id: str) -> bool:
    """检测单个 Provider 是否可用"""
    result = check_provider_availability(provider_id)
    return result.available


def clear_availability_cache() -> None:
    """清除缓存（用于手动刷新）"""
    with _cache_lock:
        _cache.clear()


def get_availability_summary() -> dict:
    """获取可用性检测摘要"""
    results = check_all_providers_availability()
    available = [r for r in results if r.available]
    unavailable = [r for r in results if not r.available]

    return {
        "totalProviders": len(results),
        "availableCount": len(available),
        "unavailableCount": len(unavailable),
        "availableProviders": [r.to_dict() for r in available],
        "unavailableProviders": [r.to_dict() for r in unavailable],
        "lastChecked": datetime.now(timezone.utc).isoformat(),
    }


def register_provider_config(config: ProviderConfig) -> None:
    """动态注册 Provider 配置"""
    PROVIDER_CONFIGS[config.id] = config


def unregister_provider_config(provider_id: str) -> bool:
    """注销 Provider 配置"""
    if provider_id in PROVIDER_CONFIGS:
        del PROVIDER_CONFIGS[provider_id]
        return True
    return False
