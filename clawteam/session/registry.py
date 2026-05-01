"""Session Registry for cross-session awareness.

This module provides a central registry for all active sessions, enabling:
- Session registration and lifecycle management
- Session discovery and search
- Session summary retrieval

Inspired by SpectrAI's supervisorPrompt.ts awareness layer.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from clawteam.team.models import get_data_dir


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SessionStatus(str, Enum):
    """Status of a session."""
    active = "active"
    idle = "idle"
    completed = "completed"
    error = "error"
    shutdown = "shutdown"


class SessionInfo(BaseModel):
    """Information about a single session."""
    
    model_config = {"populate_by_name": True}
    
    session_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12], alias="sessionId")
    session_name: str = Field(default="", alias="sessionName")
    status: SessionStatus = SessionStatus.active
    work_dir: str = Field(default="", alias="workDir")
    team_name: str = Field(default="", alias="teamName")
    agent_name: str = Field(default="", alias="agentName")
    agent_id: str = Field(default="", alias="agentId")
    role: str = Field(default="worker")  # leader, worker, etc.
    provider: str = Field(default="")  # claude-code, codex, gemini, etc.
    created_at: str = Field(default_factory=_now_iso, alias="createdAt")
    updated_at: str = Field(default_factory=_now_iso, alias="updatedAt")
    last_heartbeat: str = Field(default_factory=_now_iso, alias="lastHeartbeat")
    
    # Activity tracking
    files_modified: list[str] = Field(default_factory=list, alias="filesModified")
    commands_executed: list[str] = Field(default_factory=list, alias="commandsExecuted")
    tasks_completed: int = Field(default=0, alias="tasksCompleted")
    current_task: str = Field(default="", alias="currentTask")
    
    # Summary
    summary: str = Field(default="")
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionActivity(BaseModel):
    """Activity record for a session."""
    
    model_config = {"populate_by_name": True}
    
    session_id: str = Field(alias="sessionId")
    timestamp: str = Field(default_factory=_now_iso)
    activity_type: str = Field(alias="activityType")  # file_write, command, task_complete, message
    description: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class SessionRegistry:
    """Central registry for all active sessions.
    
    Provides:
    - register/unregister: Session lifecycle management
    - list_sessions: Query sessions by status, team, etc.
    - get_session_summary: Get detailed session info
    - search_sessions: Full-text search across session activities
    """
    
    def __init__(self, data_dir: Path | None = None):
        self._data_dir = data_dir or get_data_dir()
        self._sessions_dir = self._data_dir / "sessions"
        self._sessions_dir.mkdir(parents=True, exist_ok=True)
        self._activities_dir = self._sessions_dir / "activities"
        self._activities_dir.mkdir(parents=True, exist_ok=True)
    
    def _session_path(self, session_id: str) -> Path:
        """Get the path to a session file."""
        return self._sessions_dir / f"{session_id}.json"
    
    def _activities_path(self, session_id: str) -> Path:
        """Get the path to a session's activities directory."""
        return self._activities_dir / session_id
    
    def register(
        self,
        session_name: str = "",
        work_dir: str = "",
        team_name: str = "",
        agent_name: str = "",
        agent_id: str = "",
        role: str = "worker",
        provider: str = "",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SessionInfo:
        """Register a new session.
        
        Args:
            session_name: Human-readable session name
            work_dir: Working directory path
            team_name: Team this session belongs to
            agent_name: Agent name in the team
            agent_id: Unique agent identifier
            role: Role (leader, worker, etc.)
            provider: AI provider (claude-code, codex, gemini, etc.)
            tags: Optional tags for categorization
            metadata: Additional metadata
            
        Returns:
            SessionInfo: The registered session
        """
        session = SessionInfo(
            session_name=session_name or f"session-{uuid.uuid4().hex[:8]}",
            work_dir=work_dir,
            team_name=team_name,
            agent_name=agent_name,
            agent_id=agent_id,
            role=role,
            provider=provider,
            tags=tags or [],
            metadata=metadata or {},
        )
        self._save_session(session)
        return session
    
    def unregister(self, session_id: str) -> bool:
        """Unregister a session.
        
        Args:
            session_id: Session ID to unregister
            
        Returns:
            bool: True if session was removed, False if not found
        """
        path = self._session_path(session_id)
        if path.exists():
            # Mark as shutdown instead of deleting for history
            session = self.get_session(session_id)
            if session:
                session.status = SessionStatus.shutdown
                session.updated_at = _now_iso()
                self._save_session(session)
            return True
        return False
    
    def _save_session(self, session: SessionInfo) -> None:
        """Save session to disk atomically."""
        path = self._session_path(session.session_id)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(
            session.model_dump_json(indent=2, by_alias=True, exclude_none=True),
            encoding="utf-8",
        )
        os.replace(str(tmp), str(path))
    
    def get_session(self, session_id: str) -> SessionInfo | None:
        """Get a session by ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            SessionInfo or None if not found
        """
        path = self._session_path(session_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return SessionInfo.model_validate(data)
        except Exception:
            return None
    
    def get_session_by_name(self, session_name: str) -> SessionInfo | None:
        """Get a session by name.
        
        Args:
            session_name: Session name
            
        Returns:
            SessionInfo or None if not found
        """
        for session in self.list_sessions():
            if session.session_name == session_name:
                return session
        return None
    
    def update_session(
        self,
        session_id: str,
        **updates: Any,
    ) -> SessionInfo | None:
        """Update session fields.
        
        Args:
            session_id: Session ID
            **updates: Fields to update
            
        Returns:
            Updated SessionInfo or None if not found
        """
        session = self.get_session(session_id)
        if not session:
            return None
        
        for key, value in updates.items():
            if hasattr(session, key):
                setattr(session, key, value)
        
        session.updated_at = _now_iso()
        self._save_session(session)
        return session
    
    def heartbeat(self, session_id: str) -> bool:
        """Update session heartbeat.
        
        Args:
            session_id: Session ID
            
        Returns:
            bool: True if heartbeat was updated, False if session not found
        """
        return self.update_session(session_id, last_heartbeat=_now_iso()) is not None
    
    def list_sessions(
        self,
        status: SessionStatus | None = None,
        team_name: str | None = None,
        role: str | None = None,
        provider: str | None = None,
        limit: int = 100,
    ) -> list[SessionInfo]:
        """List sessions with optional filters.
        
        Args:
            status: Filter by status
            team_name: Filter by team name
            role: Filter by role
            provider: Filter by provider
            limit: Maximum number of sessions to return
            
        Returns:
            List of SessionInfo objects
        """
        sessions = []
        for path in sorted(self._sessions_dir.glob("*.json"), reverse=True):
            if len(sessions) >= limit:
                break
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                session = SessionInfo.model_validate(data)
                
                # Apply filters
                if status and session.status != status:
                    continue
                if team_name and session.team_name != team_name:
                    continue
                if role and session.role != role:
                    continue
                if provider and session.provider != provider:
                    continue
                
                sessions.append(session)
            except Exception:
                continue
        
        return sessions
    
    def get_session_summary(
        self,
        session_id: str | None = None,
        session_name: str | None = None,
    ) -> dict[str, Any]:
        """Get a detailed summary of a session.
        
        Args:
            session_id: Session ID (preferred)
            session_name: Session name (fallback)
            
        Returns:
            Dict with session info, recent activities, and statistics
        """
        session = None
        if session_id:
            session = self.get_session(session_id)
        elif session_name:
            session = self.get_session_by_name(session_name)
        
        if not session:
            return {"error": "Session not found"}
        
        # Get recent activities
        activities = self._get_recent_activities(session.session_id, limit=20)
        
        return {
            "session": session.model_dump(by_alias=True, exclude_none=True),
            "recentActivities": [a.model_dump(by_alias=True, exclude_none=True) for a in activities],
            "statistics": {
                "filesModifiedCount": len(session.files_modified),
                "commandsExecutedCount": len(session.commands_executed),
                "tasksCompleted": session.tasks_completed,
                "uptimeSeconds": self._calculate_uptime(session),
            },
        }
    
    def _calculate_uptime(self, session: SessionInfo) -> int:
        """Calculate session uptime in seconds."""
        try:
            created = datetime.fromisoformat(session.created_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            return int((now - created).total_seconds())
        except Exception:
            return 0
    
    def _get_recent_activities(self, session_id: str, limit: int = 20) -> list[SessionActivity]:
        """Get recent activities for a session."""
        activities_dir = self._activities_path(session_id)
        if not activities_dir.exists():
            return []
        
        activities = []
        for path in sorted(activities_dir.glob("*.json"), reverse=True)[:limit]:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                activities.append(SessionActivity.model_validate(data))
            except Exception:
                continue
        
        return activities
    
    def log_activity(
        self,
        session_id: str,
        activity_type: str,
        description: str,
        details: dict[str, Any] | None = None,
    ) -> SessionActivity | None:
        """Log an activity for a session.
        
        Args:
            session_id: Session ID
            activity_type: Type of activity (file_write, command, task_complete, message)
            description: Human-readable description
            details: Additional details
            
        Returns:
            SessionActivity or None if session not found
        """
        session = self.get_session(session_id)
        if not session:
            return None
        
        activity = SessionActivity(
            session_id=session_id,
            activity_type=activity_type,
            description=description,
            details=details or {},
        )
        
        # Save activity
        activities_dir = self._activities_path(session_id)
        activities_dir.mkdir(parents=True, exist_ok=True)
        
        ts = int(datetime.now(timezone.utc).timestamp() * 1000)
        uid = uuid.uuid4().hex[:8]
        path = activities_dir / f"act-{ts}-{uid}.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(
            activity.model_dump_json(indent=2, by_alias=True, exclude_none=True),
            encoding="utf-8",
        )
        os.replace(str(tmp), str(path))
        
        # Update session based on activity type
        if activity_type == "file_write" and details and "file" in details:
            if details["file"] not in session.files_modified:
                session.files_modified.append(details["file"])
        elif activity_type == "command" and details and "command" in details:
            session.commands_executed.append(details["command"])
        elif activity_type == "task_complete":
            session.tasks_completed += 1
        
        session.updated_at = _now_iso()
        self._save_session(session)
        
        return activity
    
    def search_sessions(
        self,
        query: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search sessions by keyword.
        
        Searches across:
        - Session name
        - Agent name
        - Team name
        - Files modified
        - Commands executed
        - Activity descriptions
        
        Args:
            query: Search query (case-insensitive)
            limit: Maximum results to return
            
        Returns:
            List of matching sessions with highlights
        """
        query_lower = query.lower()
        results = []
        
        for session in self.list_sessions(limit=1000):  # Scan all sessions
            matches = []
            score = 0
            
            # Check session fields
            if query_lower in session.session_name.lower():
                matches.append(f"session_name: {session.session_name}")
                score += 10
            if query_lower in session.agent_name.lower():
                matches.append(f"agent_name: {session.agent_name}")
                score += 8
            if query_lower in session.team_name.lower():
                matches.append(f"team_name: {session.team_name}")
                score += 8
            
            # Check files modified
            for f in session.files_modified:
                if query_lower in f.lower():
                    matches.append(f"file: {f}")
                    score += 5
            
            # Check commands executed
            for c in session.commands_executed:
                if query_lower in c.lower():
                    matches.append(f"command: {c}")
                    score += 3
            
            # Check activities
            activities = self._get_recent_activities(session.session_id, limit=50)
            for act in activities:
                if query_lower in act.description.lower():
                    matches.append(f"activity: {act.description[:100]}")
                    score += 2
            
            if score > 0:
                results.append({
                    "session": session.model_dump(by_alias=True, exclude_none=True),
                    "matches": matches[:10],  # Limit matches shown
                    "score": score,
                })
        
        # Sort by score and return top results
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
    
    def cleanup_stale_sessions(self, max_age_hours: int = 24) -> int:
        """Clean up sessions that haven't had a heartbeat recently.
        
        Args:
            max_age_hours: Maximum age in hours before a session is considered stale
            
        Returns:
            Number of sessions cleaned up
        """
        cleaned = 0
        now = datetime.now(timezone.utc)
        
        for session in self.list_sessions(status=SessionStatus.active):
            try:
                last_heartbeat = datetime.fromisoformat(
                    session.last_heartbeat.replace("Z", "+00:00")
                )
                age_hours = (now - last_heartbeat).total_seconds() / 3600
                
                if age_hours > max_age_hours:
                    session.status = SessionStatus.shutdown
                    session.updated_at = _now_iso()
                    self._save_session(session)
                    cleaned += 1
            except Exception:
                continue
        
        return cleaned


# Singleton instance
_registry: SessionRegistry | None = None


def get_session_registry() -> SessionRegistry:
    """Get the singleton SessionRegistry instance."""
    global _registry
    if _registry is None:
        _registry = SessionRegistry()
    return _registry