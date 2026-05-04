"""Tests for WebSocket functionality."""

from __future__ import annotations

import pytest
import time
import threading

from clawteam.board.websocket import (
    WebSocketManager,
    WebSocketConnection,
    ConnectionPool,
    MessageBatcher,
    ws_manager,
    get_websocket_js_code,
)


class TestConnectionPool:
    """Test ConnectionPool class."""

    def test_pool_initialization(self):
        """Test that ConnectionPool initializes correctly."""
        pool = ConnectionPool(max_size=100)
        stats = pool.get_stats()
        assert stats["total_connections"] == 0
        assert stats["total_teams"] == 0

    def test_add_connection(self):
        """Test adding a connection to the pool."""
        pool = ConnectionPool()
        conn = WebSocketConnection(team_name="test-team", conn_id="conn-1", connected_at=time.time())
        result = pool.add(conn)
        
        assert result
        assert pool.get("conn-1") == conn
        assert len(pool.get_team_connections("test-team")) == 1

    def test_remove_connection(self):
        """Test removing a connection from the pool."""
        pool = ConnectionPool()
        conn = WebSocketConnection(team_name="test-team", conn_id="conn-1", connected_at=time.time())
        pool.add(conn)
        
        result = pool.remove(conn)
        assert result
        assert pool.get("conn-1") is None

    def test_get_stats(self):
        """Test getting pool statistics."""
        pool = ConnectionPool()
        conn1 = WebSocketConnection(team_name="test-team", conn_id="conn-1", connected_at=time.time())
        conn2 = WebSocketConnection(team_name="test-team", conn_id="conn-2", connected_at=time.time())
        pool.add(conn1)
        pool.add(conn2)
        
        stats = pool.get_stats()
        assert stats["total_connections"] == 2
        assert stats["total_teams"] == 1


class TestMessageBatcher:
    """Test MessageBatcher class."""

    def test_batcher_initialization(self):
        """Test that MessageBatcher initializes correctly."""
        batcher = MessageBatcher(flush_interval=0.1, max_batch_size=10)
        assert batcher._flush_interval == 0.1
        assert batcher._max_batch_size == 10

    def test_add_message(self):
        """Test adding a message to the batcher."""
        batcher = MessageBatcher()
        should_flush = batcher.add_message("test-team", {"type": "test", "data": "hello"})
        
        # First message shouldn't trigger flush (not enough messages and time hasn't elapsed)
        assert not should_flush

    def test_should_flush_by_size(self):
        """Test that batcher flushes when max batch size is reached."""
        batcher = MessageBatcher(flush_interval=60.0, max_batch_size=3)
        
        batcher.add_message("test-team", {"msg": 1})
        batcher.add_message("test-team", {"msg": 2})
        should_flush = batcher.add_message("test-team", {"msg": 3})
        
        assert should_flush

    def test_get_and_clear_batch(self):
        """Test getting and clearing a batch."""
        batcher = MessageBatcher()
        batcher.add_message("test-team", {"msg": 1})
        batcher.add_message("test-team", {"msg": 2})
        
        messages = batcher.get_and_clear_batch("test-team")
        
        assert len(messages) == 2
        assert batcher.get_and_clear_batch("test-team") == []


