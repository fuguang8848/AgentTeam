---
name: AgentTeam Multi-Agent Coordination
description: >
  This skill should be used when the user asks to "create a team", "spawn agents",
  "assign tasks", "coordinate multiple agents", "check team status", "view kanban board",
  "send messages between agents", "manage team tasks", "monitor team progress",
  or mentions "agentteam", "multi-agent coordination", "team collaboration",
  "agent inbox", "task board", "spawn worker". This skill should also be triggered
  when the current task is complex enough to benefit from splitting into subtasks
  and delegating to multiple agents — for example when the user asks to "build a
  full-stack app", "refactor the entire codebase", "implement multiple features
  in parallel", or when the agent determines that the work scope exceeds what a
  single agent can efficiently handle alone. Provides comprehensive guidance for
  using the AgentTeam CLI to orchestrate multi-agent teams with task management,
  messaging, and monitoring.
version: 0.4.0
minCliVersion: "0.3.0"
framework: agentteam
---

# AgentTeam Multi-Agent Coordination

AgentTeam is a framework-agnostic CLI tool for coordinating multiple AI agents as a team.
It provides file-based team management, inter-agent messaging, shared task tracking with
dependency resolution, plan approval workflows, and terminal-based monitoring dashboards.

All operations are performed via the `agentteam` CLI. Data is stored in `~/.agentteam/` by default.

## Core Concepts

### Teams
A named group of agents with one leader and zero or more workers. Created via
`agentteam team spawn-team`. The leader approves joins, reviews plans, and coordinates shutdown.

### Inbox
File-based message queue per agent. `agentteam message send` for point-to-point,
`agentteam message broadcast` for all members. `agentteam message receive` consumes messages
(destructive); `agentteam message peek` reads without consuming.

### Tasks
Shared task board with statuses: `pending`, `in_progress`, `completed`, `blocked`.
Tasks support dependency chains (`--blocks`, `--blocked-by`). Completing a task auto-unblocks dependents.

### Board
Terminal kanban dashboard. `agentteam board show` for single team, `agentteam board overview`
for all teams, `agentteam board live` for real-time auto-refresh.

### Identity
Each agent has env vars (`AGENTTEAM_AGENT_ID`, `AGENTTEAM_AGENT_NAME`, `AGENTTEAM_AGENT_TYPE`,
`AGENTTEAM_TEAM_NAME`). Set automatically when spawned via `agentteam agent spawn`.

## Quick Start

### Set Up a Team with Tasks

```bash
# Set identity for the current session
export AGENTTEAM_AGENT_ID="leader-001"
export AGENTTEAM_AGENT_NAME="leader"
export AGENTTEAM_AGENT_TYPE="leader"

# Create team
agentteam team spawn-team my-team -d "Project team" -n leader

# Create tasks
agentteam task create my-team "Design system" -o leader
agentteam task create my-team "Implement feature" -o worker1
agentteam task create my-team "Write tests" -o worker2

# View board
agentteam board show my-team
```

### Spawn and Coordinate Agents

```bash
# Spawn workers — defaults: tmux backend, openclaw command, git worktree isolation, skip-permissions on
agentteam agent spawn --team my-team --agent-name worker1 --task "Implement the auth module"
agentteam agent spawn --team my-team --agent-name worker2 --task "Write unit tests"

# Watch all agents working simultaneously (tiled tmux panes)
agentteam board attach my-team

# Send instructions
agentteam message send my-team worker1 "Start implementing the auth module"

# Monitor task board
agentteam board live my-team --interval 3
```

### Spawn Defaults

| Setting | Default | Override |
|---------|---------|----------|
| Backend | `auto` | `agentteam agent spawn tmux ...` |
| Command | `openclaw` | `agentteam agent spawn subprocess openclaw ...` |
| Workspace | `auto` (git worktree) | `--no-workspace` or config `workspace=never` |
| Permissions | skip (no approval needed) | `--no-skip-permissions` or config `skip_permissions=false` |

## Command Groups Reference

### team - Team Management
```bash
agentteam team create <name>              # Create new team
agentteam team discover                    # List all teams
agentteam team spawn-team <name>          # Create team with leader
agentteam team status <name>              # Show team status
agentteam team request-join <team> <name> # Request to join team
agentteam team approve-join <team> <id>   # Approve join request
agentteam team cleanup <name>             # Delete team
```

### agent - Agent Lifecycle
```bash
agentteam agent spawn [backend] [cmd]     # Spawn new agent
agentteam agent list                      # List all agents
agentteam agent info <name>              # Show agent details
agentteam agent health <name>             # Check agent health
agentteam agent restart <name>           # Restart agent
agentteam agent kill <name>              # Kill agent
```

