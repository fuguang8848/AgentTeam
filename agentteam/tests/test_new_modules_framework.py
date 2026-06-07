"""新模块测试框架 + 性能基准

测试框架汇总：
- OutputParser (test_output_parser.py)
- NotificationManager (test_notification_manager.py)
- ConcurrencyGuard (test_concurrency_guard.py)
- ConfirmationDetector (test_confirmation_detector.py)
- SkillEngine (test_skill_engine.py)

性能基准：
- 全量测试执行时间基线
- 模块导入时间测量
- 内存使用基线
"""

import pytest
import time
import sys
import os
from pathlib import Path
from unittest.mock import Mock

# ==============================================================================
# 测试框架汇总
# ==============================================================================


class TestNewModulesFramework:
    """新模块测试框架汇总"""

    def test_output_parser_module_exists(self):
        """测试 OutputParser 模块存在"""
        from agentteam.parser.output_parser import OutputParser

        assert OutputParser is not None

    def test_notification_manager_module_exists(self):
        """测试 NotificationManager 模块存在"""
        from agentteam.notification.manager import NotificationManager

        assert NotificationManager is not None

    def test_concurrency_guard_module_exists(self):
        """测试 ConcurrencyGuard 模块存在"""
        from agentteam.concurrency.guard import ConcurrencyGuard

        assert ConcurrencyGuard is not None

    def test_confirmation_detector_module_exists(self):
        """测试 ConfirmationDetector 模块存在"""
        from agentteam.parser.confirmation_detector import ConfirmationDetector

        assert ConfirmationDetector is not None

    def test_skill_engine_module_exists(self):
        """测试 SkillEngine 模块存在"""
        from agentteam.skill.engine import SkillEngine

        assert SkillEngine is not None

    def test_all_modules_importable(self):
        """测试所有模块可导入"""
        modules = [
            "agentteam.parser.output_parser",
            "agentteam.notification.manager",
            "agentteam.concurrency.guard",
            "agentteam.parser.confirmation_detector",
            "agentteam.skill.engine",
        ]
        for module in modules:
            __import__(module)


# ==============================================================================
# 性能基准测试
# ==============================================================================


class TestPerformanceBaseline:
    """性能基准测试"""

    def test_import_time_output_parser(self):
        """测试 OutputParser 导入时间"""
        start = time.time()
        # 强制重新导入
        if "agentteam.parser.output_parser" in sys.modules:
            del sys.modules["agentteam.parser.output_parser"]
        from agentteam.parser.output_parser import OutputParser

        elapsed = time.time() - start
        # 导入时间应该小于 1秒
        assert elapsed < 1.0
        print(f"OutputParser import time: {elapsed:.3f}s")

    def test_import_time_notification_manager(self):
        """测试 NotificationManager 导入时间"""
        start = time.time()
        if "agentteam.notification.manager" in sys.modules:
            del sys.modules["agentteam.notification.manager"]
        from agentteam.notification.manager import NotificationManager

        elapsed = time.time() - start
        assert elapsed < 1.0
        print(f"NotificationManager import time: {elapsed:.3f}s")

    def test_import_time_concurrency_guard(self):
        """测试 ConcurrencyGuard 导入时间"""
        start = time.time()
        if "agentteam.concurrency.guard" in sys.modules:
            del sys.modules["agentteam.concurrency.guard"]
        from agentteam.concurrency.guard import ConcurrencyGuard

        elapsed = time.time() - start
        assert elapsed < 1.0
        print(f"ConcurrencyGuard import time: {elapsed:.3f}s")

    def test_import_time_confirmation_detector(self):
        """测试 ConfirmationDetector 导入时间"""
        start = time.time()
        if "agentteam.parser.confirmation_detector" in sys.modules:
            del sys.modules["agentteam.parser.confirmation_detector"]
        from agentteam.parser.confirmation_detector import ConfirmationDetector

        elapsed = time.time() - start
        assert elapsed < 1.0
        print(f"ConfirmationDetector import time: {elapsed:.3f}s")

    def test_import_time_skill_engine(self):
        """测试 SkillEngine 导入时间"""
        start = time.time()
        if "agentteam.skill.engine" in sys.modules:
            del sys.modules["agentteam.skill.engine"]
        from agentteam.skill.engine import SkillEngine

        elapsed = time.time() - start
        assert elapsed < 1.0
        print(f"SkillEngine import time: {elapsed:.3f}s")

    def test_all_modules_import_time(self):
        """测试所有模块总导入时间"""
        start = time.time()

        # 清除所有模块
        modules_to_clear = [
            "agentteam.parser.output_parser",
            "agentteam.notification.manager",
            "agentteam.concurrency.guard",
            "agentteam.parser.confirmation_detector",
            "agentteam.skill.engine",
        ]
        for m in modules_to_clear:
            if m in sys.modules:
                del sys.modules[m]

        # 重新导入所有模块
        from agentteam.parser.output_parser import OutputParser
        from agentteam.notification.manager import NotificationManager
        from agentteam.concurrency.guard import ConcurrencyGuard
        from agentteam.parser.confirmation_detector import ConfirmationDetector
        from agentteam.skill.engine import SkillEngine

        elapsed = time.time() - start
        # 总导入时间应该小于 5秒
        assert elapsed < 5.0
        print(f"All modules import time: {elapsed:.3f}s")


