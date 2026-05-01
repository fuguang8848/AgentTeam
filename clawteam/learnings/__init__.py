"""
ClawTeam .learnings 自动闭环系统

参考 Hermes 机制实现：
- .learnings 文件格式解析
- 错误/修正/技巧自动提取
- 结构化存储
- 与 session 关联
- 查询/回放
- 应用到新任务上下文注入
- 去重/合并/优先级排序
- P12 自动闭环集成
"""

from clawteam.learnings.auto_capture import (
    LearningType,
    ExperienceEntry,
    AutoCaptureEngine,
    PatternDetector,
)
from clawteam.learnings.integration import (
    LearningsIntegrator,
    get_integrator,
)

__all__ = [
    "LearningType",
    "ExperienceEntry",
    "AutoCaptureEngine",
    "PatternDetector",
    "LearningsIntegrator",
    "get_integrator",
]
