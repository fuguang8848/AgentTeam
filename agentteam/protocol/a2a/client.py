"""
A2A Client Implementation.

Provides a client for interacting with A2A protocol servers,
enabling task submission, message passing, and event subscription.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncGenerator
from urllib.parse import urljoin

import aiohttp

from .models import (
    AgentCard,
    Task,
    TaskStatus,
    Message,
    MessageType,
    A2ARequest,
    A2AResponse,
)

logger = logging.getLogger(__name__)


class A2AClientError(Exception):
    """Base exception for A2A client errors."""
    pass


class A2AClient:
    """
    A2A Protocol Client.
    
    Client for interacting with A2A protocol servers. Supports:
    - AgentCard discovery
    - Task submission and management
    - Message passing
    - SSE event subscription
    
    Example:
        ```python
        client = A2AClient("http://localhost:8080")
        
        # Get agent card
        card = await client.get_agent_card()
        
        # Submit a task
        task = await client.submit_task(
            name="analyze_code",
            arguments={"path": "/src"}
        )
        
        # Subscribe to events
        async for event in client.subscribe_events():
            print(event)
        ```
    """

    def __init__(
        self,
        base_url: str,
        auth_token: str | None = None,
        timeout: float = 30.0,
    ):
        """
        Initialize A2A Client.
        
        Args:
            base_url: Base URL of the A2A server
            auth_token: Optional authentication token
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self.timeout = timeout
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the HTTP session."""
        if self._session is None or self._session.closed:
            headers = {}
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=timeout,
            )
        return self._session

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def _rpc(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> Any:
        """
        Make an RPC call to the server.
        
        Args:
            method: The RPC method name
            params: Method parameters
            request_id: Optional request ID
            
        Returns:
            The result from the server
        """
        session = await self._get_session()
        
        request = A2ARequest(
            method=method,
            params=params or {},
            request_id=request_id,
        )
        
        url = urljoin(self.base_url, "/rpc")
        async with session.post(url, json=request.model_dump(by_alias=True)) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise A2AClientError(f"HTTP {resp.status}: {text}")
            
            data = await resp.json()
            
            # Handle batch response
            if isinstance(data, list):
                return [self._parse_response(item) for item in data]
            
            return self._parse_response(data)

    def _parse_response(self, data: dict[str, Any]) -> Any:
        """Parse an A2A response."""
        response = A2AResponse(**data)
        
        if response.error:
            raise A2AClientError(
                f"RPC Error {response.error.get('code')}: "
                f"{response.error.get('message')}"
            )
        
        return response.result

    async def get_agent_card(self) -> AgentCard:
        """
        Get the AgentCard from the server.
        
        Returns:
            The agent's AgentCard
        """
        session = await self._get_session()
        url = urljoin(self.base_url, "/.well-known/agent-card")
        
        async with session.get(url) as resp:
            if resp.status != 200:
                raise A2AClientError(f"Failed to get agent card: HTTP {resp.status}")
            
            data = await resp.json()
            return AgentCard(**data)

    async def submit_task(
        self,
        name: str | None = None,
        description: str | None = None,
        arguments: dict[str, Any] | None = None,
        priority: str = "medium",
        input_schema: dict[str, Any] | None = None,
    ) -> Task:
        """
        Submit a new task to the agent.
        
        Args:
            name: Task name
            description: Task description
            arguments: Task input arguments
            priority: Task priority
            input_schema: JSON Schema for input
            
        Returns:
            The submitted task
        """
        params = {
            "priority": priority,
        }
        if name:
            params["name"] = name
        if description:
            params["description"] = description
        if arguments:
            params["arguments"] = arguments
        if input_schema:
            params["inputSchema"] = input_schema
        
        result = await self._rpc("tasks.submit", params)
        return Task(**result)

    async def get_task(self, task_id: str) -> Task:
        """
        Get a task by ID.
        
        Args:
            task_id: The task ID
            
        Returns:
            The task
        """
        result = await self._rpc("tasks.get", {"taskId": task_id})
        return Task(**result)

    async def get_task_status(self, task_id: str) -> TaskStatus:
        """
        Get the status of a task.
        
        Args:
            task_id: The task ID
            
        Returns:
            The task status
        """
        result = await self._rpc("tasks.status", {"taskId": task_id})
        return TaskStatus(result.get("status"))

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task.
        
        Args:
            task_id: The task ID
            
        Returns:
            True if cancelled
        """
        result = await self._rpc("tasks.cancel", {"taskId": task_id})
        return result.get("cancelled", False)

    async def accept_task(self, task_id: str) -> Task:
        """
        Accept a task for processing.
        
        Args:
            task_id: The task ID
            
        Returns:
            The accepted task
        """
        result = await self._rpc("tasks.accept", {"taskId": task_id})
        return Task(**result)

    async def reject_task(self, task_id: str, reason: str) -> bool:
        """
        Reject a task.
        
        Args:
            task_id: The task ID
            reason: Reason for rejection
            
        Returns:
            True if rejected
        """
        result = await self._rpc("tasks.reject", {
            "taskId": task_id,
            "reason": reason,
        })
        return result.get("rejected", False)

    async def get_task_result(self, task_id: str) -> Any:
        """
        Get the result of a completed task.
        
        Args:
            task_id: The task ID
            
        Returns:
            The task result
        """
        result = await self._rpc("tasks.result", {"taskId": task_id})
        return result.get("result")

    async def send_message(
        self,
        content: str,
        to_agent_id: str | None = None,
        to_agent_name: str | None = None,
        task_id: str | None = None,
        message_type: str = "message",
    ) -> Message:
        """
        Send a message to an agent.
        
        Args:
            content: Message content
            to_agent_id: Target agent ID
            to_agent_name: Target agent name
            task_id: Associated task ID
            message_type: Message type
            
        Returns:
            The sent message
        """
        params: dict[str, Any] = {
            "type": message_type,
            "content": content,
        }
        if to_agent_id:
            params["toAgentId"] = to_agent_id
        if to_agent_name:
            params["toAgentName"] = to_agent_name
        if task_id:
            params["taskId"] = task_id
        
        result = await self._rpc("messages.send", params)
        return Message(**result)

    async def subscribe_events(
        self,
        client_id: str | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Subscribe to server events via SSE.
        
        Args:
            client_id: Optional client ID for the subscription
            
        Yields:
            Event dictionaries from the server
        """
        session = await self._get_session()
        client_id = client_id or id(self)
        
        url = f"{self.base_url}/events?client_id={client_id}"
        
        async with session.get(url) as resp:
            if resp.status != 200:
                raise A2AClientError(f"Failed to subscribe: HTTP {resp.status}")
            
            async for line in resp.content:
                line = line.decode().strip()
                if line.startswith("data: "):
                    data = line[6:]
                    try:
                        event = json.loads(data)
                        yield event
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in event: {data}")
                elif line.startswith(":"):
                    # Comment (keepalive)
                    pass

    async def wait_for_task_completion(
        self,
        task_id: str,
        poll_interval: float = 1.0,
        timeout: float | None = None,
    ) -> Task:
        """
        Wait for a task to complete.
        
        Args:
            task_id: The task ID
            poll_interval: Polling interval in seconds
            timeout: Maximum wait time in seconds
            
        Returns:
            The completed task
            
        Raises:
            asyncio.TimeoutError: If timeout is reached
        """
        start_time = asyncio.get_event_loop().time()
        
        while True:
            status = await self.get_task_status(task_id)
            
            if status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                return await self.get_task(task_id)
            
            if timeout:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= timeout:
                    raise asyncio.TimeoutError(f"Task {task_id} did not complete within {timeout}s")
            
            await asyncio.sleep(poll_interval)

    async def __aenter__(self) -> A2AClient:
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        await self.close()
