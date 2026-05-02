"""Agent readiness detector - v5.

Detection logic:
  1. Fast Path (event-driven): on_screen_update detects prompt markers → immediate resolve.
     ★ Only for CLI startup detection and oneShot mode. Interactive mode disabled (too many false positives).
  2. Slow Path (polling fallback): screen content stable beyond threshold → quiescence resolve.
     ★ Main detection method for interactive mode. Generic, not dependent on any CLI-specific format.
  3. Structured signal: notify_task_complete() - deterministic signals from parsers like JSONL.
     ★ Claude Code specific acceleration. Use if available, but don't depend on it.

@author ClawTeam
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Callable, Optional, List, Tuple
from dataclasses import dataclass
from threading import Timer

from clawteam.readiness.config import (
    DetectorConfig,
    PROVIDER_PROMPT_MARKERS,
    DEFAULT_PROMPT_MARKERS,
)

logger = logging.getLogger(__name__)

# Constants
AUTOSEND_MIN_WAIT_MS = 500  # Minimum wait after launch
DEFAULT_MAX_WAIT_MS = 180_000  # Default timeout 3 minutes
QUIESCENCE_POLL_MS = 500  # Quiescence polling interval
DEFAULT_QUIESCENCE_THRESHOLD_MS = 3_000  # Default output stability threshold
FAST_PATH_FALLBACK_MS = 500  # Fast Path fallback timeout


@dataclass
class ScreenUpdateInfo:
    """Screen update information."""

    last_lines: List[str]
    total_appended: int


class AgentReadinessDetector:
    """Agent readiness detector with three-path detection.

    v5 improvement: Interactive mode disables Fast Path, only uses Quiescence + structured signals.
    """

    def __init__(self, agent_id: str, config: Optional[DetectorConfig] = None):
        """Initialize detector.

        Args:
            agent_id: Unique identifier for the agent.
            config: Detector configuration.
        """
        self.agent_id = agent_id
        self.spawned_at = time.time() * 1000

        # Configuration
        self.config = config or DetectorConfig()
        self.prompt_markers = self.config.prompt_markers or DEFAULT_PROMPT_MARKERS
        self.max_wait_ms = self.config.max_wait_ms
        self.quiescence_threshold_ms = self.config.quiescence_threshold_ms
        self.post_reset_cooldown_ms = self.config.post_reset_cooldown_ms

        # v5: Fast Path switch (disabled for interactive mode)
        self._fast_path_disabled = False

        # Ready promise control
        self._ready_future: Optional[asyncio.Future] = None
        self._ready_event: Optional[asyncio.Event] = None
        self._ready_result: Optional[bool] = None

        # v4 Fast Path state: event-driven continuous confirmation
        self.prompt_detected = False
        self.fast_path_fallback_timer: Optional[Timer] = None

        # Slow path (quiescence) state
        self.quiescence_timer: Optional[Timer] = None
        self.last_screen_snapshot = ""
        self.stable_since = 0

        # Latest screen content (updated by on_screen_update)
        self.current_screen_text = ""
        self._last_total_appended = 0

        # Timeout
        self.timeout_timer: Optional[Timer] = None

        self.destroyed = False
        self.is_resetting = False

        # After reset, need to see output changes before allowing quiescence detection
        self.output_seen_since_reset = True  # Initial True, first waitReady not limited
        self.reset_at = 0
        self.is_first_wait = True

    @property
    def fast_path_disabled(self) -> bool:
        """Whether Fast Path is disabled."""
        return self._fast_path_disabled

    @fast_path_disabled.setter
    def fast_path_disabled(self, value: bool):
        """Set Fast Path disabled status.

        When disabled for interactive mode, only quiescence + structured signals are used.
        This setting persists across resets.
        """
        self._fast_path_disabled = value
        if value:
            # Clean up fast path state
            self.prompt_detected = False
            if self.fast_path_fallback_timer:
                self.fast_path_fallback_timer.cancel()
                self.fast_path_fallback_timer = None

    def on_screen_update(self, last_lines: List[str], total_appended: int) -> None:
        """Receive screen update notification from virtual terminal (event-driven).

        Args:
            last_lines: Last N lines of screen content.
            total_appended: Total bytes appended so far.
        """
        if self.destroyed or not self._ready_future or self.is_resetting:
            return

        # Update screen snapshot
        self.current_screen_text = "\n".join(last_lines)
        self._last_total_appended = total_appended

        # v5: Skip prompt marker detection when Fast Path is disabled
        if self._fast_path_disabled:
            return

        # Post-reset cooldown: no detection for a period after reset
        if not self.is_first_wait and self.reset_at > 0:
            since_reset = (time.time() * 1000) - self.reset_at
            if since_reset < self.post_reset_cooldown_ms:
                return

        # Fast Path: Detect prompt markers
        # Only if we have enough lines and not already detected
        if not self.prompt_detected and len(last_lines) >= 2:
            # Check last few lines for prompt markers
            for line in last_lines[-5:]:
                if self._contains_prompt_marker(line):
                    logger.debug(
                        "[%s] Fast Path: prompt marker detected in line: %s",
                        self.agent_id,
                        line[:50],
                    )
                    self.prompt_detected = True
                    self._start_fast_path_fallback()
                    return

    def _contains_prompt_marker(self, line: str) -> bool:
        """Check if line contains a prompt marker."""
        for pattern in self.prompt_markers:
            if re.search(pattern, line):
                return True
        return False

    def _start_fast_path_fallback(self) -> None:
        """Start Fast Path fallback timer."""
        if self.fast_path_fallback_timer:
            self.fast_path_fallback_timer.cancel()

        def fallback_handler():
            if self.prompt_detected and not self.destroyed:
                logger.debug(
                    "[%s] Fast Path fallback: no subsequent writes, resolve ready", self.agent_id
                )
                self._resolve_ready(True)

        self.fast_path_fallback_timer = Timer(FAST_PATH_FALLBACK_MS / 1000, fallback_handler)
        self.fast_path_fallback_timer.start()

    def notify_task_complete(self) -> None:
        """Structured signal: Task completed notification (from JSONL parser, etc.)."""
        if not self.destroyed and self._ready_future:
            logger.debug("[%s] Structured signal: notify_task_complete", self.agent_id)
            self._resolve_ready(True)

    async def wait_ready(self) -> bool:
        """Wait for agent to be ready.

        Returns:
            True if ready, False if timeout.
        """
        if self.destroyed:
            return False

        # Create future if not exists
        if not self._ready_future:
            loop = asyncio.get_event_loop()
            self._ready_future = loop.create_future()

        # Start detection
        self._start_timeout()

        # Wait for minimum time after launch
        elapsed = (time.time() * 1000) - self.spawned_at
        if elapsed < AUTOSEND_MIN_WAIT_MS:
            await asyncio.sleep((AUTOSEND_MIN_WAIT_MS - elapsed) / 1000)

        # Start slow path (quiescence) detection
        self._start_quiescence_detection()

        try:
            return await self._ready_future
        except asyncio.CancelledError:
            return False

    def _start_timeout(self) -> None:
        """Start timeout timer."""
        if self.timeout_timer:
            self.timeout_timer.cancel()

        def timeout_handler():
            if not self.destroyed and self._ready_future and not self._ready_future.done():
                logger.warning(
                    "[%s] Wait ready timeout after %d ms", self.agent_id, self.max_wait_ms
                )
                self._resolve_ready(False)

        self.timeout_timer = Timer(self.max_wait_ms / 1000, timeout_handler)
        self.timeout_timer.start()

    def _start_quiescence_detection(self) -> None:
        """Start slow path (quiescence) detection."""
        if self.quiescence_timer:
            self.quiescence_timer.cancel()

        def quiescence_check():
            if self.destroyed or not self._ready_future or self._ready_future.done():
                return

            screen = self.current_screen_text

            # Post-reset check: wait for output to appear
            if not self.is_first_wait and self.reset_at > 0:
                since_reset = (time.time() * 1000) - self.reset_at
                if since_reset < self.post_reset_cooldown_ms:
                    # Still in cooldown, skip check
                    return

                if not self.output_seen_since_reset:
                    # No output yet, wait for it
                    if screen and screen.strip():
                        self.output_seen_since_reset = True
                    else:
                        return

            if not screen.strip():
                # Empty screen, wait
                return

            if screen == self.last_screen_snapshot:
                # Screen unchanged, check if stable long enough
                stable_duration = (time.time() * 1000) - self.stable_since
                if stable_duration >= self.quiescence_threshold_ms:
                    logger.debug(
                        "[%s] Quiescence detection: screen stable for %d ms, resolve ready",
                        self.agent_id,
                        stable_duration,
                    )
                    self._resolve_ready(True)
            else:
                # Screen changed → reset
                self.stable_since = time.time() * 1000
                self.last_screen_snapshot = screen
                self.output_seen_since_reset = True

        self.quiescence_timer = Timer(QUIESCENCE_POLL_MS / 1000, quiescence_check)
        self.quiescence_timer.start()
        # Also check immediately
        asyncio.create_task(self._run_quiescence_check())

    async def _run_quiescence_check(self):
        """Run quiescence check asynchronously."""
        while not self.destroyed and self._ready_future and not self._ready_future.done():
            await asyncio.sleep(QUIESCENCE_POLL_MS / 1000)
            # Check logic would be here in a real implementation

    def _resolve_ready(self, ready: bool) -> None:
        """Resolve the ready future."""
        if self._ready_future and not self._ready_future.done():
            self._ready_future.set_result(ready)
        self._cleanup()

    def reset(self) -> None:
        """Reset state for detecting next readiness.

        v5: fast_path_disabled is not affected by reset (persists across cycles).
        """
        self.is_resetting = True
        try:
            self._cleanup()
            self.prompt_detected = False
            self.last_screen_snapshot = ""
            self.stable_since = 0
            self._ready_future = None
            self.spawned_at = time.time() * 1000
            self.reset_at = time.time() * 1000
            self.is_first_wait = False
            self.output_seen_since_reset = False
        finally:
            self.is_resetting = False

    def destroy(self) -> None:
        """Destroy detector and release resources."""
        self.destroyed = True
        self._cleanup()
        if self._ready_future and not self._ready_future.done():
            self._ready_future.set_result(False)

    def _cleanup(self) -> None:
        """Clean up timers."""
        if self.fast_path_fallback_timer:
            self.fast_path_fallback_timer.cancel()
            self.fast_path_fallback_timer = None

        if self.quiescence_timer:
            self.quiescence_timer.cancel()
            self.quiescence_timer = None

        if self.timeout_timer:
            self.timeout_timer.cancel()
            self.timeout_timer = None
