"""Dynamic role assignment for ClawTeam agents.

Manages agent roles (developer, reviewer, tester, architect, coordinator)
with persistent storage per team.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from clawteam.fileutil import atomic_write_text
from clawteam.paths import ensure_within_root, validate_identifier
from clawteam.team.models import TaskItem, TaskStatus, get_data_dir


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _roles_path(team: str) -> Path:
    """Return the path to the roles.json file for a team."""
    d = ensure_within_root(
        get_data_dir() / "teams" / team,
        validate_identifier(team, "team name"),
    )
    d.mkdir(parents=True, exist_ok=True)
    return d / "roles.json"


class AgentRole(str, Enum):
    """Available roles an agent can be assigned."""

    developer = "developer"
    reviewer = "reviewer"
    tester = "tester"
    architect = "architect"
    coordinator = "coordinator"


class RoleAssignment(BaseModel):
    """A single role assignment for an agent."""

    agent_name: str
    role: AgentRole
    assigned_at: str = Field(default_factory=_now_iso)
    expires_at: str | None = Field(default=None)


class RoleStore(BaseModel):
    """Persistent storage for role assignments, keyed by agent name."""

    model_config = {"arbitrary_types_allowed": True}

    assignments: dict[str, list[RoleAssignment]] = Field(default_factory=dict)
    """agent_name -> list of RoleAssignment (one per role)"""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        return {
            agent: [
                {
                    "agent_name": a.agent_name,
                    "role": a.role.value,
                    "assigned_at": a.assigned_at,
                    "expires_at": a.expires_at,
                }
                for a in assignments
            ]
            for agent, assignments in self.assignments.items()
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RoleStore:
        """Deserialize from a JSON-compatible dict."""
        store = cls()
        for agent, assignments_data in data.items():
            store.assignments[agent] = [
                RoleAssignment(
                    agent_name=a["agent_name"],
                    role=AgentRole(a["role"]),
                    assigned_at=a.get("assigned_at", _now_iso()),
                    expires_at=a.get("expires_at"),
                )
                for a in assignments_data
            ]
        return store


def _load_roles(team: str) -> RoleStore:
    """Load role assignments from disk."""
    path = _roles_path(team)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        return RoleStore.from_dict(data)
    return RoleStore()


def _save_roles(team: str, store: RoleStore) -> None:
    """Save role assignments to disk."""
    path = _roles_path(team)
    atomic_write_text(path, json.dumps(store.to_dict(), ensure_ascii=False, indent=2))


def assign_role(
    team: str,
    agent_name: str,
    role: AgentRole | str,
    expires_at: str | None = None,
) -> RoleAssignment:
    """Assign a role to an agent.

    If the agent already has this role, it is replaced with the new assignment.

    Args:
        team: Team name.
        agent_name: Agent name to assign the role to.
        role: Role to assign (AgentRole enum or string).
        expires_at: Optional expiration timestamp (ISO format).

    Returns:
        The created RoleAssignment.
    """
    if isinstance(role, str):
        role = AgentRole(role)

    store = _load_roles(team)
    assignments = store.assignments.setdefault(agent_name, [])

    # Replace existing assignment for this role, or append
    replaced = False
    for i, existing in enumerate(assignments):
        if existing.role == role:
            assignments[i] = RoleAssignment(
                agent_name=agent_name,
                role=role,
                assigned_at=_now_iso(),
                expires_at=expires_at,
            )
            replaced = True
            break

    if not replaced:
        assignments.append(
            RoleAssignment(
                agent_name=agent_name,
                role=role,
                assigned_at=_now_iso(),
                expires_at=expires_at,
            )
        )

    _save_roles(team, store)

    # Return the assignment we just created
    for a in store.assignments[agent_name]:
        if a.role == role:
            return a

    # Should never reach here, but just in case
    return RoleAssignment(agent_name=agent_name, role=role, expires_at=expires_at)


def unassign_role(team: str, agent_name: str, role: AgentRole | str) -> bool:
    """Remove a role from an agent.

    Args:
        team: Team name.
        agent_name: Agent name to remove the role from.
        role: Role to remove (AgentRole enum or string).

    Returns:
        True if the role was found and removed, False otherwise.
    """
    if isinstance(role, str):
        role = AgentRole(role)

    store = _load_roles(team)
    assignments = store.assignments.get(agent_name, [])

    new_assignments = [a for a in assignments if a.role != role]
    if len(new_assignments) == len(assignments):
        return False

    if new_assignments:
        store.assignments[agent_name] = new_assignments
    else:
        del store.assignments[agent_name]

    _save_roles(team, store)
    return True


def get_agent_roles(team: str, agent_name: str) -> list[AgentRole]:
    """Get all roles assigned to an agent.

    Args:
        team: Team name.
        agent_name: Agent name to query.

    Returns:
        List of AgentRole enums assigned to this agent.
    """
    store = _load_roles(team)
    assignments = store.assignments.get(agent_name, [])

    # Filter out expired assignments
    now = datetime.now(timezone.utc)
    valid_roles: list[AgentRole] = []
    for a in assignments:
        if a.expires_at:
            try:
                expires = datetime.fromisoformat(a.expires_at)
                if expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)
                if expires <= now:
                    continue
            except (ValueError, TypeError):
                pass
        valid_roles.append(a.role)

    return valid_roles


def get_agents_with_role(team: str, role: AgentRole | str) -> list[str]:
    """Get all agents assigned a specific role.

    Args:
        team: Team name.
        role: Role to filter by (AgentRole enum or string).

    Returns:
        List of agent names that have this role.
    """
    if isinstance(role, str):
        role = AgentRole(role)

    store = _load_roles(team)
    agents: list[str] = []

    for agent_name, assignments in store.assignments.items():
        for a in assignments:
            if a.role == role:
                # Check expiration
                if a.expires_at:
                    try:
                        expires = datetime.fromisoformat(a.expires_at)
                        if expires.tzinfo is None:
                            expires = expires.replace(tzinfo=timezone.utc)
                        if expires <= datetime.now(timezone.utc):
                            continue
                    except (ValueError, TypeError):
                        pass
                agents.append(agent_name)
                break

    return agents


def get_all_assignments(team: str) -> dict[str, list[RoleAssignment]]:
    """Get all role assignments for a team.

    Args:
        team: Team name.

    Returns:
        Dict mapping agent names to their list of RoleAssignment.
    """
    store = _load_roles(team)
    return dict(store.assignments)


# Keyword hints for automatic role suggestion
_ROLE_KEYWORDS: dict[AgentRole, list[str]] = {
    AgentRole.developer: [
        "implement",
        "code",
        "develop",
        "build",
        "feature",
        "function",
        "class",
        "module",
        "api",
        "backend",
        "frontend",
        "write",
        "重构",
        "实现",
        "开发",
        "编码",
        "编写",
    ],
    AgentRole.reviewer: [
        "review",
        "audit",
        "check",
        "verify",
        "inspect",
        "evaluate",
        "code review",
        "pr review",
        "pull request",
        "审查",
        "评审",
        "检查",
        "评估",
    ],
    AgentRole.tester: [
        "test",
        "unit test",
        "integration test",
        "e2e",
        "qa",
        "quality",
        "coverage",
        "assert",
        "mock",
        "fixture",
        "spec",
        "测试",
        "单元测试",
        "集成测试",
        "质量",
    ],
    AgentRole.architect: [
        "design",
        "architecture",
        "plan",
        "structure",
        "system design",
        "pattern",
        "blueprint",
        "specification",
        "schema",
        "设计",
        "架构",
        "规划",
        "蓝图",
        "方案",
    ],
    AgentRole.coordinator: [
        "coordinate",
        "manage",
        "organize",
        "schedule",
        "delegate",
        "communicate",
        "report",
        "status",
        "sync",
        "standup",
        "协调",
        "管理",
        "组织",
        "同步",
        "汇报",
    ],
}


def suggest_role(
    task: TaskItem,
    agent_name: str,
    router: Any = None,
) -> AgentRole:
    """Suggest the best role for an agent based on task content and history.

    Uses keyword matching on the task subject and description to suggest
    the most appropriate role. If a router is provided, also considers
    the agent's historical performance.

    Args:
        task: The TaskItem to analyze.
        agent_name: The agent name to suggest a role for.
        router: Optional TaskRouter instance for history-based suggestions.

    Returns:
        The suggested AgentRole.
    """
    # Combine subject and description for keyword matching
    text = f"{task.subject} {task.description}".lower()

    # Score each role by keyword overlap
    best_role: AgentRole = AgentRole.developer  # default
    best_score = 0

    for role, keywords in _ROLE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > best_score:
            best_score = score
            best_role = role

    # If router is available, check agent's historical strengths
    if router is not None:
        try:
            router.load_profiles()
            profile = router._profiles.get(agent_name)
            if profile and profile.topics:
                # Check if agent has strong history in a specific area
                role_topic_scores: dict[AgentRole, int] = {}
                for topic, count in profile.topics.items():
                    for role, keywords in _ROLE_KEYWORDS.items():
                        if any(kw in topic for kw in keywords):
                            role_topic_scores[role] = role_topic_scores.get(role, 0) + count

                if role_topic_scores:
                    history_best = max(role_topic_scores, key=role_topic_scores.get)
                    # Only override if history score is meaningful (> 2 tasks)
                    if role_topic_scores.get(history_best, 0) >= 2:
                        best_role = history_best
        except Exception:
            pass  # Fall back to keyword-based suggestion

    return best_role
