"""Tests for Supervisor Engine - AI autonomous task orchestration."""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock

from agentteam.orchestrator.supervisor import (
    SupervisorEngine,
    TaskPlan,
    ExecutionResult,
    VerificationResult,
    DecompositionPattern,
    DecompositionRule,
    DEFAULT_RULES,
    get_supervisor,
)
from agentteam.orchestrator.provider_selector import (
    ProviderSelector,
    ProviderStatus,
    TaskType,
    SelectionResult,
)
from agentteam.team.models import TaskItem, TaskStatus, TaskPriority


@pytest.fixture
def supervisor():
    """Create a SupervisorEngine instance for testing."""
    return SupervisorEngine("test_team")


@pytest.fixture
def sample_task():
    """Create a sample TaskItem for testing."""
    return TaskItem(
        id="test-001",
        subject="[1/3] Analyze requirements",
        description="Subtask",
        status=TaskStatus.pending,
        assigned_to="",
        depends_on=[],
        created_at=datetime.now(timezone.utc).isoformat(),
        priority=TaskPriority.medium,
    )


class TestDecompositionPatterns:
    """Tests for goal pattern matching."""

    def test_match_implement_feature(self, supervisor):
        """Test matching implement feature pattern."""
        goal = "实现用户认证功能"
        pattern, rule = supervisor._match_goal_pattern(goal)
        assert pattern == DecompositionPattern.IMPLEMENT_FEATURE
        assert len(rule.subtask_templates) == 5

    def test_match_fix_bug(self, supervisor):
        """Test matching fix bug pattern."""
        goal = "修复登录页面的bug"
        pattern, rule = supervisor._match_goal_pattern(goal)
        assert pattern == DecompositionPattern.FIX_BUG

    def test_match_add_test(self, supervisor):
        """Test matching add test pattern."""
        goal = "添加单元测试覆盖"
        pattern, rule = supervisor._match_goal_pattern(goal)
        assert pattern == DecompositionPattern.ADD_TEST

    def test_match_refactor(self, supervisor):
        """Test matching refactor pattern."""
        goal = "重构代码结构优化性能"
        pattern, rule = supervisor._match_goal_pattern(goal)
        assert pattern == DecompositionPattern.REFACTOR

    def test_match_document(self, supervisor):
        """Test matching document pattern."""
        goal = "编写API文档说明"
        pattern, rule = supervisor._match_goal_pattern(goal)
        assert pattern == DecompositionPattern.DOCUMENT

    def test_match_analyze(self, supervisor):
        """Test matching analyze pattern."""
        goal = "分析系统性能瓶颈"
        pattern, rule = supervisor._match_goal_pattern(goal)
        assert pattern == DecompositionPattern.ANALYZE

    def test_match_deploy(self, supervisor):
        """Test matching deploy pattern."""
        goal = "部署到生产环境"
        pattern, rule = supervisor._match_goal_pattern(goal)
        assert pattern == DecompositionPattern.DEPLOY

    def test_match_review(self, supervisor):
        """Test matching review pattern."""
        goal = "审查代码质量"
        pattern, rule = supervisor._match_goal_pattern(goal)
        assert pattern == DecompositionPattern.REVIEW

    def test_match_general(self, supervisor):
        """Test defaulting to general pattern."""
        goal = "做一些事情"
        pattern, rule = supervisor._match_goal_pattern(goal)
        assert pattern == DecompositionPattern.GENERAL

    def test_match_english(self, supervisor):
        """Test matching English keywords."""
        goal = "Implement user authentication"
        pattern, rule = supervisor._match_goal_pattern(goal)
        assert pattern == DecompositionPattern.IMPLEMENT_FEATURE


class TestTaskDecomposition:
    """Tests for goal decomposition."""

    def test_decompose_count(self, supervisor):
        """Test decomposition creates correct task count."""
        goal = "实现用户认证功能"
        plan = supervisor.plan(goal)
        assert len(plan.tasks) == 5

    def test_decompose_unique_ids(self, supervisor):
        """Test tasks have unique IDs."""
        goal = "实现用户认证功能"
        plan = supervisor.plan(goal)
        task_ids = [t.id for t in plan.tasks]
        assert len(task_ids) == len(set(task_ids))

    def test_decompose_pending_status(self, supervisor):
        """Test tasks start with pending status."""
        goal = "实现用户认证功能"
        plan = supervisor.plan(goal)
        for task in plan.tasks:
            assert task.status == TaskStatus.pending

    def test_decompose_providers(self, supervisor):
        """Test providers are assigned."""
        goal = "实现用户认证功能"
        plan = supervisor.plan(goal)
        assert len(plan.provider_assignments) == len(plan.tasks)


class TestProviderSelection:
    """Tests for provider selection."""

    def test_infer_architecture(self, supervisor):
        """Test inferring architecture task type."""
        task_type = supervisor._infer_task_type("分析需求并设计架构方案")
        assert task_type == TaskType.architecture

    def test_infer_code(self, supervisor):
        """Test inferring code generation task type."""
        task_type = supervisor._infer_task_type("实现核心功能代码")
        assert task_type == TaskType.code_generation

    def test_infer_testing(self, supervisor):
        """Test inferring testing task type."""
        task_type = supervisor._infer_task_type("编写单元测试")
        assert task_type == TaskType.testing

    def test_infer_documentation(self, supervisor):
        """Test inferring documentation task type."""
        task_type = supervisor._infer_task_type("更新文档")
        assert task_type == TaskType.documentation

    def test_infer_analysis(self, supervisor):
        """Test inferring analysis task type."""
        task_type = supervisor._infer_task_type("分析错误日志")
        assert task_type == TaskType.analysis

    def test_infer_debugging(self, supervisor):
        """Test inferring debugging task type."""
        task_type = supervisor._infer_task_type("修复bug问题")
        assert task_type == TaskType.debugging

    def test_infer_general(self, supervisor):
        """Test defaulting to general task type."""
        task_type = supervisor._infer_task_type("执行主要工作")
        assert task_type == TaskType.general


