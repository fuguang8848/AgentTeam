"""
AgentTeam Core SDK - 真正的多 Agent 协作框架

核心模块，提供：
- CTTeam: 团队容器，管理多个 CTAgent
- CTAgent: 运行在 OpenClaw Session 中的智能体
- CTInbox: Agent 之间的消息队列
- CTTask: 任务跟踪
"""

from __future__ import annotations

# Core types
from .types import (
    AgentState,
    TaskState,
    MessageType,
    AgentStatus,
    TaskStatus,
)

# Core classes
from .agent import CTAgent, Agent
from .task import CTTask, Task
from .message import CTMessage, CTInbox, Message, Inbox
from .team import CTTeam, Team

# Factory functions
from pathlib import Path
from typing import Optional


def create_team(name: str, storage_path: Optional[Path] = None) -> CTTeam:
    """创建新团队"""
    return CTTeam(name, storage_path=storage_path)


def get_team(name: str) -> Optional[CTTeam]:
    """获取已存在的团队"""
    storage_path = Path(f"~/.agentteam/teams/{name}").expanduser()
    if storage_path.exists():
        return CTTeam(name, storage_path=storage_path)
    return None


def list_teams() -> list[str]:
    """列出所有团队"""
    teams_dir = Path("~/.agentteam/teams").expanduser()
    if teams_dir.exists():
        return [d.name for d in teams_dir.iterdir() if d.is_dir()]
    return []


__all__ = [
    # Types
    "AgentState",
    "TaskState",
    "MessageType",
    "AgentStatus",
    "TaskStatus",
    # Classes
    "CTAgent",
    "CTTask",
    "CTMessage",
    "CTInbox",
    "CTTeam",
    # Backwards compatibility
    "Agent",
    "Task",
    "Message",
    "Inbox",
    "Team",
    # Factory functions
    "create_team",
    "get_team",
    "list_teams",
]
