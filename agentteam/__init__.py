"""AgentTeam - Framework-agnostic multi-agent coordination CLI."""

__version__ = "0.7.6"

# Exceptions
from agentteam.exceptions import (
    AgentTeamError,
    AgentNotFoundError,
    AgentSpawnError,
    AuthenticationError,
    ConfigurationError,
    TeamAlreadyExistsError,
    TeamNotFoundError,
    TaskError,
    TaskNotFoundError,
    TransportError,
    ValidationError,
)

# Core multi-agent framework (SDK-style)
from agentteam.alerts import (
    Alert,
    AlertType,
    acknowledge_alert,
    check_agent_failure_rates,
    check_task_timeouts,
    create_alert,
)
from agentteam.audit import (
    AuditEvent,
    AuditEventType,
    get_audit_summary,
    log_audit_event,
    read_audit_log,
)
from agentteam.core import (
    AgentState as AgentStatus,
)
from agentteam.core import (
    CTAgent as Agent,
)
from agentteam.core import (
    CTMessage as Message,
)
from agentteam.core import (
    CTTask as Task,
)
from agentteam.core import (
    CTTeam as Team,
)
from agentteam.core import (
    TaskState as TaskStatus,
)
from agentteam.core import (
    create_team,
    get_team,
)

from agentteam.orchestrator.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitOpenError,
    get_circuit_breaker,
    list_circuit_breakers,
)

from agentteam.team.snapshot import SnapshotManager
from agentteam.team.dag import topological_sort, CycleDetectedError
from agentteam.team.roles import assign_role, get_agent_roles, suggest_role, AgentRole
from agentteam.async_core import AsyncExecutor

# Orchestrator module (P6, P9)
from agentteam.orchestrator import (
    FallbackChain,
    ProviderInfo,
    ProviderSelector,
    ProviderStatus,
    QuotaInfo,
    SelectionResult,
)
from agentteam.orchestrator.supervisor import (
    DecompositionPattern,
    DecompositionRule,
    ExecutionResult,
    SupervisorEngine,
    VerificationResult,
    get_supervisor,
)
from agentteam.orchestrator.supervisor import (
    TaskPlan as SupervisorPlan,
)

# Session module (P7)
from agentteam.session import (
    CrossSessionBus,
    CrossSessionMessage,
    NotificationType,
    SessionInfo,
    SessionRegistry,
    SessionStatus,
    get_cross_session_bus,
    get_session_registry,
)
from agentteam.team import (
    InboxWatcher,
    LifecycleManager,
    MailboxManager,
    PlanManager,
    TeamManager,
)

# Task models from team module (used by Supervisor)
from agentteam.team.models import (
    TaskItem as SubTask,
)
from agentteam.team.models import (
    TaskPriority,
    TaskStatus,
)

# Tracker module (P8, P11)
from agentteam.tracker import (
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
from agentteam.workspace import (
    WorkspaceManager,
    get_workspace_manager,
)
from agentteam.workspace.worktree import (
    MergeCheckResult,
    MergeResult,
    WorktreeInfo,
    WorktreeManager,
    WorktreeStatus,
)

# 注：WorktreeConflict 在 worktree.py 中不存在，可能是个遗留引用

# Usage module (P11) - 暂时跳过，后面实现
try:
    from agentteam.usage import (
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
from agentteam.insights import (
    InsightsEngine,
)
from agentteam.memory import (
    FTS5MemoryProvider,
    MemoryProvider,
)

# Skill module (P13)
from agentteam.skill.engine import SkillEngine

__all__ = [
    # Exceptions
    "AgentTeamError",
    "TeamNotFoundError",
    "TeamAlreadyExistsError",
    "TaskNotFoundError",
    "TaskError",
    "AgentError",
    "AgentNotFoundError",
    "AgentSpawnError",
    "ConfigurationError",
    "TransportError",
    "AuthenticationError",
    "ValidationError",
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
    "SkillEngine", "SnapshotManager", "topological_sort", "CycleDetectedError", "assign_role", "get_agent_roles", "suggest_role", "AgentRole", "AsyncExecutor", "CircuitBreaker", "CircuitState", "CircuitOpenError", "get_circuit_breaker", "list_circuit_breakers"
]
