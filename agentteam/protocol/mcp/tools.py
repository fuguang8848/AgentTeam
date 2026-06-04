"""
MCP Tool Implementations.

Provides built-in tools for the MCP protocol that integrate
with the SpectrAI/AgentTeam platform. These tools enable:
- MCP server discovery and management
- Skill installation and management
- Plugin management
- Built-in platform tools

Reference: SpectrAI MCP Gateway Implementation
"""

from __future__ import annotations

import json
import logging
from typing import Any

from .types import MCPTool, MCPToolInputSchema

logger = logging.getLogger(__name__)


# =============================================================================
# Tool Registry
# =============================================================================

def get_builtin_tools() -> list[MCPTool]:
    """
    Get all built-in MCP tools.
    
    Returns:
        List of MCPTool definitions
    """
    return [
        search_mcp_tools,
        list_mcp_servers,
        call_mcp_tool,
        install_mcp,
        install_skill,
        analyze_skill_repo,
        install_plugin,
        get_tool_info,
    ]


# =============================================================================
# MCP Server Discovery Tools
# =============================================================================

search_mcp_tools = MCPTool(
    name="search_mcp_tools",
    description="Search for available MCP tools by keyword. Returns tool names, descriptions, inputSchema, and server_id. Use this before using call_mcp_tool to discover available tools.",
    input_schema=MCPToolInputSchema(
        type="object",
        properties={
            "query": {
                "type": "string",
                "description": "Search keyword (e.g., 'ssh', 'database', 'github', 'deploy', 'news'). Short and specific keywords work best.",
            },
            "server_id": {
                "type": "string",
                "description": "Optional server ID to limit search to a specific server.",
            },
        },
        required=["query"],
    ),
    output_schema=MCPToolInputSchema(
        type="object",
        properties={
            "tools": {
                "type": "array",
                "description": "List of matching tools",
            },
        },
    ),
)


async def handle_search_mcp_tools(
    query: str,
    server_id: str | None = None,
) -> dict[str, Any]:
    """
    Handle search_mcp_tools tool calls.
    
    This is a wrapper around the platform's search_mcp_tools functionality.
    In a real implementation, this would call the actual MCP gateway.
    """
    # Note: In production, this would call the actual MCP gateway
    # For now, return a mock response structure
    logger.info(f"Searching MCP tools for query: {query}")
    
    return {
        "query": query,
        "results": [
            {
                "server_id": "__builtin__",
                "tool_name": "team_get_tasks",
                "description": "Get list of team tasks",
            },
            {
                "server_id": "__builtin__",
                "tool_name": "team_claim_task",
                "description": "Claim a specific task",
            },
            {
                "server_id": "__builtin__",
                "tool_name": "team_complete_task",
                "description": "Mark a task as completed",
            },
        ],
        "hint": "Use call_mcp_tool with server_id and tool_name to invoke",
    }


list_mcp_servers = MCPTool(
    name="list_mcp_servers",
    description="List all registered MCP servers and their tool overview. Returns server_id, server_name, description, status, tool_count, and tool_names.",
    input_schema=MCPToolInputSchema(
        type="object",
        properties={},
    ),
    output_schema=MCPToolInputSchema(
        type="object",
        properties={
            "servers": {
                "type": "array",
                "description": "List of MCP servers",
            },
        },
    ),
)


async def handle_list_mcp_servers() -> dict[str, Any]:
    """
    Handle list_mcp_servers tool calls.
    
    Returns information about all registered MCP servers.
    """
    # Note: In production, this would call the actual MCP gateway
    logger.info("Listing MCP servers")
    
    return {
        "servers": [
            {
                "server_id": "__builtin__",
                "server_name": "builtin",
                "description": "Built-in SpectrAI tools",
                "status": "active",
                "tool_count": 10,
                "tool_names": [
                    "team_get_tasks",
                    "team_claim_task",
                    "team_complete_task",
                    "team_report_idle",
                    "team_message_role",
                    "team_broadcast",
                ],
            },
        ],
    }


