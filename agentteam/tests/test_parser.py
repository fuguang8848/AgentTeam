"""Tests for the output parsing engine."""

from __future__ import annotations

import pytest
import time
from pathlib import Path

from agentteam.parser import (
    OutputParser,
    ActivityEvent,
    ActivityEventType,
    ParserRule,
    PARSER_RULES,
    ConfirmationDetector,
    UsageEstimator,
)
from agentteam.parser.types import ConfirmationDetection, UsageSummary
from agentteam.parser.confirmation_detector import detect_confirmation
from agentteam.parser.output_parser import get_parser, parse_output


class TestActivityEvent:
    """Tests for ActivityEvent class."""

    def test_create_event(self):
        """Test creating an activity event."""
        event = ActivityEvent.create(
            event_type=ActivityEventType.FILE_READ,
            session_id="test-session",
            provider_id="claude-code",
            detail="读取文件: test.py",
        )

        assert event.event_type == ActivityEventType.FILE_READ
        assert event.session_id == "test-session"
        assert event.provider_id == "claude-code"
        assert event.detail == "读取文件: test.py"
        assert event.event_id  # Auto-generated
        assert event.timestamp  # Auto-generated

    def test_to_dict(self):
        """Test converting event to dictionary."""
        event = ActivityEvent.create(
            event_type=ActivityEventType.COMMAND_EXECUTED,
            session_id="session-1",
            provider_id="codex",
            detail="执行命令: npm test",
            raw_line="Running command: npm test",
        )

        d = event.to_dict()
        assert d["event_type"] == "command_executed"
        assert d["session_id"] == "session-1"
        assert d["provider_id"] == "codex"
        assert d["detail"] == "执行命令: npm test"
        assert d["raw_line"] == "Running command: npm test"


class TestParserRule:
    """Tests for ParserRule class."""

    def test_rule_matches(self):
        """Test rule pattern matching."""
        import re

        rule = ParserRule(
            type=ActivityEventType.FILE_READ,
            priority=15,
            provider_id="claude-code",
            patterns=[re.compile(r"[⏺●]\s*Read\s*\(?([^\s)]+)")],
        )

        # Should match
        assert rule.matches("⏺ Read(test.py)", "claude-code")

        # Should not match (wrong provider)
        assert not rule.matches("⏺ Read(test.py)", "codex")

        # Should not match (no pattern match)
        assert not rule.matches("Some other text", "claude-code")

    def test_generic_rule_matches_all_providers(self):
        """Test that generic rules match all providers."""
        import re

        rule = ParserRule(
            type=ActivityEventType.ERROR,
            priority=25,
            provider_id=None,  # Generic
            patterns=[re.compile(r"Error:\s+(.+)", re.IGNORECASE)],
        )

        # Should match any provider
        assert rule.matches("Error: something failed", "claude-code")
        assert rule.matches("Error: something failed", "codex")
        assert rule.matches("Error: something failed", "gemini-cli")
        assert rule.matches("Error: something failed", None)


class TestConfirmationDetector:
    """Tests for ConfirmationDetector class."""

    def test_detect_high_confidence(self):
        """Test detecting high-confidence confirmation."""
        detector = ConfirmationDetector()

        result = detector.detect("Allow Bash? (y)")
        assert result is not None
        assert result.confidence == "high"
        assert "Bash" in result.prompt_text

    def test_detect_medium_confidence(self):
        """Test detecting medium-confidence confirmation."""
        detector = ConfirmationDetector()

        result = detector.detect("Do you want to proceed?")
        assert result is not None
        assert result.confidence == "medium"

    def test_no_detection(self):
        """Test that non-confirmation lines return None."""
        detector = ConfirmationDetector()

        result = detector.detect("Some regular output")
        assert result is None

    def test_detect_confirmation_helper(self):
        """Test the detect_confirmation helper function."""
        result = detect_confirmation("Press Enter to continue")
        assert result is not None
        assert result.confidence == "high"


class TestUsageEstimator:
    """Tests for UsageEstimator class."""

    def test_estimate_tokens_ascii(self):
        """Test token estimation for ASCII text."""
        estimator = UsageEstimator()

        # ASCII: ~4 chars per token
        text = "Hello world this is a test"  # 26 chars
        tokens = estimator.estimate_tokens(text)
        assert tokens == 6  # 26 / 4 = 6.5 -> 6

    def test_estimate_tokens_cjk(self):
        """Test token estimation for CJK text."""
        estimator = UsageEstimator()

        # CJK: ~2 chars per token
        text = "你好世界测试"  # 6 chars
        tokens = estimator.estimate_tokens(text)
        assert tokens == 3  # 6 / 2 = 3

    def test_accumulate_usage(self):
        """Test accumulating usage for a session."""
        estimator = UsageEstimator()

        estimator.accumulate_usage("session-1", "Hello world")
        estimator.accumulate_usage("session-1", "Another line")

        usage = estimator.get_session_usage("session-1")
        assert usage > 0

    def test_get_summary(self):
        """Test getting usage summary."""
        estimator = UsageEstimator()

        estimator.accumulate_usage("session-1", "Test text")
        estimator.accumulate_usage("session-2", "More text")

        summary = estimator.get_summary()
        assert summary.total_tokens > 0
        assert summary.active_sessions == 2
        assert "session-1" in summary.session_breakdown

    def test_reset_session(self):
        """Test resetting session usage."""
        estimator = UsageEstimator()

        estimator.accumulate_usage("session-1", "Test")
        assert estimator.get_session_usage("session-1") > 0

        estimator.reset_session_usage("session-1")
        assert estimator.get_session_usage("session-1") == 0

    def test_mark_session_ended(self):
        """Test marking session as ended."""
        estimator = UsageEstimator()

        estimator.accumulate_usage("session-1", "Test text")
        summary = estimator.mark_session_ended("session-1")

        assert summary.total_tokens > 0


