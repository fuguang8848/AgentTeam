"""Board module - Web UI dashboard for AgentTeam.

This module provides the web interface for the AgentTeam multi-agent coordination system.
It has been refactored for modularity:

Main components:
- server.py: Main HTTP server entry point
- collector.py: Data collection from agents/teams
- renderer.py: HTML rendering utilities
- websocket.py: WebSocket support

Modular subpackages:
- handlers/: HTTP API handlers (modular since refactoring)
- sse/: Server-Sent Events broadcasting
- chat/: Chat and AI assistant functionality
- utils.py: Utility functions

To start the server:
    from agentteam.board import serve
    serve(host="0.0.0.0", port=8080)
"""

from agentteam.board.server import serve, BoardHandler

__all__ = ["serve", "BoardHandler"]
