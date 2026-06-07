"""
MCP (Model Context Protocol) Server Implementation.

Provides a server implementation for the MCP protocol,
enabling tool registration, resource management, and
standardized AI tool calling.

Features:
- Dynamic tool registration
- Resource and prompt management
- Stdio and SSE transport support
- Progress notifications
- Logging integration

Reference: Anthropic MCP Protocol Specification
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from typing import Any, Callable, Awaitable
from datetime import datetime, timezone

from .types import (
    MCPTool,
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

logger = logging.getLogger(__name__)


# MCP Method names
class MCPMethod:
    """Standard MCP JSON-RPC method names."""

    # Lifecycle
    INITIALIZE = "initialize"
    SHUTDOWN = "shutdown"

    # Tools
    TOOLS_LIST = "tools/list"
    TOOLS_CALL = "tools/call"

    # Resources
    RESOURCES_LIST = "resources/list"
    RESOURCES_READ = "resources/read"
    RESOURCES_TEMPLATES_LIST = "resources/templates/list"
    RESOURCES_SUBSCRIBE = "resources/subscribe"
    RESOURCES_UNSUBSCRIBE = "resources/unsubscribe"

    # Prompts
    PROMPTS_LIST = "prompts/list"
    PROMPTS_GET = "prompts/get"

    # Logging
    LOGGING_SET_LEVEL = "logging/setLevel"


# Type aliases
ToolHandler = Callable[..., Awaitable[dict[str, Any]]]
RequestHandler = Callable[[MCPRequest], Awaitable[MCPResponse]]


class MCPServer:
    """
    MCP Protocol Server.

    Implements the Model Context Protocol server, providing
    tools, resources, and prompts to connected AI clients.

    Example:
        ```python
        server = MCPServer(
            name="my-agent",
            version="1.0.0",
            tools=[my_tool],
        )

        # Run as stdio server
        await server.run_stdio()

        # Or run as HTTP/SSE server
        await server.run_sse(host="0.0.0.0", port=8080)
        ```
    """

    def __init__(
        self,
        name: str = "agentteam-mcp",
        version: str = "1.0.0",
        protocol_version: str = "2024-11-05",
        tools: list[MCPTool] | None = None,
        resources: list[MCPResource] | None = None,
        resource_templates: list[MCPResourceTemplate] | None = None,
        prompts: list[MCPrompt] | None = None,
        on_tool_call: Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]] | None = None,
    ):
        """
        Initialize MCP Server.

        Args:
            name: Server name
            version: Server version
            protocol_version: MCP protocol version
            tools: Initial tools to register
            resources: Initial resources to register
            resource_templates: Initial resource templates
            prompts: Initial prompts to register
            on_tool_call: Handler for tool calls
        """
        self.info = MCPServerInfo(
            name=name,
            version=version,
            protocol_version=protocol_version,
        )

        # Storage
        self._tools: dict[str, MCPTool] = {}
        self._resources: dict[str, MCPResource] = {}
        self._resource_templates: dict[str, MCPResourceTemplate] = {}
        self._prompts: dict[str, MCPrompt] = {}

        # Tool handler
        self._tool_handlers: dict[str, ToolHandler] = {}
        self._on_tool_call = on_tool_call

        # Capabilities
        self._capabilities = MCPCapabilities(
            tools={} if tools else None,
            resources={} if resources else None,
            prompts={} if prompts else None,
            logging={},
        )

        # Client state
        self._client_info: dict[str, Any] | None = None
        self._initialized = False

        # Registered handlers
        self._handlers: dict[str, RequestHandler] = {}
        self._setup_handlers()

        # Register initial items
        if tools:
            for tool in tools:
                self.register_tool(tool)
        if resources:
            for resource in resources:
                self.register_resource(resource)
        if resource_templates:
            for template in resource_templates:
                self.register_resource_template(template)
        if prompts:
            for prompt in prompts:
                self.register_prompt(prompt)

    def _setup_handlers(self) -> None:
        """Setup default request handlers."""

        # Initialize handler
        async def handle_initialize(request: MCPRequest) -> MCPResponse:
            params = request.params
            self._client_info = params.get("clientInfo", {})

            result = {
                "protocolVersion": self.info.protocol_version,
                "serverInfo": self.info.to_dict(),
                "capabilities": self._capabilities.to_dict(),
                "instructions": f"{self.info.name} v{self.info.version}",
            }
            self._initialized = True
            return MCPResponse.success(result, request.id)

        self._handlers[MCPMethod.INITIALIZE] = handle_initialize

        # Shutdown handler
        async def handle_shutdown(request: MCPRequest) -> MCPResponse:
            self._initialized = False
            return MCPResponse.success({"shutdown": True}, request.id)

        self._handlers[MCPMethod.SHUTDOWN] = handle_shutdown

        # Tools list handler
        async def handle_tools_list(request: MCPRequest) -> MCPResponse:
            tools_list = [tool.to_dict() for tool in self._tools.values()]
            return MCPResponse.success({"tools": tools_list}, request.id)

        self._handlers[MCPMethod.TOOLS_LIST] = handle_tools_list

        # Tools call handler
        async def handle_tools_call(request: MCPRequest) -> MCPResponse:
            params = request.params
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if not tool_name:
                return MCPResponse.create_error(
                    MCPJSONRPCError.INVALID_PARAMS,
                    "Tool name is required",
                    id=request.id,
                )

            if tool_name not in self._tool_handlers:
                return MCPResponse.create_error(
                    MCPJSONRPCError.TOOL_NOT_FOUND,
                    f"Tool '{tool_name}' not found",
                    id=request.id,
                )

            try:
                handler = self._tool_handlers[tool_name]
                result = await handler(**arguments)
                return MCPResponse.success(
                    {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, ensure_ascii=False),
                            }
                        ],
                        "isError": False,
                    },
                    request.id,
                )
            except Exception as e:
                logger.exception(f"Error calling tool {tool_name}")
                return MCPResponse.success(
                    {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Error: {str(e)}",
                            }
                        ],
                        "isError": True,
                    },
                    request.id,
                )

        self._handlers[MCPMethod.TOOLS_CALL] = handle_tools_call

        # Resources list handler
        async def handle_resources_list(request: MCPRequest) -> MCPResponse:
            resources_list = [r.to_dict() for r in self._resources.values()]
            return MCPResponse.success({"resources": resources_list}, request.id)

        self._handlers[MCPMethod.RESOURCES_LIST] = handle_resources_list

        # Resources templates list handler
        async def handle_resources_templates_list(request: MCPRequest) -> MCPResponse:
            templates_list = [t.to_dict() for t in self._resource_templates.values()]
            return MCPResponse.success({"resourceTemplates": templates_list}, request.id)

        self._handlers[MCPMethod.RESOURCES_TEMPLATES_LIST] = handle_resources_templates_list

        # Prompts list handler
        async def handle_prompts_list(request: MCPRequest) -> MCPResponse:
            prompts_list = [p.to_dict() for p in self._prompts.values()]
            return MCPResponse.success({"prompts": prompts_list}, request.id)

        self._handlers[MCPMethod.PROMPTS_LIST] = handle_prompts_list

        # Logging set level handler
        async def handle_logging_set_level(request: MCPRequest) -> MCPResponse:
            level = request.params.get("level", "info")
            numeric_level = getattr(logging, level.upper(), logging.INFO)
            logging.getLogger().setLevel(numeric_level)
            return MCPResponse.success(None, request.id)

        self._handlers[MCPMethod.LOGGING_SET_LEVEL] = handle_logging_set_level

    def register_tool(self, tool: MCPTool) -> None:
        """
        Register a tool with the server.

        Args:
            tool: The tool to register
        """
        self._tools[tool.name] = tool
        if self._capabilities.tools is None:
            self._capabilities.tools = {}
        logger.debug(f"Registered tool: {tool.name}")

    def register_tool_handler(
        self,
        tool_name: str,
        handler: ToolHandler,
    ) -> None:
        """
        Register a handler for a tool.

        Args:
            tool_name: Name of the tool
            handler: Async function to handle tool calls
        """
        self._tool_handlers[tool_name] = handler

    def register_resource(self, resource: MCPResource) -> None:
        """
        Register a resource with the server.

        Args:
            resource: The resource to register
        """
        self._resources[resource.uri] = resource
        if self._capabilities.resources is None:
            self._capabilities.resources = {}
        logger.debug(f"Registered resource: {resource.uri}")

    def register_resource_template(self, template: MCPResourceTemplate) -> None:
        """
        Register a resource template with the server.

        Args:
            template: The resource template to register
        """
        self._resource_templates[template.uri_template] = template
        if self._capabilities.resources is None:
            self._capabilities.resources = {}

    def register_prompt(self, prompt: MCPrompt) -> None:
        """
        Register a prompt with the server.

        Args:
            prompt: The prompt to register
        """
        self._prompts[prompt.name] = prompt
        if self._capabilities.prompts is None:
            self._capabilities.prompts = {}
        logger.debug(f"Registered prompt: {prompt.name}")

    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """
        Handle an incoming MCP request.

        Args:
            request: The MCP request to process

        Returns:
            MCPResponse with the result or error
        """
        # Check initialization
        if request.method != MCPMethod.INITIALIZE and not self._initialized:
            return MCPResponse.create_error(
                MCPJSONRPCError.INTERNAL_ERROR,
                "Server not initialized",
                id=request.id,
            )

        # Find handler
        handler = self._handlers.get(request.method)
        if not handler:
            return MCPResponse.create_error(
                MCPJSONRPCError.METHOD_NOT_FOUND,
                f"Method '{request.method}' not found",
                id=request.id,
            )

        try:
            return await handler(request)
        except Exception as e:
            logger.exception(f"Error handling {request.method}")
            return MCPResponse.create_error(
                MCPJSONRPCError.INTERNAL_ERROR,
                str(e),
                id=request.id,
            )

    async def run_stdio(self) -> None:
        """
        Run the server using stdio transport.

        This is the primary mode for local MCP servers.
        """
        logger.info("Starting MCP server in stdio mode")

        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                if not line:
                    break

                try:
                    request_data = json.loads(line)
                except json.JSONDecodeError:
                    response = MCPResponse.create_error(
                        MCPJSONRPCError.PARSE_ERROR,
                        "Invalid JSON",
                    )
                    print(json.dumps(response.to_dict()), flush=True)
                    continue

                request = MCPRequest(
                    id=request_data.get("id"),
                    method=request_data.get("method", ""),
                    params=request_data.get("params", {}),
                )

                response = await self.handle_request(request)
                print(json.dumps(response.to_dict(), ensure_ascii=False), flush=True)

                # Exit on shutdown
                if request.method == MCPMethod.SHUTDOWN:
                    break

            except Exception as e:
                logger.exception("Error in stdio loop")
                break

    async def run_sse(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
    ) -> None:
        """
        Run the server using SSE transport.

        Args:
            host: Host to bind to
            port: Port to listen on
        """
        import aiohttp
        from aiohttp import web

        logger.info(f"Starting MCP server on {host}:{port}")

        app = web.Application()
        app.router.add_post("/mcp", self._handle_http)
        app.router.add_get("/sse", self._handle_sse)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()

        # Keep running
        while True:
            await asyncio.sleep(3600)

    async def _handle_http(self, request: web.Request) -> web.Response:
        """Handle HTTP MCP requests."""
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return web.json_response(
                MCPResponse.create_error(
                    MCPJSONRPCError.PARSE_ERROR,
                    "Invalid JSON",
                ).to_dict(),
                status=400,
            )

        req = MCPRequest(
            id=body.get("id"),
            method=body.get("method", ""),
            params=body.get("params", {}),
        )

        response = await self.handle_request(req)
        return web.json_response(response.to_dict())

    async def _handle_sse(self, request: web.Request) -> web.Response:
        """Handle SSE subscriptions."""
        client_id = str(id(request))
        queue: asyncio.Queue = asyncio.Queue()

        response = web.StreamResponse(
            status=200,
            reason="OK",
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
        await response.prepare(request)

        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30)
                    await response.write(f"data: {event}\n\n".encode())
                except asyncio.TimeoutError:
                    await response.write(b": keepalive\n\n")
        except ConnectionResetError:
            pass

        return response
