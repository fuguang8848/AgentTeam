"""Intelligent task routing for ClawTeam multi-agent teams.

Routes tasks to the best-matched agent based on:
- Historical performance (success rate, quality scores)
- Current workload (number of in-progress tasks)
- Skill/topic matching (keyword-based)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from clawteam.fileutil import atomic_write_text
from clawteam.paths import ensure_within_root, validate_identifier
from clawteam.team.models import TaskItem, TaskStatus, get_data_dir


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _router_root(team_name: str) -> Path:
    d = ensure_within_root(get_data_dir() / "router", validate_identifier(team_name, "team name"))
    d.mkdir(parents=True, exist_ok=True)
    return d


# Simple keyword extraction for topic matching
_TOPIC_KEYWORDS = re.compile(r"[a-zA-Z]{3,}|[\u4e00-\u9fff]")


def _extract_keywords(text: str) -> set[str]:
    """Extract keywords from text for topic matching."""
    return set(_TOPIC_KEYWORDS.findall(text.lower()))


@dataclass
class AgentProfile:
    """Profile of an agent's capabilities and performance."""

    name: str
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    total_score: float = 0.0
    score_count: int = 0
    topics: dict[str, int] = field(default_factory=dict)  # keyword -> count
    current_load: int = 0  # number of in-progress tasks

    @property
    def success_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.5  # default for new agents
        return self.completed_tasks / self.total_tasks

    @property
    def avg_score(self) -> float:
        if self.score_count == 0:
            return 5.0  # default for new agents
        return self.total_score / self.score_count

    def update_from_task(self, task: TaskItem) -> None:
        """Update profile from a completed task."""
        if task.owner != self.name:
            return

        self.total_tasks += 1
        if task.status == TaskStatus.completed:
            self.completed_tasks += 1
        else:
            self.failed_tasks += 1

        # Extract topics from subject and description
        keywords = _extract_keywords(task.subject + " " + task.description)
        for kw in keywords:
            self.topics[kw] = self.topics.get(kw, 0) + 1

        # Update scores if available
        if task.scores:
            for score in task.scores:
                # Convert 0-100 score to 0-10 range for avg_score calculation
                self.total_score += score.total / 10.0
                self.score_count += 1


@dataclass
class RouteCandidate:
    """A candidate agent for task assignment."""

    name: str
    match_score: float  # 0-100, higher is better
    success_rate: float
    avg_score: float
    current_load: int
    matching_topics: list[str] = field(default_factory=list)


class TaskRouter:
    """Intelligent task router based on agent profiles and task characteristics."""

    def __init__(self, team_name: str):
        self.team_name = team_name
        self._profiles: dict[str, AgentProfile] = {}

    def load_profiles(self) -> None:
        """Load agent profiles from disk."""
        path = _router_root(self.team_name) / "profiles.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            for name, profile_data in data.items():
                self._profiles[name] = AgentProfile(**profile_data)

    def save_profiles(self) -> None:
        """Save agent profiles to disk."""
        path = _router_root(self.team_name) / "profiles.json"
        data = {
            name: {
                "name": p.name,
                "total_tasks": p.total_tasks,
                "completed_tasks": p.completed_tasks,
                "failed_tasks": p.failed_tasks,
                "total_score": p.total_score,
                "score_count": p.score_count,
                "topics": p.topics,
                "current_load": p.current_load,
            }
            for name, p in self._profiles.items()
        }
        atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=2))

    def update_profile(self, task: TaskItem) -> None:
        """Update profile for an agent based on a completed task."""
        if not task.owner:
            return

        if task.owner not in self._profiles:
            self._profiles[task.owner] = AgentProfile(name=task.owner)

        self._profiles[task.owner].update_from_task(task)
        self.save_profiles()

    def update_load(self, team_name: str) -> None:
        """Update current load for all agents from task store."""
        from clawteam.store import get_task_store

        store = get_task_store(team_name)
        in_progress = store.list_tasks(status=TaskStatus.in_progress)

        # Reset all loads
        for profile in self._profiles.values():
            profile.current_load = 0

        # Count in-progress tasks per agent
        for task in in_progress:
            if task.owner and task.owner in self._profiles:
                self._profiles[task.owner].current_load += 1

        self.save_profiles()

    def route(
        self, subject: str, description: str, available_agents: list[str] | None = None
    ) -> RouteCandidate | None:
        """Find the best agent for a task.

        Args:
            subject: Task subject
            description: Task description
            available_agents: Optional list of candidate agent names. If None, use all known agents.

        Returns:
            RouteCandidate with match score, or None if no candidates available.
        """
        task_keywords = _extract_keywords(subject + " " + description)
        if not task_keywords:
            task_keywords = {"general"}

        if available_agents:
            profiles = {n: p for n, p in self._profiles.items() if n in available_agents}
            # Add default profiles for agents not in _profiles
            for name in available_agents:
                if name not in profiles:
                    profiles[name] = AgentProfile(name=name)
        else:
            profiles = self._profiles

        if not profiles:
            return None

        candidates_list = []
        for name, profile in profiles.items():
            # Calculate topic match score (0-50)
            matching_topics = task_keywords & set(profile.topics.keys())
            topic_match = len(matching_topics) / max(len(task_keywords), 1) * 50

            # Calculate success rate score (0-30)
            success_score = profile.success_rate * 30

            # Calculate quality score (0-20)
            quality_score = min(profile.avg_score / 10, 1.0) * 20

            # Load penalty (reduce score for busy agents)
            load_penalty = min(profile.current_load * 5, 15)

            total_score = topic_match + success_score + quality_score - load_penalty

            candidates_list.append(
                RouteCandidate(
                    name=name,
                    match_score=round(total_score, 2),
                    success_rate=profile.success_rate,
                    avg_score=profile.avg_score,
                    current_load=profile.current_load,
                    matching_topics=list(matching_topics),
                )
            )

        # Sort by match score descending
        candidates_list.sort(key=lambda c: c.match_score, reverse=True)
        return candidates_list[0] if candidates_list else None

    def get_all_candidates(
        self, subject: str, description: str, available_agents: list[str] | None = None
    ) -> list[RouteCandidate]:
        """Get all candidates sorted by match score."""
        task_keywords = _extract_keywords(subject + " " + description)
        if not task_keywords:
            task_keywords = {"general"}

        if available_agents:
            profiles = {n: p for n, p in self._profiles.items() if n in available_agents}
        else:
            profiles = self._profiles

        result = []
        for name, profile in profiles.items():
            matching_topics = task_keywords & set(profile.topics.keys())
            topic_match = len(matching_topics) / max(len(task_keywords), 1) * 50
            success_score = profile.success_rate * 30
            quality_score = min(profile.avg_score / 10, 1.0) * 20
            load_penalty = min(profile.current_load * 5, 15)
            total_score = topic_match + success_score + quality_score - load_penalty

            result.append(
                RouteCandidate(
                    name=name,
                    match_score=round(total_score, 2),
                    success_rate=profile.success_rate,
                    avg_score=profile.avg_score,
                    current_load=profile.current_load,
                    matching_topics=list(matching_topics),
                )
            )

        result.sort(key=lambda c: c.match_score, reverse=True)
        return result


# Convenience function
def get_router(team_name: str) -> TaskRouter:
    """Get a TaskRouter instance with profiles loaded."""
    router = TaskRouter(team_name)
    router.load_profiles()
    return router
