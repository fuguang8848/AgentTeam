"""
MCP Protocol Type Definitions.

Implements the core types for the Model Context Protocol (MCP),
including tools, resources, prompts, and protocol messages.

Reference: Anthropic MCP Protocol Specification
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal


def _now_iso() -> str:
    """Return current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


# =============================================================================
# JSON-RPC Types
# =============================================================================


class MCPJSONRPCError:
    """MCP JSON-RPC error codes."""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    TOOL_NOT_FOUND = -32001
    RESOURCE_NOT_FOUND = -32002
    PROMPT_NOT_FOUND = -32003


@dataclass
class MCPRequest:
    """MCP JSON-RPC request."""

    jsonrpc: str = "2.0"
    id: str | int | None = None
    method: str = ""
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
            "method": self.method,
            "params": self.params,
        }


class MCPResponse:
    """MCP JSON-RPC response (not using dataclass to allow property)."""

    def __init__(
        self,
        jsonrpc: str = "2.0",
        id: str | int | None = None,
        result: dict[str, Any] | list[Any] | None = None,
        error_obj: MCPError | None = None,
    ):
        self.jsonrpc = jsonrpc
        self.id = id
        self.result = result
        self.error_obj = error_obj

    def to_dict(self) -> dict[str, Any]:
        result = {"jsonrpc": self.jsonrpc, "id": self.id}
        if self.error_obj:
            result["error"] = self.error_obj.to_dict()
        else:
            result["result"] = self.result
        return result

    @property
    def error(self) -> MCPError | None:
        """Access error (for backward compatibility)."""
        return self.error_obj

    @classmethod
    def success(cls, result: Any, id: str | int | None = None) -> MCPResponse:
        """Create a successful response."""
        return cls(jsonrpc="2.0", id=id, result=result)

    @classmethod
    def create_error(cls, code: int, message: str, data: Any = None, id: str | int | None = None) -> MCPResponse:
        """Create an error response."""
        return cls(
            jsonrpc="2.0",
            id=id,
            error_obj=MCPError(code=code, message=message, data=data),
        )


@dataclass
class MCPError:
    """MCP error object."""

    code: int
    message: str
    data: Any = None

    def to_dict(self) -> dict[str, Any]:
        result = {"code": self.code, "message": self.message}
        if self.data is not None:
            result["data"] = self.data
        return result


# =============================================================================
# Tool Types
# =============================================================================


@dataclass
class MCPToolInputSchema:
    """JSON Schema for tool input."""

    type: str = "object"
    properties: dict[str, Any] = field(default_factory=dict)
    required: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "properties": self.properties,
            "required": self.required,
        }


@dataclass
class MCPToolOutputSchema:
    """JSON Schema for tool output."""

    type: str = "object"
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "properties": self.properties,
        }


@dataclass
class MCPTool:
    """
    MCP Tool definition.

    Represents a callable function/tool that can be invoked
    by an LLM through the MCP protocol.
    """

    name: str
    description: str
    input_schema: MCPToolInputSchema | dict[str, Any]
    output_schema: MCPToolOutputSchema | dict[str, Any] | None = None
    annotations: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": (
                self.input_schema.to_dict() if isinstance(self.input_schema, MCPToolInputSchema) else self.input_schema
            ),
            "outputSchema": (
                self.output_schema.to_dict()
                if isinstance(self.output_schema, MCPToolOutputSchema)
                else self.output_schema
            )
            if self.output_schema
            else None,
            "annotations": self.annotations,
        }


# =============================================================================
# Resource Types
# =============================================================================


@dataclass
class MCPResource:
    """MCP resource definition."""

    uri: str
    name: str
    description: str = ""
    mime_type: str = "text/plain"

    def to_dict(self) -> dict[str, Any]:
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
        }


@dataclass
class MCPResourceTemplate:
    """MCP resource template for dynamic resources."""

    uri_template: str
    name: str
    description: str = ""
    mime_type: str = "text/plain"

    def to_dict(self) -> dict[str, Any]:
        return {
            "uriTemplate": self.uri_template,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
        }


# =============================================================================
# Prompt Types
# =============================================================================


@dataclass
class MCPrompt:
    """MCP prompt definition."""

    name: str
    description: str = ""
    arguments: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "arguments": self.arguments,
        }


# =============================================================================
# Server Info Types
# =============================================================================


@dataclass
class MCPServerInfo:
    """MCP server information."""

    name: str
    version: str
    protocol_version: str = "2024-11-05"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "protocolVersion": self.protocol_version,
        }


# =============================================================================
# Capability Types
# =============================================================================


@dataclass
class MCPCapabilities:
    """MCP server capabilities."""

    tools: dict[str, Any] | None = None
    resources: dict[str, Any] | None = None
    prompts: dict[str, Any] | None = None
    logging: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {}
        if self.tools is not None:
            result["tools"] = self.tools
        if self.resources is not None:
            result["resources"] = self.resources
        if self.prompts is not None:
            result["prompts"] = self.prompts
        if self.logging is not None:
            result["logging"] = self.logging
        return result


# =============================================================================
# Transport Types
# =============================================================================


class MCPTransport(str, Enum):
    """MCP transport types."""

    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"
    WEBSOCKET = "websocket"


@dataclass
class MCPStdioTransport:
    """Stdio transport configuration."""

    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "args": self.args,
            "env": self.env,
        }


@dataclass
class MCPSSETransport:
    """SSE (Server-Sent Events) transport configuration."""

    url: str
    headers: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "headers": self.headers,
        }


# =============================================================================
# Notification Types
# =============================================================================


@dataclass
class MCPProgressNotification:
    """Progress notification for long-running operations."""

    progress_token: str
    progress: float
    total: float | None = None
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "progressToken": self.progress_token,
            "progress": self.progress,
        }
        if self.total is not None:
            result["total"] = self.total
        if self.message is not None:
            result["message"] = self.message
        return result


@dataclass
class MCPLogMessage:
    """Log message notification."""

    level: str
    logger: str = ""
    data: Any = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"level": self.level}
        if self.logger:
            result["logger"] = self.logger
        if self.data is not None:
            result["data"] = self.data
        return result
