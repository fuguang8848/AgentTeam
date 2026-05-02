"""
ClawTeam 自主技能创建系统 - P13 实现

核心功能：
1. 检测对话中的技能创建意图
2. 从 learnings 提取知识
3. 生成 SKILL.md
4. 注册到 SpectrAI

参考架构设计文档实现
"""

from .auto_creator import (
    DetectedPattern,
    SkillSpec,
    SkillAutoCreator,
    SkillUsageTracker,
)

__all__ = [
    "DetectedPattern",
    "SkillSpec",
    "SkillAutoCreator",
    "SkillUsageTracker",
]
