"""Collaboration Module Tests.

Tests for the collaboration module which provides:
- PresenceManager: Agent presence status tracking
- ContextBoard: Shared context board for team collaboration
- ActivityFeed: Real-time activity feed for team events
- MentionParser: @mention parsing for messages
"""

import pytest
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from agentteam.collaboration.presence import PresenceManager, PresenceStatus
from agentteam.collaboration.context_board import ContextBoard, ContextCategory, ContextEntry
from agentteam.collaboration.activity_feed import ActivityFeed, ActivityType, ActivityEntry
from agentteam.collaboration.mentions import MentionParser, MentionType, Mention


class TestPresenceStatus:
    """Tests for PresenceStatus enum."""

    def test_presence_status_values(self):
        """Test all presence status values exist."""
        assert PresenceStatus.ONLINE.value == "online"
        assert PresenceStatus.BUSY.value == "busy"
        assert PresenceStatus.IDLE.value == "idle"
        assert PresenceStatus.AWAY.value == "away"
        assert PresenceStatus.OFFLINE.value == "offline"

    def test_presence_status_is_string_enum(self):
        """Test that PresenceStatus is a string enum for JSON serialization."""
        status = PresenceStatus.ONLINE
        assert isinstance(status, str)
        assert status == "online"


class TestPresenceManager:
    """Tests for PresenceManager."""

    def test_initialization(self):
        """Test PresenceManager initialization."""
        manager = PresenceManager(team_name="test-team")
        assert manager.team_name == "test-team"
        assert manager._presence == {}

    def test_set_and_get_status(self):
        """Test setting and getting presence status."""
        manager = PresenceManager(team_name="test-team")

        result = manager.set_status("alice", PresenceStatus.ONLINE, "Working on auth")
        assert result["agent_name"] == "alice"
        assert result["status"] == "online"
        assert result["status_message"] == "Working on auth"
        assert "updated_at" in result

        status = manager.get_status("alice")
        assert status is not None
        assert status["status"] == "online"
        assert status["status_message"] == "Working on auth"

    def test_get_status_not_found(self):
        """Test get_status returns None for unknown agent."""
        manager = PresenceManager(team_name="test-team")
        assert manager.get_status("unknown") is None

    def test_set_away_status_with_duration(self):
        """Test setting AWAY status with auto-expiry."""
        manager = PresenceManager(team_name="test-team")

        result = manager.set_status("alice", PresenceStatus.AWAY, "BRB", duration_minutes=5)
        assert result["status"] == "away"
        assert result["expires_at"] is not None

        # Should still be AWAY immediately
        status = manager.get_status("alice")
        assert status["status"] == "away"

    def test_clear_status(self):
        """Test clearing presence status."""
        manager = PresenceManager(team_name="test-team")

        manager.set_status("alice", PresenceStatus.ONLINE)
        assert manager.get_status("alice") is not None

        result = manager.clear_status("alice")
        assert result is True
        assert manager.get_status("alice") is None

    def test_clear_status_not_found(self):
        """Test clearing non-existent status returns False."""
        manager = PresenceManager(team_name="test-team")
        assert manager.clear_status("unknown") is False

    def test_get_team_presence(self):
        """Test getting all team presence."""
        manager = PresenceManager(team_name="test-team")

        manager.set_status("alice", PresenceStatus.ONLINE)
        manager.set_status("bob", PresenceStatus.BUSY)
        manager.set_status("carol", PresenceStatus.IDLE)

        team = manager.get_team_presence()
        assert len(team) == 3

        # Should be sorted by status priority (ONLINE first)
        statuses = [p["status"] for p in team]
        assert statuses[0] == "online"

    def test_get_team_presence_excludes_expired(self):
        """Test that get_team_presence excludes expired AWAY statuses."""
        manager = PresenceManager(team_name="test-team")

        # Set AWAY with very short duration (should expire quickly)
        # Note: duration_minutes=0 is falsy so won't set expires_at
        manager.set_status("alice", PresenceStatus.AWAY, duration_minutes=0.001)

        # Wait for expiry to occur (duration is 0.001 min = 60ms, wait 100ms)
        import time
        time.sleep(0.1)

        team = manager.get_team_presence()
        # Should not include alice since AWAY status expired
        agent_names = [p["agent_name"] for p in team]
        assert "alice" not in agent_names

    def test_is_available(self):
        """Test is_available check."""
        manager = PresenceManager(team_name="test-team")

        manager.set_status("alice", PresenceStatus.ONLINE)
        manager.set_status("bob", PresenceStatus.BUSY)
        manager.set_status("carol", PresenceStatus.AWAY)

        assert manager.is_available("alice") is True  # ONLINE
        assert manager.is_available("bob") is False  # BUSY
        assert manager.is_available("carol") is False  # AWAY
        assert manager.is_available("unknown") is False  # Not found

    def test_status_callback(self):
        """Test status change callbacks."""
        manager = PresenceManager(team_name="test-team")

        callback = Mock()
        manager.add_status_callback(callback)

        manager.set_status("alice", PresenceStatus.ONLINE)

        callback.assert_called_once()
        args = callback.call_args[0]
        assert args[0] == "alice"
        assert args[1]["status"] == "online"

    def test_remove_status_callback(self):
        """Test removing status change callback."""
        manager = PresenceManager(team_name="test-team")

        callback = Mock()
        manager.add_status_callback(callback)
        manager.remove_status_callback(callback)

        manager.set_status("alice", PresenceStatus.ONLINE)
        callback.assert_not_called()  # Should not be called after removal

    def test_thread_safety(self):
        """Test that PresenceManager is thread-safe."""
        import threading

        manager = PresenceManager(team_name="test-team")

        def set_status(name):
            for i in range(10):
                manager.set_status(name, PresenceStatus.ONLINE)
                time.sleep(0.001)

        t1 = threading.Thread(target=set_status, args=("alice",))
        t2 = threading.Thread(target=set_status, args=("bob",))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Should not raise any exceptions
        assert manager.get_status("alice") is not None
        assert manager.get_status("bob") is not None


