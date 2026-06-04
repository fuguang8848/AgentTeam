"""
Agent Communication Protocol for AgentTeam SDK

定义 Agent 之间的通信协议和消息格式。
"""

from __future__ import annotations

import json
import uuid
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum

from ..core.types import MessageType
from ..core.message import CTMessage


class ProtocolVersion:
    """协议版本"""
    CURRENT = "1.0"
    MINIMUM = "1.0"


class MessagePriority(Enum):
    """消息优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


@dataclass
class AgentMessage:
    """Agent 间通信的消息格式"""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    protocol_version: str = ProtocolVersion.CURRENT
    message_type: MessageType = MessageType.TEXT
    priority: MessagePriority = MessagePriority.NORMAL
    sender: str = ""
    receiver: str = ""
    content: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "protocol_version": self.protocol_version,
            "message_type": self.message_type.value,
            "priority": self.priority.value,
            "sender": self.sender,
            "receiver": self.receiver,
            "content": self.content,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "reply_to": self.reply_to,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "AgentMessage":
        """从字典创建"""
        msg_type = data.get("message_type", "text")
        if isinstance(msg_type, str):
            msg_type = MessageType(msg_type)
        
        priority = data.get("priority", 1)
        if isinstance(priority, int):
            priority = MessagePriority(priority)
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            protocol_version=data.get("protocol_version", ProtocolVersion.CURRENT),
            message_type=msg_type,
            priority=priority,
            sender=data.get("sender", ""),
            receiver=data.get("receiver", ""),
            content=data.get("content", ""),
            payload=data.get("payload", {}),
            timestamp=data.get("timestamp", time.time()),
            correlation_id=data.get("correlation_id"),
            reply_to=data.get("reply_to"),
        )
    
    def to_json(self) -> str:
        """序列化为 JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> "AgentMessage":
        """从 JSON 反序列化"""
        return cls.from_dict(json.loads(json_str))
    
    def create_reply(self, content: str, sender: str) -> "AgentMessage":
        """创建回复消息"""
        return AgentMessage(
            sender=sender,
            receiver=self.sender,
            content=content,
            correlation_id=self.correlation_id or self.id,
            reply_to=self.id,
        )
    
    def is_broadcast(self) -> bool:
        """是否是广播消息"""
        return self.receiver == "__broadcast__" or self.receiver == ""


# Convert between CTMessage and AgentMessage
def ctmessage_to_agentmessage(ct_msg: CTMessage) -> AgentMessage:
    """将 CTMessage 转换为 AgentMessage"""
    return AgentMessage(
        id=ct_msg.id,
        sender=ct_msg.from_agent,
        receiver=ct_msg.to_agent,
        content=ct_msg.content,
        message_type=ct_msg.message_type,
        timestamp=ct_msg.timestamp,
        payload=ct_msg.metadata,
    )


def agentmessage_to_ctmessage(agent_msg: AgentMessage) -> CTMessage:
    """将 AgentMessage 转换为 CTMessage"""
    return CTMessage(
        id=agent_msg.id,
        from_agent=agent_msg.sender,
        to_agent=agent_msg.receiver,
        content=agent_msg.content,
        message_type=agent_msg.message_type,
        timestamp=agent_msg.timestamp,
        metadata=agent_msg.payload,
    )


__all__ = [
    "ProtocolVersion",
    "MessagePriority",
    "AgentMessage",
    "ctmessage_to_agentmessage",
    "agentmessage_to_ctmessage",
]
