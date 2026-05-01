"""Spawn backends for launching team agents."""

from __future__ import annotations

import logging
import time

from clawteam.spawn.base import SpawnBackend

logger = logging.getLogger(__name__)


def get_backend(name: str = "auto") -> SpawnBackend:
    """Factory function to get a spawn backend by name.

    Args:
        name: Backend name. "auto" (default) detects the best available backend.
              On Windows or if tmux is not installed, uses subprocess backend.
    """
    if name == "auto":
        # Auto-detect best available backend
        import shutil
        import sys

        if sys.platform == "win32" or not shutil.which("tmux"):
            # Windows or tmux not available - use subprocess backend
            name = "subprocess"
        else:
            # Unix with tmux available - prefer tmux for better observability
            name = "tmux"

    if name == "subprocess":
        from clawteam.spawn.subprocess_backend import SubprocessBackend
        return SubprocessBackend()
    elif name == "tmux":
        from clawteam.spawn.tmux_backend import TmuxBackend
        return TmuxBackend()
    else:
        raise ValueError(f"Unknown spawn backend: {name}. Available: auto, subprocess, tmux")


def spawn_with_retry(
    backend: SpawnBackend,
    max_retries: int = 3,
    backoff_base: float = 1.0,
    backoff_max: float = 30.0,
    **spawn_kwargs,
) -> str:
    """Wrap backend.spawn() with exponential backoff retry.

    Returns the result of a successful spawn, or the last error message.
    """
    last_result = ""
    for attempt in range(max_retries + 1):
        result = backend.spawn(**spawn_kwargs)
        if not result.startswith("Error"):
            return result
        last_result = result
        if attempt < max_retries:
            delay = min(backoff_base * (2 ** attempt), backoff_max)
            logger.warning(
                "Spawn attempt %d/%d failed: %s — retrying in %.1fs",
                attempt + 1, max_retries + 1, result, delay,
            )
            time.sleep(delay)
    return last_result


__all__ = ["SpawnBackend", "get_backend", "spawn_with_retry"]
