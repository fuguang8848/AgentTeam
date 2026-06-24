"""
Core Team Definition for AgentTeam SDK

包含 CTTeam 类的定义。
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Optional, Dict, List

from .types import AgentState, TaskState, MessageType
from .agent import CTAgent, AgentHierarchy
from .task import CTTask
from .message import CTInbox, CTMessage
from .organizational_analysis import (
    MBOTargetAlignment,
    ManagerEffectivenessFeedback,
    FayolManagementCoverage,
    FeedbackLoop,
    FeedbackLoopType,
    OrganizationalLearningEngine,
    TeamObjective,
    ObjectiveState,
)


class CTTeam:
    """
    Team Container - 团队容器

    管理多个 CTAgent 和任务，支持：
    - Agent 注册和管理
    - 任务分配和跟踪
    - 消息队列
    - 状态持久化
    """

    def __init__(self, name: str, storage_path: Optional[Path] = None):
        self.name = name
        self.agents: Dict[str, CTAgent] = {}
        self.tasks: Dict[str, CTTask] = {}
        self.inbox = CTInbox()
        self.hierarchy = AgentHierarchy()

        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            self.storage_path = Path("~/.agentteam/teams").expanduser() / name

        # ── 2026-06-24 哲学协作层初始化 ─────────────────────────────
        # 尼采系谱学：安全规则来源追踪
        self.genealogy_tracker = RuleGenealogyTracker()
        # 苏格拉底产婆术：通过诘问发现矛盾
        self.socratic_elenchus = SocraticElenchus(self)
        # 富兰克林协作协议：冲突解决
        self.collaboration_protocol = CollaborationProtocol(self)
        
        # ── Wiener 控制论反馈回路 ─────────────────────────────────
        # 真正的控制是对信息的反馈 - 完整的反馈回路
        from agentteam.philosophical import (
            CyberneticFeedbackLoop,
            BoundedRationalityTracker,
            GestellAnalyzer,
            FeedbackLoopConfig,
        )
        self.feedback_loop = CyberneticFeedbackLoop(
            config=FeedbackLoopConfig(
                ack_timeout_seconds=30.0,
                self_adjustment_enabled=True,
                deviation_threshold=0.3,
            )
        )
        
        # ── Simon 有限理性追踪器 ─────────────────────────────────
        # 多 agent 协调必须考虑每个 agent 的知识边界
        self.bounded_rationality = BoundedRationalityTracker()
        
        # ── Heidegger 技术座架分析器 ──────────────────────────────
        # 技术框架决定了什么可以被问 - 分析座架限制
        self.gestell_analyzer = GestellAnalyzer()

        # ── Drucker MBO: 目标对齐系统 ────────────────────────────
        # 组织的目标应该让每个人的工作与组织整体目标对齐
        # Agent 是否知道自己的任务如何贡献整体目标？
        self.mbo_system = MBOTargetAlignment()
        
        # ── Drucker 有效管理者: 管理者有效性反馈 ─────────────────
        # 管理者的有效性不是天生的，是可以学会的
        # 需要具体的反馈数据来改进管理者表现
        self.manager_effectiveness: Dict[str, ManagerEffectivenessFeedback] = {}
        
        # ── Fayol 五项管理功能覆盖分析 ───────────────────────────
        self.fayol_coverage = FayolManagementCoverage()
        
        # ── Senge 系统反馈回路追踪 ───────────────────────────────
        # 整体大于部分之和 - 系统的行为来自各部分之间的反馈回路
        # 识别增强回路和平衡回路
        self.senge_feedback_loops: Dict[str, FeedbackLoop] = {}
        
        # ── Senge 组织学习引擎 ───────────────────────────────────
        # "学习"必须嵌入组织运作中
        # Agent 在每次任务中是否在真正学习，还是只在执行？
        self.organizational_learning = OrganizationalLearningEngine()

        # ── Bengio 注意力可视化 ─────────────────────────────────
        # 【Bengio注意力可视化】追踪每个 agent 的"注意力"分布
        # 即每个 agent 在关注谁（哪个 agent 或任务）
        # 用于解释 multi-agent 协调中每个 agent 在"看什么"
        self._agent_attention: Dict[str, Dict[str, float]] = {}  # agent_name -> {target: attention_weight}
        
        # 消息传递的注意力权重（基于消息类型和频率）
        # 【Bengio注意力可视化】不同类型的消息有不同的注意力权重
        self._message_attention_weights: Dict[str, float] = {
            "text": 0.3,
            "task": 0.5,
            "notification": 0.4,
            "system": 0.2,
            "broadcast": 0.2,
            "direct": 0.6,
            "socratic_question": 0.8,  # 苏格拉底诘问需要高度关注
            "blind_spot_report": 0.7,   # 盲区报告需要关注
            "genealogy_trace": 0.6,    # 系谱追踪
        }
        
        # 注意力衰减因子（时间越久注意力越低）
        self._attention_decay_factor: float = 0.95
        
        # 上一次更新注意力的时间戳
        self._last_attention_update: float = time.time()
        
        # ── Marcuse 单向度修复：全局自动化退出开关 ─────────────────────
        # 7个自动化功能（NightWatch/auto-retry/DreamNet推送/CTTeam冲突协议/
        # CircuitBreaker/AgentSafety BLOCK/混合搜索）默认开启
        # 用户可通过 AUTO_MODE=false 环境变量全部关闭
        # 关闭后系统进入"批判模式"——所有自动化推送改为储备制
        # 用户主动请求时才提供建议
        self._auto_mode = os.environ.get("AUTO_MODE", "true").lower() != "false"

        # 灵感储备制：不是推送，是储备
        self._insight_reserve: list[dict] = []
        self._insight_reserve_limit = 50  # 最多储备50条
        
        self._load_state()

    # ══════════════════════════════════════════════════════════════
    # Marcuse 单向度修复：全局自动化退出开关 + 灵感储备制
    # ══════════════════════════════════════════════════════════════

    def is_auto_mode(self) -> bool:
        """当前是否自动模式"""
        return self._auto_mode

    def get_insight_reserve(self) -> list[dict]:
        """获取储备的灵感（用户主动请求时）"""
        return self._insight_reserve.copy()

    def store_insight(self, insight: dict) -> None:
        """
        储备灵感（不推送）
        Marcuse大拒绝：不是强迫用户接受，而是给用户选择权
        """
        if len(self._insight_reserve) >= self._insight_reserve_limit:
            # LRU淘汰最老的
            self._insight_reserve.pop(0)
        insight["reserved_at"] = time.time()
        self._insight_reserve.append(insight)

    def dismiss_insight(self, insight_id: str) -> bool:
        """用户主动拒绝某个灵感"""
        for i, ins in enumerate(self._insight_reserve):
            if ins.get("id") == insight_id:
                self._insight_reserve.pop(i)
                return True
        return False

    def get_auto_mode_status(self) -> dict:
        """获取自动化模式状态（供诊断用）"""
        return {
            "auto_mode": self._auto_mode,
            "insight_reserve_count": len(self._insight_reserve),
            "insight_reserve_limit": self._insight_reserve_limit,
        }

    # ==================== Agent Management ====================

    def register_agent(
        self,
        name: str,
        agent_type: str,
        session_key: str,
        metadata: Optional[dict] = None,
        parent_name: Optional[str] = None,
    ) -> CTAgent:
        """注册 Agent

        Args:
            parent_name: 可选，父 agent 名称，用于层级关系建模
        """
        agent = CTAgent(
            name=name,
            agent_type=agent_type,
            session_key=session_key,
            team_name=self.name,
            metadata=metadata or {},
        )
        self.agents[name] = agent
        self.hierarchy.add_node(name, parent_name)
        
        # ── 注册 agent 的有限理性边界 ───────────────────────────
        # Simon: 每个 agent 都有有限的知识边界
        self.bounded_rationality.register_agent(name)
        
        self._save_state()
        return agent

    def get_agent(self, name: str) -> Optional[CTAgent]:
        """获取 Agent"""
        return self.agents.get(name)

    def remove_agent(self, name: str) -> bool:
        """移除 Agent"""
        if name in self.agents:
            del self.agents[name]
            self._save_state()
            return True
        return False

    def update_agent_state(self, name: str, state: AgentState) -> bool:
        """更新 Agent 状态"""
        agent = self.agents.get(name)
        if agent:
            agent.update_state(state)
            self._save_state()
            return True
        return False

    # ══════════════════════════════════════════════════════════════
    # 2026-06-24 Bengio 注意力可视化 (Attention Visualization)
    # ══════════════════════════════════════════════════════════════

    def _update_attention_on_message(
        self,
        from_agent: str,
        to_agent: str,
        message_type: MessageType,
    ):
        """
        【Bengio注意力可视化】
        
        当消息发送时，更新发送者和接收者的注意力分布。
        这模拟了人类的注意力机制：
        - 发送者将注意力投向接收者（因为我需要你的帮助/回应）
        - 接收者将注意力投向发送者（因为有人在跟我说话）
        
        注意力权重基于消息类型：重要的消息类型（如SOCRATIC_QUESTION）权重更高。
        """
        if from_agent not in self._agent_attention:
            self._agent_attention[from_agent] = {}
        if to_agent not in self._agent_attention:
            self._agent_attention[to_agent] = {}
        
        # 获取消息类型的注意力权重
        msg_weight = self._message_attention_weights.get(message_type.value, 0.3)
        
        # 发送者对接收者的注意力 += 消息权重（发送者主动关注接收者）
        current_from_attention = self._agent_attention[from_agent].get(to_agent, 0.0)
        self._agent_attention[from_agent][to_agent] = min(1.0, current_from_attention + msg_weight)
        
        # 接收者对发送者的注意力 += 消息权重（接收者被动关注发送者）
        current_to_attention = self._agent_attention[to_agent].get(from_agent, 0.0)
        self._agent_attention[to_agent][from_agent] = min(1.0, current_to_attention + msg_weight)
        
        self._last_attention_update = time.time()
    
    def _apply_attention_decay(self):
        """
        【Bengio注意力可视化】
        
        对所有注意力应用时间衰减。
        随着时间推移，如果不更新注意力，权重会逐渐降低。
        """
        time_elapsed = time.time() - self._last_attention_update
        if time_elapsed < 1.0:
            return  # 不到1秒，不衰减
        
        decay_rate = self._attention_decay_factor ** time_elapsed
        
        for agent_name in self._agent_attention:
            for target_name in list(self._agent_attention[agent_name].keys()):
                old_weight = self._agent_attention[agent_name][target_name]
                new_weight = old_weight * decay_rate
                if new_weight < 0.01:  # 太低就移除
                    del self._agent_attention[agent_name][target_name]
                else:
                    self._agent_attention[agent_name][target_name] = new_weight
        
        self._last_attention_update = time.time()
    
    def get_agent_attention(self, agent_name: str) -> Dict[str, float]:
        """
        【Bengio注意力可视化】
        
        获取某个 agent 的注意力分布（即它在关注谁）。
        返回一个字典：{target: attention_weight}
        
        可用于可视化解释：
        - 这个 agent 当前最关注哪个 agent
        - 是否有 agent 被完全忽略
        - 注意力分布是否健康（不是只关注一个 agent）
        """
        if agent_name not in self._agent_attention:
            return {}
        
        self._apply_attention_decay()
        
        # 排序返回（按注意力权重降序）
        attention = self._agent_attention[agent_name]
        return dict(sorted(attention.items(), key=lambda x: x[1], reverse=True))
    
    def get_attention_heatmap(self) -> Dict[str, Dict[str, float]]:
        """
        【Bengio注意力可视化】
        
        获取所有 agent 的注意力热力图。
        返回：{agent_name: {target: weight}}
        
        可用于：
        - 可视化整个系统的注意力分布
        - 识别注意力孤岛（不被任何 agent 关注的 agent）
        - 识别注意力黑洞（只接收消息不发送消息的 agent）
        """
        self._apply_attention_decay()
        return dict(self._agent_attention)
    
    def get_attention_stats(self) -> dict:
        """
        【Bengio注意力可视化】
        
        获取注意力分布的统计信息。
        """
        self._apply_attention_decay()
        
        total_edges = 0
        weighted_sum = 0.0
        max_weight = 0.0
        max_weight_pair = ("", "")
        
        for agent_name, attention in self._agent_attention.items():
            for target_name, weight in attention.items():
                total_edges += 1
                weighted_sum += weight
                if weight > max_weight:
                    max_weight = weight
                    max_weight_pair = (agent_name, target_name)
        
        avg_weight = weighted_sum / total_edges if total_edges > 0 else 0.0
        
        return {
            "total_attention_edges": total_edges,
            "average_attention_weight": round(avg_weight, 3),
            "max_attention": {
                "weight": round(max_weight, 3),
                "from": max_weight_pair[0],
                "to": max_weight_pair[1],
            },
            "decay_factor": self._attention_decay_factor,
            "last_update": self._last_attention_update,
        }

    # ==================== Task Management ====================

    def create_task(
        self,
        title: str,
        description: str = "",
        assignee: Optional[str] = None,
        priority: int = 0,
    ) -> CTTask:
        """创建任务"""
        task = CTTask.create(
            title=title,
            description=description,
            assignee=assignee,
            priority=priority,
        )
        self.tasks[task.id] = task

        if assignee:
            agent = self.agents.get(assignee)
            if agent:
                agent.assign_task(task.id)

        self._save_state()
        return task

    def get_task(self, task_id: str) -> Optional[CTTask]:
        """获取任务"""
        return self.tasks.get(task_id)

    def assign_task(self, task_id: str, agent_name: str, required_domains: List[str] = None) -> bool:
        """分配任务给 Agent
        
        Simon 有限理性：任务分配应考虑 agent 的知识边界
        如果 agent 声明不知道某领域，应警告或重新分配
        """
        task = self.tasks.get(task_id)
        agent = self.agents.get(agent_name)
        
        if task and agent:
            # ── Simon 有限理性检查 ────────────────────────────────
            if required_domains:
                can_assign, missing = self.bounded_rationality.can_assign_task(
                    agent_name, required_domains
                )
                if not can_assign:
                    # Agent 知识边界不足，建议寻找其他 agent
                    candidates = self.bounded_rationality.find_competent_agents(
                        required_domains, exclude=[agent_name]
                    )
                    if candidates:
                        suggested_agent = candidates[0][0]
                        # 记录不确定性声明
                        self.bounded_rationality.declare_uncertainty(
                            agent_name=agent_name,
                            domain=", ".join(missing),
                            declaration_type="unknown",
                            reason=f"任务分配 '{task.title}' 需要但缺少: {missing}",
                            task_id=task_id,
                        )
            
            task.assign_to(agent_name)
            agent.assign_task(task_id)
            self._save_state()
            return True
        return False

    def complete_task(self, task_id: str, result: Optional[str] = None) -> bool:
        """完成任务"""
        task = self.tasks.get(task_id)
        if not task:
            return False

        task.complete(result)

        if task.assignee:
            agent = self.agents.get(task.assignee)
            if agent:
                agent.complete_task()

        self._save_state()
        return True

    def fail_task(self, task_id: str, error: str) -> bool:
        """标记任务失败"""
        task = self.tasks.get(task_id)
        if task:
            task.fail(error)
            self._save_state()
            return True
        return False

    def get_pending_tasks(self) -> List[CTTask]:
        """获取待处理任务"""
        return [t for t in self.tasks.values() if t.state == TaskState.PENDING]

    # ==================== Message Management ====================

    def send_message(
        self,
        from_agent: str,
        to_agent: str,
        content: str,
        message_type: MessageType = MessageType.TEXT,
        metadata: Optional[dict] = None,
        blind_spot_report: Optional[str] = None,
        genealogy_trace: Optional[dict] = None,
    ) -> Optional[CTMessage]:
        """发送消息，支持柏拉图洞穴盲区汇报和尼采系谱学追踪
        
        Wiener 控制论：消息发送后需要确认回执构成完整反馈回路
        """
        # 先发送消息
        msg = self.inbox.send_message(
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            message_type=message_type,
            metadata=metadata,
            blind_spot_report=blind_spot_report,
            genealogy_trace=genealogy_trace,
        )
        
        # ── Wiener: 创建确认回执 ─────────────────────────────────
        # 没有确认的发送只是噪音，不是真正的控制
        if msg:
            import hashlib
            content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
            self.feedback_loop.send_with_ack(
                message_id=msg.id,
                from_agent=from_agent,
                to_agent=to_agent,
                content_hash=content_hash,
            )
        
        # ── Bengio 注意力可视化：更新注意力分布 ──────────────────────
        self._update_attention_on_message(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
        )
        
        return msg

    def broadcast(
        self,
        from_agent: str,
        content: str,
        message_type: MessageType = MessageType.BROADCAST,
        metadata: Optional[dict] = None,
        blind_spot_report: Optional[str] = None,
        genealogy_trace: Optional[dict] = None,
    ) -> Optional[CTMessage]:
        """广播消息，支持柏拉图洞穴盲区汇报和尼采系谱学追踪
        
        Wiener 控制论：广播也需要确认回执（来自各接收者的确认）
        """
        msg = self.inbox.broadcast(
            from_agent=from_agent,
            content=content,
            message_type=message_type,
            metadata=metadata,
            blind_spot_report=blind_spot_report,
            genealogy_trace=genealogy_trace,
        )
        
        # ── Wiener: 广播也需要确认 ───────────────────────────────
        if msg:
            import hashlib
            content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
            # 广播消息需要所有 agent 确认
            for agent_name in self.agents.keys():
                if agent_name != from_agent:
                    self.feedback_loop.send_with_ack(
                        message_id=f"{msg.id}_{agent_name}",
                        from_agent=from_agent,
                        to_agent=agent_name,
                        content_hash=content_hash,
                    )
        
        # ── Bengio 注意力可视化：广播者对所有接收者更新注意力 ──────────
        for agent_name in self.agents.keys():
            if agent_name != from_agent:
                self._update_attention_on_message(
                    from_agent=from_agent,
                    to_agent=agent_name,
                    message_type=message_type,
                )
        
        return msg

    def get_messages(
        self,
        agent_name: Optional[str] = None,
        unread_only: bool = False,
        message_type: Optional[MessageType] = None,
    ) -> List[CTMessage]:
        """获取消息，支持按消息类型过滤（包括 SOCRATIC_QUESTION、BLIND_SPOT_REPORT、GENEALOGY_TRACE）"""
        return self.inbox.get_messages(agent_name=agent_name, unread_only=unread_only, message_type=message_type)

    # ==================== Status & Utilities ====================

    def get_status(self) -> dict:
        """获取团队状态
        
        包含 Wiener 控制论反馈回路健康状态
        """
        status = {
            "team": self.name,
            "agents": {
                name: {"state": a.state.value, "type": a.agent_type, "task_id": a.task_id}
                for name, a in self.agents.items()
            },
            "tasks": {
                "total": len(self.tasks),
                "completed": sum(1 for t in self.tasks.values() if t.state == TaskState.COMPLETED),
                "in_progress": sum(1 for t in self.tasks.values() if t.state == TaskState.IN_PROGRESS),
            },
            "inbox": {
                "total": len(self.inbox.messages),
                "unread": self.inbox.count(unread_only=True),
            },
            # ── Wiener 控制论反馈回路健康状态 ─────────────────────
            "cybernetic_feedback": {
                "pending_acks": self.feedback_loop.get_pending_acks_count(),
                "health": self.feedback_loop.get_cybernetic_report().get("feedback_loop_health", "unknown"),
            },
            # ── Simon 有限理性状态 ────────────────────────────────
            "bounded_rationality": {
                "tracked_agents": len(self.bounded_rationality.knowledge_boundaries),
                "uncertain_agents": sum(
                    1 for kb in self.bounded_rationality.knowledge_boundaries.values()
                    if kb.confidence_level < 0.8
                ),
            },
            # ── Bengio 注意力可视化状态 ───────────────────────────
            "attention": self.get_attention_stats(),
        }
        return status

    # ══════════════════════════════════════════════════════════════
    # 2026-06-24 Drucker MBO + Fayol + Senge 组织管理与系统思维
    # ══════════════════════════════════════════════════════════════

    def create_team_objective(
        self,
        title: str,
        description: str,
        success_criteria: str,
        owner: str,
        deadline: Optional[float] = None,
    ) -> str:
        """
        【Drucker MBO】创建团队目标
        
        组织的目标应该让每个人的工作与组织整体目标对齐。
        每个目标需要：
        1. 清晰的成功标准
        2. 明确的负责人
        3. 时间线
        """
        import uuid
        objective_id = f"obj_{uuid.uuid4().hex[:8]}"
        objective = TeamObjective(
            objective_id=objective_id,
            title=title,
            description=description,
            success_criteria=success_criteria,
            owner=owner,
            deadline=deadline,
        )
        self.mbo_system.add_objective(objective)
        return objective_id

    def align_task_to_objective(self, task_id: str, objective_id: str) -> bool:
        """
        【Drucker MBO】将任务对齐到目标
        
        问：Agent 是否知道自己的任务如何贡献整体目标？
        """
        success = self.mbo_system.align_task_to_objective(task_id, objective_id)
        if success:
            self._save_state()
        return success

    def get_agent_contribution(self, agent_name: str) -> dict:
        """
        【Drucker MBO】获取 Agent 对整体目标的贡献
        
        回答：Agent 的任务如何贡献整体目标？
        """
        return self.mbo_system.get_agent_contribution(agent_name)

    def record_manager_effectiveness(
        self,
        manager_id: str,
        objective_achievement_rate: float,
        team_output_quality: float,
        decision_quality_score: float,
        resource_efficiency: float,
        agent_development_score: float,
    ) -> ManagerEffectivenessFeedback:
        """
        【Drucker 有效管理者】记录管理者有效性反馈
        
        管理者的有效性不是天生的，是可以学会的。
        需要具体的反馈数据来改进管理者表现。
        """
        feedback = ManagerEffectivenessFeedback(
            manager_id=manager_id,
            objective_achievement_rate=objective_achievement_rate,
            team_output_quality=team_output_quality,
            decision_quality_score=decision_quality_score,
            resource_efficiency=resource_efficiency,
            agent_development_score=agent_development_score,
        )
        self.manager_effectiveness[manager_id] = feedback
        return feedback

    def get_manager_effectiveness_report(self, manager_id: str) -> dict:
        """获取管理者有效性报告"""
        feedback = self.manager_effectiveness.get(manager_id)
        if not feedback:
            return {"error": f"No effectiveness data for manager {manager_id}"}
        return feedback.to_dict()

    def analyze_fayol_coverage(self) -> dict:
        """
        【Fayol 五项管理功能】覆盖分析
        
        计划 (Planning): 目标设定、战略制定
        组织 (Organizing): 资源分配、结构设计
        指挥 (Commanding): 指示、指导、领导
        协调 (Coordinating): 整合活动、解决冲突
        控制 (Controlling): 监控、纠正偏差
        """
        coverage = self.fayol_coverage
        
        # 检查计划功能
        if hasattr(self, 'mbo_system') and self.mbo_system.team_objectives:
            coverage.planning_coverage = min(1.0, 0.4 + len(self.mbo_system.team_objectives) * 0.1)
        
        # 检查组织功能
        if hasattr(self, 'bounded_rationality'):
            coverage.organizing_coverage = 0.7  # 有资源分配
        
        # 检查指挥功能 - 需要有 coordinator agent
        if hasattr(self, 'hierarchy'):
            has_coordinator = any(
                a.agent_type == 'coordinator' for a in self.agents.values()
            )
            coverage.commanding_coverage = 0.8 if has_coordinator else 0.3
        
        # 检查协调功能
        if hasattr(self, 'collaboration_protocol'):
            coverage.coordinating_coverage = 0.75
        
        # 检查控制功能
        if hasattr(self, 'feedback_loop'):
            coverage.controlling_coverage = 0.7
        
        # 识别缺失功能
        coverage.missing_functions = []
        if coverage.planning_coverage < 0.5:
            coverage.missing_functions.append("planning")
        if coverage.commanding_coverage < 0.5:
            coverage.missing_functions.append("commanding")
        if coverage.controlling_coverage < 0.5:
            coverage.missing_functions.append("controlling")
        
        # 改进建议
        coverage.improvement_suggestions = []
        if coverage.planning_coverage < 0.7:
            coverage.improvement_suggestions.append(
                "建议：建立更正式的目标设定和战略规划流程"
            )
        if coverage.commanding_coverage < 0.7:
            coverage.improvement_suggestions.append(
                "建议：明确 coordinator agent 的领导角色和指令传达机制"
            )
        if coverage.controlling_coverage < 0.7:
            coverage.improvement_suggestions.append(
                "建议：增强偏差检测和纠正机制"
            )
        
        return coverage.analyze_coverage()

    def register_feedback_loop(
        self,
        name: str,
        loop_type: FeedbackLoopType,
        description: str,
        variables: List[str],
        strength: float = 1.0,
    ) -> str:
        """
        【Senge 系统思维】注册反馈回路
        
        整体大于部分之和 - 系统的行为来自各部分之间的反馈回路。
        识别增强回路和平衡回路：
        - 增强回路 (Reinforcing): 放大变化，如成功带来更多成功
        - 平衡回路 (Balancing): 趋于稳定目标，如 thermostat
        """
        import uuid
        loop_id = f"loop_{uuid.uuid4().hex[:8]}"
        loop = FeedbackLoop(
            loop_id=loop_id,
            name=name,
            loop_type=loop_type,
            description=description,
            variables=variables,
            strength=strength,
        )
        self.senge_feedback_loops[loop_id] = loop
        return loop_id

    def trigger_feedback_loop(self, loop_id: str) -> bool:
        """触发反馈回路"""
        loop = self.senge_feedback_loops.get(loop_id)
        if loop and loop.is_active:
            loop.trigger_count += 1
            loop.last_triggered = time.time()
            return True
        return False

    def get_senge_feedback_report(self) -> dict:
        """
        【Senge 系统思维】反馈回路分析报告
        
        检查是否存在隐藏的反馈回路：
        - 增强回路可能导致指数级增长或崩溃
        - 平衡回路可能导致振荡或稳定
        """
        reinforcing = []
        balancing = []
        
        for loop in self.senge_feedback_loops.values():
            loop_info = {
                "loop_id": loop.loop_id,
                "name": loop.name,
                "strength": loop.strength,
                "trigger_count": loop.trigger_count,
                "last_triggered": loop.last_triggered,
            }
            if loop.loop_type == FeedbackLoopType.REINFORCING:
                reinforcing.append(loop_info)
            else:
                balancing.append(loop_info)
        
        return {
            "total_loops": len(self.senge_feedback_loops),
            "reinforcing_loops": reinforcing,
            "balancing_loops": balancing,
            "potential_risks": self._identify_feedback_risks(reinforcing, balancing),
        }

    def _identify_feedback_risks(self, reinforcing: List, balancing: List) -> List[str]:
        """识别反馈回路潜在风险"""
        risks = []
        
        # 强增强回路无平衡回路可能失控
        strong_reinforcing = [r for r in reinforcing if r['strength'] > 1.5]
        if strong_reinforcing and not balancing:
            risks.append("存在强增强回路但缺乏平衡回路，可能导致失控增长")
        
        # 多个平衡回路可能造成振荡
        if len(balancing) > 3:
            risks.append("多个平衡回路可能造成系统振荡")
        
        return risks

    def record_organizational_learning(
        self,
        agent_id: str,
        task_id: str,
        task_name: str,
        task_result: str,
        learning_type: str,
        content: str,
        quality_score: float = 0.5,
    ) -> str:
        """
        【Senge 第五项修炼】记录组织学习
        
        "学习"必须嵌入组织运作中。
        问：Agent 在每次任务中是否在真正学习，还是只在执行？
        """
        record = self.organizational_learning.record_learning(
            agent_id=agent_id,
            task_id=task_id,
            task_name=task_name,
            task_result=task_result,
            learning_type=learning_type,
            content=content,
            quality_score=quality_score,
        )
        return record.record_id

    def get_relevant_learning(
        self,
        agent_id: Optional[str] = None,
        learning_type: Optional[str] = None,
    ) -> List[dict]:
        """获取相关学习记录，用于任务规划参考"""
        records = self.organizational_learning.get_relevant_learning(
            agent_id=agent_id,
            learning_type=learning_type,
        )
        return [r.to_dict() for r in records]

    def get_organizational_learning_report(self) -> dict:
        """【Senge 第五项修炼】组织学习报告"""
        return self.organizational_learning.get_learning_report()

    def get_organizational_health_report(self) -> dict:
        """
        综合组织健康度报告
        
        整合 Drucker MBO + Fayol + Senge 三个维度的分析
        """
        return {
            "drucker_mbo": self.mbo_system.get_alignment_report(),
            "fayol_coverage": self.analyze_fayol_coverage(),
            "senge_feedback": self.get_senge_feedback_report(),
            "organizational_learning": self.get_organizational_learning_report(),
        }

    # ══════════════════════════════════════════════════════════════
    # End of Drucker + Fayol + Senge 组织管理
    # ══════════════════════════════════════════════════════════════

    def wait_all(self, timeout: int = 3600, check_deadlock: bool = True) -> dict:
        """等待所有 Agent 完成
        
        Simon 有限理性：无限等待违反有限理性原则
        - 添加了渐进式警告
        - 可选的死锁检测
        - 违反有限理性时抛出异常
        """
        import logging
        start = time.time()
        last_warning_time = start
        
        while time.time() - start < timeout:
            states = [a.state for a in self.agents.values()]
            
            # 检查是否全部完成
            if all(s in (AgentState.COMPLETED, AgentState.FAILED) for s in states):
                return self.get_status()
            
            # ── 渐进式警告：避免无限等待 ───────────────────────────
            elapsed = time.time() - start
            if elapsed > 60 and time.time() - last_warning_time > 60:
                logging.warning(
                    f"[Bounded Rationality] wait_all 等待已超过 {elapsed:.0f}秒"
                    f" - 可能存在死锁或任务卡住"
                )
                last_warning_time = time.time()
                
                # ── 可选的死锁检测 ───────────────────────────────
                if check_deadlock:
                    conflicts = self.collaboration_protocol.detect_conflicts()
                    if conflicts:
                        logging.error(
                            f"[Bounded Rationality] 检测到 {len(conflicts)} 个潜在冲突"
                        )
            
            time.sleep(1)
        
        # ── 超时：违反有限理性 ───────────────────────────────────
        elapsed = time.time() - start
        logging.error(
            f"[Bounded Rationality] wait_all 超时 ({timeout}秒)"
            f" - 这违反了 Simon 的有限理性原则：不应该无限等待"
        )
        return self.get_status()

    # ==================== Persistence ====================

    def _get_state_file(self) -> Path:
        """获取状态文件路径"""
        return self.storage_path / "team_state.json"

    def _save_state(self) -> None:
        """保存状态"""
        try:
            self.storage_path.mkdir(parents=True, exist_ok=True)
            state = {
                "name": self.name,
                "agents": {name: agent.to_dict() for name, agent in self.agents.items()},
                "tasks": {tid: task.to_dict() for tid, task in self.tasks.items()},
                "inbox": self.inbox.to_dict(),
                "hierarchy": self.hierarchy.to_dict(),
            }
            with open(self._get_state_file(), "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _load_state(self) -> None:
        """加载状态"""
        state_file = self._get_state_file()
        if state_file.exists():
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)

                self.name = state.get("name", self.name)
                self.agents = {name: CTAgent.from_dict(data) for name, data in state.get("agents", {}).items()}
                self.tasks = {tid: CTTask.from_dict(data) for tid, data in state.get("tasks", {}).items()}
                self.inbox = CTInbox.from_dict(state.get("inbox", {}))
                self.hierarchy = AgentHierarchy.from_dict(state.get("hierarchy", {}))
            except Exception:
                pass

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "name": self.name,
            "agents": {name: agent.to_dict() for name, agent in self.agents.items()},
            "tasks": {tid: task.to_dict() for tid, task in self.tasks.items()},
        }

    @classmethod
    def from_dict(cls, data: dict, storage_path: Optional[Path] = None) -> "CTTeam":
        """从字典创建"""
        team = cls(data.get("name", "unknown"), storage_path=storage_path)
        team.agents = {name: CTAgent.from_dict(agent_data) for name, agent_data in data.get("agents", {}).items()}
        team.tasks = {tid: CTTask.from_dict(task_data) for tid, task_data in data.get("tasks", {}).items()}
        return team


# Backwards compatibility alias
Team = CTTeam


# ══════════════════════════════════════════════════════════════
# 2026-06-24 富兰克林协作协议层
# 冲突解决 + 谈判 + 共识达成
# ══════════════════════════════════════════════════════════════

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import time
import uuid as _uuid


class ConflictType(Enum):
    """冲突类型"""
    TASK_OVERLAP = "task_overlap"       # 任务重叠（两个 agent 争抢同一任务）
    RESOURCE_CONTENTION = "resource"    # 资源争用（同时需要同一资源）
    PRIORITY_DISPUTE = "priority"       # 优先级争议
    GOAL_MISMATCH = "goal_mismatch"    # 目标不一致
    DEADLOCK = "deadlock"              # 死锁（相互等待）


class NegotiationStatus(Enum):
    """谈判状态"""
    PROPOSED = "proposed"              # 方案已提出
    ACCEPTED = "accepted"              # 接受
    REJECTED = "rejected"              # 拒绝
    COUNTERED = "countered"            # 反提案
    WITHDRAWN = "withdrawn"            # 撤回
    EXPIRED = "expired"                # 超时


@dataclass
class ConflictRecord:
    """冲突记录"""
    id: str
    conflict_type: ConflictType
    agents_involved: list[str]
    description: str
    severity: int  # 1-10
    created_at: float = field(default_factory=time.time)
    resolved: bool = False
    resolution: str = ""
    resolved_at: float = 0.0


@dataclass
class NegotiationProposal:
    """谈判提案"""
    id: str
    conflict_id: str
    proposer: str
    proposee: str  # 对方 agent
    status: NegotiationStatus = NegotiationStatus.PROPOSED
    description: str = ""
    proposed_actions: list[str] = field(default_factory=list)
    priority_win: str = ""  # 谁赢："proposer" / "proposee" / "compromise"
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    votes_for: list[str] = field(default_factory=list)
    votes_against: list[str] = field(default_factory=list)


# ══════════════════════════════════════════════════════════════
# 2026-06-24 尼采系谱学层 (Nietzschean Genealogy)
# 安全规则来源追踪 — 何时创建、何人创建、何原因
# ══════════════════════════════════════════════════════════════


@dataclass
class SafetyPolicyGenealogy:
    """
    尼采系谱学 — 安全规则的谱系追踪

    每条 SafetyPolicy 记录其"谱系"：
    - rule_id:       规则唯一标识
    - created_at:    创建时间戳
    - created_by:    创建者（agent / human / system）
    - reason:        创建原因（为什么需要这条规则）
    - parent_rule_id: 派生自哪条更早的规则（追溯起源）
    - ancestors:     完整祖先链 [root_rule_id, ..., parent_rule_id]
    - version:       版本号
    - is_overridden: 是否被后续规则覆盖
    """

    rule_id: str
    created_at: float = field(default_factory=time.time)
    created_by: str = "system"
    reason: str = ""
    parent_rule_id: Optional[str] = None
    ancestors: list[str] = field(default_factory=list)
    version: int = 1
    is_overridden: bool = False
    overridden_by: Optional[str] = None
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "reason": self.reason,
            "parent_rule_id": self.parent_rule_id,
            "ancestors": self.ancestors,
            "version": self.version,
            "is_overridden": self.is_overridden,
            "overridden_by": self.overridden_by,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SafetyPolicyGenealogy":
        return cls(
            rule_id=data["rule_id"],
            created_at=data.get("created_at", time.time()),
            created_by=data.get("created_by", "system"),
            reason=data.get("reason", ""),
            parent_rule_id=data.get("parent_rule_id"),
            ancestors=data.get("ancestors", []),
            version=data.get("version", 1),
            is_overridden=data.get("is_overridden", False),
            overridden_by=data.get("overridden_by"),
            description=data.get("description", ""),
        )


class RuleGenealogyTracker:
    """
    安全规则系谱追踪器

    核心功能：
    1. register_rule:      注册新规则，记录其谱系
    2. derive_rule:       派生新规则（建立父子关系）
    3. override_rule:     覆盖旧规则
    4. get_genealogy:     查询完整谱系
    5. trace_back:        追溯到最原始的根规则
    """

    def __init__(self):
        self.policies: dict[str, SafetyPolicyGenealogy] = {}

    def register_rule(
        self,
        rule_id: str,
        created_by: str = "system",
        reason: str = "",
        description: str = "",
    ) -> SafetyPolicyGenealogy:
        """注册一条新规则（根规则，无父规则）"""
        gp = SafetyPolicyGenealogy(
            rule_id=rule_id,
            created_by=created_by,
            reason=reason,
            description=description,
            ancestors=[],
        )
        self.policies[rule_id] = gp
        return gp

    def derive_rule(
        self,
        child_rule_id: str,
        parent_rule_id: str,
        created_by: str,
        reason: str,
        description: str = "",
    ) -> Optional[SafetyPolicyGenealogy]:
        """派生新规则（子规则，继承 parent_rule_id 的谱系）"""
        parent = self.policies.get(parent_rule_id)
        if not parent:
            return None

        ancestors = parent.ancestors + [parent_rule_id]
        gp = SafetyPolicyGenealogy(
            rule_id=child_rule_id,
            created_by=created_by,
            reason=reason,
            parent_rule_id=parent_rule_id,
            ancestors=ancestors,
            description=description,
        )
        self.policies[child_rule_id] = gp
        return gp

    def override_rule(
        self,
        old_rule_id: str,
        new_rule_id: str,
        created_by: str,
        reason: str,
        description: str = "",
    ) -> Optional[SafetyPolicyGenealogy]:
        """覆盖旧规则（新规则取代旧规则）"""
        old = self.policies.get(old_rule_id)
        if not old:
            return None

        # 标记旧规则为已覆盖
        old.is_overridden = True
        old.overridden_by = new_rule_id

        # 创建新规则，继承旧规则的完整祖先链
        ancestors = old.ancestors + [old_rule_id]
        gp = SafetyPolicyGenealogy(
            rule_id=new_rule_id,
            created_by=created_by,
            reason=reason,
            parent_rule_id=old_rule_id,
            ancestors=ancestors,
            description=description,
            version=old.version + 1,
        )
        self.policies[new_rule_id] = gp
        return gp

    def get_genealogy(self, rule_id: str) -> Optional[dict]:
        """获取规则的完整谱系报告"""
        rule = self.policies.get(rule_id)
        if not rule:
            return None

        ancestor_chain = []
        for ancestor_id in rule.ancestors:
            anc = self.policies.get(ancestor_id)
            if anc:
                ancestor_chain.append({
                    "rule_id": anc.rule_id,
                    "created_at": anc.created_at,
                    "created_by": anc.created_by,
                    "reason": anc.reason,
                })

        return {
            "rule_id": rule.rule_id,
            "version": rule.version,
            "created_at": rule.created_at,
            "created_by": rule.created_by,
            "reason": rule.reason,
            "description": rule.description,
            "is_overridden": rule.is_overridden,
            "overridden_by": rule.overridden_by,
            "parent_rule_id": rule.parent_rule_id,
            "ancestor_chain": ancestor_chain,
            "root_rule_id": ancestor_chain[0]["rule_id"] if ancestor_chain else rule.rule_id,
        }

    def trace_back(self, rule_id: str) -> list[str]:
        """追溯到最原始的根规则"""
        rule = self.policies.get(rule_id)
        if not rule:
            return []
        if not rule.ancestors:
            return [rule_id]
        return [rule.ancestors[0]] + self.trace_back(rule.ancestors[0])

    def get_all_rules_report(self) -> dict:
        """生成所有规则的完整谱系报告"""
        return {
            "total_rules": len(self.policies),
            "active_rules": len([r for r in self.policies.values() if not r.is_overridden]),
            "overridden_rules": len([r for r in self.policies.values() if r.is_overridden]),
            "rules": {
                rule_id: self.get_genealogy(rule_id)
                for rule_id, rule in self.policies.items()
            },
        }


# ══════════════════════════════════════════════════════════════
# 2026-06-24 苏格拉底产婆术层 (Socratic Elenchus)
# 通过诘问让对方发现自己的矛盾
# ══════════════════════════════════════════════════════════════


@dataclass
class SocraticQuestion:
    """
    苏格拉底诘问 — 质疑对方论点的矛盾

    属性：
    - question_id:     诘问唯一ID
    - from_agent:      提问者
    - to_agent:       被提问者
    - target_claim:   被质疑的主张内容
    - question_type:  诘问类型（证据/反例/假设/推理链）
    - question_text:  具体的诘问问题
    - created_at:     提问时间戳
    - answered:       是否已回答
    - answer:         回答内容
    """
    question_id: str = field(default_factory=lambda: f"sq_{_uuid.uuid4().hex[:8]}")
    from_agent: str = ""
    to_agent: str = ""
    target_claim: str = ""
    question_type: str = "evidence"  # evidence | counterexample | assumption | inference
    question_text: str = ""
    created_at: float = field(default_factory=time.time)
    answered: bool = False
    answer: str = ""

    # 标准苏格拉底诘问模板
    EVIDENCE_QUESTION = "你怎么知道这是正确的？支撑这个结论的证据是什么？"
    COUNTEREXAMPLE_QUESTION = "这个结论有没有反例？如果有，会是什么？"
    ASSUMPTION_QUESTION = "你这个推理依赖于什么前提？那个前提本身成立吗？"
    INFERENCE_QUESTION = "从前提到结论的推理链条是什么？每一步都必然成立吗？"

    def to_dict(self) -> dict:
        return {
            "question_id": self.question_id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "target_claim": self.target_claim,
            "question_type": self.question_type,
            "question_text": self.question_text,
            "created_at": self.created_at,
            "answered": self.answered,
            "answer": self.answer,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SocraticQuestion":
        return cls(**data)


class SocraticElenchus:
    """
    苏格拉底产婆术管理器

    核心理念：对话不是传递信息，而是通过诘问让对方发现自己的矛盾。
    当一个 agent 收到另一个 agent 的报告/结论时，它应该：
    1. 识别该结论依赖的关键主张
    2. 用标准诘问模板追问（证据、反例、假设、推理链）
    3. 如果对方无法回答，则该结论被质疑

    支持的诘问类型：
    - evidence:       质疑证据（"你怎么知道这是正确的？"）
    - counterexample: 质疑反例（"有没有反例？"）
    - assumption:     质疑隐藏假设（"这个前提成立吗？"）
    - inference:      质疑推理链（"推理每一步都必然吗？"）
    """

    def __init__(self, team: "CTTeam"):
        self.team = team
        self.questions: dict[str, SocraticQuestion] = {}
        self._counter = 0

    def generate_question(
        self,
        from_agent: str,
        to_agent: str,
        target_claim: str,
        question_type: str = "evidence",
        custom_question: Optional[str] = None,
    ) -> SocraticQuestion:
        """生成一个苏格拉底诘问，并自动发送到 to_agent"""
        self._counter += 1
        question_text = custom_question or {
            "evidence": SocraticQuestion.EVIDENCE_QUESTION,
            "counterexample": SocraticQuestion.COUNTEREXAMPLE_QUESTION,
            "assumption": SocraticQuestion.ASSUMPTION_QUESTION,
            "inference": SocraticQuestion.INFERENCE_QUESTION,
        }.get(question_type, SocraticQuestion.EVIDENCE_QUESTION)

        sq = SocraticQuestion(
            question_id=f"sq_{self._counter}",
            from_agent=from_agent,
            to_agent=to_agent,
            target_claim=target_claim,
            question_type=question_type,
            question_text=f"[苏格拉底诘问] {question_text}\n\n[被质疑的主张]: {target_claim}",
        )
        self.questions[sq.question_id] = sq

        # 发送 SOCRATIC_QUESTION 类型的消息
        self.team.send_message(
            from_agent=from_agent,
            to_agent=to_agent,
            content=sq.question_text,
            message_type=MessageType.SOCRATIC_QUESTION,
            metadata={
                "socratic_question_id": sq.question_id,
                "question_type": question_type,
                "target_claim": target_claim,
            },
        )
        return sq

    def answer_question(self, question_id: str, answer: str) -> dict:
        """被提问者回答诘问"""
        sq = self.questions.get(question_id)
        if not sq:
            return {"status": "not_found"}

        sq.answered = True
        sq.answer = answer

        # 发送回答回提问者
        self.team.send_message(
            from_agent=sq.to_agent,
            to_agent=sq.from_agent,
            content=f"[苏格拉底回答] question_id={question_id}\n\n{answer}",
            message_type=MessageType.TEXT,
            metadata={"socratic_question_id": question_id, "answered": True},
        )
        return {"status": "answered", "question_id": question_id}

    def get_pending_questions(self, agent_name: Optional[str] = None) -> list[dict]:
        """获取待回答的诘问"""
        result = []
        for sq in self.questions.values():
            if not sq.answered:
                if agent_name is None or sq.to_agent == agent_name:
                    result.append(sq.to_dict())
        return result

    def get_questions_report(self) -> dict:
        """生成诘问统计报告"""
        all_qs = list(self.questions.values())
        answered = [q for q in all_qs if q.answered]
        pending = [q for q in all_qs if not q.answered]

        by_type: dict[str, int] = {}
        for q in all_qs:
            by_type[q.question_type] = by_type.get(q.question_type, 0) + 1

        return {
            "total_questions": len(all_qs),
            "answered": len(answered),
            "pending": len(pending),
            "by_type": by_type,
            "collaboration_score": round(len(answered) / max(1, len(all_qs)), 2),
        }


class CollaborationProtocol:
    """
    富兰克林协作协议 — 叠加在 CTTeam 之上的冲突解决层

    核心理念（富兰克林 × 亚当斯）：
    - 富兰克林：诚实地承认冲突，不掩盖，通过谈判解决
    - 亚当斯：量级放大 — 优先解决最严重的冲突

    支持的冲突解决策略：
    1. 任务优先级仲裁（priority-based arbitration）
    2. 资源轮换（resource rotation）
    3. 谈判协商（negotiation with counter-proposal）
    4. 投票共识（voting-based consensus）
    5. 第三方调解（mediation via supervisor）
    """

    def __init__(self, team: CTTeam):
        self.team = team
        self.conflicts: dict[str, ConflictRecord] = {}
        self.negotiations: dict[str, NegotiationProposal] = {}
        self._negotiation_counter = 0

    # ── 冲突检测 ───────────────────────────

    def detect_conflicts(self) -> list[ConflictRecord]:
        """检测当前所有冲突"""
        detected = []

        # 冲突1：任务重叠（同一任务被多个 agent 认领）
        task_agents: dict[str, list[str]] = {}
        for agent in self.team.agents.values():
            task_id = getattr(agent, 'task_id', None)
            if task_id:
                if task_id not in task_agents:
                    task_agents[task_id] = []
                task_agents[task_id].append(agent.name)

        for task_id, agents in task_agents.items():
            if len(agents) > 1:
                conflict = ConflictRecord(
                    id=f"conflict_task_{task_id}",
                    conflict_type=ConflictType.TASK_OVERLAP,
                    agents_involved=agents,
                    description=f"任务 {task_id} 被 {len(agents)} 个 agent 争抢: {agents}",
                    severity=7,
                )
                if conflict.id not in self.conflicts:
                    self.conflicts[conflict.id] = conflict
                detected.append(conflict)

        # 冲突2：死锁检测（两个 agent 互相等待对方完成任务）
        for a1_name, a1 in self.team.agents.items():
            for a2_name, a2 in self.team.agents.items():
                if a1_name >= a2_name:
                    continue
                # 简化检测：检查是否有互相等待的消息
                msgs = self.team.get_messages(a1_name)
                for msg in msgs:
                    if msg.from_agent == a2_name:
                        # 发现 a2 向 a1 发过消息，a1 可能也在等 a2
                        detected.append(ConflictRecord(
                            id=f"conflict_deadlock_{a1_name}_{a2_name}",
                            conflict_type=ConflictType.DEADLOCK,
                            agents_involved=[a1_name, a2_name],
                            description=f"可能死锁: {a1_name} ↔ {a2_name}",
                            severity=8,
                        ))

        return detected

    # ── 冲突解决 ───────────────────────────

    def resolve_via_priority(self, conflict_id: str) -> dict:
        """
        优先级仲裁：优先级高的 agent 获得资源

        富兰克林诚信：不偏袒，按规则办
        """
        conflict = self.conflicts.get(conflict_id)
        if not conflict:
            return {"status": "not_found"}

        agents = conflict.agents_involved
        if not agents:
            return {"status": "no_agents"}

        # 找优先级最高的 agent（通过 metadata 或 agent_type）
        priority_key = lambda name: (
            -self.team.agents[name].metadata.get("priority", 5),
            name,
        )
        winner = min(agents, key=priority_key)

        conflict.resolved = True
        conflict.resolution = f"优先级仲裁: {winner} 获得资源"
        conflict.resolved_at = time.time()

        return {
            "status": "resolved",
            "winner": winner,
            "conflict_id": conflict_id,
            "method": "priority_arbitration",
        }

    def start_negotiation(
        self,
        conflict_id: str,
        proposer: str,
        proposee: str,
        description: str,
        proposed_actions: list[str],
    ) -> NegotiationProposal:
        """
        发起谈判

        流程：
        1. proposer 提出方案
        2. proposee 可以接受/拒绝/反提案
        3. 双方达成共识或升级到 supervisor 仲裁
        """
        self._negotiation_counter += 1
        proposal = NegotiationProposal(
            id=f"neg_{self._negotiation_counter}",
            conflict_id=conflict_id,
            proposer=proposer,
            proposee=proposee,
            description=description,
            proposed_actions=proposed_actions,
            expires_at=time.time() + 300,  # 5分钟超时
        )
        self.negotiations[proposal.id] = proposal
        return proposal

    def respond_to_proposal(
        self,
        proposal_id: str,
        response: str,  # "accept" / "reject" / "counter"
        counter_actions: Optional[list[str]] = None,
    ) -> dict:
        """
        响应谈判提案

        - accept: 接受方案，冲突解决
        - reject: 拒绝，可能升级
        - counter: 反提案，返回新谈判
        """
        proposal = self.negotiations.get(proposal_id)
        if not proposal:
            return {"status": "not_found"}

        if time.time() > proposal.expires_at:
            proposal.status = NegotiationStatus.EXPIRED
            return {"status": "expired", "proposal_id": proposal_id}

        if response == "accept":
            proposal.status = NegotiationStatus.ACCEPTED
            # 解决冲突
            conflict = self.conflicts.get(proposal.conflict_id)
            if conflict:
                conflict.resolved = True
                conflict.resolution = f"谈判达成: {proposal.description}"
                conflict.resolved_at = time.time()
            return {"status": "accepted", "proposal_id": proposal_id}

        elif response == "reject":
            proposal.status = NegotiationStatus.REJECTED
            return {"status": "rejected", "proposal_id": proposal_id}

        elif response == "counter" and counter_actions:
            proposal.status = NegotiationStatus.COUNTERED
            # 创建反提案
            new_proposal = self.start_negotiation(
                conflict_id=proposal.conflict_id,
                proposer=proposal.proposee,
                proposee=proposal.proposer,
                description=f"反提案: {proposal.description}",
                proposed_actions=counter_actions,
            )
            return {"status": "countered", "original_id": proposal_id, "new_proposal_id": new_proposal.id}

        return {"status": "unknown_response"}

    def vote_on_proposal(self, proposal_id: str, voter: str, vote: bool) -> dict:
        """
        投票决定提案

        适用场景：多人团队中多个 agent 对某提案投票
        决策规则：简单多数，票数相同则优先考虑优先级
        """
        proposal = self.negotiations.get(proposal_id)
        if not proposal:
            return {"status": "not_found"}

        if vote:
            if voter not in proposal.votes_for:
                proposal.votes_for.append(voter)
            if voter in proposal.votes_against:
                proposal.votes_against.remove(voter)
        else:
            if voter not in proposal.votes_against:
                proposal.votes_against.append(voter)
            if voter in proposal.votes_for:
                proposal.votes_for.remove(voter)

        # 检查是否达成共识
        total_agents = len(self.team.agents)
        if len(proposal.votes_for) > total_agents / 2:
            proposal.status = NegotiationStatus.ACCEPTED
            return {"status": "passed", "proposal_id": proposal_id}
        if len(proposal.votes_against) >= total_agents / 2:
            proposal.status = NegotiationStatus.REJECTED
            return {"status": "rejected", "proposal_id": proposal_id}

        return {
            "status": "pending",
            "votes_for": proposal.votes_for,
            "votes_against": proposal.votes_against,
        }

    def escalate_to_supervisor(self, conflict_id: str) -> dict:
        """
        升级到 supervisor 仲裁

        亚当斯量级放大：如果谈判失败，交给更有权力的第三方
        """
        conflict = self.conflicts.get(conflict_id)
        if not conflict:
            return {"status": "not_found"}

        return {
            "status": "escalated",
            "conflict_id": conflict_id,
            "escalated_to": "supervisor",
            "description": conflict.description,
            "severity": conflict.severity,
        }

    # ── 状态查询 ───────────────────────────

    def get_conflict_report(self) -> dict:
        """生成冲突报告（富兰克林自省法：诚实面对问题）"""
        unresolved = [c for c in self.conflicts.values() if not c.resolved]
        resolved = [c for c in self.conflicts.values() if c.resolved]

        return {
            "total_conflicts": len(self.conflicts),
            "unresolved": len(unresolved),
            "resolved": len(resolved),
            "unresolved_list": [
                {
                    "id": c.id,
                    "type": c.conflict_type.value,
                    "agents": c.agents_involved,
                    "severity": c.severity,
                    "description": c.description,
                    "age_seconds": round(time.time() - c.created_at, 1),
                }
                for c in sorted(unresolved, key=lambda x: -x.severity)
            ],
            "resolved_list": [
                {
                    "id": c.id,
                    "type": c.conflict_type.value,
                    "resolution": c.resolution,
                    "resolved_at": c.resolved_at,
                }
                for c in sorted(resolved, key=lambda x: -x.resolved_at)[:10]
            ],
            "active_negotiations": len([n for n in self.negotiations.values() if n.status == NegotiationStatus.PROPOSED]),
            "collaboration_score": self._compute_collaboration_score(unresolved, resolved),
        }

    def _compute_collaboration_score(self, unresolved: list, resolved: list) -> float:
        """
        协作健康度评分（0-10）

        - 无未解决高严重度冲突 → 高分
        - 有未解决低严重度冲突 → 中等
        - 有未解决高严重度冲突 → 低分
        """
        if not self.conflicts:
            return 10.0

        unresolved_severity_sum = sum(c.severity for c in unresolved)
        resolved_count = len(resolved)
        unresolved_count = len(unresolved)

        # 基础分 10，每增加一个未解决严重冲突扣分
        score = 10.0 - unresolved_severity_sum * 0.2
        # 完成的冲突加分（说明有解决能力）
        score += min(2.0, resolved_count * 0.1)

        return max(0.0, min(10.0, round(score, 2)))
