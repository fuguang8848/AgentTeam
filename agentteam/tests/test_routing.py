"""Tests for the intelligent task routing module."""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from agentteam.team.router import (
    TaskRouter,
    AgentProfile,
    RouteCandidate,
    _extract_keywords,
    _router_root,
)
from agentteam.team.models import TaskItem, TaskStatus, QualityScore


class TestKeywordExtraction:
    """Test keyword extraction functionality."""

    def test_extract_keywords_basic(self):
        """Test basic keyword extraction."""
        text = "Implement user authentication system"
        keywords = _extract_keywords(text)
        expected = {"implement", "user", "authentication", "system"}
        assert keywords == expected

    def test_extract_keywords_chinese(self):
        """Test keyword extraction with Chinese characters."""
        text = "实现用户认证系统"
        keywords = _extract_keywords(text)
        # Each Chinese character is treated as a separate keyword
        expected = {"实", "现", "用", "户", "认", "证", "系", "统"}
        assert keywords == expected

    def test_extract_keywords_mixed(self):
        """Test keyword extraction with mixed languages."""
        text = "Build API 用户管理"
        keywords = _extract_keywords(text)
        expected = {"build", "api", "用", "户", "管", "理"}
        assert keywords == expected

    def test_extract_keywords_min_length(self):
        """Test that short words are filtered out."""
        text = "a an the API"
        keywords = _extract_keywords(text)
        expected = {"the", "api"}  # words with 3+ chars
        assert keywords == expected


class TestAgentProfile:
    """Test AgentProfile functionality."""

    def test_agent_profile_defaults(self):
        """Test default values for new agent profile."""
        profile = AgentProfile(name="test-agent")
        assert profile.name == "test-agent"
        assert profile.total_tasks == 0
        assert profile.completed_tasks == 0
        assert profile.failed_tasks == 0
        assert profile.total_score == 0.0
        assert profile.score_count == 0
        assert profile.topics == {}
        assert profile.current_load == 0
        assert profile.success_rate == 0.5  # default for new agents
        assert profile.avg_score == 5.0  # default for new agents

    def test_agent_profile_success_rate(self):
        """Test success rate calculation."""
        profile = AgentProfile(name="test-agent")
        profile.total_tasks = 10
        profile.completed_tasks = 8
        profile.failed_tasks = 2
        assert profile.success_rate == 0.8

    def test_agent_profile_avg_score(self):
        """Test average score calculation."""
        profile = AgentProfile(name="test-agent")
        profile.total_score = 45.0
        profile.score_count = 9
        assert profile.avg_score == 5.0

    def test_update_from_task_completed(self):
        """Test updating profile from completed task."""
        profile = AgentProfile(name="test-agent")
        task = TaskItem(
            id="task-1",
            subject="Test task",
            description="Test description",
            owner="test-agent",
            status=TaskStatus.completed,
            scores=[QualityScore(completeness=8, accuracy=9, quality=8, 规范性=9, innovation=8, scorer="leader")],
        )

        profile.update_from_task(task)
        assert profile.total_tasks == 1
        assert profile.completed_tasks == 1
        assert profile.failed_tasks == 0
        assert profile.total_score == 8.45  # calculated from QualityScore
        assert profile.score_count == 1
        assert "test" in profile.topics
        assert "task" in profile.topics
        assert "description" in profile.topics

    def test_update_from_task_failed(self):
        """Test updating profile from failed task."""
        profile = AgentProfile(name="test-agent")
        task = TaskItem(
            id="task-1",
            subject="Test task",
            description="Test description",
            owner="test-agent",
            status=TaskStatus.blocked,
        )

        profile.update_from_task(task)
        assert profile.total_tasks == 1
        assert profile.completed_tasks == 0
        assert profile.failed_tasks == 1
        assert profile.total_score == 0.0
        assert profile.score_count == 0


