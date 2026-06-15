"""
MCP (Model Context Protocol) Implementation for AgentTeam.

This module provides MCP server implementation following the
Model Context Protocol specification for AI tool/function calling.

Reference: Anthropic MCP Protocol Specification
"""

from agentteam.protocol.mcp.types import (
    MCPTool,
    MCPToolInputSchema,
    MCPToolOutputSchema,
    MCPResource,
    MCPResourceTemplate,
    MCPrompt,
    MCPRequest,
    MCPResponse,
    MCPError,
    MCPJSONRPCError,
    MCPTransport,
    MCPStdioTransport,
    MCPSSETransport,
)
from agentteam.protocol.mcp.server import MCPServer
from agentteam.protocol.mcp.tools import (
    # Built-in tools
    search_mcp_tools,
    list_mcp_servers,
    call_mcp_tool,
    install_mcp,
    install_skill,
    analyze_skill_repo,
    install_plugin,
    get_builtin_tools,
)

__all__ = [
    # Types
    "MCPTool",
    "MCPToolInputSchema",
    "MCPToolOutputSchema",
    "MCPResource",
    "MCPResourceTemplate",
    "MCPrompt",
    "MCPRequest",
    "MCPResponse",
    "MCPError",
    "MCPJSONRPCError",
    "MCPTransport",
    "MCPStdioTransport",
    "MCPSSETransport",
    # Server
    "MCPServer",
    # Tools
    "search_mcp_tools",
    "list_mcp_servers",
    "call_mcp_tool",
    "install_mcp",
    "install_skill",
    "analyze_skill_repo",
    "install_plugin",
    "get_builtin_tools",
]
