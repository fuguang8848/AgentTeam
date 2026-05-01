# ClawTeam P6-P17 整体架构设计文档

**版本**: 1.0.0  
**作者**: 架构师  
**日期**: 2026-04-28  
**审核者**: 楚灵  
**工作目录**: `C:\Users\31683\.openclaw\workspace\ClawTeam-OpenClaw`

## 1. 总览

P6-P17 升级计划将 ClawTeam 从一个基础的多 Agent 协调框架，进化为一个具有 AI 自主编排、跨会话感知、自主学习和进化能力的智能平台。整个架构分为四个层次：

1. **编排层** (P6, P9): Supervisor 模式 + Provider 自适应
2. **感知层** (P7, P8): 跨会话感知 + 文件改动追踪
3. **进化层** (P12-P16): 自动经验捕获 + 自主技能创建 + 用户画像 + 记忆增强 + 洞察报告
4. **交互层** (P17): Web UI 聊天窗口

### 1.1 架构图（文字描述）

```
用户 (CLI/Web UI)
    ↓
┌─────────────────────────────────────┐
│           交互层 (P17)              │
│  ┌─────────┐     ┌──────────────┐  │
│  │ Web UI  │ ←→ │ 聊天服务器    │  │
│  │ 聊天    │     │ (SSE/API)    │  │
│  └─────────┘     └──────────────┘  │
└─────────────────┬───────────────────┘
                  ↓
┌─────────────────────────────────────┐
│           编排层 (P6, P9)           │
│  ┌─────────┐     ┌──────────────┐  │
│  │Supervisor│ ←→ │ Provider选择器 │  │
│  │ 引擎     │     │ (智能路由)   │  │
│  └─────────┘     └──────────────┘  │
└─────────────────┬───────────────────┘
                  ↓
┌─────────────────────────────────────┐
│           感知层 (P7, P8)           │
│  ┌─────────┐     ┌──────────────┐  │
│  │会话注册 │ ←→ │ 文件改动      │  │
│  │中心     │     │ 追踪器       │  │
│  └─────────┘     └──────────────┘  │
└─────────────────┬───────────────────┘
                  ↓
┌─────────────────────────────────────┐
│           进化层 (P12-P16)          │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐│
│  │经验捕获 │ │技能创建 │ │用户画像 ││
│  │引擎     │ │引擎     │ │系统     ││
│  └─────────┘ └─────────┘ └─────────┘│
│  ┌─────────┐ ┌─────────┐           │
│  │记忆增强 │ │洞察报告 │           │
│  │系统     │ │引擎     │           │
│  └─────────┘ └─────────┘           │
└─────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────┐
│           存储层                    │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐│
│  │SQLite   │ │JSON文件 │ │Git仓库  ││
│  │数据库   │ │系统     │ │(Worktree)││
│  └─────────┘ └─────────┘ └─────────┘│
└─────────────────────────────────────┘
```

### 1.2 关键设计原则

1. **向后兼容性**: 所有新增模块都不影响现有 API 和行为
2. **模块化**: 每个 Phase 可独立开发、测试和部署
3. **可插拔架构**: Provider、记忆、技能等系统支持插件机制
4. **事件驱动**: 通过事件总线实现松散耦合
5. **分层存储**: 根据数据类型选择合适的存储介质

## 2. 各 Phase 详细接口设计

### 2.1 P6: Supervisor 模式（AI 自主编排）

#### 2.1.1 接口定义

```python
# clawteam/orchestrator/supervisor.py
from __future__ import annotations
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

class SubTaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

class SubTask(BaseModel):
    task_id: str = Field(default_factory=lambda: f"subtask_{uuid.uuid4().hex[:8]}")
    description: str
    depends_on: List[str] = Field(default_factory=list)
    assigned_agent: str = ""
    provider: str = ""
    status: SubTaskStatus = SubTaskStatus.PENDING
    result: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3

class TaskPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:8]}")
    goal: str
    team_name: str
    subtasks: List[SubTask] = Field(default_factory=list)
    status: Literal["planning", "executing", "completed", "failed"] = "planning"
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    dag: Dict[str, List[str]] = Field(default_factory=dict)  # 任务依赖图
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SupervisorEngine:
    """Supervisor 引擎 — AI 自主任务编排"""
    
    def __init__(self, team_name: str, provider_selector: Optional[ProviderSelector] = None):
        self.team_name = team_name
        self.provider_selector = provider_selector or get_provider_selector(team_name)
        
    async def plan(self, goal: str) -> TaskPlan:
        """LLM 驱动的任务分解"""
        # 使用 LLM 分解任务，生成 DAG
        pass
    
    async def execute(self, plan: TaskPlan) -> Dict[str, Any]:
        """执行计划：按 DAG 顺序 spawn 子 Agent"""
        pass
    
    async def monitor(self, plan_id: str) -> Dict[str, Any]:
        """监控计划执行状态"""
        pass
    
    async def verify_subtask(self, subtask_id: str, result: str) -> Dict[str, Any]:
        """验证子任务结果"""
        pass
    
    async def retry_failed_subtasks(self, plan_id: str) -> Dict[str, Any]:
        """重试失败的任务"""
        pass
    
    def get_plan_status(self, plan_id: str) -> Dict[str, Any]:
        """获取计划状态"""
        pass
    
    def cancel_plan(self, plan_id: str) -> bool:
        """取消计划"""
        pass

# CLI 接口
class SupervisorCLI:
    @staticmethod
    def start(goal: str, team_name: str = "default") -> str:
        """启动 Supervisor 任务"""
        pass
    
    @staticmethod
    def status(plan_id: str) -> Dict[str, Any]:
        """查看计划状态"""
        pass
    
    @staticmethod
    def tasks(plan_id: str) -> List[Dict[str, Any]]:
        """查看子任务列表"""
        pass
    
    @staticmethod
    def cancel(plan_id: str) -> bool:
        """取消计划"""
        pass
```

#### 2.1.2 数据结构

