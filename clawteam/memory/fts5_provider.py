"""基于 SQLite FTS5 的全文记忆检索。

与 LanceDB 向量检索互补：
- FTS5：精确关键词匹配
- LanceDB：语义相似度

注意事项：
- FTS5 在大多数 SQLite 版本中可用，但不是所有
- 需要提供 fallback 机制
"""

from __future__ import annotations
import sqlite3
import json
import time
from pathlib import Path
from typing import List, Optional, Tuple
import logging

from .provider import MemoryProvider

logger = logging.getLogger(__name__)


class FTS5MemoryProvider(MemoryProvider):
    """FTS5 全文检索记忆提供者"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Args:
            db_path: SQLite 数据库文件路径，None 则使用内存数据库
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._fts5_available = False
        self._initialized = False
        
    @property
    def name(self) -> str:
        return "fts5_memory"
    
    def _check_fts5_available(self) -> bool:
        """检查 FTS5 是否可用"""
        try:
            conn = sqlite3.connect(":memory:")
            conn.execute("CREATE VIRTUAL TABLE test_fts5 USING fts5(content);")
            conn.execute("DROP TABLE test_fts5;")
            conn.close()
            return True
        except sqlite3.OperationalError as e:
            logger.warning(f"FTS5 not available: {e}")
            return False
    
    def _initialize_db(self) -> bool:
        """初始化数据库"""
        if self._initialized:
            return self._fts5_available
            
        self._fts5_available = self._check_fts5_available()
        
        if not self._fts5_available:
            logger.warning("FTS5 not available, provider will operate in fallback mode")
            self._initialized = True
            return False
        
        try:
            if self.db_path:
                db_file = Path(self.db_path)
                db_file.parent.mkdir(parents=True, exist_ok=True)
                self.conn = sqlite3.connect(str(db_file))
            else:
                self.conn = sqlite3.connect(":memory:")
            
            # 创建 FTS5 表
            self.conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts5 USING fts5(
                    id UNINDEXED,
                    text,
                    timestamp,
                    session_id,
                    metadata
                );
            """)
            
            # 创建普通表作为 fallback
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_fallback (
                    id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    session_id TEXT,
                    metadata TEXT
                );
            """)
            
            # 创建索引
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_fallback_timestamp ON memory_fallback(timestamp);")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_fallback_session ON memory_fallback(session_id);")
            
            self.conn.commit()
            self._initialized = True
            logger.info(f"FTS5 memory provider initialized (db_path={self.db_path})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize FTS5 memory provider: {e}")
            self._fts5_available = False
            self._initialized = True
            return False
    
    def _generate_id(self) -> str:
        """生成唯一 ID"""
        import uuid
        return f"mem_{uuid.uuid4().hex[:16]}"
    
    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        if not self._initialized:
            self._initialize_db()
        
        if self.conn is None:
            # 如果没有可用连接，创建内存连接
            self.conn = sqlite3.connect(":memory:")
            self._fts5_available = False
            logger.warning("Using in-memory fallback database")
        
        return self.conn
    
    def prefetch(self, query: str) -> str:
        """后台预取记忆"""
        results = self.search(query, limit=5)
        if not results:
            return ""
        
        # 合并相关记忆
        memory_texts = [r.get("text", "") for r in results]
        return "\n".join(memory_texts)
    
    def sync_turn(self, user_msg: str, assistant_msg: str) -> None:
        """同步对话到记忆"""
        conn = self._get_conn()
        timestamp = time.time()
        
        # 为对话生成摘要
        summary = f"用户: {user_msg[:100]}... | 助手: {assistant_msg[:100]}..."
        metadata = {
            "type": "conversation_turn",
            "user_msg_length": len(user_msg),
            "assistant_msg_length": len(assistant_msg),
            "timestamp": timestamp
        }
        
        memory_id = self._generate_id()
        
        try:
            if self._fts5_available:
                conn.execute(
                    "INSERT INTO memory_fts5 (id, text, timestamp, session_id, metadata) VALUES (?, ?, ?, ?, ?)",
                    (memory_id, summary, timestamp, "current", json.dumps(metadata))
                )
            else:
                conn.execute(
                    "INSERT INTO memory_fallback (id, text, timestamp, session_id, metadata) VALUES (?, ?, ?, ?, ?)",
                    (memory_id, summary, timestamp, "current", json.dumps(metadata))
                )
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to sync conversation to memory: {e}")
            conn.rollback()
    
    def on_session_end(self, messages: list[dict]) -> None:
        """会话结束时提取事实"""
        if not messages:
            return
        
        # 提取关键事实：最后几个消息的摘要
        key_messages = messages[-5:] if len(messages) > 5 else messages
        facts = []
        for msg in key_messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if content:
                facts.append(f"{role}: {content[:200]}")
        
        if facts:
            summary = "会话关键事实:\n" + "\n".join(facts)
            metadata = {
                "type": "session_summary",
                "message_count": len(messages),
                "timestamp": time.time()
            }
            
            conn = self._get_conn()
            memory_id = self._generate_id()
            
            try:
                if self._fts5_available:
                    conn.execute(
                        "INSERT INTO memory_fts5 (id, text, timestamp, session_id, metadata) VALUES (?, ?, ?, ?, ?)",
                        (memory_id, summary, time.time(), "session_end", json.dumps(metadata))
                    )
                else:
                    conn.execute(
                        "INSERT INTO memory_fallback (id, text, timestamp, session_id, metadata) VALUES (?, ?, ?, ?, ?)",
                        (memory_id, summary, time.time(), "session_end", json.dumps(metadata))
                    )
                conn.commit()
            except Exception as e:
                logger.error(f"Failed to save session summary: {e}")
                conn.rollback()
    
    def on_pre_compress(self, messages: list[dict]) -> str:
        """上下文压缩前提取洞察"""
        # 分析消息模式：用户频繁提问的类型、常用工具等
        if not messages:
            return ""
        
        tool_calls = []
        user_questions = []
        
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "user" and content:
                # 简单提取问题关键词（前50个字符）
                user_questions.append(content[:50])
            elif role == "assistant":
                # 检查是否有工具调用
                if "tool_calls" in msg:
                    tool_calls.extend(msg.get("tool_calls", []))
        
        insights = []
        if user_questions:
            insights.append(f"用户关注点: {', '.join(set(user_questions[:3]))}")
        if tool_calls:
            tool_names = [tc.get("name", "") for tc in tool_calls if isinstance(tc, dict)]
            if tool_names:
                insights.append(f"常用工具: {', '.join(set(tool_names))}")
        
        return "; ".join(insights) if insights else ""
    
    def search(self, query: str, limit: int = 10) -> List[dict]:
        """搜索记忆"""
        conn = self._get_conn()
        results = []
        
        try:
            if self._fts5_available:
                # 使用 FTS5 全文搜索
                cursor = conn.execute(
                    "SELECT id, text, timestamp, session_id, metadata, "
                    "snippet(memory_fts5, 0, '<b>', '</b>', '...', 32) as snippet "
                    "FROM memory_fts5 WHERE memory_fts5 MATCH ? "
                    "ORDER BY rank LIMIT ?",
                    (query, limit)
                )
            else:
                # Fallback: 简单的 LIKE 搜索
                cursor = conn.execute(
                    "SELECT id, text, timestamp, session_id, metadata FROM memory_fallback "
                    "WHERE text LIKE ? ORDER BY timestamp DESC LIMIT ?",
                    (f"%{query}%", limit)
                )
            
            for row in cursor.fetchall():
                try:
                    metadata = json.loads(row[4]) if row[4] else {}
                except:
                    metadata = {}
                
                result = {
                    "id": row[0],
                    "text": row[1],
                    "timestamp": row[2],
                    "session_id": row[3],
                    "metadata": metadata
                }
                
                if self._fts5_available and len(row) > 5:
                    result["snippet"] = row[5]
                
                results.append(result)
                
        except Exception as e:
            logger.error(f"Search failed: {e}")
        
        return results
    
    def get_stats(self) -> dict:
        """获取统计数据"""
        conn = self._get_conn()
        stats = {
            "fts5_available": self._fts5_available,
            "initialized": self._initialized,
            "total_memories": 0,
            "by_type": {}
        }
        
        try:
            if self._fts5_available:
                cursor = conn.execute("SELECT COUNT(*) FROM memory_fts5")
            else:
                cursor = conn.execute("SELECT COUNT(*) FROM memory_fallback")
            stats["total_memories"] = cursor.fetchone()[0]
        except:
            pass
        
        return stats
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __del__(self):
        self.close()