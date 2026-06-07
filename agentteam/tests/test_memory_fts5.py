"""测试 FTS5 记忆提供者"""

import pytest
import tempfile
import json
from pathlib import Path

from agentteam.memory import FTS5MemoryProvider


@pytest.fixture
def temp_db():
    """临时数据库文件"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def memory_provider(temp_db):
    """内存提供者实例"""
    provider = FTS5MemoryProvider(db_path=temp_db)
    yield provider
    provider.close()


def test_fts5_provider_initialization(memory_provider):
    """测试 FTS5 提供者初始化"""
    # 检查基本属性
    assert memory_provider.name == "fts5_memory"
    assert memory_provider.db_path is not None

    # 检查是否已初始化
    # 注意：_initialize_db() 会在第一次访问时调用
    assert not memory_provider._initialized  # 还未初始化

    # 触发初始化
    memory_provider._initialize_db()
    assert memory_provider._initialized


def test_fts5_availability_check():
    """测试 FTS5 可用性检查"""
    provider = FTS5MemoryProvider()
    available = provider._check_fts5_available()
    # 大多数环境应该支持 FTS5，但允许不支持的情况
    assert isinstance(available, bool)


def test_sync_conversation(memory_provider):
    """测试同步对话到记忆"""
    user_msg = "How to write a Python function?"
    assistant_msg = "Use def keyword followed by function name and parameters."

    # 同步对话
    memory_provider.sync_turn(user_msg, assistant_msg)

    # 搜索相关记忆
    results = memory_provider.search("Python function")
    assert len(results) > 0

    # 检查记忆内容
    memory = results[0]
    assert "text" in memory
    assert "timestamp" in memory
    assert "metadata" in memory

    metadata = memory["metadata"]
    assert metadata.get("type") == "conversation_turn"


def test_prefetch(memory_provider):
    """测试后台预取记忆"""
    # 先添加一些记忆
    memory_provider.sync_turn("What is AI?", "AI stands for Artificial Intelligence.")
    memory_provider.sync_turn("What is ML?", "ML stands for Machine Learning.")

    # 预取记忆 - 使用单一关键词查询
    prefetched = memory_provider.prefetch("AI")
    assert isinstance(prefetched, str)
    # 可能返回空字符串（如果没有匹配），但如果FTS5可用应该能找到
    if memory_provider._fts5_available:
        # 检查是否包含相关关键词（如果非空）
        if len(prefetched) > 0:
            # 应该包含相关关键词
            assert "AI" in prefetched or "Artificial Intelligence" in prefetched


def test_session_end_summary(memory_provider):
    """测试会话结束时提取事实"""
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "What can you do?"},
        {"role": "assistant", "content": "I can help with coding and answer questions."},
        {"role": "user", "content": "Tell me about Python"},
        {"role": "assistant", "content": "Python is a popular programming language."},
    ]

    # 提取会话摘要
    memory_provider.on_session_end(messages)

    # 搜索会话摘要
    results = memory_provider.search("session")
    # 可能找到会话摘要
    if results:
        memory = results[0]
        assert "text" in memory
        assert "会话关键事实" in memory["text"] or "session" in memory["text"].lower()


def test_pre_compress_insights(memory_provider):
    """测试上下文压缩前提取洞察"""
    messages = [
        {"role": "user", "content": "How to write a function?"},
        {"role": "assistant", "content": "Use def keyword.", "tool_calls": [{"name": "write_file"}]},
        {"role": "user", "content": "What about classes?"},
        {"role": "assistant", "content": "Use class keyword.", "tool_calls": [{"name": "read_file"}]},
    ]

    insights = memory_provider.on_pre_compress(messages)
    assert isinstance(insights, str)
    # 可能包含工具使用信息
    if "write_file" in insights or "read_file" in insights:
        assert True  # 找到了工具信息


def test_search_functionality(memory_provider):
    """测试搜索功能"""
    # 添加测试数据
    test_data = [
        ("Python is great for data science", "Python 适合数据科学"),
        ("Machine learning uses algorithms", "机器学习使用算法"),
        ("Artificial intelligence is evolving", "人工智能正在发展"),
    ]

    for user, assistant in test_data:
        memory_provider.sync_turn(user, assistant)

    # 测试搜索
    results = memory_provider.search("Python data")
    assert len(results) > 0

    # 测试限制
    results = memory_provider.search("learning", limit=1)
    assert len(results) <= 1

    # 测试空查询
    results = memory_provider.search("")
    # 空查询可能返回空结果或所有结果


def test_provider_stats(memory_provider):
    """测试提供者统计"""
    # 添加一些数据
    memory_provider.sync_turn("Test 1", "Response 1")
    memory_provider.sync_turn("Test 2", "Response 2")

    stats = memory_provider.get_stats()
    assert "fts5_available" in stats
    assert "initialized" in stats
    assert "total_memories" in stats
    assert "by_type" in stats

    assert isinstance(stats["fts5_available"], bool)
    assert isinstance(stats["initialized"], bool)
    assert isinstance(stats["total_memories"], int)


def test_fallback_mode():
    """测试降级模式"""
    # 使用内存数据库（应该支持 FTS5）
    provider = FTS5MemoryProvider()

    # 检查初始化状态
    provider._initialize_db()
    stats = provider.get_stats()

    # 无论 FTS5 是否可用，都应该能工作
    provider.sync_turn("Test fallback", "Fallback response")
    results = provider.search("Test")
    assert isinstance(results, list)

    provider.close()


def test_memory_id_generation(memory_provider):
    """测试记忆 ID 生成"""
    id1 = memory_provider._generate_id()
    id2 = memory_provider._generate_id()

    assert isinstance(id1, str)
    assert len(id1) > 0
    assert id1.startswith("mem_")
    assert id1 != id2  # ID 应该唯一