- **TaskPlan**: 包含完整任务分解和 DAG
- **SubTask**: 原子任务单元，支持依赖关系
- **DAG 表示**: 使用邻接表存储任务依赖关系

### 2.2 P7: 跨会话感知

#### 2.2.1 接口定义

```python
# clawteam/session/registry.py (扩展现有接口)
from clawteam.session.registry import SessionRegistry, SessionInfo

class EnhancedSessionInfo(SessionInfo):
    """增强的会话信息，支持跨会话感知"""
    current_files: List[str] = Field(default_factory=list)
    recent_commands: List[str] = Field(default_factory=list, max_items=10)
    collaboration_requests: List[Dict[str, Any]] = Field(default_factory=list)
    awareness_level: Literal["none", "basic", "full"] = "basic"

class CrossSessionAwareness:
    """跨会话感知引擎"""
    
    def __init__(self, registry: SessionRegistry):
        self.registry = registry
        self.message_bus = SessionMessageBus()
    
    async def broadcast_to_team(self, 
                               team_name: str,
                               message: Dict[str, Any],
                               sender_session_id: str) -> Dict[str, Any]:
        """向团队内所有会话广播消息"""
        pass
    
    async def send_to_session(self,
                            target_session_id: str,
                            message: Dict[str, Any],
                            sender_session_id: str) -> bool:
        """向指定会话发送消息"""
        pass
    
    async def search_collaborators(self,
                                 query: str,
                                 team_name: str,
                                 current_session_id: str) -> List[Dict[str, Any]]:
        """搜索可能协作的会话"""
        pass
    
    async def detect_conflicts(self,
                             file_path: str,
                             team_name: str) -> List[Dict[str, Any]]:
        """检测文件冲突（多个会话同时修改同一文件）"""
        pass
    
    def get_team_overview(self, team_name: str) -> Dict[str, Any]:
        """获取团队概览"""
        pass

class SessionMessageBus:
    """会话消息总线"""
    
    async def subscribe(self, session_id: str, callback: Callable[[Dict[str, Any]], None]):
        """订阅消息"""
        pass
    
    async def publish(self, session_id: str, message: Dict[str, Any]):
        """发布消息"""
        pass
    
    def get_unread_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """获取未读消息"""
        pass
```

#### 2.2.2 数据结构

- **EnhancedSessionInfo**: 扩展现有 SessionInfo，增加当前文件和命令
- **消息格式**: `{"type": str, "sender": str, "content": Any, "timestamp": datetime}`

### 2.3 P8: 文件改动追踪

#### 2.3.1 接口定义

```python
# clawteam/tracker/file_tracker.py
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import hashlib

class ChangeType(str, Enum):
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"

class FileChange(BaseModel):
    change_id: str = Field(default_factory=lambda: f"change_{uuid.uuid4().hex[:8]}")
    file_path: str
    relative_path: str = ""
    agent_name: str
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    change_type: ChangeType
    diff: str = ""
    before_hash: str = ""
    after_hash: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)

class FileChangeTracker:
    """文件改动追踪器"""
    
    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self.watcher = FileWatcher(workspace_root)
        
    def start_tracking(self, session_id: str, agent_name: str) -> None:
        """开始追踪指定会话的文件改动"""
        pass
    
    def stop_tracking(self, session_id: str) -> None:
        """停止追踪"""
        pass
    
    def record_change(self,
                     file_path: str,
                     session_id: str,
                     agent_name: str,
                     change_type: ChangeType,
                     diff: Optional[str] = None) -> FileChange:
        """记录文件改动"""
        pass
    
    def get_changes(self,
                   file_path: Optional[str] = None,
                   agent_name: Optional[str] = None,
                   session_id: Optional[str] = None,
                   time_range: Optional[Tuple[datetime, datetime]] = None) -> List[FileChange]:
        """查询文件改动"""
        pass
    
    def get_file_history(self, file_path: str, limit: int = 50) -> List[FileChange]:
        """获取文件历史记录"""
        pass
    
    def get_diff(self, file_path: str, change_id1: str, change_id2: str) -> str:
        """生成两个版本间的 diff"""
        pass
    
    def annotate_file(self, file_path: str) -> Dict[str, Any]:
        """标注文件状态（蓝点标注）"""
        pass

class FileWatcher:
    """文件监视器"""
    
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.handlers: Dict[str, List[Callable]] = {}
        
    def watch(self, patterns: List[str] = None) -> None:
        """开始监视文件"""
        pass
    
    def add_handler(self, pattern: str, handler: Callable[[Path, str], None]) -> None:
        """添加文件变化处理器"""
        pass
    
    def remove_handler(self, pattern: str, handler: Callable[[Path, str], None]) -> None:
        """移除处理器"""
        pass
```

#### 2.3.2 数据结构

- **FileChange**: 完整的文件变化记录，包含前后哈希值
- **ChangeType**: 四种变化类型枚举
- **文件哈希**: 使用 SHA-256 计算文件内容哈希

### 2.4 P9: Provider 自适应

#### 2.4.1 接口定义

