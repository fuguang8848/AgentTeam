"""Tests for agentteam.team.roles — dynamic role assignment."""

from datetime import datetime, timezone, timedelta

import pytest

from agentteam.team.roles import (
    AgentRole,
    RoleAssignment,
    RoleStore,
    assign_role,
    get_agent_roles,
    get_agents_with_role,
    get_all_assignments,
    suggest_role,
    unassign_role,
)
from agentteam.team.models import TaskItem, TaskPriority, TaskStatus


class TestAgentRole:
    """Tests for AgentRole enum."""

    def test_all_roles_exist(self):
        """All five roles are defined."""
        roles = [r.value for r in AgentRole]
        assert "developer" in roles
        assert "reviewer" in roles
        assert "tester" in roles
        assert "architect" in roles
        assert "coordinator" in roles

    def test_role_from_string(self):
        """Can create AgentRole from string value."""
        assert AgentRole("developer") == AgentRole.developer
        assert AgentRole("reviewer") == AgentRole.reviewer

    def test_invalid_role_raises(self):
        """Invalid role string raises ValueError."""
        with pytest.raises(ValueError):
            AgentRole("invalid_role")


class TestRoleAssignment:
    """Tests for RoleAssignment model."""

    def test_create_assignment(self):
        """Can create a RoleAssignment."""
        a = RoleAssignment(agent_name="alice", role=AgentRole.developer)
        assert a.agent_name == "alice"
        assert a.role == AgentRole.developer
        assert a.assigned_at is not None
        assert a.expires_at is None

    def test_assignment_with_expiry(self):
        """Can create a RoleAssignment with expiration."""
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        a = RoleAssignment(agent_name="bob", role=AgentRole.tester, expires_at=future)
        assert a.expires_at == future

    def test_assignment_serialization(self):
        """RoleAssignment can be serialized and deserialized."""
        a = RoleAssignment(agent_name="carol", role=AgentRole.architect)
        data = a.model_dump()
        assert data["agent_name"] == "carol"
        assert data["role"] == "architect"


class TestRoleStore:
    """Tests for RoleStore serialization."""

    def test_empty_store(self):
        """Empty store serializes to empty dict."""
        store = RoleStore()
        data = store.to_dict()
        assert data == {}

    def test_store_roundtrip(self):
        """Store can be serialized and deserialized."""
        store = RoleStore()
        store.assignments["alice"] = [
            RoleAssignment(agent_name="alice", role=AgentRole.developer),
        ]
        data = store.to_dict()
        restored = RoleStore.from_dict(data)
        assert "alice" in restored.assignments
        assert restored.assignments["alice"][0].role == AgentRole.developer


class TestAssignRole:
    """Tests for assign_role()."""

    def test_assign_new_role(self, team_name):
        """Assigning a new role to an agent."""
        assignment = assign_role(team_name, "alice", AgentRole.developer)
        assert assignment.agent_name == "alice"
        assert assignment.role == AgentRole.developer

    def test_assign_string_role(self, team_name):
        """Can assign role using string value."""
        assignment = assign_role(team_name, "bob", "reviewer")
        assert assignment.role == AgentRole.reviewer

    def test_assign_multiple_roles(self, team_name):
        """Agent can have multiple roles."""
        assign_role(team_name, "alice", AgentRole.developer)
        assign_role(team_name, "alice", AgentRole.reviewer)
        roles = get_agent_roles(team_name, "alice")
        assert AgentRole.developer in roles
        assert AgentRole.reviewer in roles

    def test_replace_existing_role(self, team_name):
        """Re-assigning same role replaces the old assignment."""
        assign_role(team_name, "alice", AgentRole.developer)
        assign_role(team_name, "alice", AgentRole.developer)
        roles = get_agent_roles(team_name, "alice")
        # Should only have one developer role
        assert roles.count(AgentRole.developer) == 1

    def test_assign_with_expiry(self, team_name):
        """Can assign role with expiration."""
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        assignment = assign_role(team_name, "alice", AgentRole.tester, expires_at=future)
        assert assignment.expires_at == future


class TestUnassignRole:
    """Tests for unassign_role()."""

    def test_unassign_existing(self, team_name):
        """Removing an existing role returns True."""
        assign_role(team_name, "alice", AgentRole.developer)
        result = unassign_role(team_name, "alice", AgentRole.developer)
        assert result is True
        roles = get_agent_roles(team_name, "alice")
        assert AgentRole.developer not in roles

    def test_unassign_nonexistent(self, team_name):
        """Removing a non-existent role returns False."""
        result = unassign_role(team_name, "alice", AgentRole.developer)
        assert result is False

    def test_unassign_string_role(self, team_name):
        """Can unassign role using string value."""
        assign_role(team_name, "alice", "reviewer")
        result = unassign_role(team_name, "alice", "reviewer")
        assert result is True

    def test_unassign_preserves_other_roles(self, team_name):
        """Unassigning one role keeps other roles intact."""
        assign_role(team_name, "alice", AgentRole.developer)
        assign_role(team_name, "alice", AgentRole.reviewer)
        unassign_role(team_name, "alice", AgentRole.developer)
        roles = get_agent_roles(team_name, "alice")
        assert AgentRole.developer not in roles
        assert AgentRole.reviewer in roles


