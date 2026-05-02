"""文件改动追踪 — 追踪 AI Agent 的文件修改。

能力：
- FS Watch 监听文件变化
- 去抖（debounce）避免频繁触发
- 归因：记录哪个 Agent 在哪个 Session 改的
- diff 生成
- 蓝点标注（文件在编辑器中标记为已修改）

集成现有模块：
- change_attribution.py: 归因引擎
- diff_tracker.py: diff 生成和存储
- file_watcher.py: 文件系统监听

这是对已有 tracker 模块的整合和增强，提供统一的 FileChangeTracker API。
"""

from __future__ import annotations
import logging
import threading
import time
from typing import Any, Dict, List, Optional, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from clawteam.tracker.change_attribution import ChangeRecord, ChangeAttributor, ActiveSession
from clawteam.tracker.diff_tracker import DiffTracker, DiffEntry
from clawteam.tracker.file_watcher import FileWatcher, WatchEvent, ChangeType, watch_directory

logger = logging.getLogger(__name__)


class FileChange(BaseModel):
    """单个文件变更记录"""

    file_path: str
    agent_name: str
    session_id: str
    timestamp: float = Field(default_factory=time.time)
    change_type: str  # created, modified, deleted
    diff: str = ""
    team_name: str = ""
    task_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "file_path": self.file_path,
            "agent_name": self.agent_name,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "change_type": self.change_type,
            "diff": self.diff,
            "team_name": self.team_name,
            "task_id": self.task_id,
        }

    @classmethod
    def from_change_record(cls, record: ChangeRecord, diff: Optional[str] = None) -> FileChange:
        """从 ChangeRecord 创建 FileChange"""
        return cls(
            file_path=record.path,
            agent_name=record.agent_name,
            session_id=record.session_id,
            timestamp=datetime.fromisoformat(record.timestamp).timestamp(),
            change_type=record.change_type,
            diff=diff or record.diff or "",
            team_name=record.team_name,
            task_id=record.task_id,
        )


@dataclass
class FileChangeTrackerConfig:
    """文件追踪器配置"""

    # 监听路径
    watch_paths: List[str] = field(default_factory=list)
    # 忽略模式
    ignore_patterns: List[str] = field(
        default_factory=lambda: [
            "*.pyc",
            "*.pyo",
            "__pycache__/*",
            ".git/*",
            "*.swp",
            "*.swo",
            ".DS_Store",
            "node_modules/*",
            "*.log",
            ".coverage",
            "htmlcov/*",
        ]
    )
    # 去抖间隔（毫秒）
    debounce_ms: int = 100
    # 是否自动开始监听
    auto_start: bool = True
    # 团队名称
    team_name: str = "default"
    # 最大历史记录数
    max_history: int = 1000


