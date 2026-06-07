"""
Agent Base Classes for AgentTeam SDK

提供 Agent 的基础抽象类和接口。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field

from ..core.types import AgentState
from ..core.agent import CTAgent


@dataclass
class AgentConfig:
    """Agent 配置"""

    name: str
    agent_type: str
    session_key: str = ""
    timeout: int = 3600
    max_retries: int = 3
    retry_delay: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """
    Agent 抽象基类

    提供 Agent 的通用接口和生命周期管理。
    子类需要实现具体的行为逻辑。
    """

    def __init__(
        self,
        config: AgentConfig,
        agent_instance: Optional[CTAgent] = None,
    ):
        self.config = config
        self._agent = agent_instance or CTAgent(
            name=config.name,
            agent_type=config.agent_type,
            session_key=config.session_key,
            metadata=config.metadata,
        )

        # 回调
        self._on_state_change: Optional[Callable[[AgentState, AgentState], None]] = None
        self._on_message: Optional[Callable[[str, str], None]] = None
        self._on_error: Optional[Callable[[Exception], None]] = None

    @property
    def name(self) -> str:
        """Agent 名称"""
        return self._agent.name

    @property
    def agent_type(self) -> str:
        """Agent 类型"""
        return self._agent.agent_type

    @property
    def state(self) -> AgentState:
        """当前状态"""
        return self._agent.state

    @property
    def agent(self) -> CTAgent:
        """底层 CTAgent 实例"""
        return self._agent

    def update_state(self, state: AgentState) -> None:
        """更新状态"""
        old_state = self._agent.state
        self._agent.update_state(state)
        if self._on_state_change:
            self._on_state_change(old_state, state)

    @abstractmethod
    async def start(self) -> None:
        """启动 Agent"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """停止 Agent"""
        pass

    @abstractmethod
    async def execute(self, task_id: str, instruction: str) -> str:
        """执行任务"""
        pass

    def is_active(self) -> bool:
        """检查是否处于活跃状态"""
        return self._agent.is_active()

    def is_done(self) -> bool:
        """检查是否已结束"""
        return self._agent.is_done()

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "config": {
                "name": self.config.name,
                "agent_type": self.config.agent_type,
                "session_key": self.config.session_key,
                "timeout": self.config.timeout,
                "max_retries": self.config.max_retries,
                "metadata": self.config.metadata,
            },
            "agent": self._agent.to_dict(),
        }


class SyncAgent(BaseAgent):
    """同步 Agent 基类"""

    def __init__(self, config: AgentConfig):
        super().__init__(config)

    async def start(self) -> None:
        self.update_state(AgentState.RUNNING)

    async def stop(self) -> None:
        self.update_state(AgentState.TERMINATED)

    async def execute(self, task_id: str, instruction: str) -> str:
        self.update_state(AgentState.RUNNING)
        self._agent.assign_task(task_id)

        try:
            result = self._execute_sync(task_id, instruction)
            self._agent.complete_task()
            return result
        except Exception as e:
            self._agent.fail(str(e))
            raise

    @abstractmethod
    def _execute_sync(self, task_id: str, instruction: str) -> str:
        """同步执行任务"""
        pass


__all__ = [
    "AgentConfig",
    "BaseAgent",
    "SyncAgent",
]