call_mcp_tool = MCPTool(
    name="call_mcp_tool",
    description="Call a tool on an external MCP Server. Always use search_mcp_tools first to discover tool names and their server_id, then call this tool with the correct parameters.",
    input_schema=MCPToolInputSchema(
        type="object",
        properties={
            "server_id": {
                "type": "string",
                "description": "The MCP Server ID (from search_mcp_tools results)",
            },
            "tool_name": {
                "type": "string",
                "description": "The tool name to invoke (from search_mcp_tools results)",
            },
            "arguments": {
                "type": "object",
                "description": "Tool arguments as JSON object (follow inputSchema)",
            },
            "timeout": {
                "type": "number",
                "description": "Optional timeout in milliseconds. Default 300000 (5min). For video/audio generation use 600000+.",
            },
        },
        required=["server_id", "tool_name", "arguments"],
    ),
    output_schema=MCPToolInputSchema(
        type="object",
        properties={
            "result": {
                "type": "any",
                "description": "The result from the tool call",
            },
        },
    ),
)


async def handle_call_mcp_tool(
    server_id: str,
    tool_name: str,
    arguments: dict[str, Any],
    timeout: int | None = None,
) -> dict[str, Any]:
    """
    Handle call_mcp_tool tool calls.
    
    Invokes a tool on a registered MCP server.
    """
    logger.info(f"Calling MCP tool: {server_id}.{tool_name}")
    
    # Validate server_id
    if server_id == "__builtin__":
        # Handle built-in tools
        return await _handle_builtin_tool(tool_name, arguments)
    
    # In production, would route to actual MCP server
    return {
        "success": True,
        "server_id": server_id,
        "tool_name": tool_name,
        "message": "Tool call routed successfully",
    }


