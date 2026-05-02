"""
ClawTeam Core - 真正的多 Agent 协作框架 (SDK 风格)

核心概念：
- CTTeam: 团队容器，管理多个 CTAgent
- CTAgent: 运行在 OpenClaw Session 中的智能体
- CTInbox: Agent 之间的消息队列
- CTTask: 任务跟踪

架构：
┌─────────────────────────────────────────────────────────────┐
│                        CTTeam                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │ CTAgent  │  │ CTAgent  │  │ CTAgent  │               │
│  │ (LLM)   │  │ (LLM)    │  │ (LLM)    │               │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘               │
│       │             │             │                       │
│       └─────────────┼─────────────┘                       │
│                     │                                     │
│              ┌──────▼──────┐                             │
│              │   CTInbox   │  (消息队列)                  │
│              └─────────────┘                             │
└─────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from enum import Enum


class AgentState(Enum):
    """Agent State"""

    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"
    TERMINATED = "terminated"


class TaskState(Enum):
    """Task State"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


@dataclass
class CTAgent:
    """Team Agent - runs in OpenClaw Session"""

    name: str
    agent_type: str  # "coder", "reviewer", "leader", etc.
    session_key: str
    state: AgentState = AgentState.PENDING
    team_name: str = ""
    task_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "agent_type": self.agent_type,
            "session_key": self.session_key,
            "state": self.state.value,
            "team_name": self.team_name,
            "task_id": self.task_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CTAgent":
        return cls(
            name=data["name"],
            agent_type=data["agent_type"],
            session_key=data["session_key"],
            state=AgentState(data.get("state", "pending")),
            team_name=data.get("team_name", ""),
            task_id=data.get("task_id"),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            metadata=data.get("metadata", {}),
        )


@dataclass
class CTTask:
    """Team Task"""

    id: str
    title: str
    description: str
    assignee: Optional[str] = None
    state: TaskState = TaskState.PENDING
    priority: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    result: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "assignee": self.assignee,
            "state": self.state.value,
            "priority": self.priority,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CTTask":
        return cls(
            id=data["id"],
            title=data["title"],
            description=data["description"],
            assignee=data.get("assignee"),
            state=TaskState(data.get("state", "pending")),
            priority=data.get("priority", 0),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            completed_at=data.get("completed_at"),
            result=data.get("result"),
            error=data.get("error"),
        )


@dataclass
class CTMessage:
    """Inbox Message"""

    id: str
    from_agent: str
    to_agent: str
    content: str
    msg_type: str = "text"  # "text", "task", "alert", "result"
    timestamp: float = field(default_factory=time.time)
    read: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "content": self.content,
            "msg_type": self.msg_type,
            "timestamp": self.timestamp,
            "read": self.read,
        }


