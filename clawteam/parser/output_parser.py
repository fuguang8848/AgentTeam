"""Output parsing engine for ClawTeam multi-agent teams.

Parses AI provider outputs, detects activity events, estimates token usage,
and supports event deduplication.

Inspired by SpectrAI's OutputParser.ts.
"""

from __future__ import annotations

import json
import re
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from clawteam.parser.types import (
    ActivityEvent,
    ActivityEventType,
    ParserState,
    ParserRule,
    ConfirmationDetection,
    UsageSummary,
)
from clawteam.parser.rules import PARSER_RULES
from clawteam.parser.confirmation_detector import ConfirmationDetector, detect_confirmation
from clawteam.parser.usage_estimator import UsageEstimator


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    ansi_pattern = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")
    return ansi_pattern.sub("", text)


def _get_or_create_state(
    state_map: dict[str, ParserState],
    session_id: str,
) -> ParserState:
    """Get or create parser state for a session."""
    if session_id not in state_map:
        state_map[session_id] = ParserState(
            session_id=session_id,
            last_output_time=time.time(),
        )
    return state_map[session_id]


class OutputParser:
    """Output parsing engine for AI provider outputs.
    
    Features:
    - Multi-provider support (Claude Code, Codex, Gemini, etc.)
    - Event deduplication with configurable windows
    - Token usage estimation
    - Confirmation request detection
    - Custom rule loading
    """
    
    # Deduplication windows
    DEDUPE_WINDOW_MS = 3000  # 3 seconds for normal events
    INTERVENTION_DEDUPE_WINDOW_MS = 30000  # 30 seconds for intervention events
    
    # Text buffer flush delay
    TEXT_FLUSH_DELAY_MS = 2000  # 2 seconds
    
    def __init__(
        self,
        rules: list[ParserRule] | None = None,
        custom_rules_path: Path | None = None,
        usage_estimator: UsageEstimator | None = None,
    ):
        self._rules = rules or PARSER_RULES
        self._custom_rules_path = custom_rules_path
        
        # Session state
        self._line_buffer: dict[str, str] = {}
        self._state_map: dict[str, ParserState] = {}
        self._session_provider_map: dict[str, str] = {}
        
        # Deduplication cache: session_id -> {type+detail -> timestamp}
        self._dedupe_cache: dict[str, dict[str, float]] = defaultdict(dict)
        
        # Event handlers
        self._event_handlers: list[Callable[[ActivityEvent], None]] = []
        
        # Token usage estimator
        self._usage_estimator = usage_estimator or UsageEstimator()
        
        # Confirmation detector
        self._confirmation_detector = ConfirmationDetector()
        
        # Provider-specific confirmation detectors
        self._provider_confirm_detectors: dict[str, ConfirmationDetector] = {}
        
        # Lock for thread safety
        self._lock = threading.Lock()
        
        # Load custom rules if path provided
        if custom_rules_path and custom_rules_path.exists():
            self._load_custom_rules()
    
    def _load_custom_rules(self) -> None:
        """Load custom rules from JSON file."""
        if self._custom_rules_path is None or not self._custom_rules_path.exists():
            return
        
        try:
            content = self._custom_rules_path.read_text("utf-8")
            custom_rules_data = json.loads(content)
            
            if not isinstance(custom_rules_data, list):
                return
            
            custom_rules = []
            for rule_data in custom_rules_data:
                rule = self._validate_and_convert_rule(rule_data)
                if rule:
                    custom_rules.append(rule)
            
            # Merge and sort by priority
            self._rules = sorted(
                self._rules + custom_rules,
                key=lambda r: r.priority,
                reverse=True,
            )
            
        except (json.JSONDecodeError, IOError) as e:
            pass
    
    def _validate_and_convert_rule(self, data: dict[str, Any]) -> ParserRule | None:
        """Validate and convert a custom rule from JSON."""
        try:
            type_str = data.get("type")
            if not type_str:
                return None
            
            event_type = ActivityEventType(type_str)
            priority = data.get("priority", 10)
            provider_id = data.get("provider_id")
            
            patterns_str = data.get("patterns", [])
            patterns = []
            for p in patterns_str:
                try:
                    patterns.append(re.compile(p, re.IGNORECASE))
                except re.error:
                    pass
            
            if not patterns:
                return None
            
            detail_template = data.get("detail_template", "")
            
            def extract_detail(line: str) -> str:
                for pattern in patterns:
                    match = pattern.search(line)
                    if match:
                        # Replace $1, $2, etc. with captured groups
                        result = detail_template
                        for i, group in enumerate(match.groups()):
                            if group:
                                result = result.replace(f"${i+1}", group[:80])
                        return result
                return line.strip()[:80]
            
            return ParserRule(
                type=event_type,
                priority=priority,
                provider_id=provider_id,
                patterns=patterns,
                extract_detail=extract_detail,
            )
            
        except (ValueError, KeyError):
            return None
    
    def add_event_handler(self, handler: Callable[[ActivityEvent], None]) -> None:
        """Add an event handler to be called when events are detected."""
        self._event_handlers.append(handler)
    
    def remove_event_handler(self, handler: Callable[[ActivityEvent], None]) -> None:
        """Remove an event handler."""
        try:
            self._event_handlers.remove(handler)
        except ValueError:
            pass
    
    def set_provider(self, session_id: str, provider_id: str) -> None:
        """Set the provider ID for a session."""
        with self._lock:
            self._session_provider_map[session_id] = provider_id
    
    def get_provider(self, session_id: str) -> str | None:
        """Get the provider ID for a session."""
        with self._lock:
            return self._session_provider_map.get(session_id)
    
    def parse(self, session_id: str, data: str) -> list[ActivityEvent]:
        """Parse output data and return detected events.
        
        Args:
            session_id: The session ID
            data: Raw output data (may contain multiple lines)
            
        Returns:
            List of detected ActivityEvent objects
        """
        # Accumulate usage
        self._usage_estimator.accumulate_usage(session_id, data)
        
        # Get provider
        provider_id = self.get_provider(session_id)
        
        # Get/create state
        with self._lock:
            state = _get_or_create_state(self._state_map, session_id)
        
        # Get line buffer
        buffer = self._line_buffer.get(session_id, "")
        new_buffer = buffer + data
        
        # Find last newline
        last_newline = new_buffer.rfind("\n")
        if last_newline == -1:
            # No complete lines, buffer everything
            self._line_buffer[session_id] = new_buffer
            return []
        
        # Keep incomplete line in buffer
        incomplete_line = new_buffer[last_newline + 1:]
        self._line_buffer[session_id] = incomplete_line
        
        # Process complete lines
        complete_lines = new_buffer[:last_newline].split("\n")
        
        events = []
        for line in complete_lines:
            # Strip ANSI codes
            clean_line = _strip_ansi(line)
            
            # Parse the line
            event = self._parse_line(session_id, clean_line, provider_id, state)
            if event:
                events.append(event)
                # Call handlers
                for handler in self._event_handlers:
                    try:
                        handler(event)
                    except Exception:
                        pass
        
        return events
    
    def _parse_line(
        self,
        session_id: str,
        line: str,
        provider_id: str | None,
        state: ParserState,
    ) -> ActivityEvent | None:
        """Parse a single line and detect events."""
        if not line.strip():
            return None
        
        # Update state
        state.last_output_time = time.time()
        
        # Check for confirmation first (high priority)
        confirmation = self._confirmation_detector.detect(line)
        if confirmation:
            event_type = ActivityEventType.WAITING_CONFIRMATION
            detail = f"等待确认: {confirmation.prompt_text}"
            
            # Check deduplication
            if self._is_duplicated(session_id, event_type, detail, is_intervention=True):
                return None
            
            return ActivityEvent.create(
                event_type=event_type,
                session_id=session_id,
                provider_id=provider_id or "unknown",
                detail=detail,
                confidence=confirmation.confidence,
                raw_line=line,
            )
        
        # Apply parsing rules
        for rule in self._rules:
            if rule.matches(line, provider_id):
                detail = rule.get_detail(line)
                
                # Check deduplication
                if self._is_duplicated(session_id, rule.type, detail, is_intervention=False):
                    continue
                
                # Update state
                state.last_event_type = rule.type
                
                return ActivityEvent.create(
                    event_type=rule.type,
                    session_id=session_id,
                    provider_id=provider_id or "unknown",
                    detail=detail,
                    confidence="high",
                    raw_line=line,
                )
        
        # No rule matched - could be AI message text
        # We don't emit AI_MESSAGE events for every line to avoid noise
        return None
    
    def _is_duplicated(
        self,
        session_id: str,
        event_type: ActivityEventType,
        detail: str,
        is_intervention: bool = False,
    ) -> bool:
        """Check if an event is duplicated within the deduplication window."""
        key = f"{event_type.value}:{detail}"
        now = time.time() * 1000  # milliseconds
        
        window_ms = self.INTERVENTION_DEDUPE_WINDOW_MS if is_intervention else self.DEDUPE_WINDOW_MS
        
        with self._lock:
            cache = self._dedupe_cache[session_id]
            last_time = cache.get(key)
            
            if last_time and now - last_time < window_ms:
                return True
            
            # Update cache
            cache[key] = now
            return False
    
    def get_usage_summary(self) -> UsageSummary:
        """Get token usage summary."""
        return self._usage_estimator.get_summary()
    
    def get_session_usage(self, session_id: str) -> int:
        """Get token usage for a specific session."""
        return self._usage_estimator.get_session_usage(session_id)
    
    def get_usage_estimator(self) -> UsageEstimator:
        """Get the usage estimator instance."""
        return self._usage_estimator
    
    def mark_session_ended(self, session_id: str) -> UsageSummary:
        """Mark a session as ended."""
        # Clear line buffer
        self._line_buffer.pop(session_id, None)
        
        # Clear state
        with self._lock:
            self._state_map.pop(session_id, None)
            self._dedupe_cache.pop(session_id, None)
            self._session_provider_map.pop(session_id, None)
        
        return self._usage_estimator.mark_session_ended(session_id)
    
    def clear_session(self, session_id: str) -> None:
        """Clear all session resources."""
        self._line_buffer.pop(session_id, None)
        
        with self._lock:
            self._state_map.pop(session_id, None)
            self._dedupe_cache.pop(session_id, None)
            self._session_provider_map.pop(session_id, None)
        
        self._usage_estimator.reset_session_usage(session_id)
    
    def cleanup(self) -> None:
        """Clean up all resources."""
        self._line_buffer.clear()
        with self._lock:
            self._state_map.clear()
            self._dedupe_cache.clear()
            self._session_provider_map.clear()
        self._usage_estimator.cleanup()


# Singleton instance
_parser_instance: OutputParser | None = None
_parser_lock = threading.Lock()


def get_parser() -> OutputParser:
    """Get the global parser instance."""
    global _parser_instance
    with _parser_lock:
        if _parser_instance is None:
            _parser_instance = OutputParser()
        return _parser_instance


def parse_output(session_id: str, data: str) -> list[ActivityEvent]:
    """Parse output using the global parser instance."""
    return get_parser().parse(session_id, data)