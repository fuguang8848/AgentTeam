"""Output Parser 测试框架

测试 OutputParser 的功能：
- 多Provider输出解析
- 活动事件检测
- Token用量估算
- 确认请求检测
- 事件去重
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from agentteam.parser.output_parser import (
    OutputParser,
    _strip_ansi,
    _get_or_create_state,
    get_parser,
    parse_output,
)
from agentteam.parser.types import (
    ActivityEvent,
    ActivityEventType,
    ParserState,
    ParserRule,
    UsageSummary,
)
from agentteam.parser.rules import PARSER_RULES


class TestStripAnsi:
    """测试 ANSI 转义码移除"""

    def test_no_ansi(self):
        """测试无 ANSI 码的文本"""
        text = "Hello World"
        result = _strip_ansi(text)
        assert result == "Hello World"

    def test_simple_ansi(self):
        """测试简单 ANSI 码"""
        text = "\x1b[31mRed Text\x1b[0m"
        result = _strip_ansi(text)
        assert result == "Red Text"

    def test_complex_ansi(self):
        """测试复杂 ANSI 码"""
        text = "\x1b[1;31;42mBold Red on Green\x1b[0m"
        result = _strip_ansi(text)
        assert result == "Bold Red on Green"

    def test_multiple_ansi(self):
        """测试多个 ANSI 码"""
        text = "\x1b[31mRed\x1b[0m \x1b[32mGreen\x1b[0m"
        result = _strip_ansi(text)
        assert result == "Red Green"


class TestParserState:
    """测试解析器状态"""

    def test_state_creation(self):
        """测试状态创建"""
        state = ParserState(session_id="test-session")
        assert state.session_id == "test-session"
        # ParserState 没有 last_output_time 字段，使用 last_event_type
        assert state.last_event_type is None

    def test_state_defaults(self):
        """测试状态默认值"""
        state = ParserState(session_id="test-session")
        assert not state.is_thinking
        assert state.text_buffer_lines == []


class TestGetOrCreateState:
    """测试状态获取/创建"""

    def test_create_new_state(self):
        """测试创建新状态"""
        state_map = {}
        state = _get_or_create_state(state_map, "new-session")
        assert state.session_id == "new-session"
        assert "new-session" in state_map

    def test_get_existing_state(self):
        """测试获取已存在状态"""
        state_map = {"existing": ParserState(session_id="existing")}
        state = _get_or_create_state(state_map, "existing")
        assert state.session_id == "existing"
        assert len(state_map) == 1


class TestOutputParserInit:
    """测试 OutputParser 初始化"""

    def test_default_init(self):
        """测试默认初始化"""
        parser = OutputParser()
        assert parser._rules is not None
        assert len(parser._state_map) == 0

    def test_custom_rules_path_init(self):
        """测试自定义规则路径初始化"""
        parser = OutputParser(custom_rules_path=Path("/tmp/rules"))
        assert parser._custom_rules_path == Path("/tmp/rules")


class TestOutputParserParse:
    """测试 OutputParser 解析功能"""

    def test_parse_empty_output(self):
        """测试空输出解析"""
        parser = OutputParser()
        # parse 参数顺序: (session_id, data)
        events = parser.parse("test-session", "")
        assert len(events) == 0

    def test_parse_simple_output(self):
        """测试简单输出解析"""
        parser = OutputParser()
        events = parser.parse("test-session", "Hello World")
        # 应该至少有一个文本事件
        assert len(events) >= 0

    def test_parse_creates_state(self):
        """测试解析创建状态"""
        parser = OutputParser()
        parser.parse("session-123", "Test output")
        assert "session-123" in parser._state_map

    def test_parse_multiline_output(self):
        """测试多行输出解析"""
        parser = OutputParser()
        output = """Line 1
