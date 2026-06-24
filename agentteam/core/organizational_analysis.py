"""
组织管理与系统思维改进模块
基于 Drucker MBO + Fayol 五项管理功能 + Senge 系统思维

改进点：
1. Drucker MBO: 目标对齐机制
2. Drucker 有效管理者: 管理者有效性反馈
3. Fayol 五项管理功能覆盖
4. Senge 系统反馈回路
5. Senge 组织学习
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List, Callable
from datetime import datetime
import time


class ObjectiveState(Enum):
    PENDING = "pending"
    ALIGNED = "aligned"
    IN_PROGRESS = "in_progress"
    ACHIEVED = "achieved"
    FAILED = "failed"


class FeedbackLoopType(Enum):
    REINFORCING = "reinforcing"  # 增强回路 (A→B→A)
    BALANCING = "balancing"      # 平衡回路 (A→B→-A)
    DELAYED = "delayed"          # 延迟反馈


@dataclass
class TeamObjective:
    """
    Drucker MBO: 组织目标定义
    
    每个目标应该：
    1. 清晰定义成功标准
    2. 可分解为子目标
    3. 有明确的负责人
    4. 有时间线和进度追踪
    """
    objective_id: str
    title: str
    description: str
    success_criteria: str  # 成功标准
    owner: str  # 负责人
    
    state: ObjectiveState = ObjectiveState.PENDING
    progress: float = 0.0  # 0.0 - 1.0
    
    created_at: float = field(default_factory=time.time)
    deadline: Optional[float] = None
    achieved_at: Optional[float] = None
    
    # 子目标分解
    sub_objectives: List[str] = field(default_factory=list)  # 子目标ID列表
    
    # 对齐的任务
    aligned_task_ids: List[str] = field(default_factory=list)
    
    # 关键结果 (Key Results)
    key_results: List[Dict] = field(default_factory=list)


@dataclass
class ManagerEffectivenessFeedback:
    """
    Drucker 有效管理者: 管理者有效性反馈
    
    管理者有效性不是天生的，是可以学会的。
    这需要：
    1. 具体的反馈数据
    2. 同行评估
    3. 结果对比
    """
    manager_id: str
    evaluation_time: float = field(default_factory=time.time)
    
    # 目标达成率
    objective_achievement_rate: float = 0.0  # 管理者负责的目标达成率
    
    # 团队绩效
    team_output_quality: float = 0.0  # 团队输出质量评分
    team_output_quantity: float = 0.0  # 团队输出数量
    
    # 决策质量
    decision_quality_score: float = 0.0  # 决策质量评分
    decision_speed_score: float = 0.0  # 决策速度评分
    
    # 资源利用效率
    resource_efficiency: float = 0.0  # 资源利用效率
    
    # 员工发展
    agent_development_score: float = 0.0  # 团队成员发展评分
    
    # 同行评估 (360度反馈)
    peer_feedback: Dict[str, float] = field(default_factory=dict)  # peer_id -> score
    
    # 自我评估
    self_assessment: float = 0.0
    
    # 综合评分
    @property
    def overall_effectiveness(self) -> float:
        """综合有效性评分"""
        weights = {
            'objective': 0.25,
            'quality': 0.20,
            'decision': 0.20,
            'resource': 0.15,
            'development': 0.20,
        }
        return (
            weights['objective'] * self.objective_achievement_rate +
            weights['quality'] * self.team_output_quality +
            weights['decision'] * (self.decision_quality_score * 0.6 + self.decision_speed_score * 0.4) +
            weights['resource'] * self.resource_efficiency +
            weights['development'] * self.agent_development_score
        )
    
    def to_dict(self) -> dict:
        return {
            "manager_id": self.manager_id,
            "evaluation_time": datetime.fromtimestamp(self.evaluation_time).isoformat(),
            "objective_achievement_rate": self.objective_achievement_rate,
            "team_output_quality": self.team_output_quality,
            "team_output_quantity": self.team_output_quantity,
            "decision_quality_score": self.decision_quality_score,
            "decision_speed_score": self.decision_speed_score,
            "resource_efficiency": self.resource_efficiency,
            "agent_development_score": self.agent_development_score,
            "peer_feedback": self.peer_feedback,
            "self_assessment": self.self_assessment,
            "overall_effectiveness": round(self.overall_effectiveness, 3),
        }


@dataclass
class FeedbackLoop:
    """
    Senge 系统反馈回路定义
    
    增强回路 (Reinforcing): 指数增长或崩溃
    平衡回路 (Balancing): 趋于稳定目标
    延迟反馈 (Delayed): 效果需要时间显现
    """
    loop_id: str
    name: str
    loop_type: FeedbackLoopType
    
    # 回路描述: A -> B -> C -> A
    description: str
    
    # 涉及的变量
    variables: List[str] = field(default_factory=list)
    
    # 回路强度 (放大/缩小效果)
    strength: float = 1.0  # >1 增强, <1 减弱
    
    # 是否激活
    is_active: bool = True
    
    # 上一次触发时间
    last_triggered: float = 0.0
    
    # 触发计数
    trigger_count: int = 0


@dataclass
class LearningRecord:
    """
    Senge 第五项修炼: 组织学习记录
    
    "学习"必须嵌入组织运作中。
    每次任务执行后都应该产生可积累的学习。
    """
    record_id: str
    agent_id: str
    task_id: str
    
    # 学习类型
    learning_type: str  # "skill_gap", "process_improvement", "error_pattern", "new_knowledge"
    
    # 学习内容
    content: str
    summary: str  # 压缩摘要
    
    # 来源任务
    task_name: str
    task_result: str  # "success", "failure", "partial"
    
    # 质量评分
    quality_score: float = 0.0
    
    # 可复用性
    reusability: str = "unknown"  # "high", "medium", "low", "unknown"
    
    # 应用次数
    applied_count: int = 0
    
    # 创建时间
    created_at: float = field(default_factory=time.time)
    
    # 上次应用时间
    last_applied_at: Optional[float] = None
    
    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "learning_type": self.learning_type,
            "content": self.content,
            "summary": self.summary,
            "task_name": self.task_name,
            "task_result": self.task_result,
            "quality_score": self.quality_score,
            "reusability": self.reusability,
            "applied_count": self.applied_count,
            "created_at": datetime.fromtimestamp(self.created_at).isoformat(),
            "last_applied_at": datetime.fromtimestamp(self.last_applied_at).isoformat() if self.last_applied_at else None,
        }


class FayolManagementCoverage:
    """
    Fayol 五项管理功能覆盖分析
    
    计划 (Planning): 目标设定、战略制定
    组织 (Organizing): 资源分配、结构设计
    指挥 (Commanding): 指示、指导、领导下层
    协调 (Coordinating): 整合活动、解决冲突
    控制 (Controlling): 监控、纠正偏差
    """
    
    def __init__(self):
        # 每项功能的覆盖评分 (0.0 - 1.0)
        self.planning_coverage: float = 0.0
        self.organizing_coverage: float = 0.0
        self.commanding_coverage: float = 0.0
        self.coordinating_coverage: float = 0.0
        self.controlling_coverage: float = 0.0
        
        # 缺失的功能
        self.missing_functions: List[str] = []
        
        # 改进建议
        self.improvement_suggestions: List[str] = []
    
    def get_overall_coverage(self) -> float:
        """获取总体管理功能覆盖率"""
        return (
            self.planning_coverage * 0.20 +
            self.organizing_coverage * 0.25 +
            self.commanding_coverage * 0.20 +
            self.coordinating_coverage * 0.15 +
            self.controlling_coverage * 0.20
        )
    
    def analyze_coverage(self) -> Dict:
        """返回完整的覆盖分析"""
        return {
            "planning": {
                "coverage": self.planning_coverage,
                "description": "目标设定、战略制定、预测"
            },
            "organizing": {
                "coverage": self.organizing_coverage,
                "description": "资源分配、结构设计、任务协调"
            },
            "commanding": {
                "coverage": self.commanding_coverage,
                "description": "指示、指导、领导下属"
            },
            "coordinating": {
                "coverage": self.coordinating_coverage,
                "description": "整合活动、解决冲突、信息共享"
            },
            "controlling": {
                "coverage": self.controlling_coverage,
                "description": "监控、测量、纠正偏差"
            },
            "overall": self.get_overall_coverage(),
            "missing_functions": self.missing_functions,
            "improvement_suggestions": self.improvement_suggestions,
        }


class OrganizationalLearningEngine:
    """
    Senge 第五项修炼: 组织学习引擎
    
    将"学习"嵌入组织运作中：
    1. 从每次任务执行中提取学习
    2. 记录到可搜索的知识库
    3. 在类似场景中应用
    4. 评估学习效果
    """
    
    def __init__(self):
        self.learning_records: Dict[str, LearningRecord] = {}
        self._record_counter = 0
        
        # 按类型索引
        self._by_type: Dict[str, List[str]] = {}  # learning_type -> record_ids
        
        # 按 agent 索引
        self._by_agent: Dict[str, List[str]] = {}  # agent_id -> record_ids
        
        # 按可复用性索引
        self._by_reusability: Dict[str, List[str]] = {
            "high": [], "medium": [], "low": [], "unknown": []
        }
    
    def record_learning(
        self,
        agent_id: str,
        task_id: str,
        task_name: str,
        task_result: str,
        learning_type: str,
        content: str,
        quality_score: float = 0.5,
    ) -> LearningRecord:
        """记录一次学习"""
        self._record_counter += 1
        record_id = f"lr_{self._record_counter}"
        
        # 压缩摘要（取前100字符）
        summary = content[:100] + "..." if len(content) > 100 else content
        
        # 评估可复用性
        reusability = self._assess_reusability(learning_type, quality_score, task_result)
        
        record = LearningRecord(
            record_id=record_id,
            agent_id=agent_id,
            task_id=task_id,
            task_name=task_name,
            task_result=task_result,
            learning_type=learning_type,
            content=content,
            summary=summary,
            quality_score=quality_score,
            reusability=reusability,
        )
        
        self.learning_records[record_id] = record
        
        # 更新索引
        if learning_type not in self._by_type:
            self._by_type[learning_type] = []
        self._by_type[learning_type].append(record_id)
        
        if agent_id not in self._by_agent:
            self._by_agent[agent_id] = []
        self._by_agent[agent_id].append(record_id)
        
        self._by_reusability[reusability].append(record_id)
        
        return record
    
    def _assess_reusability(self, learning_type: str, quality_score: float, task_result: str) -> str:
        """评估学习的可复用性"""
        if quality_score < 0.3:
            return "low"
        if quality_score > 0.7 and task_result == "success":
            return "high"
        return "medium"
    
    def get_relevant_learning(
        self,
        agent_id: Optional[str] = None,
        learning_type: Optional[str] = None,
        min_reusability: str = "medium",
    ) -> List[LearningRecord]:
        """获取相关学习记录"""
        candidates = set(self.learning_records.keys())
        
        if agent_id and agent_id in self._by_agent:
            candidates &= set(self._by_agent[agent_id])
        
        if learning_type and learning_type in self._by_type:
            candidates &= set(self._by_type[learning_type])
        
        # 过滤可复用性
        reusability_order = ["high", "medium", "low", "unknown"]
        min_idx = reusability_order.index(min_reusability)
        filtered = []
        for record_id in candidates:
            record = self.learning_records[record_id]
            if reusability_order.index(record.reusability) <= min_idx:
                filtered.append(record)
        
        # 按应用次数和创建时间排序
        filtered.sort(key=lambda r: (r.applied_count, r.created_at), reverse=True)
        
        return filtered
    
    def apply_learning(self, record_id: str) -> bool:
        """标记学习被应用"""
        record = self.learning_records.get(record_id)
        if record:
            record.applied_count += 1
            record.last_applied_at = time.time()
            return True
        return False
    
    def get_learning_report(self) -> Dict:
        """生成组织学习报告"""
        total = len(self.learning_records)
        by_type = {k: len(v) for k, v in self._by_type.items()}
        by_reusability = {k: len(v) for k, v in self._by_reusability.items()}
        
        avg_quality = sum(r.quality_score for r in self.learning_records.values()) / max(1, total)
        total_applications = sum(r.applied_count for r in self.learning_records.values())
        
        return {
            "total_learning_records": total,
            "by_type": by_type,
            "by_reusability": by_reusability,
            "average_quality_score": round(avg_quality, 3),
            "total_applications": total_applications,
            "learning_effectiveness": round(total_applications / max(1, total), 2) if total > 0 else 0,
        }


class MBOTargetAlignment:
    """
    Drucker MBO: 目标对齐系统
    
    组织的目标应该让每个人的工作与组织整体目标对齐。
    问：
    1. Agent 的任务是否有清晰的目标对齐机制？
    2. Agent 是否知道自己的任务如何贡献整体目标？
    """
    
    def __init__(self):
        # 团队级目标
        self.team_objectives: Dict[str, TeamObjective] = {}
        
        # Agent 目标对齐映射
        # agent_id -> [objective_id, ...]
        self.agent_objective_mapping: Dict[str, List[str]] = {}
        
        # 任务目标对齐映射
        # task_id -> objective_id
        self.task_objective_mapping: Dict[str, str] = {}
        
        # 未对齐的任务
        self.unaligned_tasks: List[str] = []
    
    def add_objective(self, objective: TeamObjective) -> str:
        """添加团队目标"""
        self.team_objectives[objective.objective_id] = objective
        return objective.objective_id
    
    def align_task_to_objective(self, task_id: str, objective_id: str) -> bool:
        """将任务对齐到目标"""
        if objective_id not in self.team_objectives:
            return False
        
        self.task_objective_mapping[task_id] = objective_id
        self.team_objectives[objective_id].aligned_task_ids.append(task_id)
        
        # 如果任务从不对齐列表移除
        if task_id in self.unaligned_tasks:
            self.unaligned_tasks.remove(task_id)
        
        return True
    
    def mark_task_unaligned(self, task_id: str):
        """标记任务未对齐"""
        if task_id not in self.unaligned_tasks:
            self.unaligned_tasks.append(task_id)
    
    def align_agent_to_objectives(self, agent_id: str, objective_ids: List[str]):
        """将 Agent 对齐到多个目标"""
        self.agent_objective_mapping[agent_id] = objective_ids
    
    def get_agent_contribution(self, agent_id: str) -> Dict:
        """获取 Agent 对整体目标的贡献"""
        objective_ids = self.agent_objective_mapping.get(agent_id, [])
        contributions = []
        
        for obj_id in objective_ids:
            obj = self.team_objectives.get(obj_id)
            if obj:
                contributions.append({
                    "objective_id": obj_id,
                    "title": obj.title,
                    "state": obj.state.value,
                    "progress": obj.progress,
                })
        
        # 计算对齐度
        aligned_tasks = sum(1 for tid in self.task_objective_mapping if 
                          self.task_objective_mapping[tid] in objective_ids)
        alignment_rate = aligned_tasks / max(1, len(self.task_objective_mapping))
        
        return {
            "agent_id": agent_id,
            "aligned_objectives": contributions,
            "total_objectives": len(objective_ids),
            "alignment_rate": round(alignment_rate, 3),
        }
    
    def get_objective_progress(self, objective_id: str) -> float:
        """计算目标进度"""
        obj = self.team_objectives.get(objective_id)
        if not obj:
            return 0.0
        
        if not obj.aligned_task_ids:
            return 0.0
        
        # 基于任务完成度计算
        # 这里需要外部提供任务状态，实际使用时应注入
        return obj.progress
    
    def get_alignment_report(self) -> Dict:
        """生成目标对齐报告"""
        total_objectives = len(self.team_objectives)
        achieved = sum(1 for o in self.team_objectives.values() if o.state == ObjectiveState.ACHIEVED)
        in_progress = sum(1 for o in self.team_objectives.values() if o.state == ObjectiveState.IN_PROGRESS)
        
        total_tasks = len(self.task_objective_mapping)
        aligned_tasks = total_tasks
        unaligned_tasks = len(self.unaligned_tasks)
        
        alignment_rate = (total_tasks - unaligned_tasks) / max(1, total_tasks)
        
        return {
            "objectives": {
                "total": total_objectives,
                "achieved": achieved,
                "in_progress": in_progress,
                "achievement_rate": round(achieved / max(1, total_objectives), 3),
            },
            "tasks": {
                "total": total_tasks,
                "aligned": aligned_tasks,
                "unaligned": unaligned_tasks,
                "alignment_rate": round(alignment_rate, 3),
            },
            "unaligned_task_ids": self.unaligned_tasks[:10],  # 最多显示10个
        }
