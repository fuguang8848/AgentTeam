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
    """Message Type - 消息类型枚举"""

    TEXT = "text"
    TASK = "task"
    NOTIFICATION = "notification"
    SYSTEM = "system"
    BROADCAST = "broadcast"
    DIRECT = "direct"

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
