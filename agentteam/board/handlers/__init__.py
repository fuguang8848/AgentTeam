"""HTTP handlers module for the board server."""

from __future__ import annotations

from agentteam.board.handlers.base import BaseHandler
from agentteam.board.handlers.auth import AuthMixin
from agentteam.board.handlers.static import StaticMixin
from agentteam.board.handlers.team import TeamMixin
from agentteam.board.handlers.agent import AgentMixin
from agentteam.board.handlers.session import SessionMixin
from agentteam.board.handlers.settings import SettingsMixin
from agentteam.board.handlers.transport import TransportMixin
from agentteam.board.handlers.notifications import NotificationsMixin
from agentteam.board.handlers.providers import ProvidersMixin
from agentteam.board.handlers.tasks import TasksMixin
from agentteam.board.handlers.overview import OverviewMixin

__all__ = [
    "BaseHandler",
    "AuthMixin",
    "StaticMixin",
    "TeamMixin",
    "AgentMixin",
    "SessionMixin",
    "SettingsMixin",
    "TransportMixin",
    "NotificationsMixin",
    "ProvidersMixin",
    "TasksMixin",
    "OverviewMixin",
]
