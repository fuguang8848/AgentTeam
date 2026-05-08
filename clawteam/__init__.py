"""ClawTeam - Framework-agnostic multi-agent coordination CLI."""

__version__ = "0.7.6"

# Core multi-agent framework (SDK-style)
from clawteam.alerts import (
    Alert,
    AlertType,
    acknowledge_alert,
    check_agent_failure_rates,
    check_task_timeouts,
    create_alert,
)
from clawteam.audit import (
    AuditEvent,
    AuditEventType,
    get_audit_summary,
    log_audit_event,
    read_audit_log,
)
from clawteam.core import (
    AgentState as AgentStatus,
)
from clawteam.core import (
    CTAgent as Agent,
)
from clawteam.core import (
    CTMessage as Message,
)
from clawteam.core import (
    CTTask as Task,
)
from clawteam.core import (
    CTTeam as Team,
)
from clawteam.core import (
    TaskState as TaskStatus,
)
from clawteam.core import (
    create_team,
    get_team,
)

# Orchestrator module (P6, P9)
from clawteam.orchestrator import (
    FallbackChain,
    ProviderInfo,
    ProviderSelector,
    ProviderStatus,
    QuotaInfo,
    SelectionResult,
)
from clawteam.orchestrator.supervisor import (
    DecompositionPattern,
    DecompositionRule,
    ExecutionResult,
    SupervisorEngine,
    VerificationResult,
    get_supervisor,
)
from clawteam.orchestrator.supervisor import (
    TaskPlan as SupervisorPlan,
)

# Session module (P7)
from clawteam.session import (
    CrossSessionBus,
    CrossSessionMessage,
    NotificationType,
    SessionInfo,
    SessionRegistry,
    SessionStatus,
    get_cross_session_bus,
    get_session_registry,
)
from clawteam.team import (
    InboxWatcher,
    LifecycleManager,
    MailboxManager,
    PlanManager,
    TeamManager,
)

# Task models from team module (used by Supervisor)
from clawteam.team.models import (
    TaskItem as SubTask,
)
from clawteam.team.models import (
    TaskPriority,
    TaskStatus,
)

# Tracker module (P8, P11)
from clawteam.tracker import (
    DailyUsage,
    ProviderUsageStats,
    SessionUsage,
    TrendAnalysis,
    UsageEstimator,
    UsageSummary,
    accumulate_usage,
    estimate_tokens,
    get_provider_stats,
    get_usage_estimator,
    get_usage_summary,
    get_usage_trend,
    mark_session_ended,
    record_request,
)

# Git module (P10) - Workspace worktree management
from clawteam.workspace import (
    WorkspaceManager,
    get_workspace_manager,
)
from clawteam.workspace.worktree import (
    MergeCheckResult,
    MergeResult,
    WorktreeInfo,
    WorktreeManager,
    WorktreeStatus,
)

# 注：WorktreeConflict 在 worktree.py 中不存在，可能是个遗留引用

# Usage module (P11) - 暂时跳过，后面实现
try:
    from clawteam.usage import (
        TokenStatsTracker,
        TokenStatType,
        TokenUsage,
        UsageAggregate,
    )
except ImportError:
    # Usage module not yet implemented
    TokenStatsTracker = None
    TokenUsage = None
    UsageAggregate = None
    TokenStatType = None

# Memory module (P15)
# Insights module (P16)
from clawteam.insights import (
    InsightsEngine,
)
from clawteam.memory import (
    FTS5MemoryProvider,
    MemoryProvider,
)

# Skill module (P13)
from clawteam.skill.engine import SkillEngine

__all__ = [
    # Core multi-agent framework
    "Team",
    "Agent",
    "Task",
    "Message",
    "AgentStatus",
    "TaskStatus",
    "create_team",
    "get_team",
    # Alerts module
    "Alert",
    "AlertType",
    "create_alert",
    "acknowledge_alert",
    "check_task_timeouts",
    "check_agent_failure_rates",
    # Audit module
    "AuditEvent",
    "AuditEventType",
    "get_audit_summary",
    "log_audit_event",
    "read_audit_log",
    # Team module
    "TeamManager",
    "MailboxManager",
    "PlanManager",
    "LifecycleManager",
    "InboxWatcher",
    # Orchestrator module (P6, P9)
    "ProviderSelector",
    "ProviderInfo",
    "ProviderStatus",
    "QuotaInfo",
    "SelectionResult",
    "FallbackChain",
    "SupervisorEngine",
    "DecompositionPattern",
    "DecompositionRule",
    "SupervisorPlan",
    "SubTask",
    "ExecutionResult",
    "VerificationResult",
    "get_supervisor",
    "TaskStatus",
    "TaskPriority",
    # Session module (P7)
    "SessionRegistry",
    "SessionInfo",
    "SessionStatus",
    "get_session_registry",
    "CrossSessionBus",
    "CrossSessionMessage",
    "NotificationType",
    "get_cross_session_bus",
    # Tracker module (P8, P11)
    "UsageEstimator",
    "UsageSummary",
    "DailyUsage",
    "SessionUsage",
    "TrendAnalysis",
    "ProviderUsageStats",
    "get_usage_estimator",
    "estimate_tokens",
    "accumulate_usage",
    "get_usage_summary",
    "get_usage_trend",
    "get_provider_stats",
    "record_request",
    "mark_session_ended",
    # Git module (P10) - Workspace worktree management
    "WorkspaceManager",
    "get_workspace_manager",
    "WorktreeManager",
    "WorktreeInfo",
    "WorktreeStatus",
    "MergeCheckResult",
    "MergeResult",
    # Usage module (P11)
    "TokenStatsTracker",
    "TokenUsage",
    "UsageAggregate",
    "TokenStatType",
    # Memory module (P15)
    "MemoryProvider",
    "FTS5MemoryProvider",
    # Insights module (P16)
    "InsightsEngine",
    # Skill module (P13)
    "SkillEngine",
]
