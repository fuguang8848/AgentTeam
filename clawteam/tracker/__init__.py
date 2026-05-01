"""ClawTeam Tracker Module — 文件追踪和Token统计"""

from __future__ import annotations

from clawteam.tracker.file_watcher import FileWatcher, WatchEvent, ChangeType, watch_directory
from clawteam.tracker.change_attribution import ChangeRecord, ChangeAttributor, ActiveSession
from clawteam.tracker.diff_tracker import DiffTracker, DiffEntry, FileSnapshot
from clawteam.tracker.file_tracker import (
    FileChange,
    FileChangeTracker,
    FileChangeTrackerConfig,
    get_file_change_tracker,
    track_file_change,
    get_recent_file_changes,
)
from clawteam.tracker.token_stats import (
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

__all__ = [
    # File watcher
    "FileWatcher",
    "WatchEvent",
    "ChangeType",
    "watch_directory",
    
    # Change attribution
    "ChangeRecord",
    "ChangeAttributor",
    "ActiveSession",
    
    # Diff tracker
    "DiffTracker",
    "DiffEntry",
    "FileSnapshot",
    
    # File change tracker
    "FileChange",
    "FileChangeTracker",
    "FileChangeTrackerConfig",
    "get_file_change_tracker",
    "track_file_change",
    "get_recent_file_changes",
    
    # Token stats
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
]