class TestContextCategory:
    """Tests for ContextCategory enum."""

    def test_context_category_values(self):
        """Test all context category values."""
        assert ContextCategory.TASK.value == "task"
        assert ContextCategory.REVIEW.value == "review"
        assert ContextCategory.MEETING.value == "meeting"
        assert ContextCategory.RESEARCH.value == "research"
        assert ContextCategory.BREAK.value == "break"
        assert ContextCategory.OTHER.value == "other"


class TestContextEntry:
    """Tests for ContextEntry dataclass."""

    def test_context_entry_creation(self):
        """Test creating a context entry."""
        entry = ContextEntry(
            id="test-1",
            agent_name="alice",
            category=ContextCategory.TASK,
            title="Implementing auth",
            description="Working on OAuth",
            file_path="/src/auth.py",
            tags=["auth", "feature"],
        )

        assert entry.id == "test-1"
        assert entry.agent_name == "alice"
        assert entry.category == ContextCategory.TASK
        assert entry.title == "Implementing auth"
        assert entry.tags == ["auth", "feature"]
        assert entry.is_pinned is False
        assert entry.is_private is False

    def test_context_entry_to_dict(self):
        """Test converting entry to dictionary."""
        entry = ContextEntry(
            id="test-1",
            agent_name="alice",
            category=ContextCategory.TASK,
            title="Test",
        )

        data = entry.to_dict()
        assert data["id"] == "test-1"
        assert data["category"] == "task"
        assert isinstance(data["created_at"], str)

    def test_context_entry_from_dict(self):
        """Test creating entry from dictionary."""
        data = {
            "id": "test-1",
            "agent_name": "alice",
            "category": "task",
            "title": "Test",
            "description": None,
            "file_path": None,
            "task_id": None,
            "tags": [],
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "is_pinned": False,
            "is_private": False,
        }

        entry = ContextEntry.from_dict(data)
        assert entry.id == "test-1"
        assert entry.category == ContextCategory.TASK

    def test_context_entry_update(self):
        """Test updating a context entry."""
        entry = ContextEntry(
            id="test-1",
            agent_name="alice",
            category=ContextCategory.TASK,
            title="Original",
        )

        original_updated = entry.updated_at
        time.sleep(0.01)

        entry.update(
            title="Updated",
            description="New description",
            tags=["updated"],
        )

        assert entry.title == "Updated"
        assert entry.description == "New description"
        assert entry.tags == ["updated"]
        assert entry.updated_at != original_updated


