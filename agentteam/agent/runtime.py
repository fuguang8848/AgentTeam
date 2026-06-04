"""
Agent Runtime for AgentTeam SDK

提供 Agent 的异步运行时环境。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional, Dict, List, Callable, Any, TypeVar

from ..core.types import AgentState
from .base import BaseAgent
from .protocol import AgentMessage, MessagePriority

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AsyncQueue:
    """异步队列"""
    
    def __init__(self, maxsize: int = 0):
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
    
    async def put(self, item: T) -> None:
        """添加元素"""
        await self._queue.put(item)
    
    async def get(self) -> T:
        """获取元素"""
        return await self._queue.get()
    
    def get_nowait(self) -> Optional[T]:
        """非阻塞获取"""
        try:
            return self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None
    
    async def join(self) -> None:
        """等待队列清空"""
        await self._queue.join()
    
    def qsize(self) -> int:
        """队列大小"""
        return self._queue.qsize()
    
    def empty(self) -> bool:
        """是否为空"""
        return self._queue.empty()


class AgentRuntime:
    """
    Agent 异步运行时
    
    管理 Agent 的生命周期、消息路由和并发执行。
    """
    
    def __init__(self, max_concurrent: int = 10):
        self._agents: Dict[str, BaseAgent] = {}
        self._tasks: Dict[str, asyncio.Task] = {}
        self._message_queue = AsyncQueue[AgentMessage]()
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._running = False
        self._max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    def register_agent(self, agent: BaseAgent) -> None:
        """注册 Agent"""
        if agent.name in self._agents:
            raise ValueError(f"Agent {agent.name} already registered")
        self._agents[agent.name] = agent
        logger.info(f"Registered agent: {agent.name}")
    
    def unregister_agent(self, name: str) -> bool:
        """注销 Agent"""
        if name in self._agents:
            del self._agents[name]
            logger.info(f"Unregistered agent: {name}")
            return True
        return False
    
    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """获取 Agent"""
        return self._agents.get(name)
    
    async def start(self) -> None:
        """启动运行时"""
        if self._running:
            return
        
        self._running = True
        self._message_processor = asyncio.create_task(self._process_messages())
        logger.info("AgentRuntime started")
    
    async def stop(self) -> None:
        """停止运行时"""
        if not self._running:
            return
        
        self._running = False
        
        for task in self._tasks.values():
            task.cancel()
        
        if self._message_processor:
            self._message_processor.cancel()
            try:
                await self._message_processor
            except asyncio.CancelledError:
                pass
        
        for agent in self._agents.values():
            try:
                await agent.stop()
            except Exception as e:
                logger.error(f"Error stopping agent {agent.name}: {e}")
        
        logger.info("AgentRuntime stopped")
    
    async def submit_task(
        self,
        agent_name: str,
        task_id: str,
        instruction: str,
    ) -> asyncio.Task:
        """提交任务到 Agent 执行"""
        agent = self._agents.get(agent_name)
        if not agent:
            raise ValueError(f"Agent {agent_name} not found")
        
        task = asyncio.create_task(self._execute_task(agent, task_id, instruction))
        self._tasks[task_id] = task
        return task
    
    async def _execute_task(self, agent: BaseAgent, task_id: str, instruction: str) -> str:
        """执行任务"""
        async with self._semaphore:
            try:
                result = await agent.execute(task_id, instruction)
                return result
            finally:
                if task_id in self._tasks:
                    del self._tasks[task_id]
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self._tasks:
            self._tasks[task_id].cancel()
            return True
        return False
    
    async def send_message(
        self,
        sender: str,
        receiver: str,
        content: str,
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> None:
        """发送消息"""
        message = AgentMessage(
            sender=sender,
            receiver=receiver,
            content=content,
            priority=priority,
        )
        await self._message_queue.put(message)
    
    async def _process_messages(self) -> None:
        """消息处理器"""
        while self._running:
            try:
                message = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=0.1,
                )
                
                if message.receiver == "__broadcast__":
                    await self._broadcast_message(message)
                else:
                    await self._route_message(message)
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")
    
    async def _route_message(self, message: AgentMessage) -> None:
        """路由消息到目标 Agent"""
        receiver = self._agents.get(message.receiver)
        if receiver and receiver.name in self._event_handlers:
            for handler in self._event_handlers[receiver.name]:
                try:
                    await handler(message)
                except Exception as e:
                    logger.error(f"Error in message handler: {e}")
    
    async def _broadcast_message(self, message: AgentMessage) -> None:
        """广播消息到所有 Agent"""
        for agent in self._agents.values():
            if agent.name != message.sender:
                message.receiver = agent.name
                await self._route_message(message)
    
    def on_message(self, agent_name: str, handler: Callable) -> None:
        """注册消息处理器"""
        if agent_name not in self._event_handlers:
            self._event_handlers[agent_name] = []
        self._event_handlers[agent_name].append(handler)
    
    def get_status(self) -> Dict[str, Any]:
        """获取运行时状态"""
        return {
            "running": self._running,
            "agents": {
                name: {
                    "type": agent.agent_type,
                    "state": agent.state.value,
                }
                for name, agent in self._agents.items()
            },
            "tasks": {
                "total": len(self._tasks),
                "running": sum(1 for t in self._tasks.values() if not t.done()),
            },
        }


# Global runtime instance
_runtime: Optional[AgentRuntime] = None


def get_runtime() -> AgentRuntime:
    """获取全局运行时实例"""
    global _runtime
    if _runtime is None:
        _runtime = AgentRuntime()
    return _runtime


async def init_runtime(max_concurrent: int = 10) -> AgentRuntime:
    """初始化全局运行时"""
    global _runtime
    _runtime = AgentRuntime(max_concurrent=max_concurrent)
    await _runtime.start()
    return _runtime


async def shutdown_runtime() -> None:
    """关闭全局运行时"""
    global _runtime
    if _runtime:
        await _runtime.stop()
        _runtime = None


__all__ = [
    "AgentRuntime",
    "AsyncQueue",
    "get_runtime",
    "init_runtime",
    "shutdown_runtime",
]
