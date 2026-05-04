"""测试 P9/P10/P11 功能：Provider 自适应、Git Worktree、Token 统计

@author ClawTeam
"""

import pytest
import tempfile
import os
import json
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock


# ==============================================================================
# P9: Provider 自适应测试
# ==============================================================================

class TestProviderCapabilityRegistry:
    """测试 Provider 能力注册表"""
    
    def test_get_capability(self):
        """测试获取 Provider 能力"""
        from clawteam.orchestrator.provider_capability import ProviderCapabilityRegistry
        
        # 测试已知 Provider
        cap = ProviderCapabilityRegistry.get("claude-code")
        assert cap is not None
        assert cap.provider_id == "claude-code"
        assert cap.mcp_support.native
        assert cap.skill_support.slash_commands
        
    def test_get_unknown_capability(self):
        """测试获取未知 Provider"""
        from clawteam.orchestrator.provider_capability import ProviderCapabilityRegistry
        
        cap = ProviderCapabilityRegistry.get("unknown-provider")
        assert cap is None
    
    def test_get_all_capabilities(self):
        """测试获取所有能力"""
        from clawteam.orchestrator.provider_capability import ProviderCapabilityRegistry
        
        caps = ProviderCapabilityRegistry.get_all()
        assert len(caps) > 0
        assert any(c.provider_id == "claude-code" for c in caps)
    
    def test_get_mcp_capability(self):
        """测试获取 MCP 能力"""
        from clawteam.orchestrator.provider_capability import ProviderCapabilityRegistry
        
        mcp = ProviderCapabilityRegistry.get_mcp_capability("claude-code")
        assert mcp.native
        
        # 未知 Provider 返回默认值
        mcp = ProviderCapabilityRegistry.get_mcp_capability("unknown")
        assert not mcp.native
    
    def test_get_skill_capability(self):
        """测试获取 Skill 能力"""
        from clawteam.orchestrator.provider_capability import ProviderCapabilityRegistry
        
        skill = ProviderCapabilityRegistry.get_skill_capability("claude-code")
        assert skill.slash_commands
        assert skill.system_prompt
    
    def test_supports_native_mcp(self):
        """测试原生 MCP 支持"""
        from clawteam.orchestrator.provider_capability import ProviderCapabilityRegistry
        
        assert ProviderCapabilityRegistry.supports_native_mcp("claude-code")
        assert not ProviderCapabilityRegistry.supports_native_mcp("codex")
    
    def test_supports_mcp_fallback(self):
        """测试 MCP 降级支持"""
        from clawteam.orchestrator.provider_capability import ProviderCapabilityRegistry
        
        assert ProviderCapabilityRegistry.supports_mcp_fallback("codex")
        assert not ProviderCapabilityRegistry.supports_mcp_fallback("claude-code")
    
    def test_get_registered_ids(self):
        """测试获取已注册 ID"""
        from clawteam.orchestrator.provider_capability import ProviderCapabilityRegistry
        
        ids = ProviderCapabilityRegistry.get_registered_ids()
        assert "claude-code" in ids
        assert "codex" in ids
    
    def test_register_new_capability(self):
        """测试动态注册新能力"""
        from clawteam.orchestrator.provider_capability import (
            ProviderCapabilityRegistry,
            ProviderCapability,
            ProviderMcpCapability,
            ProviderSkillCapability,
        )
        
        new_cap = ProviderCapability(
            provider_id="new-provider",
            mcp_support=ProviderMcpCapability(native=True),
            skill_support=ProviderSkillCapability(slash_commands=True),
        )
        
        ProviderCapabilityRegistry.register(new_cap)
        assert ProviderCapabilityRegistry.has("new-provider")
        
        # 清理
        ProviderCapabilityRegistry.unregister("new-provider")
        assert not ProviderCapabilityRegistry.has("new-provider")
    
    def test_get_summary(self):
        """测试获取摘要"""
        from clawteam.orchestrator.provider_capability import ProviderCapabilityRegistry
        
        summary = ProviderCapabilityRegistry.get_summary()
        assert "totalProviders" in summary
        assert "nativeMcpProviders" in summary