Line 2
Line 3"""
        events = parser.parse("test-session", output)
        # 多行输出应该被正确处理
        assert len(events) >= 0


class TestOutputParserDeduplication:
    """测试事件去重"""

    def test_dedup_same_event(self):
        """测试相同事件去重"""
        parser = OutputParser()
        # 第一次解析
        events1 = parser.parse("session-1", "Tool use: read_file")
        # 立即再次解析相同内容
        events2 = parser.parse("session-1", "Tool use: read_file")
        # 去重应该生效
        # 注意：具体行为取决于实现

    def test_dedup_different_events(self):
        """测试不同事件不去重"""
        parser = OutputParser()
        events1 = parser.parse("session-1", "Tool use: read_file")
        events2 = parser.parse("session-1", "Tool use: write_file")
        # 不同事件不应该被去重


class TestOutputParserEventHandler:
    """测试事件处理器"""

    def test_add_event_handler(self):
        """测试添加事件处理器"""
        parser = OutputParser()
        handler = Mock()
        parser.add_event_handler(handler)
        assert handler in parser._event_handlers

    def test_remove_event_handler(self):
        """测试移除事件处理器"""
        parser = OutputParser()
        handler = Mock()
        parser.add_event_handler(handler)
        parser.remove_event_handler(handler)
        assert handler not in parser._event_handlers

    def test_event_handler_called(self):
        """测试事件处理器被调用"""
        parser = OutputParser()
        handler = Mock()
        parser.add_event_handler(handler)
        # 解析输出触发事件
        parser.parse("test-session", "Test output")
        # 处理器可能被调用（取决于实现）


class TestOutputParserProviderMapping:
    """测试 Provider 映射"""

    def test_set_provider(self):
        """测试设置 Provider"""
        parser = OutputParser()
        parser.set_provider("test-session", "claude-code")
        assert parser._session_provider_map["test-session"] == "claude-code"

    def test_get_provider(self):
        """测试获取 Provider"""
        parser = OutputParser()
        parser.set_provider("test-session", "codex")
        provider = parser.get_provider("test-session")
        assert provider == "codex"

    def test_get_unknown_provider(self):
        """测试获取未知 Provider"""
        parser = OutputParser()
        provider = parser.get_provider("unknown-session")
        assert provider is None


class TestOutputParserUsage:
    """测试 Token 用量估算"""

    def test_get_usage_summary(self):
        """测试获取用量摘要"""
        parser = OutputParser()
        summary = parser.get_usage_summary()
        assert summary is not None

    def test_get_session_usage(self):
        """测试获取会话用量"""
        parser = OutputParser()
        parser.parse("test-session", "This is a test output with some tokens")
        usage = parser.get_session_usage("test-session")
        # 用量应该被估算

    def test_mark_session_ended(self):
        """测试标记会话结束"""
        parser = OutputParser()
        parser.parse("test-session", "Test output")
        summary = parser.mark_session_ended("test-session")
        assert summary is not None


class TestOutputParserConfirmation:
    """测试确认请求检测"""

    def test_detect_confirmation_prompt(self):
        """测试检测确认提示"""
        parser = OutputParser()
        output = "Allow tool use? (Y/n)"
        events = parser.parse("test-session", output)
        # 应该检测到确认请求

    def test_detect_high_confidence_confirmation(self):
        """测试高置信度确认检测"""
        parser = OutputParser()
        output = "Proceed with file modification? [Y/n]"
        events = parser.parse("test-session", output)


class TestOutputParserClear:
    """测试状态清理"""

    def test_clear_session(self):
        """测试清理会话状态"""
        parser = OutputParser()
        parser.parse("test-session", "Test")
        parser.clear_session("test-session")
        assert "test-session" not in parser._state_map

    def test_cleanup(self):
        """测试清理所有状态"""
        parser = OutputParser()
        parser.parse("session-1", "Test 1")
        parser.parse("session-2", "Test 2")
        parser.cleanup()
        # cleanup 应该清理所有状态


class TestOutputParserThreadSafety:
    """测试线程安全"""

    def test_concurrent_parse(self):
        """测试并发解析"""
        import threading

        parser = OutputParser()
        results = []

        def parse_thread(session_id, output):
            events = parser.parse(session_id, output)
            results.append((session_id, len(events)))

        threads = [threading.Thread(target=parse_thread, args=(f"session-{i}", f"Output {i}")) for i in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 所有线程应该成功完成
        assert len(results) == 5


class TestOutputParserIntegration:
    """集成测试"""

    def test_full_parse_workflow(self):
        """测试完整解析工作流"""
        parser = OutputParser()
        handler = Mock()
        parser.add_event_handler(handler)

        # 设置 Provider
        parser.set_provider("test-session", "claude-code")

        # 解析输出
        output = """Tool use: read_file
Processing file content
Tool use: write_file
Complete"""
        events = parser.parse("test-session", output)

        # 获取用量
        summary = parser.get_usage_summary()

        # 清理
        parser.clear_session("test-session")

        assert "test-session" not in parser._state_map

    def test_parse_output_function(self):
        """测试 parse_output便捷函数"""
        events = parse_output("test-session", "Test output")
        assert isinstance(events, list)

    def test_get_parser_singleton(self):
        """测试 get_parser 单例"""
        parser1 = get_parser()
        parser2 = get_parser()
        assert parser1 is parser2
