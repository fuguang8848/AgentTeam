"""WebSocket support for real-time team updates."""

from __future__ import annotations

import asyncio
import json
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class WebSocketConnection:
    """Represents a WebSocket connection."""

    team_name: str
    connected_at: float
    last_ping: float = field(default_factory=time.time)
    is_alive: bool = True


class WebSocketManager:
    """Manages WebSocket connections for team updates."""

    def __init__(self):
        self._connections: dict[str, list[WebSocketConnection]] = {}
        self._lock = threading.Lock()
        self._ping_interval = 30.0  # seconds
        self._ping_timeout = 10.0  # seconds

    def add_connection(self, team_name: str, conn_id: str) -> WebSocketConnection:
        """Add a new WebSocket connection."""
        conn = WebSocketConnection(team_name=team_name, connected_at=time.time())
        with self._lock:
            if team_name not in self._connections:
                self._connections[team_name] = []
            self._connections[team_name].append(conn)
        logger.info(f"WebSocket connected for team {team_name}")
        return conn

    def remove_connection(self, team_name: str, conn: WebSocketConnection):
        """Remove a WebSocket connection."""
        with self._lock:
            if team_name in self._connections:
                try:
                    self._connections[team_name].remove(conn)
                    if not self._connections[team_name]:
                        del self._connections[team_name]
                except ValueError:
                    pass
        logger.info(f"WebSocket disconnected for team {team_name}")

    def get_connections(self, team_name: str) -> list[WebSocketConnection]:
        """Get all connections for a team."""
        with self._lock:
            return list(self._connections.get(team_name, []))

    def broadcast(self, team_name: str, message: dict):
        """Broadcast a message to all connections for a team."""
        pass

    def check_health(self):
        """Check connection health and remove stale connections."""
        now = time.time()
        with self._lock:
            for team_name, conns in list(self._connections.items()):
                stale = []
                for conn in conns:
                    if now - conn.last_ping > self._ping_interval + self._ping_timeout:
                        conn.is_alive = False
                        stale.append(conn)
                for conn in stale:
                    conns.remove(conn)
                if not conns:
                    del self._connections[team_name]


ws_manager = WebSocketManager()


def create_websocket_handler(collector, team_cache):
    """Create a WebSocket handler function for aiohttp or similar."""

    async def websocket_handler(ws, team_name: str):
        """Handle WebSocket connection for a team."""
        conn = ws_manager.add_connection(team_name, str(id(ws)))

        try:
            team_data = team_cache.get(team_name, lambda: collector.collect_team(team_name))
            await ws.send_json({"type": "init", "data": team_data, "timestamp": time.time()})

            ping_task = asyncio.create_task(ping_loop(ws, conn))
            message_task = asyncio.create_task(message_loop(ws, team_name, collector, team_cache))

            try:
                await asyncio.gather(ping_task, message_task)
            except asyncio.CancelledError:
                pass
            finally:
                ping_task.cancel()
                message_task.cancel()

        except Exception as e:
            logger.error(f"WebSocket error for team {team_name}: {e}")
        finally:
            ws_manager.remove_connection(team_name, conn)

    return websocket_handler


async def ping_loop(ws, conn: WebSocketConnection):
    """Send periodic ping messages to keep connection alive."""
    while conn.is_alive:
        try:
            await ws.send_json({"type": "ping", "timestamp": time.time()})
            conn.last_ping = time.time()
            await asyncio.sleep(30.0)
        except Exception:
            conn.is_alive = False
            break


async def message_loop(ws, team_name: str, collector, team_cache):
    """Listen for incoming messages and handle them."""
    while True:
        try:
            msg = await ws.receive()
            if msg.type == "json":
                data = msg.json()
                if data.get("type") == "pong":
                    pass
                elif data.get("type") == "refresh":
                    team_data = team_cache.get(team_name, lambda: collector.collect_team(team_name))
                    await ws.send_json(
                        {"type": "update", "data": team_data, "timestamp": time.time()}
                    )
            elif msg.type == "close":
                break
        except Exception:
            break


WEBSOCKET_JS_CODE = """
// WebSocket connection with SSE fallback
class TeamWebSocket {
    constructor(teamName) {
        this.teamName = teamName;
        this.ws = null;
        this.sseSource = null;
        this.reconnectDelay = 1000;
        this.maxReconnectDelay = 30000;
        this.useWebSocket = true;
        this.connect();
    }
    
    connect() {
        if (this.useWebSocket && 'WebSocket' in window) {
            this.connectWebSocket();
        } else {
            this.connectSSE();
        }
    }
    
    connectWebSocket() {
        const wsUrl = (location.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + location.host + '/ws/' + this.teamName;
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectDelay = 1000;
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'ping') {
                this.ws.send(JSON.stringify({type: 'pong'}));
            } else if (data.type === 'init' || data.type === 'update') {
                this.onMessage(data.data);
            }
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.useWebSocket = false;
            this.connectSSE();
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket closed');
            this.scheduleReconnect();
        };
    }
    
    connectSSE() {
        const sseUrl = '/api/events/' + this.teamName;
        this.sseSource = new EventSource(sseUrl);
        
        this.sseSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.onMessage(data);
        };
        
        this.sseSource.onerror = () => {
            console.error('SSE error');
            this.sseSource.close();
            this.scheduleReconnect();
        };
    }
    
    scheduleReconnect() {
        setTimeout(() => {
            this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
            this.connect();
        }, this.reconnectDelay);
    }
    
    onMessage(data) {
        console.log('Team update:', data);
    }
    
    refresh() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({type: 'refresh'}));
        }
    }
    
    close() {
        if (this.ws) this.ws.close();
        if (this.sseSource) this.sseSource.close();
    }
}
"""


def get_websocket_js_code() -> str:
    """Return JavaScript code for WebSocket client with SSE fallback."""
    return WEBSOCKET_JS_CODE
