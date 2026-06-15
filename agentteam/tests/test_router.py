"""Tests for the intelligent task routing module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from agentteam.team.models import TaskItem, TaskStatus
from agentteam.team.router import (
    AgentProfile,
    RouteCandidate,
    TaskRouter,
    _extract_keywords,
    get_router,
)


def test_extract_keywords():
    """Test keyword extraction from text."""
    # English keywords (min 3 chars)
    assert _extract_keywords("Hello world! This is a test.") == {"hello", "world", "this", "test"}

    # Chinese keywords (using actual Chinese characters)
    chinese_text = "你好世界！这是一个测试。"
    chinese_keywords = _extract_keywords(chinese_text)
    # Should extract Chinese words (each Chinese character sequence)
    assert len(chinese_keywords) >= 2  # At least "你好世界" and "这是一个测试"

    # Mixed content
    mixed_text = "Hello world! This is a test."
    mixed_keywords = _extract_keywords(mixed_text)
    assert "hello" in mixed_keywords
    assert "world" in mixed_keywords
    assert "test" in mixed_keywords

    # Short words are filtered out (less than 3 chars)
    assert _extract_keywords("a an I") == set()
    assert _extract_keywords("the") == {"the"}  # "the" has 3 chars, so it's included

    # Empty input
    assert _extract_keywords("") == set()


def test_agent_profile_defaults():
    """Test AgentProfile default values and properties."""
    profile = AgentProfile(name="test-agent")

    assert profile.name == "test-agent"
    assert profile.total_tasks == 0
    assert profile.completed_tasks == 0
    assert profile.failed_tasks == 0
    assert profile.total_score == 0.0
    assert profile.score_count == 0
    assert profile.topics == {}
    assert profile.current_load == 0

    # Default success rate for new agents
    assert profile.success_rate == 0.5

    # Default average score for new agents
    assert profile.avg_score == 5.0


def test_agent_profile_update_from_task():
    """Test updating AgentProfile from completed tasks."""
    profile = AgentProfile(name="test-agent")

    # Create a completed task
    task = TaskItem(
        id="task1",
        subject="Test task",
        description="This is a test task for routing",
        status=TaskStatus.completed,
        owner="test-agent",
    )

    # Add quality scores
    from agentteam.team.models import QualityScore

    task.scores = [
        QualityScore(
            completeness=8,
            accuracy=9,
            quality=7,
            规范性=8,
            innovation=6,
            scorer="leader",
        )
    ]

    profile.update_from_task(task)

    assert profile.total_tasks == 1
    assert profile.completed_tasks == 1
    assert profile.failed_tasks == 0
    assert profile.score_count == 1
    assert (
        profile.total_score == 7.9
    )  # Calculated from QualityScore weights: 8*0.25 + 9*0.30 + 7*0.20 + 8*0.15 + 6*0.10 = 7.9

    # Check topic extraction
    expected_topics = {"test", "task", "this", "for", "routing"}
    assert set(profile.topics.keys()) == expected_topics
    for topic in expected_topics:
        assert profile.topics[topic] == 1


def test_agent_profile_update_from_failed_task():
    """Test updating AgentProfile from failed tasks."""
    profile = AgentProfile(name="test-agent")

    # Create a failed task (not completed)
    task = TaskItem(
        id="task1",
        subject="Failed task",
        description="This task failed",
        status=TaskStatus.blocked,  # Not completed
        owner="test-agent",
    )

    profile.update_from_task(task)

    assert profile.total_tasks == 1
    assert profile.completed_tasks == 0
    assert profile.failed_tasks == 1
    assert profile.success_rate == 0.0


def test_task_router_initialization():
    """Test TaskRouter initialization."""
    router = TaskRouter(team_name="test-team")

    assert router.team_name == "test-team"
    assert router._profiles == {}


@patch("agentteam.team.router.get_data_dir")
def test_task_router_load_save_profiles(mock_get_data_dir):
    """Test loading and saving agent profiles."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mock_get_data_dir.return_value = Path(tmpdir)

        router = TaskRouter(team_name="test-team")

        # Add a profile
        profile = AgentProfile(name="agent1")
        profile.total_tasks = 10
        profile.completed_tasks = 8
        profile.topics = {"python": 5, "testing": 3}
        router._profiles["agent1"] = profile

        # Save profiles
        router.save_profiles()

        # Load profiles into a new router
        new_router = TaskRouter(team_name="test-team")
        new_router.load_profiles()

        assert len(new_router._profiles) == 1
        loaded_profile = new_router._profiles["agent1"]
        assert loaded_profile.name == "agent1"
        assert loaded_profile.total_tasks == 10
        assert loaded_profile.completed_tasks == 8
        assert loaded_profile.topics == {"python": 5, "testing": 3}


