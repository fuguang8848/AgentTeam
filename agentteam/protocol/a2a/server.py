"""
A2A Server Implementation.

Provides an HTTP/SSE server for handling A2A protocol requests,
enabling agent-to-agent communication, task management, and
event streaming.

Features:
- AgentCard discovery endpoint
- Task submission and management
- Message passing
- Server-Sent Events (SSE) for streaming
- Authentication and authorization
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Awaitable
from datetime import datetime, timezone

from .models import (
    AgentCard,
    Task,
    TaskStatus,
    Message,
    MessageType,
    A2ARequest,
    A2AResponse,
    StreamingChunk,
)

logger = logging.getLogger(__name__)


# Error codes following JSON-RPC and A2A protocol
class A2AErrorCode:
    """Standard A2A error codes."""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    SERVER_ERROR = -32000
    TASK_NOT_FOUND = -32001
    TASK_REJECTED = -32002
    AGENT_UNAVAILABLE = -32003
    AUTHENTICATION_FAILED = -32004


# A2A Method names
class A2AMethod:
    """Standard A2A RPC method names."""

    # Agent endpoints
    GET_AGENT_CARD = "agentCard.get"

    # Task endpoints
    TASK_SUBMIT = "tasks.submit"
    TASK_GET = "tasks.get"
    TASK_CANCEL = "tasks.cancel"
    TASK_ACCEPT = "tasks.accept"
    TASK_REJECT = "tasks.reject"
    TASK_STATUS = "tasks.status"
    TASK_RESULT = "tasks.result"

    # Message endpoints
    MESSAGE_SEND = "messages.send"
    MESSAGE_PUSH = "messages.push"

    # Stream endpoints
    STREAM_START = "stream.start"
    STREAM_CHUNK = "stream.chunk"
    STREAM_END = "stream.end"


# Type aliases for handlers
RequestHandler = Callable[[A2ARequest], Awaitable[A2AResponse]]
TaskHandler = Callable[[Task], Awaitable[None]]
MessageHandler = Callable[[Message], Awaitable[None]]


class A2AServer:
    """
    A2A Protocol Server.

    Implements the server-side of the A2A protocol, handling:
    - AgentCard discovery (GET /.well-known/agent-card)
    - Task submission and management via JSON-RPC
    - Server-Sent Events for push notifications
    - Authentication and authorization

    Example:
        ```python
        server = A2AServer(
            agent_card=my_agent_card,
            on_task_submit=handle_task,
        )
        await server.start(port=8080)
        ```
    """

    def __init__(
        self,
        agent_card: AgentCard,
        on_task_submit: RequestHandler | None = None,
        on_task_accept: RequestHandler | None = None,
        on_task_reject: RequestHandler | None = None,
        on_task_cancel: RequestHandler | None = None,
        on_message_send: RequestHandler | None = None,
        auth_token: str | None = None,
    ):
        """
        Initialize A2A Server.

        Args:
            agent_card: The AgentCard for this agent
            on_task_submit: Handler for task submission
            on_task_accept: Handler for task acceptance
            on_task_reject: Handler for task rejection
            on_task_cancel: Handler for task cancellation
            on_message_send: Handler for messages
            auth_token: Optional authentication token
        """
        self.agent_card = agent_card
        self.auth_token = auth_token

        # Task storage
        self._tasks: dict[str, Task] = {}

        # Event queues for SSE clients
        self._event_queues: dict[str, asyncio.Queue] = {}

        # Handlers
        self._handlers: dict[str, RequestHandler] = {}
        if on_task_submit:
            self._handlers[A2AMethod.TASK_SUBMIT] = on_task_submit
        if on_task_accept:
            self._handlers[A2AMethod.TASK_ACCEPT] = on_task_accept
        if on_task_reject:
            self._handlers[A2AMethod.TASK_REJECT] = on_task_reject
        if on_task_cancel:
            self._handlers[A2AMethod.TASK_CANCEL] = on_task_cancel
        if on_message_send:
            self._handlers[A2AMethod.MESSAGE_SEND] = on_message_send

        # Default handlers
        self._setup_default_handlers()

        # Server state
        self._running = False
        self._server = None

    def _setup_default_handlers(self) -> None:
        """Setup default request handlers for built-in methods."""

        # AgentCard handler
        async def get_agent_card(request: A2ARequest) -> A2AResponse:
            return A2AResponse.success(self.agent_card.to_dict(), request.request_id)

        self._handlers[A2AMethod.GET_AGENT_CARD] = get_agent_card

        # Task submit handler
        async def task_submit(request: A2ARequest) -> A2AResponse:
            params = request.params
            task = Task(
                name=params.get("name"),
                description=params.get("description"),
                arguments=params.get("arguments", {}),
                priority=params.get("priority", "medium"),
            )
            self._tasks[task.id] = task
            return A2AResponse.success(task.to_dict(), request.request_id)

        self._handlers[A2AMethod.TASK_SUBMIT] = task_submit

        # Task get handler
        async def task_get(request: A2ARequest) -> A2AResponse:
            task_id = request.params.get("taskId")
            task = self._tasks.get(task_id)
            if not task:
                return A2AResponse.error_response(
                    A2AErrorCode.TASK_NOT_FOUND, f"Task {task_id} not found", request.request_id
                )
            return A2AResponse.success(task.to_dict(), request.request_id)

        self._handlers[A2AMethod.TASK_GET] = task_get

        # Task status handler
        async def task_status(request: A2ARequest) -> A2AResponse:
            task_id = request.params.get("taskId")
            task = self._tasks.get(task_id)
            if not task:
                return A2AResponse.error_response(
                    A2AErrorCode.TASK_NOT_FOUND, f"Task {task_id} not found", request.request_id
                )
            return A2AResponse.success({"taskId": task.id, "status": task.status.value}, request.request_id)

        self._handlers[A2AMethod.TASK_STATUS] = task_status

        # Task result handler
        async def task_result(request: A2ARequest) -> A2AResponse:
            task_id = request.params.get("taskId")
            task = self._tasks.get(task_id)
            if not task:
                return A2AResponse.error_response(
                    A2AErrorCode.TASK_NOT_FOUND, f"Task {task_id} not found", request.request_id
                )
            if task.status != TaskStatus.COMPLETED:
                return A2AResponse.error_response(
                    A2AErrorCode.INVALID_REQUEST, "Task is not completed yet", request.request_id
                )
            return A2AResponse.success({"taskId": task.id, "result": task.result}, request.request_id)

        self._handlers[A2AMethod.TASK_RESULT] = task_result

        # Message send handler
        async def message_send(request: A2ARequest) -> A2AResponse:
            params = request.params
            message = Message(
                type=MessageType(params.get("type", "message")),
                from_agent_id=params.get("fromAgentId"),
                from_agent_name=params.get("fromAgentName"),
                to_agent_id=params.get("toAgentId"),
                content=params.get("content"),
                task_id=params.get("taskId"),
            )
            return A2AResponse.success(message.to_dict(), request.request_id)

        self._handlers[A2AMethod.MESSAGE_SEND] = message_send

    async def handle_request(self, request: A2ARequest) -> A2AResponse:
        """
        Handle an incoming A2A JSON-RPC request.

        Args:
            request: The A2A request to process

        Returns:
            A2AResponse with the result or error
        """
        method = request.method

        # Check authentication
        if self.auth_token:
            token = request.params.get("_auth_token") or request.params.get("_token")
            if token != self.auth_token:
                return A2AResponse.error_response(
                    A2AErrorCode.AUTHENTICATION_FAILED, "Authentication required", request.request_id
                )

        # Find handler
        handler = self._handlers.get(method)
        if not handler:
            return A2AResponse.error_response(
                A2AErrorCode.METHOD_NOT_FOUND, f"Method {method} not found", request.request_id
            )

        try:
            result = await handler(request)
            return result
        except Exception as e:
            logger.exception(f"Error handling {method}")
            return A2AResponse.error_response(A2AErrorCode.INTERNAL_ERROR, str(e), request.request_id)

    def register_handler(self, method: str, handler: RequestHandler) -> None:
        """
        Register a custom request handler.

        Args:
            method: The JSON-RPC method name
            handler: Async handler function
        """
        self._handlers[method] = handler

    async def create_task(self, task: Task) -> Task:
        """
        Create a new task in the server.

        Args:
            task: The task to create

        Returns:
            The created task with updated metadata
        """
        task.created_at = datetime.now(timezone.utc).isoformat()
        self._tasks[task.id] = task
        return task

    async def get_task(self, task_id: str) -> Task | None:
        """
        Get a task by ID.

        Args:
            task_id: The task ID

        Returns:
            The task or None if not found
        """
        return self._tasks.get(task_id)

    async def update_task(self, task_id: str, **updates) -> Task | None:
        """
        Update a task.

        Args:
            task_id: The task ID
            **updates: Fields to update

        Returns:
            The updated task or None if not found
        """
        task = self._tasks.get(task_id)
        if not task:
            return None

        for key, value in updates.items():
            if hasattr(task, key):
                setattr(task, key, value)

        task.updated_at = datetime.now(timezone.utc).isoformat()
        return task

    async def send_notification(self, event_type: str, data: dict[str, Any], client_id: str | None = None) -> None:
        """
        Send a notification to connected clients.

        Args:
            event_type: Type of event (e.g., "task_update", "message")
            data: Event data
            client_id: Optional specific client to send to
        """
        event = json.dumps(
            {
                "type": event_type,
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        if client_id and client_id in self._event_queues:
            await self._event_queues[client_id].put(event)
        else:
            # Broadcast to all clients
            for queue in self._event_queues.values():
                await queue.put(event)

    async def subscribe(self, client_id: str) -> asyncio.Queue:
        """
        Subscribe a client to event notifications.

        Args:
            client_id: Unique client identifier

        Returns:
            Queue for receiving events
        """
        queue = asyncio.Queue()
        self._event_queues[client_id] = queue
        return queue

    async def unsubscribe(self, client_id: str) -> None:
        """
        Unsubscribe a client from notifications.

        Args:
            client_id: The client to unsubscribe
        """
        if client_id in self._event_queues:
            del self._event_queues[client_id]

    async def broadcast_task_update(self, task: Task) -> None:
        """
        Broadcast a task status update to all subscribers.

        Args:
            task: The updated task
        """
        await self.send_notification(
            "task_update",
            {
                "taskId": task.id,
                "status": task.status.value,
                "updatedAt": task.updated_at,
                "result": task.result,
                "error": task.error,
            },
        )

    async def start(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        """
        Start the A2A server.

        Args:
            host: Host to bind to
            port: Port to listen on
        """
        import aiohttp
        from aiohttp import web

        self._running = True

        app = web.Application()

        # AgentCard well-known endpoint
        app.router.add_get("/.well-known/agent-card", self._agent_card_handler)

        # JSON-RPC endpoint
        app.router.add_post("/rpc", self._rpc_handler)

        # SSE endpoint for streaming
        app.router.add_get("/events", self._events_handler)

        # Health check
        app.router.add_get("/health", self._health_handler)

        runner = web.AppRunner(app)
        await runner.setup()
        self._server = web.TCPSite(runner, host, port)
        await self._server.start()
        logger.info(f"A2A Server started on {host}:{port}")

    async def stop(self) -> None:
        """Stop the A2A server."""
        self._running = False
        if self._server:
            await self._server.stop()
            logger.info("A2A Server stopped")

    async def _agent_card_handler(self, request: web.Request) -> web.Response:
        """Handle AgentCard discovery requests."""
        return web.json_response(self.agent_card.to_dict())

    async def _rpc_handler(self, request: web.Request) -> web.Response:
        """Handle JSON-RPC requests."""
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return web.json_response(
                A2AResponse.error_response(A2AErrorCode.PARSE_ERROR, "Invalid JSON", "").model_dump(by_alias=True),
                status=400,
            )

        try:
            # Handle batch requests
            if isinstance(body, list):
                results = []
                for item in body:
                    req = A2ARequest(**item)
                    resp = await self.handle_request(req)
                    results.append(resp.model_dump(by_alias=True))
                return web.json_response(results)
            else:
                req = A2ARequest(**body)
                resp = await self.handle_request(req)
                return web.json_response(resp.model_dump(by_alias=True))
        except Exception as e:
            logger.exception("Error in RPC handler")
            return web.json_response(
                A2AResponse.error_response(A2AErrorCode.INTERNAL_ERROR, str(e), body.get("id", "")).model_dump(
                    by_alias=True
                ),
                status=500,
            )

    async def _events_handler(self, request: web.Request) -> web.Response:
        """Handle SSE (Server-Sent Events) subscriptions."""
        client_id = request.query.get("client_id", "default")
        queue = await self.subscribe(client_id)

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
            while self._running:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30)
                    await response.write(f"data: {event}\n\n".encode())
                except asyncio.TimeoutError:
                    # Send keepalive
                    await response.write(b": keepalive\n\n")
        except ConnectionResetError:
            pass
        finally:
            await self.unsubscribe(client_id)

        return response

    async def _health_handler(self, request: web.Request) -> web.Response:
        """Handle health check requests."""
        return web.json_response(
            {
                "status": "healthy",
                "agent_id": self.agent_card.agent_id,
                "version": self.agent_card.version,
            }
        )