class TestProviderAvailability:
    """测试 Provider 可用性检测"""
    
    def test_check_provider_availability(self):
        """测试检测 Provider 可用性"""
        from clawteam.orchestrator.provider_availability import check_provider_availability
        
        # 测试一个可能存在的命令
        result = check_provider_availability("claude-code")
        assert result.id == "claude-code"
        assert result.available in [True, False]  # 取决于环境
    
    def test_check_unknown_provider(self):
        """测试检测未知 Provider"""
        from clawteam.orchestrator.provider_availability import check_provider_availability
        
        result = check_provider_availability("unknown-provider")
        assert not result.available
        assert "Unknown provider" in result.error
    
    def test_get_availability_summary(self):
        """测试获取可用性摘要"""
        from clawteam.orchestrator.provider_availability import get_availability_summary
        
        summary = get_availability_summary()
        assert "totalProviders" in summary
        assert "availableCount" in summary
        assert "unavailableCount" in summary
    
    def test_clear_cache(self):
        """测试清除缓存"""
        from clawteam.orchestrator.provider_availability import (
            check_provider_availability,
            clear_availability_cache,
        )
        
        # 先检测一次
        check_provider_availability("claude-code")
        
        # 清除缓存
        clear_availability_cache()


class TestProviderAutoSwitchManager:
    """测试 Provider 自动切换管理器"""
    
    def test_init(self):
        """测试初始化"""
        from clawteam.orchestrator.provider_selector import ProviderAutoSwitchManager
        
        manager = ProviderAutoSwitchManager("test-team")
        assert manager.team_name == "test-team"
        assert manager.auto_switch_enabled
    
    def test_get_current_provider(self):
        """测试获取当前 Provider"""
        from clawteam.orchestrator.provider_selector import ProviderAutoSwitchManager
        
        manager = ProviderAutoSwitchManager("test-team")
        assert manager.get_current_provider() is None
        
        manager.set_current_provider("claude")
        assert manager.get_current_provider() == "claude"
    
    def test_handle_quota_exceeded(self):
        """测试处理额度不足"""
        from clawteam.orchestrator.provider_selector import ProviderAutoSwitchManager, TaskType
        
        manager = ProviderAutoSwitchManager("test-team")
        
        # 模拟额度不足
        result = manager.handle_quota_exceeded("claude", TaskType.code_generation)
        
        # 验证切换历史记录
        history = manager.get_switch_history()
        assert len(history) > 0
        assert history[-1]["from_provider"] == "claude"
        assert history[-1]["reason"] == "quota_exceeded"
    
    def test_get_switch_summary(self):
        """测试获取切换摘要"""
        from clawteam.orchestrator.provider_selector import ProviderAutoSwitchManager
        
        manager = ProviderAutoSwitchManager("test-team")
        summary = manager.get_switch_summary()
        
        assert "totalSwitches" in summary
        assert "currentProvider" in summary
    
    def test_get_status_report(self):
        """测试获取状态报告"""
        from clawteam.orchestrator.provider_selector import ProviderAutoSwitchManager
        
        manager = ProviderAutoSwitchManager("test-team")
        report = manager.get_status_report()
        
        assert "teamName" in report
        assert "currentProvider" in report
        assert "selectorSummary" in report


# ==============================================================================
# P10: Git Worktree 管理测试
# ==============================================================================

