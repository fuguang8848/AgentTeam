"""
ClawTeam 用户画像系统 - P14 实现

核心功能：
1. 自动从对话中提取用户偏好
2. 用户画像结构化存储
3. 为系统提示生成用户上下文
4. 行为模式检测
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Set, Literal
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timedelta
from pathlib import Path
import json
import re
import logging
import uuid

logger = logging.getLogger(__name__)


class Preference(BaseModel):
    """用户偏好"""
    key: str
    value: Any
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    source: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    evidence: List[str] = Field(default_factory=list)

    pass


class BehavioralPattern(BaseModel):
    """行为模式"""
    pattern_type: str  # working_hours, tool_preference, communication_style
    data: Dict[str, Any]
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    first_observed: datetime = Field(default_factory=datetime.now)
    last_observed: datetime = Field(default_factory=datetime.now)

    pass


class UserProfile(BaseModel):
    """用户画像"""
    user_id: str = "default"
    name: Optional[str] = None
    identity: str = ""
    preferences: Dict[str, Preference] = Field(default_factory=dict)
    behavioral_patterns: Dict[str, BehavioralPattern] = Field(default_factory=dict)
    projects: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    evolution: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    pass


class PreferenceExtractor:
    """偏好提取器 - 从对话中提取用户偏好"""

    # 偏好模式定义
    PREFERENCE_PATTERNS = {
        # 代码风格偏好
        "indent_size": [
            (r"(\d+)\s*空格", "indent_size"),
            (r"缩进.*?(\d+)", "indent_size"),
            (r"indent.*?(\d+)", "indent_size"),
            (r"(\d+)\s*space", "indent_size"),
        ],
        "quote_style": [
            (r"单引号", "single"),
            (r"双引号", "double"),
            (r"single.*?quote", "single"),
            (r"double.*?quote", "double"),
        ],
        "line_length": [
            (r"最大.*?(\d+).*?字符", "line_length"),
            (r"line.*?length.*?(\d+)", "line_length"),
            (r"max.*?(\d+).*?chars", "line_length"),
        ],
        # 命名偏好
        "naming_convention": [
            (r"驼峰命名", "camelCase"),
            (r"下划线", "snake_case"),
            (r"camelCase", "camelCase"),
            (r"snake_case", "snake_case"),
        ],
        # 工作偏好
        "timezone": [
            (r"时区.*?([A-Za-z/]+)", "timezone"),
            (r"timezone.*?([A-Za-z/]+)", "timezone"),
            (r"Asia/Shanghai", "Asia/Shanghai"),
        ],
        "working_hours": [
            (r"工作.*?(\d+).*?-.*?(\d+)", "working_hours"),
            (r"(\d+):00.*?(\d+):00", "working_hours"),
        ],
        # 语言偏好
        "language": [
            (r"用中文", "中文"),
            (r"用英文", "英文"),
            (r"用日语", "日语"),
            (r"用韩语", "韩语"),
            (r"chinese", "chinese"),
            (r"english", "english"),
            (r"japanese", "japanese"),
            (r"korean", "korean"),
        ],
        # 响应风格
        "response_style": [
            (r"简洁", "concise"),
            (r"详细", "detailed"),
            (r"简洁点", "concise"),
            (r"详细点", "detailed"),
            (r"concise", "concise"),
            (r"detailed", "detailed"),
        ],
    }

    def __init__(self):
        self._compiled_patterns: Dict[str, List[tuple]] = {}
        for key, patterns in self.PREFERENCE_PATTERNS.items():
            self._compiled_patterns[key] = [
                (re.compile(p, re.IGNORECASE), v)
                for p, v in patterns
            ]

    def extract(self, user_message: str, assistant_response: str = "") -> List[Dict[str, Any]]:
        """从对话中提取偏好

        Args:
            user_message: 用户消息
            assistant_response: 助手回复

        Returns:
            提取到的偏好列表
        """
        combined_text = f"{user_message} {assistant_response}"
        extracted = []

        for pref_key, patterns in self._compiled_patterns.items():
            for compiled_pattern, value in patterns:
                match = compiled_pattern.search(combined_text)
                if match:
                    # 提取数值（如果是数字）
                    if pref_key == "indent_size" or pref_key == "line_length":
                        try:
                            value = int(match.group(1))
                        except (IndexError, ValueError):
                            pass

                    evidence = match.group(0)
                    extracted.append({
                        "key": pref_key,
                        "value": value,
                        "confidence": 0.7,
                        "evidence": [evidence],
                        "source": "conversation"
                    })
                    break  # 每个偏好类型只取第一个匹配

        return extracted

    def update_confidence(self, existing_pref: Preference, new_evidence: str) -> Preference:
        """更新偏好置信度"""
        evidence_count = len(existing_pref.evidence)
        # 每次新证据增加置信度，但有上限
        new_confidence = min(0.99, existing_pref.confidence + 0.1 / (evidence_count + 1))
        existing_pref.confidence = new_confidence
        existing_pref.evidence.append(new_evidence)
        existing_pref.updated_at = datetime.now()
        return existing_pref


class BehaviorAnalyzer:
    """行为分析器 - 检测用户行为模式"""

    def __init__(self):
        self.pattern_window_days = 7

    def analyze_working_hours(
        self, conversation_times: List[datetime]
    ) -> Optional[BehavioralPattern]:
        """分析工作时间模式"""
        if len(conversation_times) < 3:
            return None

        # 提取小时
        hours = [t.hour for t in conversation_times]
        avg_hour = sum(hours) / len(hours)

        # 简单的工作时间检测 (9-18 点)
        work_hours = [h for h in hours if 9 <= h <= 18]
        if len(work_hours) / len(hours) > 0.7:
            return BehavioralPattern(
                pattern_type="working_hours",
                data={
                    "peak_start": "09:00",
                    "peak_end": "18:00",
                    "timezone": "Asia/Shanghai"
                },
                confidence=0.8,
                first_observed=min(conversation_times),
                last_observed=max(conversation_times)
            )

        return None

    def analyze_tool_preference(
        self, tool_usage_history: List[str]
    ) -> Optional[BehavioralPattern]:
        """分析工具使用偏好"""
        if len(tool_usage_history) < 5:
            return None

        # 统计工具使用频率
        from collections import Counter
        tool_counts = Counter(tool_usage_history)
        most_common = tool_counts.most_common(3)

        if not most_common:
            return None

        total = sum(tool_counts.values())
        top_tool, count = most_common[0]
        preference_ratio = count / total

        if preference_ratio > 0.4:  # 明显偏好
            return BehavioralPattern(
                pattern_type="tool_preference",
                data={
                    "preferred_tools": [t for t, _ in most_common],
                    "usage_ratios": {t: c / total for t, c in most_common}
                },
                confidence=min(0.9, preference_ratio),
                first_observed=datetime.now() - timedelta(days=self.pattern_window_days),
                last_observed=datetime.now()
            )

        return None

    def analyze_communication_style(
        self, messages: List[str]
    ) -> Optional[BehavioralPattern]:
        """分析沟通风格"""
        if len(messages) < 3:
            return None

        # 简单统计
        total_chars = sum(len(m) for m in messages)
        avg_length = total_chars / len(messages)

        question_count = sum(1 for m in messages if "?" in m or "？" in m)
        question_ratio = question_count / len(messages)

        # 基于消息长度判断
        style = "detailed" if avg_length > 50 else "concise"
        confidence = 0.6

        # 如果问题多，可能是学习型用户
        if question_ratio > 0.3:
            style = "inquisitive"
            confidence = 0.7

        return BehavioralPattern(
            pattern_type="communication_style",
            data={
                "style": style,
                "avg_message_length": avg_length,
                "question_ratio": question_ratio
            },
            confidence=confidence,
            first_observed=datetime.now() - timedelta(days=self.pattern_window_days),
            last_observed=datetime.now()
        )


class UserProfileManager:
    """用户画像管理器"""

    def __init__(self, profile_dir: Optional[str] = None):
        """
        Args:
            profile_dir: 画像存储目录，默认 ~/.openclaw/profiles
        """
        self.profile_dir = Path(profile_dir or "~/.openclaw/profiles").expanduser()
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.preference_extractor = PreferenceExtractor()
        self.behavior_analyzer = BehaviorAnalyzer()
        self._profiles: Dict[str, UserProfile] = {}
        self._conversation_times: Dict[str, List[datetime]] = {}
        self._tool_usage_history: Dict[str, List[str]] = {}
        self._load_profiles()

    def _load_profiles(self) -> None:
        """加载已存在的用户画像"""
        try:
            for file_path in self.profile_dir.glob("*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # 转换 datetime 字符串
                        for key in ["created_at", "updated_at"]:
                            if key in data and isinstance(data[key], str):
                                data[key] = datetime.fromisoformat(data[key].replace('Z', '+00:00'))
                        # 转换 preferences 中的 datetime
                        if "preferences" in data:
                            for pref in data["preferences"].values():
                                for key in ["created_at", "updated_at"]:
                                    if key in pref and isinstance(pref[key], str):
                                        pref[key] = datetime.fromisoformat(pref[key].replace('Z', '+00:00'))
                        # 转换 behavioral_patterns 中的 datetime
                        if "behavioral_patterns" in data:
                            for bp in data["behavioral_patterns"].values():
                                for key in ["first_observed", "last_observed"]:
                                    if key in bp and isinstance(bp[key], str):
                                        bp[key] = datetime.fromisoformat(bp[key].replace('Z', '+00:00'))
                        profile = UserProfile(**data)
                        self._profiles[profile.user_id] = profile
                except Exception as e:
                    logger.warning(f"Failed to load profile from {file_path}: {e}")
            logger.info(f"Loaded {len(self._profiles)} user profiles")
        except Exception as e:
            logger.error(f"Error loading profiles: {e}")

    def _save_profile(self, profile: UserProfile) -> None:
        """保存用户画像到文件"""
        file_path = self.profile_dir / f"{profile.user_id}.json"
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                data = profile.model_dump()
                # 转换 datetime 为 ISO 字符串
                for key in ["created_at", "updated_at"]:
                    if key in data and isinstance(data[key], datetime):
                        data[key] = data[key].isoformat()
                for pref in data.get("preferences", {}).values():
                    for key in ["created_at", "updated_at"]:
                        if key in pref and isinstance(pref[key], datetime):
                            pref[key] = pref[key].isoformat()
                for bp in data.get("behavioral_patterns", {}).values():
                    for key in ["first_observed", "last_observed"]:
                        if key in bp and isinstance(bp[key], datetime):
                            bp[key] = bp[key].isoformat()
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save profile {profile.user_id}: {e}")
            raise

    def analyze_conversation(
        self,
        user_message: str,
        assistant_response: str = "",
        session_context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """分析对话，提取用户偏好

        Args:
            user_message: 用户消息
            assistant_response: 助手回复
            session_context: 会话上下文（包含 user_id 等）

        Returns:
            提取到的偏好变化列表
        """
        session_context = session_context or {}
        user_id = session_context.get("user_id", "default")
        timestamp = datetime.now()

        # 记录对话时间
        if user_id not in self._conversation_times:
            self._conversation_times[user_id] = []
        self._conversation_times[user_id].append(timestamp)

        # 记录工具使用
        if "tool" in session_context:
            if user_id not in self._tool_usage_history:
                self._tool_usage_history[user_id] = []
            self._tool_usage_history[user_id].append(session_context["tool"])

        # 提取偏好
        extracted = self.preference_extractor.extract(user_message, assistant_response)

        # 更新画像
        changes = []
        profile = self.get_profile(user_id)

        for pref_data in extracted:
            key = pref_data["key"]
            value = pref_data["value"]
            evidence = pref_data["evidence"][0]
            source = pref_data["source"]

            if key in profile.preferences:
                # 更新现有偏好
                existing = profile.preferences[key]
                updated = self.preference_extractor.update_confidence(existing, evidence)
                # 如果值相同，更新值
                if value != existing.value:
                    updated.value = value
                    updated.updated_at = datetime.now()
                profile.preferences[key] = updated
                changes.append({
                    "action": "updated",
                    "key": key,
                    "old_confidence": existing.confidence,
                    "new_confidence": updated.confidence
                })
            else:
                # 新增偏好
                profile.preferences[key] = Preference(
                    key=key,
                    value=value,
                    confidence=pref_data["confidence"],
                    source=source,
                    evidence=[evidence]
                )
                changes.append({
                    "action": "created",
                    "key": key,
                    "value": value
                })

        if changes:
            profile.updated_at = datetime.now()
            self._save_profile(profile)
            self._profiles[user_id] = profile

        return changes

    def update_profile(
        self,
        user_id: str,
        changes: List[Dict[str, Any]],
        source: str = "conversation"
    ) -> UserProfile:
        """更新用户画像

        Args:
            user_id: 用户 ID
            changes: 变更列表
            source: 变更来源

        Returns:
            更新后的画像
        """
        profile = self.get_profile(user_id)

        for change in changes:
            change_type = change.get("type")
            key = change.get("key")
            value = change.get("value")

            if change_type == "preference":
                if key in profile.preferences:
                    profile.preferences[key].value = value
                    profile.preferences[key].updated_at = datetime.now()
                else:
                    profile.preferences[key] = Preference(
                        key=key,
                        value=value,
                        source=source
                    )

            elif change_type == "identity":
                profile.identity = value

            elif change_type == "name":
                profile.name = value

            elif change_type == "project":
                project_name = change.get("project_name")
                if project_name:
                    profile.projects[project_name] = value

        # 记录进化
        profile.evolution.append({
            "timestamp": datetime.now().isoformat(),
            "changes": changes,
            "source": source
        })
        profile.updated_at = datetime.now()

        self._save_profile(profile)
        self._profiles[user_id] = profile

        return profile

    def get_context_for_prompt(
        self,
        user_id: str,
        task_type: Optional[str] = None
    ) -> str:
        """为系统提示生成用户上下文

        Args:
            user_id: 用户 ID
            task_type: 任务类型（可选）

        Returns:
            格式化的用户上下文
        """
        profile = self.get_profile(user_id)

        # 如果什么都没有，返回空
        if not profile.preferences and not profile.behavioral_patterns and not profile.identity and not profile.name:
            return ""

        context_parts = ["## 用户上下文"]

        # 身份信息
        if profile.identity:
            context_parts.append(f"**用户身份**: {profile.identity}")
        if profile.name:
            context_parts.append(f"**用户名**: {profile.name}")

        # 偏好信息
        if profile.preferences:
            pref_lines = ["**用户偏好**:"]
            for key, pref in sorted(profile.preferences.items()):
                if pref.confidence >= 0.5:  # 只包含置信度较高的偏好
                    pref_lines.append(f"- {key}: {pref.value} (置信度: {pref.confidence:.0%})")
            if len(pref_lines) > 1:
                context_parts.append("\n".join(pref_lines))

        # 行为模式
        if profile.behavioral_patterns:
            pattern_lines = ["**行为模式**"]
            for ptype, pattern in profile.behavioral_patterns.items():
                if pattern.confidence >= 0.5:
                    if ptype == "working_hours":
                        data = pattern.data
                        context_parts.append(
                            f"- 工作时间: {data.get('peak_start', 'N/A')}-{data.get('peak_end', 'N/A')} "
                            f"({data.get('timezone', 'N/A')})"
                        )
                    elif ptype == "communication_style":
                        context_parts.append(
                            f"- 沟通风格: {pattern.data.get('style', 'unknown')}"
                        )
                    elif ptype == "tool_preference":
                        tools = pattern.data.get("preferred_tools", [])
                        if tools:
                            context_parts.append(f"- 常用工具: {', '.join(tools[:3])}")

        # 项目信息
        if profile.projects:
            active_projects = [
                name for name, info in profile.projects.items()
                if info.get("status") == "active"
            ]
            if active_projects:
                context_parts.append(f"**活跃项目**: {', '.join(active_projects)}")

        return "\n".join(context_parts)

    def detect_behavioral_changes(
        self,
        user_id: str,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """检测行为变化

        Args:
            user_id: 用户 ID
            days: 分析天数

        Returns:
            检测到的行为变化列表
        """
        changes = []
        profile = self.get_profile(user_id)

        # 分析工作时间变化
        conv_times = self._conversation_times.get(user_id, [])
        if len(conv_times) >= 3:
            work_hours = self.behavior_analyzer.analyze_working_hours(conv_times)
            if work_hours:
                existing = profile.behavioral_patterns.get("working_hours")
                if existing:
                    # 检查是否有明显变化
                    old_data = existing.data
                    new_data = work_hours.data
                    if old_data.get("peak_start") != new_data.get("peak_start"):
                        changes.append({
                            "type": "working_hours_changed",
                            "old": old_data,
                            "new": new_data,
                            "confidence": work_hours.confidence
                        })
                else:
                    changes.append({
                        "type": "new_pattern",
                        "pattern_type": "working_hours",
                        "data": work_hours.data,
                        "confidence": work_hours.confidence
                    })

        # 分析工具偏好变化
        tool_history = self._tool_usage_history.get(user_id, [])
        if len(tool_history) >= 5:
            tool_pattern = self.behavior_analyzer.analyze_tool_preference(tool_history)
            if tool_pattern:
                existing = profile.behavioral_patterns.get("tool_preference")
                if existing:
                    old_tools = set(existing.data.get("preferred_tools", []))
                    new_tools = set(tool_pattern.data.get("preferred_tools", []))
                    if old_tools != new_tools:
                        changes.append({
                            "type": "tool_preference_changed",
                            "old": existing.data,
                            "new": tool_pattern.data,
                            "confidence": tool_pattern.confidence
                        })

        return changes

    def get_profile(self, user_id: str) -> UserProfile:
        """获取用户画像"""
        if user_id not in self._profiles:
            self._profiles[user_id] = UserProfile(user_id=user_id)
        return self._profiles[user_id]

    def save_profile(self, profile: UserProfile) -> None:
        """保存用户画像"""
        self._save_profile(profile)
        self._profiles[profile.user_id] = profile

    def load_profile(self, user_id: str) -> Optional[UserProfile]:
        """加载用户画像"""
        return self._profiles.get(user_id)

    def merge_profiles(self, profiles: List[UserProfile]) -> UserProfile:
        """合并多个用户画像"""
        if not profiles:
            return UserProfile(user_id="merged")

        # 以第一个画像为基础
        merged = profiles[0].model_copy(deep=True)

        for profile in profiles[1:]:
            # 合并偏好（取置信度较高的）
            for key, pref in profile.preferences.items():
                if key not in merged.preferences:
                    merged.preferences[key] = pref
                elif pref.confidence > merged.preferences[key].confidence:
                    merged.preferences[key] = pref

            # 合并行为模式
            for key, pattern in profile.behavioral_patterns.items():
                if key not in merged.behavioral_patterns:
                    merged.behavioral_patterns[key] = pattern
                elif pattern.confidence > merged.behavioral_patterns[key].confidence:
                    merged.behavioral_patterns[key] = pattern

            # 合并项目
            for proj_name, proj_info in profile.projects.items():
                if proj_name not in merged.projects:
                    merged.projects[proj_name] = proj_info

        merged.user_id = "merged"
        merged.updated_at = datetime.now()

        return merged

    def list_profiles(self) -> List[str]:
        """列出所有用户 ID"""
        return list(self._profiles.keys())

    def delete_profile(self, user_id: str) -> bool:
        """删除用户画像"""
        if user_id in self._profiles:
            del self._profiles[user_id]
            file_path = self.profile_dir / f"{user_id}.json"
            if file_path.exists():
                file_path.unlink()
            return True
        return False
