"""Git Worktree manager for ClawTeam.

Provides isolated Git worktrees for concurrent tasks, enabling parallel
development without conflicts.
"""

import asyncio
import json
import subprocess
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from ..team.models import get_data_dir
from ..utils.logger import get_logger

logger = get_logger(__name__)


class WorktreeStatus(str, Enum):
    """Worktree status."""

    ACTIVE = "active"
    STALE = "stale"
    MERGED = "merged"
    ABANDONED = "abandoned"


class WorktreeInfo(BaseModel):
    """Worktree metadata."""

    worktree_id: str
    branch_name: str
    path: str
    base_branch: str = "main"
    created_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    status: WorktreeStatus = WorktreeStatus.ACTIVE
    associated_task: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GitCommandError(Exception):
    """Git command execution error."""

    def __init__(self, command: str, returncode: int, stderr: str):
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"Git command '{command}' failed with code {returncode}: {stderr}")


class WorktreeManager:
    """Git Worktree manager."""

    def __init__(self, repo_path: Optional[str] = None):
        """
        Initialize worktree manager.

        Args:
            repo_path: Optional repository path. If not provided, uses current directory.
        """
        if repo_path:
            self.repo_path = Path(repo_path).absolute()
        else:
            # Try to find git root
            try:
                result = subprocess.run(
                    ["git", "rev-parse", "--show-toplevel"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                self.repo_path = Path(result.stdout.strip()).absolute()
            except subprocess.CalledProcessError:
                raise ValueError("Could not find git repository. Please provide repo_path.")

        self.worktrees_dir = get_data_dir() / "worktrees"
        self.worktrees_dir.mkdir(parents=True, exist_ok=True)

        self._metadata_file = self.worktrees_dir / "worktrees.json"
        self._load_metadata()

    def _load_metadata(self) -> None:
        """Load worktree metadata from file."""
        if self._metadata_file.exists():
            try:
                with open(self._metadata_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._worktrees = [WorktreeInfo(**item) for item in data.get("worktrees", [])]
            except (json.JSONDecodeError, Exception) as e:
                logger.warning("Failed to load worktree metadata: %s", e)
                self._worktrees = []
        else:
            self._worktrees = []

    def _save_metadata(self) -> None:
        """Save worktree metadata to file."""
        data = {
            "worktrees": [wt.model_dump() for wt in self._worktrees],
            "updated_at": datetime.now().isoformat(),
        }
        try:
            with open(self._metadata_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error("Failed to save worktree metadata: %s", e)

    def _run_git(self, args: List[str], cwd: Optional[Path] = None) -> Tuple[int, str, str]:
        """Run git command."""
        cmd = ["git"] + args
        cwd_path = cwd or self.repo_path
        logger.debug("Running git command: %s in %s", cmd, cwd_path)

        try:
            result = subprocess.run(
                cmd,
                cwd=cwd_path,
                capture_output=True,
                text=True,
                check=False,
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except Exception as e:
            raise GitCommandError(" ".join(cmd), -1, str(e))

    def _get_worktree_by_id(self, worktree_id: str) -> Optional[WorktreeInfo]:
        """Get worktree by ID."""
        for wt in self._worktrees:
            if wt.worktree_id == worktree_id:
                return wt
        return None

    def _update_worktree_activity(self, worktree_id: str) -> None:
        """Update worktree last activity timestamp."""
        wt = self._get_worktree_by_id(worktree_id)
        if wt:
            wt.last_activity = datetime.now()
            self._save_metadata()

    def create_worktree(
        self,
        task_id: str,
        base_branch: str = "main",
        branch_name: Optional[str] = None,
    ) -> WorktreeInfo:
        """
        Create worktree for a task.

        Args:
            task_id: Task identifier.
            base_branch: Base branch to create worktree from.
            branch_name: Optional branch name. If not provided, generates one.

        Returns:
            WorktreeInfo instance.
        """
        if branch_name is None:
            branch_name = f"task-{task_id}-{uuid.uuid4().hex[:8]}"

        # Generate unique worktree ID
        worktree_id = f"wt-{uuid.uuid4().hex[:8]}"

        # Create worktree directory
        worktree_dir = self.worktrees_dir / worktree_id

        # Create worktree
        returncode, stdout, stderr = self._run_git(
            [
                "worktree",
                "add",
                "--detach",
                str(worktree_dir),
                base_branch,
            ]
        )
        if returncode != 0:
            raise GitCommandError("git worktree add", returncode, stderr)

        # Checkout branch
        returncode, stdout, stderr = self._run_git(
            ["checkout", "-b", branch_name], cwd=worktree_dir
        )
        if returncode != 0:
            # Clean up worktree if checkout fails
            self._run_git(["worktree", "remove", "--force", str(worktree_dir)])
            raise GitCommandError("git checkout", returncode, stderr)

        # Create worktree info
        worktree_info = WorktreeInfo(
            worktree_id=worktree_id,
            branch_name=branch_name,
            path=str(worktree_dir),
            base_branch=base_branch,
            associated_task=task_id,
            metadata={"created_for_task": task_id},
        )

        self._worktrees.append(worktree_info)
        self._save_metadata()

        logger.info(
            "Created worktree %s for task %s at %s",
            worktree_id,
            task_id,
            worktree_dir,
        )
        return worktree_info

    def list_worktrees(self, status_filter: Optional[WorktreeStatus] = None) -> List[WorktreeInfo]:
        """
        List worktrees.

        Args:
            status_filter: Optional status filter.

        Returns:
            List of worktree info.
        """
        worktrees = self._worktrees

        # Update status based on actual existence
        for wt in worktrees:
            wt_path = Path(wt.path)
            if not wt_path.exists():
                wt.status = WorktreeStatus.ABANDONED
            elif wt.status == WorktreeStatus.ACTIVE:
                # Check if branch still exists
                returncode, stdout, stderr = self._run_git(["branch", "--list", wt.branch_name])
                if returncode == 0 and wt.branch_name not in stdout:
                    wt.status = WorktreeStatus.MERGED

        self._save_metadata()

        if status_filter:
            worktrees = [wt for wt in worktrees if wt.status == status_filter]

        return worktrees

    def get_worktree_status(self, worktree_id: str) -> Dict[str, Any]:
        """
        Get detailed worktree status.

        Args:
            worktree_id: Worktree ID.

        Returns:
            Status dictionary.
        """
        wt = self._get_worktree_by_id(worktree_id)
        if not wt:
            raise ValueError(f"Worktree {worktree_id} not found")

        wt_path = Path(wt.path)

        status = {
            "worktree_id": worktree_id,
            "exists": wt_path.exists(),
            "branch_exists": False,
            "has_uncommitted_changes": False,
            "ahead_of_base": 0,
            "behind_base": 0,
        }

        if wt_path.exists():
            # Check branch existence
            returncode, stdout, stderr = self._run_git(
                ["branch", "--list", wt.branch_name], cwd=wt_path
            )
            status["branch_exists"] = returncode == 0 and wt.branch_name in stdout

            # Check uncommitted changes
            returncode, stdout, stderr = self._run_git(["status", "--porcelain"], cwd=wt_path)
            status["has_uncommitted_changes"] = len(stdout.strip()) > 0

            # Check ahead/behind base branch
            returncode, stdout, stderr = self._run_git(
                ["rev-list", "--count", f"{wt.branch_name}..{wt.base_branch}"],
                cwd=wt_path,
            )
            if returncode == 0:
                status["behind_base"] = int(stdout.strip()) if stdout else 0

            returncode, stdout, stderr = self._run_git(
                ["rev-list", "--count", f"{wt.base_branch}..{wt.branch_name}"],
                cwd=wt_path,
            )
            if returncode == 0:
                status["ahead_of_base"] = int(stdout.strip()) if stdout else 0

        return status

    def merge_worktree(
        self,
        worktree_id: str,
        target_branch: str = "main",
        strategy: str = "merge",
    ) -> Dict[str, Any]:
        """
        Merge worktree content to target branch.

        Args:
            worktree_id: Worktree ID.
            target_branch: Target branch.
            strategy: Merge strategy ("merge" or "rebase").

        Returns:
            Merge result.
        """
        wt = self._get_worktree_by_id(worktree_id)
        if not wt:
            raise ValueError(f"Worktree {worktree_id} not found")

        wt_path = Path(wt.path)
        if not wt_path.exists():
            raise ValueError(f"Worktree path {wt_path} does not exist")

        result: Dict[str, Any] = {
            "worktree_id": worktree_id,
            "merged": False,
            "conflicts": [],
            "merged_commits": [],
        }

        # Fetch latest from origin
        self._run_git(["fetch", "origin", target_branch])

        # Checkout target branch in main worktree
        returncode, stdout, stderr = self._run_git(["checkout", target_branch])
        if returncode != 0:
            result["error"] = f"Failed to checkout {target_branch}: {stderr}"
            return result

        # Merge or rebase
        if strategy == "merge":
            returncode, stdout, stderr = self._run_git(["merge", "--no-ff", wt.branch_name])
        else:  # rebase
            returncode, stdout, stderr = self._run_git(["rebase", wt.branch_name])

        if returncode != 0:
            result["error"] = f"Merge failed: {stderr}"
            result["conflicts"] = self.detect_conflicts(worktree_id)
        else:
            result["merged"] = True
            wt.status = WorktreeStatus.MERGED
            self._save_metadata()

            # Get merged commits
            returncode, stdout, stderr = self._run_git(
                ["log", f"{target_branch}..{wt.branch_name}", "--oneline"]
            )
            if returncode == 0:
                result["merged_commits"] = [
                    line.strip() for line in stdout.split("\n") if line.strip()
                ]

        return result

    def detect_conflicts(self, worktree_id: str) -> List[Dict[str, Any]]:
        """
        Detect merge conflicts.

        Args:
            worktree_id: Worktree ID.

        Returns:
            List of conflict information.
        """
        wt = self._get_worktree_by_id(worktree_id)
        if not wt:
            return []

        wt_path = Path(wt.path)
        if not wt_path.exists():
            return []

        returncode, stdout, stderr = self._run_git(["status", "--porcelain"], cwd=wt_path)
        if returncode != 0:
            return []

        conflicts = []
        for line in stdout.split("\n"):
            line = line.strip()
            if line.startswith("UU ") or line.startswith("AA "):
                conflicts.append(
                    {
                        "file": line[3:].strip(),
                        "status": "conflict",
                    }
                )

        return conflicts

    def cleanup_worktrees(self, max_age_hours: int = 168, auto_merge: bool = False) -> List[str]:
        """
        Clean up stale worktrees.

        Args:
            max_age_hours: Maximum age in hours (default 168 = 7 days).
            auto_merge: Whether to auto-merge before cleanup.

        Returns:
            List of cleaned worktree IDs.
        """
        cleaned = []
        now = datetime.now()

        for wt in self._worktrees[:]:  # Copy for safe iteration
            if wt.status == WorktreeStatus.MERGED:
                # Already merged, can remove
                pass
            elif wt.status == WorktreeStatus.ABANDONED:
                # Already abandoned
                pass
            else:
                # Check age
                age_hours = (now - wt.last_activity).total_seconds() / 3600
                if age_hours > max_age_hours:
                    wt.status = WorktreeStatus.STALE

            # Clean up stale/abandoned/merged worktrees
            if wt.status in (
                WorktreeStatus.STALE,
                WorktreeStatus.ABANDONED,
                WorktreeStatus.MERGED,
            ):
                wt_path = Path(wt.path)
                if wt_path.exists():
                    if auto_merge and wt.status == WorktreeStatus.STALE:
                        try:
                            self.merge_worktree(wt.worktree_id)
                        except Exception as e:
                            logger.warning(
                                "Failed to auto-merge worktree %s: %s",
                                wt.worktree_id,
                                e,
                            )

                    # Remove worktree
                    returncode, stdout, stderr = self._run_git(
                        ["worktree", "remove", "--force", str(wt_path)]
                    )
                    if returncode == 0:
                        cleaned.append(wt.worktree_id)
                        self._worktrees.remove(wt)

        self._save_metadata()
        return cleaned

    def remove_worktree(self, worktree_id: str, force: bool = False) -> bool:
        """
        Remove worktree.

        Args:
            worktree_id: Worktree ID.
            force: Force removal even with uncommitted changes.

        Returns:
            True if removed successfully.
        """
        wt = self._get_worktree_by_id(worktree_id)
        if not wt:
            return False

        wt_path = Path(wt.path)
        if not wt_path.exists():
            self._worktrees.remove(wt)
            self._save_metadata()
            return True

        args = ["worktree", "remove"]
        if force:
            args.append("--force")
        args.append(str(wt_path))

        returncode, stdout, stderr = self._run_git(args)
        if returncode == 0:
            self._worktrees.remove(wt)
            self._save_metadata()
            return True
        else:
            return False
