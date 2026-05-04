"""WebSocket support for real-time team updates."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class WebSocketConnection:
    """Represents a WebSocket connection."""

    team_name: str
    conn_id: str
    connected_at: float
    last_ping: float = field(default_factory=time.time)
    is_alive: bool = True


class ConnectionPool:
    """Pool of WebSocket connections for efficient management."""

    def __init__(self, max_size: int = 1000):
        self._connections: Dict[str, WebSocketConnection] = {}
        self._team_connections: Dict[str, set] = {}
        self._lock = threading.Lock()
        self._max_size = max_size

    def add(self, conn: WebSocketConnection) -> bool:
        """Add a connection to the pool."""
        with self._lock:
            if len(self._connections) >= self._max_size:
                # Remove oldest connection
                oldest = min(self._connections.values(), key=lambda c: c.connected_at)
                self.remove(oldest)
            
            self._connections[conn.conn_id] = conn
            
            if conn.team_name not in self._team_connections:
                self._team_connections[conn.team_name] = set()
            self._team_connections[conn.team_name].add(conn.conn_id)
            
            return True

    def remove(self, conn: WebSocketConnection) -> bool:
        """Remove a connection from the pool."""
        with self._lock:
            if conn.conn_id in self._connections:
                del self._connections[conn.conn_id]
                
                if conn.team_name in self._team_connections:
                    self._team_connections[conn.team_name].discard(conn.conn_id)
                    if not self._team_connections[conn.team_name]:
                        del self._team_connections[conn.team_name]
                
                return True
            return False

    def get(self, conn_id: str) -> Optional[WebSocketConnection]:
        """Get a connection by ID."""
        with self._lock:
            return self._connections.get(conn_id)

    def get_team_connections(self, team_name: str) -> List[WebSocketConnection]:
        """Get all connections for a team."""
        with self._lock:
            conn_ids = self._team_connections.get(team_name, set())
            return [self._connections[cid] for cid in conn_ids if cid in self._connections]

    def get_stats(self) -> Dict:
        """Get pool statistics."""
        with self._lock:
            return {
                "total_connections": len(self._connections),
                "total_teams": len(self._team_connections),
                "team_counts": {team: len(conns) for team, conns in self._team_connections.items()}
            }


class MessageBatcher:
    """Batches messages for efficient broadcast delivery."""

    def __init__(self, flush_interval: float = 0.1, max_batch_size: int = 100):
        self._flush_interval = flush_interval
        self._max_batch_size = max_batch_size
        self._batches: Dict[str, deque] = {}
        self._lock = threading.Lock()
        self._last_flush: Dict[str, float] = {}
        self._pending_count: Dict[str, int] = {}

    def add_message(self, team_name: str, message: dict) -> bool:
        """Add a message to the batch queue.
        
        Returns True if batch should be flushed.
        """
        with self._lock:
            if team_name not in self._batches:
                self._batches[team_name] = deque(maxlen=self._max_batch_size)
                self._last_flush[team_name] = time.time()
                self._pending_count[team_name] = 0
            
            self._batches[team_name].append(message)
            self._pending_count[team_name] += 1
            
            # Check if we should flush
            should_flush = (
                len(self._batches[team_name]) >= self._max_batch_size or
                time.time() - self._last_flush[team_name] >= self._flush_interval
            )
            
            return should_flush

    def get_and_clear_batch(self, team_name: str) -> List[dict]:
        """Get all pending messages for a team and clear the batch."""
        with self._lock:
            messages = list(self._batches.get(team_name, []))
            self._batches[team_name].clear()
            self._last_flush[team_name] = time.time()
            self._pending_count[team_name] = 0
            return messages

    def should_flush(self, team_name: str) -> bool:
        """Check if a team's batch should be flushed."""
        with self._lock:
            if team_name not in self._batches:
                return False
            return (
                len(self._batches[team_name]) >= self._max_batch_size or
                time.time() - self._last_flush[team_name] >= self._flush_interval
            )


