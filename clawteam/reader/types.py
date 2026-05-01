"""Reader type definitions for multi-provider output parsing."""

from __future__ import annotations

from typing import Optional, Dict, Any, Union
from enum import Enum
from dataclasses import dataclass
import time


class ReaderState(str, Enum):
    """Reader state enumeration."""
    IDLE = "idle"
    WATCHING = "watching"
    READING = "reading"
    COMPLETE = "complete"
    ERROR = "error"


class OutputEventType(str, Enum):
    """Output event type enumeration."""
    MESSAGE = "message"
    TOOL_CALL = "tool_call"
    THINKING = "thinking"
    COMMAND = "command"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_CREATE = "file_create"
    SEARCH = "search"
    PROGRESS = "progress"
    COMPLETE = "complete"


@dataclass
class TokenUsage:
    """Token usage information."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    input_cost: float = 0.0
    output_cost: float = 0.0
    total_cost: float = 0.0


@dataclass
class OutputEvent:
    """Output event from reader."""
    session_id: str
    event_type: OutputEventType
    content: str
    timestamp: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    token_usage: Optional[TokenUsage] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = time.time()


class BaseOutputReader:
    """Base class for output readers.
    
    Events:
        message(event: OutputEvent) - parsed standardized message
    """
    
    @property
    def provider_id(self) -> str:
        """Provider ID this reader supports."""
        raise NotImplementedError
    
    def start_watching(self, session_id: str, work_dir: str) -> None:
        """Start watching for output (called when session is created)."""
        raise NotImplementedError
    
    def bind_conversation_id(self, session_id: str, conversation_id: str) -> None:
        """Bind CLI internal conversation ID to precisely locate output file."""
        raise NotImplementedError
    
    def stop_watching(self, session_id: str) -> None:
        """Stop watching session."""
        raise NotImplementedError
    
    def cleanup(self) -> None:
        """Clean up all resources."""
        raise NotImplementedError
    
    def emit_message(self, event: OutputEvent) -> None:
        """Emit a message event (to be implemented by subclasses)."""
        raise NotImplementedError