class TestGitWorktreeService:
    """测试 Git Worktree 服务"""
    
    @pytest.fixture
    def mock_repo(self, tmp_path):
        """创建模拟 Git 仓库"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        
        # 初始化 Git 仓库
        os.system(f"cd {repo_path} && git init")
        os.system(f"cd {repo_path} && git config user.email 'test@test.com'")
        os.system(f"cd {repo_path} && git config user.name 'Test User'")
        os.system(f"cd {repo_path} && echo 'test' > test.txt && git add . && git commit -m 'init'")
        
        return repo_path
    
    def test_is_git_repo(self, mock_repo):
        """测试检查 Git 仓库"""
        from clawteam.workspace.worktree import GitWorktreeService
        
        service = GitWorktreeService(mock_repo)
        assert service.is_git_repo()
    
    def test_get_current_branch(self, mock_repo):
        """测试获取当前分支"""
        from clawteam.workspace.worktree import GitWorktreeService
        
        service = GitWorktreeService(mock_repo)
        branch = service.get_current_branch()
        # 默认分支可能是 master 或 main
        assert branch in ["master", "main"]
    
    def test_list_worktrees(self, mock_repo):
        """测试列出 worktrees"""
        from clawteam.workspace.worktree import GitWorktreeService
        
        service = GitWorktreeService(mock_repo)
        worktrees = service.list_worktrees()
        
        # 至少有一个主 worktree
        assert len(worktrees) >= 1
        assert any(wt.branch in ["master", "main"] for wt in worktrees)
    
    def test_slugify_branch(self, mock_repo):
        """测试分支名转换"""
        from clawteam.workspace.worktree import GitWorktreeService
        
        service = GitWorktreeService(mock_repo)
        
        # 测试各种输入
        result1 = service._slugify_branch("Test Feature")
        assert "task/" in result1
        assert "test-feature" in result1
        
        result2 = service._slugify_branch("123")
        assert "task/" in result2
    
    def test_get_summary(self, mock_repo):
        """测试获取摘要"""
        from clawteam.workspace.worktree import GitWorktreeService
        
        service = GitWorktreeService(mock_repo)
        summary = service.get_summary()
        
        assert "totalWorktrees" in summary
        assert "activeWorktrees" in summary


class TestWorktreeManager:
    """测试 Worktree 管理器"""
    
    @pytest.fixture
    def mock_repo(self, tmp_path):
        """创建模拟 Git 仓库"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        
        os.system(f"cd {repo_path} && git init")
        os.system(f"cd {repo_path} && git config user.email 'test@test.com'")
        os.system(f"cd {repo_path} && git config user.name 'Test User'")
        os.system(f"cd {repo_path} && echo 'test' > test.txt && git add . && git commit -m 'init'")
        
        return repo_path
    
    def test_init(self, mock_repo):
        """测试初始化"""
        from clawteam.workspace.worktree import WorktreeManager
        
        manager = WorktreeManager(mock_repo)
        assert manager.repo_path == mock_repo.resolve()
    
    def test_get_all_worktrees(self, mock_repo):
        """测试获取所有 worktrees"""
        from clawteam.workspace.worktree import WorktreeManager
        
        manager = WorktreeManager(mock_repo)
        worktrees = manager.get_all_worktrees()
        assert len(worktrees) >= 1
    
    def test_get_summary(self, mock_repo):
        """测试获取摘要"""
        from clawteam.workspace.worktree import WorktreeManager
        
        manager = WorktreeManager(mock_repo)
        summary = manager.get_summary()
        
        assert "totalWorktrees" in summary
        assert "registeredTasks" in summary


class TestWorktreeDataClasses:
    """测试 Worktree 数据类"""
    
    def test_worktree_info_to_dict(self):
        """测试 WorktreeInfo 序列化"""
        from clawteam.workspace.worktree import WorktreeInfo, WorktreeStatus
        
        info = WorktreeInfo(
            path="/test/path",
            branch="test-branch",
            head="abc123",
            status=WorktreeStatus.ACTIVE,
            task_id="task-1",
            agent_name="agent-1",
        )
        
        d = info.to_dict()
        assert d["path"] == "/test/path"
        assert d["branch"] == "test-branch"
        assert d["status"] == "active"
    
    def test_merge_check_result_to_dict(self):
        """测试 MergeCheckResult 序列化"""
        from clawteam.workspace.worktree import MergeCheckResult
        
        result = MergeCheckResult(
            can_merge=True,
            has_conflicts=False,
            ahead_by=5,
            behind_by=2,
        )
        
        d = result.to_dict()
        assert d["canMerge"]
        assert d["aheadBy"] == 5
    
    def test_merge_result_to_dict(self):
        """测试 MergeResult 序列化"""
        from clawteam.workspace.worktree import MergeResult
        
        result = MergeResult(
            success=True,
            message="Merge successful",
            commit_hash="abc123",
        )
        
        d = result.to_dict()
        assert d["success"]
        assert d["commitHash"] == "abc123"