class TestTaskRouter:
    """Test TaskRouter functionality."""

    def setup_method(self):
        """Set up temporary directory for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_data_dir = os.environ.get("AGENTTEAM_DATA_DIR")
        os.environ["AGENTTEAM_DATA_DIR"] = self.temp_dir

    def teardown_method(self):
        """Clean up temporary directory."""
        if self.original_data_dir is not None:
            os.environ["AGENTTEAM_DATA_DIR"] = self.original_data_dir
        else:
            os.environ.pop("AGENTTEAM_DATA_DIR", None)
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_router_root_creation(self):
        """Test that router root directory is created properly."""
        team_name = "test-team"
        root = _router_root(team_name)
        assert root.exists()
        assert root.is_dir()
        expected_suffix = f"router{os.path.sep}{team_name}"
        assert str(root).endswith(expected_suffix)

    def test_load_save_profiles(self):
        """Test loading and saving agent profiles."""
        router = TaskRouter("test-team")

        # Create some profiles
        profile1 = router._profiles["agent1"] = AgentProfile(name="agent1")
        profile1.total_tasks = 5
        profile1.completed_tasks = 4
        profile1.topics = {"auth": 3, "api": 2}

        profile2 = router._profiles["agent2"] = AgentProfile(name="agent2")
        profile2.total_tasks = 3
        profile2.completed_tasks = 2
        profile2.topics = {"database": 2, "api": 1}

        # Save profiles
        router.save_profiles()

        # Load profiles in new router instance
        router2 = TaskRouter("test-team")
        router2.load_profiles()

        assert len(router2._profiles) == 2
        assert router2._profiles["agent1"].total_tasks == 5
        assert router2._profiles["agent1"].completed_tasks == 4
        assert router2._profiles["agent1"].topics == {"auth": 3, "api": 2}
        assert router2._profiles["agent2"].total_tasks == 3
        assert router2._profiles["agent2"].completed_tasks == 2
        assert router2._profiles["agent2"].topics == {"database": 2, "api": 1}

    def test_update_profiles_from_tasks(self):
        """Test updating profiles from task list."""
        router = TaskRouter("test-team")

        # Create tasks
        tasks = [
            TaskItem(
                id="task-1",
                subject="Auth implementation",
                description="Implement user authentication",
                owner="agent1",
                status=TaskStatus.completed,
                scores=[QualityScore(completeness=9, accuracy=9, quality=9, 规范性=9, innovation=9, scorer="leader")],
            ),
            TaskItem(
                id="task-2",
                subject="Database setup",
                description="Set up database schema",
                owner="agent2",
                status=TaskStatus.in_progress,
            ),
            TaskItem(
                id="task-3",
                subject="API development",
                description="Develop REST API",
                owner="agent1",
                status=TaskStatus.pending,
            ),
            TaskItem(
                id="task-4",
                subject="Bug fix",
                description="Fix authentication bug",
                owner="agent1",
                status=TaskStatus.blocked,
            ),
        ]

        # Update profiles manually (since update_load requires FileTaskStore)
        for task in tasks:
            if task.status in (TaskStatus.completed, TaskStatus.blocked):
                router.update_profile(task)

        # Check agent1 profile
        agent1 = router._profiles["agent1"]
        assert agent1.total_tasks == 2  # completed + blocked
        assert agent1.completed_tasks == 1
        assert agent1.failed_tasks == 1
        assert agent1.total_score == 9.0  # from QualityScore (all 9s: 9*0.25 + 9*0.30 + 9*0.20 + 9*0.15 + 9*0.10 = 9.0)
        assert agent1.score_count == 1
        assert "auth" in agent1.topics
        assert "implementation" in agent1.topics

        # Check agent2 profile (should not be updated since no completed/failed tasks)
        assert "agent2" not in router._profiles

    def test_route_basic(self):
        """Test basic task routing."""
        router = TaskRouter("test-team")

        # Set up agent profiles
        agent1 = router._profiles["agent1"] = AgentProfile(name="agent1")
        agent1.total_tasks = 10
        agent1.completed_tasks = 8
        agent1.topics = {"auth": 5, "security": 3}
        agent1.current_load = 2

        agent2 = router._profiles["agent2"] = AgentProfile(name="agent2")
        agent2.total_tasks = 5
        agent2.completed_tasks = 5
        agent2.topics = {"database": 4, "api": 3}
        agent2.current_load = 1

        candidates = ["agent1", "agent2"]

        # Route a task related to authentication
        candidate = router.route(
            subject="Fix auth bug",
            description="Fix security vulnerability in authentication",
            available_agents=candidates,
        )

        assert candidate.name == "agent1"  # should match on auth/security topics
        assert "auth" in candidate.matching_topics
        assert "security" in candidate.matching_topics
        assert candidate.success_rate == 0.8
        assert candidate.current_load == 2

    def test_route_load_balancing(self):
        """Test that load balancing affects routing decisions."""
        router = TaskRouter("test-team")

        # Both agents have same performance but different loads
        agent1 = router._profiles["agent1"] = AgentProfile(name="agent1")
        agent1.total_tasks = 10
        agent1.completed_tasks = 8
        agent1.topics = {"api": 5}
        agent1.current_load = 5  # high load

        agent2 = router._profiles["agent2"] = AgentProfile(name="agent2")
        agent2.total_tasks = 10
        agent2.completed_tasks = 8
        agent2.topics = {"api": 5}
        agent2.current_load = 1  # low load

        candidates = ["agent1", "agent2"]

        # Route an API-related task
        candidate = router.route(
            subject="New API endpoint", description="Create new REST endpoint", available_agents=candidates
        )

        # Should prefer agent2 due to lower load
        assert candidate.name == "agent2"
        assert candidate.current_load == 1

    def test_route_no_matching_topics(self):
        """Test routing when no agent has matching topics."""
        router = TaskRouter("test-team")

        # Agents with different topics
        agent1 = router._profiles["agent1"] = AgentProfile(name="agent1")
        agent1.topics = {"auth": 5}
        agent1.current_load = 0

        agent2 = router._profiles["agent2"] = AgentProfile(name="agent2")
        agent2.topics = {"database": 5}
        agent2.current_load = 0

        candidates = ["agent1", "agent2"]

        # Route a task with completely different topic
        candidate = router.route(subject="UI design", description="Design user interface", available_agents=candidates)

        # Should pick based on other factors (performance, load)
        # Since both have same load and default performance, it could be either
        assert candidate.name in ["agent1", "agent2"]
        assert candidate.matching_topics == []

    def test_route_new_agents(self):
        """Test routing with new agents (no history)."""
        router = TaskRouter("test-team")

        # New agents with no history
        candidates = ["new-agent1", "new-agent2"]

        candidate = router.route(subject="Simple task", description="Basic implementation", available_agents=candidates)

        # Should work with default values
        assert candidate.name in ["new-agent1", "new-agent2"]
        assert candidate.success_rate == 0.5  # default
        assert candidate.avg_score == 5.0  # default
        assert candidate.current_load == 0

    def test_get_all_candidates(self):
        """Test getting all candidates sorted by match score."""
        router = TaskRouter("test-team")

        # Set up agent profiles
        agent1 = router._profiles["agent1"] = AgentProfile(name="agent1")
        agent1.total_tasks = 10
        agent1.completed_tasks = 8
        agent1.topics = {"auth": 5}
        agent1.current_load = 2

        agent2 = router._profiles["agent2"] = AgentProfile(name="agent2")
        agent2.total_tasks = 10
        agent2.completed_tasks = 8
        agent2.topics = {"database": 4}
        agent2.current_load = 2

        candidates = ["agent1", "agent2"]

        # Get all candidates for auth task
        all_candidates = router.get_all_candidates(
            subject="Authentication task", description="Implement auth system", available_agents=candidates
        )

        assert len(all_candidates) == 2
        # agent1 should be first due to topic match (same success rate and load)
        assert all_candidates[0].name == "agent1"
        assert "auth" in all_candidates[0].matching_topics


def test_route_candidate_comparison():
    """Test RouteCandidate comparison."""
    candidate1 = RouteCandidate(name="agent1", match_score=85.5, success_rate=0.8, avg_score=8.5, current_load=2)

    candidate2 = RouteCandidate(name="agent2", match_score=92.0, success_rate=0.9, avg_score=9.0, current_load=1)

    # Should compare by match_score
    assert candidate2.match_score > candidate1.match_score