```python
# clawteam/provider/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from enum import Enum

class ProviderCapability(str, Enum):
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    ARCHITECTURE = "architecture"
    DEBUGGING = "debugging"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    REFACTORING = "refactoring"
    RESEARCH = "research"
    LONG_CONTEXT = "long_context"
    IMAGE_UNDERSTANDING = "image_understanding"
    TOOL_USE = "tool_use"

class ProviderQuota(BaseModel):
    quota_limit: int = -1  # -1 表示无限
    quota_used: int = 0
    quota_reset_at: Optional[datetime] = None
    rate_limit_per_minute: int = -1
    requests_this_minute: int = 0

class ProviderResult(BaseModel):
    success: bool
    content: str
    provider_name: str
    tokens_used: int = 0
    latency_ms: int = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BaseProvider(ABC):
    """Provider 抽象基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def capabilities(self) -> List[ProviderCapability]:
        pass
    
    @abstractmethod
    async def run(self,
                 prompt: str,
                 workspace: str,
                 tools: Optional[List[Dict[str, Any]]] = None,
                 **kwargs) -> ProviderResult:
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        pass
    
    async def get_quota(self) -> ProviderQuota:
        """获取配额信息"""
        pass
    
    def can_handle(self, task_type: str) -> bool:
        """判断是否能处理特定任务类型"""
        pass

# 具体 Provider 实现
class ClaudeProvider(BaseProvider):
    """Claude Code Provider"""
    
    @property
    def name(self) -> str:
        return "claude-code"
    
    @property
    def capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability.CODE_GENERATION,
            ProviderCapability.CODE_REVIEW,
            ProviderCapability.ARCHITECTURE,
            ProviderCapability.DEBUGGING,
            ProviderCapability.REFACTORING,
            ProviderCapability.TOOL_USE,
        ]
    
    # ... 具体实现

class ProviderSelector:
    """智能 Provider 选择器"""
    
    def __init__(self):
        self.providers: Dict[str, BaseProvider] = {}
        self.fallback_chain = ["claude-code", "gemini", "codex", "opencode"]
        
    def register_provider(self, provider: BaseProvider) -> None:
        """注册 Provider"""
        pass
    
    async def select_provider(self,
                             task_type: str,
                             task_description: str,
                             constraints: Optional[Dict[str, Any]] = None) -> BaseProvider:
        """选择最适合的 Provider"""
        pass
    
    async def get_fallback_provider(self,
                                  current_provider: str,
                                  error_reason: str) -> Optional[BaseProvider]:
        """获取备选 Provider"""
        pass
    
    def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有 Provider 状态"""
        pass
```

### 2.5 P10: Git Worktree 自动管理

#### 2.5.1 接口定义

```python
# clawteam/git/worktree.py
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import subprocess

class WorktreeInfo(BaseModel):
    worktree_id: str
    branch_name: str
    path: str
    base_branch: str = "main"
    created_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    status: Literal["active", "stale", "merged", "abandoned"] = "active"
    associated_task: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class WorktreeManager:
    """Git Worktree 管理器"""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.worktrees_dir = self.repo_path / ".clawteam" / "worktrees"
        
    def create_worktree(self,
                       task_id: str,
                       base_branch: str = "main",
                       branch_name: Optional[str] = None) -> WorktreeInfo:
        """为任务创建 worktree"""
        pass
    
    def merge_worktree(self,
                      worktree_id: str,
                      target_branch: str = "main",
                      strategy: str = "merge") -> Dict[str, Any]:
        """合并 worktree 内容"""
        pass
    
    def cleanup_worktrees(self,
                         max_age_hours: int = 168,  # 7天
                         auto_merge: bool = False) -> List[str]:
        """清理过时的 worktree"""
        pass
    
    def detect_conflicts(self, worktree_id: str) -> List[Dict[str, Any]]:
        """检测合并冲突"""
        pass
    
    def get_worktree_status(self, worktree_id: str) -> Dict[str, Any]:
        """获取 worktree 状态"""
        pass
    
    def list_worktrees(self, status_filter: Optional[str] = None) -> List[WorktreeInfo]:
        """列出所有 worktree"""
        pass
```

### 2.6 P11: Token 统计

#### 2.6.1 接口定义

```python
# clawteam/usage/stats.py
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

class TokenUsage(BaseModel):
    usage_id: str = Field(default_factory=lambda: f"usage_{uuid.uuid4().hex[:8]}")
    session_id: str
    agent_name: str
    task_id: Optional[str] = None
    provider_name: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TokenStats:
    """Token 统计管理器"""
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path or get_data_dir() / "usage"
        
    def record_usage(self,
                    session_id: str,
                    agent_name: str,
                    provider_name: str,
                    input_tokens: int,
                    output_tokens: int,
                    task_id: Optional[str] = None) -> TokenUsage:
        """记录 Token 使用量"""
        pass
    
    def get_usage_summary(self,
                         time_range: Optional[Tuple[datetime, datetime]] = None,
                         group_by: str = "provider") -> Dict[str, Any]:
        """获取使用量摘要"""
        pass
    
    def get_provider_cost(self,
                         provider_name: str,
                         days: int = 30) -> Dict[str, Any]:
        """获取 Provider 成本统计"""
        pass
    
    def get_agent_usage(self,
                       agent_name: str,
                       limit: int = 100) -> List[TokenUsage]:
        """获取 Agent 使用记录"""
        pass
    
    def predict_remaining_quota(self,
                              provider_name: str,
                              period_days: int = 30) -> Dict[str, Any]:
        """预测剩余配额"""
        pass
    
    def generate_cost_report(self,
                           format: str = "json",
                           include_charts: bool = False) -> str:
        """生成成本报告"""
        pass
```

### 2.7 P12: .learnings 自动闭环

#### 2.7.1 接口定义

