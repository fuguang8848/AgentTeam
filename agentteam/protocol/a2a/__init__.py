"""
A2A (Agent-to-Agent) Protocol Implementation for AgentTeam.

This module provides a standardized protocol for inter-agent communication,
enabling agents to discover each other, exchange messages, and coordinate
tasks across different agent frameworks and systems.

Based on the A2A protocol specification for agent interoperability.
"""

from agentteam.protocol.a2a.models import (
    AgentCard,
    AgentProvider,
    AgentCapabilities,
    AgentSkill,
    Task,
    TaskStatus,
    TaskPriority,
    Message,
    MessageType,
    A2ARequest,
    A2AResponse,
    StreamingChunk,
)
from agentteam.protocol.a2a.server import A2AServer
from agentteam.protocol.a2a.client import A2AClient

__all__ = [
    # Models
    "AgentCard",
    "AgentProvider",
    "AgentCapabilities",
    "AgentSkill",
    "Task",
    "TaskStatus",
    "TaskPriority",
    "Message",
    "MessageType",
    "A2ARequest",
    "A2AResponse",
    "StreamingChunk",
    # Server/Client
    "A2AServer",
    "A2AClient",
]
