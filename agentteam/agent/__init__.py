"""
Agent Module for AgentTeam SDK

提供 Agent 的抽象基类、运行时环境和通信协议。
"""

from __future__ import annotations

# Base classes
from .base import (
    AgentConfig,
    BaseAgent,
    SyncAgent,
)

# Protocol
from .protocol import (
    ProtocolVersion,
    MessagePriority,
    AgentMessage,
    ctmessage_to_agentmessage,
    agentmessage_to_ctmessage,
)

# Runtime
from .runtime import (
    AgentRuntime,
    AsyncQueue,
    get_runtime,
    init_runtime,
    shutdown_runtime,
)

__all__ = [
    # Base
    "AgentConfig",
    "BaseAgent",
    "SyncAgent",
    # Protocol
    "ProtocolVersion",
    "MessagePriority",
    "AgentMessage",
    "ctmessage_to_agentmessage",
    "agentmessage_to_ctmessage",
    # Runtime
    "AgentRuntime",
    "AsyncQueue",
    "get_runtime",
    "init_runtime",
    "shutdown_runtime",
]