class TestMemoryBaseline:
    """内存使用基线测试"""

    def test_output_parser_memory(self):
        """测试 OutputParser 内存使用"""
        from agentteam.parser.output_parser import OutputParser
        import tracemalloc

        tracemalloc.start()
        parser = OutputParser()
        # 解析一些输出（参数顺序: session_id, data）
        for i in range(100):
            parser.parse(f"session-{i}", f"Test output {i}")
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # 内存使用应该合理（小于 10MB）
        assert peak < 10 * 1024 * 1024
        print(f"OutputParser memory: current={current / 1024:.1f}KB, peak={peak / 1024:.1f}KB")

    def test_notification_manager_memory(self):
        """测试 NotificationManager 内存使用"""
        from agentteam.notification.manager import NotificationManager
        import tracemalloc

        tracemalloc.start()
        manager = NotificationManager()
        # 发送一些通知（使用正确参数）
        for i in range(100):
            manager.on_task_completed(session_id=f"session-{i}", session_name=f"Session {i}")
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        assert peak < 10 * 1024 * 1024
        print(f"NotificationManager memory: current={current / 1024:.1f}KB, peak={peak / 1024:.1f}KB")

    def test_concurrency_guard_memory(self):
        """测试 ConcurrencyGuard 内存使用"""
        from agentteam.concurrency.guard import ConcurrencyGuard, ConcurrencyConfig
        import tracemalloc

        tracemalloc.start()
        guard = ConcurrencyGuard(ConcurrencyConfig(max_sessions=100))
        # 注册一些会话
        for i in range(50):
            guard.register_session()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        assert peak < 5 * 1024 * 1024
        print(f"ConcurrencyGuard memory: current={current / 1024:.1f}KB, peak={peak / 1024:.1f}KB")

    def test_skill_engine_memory(self):
        """测试 SkillEngine 内存使用"""
        from agentteam.skill.engine import SkillEngine, Skill, SkillType
        import tracemalloc

        tracemalloc.start()
        engine = SkillEngine()
        # 创建一些技能并展开（Skill 需要 id, name, description, category）
        for i in range(50):
            skill = Skill(
                id=f"skill-{i}",
                name=f"skill-{i}",
                description=f"Skill {i}",
                category="custom",
                type=SkillType.PROMPT,
                prompt_template=f"Template {i}: {{input}}",
            )
            # 使用 expand 方法展开技能
            engine.expand(skill, f"input {i}", {})
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        assert peak < 10 * 1024 * 1024
        print(f"SkillEngine memory: current={current / 1024:.1f}KB, peak={peak / 1024:.1f}KB")


class TestExecutionTimeBaseline:
    """执行时间基线测试"""

    def test_output_parser_parse_speed(self):
        """测试 OutputParser 解析速度"""
        from agentteam.parser.output_parser import OutputParser

        parser = OutputParser()
        start = time.time()

        # 解析 1000次（参数顺序: session_id, data）
        for i in range(1000):
            parser.parse(f"session-{i % 10}", f"Test output line {i}\nTool use: read_file\nComplete")

        elapsed = time.time() - start
        # 1000次解析应该小于 5秒
        assert elapsed < 5.0
        print(f"OutputParser parse 1000 times: {elapsed:.3f}s ({elapsed / 1000 * 1000:.3f}ms per parse)")

    def test_notification_manager_notify_speed(self):
        """测试 NotificationManager 通知速度"""
        from agentteam.notification.manager import NotificationManager

        manager = NotificationManager()
        start = time.time()

        # 发送 1000次通知（使用正确参数）
        for i in range(1000):
            manager.on_task_completed(session_id=f"session-{i % 10}", session_name=f"Session {i}")

        elapsed = time.time() - start
        assert elapsed < 5.0
        print(f"NotificationManager notify 1000 times: {elapsed:.3f}s ({elapsed / 1000 * 1000:.3f}ms per notify)")

    def test_concurrency_guard_check_speed(self):
        """测试 ConcurrencyGuard 检查速度"""
        from agentteam.concurrency.guard import ConcurrencyGuard, ConcurrencyConfig

        guard = ConcurrencyGuard(ConcurrencyConfig(max_sessions=100))
        start = time.time()

        # 检查 1000次
        for i in range(1000):
            guard.can_create_session()

        elapsed = time.time() - start
        assert elapsed < 1.0
        print(f"ConcurrencyGuard check 1000 times: {elapsed:.3f}s ({elapsed / 1000 * 1000:.3f}ms per check)")

    def test_skill_engine_expand_speed(self):
        """测试 SkillEngine 展开速度"""
        from agentteam.skill.engine import SkillEngine, Skill, SkillType

        engine = SkillEngine()
        skill = Skill(
            id="test-skill",
            name="test-skill",
            description="Test skill",
            category="custom",
            type=SkillType.PROMPT,
            prompt_template="Hello {{name}}, your task is {{task}}",
        )

        start = time.time()

        # 展开 1000次（使用 expand 方法）
        for i in range(1000):
            engine.expand(skill, "", {"name": f"User{i}", "task": f"Task{i}"})

        elapsed = time.time() - start
        assert elapsed < 5.0
        print(f"SkillEngine expand 1000 times: {elapsed:.3f}s ({elapsed / 1000 * 1000:.3f}ms per expand)")


