"""Tests for board renderer."""

from __future__ import annotations

from io import StringIO

from rich.console import Console

from agentteam.board.renderer import BoardRenderer


class TestBoardRenderer:
    """Test BoardRenderer class."""

    def test_render_overview_empty_teams(self):
        """Test rendering overview with no teams."""
        console = Console(file=StringIO(), force_terminal=True)
        renderer = BoardRenderer(console=console)
        renderer.render_overview([])
        output = console.file.getvalue()
        assert "No teams found" in output

    def test_render_overview_with_teams(self):
        """Test rendering overview with multiple teams."""
        console = Console(file=StringIO(), force_terminal=True, width=100)
        renderer = BoardRenderer(console=console)
        teams = [
            {"name": "team1", "leader": "alice", "members": 3, "tasks": 10, "pendingMessages": 2},
            {"name": "team2", "leader": "bob", "members": 5, "tasks": 20, "pendingMessages": 0},
        ]
        renderer.render_overview(teams)
        output = console.file.getvalue()
        assert "team1" in output
        assert "team2" in output
        assert "alice" in output
        assert "bob" in output

    def test_build_team_board_basic(self):
        """Test building a basic team board."""
        renderer = BoardRenderer()
        data = {
            "team": {
                "name": "test-team",
                "leaderName": "leader1",
                "createdAt": "2024-01-01T10:00:00Z",
            },
            "members": [
                {
                    "name": "agent1",
                    "agentType": "worker",
                    "joinedAt": "2024-01-01T10:05:00Z",
                    "inboxCount": 0,
                },
            ],
            "tasks": {
                "pending": [],
                "in_progress": [],
                "completed": [],
                "blocked": [],
            },
            "taskSummary": {
                "pending": 0,
                "in_progress": 0,
                "completed": 0,
                "blocked": 0,
                "total": 0,
            },
        }
        result = renderer._build_team_board(data)
        assert result is not None

    def test_build_team_board_with_tasks(self):
        """Test building a team board with tasks."""
        renderer = BoardRenderer()
        data = {
            "team": {
                "name": "test-team",
                "leaderName": "leader1",
                "createdAt": "2024-01-01T10:00:00Z",
            },
            "members": [
                {
                    "name": "agent1",
                    "agentType": "worker",
                    "joinedAt": "2024-01-01T10:05:00Z",
                    "inboxCount": 2,
                },
            ],
            "tasks": {
                "pending": [{"id": "task-001", "subject": "Task 1", "owner": None}],
                "in_progress": [{"id": "task-002", "subject": "Task 2", "owner": "agent1", "lockedBy": "agent1"}],
                "completed": [{"id": "task-003", "subject": "Task 3", "owner": "agent1"}],
                "blocked": [{"id": "task-004", "subject": "Task 4", "owner": "agent1", "blockedBy": ["task-001"]}],
            },
            "taskSummary": {
                "pending": 1,
                "in_progress": 1,
                "completed": 1,
                "blocked": 1,
                "total": 4,
            },
        }
        result = renderer._build_team_board(data)
        assert result is not None

    def test_build_team_board_with_cost(self):
        """Test building a team board with cost information."""
        renderer = BoardRenderer()
        data = {
            "team": {
                "name": "test-team",
                "leaderName": "leader1",
                "createdAt": "2024-01-01T10:00:00Z",
                "budgetCents": 10000,
            },
            "members": [],
            "tasks": {},
            "taskSummary": {},
            "cost": {"totalCostCents": 5000},
        }
        result = renderer._build_team_board(data)
        assert result is not None

    def test_build_task_kanban_empty(self):
        """Test building kanban with no tasks."""
        renderer = BoardRenderer()
        result = renderer._build_task_kanban({}, {})
        assert result is not None

    def test_build_task_kanban_with_tasks(self):
        """Test building kanban with tasks in each column."""
        renderer = BoardRenderer()
        tasks = {
            "pending": [{"id": "t1", "subject": "Pending task"}],
            "in_progress": [{"id": "t2", "subject": "In progress", "lockedBy": "agent1"}],
            "completed": [{"id": "t3", "subject": "Done"}],
            "blocked": [{"id": "t4", "subject": "Blocked", "blockedBy": ["t1"]}],
        }
        summary = {"pending": 1, "in_progress": 1, "completed": 1, "blocked": 1, "total": 4}
        result = renderer._build_task_kanban(tasks, summary)
        assert result is not None

    def test_render_team_board_outputs_to_console(self):
        """Test that render_team_board outputs to console."""
        console = Console(file=StringIO(), force_terminal=True, width=100)
        renderer = BoardRenderer(console=console)
        data = {
            "team": {
                "name": "test-team",
                "leaderName": "leader1",
                "createdAt": "2024-01-01T10:00:00Z",
            },
            "members": [],
            "tasks": {},
            "taskSummary": {"total": 0},
        }
        renderer.render_team_board(data)
        output = console.file.getvalue()
        assert "test-team" in output