class TestContextBoard:
    """Tests for ContextBoard."""

    def test_initialization(self):
        """Test ContextBoard initialization."""
        board = ContextBoard(team_name="test-team")
        assert board.team_name == "test-team"
        assert board.get_all() == []

    def test_post_entry(self):
        """Test posting a new context entry."""
        board = ContextBoard(team_name="test-team")

        entry = board.post(
            agent_name="alice",
            category=ContextCategory.TASK,
            title="Implementing auth",
            description="Working on OAuth flow",
        )

        assert entry.id.startswith("ctx_")
        assert entry.agent_name == "alice"
        assert entry.category == ContextCategory.TASK
        assert entry.title == "Implementing auth"

    def test_post_private_entry(self):
        """Test posting a private context entry."""
        board = ContextBoard(team_name="test-team")

        entry = board.post(
            agent_name="alice",
            category=ContextCategory.TASK,
            title="Private note",
            is_private=True,
        )

        # Should be visible to author
        found = board.get_entry(entry.id, viewer_name="alice")
        assert found is not None

        # Should not be visible to others
        found = board.get_entry(entry.id, viewer_name="bob")
        assert found is None

    def test_get_all_entries(self):
        """Test getting all entries."""
        board = ContextBoard(team_name="test-team")

        board.post(agent_name="alice", category=ContextCategory.TASK, title="Task 1")
        board.post(agent_name="bob", category=ContextCategory.REVIEW, title="Review 1")

        entries = board.get_all()
        assert len(entries) == 2

    def test_filter_by_agent(self):
        """Test filtering entries by agent."""
        board = ContextBoard(team_name="test-team")

        board.post(agent_name="alice", category=ContextCategory.TASK, title="Alice 1")
        board.post(agent_name="alice", category=ContextCategory.TASK, title="Alice 2")
        board.post(agent_name="bob", category=ContextCategory.TASK, title="Bob 1")

        alice_entries = board.get_all(agent_name_filter="alice")
        assert len(alice_entries) == 2

    def test_filter_by_category(self):
        """Test filtering entries by category."""
        board = ContextBoard(team_name="test-team")

        board.post(agent_name="alice", category=ContextCategory.TASK, title="Task 1")
        board.post(agent_name="bob", category=ContextCategory.REVIEW, title="Review 1")

        task_entries = board.get_all(category_filter=ContextCategory.TASK)
        assert len(task_entries) == 1
        assert task_entries[0].title == "Task 1"

    def test_filter_by_tag(self):
        """Test filtering entries by tag."""
        board = ContextBoard(team_name="test-team")

        board.post(agent_name="alice", category=ContextCategory.TASK, title="Task 1", tags=["urgent"])
        board.post(agent_name="bob", category=ContextCategory.TASK, title="Task 2", tags=["normal"])

        urgent_entries = board.get_all(tag_filter="urgent")
        assert len(urgent_entries) == 1
        assert urgent_entries[0].title == "Task 1"

    def test_update_entry(self):
        """Test updating an entry."""
        board = ContextBoard(team_name="test-team")

        entry = board.post(agent_name="alice", category=ContextCategory.TASK, title="Original")
        updated = board.update_entry(entry.id, agent_name="alice", title="Updated")

        assert updated is not None
        assert updated.title == "Updated"

    def test_update_entry_unauthorized(self):
        """Test that non-authors cannot update entries."""
        board = ContextBoard(team_name="test-team")

        entry = board.post(agent_name="alice", category=ContextCategory.TASK, title="Original")
        updated = board.update_entry(entry.id, agent_name="bob", title="Hacked")

        assert updated is None

    def test_delete_entry(self):
        """Test deleting an entry."""
        board = ContextBoard(team_name="test-team")

        entry = board.post(agent_name="alice", category=ContextCategory.TASK, title="To delete")
        result = board.delete_entry(entry.id, agent_name="alice")

        assert result is True
        assert board.get_entry(entry.id) is None

    def test_delete_entry_unauthorized(self):
        """Test that non-authors cannot delete entries."""
        board = ContextBoard(team_name="test-team")

        entry = board.post(agent_name="alice", category=ContextCategory.TASK, title="To delete")
        result = board.delete_entry(entry.id, agent_name="bob")

        assert result is False
        assert board.get_entry(entry.id) is not None  # Still exists

    def test_pin_entry(self):
        """Test pinning an entry."""
        board = ContextBoard(team_name="test-team")

        entry = board.post(agent_name="alice", category=ContextCategory.TASK, title="Pinnable")
        result = board.pin_entry(entry.id, agent_name="alice")

        assert result is True
        updated = board.get_entry(entry.id)
        assert updated.is_pinned is True

    def test_unpin_entry(self):
        """Test unpinning an entry."""
        board = ContextBoard(team_name="test-team")

        entry = board.post(agent_name="alice", category=ContextCategory.TASK, title="Unpinnable")
        board.pin_entry(entry.id, agent_name="alice")
        result = board.unpin_entry(entry.id, agent_name="alice")

        assert result is True
        updated = board.get_entry(entry.id)
        assert updated.is_pinned is False

    def test_get_by_agent(self):
        """Test getting entries by specific agent."""
        board = ContextBoard(team_name="test-team")

        board.post(agent_name="alice", category=ContextCategory.TASK, title="Alice 1")
        board.post(agent_name="alice", category=ContextCategory.TASK, title="Alice 2")
        board.post(agent_name="bob", category=ContextCategory.TASK, title="Bob 1")

        alice_entries = board.get_by_agent("alice")
        assert len(alice_entries) == 2

    def test_get_by_task(self):
        """Test getting entries by task ID."""
        board = ContextBoard(team_name="test-team")

        board.post(agent_name="alice", category=ContextCategory.TASK, title="Task 1", task_id="task-1")
        board.post(agent_name="bob", category=ContextCategory.TASK, title="Task 2", task_id="task-2")

        task_entries = board.get_by_task("task-1")
        assert len(task_entries) == 1
        assert task_entries[0].title == "Task 1"

    def test_get_active_workers(self):
        """Test getting list of active workers."""
        board = ContextBoard(team_name="test-team")

        board.post(agent_name="alice", category=ContextCategory.TASK, title="Working")
        board.post(agent_name="bob", category=ContextCategory.BREAK, title="On break")
        board.post(agent_name="carol", category=ContextCategory.TASK, title="Also working")

        workers = board.get_active_workers()
        assert "alice" in workers
        assert "carol" in workers
        assert "bob" not in workers  # On break

    def test_clear_agent_entries(self):
        """Test clearing all entries for an agent."""
        board = ContextBoard(team_name="test-team")

        board.post(agent_name="alice", category=ContextCategory.TASK, title="Alice 1")
        board.post(agent_name="alice", category=ContextCategory.TASK, title="Alice 2")
        board.post(agent_name="bob", category=ContextCategory.TASK, title="Bob 1")

        count = board.clear_agent_entries("alice")
        assert count == 2

        remaining = board.get_all()
        assert len(remaining) == 1
        assert remaining[0].agent_name == "bob"

    def test_pinned_first_sorting(self):
        """Test that pinned entries appear first."""
        board = ContextBoard(team_name="test-team")

        # Post the pinned entry first
        entry1 = board.post(agent_name="alice", category=ContextCategory.TASK, title="Pinned")
        board.pin_entry(entry1.id, agent_name="alice")
        # Then post a regular entry
        entry2 = board.post(agent_name="bob", category=ContextCategory.TASK, title="Regular")

        entries = board.get_all(include_pinned_first=True)
        # Pinned entry should appear first despite being posted earlier
        assert entries[0].title == "Pinned"

    def test_change_callback(self):
        """Test change callbacks."""
        board = ContextBoard(team_name="test-team")

        callback = Mock()
        board.add_change_callback(callback)

        entry = board.post(agent_name="alice", category=ContextCategory.TASK, title="Test")

        callback.assert_called_once_with("post", entry)