```python
# clawteam/learnings/auto_capture.py
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class LearningType(str, Enum):
    ERROR = "error"
    LEARNING = "learning"
    BEST_PRACTICE = "best_practice"
    FEATURE_REQUEST = "feature_request"
    KNOWLEDGE_GAP = "knowledge_gap"

class ExperienceEntry(BaseModel):
    entry_id: str = Field(default_factory=lambda: f"exp_{uuid.uuid4().hex[:8]}")
    entry_type: LearningType
    summary: str
    details: str = ""
    category: str = ""  # correction, best_practice, knowledge_gap
    area: str = ""  # frontend, backend, infra, tests, docs, config
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    count: int = 1
    first_seen: datetime = Field(default_factory=datetime.now)
    last_seen: datetime = Field(default_factory=datetime.now)
    occurrences: List[Dict[str, Any]] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    resolved: bool = False
    resolution: Optional[str] = None

class AutoCaptureEngine:
    """自动经验捕获引擎"""
    
    def __init__(self, learnings_dir: Optional[str] = None):
        self.learnings_dir = Path(learnings_dir or "~/.openclaw/workspace/.learnings")
        self.pattern_detector = PatternDetector()
        
    def evaluate_task_result(self,
                           task_result: Dict[str, Any],
                           user_feedback: Optional[str] = None) -> Optional[ExperienceEntry]:
        """评估任务结果，判断是否需要记录"""
        pass
    
    def record_experience(self, entry: ExperienceEntry) -> str:
        """记录经验到 .learnings 系统"""
        pass
    
    def check_for_promotion(self,
                          min_occurrences: int = 3,
                          min_confidence: float = 0.8) -> List[ExperienceEntry]:
        """检查是否需要晋升到 AGENTS.md/TOOLS.md/SOUL.md"""
        pass
    
    def promote_to_documentation(self,
                               entry: ExperienceEntry,
                               target_doc: str) -> bool:
        """晋升到文档系统"""
        pass
    
    def search_experiences(self,
                          query: str,
                          entry_type: Optional[LearningType] = None,
                          limit: int = 50) -> List[ExperienceEntry]:
        """搜索经验记录"""
        pass
    
    def generate_learning_summary(self,
                                 days: int = 7,
                                 format: str = "markdown") -> str:
        """生成学习摘要"""
        pass

class PatternDetector:
    """模式检测器"""
    
    def detect_repetitive_patterns(self,
                                  activities: List[Dict[str, Any]],
                                  window_size: int = 10) -> List[Dict[str, Any]]:
        """检测重复模式"""
        pass
    
    def calculate_pattern_confidence(self,
                                   pattern: Dict[str, Any],
                                   occurrences: List[Dict[str, Any]]) -> float:
        """计算模式置信度"""
        pass
```

### 2.8 P13: 自主技能创建

#### 2.8.1 接口定义

```python
# clawteam/skills/auto_creator.py
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from pathlib import Path
import yaml

class DetectedPattern(BaseModel):
    pattern_id: str = Field(default_factory=lambda: f"pattern_{uuid.uuid4().hex[:8]}")
    name: str
    description: str
    trigger_count: int
    tools_used: List[str] = Field(default_factory=list)
    steps: List[str] = Field(default_factory=list)
    estimated_savings: int = 0  # 预计节省步数
    confidence: float = 0.0
    first_detected: datetime = Field(default_factory=datetime.now)
    last_detected: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SkillSpec(BaseModel):
    name: str
    description: str
    version: str = "1.0.0"
    author: str = "ClawTeam Auto Creator"
    created_at: datetime = Field(default_factory=datetime.now)
    category: str = "automation"
    instructions: str
    inputs: List[Dict[str, Any]] = Field(default_factory=list)
    outputs: List[Dict[str, Any]] = Field(default_factory=list)
    references: Dict[str, str] = Field(default_factory=dict)
    templates: Dict[str, str] = Field(default_factory=dict)
    examples: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SkillAutoCreator:
    """自主技能创建引擎"""
    
    def __init__(self, skills_dir: Optional[str] = None):
        self.skills_dir = Path(skills_dir or "~/.openclaw/workspace/skills")
        self.usage_tracker = SkillUsageTracker()
        
    def detect_patterns_from_usage(self,
                                  min_occurrences: int = 5,
                                  min_confidence: float = 0.7) -> List[DetectedPattern]:
        """从使用数据中检测模式"""
        pass
    
    def create_skill_from_pattern(self,
                                pattern: DetectedPattern,
                                confirm: bool = True) -> Optional[SkillSpec]:
        """基于模式创建技能"""
        pass
    
    def install_skill(self,
                     spec: SkillSpec,
                     force: bool = False) -> Path:
        """安装技能到技能目录"""
        pass
    
    def evaluate_existing_skills(self) -> List[Dict[str, Any]]:
        """评估现有技能效果"""
        pass
    
    def optimize_skill(self,
                      skill_name: str,
                      based_on_feedback: Optional[List[Dict[str, Any]]] = None) -> bool:
        """优化技能"""
        pass
    
    def get_skill_metrics(self,
                         skill_name: str,
                         time_range: Optional[Tuple[datetime, datetime]] = None) -> Dict[str, Any]:
        """获取技能使用指标"""
        pass

class SkillUsageTracker:
    """技能使用追踪器"""
    
    def record_skill_usage(self,
                          skill_name: str,
                          session_id: str,
                          inputs: Dict[str, Any],
                          outputs: Dict[str, Any],
                          success: bool,
                          duration_ms: int) -> None:
        """记录技能使用"""
        pass
    
    def get_skill_stats(self,
                       skill_name: Optional[str] = None,
                       days: int = 30) -> Dict[str, Any]:
        """获取技能统计"""
        pass
```

### 2.9 P14: 用户画像系统

#### 2.9.1 接口定义

```python
# clawteam/profile/user_model.py
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime, time

class Preference(BaseModel):
    key: str
    value: Any
    confidence: float = Field(ge=0.0, le=1.0)
    source: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    evidence: List[str] = Field(default_factory=list)

class BehavioralPattern(BaseModel):
    pattern_type: str  # working_hours, tool_preference, communication_style
    data: Dict[str, Any]
    confidence: float = Field(ge=0.0, le=1.0)
    first_observed: datetime = Field(default_factory=datetime.now)
    last_observed: datetime = Field(default_factory=datetime.now)

class UserProfile(BaseModel):
    user_id: str = "default"
    name: Optional[str] = None
    identity: str = ""
    preferences: Dict[str, Preference] = Field(default_factory=dict)
    behavioral_patterns: Dict[str, BehavioralPattern] = Field(default_factory=dict)
    projects: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    evolution: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class UserProfileManager:
    """用户画像管理器"""
    
    def __init__(self, profile_dir: Optional[str] = None):
        self.profile_dir = Path(profile_dir or "~/.openclaw/profiles")
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        
    def analyze_conversation(self,
                           user_message: str,
                           assistant_response: str,
                           session_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """分析对话，提取用户偏好"""
        pass
    
    def update_profile(self,
                      user_id: str,
                      changes: List[Dict[str, Any]],
                      source: str = "conversation") -> UserProfile:
        """更新用户画像"""
        pass
    
    def get_context_for_prompt(self,
                              user_id: str,
                              task_type: Optional[str] = None) -> str:
        """为系统提示生成用户上下文"""
        pass
    
    def detect_behavioral_changes(self,
                                user_id: str,
                                days: int = 7) -> List[Dict[str, Any]]:
        """检测行为变化"""
        pass
    
    def save_profile(self, profile: UserProfile) -> None:
        """保存用户画像"""
        pass
    
    def load_profile(self, user_id: str) -> Optional[UserProfile]:
        """加载用户画像"""
        pass
    
    def merge_profiles(self, profiles: List[UserProfile]) -> UserProfile:
        """合并多个用户画像"""
        pass
```

