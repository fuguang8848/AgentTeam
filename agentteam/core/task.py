"""
Core Task Definition for AgentTeam SDK

包含 CTTask 类的定义。
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from .types import TaskState


@dataclass
class CTTask:
    """
    Team Task - 团队任务

    属性:
        id: 任务唯一 ID
        title: 任务标题
        description: 任务描述
        assignee: 任务分配给的 Agent 名称
        state: 当前状态
        priority: 优先级 (0-9)
        created_at: 创建时间戳
        updated_at: 更新时间戳
        completed_at: 完成时间戳
        result: 任务结果
        error: 错误信息
    """

    id: str
    title: str
    description: str
    assignee: Optional[str] = None
    state: TaskState = TaskState.PENDING
    priority: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    result: Optional[str] = None
    error: Optional[str] = None

    @classmethod
    def create(
        cls,
        title: str,
        description: str = "",
        assignee: Optional[str] = None,
        priority: int = 0,
    ) -> "CTTask":
        """
        创建新任务的工厂方法
        """
        return cls(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            assignee=assignee,
            priority=priority,
        )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "assignee": self.assignee,
            "state": self.state.value,
            "priority": self.priority,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CTTask":
        """从字典创建"""
        state = data.get("state", "pending")
        if isinstance(state, str):
            state = TaskState(state)
        return cls(
            id=data["id"],
            title=data["title"],
            description=data["description"],
            assignee=data.get("assignee"),
            state=state,
            priority=data.get("priority", 0),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            completed_at=data.get("completed_at"),
            result=data.get("result"),
            error=data.get("error"),
        )

    def assign_to(self, agent_name: str) -> None:
        """分配给 Agent"""
        self.assignee = agent_name
        self.state = TaskState.IN_PROGRESS
        self.updated_at = time.time()

    def complete(self, result: Optional[str] = None) -> None:
        """完成任务"""
        self.state = TaskState.COMPLETED
        self.completed_at = time.time()
        self.updated_at = time.time()
        if result:
            self.result = result

    def fail(self, error: str) -> None:
        """标记失败"""
        self.state = TaskState.BLOCKED
        self.error = error
        self.updated_at = time.time()

    def cancel(self) -> None:
        """取消任务"""
        self.state = TaskState.CANCELLED
        self.updated_at = time.time()

    def is_active(self) -> bool:
        """检查是否处于活跃状态"""
        return self.state in (TaskState.PENDING, TaskState.IN_PROGRESS)

    def is_done(self) -> bool:
        """检查是否已结束"""
        return self.state in (TaskState.COMPLETED, TaskState.BLOCKED, TaskState.CANCELLED)


# Backwards compatibility alias
Task = CTTask
