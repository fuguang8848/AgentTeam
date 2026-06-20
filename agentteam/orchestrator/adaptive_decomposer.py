"""
Adaptive Task Decomposer - 自适应任务分解器

参考 SpectrAI/src/main/orchestrator/AdaptiveDecomposer.ts 实现
基于历史执行数据动态调整任务分解粒度

功能：
- 基于历史执行数据动态调整任务分解粒度
- 记录分解模式到 .decomposer_stats.json
- 支持手动 override
- 智能判断任务复杂度并调整分解策略

@author AgentTeam
@version 1.0.0
"""

import json
import logging
import os
import re
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class TaskComplexity(Enum):
    """任务复杂度等级"""
    TRIVIAL = "trivial"      # 简单任务，无需分解
    SIMPLE = "simple"       # 简单任务，少量子任务
    MODERATE = "moderate"   # 中等复杂度
    COMPLEX = "complex"     # 复杂任务，多层分解
    VERY_COMPLEX = "very_complex"  # 极复杂任务


class DecompositionStrategy(Enum):
    """分解策略"""
    FLAT = "flat"           # 扁平分解，并行执行
    HIERARCHICAL = "hierarchical"  # 层级分解
    LINEAR = "linear"       # 线性分解，顺序执行
    ADAPTIVE = "adaptive"   # 自适应分解


@dataclass
class SubTask:
    """子任务定义"""
    id: str
    name: str
    description: str
    priority: int = 0
    estimated_duration: Optional[float] = None  # 分钟
    dependencies: List[str] = field(default_factory=list)
    assigned_agent: Optional[str] = None
    skill_requirements: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "priority": self.priority,
            "estimated_duration": self.estimated_duration,
            "dependencies": self.dependencies,
            "assigned_agent": self.assigned_agent,
            "skill_requirements": self.skill_requirements,
            "metadata": self.metadata,
        }


@dataclass
class DecompositionResult:
    """分解结果"""
    task_id: str
    original_task: str
    sub_tasks: List[SubTask]
    strategy: DecompositionStrategy
    complexity: TaskComplexity
    confidence: float  # 0.0 - 1.0
    reasoning: str
    execution_history_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "original_task": self.original_task,
            "sub_tasks": [st.to_dict() for st in self.sub_tasks],
            "strategy": self.strategy.value,
            "complexity": self.complexity.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "execution_history_id": self.execution_history_id,
        }


@dataclass
class ExecutionRecord:
    """执行记录"""
    task_id: str
    sub_task_count: int
    actual_duration: float  # 分钟
    success: bool
    strategy_used: DecompositionStrategy
    complexity_estimated: TaskComplexity
    timestamp: str
    user_feedback: Optional[float] = None  # 0.0 - 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "sub_task_count": self.sub_task_count,
            "actual_duration": self.actual_duration,
            "success": self.success,
            "strategy_used": self.strategy_used.value,
            "complexity_estimated": self.complexity_estimated.value,
            "timestamp": self.timestamp,
            "user_feedback": self.user_feedback,
        }


@dataclass
class DecomposerStats:
    """分解器统计信息"""
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    avg_subtask_count: float = 0.0
    avg_duration: float = 0.0
    strategy_effectiveness: Dict[str, float] = field(default_factory=dict)  # strategy -> avg_feedback
    complexity_accuracy: Dict[str, float] = field(default_factory=dict)  # complexity -> accuracy
    recent_executions: List[Dict] = field(default_factory=list)
    override_active: bool = False
    override_strategy: Optional[str] = None
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_tasks": self.total_tasks,
            "successful_tasks": self.successful_tasks,
            "failed_tasks": self.failed_tasks,
            "avg_subtask_count": self.avg_subtask_count,
            "avg_duration": self.avg_duration,
            "strategy_effectiveness": self.strategy_effectiveness,
            "complexity_accuracy": self.complexity_accuracy,
            "recent_executions": self.recent_executions[-100:],  # Keep last 100
            "override_active": self.override_active,
            "override_strategy": self.override_strategy,
            "last_updated": self.last_updated,
        }