### 2.10 P15: 记忆增强

#### 2.10.1 接口定义

```python
# clawteam/memory/provider.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class MemoryEntry(BaseModel):
    memory_id: str = Field(default_factory=lambda: f"mem_{uuid.uuid4().hex[:8]}")
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    accessed_at: datetime = Field(default_factory=datetime.now)
    access_count: int = 0
    relevance_score: float = 0.0

class MemoryQuery(BaseModel):
    query: str
    limit: int = 10
    min_relevance: float = 0.3
    filters: Dict[str, Any] = Field(default_factory=dict)

class MemoryResult(BaseModel):
    memories: List[MemoryEntry]
    query: str
    total_found: int
    retrieval_time_ms: int

class BaseMemoryProvider(ABC):
    """记忆 Provider 抽象基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def supports_embedding(self) -> bool:
        pass
    
    @abstractmethod
    async def store(self,
                   content: str,
                   metadata: Optional[Dict[str, Any]] = None) -> str:
        """存储记忆"""
        pass
    
    @abstractmethod
    async def retrieve(self,
                      query: MemoryQuery) -> MemoryResult:
        """检索记忆"""
        pass
    
    @abstractmethod
    async def prefetch(self,
                      context: str,
                      limit: int = 5) -> List[MemoryEntry]:
        """预取相关记忆"""
        pass
    
    async def sync_conversation(self,
                              user_message: str,
                              assistant_response: str,
                              session_context: Dict[str, Any]) -> List[str]:
        """同步对话到记忆"""
        pass
    
    async def on_session_end(self,
                           messages: List[Dict[str, Any]]) -> List[str]:
        """会话结束时提取关键事实"""
        pass
    
    async def cleanup_old_memories(self,
                                 max_age_days: int = 90,
                                 min_access_count: int = 1) -> int:
        """清理旧记忆"""
        pass

# FTS5 实现
class FTS5MemoryProvider(BaseMemoryProvider):
    """基于 SQLite FTS5 的全文检索记忆 Provider"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path or "~/.openclaw/memory/fts5.db")
        self._init_db()
    
    @property
    def name(self) -> str:
        return "fts5"
    
    @property
    def supports_embedding(self) -> bool:
        return False
    
    # ... 具体实现

# LanceDB 实现  
class LanceDBMemoryProvider(BaseMemoryProvider):
    """基于 LanceDB 的向量检索记忆 Provider"""
    
    def __init__(self, db_path: Optional[str] = None, embedding_model: str = "all-MiniLM-L6-v2"):
        self.db_path = Path(db_path or "~/.openclaw/memory/lancedb")
        self.embedding_model = embedding_model
        
    @property
    def name(self) -> str:
        return "lancedb"
    
    @property
    def supports_embedding(self) -> bool:
        return True
    
    # ... 具体实现

class MemoryManager:
    """记忆管理器（多 Provider 协调）"""
    
    def __init__(self):
        self.providers: Dict[str, BaseMemoryProvider] = {}
        self.default_providers = ["fts5", "lancedb"]
        
    def register_provider(self, provider: BaseMemoryProvider) -> None:
        """注册记忆 Provider"""
        pass
    
    async def hybrid_retrieve(self,
                            query: MemoryQuery,
                            provider_weights: Optional[Dict[str, float]] = None) -> MemoryResult:
        """混合检索（结合多个 Provider）"""
        pass
    
    def get_provider_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取 Provider 统计信息"""
        pass
```

### 2.11 P16: 洞察报告

#### 2.11.1 接口定义

```python
# clawteam/insights/engine.py
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import pandas as pd

class InsightMetric(BaseModel):
    name: str
    value: Any
    unit: Optional[str] = None
    trend: Optional[str] = None  # up, down, stable
    change_percentage: Optional[float] = None
    description: str = ""

class InsightReport(BaseModel):
    report_id: str = Field(default_factory=lambda: f"insight_{uuid.uuid4().hex[:8]}")
    period_start: datetime
    period_end: datetime
    generated_at: datetime = Field(default_factory=datetime.now)
    metrics: Dict[str, InsightMetric] = Field(default_factory=dict)
    trends: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    summary: str = ""

class InsightsEngine:
    """洞察引擎"""
    
    def __init__(self, data_sources: Optional[List[str]] = None):
        self.data_sources = data_sources or [
            "usage",
            "skills", 
            "memory",
            "sessions",
            "tasks"
        ]
        
    def generate_daily_report(self, date: Optional[datetime] = None) -> InsightReport:
        """生成日报"""
        pass
    
    def generate_weekly_report(self, week_start: Optional[datetime] = None) -> InsightReport:
        """生成周报"""
        pass
    
    def analyze_trends(self,
                      metric_name: str,
                      days: int = 30,
                      interval: str = "daily") -> Dict[str, Any]:
        """分析趋势"""
        pass
    
    def compare_periods(self,
                       period1: Tuple[datetime, datetime],
                       period2: Tuple[datetime, datetime]) -> Dict[str, Any]:
        """比较两个时间段"""
        pass
    
    def detect_anomalies(self,
                        metric_name: str,
                        threshold: float = 2.0) -> List[Dict[str, Any]]:
        """检测异常"""
        pass
    
    def generate_cost_analysis(self,
                             provider_filter: Optional[List[str]] = None,
                             days: int = 30) -> Dict[str, Any]:
        """生成成本分析"""
        pass
    
    def get_top_metrics(self,
                       category: str,
                       limit: int = 10,
                       days: int = 7) -> List[Dict[str, Any]]:
        """获取 Top N 指标"""
        pass

class CLIInsights:
    """CLI 洞察接口"""
    
    @staticmethod
    def show_overview(days: int = 7) -> str:
        """显示概览"""
        pass
    
    @staticmethod
    def show_tools_ranking(days: int = 30, limit: int = 10) -> str:
        """显示工具使用排行"""
        pass
    
    @staticmethod
    def show_skills_ranking(days: int = 30, limit: int = 10) -> str:
        """显示技能使用排行"""
        pass
    
    @staticmethod
    def show_cost_breakdown(days: int = 30, format: str = "table") -> str:
        """显示成本明细"""
        pass
    
    @staticmethod
    def show_memory_usage(days: int = 7) -> str:
        """显示记忆使用情况"""
        pass
```

