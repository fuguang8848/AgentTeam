"""Aggregates team/task/inbox data into plain dicts for rendering."""

from __future__ import annotations

import json

from clawteam.spawn.registry import is_agent_alive
from clawteam.team.mailbox import MailboxManager
from clawteam.team.manager import TeamManager
from clawteam.team.tasks import TaskStore
from clawteam.profiler import get_profiler


class BoardCollector:
    """Aggregates team/task/inbox data into plain dicts."""

    def collect_team(self, team_name: str) -> dict:
        """Collect full board data for a single team.

        Returns a dict with keys: team, members, tasks, taskSummary.
        Raises ValueError if the team does not exist.
        """
        config = TeamManager.get_team(team_name)
        if not config:
            raise ValueError(f"Team '{team_name}' not found")

        mailbox = MailboxManager(team_name)
        store = TaskStore(team_name)

        # Members with inbox counts
        members = []
        for m in config.members:
            inbox_name = f"{m.user}_{m.name}" if m.user else m.name
            alive = is_agent_alive(team_name, m.name)
            entry = {
                "name": m.name,
                "agentId": m.agent_id,
                "agentType": m.agent_type,
                "joinedAt": m.joined_at,
                "inboxCount": mailbox.peek_count(inbox_name),
                "alive": alive,
            }
            if m.user:
                entry["user"] = m.user
            members.append(entry)

        # Tasks grouped by status
        all_tasks = store.list_tasks()
        grouped: dict[str, list[dict]] = {
            "pending": [],
            "in_progress": [],
            "completed": [],
            "blocked": [],
        }
        for t in all_tasks:
            td = json.loads(t.model_dump_json(by_alias=True, exclude_none=True))
            grouped[t.status.value].append(td)

        summary = {
            s: len(grouped[s]) for s in grouped
        }
        summary["total"] = len(all_tasks)

        # Find leader name
        leader_name = ""
        for m in config.members:
            if m.agent_id == config.lead_agent_id:
                leader_name = m.name
                break

        # Collect message history from event log (persistent, never consumed)
        all_messages = []
        try:
            events = mailbox.get_event_log(limit=200)
            for msg in events:
                all_messages.append(
                    json.loads(msg.model_dump_json(by_alias=True, exclude_none=True))
                )
        except Exception:
            pass

        # Cost summary
        cost_data = {}
        try:
            from clawteam.team.costs import CostStore
            cost_store = CostStore(team_name)
            cost_summary = cost_store.summary()
            cost_data = {
                "totalCostCents": cost_summary.total_cost_cents,
                "totalInputTokens": cost_summary.total_input_tokens,
                "totalOutputTokens": cost_summary.total_output_tokens,
                "eventCount": cost_summary.event_count,
                "byAgent": cost_summary.by_agent,
            }
        except Exception:
            pass

        return {
            "team": {
                "name": config.name,
                "description": config.description,
                "leadAgentId": config.lead_agent_id,
                "leaderName": leader_name,
                "createdAt": config.created_at,
                "budgetCents": config.budget_cents,
            },
            "members": members,
            "tasks": grouped,
            "taskSummary": summary,
            "messages": all_messages,
            "cost": cost_data,
        }

    def collect_overview(self) -> list[dict]:
        """Collect summary data for all teams.

        Returns a list of dicts with keys: name, description, leader,
        members, tasks, pendingMessages.
        """
        teams_meta = TeamManager.discover_teams()
        result = []
        for meta in teams_meta:
            name = meta["name"]
            try:
                data = self.collect_team(name)
                total_inbox = sum(m["inboxCount"] for m in data["members"])
                leader = data["team"].get("leaderName", "")
                alive_count = sum(1 for m in data["members"] if m.get("alive"))
                result.append({
                    "name": name,
                    "description": meta.get("description", ""),
                    "leader": leader,
                    "members": len(data["members"]),
                    "tasks": data["taskSummary"]["total"],
                    "pendingMessages": total_inbox,
                    "session_count": len(data["members"]),
                    "active_sessions": alive_count,
                })
            except Exception:
                result.append({
                    "name": name,
                    "description": meta.get("description", ""),
                    "leader": "",
                    "members": meta.get("memberCount", 0),
                    "tasks": 0,
                    "pendingMessages": 0,
                    "session_count": meta.get("memberCount", 0),
                    "active_sessions": 0,
                })
        return result

    def collect_profiler_stats(self) -> dict:
        """Collect performance profiling statistics.

        Returns a dict with keys: profiles (list of recent profiles),
        latency_stats (list of latency statistics), system_metrics (current usage).
        """
        profiler = get_profiler()

        # Get profile results
        profiles = profiler.get_all_profiles()
        profile_list = []
        for p in profiles[-10:]:  # Last 10 profiles
            profile_list.append({
                "name": p.name,
                "duration_ms": round(p.duration_ms, 2),
                "cpu_percent": round(p.cpu_percent, 1),
                "memory_mb": round(p.memory_mb, 1),
                "memory_percent": round(p.memory_percent, 2),
                "start_time": p.start_time,
            })

        # Get latency statistics
        latency_stats = profiler.get_all_latency_stats()
        latency_list = []
        for ls in latency_stats:
            latency_list.append({
                "operation": ls.operation,
                "count": ls.count,
                "total_ms": round(ls.total_ms, 2),
                "avg_ms": round(ls.avg_ms, 2),
                "min_ms": round(ls.min_ms, 2),
                "max_ms": round(ls.max_ms, 2),
                "p50_ms": round(ls.p50_ms, 2),
                "p95_ms": round(ls.p95_ms, 2),
                "p99_ms": round(ls.p99_ms, 2),
            })

        # Get system metrics
        try:
            from clawteam.profiler import ResourceMonitor
            monitor = ResourceMonitor(interval=0.01)
            current = monitor.get_current_usage()
            system_metrics = {
                "cpu_percent": round(current["cpu_percent"], 1),
                "memory_mb": round(current["memory_mb"], 1),
                "memory_percent": round(current["memory_percent"], 2),
                "threads": current["threads"],
                "open_files": current["open_files"],
            }
        except Exception:
            system_metrics = {}

        return {
            "profiles": profile_list,
            "latency_stats": latency_list,
            "system_metrics": system_metrics,
            "total_profiles": len(profiles),
            "total_operations": sum(ls.count for ls in latency_stats),
        }
