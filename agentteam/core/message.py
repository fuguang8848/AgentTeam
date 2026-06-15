"""
Core Message Definition for AgentTeam SDK

包含 CTMessage 和 CTInbox 类的定义。
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional, List, Callable, Dict

from .types import MessageType


@dataclass
class CTMessage:
    """
    Team Message - 团队消息
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    from_agent: str = ""
    to_agent: str = ""
    content: str = ""
    message_type: MessageType = MessageType.TEXT
    timestamp: float = field(default_factory=time.time)
    read: bool = False
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "content": self.content,
            "message_type": self.message_type.value,
            "timestamp": self.timestamp,
            "read": self.read,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CTMessage":
        """从字典创建"""
        msg_type = data.get("message_type", "text")
        if isinstance(msg_type, str):
            msg_type = MessageType(msg_type)
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            from_agent=data.get("from_agent", ""),
            to_agent=data.get("to_agent", ""),
            content=data.get("content", ""),
            message_type=msg_type,
            timestamp=data.get("timestamp", time.time()),
            read=data.get("read", False),
            metadata=data.get("metadata", {}),
        )

    def mark_read(self) -> None:
        """标记为已读"""
        self.read = True

    def is_broadcast(self) -> bool:
        """检查是否是广播消息"""
        return self.to_agent == "__broadcast__"


class CTInbox:
    """
    Team Inbox - Agent 消息队列
    """

    def __init__(self):
        self.messages: List[CTMessage] = []
        self._handlers: Dict[str, List[Callable[[CTMessage], None]]] = {}

    def send(self, message: CTMessage) -> None:
        """发送消息"""
        self.messages.append(message)
        self._dispatch(message)

    def send_message(
        self,
        from_agent: str,
        to_agent: str,
        content: str,
        message_type: MessageType = MessageType.TEXT,
        metadata: Optional[dict] = None,
    ) -> CTMessage:
        """发送消息的便捷方法"""
        message = CTMessage(
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            message_type=message_type,
            metadata=metadata or {},
        )
        self.send(message)
        return message

    def broadcast(
        self,
        from_agent: str,
        content: str,
        message_type: MessageType = MessageType.BROADCAST,
        metadata: Optional[dict] = None,
    ) -> CTMessage:
        """广播消息"""
        return self.send_message(
            from_agent=from_agent,
            to_agent="__broadcast__",
            content=content,
            message_type=message_type,
            metadata=metadata,
        )

    def receive(self, agent_name: str, mark_read: bool = True) -> Optional[CTMessage]:
        """接收消息（阻塞式）"""
        for msg in self.messages:
            if msg.to_agent == agent_name and not msg.read:
                if mark_read:
                    msg.mark_read()
                return msg
        return None

    def get_messages(
        self,
        agent_name: Optional[str] = None,
        unread_only: bool = False,
        message_type: Optional[MessageType] = None,
    ) -> List[CTMessage]:
        """获取消息列表"""
        result = self.messages

        if agent_name:
            result = [m for m in result if m.to_agent == agent_name or m.is_broadcast()]

        if unread_only:
            result = [m for m in result if not m.read]

        if message_type:
            result = [m for m in result if m.message_type == message_type]

        return result

    def count(self, agent_name: Optional[str] = None, unread_only: bool = False) -> int:
        """统计消息数量"""
        return len(self.get_messages(agent_name=agent_name, unread_only=unread_only))

    def clear(self, agent_name: Optional[str] = None) -> None:
        """清除消息"""
        if agent_name:
            self.messages = [m for m in self.messages if m.to_agent != agent_name and m.from_agent != agent_name]
        else:
            self.messages = []

    def register_handler(
        self,
        agent_name: str,
        handler: Callable[[CTMessage], None],
    ) -> None:
        """注册消息处理器"""
        if agent_name not in self._handlers:
            self._handlers[agent_name] = []
        self._handlers[agent_name].append(handler)

    def _dispatch(self, message: CTMessage) -> None:
        """分发消息到处理器"""
        if message.to_agent in self._handlers:
            for handler in self._handlers[message.to_agent]:
                handler(message)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {"messages": [m.to_dict() for m in self.messages]}

    @classmethod
    def from_dict(cls, data: dict) -> "CTInbox":
        """从字典创建"""
        inbox = cls()
        inbox.messages = [CTMessage.from_dict(m) for m in data.get("messages", [])]
        return inbox


# Backwards compatibility alias
Message = CTMessage
Inbox = CTInbox