class TestGetAgentRoles:
    """Tests for get_agent_roles()."""

    def test_no_roles(self, team_name):
        """Agent with no roles returns empty list."""
        roles = get_agent_roles(team_name, "unknown")
        assert roles == []

    def test_multiple_roles(self, team_name):
        """Agent with multiple roles returns all of them."""
        assign_role(team_name, "alice", AgentRole.developer)
        assign_role(team_name, "alice", AgentRole.tester)
        roles = get_agent_roles(team_name, "alice")
        assert len(roles) == 2

    def test_expired_role_excluded(self, team_name):
        """Expired roles are not returned."""
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        assign_role(team_name, "alice", AgentRole.developer, expires_at=past)
        roles = get_agent_roles(team_name, "alice")
        assert AgentRole.developer not in roles


class TestGetAgentsWithRole:
    """Tests for get_agents_with_role()."""

    def test_no_agents(self, team_name):
        """No agents with a role returns empty list."""
        agents = get_agents_with_role(team_name, AgentRole.developer)
        assert agents == []

    def test_multiple_agents(self, team_name):
        """Multiple agents can have the same role."""
        assign_role(team_name, "alice", AgentRole.developer)
        assign_role(team_name, "bob", AgentRole.developer)
        assign_role(team_name, "carol", AgentRole.reviewer)
        agents = get_agents_with_role(team_name, AgentRole.developer)
        assert sorted(agents) == ["alice", "bob"]

    def test_string_role(self, team_name):
        """Can query using string role value."""
        assign_role(team_name, "alice", "tester")
        agents = get_agents_with_role(team_name, "tester")
        assert "alice" in agents

    def test_expired_agent_excluded(self, team_name):
        """Agents with expired role assignments are excluded."""
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        assign_role(team_name, "alice", AgentRole.developer, expires_at=past)
        assign_role(team_name, "bob", AgentRole.developer)
        agents = get_agents_with_role(team_name, AgentRole.developer)
        assert "alice" not in agents
        assert "bob" in agents


class TestGetAllAssignments:
    """Tests for get_all_assignments()."""

    def test_empty(self, team_name):
        """No assignments returns empty dict."""
        assignments = get_all_assignments(team_name)
        assert assignments == {}

    def test_multiple_agents(self, team_name):
        """Returns all assignments for all agents."""
        assign_role(team_name, "alice", AgentRole.developer)
        assign_role(team_name, "bob", AgentRole.tester)
        assignments = get_all_assignments(team_name)
        assert "alice" in assignments
        assert "bob" in assignments
        assert len(assignments["alice"]) == 1
        assert len(assignments["bob"]) == 1


class TestSuggestRole:
    """Tests for suggest_role()."""

    def test_suggest_developer(self, team_name):
        """Code-related task suggests developer."""
        task = TaskItem(
            id="t1", subject="Implement user authentication API",
            description="Write backend code for login and registration endpoints",
        )
        role = suggest_role(task, "alice")
        assert role == AgentRole.developer

    def test_suggest_reviewer(self, team_name):
        """Review-related task suggests reviewer."""
        task = TaskItem(
            id="t2", subject="Review PR #42 for security issues",
            description="Audit the code changes and verify no vulnerabilities",
        )
        role = suggest_role(task, "alice")
        assert role == AgentRole.reviewer

    def test_suggest_tester(self, team_name):
        """Test-related task suggests tester."""
        task = TaskItem(
            id="t3", subject="Run integration tests and QA for payment module",
            description="Create comprehensive test coverage with mocks and fixtures",
        )
        role = suggest_role(task, "alice")
        assert role == AgentRole.tester

    def test_suggest_architect(self, team_name):
        """Design-related task suggests architect."""
        task = TaskItem(
            id="t4", subject="Design microservice architecture",
            description="Plan the system design and create blueprints for service communication",
        )
        role = suggest_role(task, "alice")
        assert role == AgentRole.architect

    def test_suggest_coordinator(self, team_name):
        """Coordination-related task suggests coordinator."""
        task = TaskItem(
            id="t5", subject="Coordinate sprint planning meeting",
            description="Organize the team and manage the schedule for the next sprint",
        )
        role = suggest_role(task, "alice")
        assert role == AgentRole.coordinator

    def test_default_to_developer(self, team_name):
        """Generic task defaults to developer."""
        task = TaskItem(id="t6", subject="General task", description="Do some work")
        role = suggest_role(task, "alice")
        assert role == AgentRole.developer

    def test_chinese_keywords(self, team_name):
        """Chinese keywords are also recognized."""
        task = TaskItem(
            id="t7", subject="编写单元测试",
            description="为支付模块创建全面的测试覆盖",
        )
        role = suggest_role(task, "alice")
        assert role == AgentRole.tester