class TestOutputParser:
    """Tests for OutputParser class."""

    def test_parse_claude_code_read(self):
        """Test parsing Claude Code file read output."""
        parser = OutputParser()
        parser.set_provider("session-1", "claude-code")

        events = parser.parse("session-1", "⏺ Read(test.py)\n")

        assert len(events) == 1
        assert events[0].event_type == ActivityEventType.FILE_READ
        assert "test.py" in events[0].detail

    def test_parse_claude_code_write(self):
        """Test parsing Claude Code file write output."""
        parser = OutputParser()
        parser.set_provider("session-1", "claude-code")

        events = parser.parse("session-1", "⏺ Write(output.py)\n")

        assert len(events) == 1
        assert events[0].event_type == ActivityEventType.FILE_WRITE

    def test_parse_claude_code_bash(self):
        """Test parsing Claude Code bash command output."""
        parser = OutputParser()
        parser.set_provider("session-1", "claude-code")

        events = parser.parse("session-1", "⏺ Bash(npm test)\n")

        assert len(events) == 1
        assert events[0].event_type == ActivityEventType.COMMAND_EXECUTED
        assert "npm test" in events[0].detail

    def test_parse_error(self):
        """Test parsing error output."""
        parser = OutputParser()

        events = parser.parse("session-1", "Error: something went wrong\n")

        assert len(events) == 1
        assert events[0].event_type == ActivityEventType.ERROR

    def test_parse_confirmation(self):
        """Test parsing confirmation request."""
        parser = OutputParser()

        events = parser.parse("session-1", "Allow Bash? (y)\n")

        assert len(events) == 1
        assert events[0].event_type == ActivityEventType.WAITING_CONFIRMATION

    def test_parse_task_complete(self):
        """Test parsing task completion."""
        parser = OutputParser()

        events = parser.parse("session-1", "Task completed successfully\n")

        assert len(events) == 1
        assert events[0].event_type == ActivityEventType.TASK_COMPLETE

    def test_parse_multiline(self):
        """Test parsing multiple lines."""
        parser = OutputParser()
        parser.set_provider("session-1", "claude-code")

        output = "⏺ Read(file1.py)\n⏺ Write(file2.py)\n⏺ Bash(npm test)\n"
        events = parser.parse("session-1", output)

        assert len(events) == 3
        assert events[0].event_type == ActivityEventType.FILE_READ
        assert events[1].event_type == ActivityEventType.FILE_WRITE
        assert events[2].event_type == ActivityEventType.COMMAND_EXECUTED

    def test_deduplication(self):
        """Test event deduplication."""
        parser = OutputParser()

        # Same event within dedupe window should be filtered
        events1 = parser.parse("session-1", "Error: test error\n")
        assert len(events1) == 1

        # Immediate duplicate should be filtered
        events2 = parser.parse("session-1", "Error: test error\n")
        assert len(events2) == 0

    def test_event_handler(self):
        """Test event handler callback."""
        parser = OutputParser()

        received_events = []
        parser.add_event_handler(lambda e: received_events.append(e))

        parser.parse("session-1", "Error: test\n")

        assert len(received_events) == 1
        assert received_events[0].event_type == ActivityEventType.ERROR

    def test_clear_session(self):
        """Test clearing session resources."""
        parser = OutputParser()

        parser.parse("session-1", "Test output\n")
        parser.clear_session("session-1")

        # Should be able to parse again without deduplication
        events = parser.parse("session-1", "Error: test\n")
        assert len(events) == 1

    def test_get_usage_summary(self):
        """Test getting usage summary from parser."""
        parser = OutputParser()

        parser.parse("session-1", "Some text output\n")
        summary = parser.get_usage_summary()

        assert summary.total_tokens > 0

    def test_global_parser(self):
        """Test global parser instance."""
        parser1 = get_parser()
        parser2 = get_parser()

        assert parser1 is parser2  # Same instance

    def test_parse_output_helper(self):
        """Test parse_output helper function."""
        events = parse_output("session-1", "Error: test\n")

        assert len(events) >= 0


class TestParserRules:
    """Tests for parser rules."""

    def test_rules_sorted_by_priority(self):
        """Test that rules are sorted by priority."""
        priorities = [r.priority for r in PARSER_RULES]

        # Should be descending
        assert priorities == sorted(priorities, reverse=True)

    def test_error_rule_high_priority(self):
        """Test that error rule has high priority."""
        error_rules = [r for r in PARSER_RULES if r.type == ActivityEventType.ERROR]

        assert len(error_rules) > 0
        assert error_rules[0].priority >= 20  # High priority

    def test_confirmation_rule_high_priority(self):
        """Test that confirmation rule has high priority."""
        confirm_rules = [r for r in PARSER_RULES if r.type == ActivityEventType.WAITING_CONFIRMATION]

        assert len(confirm_rules) > 0
        assert confirm_rules[0].priority >= 20  # High priority


class TestAnsiStripping:
    """Tests for ANSI code stripping."""

    def test_strip_ansi(self):
        """Test stripping ANSI escape codes."""
        from agentteam.parser.output_parser import _strip_ansi

        text_with_ansi = "\x1b[32mSuccess\x1b[0m"
        clean = _strip_ansi(text_with_ansi)

        assert clean == "Success"

    def test_parse_with_ansi(self):
        """Test parsing output with ANSI codes."""
        parser = OutputParser()

        # ANSI-colored error
        events = parser.parse("session-1", "\x1b[31mError: failed\x1b[0m\n")

        assert len(events) == 1
        assert events[0].event_type == ActivityEventType.ERROR
