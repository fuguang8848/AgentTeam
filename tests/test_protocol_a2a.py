"""
Tests for A2A Protocol Implementation.

Tests the A2A (Agent-to-Agent) protocol layer including:
- AgentCard data model
- Task management
- Message handling
- A2A Server functionality
- A2A Client functionality
"""

import asyncio
import pytest
from datetime import datetime, timezone

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
from agentteam.protocol.a2a.server import A2AServer, A2AMethod, A2AErrorCode
from agentteam.protocol.a2a.client import A2AClient, A2AClientError


class TestAgentCard:
    """Tests for AgentCard model."""

    def test_create_basic_agent_card(self):
        """Test creating a basic AgentCard."""
        card = AgentCard(
            name="test-agent",
            description="A test agent",
        )
        
        assert card.name == "test-agent"
        assert card.description == "A test agent"
        assert card.version == "1.0.0"
        assert card.a2a_protocol_version == "1.0.0"
        assert card.agent_id is not None

    def test_agent_card_with_capabilities(self):
        """Test AgentCard with custom capabilities."""
        capabilities = AgentCapabilities(
            streaming=True,
            push_notifications=True,
            task_management=True,
        )
        
        card = AgentCard(
            name="capable-agent",
            capabilities=capabilities,
        )
        
        assert card.capabilities.streaming is True
        assert card.capabilities.push_notifications is True
        assert card.capabilities.task_management is True

    def test_agent_card_with_skills(self):
        """Test AgentCard with skills."""
        skill = AgentSkill(
            id="code-review",
            name="Code Review",
            description="Review code for issues",
        )
        
        card = AgentCard(
            name="review-agent",
            skills=[skill],
        )
        
        assert len(card.skills) == 1
        assert card.skills[0].name == "Code Review"

    def test_agent_card_to_dict(self):
        """Test AgentCard serialization."""
        card = AgentCard(
            name="test-agent",
            description="Test",
        )
        
        # to_dict uses exclude_none=True but keeps field names
        data = card.to_dict()
        
        assert data["name"] == "test-agent"
        assert "agent_id" in data  # Uses field name, not alias
        assert "capabilities" in data


class TestTask:
    """Tests for Task model."""

    def test_create_basic_task(self):
        """Test creating a basic Task."""
        task = Task(
            name="test-task",
            description="A test task",
        )
        
        assert task.name == "test-task"
        assert task.status == TaskStatus.PENDING
        assert task.id is not None

    def test_task_status_transitions(self):
        """Test Task status update method."""
        task = Task(name="test")
        
        task.update_status(TaskStatus.SUBMITTED)
        assert task.status == TaskStatus.SUBMITTED
        assert task.submitted_at is not None
        
        task.update_status(TaskStatus.ACCEPTED)
        assert task.status == TaskStatus.ACCEPTED
        assert task.accepted_at is not None
        
        task.update_status(TaskStatus.COMPLETED)
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None

    def test_task_with_arguments(self):
        """Test Task with input arguments."""
        task = Task(
            name="process-data",
            arguments={"path": "/data/input.csv", "format": "csv"},
        )
        
        assert task.arguments["path"] == "/data/input.csv"
        assert task.arguments["format"] == "csv"

    def test_task_to_dict(self):
        """Test Task serialization."""
        task = Task(
            name="test-task",
            description="Test",
            priority=TaskPriority.HIGH,
        )
        
        data = task.to_dict()
        
        assert data["name"] == "test-task"
        assert data["priority"] == "high"
        assert "taskId" not in data  # Uses alias


class TestMessage:
    """Tests for Message model."""

    def test_create_message(self):
        """Test creating a Message."""
        msg = Message(
            type=MessageType.MESSAGE,
            content="Hello, agent!",
            from_agent_id="agent-1",
            to_agent_id="agent-2",
        )
        
        assert msg.content == "Hello, agent!"
        assert msg.from_agent_id == "agent-1"
        assert msg.to_agent_id == "agent-2"

    def test_message_with_task_reference(self):
        """Test Message with task reference."""
        msg = Message(
            type=MessageType.TASK_NOTIFICATION,
            content="Task completed",
            task_id="task-123",
        )
        
        assert msg.task_id == "task-123"

    def test_streaming_message(self):
        """Test streaming message properties."""
        msg = Message(
            type=MessageType.STREAM_CHUNK,
            stream_id="stream-abc",
            chunk_index=5,
            total_chunks=10,
            is_final=False,
        )
        
        assert msg.stream_id == "stream-abc"
        assert msg.chunk_index == 5
        assert msg.total_chunks == 10
        assert msg.is_final is False


