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

        if sys.platform == "win32":
            # Windows - prefer openclaw_sdk for true multi-agent collaboration
            # Falls back to openclaw_api or subprocess if SDK not available
            try:
                import subprocess
                result = subprocess.run(
                    ["cmd", "/c", "openclaw", "gateway", "health"],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    name = "openclaw_sdk"
                else:
                    name = "subprocess"
            except Exception:
                name = "subprocess"
        elif not shutil.which("tmux"):
            # Unix but tmux not available - try openclaw_sdk
            name = "openclaw_sdk"
        else:
            # Unix with tmux available - prefer tmux for better observability
            name = "tmux"

    if name == "subprocess":
        from clawteam.spawn.subprocess_backend import SubprocessBackend
        return SubprocessBackend()
    elif name == "tmux":
        from clawteam.spawn.tmux_backend import TmuxBackend
        return TmuxBackend()
    elif name == "openclaw_api":
        from clawteam.spawn.openclaw_api_backend import OpenClawAPIBackend
        return OpenClawAPIBackend()
    elif name == "openclaw_sdk":
        from clawteam.spawn.openclaw_sdk_backend import OpenClawSDKBackend
        return OpenClawSDKBackend()
    else:
        raise ValueError(f"Unknown spawn backend: {name}. Available: auto, subprocess, tmux, openclaw_api, openclaw_sdk")


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