### 2.12 P17: Web UI 聊天窗口

#### 2.12.1 接口定义

```python
# clawteam/board/chat_server.py
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from sse_starlette.sse import EventSourceResponse

class ChatMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:8]}")
    sender: str  # "user" 或 "assistant" 或 "system"
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ChatCommand(BaseModel):
    command: str  # "create_task", "assign_agent", "status", "cancel"
    parameters: Dict[str, Any] = Field(default_factory=dict)
    sender: str
    timestamp: datetime = Field(default_factory=datetime.now)

class ChatSession(BaseModel):
    session_id: str = Field(default_factory=lambda: f"chat_{uuid.uuid4().hex[:8]}")
    user_id: str = "anonymous"
    created_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    messages: List[ChatMessage] = Field(default_factory=list)
    commands: List[ChatCommand] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ChatServer:
    """聊天服务器"""
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.sessions: Dict[str, ChatSession] = {}
        self.connections: Dict[str, List[WebSocket]] = {}
        self._setup_routes()
        
    def _setup_routes(self) -> None:
        """设置路由"""
        
        @self.app.post("/api/chat/send")
        async def send_message(message: ChatMessage, session_id: Optional[str] = None):
            """发送消息"""
            pass
            
        @self.app.get("/api/chat/events")
        async def chat_events(session_id: str):
            """SSE 事件流"""
            pass
            
        @self.app.get("/api/chat/history")
        async def get_history(session_id: str, limit: int = 100):
            """获取聊天历史"""
            pass
            
        @self.app.post("/api/chat/command")
        async def send_command(command: ChatCommand, session_id: str):
            """发送命令"""
            pass
            
        @self.app.websocket("/api/chat/ws/{session_id}")
        async def websocket_endpoint(websocket: WebSocket, session_id: str):
            """WebSocket 连接"""
            pass
    
    async def broadcast_to_session(self,
                                  session_id: str,
                                  event_type: str,
                                  data: Dict[str, Any]) -> None:
        """向会话广播事件"""
        pass
    
    async def process_command(self,
                            command: ChatCommand,
                            session_id: str) -> Dict[str, Any]:
        """处理命令"""
        pass
    
    def create_session(self, user_id: str = "anonymous") -> str:
        """创建聊天会话"""
        pass
    
    def cleanup_inactive_sessions(self, max_inactive_minutes: int = 60) -> List[str]:
        """清理不活跃会话"""
        pass
```

## 3. 模块间依赖关系分析

### 3.1 核心依赖图

```
Supervisor (P6) → ProviderSelector (P9) → BaseProvider (P9)
    ↓                           ↓                ↓
SessionRegistry (P7)    FileChangeTracker (P8)  TokenStats (P11)
    ↓                           ↓                ↓
CrossSessionAwareness (P7) → AutoCapture (P12) → Insights (P16)
    ↓                           ↓                ↓
SkillAutoCreator (P13) → UserProfile (P14) → Memory (P15)
    ↓                           ↓                ↓
ChatServer (P17) ←──────────────┴────────────────┘
```

### 3.2 依赖矩阵

| 模块 | 依赖的模块 | 被依赖的模块 |
|------|------------|--------------|
| Supervisor (P6) | ProviderSelector, SessionRegistry, TokenStats | ChatServer, Insights |
| SessionRegistry (P7) | (无核心依赖) | Supervisor, CrossSessionAwareness, Insights |
| FileChangeTracker (P8) | (文件系统) | CrossSessionAwareness, AutoCapture |
| ProviderSelector (P9) | BaseProvider, TokenStats | Supervisor, Insights |
| WorktreeManager (P10) | (Git) | Supervisor, AutoCapture |
| TokenStats (P11) | (数据库) | Supervisor, ProviderSelector, Insights |
| AutoCapture (P12) | SessionRegistry, FileChangeTracker | SkillAutoCreator, Insights |
| SkillAutoCreator (P13) | AutoCapture, TokenStats | Insights, ChatServer |
| UserProfile (P14) | SessionRegistry | Memory, Insights |
| Memory (P15) | (向量数据库/SQLite) | UserProfile, Insights |
| Insights (P16) | 所有数据源 | ChatServer |
| ChatServer (P17) | 所有上层模块 | (用户界面) |

### 3.3 事件流

1. **任务启动**: User → ChatServer → Supervisor → ProviderSelector
2. **文件修改**: Agent → FileChangeTracker → AutoCapture → SkillAutoCreator
3. **会话活动**: Agent → SessionRegistry → CrossSessionAwareness → Insights
4. **记忆同步**: Conversation → Memory → UserProfile → Insights
5. **报告生成**: Insights → ChatServer → User

## 4. 数据库/文件存储格式设计

### 4.1 P7: Session Registry 存储格式

