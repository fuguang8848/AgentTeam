"""
L1-L4 分层记忆系统 — P15 记忆增强实现

层次结构：
- L1 (Working Memory): 当前对话上下文，瞬间记忆
- L2 (Session Memory): 当前会话的事实，短中期
- L3 (Cross-Session Memory): 跨会话重要事实，长期
- L4 (Knowledge Base): 语义知识，学习到的模式，最长

每个层级有不同的 TTL 和检索策略。
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import json
import uuid
import logging
import threading

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """记忆条目"""
    entry_id: str
    content: str
    layer: str  # L1, L2, L3, L4
    importance: float = 0.5  # 0.0 - 1.0
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = ""  # conversation, extracted, learned
    session_id: str = ""

    def access(self) -> None:
        """记录访问"""
        self.last_accessed = datetime.now()
        self.access_count += 1

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "content": self.content,
            "layer": self.layer,
            "importance": self.importance,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
            "tags": list(self.tags),
            "metadata": self.metadata,
            "source": self.source,
            "session_id": self.session_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MemoryEntry":
        d = d.copy()
        for key in ["created_at", "last_accessed"]:
            if key in d and isinstance(d[key], str):
                d[key] = datetime.fromisoformat(d[key].replace('Z', '+00:00'))
        if "tags" in d and isinstance(d["tags"], list):
            d["tags"] = set(d["tags"])
        return cls(**d)


class L1WorkingMemory:
    """L1 工作记忆 - 当前对话上下文"""

    def __init__(self, max_entries: int = 50):
        self.max_entries = max_entries
        self._entries: List[MemoryEntry] = []
        self._lock = threading.Lock()

    def add(self, content: str, importance: float = 0.5, tags: Set[str] = None,
            metadata: Dict[str, Any] = None, session_id: str = "") -> MemoryEntry:
        """添加记忆"""
        entry = MemoryEntry(
            entry_id=f"l1_{uuid.uuid4().hex[:8]}",
            content=content,
            layer="L1",
            importance=importance,
            tags=tags or set(),
            metadata=metadata or {},
            source="conversation",
            session_id=session_id,
        )
        with self._lock:
            self._entries.append(entry)
            # 保持上限
            if len(self._entries) > self.max_entries:
                # 移除最旧的非重要条目
                self._entries.sort(key=lambda e: (e.importance, e.created_at))
                self._entries = self._entries[-self.max_entries:]
        return entry

    def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """搜索记忆"""
        query_lower = query.lower()
        results = []
        with self._lock:
            for entry in reversed(self._entries):
                entry.access()
                if query_lower in entry.content.lower():
                    results.append(entry)
                    if len(results) >= limit:
                        break
        return results

    def get_recent(self, limit: int = 10) -> List[MemoryEntry]:
        """获取最近记忆"""
        with self._lock:
            return list(reversed(self._entries[-limit:]))

    def clear(self) -> None:
        """清空工作记忆"""
        with self._lock:
            self._entries.clear()

    def size(self) -> int:
        return len(self._entries)

    def to_list(self) -> List[MemoryEntry]:
        with self._lock:
            return list(self._entries)


class L2SessionMemory:
    """L2 会话记忆 - 当前会话的事实"""

    def __init__(self, ttl_hours: int = 24):
        self.ttl = timedelta(hours=ttl_hours)
        self._entries: Dict[str, MemoryEntry] = {}  # session_id -> entries
        self._lock = threading.Lock()

    def add(self, content: str, session_id: str, importance: float = 0.5,
            tags: Set[str] = None, metadata: Dict[str, Any] = None) -> MemoryEntry:
        """添加会话记忆"""
        entry = MemoryEntry(
            entry_id=f"l2_{uuid.uuid4().hex[:8]}",
            content=content,
            layer="L2",
            importance=importance,
            tags=tags or set(),
            metadata=metadata or {},
            source="conversation",
            session_id=session_id,
        )
        with self._lock:
            if session_id not in self._entries:
                self._entries[session_id] = []
            self._entries[session_id].append(entry)
        return entry

    def get_session(self, session_id: str) -> List[MemoryEntry]:
        """获取会话的所有记忆"""
        with self._lock:
            entries = self._entries.get(session_id, [])
            # 过滤过期
            cutoff = datetime.now() - self.ttl
            return [e for e in entries if e.created_at > cutoff]

    def search(self, query: str, session_id: str = None, limit: int = 20) -> List[MemoryEntry]:
        """搜索会话记忆"""
        query_lower = query.lower()
        results = []
        cutoff = datetime.now() - self.ttl

        with self._lock:
            sessions = [session_id] if session_id else list(self._entries.keys())
            for sid in sessions:
                for entry in self._entries.get(sid, []):
                    if entry.created_at > cutoff:
                        entry.access()
                        if query_lower in entry.content.lower():
                            results.append(entry)
                            if len(results) >= limit:
                                return results
        return results

    def extract_facts(self, session_id: str) -> List[str]:
        """从会话中提取事实（用于会话结束）"""
        entries = self.get_session(session_id)
        return [e.content for e in entries if e.importance >= 0.6]

    def cleanup(self) -> int:
        """清理过期记忆"""
        cutoff = datetime.now() - self.ttl
        removed = 0
        with self._lock:
            for sid in list(self._entries.keys()):
                before = len(self._entries[sid])
                self._entries[sid] = [e for e in self._entries[sid] if e.created_at > cutoff]
                removed += before - len(self._entries[sid])
                if not self._entries[sid]:
                    del self._entries[sid]
        return removed

    def size(self, session_id: str = None) -> int:
        with self._lock:
            if session_id:
                return len(self._entries.get(session_id, []))
            return sum(len(v) for v in self._entries.values())


class L3CrossSessionMemory:
    """L3 跨会话记忆 - 跨会话重要事实"""

    def __init__(self, storage_dir: str = None, ttl_days: int = 90):
        self.storage_dir = Path(storage_dir or "~/.openclaw/workspace/memory/l3").expanduser()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(days=ttl_days)
        self._entries: Dict[str, MemoryEntry] = {}
        self._lock = threading.Lock()
        self._load_from_disk()

    def _entry_file(self, entry_id: str) -> Path:
        return self.storage_dir / f"{entry_id}.json"

    def _load_from_disk(self) -> None:
        """从磁盘加载"""
        try:
            for f in self.storage_dir.glob("*.json"):
                try:
                    with open(f, 'r', encoding='utf-8') as fh:
                        d = json.load(fh)
                        entry = MemoryEntry.from_dict(d)
                        self._entries[entry.entry_id] = entry
                except Exception as e:
                    logger.warning(f"Failed to load L3 entry {f}: {e}")
            logger.info(f"Loaded {len(self._entries)} L3 entries")
        except Exception as e:
            logger.error(f"Error loading L3 memory: {e}")

    def _save_entry(self, entry: MemoryEntry) -> None:
        """保存到磁盘"""
        path = self._entry_file(entry.entry_id)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(entry.to_dict(), f, ensure_ascii=False, indent=2)

    def add(self, content: str, importance: float = 0.6, tags: Set[str] = None,
            metadata: Dict[str, Any] = None, session_id: str = "") -> MemoryEntry:
        """添加跨会话记忆"""
        entry = MemoryEntry(
            entry_id=f"l3_{uuid.uuid4().hex[:8]}",
            content=content,
            layer="L3",
            importance=importance,
            tags=tags or set(),
            metadata=metadata or {},
            source="extracted",
            session_id=session_id,
        )
        with self._lock:
            self._entries[entry.entry_id] = entry
            self._save_entry(entry)
        return entry

    def search(self, query: str, limit: int = 20) -> List[MemoryEntry]:
        """搜索跨会话记忆"""
        query_lower = query.lower()
        results = []
        cutoff = datetime.now() - self.ttl

        with self._lock:
            for entry in self._entries.values():
                if entry.created_at < cutoff:
                    continue
                entry.access()
                if query_lower in entry.content.lower():
                    results.append(entry)
                elif any(query_lower in tag.lower() for tag in entry.tags):
                    results.append(entry)
                if len(results) >= limit:
                    break

        # 按重要性和访问次数排序
        results.sort(key=lambda e: (e.importance, e.access_count), reverse=True)
        return results[:limit]

    def promote_from_l2(self, content: str, session_id: str,
                         importance: float = 0.7, tags: Set[str] = None) -> Optional[MemoryEntry]:
        """从 L2 晋升重要记忆"""
        # 检查是否已存在相似记忆
        existing = self.search(content, limit=5)
        for ex in existing:
            if content in ex.content or ex.content in content:
                # 更新已有条目的访问
                ex.access()
                return ex

        return self.add(content, importance=importance, tags=tags,
                       metadata={"promoted_from": session_id}, session_id=session_id)

    def cleanup(self) -> int:
        """清理过期记忆"""
        cutoff = datetime.now() - self.ttl
        removed = 0
        with self._lock:
            expired = [eid for eid, e in self._entries.items() if e.created_at < cutoff]
            for eid in expired:
                path = self._entry_file(eid)
                if path.exists():
                    path.unlink()
                del self._entries[eid]
                removed += 1
        return removed

    def size(self) -> int:
        return len(self._entries)


class L4KnowledgeBase:
    """L4 知识库 - 语义知识和学习到的模式"""

    def __init__(self, storage_dir: str = None):
        self.storage_dir = Path(storage_dir or "~/.openclaw/workspace/memory/l4").expanduser()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._patterns: Dict[str, Dict[str, Any]] = {}
        self._facts: Dict[str, MemoryEntry] = {}
        self._lock = threading.Lock()
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """从磁盘加载"""
        # 加载模式
        patterns_file = self.storage_dir / "patterns.json"
        if patterns_file.exists():
            try:
                with open(patterns_file, 'r', encoding='utf-8') as f:
                    self._patterns = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load patterns: {e}")

        # 加载事实
        facts_dir = self.storage_dir / "facts"
        if facts_dir.exists():
            for f in facts_dir.glob("*.json"):
                try:
                    with open(f, 'r', encoding='utf-8') as fh:
                        d = json.load(fh)
                        entry = MemoryEntry.from_dict(d)
                        self._facts[entry.entry_id] = entry
                except Exception as e:
                    logger.warning(f"Failed to load L4 fact {f}: {e}")

        logger.info(f"Loaded {len(self._patterns)} patterns and {len(self._facts)} facts in L4")

    def _save_patterns(self) -> None:
        path = self.storage_dir / "patterns.json"
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self._patterns, f, ensure_ascii=False, indent=2)

    def add_pattern(self, name: str, pattern: Dict[str, Any]) -> None:
        """添加学习到的模式"""
        with self._lock:
            self._patterns[name] = {
                **pattern,
                "learned_at": datetime.now().isoformat(),
                "id": name,
            }
            self._save_patterns()

    def get_pattern(self, name: str) -> Optional[Dict[str, Any]]:
        return self._patterns.get(name)

    def search_patterns(self, query: str) -> List[Dict[str, Any]]:
        """搜索模式"""
        query_lower = query.lower()
        results = []
        for name, pattern in self._patterns.items():
            if query_lower in name.lower():
                results.append(pattern)
            elif query_lower in pattern.get("description", "").lower():
                results.append(pattern)
            elif any(query_lower in t.lower() for t in pattern.get("tags", [])):
                results.append(pattern)
        return results

    def add_fact(self, content: str, importance: float = 0.8,
                 tags: Set[str] = None, metadata: Dict[str, Any] = None) -> MemoryEntry:
        """添加知识库事实"""
        entry = MemoryEntry(
            entry_id=f"l4_{uuid.uuid4().hex[:8]}",
            content=content,
            layer="L4",
            importance=importance,
            tags=tags or set(),
            metadata=metadata or {},
            source="learned",
        )
        with self._lock:
            self._facts[entry.entry_id] = entry
            # 保存到磁盘
            facts_dir = self.storage_dir / "facts"
            facts_dir.mkdir(exist_ok=True)
            path = facts_dir / f"{entry.entry_id}.json"
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(entry.to_dict(), f, ensure_ascii=False, indent=2)
        return entry

    def search(self, query: str, limit: int = 20) -> List[MemoryEntry]:
        """搜索知识库"""
        query_lower = query.lower()
        results = []

        with self._lock:
            for entry in self._facts.values():
                entry.access()
                if query_lower in entry.content.lower():
                    results.append(entry)
                elif any(query_lower in tag.lower() for tag in entry.tags):
                    results.append(entry)
                if len(results) >= limit:
                    break

        results.sort(key=lambda e: (e.importance, e.access_count), reverse=True)
        return results[:limit]

    def size(self) -> int:
        return len(self._facts) + len(self._patterns)


class LayeredMemoryProvider:
    """
    L1-L4 分层记忆 Provider

    整合 L1-L4 四个层级的记忆系统，
    提供统一的检索接口。
    """

    def __init__(self, storage_dir: str = None):
        storage_dir = storage_dir or "~/.openclaw/workspace/memory"
        storage_path = Path(storage_dir).expanduser()

        self.l1 = L1WorkingMemory(max_entries=50)
        self.l2 = L2SessionMemory(ttl_hours=24)
        self.l3 = L3CrossSessionMemory(storage_dir=str(storage_path / "l3"), ttl_days=90)
        self.l4 = L4KnowledgeBase(storage_dir=str(storage_path / "l4"))

        self._current_session_id: str = ""

    @property
    def name(self) -> str:
        return "layered_memory"

    def set_session(self, session_id: str) -> None:
        """设置当前会话 ID"""
        self._current_session_id = session_id

    def prefetch(self, query: str) -> str:
        """后台预取记忆"""
        results = self.search(query, limit=5)
        if not results:
            return ""
        return "\n".join(f"- {e.content}" for e in results)

    def sync_turn(self, user_msg: str, assistant_msg: str) -> None:
        """同步对话到记忆"""
        session_id = self._current_session_id

        # 用户消息 -> L1
        self.l1.add(user_msg, importance=0.5, session_id=session_id)

        # 助手回复 -> L1
        self.l1.add(assistant_msg, importance=0.5, session_id=session_id)

        # 提取可能的事实 -> L2
        potential_facts = self._extract_facts(user_msg)
        for fact in potential_facts:
            self.l2.add(fact, session_id=session_id, importance=0.6,
                       tags={"extracted"}, metadata={"role": "user"})

        potential_facts = self._extract_facts(assistant_msg)
        for fact in potential_facts:
            self.l2.add(fact, session_id=session_id, importance=0.6,
                       tags={"extracted"}, metadata={"role": "assistant"})

    def _extract_facts(self, text: str) -> List[str]:
        """简单的事实提取（基于规则的启发式方法）"""
        facts = []
        lines = text.split('\n')

        # 提取包含数字/日期的行
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 包含具体信息的行
            if any(c.isdigit() for c in line) and len(line) > 10 and len(line) < 200:
                facts.append(line)
            # 以 "记住" 或 "用户说" 开头的行
            if line.startswith("记住") or line.startswith("用户说"):
                facts.append(line)

        return facts[:3]  # 限制每条消息提取的事实数量

    def on_session_end(self, messages: list[dict]) -> None:
        """会话结束时：将重要事实晋升到 L3"""
        session_id = self._current_session_id
        if not session_id:
            return

        # 从 L2 获取会话中的重要事实
        l2_facts = self.l2.extract_facts(session_id)

        # 晋升到 L3
        promoted_count = 0
        for fact in l2_facts:
            if len(fact) > 5:  # 过滤太短的事实
                self.l3.promote_from_l2(fact, session_id, importance=0.7)
                promoted_count += 1

        if promoted_count > 0:
            logger.info(f"Promoted {promoted_count} facts from L2 to L3 for session {session_id}")

    def on_pre_compress(self, messages: list[dict]) -> str:
        """上下文压缩前：提取关键洞察"""
        insights = []

        # 从最近消息中提取关键信息
        recent = messages[-10:] if len(messages) > 10 else messages
        for msg in recent:
            content = msg.get("content", "")
            if content:
                facts = self._extract_facts(content)
                insights.extend(facts)

        # 从 L3 获取相关记忆
        if messages:
            last_msg = messages[-1].get("content", "")[:100]
            l3_related = self.l3.search(last_msg, limit=3)
            for entry in l3_related:
                insights.append(entry.content)

        return "\n".join(insights[:10]) if insights else ""

    def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """跨所有层级搜索"""
        all_results: Dict[str, MemoryEntry] = {}

        # L1: 工作记忆优先（最新鲜）
        for entry in self.l1.search(query, limit=5):
            all_results[entry.entry_id] = entry

        # L2: 会话记忆
        for entry in self.l2.search(query, session_id=self._current_session_id, limit=5):
            all_results[entry.entry_id] = entry

        # L3: 跨会话记忆
        for entry in self.l3.search(query, limit=5):
            all_results[entry.entry_id] = entry

        # L4: 知识库
        for entry in self.l4.search(query, limit=3):
            all_results[entry.entry_id] = entry

        # 合并并排序：L1 > L2 > L3 > L4，然后按重要性
        layer_order = {"L1": 0, "L2": 1, "L3": 2, "L4": 3}
        results = list(all_results.values())
        results.sort(key=lambda e: (layer_order.get(e.layer, 99), -e.importance, -e.access_count))

        return results[:limit]

    def promote_to_l4(self, content: str, pattern_name: str = None,
                      tags: Set[str] = None) -> Optional[MemoryEntry]:
        """将重要内容晋升到 L4 知识库"""
        # 检查是否值得晋升（高频出现或高重要性）
        existing = self.l3.search(content, limit=3)
        if existing:
            # 已有类似内容，更新高重要性
            entry = existing[0]
            if entry.importance < 0.9:
                entry.importance = min(0.95, entry.importance + 0.1)
            return self.l4.add_fact(content, importance=0.9, tags=tags,
                                   metadata={"derived_from": entry.entry_id})

        return self.l4.add_fact(content, importance=0.8, tags=tags)

    def get_context_summary(self, max_entries: int = 10) -> str:
        """获取当前上下文摘要"""
        parts = ["## 当前记忆上下文"]

        # L1 最近
        l1_recent = self.l1.get_recent(limit=5)
        if l1_recent:
            parts.append("### L1 最近对话")
            for e in l1_recent:
                parts.append(f"- {e.content[:100]}")

        # L2 会话事实
        if self._current_session_id:
            l2_facts = self.l2.get_session(self._current_session_id)
            if l2_facts:
                parts.append("### L2 会话事实")
                for e in l2_facts[-5:]:
                    parts.append(f"- {e.content[:100]}")

        return "\n".join(parts)

    def cleanup_all(self) -> Dict[str, int]:
        """清理所有层级的过期数据"""
        results = {}
        results["l2_removed"] = self.l2.cleanup()
        results["l3_removed"] = self.l3.cleanup()
        return results
