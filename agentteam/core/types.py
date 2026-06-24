"""
Core Type Definitions for AgentTeam SDK

包含所有核心枚举和类型定义。
"""

from __future__ import annotations

from enum import Enum
from typing import Optional


class AgentState(Enum):
    """Agent State - Agent 的状态枚举"""

    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"
    TERMINATED = "terminated"

    @classmethod
    def from_string(cls, value: str) -> "AgentState":
        """从字符串创建状态"""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.PENDING


class TaskState(Enum):
    """Task State - Task 的状态枚举"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"

    @classmethod
    def from_string(cls, value: str) -> "TaskState":
        """从字符串创建状态"""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.PENDING


class MessageType(Enum):
    """Message Type - 消息类型枚举

    Extended with Socratic questioning, blind spot reporting, and rule genealogy
    for deeper philosophical collaboration (Plato's Cave, Socratic Elenchus, Nietzschean Genealogy).
    """

    TEXT = "text"
    TASK = "task"
    NOTIFICATION = "notification"
    SYSTEM = "system"
    BROADCAST = "broadcast"
    DIRECT = "direct"
    # ── 苏格拉底产婆术 (Socratic Elenchus) ──────────────────────────
    SOCRATIC_QUESTION = "socratic_question"  # 诘问：质疑对方论点的漏洞
    # ── 柏拉图洞穴 allegory (Plato's Cave Allegory) ─────────────────
    BLIND_SPOT_REPORT = "blind_spot_report"   # 全局视角汇报：汇报执行结果的"盲区"
    # ── 尼采系谱学 (Nietzschean Genealogy) ─────────────────────────
    GENEALOGY_TRACE = "genealogy_trace"       # 安全规则来源追踪：何时创建、何人创建、何原因

    @classmethod
    def from_string(cls, value: str) -> "MessageType":
        """从字符串创建消息类型"""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.TEXT


# Re-export aliases for backwards compatibility
AgentStatus = AgentState
TaskStatus = TaskState