```json
// ~/.openclaw/data/sessions/{session_id}.json
{
  "sessionId": "abc123def456",
  "sessionName": "backend-refactor",
  "status": "active",
  "workDir": "/path/to/project",
  "teamName": "default",
  "agentName": "backend",
  "agentId": "agent-001",
  "role": "worker",
  "provider": "claude-code",
  "createdAt": "2026-04-28T10:30:00Z",
  "updatedAt": "2026-04-28T11:45:00Z",
  "lastHeartbeat": "2026-04-28T11:45:00Z",
  "filesModified": ["src/api.py", "tests/test_api.py"],
  "commandsExecuted": ["pytest tests/", "ruff check src/"],
  "tasksCompleted": 3,
  "currentTask": "重构认证模块",
  "summary": "正在重构用户认证系统",
  "tags": ["backend", "refactoring"],
  "metadata": {
    "estimatedCompletion": "2026-04-28T14:00:00Z",
    "priority": "high"
  }
}
```

### 4.2 P14: User Profile 存储格式

```json
// ~/.openclaw/profiles/{user_id}.json
{
  "userId": "default",
  "name": "楚灵",
  "identity": "技术负责人",
  "preferences": {
    "codeStyle": {
      "key": "codeStyle",
      "value": {
        "indent": 2,
        "quoteStyle": "single",
        "maxLineLength": 100
      },
      "confidence": 0.9,
      "source": "多次提到偏好",
      "createdAt": "2026-04-25T09:00:00Z",
      "updatedAt": "2026-04-28T10:15:00Z",
      "evidence": [
        "对话1: '我喜欢2空格缩进'",
        "对话2: '单引号更简洁'"
      ]
    }
  },
  "behavioralPatterns": {
    "workingHours": {
      "patternType": "working_hours",
      "data": {
        "peakStart": "09:00",
        "peakEnd": "18:00",
        "timezone": "Asia/Shanghai"
      },
      "confidence": 0.85,
      "firstObserved": "2026-04-20T08:30:00Z",
      "lastObserved": "2026-04-28T17:45:00Z"
    }
  },
  "projects": {
    "clawteam": {
      "name": "ClawTeam升级",
      "status": "active",
      "priority": "high",
      "lastActivity": "2026-04-28T11:30:00Z"
    }
  },
  "evolution": [
    {
      "timestamp": "2026-04-25T10:00:00Z",
      "change": "偏好代码风格",
      "source": "对话分析"
    }
  ],
  "createdAt": "2026-04-20T08:00:00Z",
  "updatedAt": "2026-04-28T11:45:00Z"
}
```

### 4.3 P15: Memory 存储格式

#### 4.3.1 FTS5 SQLite 表结构

```sql
-- ~/.openclaw/memory/fts5.db
CREATE TABLE memories (
    memory_id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 0
);

CREATE VIRTUAL TABLE memories_fts USING fts5(
    content,
    metadata,
    content='memories',
    content_rowid='rowid'
);

-- 触发器保持同步
CREATE TRIGGER memories_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, content, metadata)
    VALUES (new.rowid, new.content, new.metadata);
END;
```

#### 4.3.2 LanceDB 向量存储

```
~/.openclaw/memory/lancedb/
├── memories/
│   ├── _versions/
│   ├── data.lance
│   └── schema.json
└── embeddings/
    └── all-MiniLM-L6-v2/
        └── vectors.lance
```

### 4.4 P16: Insights 数据存储

```json
// ~/.openclaw/insights/daily/2026-04-28.json
{
  "date": "2026-04-28",
  "metrics": {
    "total_tokens": {
      "input": 12500,
      "output": 8500,
      "total": 21000
    },
    "cost_estimate": {
      "total_usd": 0.42,
      "by_provider": {
        "claude-code": 0.25,
        "gemini": 0.12,
        "codex": 0.05
      }
    },
    "session_activity": {
      "active_sessions": 3,
      "total_sessions": 5,
      "avg_session_duration_minutes": 45
    },
    "skill_usage": {
      "total_invocations": 12,
      "success_rate": 0.92,
      "top_skills": ["code-review", "test-generation"]
    }
  },
  "trends": [
    {
      "metric": "total_tokens",
      "trend": "up",
      "change_percentage": 15.5
    }
  ],
  "anomalies": [],
  "generated_at": "2026-04-28T23:59:59Z"
}
```

## 5. 向后兼容性保证策略

### 5.1 兼容性原则

1. **API 兼容性**: 所有公共 API 保持向后兼容
2. **数据兼容性**: 数据迁移提供自动升级路径
3. **配置兼容性**: 配置文件支持新旧版本共存
4. **插件兼容性**: 插件系统保持稳定接口

### 5.2 具体策略

#### 5.2.1 版本化 API

```python
# 所有新增功能通过版本化端点提供
# 旧端点保持原状
@app.get("/api/v1/sessions")  # 保持兼容
@app.get("/api/v2/sessions")  # 新增功能
```

#### 5.2.2 数据迁移工具

```python
class DataMigrator:
    """数据迁移工具"""
    
    @staticmethod
    def migrate_sessions_v1_to_v2(old_data_dir: Path, new_data_dir: Path) -> MigrationResult:
        """会话数据迁移"""
        pass
    
    @staticmethod
    def migrate_memories_v1_to_v2(old_db_path: Path, new_db_path: Path) -> MigrationResult:
        """记忆数据迁移"""
        pass
    
    @staticmethod
    def check_compatibility(current_version: str, target_version: str) -> CompatibilityReport:
        """检查兼容性"""
        pass
```

#### 5.2.3 配置回退机制

```python
class ConfigManager:
    """配置管理器"""
    
    def load_config(self, config_path: Path) -> Dict[str, Any]:
        """加载配置，支持多版本"""
        version = self._detect_config_version(config_path)
        
        if version == "1.0":
            return self._migrate_v1_to_v2(config_path)
        elif version == "2.0":
            return self._load_v2_config(config_path)
        else:
            raise ValueError(f"Unsupported config version: {version}")
    
    def save_config_with_backup(self, config: Dict[str, Any], config_path: Path) -> None:
        """保存配置并备份旧版本"""
        backup_path = config_path.with_suffix(f".backup_{datetime.now().isoformat()}")
        if config_path.exists():
            shutil.copy(config_path, backup_path)
        self._save_config(config, config_path)
```