class TestActivityType:
    """Tests for ActivityType enum."""

    def test_activity_type_values(self):
        """Test activity type values exist."""
        assert ActivityType.TASK_CREATED.value == "task_created"
        assert ActivityType.TASK_COMPLETED.value == "task_completed"
        assert ActivityType.MESSAGE_SENT.value == "message_sent"
        assert ActivityType.AGENT_JOINED.value == "agent_joined"

    def test_activity_types_cover_all_categories(self):
        """Test that all expected categories are covered."""
        # Task activities
        assert ActivityType.TASK_CREATED in list(ActivityType)
        assert ActivityType.TASK_COMPLETED in list(ActivityType)

        # Messaging
        assert ActivityType.MESSAGE_SENT in list(ActivityType)

        # Collaboration
        assert ActivityType.CONTEXT_POSTED in list(ActivityType)

        # Team activities
        assert ActivityType.AGENT_JOINED in list(ActivityType)
        assert ActivityType.AGENT_LEFT in list(ActivityType)


class TestActivityEntry:
    """Tests for ActivityEntry dataclass."""

    def test_activity_entry_creation(self):
        """Test creating an activity entry."""
        entry = ActivityEntry(
            id="act_123",
            type=ActivityType.TASK_COMPLETED,
            agent_name="alice",
            title="Completed auth module",
            description="Finished OAuth implementation",
            task_id="task-1",
            tags=["auth", "feature"],
        )

        assert entry.id == "act_123"
        assert entry.type == ActivityType.TASK_COMPLETED
        assert entry.agent_name == "alice"
        assert entry.title == "Completed auth module"
        assert entry.task_id == "task-1"

    def test_activity_entry_to_dict(self):
        """Test converting entry to dictionary."""
        entry = ActivityEntry(
            id="act_123",
            type=ActivityType.MESSAGE_SENT,
            agent_name="alice",
            title="Sent message",
        )

        data = entry.to_dict()
        assert data["id"] == "act_123"
        assert data["type"] == "message_sent"

    def test_activity_entry_from_dict(self):
        """Test creating entry from dictionary."""
        data = {
            "id": "act_123",
            "type": "task_completed",
            "agent_name": "alice",
            "title": "Completed",
            "description": None,
            "timestamp": "2026-01-01T00:00:00Z",
            "task_id": None,
            "message_id": None,
            "file_path": None,
            "target_agent": None,
            "tags": [],
            "metadata": {},
            "is_private": False,
        }

        entry = ActivityEntry.from_dict(data)
        assert entry.id == "act_123"
        assert entry.type == ActivityType.TASK_COMPLETED


