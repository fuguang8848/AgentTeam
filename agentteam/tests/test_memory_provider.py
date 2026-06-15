"""P15: 记忆增强 - MemoryProvider 抽象基类测试

测试覆盖:
- MemoryProvider 抽象基类接口
- Provider 注册和获取
- 预取、同步、会话结束等方法
"""

import pytest
from abc import ABC

from agentteam.memory import MemoryProvider, FTS5MemoryProvider


class TestMemoryProviderAbstract:
    """测试 MemoryProvider 抽象基类"""

    def test_memory_provider_is_abc(self):
        """验证 MemoryProvider 是 ABC"""
        assert issubclass(MemoryProvider, ABC)

    def test_name_property_is_abstract(self):
        """验证 name 属性是抽象的"""
        with pytest.raises(TypeError):
            # 直接实例化应该失败，因为 name 是抽象属性
            MemoryProvider()

    def test_abstract_methods_exist(self):
        """验证所有抽象方法都存在"""
        # 检查 prefetch 是抽象的
        assert hasattr(MemoryProvider, "prefetch")
        # 检查 sync_turn 是抽象的
        assert hasattr(MemoryProvider, "sync_turn")
        # 检查 on_session_end 是抽象的
        assert hasattr(MemoryProvider, "on_session_end")
        # 检查 on_pre_compress 是抽象的
        assert hasattr(MemoryProvider, "on_pre_compress")


class DummyMemoryProvider(MemoryProvider):
    """用于测试的具体实现"""

    def __init__(self):
        self._name = "dummy_memory"

    @property
    def name(self) -> str:
        return self._name

    def prefetch(self, query: str) -> str:
        return f"prefetched: {query}"

    def sync_turn(self, user_msg: str, assistant_msg: str) -> None:
        self.last_sync = (user_msg, assistant_msg)

    def on_session_end(self, messages: list) -> None:
        return {"summary": f"session with {len(messages)} messages"}

    def on_pre_compress(self, messages: list) -> str:
        return f"insights from {len(messages)} messages"


class TestMemoryProviderConcrete:
    """测试具体实现"""

    def test_concrete_provider_has_name(self):
        """测试具体实现的 name 属性"""
        provider = DummyMemoryProvider()
        assert provider.name == "dummy_memory"

    def test_prefetch_returns_text(self):
        """测试 prefetch 返回记忆文本"""
        provider = DummyMemoryProvider()
        result = provider.prefetch("test query")
        assert isinstance(result, str)
        assert "test query" in result

    def test_sync_turn_accepts_two_strings(self):
        """测试 sync_turn 接受两个字符串参数"""
        provider = DummyMemoryProvider()
        provider.sync_turn("user message", "assistant reply")
        assert provider.last_sync == ("user message", "assistant reply")

    def test_on_session_end_returns_dict(self):
        """测试 on_session_end 返回字典"""
        provider = DummyMemoryProvider()
        messages = [{"role": "user", "content": "hello"}]
        result = provider.on_session_end(messages)
        assert isinstance(result, dict)
        assert "summary" in result

    def test_on_pre_compress_returns_string(self):
        """测试 on_pre_compress 返回字符串"""
        provider = DummyMemoryProvider()
        messages = [{"role": "user", "content": "hello"}]
        result = provider.on_pre_compress(messages)
        assert isinstance(result, str)

    def test_search_method_exists(self):
        """测试 search 方法存在"""
        provider = DummyMemoryProvider()
        assert hasattr(provider, "search")
        result = provider.search("test")
        assert isinstance(result, list)


class TestProviderRegistration:
    """测试 Provider 注册和获取"""

    def test_fts5_provider_name(self):
        """测试 FTS5 Provider 名称"""
        provider = FTS5MemoryProvider()
        assert provider.name == "fts5_memory"

    def test_fts5_provider_initialized(self):
        """测试 FTS5 Provider 可初始化"""
        provider = FTS5MemoryProvider()
        # 触发初始化
        available = provider._check_fts5_available()
        assert isinstance(available, bool)

    def test_fts5_provider_has_all_required_methods(self):
        """测试 FTS5 Provider 有所有必需方法"""
        provider = FTS5MemoryProvider()
        assert hasattr(provider, "name")
        assert hasattr(provider, "prefetch")
        assert hasattr(provider, "sync_turn")
        assert hasattr(provider, "on_session_end")
        assert hasattr(provider, "on_pre_compress")
        assert hasattr(provider, "search")

    def test_fts5_provider_prefetch_returns_string(self):
        """测试 FTS5 Provider prefetch 返回字符串"""
        provider = FTS5MemoryProvider()
        result = provider.prefetch("test")
        assert isinstance(result, str)

    def test_fts5_provider_sync_turn(self):
        """测试 FTS5 Provider sync_turn"""
        provider = FTS5MemoryProvider()
        provider.sync_turn("Hello", "Hi there!")
        # 不应抛出异常
        assert True

    def test_fts5_provider_on_session_end(self):
        """测试 FTS5 Provider on_session_end"""
        provider = FTS5MemoryProvider()
        messages = [{"role": "user", "content": "Test message"}, {"role": "assistant", "content": "Test response"}]
        result = provider.on_session_end(messages)
        # on_session_end 可能返回 None（基类默认实现）或 dict
        assert result is None or isinstance(result, dict)

    def test_fts5_provider_on_pre_compress(self):
        """测试 FTS5 Provider on_pre_compress"""
        provider = FTS5MemoryProvider()
        messages = [
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a language."},
        ]
        result = provider.on_pre_compress(messages)
        assert isinstance(result, str)


class TestMemoryProviderInheritance:
    """测试 Provider 继承关系"""

    def test_fts5_is_memory_provider(self):
        """验证 FTS5MemoryProvider 继承自 MemoryProvider"""
        assert issubclass(FTS5MemoryProvider, MemoryProvider)

    def test_dummy_is_memory_provider(self):
        """验证 DummyMemoryProvider 继承自 MemoryProvider"""
        assert issubclass(DummyMemoryProvider, MemoryProvider)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
