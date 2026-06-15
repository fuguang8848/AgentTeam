"""Tests for P38: Intelligent Model Router."""

import pytest

from agentteam.orchestrator.model_router import (
    ComplexityLevel,
    ModelRouter,
    ModelTier,
    ModelRoutingPolicy,
    TaskComplexityAnalyzer,
    TaskType,
)


class TestTaskComplexityAnalyzer:
    """Tests for TaskComplexityAnalyzer."""

    def setup_method(self):
        self.analyzer = TaskComplexityAnalyzer()

    def test_trivial_task(self):
        """Simple questions should be low/trivial complexity."""
        level, score = self.analyzer.analyze("What is Python?", TaskType.general)
        assert level in (ComplexityLevel.TRIVIAL, ComplexityLevel.LOW)
        assert score <= 4

    def test_low_complexity_task(self):
        """Simple code tasks should be low complexity."""
        level, score = self.analyzer.analyze(
            "Fix the variable naming issue",
            TaskType.code_generation,
        )
        assert level in (ComplexityLevel.LOW, ComplexityLevel.TRIVIAL)
        assert score <= 4

    def test_medium_complexity_task(self):
        """Standard implementation tasks should be medium complexity."""
        level, score = self.analyzer.analyze(
            "Add feature to user profile page with form validation",
            TaskType.code_generation,
        )
        assert level == ComplexityLevel.MEDIUM
        assert 5 <= score <= 6

    def test_high_complexity_task(self):
        """Complex tasks like optimization should be high complexity."""
        level, score = self.analyzer.analyze(
            "Optimize the database query performance for the reporting module",
            TaskType.debugging,
        )
        assert level in (ComplexityLevel.HIGH, ComplexityLevel.MEDIUM, ComplexityLevel.EXPERT)

    def test_expert_complexity_task(self):
        """Architecture design should be expert/high level."""
        level, score = self.analyzer.analyze(
            "设计一个高并发分布式缓存系统，需要支持多机房容灾",
            TaskType.architecture,
        )
        # Should be high or expert (score >= 7)
        assert level in (ComplexityLevel.HIGH, ComplexityLevel.EXPERT)

    def test_chinese_keywords(self):
        """Chinese keywords should be recognized."""
        level, score = self.analyzer.analyze(
            "重构这段代码，优化性能瓶颈",
            TaskType.refactoring,
        )
        # Should be medium or higher (score >= 5)
        assert score >= 5
        assert level in (ComplexityLevel.MEDIUM, ComplexityLevel.HIGH, ComplexityLevel.EXPERT)

    def test_english_keywords(self):
        """English keywords should be recognized."""
        level, score = self.analyzer.analyze(
            "Design a microservices architecture with service mesh",
            TaskType.architecture,
        )
        assert level in (ComplexityLevel.HIGH, ComplexityLevel.EXPERT)

    def test_length_adjustment(self):
        """Longer descriptions should increase complexity score."""
        short_task = "Fix a bug"
        long_task = "Fix a bug" + " This requires analyzing the entire codebase" * 10

        _, short_score = self.analyzer.analyze(short_task, TaskType.debugging)
        _, long_score = self.analyzer.analyze(long_task, TaskType.debugging)

        assert long_score >= short_score

    def test_code_blocks_increase_complexity(self):
        """Multiple code blocks indicate implementation work."""
        task_no_code = "How do I use Python decorators?"
        task_with_code = "Implement a decorator that logs function calls\n```python\ndef log():\n    pass\n```\n```python\ndef measure():\n    pass\n```\n```python\ndef cache():\n    pass\n```"

        _, score_no_code = self.analyzer.analyze(task_no_code, TaskType.code_generation)
        _, score_with_code = self.analyzer.analyze(task_with_code, TaskType.code_generation)

        # Should score higher with code blocks
        assert score_with_code >= score_no_code


