"""Cross-session awareness module for ClawTeam.

This module provides session registry and cross-session communication capabilities,
inspired by SpectrAI's supervisorPrompt.ts awareness layer.

Key components:
- SessionRegistry: Central registry for all active sessions
- CrossSessionBus: Message bus for cross-session communication
"""

from clawteam.session.registry import (
    SessionRegistry,
    SessionInfo,
    SessionStatus,
    get_session_registry,
)
from clawteam.session.cross_session import (
    CrossSessionBus,
    CrossSessionMessage,
    NotificationType,
    get_cross_session_bus,
)

__all__ = [
    "SessionRegistry",
    "SessionInfo",
    "SessionStatus",
    "get_session_registry",
    "CrossSessionBus",
    "CrossSessionMessage",
    "NotificationType",
    "get_cross_session_bus",
]