class WebSocketManager:
    """Manages WebSocket connections for team updates with pooling and batching."""

    def __init__(self):
        self._pool = ConnectionPool(max_size=1000)
        self._batcher = MessageBatcher(flush_interval=0.1, max_batch_size=50)
        self._ping_interval = 30.0  # seconds
        self._ping_timeout = 10.0  # seconds
        self._broadcast_handlers: Dict[str, Callable] = {}
        # Direct connection tracking for efficient health checks
        self._connections: Dict[str, WebSocketConnection] = {}
        self._team_connections: Dict[str, List[str]] = {}
        self._lock = threading.Lock()

    def add_connection(self, team_name: str, conn_id: str) -> WebSocketConnection:
        """Add a new WebSocket connection."""
        conn = WebSocketConnection(
            team_name=team_name,
            conn_id=conn_id,
            connected_at=time.time()
        )
        with self._lock:
            self._connections[conn_id] = conn
            if team_name not in self._team_connections:
                self._team_connections[team_name] = []
            if conn_id not in self._team_connections[team_name]:
                self._team_connections[team_name].append(conn_id)
        self._pool.add(conn)
        logger.info(f"WebSocket connected for team {team_name} (pool size: {self._pool.get_stats()['total_connections']})")
        return conn

    def remove_connection(self, team_name: str, conn: WebSocketConnection):
        """Remove a WebSocket connection."""
        with self._lock:
            if conn.conn_id in self._connections:
                del self._connections[conn.conn_id]
            if team_name in self._team_connections:
                self._team_connections[team_name] = [c for c in self._team_connections[team_name] if c != conn.conn_id]
        self._pool.remove(conn)
        logger.info(f"WebSocket disconnected for team {team_name} (pool size: {self._pool.get_stats()['total_connections']})")

    def get_connections(self, team_name: str) -> List[WebSocketConnection]:
        """Get all connections for a team."""
        with self._lock:
            conn_ids = self._team_connections.get(team_name, [])
            return [self._connections[cid] for cid in conn_ids if cid in self._connections]

    def register_broadcast_handler(self, team_name: str, handler: Callable):
        """Register a handler for broadcasting messages to a team."""
        with self._lock:
            self._broadcast_handlers[team_name] = handler

    def unregister_broadcast_handler(self, team_name: str):
        """Unregister a broadcast handler."""
        with self._lock:
            if team_name in self._broadcast_handlers:
                del self._broadcast_handlers[team_name]

    def broadcast(self, team_name: str, message: dict):
        """Broadcast a message to all connections for a team with batching."""
        # Add to batcher
        should_flush = self._batcher.add_message(team_name, message)
        
        if should_flush:
            self._flush_batch(team_name)

    def _flush_batch(self, team_name: str):
        """Flush a team's message batch."""
        messages = self._batcher.get_and_clear_batch(team_name)
        if not messages:
            return
        
        # Get broadcast handler
        with self._lock:
            handler = self._broadcast_handlers.get(team_name)
        
        if handler:
            # Combine messages into a single batch
            batch_message = {
                "type": "batch",
                "messages": messages,
                "count": len(messages),
                "timestamp": time.time()
            }
            try:
                handler(batch_message)
            except Exception as e:
                logger.error(f"Broadcast error for team {team_name}: {e}")

    def flush_all(self):
        """Flush all pending batches."""
        with self._lock:
            team_names = list(self._broadcast_handlers.keys())
        
        for team_name in team_names:
            if self._batcher.should_flush(team_name):
                self._flush_batch(team_name)

    def check_health(self):
        """Check connection health and remove stale connections."""
        now = time.time()
        stale_threshold = self._ping_interval + self._ping_timeout
        
        with self._lock:
            team_names = list(self._team_connections.keys())
        
        for team_name in team_names:
            stale_conn_ids = []
            
            with self._lock:
                conn_ids = list(self._team_connections.get(team_name, []))
            
            # Identify stale connections
            for conn_id in conn_ids:
                conn = self._connections.get(conn_id)
                if conn and now - conn.last_ping > stale_threshold:
                    conn.is_alive = False
                    stale_conn_ids.append(conn_id)
            
            # Remove stale connections
            for conn_id in stale_conn_ids:
                conn = self._connections.get(conn_id)
                if conn:
                    self.remove_connection(team_name, conn)

    def get_stats(self) -> Dict:
        """Get manager statistics."""
        pool_stats = self._pool.get_stats()
        return {
            "pool": pool_stats,
            "ping_interval": self._ping_interval,
            "ping_timeout": self._ping_timeout
        }


# Global WebSocket manager instance
ws_manager = WebSocketManager()


def create_websocket_handler(collector, team_cache):
    """Create a WebSocket handler function for aiohttp or similar."""

    async def websocket_handler(ws, team_name: str):
        """Handle WebSocket connection for a team."""
        conn_id = str(id(ws))
        conn = ws_manager.add_connection(team_name, conn_id)

        # Register broadcast handler for this connection
        async def send_message(message):
            try:
                await ws.send_json(message)
            except Exception:
                conn.is_alive = False
        
        ws_manager.register_broadcast_handler(team_name, send_message)

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
            ws_manager.unregister_broadcast_handler(team_name)
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
                    await ws.send_json({"type": "update", "data": team_data, "timestamp": time.time()})
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
            } else if (data.type === 'batch') {
                // Handle batched messages
                data.messages.forEach(msg => this.onMessage(msg));
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