class FileChangeTracker:
    """文件改动追踪管理器"""

    def __init__(self, config: Optional[FileChangeTrackerConfig] = None):
        """初始化文件追踪器"""
        self.config = config or FileChangeTrackerConfig()

        # 归因引擎
        self.attributor = ChangeAttributor(team_name=self.config.team_name)

        # diff 追踪器
        self.diff_tracker = DiffTracker(team_name=self.config.team_name)

        # 文件监听器
        self.watcher: Optional[FileWatcher] = None

        # 活跃会话跟踪
        self.active_sessions: Dict[str, ActiveSession] = {}

        # 变更历史
        self.change_history: List[FileChange] = []

        # 锁
        self._lock = threading.Lock()

        # 启动文件监听器
        if self.config.auto_start and self.config.watch_paths:
            self.start()

    # ------------------------------------------------------------------
    # 会话管理
    # ------------------------------------------------------------------

    def register_session(
        self,
        session_id: str,
        agent_name: str,
        team_name: str = "",
        task_id: str = "",
        working_directory: str = "",
    ) -> None:
        """注册活跃会话"""
        with self._lock:
            session = ActiveSession(
                session_id=session_id,
                agent_name=agent_name,
                team_name=team_name or self.config.team_name,
                task_id=task_id,
                working_directory=working_directory,
            )
            self.active_sessions[session_id] = session
            # 使用 attributor 的正确 API
            self.attributor.register_session(
                session_id=session_id,
                agent_name=agent_name,
                working_directory=working_directory,
                task_id=task_id,
            )
            logger.info(f"Registered session {session_id} for agent {agent_name}")

    def unregister_session(self, session_id: str) -> None:
        """注销会话"""
        with self._lock:
            if session_id in self.active_sessions:
                self.attributor.unregister_session(session_id)
                del self.active_sessions[session_id]
                logger.info(f"Unregistered session {session_id}")

    def update_session_activity(self, session_id: str, file_path: Optional[str] = None) -> None:
        """更新会话活跃时间"""
        with self._lock:
            if session_id in self.active_sessions:
                session = self.active_sessions[session_id]
                session.last_activity_at = datetime.now(timezone.utc).isoformat()
                if file_path:
                    if file_path not in session.files_modified:
                        session.files_modified.append(file_path)

    # ------------------------------------------------------------------
    # 文件监听控制
    # ------------------------------------------------------------------

    def start(self) -> None:
        """开始文件监听"""
        if not self.config.watch_paths:
            logger.warning("No watch paths configured, cannot start watcher")
            return

        if self.watcher is not None:
            logger.info("Watcher already running")
            return

        try:
            self.watcher = FileWatcher(
                watch_paths=self.config.watch_paths,
                handler=self._handle_watch_event,
                ignore_patterns=self.config.ignore_patterns,
                debounce_ms=self.config.debounce_ms,
            )
            self.watcher.start()
            logger.info(f"File watcher started for paths: {self.config.watch_paths}")
        except Exception as e:
            logger.error(f"Failed to start file watcher: {e}")
            self.watcher = None

    def stop(self) -> None:
        """停止文件监听"""
        if self.watcher is not None:
            self.watcher.stop()
            self.watcher = None
            logger.info("File watcher stopped")

    def add_watch_path(self, path: str) -> None:
        """添加监听路径"""
        self.config.watch_paths.append(path)
        if self.watcher is not None:
            self.watcher.watch_paths = [Path(p).resolve() for p in self.config.watch_paths]
            logger.info(f"Added watch path: {path}")

    def remove_watch_path(self, path: str) -> None:
        """移除监听路径"""
        if path in self.config.watch_paths:
            self.config.watch_paths.remove(path)
            if self.watcher is not None:
                self.watcher.watch_paths = [Path(p).resolve() for p in self.config.watch_paths]
                logger.info(f"Removed watch path: {path}")

    # ------------------------------------------------------------------
    # 变更处理
    # ------------------------------------------------------------------

    def _handle_watch_event(self, event: WatchEvent) -> None:
        """处理文件监听事件"""
        try:
            # 跳过目录事件
            if event.is_directory:
                return

            # 将 WatchEvent 转换为 ChangeRecord
            record = ChangeRecord(
                path=event.path,
                change_type=event.change_type.value,
                old_path=event.old_path,
                is_directory=event.is_directory,
                size=event.size,
                checksum=event.checksum,
            )

            # 归因
            attribution = self.attributor.attribute_change(record)

            # 如果有归属的会话，更新会话活跃时间
            if attribution.success and attribution.session_id:
                self.update_session_activity(attribution.session_id, event.path)

            # 如果是文本文件且修改类型，生成 diff
            diff_entry: Optional[DiffEntry] = None
            if event.change_type == ChangeType.modified and not record.is_directory:
                diff_entry = self.diff_tracker.track_change(
                    path=event.path,
                    change_type=record.change_type,
                    agent_name=attribution.agent_name or "",
                    session_id=attribution.session_id or "",
                )

            # 创建 FileChange 记录
            file_change = FileChange.from_change_record(
                record, diff=diff_entry.diff if diff_entry else ""
            )
            file_change.agent_name = attribution.agent_name or ""
            file_change.session_id = attribution.session_id or ""
            file_change.team_name = self.config.team_name

            # 添加到历史
            with self._lock:
                self.change_history.append(file_change)
                # 限制历史记录长度
                if len(self.change_history) > self.config.max_history:
                    self.change_history = self.change_history[-self.config.max_history :]

            # 记录日志
            if attribution.success:
                logger.info(
                    f"File change attributed: {event.path} -> {attribution.agent_name} "
                    f"(session: {attribution.session_id})"
                )
            else:
                logger.info(f"File change not attributed: {event.path}")

        except Exception as e:
            logger.error(f"Error handling watch event for {event.path}: {e}")

    def track_manual_change(
        self,
        file_path: str,
        change_type: str = "modified",
        agent_name: str = "",
        session_id: str = "",
    ) -> FileChange:
        """手动追踪文件变更（当监听器无法工作时使用）"""
        record = ChangeRecord(
            path=file_path,
            change_type=change_type,
        )

        # 如果有提供归因信息，直接使用
        if agent_name and session_id:
            record.agent_name = agent_name
            record.session_id = session_id
            record.team_name = self.config.team_name
        else:
            # 否则尝试归因
            attribution = self.attributor.attribute_change(record)
            if attribution.success:
                record.agent_name = attribution.agent_name or ""
                record.session_id = attribution.session_id or ""

        # 生成 diff
        diff_entry: Optional[DiffEntry] = None
        if change_type == "modified":
            diff_entry = self.diff_tracker.track_change(
                path=file_path,
                change_type=change_type,
                agent_name=record.agent_name,
                session_id=record.session_id,
            )

        # 创建 FileChange
        file_change = FileChange.from_change_record(
            record, diff=diff_entry.diff if diff_entry else ""
        )

        # 添加到历史
        with self._lock:
            self.change_history.append(file_change)
            if len(self.change_history) > self.config.max_history:
                self.change_history = self.change_history[-self.config.max_history :]

        return file_change

    # ------------------------------------------------------------------
    # 查询接口
    # ------------------------------------------------------------------

    def get_changes(
        self,
        file_path: Optional[str] = None,
        agent_name: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[FileChange]:
        """获取变更记录"""
        with self._lock:
            filtered = self.change_history

            if file_path:
                filtered = [c for c in filtered if c.file_path == file_path]
            if agent_name:
                filtered = [c for c in filtered if c.agent_name == agent_name]
            if session_id:
                filtered = [c for c in filtered if c.session_id == session_id]

            return filtered[-limit:]

    def get_diff(self, file_path: str, limit: int = 10) -> List[str]:
        """获取文件的 diff 历史"""
        diffs = self.diff_tracker.get_file_diffs(file_path, limit=limit)
        return [d.diff for d in diffs if d.diff]

    def get_agent_changes(self, agent_name: str, limit: int = 50) -> List[FileChange]:
        """获取指定 Agent 的变更记录"""
        return self.get_changes(agent_name=agent_name, limit=limit)

    def get_session_changes(self, session_id: str, limit: int = 50) -> List[FileChange]:
        """获取指定会话的变更记录"""
        return self.get_changes(session_id=session_id, limit=limit)

    def get_recent_changes(self, limit: int = 20) -> List[FileChange]:
        """获取最近变更"""
        return self.get_changes(limit=limit)

    def get_change_summary(self) -> Dict[str, Any]:
        """获取变更摘要"""
        with self._lock:
            total_changes = len(self.change_history)
            agents = set(c.agent_name for c in self.change_history if c.agent_name)
            sessions = set(c.session_id for c in self.change_history if c.session_id)
            files = set(c.file_path for c in self.change_history)

            # 按类型统计
            by_type = {}
            for change in self.change_history:
                by_type[change.change_type] = by_type.get(change.change_type, 0) + 1

            # 按 Agent 统计
            by_agent = {}
            for change in self.change_history:
                if change.agent_name:
                    by_agent[change.agent_name] = by_agent.get(change.agent_name, 0) + 1

            return {
                "total_changes": total_changes,
                "unique_agents": len(agents),
                "unique_sessions": len(sessions),
                "unique_files": len(files),
                "by_type": by_type,
                "by_agent": by_agent,
                "recent_changes": [c.to_dict() for c in self.change_history[-10:]],
            }

    # ------------------------------------------------------------------
    # 清理
    # ------------------------------------------------------------------

    def clear_history(self) -> None:
        """清理历史记录"""
        with self._lock:
            self.change_history.clear()
            logger.info("Cleared change history")

    def cleanup_old_sessions(self, max_age_hours: int = 24) -> None:
        """清理旧会话"""
        cutoff = time.time() - (max_age_hours * 3600)
        to_remove = []
        with self._lock:
            for session_id, session in self.active_sessions.items():
                session_time = datetime.fromisoformat(session.last_activity_at).timestamp()
                if session_time < cutoff:
                    to_remove.append(session_id)

        for session_id in to_remove:
            # unregister_session acquires its own lock
            with self._lock:
                if session_id in self.active_sessions:
                    self.attributor.unregister_session(session_id)
                    del self.active_sessions[session_id]
                    logger.info(f"Unregistered session {session_id}")

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old sessions")

    # ------------------------------------------------------------------
    # 上下文管理器支持
    # ------------------------------------------------------------------

    def __enter__(self) -> "FileChangeTracker":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()


# 全局默认追踪器实例
_default_tracker: Optional[FileChangeTracker] = None


def get_file_change_tracker(config: Optional[FileChangeTrackerConfig] = None) -> FileChangeTracker:
    """获取文件变更追踪器实例（单例模式）"""
    global _default_tracker
    if _default_tracker is None:
        _default_tracker = FileChangeTracker(config)
    return _default_tracker


def track_file_change(file_path: str, agent_name: str = "", session_id: str = "") -> FileChange:
    """便捷函数：追踪文件变更"""
    tracker = get_file_change_tracker()
    return tracker.track_manual_change(
        file_path=file_path,
        agent_name=agent_name,
        session_id=session_id,
    )


def get_recent_file_changes(limit: int = 20) -> List[Dict[str, Any]]:
    """便捷函数：获取最近文件变更"""
    tracker = get_file_change_tracker()
    changes = tracker.get_recent_changes(limit=limit)
    return [c.to_dict() for c in changes]
