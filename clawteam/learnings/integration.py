"""
P12 .learnings 自动闭环集成

将 learnings 系统与 ClawTeam Agent 集成：
1. 任务完成后自动捕获经验
2. 周期性晋升检查
3. 上下文注入到新任务
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from pathlib import Path
import logging

from clawteam.learnings.auto_capture import (
    AutoCaptureEngine,
    LearningType,
    ExperienceEntry,
)

logger = logging.getLogger(__name__)


class LearningsIntegrator:
    """
    Learnings 自动闭环集成器

    使用方式：
    1. 在 Agent 初始化时创建实例
    2. 任务完成后调用 capture_task_result()
    3. 新任务开始前调用 inject_context()
    4. 定期调用 check_promotions()
    """

    def __init__(self, learnings_dir: str = None, workspace_dir: str = None):
        learnings_dir = learnings_dir or "~/.openclaw/workspace/ClawTeam-OpenClaw/.learnings"
        workspace_dir = workspace_dir or "~/.openclaw/workspace/ClawTeam-OpenClaw"

        self.learnings_dir = Path(learnings_dir).expanduser()
        self.learnings_dir.mkdir(parents=True, exist_ok=True)

        self.workspace_dir = Path(workspace_dir).expanduser()

        self.engine = AutoCaptureEngine(str(self.learnings_dir))

    def capture_task_result(
        self,
        task_id: str,
        status: str,
        error: Optional[str] = None,
        session_id: str = "",
        user_feedback: Optional[str] = None,
        tools_used: List[str] = None,
        time_saved_minutes: int = 0,
        method: str = "",
    ) -> Optional[str]:
        """捕获任务结果并记录经验

        Args:
            task_id: 任务 ID
            status: 任务状态 (success, failed)
            error: 错误信息（如有）
            session_id: 会话 ID
            user_feedback: 用户反馈
            tools_used: 使用的工具列表
            time_saved_minutes: 节省的时间（分钟）
            method: 使用的方法描述

        Returns:
            经验条目 ID
        """
        task_result = {
            "task_id": task_id,
            "status": status,
            "error": error,
            "session_id": session_id,
            "tools_used": tools_used or [],
            "time_saved_minutes": time_saved_minutes,
            "method": method,
        }

        entry = self.engine.evaluate_task_result(task_result, user_feedback)
        if entry:
            return self.engine.record_experience(entry)

        return None

    def inject_context(self, task_description: str, max_entries: int = 5) -> str:
        """为新任务注入相关经验上下文

        Args:
            task_description: 新任务描述
            max_entries: 最多注入多少条经验

        Returns:
            格式化的经验上下文字符串
        """
        context = self.engine.get_context_for_task(task_description, max_entries)
        return context

    def check_promotions(self) -> List[str]:
        """
        检查需要晋升的经验并自动晋升到文档

        Returns:
            已晋升的经验条目 ID 列表
        """
        promoted = []

        # 检查晋升候选
        candidates = self.engine.check_for_promotion(
            min_occurrences=3,
            min_confidence=0.8
        )

        for entry in candidates:
            # 优先晋升到 AGENTS.md
            target = "AGENTS.md"

            success = self.engine.promote_to_documentation(entry, target)
            if success:
                promoted.append(entry.entry_id)
                logger.info(
                    f"Promoted experience {entry.entry_id} to {target}"
                )

        return promoted

    def get_learning_summary(self, days: int = 7) -> str:
        """获取学习摘要报告"""
        return self.engine.generate_learning_summary(days=days, format="markdown")

    def search_learnings(self, query: str, entry_type: str = None) -> List[Dict[str, Any]]:
        """搜索经验记录"""
        lt = None
        if entry_type:
            try:
                lt = LearningType(entry_type)
            except ValueError:
                pass

        entries = self.engine.search_experiences(query, entry_type=lt)
        return [e.model_dump() for e in entries]

    def get_stats(self) -> Dict[str, Any]:
        """获取经验统计"""
        all_entries = self.engine.list_experiences()
        stats = {
            "total": len(all_entries),
            "by_type": {},
            "unresolved": 0,
            "high_priority": 0,
        }

        for entry in all_entries:
            t = entry.entry_type.value
            stats["by_type"][t] = stats["by_type"].get(t, 0) + 1
            if not entry.resolved:
                stats["unresolved"] += 1
            if entry.priority in ("high", "critical"):
                stats["high_priority"] += 1

        return stats


# 全局单例
_integration_instance: Optional[LearningsIntegrator] = None


def get_integrator() -> LearningsIntegrator:
    """获取全局 LearningsIntegrator 实例"""
    global _integration_instance
    if _integration_instance is None:
        _integration_instance = LearningsIntegrator()
    return _integration_instance
