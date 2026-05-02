"""State inference engine.

Combines prompt marker detection (precise) and timeout inference (fallback)
to accurately determine session state.

@author ClawTeam
"""

from __future__ import annotations

import re
import time
import logging
from typing import Dict, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SessionStatus(str, Enum):
    """Session status enumeration."""

    STARTING = "starting"
    RUNNING = "running"
    WAITING_INPUT = "waiting_input"
    PAUSED = "paused"
    POSSIBLE_STUCK = "possible_stuck"
    STUCK = "stuck"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class ProviderStateConfig:
    """Provider-specific state configuration."""

    startup_pattern: str = ""
    idle_timeout_ms: int = 300_000  # 5 minutes
    possible_stuck_ms: int = 120_000  # 2 minutes
    stuck_intervention_ms: int = 300_000  # 5 minutes
    startup_stuck_ms: int = 60_000  # 1 minute


# Default state configuration (used when no provider config)
DEFAULT_STATE_CONFIG = ProviderStateConfig()

# Prompt marker detection stability parameters
PROMPT_STABILITY_DELAY_MS = 1000  # Wait for confirmation after marker detection
PROMPT_STABILITY_CHECKS = 2  # Required consecutive stable checks


@dataclass
class PromptDetectionState:
    """Prompt detection state per session."""

    prompt_detected: bool = False
    stability_checks_remaining: int = 0
    stability_snapshot: str = ""
    last_normalized: str = ""
    stable_since: float = 0.0


