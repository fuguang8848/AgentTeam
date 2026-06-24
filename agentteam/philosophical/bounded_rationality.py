"""
Philosophical Enhancement: Bounded Rationality Support

基于 Herbert Simon 有限理性理论：
- 显式追踪每个 agent 的知识边界
- 任务分配考虑"谁真正知道什么"
- 引入"不确定性声明"机制
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Set, Dict
import time


@dataclass
class KnowledgeBoundary:
    """
    知识边界 - 显式建模 agent 的有限理性
    
    基于 Simon 的有限理性理论：
    - known_facts: agent 确认知道的事实
    - unknown_facts: agent 确认不知道
    - probable_facts: agent 不确定是否知道（需要验证）
    - confidence_level: 对自己知识准确性的信心 (0-1)
    """
    known_domains: Set[str] = field(default_factory=set)      # 已知的领域/主题
    unknown_domains: Set[str] = field(default_factory=set)     # 确认不懂的领域
    probable_domains: Set[str] = field(default_factory=set)    # 可能懂但不确定
    confidence_level: float = 1.0                              # 0.0-1.0
    last_calibrated: float = field(default_factory=time.time)  # 上次校准时间
    
    def can_attempt(self, required_domain: str) -> bool:
        """判断是否能尝试处理某个领域的问题"""
        if required_domain in self.known_domains:
            return True
        if required_domain in self.unknown_domains:
            return False
        # probable 域：需要进一步确认，但允许尝试
        return self.confidence_level > 0.3
    
    def declare_uncertainty(self, domain: str, is_unknown: bool) -> None:
        """声明对某领域的不确定性"""
        self.probable_domains.discard(domain)
        if is_unknown:
            self.unknown_domains.add(domain)
            self.known_domains.discard(domain)
        else:
            self.known_domains.add(domain)
            self.unknown_domains.discard(domain)
        self.last_calibrated = time.time()


@dataclass  
class UncertaintyDeclaration:
    """
    不确定性声明 - agent 可以显式声明自己不知道什么
    
    这是有限理性协调的关键：
    - 不是假装知道，而是诚实承认边界
    - 允许系统重新分配任务给更合适的 agent
    """
    agent_name: str
    domain: str
    declaration_type: str  # "unknown" | "probable" | "overwhelmed"
    reason: str
    timestamp: float = field(default_factory=time.time)
    task_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "agent_name": self.agent_name,
            "domain": self.domain,
            "declaration_type": self.declaration_type,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "task_id": self.task_id,
        }


class BoundedRationalityTracker:
    """
    有限理性追踪器 - 协调多个 agent 的知识边界
    
    核心功能：
    1. 维护每个 agent 的知识边界
    2. 任务分配时考虑知识边界
    3. 检测"知识幻觉" - agent 声称知道但实际不知道
    4. 支持不确定性声明传播
    """
    
    def __init__(self):
        self.knowledge_boundaries: Dict[str, KnowledgeBoundary] = {}
        self.uncertainty_declarations: List[UncertaintyDeclaration] = []
        self._calibration_threshold = 0.8  # 信心度阈值
    
    def register_agent(self, agent_name: str, known_domains: List[str] = None) -> KnowledgeBoundary:
        """注册 agent 的初始知识边界"""
        kb = KnowledgeBoundary(
            known_domains=set(known_domains) if known_domains else set()
        )
        self.knowledge_boundaries[agent_name] = kb
        return kb
    
    def get_boundary(self, agent_name: str) -> Optional[KnowledgeBoundary]:
        """获取 agent 的知识边界"""
        return self.knowledge_boundaries.get(agent_name)
    
    def declare_uncertainty(
        self, 
        agent_name: str, 
        domain: str, 
        declaration_type: str,
        reason: str,
        task_id: Optional[str] = None,
    ) -> UncertaintyDeclaration:
        """Agent 声明自己对某领域的不确定性"""
        decl = UncertaintyDeclaration(
            agent_name=agent_name,
            domain=domain,
            declaration_type=declaration_type,
            reason=reason,
            task_id=task_id,
        )
        self.uncertainty_declarations.append(decl)
        
        # 更新知识边界
        kb = self.knowledge_boundaries.get(agent_name)
        if kb:
            kb.declare_uncertainty(domain, declaration_type == "unknown")
        
        return decl
    
    def can_assign_task(
        self, 
        agent_name: str, 
        required_domains: List[str]
    ) -> tuple[bool, List[str]]:
        """
        检查是否可以分配任务给 agent
        返回 (可以分配, 缺少的领域列表)
        """
        kb = self.knowledge_boundaries.get(agent_name)
        if not kb:
            # 未注册 agent，保守处理
            return False, list(required_domains)
        
        missing: List[str] = []
        for domain in required_domains:
            if not kb.can_attempt(domain):
                missing.append(domain)
        
        return len(missing) == 0, missing
    
    def find_competent_agents(
        self, 
        required_domains: List[str],
        exclude: List[str] = None
    ) -> List[tuple[str, float]]:
        """
        找到能够处理所需领域的 agent，按信心度排序
        返回 [(agent_name, confidence), ...]
        """
        candidates = []
        exclude = set(exclude) if exclude else set()
        
        for name, kb in self.knowledge_boundaries.items():
            if name in exclude:
                continue
            
            can_handle, missing = self.can_assign_task(name, required_domains)
            if can_handle:
                candidates.append((name, kb.confidence_level))
        
        # 按信心度排序
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates
    
    def detect_knowledge_hallucination(self, agent_name: str) -> List[str]:
        """
        检测知识幻觉 - 检查 agent 最近是否声称知道某事但失败了
        
        通过分析不确定声明来推断：
        - 如果一个 domain 被声明为 known 但随后出现 unknown 声明，说明有幻觉
        """
        agent_decls = [d for d in self.uncertainty_declarations if d.agent_name == agent_name]
        
        claimed_known = set()
        declared_unknown = set()
        
        for decl in agent_decls:
            if decl.declaration_type == "unknown":
                declared_unknown.add(decl.domain)
        
        return list(declared_unknown)
    
    def get_rationality_report(self) -> dict:
        """生成有限理性协调报告"""
        total_agents = len(self.knowledge_boundaries)
        uncertain_agents = sum(
            1 for kb in self.knowledge_boundaries.values() 
            if kb.confidence_level < self._calibration_threshold
        )
        
        return {
            "total_agents": total_agents,
            "uncertain_agents": uncertain_agents,
            "total_uncertainty_declarations": len(self.uncertainty_declarations),
            "recent_declarations": [
                d.to_dict() for d in self.uncertainty_declarations[-10:]
            ],
        }