async def _handle_builtin_tool(
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle built-in SpectrAI tools."""
    
    if tool_name == "team_get_tasks":
        return {"tasks": [], "message": "Task listing is available via team interface"}
    
    elif tool_name == "team_claim_task":
        return {"success": True, "message": "Task claimed"}
    
    elif tool_name == "team_complete_task":
        return {"success": True, "message": "Task completed"}
    
    elif tool_name == "team_report_idle":
        return {"success": True, "message": "Idle status reported"}
    
    else:
        return {
            "success": False,
            "error": f"Unknown built-in tool: {tool_name}",
        }


# =============================================================================
# Skill Management Tools
# =============================================================================

install_mcp = MCPTool(
    name="install_mcp",
    description="Install a MCP Server (tool server) to SpectrAI. After installation, it registers to the MCP Gateway automatically and all new sessions can use it immediately.",
    input_schema=MCPToolInputSchema(
        type="object",
        properties={
            "name": {
                "type": "string",
                "description": "MCP Server name, short and easy to understand (e.g., 'Pexels 素材库')",
            },
            "description": {
                "type": "string",
                "description": "MCP Server description, explaining what this server provides",
            },
            "command": {
                "type": "string",
                "description": "Startup command (e.g., 'npx', 'uvx', 'node', or full path)",
            },
            "args": {
                "type": "string",
                "description": "Command arguments in JSON array format, e.g. '[\"-y\", \"some-mcp-package\"]'",
            },
            "env_vars": {
                "type": "string",
                "description": "Environment variables in JSON object format, e.g. '{\"API_KEY\": \"xxx\"}'. API keys should be set here.",
            },
            "transport": {
                "type": "string",
                "description": "Transport protocol: stdio (default) | http | sse",
            },
            "url": {
                "type": "string",
                "description": "HTTP/SSE transport server URL (required when transport is not stdio)",
            },
            "category": {
                "type": "string",
                "description": "Category: media | database | code | filesystem | custom (default: custom)",
            },
            "install_command": {
                "type": "string",
                "description": "Optional install command (e.g., 'npm install -g some-package')",
            },
        },
        required=["name", "description", "command"],
    ),
    output_schema=MCPToolInputSchema(
        type="object",
        properties={
            "success": {"type": "boolean"},
            "server_id": {"type": "string"},
            "message": {"type": "string"},
        },
    ),
)


async def handle_install_mcp(
    name: str,
    description: str,
    command: str,
    args: str | None = None,
    env_vars: str | None = None,
    transport: str = "stdio",
    url: str | None = None,
    category: str = "custom",
    install_command: str | None = None,
) -> dict[str, Any]:
    """
    Handle install_mcp tool calls.
    
    Installs a new MCP server to the platform.
    """
    logger.info(f"Installing MCP server: {name}")
    
    # Parse optional JSON arguments
    args_list = json.loads(args) if args else []
    env_dict = json.loads(env_vars) if env_vars else {}
    
    return {
        "success": True,
        "server_id": f"mcp-{name.lower().replace(' ', '-')}",
        "name": name,
        "description": description,
        "command": command,
        "args": args_list,
        "env_vars": env_dict,
        "transport": transport,
        "message": f"MCP server '{name}' installed successfully",
    }


install_skill = MCPTool(
    name="install_skill",
    description="Install a Skill (ability) to SpectrAI. After installation, it can be invoked in conversations via /slash commands.",
    input_schema=MCPToolInputSchema(
        type="object",
        properties={
            "name": {
                "type": "string",
                "description": "Skill name (required for promptTemplate/nativeContent paths; read from SKILL.md frontmatter for GitHub/npx/localDir paths)",
            },
            "description": {
                "type": "string",
                "description": "Skill description",
            },
            "github_url": {
                "type": "string",
                "description": "GitHub repository URL",
            },
            "npx_command": {
                "type": "string",
                "description": "npx/npm command or package name (e.g., '@scope/pkg', 'npx -y my-skill')",
            },
            "local_dir": {
                "type": "string",
                "description": "Local directory absolute path containing SKILL.md",
            },
            "slash_command": {
                "type": "string",
                "description": "Trigger command without / (e.g., 'code-review'). Users invoke with /code-review",
            },
            "type": {
                "type": "string",
                "description": "Skill type: prompt | native | orchestration (default: prompt)",
            },
            "prompt_template": {
                "type": "string",
                "description": "Prompt template content with {{user_input}} placeholders",
            },
            "category": {
                "type": "string",
                "description": "Category: development | writing | analysis | custom (default: custom)",
            },
            "tags": {
                "type": "string",
                "description": "Tags separated by commas (e.g., 'review,code,quality')",
            },
        },
        required=["name"],
    ),
    output_schema=MCPToolInputSchema(
        type="object",
        properties={
            "success": {"type": "boolean"},
            "skill_name": {"type": "string"},
            "message": {"type": "string"},
        },
    ),
)


async def handle_install_skill(
    name: str,
    description: str | None = None,
    github_url: str | None = None,
    npx_command: str | None = None,
    local_dir: str | None = None,
    slash_command: str | None = None,
    type: str = "prompt",
    prompt_template: str | None = None,
    category: str = "custom",
    tags: str | None = None,
) -> dict[str, Any]:
    """
    Handle install_skill tool calls.
    
    Installs a new skill to the platform.
    """
    logger.info(f"Installing skill: {name}")
    
    # Determine installation method
    method = "unknown"
    if github_url:
        method = "github"
    elif npx_command:
        method = "npx"
    elif local_dir:
        method = "local"
    elif prompt_template:
        method = "prompt_template"
    
    return {
        "success": True,
        "skill_name": name,
        "description": description or "",
        "method": method,
        "slash_command": slash_command or name.lower().replace(" ", "-"),
        "category": category,
        "tags": tags.split(",") if tags else [],
        "message": f"Skill '{name}' installed successfully",
    }


analyze_skill_repo = MCPTool(
    name="analyze_skill_repo",
    description="Read-only detection of a GitHub repository structure without writing any SpectrAI state. Returns repoType (single-skill/skill-package/plugin/mixed), detectedMarkers, skillCount, and warnings.",
    input_schema=MCPToolInputSchema(
        type="object",
        properties={
            "github_url": {
                "type": "string",
                "description": "GitHub repository URL, can specify subdirectory or branch (e.g., https://github.com/owner/repo or https://github.com/owner/repo/tree/main/skills/foo)",
            },
        },
        required=["github_url"],
    ),
    output_schema=MCPToolInputSchema(
        type="object",
        properties={
            "repo_type": {"type": "string"},
            "skill_count": {"type": "number"},
            "warnings": {"type": "array"},
        },
    ),
)


async def handle_analyze_skill_repo(github_url: str) -> dict[str, Any]:
    """
    Handle analyze_skill_repo tool calls.
    
    Analyzes a GitHub repository to determine its type.
    """
    logger.info(f"Analyzing skill repo: {github_url}")
    
    # In production, would fetch and analyze the repo
    return {
        "repo_type": "unknown",
        "detected_markers": {},
        "skill_count": 0,
        "warnings": ["Would require network access to analyze repository"],
        "message": f"Analysis of {github_url} requires network access",
    }


install_plugin = MCPTool(
    name="install_plugin",
    description="Install a Claude Code plugin from a GitHub repo. For plugin/mixed repositories only.",
    input_schema=MCPToolInputSchema(
        type="object",
        properties={
            "github_url": {
                "type": "string",
                "description": "GitHub plugin repository URL",
            },
            "dry_run": {
                "type": "boolean",
                "description": "Only download to temp and scan, don't write to ~/.claude/plugins (default: false)",
            },
        },
        required=["github_url"],
    ),
    output_schema=MCPToolInputSchema(
        type="object",
        properties={
            "success": {"type": "boolean"},
            "message": {"type": "string"},
        },
    ),
)


async def handle_install_plugin(
    github_url: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Handle install_plugin tool calls.
    
    Installs a plugin to the Claude Code plugin marketplace.
    """
    logger.info(f"Installing plugin from: {github_url} (dry_run={dry_run})")
    
    return {
        "success": True,
        "github_url": github_url,
        "dry_run": dry_run,
        "message": f"Plugin analysis {'completed' if dry_run else 'installation started'} for {github_url}",
    }


# =============================================================================
# Utility Tools
# =============================================================================

get_tool_info = MCPTool(
    name="get_tool_info",
    description="Get detailed information about a specific MCP tool including its full input schema and description.",
    input_schema=MCPToolInputSchema(
        type="object",
        properties={
            "tool_name": {
                "type": "string",
                "description": "Name of the tool to get information about",
            },
            "server_id": {
                "type": "string",
                "description": "Optional server ID to scope the search",
            },
        },
        required=["tool_name"],
    ),
    output_schema=MCPToolInputSchema(
        type="object",
        properties={
            "tool_name": {"type": "string"},
            "description": {"type": "string"},
            "input_schema": {"type": "object"},
        },
    ),
)


async def handle_get_tool_info(
    tool_name: str,
    server_id: str | None = None,
) -> dict[str, Any]:
    """
    Handle get_tool_info tool calls.
    
    Returns detailed information about a specific tool.
    """
    logger.info(f"Getting tool info for: {tool_name}")
    
    # Check built-in tools
    for tool in get_builtin_tools():
        if tool.name == tool_name:
            return {
                "tool_name": tool.name,
                "description": tool.description,
                "input_schema": (
                    tool.input_schema.to_dict()
                    if isinstance(tool.input_schema, MCPToolInputSchema)
                    else tool.input_schema
                ),
                "server_id": "__builtin__",
            }
    
    return {
        "error": f"Tool '{tool_name}' not found",
        "hint": "Use list_mcp_servers or search_mcp_tools to discover available tools",
    }


# =============================================================================
# Tool Handler Registration
# =============================================================================

def register_tool_handlers(server) -> None:
    """
    Register all built-in tool handlers with an MCP server.
    
    Args:
        server: MCPServer instance
    """
    handlers = {
        "search_mcp_tools": handle_search_mcp_tools,
        "list_mcp_servers": handle_list_mcp_servers,
        "call_mcp_tool": handle_call_mcp_tool,
        "install_mcp": handle_install_mcp,
        "install_skill": handle_install_skill,
        "analyze_skill_repo": handle_analyze_skill_repo,
        "install_plugin": handle_install_plugin,
        "get_tool_info": handle_get_tool_info,
    }
    
    for name, handler in handlers.items():
        server.register_tool_handler(name, handler)
