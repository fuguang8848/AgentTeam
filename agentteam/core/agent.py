"""
Core Agent Definition for AgentTeam SDK

包含 CTAgent 类的定义。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional, Dict, List

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


@dataclass
class AgentHierarchy:
    """
    Agent 层级关系 - 建模 agent 之间的层级结构

    属性:
        root: 根节点 agent 名称（顶级 leader）
        parent_map: 子 agent 到父 agent 的映射 (child_name -> parent_name)
        children_map: 父 agent 到子 agents 的映射 (parent_name -> List[child_name])
        level_map: agent 到层级的映射 (agent_name -> level), level 0 为根
    """

    root: Optional[str] = None
    parent_map: Dict[str, str] = field(default_factory=dict)
    children_map: Dict[str, List[str]] = field(default_factory=dict)
    level_map: Dict[str, int] = field(default_factory=dict)

    def add_node(self, agent_name: str, parent_name: Optional[str] = None) -> None:
        """添加节点到层级结构"""
        if parent_name is None:
            # 根节点
            if self.root is None:
                self.root = agent_name
            self.level_map[agent_name] = 0
        else:
            self.parent_map[agent_name] = parent_name
            if parent_name not in self.children_map:
                self.children_map[parent_name] = []
            self.children_map[parent_name].append(agent_name)
            # 计算层级
            self.level_map[agent_name] = self.level_map.get(parent_name, 0) + 1

    def get_parent(self, agent_name: str) -> Optional[str]:
        """获取父节点"""
        return self.parent_map.get(agent_name)

    def get_children(self, agent_name: str) -> List[str]:
        """获取子节点"""
        return self.children_map.get(agent_name, [])

    def get_siblings(self, agent_name: str) -> List[str]:
        """获取同级节点（兄弟节点）"""
        parent = self.get_parent(agent_name)
        if parent is None:
            return []
        siblings = self.get_children(parent)
        return [s for s in siblings if s != agent_name]

    def get_ancestors(self, agent_name: str) -> List[str]:
        """获取所有祖先节点（从父到根）"""
        ancestors = []
        current = agent_name
        while True:
            parent = self.get_parent(current)
            if parent is None:
                break
            ancestors.append(parent)
            current = parent
        return ancestors

    def get_descendants(self, agent_name: str) -> List[str]:
        """获取所有后代节点"""
        descendants = []
        stack = self.get_children(agent_name)
        while stack:
            child = stack.pop()
            descendants.append(child)
            stack.extend(self.get_children(child))
        return descendants

    def get_level(self, agent_name: str) -> int:
        """获取节点层级"""
        return self.level_map.get(agent_name, 0)

    def is_root(self, agent_name: str) -> bool:
        """是否为根节点"""
        return self.root == agent_name

    def is_leaf(self, agent_name: str) -> bool:
        """是否为叶子节点"""
        return agent_name not in self.children_map

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "root": self.root,
            "parent_map": self.parent_map,
            "children_map": self.children_map,
            "level_map": self.level_map,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentHierarchy":
        """从字典创建"""
        return cls(
            root=data.get("root"),
            parent_map=data.get("parent_map", {}),
            children_map=data.get("children_map", {}),
            level_map=data.get("level_map", {}),
        )


# Backwards compatibility alias
Agent = CTAgent