# ==============================================================================
# P11: Token 统计测试
# ==============================================================================

class TestUsageEstimator:
    """测试 Token 用量估算器"""
    
    def test_estimate_tokens_ascii(self):
        """测试 ASCII 文本估算"""
        from clawteam.tracker.token_stats import UsageEstimator
        
        estimator = UsageEstimator()
        
        # 纯 ASCII 文本
        text = "Hello World"  # 11 字符
        tokens = estimator.estimate_tokens(text)
        # 11 / 4 + 1 = 3
        assert tokens >= 2
    
    def test_estimate_tokens_chinese(self):
        """测试中文文本估算"""
        from clawteam.tracker.token_stats import UsageEstimator
        
        estimator = UsageEstimator()
        
        # 中文文本
        text = "你好世界"  # 4 字符
        tokens = estimator.estimate_tokens(text)
        # 4 / 2 + 1 = 3
        assert tokens >= 2
    
    def test_accumulate_usage(self):
        """测试累加用量"""
        from clawteam.tracker.token_stats import UsageEstimator
        
        estimator = UsageEstimator()
        
        tokens = estimator.accumulate_usage("session-1", "Hello World", "claude")
        assert tokens > 0
        
        # 再次累加
        tokens2 = estimator.accumulate_usage("session-1", "Another text")
        assert tokens2 > 0
    
    def test_record_request(self):
        """测试记录请求"""
        from clawteam.tracker.token_stats import UsageEstimator
        
        estimator = UsageEstimator()
        
        total = estimator.record_request("session-2", 100, 50, "claude")
        assert total == 150
    
    def test_get_summary(self):
        """测试获取汇总"""
        from clawteam.tracker.token_stats import UsageEstimator
        
        estimator = UsageEstimator()
        estimator.accumulate_usage("session-1", "Test text", "claude")
        
        summary = estimator.get_summary()
        assert summary.total_tokens > 0
        assert summary.active_sessions >= 1
        assert "claude" in summary.provider_breakdown
    
    def test_get_trend(self):
        """测试获取趋势"""
        from clawteam.tracker.token_stats import UsageEstimator
        
        estimator = UsageEstimator()
        estimator.accumulate_usage("session-1", "Test text", "claude")
        
        trend = estimator.get_trend(7)
        assert len(trend.daily_data) == 7
        assert trend.avg_daily_tokens >= 0
    
    def test_get_provider_stats(self):
        """测试获取 Provider 统计"""
        from clawteam.tracker.token_stats import UsageEstimator
        
        estimator = UsageEstimator()
        estimator.accumulate_usage("session-1", "Test text", "claude")
        estimator.accumulate_usage("session-2", "Test text", "codex")
        
        stats = estimator.get_provider_stats()
        assert len(stats) >= 2
        assert any(s.provider == "claude" for s in stats)
    
    def test_mark_session_ended(self):
        """测试标记会话结束"""
        from clawteam.tracker.token_stats import UsageEstimator
        
        estimator = UsageEstimator()
        estimator.accumulate_usage("session-1", "Test text", "claude")
        
        estimator.mark_session_ended("session-1")
        
        # 会话应该被清理
        assert estimator.get_session_usage("session-1") == 0
    
    def test_get_web_ui_data(self):
        """测试获取 Web UI 数据"""
        from clawteam.tracker.token_stats import UsageEstimator
        
        estimator = UsageEstimator()
        estimator.accumulate_usage("session-1", "Test text", "claude")
        
        data = estimator.get_web_ui_data()
        assert "summary" in data
        assert "trend" in data
        assert "providerStats" in data


