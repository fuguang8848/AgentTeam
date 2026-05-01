"""Message TTL (Time-To-Live) configuration and utilities.

Messages can be configured to automatically expire after a specified duration.
This helps prevent message accumulation in long-running deployments.

Configuration:
    export CLAWTEAM_MESSAGE_TTL=86400  # 24 hours in seconds (default)
    export CLAWTEAM_MESSAGE_TTL=0      # Disable TTL (messages never expire)

Environment Variables:
    CLAWTEAM_MESSAGE_TTL: TTL in seconds (default: 86400 = 24 hours)
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Optional


# Default TTL: 24 hours (86400 seconds)
DEFAULT_TTL_SECONDS = 86400


def get_message_ttl() -> int:
    """Get message TTL from environment.
    
    Returns:
        TTL in seconds. 0 means no TTL (messages never expire).
    """
    ttl_str = os.environ.get("CLAWTEAM_MESSAGE_TTL", str(DEFAULT_TTL_SECONDS))
    try:
        ttl = int(ttl_str)
        if ttl < 0:
            return DEFAULT_TTL_SECONDS
        return ttl
    except ValueError:
        return DEFAULT_TTL_SECONDS


def is_ttl_enabled() -> bool:
    """Check if TTL is enabled.
    
    Returns:
        True if TTL > 0, False if TTL == 0 (disabled).
    """
    return get_message_ttl() > 0


def is_message_expired(timestamp_ms: int, ttl_seconds: Optional[int] = None) -> bool:
    """Check if a message timestamp is expired.
    
    Args:
        timestamp_ms: Message timestamp in milliseconds.
        ttl_seconds: TTL in seconds. If None, uses environment config.
        
    Returns:
        True if message is expired, False otherwise.
    """
    if ttl_seconds is None:
        ttl_seconds = get_message_ttl()
    
    if ttl_seconds <= 0:
        return False  # TTL disabled
    
    current_ms = int(time.time() * 1000)
    age_ms = current_ms - timestamp_ms
    age_seconds = age_ms / 1000
    
    return age_seconds > ttl_seconds


def get_expiry_timestamp_ms(timestamp_ms: int, ttl_seconds: Optional[int] = None) -> int:
    """Calculate expiry timestamp for a message.
    
    Args:
        timestamp_ms: Message creation timestamp in milliseconds.
        ttl_seconds: TTL in seconds. If None, uses environment config.
        
    Returns:
        Expiry timestamp in milliseconds.
    """
    if ttl_seconds is None:
        ttl_seconds = get_message_ttl()
    
    return timestamp_ms + (ttl_seconds * 1000)


@dataclass
class TTLConfig:
    """TTL configuration container."""
    
    ttl_seconds: int
    enabled: bool
    
    @classmethod
    def from_env(cls) -> "TTLConfig":
        """Create TTLConfig from environment."""
        ttl = get_message_ttl()
        return cls(
            ttl_seconds=ttl,
            enabled=ttl > 0,
        )
    
    def is_expired(self, timestamp_ms: int) -> bool:
        """Check if a timestamp is expired."""
        if not self.enabled:
            return False
        return is_message_expired(timestamp_ms, self.ttl_seconds)
    
    def get_expiry_ms(self, timestamp_ms: int) -> int:
        """Get expiry timestamp."""
        return get_expiry_timestamp_ms(timestamp_ms, self.ttl_seconds)


__all__ = [
    "DEFAULT_TTL_SECONDS",
    "get_message_ttl",
    "is_ttl_enabled",
    "is_message_expired",
    "get_expiry_timestamp_ms",
    "TTLConfig",
]
