"""Agent readiness detector configuration."""

from __future__ import annotations

from typing import Optional
from dataclasses import dataclass


@dataclass
class DetectorConfig:
    """Configuration for AgentReadinessDetector.
    
    Args:
        prompt_markers: Provider-specific regex patterns for prompt markers.
        max_wait_ms: Maximum time to wait for readiness (milliseconds).
        quiescence_threshold_ms: Output stability threshold (milliseconds).
        post_reset_cooldown_ms: Cooldown after reset to prevent echo misdetection.
    """
    prompt_markers: Optional[list[str]] = None
    max_wait_ms: int = 180_000  # 3 minutes
    quiescence_threshold_ms: int = 3_000  # 3 seconds
    post_reset_cooldown_ms: int = 2_000  # 2 seconds


# Provider-specific prompt markers
PROVIDER_PROMPT_MARKERS = {
    "claude-code": [r"^(>|#|>>>|In \[\d+\]:|\$\s)", r"^\s*$", r"^Type your question here"],
    "codex": [r"^\$\s", r"^>", r"^>>>", r"^In \[\d+\]:"],
    "openai": [r"^User:", r"^Assistant:", r"^System:", r"^\s*$"],
    "anthropic": [r"^\n\nAssistant:", r"^\n\nHuman:", r"^\s*$"],
}

DEFAULT_PROMPT_MARKERS = [
    r"^(>|#|\$|>>>|In \[\d+\]:)",  # CLI prompts
    r"^\s*$",  # Blank line
    r"^Type your question here",  # Interactive prompts
    r"^Press Enter to continue",  # Waiting for input
]