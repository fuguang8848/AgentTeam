"""Database migration system."""

from __future__ import annotations

import logging
from typing import Any, List, Tuple, Optional
import sqlite3

logger = logging.getLogger(__name__)


class Migration:
    """Single migration definition."""

    def __init__(self, version: int, description: str, up_func):
        self.version = version
        self.description = description
        self.up_func = up_func

    def up(self, db: sqlite3.Connection) -> None:
        """Execute migration."""
        self.up_func(db)


# Migration helper functions
def table_exists(db: sqlite3.Connection, table_name: str) -> bool:
    """Check if a table exists."""
    cursor = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
    )
    return cursor.fetchone() is not None


def get_column_names(db: sqlite3.Connection, table_name: str) -> List[str]:
    """Get all column names of a table."""
    cursor = db.execute(f"PRAGMA table_info('{table_name}')")
    return [row[1] for row in cursor.fetchall()]


def add_column_if_not_exists(
    db: sqlite3.Connection, table: str, column: str, definition: str
) -> bool:
    """Add column if it doesn't exist."""
    cols = get_column_names(db, table)
    if column not in cols:
        try:
            db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            return True
        except Exception as e:
            logger.error(f"Failed to add column {column} to {table}: {e}")
            return False
    return False


# Define migrations
MIGRATIONS: List[Migration] = [
    # Version 1: Initial schema (already created by manager._initialize_schema)
    Migration(
        version=1,
        description="Initial database schema",
        up_func=lambda db: None,  # Schema created by manager
    ),
    # Version 2: Add indexes for performance
    Migration(
        version=2,
        description="Add performance indexes",
        up_func=lambda db: db.executescript("""
            CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at);
            CREATE INDEX IF NOT EXISTS idx_sessions_created ON sessions(created_at);
            CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);
            CREATE INDEX IF NOT EXISTS idx_agents_last_seen ON agents(last_seen_at);
        """),
    ),
    # Version 3: Add message_ttl column to messages table
    Migration(
        version=3,
        description="Add message_ttl column to messages table",
        up_func=lambda db: add_column_if_not_exists(db, "messages", "message_ttl", "INTEGER"),
    ),
    # Version 4: Add token_limit column to usage_stats
    Migration(
        version=4,
        description="Add token_limit column to usage_stats",
        up_func=lambda db: add_column_if_not_exists(db, "usage_stats", "token_limit", "INTEGER"),
    ),
    # Version 5: Add session_type column to sessions
    Migration(
        version=5,
        description="Add session_type column to sessions",
        up_func=lambda db: add_column_if_not_exists(db, "sessions", "session_type", "TEXT"),
    ),
]


def get_current_version(db: sqlite3.Connection) -> int:
    """Get current database version."""
    try:
        cursor = db.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else 0
    except sqlite3.OperationalError:
        # Table doesn't exist yet
        return 0


def set_version(db: sqlite3.Connection, version: int) -> None:
    """Set database version."""
    # Create schema_version table if it doesn't exist
    db.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            description TEXT
        )
    """)

    # Insert or update version
    db.execute(
        "INSERT OR REPLACE INTO schema_version (version, description) VALUES (?, ?)",
        (version, f"Migration to version {version}"),
    )
    db.commit()


def run_migrations(db: sqlite3.Connection) -> None:
    """Run all pending migrations."""
    if not db:
        return

    current_version = get_current_version(db)

    # Sort migrations by version
    sorted_migrations = sorted(MIGRATIONS, key=lambda m: m.version)

    applied = 0
    for migration in sorted_migrations:
        if migration.version > current_version:
            logger.info(f"Applying migration {migration.version}: {migration.description}")
            try:
                db.execute("BEGIN")
                migration.up(db)
                set_version(db, migration.version)
                db.commit()
                applied += 1
                logger.info(f"Migration {migration.version} applied successfully")
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to apply migration {migration.version}: {e}")
                raise

    if applied > 0:
        logger.info(
            f"Applied {applied} migration(s), current version: {sorted_migrations[-1].version}"
        )
    else:
        logger.info(f"Database is up to date at version {current_version}")


def rollback_migration(db: sqlite3.Connection, target_version: int) -> bool:
    """Rollback to specific version (basic implementation).

    Note: Full rollback requires down migrations which we don't implement yet.
    """
    logger.warning("Rollback not fully implemented - requires down migrations")
    return False