@patch("agentteam.team.router.get_data_dir")
def test_task_router_route_basic(mock_get_data_dir):
    """Test basic routing functionality."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mock_get_data_dir.return_value = Path(tmpdir)

        router = TaskRouter(team_name="test-team")

        # Add some profiles
        profile1 = AgentProfile(name="python-expert")
        profile1.topics = {"python": 10, "testing": 5}
        profile1.completed_tasks = 20
        profile1.total_tasks = 25
        router._profiles["python-expert"] = profile1

        profile2 = AgentProfile(name="javascript-expert")
        profile2.topics = {"javascript": 10, "web": 8}
        profile2.completed_tasks = 15
        profile2.total_tasks = 20
        router._profiles["javascript-expert"] = profile2

        # Route a Python task
        candidate = router.route("Python testing task", "Write unit tests for Python code")

        assert candidate is not None
        assert candidate.name == "python-expert"
        assert candidate.match_score > 0
        assert "python" in candidate.matching_topics
        assert "testing" in candidate.matching_topics

        # Route a JavaScript task
        candidate = router.route("JavaScript web task", "Build a React component")

        assert candidate is not None
        assert candidate.name == "javascript-expert"
        assert "javascript" in candidate.matching_topics
        assert "web" in candidate.matching_topics


@patch("agentteam.team.router.get_data_dir")
def test_task_router_route_with_load_penalty(mock_get_data_dir):
    """Test routing considers current load as a penalty."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mock_get_data_dir.return_value = Path(tmpdir)

        router = TaskRouter(team_name="test-team")

        # Two agents with same skills, but different loads
        profile1 = AgentProfile(name="agent1")
        profile1.topics = {"python": 10}
        profile1.completed_tasks = 10
        profile1.total_tasks = 10
        profile1.current_load = 0  # Not busy
        router._profiles["agent1"] = profile1

        profile2 = AgentProfile(name="agent2")
        profile2.topics = {"python": 10}
        profile2.completed_tasks = 10
        profile2.total_tasks = 10
        profile2.current_load = 5  # Very busy
        router._profiles["agent2"] = profile2

        # Should prefer the less busy agent
        candidate = router.route("Python task", "Simple Python task")

        assert candidate.name == "agent1"
        # The match score should be higher for the less busy agent
        candidates = router.get_all_candidates("Python task", "Simple Python task")
        agent1_score = next(c.match_score for c in candidates if c.name == "agent1")
        agent2_score = next(c.match_score for c in candidates if c.name == "agent2")
        assert agent1_score > agent2_score


@patch("agentteam.team.router.get_data_dir")
def test_task_router_get_all_candidates(mock_get_data_dir):
    """Test getting all candidates sorted by match score."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mock_get_data_dir.return_value = Path(tmpdir)

        router = TaskRouter(team_name="test-team")

        # Add multiple profiles with different success rates
        profile0 = AgentProfile(name="agent0")
        profile0.topics = {"task": 1}
        profile0.completed_tasks = 5
        profile0.total_tasks = 10  # 50% success rate
        router._profiles["agent0"] = profile0

        profile1 = AgentProfile(name="agent1")
        profile1.topics = {"task": 1}
        profile1.completed_tasks = 8
        profile1.total_tasks = 10  # 80% success rate
        router._profiles["agent1"] = profile1

        profile2 = AgentProfile(name="agent2")
        profile2.topics = {"task": 1}
        profile2.completed_tasks = 9
        profile2.total_tasks = 10  # 90% success rate
        router._profiles["agent2"] = profile2

        candidates = router.get_all_candidates("Test task", "Simple test")

        assert len(candidates) == 3
        # Should be sorted by match score (which includes success rate)
        assert candidates[0].name == "agent2"  # Highest success rate
        assert candidates[1].name == "agent1"
        assert candidates[2].name == "agent0"


@patch("agentteam.team.router.get_data_dir")
def test_task_router_route_with_candidates_filter(mock_get_data_dir):
    """Test routing with specific candidate list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mock_get_data_dir.return_value = Path(tmpdir)

        router = TaskRouter(team_name="test-team")

        # Add multiple profiles
        for name in ["agent1", "agent2", "agent3"]:
            profile = AgentProfile(name=name)
            profile.topics = {"task": 1}
            router._profiles[name] = profile

        # Only consider agent1 and agent2
        candidate = router.route("Test task", "Simple test", available_agents=["agent1", "agent2"])

        assert candidate.name in ["agent1", "agent2"]
        all_candidates = router.get_all_candidates("Test task", "Simple test", ["agent1", "agent2"])
        candidate_names = [c.name for c in all_candidates]
        assert "agent1" in candidate_names
        assert "agent2" in candidate_names
        assert "agent3" not in candidate_names


