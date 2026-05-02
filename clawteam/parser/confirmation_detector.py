"""Confirmation request detector for AI provider outputs.

Detects when an AI agent is waiting for user confirmation.
Inspired by SpectrAI's ConfirmationDetector.ts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from clawteam.parser.types import ConfirmationDetection


# Default high-confidence confirmation patterns
DEFAULT_HIGH_PATTERNS = [
    re.compile(r"\(?Y/n\)?", re.IGNORECASE),
    re.compile(r"\(?y/N\)?", re.IGNORECASE),
    re.compile(r"\[Y/n\]", re.IGNORECASE),
    re.compile(r"\[y/N\]", re.IGNORECASE),
    re.compile(r"\(?yes/no\)?", re.IGNORECASE),
    re.compile(r"Allow\s+.+\?\s*\(?y\)?", re.IGNORECASE),
    re.compile(r"Press Enter to continue", re.IGNORECASE),
]

# Default medium-confidence confirmation patterns
DEFAULT_MEDIUM_PATTERNS = [
    re.compile(r"Do you want to proceed", re.IGNORECASE),
    re.compile(r"Continue\?", re.IGNORECASE),
    re.compile(r"Are you sure", re.IGNORECASE),
    re.compile(r"Shall I (?:continue|proceed)", re.IGNORECASE),
    re.compile(r"Would you like me to", re.IGNORECASE),
]


@dataclass
class ProviderConfirmationConfig:
    """Configuration for provider-specific confirmation patterns."""

    high_patterns: list[str] = field(default_factory=list)
    medium_patterns: list[str] = field(default_factory=list)


class ConfirmationDetector:
    """Detects confirmation requests in AI output lines."""

    def __init__(
        self,
        high_patterns: list[re.Pattern] | None = None,
        medium_patterns: list[re.Pattern] | None = None,
    ):
        self.high_patterns = high_patterns or DEFAULT_HIGH_PATTERNS
        self.medium_patterns = medium_patterns or DEFAULT_MEDIUM_PATTERNS

    @classmethod
    def from_config(cls, config: ProviderConfirmationConfig) -> ConfirmationDetector:
        """Create detector from provider configuration."""
        high = []
        for pattern_str in config.high_patterns:
            try:
                high.append(re.compile(pattern_str, re.IGNORECASE))
            except re.error:
                pass

        medium = []
        for pattern_str in config.medium_patterns:
            try:
                medium.append(re.compile(pattern_str, re.IGNORECASE))
            except re.error:
                pass

        # Merge with defaults
        return cls(
            high_patterns=high + DEFAULT_HIGH_PATTERNS,
            medium_patterns=medium + DEFAULT_MEDIUM_PATTERNS,
        )

    def detect(self, line: str) -> ConfirmationDetection | None:
        """Detect confirmation request in a line.

        Returns ConfirmationDetection if found, None otherwise.
        """
        # Check high-confidence patterns first
        for pattern in self.high_patterns:
            if pattern.search(line):
                # Try to extract the prompt text
                match = re.search(r"Allow\s+(.+?)\s*\?", line, re.IGNORECASE)
                prompt_text = match.group(1) if match else line.strip()
                return ConfirmationDetection(
                    confidence="high",
                    prompt_text=prompt_text,
                    original_line=line,
                )

        # Check medium-confidence patterns
        for pattern in self.medium_patterns:
            if pattern.search(line):
                return ConfirmationDetection(
                    confidence="medium",
                    prompt_text=line.strip(),
                    original_line=line,
                )

        return None


# Singleton instance for default detection
_default_detector: ConfirmationDetector | None = None


def get_default_detector() -> ConfirmationDetector:
    """Get the default confirmation detector instance."""
    global _default_detector
    if _default_detector is None:
        _default_detector = ConfirmationDetector()
    return _default_detector


def detect_confirmation(line: str) -> ConfirmationDetection | None:
    """Detect confirmation request using the default detector."""
    return get_default_detector().detect(line)
