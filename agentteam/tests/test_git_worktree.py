"""Tests for Git worktree module."""

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from agentteam.git import WorktreeManager, WorktreeInfo, WorktreeStatus, GitCommandError


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository for testing."""
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir) / "test-repo"
        repo_path.mkdir()

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
        )

        # Create initial file and commit
        (repo_path / "README.md").write_text("# Test Repo")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            check=True,
        )

        # Check current branch name and rename to main if needed
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        current_branch = result.stdout.strip()
        if current_branch == "master":
            # Rename to main for consistency
            subprocess.run(
                ["git", "branch", "-m", "main"],
                cwd=repo_path,
                check=True,
            )

        yield repo_path


@pytest.fixture
def worktree_manager(temp_git_repo):
    """Create a WorktreeManager instance."""
    return WorktreeManager(repo_path=str(temp_git_repo))


class TestWorktreeInfo:
    """Test WorktreeInfo model."""

    def test_worktree_info_creation(self):
        """Test creating WorktreeInfo."""
        info = WorktreeInfo(
            worktree_id="test-123",
            branch_name="feature-test",
            path="/tmp/test",
            base_branch="main",
        )
        assert info.worktree_id == "test-123"
        assert info.branch_name == "feature-test"
        assert info.path == "/tmp/test"
        assert info.base_branch == "main"
        assert info.status == WorktreeStatus.ACTIVE
        assert info.associated_task is None

    def test_worktree_info_with_task(self):
        """Test WorktreeInfo with associated task."""
        info = WorktreeInfo(
            worktree_id="test-456",
            branch_name="feature-task",
            path="/tmp/test2",
            associated_task="task-789",
        )
        assert info.associated_task == "task-789"


class TestWorktreeManager:
    """Test WorktreeManager."""

    def test_init_without_repo_path(self, monkeypatch):
        """Test initialization without repo path."""
        # Mock git root detection
        mock_run = MagicMock()
        mock_run.returncode = 0
        mock_run.stdout = "/fake/repo\n"

        monkeypatch.setattr(
            "agentteam.git.worktree.subprocess.run",
            lambda *args, **kwargs: mock_run,
        )

        manager = WorktreeManager()
        assert manager.repo_path == Path("/fake/repo").absolute()

    def test_init_with_invalid_repo(self):
        """Test initialization with invalid repository.

        Note: WorktreeManager only validates when repo_path is NOT provided.
        When repo_path IS provided, it accepts the path without git validation.
        This test verifies that behavior.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Should NOT raise — WorktreeManager accepts any path when repo_path is provided
            manager = WorktreeManager(repo_path=tmpdir)
            assert manager.repo_path == Path(tmpdir).absolute()
            # Clean up
            manager = None

    def test_create_worktree(self, worktree_manager):
        """Test creating a worktree."""
        info = worktree_manager.create_worktree(
            task_id="test-task-1",
            base_branch="main",
            branch_name="test-branch-1",
        )

        assert info.worktree_id.startswith("wt-")
        assert info.branch_name == "test-branch-1"
        assert info.base_branch == "main"
        assert info.associated_task == "test-task-1"
        assert info.status == WorktreeStatus.ACTIVE

        # Verify worktree directory exists
        worktree_path = Path(info.path)
        assert worktree_path.exists()
        assert (worktree_path / "README.md").exists()

        # Verify branch exists
        import subprocess

        result = subprocess.run(
            ["git", "branch", "--list", "test-branch-1"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
        )
        assert "test-branch-1" in result.stdout

    def test_create_worktree_auto_branch_name(self, worktree_manager):
        """Test creating worktree with auto-generated branch name."""
        info = worktree_manager.create_worktree(task_id="test-task-2")

        assert info.branch_name.startswith("task-test-task-2-")
        assert info.associated_task == "test-task-2"

    def test_list_worktrees(self, worktree_manager):
        """Test listing worktrees."""
        # Create multiple worktrees
        info1 = worktree_manager.create_worktree(task_id="task-1", branch_name="branch-1")
        info2 = worktree_manager.create_worktree(task_id="task-2", branch_name="branch-2")

        worktrees = worktree_manager.list_worktrees()
        assert len(worktrees) >= 2

        worktree_ids = {wt.worktree_id for wt in worktrees}
        assert info1.worktree_id in worktree_ids
        assert info2.worktree_id in worktree_ids

    def test_list_worktrees_with_filter(self, worktree_manager):
        """Test listing worktrees with status filter."""
        info = worktree_manager.create_worktree(task_id="task-filter", branch_name="branch-filter")

        # Should appear in active filter
        active = worktree_manager.list_worktrees(WorktreeStatus.ACTIVE)
        active_ids = {wt.worktree_id for wt in active}
        assert info.worktree_id in active_ids

        # Should not appear in merged filter
        merged = worktree_manager.list_worktrees(WorktreeStatus.MERGED)
        merged_ids = {wt.worktree_id for wt in merged}
        assert info.worktree_id not in merged_ids

    def test_get_worktree_status(self, worktree_manager):
        """Test getting worktree status."""
        info = worktree_manager.create_worktree(task_id="task-status", branch_name="branch-status")

        status = worktree_manager.get_worktree_status(info.worktree_id)
        assert status["worktree_id"] == info.worktree_id
        assert status["exists"] is True
        assert status["branch_exists"] is True
        assert status["has_uncommitted_changes"] is False

    def test_get_worktree_status_nonexistent(self, worktree_manager):
        """Test getting status for non-existent worktree."""
        with pytest.raises(ValueError):
            worktree_manager.get_worktree_status("non-existent-id")

    def test_remove_worktree(self, worktree_manager):
        """Test removing a worktree."""
        info = worktree_manager.create_worktree(task_id="task-remove", branch_name="branch-remove")

        # Verify worktree exists
        assert Path(info.path).exists()

        # Remove worktree
        result = worktree_manager.remove_worktree(info.worktree_id)
        assert result is True

        # Verify worktree is gone
        assert not Path(info.path).exists()

        # Verify removed from list
        worktrees = worktree_manager.list_worktrees()
        worktree_ids = {wt.worktree_id for wt in worktrees}
        assert info.worktree_id not in worktree_ids

    def test_remove_nonexistent_worktree(self, worktree_manager):
        """Test removing non-existent worktree."""
        result = worktree_manager.remove_worktree("non-existent-id")
        assert result is False

    @patch("agentteam.git.worktree.subprocess.run")
    def test_merge_worktree_success(self, mock_run, worktree_manager):
        """Test merging worktree successfully."""
        # Mock git commands
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        with tempfile.TemporaryDirectory() as tmpdir:
            info = WorktreeInfo(
                worktree_id="test-merge",
                branch_name="branch-merge",
                path=tmpdir,
                base_branch="main",
            )
            worktree_manager._worktrees = [info]

            result = worktree_manager.merge_worktree("test-merge", target_branch="main", strategy="merge")
            assert result["merged"] is True
            assert result["worktree_id"] == "test-merge"

    @patch("agentteam.git.worktree.subprocess.run")
    def test_merge_worktree_failure(self, mock_run, worktree_manager):
        """Test merging worktree with conflict."""
        # Mock git command to fail
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Merge conflict"
        mock_run.return_value = mock_result

        with tempfile.TemporaryDirectory() as tmpdir:
            info = WorktreeInfo(
                worktree_id="test-merge-fail",
                branch_name="branch-merge-fail",
                path=tmpdir,
                base_branch="main",
            )
            worktree_manager._worktrees = [info]

            result = worktree_manager.merge_worktree("test-merge-fail")
            assert result["merged"] is False
            assert "error" in result
            assert "Merge conflict" in result["error"]

    def test_detect_conflicts(self, worktree_manager):
        """Test detecting conflicts."""
        # Create a worktree
        info = worktree_manager.create_worktree(task_id="task-conflict", branch_name="branch-conflict")

        # No conflicts initially
        conflicts = worktree_manager.detect_conflicts(info.worktree_id)
        assert conflicts == []

    def test_cleanup_worktrees(self, worktree_manager):
        """Test cleaning up worktrees."""
        # Create worktree
        info = worktree_manager.create_worktree(task_id="task-cleanup", branch_name="branch-cleanup")

        # Mark as stale
        info.status = WorktreeStatus.STALE
        worktree_manager._save_metadata()

        # Clean up
        cleaned = worktree_manager.cleanup_worktrees(max_age_hours=0)
        assert info.worktree_id in cleaned

        # Verify removed
        worktrees = worktree_manager.list_worktrees()
        worktree_ids = {wt.worktree_id for wt in worktrees}
        assert info.worktree_id not in worktree_ids

    def test_update_worktree_activity(self, worktree_manager):
        """Test updating worktree activity."""
        import time
        from datetime import datetime

        info = worktree_manager.create_worktree(task_id="task-activity", branch_name="branch-activity")

        original_activity = info.last_activity
        time.sleep(0.01)

        worktree_manager._update_worktree_activity(info.worktree_id)
        worktree_manager._load_metadata()  # Reload

        updated_info = worktree_manager._get_worktree_by_id(info.worktree_id)
        assert updated_info is not None
        assert updated_info.last_activity > original_activity

    def test_git_command_error(self):
        """Test GitCommandError."""
        error = GitCommandError(
            command="git test",
            returncode=128,
            stderr="fatal: not a git repository",
        )
        assert "git test" in str(error)
        assert "128" in str(error)
        assert "not a git repository" in str(error)
