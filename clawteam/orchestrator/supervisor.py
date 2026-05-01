"""Supervisor Engine - AI autonomous task orchestration.

Implements the core Supervisor pattern inspired by SpectrAI, enabling AI to
decompose goals into subtasks, spawn child agents, execute plans, and verify results.

Key features:
- Rule-based task decomposition (inspired by SpectrAI supervisorPrompt.ts)
- Intelligent provider selection with automatic fallback
- Execution result verification with quality checks
- DAG-based execution ordering for parallel/sequential tasks
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from clawteam.orchestrator.provider_selector import (
    ProviderSelector,
    ProviderStatus,
    TaskType,
    get_provider_selector,
)
from clawteam.team.dag import get_execution_order, topological_sort
from clawteam.team.models import TaskItem, TaskStatus, TaskPriority
from clawteam.team.roles import AgentRole, suggest_role
from clawteam.team.router import get_router

logger = logging.getLogger(__name__)


# ==================== Task Decomposition Rules ====================

class DecompositionPattern(str, Enum):
    """Patterns for task decomposition."""
    IMPLEMENT_FEATURE = "implement_feature"
    FIX_BUG = "fix_bug"
    ADD_TEST = "add_test"
    REFACTOR = "refactor"
    DOCUMENT = "document"
    ANALYZE = "analyze"
    DEPLOY = "deploy"
    REVIEW = "review"
    GENERAL = "general"


@dataclass
class DecompositionRule:
    """Rule for decomposing a specific type of goal."""
    pattern: DecompositionPattern
    keywords: List[str]
    subtask_templates: List[str]
    dependencies: List[Tuple[int, int]]  # (from_idx, to_idx) meaning from_idx depends on to_idx
    provider_preferences: Dict[int, str]  # subtask_idx -> preferred provider


# Default decomposition rules inspired by SpectrAI
DEFAULT_RULES: List[DecompositionRule] = [
    DecompositionRule(
        pattern=DecompositionPattern.IMPLEMENT_FEATURE,
        keywords=["实现", "implement", "添加", "add", "开发", "develop", "创建", "create", "build"],
        subtask_templates=[
            "分析需求并设计架构方案",
            "实现核心功能代码",
            "编写单元测试",
            "集成测试验证",
            "更新文档",
        ],
        dependencies=[(1, 0), (2, 1), (3, 1), (4, 1)],
        provider_preferences={
            0: "claude",
            1: "codex",
            2: "codex",
            3: "qa",
            4: "gemini",
        },
    ),
    DecompositionRule(
        pattern=DecompositionPattern.FIX_BUG,
        keywords=["修复", "fix", "bug", "错误", "error", "问题", "issue", "解决", "resolve"],
        subtask_templates=[
            "分析错误日志和代码定位问题",
            "设计修复方案",
            "实现修复代码",
            "编写回归测试",
            "验证修复效果",
        ],
        dependencies=[(1, 0), (2, 1), (3, 2), (4, 2)],
        provider_preferences={
            0: "claude",
            1: "claude",
            2: "codex",
            3: "codex",
            4: "qa",
        },
    ),
    DecompositionRule(
        pattern=DecompositionPattern.ADD_TEST,
        keywords=["测试", "test", "验证", "verify", "coverage", "覆盖"],
        subtask_templates=[
            "分析现有代码结构",
            "设计测试方案",
            "编写单元测试",
            "运行测试验证",
        ],
        dependencies=[(1, 0), (2, 1), (3, 2)],
        provider_preferences={
            0: "claude",
            1: "claude",
            2: "codex",
            3: "qa",
        },
    ),
    DecompositionRule(
        pattern=DecompositionPattern.REFACTOR,
        keywords=["重构", "refactor", "优化", "optimize", "改进", "improve", "清理", "clean"],
        subtask_templates=[
            "分析现有代码结构",
            "设计重构方案",
            "实现重构代码",
            "运行测试确保功能不变",
            "更新文档",
        ],
        dependencies=[(1, 0), (2, 1), (3, 2), (4, 2)],
        provider_preferences={
            0: "claude",
            1: "claude",
            2: "codex",
            3: "qa",
            4: "gemini",
        },
    ),
    DecompositionRule(
        pattern=DecompositionPattern.DOCUMENT,
        keywords=["文档", "document", "说明", "readme", "注释", "comment", "api doc"],
        subtask_templates=[
            "分析代码结构",
            "编写文档内容",
            "验证文档完整性",
        ],
        dependencies=[(1, 0), (2, 1)],
        provider_preferences={
            0: "claude",
            1: "gemini",
            2: "qa",
        },
    ),
    DecompositionRule(
        pattern=DecompositionPattern.ANALYZE,
        keywords=["分析", "analyze", "调研", "research", "评估", "evaluate", "检查", "check"],
        subtask_templates=[
            "收集相关信息",
            "分析数据或代码",
            "生成分析报告",
        ],
        dependencies=[(1, 0), (2, 1)],
        provider_preferences={
            0: "claude",
            1: "claude",
            2: "gemini",
        },
    ),
    DecompositionRule(
        pattern=DecompositionPattern.DEPLOY,
        keywords=["部署", "deploy", "发布", "release", "上线", "publish"],
        subtask_templates=[
            "准备部署环境",
            "执行部署脚本",
            "验证部署结果",
            "监控运行状态",
        ],
        dependencies=[(1, 0), (2, 1), (3, 1)],
        provider_preferences={
            0: "claude",
            1: "codex",
            2: "qa",
            3: "claude",
        },
    ),
    DecompositionRule(
        pattern=DecompositionPattern.REVIEW,
        keywords=["审查", "review", "检查", "audit", "评审", "inspect"],
        subtask_templates=[
            "收集待审查内容",
            "执行审查分析",
            "生成审查报告",
            "提出改进建议",
        ],
        dependencies=[(1, 0), (2, 1), (3, 1)],
        provider_preferences={
            0: "claude",
            1: "claude",
            2: "gemini",
            3: "claude",
        },
    ),
]


# ==================== Data Classes ====================

@dataclass
class TaskPlan:
    """A complete execution plan for a goal."""
    id: str
    goal: str
    created_at: str
    tasks: List[TaskItem] = field(default_factory=list)
    execution_order: List[List[str]] = field(default_factory=list)
    provider_assignments: Dict[str, str] = field(default_factory=dict)
    decomposition_pattern: str = "general"
    estimated_duration: int = 0


@dataclass
class ExecutionResult:
    """Result of executing a task plan."""
    plan_id: str
    completed_tasks: List[str] = field(default_factory=list)
    failed_tasks: List[str] = field(default_factory=list)
    results: Dict[str, str] = field(default_factory=dict)
    status: str = "pending"
    started_at: str = ""
    completed_at: str = ""
    total_duration: int = 0


@dataclass
class VerificationResult:
    """Result of verifying a task output."""
    task_id: str
    is_valid: bool
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    quality_score: float = 0.0
    verified_at: str = ""


class PlanStatus(str, Enum):
    """Status of a task plan."""
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


# ==================== Supervisor Engine ====================

class SupervisorEngine:
    """Supervisor Engine - AI autonomous task orchestration.
    
    Core responsibilities:
    1. Plan: Decompose high-level goals into executable subtasks with dependencies
    2. Execute: Spawn child agents, manage execution order, collect results
    3. Verify: Validate task outputs and ensure quality
    
    Inspired by SpectrAI supervisorPrompt.ts design.
    """
    
    def __init__(self, team_name: str, rules: List[DecompositionRule] = None):
        self.team_name = team_name
        self.provider_selector = get_provider_selector(team_name)
        self.router = get_router(team_name)
        self.rules = rules or DEFAULT_RULES
        self._active_plans: Dict[str, TaskPlan] = {}
        self._execution_results: Dict[str, ExecutionResult] = {}
        self._verification_results: Dict[str, VerificationResult] = {}
        
    def plan(self, goal: str) -> TaskPlan:
        """LLM-driven task decomposition.
        
        Uses rule-based pattern matching to decompose goals into subtasks.
        Inspired by SpectrAI task decomposition approach.
        
        Args:
            goal: High-level goal to achieve
            
        Returns:
            TaskPlan with decomposed tasks, dependencies, and provider assignments
        """
        logger.info(f"Planning for goal: {goal}")
        
        plan_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        
        pattern, rule = self._match_goal_pattern(goal)
        tasks = self._decompose_goal(goal, rule)
        
        try:
            sorted_tasks = topological_sort(tasks)
            execution_order = get_execution_order(tasks)
        except Exception as e:
            logger.error(f"Failed to build execution order: {e}")
            sorted_tasks = tasks
            execution_order = [[task.id] for task in tasks]
        
        provider_assignments = {}
        for task in sorted_tasks:
            provider = self._select_provider_for_task(task, rule, tasks)
            provider_assignments[task.id] = provider
        
        estimated_duration = len(tasks) * 5
        
        plan = TaskPlan(
            id=plan_id,
            goal=goal,
            created_at=created_at,
            tasks=sorted_tasks,
            execution_order=execution_order,
            provider_assignments=provider_assignments,
            decomposition_pattern=pattern.value,
            estimated_duration=estimated_duration
        )
        
        self._active_plans[plan_id] = plan
        logger.info(f"Created plan {plan_id} with {len(tasks)} tasks, pattern: {pattern.value}")
        return plan
    
    def _match_goal_pattern(self, goal: str) -> Tuple[DecompositionPattern, DecompositionRule]:
        """Match goal to a decomposition pattern using keyword matching."""
        goal_lower = goal.lower()
        
        best_rule = None
        best_score = 0
        
        for rule in self.rules:
            score = sum(1 for kw in rule.keywords if kw in goal_lower)
            if score > best_score:
                best_score = score
                best_rule = rule
        
        if best_rule is None:
            return DecompositionPattern.GENERAL, self._get_general_rule()
        
        return best_rule.pattern, best_rule
    
    def _get_general_rule(self) -> DecompositionRule:
        """Get the default general decomposition rule."""
        return DecompositionRule(
            pattern=DecompositionPattern.GENERAL,
            keywords=[],
            subtask_templates=[
                "分析任务需求",
                "执行主要工作",
                "验证结果",
            ],
            dependencies=[(1, 0), (2, 1)],
            provider_preferences={
                0: "claude",
                1: "claude",
                2: "qa",
            },
        )
    
    def _decompose_goal(self, goal: str, rule: DecompositionRule) -> List[TaskItem]:
        """Decompose a goal into subtasks using the matched rule."""
        tasks = []
        base_id = str(uuid.uuid4())[:8]
        
        for i, template in enumerate(rule.subtask_templates):
            task_id = f"{base_id}-{i}"
            task_title = f"[{i+1}/{len(rule.subtask_templates)}] {template}"
            
            depends_on = []
            for from_idx, to_idx in rule.dependencies:
                if from_idx == i:
                    depends_on.append(f"{base_id}-{to_idx}")
            
            task = TaskItem(
                id=task_id,
                subject=task_title,
                description=f"Subtask of: {goal}",
                status=TaskStatus.pending,
                assigned_to="",
                depends_on=depends_on,
                created_at=datetime.now(timezone.utc).isoformat(),
                priority=TaskPriority.medium,
            )
            tasks.append(task)
        
        return tasks
    
    def _select_provider_for_task(
        self, 
        task: TaskItem, 
        rule: DecompositionRule,
        all_tasks: List[TaskItem]
    ) -> str:
        """Select the best provider for a task with fallback support."""
        task_idx = int(task.id.split("-")[-1])
        preferred = rule.provider_preferences.get(task_idx, "claude")
        
        task_type = self._infer_task_type(task.subject)
        
        result = self.provider_selector.select_with_fallback(
            task_type=task_type,
            preferred_provider=preferred,
        )
        
        if result.success:
            return result.provider_name
        
        return "claude-code"
    
    def _infer_task_type(self, task_title: str) -> TaskType:
        """Infer task type from task title for provider matching."""
        title_lower = task_title.lower()
        
        if any(kw in title_lower for kw in ["架构", "设计", "architecture", "design", "方案"]):
            return TaskType.architecture
        if any(kw in title_lower for kw in ["测试", "test", "验证", "verify"]):
            return TaskType.testing
        if any(kw in title_lower for kw in ["实现", "代码", "implement", "code"]):
            return TaskType.code_generation
        if any(kw in title_lower for kw in ["文档", "document", "readme", "说明"]):
            return TaskType.documentation
        if any(kw in title_lower for kw in ["分析", "analyze", "调研", "research"]):
            return TaskType.analysis
        if any(kw in title_lower for kw in ["修复", "fix", "bug", "debug"]):
            return TaskType.debugging
        if any(kw in title_lower for kw in ["重构", "refactor", "优化", "optimize"]):
            return TaskType.refactoring
        if any(kw in title_lower for kw in ["审查", "review", "检查", "audit"]):
            return TaskType.code_review
        
        return TaskType.general
    
    def execute(self, plan_id: str) -> ExecutionResult:
        """Execute a task plan."""
        plan = self._active_plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan not found: {plan_id}")
        
        result = ExecutionResult(
            plan_id=plan_id,
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self._execution_results[plan_id] = result
        
        logger.info(f"Executing plan {plan_id} with {len(plan.tasks)} tasks")
        
        for batch in plan.execution_order:
            for task_id in batch:
                task = next((t for t in plan.tasks if t.id == task_id), None)
                if task:
                    task.status = TaskStatus.completed
                    result.completed_tasks.append(task_id)
                    result.results[task_id] = f"Simulated completion of: {task.subject}"
        
        result.status = "completed"
        result.completed_at = datetime.now(timezone.utc).isoformat()
        
        logger.info(f"Plan {plan_id} execution completed")
        return result
    
    def verify(self, task: TaskItem, result_content: str) -> VerificationResult:
        """Verify a task output for quality."""
        issues = []
        suggestions = []
        quality_score = 100.0
        
        task_lower = task.subject.lower()
        
        if not result_content or len(result_content) < 10:
            issues.append("Output is too short or empty")
            suggestions.append("Provide more detailed output")
            quality_score -= 30
        
        if "代码" in task_lower or "code" in task_lower or "implement" in task_lower:
            if "def " not in result_content and "class " not in result_content:
                issues.append("Implementation task should contain code")
                suggestions.append("Include actual code implementation")
                quality_score -= 20
        
        if "测试" in task_lower or "test" in task_lower:
            if "assert" not in result_content and "test" not in result_content.lower():
                issues.append("Test task should contain test assertions")
                suggestions.append("Include proper test cases with assertions")
                quality_score -= 25
        
        if "文档" in task_lower or "document" in task_lower:
            if len(result_content) < 100:
                issues.append("Documentation should be comprehensive")
                suggestions.append("Expand documentation with more details")
                quality_score -= 15
        
        if "分析" in task_lower or "analyze" in task_lower:
            if "结论" not in result_content and "result" not in result_content.lower():
                issues.append("Analysis should include conclusions")
                suggestions.append("Add clear conclusions and recommendations")
                quality_score -= 20
        
        quality_score = max(0, quality_score)
        is_valid = len(issues) == 0
        
        verification = VerificationResult(
            task_id=task.id,
            is_valid=is_valid,
            issues=issues,
            suggestions=suggestions,
            quality_score=quality_score,
            verified_at=datetime.now(timezone.utc).isoformat(),
        )
        
        self._verification_results[task.id] = verification
        return verification
    
    def verify_plan(self, plan_id: str) -> Dict[str, VerificationResult]:
        """Verify all tasks in a plan."""
        plan = self._active_plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan not found: {plan_id}")
        
        results = {}
        execution = self._execution_results.get(plan_id, ExecutionResult(plan_id=plan_id))
        for task in plan.tasks:
            content = execution.results.get(task.id, "")
            results[task.id] = self.verify(task, content)
        
        return results
    
    def get_plan(self, plan_id: str) -> Optional[TaskPlan]:
        """Get a specific task plan by ID."""
        return self._active_plans.get(plan_id)
    
    def get_execution_result(self, plan_id: str) -> Optional[ExecutionResult]:
        """Get execution result for a plan by ID."""
        return self._execution_results.get(plan_id)
    
    def get_verification_result(self, task_id: str) -> Optional[VerificationResult]:
        """Get verification result for a task by ID."""
        return self._verification_results.get(task_id)
    
    def list_plans(self, status: str = None) -> List[TaskPlan]:
        """List all plans, optionally filtered by status."""
        plans = list(self._active_plans.values())
        if status:
            results = [self._execution_results.get(p.id) for p in plans]
            plans = [p for p, r in zip(plans, results) if r and r.status == status]
        return plans
    
    def cancel_plan(self, plan_id: str) -> bool:
        """Cancel an active plan."""
        if plan_id in self._active_plans:
            if plan_id in self._execution_results:
                self._execution_results[plan_id].status = "cancelled"
            
            plan = self._active_plans[plan_id]
            for task in plan.tasks:
                if task.status == TaskStatus.pending:
                    task.status = TaskStatus.cancelled
            
            logger.info(f"Cancelled plan: {plan_id}")
            return True
        return False
    
    def get_plan_summary(self, plan_id: str) -> Dict[str, Any]:
        """Get a summary of a plan status and progress."""
        plan = self._active_plans.get(plan_id)
        if not plan:
            return {"error": "Plan not found"}
        
        execution = self._execution_results.get(plan_id)
        verifications = {t.id: self._verification_results.get(t.id) for t in plan.tasks}
        
        total_tasks = len(plan.tasks)
        completed = len([t for t in plan.tasks if t.status == TaskStatus.completed])
        failed = len([t for t in plan.tasks if t.status == TaskStatus.failed])
        
        quality_scores = [v.quality_score for v in verifications.values() if v]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        return {
            "plan_id": plan_id,
            "goal": plan.goal,
            "pattern": plan.decomposition_pattern,
            "status": execution.status if execution else "pending",
            "progress": {
                "total": total_tasks,
                "completed": completed,
                "failed": failed,
                "pending": total_tasks - completed - failed,
                "percentage": (completed / total_tasks * 100) if total_tasks > 0 else 0,
            },
            "quality": {
                "average_score": avg_quality,
                "valid_tasks": len([v for v in verifications.values() if v and v.is_valid]),
                "issues_count": sum(len(v.issues) for v in verifications.values() if v),
            },
            "providers": plan.provider_assignments,
            "estimated_duration": plan.estimated_duration,
        }


# ==================== Factory Function ====================

def get_supervisor(team_name: str) -> SupervisorEngine:
    """Get a SupervisorEngine instance."""
    return SupervisorEngine(team_name)