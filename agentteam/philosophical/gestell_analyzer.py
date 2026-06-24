"""
Philosophical Enhancement: Heideggerian Gestell Analysis

基于 Martin Heidegger 存在主义技术哲学中的"技术座架"(Gestell)概念：

技术不是中立的工具，而是"座架"(Enframing)——
它决定了什么能够被发现、什么问题能够被提出。

在 AgentTeam 中：
- DecompositionPattern 预定义的 8 种模式构成了座架
- 它们决定了什么样的任务"存在"，什么样的任务被排除
- agent 只能提出框架允许的问题

这个模块分析并缓解技术座架的限制：
1. 检测哪些问题类型被当前框架排除
2. 提供"框架外"思考的机制
3. 识别"问题移交给技术处理"的情况
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Set, Dict, Any
from enum import Enum
import hashlib
import time


class GestellLimitation(Enum):
    """座架限制类型"""
    QUESTION_TYPE_EXCLUDED = "question_type_excluded"  # 问题类型被排除
    COMPLEXITY_PREJUDGED = "complexity_prejudged"      # 复杂度被预设
    DOMAIN_BLINDNESS = "domain_blindness"              # 领域盲视
    TEMPORAL_NARROWING = "temporal_narrowing"           # 时间视角收窄
    CAUSALITY_FIXED = "causality_fixed"               # 因果关系被固定


@dataclass
class UnaskableQuestion:
    """
    不可提出的问题 - 在当前框架下无法被表达的问题
    
    这些问题"存在但被座架遮蔽"（Heidegger: entities are revealed but concealed）
    """
    question_id: str
    question_text: str
    why_excluded: str                              # 为什么被排除
    limitation_type: GestellLimitation
    attempted_at: float = field(default_factory=time.time)
    workaround_attempted: bool = False
    
    def to_dict(self) -> dict:
        return {
            "question_id": self.question_id,
            "question_text": self.question_text,
            "why_excluded": self.why_excluded,
            "limitation_type": self.limitation_type.value,
            "attempted_at": self.attempted_at,
            "workaround_attempted": self.workaround_attempted,
        }


@dataclass
class GestellLayer:
    """
    座架层 - 描述构成技术框架的各个层次
    
    每一层都限制了可以被提出的问题
    """
    name: str
    description: str
    restricts: List[str]                    # 这一层限制的问题类型
    allows: List[str]                       # 这一层允许的问题类型
    is_visible: bool = True                # 用户是否知道这一层的存在
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "restricts": self.restricts,
            "allows": self.allows,
            "is_visible": self.is_visible,
        }


class GestellAnalyzer:
    """
    技术座架分析器 - 检测框架对问题的限制
    
    核心功能：
    1. 识别当前框架的座架层
    2. 检测哪些问题被排除
    3. 提供"框架突破"机制
    4. 识别"问题被框架接管"的情况
    """
    
    # 当前 AgentTeam 的座架层定义
    DEFAULT_GESTELL_LAYERS = [
        GestellLayer(
            name="DecompositionPattern",
            description="预定义的 8 种任务分解模式：IMPLEMENT_FEATURE, FIX_BUG, ADD_TEST, REFACTOR, DOCUMENT, ANALYZE, DEPLOY, REVIEW",
            restricts=[
                "不在关键词列表中的任务类型",
                "跨领域问题",
                "没有明确关键词的探索性问题",
                "根本性重新定义问题",
            ],
            allows=[
                "符合关键词匹配的任务",
                "明确可分类的问题",
            ],
        ),
        GestellLayer(
            name="ComplexityKeywordMapping",
            description="复杂度关键词映射 - 决定任务的分解粒度",
            restricts=[
                "不被关键词覆盖的微妙复杂度",
                "主观复杂度评估",
                "上下文相关的复杂度",
            ],
            allows=[
                "匹配关键词的复杂度评估",
            ],
        ),
        GestellLayer(
            name="ProviderPreference",
            description="Provider 偏好映射 - 决定什么 agent 类型处理什么任务",
            restricts=[
                "非标准 provider 组合",
                "动态 provider 选择",
            ],
            allows=[
                "预定义的 provider 分配",
            ],
        ),
        GestellLayer(
            name="SOPFixedSteps",
            description="标准操作流程 - 决定任务执行的固定步骤",
            restricts=[
                "非标准执行路径",
                "顿悟式解决",
                "非线性任务执行",
            ],
            allows=[
                "符合 SOP 的执行",
            ],
        ),
    ]
    
    def __init__(self, custom_layers: List[GestellLayer] = None):
        self.gestell_layers = custom_layers if custom_layers is not None else self.DEFAULT_GESTELL_LAYERS
        self.unaskable_questions: List[UnaskableQuestion] = []
        self._question_counter = 0
    
    def analyze_question(self, question_text: str) -> Dict[str, Any]:
        """
        分析问题是否被当前座架限制
        
        Returns:
            {
                "is_askable": bool,
                "blocked_by": List[str],  # 被哪些层阻挡
                "limitation_types": List[GestellLimitation],
                "alternative_framing": Optional[str],  # 可替换的问题表述
            }
        """
        question_lower = question_text.lower()
        blocked_by = []
        limitation_types = []
        
        # 检查 DecompositionPattern 限制
        decomposition_keywords = [
            "实现", "implement", "添加", "add", "开发", "develop",
            "创建", "create", "build", "修复", "fix", "bug",
            "错误", "error", "问题", "issue", "解决", "resolve",
            "测试", "test", "验证", "verify", "coverage", "覆盖",
            "重构", "refactor", "优化", "optimize", "改进", "improve",
            "清理", "clean", "文档", "document", "说明", "readme",
            "分析", "analyze", "调研", "research", "评估", "evaluate",
            "部署", "deploy", "发布", "release", "上线", "publish",
            "审查", "review", "检查", "audit", "评审", "inspect",
        ]
        
        has_matching_keyword = any(kw in question_lower for kw in decomposition_keywords)
        if not has_matching_keyword:
            blocked_by.append("DecompositionPattern: 没有匹配的任务类型关键词")
            limitation_types.append(GestellLimitation.QUESTION_TYPE_EXCLUDED)
        
        # 检查复杂度关键词
        complexity_keywords = [
            "简单", "简单修改", "翻译", "格式化", "检查", "验证",
            "实现", "添加", "创建", "编写", "生成",
            "系统", "模块", "功能", "多个", "集成", "优化",
            "复杂", "分布式", "微服务", "架构", "平台",
            "极复杂", "人工智能", "机器学习", "大数据",
        ]
        
        has_complexity_keyword = any(kw in question_lower for kw in complexity_keywords)
        if not has_complexity_keyword and not has_matching_keyword:
            blocked_by.append("ComplexityKeywordMapping: 无法确定复杂度")
            limitation_types.append(GestellLimitation.COMPLEXITY_PREJUDGED)
        
        # 检查是否尝试根本性重构问题
        revolutionary_keywords = [
            "为什么", "why", "是否应该", "should", 
            "重新定义", "redefine", "根本解决", "fundamental",
        ]
        
        if any(kw in question_lower for kw in revolutionary_keywords):
            # 这是 Meta-question，应该被标记
            limitation_types.append(GestellLimitation.CAUSALITY_FIXED)
        
        return {
            "is_askable": len(blocked_by) == 0,
            "blocked_by": blocked_by,
            "limitation_types": limitation_types,
            "alternative_framing": self._suggest_alternative(question_text) if blocked_by else None,
        }
    
    def _suggest_alternative(self, question_text: str) -> str:
        """建议一个在当前框架内可表达的问题"""
        # 简化：如果原始问题无法表达，提供一个框架内最接近的版本
        return f"[框架内近似] 将问题重新表述为：实现/修复/分析类型任务 - {question_text[:50]}..."
    
    def record_unaskable(self, question_text: str, why_excluded: str, limitation_type: GestellLimitation) -> UnaskableQuestion:
        """记录一个不可提出的问题"""
        self._question_counter += 1
        unaskable = UnaskableQuestion(
            question_id=f"uq_{self._question_counter}",
            question_text=question_text,
            why_excluded=why_excluded,
            limitation_type=limitation_type,
        )
        self.unaskable_questions.append(unaskable)
        return unaskable
    
    def detect_problem_displacement(self, task_description: str) -> bool:
        """
        检测"问题被技术框架接管"的情况
        
        这种情况发生在：用户提出一个复杂问题，但框架
        把它简化为一个标准模式，丢失了问题的本质
        """
        analysis = self.analyze_question(task_description)
        
        # 如果问题被轻易分类为标准类型，可能发生了问题接管
        if analysis["is_askable"]:
            # 问题太容易匹配标准模式
            for layer in self.gestell_layers:
                if layer.name == "DecompositionPattern":
                    if "无法表达" not in str(analysis["blocked_by"]):
                        # 问题太符合标准框架，可能被框架接管了
                        return True
        
        return False
    
    def get_gestell_report(self) -> Dict[str, Any]:
        """生成座架分析报告"""
        by_limitation: Dict[str, int] = {}
        for uq in self.unaskable_questions:
            lt = uq.limitation_type.value
            by_limitation[lt] = by_limitation.get(lt, 0) + 1
        
        return {
            "total_gestell_layers": len(self.gestell_layers),
            "total_unaskable_questions": len(self.unaskable_questions),
            "by_limitation_type": by_limitation,
            "layers": [layer.to_dict() for layer in self.gestell_layers],
            "recent_unaskable": [uq.to_dict() for uq in self.unaskable_questions[-10:]],
        }
    
    def add_gestell_layer(self, layer: GestellLayer) -> None:
        """添加新的座架层（用于动态框架扩展）"""
        self.gestell_layers.append(layer)
    
    def get_question_hash(self, question_text: str) -> str:
        """获取问题的哈希值，用于追踪"""
        return hashlib.md5(question_text.encode()).hexdigest()[:8]


# 便捷函数
def analyze_gestell_constraints(task_description: str) -> Dict[str, Any]:
    """便捷函数：分析单个任务的座架约束"""
    analyzer = GestellAnalyzer()
    return analyzer.analyze_question(task_description)
