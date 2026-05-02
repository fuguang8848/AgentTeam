"""
Database migration module for ClawTeam

Provides database schema version management and migration support.
"""

import json
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from clawteam.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Migration:
    """A single database migration"""

    version: int
    name: str
    description: str = ""
    up_sql: str = ""
    down_sql: str = ""
    applied_at: Optional[datetime] = None

    @property
    def id(self) -> str:
        return f"V{self.version:04d}_{self.name}"


@dataclass
class MigrationResult:
    """Result of a migration operation"""

    success: bool
    migration: Migration
    message: str = ""
    error: Optional[str] = None


class DatabaseConfig:
    """Database configuration"""

    def __init__(
        self,
        db_path: str = "clawteam.db",
        migrations_dir: str = "migrations",
        auto_migrate: bool = True,
    ):
        self.db_path = db_path
        self.migrations_dir = migrations_dir
        self.auto_migrate = auto_migrate

    def get_connection_string(self) -> str:
        """Get database connection string"""
        return f"sqlite:///{self.db_path}"


class MigrationManager:
    """
    Database migration manager

    Manages database schema versions and applies migrations.

    Example:
        manager = MigrationManager(config=DatabaseConfig())

        # Register migrations
        manager.add_migration(Migration(
            version=1,
            name="initial_schema",
            description="Create initial tables",
            up_sql="CREATE TABLE users (id INTEGER PRIMARY KEY);",
            down_sql="DROP TABLE users;",
        ))

        # Apply pending migrations
        results = manager.migrate()

        # Get current version
        current = manager.get_current_version()
    """

    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self._migrations: list[Migration] = []
        self._version_lock = threading.Lock()

        # Ensure migrations directory exists
        Path(self.config.migrations_dir).mkdir(parents=True, exist_ok=True)

    def add_migration(self, migration: Migration) -> None:
        """Register a migration"""
        self._migrations.append(migration)
        self._migrations.sort(key=lambda m: m.version)
        logger.info(f"Registered migration: {migration.id}")

    def get_migrations(self) -> list[Migration]:
        """Get all registered migrations"""
        return list(self._migrations)

    def get_pending_migrations(self, current_version: int) -> list[Migration]:
        """Get migrations that need to be applied"""
        return [m for m in self._migrations if m.version > current_version]

    def get_applied_migrations(self, current_version: int) -> list[Migration]:
        """Get migrations that have been applied"""
        return [m for m in self._migrations if m.version <= current_version]

    def get_current_version(self) -> int:
        """Get the current database schema version"""
        db_path = self.config.db_path

        if not os.path.exists(db_path):
            return 0

        try:
            import sqlite3

            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute(
                    "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
                )
                row = cursor.fetchone()
                return row[0] if row else 0
        except Exception as e:
            logger.error(f"Error getting current version: {e}")
            return 0

    def _ensure_version_table(self) -> None:
        """Ensure the schema_version table exists"""
        db_path = self.config.db_path

        import sqlite3

        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TEXT NOT NULL
                )
            """)

    def migrate(self, target_version: Optional[int] = None) -> list[MigrationResult]:
        """
        Apply pending migrations

        Args:
            target_version: Target version to migrate to (None = latest)

        Returns:
            List of migration results
        """
        self._ensure_version_table()
        current_version = self.get_current_version()

        if target_version is None:
            target_version = self._migrations[-1].version if self._migrations else current_version

        pending = self.get_pending_migrations(current_version)
        results = []

        for migration in pending:
            if migration.version > target_version:
                break

            result = self._apply_migration(migration)
            results.append(result)

            if not result.success:
                logger.error(f"Migration {migration.id} failed: {result.error}")
                break

        return results

    def _apply_migration(self, migration: Migration) -> MigrationResult:
        """Apply a single migration"""
        db_path = self.config.db_path

        try:
            import sqlite3

            with sqlite3.connect(db_path) as conn:
                # Execute migration SQL
                if migration.up_sql:
                    conn.executescript(migration.up_sql)

                # Record in schema_version
                conn.execute(
                    "INSERT INTO schema_version (version, name, applied_at) VALUES (?, ?, ?)",
                    (migration.version, migration.name, datetime.now().isoformat()),
                )

                conn.commit()

            migration.applied_at = datetime.now()
            logger.info(f"Applied migration: {migration.id}")

            return MigrationResult(
                success=True,
                migration=migration,
                message=f"Successfully applied {migration.id}",
            )

        except Exception as e:
            logger.error(f"Failed to apply migration {migration.id}: {e}")
            return MigrationResult(
                success=False,
                migration=migration,
                message=f"Failed to apply {migration.id}",
                error=str(e),
            )

    def rollback(self, version: int) -> MigrationResult:
        """
        Rollback to a specific version

        Args:
            version: Version to rollback to

        Returns:
            MigrationResult
        """
        self._ensure_version_table()
        current_version = self.get_current_version()

        if version >= current_version:
            return MigrationResult(
                success=False,
                migration=Migration(version=0, name=""),
                message="Nothing to rollback",
            )

        # Find the migration to rollback
        migration_to_rollback = None
        for m in reversed(self._migrations):
            if m.version > version and m.version <= current_version:
                migration_to_rollback = m
                break

        if not migration_to_rollback:
            return MigrationResult(
                success=False,
                migration=Migration(version=0, name=""),
                message="Migration to rollback not found",
            )

        db_path = self.config.db_path

        try:
            import sqlite3

            with sqlite3.connect(db_path) as conn:
                # Execute rollback SQL
                if migration_to_rollback.down_sql:
                    conn.executescript(migration_to_rollback.down_sql)

                # Remove from schema_version
                conn.execute(
                    "DELETE FROM schema_version WHERE version = ?", (migration_to_rollback.version,)
                )

                conn.commit()

            logger.info(f"Rolled back migration: {migration_to_rollback.id}")

            return MigrationResult(
                success=True,
                migration=migration_to_rollback,
                message=f"Successfully rolled back {migration_to_rollback.id}",
            )

        except Exception as e:
            logger.error(f"Failed to rollback {migration_to_rollback.id}: {e}")
            return MigrationResult(
                success=False,
                migration=migration_to_rollback,
                message=f"Failed to rollback {migration_to_rollback.id}",
                error=str(e),
            )

    def get_migration_status(self) -> dict[str, Any]:
        """Get detailed migration status"""
        current_version = self.get_current_version()

        return {
            "current_version": current_version,
            "total_migrations": len(self._migrations),
            "applied_migrations": len(self.get_applied_migrations(current_version)),
            "pending_migrations": len(self.get_pending_migrations(current_version)),
            "migrations": [
                {
                    "version": m.version,
                    "name": m.name,
                    "description": m.description,
                    "applied": m.version <= current_version,
                    "applied_at": m.applied_at.isoformat() if m.applied_at else None,
                }
                for m in self._migrations
            ],
        }

    def create_migration_file(self, version: int, name: str, up_sql: str, down_sql: str) -> str:
        """
        Create a migration file

        Returns:
            Path to the created migration file
        """
        migration = Migration(
            version=version,
            name=name,
            description=f"Migration {version}: {name}",
            up_sql=up_sql,
            down_sql=down_sql,
        )

        filename = f"{migration.id}.py"
        filepath = os.path.join(self.config.migrations_dir, filename)

        content = f'''\"\"\"Migration: {migration.name}\"\"\"\nfrom clawteam.database import Migration\n\nmigration = Migration(\n    version={version},\n    name="{name}",\n    description="{migration.description}",\n    up_sql="""{up_sql}""",\n    down_sql="""{down_sql}""",\n)\n'''

        with open(filepath, "w") as f:
            f.write(content)

        logger.info(f"Created migration file: {filepath}")
        return filepath


def get_default_migrations() -> list[Migration]:
    """Get the default set of migrations for ClawTeam"""
    migrations = []

    # V1: Initial schema
    migrations.append(
        Migration(
            version=1,
            name="initial_schema",
            description="Create initial tables",
            up_sql="""
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                role TEXT,
                status TEXT DEFAULT 'idle',
                created_at TEXT NOT NULL,
                FOREIGN KEY (team_id) REFERENCES teams(id)
            );
            
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'pending',
                priority TEXT DEFAULT 'medium',
                assignee_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (team_id) REFERENCES teams(id),
                FOREIGN KEY (assignee_id) REFERENCES agents(id)
            );
            
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                team_id INTEGER NOT NULL,
                agent_id INTEGER,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                ended_at TEXT,
                FOREIGN KEY (team_id) REFERENCES teams(id),
                FOREIGN KEY (agent_id) REFERENCES agents(id)
            );
        """,
            down_sql="""
            DROP TABLE IF EXISTS sessions;
            DROP TABLE IF EXISTS tasks;
            DROP TABLE IF EXISTS agents;
            DROP TABLE IF EXISTS teams;
        """,
        )
    )

    # V2: Add indexes
    migrations.append(
        Migration(
            version=2,
            name="add_indexes",
            description="Add performance indexes",
            up_sql="""
            CREATE INDEX IF NOT EXISTS idx_agents_team ON agents(team_id);
            CREATE INDEX IF NOT EXISTS idx_tasks_team ON tasks(team_id);
            CREATE INDEX IF NOT EXISTS idx_tasks_assignee ON tasks(assignee_id);
            CREATE INDEX IF NOT EXISTS idx_sessions_team ON sessions(team_id);
            CREATE INDEX IF NOT EXISTS idx_sessions_agent ON sessions(agent_id);
        """,
            down_sql="""
            DROP INDEX IF EXISTS idx_agents_team;
            DROP INDEX IF EXISTS idx_tasks_team;
            DROP INDEX IF EXISTS idx_tasks_assignee;
            DROP INDEX IF EXISTS idx_sessions_team;
            DROP INDEX IF EXISTS idx_sessions_agent;
        """,
        )
    )

    # V3: Add templates
    migrations.append(
        Migration(
            version=3,
            name="add_templates",
            description="Add team templates",
            up_sql="""
            CREATE TABLE IF NOT EXISTS team_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                config TEXT,
                created_at TEXT NOT NULL
            );
        """,
            down_sql="""
            DROP TABLE IF EXISTS team_templates;
        """,
        )
    )

    return migrations


__all__ = [
    "Migration",
    "MigrationResult",
    "MigrationManager",
    "DatabaseConfig",
    "get_default_migrations",
]