class StateInference:
    """State inference engine.

    Based on prompt marker + timeout dual mechanism to infer session state.
    """

    def __init__(self):
        """Initialize state inference engine."""
        self._last_output_time: Dict[str, float] = {}
        self._session_status: Dict[str, SessionStatus] = {}
        self._notified_stuck: Set[str] = set()
        self._notified_possible_stuck: Set[str] = set()
        self._startup_phase: Set[str] = set()
        self._notified_startup_stuck: Set[str] = set()
        self._awaiting_user_input: Set[str] = set()
        self._session_state_config: Dict[str, ProviderStateConfig] = {}
        self._startup_patterns: Dict[str, Optional[re.Pattern]] = {}
        self._prompt_detection: Dict[str, PromptDetectionState] = {}
        self._removed_sessions: Set[str] = set()

        # Callbacks
        self._status_callbacks = []

    def register_session_config(
        self, session_id: str, config: Optional[ProviderStateConfig] = None
    ):
        """Register provider state configuration for session.

        Args:
            session_id: Session ID.
            config: Provider-specific configuration.
        """
        merged = config or DEFAULT_STATE_CONFIG
        self._session_state_config[session_id] = merged

        # Compile startup detection regex
        if merged.startup_pattern:
            try:
                self._startup_patterns[session_id] = re.compile(
                    merged.startup_pattern, re.IGNORECASE
                )
            except re.error:
                self._startup_patterns[session_id] = None
        else:
            self._startup_patterns[session_id] = None

    def get_config(self, session_id: str) -> ProviderStateConfig:
        """Get session state configuration.

        Args:
            session_id: Session ID.

        Returns:
            Provider state configuration.
        """
        return self._session_state_config.get(session_id, DEFAULT_STATE_CONFIG)

    def _get_or_create_prompt_state(self, session_id: str) -> PromptDetectionState:
        """Get or create prompt detection state for session.

        Args:
            session_id: Session ID.

        Returns:
            Prompt detection state.
        """
        if session_id not in self._prompt_detection:
            self._prompt_detection[session_id] = PromptDetectionState(stable_since=time.time())
        return self._prompt_detection[session_id]

    def check_startup_pattern(self, session_id: str, clean_data: str) -> bool:
        """Check if output matches startup completion pattern.

        Args:
            session_id: Session ID.
            clean_data: Clean text without ANSI.

        Returns:
            True if startup pattern matched.
        """
        pattern = self._startup_patterns.get(session_id)
        if not pattern or session_id not in self._startup_phase:
            return False

        if pattern.search(clean_data):
            self._mark_startup_complete(session_id)
            return True
        return False

    def receive_output(self, session_id: str, raw_data: str) -> None:
        """Receive raw PTY output data.

        Updates last output time and manages prompt detection.

        Args:
            session_id: Session ID.
            raw_data: Raw output data.
        """
        if session_id in self._removed_sessions:
            return

        self._last_output_time[session_id] = time.time()

        # Start prompt detection if in startup phase
        if session_id in self._startup_phase:
            self._detect_prompt_markers(session_id, raw_data)

    def _detect_prompt_markers(self, session_id: str, raw_data: str) -> None:
        """Detect prompt markers in output.

        Args:
            session_id: Session ID.
            raw_data: Raw output data.
        """
        # Simplified detection logic
        # In a real implementation, this would use TailBuffer and ANSI stripping
        state = self._get_or_create_prompt_state(session_id)

        # Check for common prompt markers
        if not state.prompt_detected:
            # Simple detection for CLI prompts
            prompt_patterns = [
                r"^(>|#|\$|>>>|In \[\d+\]:)",  # CLI prompts
                r"^\s*$",  # Blank line
                r"^Type your question here",  # Interactive prompts
                r"^Press Enter to continue",  # Waiting for input
            ]

            lines = raw_data.split("\n")
            for line in lines[-5:]:  # Check last 5 lines
                for pattern in prompt_patterns:
                    if re.search(pattern, line):
                        logger.debug(
                            "[StateInference] Prompt marker detected for session %s: %s",
                            session_id,
                            line[:50],
                        )
                        state.prompt_detected = True
                        state.stability_checks_remaining = PROMPT_STABILITY_CHECKS
                        state.stability_snapshot = self._normalize_output(raw_data)
                        return

    def _normalize_output(self, data: str) -> str:
        """Normalize output for comparison.

        Args:
            data: Raw output data.

        Returns:
            Normalized text.
        """
        # Simplified normalization
        # In a real implementation, this would strip ANSI and normalize whitespace
        return data.strip()

    def _mark_startup_complete(self, session_id: str) -> None:
        """Mark session startup as complete.

        Args:
            session_id: Session ID.
        """
        self._startup_phase.discard(session_id)
        self._notified_startup_stuck.discard(session_id)
        self.set_session_status(session_id, SessionStatus.RUNNING)
        logger.info("[StateInference] Session %s startup complete", session_id)

    def set_session_status(self, session_id: str, status: SessionStatus) -> None:
        """Manually set session status.

        Args:
            session_id: Session ID.
            status: Session status.
        """
        if session_id in self._removed_sessions:
            return

        self._session_status[session_id] = status
        if status in [SessionStatus.WAITING_INPUT, SessionStatus.PAUSED]:
            self._awaiting_user_input.add(session_id)
        else:
            self._awaiting_user_input.discard(session_id)

        self._notify_status_change(session_id, status)

    def mark_awaiting_user_input(self, session_id: str) -> None:
        """Mark session as waiting for user next input.

        Args:
            session_id: Session ID.
        """
        if session_id in self._removed_sessions:
            return

        self._awaiting_user_input.add(session_id)
        if self._session_status.get(session_id) != SessionStatus.PAUSED:
            self.set_session_status(session_id, SessionStatus.WAITING_INPUT)

    def mark_work_started(self, session_id: str) -> None:
        """Mark user has initiated new input, restore to running state.

        Args:
            session_id: Session ID.
        """
        if session_id in self._removed_sessions:
            return

        self._awaiting_user_input.discard(session_id)
        self._notified_stuck.discard(session_id)
        self._notified_possible_stuck.discard(session_id)
        self._last_output_time[session_id] = time.time()
        self.set_session_status(session_id, SessionStatus.RUNNING)

        # Reset prompt detection state
        if session_id in self._prompt_detection:
            state = self._prompt_detection[session_id]
            state.prompt_detected = False
            state.stability_checks_remaining = 0
            state.stability_snapshot = ""

    def check_stuck_status(self) -> Dict[str, SessionStatus]:
        """Check stuck status for all active sessions.

        Returns:
            Dict mapping session_id to updated status.
        """
        updated_statuses = {}
        now = time.time()

        for session_id in list(self._session_status.keys()):
            if session_id in self._removed_sessions:
                continue

            status = self._session_status.get(session_id)
            if status in [SessionStatus.COMPLETE, SessionStatus.ERROR]:
                continue

            last_output = self._last_output_time.get(session_id, 0)
            idle_duration_ms = (now - last_output) * 1000

            config = self.get_config(session_id)

            # Check stuck conditions
            if session_id in self._startup_phase:
                if idle_duration_ms >= config.startup_stuck_ms:
                    if session_id not in self._notified_startup_stuck:
                        updated_statuses[session_id] = SessionStatus.STUCK
                        self._notified_startup_stuck.add(session_id)
                        logger.warning(
                            "[StateInference] Session %s startup stuck for %d ms",
                            session_id,
                            idle_duration_ms,
                        )
            else:
                if idle_duration_ms >= config.stuck_intervention_ms:
                    if session_id not in self._notified_stuck:
                        updated_statuses[session_id] = SessionStatus.STUCK
                        self._notified_stuck.add(session_id)
                        logger.warning(
                            "[StateInference] Session %s stuck for %d ms",
                            session_id,
                            idle_duration_ms,
                        )
                elif idle_duration_ms >= config.possible_stuck_ms:
                    if session_id not in self._notified_possible_stuck:
                        updated_statuses[session_id] = SessionStatus.POSSIBLE_STUCK
                        self._notified_possible_stuck.add(session_id)
                        logger.info(
                            "[StateInference] Session %s possibly stuck for %d ms",
                            session_id,
                            idle_duration_ms,
                        )
                elif idle_duration_ms >= config.idle_timeout_ms:
                    if status != SessionStatus.WAITING_INPUT:
                        updated_statuses[session_id] = SessionStatus.WAITING_INPUT
                        self.mark_awaiting_user_input(session_id)
                        logger.debug(
                            "[StateInference] Session %s idle for %d ms",
                            session_id,
                            idle_duration_ms,
                        )

            # Update status if changed
            if session_id in updated_statuses:
                self.set_session_status(session_id, updated_statuses[session_id])

        return updated_statuses

    def get_session_status(self, session_id: str) -> Optional[SessionStatus]:
        """Get current session status.

        Args:
            session_id: Session ID.

        Returns:
            Session status, or None if not found.
        """
        return self._session_status.get(session_id)

    def remove_session(self, session_id: str) -> None:
        """Remove session from inference engine.

        Args:
            session_id: Session ID.
        """
        self._removed_sessions.add(session_id)
        self._last_output_time.pop(session_id, None)
        self._session_status.pop(session_id, None)
        self._notified_stuck.discard(session_id)
        self._notified_possible_stuck.discard(session_id)
        self._startup_phase.discard(session_id)
        self._notified_startup_stuck.discard(session_id)
        self._awaiting_user_input.discard(session_id)
        self._session_state_config.pop(session_id, None)
        self._startup_patterns.pop(session_id, None)
        self._prompt_detection.pop(session_id, None)

    def add_status_callback(self, callback):
        """Add status change callback.

        Args:
            callback: Callback function taking (session_id, status).
        """
        self._status_callbacks.append(callback)

    def _notify_status_change(self, session_id: str, status: SessionStatus):
        """Notify status change to callbacks.

        Args:
            session_id: Session ID.
            status: New status.
        """
        for callback in self._status_callbacks:
            try:
                callback(session_id, status)
            except Exception as e:
                logger.error("Error in status change callback: %s", e)
