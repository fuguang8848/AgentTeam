"""
Philosophical Enhancement: Cybernetic Feedback Loop

基于 Norbert Wiener 控制论：
- 真正的控制是对信息的反馈
- 系统必须不断收集信息来调整自己的行为
- 没有反馈的自动化是危险的

这个模块实现完整的 cybernetic feedback loop：
1. 消息确认回执 (Acknowledgment Receipt)
2. 执行结果反馈收集
3. 自我调整机制
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
from enum import Enum
import time


class FeedbackStatus(Enum):
    """反馈状态"""
    PENDING = "pending"      # 等待反馈
    RECEIVED = "received"   # 已收到反馈
    TIMEOUT = "timeout"     # 反馈超时
    IGNORED = "ignored"     # 反馈被忽略


@dataclass
class AcknowledgmentReceipt:
    """
    消息确认回执 - 确保消息被正确接收
    
    Wiener 控制论核心：没有确认的发送只是噪音
    """
    message_id: str
    from_agent: str
    to_agent: str
    sent_at: float = field(default_factory=time.time)
    acknowledged_at: Optional[float] = None
    status: FeedbackStatus = FeedbackStatus.PENDING
    content_hash: str = ""  # 用于验证内容完整性
    
    def acknowledge(self) -> None:
        """确认回执"""
        self.acknowledged_at = time.time()
        self.status = FeedbackStatus.RECEIVED
    
    def mark_timeout(self) -> None:
        """标记超时"""
        self.status = FeedbackStatus.TIMEOUT
    
    def is_complete(self) -> bool:
        """反馈回路是否完整"""
        return self.status == FeedbackStatus.RECEIVED


@dataclass
class ExecutionFeedback:
    """
    执行反馈 - 收集任务执行后的结果信息
    
    用于控制论中的"比较器"：比较预期与实际，调整行为
    """
    task_id: str
    agent_name: str
    expected_outcome: str = ""
    actual_outcome: str = ""
    quality_score: float = 0.0  # 0-1
    deviation: float = 0.0       # 偏离度
    corrective_action: str = ""  # 需要的纠正行动
    collected_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FeedbackLoopConfig:
    """反馈回路配置"""
    ack_timeout_seconds: float = 30.0        # 确认超时
    feedback_retries: int = 3                  # 反馈重试次数
    self_adjustment_enabled: bool = True     # 是否启用自我调整
    deviation_threshold: float = 0.3          # 偏离度阈值


class CyberneticFeedbackLoop:
    """
    控制论反馈回路管理器
    
    核心原则（Wiener）：
    1. 每个消息都需要确认回执
    2. 每个执行结果都需要收集反馈
    3. 系统必须基于反馈进行自我调整
    
    这个类作为 Mixin 可以被 CTTeam 使用
    """
    
    def __init__(self, config: Optional[FeedbackLoopConfig] = None):
        self.config = config or FeedbackLoopConfig()
        self._pending_acks: Dict[str, AcknowledgmentReceipt] = {}
        self._execution_feedback: Dict[str, List[ExecutionFeedback]] = {}
        self._adjustment_handlers: List[Callable[[ExecutionFeedback], None]] = []
        self._last_adjustment_time: float = 0.0
    
    def register_adjustment_handler(self, handler: Callable[[ExecutionFeedback], None]) -> None:
        """注册调整处理器 - 当偏离发生时调用"""
        self._adjustment_handlers.append(handler)
    
    def send_with_ack(
        self,
        message_id: str,
        from_agent: str,
        to_agent: str,
        content_hash: str = "",
    ) -> AcknowledgmentReceipt:
        """发送消息并创建确认回执"""
        ack = AcknowledgmentReceipt(
            message_id=message_id,
            from_agent=from_agent,
            to_agent=to_agent,
            content_hash=content_hash,
        )
        self._pending_acks[message_id] = ack
        return ack
    
    def receive_ack(self, message_id: str) -> bool:
        """接收确认回执"""
        ack = self._pending_acks.get(message_id)
        if not ack:
            return False
        
        ack.acknowledge()
        return True
    
    def check_timeouts(self) -> List[AcknowledgmentReceipt]:
        """检查所有待确认消息的超时"""
        now = time.time()
        timed_out = []
        
        for ack in self._pending_acks.values():
            if ack.status == FeedbackStatus.PENDING:
                if now - ack.sent_at > self.config.ack_timeout_seconds:
                    ack.mark_timeout()
                    timed_out.append(ack)
        
        return timed_out
    
    def collect_execution_feedback(
        self,
        task_id: str,
        agent_name: str,
        expected_outcome: str,
        actual_outcome: str,
        quality_score: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExecutionFeedback:
        """收集执行反馈"""
        # 计算偏离度
        deviation = self._calculate_deviation(expected_outcome, actual_outcome)
        
        feedback = ExecutionFeedback(
            task_id=task_id,
            agent_name=agent_name,
            expected_outcome=expected_outcome,
            actual_outcome=actual_outcome,
            quality_score=quality_score,
            deviation=deviation,
            metadata=metadata or {},
        )
        
        if task_id not in self._execution_feedback:
            self._execution_feedback[task_id] = []
        self._execution_feedback[task_id].append(feedback)
        
        # 检查是否需要自我调整
        if self.config.self_adjustment_enabled:
            self._trigger_adjustment(feedback)
        
        return feedback
    
    def _calculate_deviation(self, expected: str, actual: str) -> float:
        """计算偏离度 (0.0 - 1.0)"""
        if expected == actual:
            return 0.0
        if not expected:
            return 1.0 if actual else 0.0
        
        # 简单的词级别比较
        expected_words = set(expected.split())
        actual_words = set(actual.split())
        
        if not expected_words:
            return 0.0
        
        intersection = len(expected_words & actual_words)
        union = len(expected_words | actual_words)
        
        return 1.0 - (intersection / union) if union > 0 else 0.0
    
    def _trigger_adjustment(self, feedback: ExecutionFeedback) -> None:
        """触发自我调整机制"""
        if feedback.deviation < self.config.deviation_threshold:
            return
        
        feedback.corrective_action = self._suggest_correction(feedback)
        
        # 调用所有注册的调整处理器
        for handler in self._adjustment_handlers:
            try:
                handler(feedback)
            except Exception:
                pass  # 不要因为单个处理器失败而停止
        
        self._last_adjustment_time = time.time()
    
    def _suggest_correction(self, feedback: ExecutionFeedback) -> str:
        """基于偏离度建议纠正措施"""
        if feedback.deviation > 0.8:
            return f"AGENT {feedback.agent_name}: 严重偏离预期，建议重新分解任务"
        elif feedback.deviation > 0.5:
            return f"AGENT {feedback.agent_name}: 中度偏离，建议检查任务理解"
        else:
            return f"AGENT {feedback.agent_name}: 轻度偏离，可继续监控"
    
    def get_feedback_summary(self, task_id: str) -> Dict[str, Any]:
        """获取任务反馈摘要"""
        feedbacks = self._execution_feedback.get(task_id, [])
        
        if not feedbacks:
            return {"status": "no_feedback", "task_id": task_id}
        
        total_deviation = sum(f.deviation for f in feedbacks)
        avg_quality = sum(f.quality_score for f in feedbacks) / len(feedbacks)
        
        return {
            "task_id": task_id,
            "feedback_count": len(feedbacks),
            "avg_deviation": total_deviation / len(feedbacks),
            "avg_quality": avg_quality,
            "needs_adjustment": any(f.deviation > self.config.deviation_threshold for f in feedbacks),
            "status": "feedback_collected",
        }
    
    def get_pending_acks_count(self) -> int:
        """获取待确认消息数"""
        return sum(1 for ack in self._pending_acks.values() 
                   if ack.status == FeedbackStatus.PENDING)
    
    def get_cybernetic_report(self) -> Dict[str, Any]:
        """生成控制论反馈回路报告"""
        total_acks = len(self._pending_acks)
        completed_acks = sum(1 for ack in self._pending_acks.values() 
                            if ack.status == FeedbackStatus.RECEIVED)
        timed_out_acks = sum(1 for ack in self._pending_acks.values() 
                            if ack.status == FeedbackStatus.TIMEOUT)
        
        all_feedbacks = [f for feedbacks in self._execution_feedback.values() for f in feedbacks]
        
        return {
            "total_pending_acks": total_acks,
            "completed_acks": completed_acks,
            "timeout_acks": timed_out_acks,
            "ack_completion_rate": completed_acks / total_acks if total_acks > 0 else 1.0,
            "total_feedbacks_collected": len(all_feedbacks),
            "last_adjustment_time": self._last_adjustment_time,
            "feedback_loop_health": "healthy" if completed_acks / total_acks > 0.8 else "degraded",
        }