#### 5.2.4 测试覆盖

- **单元测试**: 验证新旧 API 行为一致
- **集成测试**: 验证数据迁移路径
- **回归测试**: 确保现有功能不受影响
- **兼容性测试矩阵**:

| 组件 | 测试重点 | 兼容性保证 |
|------|----------|------------|
| SessionRegistry | 会话注册/查询 | 现有会话数据可读 |
| ProviderSelector | Provider 选择 | 现有配置有效 |
| FileChangeTracker | 文件追踪 | 历史记录可访问 |
| Supervisor | 任务编排 | 现有任务可继续 |

## 6. pyproject.toml 新增依赖清单

### 6.1 必需依赖

```toml
[project]
dependencies = [
    # 现有依赖保持不变
    "typer>=0.12.0,<1.0.0",
    "pydantic>=2.0.0,<3.0.0", 
    "rich>=13.0.0,<15.0.0",
    "tomli>=2.0.0; python_version < '3.11'",
    
    # P6-P17 新增核心依赖
    "watchfiles>=0.21.0",        # P8 文件监视
    "pydantic-settings>=2.0.0",  # P9 配置管理
    "aiosqlite>=0.19.0",         # P11/P15 异步 SQLite
    "python-dateutil>=2.8.0",    # P11/P16 日期处理
    "orjson>=3.9.0",             # P12-P16 JSON 高性能处理
    "pyyaml>=6.0",               # P13 技能 YAML 解析
    "sse-starlette>=1.6.0",      # P17 SSE 支持
    "websockets>=12.0",          # P17 WebSocket 支持
]
```

### 6.2 可选依赖组

```toml
[project.optional-dependencies]
# 现有可选依赖
dev = [
    "pytest>=9.0.0,<10.0.0",
    "ruff>=0.1.0",
]
p2p = [
    "pyzmq>=25.0.0,<27.0.0",
]
redis = [
    "redis>=4.5.0,<6.0.0",
]

# P6-P17 新增可选依赖
supervisor = [
    "networkx>=3.0",          # P6 DAG 分析
    "graphviz>=0.20.0",       # P6 可视化
]

provider = [
    "openai>=1.0.0",          # P9 OpenAI 支持
    "anthropic>=0.18.0",      # P9 Anthropic 支持
    "google-generativeai>=0.3.0",  # P9 Gemini 支持
]

memory = [
    "sqlite-fts5",            # P15 FTS5 全文检索
    "lancedb>=0.5.0",         # P15 向量数据库
    "sentence-transformers>=2.2.0",  # P15 嵌入模型
]

insights = [
    "pandas>=2.0.0",          # P16 数据分析
    "plotly>=5.18.0",         # P16 可视化
    "numpy>=1.24.0",          # P16 数值计算
]

web = [
    "fastapi>=0.104.0",       # P17 Web 框架
    "uvicorn[standard]>=0.24.0",  # P17 ASGI 服务器
    "jinja2>=3.1.0",          # P17 模板引擎
]

all = [
    "clawteam[supervisor]",
    "clawteam[provider]",
    "clawteam[memory]",
    "clawteam[insights]",
    "clawteam[web]",
]
```

### 6.3 开发依赖

```toml
[tool.hatch.envs.test]
dependencies = [
    "pytest-asyncio>=0.21.0",      # 异步测试
    "pytest-cov>=4.0.0",           # 覆盖率
    "httpx>=0.25.0",               # HTTP 测试
    "freezegun>=1.2.0",            # 时间模拟
]

[tool.hatch.envs.lint]
dependencies = [
    "ruff>=0.1.0",
    "mypy>=1.7.0",
    "black>=23.0.0",
    "isort>=5.12.0",
]

[tool.hatch.envs.docs]
dependencies = [
    "mkdocs>=1.5.0",
    "mkdocs-material>=9.0.0",
    "mkdocstrings[python]>=0.23.0",
]
```

## 7. 实施建议

### 7.1 开发顺序

1. **第一阶段 (P6-P8)**: 核心编排能力
   - 先实现 Supervisor 基本框架
   - 集成现有 SessionRegistry
   - 添加 FileChangeTracker
   
2. **第二阶段 (P9-P11)**: 基础设施完善
   - Provider 自适应系统
   - Git Worktree 管理
   - Token 统计系统
   
3. **第三阶段 (P12-P13)**: 自主进化
   - .learnings 自动闭环
   - 自主技能创建
   
4. **第四阶段 (P14-P16)**: 智能增强
   - 用户画像系统
   - 记忆增强
   - 洞察报告
   
5. **第五阶段 (P17)**: 用户体验
   - Web UI 聊天窗口

### 7.2 测试策略

1. **单元测试**: 每个模块独立测试
2. **集成测试**: 模块间交互测试
3. **端到端测试**: 完整流程测试
4. **性能测试**: 大数据量场景测试
5. **兼容性测试**: 版本升级测试

### 7.3 部署建议

1. **分阶段部署**: 按 Phase 逐个部署
2. **功能开关**: 新功能通过配置开关控制
3. **监控报警**: 关键指标监控
4. **回滚计划**: 出现问题快速回滚

## 8. 总结

本架构设计文档为 ClawTeam P6-P17 升级提供了完整的蓝图。通过分层架构设计，确保了系统的可扩展性、可维护性和向后兼容性。每个 Phase 都有明确的接口定义、数据存储设计和实施路径。

关键创新点包括：
1. **AI 自主编排**: Supervisor 模式实现任务自动分解和执行
2. **跨会话感知**: 实时协作和冲突检测
3. **自主进化**: 从经验中学习并创建新技能
4. **个性化适配**: 用户画像和记忆增强
5. **智能洞察**: 数据驱动的优化建议

实施本架构将使 ClawTeam 从一个基础的多 Agent 协调框架，进化为一个具有自主学习和进化能力的智能开发平台。

---
**文档版本**: 1.0.0  
**最后更新**: 2026-04-28  
**下一步**: 开始 P6 Supervisor 模式的具体实现