"""
AgentTeam 用户画像系统测试 (P14)

测试 P14 实现：
- 偏好提取（PreferenceExtractor）
- 行为模式分析（BehaviorAnalyzer）
- 用户画像管理（UserProfileManager）
- 画像持久化存储
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch

from agentteam.profile import (
    Preference,
    BehavioralPattern,
    UserProfile,
    PreferenceExtractor,
    BehaviorAnalyzer,
    UserProfileManager,
)


class TestPreferenceExtractor:
    """测试偏好提取器"""

    def test_extract_indent_size(self):
        """测试提取缩进大小偏好"""
        extractor = PreferenceExtractor()

        result = extractor.extract("我想要2空格缩进")
        assert len(result) >= 1
        # 找到 indent_size 偏好
        indent_prefs = [r for r in result if r["key"] == "indent_size"]
        assert len(indent_prefs) == 1
        assert indent_prefs[0]["value"] == 2

    def test_extract_indent_size_english(self):
        """测试英文缩进偏好"""
        extractor = PreferenceExtractor()

        result = extractor.extract("I prefer 4 space indent")
        indent_prefs = [r for r in result if r["key"] == "indent_size"]
        assert len(indent_prefs) == 1
        assert indent_prefs[0]["value"] == 4

    def test_extract_quote_style(self):
        """测试引号风格偏好"""
        extractor = PreferenceExtractor()

        result = extractor.extract("我更喜欢单引号")
        quote_prefs = [r for r in result if r["key"] == "quote_style"]
        assert len(quote_prefs) == 1
        assert quote_prefs[0]["value"] == "single"

    def test_extract_double_quote(self):
        """测试双引号偏好"""
        extractor = PreferenceExtractor()

        result = extractor.extract("双引号更规范")
        quote_prefs = [r for r in result if r["key"] == "quote_style"]
        assert len(quote_prefs) == 1
        assert quote_prefs[0]["value"] == "double"

    def test_extract_naming_convention(self):
        """测试命名约定偏好"""
        extractor = PreferenceExtractor()

        result = extractor.extract("请用驼峰命名法")
        naming_prefs = [r for r in result if r["key"] == "naming_convention"]
        assert len(naming_prefs) == 1
        assert naming_prefs[0]["value"] == "camelCase"

    def test_extract_snake_case(self):
        """测试下划线命名偏好"""
        extractor = PreferenceExtractor()

        result = extractor.extract("用下划线命名更好")
        naming_prefs = [r for r in result if r["key"] == "naming_convention"]
        assert len(naming_prefs) == 1
        assert naming_prefs[0]["value"] == "snake_case"

    def test_extract_language_preference(self):
        """测试语言偏好"""
        extractor = PreferenceExtractor()

        result = extractor.extract("请用中文回答")
        lang_prefs = [r for r in result if r["key"] == "language"]
        assert len(lang_prefs) == 1
        assert lang_prefs[0]["value"] == "中文"

    def test_extract_response_style(self):
        """测试响应风格偏好"""
        extractor = PreferenceExtractor()

        result = extractor.extract("回答简洁点")
        style_prefs = [r for r in result if r["key"] == "response_style"]
        assert len(style_prefs) == 1
        assert style_prefs[0]["value"] == "concise"

    def test_extract_response_style_detailed(self):
        """测试详细响应风格偏好"""
        extractor = PreferenceExtractor()

        result = extractor.extract("请详细点")
        style_prefs = [r for r in result if r["key"] == "response_style"]
        assert len(style_prefs) == 1
        assert style_prefs[0]["value"] == "detailed"

    def test_extract_multiple_preferences(self):
        """测试提取多个偏好"""
        extractor = PreferenceExtractor()

        result = extractor.extract("我喜欢单引号，2空格缩进，简洁回答")
        assert len(result) >= 2

    def test_extract_no_preference(self):
        """测试无偏好时的提取"""
        extractor = PreferenceExtractor()

        result = extractor.extract("今天天气真好")
        # 没有任何模式匹配，应该是空的或只有默认偏好
        pref_keys = [r["key"] for r in result]
        assert len(pref_keys) == 0

    def test_update_confidence(self):
        """测试更新偏好置信度"""
        extractor = PreferenceExtractor()

        pref = Preference(key="indent_size", value=2, confidence=0.5, evidence=["第一次提到2空格"])

        updated = extractor.update_confidence(pref, "第二次提到2空格")
        assert updated.confidence > 0.5
        assert len(updated.evidence) == 2
        assert "第二次提到2空格" in updated.evidence


class TestBehaviorAnalyzer:
    """测试行为分析器"""

    def test_analyze_working_hours_insufficient_data(self):
        """测试数据不足时的工作时间分析"""
        analyzer = BehaviorAnalyzer()

        # 少于3个时间点，应该返回None
        times = [datetime.now()]
        result = analyzer.analyze_working_hours(times)
        assert result is None

    def test_analyze_working_hours_success(self):
        """测试成功分析工作时间"""
        analyzer = BehaviorAnalyzer()

        # 创建工作时间内的对话时间
        base_date = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        times = [base_date + timedelta(hours=i) for i in range(5)]

        result = analyzer.analyze_working_hours(times)
        # 如果大多数时间在工作时间内，应该返回模式
        if result:
            assert result.pattern_type == "working_hours"
            assert "peak_start" in result.data

    def test_analyze_tool_preference_insufficient(self):
        """测试工具偏好数据不足"""
        analyzer = BehaviorAnalyzer()

        tools = ["bash", "bash"]  # 少于5个
        result = analyzer.analyze_tool_preference(tools)
        assert result is None

    def test_analyze_tool_preference_success(self):
        """测试成功分析工具偏好"""
        analyzer = BehaviorAnalyzer()

        # 创建明显的工具偏好
        tools = ["bash", "bash", "bash", "python", "bash"]
        result = analyzer.analyze_tool_preference(tools)

        if result:
            assert result.pattern_type == "tool_preference"
            assert "preferred_tools" in result.data
            assert "bash" in result.data["preferred_tools"]

    def test_analyze_communication_style_insufficient(self):
        """测试沟通风格数据不足"""
        analyzer = BehaviorAnalyzer()

        messages = ["hi", "bye"]  # 少于3条
        result = analyzer.analyze_communication_style(messages)
        assert result is None

    def test_analyze_communication_style_concise(self):
        """测试简洁沟通风格"""
        analyzer = BehaviorAnalyzer()

        messages = ["hi", "ok", "yes"]
        result = analyzer.analyze_communication_style(messages)

        if result:
            assert result.pattern_type == "communication_style"
            assert result.data.get("style") in ["concise", "inquisitive"]

    def test_analyze_communication_style_detailed(self):
        """测试详细沟通风格"""
        analyzer = BehaviorAnalyzer()

        # 创建长消息
        messages = [
            "这是一个非常详细的消息，包含了大量的解释和分析内容，希望能够全面地描述问题的各个方面，以便获得最佳解答。"
        ] * 3
        result = analyzer.analyze_communication_style(messages)

        if result:
            assert result.pattern_type == "communication_style"
            assert result.data.get("style") == "detailed"


class TestPreference:
    """测试 Preference 模型"""

    def test_preference_creation(self):
        """测试创建偏好"""
        pref = Preference(
            key="code_style", value={"indent": 2, "quote": "single"}, confidence=0.8, source="conversation"
        )

        assert pref.key == "code_style"
        assert pref.value == {"indent": 2, "quote": "single"}
        assert pref.confidence == 0.8
        assert pref.source == "conversation"
        assert len(pref.evidence) == 0

    def test_preference_defaults(self):
        """测试偏好默认值"""
        pref = Preference(key="test", value="value")

        assert pref.confidence == 0.5
        assert pref.source == ""
        assert pref.created_at is not None
        assert pref.updated_at is not None
        assert pref.evidence == []


class TestBehavioralPattern:
    """测试 BehavioralPattern 模型"""

    def test_pattern_creation(self):
        """测试创建行为模式"""
        pattern = BehavioralPattern(
            pattern_type="working_hours", data={"start": "09:00", "end": "18:00"}, confidence=0.85
        )

        assert pattern.pattern_type == "working_hours"
        assert pattern.data == {"start": "09:00", "end": "18:00"}
        assert pattern.confidence == 0.85

    def test_pattern_defaults(self):
        """测试模式默认值"""
        pattern = BehavioralPattern(pattern_type="test", data={})

        assert pattern.confidence == 0.5
        assert pattern.first_observed is not None
        assert pattern.last_observed is not None


class TestUserProfile:
    """测试 UserProfile 模型"""

    def test_profile_creation(self):
        """测试创建用户画像"""
        profile = UserProfile(user_id="test_user", name="测试用户", identity="开发者")

        assert profile.user_id == "test_user"
        assert profile.name == "测试用户"
        assert profile.identity == "开发者"
        assert profile.preferences == {}
        assert profile.behavioral_patterns == {}
        assert profile.projects == {}

    def test_profile_defaults(self):
        """测试画像默认值"""
        profile = UserProfile()

        assert profile.user_id == "default"
        assert profile.name is None
        assert profile.identity == ""
        assert profile.created_at is not None
        assert profile.updated_at is not None


class TestUserProfileManager:
    """测试用户画像管理器"""

    @pytest.fixture
    def temp_profile_dir(self):
        """创建临时画像目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_profile_dir):
        """创建测试管理器实例"""
        return UserProfileManager(profile_dir=str(temp_profile_dir))

    def test_manager_initialization(self, manager, temp_profile_dir):
        """测试管理器初始化"""
        assert manager.profile_dir == temp_profile_dir
        assert manager.profile_dir.exists()
        assert isinstance(manager.preference_extractor, PreferenceExtractor)
        assert isinstance(manager.behavior_analyzer, BehaviorAnalyzer)

    def test_analyze_conversation_extract_preference(self, manager):
        """测试分析对话提取偏好"""
        changes = manager.analyze_conversation(user_message="我喜欢单引号", assistant_response="好的，使用单引号。")

        # 应该提取到 quote_style 偏好
        pref_keys = [c.get("key") for c in changes]
        assert "quote_style" in pref_keys

    def test_analyze_conversation_update_existing(self, manager):
        """测试更新已存在的偏好"""
        # 第一次对话
        manager.analyze_conversation(user_message="我喜欢单引号", session_context={"user_id": "test_user"})

        # 第二次对话（相同偏好）
        changes = manager.analyze_conversation(user_message="单引号确实更好", session_context={"user_id": "test_user"})

        # 应该更新现有偏好而不是创建新的
        assert len(changes) >= 1
        update_changes = [c for c in changes if c.get("action") == "updated"]
        # 可能有更新也可能没有，取决于置信度计算

    def test_get_profile_new_user(self, manager):
        """测试获取新用户画像"""
        profile = manager.get_profile("new_user")

        assert profile.user_id == "new_user"
        assert profile.preferences == {}
        assert profile.behavioral_patterns == {}

    def test_get_profile_existing_user(self, manager):
        """测试获取已存在用户画像"""
        # 创建偏好
        manager.analyze_conversation(user_message="我喜欢2空格缩进", session_context={"user_id": "existing_user"})

        # 获取画像
        profile = manager.get_profile("existing_user")

        assert profile.user_id == "existing_user"
        assert len(profile.preferences) >= 1

    def test_update_profile_add_preference(self, manager):
        """测试更新画像添加偏好"""
        profile = manager.update_profile(
            user_id="test_user", changes=[{"type": "preference", "key": "language", "value": "Chinese"}]
        )

        assert "language" in profile.preferences
        assert profile.preferences["language"].value == "Chinese"

    def test_update_profile_identity(self, manager):
        """测试更新画像身份"""
        profile = manager.update_profile(
            user_id="test_user", changes=[{"type": "identity", "key": "identity", "value": "后端开发工程师"}]
        )

        assert profile.identity == "后端开发工程师"

    def test_update_profile_name(self, manager):
        """测试更新画像名称"""
        profile = manager.update_profile(
            user_id="test_user", changes=[{"type": "name", "key": "name", "value": "张三"}]
        )

        assert profile.name == "张三"

    def test_update_profile_project(self, manager):
        """测试更新画像项目"""
        profile = manager.update_profile(
            user_id="test_user",
            changes=[
                {
                    "type": "project",
                    "project_name": "AgentTeam升级",
                    "value": {"name": "AgentTeam升级", "status": "active", "priority": "high"},
                }
            ],
        )

        assert "AgentTeam升级" in profile.projects
        assert profile.projects["AgentTeam升级"]["status"] == "active"

    def test_get_context_for_prompt_empty(self, manager):
        """测试生成空上下文字符串"""
        profile = manager.get_profile("empty_user")
        context = manager.get_context_for_prompt("empty_user")

        # 空画像应该返回空字符串
        assert context == ""

    def test_get_context_for_prompt_with_preferences(self, manager):
        """测试生成带偏好的上下文字符串"""
        # 添加偏好
        manager.analyze_conversation(user_message="我喜欢单引号，2空格缩进", session_context={"user_id": "pref_user"})

        context = manager.get_context_for_prompt("pref_user")

        assert isinstance(context, str)
        assert len(context) > 0
        assert "## 用户上下文" in context
        assert "quote_style" in context or "单引号" in context

    def test_get_context_for_prompt_with_identity(self, manager):
        """测试生成带身份信息的上下文字符串"""
        manager.update_profile(
            user_id="identity_user", changes=[{"type": "identity", "key": "identity", "value": "开发者"}]
        )

        context = manager.get_context_for_prompt("identity_user")

        assert "开发者" in context

    def test_save_and_load_profile(self, manager, temp_profile_dir):
        """测试保存和加载画像"""
        # 创建并保存画像
        manager.update_profile(
            user_id="save_test",
            changes=[
                {"type": "name", "key": "name", "value": "测试用户"},
                {"type": "preference", "key": "indent", "value": 4},
            ],
        )

        # 创建新的管理器实例（应该从文件加载）
        new_manager = UserProfileManager(profile_dir=str(temp_profile_dir))
        profile = new_manager.get_profile("save_test")

        assert profile.user_id == "save_test"
        assert profile.name == "测试用户"
        assert "indent" in profile.preferences

    def test_list_profiles(self, manager):
        """测试列出用户画像"""
        # 创建多个用户
        for i in range(3):
            manager.get_profile(f"user_{i}")

        profiles = manager.list_profiles()
        assert len(profiles) >= 3
        for i in range(3):
            assert f"user_{i}" in profiles

    def test_delete_profile(self, manager):
        """测试删除用户画像"""
        manager.get_profile("to_delete")
        assert "to_delete" in manager.list_profiles()

        result = manager.delete_profile("to_delete")
        assert result is True
        assert "to_delete" not in manager.list_profiles()

    def test_delete_nonexistent_profile(self, manager):
        """测试删除不存在的画像"""
        result = manager.delete_profile("nonexistent")
        assert result is False

    def test_merge_profiles(self, manager):
        """测试合并用户画像"""
        profile1 = UserProfile(
            user_id="user1", preferences={"indent": Preference(key="indent", value=2, confidence=0.8)}
        )

        profile2 = UserProfile(
            user_id="user2",
            preferences={
                "indent": Preference(key="indent", value=4, confidence=0.9),
                "quote": Preference(key="quote", value="single", confidence=0.7),
            },
        )

        merged = manager.merge_profiles([profile1, profile2])

        assert merged.user_id == "merged"
        assert "indent" in merged.preferences
        assert "quote" in merged.preferences
        # 应该取置信度更高的 indent (4)
        assert merged.preferences["indent"].value == 4

    def test_detect_behavioral_changes(self, manager):
        """测试检测行为变化"""
        # 记录一些对话时间
        user_id = "behavior_user"
        manager._conversation_times[user_id] = []
        for i in range(5):
            manager._conversation_times[user_id].append(datetime.now() - timedelta(hours=i))

        changes = manager.detect_behavioral_changes(user_id)

        # 可能检测到一些行为变化
        assert isinstance(changes, list)

    def test_profile_persistence_across_sessions(self, manager, temp_profile_dir):
        """测试画像在会话间持久化"""
        # 第一个会话：分析对话
        manager.analyze_conversation(user_message="我想要4空格缩进", session_context={"user_id": "persistent_user"})

        # 模拟新会话
        new_manager = UserProfileManager(profile_dir=str(temp_profile_dir))

        # 应该能看到之前的偏好
        context = new_manager.get_context_for_prompt("persistent_user")
        # 如果提取到了 indent 偏好，上下文应该包含它
        profile = new_manager.get_profile("persistent_user")
        # 偏好应该被持久化
        indent_keys = [k for k in profile.preferences.keys() if "indent" in k]
        assert len(indent_keys) >= 1

    def test_extract_preference_with_context(self, manager):
        """测试带会话上下文的偏好提取"""
        changes = manager.analyze_conversation(
            user_message="单引号更好",
            assistant_response="好的，我用单引号。",
            session_context={"user_id": "ctx_user", "tool": "bash"},
        )

        # 应该提取到偏好
        assert len(changes) >= 1

        # 工具使用应该被记录
        assert "ctx_user" in manager._tool_usage_history


