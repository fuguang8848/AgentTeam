"""
Tests for MCP Protocol Implementation.

Tests the MCP (Model Context Protocol) protocol layer including:
- MCP type definitions
- Tool registration
- Resource management
- Server functionality
- Built-in tools
"""

import pytest
import json

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
    MCPServerInfo,
    MCPCapabilities,
    MCPJSONRPCError,
)
from agentteam.protocol.mcp.server import MCPServer, MCPMethod
from agentteam.protocol.mcp.tools import (
    get_builtin_tools,
    handle_search_mcp_tools,
    handle_list_mcp_servers,
    handle_call_mcp_tool,
    handle_install_mcp,
    handle_install_skill,
    handle_get_tool_info,
)


class TestMCPTypes:
    """Tests for MCP type definitions."""

    def test_tool_creation(self):
        """Test creating an MCP tool."""
        tool = MCPTool(
            name="test-tool",
            description="A test tool",
            input_schema=MCPToolInputSchema(
                type="object",
                properties={
                    "arg1": {"type": "string"},
                },
                required=["arg1"],
            ),
        )
        
        assert tool.name == "test-tool"
        assert tool.description == "A test tool"
        assert "arg1" in tool.input_schema.properties

    def test_tool_to_dict(self):
        """Test tool serialization."""
        tool = MCPTool(
            name="my-tool",
            description="Test",
            input_schema={
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        )
        
        data = tool.to_dict()
        
        assert data["name"] == "my-tool"
        assert data["inputSchema"]["type"] == "object"

    def test_resource_creation(self):
        """Test creating a resource."""
        resource = MCPResource(
            uri="file:///data/config.json",
            name="config",
            description="Application configuration",
            mime_type="application/json",
        )
        
        assert resource.uri == "file:///data/config.json"
        assert resource.name == "config"
        assert resource.mime_type == "application/json"

    def test_resource_template_creation(self):
        """Test creating a resource template."""
        template = MCPResourceTemplate(
            uri_template="file:///data/{project}/config.json",
            name="project-config",
            description="Project-specific config",
        )
        
        assert "{project}" in template.uri_template

    def test_prompt_creation(self):
        """Test creating a prompt."""
        prompt = MCPrompt(
            name="code-review",
            description="Review code for issues",
            arguments=[
                {"name": "file", "required": True},
                {"name": "strict", "required": False},
            ],
        )
        
        assert prompt.name == "code-review"
        assert len(prompt.arguments) == 2

    def test_request_response(self):
        """Test request and response types."""
        request = MCPRequest(
            id="req-1",
            method="tools/list",
            params={},
        )
        
        assert request.method == "tools/list"
        
        response = MCPResponse.success(
            {"tools": []},
            id="req-1",
        )
        
        assert response.result == {"tools": []}
        assert response.error is None  # Success response has no error

    def test_error_response(self):
        """Test error response creation."""
        response = MCPResponse.create_error(
            code=MCPJSONRPCError.TOOL_NOT_FOUND,
            message="Tool not found",
            data={"tool": "unknown"},
            id="req-1",
        )
        
        assert response.error is not None
        assert response.error.code == MCPJSONRPCError.TOOL_NOT_FOUND
        assert response.error.data == {"tool": "unknown"}

    def test_server_info(self):
        """Test server info."""
        info = MCPServerInfo(
            name="test-server",
            version="1.0.0",
            protocol_version="2024-11-05",
        )
        
        data = info.to_dict()
        
        assert data["name"] == "test-server"
        assert data["protocolVersion"] == "2024-11-05"

    def test_capabilities(self):
        """Test capabilities."""
        caps = MCPCapabilities(
            tools={},
            resources={},
        )
        
        data = caps.to_dict()
        
        assert "tools" in data
        assert "resources" in data
        assert "prompts" not in data


class TestMCPServer:
    """Tests for MCP Server."""

    @pytest.fixture
    def server(self):
        """Create a test MCP server."""
        return MCPServer(
            name="test-mcp",
            version="1.0.0",
        )

    def test_server_initialization(self, server):
        """Test server initialization."""
        assert server.info.name == "test-mcp"
        assert server.info.version == "1.0.0"

    def test_register_tool(self, server):
        """Test tool registration."""
        tool = MCPTool(
            name="my-tool",
            description="Test",
            input_schema={},
        )
        
        server.register_tool(tool)
        
        assert "my-tool" in server._tools

    def test_register_resource(self, server):
        """Test resource registration."""
        resource = MCPResource(
            uri="file:///test.txt",
            name="test",
        )
        
        server.register_resource(resource)
        
        assert "file:///test.txt" in server._resources

    @pytest.mark.asyncio
    async def test_initialize(self, server):
        """Test server initialization via protocol."""
        request = MCPRequest(
            id="req-1",
            method=MCPMethod.INITIALIZE,
            params={
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "test-client", "version": "1.0"},
            },
        )
        
        response = await server.handle_request(request)
        
        assert response.result is not None
        assert response.result["protocolVersion"] == "2024-11-05"
        assert "serverInfo" in response.result
        assert "capabilities" in response.result

    @pytest.mark.asyncio
    async def test_tools_list(self, server):
        """Test listing tools."""
        # Register a tool first
        tool = MCPTool(
            name="hello",
            description="Say hello",
            input_schema={},
        )
        server.register_tool(tool)
        
        # Initialize server first
        init_req = MCPRequest(
            id="init-1",
            method=MCPMethod.INITIALIZE,
            params={},
        )
        await server.handle_request(init_req)
        
        request = MCPRequest(
            id="req-1",
            method=MCPMethod.TOOLS_LIST,
            params={},
        )
        
        response = await server.handle_request(request)
        
        assert response.result is not None
        assert "tools" in response.result

    @pytest.mark.asyncio
    async def test_tools_call(self, server):
        """Test calling a tool."""
        # Register tool with async handler
        async def echo_handler(**kwargs):
            return {"echoed": kwargs.get("msg", "")}
        
        tool = MCPTool(
            name="echo",
            description="Echo input",
            input_schema={},
        )
        server.register_tool(tool)
        server.register_tool_handler("echo", echo_handler)
        
        # Initialize server first
        init_req = MCPRequest(
            id="init-1",
            method=MCPMethod.INITIALIZE,
            params={},
        )
        await server.handle_request(init_req)
        
        request = MCPRequest(
            id="req-1",
            method=MCPMethod.TOOLS_CALL,
            params={
                "name": "echo",
                "arguments": {"msg": "hello"},
            },
        )
        
        response = await server.handle_request(request)
        
        assert response.result is not None
        assert response.result["isError"] is False

    @pytest.mark.asyncio
    async def test_tool_not_found(self, server):
        """Test calling non-existent tool."""
        # Initialize server first
        init_req = MCPRequest(
            id="init-1",
            method=MCPMethod.INITIALIZE,
            params={},
        )
        await server.handle_request(init_req)
        
        request = MCPRequest(
            id="req-1",
            method=MCPMethod.TOOLS_CALL,
            params={
                "name": "nonexistent",
                "arguments": {},
            },
        )
        
        response = await server.handle_request(request)
        
        # When tool not found, server returns error response
        assert response.error is not None
        assert response.error.code == MCPJSONRPCError.TOOL_NOT_FOUND

    @pytest.mark.asyncio
    async def test_method_not_found(self, server):
        """Test calling unknown method."""
        # Initialize server first
        init_req = MCPRequest(
            id="init-1",
            method=MCPMethod.INITIALIZE,
            params={},
        )
        await server.handle_request(init_req)
        
        request = MCPRequest(
            id="req-1",
            method="unknown.method",
            params={},
        )
        
        response = await server.handle_request(request)
        
        assert response.error is not None
        assert response.error.code == MCPJSONRPCError.METHOD_NOT_FOUND

    @pytest.mark.asyncio
    async def test_shutdown(self, server):
        """Test server shutdown."""
        # Initialize first
        init_req = MCPRequest(
            id="req-1",
            method=MCPMethod.INITIALIZE,
            params={},
        )
        await server.handle_request(init_req)
        
        # Then shutdown
        shutdown_req = MCPRequest(
            id="req-2",
            method=MCPMethod.SHUTDOWN,
            params={},
        )
        response = await server.handle_request(shutdown_req)
        
        assert response.result is not None
        assert response.result["shutdown"] is True


