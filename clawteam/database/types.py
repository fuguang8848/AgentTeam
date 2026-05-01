"""Database schema types and models."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
import json


class DatabaseTask(BaseModel):
    """Task entity for database storage."""
    id: str
    title: str
    description: str = ""
    status: str = "pending"
    priority: str = "medium"
    tags: List[str] = Field(default_factory=list)
    parent_task_id: Optional[str] = None
    team_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    def model_dump_jsonable(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        result = self.model_dump()
        result["created_at"] = self.created_at.isoformat()
        result["updated_at"] = self.updated_at.isoformat()
        if self.completed_at:
            result["completed_at"] = self.completed_at.isoformat()
        result["tags"] = json.dumps(self.tags)
        return result
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> DatabaseTask:
        """Create from database row."""
        data = dict(row)
        # Parse tags from JSON string
        if data.get("tags"):
            try:
                data["tags"] = json.loads(data["tags"])
            except:
                data["tags"] = []
        # Convert datetime strings
        for field in ["created_at", "updated_at", "completed_at"]:
            if data.get(field) and isinstance(data[field], str):
                try:
                    data[field] = datetime.fromisoformat(data[field].replace("Z", "+00:00"))
                except:
                    pass
        return cls(**data)


class DatabaseSession(BaseModel):
    """Session entity for database storage."""
    id: str
    name: str
    task_id: Optional[str] = None
    working_directory: str = ""
    status: str = "running"
    provider_id: Optional[str] = None
    team_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    terminated_at: Optional[datetime] = None
    
    def model_dump_jsonable(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        result = self.model_dump()
        result["created_at"] = self.created_at.isoformat()
        result["updated_at"] = self.updated_at.isoformat()
        if self.terminated_at:
            result["terminated_at"] = self.terminated_at.isoformat()
        return result


class DatabaseAgent(BaseModel):
    """Agent entity for database storage."""
    id: str
    name: str
    team_id: Optional[str] = None
    role: Optional[str] = None
    status: str = "idle"
    current_task_id: Optional[str] = None
    last_seen_at: datetime = Field(default_factory=datetime.now)
    created_at: datetime = Field(default_factory=datetime.now)
    result_data: Optional[Dict[str, Any]] = None
    
    def model_dump_jsonable(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        result = self.model_dump()
        result["created_at"] = self.created_at.isoformat()
        result["last_seen_at"] = self.last_seen_at.isoformat()
        if self.result_data:
            result["result_data"] = json.dumps(self.result_data)
        return result


class DatabaseMessage(BaseModel):
    """Message entity for database storage."""
    id: str
    sender: str
    recipient: str
    content: str
    team_id: Optional[str] = None
    task_id: Optional[str] = None
    session_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    delivered: bool = False
    
    def model_dump_jsonable(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        result = self.model_dump()
        result["created_at"] = self.created_at.isoformat()
        if self.expires_at:
            result["expires_at"] = self.expires_at.isoformat()
        return result


class DatabaseAlert(BaseModel):
    """Alert entity for database storage."""
    id: str
    title: str
    message: str
    level: str = "info"
    team_id: Optional[str] = None
    task_id: Optional[str] = None
    session_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    def model_dump_jsonable(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        result = self.model_dump()
        result["created_at"] = self.created_at.isoformat()
        if self.acknowledged_at:
            result["acknowledged_at"] = self.acknowledged_at.isoformat()
        if self.resolved_at:
            result["resolved_at"] = self.resolved_at.isoformat()
        return result


class DatabaseUsage(BaseModel):
    """Usage/token statistics entity."""
    id: str
    session_id: str
    team_id: Optional[str] = None
    task_id: Optional[str] = None
    provider_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)
    
    def model_dump_jsonable(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        result = self.model_dump()
        result["timestamp"] = self.timestamp.isoformat()
        return result
