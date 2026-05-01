"""记忆 Provider 抽象基类。

借鉴 Hermes Agent 的 MemoryProvider 架构。
能力：
- 后台预取记忆（prefetch）
- 同步对话到记忆（sync_turn）
- 会话结束时提取事实（on_session_end）
- 上下文压缩前提取洞察（on_pre_compress）
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, List


class MemoryProvider(ABC):
    """记忆 Provider 抽象基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider 名称"""
        pass
    
    @abstractmethod
    def prefetch(self, query: str) -> str:
        """后台预取记忆
        
        Args:
            query: 查询关键词
            
        Returns:
            检索到的相关记忆文本
        """
        pass
    
    @abstractmethod
    def sync_turn(self, user_msg: str, assistant_msg: str) -> None:
        """同步对话到记忆
        
        Args:
            user_msg: 用户消息
            assistant_msg: 助手回复
        """
        pass
    
    def on_session_end(self, messages: list[dict]) -> None:
        """会话结束时提取事实
        
        Args:
            messages: 完整对话历史
        """
        pass
    
    def on_pre_compress(self, messages: list[dict]) -> str:
        """上下文压缩前提取洞察
        
        Args:
            messages: 即将被压缩的对话历史
            
        Returns:
            提取的关键洞察文本
        """
        return ""
    
    def search(self, query: str, limit: int = 10) -> List[dict]:
        """搜索记忆
        
        Args:
            query: 搜索关键词
            limit: 返回结果数量限制
            
        Returns:
            记忆条目列表，每个条目包含：
            - text: 记忆文本
            - relevance: 相关性评分
            - metadata: 额外元数据
        """
        return []