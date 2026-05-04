"""Agent prompt builder — identity + task only.

Coordination knowledge (how to use clawteam CLI) is provided
by the ClawTeam Skill, not duplicated here.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Boids-inspired coordination rules (Reynolds 1986, adapted for LLM agents)
# Injected when team_size > 1 to enable emergent coordination.
# ---------------------------------------------------------------------------

BOIDS_RULES = """## Coordination Rules

As a member of a multi-agent team, follow these four rules:

1. **Separation** — Do not duplicate work another agent has done or is doing. Check task statuses before starting.
2. **Alignment** — Follow the team lead's direction and maintain consistent standards (code style, naming, approach).
3. **Cohesion** — Proactively share discoveries by writing to the shared workspace. Make your findings visible to the team.
4. **Boundary** — Stay within your assigned scope. Do not modify files or areas owned by other agents without coordination."""

# ---------------------------------------------------------------------------
# Metacognitive self-evaluation block
# Injected into agent prompts so agents report confidence and escalate
# when uncertain. Based on cognitive architecture research (metacognition).
# ---------------------------------------------------------------------------

METACOGNITION_BLOCK = """## Self-Evaluation

After completing each task, include a confidence assessment:
- Tag your output with `[confidence: 0.X]` where X is 0-10 (e.g., `[confidence: 0.8]`).
- If confidence is below 0.6, explain what you are uncertain about and recommend human review.
- If you encounter something outside your expertise, say so and suggest escalation rather than guessing."""

# ---------------------------------------------------------------------------
# Continuous Running Mode for specialist agents
# Injected when agent_type != "leader" to enable persistent inbox monitoring.
# ---------------------------------------------------------------------------

CONTINUOUS_RUN_BLOCK = """## Continuous Running Mode

You are a persistent team agent. Do NOT exit after completing a task.

**Startup:**
1. Check your inbox for any pending tasks:
   `clawteam inbox peek {team_name} --agent {agent_name}`
2. If tasks exist, process them. If not, proceed to standby.

**Main Loop:**
- Every 30 seconds, check your inbox for new messages:
  `clawteam inbox peek {team_name} --agent {agent_name}`
- If you receive a new task:
  1. Acknowledge receipt: `clawteam inbox receive {team_name} --agent {agent_name}`
  2. Execute the task
  3. Report completion to leader: `clawteam inbox send {team_name} {leader_name} "Task completed: [BRIEF_SUMMARY]"`
  4. Return to standby loop

**Shutdown Protocol:**
- ONLY exit when the leader sends the exact message "shutdown"
- Before exiting after completing a task, ALWAYS ask the leader:
  `clawteam inbox send {team_name} {leader_name} "Task done. Should I exit or await new tasks?"`
- Wait for leader's response before deciding to exit or continue

**Task Completion:**
- After completing any task, do NOT auto-exit
- Send completion message to leader
- Ask if should exit or await new tasks"""

# ---------------------------------------------------------------------------
# Leader-specific coordination rules
# Injected when agent_type == "leader" to ensure proper board/task management.
# ---------------------------------------------------------------------------

LEADER_PROTOCOL = """## Leader Protocol

As the team leader, you are responsible for task coordination and board management:

**Task Board Management:**
- When you receive a task assignment, create a board task immediately:
  `clawteam task create {team_name} --title "[TASK_TITLE]" --status pending --owner [AGENT] --description "[DESCRIPTION]"`
- When you assign a task to a member, update the board:
  `clawteam task update {team_name} [TASK_ID] --status in_progress`
- When a member reports task completion, update the board:
  `clawteam task update {team_name} [TASK_ID] --status completed`
- When you receive a message about progress, keep the board in sync.

**Key Principle: ALWAYS sync tasks to the board.** The board is the source of truth for team progress. Every task mentioned in messages should be reflected on the board.

**Inbox Monitoring:**
- Check your inbox regularly for messages from team members.
- When a member sends a status update, update the corresponding board task.
- When a member completes work, acknowledge and update the board.

**Team Coordination:**
- Assign tasks to appropriate members based on their type (architect, backend, tester, etc.).
- Monitor progress and re-assign if needed.
- Report overall team status when asked."""


def build_agent_prompt(
    agent_name: str,
    agent_id: str,
    agent_type: str,
    team_name: str,
    leader_name: str,
    task: str,
    user: str = "",
    workspace_dir: str = "",
    workspace_branch: str = "",
    memory_scope: str = "",
    intent: str = "",
    end_state: str = "",
    constraints: list[str] | None = None,
    team_size: int = 1,
) -> str:
    """Build agent prompt: identity + mission + task + optional workspace info."""
    lines = [
        "## Identity\n",
        f"- Name: {agent_name}",
        f"- ID: {agent_id}",
    ]
    if user:
        lines.append(f"- User: {user}")
    lines.extend(
        [
            f"- Type: {agent_type}",
            f"- Team: {team_name}",
            f"- Leader: {leader_name}",
        ]
    )
    # Mission section (Auftragstaktik: intent + end_state + constraints)
    if intent or end_state or constraints:
        lines.extend(["", "## Mission\n"])
        if intent:
            lines.append(f"**Intent:** {intent}")
        if end_state:
            lines.append(f"**End State:** {end_state}")
        if constraints:
            lines.append("**Constraints:**")
            for c in constraints:
                lines.append(f"- {c}")
    if workspace_dir:
        lines.extend(
            [
                "",
                "## Workspace",
                f"- Working directory: {workspace_dir}",
                f"- Branch: {workspace_branch}",
                "- This is an isolated git worktree. Your changes do not affect the main branch.",
            ]
        )
    if memory_scope:
        lines.extend(
            [
                "",
                "## Shared Memory",
                f"- Your team shares memory scope `{memory_scope}`.",
                f"- Use `memory_store` with scope `{memory_scope}` for team-shared knowledge.",
                "- Use `memory_recall` to access memories stored by other team members in this scope.",
            ]
        )
    if team_size > 1:
        lines.extend(["", BOIDS_RULES])
    # Inject leader protocol for team leads
    if agent_type == "leader":
        lines.extend(["", LEADER_PROTOCOL])
    # Inject continuous running mode for specialist agents (not leader)
    else:
        lines.extend(["", CONTINUOUS_RUN_BLOCK.format(
            team_name=team_name,
            agent_name=agent_name,
            leader_name=leader_name
        )])
    lines.extend(
        [
            "",
            "## Task\n",
            task,
            "",
            "## Coordination Protocol\n",
            "- IMPORTANT: spawned OpenClaw workers run under exec allowlist mode. Use only the allowlisted executable path from $CLAWTEAM_BIN, not arbitrary shell commands.",
            f"- First action: run `clawteam task list {team_name} --owner {agent_name}` to discover your task ID.",
            f"- Starting a task: `clawteam task update {team_name} [TASK_ID] --status in_progress`",
            f"- Finishing a task: `clawteam task update {team_name} [TASK_ID] --status completed`",
            "- When you complete a task, report to the leader:",
            f'  `clawteam inbox send {team_name} {leader_name} "Task completed: [BRIEF_SUMMARY]"',
            "- If you are blocked or any clawteam command is denied/fails, message the leader immediately with the exact error text:",
            f'  `clawteam inbox send {team_name} {leader_name} "Blocked: [EXACT_ERROR]"',
            f"- After finishing work, report your costs: `clawteam cost report {team_name} --input-tokens [N] --output-tokens [N] --cost-cents [N]`",
            f"- Before finishing, save your session: `clawteam session save {team_name} --session-id [ID]`",
            "",
            METACOGNITION_BLOCK,
            "",
        ]
    )
    return "\n".join(lines)
