"""@Mention support for ClawTeam collaboration.

Provides parsing and notification for @mentions in messages,
allowing agents to directly notify each other.
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Pattern


class MentionType(str, Enum):
    """Types of mentions."""

    AGENT = "agent"  # @agent-name
    TEAM = "team"  # @team
    ALL = "all"  # @all
    HERE = "here"  # @here


@dataclass
class Mention:
    """A parsed @mention from text.

    Represents a single mention within a message.
    """

    type: MentionType
    value: str  # The name/ID mentioned (e.g., "alice" for @alice)
    raw: str  # The raw mention text (e.g., "@alice")
    start_pos: int  # Start position in original text
    end_pos: int  # End position in original text

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value if isinstance(self.type, MentionType) else self.type,
            "value": self.value,
            "raw": self.raw,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
        }


class MentionParser:
    """Parser for @mentions in messages.

    Supports:
    - @agent-name - Mention a specific agent
    - @team - Mention the whole team
    - @all - Mention all online agents
    - @here - Mention all currently active agents

    Examples:
        parser = MentionParser()

        # Parse mentions from text
        text = "Hey @alice and @bob, please review this PR"
        mentions = parser.parse(text)
        # => [Mention(type=AGENT, value="alice", ...), Mention(type=AGENT, value="bob", ...)]

        # Get unique mentioned agents
        agents = parser.get_mentioned_agents(mentions)
        # => ["alice", "bob"]

        # Check if specific agent is mentioned
        if parser.mentions_agent(mentions, "alice"):
            print("Alice was mentioned!")
    """

    # Regex patterns for different mention types
    PATTERNS: Dict[MentionType, Pattern] = {
        MentionType.AGENT: re.compile(r"@([a-zA-Z0-9_-]+)"),
        MentionType.TEAM: re.compile(r"@team\b", re.IGNORECASE),
        MentionType.ALL: re.compile(r"@all\b", re.IGNORECASE),
        MentionType.HERE: re.compile(r"@here\b", re.IGNORECASE),
    }

    # Keywords that indicate special mentions
    TEAM_KEYWORDS = {"team", "group", "everyone"}
    ALL_KEYWORDS = {"all", "everybody"}
    HERE_KEYWORDS = {"here", "online", "active"}

    def __init__(self, allow_duplicates: bool = False):
        """Initialize the parser.

        Args:
            allow_duplicates: If True, keep duplicate mentions.
                             If False, only keep first mention of each agent.
        """
        self._allow_duplicates = allow_duplicates

    def parse(self, text: str) -> List[Mention]:
        """Parse @mentions from text.

        Args:
            text: The text to parse

        Returns:
            List of Mention objects in order they appear in text
        """
        mentions = []
        seen_positions: set = set()  # Track (start, end) positions already added
        seen_agents: Dict[str, int] = {}  # agent -> first position

        for mention_type, pattern in self.PATTERNS.items():
            for match in pattern.finditer(text):
                raw = match.group(0)
                start = match.start()
                end = match.end()

                # Skip if we've already added a mention at this position
                if (start, end) in seen_positions:
                    continue

                if mention_type == MentionType.AGENT:
                    value = match.group(1)

                    # Check if this is actually a team/all/here keyword
                    lower_value = value.lower()
                    if lower_value in self.TEAM_KEYWORDS:
                        mention_type = MentionType.TEAM
                        value = "team"
                    elif lower_value in self.ALL_KEYWORDS:
                        mention_type = MentionType.ALL
                        value = "all"
                    elif lower_value in self.HERE_KEYWORDS:
                        mention_type = MentionType.HERE
                        value = "here"

                    # Handle duplicates
                    if not self._allow_duplicates and value in seen_agents:
                        continue
                    seen_agents[value] = len(mentions)

                seen_positions.add((start, end))
                mention = Mention(
                    type=mention_type,
                    value=value,
                    raw=raw,
                    start_pos=start,
                    end_pos=end,
                )
                mentions.append(mention)

        # Sort by position
        mentions.sort(key=lambda m: m.start_pos)

        return mentions

    def get_mentioned_agents(self, mentions: List[Mention]) -> List[str]:
        """Get list of unique agent names mentioned.

        Excludes @team, @all, @here.
        """
        agents = []
        seen = set()

        for mention in mentions:
            if mention.type == MentionType.AGENT:
                if mention.value not in seen:
                    agents.append(mention.value)
                    seen.add(mention.value)

        return agents

    def mentions_agent(self, mentions: List[Mention], agent_name: str) -> bool:
        """Check if a specific agent is mentioned."""
        for mention in mentions:
            if mention.type == MentionType.AGENT and mention.value == agent_name:
                return True
        return False

    def mentions_team(self, mentions: List[Mention]) -> bool:
        """Check if @team is mentioned."""
        return any(m.type == MentionType.TEAM for m in mentions)

    def mentions_all(self, mentions: List[Mention]) -> bool:
        """Check if @all is mentioned."""
        return any(m.type == MentionType.ALL for m in mentions)

    def mentions_here(self, mentions: List[Mention]) -> bool:
        """Check if @here is mentioned."""
        return any(m.type == MentionType.HERE for m in mentions)

    def format_message_with_links(
        self,
        text: str,
        mentions: List[Mention],
        format_agent: Callable[[str], str] = None,
    ) -> str:
        """Format message text with mention highlights.

        Args:
            text: Original text
            mentions: Parsed mentions
            format_agent: Optional function to format agent mentions

        Returns:
            Text with mentions potentially formatted/highlighted
        """
        if not mentions:
            return text

        # For now, just return original text
        # Subclasses or callers can override to add formatting
        return text

    @staticmethod
    def extract_mention_targets(mentions: List[Mention]) -> Dict[str, List[str]]:
        """Extract mention targets grouped by type.

        Returns:
            Dict with keys 'agents', 'team', 'all', 'here'
        """
        targets = {
            "agents": [],
            "team": False,
            "all": False,
            "here": False,
        }

        for mention in mentions:
            if mention.type == MentionType.AGENT:
                targets["agents"].append(mention.value)
            elif mention.type == MentionType.TEAM:
                targets["team"] = True
            elif mention.type == MentionType.ALL:
                targets["all"] = True
            elif mention.type == MentionType.HERE:
                targets["here"] = True

        return targets


class MentionNotifier:
    """Handles notification delivery for @mentions.

    Integrates with the notification system to send alerts
    when agents are mentioned in messages.

    Example:
        notifier = MentionNotifier(
            team_name="dev-team",
            presence_manager=presence_mgr,
            notification_manager=notif_mgr,
        )

        # Send notifications for mentions in a message
        mentions = parser.parse(message_text)
        notifier.notify_mentions(
            mentions=mentions,
            from_agent="alice",
            message_preview="Hey @bob, check this out...",
        )
    """

    def __init__(
        self,
        team_name: str,
        presence_manager,  # PresenceManager
        notification_manager,  # NotificationManager
        activity_feed=None,  # Optional[ActivityFeed]
    ):
        self.team_name = team_name
        self._presence = presence_manager
        self._notifications = notification_manager
        self._activity_feed = activity_feed

    def notify_mentions(
        self,
        mentions: List[Mention],
        from_agent: str,
        message_preview: str,
        message_id: Optional[str] = None,
    ) -> Dict[str, bool]:
        """Send notifications for all mentioned agents.

        Args:
            mentions: Parsed mentions from the message
            from_agent: Who sent the message
            message_preview: First ~100 chars of the message
            message_id: Optional message ID for reference

        Returns:
            Dict mapping agent names to whether notification was sent
        """
        from clawteam.notification.types import NotificationType, NotificationPriority

        results = {}
        targets = MentionParser.extract_mention_targets(mentions)

        # Notify individual agents
        for agent_name in targets["agents"]:
            if agent_name == from_agent:
                continue  # Don't notify sender

            if self._presence.is_available(agent_name):
                self._notifications.on_info(
                    session_id=f"mention-{agent_name}",
                    title=f"@{from_agent} mentioned you",
                    body=message_preview[:100]
                    if message_preview
                    else "You were mentioned in a message",
                    session_name=agent_name,
                )
                results[agent_name] = True

                # Record in activity feed
                if self._activity_feed:
                    from clawteam.collaboration.activity_feed import ActivityType

                    self._activity_feed.record(
                        type=ActivityType.MESSAGE_RECEIVED,
                        agent_name=from_agent,
                        title=f"Mentioned @{agent_name}",
                        description=message_preview[:200] if message_preview else None,
                        target_agent=agent_name,
                        message_id=message_id,
                        metadata={"mention_raw": f"@{agent_name}"},
                        is_private=True,
                    )
            else:
                results[agent_name] = False  # Agent not available

        # Notify team-wide mentions
        if targets["team"] or targets["all"] or targets["here"]:
            self._notify_team_mention(
                targets=targets,
                from_agent=from_agent,
                message_preview=message_preview,
                message_id=message_id,
            )

        return results

    def _notify_team_mention(
        self,
        targets: Dict[str, Any],
        from_agent: str,
        message_preview: str,
        message_id: Optional[str],
    ) -> None:
        """Handle team/all/here notifications."""
        if self._activity_feed:
            from clawteam.collaboration.activity_feed import ActivityType

            if targets.get("all") or targets.get("here"):
                mention_type = ActivityType.BROADCAST_SENT
            else:
                mention_type = ActivityType.MESSAGE_SENT

            self._activity_feed.record(
                type=mention_type,
                agent_name=from_agent,
                title="Team broadcast" if targets.get("team") else "Group mention",
                description=message_preview[:200] if message_preview else None,
                message_id=message_id,
                metadata={
                    "mention_type": "team"
                    if targets.get("team")
                    else ("all" if targets.get("all") else "here"),
                },
            )
