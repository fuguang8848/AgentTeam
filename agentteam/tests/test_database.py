"""Test database layer."""
import os
import tempfile
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from agentteam.database.manager import DatabaseManager
from agentteam.database.types import (
    DatabaseTask,
    DatabaseSession,
    DatabaseAgent,
    DatabaseMessage,
    DatabaseAlert,
    DatabaseUsage,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    db = DatabaseManager(db_path)
    yield db
    
    # Cleanup
    db.close()
    try:
        os.unlink(db_path)
    except:
        pass


class TestDatabaseManager:
    """Test DatabaseManager."""
    
    def test_init_default_path(self):
        """Test initialization with default path."""
        db = DatabaseManager()
        assert db.db_path.endswith("agentteam.db")
        assert ".agentteam" in db.db_path
        db.close()
    
    def test_init_custom_path(self):
        """Test initialization with custom path."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            db = DatabaseManager(db_path)
            assert db.db_path == db_path
            db.close()
        finally:
            try:
                os.unlink(db_path)
            except:
                pass
    
    def test_init_env_var(self, monkeypatch):
        """Test initialization with environment variable."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        try:
            monkeypatch.setenv("AGENTTEAM_DB_PATH", db_path)
            db = DatabaseManager()
            assert db.db_path == db_path
            db.close()
        finally:
            try:
                os.unlink(db_path)
            except:
                pass
    
    def test_memory_fallback(self):
        """Test memory fallback when SQLite fails."""
        # Use an invalid path that will definitely fail on all platforms
        # On Unix: /proc/nonexistent is not writable
        # On Windows: NUL: is a reserved device name
        import sys
        if sys.platform == "win32":
            db_path = "NUL:"
        else:
            db_path = "/proc/nonexistent/test.db"
        
        db = DatabaseManager(db_path)
        
        # Should fall back to memory
        assert db.using_sqlite is False
        assert db.db is None
        db.close()


class TestTaskRepository:
    """Test TaskRepository."""
    
    def test_create_task(self, temp_db):
        """Test creating a task."""
        task = DatabaseTask(
            id="task-123",
            title="Test Task",
            description="Test description",
            status="pending",
            priority="high",
            tags=["test", "database"],
            team_id="team-1",
        )
        
        result = temp_db.create_task(task)
        assert result.id == "task-123"
        assert result.title == "Test Task"
        assert result.status == "pending"
        assert result.team_id == "team-1"
        
        # Verify retrieval
        retrieved = temp_db.get_task("task-123")
        assert retrieved is not None
        assert retrieved.id == "task-123"
        assert retrieved.title == "Test Task"
    
    def test_update_task(self, temp_db):
        """Test updating a task."""
        task = DatabaseTask(
            id="task-456",
            title="Original Title",
            description="Original description",
        )
        temp_db.create_task(task)
        
        # Update task
        updates = {
            "title": "Updated Title",
            "status": "in_progress",
            "completed_at": datetime.now(),
        }
        updated = temp_db.update_task("task-456", updates)
        assert updated is not None
        assert updated.title == "Updated Title"
        assert updated.status == "in_progress"
        assert updated.completed_at is not None
        
        # Verify update persisted
        retrieved = temp_db.get_task("task-456")
        assert retrieved.title == "Updated Title"
    
    def test_delete_task(self, temp_db):
        """Test deleting a task."""
        task = DatabaseTask(id="task-789", title="To be deleted")
        temp_db.create_task(task)
        
        # Verify exists
        assert temp_db.get_task("task-789") is not None
        
        # Delete
        result = temp_db.delete_task("task-789")
        assert result is True
        
        # Verify deleted
        assert temp_db.get_task("task-789") is None
    
    def test_list_tasks(self, temp_db):
        """Test listing tasks with filters."""
        # Create test tasks
        tasks = [
            DatabaseTask(id=f"task-{i}", title=f"Task {i}", team_id="team-1", status="pending")
            for i in range(5)
        ]
        for task in tasks:
            temp_db.create_task(task)
        
        # Create task for different team
        other_task = DatabaseTask(id="other-task", title="Other Task", team_id="team-2")
        temp_db.create_task(other_task)
        
        # List all tasks
        all_tasks = temp_db.get_tasks()
        assert len(all_tasks) >= 6
        
        # List by team
        team_tasks = temp_db.get_tasks(team_id="team-1")
        assert len(team_tasks) >= 5
        
        # List by status
        pending_tasks = temp_db.get_tasks(status="pending")
        assert len(pending_tasks) >= 5
    
    def test_count_tasks(self, temp_db):
        """Test counting tasks."""
        # Create test tasks
        for i in range(3):
            task = DatabaseTask(id=f"task-{i}", title=f"Task {i}", team_id="team-1")
            temp_db.create_task(task)
        
        count = temp_db.count_tasks(team_id="team-1")
        assert count >= 3


class TestSessionRepository:
    """Test SessionRepository."""
    
    def test_create_session(self, temp_db):
        """Test creating a session."""
        session = DatabaseSession(
            id="session-123",
            name="Test Session",
            working_directory="/tmp/test",
            status="running",
            team_id="team-1",
        )
        
        result = temp_db.create_session(session)
        assert result.id == "session-123"
        assert result.name == "Test Session"
        assert result.status == "running"
        
        # Verify retrieval
        retrieved = temp_db.get_session("session-123")
        assert retrieved is not None
        assert retrieved.id == "session-123"
    
    def test_terminate_session(self, temp_db):
        """Test terminating a session."""
        session = DatabaseSession(
            id="session-456",
            name="To be terminated",
            working_directory="/tmp/test",
        )
        temp_db.create_session(session)
        
        # Terminate session
        updates = {"status": "terminated"}
        updated = temp_db.update_session("session-456", updates)
        assert updated is not None
        assert updated.status == "terminated"
        
        # Get active sessions (should not include terminated)
        active_sessions = temp_db.session_repo.get_active_sessions()
        session_ids = [s.id for s in active_sessions]
        assert "session-456" not in session_ids


class TestAgentRepository:
    """Test AgentRepository."""
    
    def test_create_agent(self, temp_db):
        """Test creating an agent."""
        agent = DatabaseAgent(
            id="agent-123",
            name="Test Agent",
            role="backend",
            status="idle",
            team_id="team-1",
        )
        
        result = temp_db.create_agent(agent)
        assert result.id == "agent-123"
        assert result.name == "Test Agent"
        assert result.role == "backend"
        
        # Verify retrieval
        retrieved = temp_db.get_agent("agent-123")
        assert retrieved is not None
        assert retrieved.id == "agent-123"
    
    def test_update_last_seen(self, temp_db):
        """Test updating agent's last_seen timestamp."""
        agent = DatabaseAgent(id="agent-456", name="Test Agent")
        temp_db.create_agent(agent)
        
        # Update last seen
        result = temp_db.agent_repo.update_last_seen("agent-456")