### task - Task Management
```bash
agentteam task create <team> <subject>   # Create task
agentteam task get <team> <id>           # Get task details
agentteam task update <team> <id>         # Update task
agentteam task list <team>                # List tasks
agentteam task stats <team>               # Show task statistics
agentteam task wait <team> <id>          # Wait for task completion
agentteam task route <team> -s <subject> # Route task to best agent
```

### message - Inter-Agent Messaging
```bash
agentteam message send <team> <to> <msg>  # Send message
agentteam message broadcast <team> <msg>  # Broadcast to all
agentteam message receive <team>          # Receive messages
agentteam message peek <team>             # Peek without consuming
agentteam message watch <team>            # Continuous monitoring
```

### board - Dashboard & Monitoring
```bash
agentteam board show <team>               # Show kanban board
agentteam board overview                  # All teams overview
agentteam board live <team>              # Live refresh
agentteam board monitor <team>           # Real-time events
agentteam board serve                    # Start web server
agentteam board attach <team>            # Attach tmux session
```

### config - Configuration
```bash
agentteam config show                    # Show config
agentteam config set <key> <value>      # Set config value
agentteam config get <key>              # Get config value
agentteam config init                    # Initialize config
agentteam config health                 # Check config health
```

### lifecycle - Agent Lifecycle
```bash
agentteam lifecycle request-shutdown <team>  # Request shutdown
agentteam lifecycle approve-shutdown <team> <agent>  # Approve shutdown
agentteam lifecycle idle <team>           # Mark agent idle
agentteam lifecycle check-zombies <team>  # Check zombies
agentteam lifecycle terminate-tree <team> <agent>  # Terminate tree
```

### workspace - Git Worktree Management
```bash
agentteam workspace list [repo]           # List worktrees
agentteam workspace checkpoint <team> <agent>  # Create checkpoint
agentteam workspace merge <team> <agent>  # Merge workspace
agentteam workspace cleanup <team>       # Cleanup worktrees
agentteam workspace status <team>       # Show workspace status
```

### session - Session Persistence
```bash
agentteam session save <team>            # Save session
agentteam session show <team>           # Show session
agentteam session clear <team>          # Clear session
```

### template - Team Templates
```bash
agentteam template list                  # List templates
agentteam template show <name>          # Show template details
```

### cost - Cost Tracking
```bash
agentteam cost report <team>             # Report token usage
agentteam cost show <team>              # Show cost summary
agentteam cost budget <team> [amount]   # Set/show budget
```

### insights - Team Insights
```bash
agentteam insights show <team>          # Show insights
agentteam insights tools <team>         # Tool usage stats
agentteam insights skills <team>        # Skill usage stats
agentteam insights memory <team>       # Memory usage stats
```

### dag - Task Dependencies
```bash
agentteam dag sort <team>               # Topological sort
agentteam dag check <team>             # Check for cycles
agentteam dag ready <team>             # Show ready tasks
```

### alert - Alert Management
```bash
agentteam alert check <team>            # Check alerts
agentteam alert list <team>             # List alerts
agentteam alert acknowledge <team> <id> # Acknowledge alert
```

### audit - Audit Logs
```bash
agentteam audit query <team>            # Query logs
agentteam audit summary <team>         # Show summary
agentteam audit log <team>             # Export logs
```

### drift - Drift Detection
```bash
agentteam drift check <team>             # Check drift
agentteam drift list <team>            # List records
agentteam drift ack <team> <path>      # Acknowledge drift
agentteam drift scan <team>            # Scan all configs
```

### role - Role Management
```bash
agentteam role assign <team> <agent> <role>  # Assign role
agentteam role unassign <team> <agent> <role>  # Remove role
agentteam role list <team>             # List assignments
agentteam role suggest <team> <agent>  # Suggest roles
```

### doctor - System Health
```bash
agentteam doctor run                     # Run health check
agentteam doctor fix                    # Fix issues
```

## JSON Output

All commands support `--json` for machine-readable output:

```bash
agentteam --json team discover
agentteam --json board show my-team
agentteam --json task list my-team --status pending
```

## Important Notes

- `message receive` **consumes** messages (deletes files). Use `message peek` for non-destructive reads.
- Task status `blocked` is **auto-set** when `--blocked-by` is specified at creation.
- Completing a task **auto-unblocks** any tasks that list it in `blockedBy`.
- `agent spawn` defaults to **auto** backend with **git worktree** isolation and **skip-permissions**.
- All file writes use atomic tmp+rename to prevent data corruption.
- Identity env vars are set automatically when spawning via `agentteam agent spawn`.
- Use `board attach <team>` to watch all agents in a tiled tmux layout.

## Reference Files

- **`references/cli-reference.md`** — Complete CLI reference with all commands, options, and data models
- **`references/workflows.md`** — Multi-agent workflows: team setup, spawn coordination, join protocol, plan approval, graceful shutdown, monitoring patterns
