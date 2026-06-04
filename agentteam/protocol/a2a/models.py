"""
A2A Protocol Data Models.

Implements the A2A (Agent-to-Agent) protocol data structures following
the specification for agent interoperability. Includes AgentCard for
agent discovery, Task for task management, and Message for communication.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field


def _now_iso() -> str:
    """Return current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


class MessageType(str, Enum):
    """A2A Message types."""
    # Core message types
    MESSAGE = "message"
    TASK_NOTIFICATION = "task_notification"
    ERROR = "error"
    
    # Task-related message types
    TASK_SUBMIT = "task_submit"
    TASK_ACCEPT = "task_accept"
    TASK_REJECT = "task_reject"
    TASK_CANCEL = "task_cancel"
    TASK_STATUS_UPDATE = "task_status_update"
    TASK_RESULT = "task_result"
    
    # Streaming message types
    STREAM_START = "stream_start"
    STREAM_CHUNK = "stream_chunk"
    STREAM_END = "stream_end"
    
    # Lifecycle message types
    IDLE = "idle"
    SHUTDOWN_REQUEST = "shutdown_request"
    SHUTDOWN_RESPONSE = "shutdown_response"


class TaskStatus(str, Enum):
    """Task status values following A2A protocol."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class StreamingChunk(BaseModel):
    """A chunk of streaming response data."""
    event_id: str = Field(alias="eventId")
    channel: str = "default"
    seq: int = 0
    data: str = ""
    is_final: bool = False

    model_config = {"populate_by_name": True}


class AgentSkill(BaseModel):
    """A skill that an agent can perform."""
    id: str
    name: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)


class AgentCapabilities(BaseModel):
    """Capabilities of an agent."""
    # Core capabilities
    streaming: bool = False
    push_notifications: bool = False
    state_transition_report: bool = False
    
    # Data handling
    attachments: bool = False
    image_url: bool = False
    
    # Task handling
    task_management: bool = False
    
    # Advanced capabilities
    agent_card: bool = True  # Supports agentCard retrieval


class AgentProvider(BaseModel):
    """Information about the agent provider/organization."""
    organization: str = "AgentTeam"
    department: str | None = None
    contact_email: str | None = None
    contact_url: str | None = None


class AgentCard(BaseModel):
    """
    AgentCard - The A2A agent identity and capability advertisement.
    
    Following the A2A protocol specification, this is the primary mechanism
    for agent discovery. Agents expose their capabilities, skills, and
    endpoint information through this data structure.
    
    Reference: A2A Protocol Specification
    """
    # Identity
    name: str
    agent_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    description: str = ""
    url: str | None = None
    
    # Version info
    version: str = "1.0.0"
    a2a_protocol_version: str = Field(default="1.0.0", alias="a2aProtocolVersion")
    
    # Provider information
    provider: AgentProvider = Field(default_factory=AgentProvider)
    
    # Capabilities
    capabilities: AgentCapabilities = Field(default_factory=AgentCapabilities)
    
    # Authentication
    authentication: dict[str, Any] = Field(default_factory=dict)
    """Supported authentication schemes."""
    
    # Skills
    skills: list[AgentSkill] = Field(default_factory=list)
    
    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=_now_iso)
    updated_at: str = Field(default_factory=_now_iso)
    
    # Endpoints
    default_api_url: str | None = Field(default=None, alias="defaultApiUrl")
    
    model_config = {"populate_by_name": True}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return self.model_dump(by_alias=True, exclude_none=True)


class Task(BaseModel):
    """
    Task - A unit of work in the A2A protocol.
    
    Tasks represent work that needs to be done, tracked through
    the A2A protocol lifecycle (submit → accept → work → complete/fail).
    """
    # Identity
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str | None = Field(default=None, alias="sessionId")
    
    # Status
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    
    # Task details
    name: str | None = None
    description: str | None = None
    
    # Input/Output
    input_schema: dict[str, Any] = Field(default_factory=dict, alias="inputSchema")
    output_schema: dict[str, Any] = Field(default_factory=dict, alias="outputSchema")
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: Any = None
    
    # Assignment
    assigned_agent_id: str | None = Field(default=None, alias="assignedAgentId")
    assigned_agent_name: str | None = Field(default=None, alias="assignedAgentName")
    
    # Priority
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    
    # Streaming
    is_streaming: bool = Field(default=False, alias="isStreaming")
    
    # Timestamps
    created_at: str = Field(default_factory=_now_iso, alias="createdAt")
    updated_at: str = Field(default_factory=_now_iso, alias="updatedAt")
    submitted_at: str | None = Field(default=None, alias="submittedAt")
    accepted_at: str | None = Field(default=None, alias="acceptedAt")
    completed_at: str | None = Field(default=None, alias="completedAt")
    failed_at: str | None = Field(default=None, alias="failedAt")
    
    # Error handling
    error: str | None = None
    
    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return self.model_dump(by_alias=True, exclude_none=True)

    def update_status(self, new_status: TaskStatus) -> None:
        """Update task status with timestamp."""
        self.status = new_status
        self.updated_at = _now_iso()
        
        if new_status == TaskStatus.SUBMITTED:
            self.submitted_at = _now_iso()
        elif new_status == TaskStatus.ACCEPTED:
            self.accepted_at = _now_iso()
        elif new_status == TaskStatus.COMPLETED:
            self.completed_at = _now_iso()
        elif new_status == TaskStatus.FAILED:
            self.failed_at = _now_iso()


class Message(BaseModel):
    """
    Message - A communication unit in the A2A protocol.
    
    Messages are used for agent-to-agent communication, including
    task notifications, status updates, and general messages.
    """
    # Identity
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    
    # Message type
    type: MessageType = Field(default=MessageType.MESSAGE)
    
    # Sender/Receiver
    from_agent_id: str | None = Field(default=None, alias="fromAgentId")
    from_agent_name: str | None = Field(default=None, alias="fromAgentName")
    to_agent_id: str | None = Field(default=None, alias="toAgentId")
    to_agent_name: str | None = Field(default=None, alias="toAgentName")
    
    # Content
    content: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    
    # Task reference
    task_id: str | None = Field(default=None, alias="taskId")
    
    # Streaming
    stream_id: str | None = Field(default=None, alias="streamId")
    chunk_index: int | None = None
    total_chunks: int | None = None
    
    # Status
    is_final: bool = False
    
    # Error
    error: str | None = None
    
    # Timestamps
    created_at: str = Field(default_factory=_now_iso, alias="createdAt")
    
    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return self.model_dump(by_alias=True, exclude_none=True)


class A2ARequest(BaseModel):
    """A2A Request envelope."""
    method: str
    params: dict[str, Any] = Field(default_factory=dict)
    request_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    jsonrpc: str = "2.0"

    model_config = {"populate_by_name": True}


class A2AResponse(BaseModel):
    """A2A Response envelope."""
    result: Any = None
    error: dict[str, Any] | None = None
    request_id: str | None = Field(default=None, alias="requestId")
    jsonrpc: str = "2.0"

    model_config = {"populate_by_name": True}

    @classmethod
    def success(cls, result: Any, request_id: str) -> A2AResponse:
        """Create a successful response."""
        return cls(result=result, request_id=request_id)

    @classmethod
    def error_response(
        cls, 
        code: int, 
        message: str, 
        request_id: str,
        data: Any = None
    ) -> A2AResponse:
        """Create an error response."""
        error = {"code": code, "message": message}
        if data is not None:
            error["data"] = data
        return cls(error=error, request_id=request_id)
