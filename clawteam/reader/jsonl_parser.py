"""Claude JSONL conversation file reader.

Claude Code writes complete structured data for each conversation:
  ~/.claude/projects/<projectHash>/<conversationId>.jsonl

Each line is a JSON with 5 types:
  user / assistant / progress / system / file-history-snapshot

This reader is responsible for:
  1. Automatically scanning project directories to find new JSONL files
  2. Incrementally reading files (tail -f semantics), parsing each JSON line
  3. Converting Claude-specific format to NormalizedMessage and emitting 'message' events

@author ClawTeam
"""

from __future__ import annotations

import json
import os
import time
import logging
from pathlib import Path
from typing import Dict, Optional, Set
from dataclasses import dataclass

from clawteam.reader.types import BaseOutputReader, OutputEvent, OutputEventType, TokenUsage

logger = logging.getLogger(__name__)


@dataclass
class SessionWatch:
    """Session watch context."""

    session_id: str
    work_dir: str
    project_dir: str
    conversation_id: Optional[str] = None
    file_path: Optional[str] = None
    file_offset: int = 0
    line_buffer: str = ""
    start_time: float = 0.0


# Tool name to activity type mapping
TOOL_TYPE_MAP = {
    "Read": OutputEventType.FILE_READ,
    "Write": OutputEventType.FILE_WRITE,
    "Edit": OutputEventType.FILE_WRITE,
    "Bash": OutputEventType.COMMAND,
    "Grep": OutputEventType.SEARCH,
    "Glob": OutputEventType.SEARCH,
    "Task": OutputEventType.TOOL_CALL,
    "WebFetch": OutputEventType.TOOL_CALL,
    "WebSearch": OutputEventType.SEARCH,
}


