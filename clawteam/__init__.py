"""ClawTeam - Framework-agnostic multi-agent coordination CLI."""

__version__ = "0.3.0+openclaw1"

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
from clawteam.team import (
    InboxWatcher,
    LifecycleManager,
    MailboxManager,
    PlanManager,
    TeamManager,
)

# Orchestrator module (P6, P9)
from clawteam.orchestrator import (
    ProviderSelector,
    ProviderInfo,
    ProviderStatus,
    QuotaInfo,
    SelectionResult,
    FallbackChain,
)
from clawteam.orchestrator.supervisor import (
    SupervisorEngine,
    DecompositionPattern,
    DecompositionRule,
    TaskPlan as SupervisorPlan,
    ExecutionResult,
    VerificationResult,
    get_supervisor,
)

# Task models from team module (used by Supervisor)
from clawteam.team.models import (
    TaskItem as SubTask,
    TaskStatus,
    TaskPriority,
)

# Session module (P7)
from clawteam.session import (
    SessionRegistry,
    SessionInfo,
    SessionStatus,
    get_session_registry,
    CrossSessionBus,
    CrossSessionMessage,
    NotificationType,
    get_cross_session_bus,
)

# Tracker module (P8, P11)
from clawteam.tracker import (
    UsageEstimator,
    UsageSummary,
    DailyUsage,
    SessionUsage,
    TrendAnalysis,
    ProviderUsageStats,
    get_usage_estimator,
    estimate_tokens,
    accumulate_usage,
    get_usage_summary,
    get_usage_trend,
    get_provider_stats,
    record_request,
    mark_session_ended,
)

# Git module (P10) - Workspace worktree management
from clawteam.workspace import (
    WorkspaceManager,
    get_workspace_manager,
)
from clawteam.workspace.worktree import (
    WorktreeManager,
    WorktreeInfo,
    WorktreeStatus,
    MergeCheckResult,
    MergeResult,
)
# 注：WorktreeConflict 在 worktree.py 中不存在，可能是个遗留引用

# Usage module (P11) - 暂时跳过，后面实现
try:
    from clawteam.usage import (
        TokenStatsTracker,
        TokenUsage,
        UsageAggregate,
        TokenStatType,
    )
except ImportError:
    # Usage module not yet implemented
    TokenStatsTracker = None
    TokenUsage = None
    UsageAggregate = None
    TokenStatType = None

# Memory module (P15)
from clawteam.memory import (
    MemoryProvider,
    FTS5MemoryProvider,
)

# Insights module (P16)
from clawteam.insights import (
    InsightsEngine,
)

# Skill module (P13)
from clawteam.skill.engine import SkillEngine

__all__ = [
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