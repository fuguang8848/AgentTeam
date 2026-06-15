"""
Core Team Definition for AgentTeam SDK

包含 CTTeam 类的定义。
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional, Dict, List

from .types import AgentState, TaskState
from .agent import CTAgent
from .task import CTTask
from .message import CTInbox, CTMessage


class CTTeam:
    """
    Team Container - 团队容器

    管理多个 CTAgent 和任务，支持：
    - Agent 注册和管理
    - 任务分配和跟踪
    - 消息队列
    - 状态持久化
    """

    def __init__(self, name: str, storage_path: Optional[Path] = None):
        self.name = name
        self.agents: Dict[str, CTAgent] = {}
        self.tasks: Dict[str, CTTask] = {}
        self.inbox = CTInbox()

        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            self.storage_path = Path("~/.agentteam/teams").expanduser() / name

        self._load_state()

    # ==================== Agent Management ====================

    def register_agent(
        self,
        name: str,
        agent_type: str,
        session_key: str,
        metadata: Optional[dict] = None,
    ) -> CTAgent:
        """注册 Agent"""
        agent = CTAgent(
            name=name,
            agent_type=agent_type,
            session_key=session_key,
            team_name=self.name,
            metadata=metadata or {},
        )
        self.agents[name] = agent
        self._save_state()
        return agent

    def get_agent(self, name: str) -> Optional[CTAgent]:
        """获取 Agent"""
        return self.agents.get(name)

    def remove_agent(self, name: str) -> bool:
        """移除 Agent"""
        if name in self.agents:
            del self.agents[name]
            self._save_state()
            return True
        return False

    def update_agent_state(self, name: str, state: AgentState) -> bool:
        """更新 Agent 状态"""
        agent = self.agents.get(name)
        if agent:
            agent.update_state(state)
            self._save_state()
            return True
        return False

    # ==================== Task Management ====================

    def create_task(
        self,
        title: str,
        description: str = "",
        assignee: Optional[str] = None,
        priority: int = 0,
    ) -> CTTask:
        """创建任务"""
        task = CTTask.create(
            title=title,
            description=description,
            assignee=assignee,
            priority=priority,
        )
        self.tasks[task.id] = task

        if assignee:
            agent = self.agents.get(assignee)
            if agent:
                agent.assign_task(task.id)

        self._save_state()
        return task

    def get_task(self, task_id: str) -> Optional[CTTask]:
        """获取任务"""
        return self.tasks.get(task_id)

    def assign_task(self, task_id: str, agent_name: str) -> bool:
        """分配任务给 Agent"""
        task = self.tasks.get(task_id)
        agent = self.agents.get(agent_name)

        if task and agent:
            task.assign_to(agent_name)
            agent.assign_task(task_id)
            self._save_state()
            return True
        return False

    def complete_task(self, task_id: str, result: Optional[str] = None) -> bool:
        """完成任务"""
        task = self.tasks.get(task_id)
        if not task:
            return False

        task.complete(result)

        if task.assignee:
            agent = self.agents.get(task.assignee)
            if agent:
                agent.complete_task()

        self._save_state()
        return True

    def fail_task(self, task_id: str, error: str) -> bool:
        """标记任务失败"""
        task = self.tasks.get(task_id)
        if task:
            task.fail(error)
            self._save_state()
            return True
        return False

    def get_pending_tasks(self) -> List[CTTask]:
        """获取待处理任务"""
        return [t for t in self.tasks.values() if t.state == TaskState.PENDING]

    # ==================== Message Management ====================

    def send_message(
        self,
        from_agent: str,
        to_agent: str,
        content: str,
    ) -> Optional[CTMessage]:
        """发送消息"""
        return self.inbox.send_message(
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
        )

    def broadcast(self, from_agent: str, content: str) -> Optional[CTMessage]:
        """广播消息"""
        return self.inbox.broadcast(from_agent=from_agent, content=content)

    def get_messages(self, agent_name: Optional[str] = None, unread_only: bool = False) -> List[CTMessage]:
        """获取消息"""
        return self.inbox.get_messages(agent_name=agent_name, unread_only=unread_only)

    # ==================== Status & Utilities ====================

    def get_status(self) -> dict:
        """获取团队状态"""
        return {
            "team": self.name,
            "agents": {
                name: {"state": a.state.value, "type": a.agent_type, "task_id": a.task_id}
                for name, a in self.agents.items()
            },
            "tasks": {
                "total": len(self.tasks),
                "completed": sum(1 for t in self.tasks.values() if t.state == TaskState.COMPLETED),
                "in_progress": sum(1 for t in self.tasks.values() if t.state == TaskState.IN_PROGRESS),
            },
            "inbox": {
                "total": len(self.inbox.messages),
                "unread": self.inbox.count(unread_only=True),
            },
        }

    def wait_all(self, timeout: int = 3600) -> dict:
        """等待所有 Agent 完成"""
        start = time.time()
        while time.time() - start < timeout:
            states = [a.state for a in self.agents.values()]
            if all(s in (AgentState.COMPLETED, AgentState.FAILED) for s in states):
                break
            time.sleep(1)
        return self.get_status()

    # ==================== Persistence ====================

    def _get_state_file(self) -> Path:
        """获取状态文件路径"""
        return self.storage_path / "team_state.json"

    def _save_state(self) -> None:
        """保存状态"""
        try:
            self.storage_path.mkdir(parents=True, exist_ok=True)
            state = {
                "name": self.name,
                "agents": {name: agent.to_dict() for name, agent in self.agents.items()},
                "tasks": {tid: task.to_dict() for tid, task in self.tasks.items()},
                "inbox": self.inbox.to_dict(),
            }
            with open(self._get_state_file(), "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _load_state(self) -> None:
        """加载状态"""
        state_file = self._get_state_file()
        if state_file.exists():
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)

                self.name = state.get("name", self.name)
                self.agents = {name: CTAgent.from_dict(data) for name, data in state.get("agents", {}).items()}
                self.tasks = {tid: CTTask.from_dict(data) for tid, data in state.get("tasks", {}).items()}
                self.inbox = CTInbox.from_dict(state.get("inbox", {}))
            except Exception:
                pass

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "name": self.name,
            "agents": {name: agent.to_dict() for name, agent in self.agents.items()},
            "tasks": {tid: task.to_dict() for tid, task in self.tasks.items()},
        }

    @classmethod
    def from_dict(cls, data: dict, storage_path: Optional[Path] = None) -> "CTTeam":
        """从字典创建"""
        team = cls(data.get("name", "unknown"), storage_path=storage_path)
        team.agents = {name: CTAgent.from_dict(agent_data) for name, agent_data in data.get("agents", {}).items()}
        team.tasks = {tid: CTTask.from_dict(task_data) for tid, task_data in data.get("tasks", {}).items()}
        return team


# Backwards compatibility alias
Team = CTTeam