class CTTeam:
    """
    CTTeam - Team container for multi-agent collaboration

    Example:
        team = CTTeam("my-project")
        team.spawn("coder", "写一个 Web 服务器")
        team.spawn("reviewer", "审查代码")
        team.wait_all()
    """

    def __init__(self, name: str, data_dir: Path | None = None):
        self.name = name
        self.data_dir = data_dir or Path(f"~/.clawteam/teams/{name}").expanduser()
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.agents: dict[str, CTAgent] = {}
        self.tasks: dict[str, CTTask] = {}
        self.inbox: list[CTMessage] = []

        self._load_state()

    def _load_state(self) -> None:
        """Load state from disk"""
        # Load agents
        agents_file = self.data_dir / "agents.json"
        if agents_file.exists():
            try:
                data = json.loads(agents_file.read_text(encoding="utf-8"))
                self.agents = {n: CTAgent.from_dict(i) for n, i in data.items()}
            except Exception:
                pass

        # Load tasks
        tasks_file = self.data_dir / "tasks.json"
        if tasks_file.exists():
            try:
                data = json.loads(tasks_file.read_text(encoding="utf-8"))
                self.tasks = {tid: CTTask.from_dict(t) for tid, t in data.items()}
            except Exception:
                pass

        # Load inbox
        inbox_file = self.data_dir / "inbox.json"
        if inbox_file.exists():
            try:
                data = json.loads(inbox_file.read_text(encoding="utf-8"))
                self.inbox = [CTMessage(**m) for m in data]
            except Exception:
                pass

    def _save_state(self) -> None:
        """Save state to disk"""
        agents_file = self.data_dir / "agents.json"
        agents_file.write_text(
            json.dumps({n: a.to_dict() for n, a in self.agents.items()}, indent=2), encoding="utf-8"
        )

        tasks_file = self.data_dir / "tasks.json"
        tasks_file.write_text(
            json.dumps({tid: t.to_dict() for tid, t in self.tasks.items()}, indent=2),
            encoding="utf-8",
        )

        inbox_file = self.data_dir / "inbox.json"
        inbox_file.write_text(
            json.dumps([m.to_dict() for m in self.inbox], indent=2), encoding="utf-8"
        )

    def spawn(
        self,
        name: str,
        task: str | None = None,
        agent_type: str = "worker",
        model: str | None = None,
    ) -> CTAgent:
        """
        Spawn an agent (uses OpenClaw SDK Backend)
        """
        from clawteam.spawn import get_backend

        backend = get_backend("openclaw_sdk")
        result = backend.spawn(
            command=["openclaw"],
            agent_name=name,
            agent_id=f"{self.name}:{name}",
            agent_type=agent_type,
            team_name=self.name,
            prompt=task,
            model=model,
        )

        if result.startswith("Error"):
            raise RuntimeError(result)

        agent = CTAgent(
            name=name,
            agent_type=agent_type,
            session_key="",
            state=AgentState.RUNNING,
            team_name=self.name,
        )

        if "session=" in result:
            session_key = result.split("session=")[1].rstrip(")")
            agent.session_key = session_key

        self.agents[name] = agent
        self._save_state()

        return agent

    def create_task(
        self,
        title: str,
        description: str,
        priority: int = 0,
    ) -> CTTask:
        """Create a task"""
        import uuid

        task = CTTask(
            id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            priority=priority,
        )
        self.tasks[task.id] = task
        self._save_state()
        return task

    def assign_task(self, task_id: str, to_agent: str) -> None:
        """Assign task to agent"""
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        task.assignee = to_agent
        task.state = TaskState.IN_PROGRESS
        task.updated_at = time.time()

        agent = self.agents.get(to_agent)
        if agent:
            agent.task_id = task_id
            agent.state = AgentState.RUNNING

        self._save_state()

        self.send_message(
            from_agent="leader",
            to_agent=to_agent,
            content=f"New task: {task.title}\n\n{task.description}",
            msg_type="task",
        )

    def send_message(
        self,
        from_agent: str,
        to_agent: str,
        content: str,
        msg_type: str = "text",
    ) -> CTMessage:
        """Send a message"""
        import uuid

        msg = CTMessage(
            id=str(uuid.uuid4())[:8],
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            msg_type=msg_type,
        )
        self.inbox.append(msg)
        self._save_state()
        return msg

    def get_messages(self, agent_name: str, unread_only: bool = False) -> list[CTMessage]:
        """Get messages for an agent"""
        msgs = [m for m in self.inbox if m.to_agent in (agent_name, "all")]
        if unread_only:
            msgs = [m for m in msgs if not m.read]
        return msgs

    def mark_read(self, message_id: str) -> None:
        """Mark message as read"""
        for msg in self.inbox:
            if msg.id == message_id:
                msg.read = True
        self._save_state()

    def complete_task(self, task_id: str, result: str) -> None:
        """Mark task as completed"""
        task = self.tasks.get(task_id)
        if task:
            task.state = TaskState.COMPLETED
            task.result = result
            task.completed_at = time.time()
            task.updated_at = time.time()

            if task.assignee:
                agent = self.agents.get(task.assignee)
                if agent:
                    agent.state = AgentState.COMPLETED

            self._save_state()

    def get_status(self) -> dict:
        """Get team status"""
        return {
            "team": self.name,
            "agents": {
                name: {"state": a.state.value, "type": a.agent_type, "task_id": a.task_id}
                for name, a in self.agents.items()
            },
            "tasks": {
                "total": len(self.tasks),
                "completed": sum(1 for t in self.tasks.values() if t.state == TaskState.COMPLETED),
                "in_progress": sum(
                    1 for t in self.tasks.values() if t.state == TaskState.IN_PROGRESS
                ),
            },
            "inbox": {
                "total": len(self.inbox),
                "unread": sum(1 for m in self.inbox if not m.read),
            },
        }

    def wait_all(self, timeout: int = 3600) -> dict:
        """Wait for all agents to complete"""
        start = time.time()
        while time.time() - start < timeout:
            states = [a.state for a in self.agents.values()]
            if all(s in (AgentState.COMPLETED, AgentState.FAILED) for s in states):
                break
            time.sleep(10)
        return self.get_status()


# Backwards compatibility aliases
Team = CTTeam
Agent = CTAgent
Task = CTTask
Message = CTMessage
AgentStatus = AgentState
TaskStatus = TaskState

create_team = lambda name: CTTeam(name)
get_team = lambda name: (
    CTTeam(name) if Path(f"~/.clawteam/teams/{name}").expanduser().exists() else None
)