@patch("agentteam.team.router.get_data_dir")
def test_get_router_function(mock_get_data_dir):
    """Test the get_router convenience function."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mock_get_data_dir.return_value = Path(tmpdir)

        router = get_router("test-team")

        assert isinstance(router, TaskRouter)
        assert router.team_name == "test-team"


def test_route_candidate_dataclass():
    """Test RouteCandidate dataclass."""
    candidate = RouteCandidate(
        name="test-agent",
        match_score=85.5,
        success_rate=0.9,
        avg_score=8.5,
        current_load=2,
        matching_topics=["python", "testing"],
    )

    assert candidate.name == "test-agent"
    assert candidate.match_score == 85.5
    assert candidate.success_rate == 0.9
    assert candidate.avg_score == 8.5
    assert candidate.current_load == 2
    assert candidate.matching_topics == ["python", "testing"]


@patch("agentteam.team.router.get_data_dir")
def test_task_router_empty_routing(mock_get_data_dir):
    """Test routing when no profiles exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mock_get_data_dir.return_value = Path(tmpdir)

        router = TaskRouter(team_name="test-team")

        # No profiles
        candidate = router.route("Test task", "Simple test")
        assert candidate is None

        candidates = router.get_all_candidates("Test task", "Simple test")
        assert candidates == []


@patch("agentteam.team.router.get_data_dir")
def test_task_router_update_profile_new_agent(mock_get_data_dir):
    """Test updating profile for a new agent."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mock_get_data_dir.return_value = Path(tmpdir)

        router = TaskRouter(team_name="test-team")

        # Update profile for an agent that doesn't exist yet
        task = TaskItem(
            id="task1",
            subject="New agent task",
            description="Task for new agent",
            status=TaskStatus.completed,
            owner="new-agent",
        )

        router.update_profile(task)

        assert "new-agent" in router._profiles
        profile = router._profiles["new-agent"]
        assert profile.name == "new-agent"
        assert profile.total_tasks == 1
        assert profile.completed_tasks == 1


@patch("agentteam.store.get_task_store")
@patch("agentteam.team.router.get_data_dir")
def test_task_router_update_load(mock_get_data_dir, mock_store_class):
    """Test updating current load from task store."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mock_get_data_dir.return_value = Path(tmpdir)

        # Mock the task store
        mock_store = Mock()
        mock_store_class.return_value = mock_store

        # Mock in-progress tasks
        mock_task1 = Mock()
        mock_task1.owner = "agent1"
        mock_task2 = Mock()
        mock_task2.owner = "agent2"
        mock_task3 = Mock()
        mock_task3.owner = "agent1"  # agent1 has 2 tasks

        # Configure the mock to return the tasks when called with status=TaskStatus.in_progress
        mock_store.list_tasks.return_value = [mock_task1, mock_task2, mock_task3]

        router = TaskRouter(team_name="test-team")

        # Add profiles
        router._profiles["agent1"] = AgentProfile(name="agent1")
        router._profiles["agent2"] = AgentProfile(name="agent2")
        router._profiles["agent3"] = AgentProfile(name="agent3")  # No in-progress tasks

        router.update_load("test-team")

        assert router._profiles["agent1"].current_load == 2
        assert router._profiles["agent2"].current_load == 1
        assert router._profiles["agent3"].current_load == 0


# Integration test for the CLI command would go here, but it's complex to mock
# the typer CLI framework. The individual components are tested above.


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
