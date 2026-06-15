"""Integration tests: drift detection triggers on task completion."""

from __future__ import annotations

import pytest

from agentteam.store.file import FileTaskStore
from agentteam.team.models import TaskPriority, TaskStatus


@pytest.fixture()
def store(tmp_path, monkeypatch):
    """Create a FileTaskStore with a temp data directory."""
    monkeypatch.setenv("AGENTTEAM_DATA_DIR", str(tmp_path))
    return FileTaskStore(team_name="test-team")


class TestDriftOnCompletion:
    """When a task transitions to completed, drift detection should run
    automatically if output metadata is present."""

    def test_no_output_no_alert(self, store):
        """Task completed without output metadata → no drift alert."""
        task = store.create(
            subject="Write tests",
            description="Add unit tests for the drift module",
            owner="agent-1",
        )
        completed = store.update(task.id, status=TaskStatus.completed)
        assert completed is not None
        assert completed.status == TaskStatus.completed
        assert completed.drift_alerts == []

    def test_output_in_metadata_triggers_detection(self, store):
        """Task completed with output metadata → drift detection runs."""
        task = store.create(
            subject="Build REST API",
            description="Implement user authentication endpoints",
            owner="agent-1",
        )
        # Simulate agent storing its output in metadata
        completed = store.update(
            task.id,
            status=TaskStatus.completed,
            metadata={"output": "Built REST API with user authentication endpoints"},
        )
        assert completed is not None
        # Aligned output → no alert
        assert completed.drift_alerts == []

    def test_drifted_output_creates_alert(self, store):
        """Task completed with drifted output → alert is created."""
        task = store.create(
            subject="Build REST API",
            description="Implement user authentication endpoints",
            owner="agent-1",
        )
        completed = store.update(
            task.id,
            status=TaskStatus.completed,
            metadata={"output": "Wrote documentation for the kitchen recipe system"},
        )
        assert completed is not None
        assert len(completed.drift_alerts) == 1
        alert = completed.drift_alerts[0]
        assert alert.task_id == task.id
        assert alert.severity in ("medium", "high", "critical")

    def test_result_key_in_metadata(self, store):
        """Support 'result' as an alternative metadata key for output."""
        task = store.create(
            subject="Fix login bug",
            description="Login returns 500 error on invalid credentials",
            owner="agent-2",
        )
        completed = store.update(
            task.id,
            status=TaskStatus.completed,
            metadata={"result": "Completely unrelated output about baking cookies"},
        )
        assert len(completed.drift_alerts) == 1

    def test_completion_text_key_in_metadata(self, store):
        """Support 'completion_text' as another alternative key."""
        task = store.create(
            subject="Design database schema",
            description="Create tables for users and orders",
            owner="agent-3",
        )
        completed = store.update(
            task.id,
            status=TaskStatus.completed,
            metadata={"completion_text": "Designed database with users and orders tables"},
        )
        # Partial alignment → low severity alert (not fully aligned)
        assert len(completed.drift_alerts) == 1
        assert completed.drift_alerts[0].severity == "low"

    def test_output_priority_over_result(self, store):
        """When both 'output' and 'result' exist, 'output' takes priority."""
        task = store.create(
            subject="Build API",
            description="REST endpoints for auth",
            owner="agent-1",
        )
        completed = store.update(
            task.id,
            status=TaskStatus.completed,
            metadata={
                "output": "Built REST API with authentication",  # aligned
                "result": "Wrote about kitchen recipes",  # drifted
            },
        )
        # 'output' is checked first — partial match → low alert (not critical)
        assert len(completed.drift_alerts) == 1
        assert completed.drift_alerts[0].severity in ("low", "medium")

    def test_no_double_alert_on_reupdate(self, store):
        """Re-updating an already completed task should not create duplicate alerts."""
        task = store.create(
            subject="Write tests",
            description="Add unit tests",
            owner="agent-1",
        )
        completed = store.update(
            task.id,
            status=TaskStatus.completed,
            metadata={"output": "Wrote comprehensive unit tests for all modules"},
        )
        # First completion: drift detection runs once
        alert_count = len(completed.drift_alerts)
        assert alert_count <= 1

        # Update again (e.g. add metadata) — should NOT re-trigger drift
        updated = store.update(
            task.id,
            metadata={"duration_seconds": 120.5},
        )
        assert updated is not None
        # Same number of alerts — no duplicates
        assert len(updated.drift_alerts) == alert_count

    def test_alert_persists_on_reload(self, store, tmp_path):
        """Drift alerts saved to disk survive reload."""
        task = store.create(
            subject="Build API",
            description="User authentication",
            owner="agent-1",
        )
        store.update(
            task.id,
            status=TaskStatus.completed,
            metadata={"output": "Wrote documentation for the kitchen recipe system"},
        )

        # Reload from disk
        store2 = FileTaskStore(team_name="test-team")
        reloaded = store2.get(task.id)
        assert reloaded is not None
        assert len(reloaded.drift_alerts) == 1
        assert reloaded.drift_alerts[0].task_id == task.id

    def test_in_progress_no_drift(self, store):
        """Moving to in_progress should not trigger drift detection."""
        task = store.create(
            subject="Build API",
            description="User auth",
            owner="agent-1",
        )
        in_progress = store.update(
            task.id,
            status=TaskStatus.in_progress,
            caller="agent-1",
            metadata={"output": "Working on it..."},
        )
        assert in_progress is not None
        assert in_progress.status == TaskStatus.in_progress
        assert in_progress.drift_alerts == []

    def test_pending_to_completed_triggers(self, store):
        """Direct transition from pending → completed triggers drift detection."""
        task = store.create(
            subject="Implement search",
            description="Elasticsearch full-text search",
            owner="agent-1",
        )
        completed = store.update(
            task.id,
            status=TaskStatus.completed,
            metadata={"output": "Completely unrelated topic about gardening"},
        )
        assert len(completed.drift_alerts) == 1