class TestActivityFeed:
    """Tests for ActivityFeed."""

    def test_initialization(self):
        """Test ActivityFeed initialization."""
        feed = ActivityFeed(team_name="test-team")
        assert feed.team_name == "test-team"
        assert feed.get_recent() == []

    def test_record_activity(self):
        """Test recording an activity."""
        feed = ActivityFeed(team_name="test-team")

        entry = feed.record(
            type=ActivityType.TASK_COMPLETED,
            agent_name="alice",
            title="Completed auth module",
        )

        assert entry.id.startswith("act_")
        assert entry.type == ActivityType.TASK_COMPLETED
        assert entry.agent_name == "alice"

    def test_get_recent(self):
        """Test getting recent activities."""
        feed = ActivityFeed(team_name="test-team")

        feed.record(type=ActivityType.TASK_CREATED, agent_name="alice", title="Task 1")
        feed.record(type=ActivityType.TASK_CREATED, agent_name="bob", title="Task 2")

        recent = feed.get_recent(limit=10)
        assert len(recent) == 2
        # Most recent first
        assert recent[0].title == "Task 2"
        assert recent[1].title == "Task 1"

    def test_filter_by_agent(self):
        """Test filtering activities by agent."""
        feed = ActivityFeed(team_name="test-team")

        feed.record(type=ActivityType.TASK_CREATED, agent_name="alice", title="Alice task")
        feed.record(type=ActivityType.TASK_CREATED, agent_name="bob", title="Bob task")

        alice_activities = feed.get_recent(agent_filter="alice")
        assert len(alice_activities) == 1
        assert alice_activities[0].title == "Alice task"

    def test_filter_by_type(self):
        """Test filtering activities by type."""
        feed = ActivityFeed(team_name="test-team")

        feed.record(type=ActivityType.TASK_CREATED, agent_name="alice", title="Created")
        feed.record(type=ActivityType.TASK_COMPLETED, agent_name="bob", title="Completed")

        created = feed.get_recent(type_filter=[ActivityType.TASK_CREATED])
        assert len(created) == 1
        assert created[0].title == "Created"

    def test_private_activity_visibility(self):
        """Test that private activities are properly filtered."""
        feed = ActivityFeed(team_name="test-team")

        # Public activity
        feed.record(
            type=ActivityType.MESSAGE_SENT,
            agent_name="alice",
            title="Public message",
            is_private=False,
        )

        # Private activity
        feed.record(
            type=ActivityType.MESSAGE_SENT,
            agent_name="alice",
            title="Private message",
            target_agent="bob",
            is_private=True,
        )

        # Bob viewing
        bob_activities = feed.get_recent(viewer_name="bob")
        # Should see public message + private message directed at bob
        titles = [a.title for a in bob_activities]
        assert "Public message" in titles
        assert "Private message" in titles

        # Carol viewing (not mentioned)
        carol_activities = feed.get_recent(viewer_name="carol")
        carol_titles = [a.title for a in carol_activities]
        assert "Public message" in carol_titles
        assert "Private message" not in carol_titles

    def test_subscribe_callback(self):
        """Test subscribing to activities."""
        feed = ActivityFeed(team_name="test-team")

        callback = Mock()
        feed.subscribe(callback, activity_types=[ActivityType.TASK_COMPLETED])

        feed.record(type=ActivityType.TASK_CREATED, agent_name="alice", title="Created")
        callback.assert_not_called()  # Different type

        feed.record(type=ActivityType.TASK_COMPLETED, agent_name="bob", title="Completed")
        callback.assert_called_once()

    def test_unsubscribe(self):
        """Test unsubscribing from activities."""
        feed = ActivityFeed(team_name="test-team")

        callback = Mock()
        feed.subscribe(callback, activity_types=[ActivityType.TASK_COMPLETED])
        feed.unsubscribe(callback)

        feed.record(type=ActivityType.TASK_COMPLETED, agent_name="alice", title="Done")
        callback.assert_not_called()

    def test_max_feed_entries(self):
        """Test that feed respects MAX_FEED_ENTRIES limit."""
        feed = ActivityFeed(team_name="test-team")

        # Record more than MAX_FEED_ENTRIES
        for i in range(ActivityFeed.MAX_FEED_ENTRIES + 100):
            feed.record(type=ActivityType.TASK_CREATED, agent_name="alice", title=f"Task {i}")

        # Should only keep the last MAX_FEED_ENTRIES
        recent = feed.get_recent(limit=ActivityFeed.MAX_FEED_ENTRIES + 50)
        assert len(recent) == ActivityFeed.MAX_FEED_ENTRIES


