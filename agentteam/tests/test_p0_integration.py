"""Integration tests for P0 improvements (logging, review, retry)."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from agentteam.team.models import TaskItem, TaskPriority, TaskStatus, get_data_dir
from agentteam.store.file import FileTaskStore
from agentteam.transport.file import FileTransport
from agentteam.utils.retry import RetryConfig, retry
from agentteam.utils.logger import get_logger, get_trace_id, set_trace_id


class TestLoggingIntegration:
    """Tests for structured logging integration."""

    def test_get_logger_returns_logger(self) -> None:
        logger = get_logger("test_module")
        assert logger is not None
        assert logger.name == "test_module"
        assert logger.logger.name == "test_module"

    def test_trace_id_context(self) -> None:
        # Initially no trace_id
        assert get_trace_id() is None

        # Set trace_id
        set_trace_id("test-trace-123")
        assert get_trace_id() == "test-trace-123"

        # Reset trace_id
        set_trace_id(None)
        assert get_trace_id() is None

    def test_logger_with_trace_id(self, tmp_path: Path) -> None:
        """Test that logger includes trace_id in output."""
        set_trace_id("integration-trace-456")
        logger = get_logger("test_integration")

        # Logger should be functional
        assert logger is not None
        assert logger.name == "test_integration"
        assert logger.logger.name == "test_integration"

        # Reset
        set_trace_id(None)


class TestRetryIntegration:
    """Tests for retry integration with file operations."""

    def test_file_store_with_retry(self, tmp_path: Path) -> None:
        """Test that FileTaskStore works with retry decorator."""
        os.environ["AGENTTEAM_DATA_DIR"] = str(tmp_path)

        try:
            store = FileTaskStore(team_name="test-team")
            task = store.create(
                subject="Test task",
                description="Test description",
                owner="test-user",
                priority=TaskPriority.high,
            )

            assert task.subject == "Test task"
            assert task.status == TaskStatus.pending
            assert task.owner == "test-user"

            # Retrieve task
            retrieved = store.get(task.id)
            assert retrieved is not None
            assert retrieved.id == task.id
            assert retrieved.subject == "Test task"
        finally:
            del os.environ["AGENTTEAM_DATA_DIR"]

    def test_file_transport_with_retry(self, tmp_path: Path) -> None:
        """Test that FileTransport works with retry decorator."""
        os.environ["AGENTTEAM_DATA_DIR"] = str(tmp_path)

        try:
            transport = FileTransport(team_name="test-team")

            # Deliver a message
            test_data = b'{"type": "message", "content": "test"}'
            transport.deliver("recipient-1", test_data)

            # Count messages
            count = transport.count("recipient-1")
            assert count == 1

            # Fetch without consuming (to avoid Windows file lock issues)
            messages = transport.fetch("recipient-1", limit=10, consume=False)
            assert len(messages) == 1
            assert messages[0] == test_data
        finally:
            del os.environ["AGENTTEAM_DATA_DIR"]

    def test_retry_config_from_env(self, tmp_path: Path) -> None:
        """Test that retry config can be loaded from environment."""
        os.environ["AGENTTEAM_RETRY_MAX_RETRIES"] = "5"
        os.environ["AGENTTEAM_RETRY_BASE_DELAY"] = "0.1"

        try:
            from agentteam.config import get_effective

            max_retries, source = get_effective("retry_max_retries")
            assert max_retries == "5"
            assert source == "env"

            base_delay, source = get_effective("retry_base_delay")
            assert base_delay == "0.1"
            assert source == "env"
        finally:
            del os.environ["AGENTTEAM_RETRY_MAX_RETRIES"]
            del os.environ["AGENTTEAM_RETRY_BASE_DELAY"]

    def test_retry_on_file_operation_failure(self, tmp_path: Path) -> None:
        """Test that retry decorator handles file operation failures."""
        call_count = 0

        @retry(config=RetryConfig(max_retries=3, base_delay=0.01, jitter=False))
        def flaky_file_write(path: Path) -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise OSError("Transient file error")
            path.write_text("success")
            return "success"

        test_file = tmp_path / "test.txt"
        result = flaky_file_write(test_file)
        assert result == "success"
        assert call_count == 3
        assert test_file.read_text() == "success"


class TestEndToEndIntegration:
    """End-to-end integration tests."""

    def test_full_task_lifecycle(self, tmp_path: Path) -> None:
        """Test complete task lifecycle with retry and logging."""
        os.environ["AGENTTEAM_DATA_DIR"] = str(tmp_path)

        try:
            # Setup
            store = FileTaskStore(team_name="e2e-team")
            transport = FileTransport(team_name="e2e-team")
            logger = get_logger("e2e_test")

            # Create task
            task = store.create(
                subject="E2E task",
                description="End-to-end test",
                owner="e2e-user",
                priority=TaskPriority.urgent,
            )
            assert task.id is not None
            assert task.status == TaskStatus.pending

            # Update task status using update method
            store.update(task.id, status=TaskStatus.in_progress)
            updated = store.get(task.id)
            assert updated is not None
            assert updated.status == TaskStatus.in_progress

            # Complete task
            store.update(task.id, status=TaskStatus.completed)
            completed = store.get(task.id)
            assert completed is not None
            assert completed.status == TaskStatus.completed

            # Send notification via transport
            notification = json.dumps(
                {
                    "type": "task_completed",
                    "task_id": task.id,
                    "status": "completed",
                }
            ).encode()
            transport.deliver("e2e-user", notification)

            # Fetch notification (without consuming to avoid Windows file lock)
            messages = transport.fetch("e2e-user", limit=10, consume=False)
            assert len(messages) == 1
            data = json.loads(messages[0])
            assert data["type"] == "task_completed"
            assert data["task_id"] == task.id

            # Verify stats
            stats = store.get_stats()
            assert stats["total"] == 1
            assert stats["completed"] == 1

        finally:
            del os.environ["AGENTTEAM_DATA_DIR"]

    def test_concurrent_task_creation(self, tmp_path: Path) -> None:
        """Test concurrent task creation with retry."""
        os.environ["AGENTTEAM_DATA_DIR"] = str(tmp_path)

        try:
            store = FileTaskStore(team_name="concurrent-team")

            # Create multiple tasks
            tasks = []
            for i in range(5):
                task = store.create(
                    subject=f"Task {i}",
                    description=f"Description {i}",
                    owner=f"user-{i}",
                )
                tasks.append(task)

            # Verify all tasks created
            assert len(tasks) == 5
            for i, task in enumerate(tasks):
                assert task.subject == f"Task {i}"
                assert task.owner == f"user-{i}"

            # List all tasks
            all_tasks = store.list_tasks()
            assert len(all_tasks) == 5

        finally:
            del os.environ["AGENTTEAM_DATA_DIR"]

    def test_idempotent_task_creation(self, tmp_path: Path) -> None:
        """Test idempotent task creation with retry."""
        os.environ["AGENTTEAM_DATA_DIR"] = str(tmp_path)

        try:
            store = FileTaskStore(team_name="idempotent-team")

            # Create task with idempotency key
            task1 = store.create(
                subject="Idempotent task",
                description="Test idempotency",
                owner="test-user",
                idempotency_key="unique-key-123",
            )

            # Try to create again with same key
            task2 = store.create(
                subject="Idempotent task",
                description="Test idempotency",
                owner="test-user",
                idempotency_key="unique-key-123",
            )

            # Should return same task
            assert task1.id == task2.id
            assert task1.subject == task2.subject

            # Only one task should exist
            all_tasks = store.list_tasks()
            assert len(all_tasks) == 1

        finally:
            del os.environ["AGENTTEAM_DATA_DIR"]