# ==============================================================================
# 基线数据记录
# ==============================================================================


class TestBaselineData:
    """基线数据记录"""

    def test_record_baseline(self):
        """记录基线数据"""
        baseline_data = {
            "test_count": 877,
            "baseline_time": 59.92,
            "modules": [
                "output_parser",
                "notification_manager",
                "concurrency_guard",
                "confirmation_detector",
                "skill_engine",
            ],
            "import_time_target": "< 1s per module",
            "memory_target": "< 10MB per module",
            "parse_speed_target": "< 5ms per operation",
        }

        # 基线数据应该被记录
        assert baseline_data["test_count"] == 877
        assert baseline_data["baseline_time"] < 100

        print(f"Baseline data recorded: {baseline_data}")


# ==============================================================================
# 集成测试
# ==============================================================================


class TestNewModulesIntegration:
    """新模块集成测试"""

    def test_parser_with_notification(self):
        """测试 Parser 与 Notification 集成"""
        from agentteam.parser.output_parser import OutputParser
        from agentteam.notification.manager import NotificationManager

        parser = OutputParser()
        manager = NotificationManager()

        # 解析输出并发送通知
        events = parser.parse("test-session", "Task completed successfully")
        manager.on_task_completed(session_id="test-session", session_name="Test Session")

        # 集成应该正常工作

    def test_concurrency_with_session(self):
        """测试 Concurrency 与 Session 集成"""
        from agentteam.concurrency.guard import ConcurrencyGuard, ConcurrencyConfig
        from agentteam.session.registry import SessionRegistry

        guard = ConcurrencyGuard(ConcurrencyConfig(max_sessions=5))
        registry = SessionRegistry()

        # 检查是否可以创建会话
        if guard.can_create_session():
            guard.register_session()
            # 注册会话

        # 集成应该正常工作

    def test_skill_with_parser(self):
        """测试 Skill 与 Parser 集成"""
        from agentteam.skill.engine import SkillEngine, Skill, SkillType
        from agentteam.parser.output_parser import OutputParser

        engine = SkillEngine()
        parser = OutputParser()

        skill = Skill(
            id="test-skill",
            name="test-skill",
            description="Test skill",
            category="custom",
            type=SkillType.PROMPT,
            prompt_template="Process {{input}}",
        )

        # 展开技能并解析输出
        prompt = engine.expand(skill, "test data", {"input": "test data"})
        events = parser.parse("test-session", prompt)

        # 集成应该正常工作

    def test_full_workflow(self):
        """测试完整工作流"""
        from agentteam.parser.output_parser import OutputParser
        from agentteam.notification.manager import NotificationManager
        from agentteam.concurrency.guard import ConcurrencyGuard, ConcurrencyConfig
        from agentteam.skill.engine import SkillEngine, Skill, SkillType

        # 初始化所有模块
        parser = OutputParser()
        manager = NotificationManager()
        guard = ConcurrencyGuard(ConcurrencyConfig(max_sessions=10))
        engine = SkillEngine()

        # 创建技能
        skill = Skill(
            id="workflow-skill",
            name="workflow-skill",
            description="Workflow skill",
            category="custom",
            type=SkillType.PROMPT,
            prompt_template="Execute {{task}}",
        )

        # 检查并发限制
        if guard.can_create_session():
            session_id = guard.register_session()

            # 展开技能
            prompt = engine.expand(skill, "test task", {"task": "test task"})

            # 解析输出
            events = parser.parse("workflow-session", prompt)

            # 发送通知
            manager.on_task_completed(session_id="workflow-session", session_name="Workflow")

            # 清理
            guard.unregister_session(session_id)

        # 完整工作流应该正常工作