class TestMentionType:
    """Tests for MentionType enum."""

    def test_mention_type_values(self):
        """Test all mention type values."""
        assert MentionType.AGENT.value == "agent"
        assert MentionType.TEAM.value == "team"
        assert MentionType.ALL.value == "all"
        assert MentionType.HERE.value == "here"


class TestMention:
    """Tests for Mention dataclass."""

    def test_mention_creation(self):
        """Test creating a mention."""
        mention = Mention(
            type=MentionType.AGENT,
            value="alice",
            raw="@alice",
            start_pos=0,
            end_pos=6,
        )

        assert mention.type == MentionType.AGENT
        assert mention.value == "alice"
        assert mention.raw == "@alice"
        assert mention.start_pos == 0
        assert mention.end_pos == 6

    def test_mention_to_dict(self):
        """Test converting mention to dictionary."""
        mention = Mention(
            type=MentionType.AGENT,
            value="alice",
            raw="@alice",
            start_pos=0,
            end_pos=6,
        )

        data = mention.to_dict()
        assert data["type"] == "agent"
        assert data["value"] == "alice"


class TestMentionParser:
    """Tests for MentionParser."""

    def test_parse_agent_mentions(self):
        """Test parsing agent mentions."""
        parser = MentionParser()

        text = "Hey @alice and @bob, please review this"
        mentions = parser.parse(text)

        assert len(mentions) == 2
        assert mentions[0].type == MentionType.AGENT
        assert mentions[0].value == "alice"
        assert mentions[0].start_pos == 4
        assert mentions[0].end_pos == 10

        assert mentions[1].type == MentionType.AGENT
        assert mentions[1].value == "bob"
        assert mentions[1].start_pos == 15  # "Hey @alice and " = 15 chars
        assert mentions[1].end_pos == 19

    def test_parse_team_mention(self):
        """Test parsing @team mention."""
        parser = MentionParser()

        text = "Hey @team, we need to discuss this"
        mentions = parser.parse(text)

        assert len(mentions) == 1
        assert mentions[0].type == MentionType.TEAM
        assert mentions[0].value == "team"

    def test_parse_all_mention(self):
        """Test parsing @all mention."""
        parser = MentionParser()

        text = "Attention @all, meeting in 5 minutes"
        mentions = parser.parse(text)

        assert len(mentions) == 1
        assert mentions[0].type == MentionType.ALL

    def test_parse_here_mention(self):
        """Test parsing @here mention."""
        parser = MentionParser()

        text = "Anyone @here want to grab lunch?"
        mentions = parser.parse(text)

        assert len(mentions) == 1
        assert mentions[0].type == MentionType.HERE

    def test_parse_mixed_mentions(self):
        """Test parsing mixed mention types."""
        parser = MentionParser()

        # Use distinct names that don't conflict with keywords
        text = "Hey @user1, @team should review this. @all please comment"
        mentions = parser.parse(text)

        assert len(mentions) == 3
        types = [m.type for m in mentions]
        assert MentionType.AGENT in types
        assert MentionType.TEAM in types
        assert MentionType.ALL in types

    def test_parse_no_mentions(self):
        """Test parsing text with no mentions."""
        parser = MentionParser()

        text = "Just a regular message with no mentions"
        mentions = parser.parse(text)

        assert len(mentions) == 0

    def test_parse_mention_with_numbers(self):
        """Test parsing mentions with numbers in names."""
        parser = MentionParser()

        text = "Hey @user123 and @agent-42"
        mentions = parser.parse(text)

        assert len(mentions) == 2
        assert mentions[0].value == "user123"
        assert mentions[1].value == "agent-42"

    def test_get_mentioned_agents(self):
        """Test getting unique list of mentioned agents."""
        parser = MentionParser()

        text = "Hey @alice, @bob, and @alice again"
        mentions = parser.parse(text)
        agents = parser.get_mentioned_agents(mentions)

        assert len(agents) == 2
        assert "alice" in agents
        assert "bob" in agents

    def test_mentions_agent(self):
        """Test checking if specific agent is mentioned."""
        parser = MentionParser()

        text = "Hey @alice, please help @bob"
        mentions = parser.parse(text)

        assert parser.mentions_agent(mentions, "alice") is True
        assert parser.mentions_agent(mentions, "bob") is True
        assert parser.mentions_agent(mentions, "carol") is False

    def test_mentions_team(self):
        """Test checking if @team is mentioned."""
        parser = MentionParser()

        mentions = parser.parse("Hey @team")
        assert parser.mentions_team(mentions) is True

        mentions = parser.parse("Hey @alice")
        assert parser.mentions_team(mentions) is False

    def test_mentions_all(self):
        """Test checking if @all is mentioned."""
        parser = MentionParser()

        mentions = parser.parse("Attention @all")
        assert parser.mentions_all(mentions) is True

        mentions = parser.parse("Hey @team")
        assert parser.mentions_all(mentions) is False

    def test_format_message_with_links(self):
        """Test formatting message with mention links."""
        parser = MentionParser()

        text = "Hey @alice and @bob!"
        mentions = parser.parse(text)
        result = parser.format_message_with_links(text, mentions)

        # Currently just returns original text (no-op implementation)
        assert result == text

    def test_extract_mention_targets(self):
        """Test extracting mention targets grouped by type."""
        parser = MentionParser()

        text = "Hey @alice and @bob, @team and @all"
        mentions = parser.parse(text)
        targets = parser.extract_mention_targets(mentions)

        assert "alice" in targets["agents"]
        assert "bob" in targets["agents"]
        assert targets["team"] is True
        assert targets["all"] is True
        assert targets["here"] is False


