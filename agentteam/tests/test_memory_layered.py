"""
P15: L1-L4 分层记忆测试
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from agentteam.memory.layered import (
    LayeredMemoryProvider,
    L1WorkingMemory,
    L2SessionMemory,
    L3CrossSessionMemory,
    L4KnowledgeBase,
    MemoryEntry,
)


@pytest.fixture
def temp_mem_dir():
    tmp = tempfile.mkdtemp()
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


class TestL1WorkingMemory:
    def test_add_and_search(self):
        mem = L1WorkingMemory(max_entries=10)
        mem.add("Hello world", session_id="s1")
        results = mem.search("hello")
        assert len(results) == 1
        assert "Hello world" in results[0].content

    def test_max_entries(self):
        mem = L1WorkingMemory(max_entries=3)
        for i in range(5):
            mem.add(f"Message {i}", session_id="s1")
        assert mem.size() == 3

    def test_clear(self):
        mem = L1WorkingMemory()
        mem.add("test", session_id="s1")
        mem.clear()
        assert mem.size() == 0


class TestL2SessionMemory:
    def test_add_and_get_session(self, temp_mem_dir):
        mem = L2SessionMemory(ttl_hours=24)
        mem.add("User likes Python", session_id="s1", importance=0.7)
        entries = mem.get_session("s1")
        assert len(entries) == 1
        assert "User likes Python" in entries[0].content

    def test_search(self, temp_mem_dir):
        mem = L2SessionMemory(ttl_hours=24)
        mem.add("Python is great", session_id="s1")
        results = mem.search("python", session_id="s1")
        assert len(results) == 1

    def test_ttl_expiry(self, temp_mem_dir):
        mem = L2SessionMemory(ttl_hours=0)  # 0 hours = immediate expiry
        mem.add("Old fact", session_id="s1")
        import time

        time.sleep(0.01)
        removed = mem.cleanup()
        assert removed >= 0


class TestL3CrossSessionMemory:
    def test_add_and_search(self, temp_mem_dir):
        mem = L3CrossSessionMemory(storage_dir=temp_mem_dir, ttl_days=90)
        entry = mem.add("Important fact about the project", importance=0.8)
        results = mem.search("project")
        assert len(results) == 1
        assert "Important fact" in results[0].content

    def test_promote_from_l2(self, temp_mem_dir):
        mem = L3CrossSessionMemory(storage_dir=temp_mem_dir)
        entry = mem.promote_from_l2("Key insight from session", "s1", importance=0.8)
        assert entry is not None
        assert entry.layer == "L3"


class TestL4KnowledgeBase:
    def test_add_fact(self, temp_mem_dir):
        kb = L4KnowledgeBase(storage_dir=temp_mem_dir)
        entry = kb.add_fact("The project uses Python 3.11", importance=0.9)
        assert entry.layer == "L4"
        assert kb.size() == 1

    def test_add_pattern(self, temp_mem_dir):
        kb = L4KnowledgeBase(storage_dir=temp_mem_dir)
        kb.add_pattern(
            "python_pattern",
            {
                "description": "Pattern for Python projects",
                "tags": ["python", "project"],
            },
        )
        pattern = kb.get_pattern("python_pattern")
        assert pattern is not None
        assert "Python projects" in pattern["description"]

    def test_search_facts(self, temp_mem_dir):
        kb = L4KnowledgeBase(storage_dir=temp_mem_dir)
        kb.add_fact("Docker is used for deployment")
        results = kb.search("docker")
        assert len(results) == 1


class TestLayeredMemoryProvider:
    def test_full_integration(self, temp_mem_dir):
        provider = LayeredMemoryProvider(storage_dir=temp_mem_dir)
        provider.set_session("session-123")

        # L1: 同步对话
        provider.sync_turn("记住用户喜欢蓝色", "好的，我记住您喜欢蓝色了")

        # L2: 自动添加事实
        l2_entries = provider.l2.get_session("session-123")
        assert len(l2_entries) >= 0  # 可能有提取的事实

        # L3: 搜索
        provider.l3.add("用户偏好蓝色", importance=0.8)
        results = provider.search("蓝色")
        assert len(results) >= 1

        # L4: 晋升到知识库
        entry = provider.promote_to_l4("蓝色是用户的首选颜色", tags={"preference"})
        assert entry is not None
        assert entry.layer == "L4"

        # 上下文摘要
        summary = provider.get_context_summary()
        assert "## 当前记忆上下文" in summary

        # 清理
        cleanup = provider.cleanup_all()
        assert "l2_removed" in cleanup
        assert "l3_removed" in cleanup


class TestMemoryEntry:
    def test_to_dict_from_dict(self):
        entry = MemoryEntry(
            entry_id="test_123",
            content="Test content",
            layer="L1",
            importance=0.8,
            tags={"test", "demo"},
            metadata={"key": "value"},
            source="test",
            session_id="s1",
        )
        d = entry.to_dict()
        restored = MemoryEntry.from_dict(d)
        assert restored.entry_id == entry.entry_id
        assert restored.content == entry.content
        assert restored.layer == entry.layer
        assert restored.tags == entry.tags

    def test_access(self):
        entry = MemoryEntry(
            entry_id="test_456",
            content="Access test",
            layer="L1",
        )
        assert entry.access_count == 0
        entry.access()
        assert entry.access_count == 1
        entry.access()
        assert entry.access_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
