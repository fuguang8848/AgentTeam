"""Tests for GitWorktree module (P10)."""

import os
import tempfile
from pathlib import Path

import pytest

from agentteam.workspace.worktree import (
    GitError,
    GitWorktreeService,
    MergeCheckResult,
    MergeResult,
    WorktreeDiffFile,
    WorktreeDiffSummary,
    WorktreeInfo,
    WorktreeLock,
    WorktreeManager,
    WorktreeStatus,
    get_worktree_manager,
)


class TestWorktreeStatus:
    """Tests for WorktreeStatus enum."""

    def test_all_statuses(self):
        """Test all status values."""
        assert WorktreeStatus.ACTIVE.value == "active"
        assert WorktreeStatus.MERGED.value == "merged"
        assert WorktreeStatus.ABANDONED.value == "abandoned"

    def test_status_from_string(self):
        """Test creating status from string."""
        status = WorktreeStatus("active")
        assert status == WorktreeStatus.ACTIVE


class TestWorktreeInfo:
    """Tests for WorktreeInfo dataclass."""

    def test_info_creation(self):
        """Test creating worktree info."""
        info = WorktreeInfo(
            path="/tmp/worktree",
            branch="feature-branch",
        )
        assert info.path == "/tmp/worktree"
        assert info.branch == "feature-branch"
        assert info.status == WorktreeStatus.ACTIVE

    def test_info_with_head(self):
        """Test info with head commit."""
        info = WorktreeInfo(
            path="/tmp/worktree",
            branch="feature-branch",
            head="abc123",
        )
        assert info.head == "abc123"

    def test_info_with_task(self):
        """Test info with task ID."""
        info = WorktreeInfo(
            path="/tmp/worktree",
            branch="feature-branch",
            task_id="task-123",
        )
        assert info.task_id == "task-123"

    def test_info_with_agent(self):
        """Test info with agent name."""
        info = WorktreeInfo(
            path="/tmp/worktree",
            branch="feature-branch",
            agent_name="test-agent",
        )
        assert info.agent_name == "test-agent"

    def test_info_to_dict(self):
        """Test info serialization."""
        info = WorktreeInfo(
            path="/tmp/worktree",
            branch="feature-branch",
            head="abc123",
        )
        d = info.to_dict()
        assert d["path"] == "/tmp/worktree"
        assert d["branch"] == "feature-branch"
        assert d["head"] == "abc123"


class TestMergeCheckResult:
    """Tests for MergeCheckResult dataclass."""

    def test_result_can_merge(self):
        """Test result can merge."""
        result = MergeCheckResult(can_merge=True)
        assert result.can_merge is True

    def test_result_has_conflicts(self):
        """Test result has conflicts."""
        result = MergeCheckResult(
            can_merge=False,
            has_conflicts=True,
            conflict_files=["file1.txt", "file2.txt"],
        )
        assert result.has_conflicts is True
        assert len(result.conflict_files) == 2

    def test_result_ahead_behind(self):
        """Test result ahead/behind counts."""
        result = MergeCheckResult(
            can_merge=True,
            ahead_by=5,
            behind_by=2,
        )
        assert result.ahead_by == 5
        assert result.behind_by == 2

    def test_result_with_error(self):
        """Test result with error."""
        result = MergeCheckResult(
            can_merge=False,
            error="Merge failed",
        )
        assert result.error == "Merge failed"

    def test_result_to_dict(self):
        """Test result serialization."""
        result = MergeCheckResult(
            can_merge=True,
            ahead_by=5,
            behind_by=2,
        )
        d = result.to_dict()
        assert d["canMerge"] is True
        assert d["aheadBy"] == 5