class TestWebSocketManager:
    """Test WebSocketManager class."""

    def test_manager_initialization(self):
        """Test that WebSocketManager initializes correctly."""
        manager = WebSocketManager()
        stats = manager.get_stats()
        assert stats["pool"]["total_connections"] == 0
        assert stats["ping_interval"] == 30.0
        assert stats["ping_timeout"] == 10.0

    def test_add_connection(self):
        """Test adding a WebSocket connection."""
        manager = WebSocketManager()
        conn = manager.add_connection("test-team", "conn-1")
        
        assert conn.team_name == "test-team"
        assert conn.is_alive
        assert len(manager.get_connections("test-team")) == 1

    def test_add_multiple_connections(self):
        """Test adding multiple connections for same team."""
        manager = WebSocketManager()
        manager.add_connection("test-team", "conn-1")
        manager.add_connection("test-team", "conn-2")
        
        assert len(manager.get_connections("test-team")) == 2

    def test_remove_connection(self):
        """Test removing a WebSocket connection."""
        manager = WebSocketManager()
        conn = manager.add_connection("test-team", "conn-1")
        manager.remove_connection("test-team", conn)
        
        assert len(manager.get_connections("test-team")) == 0

    def test_remove_connection_from_multiple(self):
        """Test removing one connection from multiple."""
        manager = WebSocketManager()
        conn1 = manager.add_connection("test-team", "conn-1")
        conn2 = manager.add_connection("test-team", "conn-2")
        
        manager.remove_connection("test-team", conn1)
        
        assert len(manager.get_connections("test-team")) == 1

    def test_get_connections(self):
        """Test getting connections for a team."""
        manager = WebSocketManager()
        manager.add_connection("test-team", "conn-1")
        manager.add_connection("test-team", "conn-2")
        
        conns = manager.get_connections("test-team")
        assert len(conns) == 2

    def test_get_connections_empty_team(self):
        """Test getting connections for non-existent team."""
        manager = WebSocketManager()
        conns = manager.get_connections("nonexistent")
        assert conns == []

    def test_check_health_removes_stale(self):
        """Test that health check removes stale connections."""
        manager = WebSocketManager()
        manager._ping_interval = 1.0
        manager._ping_timeout = 1.0
        
        conn = manager.add_connection("test-team", "conn-1")
        conn.last_ping = time.time() - 5.0  # Make it stale
        
        manager.check_health()
        
        assert len(manager.get_connections("test-team")) == 0

    def test_check_health_keeps_alive(self):
        """Test that health check keeps alive connections."""
        manager = WebSocketManager()
        conn = manager.add_connection("test-team", "conn-1")
        conn.last_ping = time.time()  # Recent ping
        
        manager.check_health()
        
        assert len(manager.get_connections("test-team")) == 1


class TestWebSocketConnection:
    """Test WebSocketConnection dataclass."""

    def test_connection_creation(self):
        """Test creating a WebSocket connection."""
        conn = WebSocketConnection(
            team_name="test-team",
            conn_id="conn-1",
            connected_at=time.time()
        )
        
        assert conn.team_name == "test-team"
        assert conn.conn_id == "conn-1"
        assert conn.is_alive
        assert conn.last_ping > 0

    def test_connection_default_values(self):
        """Test default values for connection."""
        conn = WebSocketConnection(team_name="test-team", conn_id="conn-1", connected_at=0.0)
        
        assert conn.is_alive
        assert conn.last_ping > 0  # Should be set to current time


class TestWebSocketJSCode:
    """Test WebSocket JavaScript client code."""

    def test_js_code_exists(self):
        """Test that JavaScript code is generated."""
        js_code = get_websocket_js_code()
        
        assert len(js_code) > 0
        assert "TeamWebSocket" in js_code
        assert "WebSocket" in js_code
        assert "EventSource" in js_code

    def test_js_code_has_connect_methods(self):
        """Test that JavaScript code has connection methods."""
        js_code = get_websocket_js_code()
        
        assert "connectWebSocket" in js_code
        assert "connectSSE" in js_code
        assert "scheduleReconnect" in js_code

    def test_js_code_has_fallback(self):
        """Test that JavaScript code has SSE fallback."""
        js_code = get_websocket_js_code()
        
        assert "useWebSocket" in js_code
        assert "this.connectSSE()" in js_code

    def test_js_code_has_ping_pong(self):
        """Test that JavaScript code handles ping/pong."""
        js_code = get_websocket_js_code()
        
        assert "ping" in js_code
        assert "pong" in js_code

    def test_js_code_has_reconnect_logic(self):
        """Test that JavaScript code has reconnect logic."""
        js_code = get_websocket_js_code()
        
        assert "reconnectDelay" in js_code
        assert "maxReconnectDelay" in js_code


class TestGlobalWebSocketManager:
    """Test global ws_manager instance."""

    def test_global_manager_exists(self):
        """Test that global manager exists."""
        assert ws_manager is not None
        assert isinstance(ws_manager, WebSocketManager)

    def test_global_manager_thread_safety(self):
        """Test that global manager is thread-safe."""
        results = []
        
        def add_connections():
            for i in range(10):
                conn = ws_manager.add_connection("thread-test", f"conn-{threading.current_thread().name}-{i}")
                results.append(conn)
        
        threads = [threading.Thread(target=add_connections, name=f"t{j}") for j in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have 30 connections
        assert len(results) == 30
