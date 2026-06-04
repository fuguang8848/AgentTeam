"""
Core Agent Definition for AgentTeam SDK

包含 CTAgent 类的定义。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from .types import AgentState


@dataclass
class CTAgent:
    """
    Team Agent - 运行在 OpenClaw Session 中的智能体
    
    属性:
        name: Agent 名称，必须唯一
        agent_type: Agent 类型，如 "coder", "reviewer", "leader"
        session_key: 关联的 OpenClaw Session key
        state: 当前状态
        team_name: 所属团队名称
        task_id: 当前任务 ID
        created_at: 创建时间戳
        updated_at: 更新时间戳
        metadata: 额外元数据
    """
    
    name: str
    agent_type: str  # "coder", "reviewer", "leader", etc.
    session_key: str
    state: AgentState = AgentState.PENDING
    team_name: str = ""
    task_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "name": self.name,
            "agent_type": self.agent_type,
            "session_key": self.session_key,
            "state": self.state.value,
            "team_name": self.team_name,
            "task_id": self.task_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CTAgent":
        """从字典创建"""
        state = data.get("state", "pending")
        if isinstance(state, str):
            state = AgentState(state)
        return cls(
            name=data["name"],
            agent_type=data["agent_type"],
            session_key=data["session_key"],
            state=state,
            team_name=data.get("team_name", ""),
            task_id=data.get("task_id"),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            metadata=data.get("metadata", {}),
        )
    
    def update_state(self, state: AgentState) -> None:
        """更新状态并记录时间戳"""
        self.state = state
        self.updated_at = time.time()
    
    def assign_task(self, task_id: str) -> None:
        """分配任务"""
        self.task_id = task_id
        self.state = AgentState.RUNNING
        self.updated_at = time.time()
    
    def complete_task(self) -> None:
        """完成任务"""
        self.task_id = None
        self.state = AgentState.COMPLETED
        self.updated_at = time.time()
    
    def fail(self, error: Optional[str] = None) -> None:
        """标记失败"""
        self.state = AgentState.FAILED
        if error:
            self.metadata["error"] = error
        self.updated_at = time.time()
    
    def is_active(self) -> bool:
        """检查是否处于活跃状态"""
        return self.state in (AgentState.RUNNING, AgentState.WAITING)
    
    def is_done(self) -> bool:
        """检查是否已结束"""
        return self.state in (AgentState.COMPLETED, AgentState.FAILED, AgentState.TERMINATED)


# Backwards compatibility alias
Agent = CTAgent