class TestMergeResult:
    """Tests for MergeResult dataclass."""

    def test_result_success(self):
        """Test successful merge."""
        result = MergeResult(
            success=True,
            message="Merge completed",
            commit_hash="abc123",
        )
        assert result.success is True
        assert result.message == "Merge completed"
        assert result.commit_hash == "abc123"

    def test_result_failure(self):
        """Test failed merge."""
        result = MergeResult(
            success=False,
            error="Conflict detected",
        )
        assert result.success is False
        assert result.error == "Conflict detected"

    def test_result_to_dict(self):
        """Test result serialization."""
        result = MergeResult(
            success=True,
            commit_hash="abc123",
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["commitHash"] == "abc123"


class TestWorktreeDiffFile:
    """Tests for WorktreeDiffFile dataclass."""

    def test_diff_file_creation(self):
        """Test creating diff file."""
        diff = WorktreeDiffFile(
            path="src/main.py",
            status="M",
        )
        assert diff.path == "src/main.py"
        assert diff.status == "M"

    def test_diff_file_additions(self):
        """Test diff file additions."""
        diff = WorktreeDiffFile(
            path="src/main.py",
            status="M",
            additions=10,
        )
        assert diff.additions == 10

    def test_diff_file_deletions(self):
        """Test diff file deletions."""
        diff = WorktreeDiffFile(
            path="src/main.py",
            status="M",
            deletions=5,
        )
        assert diff.deletions == 5

    def test_diff_file_status_types(self):
        """Test diff file status types."""
        statuses = ["A", "M", "D", "R"]
        for status in statuses:
            diff = WorktreeDiffFile(path="test.txt", status=status)
            assert diff.status == status

    def test_diff_file_to_dict(self):
        """Test diff file serialization."""
        diff = WorktreeDiffFile(
            path="src/main.py",
            status="M",
            additions=10,
            deletions=5,
        )
        d = diff.to_dict()
        assert d["path"] == "src/main.py"
        assert d["additions"] == 10


class TestWorktreeDiffSummary:
    """Tests for WorktreeDiffSummary dataclass."""

    def test_summary_creation(self):
        """Test creating diff summary."""
        summary = WorktreeDiffSummary()
        assert len(summary.files) == 0
        assert summary.total_additions == 0

    def test_summary_with_files(self):
        """Test summary with files."""
        files = [
            WorktreeDiffFile(path="f1.txt", status="M", additions=10),
            WorktreeDiffFile(path="f2.txt", status="A", additions=5),
        ]
        summary = WorktreeDiffSummary(files=files)
        assert len(summary.files) == 2

    def test_summary_totals(self):
        """Test summary totals."""
        files = [
            WorktreeDiffFile(path="f1.txt", status="M", additions=10, deletions=2),
            WorktreeDiffFile(path="f2.txt", status="A", additions=5, deletions=0),
        ]
        summary = WorktreeDiffSummary(
            files=files,
            total_additions=15,
            total_deletions=2,
        )
        assert summary.total_additions == 15
        assert summary.total_deletions == 2

    def test_summary_to_dict(self):
        """Test summary serialization."""
        summary = WorktreeDiffSummary(
            files=[WorktreeDiffFile(path="test.txt", status="M")],
            file_count=1,
        )
        d = summary.to_dict()
        assert d["fileCount"] == 1


class TestGitError:
    """Tests for GitError exception."""

    def test_error_creation(self):
        """Test creating Git error."""
        error = GitError("Command failed")
        assert str(error) == "Command failed"

    def test_error_inheritance(self):
        """Test error inheritance."""
        error = GitError("Test")
        assert isinstance(error, Exception)


class TestWorktreeLock:
    """Tests for WorktreeLock class."""

    def test_lock_initialization(self):
        """Test lock initialization."""
        lock = WorktreeLock()
        assert len(lock._locks) == 0

    def test_lock_get_lock(self):
        """Test getting lock for repo."""
        lock = WorktreeLock()
        repo_lock = lock._get_lock("/tmp/repo")
        assert repo_lock is not None
        assert "/tmp/repo" in lock._locks

    def test_lock_same_repo_same_lock(self):
        """Test same repo gets same lock."""
        lock = WorktreeLock()
        lock1 = lock._get_lock("/tmp/repo")
        lock2 = lock._get_lock("/tmp/repo")
        assert lock1 is lock2

    def test_lock_different_repos_different_locks(self):
        """Test different repos get different locks."""
        lock = WorktreeLock()
        lock1 = lock._get_lock("/tmp/repo1")
        lock2 = lock._get_lock("/tmp/repo2")
        assert lock1 is not lock2

    def test_lock_execute(self):
        """Test executing function in lock."""
        lock = WorktreeLock()
        result = lock.execute("/tmp/repo", lambda: 42)
        assert result == 42


class TestGitWorktreeService:
    """Tests for GitWorktreeService class."""

    def test_service_initialization(self):
        """Test service initialization."""
        service = GitWorktreeService(".")
        assert service.repo_path is not None

    def test_service_list_worktrees(self):
        """Test listing worktrees."""
        service = GitWorktreeService(".")
        worktrees = service.list_worktrees()
        assert isinstance(worktrees, list)
        # Main worktree should be included
        assert len(worktrees) >= 1

    def test_service_get_summary(self):
        """Test getting summary."""
        service = GitWorktreeService(".")
        summary = service.get_summary()
        assert "totalWorktrees" in summary
        assert "activeWorktrees" in summary

    def test_service_is_git_repo(self):
        """Test checking if git repo."""
        service = GitWorktreeService(".")
        # Current directory should be a git repo
        assert service.is_git_repo() is True

    def test_service_not_git_repo(self):
        """Test checking non-git repo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = GitWorktreeService(tmpdir)
            assert service.is_git_repo() is False

    def test_service_get_current_branch(self):
        """Test getting current branch."""
        service = GitWorktreeService(".")
        branch = service.get_current_branch()
        assert branch is not None

    def test_service_get_head_commit(self):
        """Test getting head commit."""
        service = GitWorktreeService(".")
        head = service.get_head_commit()
        assert head is not None

    def test_service_get_status(self):
        """Test getting status."""
        service = GitWorktreeService(".")
        status = service.get_status()
        assert status is not None

    def test_service_is_dirty(self):
        """Test checking if dirty."""
        service = GitWorktreeService(".")
        dirty = service.is_dirty()
        assert isinstance(dirty, bool)

    def test_service_prune_worktrees(self):
        """Test pruning worktrees."""
        service = GitWorktreeService(".")
        pruned = service.prune_worktrees()
        assert isinstance(pruned, list)


class TestWorktreeManager:
    """Tests for WorktreeManager class."""

    def test_manager_initialization(self):
        """Test manager initialization."""
        manager = WorktreeManager(".")
        assert manager.repo_path is not None
        assert manager.service is not None

    def test_manager_get_all_worktrees(self):
        """Test getting all worktrees."""
        manager = WorktreeManager(".")
        worktrees = manager.get_all_worktrees()
        assert isinstance(worktrees, list)

    def test_manager_get_active_worktrees(self):
        """Test getting active worktrees."""
        manager = WorktreeManager(".")
        worktrees = manager.get_active_worktrees()
        assert isinstance(worktrees, list)
        for wt in worktrees:
            assert wt.status == WorktreeStatus.ACTIVE

    def test_manager_get_summary(self):
        """Test getting manager summary."""
        manager = WorktreeManager(".")
        summary = manager.get_summary()
        assert "totalWorktrees" in summary

    def test_manager_cleanup_abandoned(self):
        """Test cleaning up abandoned worktrees."""
        manager = WorktreeManager(".")
        cleaned = manager.cleanup_abandoned()
        assert isinstance(cleaned, list)


class TestGetWorktreeManager:
    """Tests for get_worktree_manager factory."""

    def test_factory_returns_manager(self):
        """Test factory returns manager."""
        manager = get_worktree_manager(".")
        assert manager is not None
        assert isinstance(manager, WorktreeManager)


class TestWorktreeEdgeCases:
    """Edge case tests for Worktree."""

    def test_service_with_nonexistent_repo(self):
        """Test service with nonexistent repo."""
        service = GitWorktreeService("/nonexistent/repo")
        # Should handle gracefully
        assert service.repo_path is not None

    def test_manager_with_path_string(self):
        """Test manager with path string."""
        manager = WorktreeManager(".")
        assert manager.repo_path is not None

    def test_manager_with_path_object(self):
        """Test manager with Path object."""
        manager = WorktreeManager(Path("."))
        assert manager.repo_path is not None

    def test_worktree_info_empty_branch(self):
        """Test worktree info with empty branch."""
        info = WorktreeInfo(path="/tmp/worktree", branch="")
        assert info.branch == ""

    def test_merge_check_result_empty_conflicts(self):
        """Test merge check with empty conflicts."""
        result = MergeCheckResult(can_merge=True, conflict_files=[])
        assert len(result.conflict_files) == 0

    def test_diff_summary_empty_files(self):
        """Test diff summary with empty files."""
        summary = WorktreeDiffSummary(files=[])
        assert len(summary.files) == 0


class TestWorktreeIntegration:
    """Integration tests for Worktree."""

    def test_service_and_manager_consistency(self):
        """Test service and manager consistency."""
        service = GitWorktreeService(".")
        manager = WorktreeManager(".")
        
        service_worktrees = service.list_worktrees()
        manager_worktrees = manager.get_all_worktrees()
        
        # Should have same count
        assert len(service_worktrees) == len(manager_worktrees)

    def test_get_repo_root(self):
        """Test getting repo root."""
        service = GitWorktreeService(".")
        root = service.get_repo_root()
        assert root is not None