class AdaptiveDecomposer:
    """
    自适应任务分解器

    根据历史执行数据动态调整任务分解策略和粒度。

    使用示例：
        decomposer = AdaptiveDecomposer()

        # 分解任务
        result = decomposer.decompose("实现一个用户认证系统")
        print(f"分解为 {len(result.sub_tasks)} 个子任务")
        print(f"策略: {result.strategy.value}")
        print(f"复杂度: {result.complexity.value}")

        # 记录执行结果
        decomposer.record_execution(result, success=True, actual_duration=5.2)

        # 手动 override
        decomposer.set_override(DecompositionStrategy.FLAT)

        # 清除 override
        decomposer.clear_override()
    """

    def __init__(
        self,
        stats_file: str = ".decomposer_stats.json",
        base_dir: Optional[str] = None,
        min_subtasks: int = 1,
        max_subtasks: int = 20,
    ):
        """
        初始化自适应分解器

        Args:
            stats_file: 统计文件路径
            base_dir: 基础目录，默认为当前工作目录
            min_subtasks: 最少子任务数
            max_subtasks: 最多子任务数
        """
        self._stats_file = stats_file
        self._base_dir = base_dir or os.getcwd()
        self._min_subtasks = min_subtasks
        self._max_subtasks = max_subtasks

        self._stats = DecomposerStats()
        self._lock = threading.RLock()

        # 加载历史统计
        self._load_stats()

        # 复杂度关键词
        self._complexity_keywords = {
            TaskComplexity.TRIVIAL: [
                r"简单", r"翻译", r"格式化", r"检查", r"验证",
                r"简单修改", r"typo", r"注释",
            ],
            TaskComplexity.SIMPLE: [
                r"实现", r"添加", r"创建", r"编写", r"生成",
                r"一个", r"单个", r"基础",
            ],
            TaskComplexity.MODERATE: [
                r"系统", r"模块", r"功能", r"多个", r"集成",
                r"优化", r"重构", r"迁移",
            ],
            TaskComplexity.COMPLEX: [
                r"复杂", r"分布式", r"微服务", r"架构", r"平台",
                r"全栈", r"端到端", r"大型",
            ],
            TaskComplexity.VERY_COMPLEX: [
                r"极复杂", r"人工智能", r"机器学习", r"大数据",
                r"全新架构", r"革命性",
            ],
        }

        # 复杂度与子任务数量映射（基于历史数据调整）
        self._complexity_to_subtasks = {
            TaskComplexity.TRIVIAL: (1, 1),
            TaskComplexity.SIMPLE: (1, 3),
            TaskComplexity.MODERATE: (3, 7),
            TaskComplexity.COMPLEX: (5, 12),
            TaskComplexity.VERY_COMPLEX: (8, 20),
        }

    def _get_stats_path(self) -> Path:
        """获取统计文件完整路径"""
        return Path(self._base_dir) / self._stats_file

    def _load_stats(self):
        """从文件加载统计信息"""
        stats_path = self._get_stats_path()
        if stats_path.exists():
            try:
                with open(stats_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._stats = DecomposerStats(
                        total_tasks=data.get("total_tasks", 0),
                        successful_tasks=data.get("successful_tasks", 0),
                        failed_tasks=data.get("failed_tasks", 0),
                        avg_subtask_count=data.get("avg_subtask_count", 0.0),
                        avg_duration=data.get("avg_duration", 0.0),
                        strategy_effectiveness=data.get("strategy_effectiveness", {}),
                        complexity_accuracy=data.get("complexity_accuracy", {}),
                        recent_executions=data.get("recent_executions", []),
                        override_active=data.get("override_active", False),
                        override_strategy=data.get("override_strategy"),
                        last_updated=data.get("last_updated", datetime.now().isoformat()),
                    )
                logger.info(f"Loaded decomposer stats from {stats_path}")
            except Exception as e:
                logger.warning(f"Failed to load stats: {e}, using defaults")

    def _save_stats(self):
        """保存统计信息到文件"""
        stats_path = self._get_stats_path()
        try:
            with open(stats_path, "w", encoding="utf-8") as f:
                json.dump(self._stats.to_dict(), f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved decomposer stats to {stats_path}")
        except Exception as e:
            logger.error(f"Failed to save stats: {e}")

    def _generate_task_id(self) -> str:
        """生成唯一任务ID"""
        return f"task_{int(time.time() * 1000)}"

    def _generate_subtask_id(self, task_id: str, index: int) -> str:
        """生成子任务ID"""
        return f"{task_id}_st{index:03d}"

    def _detect_complexity(self, task_description: str) -> TaskComplexity:
        """
        基于关键词检测任务复杂度

        Args:
            task_description: 任务描述

        Returns:
            TaskComplexity: 检测到的复杂度
        """
        task_lower = task_description.lower()

        # 检查每个复杂度的关键词
        for complexity, keywords in self._complexity_keywords.items():
            for keyword in keywords:
                if re.search(keyword, task_lower):
                    return complexity

        # 根据任务长度和结构估算复杂度
        word_count = len(task_description.split())
        if word_count < 10:
            return TaskComplexity.TRIVIAL
        elif word_count < 30:
            return TaskComplexity.SIMPLE
        elif word_count < 80:
            return TaskComplexity.MODERATE
        elif word_count < 150:
            return TaskComplexity.COMPLEX
        else:
            return TaskComplexity.VERY_COMPLEX

    def _adjust_complexity_by_history(self, complexity: TaskComplexity) -> TaskComplexity:
        """
        根据历史数据调整复杂度评估

        如果某个复杂度的任务实际执行反馈较差，说明复杂度评估不准确
        """
        complexity_key = complexity.value

        # 如果该复杂度的准确率数据不足，返回原始评估
        if complexity_key not in self._stats.complexity_accuracy:
            return complexity

        accuracy = self._stats.complexity_accuracy[complexity_key]

        # 如果准确率较低，可能需要调整
        # 简化：如果复杂度的预估子任务数与实际偏差较大
        if accuracy < 0.6 and self._stats.avg_subtask_count > 0:
            # 检查最近的执行是否子任务数偏多或偏少
            recent = self._stats.recent_executions[-10:]
            if recent:
                avg_actual = sum(e.get("sub_task_count", 0) for e in recent) / len(recent)
                est_range = self._complexity_to_subtasks[complexity]
                if avg_actual < est_range[0]:
                    # 实际子任务比预估少，可能复杂度被高估
                    pass  # 暂时不做调整，保持稳定性
                elif avg_actual > est_range[1]:
                    # 实际子任务比预估多，可能复杂度被低估
                    pass

        return complexity

    def _select_strategy(self, complexity: TaskComplexity) -> DecompositionStrategy:
        """
        根据复杂度选择分解策略

        Args:
            complexity: 任务复杂度

        Returns:
            DecompositionStrategy: 选择的策略
        """
        # 检查是否有 override
        if self._stats.override_active and self._stats.override_strategy:
            try:
                return DecompositionStrategy(self._stats.override_strategy)
            except ValueError:
                pass

        # 基于复杂度和历史效果选择策略
        strategy_scores = {}

        for strategy in DecompositionStrategy:
            score = 50.0  # 基础分数

            # 复杂度匹配
            if strategy == DecompositionStrategy.FLAT:
                if complexity in [TaskComplexity.TRIVIAL, TaskComplexity.SIMPLE]:
                    score += 30
                elif complexity == TaskComplexity.MODERATE:
                    score += 10
            elif strategy == DecompositionStrategy.LINEAR:
                if complexity in [TaskComplexity.TRIVIAL, TaskComplexity.SIMPLE]:
                    score += 20
                elif complexity == TaskComplexity.VERY_COMPLEX:
                    score += 25
            elif strategy == DecompositionStrategy.HIERARCHICAL:
                if complexity in [TaskComplexity.COMPLEX, TaskComplexity.VERY_COMPLEX]:
                    score += 35
                elif complexity == TaskComplexity.MODERATE:
                    score += 20
            elif strategy == DecompositionStrategy.ADAPTIVE:
                # 自适应策略，始终是安全选择
                score += 25

            # 历史效果加成
            strategy_key = strategy.value
            if strategy_key in self._stats.strategy_effectiveness:
                effectivity = self._stats.strategy_effectiveness[strategy_key]
                score += effectivity * 20  # 最多加20分

            strategy_scores[strategy] = score

        # 选择分数最高的策略
        return max(strategy_scores.items(), key=lambda x: x[1])[0]

    def _estimate_subtask_count(self, complexity: TaskComplexity) -> Tuple[int, int]:
        """
        估算子任务数量范围

        Args:
            complexity: 任务复杂度

        Returns:
            Tuple[int, int]: (最小数量, 最大数量)
        """
        base_range = self._complexity_to_subtasks[complexity]

        # 根据历史数据调整
        if self._stats.avg_subtask_count > 0:
            # 如果历史平均子任务数与当前预估偏差较大，进行调整
            base_avg = (base_range[0] + base_range[1]) / 2
            adjustment = (self._stats.avg_subtask_count - base_avg) * 0.3

            min_adj = max(1, int(base_range[0] + adjustment * 0.5))
            max_adj = min(self._max_subtasks, int(base_range[1] + adjustment))

            return (min_adj, max_adj)
        else:
            return base_range

    def _generate_subtasks(
        self,
        task_id: str,
        original_task: str,
        complexity: TaskComplexity,
        count: int,
    ) -> List[SubTask]:
        """
        生成子任务列表

        Args:
            task_id: 父任务ID
            original_task: 原始任务描述
            complexity: 任务复杂度
            count: 子任务数量

        Returns:
            List[SubTask]: 子任务列表
        """
        sub_tasks = []

        # 基于任务描述和复杂度生成子任务
        if complexity == TaskComplexity.TRIVIAL:
            # 简单任务，可能只需要一个子任务
            sub_tasks.append(SubTask(
                id=self._generate_subtask_id(task_id, 0),
                name="执行任务",
                description=original_task,
                priority=1,
            ))
        else:
            # 通用分解模式
            task_parts = self._analyze_task_structure(original_task)

            if len(task_parts) >= count:
                # 直接使用分析出的结构
                for i, part in enumerate(task_parts[:count]):
                    sub_tasks.append(SubTask(
                        id=self._generate_subtask_id(task_id, i),
                        name=part.get("name", f"子任务 {i+1}"),
                        description=part.get("description", part.get("name", "")),
                        priority=count - i,
                        estimated_duration=part.get("duration"),
                        dependencies=part.get("dependencies", []),
                        skill_requirements=part.get("skills", []),
                    ))
            else:
                # 需要补充子任务
                for i, part in enumerate(task_parts):
                    sub_tasks.append(SubTask(
                        id=self._generate_subtask_id(task_id, i),
                        name=part.get("name", f"子任务 {i+1}"),
                        description=part.get("description", part.get("name", "")),
                        priority=count - i,
                        estimated_duration=part.get("duration"),
                        dependencies=part.get("dependencies", []),
                        skill_requirements=part.get("skills", []),
                    ))

                # 补充剩余子任务
                remaining = count - len(task_parts)
                for i in range(remaining):
                    sub_tasks.append(SubTask(
                        id=self._generate_subtask_id(task_id, len(task_parts) + i),
                        name=f"步骤 {len(task_parts) + i + 1}",
                        description="执行相关步骤",
                        priority=count - len(task_parts) - i,
                    ))

        # 设置依赖关系（基于优先级）
        self._resolve_dependencies(sub_tasks)

        return sub_tasks

    def _analyze_task_structure(self, task: str) -> List[Dict[str, Any]]:
        """
        分析任务结构，识别可能的子任务划分

        Args:
            task: 任务描述

        Returns:
            List[Dict]: 分析出的子任务结构
        """
        parts = []

        # 常见任务模式识别
        patterns = [
            # 设计与实现模式
            (r"设计.*并实现", ["设计", "实现"]),
            # 前后端模式
            (r"(前端|后端|数据库)", ["前端实现", "后端实现", "数据库设计"]),
            # CRUD 模式
            (r"CRUD|增删改查", ["创建", "读取", "更新", "删除"]),
            # 开发和测试模式
            (r"实现.*测试", ["实现功能", "编写测试", "修复问题"]),
            # 部署模式
            (r"部署.*配置", ["部署", "配置", "验证"]),
        ]

        for pattern, suggested_parts in patterns:
            if re.search(pattern, task, re.IGNORECASE):
                for i, part_name in enumerate(suggested_parts):
                    parts.append({
                        "name": part_name,
                        "description": f"执行 {part_name} 相关工作",
                        "duration": None,
                        "dependencies": [] if i == 0 else [suggested_parts[i-1]],
                        "skills": [],
                    })
                break

        # 如果没有匹配到模式，按语义分割
        if not parts:
            # 简单分割为理解、计划、执行三个阶段
            parts = [
                {"name": "理解需求", "description": "理解任务需求和目标", "duration": None, "dependencies": [], "skills": []},
                {"name": "制定计划", "description": "制定执行计划", "duration": None, "dependencies": ["理解需求"], "skills": []},
                {"name": "执行任务", "description": "执行主要任务", "duration": None, "dependencies": ["制定计划"], "skills": []},
            ]

        return parts

    def _resolve_dependencies(self, sub_tasks: List[SubTask]):
        """根据子任务结构自动解析依赖关系"""
        for i, sub_task in enumerate(sub_tasks):
            if not sub_task.dependencies and i > 0:
                # 默认依赖前一个任务
                sub_task.dependencies.append(sub_tasks[i - 1].id)

    def decompose(
        self,
        task_description: str,
        manual_strategy: Optional[DecompositionStrategy] = None,
        manual_complexity: Optional[TaskComplexity] = None,
        forced_subtask_count: Optional[int] = None,
    ) -> DecompositionResult:
        """
        分解任务为子任务

        Args:
            task_description: 任务描述
            manual_strategy: 手动指定分解策略（覆盖自适应）
            manual_complexity: 手动指定复杂度（覆盖自动检测）
            forced_subtask_count: 强制子任务数量（覆盖自动计算）

        Returns:
            DecompositionResult: 分解结果
        """
        with self._lock:
            task_id = self._generate_task_id()

            # 复杂度检测
            if manual_complexity:
                complexity = manual_complexity
            else:
                complexity = self._detect_complexity(task_description)
                complexity = self._adjust_complexity_by_history(complexity)

            # 策略选择
            if manual_strategy:
                strategy = manual_strategy
            else:
                strategy = self._select_strategy(complexity)

            # 子任务数量
            if forced_subtask_count:
                subtask_count = max(self._min_subtasks, min(self._max_subtasks, forced_subtask_count))
            else:
                range_min, range_max = self._estimate_subtask_count(complexity)
                subtask_count = (range_min + range_max) // 2

            # 生成子任务
            sub_tasks = self._generate_subtasks(task_id, task_description, complexity, subtask_count)

            # 计算置信度
            confidence = 0.7  # 基础置信度
            if self._stats.total_tasks > 10:
                # 基于历史准确率调整
                success_rate = self._stats.successful_tasks / max(1, self._stats.total_tasks)
                confidence = 0.5 + success_rate * 0.4

            result = DecompositionResult(
                task_id=task_id,
                original_task=task_description,
                sub_tasks=sub_tasks,
                strategy=strategy,
                complexity=complexity,
                confidence=confidence,
                reasoning=f"基于{complexity.value}复杂度，采用{strategy.value}策略分解为{subtask_count}个子任务",
            )

            return result

    def record_execution(
        self,
        result: DecompositionResult,
        success: bool,
        actual_duration: float,
        user_feedback: Optional[float] = None,
    ):
        """
        记录任务执行结果，用于后续自适应调整

        Args:
            result: 分解结果
            success: 是否成功
            actual_duration: 实际执行时长（分钟）
            user_feedback: 用户反馈 (0.0-1.0)
        """
        with self._lock:
            record = ExecutionRecord(
                task_id=result.task_id,
                sub_task_count=len(result.sub_tasks),
                actual_duration=actual_duration,
                success=success,
                strategy_used=result.strategy,
                complexity_estimated=result.complexity,
                timestamp=datetime.now().isoformat(),
                user_feedback=user_feedback,
            )

            # 更新统计
            self._stats.total_tasks += 1
            if success:
                self._stats.successful_tasks += 1
            else:
                self._stats.failed_tasks += 1

            # 更新平均子任务数
            total = self._stats.total_tasks
            old_avg_count = self._stats.avg_subtask_count
            old_avg_duration = self._stats.avg_duration
            self._stats.avg_subtask_count = (old_avg_count * (total - 1) + len(result.sub_tasks)) / total
            self._stats.avg_duration = (old_avg_duration * (total - 1) + actual_duration) / total

            # 更新策略效果
            strategy_key = result.strategy.value
            if user_feedback is not None:
                current_effect = self._stats.strategy_effectiveness.get(strategy_key, 0.5)
                # 指数移动平均
                self._stats.strategy_effectiveness[strategy_key] = current_effect * 0.7 + user_feedback * 0.3

            # 更新复杂度准确率（简化版）
            complexity_key = result.complexity.value
            if success:
                current_acc = self._stats.complexity_accuracy.get(complexity_key, 0.5)
                self._stats.complexity_accuracy[complexity_key] = current_acc * 0.8 + 0.2

            # 添加到最近执行记录
            self._stats.recent_executions.append(record.to_dict())

            # 保持记录数量限制
            if len(self._stats.recent_executions) > 100:
                self._stats.recent_executions = self._stats.recent_executions[-100:]

            self._stats.last_updated = datetime.now().isoformat()

            # 保存统计
            self._save_stats()

            logger.info(
                f"Recorded execution: task_id={result.task_id}, "
                f"subtasks={len(result.sub_tasks)}, success={success}, "
                f"duration={actual_duration:.1f}min"
            )

    def set_override(self, strategy: DecompositionStrategy, reason: str = ""):
        """
        设置手动 override，下次分解将强制使用指定策略

        Args:
            strategy: 要强制使用的策略
            reason: 原因说明
        """
        with self._lock:
            self._stats.override_active = True
            self._stats.override_strategy = strategy.value
            self._stats.last_updated = datetime.now().isoformat()
            self._save_stats()
            logger.info(f"Override set to {strategy.value}. Reason: {reason}")

    def clear_override(self):
        """清除手动 override，恢复自适应策略"""
        with self._lock:
            self._stats.override_active = False
            self._stats.override_strategy = None
            self._stats.last_updated = datetime.now().isoformat()
            self._save_stats()
            logger.info("Override cleared, back to adaptive mode")

    def get_stats(self) -> Dict[str, Any]:
        """获取分解器统计信息"""
        with self._lock:
            return self._stats.to_dict()

    def reset_stats(self):
        """重置统计信息"""
        with self._lock:
            self._stats = DecomposerStats()
            self._save_stats()
            logger.info("Decomposer stats reset")

    def suggest_adjustments(self) -> List[str]:
        """
        基于历史数据给出优化建议

        Returns:
            List[str]: 优化建议列表
        """
        suggestions = []

        with self._lock:
            if self._stats.total_tasks < 5:
                suggestions.append("需要更多执行数据以提供准确的建议（当前 < 5）")
                return suggestions

            # 分析策略效果
            if self._stats.strategy_effectiveness:
                worst_strategy = min(
                    self._stats.strategy_effectiveness.items(),
                    key=lambda x: x[1]
                )
                if worst_strategy[1] < 0.4:
                    suggestions.append(
                        f"策略 '{worst_strategy[0]}' 效果较差 (反馈: {worst_strategy[1]:.2f})，"
                        "建议在复杂任务中避免使用"
                    )

            # 分析复杂度评估
            for complexity, accuracy in self._stats.complexity_accuracy.items():
                if accuracy < 0.5:
                    suggestions.append(
                        f"复杂度 '{complexity}' 的评估准确率较低 ({accuracy:.2f})，"
                        "建议手动指定复杂度"
                    )

            # 分析子任务数量
            if self._stats.avg_subtask_count > 10:
                suggestions.append(
                    f"平均子任务数偏高 ({self._stats.avg_subtask_count:.1f})，"
                    "考虑将任务分解为更大的子任务以减少调度开销"
                )
            elif self._stats.avg_subtask_count < 2:
                suggestions.append(
                    f"平均子任务数偏低 ({self._stats.avg_subtask_count:.1f})，"
                    "考虑将任务进一步分解以提高并行度"
                )

            # 分析执行时长
            if self._stats.avg_duration > 30:
                suggestions.append(
                    f"平均执行时间较长 ({self._stats.avg_duration:.1f}min)，"
                    "考虑将大任务分解为更小的子任务"
                )

        return suggestions


# 全局分解器实例
_default_decomposer: Optional[AdaptiveDecomposer] = None
_decomposer_lock = threading.Lock()


def get_decomposer(base_dir: Optional[str] = None) -> AdaptiveDecomposer:
    """
    获取全局分解器实例（单例）

    Args:
        base_dir: 基础目录

    Returns:
        AdaptiveDecomposer: 分解器实例
    """
    global _default_decomposer
    with _decomposer_lock:
        if _default_decomposer is None:
            _default_decomposer = AdaptiveDecomposer(base_dir=base_dir)
        return _default_decomposer


def decompose_task(
    task_description: str,
    **kwargs,
) -> DecompositionResult:
    """
    快捷分解函数

    Args:
        task_description: 任务描述
        **kwargs: decompose 方法的其他参数

    Returns:
        DecompositionResult: 分解结果
    """
    decomposer = get_decomposer()
    return decomposer.decompose(task_description, **kwargs)
