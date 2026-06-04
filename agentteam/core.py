"""
AgentTeam Core - 向后兼容模块

此模块已被拆分为 agentteam.core 包。
请使用以下方式导入：
    from agentteam.core import CTTeam, CTAgent, CTTask
"""

# Re-export all core components from the new module structure
from agentteam.core import (
    # Types
    AgentState,
    TaskState,
    MessageType,
    AgentStatus,
    TaskStatus,
    # Classes
    CTAgent,
    CTTask,
    CTMessage,
    CTInbox,
    CTTeam,
    # Backwards compatibility aliases
    Agent,
    Task,
    Message,
    Inbox,
    Team,
    # Factory functions
    create_team,
    get_team,
)

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
    # Backwards compatibility aliases
    "Agent",
    "Task",
    "Message",
    "Inbox",
    "Team",
    # Factory functions
    "create_team",
    "get_team",
]
