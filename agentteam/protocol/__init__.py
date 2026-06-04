"""
AgentTeam Protocol Layer.

This module provides standardized protocol implementations for
agent-to-agent communication and tool calling:

- A2A (Agent-to-Agent): Protocol for inter-agent communication,
  task coordination, and discovery
- MCP (Model Context Protocol): Protocol for AI tool/function calling

The protocol layer enables AgentTeam to integrate with different
agent frameworks and AI systems in a portable, standardized way.
"""

from agentteam.protocol import a2a
from agentteam.protocol import mcp

__all__ = [
    "a2a",
    "mcp",
]

# Version info
__version__ = "1.0.0"