class TestExecution:
    """Tests for plan execution."""

    def test_execute_result(self, supervisor):
        """Test execution creates ExecutionResult."""
        goal = "实现用户认证功能"
        plan = supervisor.plan(goal)
        result = supervisor.execute(plan.id)
        assert result is not None
        assert result.plan_id == plan.id
        assert result.status == "completed"

    def test_execute_completed(self, supervisor):
        """Test execution marks tasks completed."""
        goal = "实现用户认证功能"
        plan = supervisor.plan(goal)
        result = supervisor.execute(plan.id)
        assert len(result.completed_tasks) == len(plan.tasks)


class TestVerification:
    """Tests for task verification."""

    def test_verify_empty(self, supervisor, sample_task):
        """Test empty content fails."""
        result = supervisor.verify(sample_task, "")
        assert not result.is_valid

    def test_verify_short(self, supervisor, sample_task):
        """Test short content fails."""
        result = supervisor.verify(sample_task, "short")
        assert not result.is_valid

    def test_verify_code_no_code(self, supervisor):
        """Test code task without code fails."""
        task = TaskItem(
            id="t2",
            subject="实现代码",
            description="",
            status=TaskStatus.completed,
            assigned_to="",
            depends_on=["t1"],
            created_at=datetime.now(timezone.utc).isoformat(),
            priority=TaskPriority.medium,
        )
        result = supervisor.verify(task, "Design doc")
        assert not result.is_valid

    def test_verify_test_no_assert(self, supervisor):
        """Test task without assertions fails."""
        task = TaskItem(
            id="t3",
            subject="编写测试",
            description="",
            status=TaskStatus.completed,
            assigned_to="",
            depends_on=["t2"],
            created_at=datetime.now(timezone.utc).isoformat(),
            priority=TaskPriority.medium,
        )
        result = supervisor.verify(task, "Some random notes")
        assert not result.is_valid

    def test_verify_good(self, supervisor, sample_task):
        """Test good content passes."""
        result = supervisor.verify(sample_task, "Architecture design with components and flow analysis 结论")
        assert result.is_valid


class TestPlanManagement:
    """Tests for plan management."""

    def test_get_plan(self, supervisor):
        """Test get_plan returns created plan."""
        goal = "实现用户认证功能"
        plan = supervisor.plan(goal)
        retrieved = supervisor.get_plan(plan.id)
        assert retrieved.id == plan.id

    def test_get_plan_unknown(self, supervisor):
        """Test get_plan returns None for unknown."""
        retrieved = supervisor.get_plan("unknown-id")
        assert retrieved is None

    def test_cancel_plan(self, supervisor):
        """Test cancel_plan marks tasks cancelled."""
        goal = "实现用户认证功能"
        plan = supervisor.plan(goal)
        success = supervisor.cancel_plan(plan.id)
        assert success

    def test_cancel_unknown(self, supervisor):
        """Test cancelling unknown returns False."""
        success = supervisor.cancel_plan("unknown-id")
        assert not success

    def test_list_plans(self, supervisor):
        """Test list_plans returns all plans."""
        supervisor.plan("功能A")
        supervisor.plan("bugB")
        plans = supervisor.list_plans()
        assert len(plans) == 2

    def test_plan_summary(self, supervisor):
        """Test get_plan_summary."""
        goal = "实现用户认证功能"
        plan = supervisor.plan(goal)
        summary = supervisor.get_plan_summary(plan.id)
        assert summary["plan_id"] == plan.id
        assert summary["progress"]["total"] == 5


class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_get_supervisor(self):
        """Test get_supervisor creates instance."""
        supervisor = get_supervisor("test_team")
        assert supervisor is not None
        assert supervisor.team_name == "test_team"

    def test_default_rules(self):
        """Test get_supervisor has default rules."""
        supervisor = get_supervisor("test_team")
        assert len(supervisor.rules) == 8


class TestIntegration:
    """Integration tests."""

    def test_full_workflow(self, supervisor):
        """Test full workflow."""
        goal = "实现用户认证功能"
        plan = supervisor.plan(goal)
        assert len(plan.tasks) == 5
        result = supervisor.execute(plan.id)
        assert result.status == "completed"
        verifications = supervisor.verify_plan(plan.id)
        assert len(verifications) == len(plan.tasks)

    def test_custom_rules(self):
        """Test plan with custom rules."""
        custom_rule = DecompositionRule(
            pattern=DecompositionPattern.GENERAL,
            keywords=["custom"],
            subtask_templates=["Step 1", "Step 2", "Step 3"],
            dependencies=[(1, 0), (2, 1)],
            provider_preferences={0: "claude", 1: "codex", 2: "qa"},
        )
        supervisor = SupervisorEngine("test_team", rules=[custom_rule])
        plan = supervisor.plan("custom task")
        assert len(plan.tasks) == 3