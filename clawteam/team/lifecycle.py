"""Lifecycle management for team agents (shutdown protocol)."""

from __future__ import annotations

import shutil

from clawteam.paths import ensure_within_root, validate_identifier
from clawteam.team.mailbox import MailboxManager
from clawteam.team.models import MessageType, get_data_dir
from clawteam.team.parent_child import ParentChildRegistry
from clawteam.spawn.registry import (
    get_children_of,
    get_descendants_of,
    terminate_agent_tree,
)


class LifecycleManager:
    """Manages agent lifecycle within a team (shutdown, idle, cleanup)."""

    def __init__(self, team_name: str, mailbox: MailboxManager):
        self.team_name = team_name
        self.mailbox = mailbox

    def request_shutdown(
        self,
        from_agent: str,
        to_agent: str,
        reason: str = "",
    ) -> str:
        msg = self.mailbox.send(
            from_agent=from_agent,
            to=to_agent,
            content=f"Shutdown requested.{(' Reason: ' + reason) if reason else ''}",
            msg_type=MessageType.shutdown_request,
            reason=reason or None,
        )
        return msg.request_id

    def approve_shutdown(
        self,
        agent_name: str,
        request_id: str,
        requester_name: str,
    ) -> None:
        self.mailbox.send(
            from_agent=agent_name,
            to=requester_name,
            content=f"{agent_name} shutting down.",
            msg_type=MessageType.shutdown_approved,
            request_id=request_id,
        )

    def reject_shutdown(
        self,
        agent_name: str,
        request_id: str,
        requester_name: str,
        reason: str = "",
    ) -> None:
        self.mailbox.send(
            from_agent=agent_name,
            to=requester_name,
            content=f"Shutdown rejected.{(' Reason: ' + reason) if reason else ''}",
            msg_type=MessageType.shutdown_rejected,
            request_id=request_id,
            reason=reason or None,
        )

    def send_idle(
        self,
        agent_name: str,
        agent_id: str,
        leader_name: str,
        last_task: str = "",
        task_status: str = "",
    ) -> None:
        """Send idle notification to leader."""
        self.mailbox.send(
            from_agent=agent_name,
            to=leader_name,
            msg_type=MessageType.idle,
            agent_id=agent_id,
            last_task=last_task or None,
            status=task_status or None,
        )

    @staticmethod
    def cleanup_team(team_name: str) -> bool:
        validate_identifier(team_name, "team name")
        # Best-effort cleanup of git workspaces
        try:
            from clawteam.workspace import get_workspace_manager

            ws_mgr = get_workspace_manager()
            if ws_mgr:
                ws_mgr.cleanup_team(team_name)
        except Exception:
            pass

        team_dir = ensure_within_root(get_data_dir() / "teams", team_name)
        tasks_dir = ensure_within_root(get_data_dir() / "tasks", team_name)
        costs_dir = ensure_within_root(get_data_dir() / "costs", team_name)
        sessions_dir = ensure_within_root(get_data_dir() / "sessions", team_name)
        cleaned = False
        for d in (team_dir, tasks_dir, costs_dir, sessions_dir):
            if d.exists():
                shutil.rmtree(d)
                cleaned = True
        return cleaned

    def register_child(self, parent_agent: str, child_agent: str) -> None:
        """Register a child agent under a parent agent.

        Call this when spawning a child agent so the parent-child
        relationship is tracked for cascade cleanup.
        """
        validate_identifier(parent_agent, "parent agent name")
        validate_identifier(child_agent, "child agent name")
        ParentChildRegistry.register(self.team_name, child_agent, parent_agent)

    def terminate_children(
        self,
        parent_agent: str,
        cascade: bool = False,
    ) -> list[str]:
        """Terminate children of an agent.

        Args:
            parent_agent: The parent agent whose children to terminate.
            cascade: If True, terminate entire descendant tree (grandchildren, etc.).
                     If False, only terminate direct children.

        Returns:
            List of agent names terminated, in order (leaves first).
        """
        validate_identifier(parent_agent, "parent agent name")
        if cascade:
            descendants = ParentChildRegistry.get_descendants(self.team_name, parent_agent)
            agents_to_kill = list(reversed(descendants))
        else:
            agents_to_kill = ParentChildRegistry.get_children(self.team_name, parent_agent)

        terminated: list[str] = []
        for agent in agents_to_kill:
            try:
                terminate_agent_tree(self.team_name, agent)
            except Exception:
                pass
            ParentChildRegistry.unregister(self.team_name, agent)
            terminated.append(agent)

        return terminated

    def terminate_tree(self, root_agent: str) -> list[str]:
        """Terminate an entire agent tree (root + all descendants).

        Uses bottom-up order so children are cleaned up before parents.
        Both spawn registry entries and parent-child registry entries are removed.

        Returns:
            List of agent names terminated, in order (leaves first).
        """
        validate_identifier(root_agent, "root agent name")
        terminated = terminate_agent_tree(self.team_name, root_agent)
        # Also clean up parent-child registry entries
        ParentChildRegistry.unregister(self.team_name, root_agent)
        for agent in terminated:
            if agent != root_agent:
                ParentChildRegistry.unregister(self.team_name, agent)
        return terminated

    def get_children(self, agent_name: str) -> list[str]:
        """Return direct child agents of the given agent."""
        return ParentChildRegistry.get_children(self.team_name, agent_name)

    def get_tree(self, agent_name: str) -> dict:
        """Return the full descendant tree of an agent.

        Returns a nested dict of the form:
            {
                "agent": "...",
                "children": [
                    {"agent": "child1", "children": [...]},
                    {"agent": "child2", "children": []},
                ]
            }
        """

        def build_tree(name: str) -> dict:
            children = ParentChildRegistry.get_children(self.team_name, name)
            return {
                "agent": name,
                "children": [build_tree(c) for c in children],
            }

        return build_tree(agent_name)

    def get_parent(self, agent_name: str) -> str | None:
        """Return the parent agent name, or None if no parent."""
        return ParentChildRegistry.get_parent(self.team_name, agent_name)

    def get_ancestors(self, agent_name: str) -> list[str]:
        """Return all ancestors (parent, grandparent, etc.) of an agent."""
        return ParentChildRegistry.get_ancestors(self.team_name, agent_name)
