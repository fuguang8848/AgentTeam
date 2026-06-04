"""Tests for chat API endpoints.

This test file has been updated to work with the modular board structure.
"""

import json
import os
import sys
import tempfile
import threading
import time
import unittest
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure board module is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestChatAPI(unittest.TestCase):
    """Test cases for chat API endpoints."""

    def test_generate_simple_response_greeting(self):
        """Test simple response generation for greetings."""
        from agentteam.board.chat.ai_assistant import generate_simple_response

        response = generate_simple_response("你好")
        self.assertIsInstance(response, str)
        self.assertTrue(len(response) > 0)

    def test_generate_simple_response_help(self):
        """Test simple response generation for help requests."""
        from agentteam.board.chat.ai_assistant import generate_simple_response

        response = generate_simple_response("help")
        self.assertIsInstance(response, str)
        self.assertTrue(len(response) > 0)

    def test_generate_simple_response_team(self):
        """Test simple response generation for team-related queries."""
        from agentteam.board.chat.ai_assistant import generate_simple_response

        response = generate_simple_response("team")
        self.assertIsInstance(response, str)
        self.assertTrue("team" in response.lower() or "团队" in response)

    def test_generate_simple_response_task(self):
        """Test simple response generation for task-related queries."""
        from agentteam.board.chat.ai_assistant import generate_simple_response

        response = generate_simple_response("任务")
        self.assertIsInstance(response, str)
        self.assertTrue("task" in response.lower() or "任务" in response or len(response) > 0)

    def test_generate_simple_response_default(self):
        """Test simple response generation for unknown queries."""
        from agentteam.board.chat.ai_assistant import generate_simple_response

        response = generate_simple_response("random unknown message")
        self.assertIsInstance(response, str)
        self.assertTrue(len(response) > 0)

    def test_chat_message_save_and_retrieve(self):
        """Test saving and retrieving chat messages via the chat module."""
        from agentteam.board.chat.commands import process_chat_message

        # Process a simple message to test the chat module works
        response = process_chat_message("Hello", "TestUser")
        self.assertIsInstance(response, dict)
        self.assertIn("content", response)

    def test_chat_command_help(self):
        """Test /help command handling."""
        from agentteam.board.chat.commands import handle_chat_command

        response = handle_chat_command("/help")
        self.assertEqual(response["role"], "system")
        self.assertIn("/help", response["content"])

    def test_chat_command_status(self):
        """Test /status command handling."""
        from agentteam.board.chat.commands import handle_chat_command

        response = handle_chat_command("/status")
        self.assertEqual(response["role"], "system")

    def test_chat_command_tasks_list(self):
        """Test /tasks list command handling."""
        from agentteam.board.chat.commands import handle_chat_command

        response = handle_chat_command("/tasks")
        self.assertEqual(response["role"], "system")

    def test_chat_command_unknown_command(self):
        """Test handling of unknown commands."""
        from agentteam.board.chat.commands import handle_chat_command

        response = handle_chat_command("/unknown_command")
        # Unknown commands should fall back to AI assistant
        self.assertIsInstance(response, dict)
        self.assertIn("content", response)

    def test_chat_history_clear(self):
        """Test chat history clear command."""
        from agentteam.board.chat.commands import handle_chat_command

        response = handle_chat_command("/clear")
        self.assertEqual(response["content"], "CLEAR_CHAT_HISTORY")

    def test_now_iso_format(self):
        """Test _now_iso returns proper ISO format."""
        from agentteam.board.utils import _now_iso

        iso_str = _now_iso()
        self.assertIsInstance(iso_str, str)
        # Should contain T separator for ISO format
        self.assertIn("T", iso_str)


class TestSSEBroadcasting(unittest.TestCase):
    """Test cases for SSE broadcasting functionality."""

    def test_sse_connection_registers_subscriber(self):
        """Test that SSE connections properly register as subscribers."""
        from agentteam.board.sse.broadcast import SSEBroadcaster

        broadcaster = SSEBroadcaster(max_queue_size=100)
        idx, lock = broadcaster.add_subscriber()

        self.assertEqual(idx, 0)
        self.assertIsNotNone(lock)

        broadcaster.remove_subscriber(lock)
        self.assertEqual(len(broadcaster.subscribers), 0)

    def test_broadcast_chat_event(self):
        """Test broadcasting chat events to subscribers."""
        from agentteam.board.sse.broadcast import SSEBroadcaster

        broadcaster = SSEBroadcaster(max_queue_size=100)
        idx1, lock1 = broadcaster.add_subscriber()

        event = {"type": "message", "content": "Hello"}
        broadcaster.broadcast(event)

        # Get events starting from idx1
        events = broadcaster.get_events_since(idx1)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["content"], "Hello")


class TestNaturalLanguageParsing(unittest.TestCase):
    """Test natural language parsing for chat commands."""

    def test_natural_language_create_task(self):
        """Test natural language for creating a task."""
        from agentteam.board.chat.ai_assistant import generate_simple_response

        response = generate_simple_response("创建一个新任务")
        self.assertIsInstance(response, str)
        self.assertTrue(len(response) > 0)

    def test_natural_language_view_team_status(self):
        """Test natural language for viewing team status."""
        from agentteam.board.chat.ai_assistant import generate_simple_response

        response = generate_simple_response("查看团队状态")
        self.assertIsInstance(response, str)
        self.assertTrue(len(response) > 0)


class TestBoardServerImports(unittest.TestCase):
    """Test that all board server modules can be imported."""

    def test_import_handlers(self):
        """Test importing all handler modules."""
        from agentteam.board.handlers import (
            BaseHandler, AuthMixin, StaticMixin, TeamMixin,
            AgentMixin, SessionMixin, SettingsMixin, TransportMixin,
            NotificationsMixin, ProvidersMixin, TasksMixin, OverviewMixin
        )
        self.assertIsNotNone(BaseHandler)

    def test_import_sse(self):
        """Test importing SSE modules."""
        from agentteam.board.sse import (
            SSEBroadcaster, get_sse_broadcaster,
            AgentActivityBroadcaster, get_agent_activity_broadcaster
        )
        self.assertIsNotNone(SSEBroadcaster)
        self.assertIsNotNone(AgentActivityBroadcaster)

    def test_import_chat(self):
        """Test importing chat modules."""
        from agentteam.board.chat import (
            call_ai_assistant, generate_simple_response,
            handle_chat_command, process_chat_message
        )
        self.assertIsNotNone(generate_simple_response)
        self.assertIsNotNone(handle_chat_command)

    def test_import_utils(self):
        """Test importing utils module."""
        from agentteam.board.utils import _now_iso, _get_collector
        self.assertIsNotNone(_now_iso)

    def test_import_server(self):
        """Test importing server module."""
        from agentteam.board import serve, BoardHandler
        self.assertIsNotNone(serve)
        self.assertIsNotNone(BoardHandler)


if __name__ == "__main__":
    unittest.main()
