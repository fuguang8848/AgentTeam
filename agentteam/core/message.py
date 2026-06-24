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

    Extended with philosophical collaboration fields:
    - blind_spot_report: 柏拉图洞穴 — agent 执行结果中未看到的"盲区"
    - genealogy_trace:   尼采系谱学 — 安全规则的来源追踪

    收到 SOCRATIC_QUESTION 类型的消息时，agent 应通过诘问
    迫使对方发现自己的矛盾（苏格拉底产婆术）。
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    from_agent: str = ""
    to_agent: str = ""
    content: str = ""
    message_type: MessageType = MessageType.TEXT
    timestamp: float = field(default_factory=time.time)
    read: bool = False
    metadata: dict = field(default_factory=dict)
    # ── 柏拉图洞穴 allegory — 全局视角汇报 ─────────────────────
    blind_spot_report: Optional[str] = None   # 本次执行中我未看到的全局盲区
    # ── 尼采系谱学 — 安全规则来源追踪 ─────────────────────────
    genealogy_trace: Optional[dict] = None   # {rule_id, created_at, created_by, reason, parent_rule_id}

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
            "blind_spot_report": self.blind_spot_report,
            "genealogy_trace": self.genealogy_trace,
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
            blind_spot_report=data.get("blind_spot_report"),
            genealogy_trace=data.get("genealogy_trace"),
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
        blind_spot_report: Optional[str] = None,
        genealogy_trace: Optional[dict] = None,
    ) -> CTMessage:
        """发送消息的便捷方法

        接受柏拉图洞穴 allegory 和尼采系谱学字段：
        - blind_spot_report: 发送方汇报自己在全局视角下的盲区
        - genealogy_trace: 安全规则的来源追踪数据
        """
        message = CTMessage(
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            message_type=message_type,
            metadata=metadata or {},
            blind_spot_report=blind_spot_report,
            genealogy_trace=genealogy_trace,
        )
        self.send(message)
        return message

    def broadcast(
        self,
        from_agent: str,
        content: str,
        message_type: MessageType = MessageType.BROADCAST,
        metadata: Optional[dict] = None,
        blind_spot_report: Optional[str] = None,
        genealogy_trace: Optional[dict] = None,
    ) -> CTMessage:
        """广播消息，支持柏拉图洞穴盲区汇报和尼采系谱学追踪"""
        return self.send_message(
            from_agent=from_agent,
            to_agent="__broadcast__",
            content=content,
            message_type=message_type,
            metadata=metadata,
            blind_spot_report=blind_spot_report,
            genealogy_trace=genealogy_trace,
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
        """获取消息列表，支持按消息类型过滤（包括新增的 SOCRATIC_QUESTION、BLIND_SPOT_REPORT、GENEALOGY_TRACE）"""
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