class TestA2AResponse:
    """Tests for A2AResponse."""

    def test_success_response(self):
        """Test creating a success response."""
        resp = A2AResponse.success(
            {"result": "success"},
            "req-123",
        )
        
        assert resp.result == {"result": "success"}
        assert resp.request_id == "req-123"
        assert resp.error is None

    def test_error_response(self):
        """Test creating an error response."""
        resp = A2AResponse.error_response(
            A2AErrorCode.TASK_NOT_FOUND,
            "Task not found",
            "req-456",
        )
        
        assert resp.error is not None
        assert resp.error["code"] == A2AErrorCode.TASK_NOT_FOUND
        assert resp.error["message"] == "Task not found"


class TestA2AServer:
    """Tests for A2A Server."""

    @pytest.fixture
    def agent_card(self):
        """Create a test AgentCard."""
        return AgentCard(
            name="test-server",
            description="A test A2A server",
            capabilities=AgentCapabilities(
                streaming=True,
                task_management=True,
            ),
        )

    @pytest.fixture
    def server(self, agent_card):
        """Create a test A2A Server."""
        return A2AServer(agent_card=agent_card)

    @pytest.mark.asyncio
    async def test_get_agent_card(self, server, agent_card):
        """Test getting agent card via handler."""
        request = A2ARequest(
            method=A2AMethod.GET_AGENT_CARD,
            params={},
            request_id="req-1",
        )
        
        response = await server.handle_request(request)
        
        assert response.result is not None
        assert response.result["name"] == "test-server"

    @pytest.mark.asyncio
    async def test_task_submit(self, server):
        """Test submitting a task."""
        request = A2ARequest(
            method=A2AMethod.TASK_SUBMIT,
            params={
                "name": "new-task",
                "description": "A new task",
            },
            request_id="req-2",
        )
        
        response = await server.handle_request(request)
        
        assert response.result is not None
        assert response.result["name"] == "new-task"
        assert "id" in response.result

    @pytest.mark.asyncio
    async def test_task_get(self, server):
        """Test getting a task."""
        # First create a task
        submit_req = A2ARequest(
            method=A2AMethod.TASK_SUBMIT,
            params={"name": "test-task"},
            request_id="req-1",
        )
        submit_resp = await server.handle_request(submit_req)
        task_id = submit_resp.result["id"]
        
        # Then get it
        get_req = A2ARequest(
            method=A2AMethod.TASK_GET,
            params={"taskId": task_id},
            request_id="req-2",
        )
        get_resp = await server.handle_request(get_req)
        
        assert get_resp.result is not None
        assert get_resp.result["name"] == "test-task"

    @pytest.mark.asyncio
    async def test_task_not_found(self, server):
        """Test getting a non-existent task."""
        request = A2ARequest(
            method=A2AMethod.TASK_GET,
            params={"taskId": "non-existent-id"},
            request_id="req-1",
        )
        
        response = await server.handle_request(request)
        
        assert response.error is not None
        assert response.error["code"] == A2AErrorCode.TASK_NOT_FOUND

    @pytest.mark.asyncio
    async def test_method_not_found(self, server):
        """Test calling unknown method."""
        request = A2ARequest(
            method="unknown.method",
            params={},
            request_id="req-1",
        )
        
        response = await server.handle_request(request)
        
        assert response.error is not None
        assert response.error["code"] == A2AErrorCode.METHOD_NOT_FOUND

    @pytest.mark.asyncio
    async def test_custom_handler(self, server):
        """Test registering and calling a custom handler."""
        async def custom_handler(request: A2ARequest) -> A2AResponse:
            return A2AResponse.success(
                {"custom": "response"},
                request.request_id,
            )
        
        server.register_handler("custom.method", custom_handler)
        
        request = A2ARequest(
            method="custom.method",
            params={},
            request_id="req-1",
        )
        
        response = await server.handle_request(request)
        
        assert response.result is not None
        assert response.result["custom"] == "response"

    @pytest.mark.asyncio
    async def test_create_and_get_task(self, server):
        """Test task creation and retrieval."""
        task = Task(
            name="integration-task",
            description="Test integration",
            arguments={"key": "value"},
        )
        
        created = await server.create_task(task)
        assert created.id == task.id
        
        retrieved = await server.get_task(task.id)
        assert retrieved is not None
        assert retrieved.name == "integration-task"

    @pytest.mark.asyncio
    async def test_update_task(self, server):
        """Test task update."""
        task = Task(name="update-test")
        await server.create_task(task)
        
        updated = await server.update_task(
            task.id,
            status=TaskStatus.COMPLETED,
            result={"output": "done"},
        )
        
        assert updated is not None
        assert updated.status == TaskStatus.COMPLETED
        assert updated.result == {"output": "done"}


class TestA2AClient:
    """Tests for A2A Client (mock tests)."""

    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test A2A Client initialization."""
        client = A2AClient("http://localhost:8080")
        
        assert client.base_url == "http://localhost:8080"
        
        await client.close()

    @pytest.mark.asyncio
    async def test_client_context_manager(self):
        """Test A2A Client as context manager."""
        async with A2AClient("http://localhost:8080") as client:
            assert client.base_url == "http://localhost:8080"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