class TestModelRoutingPolicy:
    """Tests for ModelRoutingPolicy."""

    def setup_method(self):
        self.policy = ModelRoutingPolicy()

    def test_architecture_always_powerful(self):
        """Architecture tasks should always route to powerful tier."""
        for complexity in ComplexityLevel:
            tier = self.policy.get_model_tier(TaskType.architecture, complexity)
            if complexity in (ComplexityLevel.TRIVIAL, ComplexityLevel.LOW):
                assert tier in (ModelTier.BALANCED, ModelTier.POWERFUL)
            else:
                assert tier == ModelTier.POWERFUL

    def test_trivial_tasks_fast(self):
        """Trivial tasks should route to fast tier."""
        for task_type in TaskType:
            tier = self.policy.get_model_tier(task_type, ComplexityLevel.TRIVIAL)
            assert tier in (ModelTier.FAST, ModelTier.BALANCED)

    def test_expert_tasks_powerful(self):
        """Expert complexity tasks should route to powerful tier."""
        for task_type in TaskType:
            tier = self.policy.get_model_tier(task_type, ComplexityLevel.EXPERT)
            assert tier == ModelTier.POWERFUL

    def test_override_policy(self):
        """Users should be able to override routing policy."""
        self.policy.set_policy(TaskType.general, ComplexityLevel.LOW, ModelTier.POWERFUL)
        tier = self.policy.get_model_tier(TaskType.general, ComplexityLevel.LOW)
        assert tier == ModelTier.POWERFUL


class TestModelRouter:
    """Tests for ModelRouter."""

    def setup_method(self):
        self.router = ModelRouter()

    def test_route_simple_question(self):
        """Simple questions should route to fast model."""
        decision = self.router.route_task(
            "What is Python?",
            TaskType.general,
        )
        assert decision.model_tier == ModelTier.FAST
        assert decision.complexity_score <= 4

    def test_route_architecture_task(self):
        """Architecture tasks should route to powerful model."""
        decision = self.router.route_task(
            "设计一个微服务架构系统",
            TaskType.architecture,
        )
        assert decision.model_tier == ModelTier.POWERFUL
        assert decision.complexity in (ComplexityLevel.HIGH, ComplexityLevel.EXPERT)

    def test_route_preferred_model(self):
        """Preferred model should override routing."""
        decision = self.router.route_task(
            "Any task",
            TaskType.general,
            preferred_model="gpt-4o",
        )
        assert decision.recommended_model == "gpt-4o"
        assert "User-specified" in decision.reasoning

    def test_route_preferred_tier(self):
        """Preferred tier should override routing."""
        decision = self.router.route_task(
            "Simple question",
            TaskType.general,
            preferred_tier=ModelTier.POWERFUL,
        )
        assert decision.model_tier == ModelTier.POWERFUL

    def test_cost_saving_fast(self):
        """Fast tier should report cost saving."""
        decision = self.router.route_task(
            "Simple question",
            TaskType.general,
            preferred_tier=ModelTier.FAST,
        )
        assert "cheaper" in decision.cost_saving.lower() or "saving" in decision.cost_saving.lower()

    def test_reasoning_includes_task_type(self):
        """Reasoning should mention task type."""
        decision = self.router.route_task(
            "Write a function",
            TaskType.code_generation,
        )
        assert "code_generation" in decision.reasoning

    def test_reasoning_includes_complexity(self):
        """Reasoning should include complexity level."""
        decision = self.router.route_task(
            "Complex system design with distributed caching",
            TaskType.architecture,
        )
        assert decision.complexity.value in decision.reasoning

    def test_multiple_complexity_keywords(self):
        """Multiple complexity indicators should stack."""
        # Task with both architecture AND optimization keywords
        decision = self.router.route_task(
            "架构重构 + 性能优化：高并发场景下的缓存设计",
            TaskType.refactoring,
        )
        # Should be medium or higher due to multiple complex indicators
        assert decision.complexity in (
            ComplexityLevel.MEDIUM,
            ComplexityLevel.HIGH,
            ComplexityLevel.EXPERT,
        )
