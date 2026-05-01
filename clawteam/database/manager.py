"""Database manager with SQLite + memory fallback."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import json
import logging

from . import migrations
from .types import (
    DatabaseTask,
    DatabaseSession,
    DatabaseAgent,
    DatabaseMessage,
    DatabaseAlert,
    DatabaseUsage,
)
from .repositories.task import TaskRepository
from .repositories.session import SessionRepository
from .repositories.agent import AgentRepository
from .repositories.message import MessageRepository
from .repositories.alert import AlertRepository
from .repositories.usage import UsageRepository

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database manager with SQLite + memory fallback."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize database manager.
        
        Args:
            db_path: SQLite database file path. If None, uses default path
                     ~/.clawteam/clawteam.db
        """
        self.db: Optional[sqlite3.Connection] = None
        self.using_sqlite: bool = False
        self.db_path: str = db_path or self._default_db_path()
        
        # Repositories
        self.task_repo: TaskRepository
        self.session_repo: SessionRepository
        self.agent_repo: AgentRepository
        self.message_repo: MessageRepository
        self.alert_repo: AlertRepository
        self.usage_repo: UsageRepository
        
        # Initialize
        self._initialize()
    
    def _default_db_path(self) -> str:
        """Get default database path."""
        env_path = os.environ.get("CLAWTEAM_DB_PATH")
        if env_path:
            return env_path
        
        # Default: ~/.clawteam/clawteam.db
        data_dir = os.path.join(Path.home(), ".clawteam")
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, "clawteam.db")
    
    def _initialize(self) -> None:
        """Initialize database connection and schema."""
        try:
            # Create directory if needed
            db_dir = os.path.dirname(self.db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
            
            # Connect to SQLite
            self.db = sqlite3.connect(self.db_path, check_same_thread=False)
            self.db.row_factory = sqlite3.Row
            self.using_sqlite = True
            
            # Set pragmas
            self.db.execute("PRAGMA journal_mode = WAL")
            self.db.execute("PRAGMA foreign_keys = ON")
            self.db.execute("PRAGMA busy_timeout = 5000")
            
            # Initialize schema
            self._initialize_schema()
            # Run migrations
            migrations.run_migrations(self.db)
            
            logger.info(f"SQLite database initialized at {self.db_path}")
            
        except Exception as e:
            logger.warning(f"SQLite unavailable, using in-memory fallback: {e}")
            self.using_sqlite = False
            self.db = None
        
        # Initialize repositories
        self.task_repo = TaskRepository(self.db, self.using_sqlite)
        self.session_repo = SessionRepository(self.db, self.using_sqlite)
        self.agent_repo = AgentRepository(self.db, self.using_sqlite)
        self.message_repo = MessageRepository(self.db, self.using_sqlite)
        self.alert_repo = AlertRepository(self.db, self.using_sqlite)
        self.usage_repo = UsageRepository(self.db, self.using_sqlite)
    
    def _initialize_schema(self) -> None:
        """Initialize database schema (create tables)."""
        if not self.db:
            return
        
        # Create tables
        schema = """
        -- Tasks table
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            priority TEXT NOT NULL DEFAULT 'medium',
            tags TEXT,
            parent_task_id TEXT,
            team_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            completed_at TEXT,
            FOREIGN KEY(parent_task_id) REFERENCES tasks(id) ON DELETE SET NULL
        );
        
        -- Sessions table
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            task_id TEXT,
            working_directory TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'running',
            provider_id TEXT,
            team_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            terminated_at TEXT,
            FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE SET NULL
        );
        
        -- Agents table
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            team_id TEXT,
            role TEXT,
            status TEXT NOT NULL DEFAULT 'idle',
            current_task_id TEXT,
            last_seen_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            result_data TEXT,
            FOREIGN KEY(current_task_id) REFERENCES tasks(id) ON DELETE SET NULL
        );
        
        -- Messages table (with TTL support)
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            sender TEXT NOT NULL,
            recipient TEXT NOT NULL,
            content TEXT NOT NULL,
            team_id TEXT,
            task_id TEXT,
            session_id TEXT,
            created_at TEXT NOT NULL,
            expires_at TEXT,
            delivered INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE SET NULL,
            FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE SET NULL
        );
        
        -- Alerts table
        CREATE TABLE IF NOT EXISTS alerts (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            level TEXT NOT NULL DEFAULT 'info',
            team_id TEXT,
            task_id TEXT,
            session_id TEXT,
            created_at TEXT NOT NULL,
            acknowledged_at TEXT,
            resolved_at TEXT,
            FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE SET NULL,
            FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE SET NULL
        );
        
        -- Usage statistics table
        CREATE TABLE IF NOT EXISTS usage_stats (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            team_id TEXT,
            task_id TEXT,
            provider_id TEXT NOT NULL,
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            total_tokens INTEGER NOT NULL DEFAULT 0,
            estimated_cost REAL NOT NULL DEFAULT 0.0,
            timestamp TEXT NOT NULL,
            FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE,
            FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE SET NULL
        );
        
        -- Indexes for performance
        CREATE INDEX IF NOT EXISTS idx_tasks_team_status ON tasks(team_id, status);
        CREATE INDEX IF NOT EXISTS idx_tasks_parent ON tasks(parent_task_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_team_status ON sessions(team_id, status);
        CREATE INDEX IF NOT EXISTS idx_messages_expires ON messages(expires_at);
        CREATE INDEX IF NOT EXISTS idx_messages_recipient ON messages(recipient, delivered);
        CREATE INDEX IF NOT EXISTS idx_alerts_team_status ON alerts(team_id, level, resolved_at);
        CREATE INDEX IF NOT EXISTS idx_usage_session ON usage_stats(session_id);
        """
        
        self.db.executescript(schema)
        self.db.commit()
    
    # ----- Task operations -----
    
    def create_task(self, task: DatabaseTask) -> DatabaseTask:
        """Create a new task."""
        return self.task_repo.create(task)
    
    def get_task(self, task_id: str) -> Optional[DatabaseTask]:
        """Get a task by ID."""
        return self.task_repo.get(task_id)
    
    def update_task(self, task_id: str, updates: Dict[str, Any]) -> Optional[DatabaseTask]:
        """Update a task."""
        return self.task_repo.update(task_id, updates)
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        return self.task_repo.delete(task_id)
    
    def list_tasks(self, team_id: Optional[str] = None, 
                  status: Optional[str] = None,
                  limit: int = 100) -> List[DatabaseTask]:
        """List tasks with optional filters."""
        return self.task_repo.list(team_id=team_id, status=status, limit=limit)
    
    def get_tasks(self, team_id: Optional[str] = None,
                  status: Optional[str] = None,
                  limit: int = 100) -> List[DatabaseTask]:
        """Alias for list_tasks (backwards compatibility)."""
        return self.list_tasks(team_id=team_id, status=status, limit=limit)
    
    def count_tasks(self, team_id: Optional[str] = None) -> int:
        """Count tasks with optional team filter."""
        return self.task_repo.count(team_id=team_id)
    
    def close(self) -> None:
        """Close database connection."""
        if self.db:
            try:
                self.db.close()
            except Exception:
                pass
            self.db = None
    
    # ----- Session operations -----
    
    def create_session(self, session: DatabaseSession) -> DatabaseSession:
        """Create a new session."""
        return self.session_repo.create(session)
    
    def get_session(self, session_id: str) -> Optional[DatabaseSession]:
        """Get a session by ID."""
        return self.session_repo.get(session_id)
    
    def update_session(self, session_id: str, updates: Dict[str, Any]) -> Optional[DatabaseSession]:
        """Update a session."""
        return self.session_repo.update(session_id, updates)
    
    def terminate_session(self, session_id: str) -> Optional[DatabaseSession]:
        """Terminate a session."""
        return self.session_repo.update(session_id, {"status": "terminated"})
    
    # ----- Agent operations -----
    
    def create_agent(self, agent: DatabaseAgent) -> DatabaseAgent:
        """Create a new agent."""
        return self.agent_repo.create(agent)
    
    def get_agent(self, agent_id: str) -> Optional[DatabaseAgent]:
        """Get an agent by ID."""
        return self.agent_repo.get(agent_id)
    
    def update_agent(self, agent_id: str, updates: Dict[str, Any]) -> Optional[DatabaseAgent]:
        """Update an agent."""
        return self.agent_repo.update(agent_id, updates)
    
    def update_last_seen(self, agent_id: str) -> bool:
        """Update agent's last_seen timestamp."""
        return self.agent_repo.update_last_seen(agent_id)