class ClaudeJsonlReader(BaseOutputReader):
    """Claude Code JSONL reader."""

    @property
    def provider_id(self) -> str:
        return "claude-code"

    def __init__(self):
        """Initialize Claude JSONL reader."""
        self._sessions: Dict[str, SessionWatch] = {}
        self._claimed_conversation_ids: Set[str] = set()

        # Configuration
        self._scan_interval = 2000  # Directory scan interval in ms
        self._poll_interval = 2000  # File polling interval in ms

        # Claude projects directory base path
        self._claude_projects_dir = Path.home() / ".claude" / "projects"

    def start_watching(self, session_id: str, work_dir: str) -> None:
        """Start watching session.

        Args:
            session_id: Session ID.
            work_dir: Working directory.
        """
        if session_id in self._sessions:
            return

        # Compute project hash from work directory
        project_hash = self._compute_project_hash(work_dir)
        project_dir = self._claude_projects_dir / project_hash

        watch = SessionWatch(
            session_id=session_id,
            work_dir=work_dir,
            project_dir=str(project_dir),
            start_time=time.time(),
        )
        self._sessions[session_id] = watch

        # Start directory scan to automatically discover JSONL files
        self._start_directory_scan(watch)
        logger.info(
            "[ClaudeJsonlReader] Started watching session %s, project dir: %s",
            session_id,
            project_dir,
        )

    def bind_conversation_id(self, session_id: str, conversation_id: str) -> None:
        """Bind CLI internal conversation ID.

        Args:
            session_id: Session ID.
            conversation_id: Conversation ID.
        """
        watch = self._sessions.get(session_id)
        if not watch:
            return

        if watch.conversation_id == conversation_id:
            return

        new_file_path = Path(watch.project_dir) / f"{conversation_id}.jsonl"

        # Already reading correct file
        if watch.file_path == str(new_file_path):
            watch.conversation_id = conversation_id
            return

        # Clean up existing file watchers
        self._cleanup_file_watcher(watch)

        # Release old claim, register new claim
        if watch.conversation_id:
            self._claimed_conversation_ids.discard(watch.conversation_id)
        self._claimed_conversation_ids.add(conversation_id)

        watch.conversation_id = conversation_id
        watch.file_path = str(new_file_path)
        watch.file_offset = 0
        watch.line_buffer = ""

        logger.info(
            "[ClaudeJsonlReader] Bound conversation %s → %s", conversation_id, new_file_path
        )
        self._start_file_reading(watch)

    def stop_watching(self, session_id: str) -> None:
        """Stop watching session.

        Args:
            session_id: Session ID.
        """
        watch = self._sessions.pop(session_id, None)
        if not watch:
            return

        self._cleanup_file_watcher(watch)

        # Release conversation claim
        if watch.conversation_id:
            self._claimed_conversation_ids.discard(watch.conversation_id)

        logger.info("[ClaudeJsonlReader] Stopped watching session %s", session_id)

    def cleanup(self) -> None:
        """Clean up all resources."""
        for session_id in list(self._sessions.keys()):
            self.stop_watching(session_id)

        self._claimed_conversation_ids.clear()
        logger.info("[ClaudeJsonlReader] Cleaned up all resources")

    def emit_message(self, event: OutputEvent) -> None:
        """Emit a message event.

        Args:
            event: Output event.
        """
        # This would be implemented to emit to manager
        pass

    def _compute_project_hash(self, work_dir: str) -> str:
        """Compute project hash from working directory.

        Args:
            work_dir: Working directory path.

        Returns:
            Project hash string.
        """
        # Simplified hash for testing
        import hashlib

        return hashlib.md5(work_dir.encode()).hexdigest()[:16]

    def _start_directory_scan(self, watch: SessionWatch) -> None:
        """Start directory scanning for JSONL files.

        Args:
            watch: Session watch context.
        """
        # Implementation would start background thread/async task
        pass

    def _start_file_reading(self, watch: SessionWatch) -> None:
        """Start reading JSONL file.

        Args:
            watch: Session watch context.
        """
        if not watch.file_path:
            return

        path = Path(watch.file_path)
        if not path.exists():
            logger.warning("[ClaudeJsonlReader] File does not exist: %s", watch.file_path)
            return

        # Implementation would start file watcher/reader
        pass

    def _cleanup_file_watcher(self, watch: SessionWatch) -> None:
        """Clean up file watcher resources.

        Args:
            watch: Session watch context.
        """
        # Implementation would cleanup file watchers
        pass

    def _process_jsonl_line(self, watch: SessionWatch, line: str) -> None:
        """Process a JSONL line.

        Args:
            watch: Session watch context.
            line: JSONL line content.
        """
        try:
            data = json.loads(line)
            line_type = data.get("type")

            if line_type == "user":
                self._handle_user_message(watch, data)
            elif line_type == "assistant":
                self._handle_assistant_message(watch, data)
            elif line_type == "progress":
                self._handle_progress(watch, data)
            elif line_type == "system":
                self._handle_system_message(watch, data)
            elif line_type == "file-history-snapshot":
                self._handle_file_snapshot(watch, data)

        except json.JSONDecodeError as e:
            logger.error("[ClaudeJsonlReader] Failed to parse JSONL line: %s", e)

    def _handle_user_message(self, watch: SessionWatch, data: dict) -> None:
        """Handle user message.

        Args:
            watch: Session watch context.
            data: JSON data.
        """
        message = data.get("message", {})
        content = message.get("content", "")

        # Could emit as tool call or other event type
        pass

    def _handle_assistant_message(self, watch: SessionWatch, data: dict) -> None:
        """Handle assistant message.

        Args:
            watch: Session watch context.
            data: JSON data.
        """
        message = data.get("message", {})
        content = message.get("content", "")

        # Extract tool calls from assistant message
        if isinstance(content, list):
            for item in content:
                if item.get("type") == "text":
                    # Text response
                    text = item.get("text", "")
                    if text.strip():
                        event = OutputEvent(
                            session_id=watch.session_id,
                            event_type=OutputEventType.MESSAGE,
                            timestamp=time.time(),
                            content=text[:500],  # Truncate long messages
                        )
                        self.emit_message(event)

                elif item.get("type") == "tool_use":
                    # Tool use
                    tool_name = item.get("name", "")
                    event_type = TOOL_TYPE_MAP.get(tool_name, OutputEventType.TOOL_CALL)

                    event = OutputEvent(
                        session_id=watch.session_id,
                        event_type=event_type,
                        timestamp=time.time(),
                        content=f"{tool_name} tool call",
                        metadata={"tool_name": tool_name},
                    )
                    self.emit_message(event)

    def _handle_progress(self, watch: SessionWatch, data: dict) -> None:
        """Handle progress message.

        Args:
            watch: Session watch context.
            data: JSON data.
        """
        # Could emit progress events
        pass

    def _handle_system_message(self, watch: SessionWatch, data: dict) -> None:
        """Handle system message.

        Args:
            watch: Session watch context.
            data: JSON data.
        """
        subtype = data.get("subtype")
        if subtype == "usage":
            # Token usage
            input_tokens = data.get("input_tokens", 0)
            output_tokens = data.get("output_tokens", 0)

            token_usage = TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
            )

            event = OutputEvent(
                session_id=watch.session_id,
                event_type=OutputEventType.PROGRESS,
                timestamp=time.time(),
                content=f"Token usage: {input_tokens} in, {output_tokens} out",
                token_usage=token_usage,
            )
            self.emit_message(event)

    def _handle_file_snapshot(self, watch: SessionWatch, data: dict) -> None:
        """Handle file history snapshot.

        Args:
            watch: Session watch context.
            data: JSON data.
        """
        # Could emit file operation events
        pass
