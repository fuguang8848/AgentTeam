"""Collaboration enhancements for ClawTeam multi-agent coordination.

This module provides enhanced collaboration features:
- Presence status management
- Shared context board
- Activity feed
- @mention support
"""

from clawteam.collaboration.presence import PresenceStatus, PresenceManager
from clawteam.collaboration.context_board import ContextBoard, ContextEntry, ContextCategory
from clawteam.collaboration.activity_feed import ActivityFeed, ActivityEntry, ActivityType
from clawteam.collaboration.mentions import MentionParser, Mention

__all__ = [
    "PresenceStatus",
    "PresenceManager",
    "ContextBoard",
    "ContextEntry",
    "ContextCategory",
    "ActivityFeed",
    "ActivityEntry",
    "ActivityType",
    "MentionParser",
    "Mention",
]