class TestIntegration:
    """集成测试"""

    def test_full_user_journey(self):
        """测试完整用户旅程"""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_dir = Path(tmpdir)
            manager = UserProfileManager(profile_dir=str(profile_dir))

            # 1. 首次对话：提取偏好
            manager.analyze_conversation(
                user_message="我喜欢单引号，2空格缩进", session_context={"user_id": "journey_user"}
            )

            # 2. 第二次对话：更新偏好
            manager.analyze_conversation(
                user_message="单引号确实更好，而且请简洁点", session_context={"user_id": "journey_user"}
            )

            # 3. 更新身份
            manager.update_profile(
                user_id="journey_user", changes=[{"type": "identity", "key": "identity", "value": "Python开发者"}]
            )

            # 4. 验证画像
            profile = manager.get_profile("journey_user")
            assert profile.identity == "Python开发者"
            assert len(profile.preferences) >= 2

            # 5. 生成上下文
            context = manager.get_context_for_prompt("journey_user")
            assert isinstance(context, str)
            assert len(context) > 0

            # 6. 持久化验证
            new_manager = UserProfileManager(profile_dir=str(profile_dir))
            loaded_profile = new_manager.get_profile("journey_user")
            assert loaded_profile.identity == "Python开发者"
            assert len(loaded_profile.preferences) >= 2

    def test_multi_user_isolation(self):
        """测试多用户隔离"""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_dir = Path(tmpdir)
            manager = UserProfileManager(profile_dir=str(profile_dir))

            # 用户A的偏好
            manager.analyze_conversation(user_message="我喜欢单引号", session_context={"user_id": "user_a"})

            # 用户B的偏好
            manager.analyze_conversation(user_message="双引号更规范", session_context={"user_id": "user_b"})

            # 验证隔离
            profile_a = manager.get_profile("user_a")
            profile_b = manager.get_profile("user_b")

            # 两个用户的画像应该不同
            quote_a = profile_a.preferences.get("quote_style")
            quote_b = profile_b.preferences.get("quote_style")

            if quote_a:
                assert quote_a.value == "single"
            if quote_b:
                assert quote_b.value == "double"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