class TestTokenStatsDataClasses:
    """测试 Token 统计数据类"""
    
    def test_usage_summary_to_dict(self):
        """测试 UsageSummary 序列化"""
        from clawteam.tracker.token_stats import UsageSummary
        
        summary = UsageSummary(
            total_tokens=1000,
            total_minutes=30,
            today_tokens=500,
            today_minutes=15,
            active_sessions=2,
            session_breakdown={"s1": 300, "s2": 200},
            provider_breakdown={"claude": 500},
        )
        
        d = summary.to_dict()
        assert d["totalTokens"] == 1000
        assert d["activeSessions"] == 2
    
    def test_daily_usage_to_dict(self):
        """测试 DailyUsage 序列化"""
        from clawteam.tracker.token_stats import DailyUsage
        
        daily = DailyUsage(
            date="2024-01-01",
            tokens=1000,
            minutes=30,
            sessions=5,
            providers={"claude": 800},
        )
        
        d = daily.to_dict()
        assert d["date"] == "2024-01-01"
        assert d["tokens"] == 1000
    
    def test_trend_analysis_to_dict(self):
        """测试 TrendAnalysis 序列化"""
        from clawteam.tracker.token_stats import TrendAnalysis, DailyUsage
        
        trend = TrendAnalysis(
            daily_data=[DailyUsage(date="2024-01-01", tokens=100)],
            avg_daily_tokens=100,
            avg_daily_minutes=30,
            peak_day="2024-01-01",
            peak_tokens=100,
            growth_rate=10.5,
            prediction_next_day=110,
        )
        
        d = trend.to_dict()
        assert d["avgDailyTokens"] == 100
        assert d["growthRate"] == 10.5


class TestTokenStatsConvenienceFunctions:
    """测试便捷函数"""
    
    def test_get_usage_summary(self):
        """测试获取用量汇总"""
        from clawteam.tracker.token_stats import get_usage_summary
        
        summary = get_usage_summary()
        assert summary is not None
    
    def test_get_usage_trend(self):
        """测试获取趋势"""
        from clawteam.tracker.token_stats import get_usage_trend
        
        trend = get_usage_trend(7)
        assert trend is not None
        assert len(trend.daily_data) == 7
    
    def test_accumulate_usage(self):
        """测试累加用量"""
        from clawteam.tracker.token_stats import accumulate_usage
        
        tokens = accumulate_usage("test-session", "Test text", "claude")
        assert tokens > 0
    
    def test_record_request(self):
        """测试记录请求"""
        from clawteam.tracker.token_stats import record_request
        
        total = record_request("test-session", 100, 50, "claude")
        assert total == 150


# ==============================================================================
# 集成测试
# ==============================================================================

class TestP9P10P11Integration:
    """P9/P10/P11 集成测试"""
    
    def test_provider_capability_and_availability(self):
        """测试 Provider 能力和可用性集成"""
        from clawteam.orchestrator.provider_capability import ProviderCapabilityRegistry
        from clawteam.orchestrator.provider_availability import check_provider_availability
        
        # 获取能力
        cap = ProviderCapabilityRegistry.get("claude-code")
        
        # 检测可用性
        avail = check_provider_availability("claude-code")
        
        # 验证数据一致性
        assert cap.provider_id == avail.id
    
    def test_token_stats_with_provider(self):
        """测试 Token 统计与 Provider 集成"""
        from clawteam.tracker.token_stats import UsageEstimator
        
        estimator = UsageEstimator()
        
        # 模拟不同 Provider 的使用
        estimator.accumulate_usage("s1", "Claude text", "claude")
        estimator.accumulate_usage("s2", "Codex text", "codex")
        
        # 获取 Provider 统计
        stats = estimator.get_provider_stats()
        
        # 验证统计正确
        assert len(stats) >= 2
        total_tokens = sum(s.total_tokens for s in stats)
        assert total_tokens > 0
    
    def test_full_workflow(self):
        """测试完整工作流"""
        from clawteam.orchestrator.provider_selector import ProviderAutoSwitchManager, TaskType
        from clawteam.tracker.token_stats import UsageEstimator
        
        # 初始化
        manager = ProviderAutoSwitchManager("test-team")
        estimator = UsageEstimator()
        
        # 选择 Provider
        result = manager.select_provider(TaskType.code_generation)
        
        # 记录使用
        if result.success:
            estimator.accumulate_usage(
                "test-session",
                "Generated code",
                result.provider_name,
            )
        
        # 获取统计
        summary = estimator.get_summary()
        provider_stats = estimator.get_provider_stats()
        
        # 验证
        assert summary is not None
        assert provider_stats is not None