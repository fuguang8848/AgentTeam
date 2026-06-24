"""
AgentTeam 哲学增强层 (Philosophical Enhancement Layer)

整合三大哲学框架：
1. Heidegger 技术座架 (Gestell) - 分析框架对问题的限制
2. Wiener 控制论 (Cybernetic Feedback) - 完整的反馈回路
3. Simon 有限理性 (Bounded Rationality) - 知识边界与任务协调

使用方法：
    from agentteam.philosophical import PhilosophicalIntegration
    
    team = CTTeam(...)
    phi = PhilosophicalIntegration(team)
    
    # 分析问题的座架约束
    result = phi.analyze_task_constraints("某个复杂任务")
    
    # 检查反馈回路健康
    feedback_report = phi.get_cybernetic_report()
    
    # 检查任务分配是否考虑有限理性
    can_assign, missing = phi.bounded_rationality_tracker.can_assign_task(
        "agent_name", ["python", "distributed"]
    )
"""

from agentteam.philosophical.bounded_rationality import (
    BoundedRationalityTracker,
    KnowledgeBoundary,
    UncertaintyDeclaration,
)
from agentteam.philosophical.cybernetic_feedback import (
    CyberneticFeedbackLoop,
    FeedbackLoopConfig,
    FeedbackStatus,
    ExecutionFeedback,
)
from agentteam.philosophical.gestell_analyzer import (
    GestellAnalyzer,
    GestellLimitation,
    UnaskableQuestion,
    GestellLayer,
)

__all__ = [
    # Bounded Rationality
    "BoundedRationalityTracker",
    "KnowledgeBoundary", 
    "UncertaintyDeclaration",
    # Cybernetic Feedback
    "CyberneticFeedbackLoop",
    "FeedbackLoopConfig",
    "FeedbackStatus",
    "ExecutionFeedback",
    # Gestell
    "GestellAnalyzer",
    "GestellLimitation",
    "UnaskableQuestion",
    "GestellLayer",
]