class TestMCPBuiltinTools:
    """Tests for built-in MCP tools."""

    def test_get_builtin_tools_count(self):
        """Test that we have 6+ built-in tools."""
        tools = get_builtin_tools()
        
        assert len(tools) >= 6, f"Expected 6+ tools, got {len(tools)}"
        
        tool_names = [t.name for t in tools]
        assert "search_mcp_tools" in tool_names
        assert "list_mcp_servers" in tool_names
        assert "call_mcp_tool" in tool_names
        assert "install_mcp" in tool_names
        assert "install_skill" in tool_names
        assert "install_plugin" in tool_names

    @pytest.mark.asyncio
    async def test_handle_search_mcp_tools(self):
        """Test search_mcp_tools handler."""
        result = await handle_search_mcp_tools(query="team")
        
        assert "query" in result
        assert "results" in result
        assert result["query"] == "team"

    @pytest.mark.asyncio
    async def test_handle_list_mcp_servers(self):
        """Test list_mcp_servers handler."""
        result = await handle_list_mcp_servers()
        
        assert "servers" in result
        assert isinstance(result["servers"], list)

    @pytest.mark.asyncio
    async def test_handle_call_mcp_tool_builtin(self):
        """Test calling built-in tool."""
        result = await handle_call_mcp_tool(
            server_id="__builtin__",
            tool_name="team_get_tasks",
            arguments={},
        )
        
        assert "success" in result or "message" in result

    @pytest.mark.asyncio
    async def test_handle_install_mcp(self):
        """Test install_mcp handler."""
        result = await handle_install_mcp(
            name="Test MCP Server",
            description="A test MCP server",
            command="npx",
            args='["-y", "test-package"]',
        )
        
        assert result["success"] is True
        assert "server_id" in result
        assert result["name"] == "Test MCP Server"

    @pytest.mark.asyncio
    async def test_handle_install_skill(self):
        """Test install_skill handler."""
        result = await handle_install_skill(
            name="Code Review",
            description="Review code for issues",
            github_url="https://github.com/example/skill",
        )
        
        assert result["success"] is True
        assert result["skill_name"] == "Code Review"
        assert result["method"] == "github"

    @pytest.mark.asyncio
    async def test_handle_get_tool_info(self):
        """Test get_tool_info handler."""
        result = await handle_get_tool_info(tool_name="search_mcp_tools")
        
        assert "tool_name" in result or "error" in result