class TestCollaborationIntegration:
    """Integration tests for collaboration module."""

    def test_presence_and_context_integration(self):
        """Test that presence and context work together."""
        presence = PresenceManager(team_name="test-team")
        board = ContextBoard(team_name="test-team")

        # Agent comes online
        presence.set_status("alice", PresenceStatus.ONLINE, "Working on auth")

        # Posts context
        entry = board.post(
            agent_name="alice",
            category=ContextCategory.TASK,
            title="Implementing OAuth",
        )

        # Verify both are set
        assert presence.get_status("alice") is not None
        assert board.get_entry(entry.id) is not None

    def test_activity_feed_with_context(self):
        """Test activity feed recording context changes."""
        feed = ActivityFeed(team_name="test-team")
        board = ContextBoard(team_name="test-team")

        # Post context
        entry = board.post(
            agent_name="alice",
            category=ContextCategory.TASK,
            title="Implementing auth",
        )

        # Record in activity feed
        feed.record(
            type=ActivityType.CONTEXT_POSTED,
            agent_name="alice",
            title="Posted new context",
            metadata={"entry_id": entry.id},
        )

        recent = feed.get_recent(agent_filter="alice")
        assert len(recent) == 1
        assert recent[0].type == ActivityType.CONTEXT_POSTED

    def test_mentions_and_activity(self):
        """Test that mentions can trigger activity recordings."""
        parser = MentionParser()
        feed = ActivityFeed(team_name="test-team")

        text = "Hey @alice, please review this PR"
        mentions = parser.parse(text)

        if parser.mentions_agent(mentions, "alice"):
            feed.record(
                type=ActivityType.MESSAGE_SENT,
                agent_name="bob",
                title="Mentioned @alice in message",
                target_agent="alice",
            )

        # Alice can see the mention
        alice_activities = feed.get_recent(viewer_name="alice")
        mention_activities = [a for a in alice_activities if "alice" in a.title.lower()]
        assert len(mention_activities) >= 1
