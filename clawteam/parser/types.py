"""Type definitions for the output parsing engine."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional


class ActivityEventType(str, Enum):
    """Types of activity events detected from AI provider outputs."""
    
    # File operations
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    FILE_DELETED = "file_deleted"
    
    # Command execution
    COMMAND_EXECUTED = "command_executed"
    
    # Search operations
    SEARCH = "search"
    
    # Tool usage
    TOOL_USE = "tool_use"
    
    # AI output
    AI_MESSAGE = "ai_message"
    
    # Status events
    THINKING = "thinking"
    WAITING_CONFIRMATION = "waiting_confirmation"
    CONTEXT_SUMMARY = "context_summary"
    
    # Task lifecycle
    TASK_COMPLETE = "task_complete"
    ERROR = "error"
    
    # Confirmation
    CONFIRMATION = "confirmation"


@dataclass
class ActivityEvent:
    """A single activity event detected from AI output."""
    
    event_id: str
    event_type: ActivityEventType
    timestamp: str
    session_id: str
    provider_id: str
    detail: str
    confidence: str = "high"  # high, medium, low
    raw_line: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.event_id:
            self.event_id = uuid.uuid4().hex
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "provider_id": self.provider_id,
            "detail": self.detail,
            "confidence": self.confidence,
        }
        if self.raw_line:
            result["raw_line"] = self.raw_line
        if self.metadata:
            result["metadata"] = self.metadata
        return result
    
    @classmethod
    def create(
        cls,
        event_type: ActivityEventType,
        session_id: str,
        provider_id: str,
        detail: str,
        confidence: str = "high",
        raw_line: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ActivityEvent:
        """Create a new activity event with auto-generated ID and timestamp."""
        return cls(
            event_id=uuid.uuid4().hex,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=session_id,
            provider_id=provider_id,
            detail=detail,
            confidence=confidence,
            raw_line=raw_line,
            metadata=metadata or {},
        )


@dataclass
class ParserState:
    """Parser state for a single session."""
    
    session_id: str
    last_event_type: ActivityEventType | None = None
    last_output_time: float = 0.0
    is_thinking: bool = False
    text_buffer_lines: list[str] = field(default_factory=list)
    text_buffer_start_time: float = 0.0
    flush_timer_handle: Any | None = None  # Timer handle for flushing text buffer


@dataclass
class ParserRule:
    """A parsing rule for detecting events from output lines."""
    
    type: ActivityEventType
    priority: int
    provider_id: str | None = None  # None = applies to all providers
    patterns: list[Any] = field(default_factory=list)  # Regex patterns
    extract_detail: Callable[[str], str] | None = None
    
    def matches(self, line: str, provider_id: str | None = None) -> bool:
        """Check if this rule matches the given line."""
        # Provider-specific check
        if self.provider_id and provider_id and self.provider_id != provider_id:
            return False
        
        import re
        for pattern in self.patterns:
            if isinstance(pattern, str):
                pattern = re.compile(pattern, re.IGNORECASE)
            if pattern.search(line):
                return True
        return False
    
    def get_detail(self, line: str) -> str:
        """Extract detail from the matched line."""
        if self.extract_detail:
            return self.extract_detail(line)
        return line.strip()[:80]


@dataclass
class ConfirmationDetection:
    """Result of confirmation request detection."""
    
    confidence: str  # high, medium
    prompt_text: str
    original_line: str


@dataclass
class UsageSummary:
    """Token usage summary."""
    
    total_tokens: int = 0
    total_minutes: int = 0
    today_tokens: int = 0
    today_minutes: int = 0
    active_sessions: int = 0
    session_breakdown: dict[str, int] = field(default_factory=dict)