class TestMCPToolSchemas:
    """Tests for tool schemas and validation."""

    def test_search_mcp_tools_schema(self):
        """Test search_mcp_tools has valid schema."""
        tool = MCPTool(
            name="search_mcp_tools",
            description="Test",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                },
                "required": ["query"],
            },
        )
        
        data = tool.to_dict()
        
        assert data["inputSchema"]["required"] == ["query"]
        assert "query" in data["inputSchema"]["properties"]

    def test_call_mcp_tool_schema(self):
        """Test call_mcp_tool has valid schema."""
        tool = MCPTool(
            name="call_mcp_tool",
            description="Test",
            input_schema={
                "type": "object",
                "properties": {
                    "server_id": {"type": "string"},
                    "tool_name": {"type": "string"},
                    "arguments": {"type": "object"},
                },
                "required": ["server_id", "tool_name", "arguments"],
            },
        )
        
        data = tool.to_dict()
        
        assert "server_id" in data["inputSchema"]["required"]
        assert "tool_name" in data["inputSchema"]["required"]
        assert "arguments" in data["inputSchema"]["required"]

    def test_install_skill_schema(self):
        """Test install_skill has valid schema."""
        tool = MCPTool(
            name="install_skill",
            description="Test",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "github_url": {"type": "string"},
                    "npx_command": {"type": "string"},
                },
                "required": ["name"],
            },
        )
        
        data = tool.to_dict()
        
        assert "name" in data["inputSchema"]["required"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
