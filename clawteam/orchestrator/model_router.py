"""Intelligent Model Router - P38: Auto-select optimal model based on task complexity.

This module provides:
- Task complexity analysis (keyword + heuristics based)
- Model tier selection based on complexity + task type
- Cost-optimized routing (use cheapest capable model)
- Integration with ProviderSelector for within-provider model selection

Example:
    router = ModelRouter(provider_selector)
    result = router.route_task("设计一个分布式缓存系统", task_type=TaskType.architecture)
    # Returns model selection: gpt-4o-mini for low complexity, o1 for high complexity
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from clawteam.orchestrator.provider_selector import ProviderSelector

logger = logging.getLogger(__name__)


class ComplexityLevel(str, Enum):
    """Task complexity levels (1-10)."""

    TRIVIAL = "trivial"  # 1-2: Simple facts, formatting, yes/no
    LOW = "low"  # 3-4: Simple tasks, short code snippets
    MEDIUM = "medium"  # 5-6: Standard tasks, moderate reasoning
    HIGH = "high"  # 7-8: Complex tasks, deep reasoning
    EXPERT = "expert"  # 9-10: Expert-level, architecture, system design


class ModelTier(str, Enum):
    """Model tiers based on capability/cost tradeoff."""

    FAST = "fast"  # Cheapest, fastest - for trivial/low complexity
    BALANCED = "balanced"  # Mid-range - for medium complexity
    POWERFUL = "powerful"  # Most capable - for high/expert complexity


class TaskType(str, Enum):
    """Types of tasks for routing (mirrors ProviderSelector.TaskType)."""

    architecture = "architecture"
    code_generation = "code_generation"
    code_review = "code_review"
    debugging = "debugging"
    documentation = "documentation"
    analysis = "analysis"
    testing = "testing"
    refactoring = "refactoring"
    research = "research"
    general = "general"


@dataclass
class RoutingDecision:
    """Result of model routing decision."""

    complexity: ComplexityLevel
    complexity_score: int  # 1-10
    model_tier: ModelTier
    recommended_model: str
    reasoning: str
    cost_saving: str  # e.g., "~70% cheaper than powerhouse model"


class TaskComplexityAnalyzer:
    """Analyzes task description to determine complexity level.

    Uses keyword matching + heuristics to score task complexity.
    """

    # Complexity indicators (higher = more complex)
    COMPLEXITY_KEYWORDS = {
        # Expert level (9-10)
        "expert": [
            "架构设计",
            "系统架构",
            "分布式系统",
            "微服务架构",
            "高并发",
            "高并发架构",
            "architecture design",
            "system architecture",
            "distributed system",
            "microservices",
            "high concurrency",
            "scalability",
            "灾难恢复",
            "多活",
            "单元化",
            "中台",
            "平台化",
            "service mesh",
            "kubernetes",
            "云原生",
            "CNCF",
            "多机房",
            "容灾",
            "异地多活",
            "全球部署",
            "单元化架构",
            "分层架构",
            "CQRS",
            "ES",
        ],
        # High level (7-8)
        "high": [
            "优化",
            "性能优化",
            "重构",
            "重构代码",
            "重新设计",
            "optimize",
            "performance tuning",
            "refactor",
            "redesign",
            "多线程",
            "并发",
            "异步",
            "缓存",
            "队列",
            "multithreading",
            "concurrency",
            "async",
            "cache",
            "queue",
            "安全",
            "加密",
            "认证",
            "授权",
            "权限",
            "security",
            "encryption",
            "authentication",
            "authorization",
            "数据库设计",
            "表结构设计",
            "索引优化",
            "database design",
            "schema design",
            "index optimization",
            "api设计",
            "接口设计",
            "协议设计",
            "API design",
            "interface design",
            "protocol design",
            "调试",
            "复杂bug",
            "根因分析",
            "troubleshoot",
            "debug complex",
            "性能瓶颈",
            "瓶颈分析",
            "根因定位",
            "数据迁移",
            "迁移方案",
            "升级方案",
            "压力测试",
            "负载测试",
            "性能测试",
        ],
        # Medium level (5-6)
        "medium": [
            "实现",
            "编写",
            "开发",
            "创建",
            "implement",
            "create",
            "develop",
            "修改",
            "更新",
            "添加功能",
            "modify",
            "update",
            "add feature",
            "查询",
            "统计",
            "报表",
            "query",
            "statistics",
            "report",
            "验证",
            "检查",
            "测试用例",
            "validate",
            "verify",
            "test case",
            "文档",
            "注释",
            "说明",
            "documentation",
            "comment",
            "spec",
            "部署",
            "配置",
            "安装",
            "deploy",
            "configure",
            "setup",
            "code review",
            "代码审查",
            "review",
            "评审",
        ],
        # Low level (3-4)
        "low": [
            "简单",
            "小",
            "修复",
            "fix",
            "simple",
            "small",
            "打印",
            "输出",
            "console.log",
            "print",
            "echo",
            "变量",
            "简单逻辑",
            "variable",
            "simple logic",
            "格式化",
            "转换",
            "format",
            "convert",
            "transform",
            "读取",
            "写入",
            "文件操作",
            "read",
            "write",
            "file operation",
            "问答题",
            "是什么",
            "什么意思",
            "what is",
            "how does",
        ],
    }

    # Task type indicators
    TASK_TYPE_KEYWORDS = {
        TaskType.architecture: [
            "架构",
            "架构设计",
            "系统设计",
            "architecture",
            "system design",
            "微服务",
            "service",
            "mesh",
            "platform",
        ],
        TaskType.code_generation: [
            "实现",
            "编写",
            "创建",
            "generate",
            "implement",
            "create",
            "写代码",
            "代码生成",
            "code generation",
        ],
        TaskType.code_review: [
            "review",
            "审查",
            "评审",
            "code review",
            "代码审查",
            "优化建议",
            "improvement",
        ],
        TaskType.debugging: [
            "调试",
            "debug",
            "bug",
            "错误",
            "修复",
            "fix",
            "error",
            "问题",
            "issue",
            "崩溃",
            "crash",
            "异常",
            "exception",
        ],
        TaskType.documentation: [
            "文档",
            "说明",
            "注释",
            "doc",
            "comment",
            "readme",
            "规范",
            "standard",
            "specification",
        ],
        TaskType.analysis: [
            "分析",
            "分析问题",
            "调研",
            "analyze",
            "analysis",
            "investigate",
            "原因",
            "为什么",
            "why",
            "reason",
        ],
        TaskType.testing: [
            "测试",
            "test",
            "用例",
            "case",
            "测试用例",
            "unit test",
            "integration test",
            "端到端",
            "e2e",
        ],
        TaskType.refactoring: [
            "重构",
            "refactor",
            "重写",
            "rewrite",
            "优化代码",
            "code optimization",
            "清理",
            "clean up",
            "代码质量",
        ],
        TaskType.research: [
            "调研",
            "研究",
            "research",
            "对比",
            "compare",
            "选型",
            "technology selection",
            "方案对比",
        ],
        TaskType.general: [
            "帮助",
            "help",
            "问题",
            "question",
            "ask",
            "怎么",
            "how to",
        ],
    }

    def analyze(self, task_description: str, task_type: TaskType = TaskType.general) -> tuple[ComplexityLevel, int]:
        """Analyze task description and return complexity level + score.

        Args:
            task_description: The task description in Chinese or English
            task_type: The type of task (used as hint)

        Returns:
            Tuple of (ComplexityLevel, score 1-10)
        """
        text = task_description.lower()

        # Score tracking
        score = 5  # Default to medium
        matched_level = "medium"

        # Check complexity keywords
        for level_name, keywords in self.COMPLEXITY_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    if level_name == "expert":
                        score = max(score, 9)
                        matched_level = "expert"
                    elif level_name == "high":
                        score = max(score, 7)
                        matched_level = "high"
                    elif level_name == "medium":
                        score = max(score, 5)
                        matched_level = "medium"
                    elif level_name == "low":
                        score = min(score, 4)
                        matched_level = "low"

        # Length-based adjustment (longer tasks = more complex)
        length = len(task_description)
        if length > 500:
            score += 1
        elif length > 1000:
            score += 1
        elif length < 50:
            score -= 1

        # Check for code blocks (indicates implementation work)
        code_blocks = len(re.findall(r"```[\s\S]*?```", task_description))
        if code_blocks >= 3:
            score += 1

        # Check for question marks (might be simple questions)
        question_marks = task_description.count("?") + task_description.count("？")
        if question_marks >= 1:
            # Single question marks suggest a simple Q&A
            score = min(score, 4)
        if question_marks >= 3:
            score = min(score, 3)

        # Check for answer indicators (strongly suggests Q&A = low complexity)
        if re.search(r"(?:^|\s)(?:是|为|答案|结果)\s*[:：]", text):
            score = min(score, 2)

        # Clamp score to 1-10
        score = max(1, min(10, score))

        # Map score to level
        if score <= 2:
            level = ComplexityLevel.TRIVIAL
        elif score <= 4:
            level = ComplexityLevel.LOW
        elif score <= 6:
            level = ComplexityLevel.MEDIUM
        elif score <= 8:
            level = ComplexityLevel.HIGH
        else:
            level = ComplexityLevel.EXPERT

        logger.debug(f"Task complexity: {level.value} (score={score}) for: {task_description[:50]}...")

        return level, score


class ModelRoutingPolicy:
    """Routing policy that maps task type + complexity to model tier.

    This is configurable - users can override the default mappings.
    """

    # Default routing table: (task_type, complexity) -> model_tier
    # Uses a class method to return the default so each instance gets its own copy
    _DEFAULT_POLICY_BASE: dict[tuple[TaskType, ComplexityLevel], ModelTier] = {
        # Architecture tasks need powerful models even at medium complexity
        (TaskType.architecture, ComplexityLevel.TRIVIAL): ModelTier.BALANCED,
        (TaskType.architecture, ComplexityLevel.LOW): ModelTier.BALANCED,
        (TaskType.architecture, ComplexityLevel.MEDIUM): ModelTier.POWERFUL,
        (TaskType.architecture, ComplexityLevel.HIGH): ModelTier.POWERFUL,
        (TaskType.architecture, ComplexityLevel.EXPERT): ModelTier.POWERFUL,
        # Code generation: balanced for most, powerful for high
        (TaskType.code_generation, ComplexityLevel.TRIVIAL): ModelTier.FAST,
        (TaskType.code_generation, ComplexityLevel.LOW): ModelTier.FAST,
        (TaskType.code_generation, ComplexityLevel.MEDIUM): ModelTier.BALANCED,
        (TaskType.code_generation, ComplexityLevel.HIGH): ModelTier.POWERFUL,
        (TaskType.code_generation, ComplexityLevel.EXPERT): ModelTier.POWERFUL,
        # Debugging needs powerful models for complex issues
        (TaskType.debugging, ComplexityLevel.TRIVIAL): ModelTier.FAST,
        (TaskType.debugging, ComplexityLevel.LOW): ModelTier.FAST,
        (TaskType.debugging, ComplexityLevel.MEDIUM): ModelTier.BALANCED,
        (TaskType.debugging, ComplexityLevel.HIGH): ModelTier.POWERFUL,
        (TaskType.debugging, ComplexityLevel.EXPERT): ModelTier.POWERFUL,
        # Code review: balanced
        (TaskType.code_review, ComplexityLevel.TRIVIAL): ModelTier.FAST,
        (TaskType.code_review, ComplexityLevel.LOW): ModelTier.BALANCED,
        (TaskType.code_review, ComplexityLevel.MEDIUM): ModelTier.BALANCED,
        (TaskType.code_review, ComplexityLevel.HIGH): ModelTier.POWERFUL,
        (TaskType.code_review, ComplexityLevel.EXPERT): ModelTier.POWERFUL,
        # Documentation: fast for simple docs
        (TaskType.documentation, ComplexityLevel.TRIVIAL): ModelTier.FAST,
        (TaskType.documentation, ComplexityLevel.LOW): ModelTier.FAST,
        (TaskType.documentation, ComplexityLevel.MEDIUM): ModelTier.BALANCED,
        (TaskType.documentation, ComplexityLevel.HIGH): ModelTier.BALANCED,
        (TaskType.documentation, ComplexityLevel.EXPERT): ModelTier.POWERFUL,
        # Analysis: needs powerful for complex analysis
        (TaskType.analysis, ComplexityLevel.TRIVIAL): ModelTier.FAST,
        (TaskType.analysis, ComplexityLevel.LOW): ModelTier.BALANCED,
        (TaskType.analysis, ComplexityLevel.MEDIUM): ModelTier.BALANCED,
        (TaskType.analysis, ComplexityLevel.HIGH): ModelTier.POWERFUL,
        (TaskType.analysis, ComplexityLevel.EXPERT): ModelTier.POWERFUL,
        # Testing: balanced for most
        (TaskType.testing, ComplexityLevel.TRIVIAL): ModelTier.FAST,
        (TaskType.testing, ComplexityLevel.LOW): ModelTier.FAST,
        (TaskType.testing, ComplexityLevel.MEDIUM): ModelTier.BALANCED,
        (TaskType.testing, ComplexityLevel.HIGH): ModelTier.BALANCED,
        (TaskType.testing, ComplexityLevel.EXPERT): ModelTier.POWERFUL,
        # Refactoring: needs powerful
        (TaskType.refactoring, ComplexityLevel.TRIVIAL): ModelTier.BALANCED,
        (TaskType.refactoring, ComplexityLevel.LOW): ModelTier.BALANCED,
        (TaskType.refactoring, ComplexityLevel.MEDIUM): ModelTier.POWERFUL,
        (TaskType.refactoring, ComplexityLevel.HIGH): ModelTier.POWERFUL,
        (TaskType.refactoring, ComplexityLevel.EXPERT): ModelTier.POWERFUL,
        # Research: balanced
        (TaskType.research, ComplexityLevel.TRIVIAL): ModelTier.FAST,
        (TaskType.research, ComplexityLevel.LOW): ModelTier.BALANCED,
        (TaskType.research, ComplexityLevel.MEDIUM): ModelTier.BALANCED,
        (TaskType.research, ComplexityLevel.HIGH): ModelTier.POWERFUL,
        (TaskType.research, ComplexityLevel.EXPERT): ModelTier.POWERFUL,
        # General: simple routing
        (TaskType.general, ComplexityLevel.TRIVIAL): ModelTier.FAST,
        (TaskType.general, ComplexityLevel.LOW): ModelTier.FAST,
        (TaskType.general, ComplexityLevel.MEDIUM): ModelTier.BALANCED,
        (TaskType.general, ComplexityLevel.HIGH): ModelTier.POWERFUL,
        (TaskType.general, ComplexityLevel.EXPERT): ModelTier.POWERFUL,
    }

    def __init__(self):
        """Initialize with a copy of the default policy."""
        # Each instance gets its own copy of the policy
        self._policy = dict(self._DEFAULT_POLICY_BASE)

    def get_model_tier(self, task_type: TaskType, complexity: ComplexityLevel) -> ModelTier:
        """Get the recommended model tier for a task type + complexity combination."""
        return self._policy.get(
            (task_type, complexity),
            ModelTier.BALANCED,  # Default fallback
        )

    def set_policy(self, task_type: TaskType, complexity: ComplexityLevel, tier: ModelTier) -> None:
        """Override a routing policy entry for this instance."""
        self._policy[(task_type, complexity)] = tier


class ModelRouter:
    """Intelligent model router that selects optimal model based on task complexity.

    This is P38 - the intelligent model routing feature.
    """

    # Default model tiers (fallback when no config is provided)
    DEFAULT_MODEL_TIERS = {
        "fast": [
            "gpt-4o-mini",
            "claude-3-haiku",
            "gemini-1.5-flash",
            "minimax/MiniMax-M2.7",
        ],
        "balanced": [
            "gpt-4o",
            "claude-3.5-sonnet",
            "gemini-1.5-pro",
            "minimax/MiniMax-M2.7-highspeed",
        ],
        "powerful": [
            "gpt-4o",
            "claude-3.5-sonnet",
            "claude-3-opus",
            "o1",
            "o1-pro",
            "o3",
            "o3-mini",
            "gemini-2.0-flash-thinking",
        ],
    }

    def __init__(self, provider_selector: "ProviderSelector | None" = None):
        """Initialize the model router.

        Args:
            provider_selector: Optional ProviderSelector for integration.
                               If not provided, uses default model selection.
        """
        self.provider_selector = provider_selector
        self.complexity_analyzer = TaskComplexityAnalyzer()
        self.routing_policy = ModelRoutingPolicy()
        
        # Load model tiers from config or use defaults
        self._model_tiers = self._load_model_tiers()

    def _load_model_tiers(self) -> dict:
        """Load model tiers from environment variable or file config.
        
        Environment Variables:
            CLAWTEAM_MODEL_TIERS_JSON: JSON string with model tier config
            CLAWTEAM_MODEL_TIERS_FILE: Path to JSON config file
        """
        import json
        import os
        
        # Try environment variable first
        env_json = os.environ.get("CLAWTEAM_MODEL_TIERS_JSON")
        if env_json:
            try:
                return json.loads(env_json)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse CLAWTEAM_MODEL_TIERS_JSON: {e}")
        
        # Try config file
        config_file = os.environ.get("CLAWTEAM_MODEL_TIERS_FILE")
        if config_file:
            try:
                with open(config_file, "r") as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                logger.warning(f"Failed to load model tiers from {config_file}: {e}")
        
        # Fall back to defaults
        return self.DEFAULT_MODEL_TIERS.copy()

    @property
    def MODEL_TIERS(self) -> dict:
        """Get current model tiers configuration."""
        return self._model_tiers

    def set_model_tiers(self, tiers: dict) -> None:
        """Set model tiers configuration (for testing/dynamic config)."""
        self._model_tiers = tiers

    def route_task(
        self,
        task_description: str,
        task_type: TaskType = TaskType.general,
        preferred_tier: ModelTier | None = None,
        preferred_model: str | None = None,
    ) -> RoutingDecision:
        """Route a task to the optimal model.

        Args:
            task_description: Description of the task
            task_type: Type of task (code_generation, debugging, etc.)
            preferred_tier: Override the tier selection
            preferred_model: Use a specific model directly

        Returns:
            RoutingDecision with complexity, tier, and recommended model
        """
        # If preferred model is specified, use it directly
        if preferred_model:
            return RoutingDecision(
                complexity=ComplexityLevel.MEDIUM,
                complexity_score=5,
                model_tier=ModelTier.BALANCED,
                recommended_model=preferred_model,
                reasoning=f"User-specified model: {preferred_model}",
                cost_saving="N/A (user-specified)",
            )

        # Analyze task complexity
        complexity, score = self.complexity_analyzer.analyze(task_description, task_type)

        # Get recommended tier
        if preferred_tier:
            tier = preferred_tier
        else:
            tier = self.routing_policy.get_model_tier(task_type, complexity)

        # Select model from tier
        model = self._select_model_for_tier(tier, task_type)

        # Calculate cost saving (rough estimate)
        cost_saving = self._estimate_cost_saving(tier)

        reasoning = f"{task_type.value} task with {complexity.value} complexity (score={score}) → {tier.value} tier"

        return RoutingDecision(
            complexity=complexity,
            complexity_score=score,
            model_tier=tier,
            recommended_model=model,
            reasoning=reasoning,
            cost_saving=cost_saving,
        )

    def _select_model_for_tier(
        self,
        tier: ModelTier,
        task_type: TaskType,
    ) -> str:
        """Select a specific model for the given tier."""
        tier_key = tier.value  # fast, balanced, powerful
        models = self._model_tiers.get(tier_key, [])

        if not models:
            # Fallback to balanced
            models = self._model_tiers.get("balanced", self.DEFAULT_MODEL_TIERS["balanced"])

        # For certain task types, prefer specific models
        if task_type == TaskType.architecture and tier == ModelTier.POWERFUL:
            # For architecture, prefer models known for reasoning
            for model in models:
                if "o1" in model or "o3" in model or "opus" in model:
                    return model

        # Return first available model in tier
        return models[0] if models else "minimax/MiniMax-M2.7"

    def _estimate_cost_saving(self, tier: ModelTier) -> str:
        """Estimate cost saving compared to most powerful model."""
        if tier == ModelTier.FAST:
            return "~80-90% cheaper than powerful tier"
        elif tier == ModelTier.BALANCED:
            return "~40-60% cheaper than powerful tier"
        else:
            return "Full cost (powerful tier)"


def create_model_router(provider_selector: "ProviderSelector | None" = None) -> ModelRouter:
    """Factory function to create a ModelRouter instance."""
    return ModelRouter(provider_selector)
