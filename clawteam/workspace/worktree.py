"""Git Worktree Service — 管理 worktree 的增删查改 & 分支合并

所有 git 操作通过链锁串行化，防止竞态条件。
参考 SpectrAI GitWorktreeService.ts 实现。

@author ClawTeam
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class WorktreeStatus(str, Enum):
    """Worktree 状态"""
    ACTIVE = "active"
    MERGED = "merged"
    ABANDONED = "abandoned"


@dataclass
class WorktreeInfo:
    """Worktree 信息"""
    path: str
    branch: str
    head: str = ""
    status: WorktreeStatus = WorktreeStatus.ACTIVE
    created_at: str = ""
    task_id: str = ""
    agent_name: str = ""
    
    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "branch": self.branch,
            "head": self.head,
            "status": self.status.value,
            "created_at": self.created_at,
            "task_id": self.task_id,
            "agent_name": self.agent_name,
        }


@dataclass
class MergeCheckResult:
    """合并检查结果"""
    can_merge: bool
    has_conflicts: bool = False
    conflict_files: list[str] = field(default_factory=list)
    ahead_by: int = 0
    behind_by: int = 0
    error: str = ""
    
    def to_dict(self) -> dict:
        return {
            "canMerge": self.can_merge,
            "hasConflicts": self.has_conflicts,
            "conflictFiles": self.conflict_files,
            "aheadBy": self.ahead_by,
            "behindBy": self.behind_by,
            "error": self.error,
        }


@dataclass
class MergeResult:
    """合并结果"""
    success: bool
    message: str = ""
    commit_hash: str = ""
    error: str = ""
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "message": self.message,
            "commitHash": self.commit_hash,
            "error": self.error,
        }


@dataclass
class WorktreeDiffFile:
    """文件差异信息"""
    path: str
    status: str  # A=added, M=modified, D=deleted, R=renamed
    additions: int = 0
    deletions: int = 0
    
    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "status": self.status,
            "additions": self.additions,
            "deletions": self.deletions,
        }


@dataclass
class WorktreeDiffSummary:
    """差异摘要"""
    files: list[WorktreeDiffFile] = field(default_factory=list)
    total_additions: int = 0
    total_deletions: int = 0
    file_count: int = 0
    
    def to_dict(self) -> dict:
        return {
            "files": [f.to_dict() for f in self.files],
            "totalAdditions": self.total_additions,
            "totalDeletions": self.total_deletions,
            "fileCount": self.file_count,
        }


class GitError(Exception):
    """Git 命令错误"""
    pass


class WorktreeLock:
    """链锁串行化 — 同一仓库的 git 操作自动串行化"""
    
    def __init__(self):
        self._locks: dict[str, threading.Lock] = {}
        self._global_lock = threading.Lock()
    
    def _get_lock(self, repo_path: str) -> threading.Lock:
        with self._global_lock:
            if repo_path not in self._locks:
                self._locks[repo_path] = threading.Lock()
            return self._locks[repo_path]
    
    def execute(self, repo_path: str, func):
        """在锁内执行函数"""
        lock = self._get_lock(repo_path)
        with lock:
            return func()


# 全局锁实例
_worktree_lock = WorktreeLock()


def _find_git_command() -> str:
    """查找 git 可执行文件路径"""
    git_path = shutil.which("git")
    return git_path or "git"


class GitWorktreeService:
    """Git Worktree 服务 — 管理 worktree 的增删查改 & 分支合并
    
    参考 SpectrAI GitWorktreeService.ts 实现。
    """
    
    def __init__(self, repo_path: Path | str):
        self.repo_path = Path(repo_path).resolve()
        self._git_cmd = _find_git_command()
    
    def _run_git(self, args: list[str], cwd: Path | None = None, check: bool = True) -> str:
        """执行 git 命令"""
        work_dir = cwd or self.repo_path
        # Windows 下使用 CREATE_NO_WINDOW 标志隐藏窗口
        startupinfo = None
        creationflags = 0
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            creationflags = subprocess.CREATE_NO_WINDOW
        
        result = subprocess.run(
            [self._git_cmd] + args,
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=60,
            startupinfo=startupinfo,
            creationflags=creationflags,
        )
        if check and result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip() or f"git {args[0]} failed"
            raise GitError(error_msg)
        return result.stdout.strip()
    
    # ------------------------------------------------------------------
    # 基础 Git 操作
    # ------------------------------------------------------------------
    
    def is_git_repo(self) -> bool:
        """检查是否为 git 仓库"""
        try:
            self._run_git(["rev-parse", "--is-inside-work-tree"])
            return True
        except GitError:
            return False
    
    def get_repo_root(self) -> Path:
        """获取仓库根目录"""
        return Path(self._run_git(["rev-parse", "--show-toplevel"]))
    
    def is_dirty(self) -> bool:
        """检查工作区是否有未提交的改动（排除 untracked 文件）"""
        try:
            output = self._run_git(["status", "--porcelain", "-uno"])
            return len(output) > 0
        except GitError:
            return False
    
    def get_status(self) -> dict:
        """获取工作区文件状态"""
        try:
            output = self._run_git(["status", "--porcelain=v1"])
            staged = []
            unstaged = []
            untracked = []
            
            for line in output.split("\n"):
                if not line:
                    continue
                x = line[0]  # staged status
                y = line[1]  # unstaged status
                raw_path = line[3:]
                # 处理重命名
                file_path = raw_path.split(" -> ")[1] if " -> " in raw_path else raw_path
                
                if x == "?" and y == "?":
                    untracked.append(file_path)
                else:
                    if x not in (" ", "?"):
                        staged.append({"path": file_path, "statusCode": x})
                    if y not in (" ", "?"):
                        unstaged.append({"path": file_path, "statusCode": y})
            
            return {"staged": staged, "unstaged": unstaged, "untracked": untracked}
        except GitError:
            return {"staged": [], "unstaged": [], "untracked": []}
    
    def get_current_branch(self) -> str:
        """获取当前分支名"""
        try:
            return self._run_git(["symbolic-ref", "--short", "HEAD"])
        except GitError:
            return self._run_git(["rev-parse", "--short", "HEAD"])
    
    def get_head_commit(self, path: Path | None = None) -> str:
        """获取 HEAD commit hash"""
        return self._run_git(["rev-parse", "HEAD"], cwd=path)
    
    # ------------------------------------------------------------------
    # Worktree 操作
    # ------------------------------------------------------------------
    
    def list_worktrees(self) -> list[WorktreeInfo]:
        """列出所有 worktree"""
        def _list():
            output = self._run_git(["worktree", "list", "--porcelain"])
            worktrees = []
            current = {}
            
            for line in output.split("\n"):
                if line.startswith("worktree "):
                    current = {"path": line.split(" ", 1)[1]}
                elif line.startswith("branch "):
                    branch = line.split(" ", 1)[1]
                    current["branch"] = branch.replace("refs/heads/", "")
                elif line.startswith("HEAD "):
                    current["head"] = line.split(" ", 1)[1]
                elif line == "" and current:
                    wt = WorktreeInfo(
                        path=current.get("path", ""),
                        branch=current.get("branch", ""),
                        head=current.get("head", ""),
                    )
                    worktrees.append(wt)
                    current = {}
            
            if current:
                wt = WorktreeInfo(
                    path=current.get("path", ""),
                    branch=current.get("branch", ""),
                    head=current.get("head", ""),
                )
                worktrees.append(wt)
            
            return worktrees
        
        return _worktree_lock.execute(str(self.repo_path), _list)
    
    def create_worktree(
        self,
        task_id: str,
        agent_name: str,
        branch_name: str | None = None,
        base_branch: str | None = None,
    ) -> WorktreeInfo:
        """创建新的 worktree
        
        Args:
            task_id: 任务 ID
            agent_name: Agent 名称
            branch_name: 分支名（可选，自动生成）
            base_branch: 基础分支（可选，默认当前分支）
            
        Returns:
            WorktreeInfo
        """
        def _create():
            # 生成分支名
            if not branch_name:
                branch_name = self._slugify_branch(f"{agent_name}-{task_id}")
            
            # 确定基础分支
            if not base_branch:
                base_branch = self.get_current_branch()
            
            # 生成 worktree 路径
            worktree_dir = self.repo_path.parent / f"{self.repo_path.name}-{task_id}"
            
            # 检查分支是否已存在
            existing_branches = self._run_git(["branch", "--list", branch_name], check=False)
            if existing_branches.strip():
                # 分支已存在，使用现有分支
                self._run_git(["worktree", "add", str(worktree_dir), branch_name])
            else:
                # 创建新分支
                self._run_git(["worktree", "add", "-b", branch_name, str(worktree_dir), base_branch])
            
            # 获取创建的 worktree 信息
            head = self.get_head_commit(worktree_dir)
            created_at = datetime.now(timezone.utc).isoformat()
            
            return WorktreeInfo(
                path=str(worktree_dir),
                branch=branch_name,
                head=head,
                status=WorktreeStatus.ACTIVE,
                created_at=created_at,
                task_id=task_id,
                agent_name=agent_name,
            )
        
        return _worktree_lock.execute(str(self.repo_path), _create)
    
    def remove_worktree(self, worktree_path: str, force: bool = False) -> bool:
        """删除 worktree
        
        Args:
            worktree_path: Worktree 路径
            force: 强制删除（即使有未提交的改动）
            
        Returns:
            是否成功
        """
        def _remove():
            args = ["worktree", "remove"]
            if force:
                args.append("--force")
            args.append(worktree_path)
            
            try:
                self._run_git(args)
                return True
            except GitError as e:
                logger.error(f"Failed to remove worktree: {e}")
                return False
        
        return _worktree_lock.execute(str(self.repo_path), _remove)
    
    def prune_worktrees(self) -> list[str]:
        """清理已删除的 worktree 引用
        
        Returns:
            清理的 worktree 路径列表
        """
        def _prune():
            # 获取已删除的 worktree
            output = self._run_git(["worktree", "list", "--porcelain"])
            pruned = []
            
            for line in output.split("\n"):
                if line.startswith("worktree "):
                    path = line.split(" ", 1)[1]
                    if not os.path.exists(path):
                        pruned.append(path)
            
            # 执行清理
            self._run_git(["worktree", "prune"])
            
            return pruned
        
        return _worktree_lock.execute(str(self.repo_path), _prune)
    
    # ------------------------------------------------------------------
    # 分支合并操作
    # ------------------------------------------------------------------
    
    def check_merge(self, worktree_path: str, target_branch: str) -> MergeCheckResult:
        """检查是否可以合并
        
        Args:
            worktree_path: Worktree 路径
            target_branch: 目标分支
            
        Returns:
            MergeCheckResult
        """
        def _check():
            worktree = Path(worktree_path)
            worktree_branch = self._run_git(["symbolic-ref", "--short", "HEAD"], cwd=worktree)
            
            # 检查是否有冲突
            try:
                # 使用 --no-commit 模拟合并
                self._run_git(["checkout", target_branch])
                output = self._run_git(["merge", "--no-commit", "--no-ff", worktree_branch], check=False)
                
                # 检查是否有冲突
                status = self._run_git(["status", "--porcelain"])
                conflict_files = []
                for line in status.split("\n"):
                    if line and line[0] == "U" or line[1] == "U":
                        file_path = line[3:]
                        conflict_files.append(file_path)
                
                # 取消合并
                self._run_git(["merge", "--abort"], check=False)
                self._run_git(["checkout", worktree_branch])
                
                if conflict_files:
                    return MergeCheckResult(
                        can_merge=False,
                        has_conflicts=True,
                        conflict_files=conflict_files,
                    )
                
                # 计算 ahead/behind
                ahead_behind = self._run_git(
                    ["rev-list", "--left-right", "--count", f"{worktree_branch}...{target_branch}"],
                    check=False
                )
                ahead, behind = 0, 0
                if ahead_behind.strip():
                    parts = ahead_behind.strip().split()
                    if len(parts) == 2:
                        ahead = int(parts[0])
                        behind = int(parts[1])
                
                return MergeCheckResult(
                    can_merge=True,
                    has_conflicts=False,
                    ahead_by=ahead,
                    behind_by=behind,
                )
                
            except GitError as e:
                return MergeCheckResult(
                    can_merge=False,
                    error=str(e),
                )
        
        return _worktree_lock.execute(str(self.repo_path), _check)
    
    def merge_worktree(
        self,
        worktree_path: str,
        target_branch: str,
        commit_message: str | None = None,
        no_ff: bool = True,
    ) -> MergeResult:
        """合并 worktree 分支到目标分支
        
        Args:
            worktree_path: Worktree 路径
            target_branch: 目标分支
            commit_message: 提交消息（可选）
            no_ff: 是否使用 --no-ff
            
        Returns:
            MergeResult
        """
        def _merge():
            worktree = Path(worktree_path)
            worktree_branch = self._run_git(["symbolic-ref", "--short", "HEAD"], cwd=worktree)
            
            # 先检查是否可以合并
            check_result = self.check_merge(worktree_path, target_branch)
            if not check_result.can_merge:
                return MergeResult(
                    success=False,
                    error=check_result.error or "Cannot merge due to conflicts",
                )
            
            # 切换到目标分支
            self._run_git(["checkout", target_branch])
            
            # 执行合并
            args = ["merge"]
            if no_ff:
                args.append("--no-ff")
            if commit_message:
                args.extend(["-m", commit_message])
            args.append(worktree_branch)
            
            try:
                output = self._run_git(args)
                
                # 获取合并提交 hash
                commit_hash = self._run_git(["rev-parse", "HEAD"])
                
                return MergeResult(
                    success=True,
                    message=output,
                    commit_hash=commit_hash,
                )
                
            except GitError as e:
                # 取消合并
                self._run_git(["merge", "--abort"], check=False)
                return MergeResult(
                    success=False,
                    error=str(e),
                )
        
        return _worktree_lock.execute(str(self.repo_path), _merge)
    
    def auto_merge_and_cleanup(
        self,
        worktree_path: str,
        target_branch: str = "main",
        delete_branch: bool = True,
    ) -> MergeResult:
        """自动合并并清理 worktree
        
        Args:
            worktree_path: Worktree 路径
            target_branch: 目标分支
            delete_branch: 是否删除分支
            
        Returns:
            MergeResult
        """
        # 先检查是否可以合并
        check_result = self.check_merge(worktree_path, target_branch)
        if not check_result.can_merge:
            return MergeResult(
                success=False,
                error=check_result.error or f"Cannot merge: {check_result.conflict_files}",
            )
        
        # 获取 worktree 信息
        worktree = Path(worktree_path)
        worktree_branch = self._run_git(["symbolic-ref", "--short", "HEAD"], cwd=worktree)
        
        # 生成提交消息
        commit_message = f"Merge worktree {worktree_branch}"
        
        # 执行合并
        result = self.merge_worktree(worktree_path, target_branch, commit_message)
        
        if result.success:
            # 删除 worktree
            self.remove_worktree(worktree_path, force=True)
            
            # 删除分支
            if delete_branch:
                try:
                    self._run_git(["branch", "-D", worktree_branch])
                except GitError as e:
                    logger.warning(f"Failed to delete branch {worktree_branch}: {e}")
        
        return result
    
    # ------------------------------------------------------------------
    # 差异分析
    # ------------------------------------------------------------------
    
    def get_diff_summary(self, worktree_path: str, base_ref: str = "HEAD") -> WorktreeDiffSummary:
        """获取 worktree 与基准的差异摘要
        
        Args:
            worktree_path: Worktree 路径
            base_ref: 基准引用
            
        Returns:
            WorktreeDiffSummary
        """
        worktree = Path(worktree_path)
        
        # 获取差异统计
        output = self._run_git(["diff", "--stat", base_ref], cwd=worktree, check=False)
        
        files = []
        total_additions = 0
        total_deletions = 0
        
        for line in output.split("\n"):
            if not line or line.startswith(" ") or "files changed" in line:
                continue
            
            # 解析格式: "path | N additions, M deletions"
            match = re.match(r"(.+?)\s+\|\s+(\d+).*?(\d+)?", line)
            if match:
                file_path = match.group(1).strip()
                additions = int(match.group(2)) if match.group(2) else 0
                deletions = int(match.group(3)) if match.group(3) else 0
                
                files.append(WorktreeDiffFile(
                    path=file_path,
                    status="M",  # 默认修改
                    additions=additions,
                    deletions=deletions,
                ))
                total_additions += additions
                total_deletions += deletions
        
        return WorktreeDiffSummary(
            files=files,
            total_additions=total_additions,
            total_deletions=total_deletions,
            file_count=len(files),
        )
    
    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------
    
    def _slugify_branch(self, title: str, prefix: str = "task") -> str:
        """将标题转为合法的 git 分支名
        
        参考 SpectrAI slugifyBranch 方法。
        """
        slug = title.lower()
        slug = re.sub(r"[^\w\u4e00-\u9fa5\s-]", "", slug)  # 保留中文、字母、数字、空格、连字符
        slug = re.sub(r"[\s_]+", "-", slug)  # 空格/下划线 → 连字符
        slug = re.sub(r"-+", "-", slug)  # 多个连字符合并
        slug = slug.strip("-")  # 去首尾连字符
        slug = slug[:40]  # 截断
        
        return f"{prefix}/{slug}" if slug else f"{prefix}/{int(time.time())}"
    
    def get_worktree_by_task(self, task_id: str) -> WorktreeInfo | None:
        """根据任务 ID 获取 worktree"""
        worktrees = self.list_worktrees()
        for wt in worktrees:
            if wt.task_id == task_id:
                return wt
        return None
    
    def get_worktree_by_agent(self, agent_name: str) -> list[WorktreeInfo]:
        """根据 Agent 名称获取 worktree 列表"""
        worktrees = self.list_worktrees()
        return [wt for wt in worktrees if wt.agent_name == agent_name]
    
    def get_summary(self) -> dict:
        """获取 worktree 摘要"""
        worktrees = self.list_worktrees()
        active = [wt for wt in worktrees if wt.status == WorktreeStatus.ACTIVE]
        merged = [wt for wt in worktrees if wt.status == WorktreeStatus.MERGED]
        abandoned = [wt for wt in worktrees if wt.status == WorktreeStatus.ABANDONED]
        
        return {
            "totalWorktrees": len(worktrees),
            "activeWorktrees": len(active),
            "mergedWorktrees": len(merged),
            "abandonedWorktrees": len(abandoned),
            "worktrees": [wt.to_dict() for wt in worktrees],
        }


class WorktreeManager:
    """Worktree 管理器 — 自动创建/合并/清理
    
    提供更高层次的 worktree 管理功能。
    """
    
    def __init__(self, repo_path: Path | str):
        self.repo_path = Path(repo_path).resolve()
        self.service = GitWorktreeService(repo_path)
        self._worktree_registry: dict[str, WorktreeInfo] = {}
        self._lock = threading.Lock()
    
    def create_for_task(
        self,
        task_id: str,
        agent_name: str,
        branch_name: str | None = None,
        base_branch: str | None = None,
    ) -> WorktreeInfo:
        """为任务创建 worktree
        
        Args:
            task_id: 任务 ID
            agent_name: Agent 名称
            branch_name: 分支名（可选）
            base_branch: 基础分支（可选）
            
        Returns:
            WorktreeInfo
        """
        # 检查是否已存在
        existing = self.service.get_worktree_by_task(task_id)
        if existing:
            logger.info(f"Worktree already exists for task {task_id}")
            return existing
        
        # 创建新 worktree
        worktree = self.service.create_worktree(task_id, agent_name, branch_name, base_branch)
        
        # 注册
        with self._lock:
            self._worktree_registry[task_id] = worktree
        
        logger.info(f"Created worktree for task {task_id}: {worktree.path}")
        return worktree
    
    def complete_task(
        self,
        task_id: str,
        target_branch: str = "main",
        auto_merge: bool = True,
    ) -> MergeResult:
        """完成任务并合并
        
        Args:
            task_id: 任务 ID
            target_branch: 目标分支
            auto_merge: 是否自动合并
            
        Returns:
            MergeResult
        """
        worktree = self.service.get_worktree_by_task(task_id)
        if not worktree:
            return MergeResult(
                success=False,
                error=f"No worktree found for task {task_id}",
            )
        
        if auto_merge:
            result = self.service.auto_merge_and_cleanup(worktree.path, target_branch)
        else:
            result = self.service.merge_worktree(worktree.path, target_branch)
        
        # 更新注册
        if result.success:
            with self._lock:
                if task_id in self._worktree_registry:
                    self._worktree_registry[task_id].status = WorktreeStatus.MERGED
        
        return result
    
    def abandon_task(self, task_id: str) -> bool:
        """放弃任务并清理
        
        Args:
            task_id: 任务 ID
            
        Returns:
            是否成功
        """
        worktree = self.service.get_worktree_by_task(task_id)
        if not worktree:
            logger.warning(f"No worktree found for task {task_id}")
            return False
        
        # 删除 worktree
        success = self.service.remove_worktree(worktree.path, force=True)
        
        # 删除分支
        if success:
            try:
                self.service._run_git(["branch", "-D", worktree.branch])
            except GitError as e:
                logger.warning(f"Failed to delete branch {worktree.branch}: {e}")
        
        # 更新注册
        with self._lock:
            if task_id in self._worktree_registry:
                self._worktree_registry[task_id].status = WorktreeStatus.ABANDONED
        
        return success
    
    def cleanup_abandoned(self) -> list[str]:
        """清理所有已放弃的 worktree
        
        Returns:
            清理的 worktree 路径列表
        """
        cleaned = []
        
        with self._lock:
            for task_id, worktree in self._worktree_registry.items():
                if worktree.status == WorktreeStatus.ABANDONED:
                    if os.path.exists(worktree.path):
                        self.service.remove_worktree(worktree.path, force=True)
                        cleaned.append(worktree.path)
        
        # 执行 prune
        pruned = self.service.prune_worktrees()
        cleaned.extend(pruned)
        
        return cleaned
    
    def get_all_worktrees(self) -> list[WorktreeInfo]:
        """获取所有 worktree"""
        return self.service.list_worktrees()
    
    def get_active_worktrees(self) -> list[WorktreeInfo]:
        """获取活跃的 worktree"""
        worktrees = self.service.list_worktrees()
        return [wt for wt in worktrees if wt.status == WorktreeStatus.ACTIVE]
    
    def get_summary(self) -> dict:
        """获取管理器摘要"""
        service_summary = self.service.get_summary()
        
        with self._lock:
            registry_count = len(self._worktree_registry)
            registered_tasks = list(self._worktree_registry.keys())
        
        return {
            **service_summary,
            "registeredTasks": registry_count,
            "registeredTaskIds": registered_tasks,
        }


def get_worktree_manager(repo_path: Path | str) -> WorktreeManager:
    """获取 WorktreeManager 实例
    
    Args:
        repo_path: 仓库路径
        
    Returns:
        WorktreeManager 实例
    """
    return WorktreeManager(repo_path)