---
name: agentteam
description: "Multi-agent swarm coordination via the AgentTeam CLI. Use when the user wants to create agent teams, spawn multiple agents to work in parallel, coordinate tasks with dependencies, broadcast messages between agents, monitor progress via kanban board, or launch pre-built team templates (hedge-fund, code-review, research-paper). AgentTeam uses git worktree isolation + tmux + filesystem-based messaging. Trigger phrases: team, swarm, multi-agent, agentteam, spawn agents, parallel agents, agent team."
---

# AgentTeam — Multi-Agent Swarm Coordination

## Overview

AgentTeam is a CLI tool (`agentteam`) for orchestrating multiple AI agents as self-organizing swarms. It uses git worktree isolation, tmux windows, and filesystem-based messaging. OpenClaw is the default agent backend.

**CLI binary**: `agentteam` (installed via pip, available in PATH)

## Quick Start

### One-Command Template Launch (Recommended)

```bash
# Launch a pre-built team from a template
agentteam launch hedge-fund --team fund1
agentteam launch code-review --team review1
agentteam launch research-paper --team paper1
```

### Manual Team Setup

```bash
# 1. Create team with leader
agentteam team spawn-team my-team -d "Build a web app" -n leader

# 2. Create tasks with dependencies
agentteam task create my-team "Design API schema" -o architect
# Returns task ID, e.g., abc123

agentteam task create my-team "Implement auth" -o backend --blocked-by abc123
agentteam task create my-team "Build frontend" -o frontend --blocked-by abc123
agentteam task create my-team "Write tests" -o tester

# 3. Spawn agents (each gets its own tmux window + git worktree)
agentteam spawn -t my-team -n architect --task "Design the API schema for a web app"
agentteam spawn -t my-team -n backend --task "Implement OAuth2 authentication"
agentteam spawn -t my-team -n frontend --task "Build React dashboard"

# 4. Monitor
agentteam board show my-team        # Kanban view
agentteam board attach my-team      # Tmux tiled view (all agents side-by-side)
agentteam board serve --port 8080   # Web dashboard
```

## Command Reference

### Team Management

| Command | Description |
|---------|-------------|
| `agentteam team spawn-team <name> -d "<desc>" -n <leader>` | Create team |
| `agentteam team discover` | List all teams |
| `agentteam team status <team>` | Show team members and info |
| `agentteam team cleanup <team> --force` | Delete team and all data |

### Task Management

| Command | Description |
|---------|-------------|
| `agentteam task create <team> "<subject>" -o <owner> [-d "<desc>"] [--blocked-by <id>]` | Create task |
| `agentteam task list <team> [--owner <name>]` | List tasks (filterable) |
| `agentteam task update <team> <id> --status <status>` | Update status |
| `agentteam task get <team> <id>` | Get single task |
| `agentteam task stats <team>` | Timing statistics |
| `agentteam task wait <team>` | Block until all tasks complete |

**Task statuses**: `pending`, `in_progress`, `completed`, `blocked`

**Dependency auto-resolution**: When a blocking task completes, dependent tasks automatically change from `blocked` to `pending`.

**Task locking**: When a task moves to `in_progress`, it is locked by the calling agent. Other agents cannot claim it unless they use `--force`. Stale locks from dead agents are automatically released.

### Agent Spawning

**IMPORTANT**: Always use the default command (`openclaw`) — do NOT override to `claude` or other agents. The default handles permissions, prompt injection, and nesting detection correctly. If you specify `claude` as the command, agents will get stuck on interactive permission prompts.

```bash
# Default (RECOMMENDED): spawns openclaw tui in tmux with prompt
agentteam spawn -t <team> -n <name> --task "<task description>"

# Explicit backend (still uses openclaw by default)
agentteam spawn tmux -t <team> -n <name> --task "<task>"
agentteam spawn subprocess -t <team> -n <name> --task "<task>"

# With git worktree isolation
agentteam spawn -t <team> -n <name> --task "<task>" --workspace --repo /path/to/repo
```

Each spawned agent gets:
- Its own tmux window (visible via `board attach`)
- Its own git worktree branch (`agentteam/{team}/{agent}`)
- An auto-injected coordination prompt (how to use agentteam CLI)
- Environment variables: `AGENTTEAM_AGENT_NAME`, `AGENTTEAM_TEAM_NAME`, etc.

**Spawn safety features:**
- Commands are pre-validated before launch — you get a clear error if the agent CLI is not installed
- If a spawn fails, the registered team member and worktree are automatically rolled back
- Claude Code and Codex workspace trust prompts are auto-confirmed in fresh worktrees

### Messaging

| Command | Description |
|---------|-------------|
| `agentteam inbox send <team> <to> "<msg>" --from <sender>` | Point-to-point message |
| `agentteam inbox broadcast <team> "<msg>" --from <sender>` | Broadcast to all |
| `agentteam inbox peek <team> -a <agent>` | Peek without consuming |
| `agentteam inbox receive <team>` | Consume messages |
| `agentteam inbox log <team>` | View message history |

### Monitoring

| Command | Description |
|---------|-------------|
| `agentteam board show <team>` | Kanban board (rich terminal) |
| `agentteam board overview` | All teams overview |
| `agentteam board live <team>` | Live-refreshing board |
| `agentteam board attach <team>` | Tmux tiled view |
| `agentteam board serve --port 8080` | Web dashboard |

### Cost Tracking

| Command | Description |
|---------|-------------|
| `agentteam cost report <team> --input-tokens <N> --output-tokens <N> --cost-cents <N>` | Report usage |
| `agentteam cost show <team>` | Show summary |
| `agentteam cost budget <team> <dollars>` | Set budget |

### Templates

| Command | Description |
|---------|-------------|
| `agentteam template list` | List available templates |
| `agentteam template show <name>` | Show template details |
| `agentteam launch <template> [--team-name <name>] [--goal "<goal>"]` | Launch from template |

**Built-in templates**: `hedge-fund`, `code-review`, `research-paper`

### Configuration

```bash
agentteam config show                           # Show all settings
agentteam config set transport file             # Set transport backend
agentteam config set skip_permissions true      # Auto-skip permission prompts
agentteam config health                         # System health check
```

### Other Commands

| Command | Description |
|---------|-------------|
| `agentteam lifecycle idle <team> --agent <name>` | Report agent idle |
| `agentteam session save <team> --session-id <id>` | Save session for resume |
| `agentteam plan submit <team> "<plan>" --from <agent>` | Submit plan for approval (team-scoped storage) |
| `agentteam workspace list <team>` | List git worktrees |
| `agentteam workspace merge <team> --agent <name>` | Merge agent branch |

## JSON Output

Add `--json` before any subcommand for machine-readable output:

```bash
agentteam --json task list my-team
agentteam --json team status my-team
```

## Typical Workflow

1. **User says**: "Create a team to build a web app"
2. **You do**: `agentteam team spawn-team webapp -d "Build web app" -n leader`
3. **Create tasks**: Use `agentteam task create` with `--blocked-by` for dependencies
4. **Spawn agents**: Use `agentteam spawn` for each worker
5. **Monitor**: Start a background polling loop immediately — do NOT wait for user to ask
6. **Communicate**: Use `agentteam inbox broadcast` for team-wide updates
7. **Deliver**: Proactively send final results to the user as soon as all tasks complete
8. **Cleanup**: `agentteam cost show`, `agentteam task stats`, merge worktrees, then `agentteam team cleanup webapp --force`

## Leader Orchestration Pattern

When YOU are the leader agent, follow this pattern to autonomously manage a swarm:

### Phase 1: Analyze & Plan
```
1. Understand the user's goal
2. Break it into independent subtasks
3. Identify dependencies between tasks (what must finish before what)
4. Decide how many worker agents are needed
```

### Phase 2: Setup
```bash
# Create team
agentteam team spawn-team <team> -d "<goal description>" -n leader

# Create tasks with dependency chains
agentteam task create <team> "Design API" -o architect
# Save the returned task ID (e.g., abc123)
agentteam task create <team> "Build backend" -o backend --blocked-by abc123
agentteam task create <team> "Build frontend" -o frontend --blocked-by abc123
agentteam task create <team> "Integration tests" -o tester --blocked-by <backend-id>,<frontend-id>
```

### Phase 3: Spawn Workers
```bash
# Each spawn launches an openclaw tui in its own tmux window
agentteam spawn -t <team> -n architect --task "Design REST API schema for <goal>"
agentteam spawn -t <team> -n backend --task "Implement backend based on API schema"
agentteam spawn -t <team> -n frontend --task "Build React frontend"
agentteam spawn -t <team> -n tester --task "Write and run integration tests"
```

### Phase 4: Monitor Loop

**IMPORTANT**: Start monitoring immediately after spawning — do NOT wait for the user to ask for status updates. Run the monitor loop in the background right away so you can:
1. **Push mid-progress updates proactively** — when ~50% of tasks complete, send the user a brief status update (e.g. "4/7 agents done, 3 still working"). Do NOT wait for them to ask.
2. **Deliver final results immediately** when all tasks complete.

```bash
# Poll task status every 30-60 seconds
while true; do
  agentteam --json task list <team> | python3 -c "
import sys, json
tasks = json.load(sys.stdin)
done = sum(1 for t in tasks if t['status'] == 'completed')
total = len(tasks)
print(f'{done}/{total} complete')
if done == total: print('ALL DONE'); sys.exit(0)
"
  # Check for messages from workers
  agentteam inbox receive <team>
  # IMPORTANT: Send a mid-progress update to the user when roughly half the tasks are done
  sleep 30
done
```

### Phase 5: Converge & Report

**IMPORTANT**: Proactively deliver results to the user as soon as all tasks complete. Do NOT wait for the user to ask. Include the final output, a summary, and cost/timing stats. ALWAYS merge worktrees and clean up.

```bash
# After all tasks complete — do ALL of these steps:
agentteam board show <team>           # Final status
agentteam cost show <team>            # Total cost — include in report to user
agentteam task stats <team>           # Timing stats — include in report to user
# Merge each worker's branch back to main
for agent in <agent1> <agent2> ...; do
  agentteam workspace merge <team> --agent $agent
done
agentteam team cleanup <team> --force  # Clean up — ALWAYS do this last
# Then: send the final deliverables to the user immediately
```

### Decision Rules for the Leader
- **Independent tasks** → spawn workers in parallel
- **Sequential tasks** → use `--blocked-by` to chain them; AgentTeam auto-unblocks
- **Worker asks for help** → check inbox, provide guidance via `inbox send`
- **Worker stuck** → check task status; if `in_progress` too long, send a nudge via `inbox send`
- **Worker done** → verify result via inbox message, then move to next phase
- **All done** → merge worktrees, deliver results to user proactively, then cleanup
- **Always** → start background monitoring immediately after spawn; never wait for user to ask for status

## Data Location

All state stored in `~/.agentteam/`:
- Teams: `~/.agentteam/teams/<team>/config.json`
- Tasks: `~/.agentteam/tasks/<team>/task-<id>.json` (with `fcntl` file locking for concurrent safety)
- Plans: `~/.agentteam/plans/<team>/<agent>-<plan_id>.md` (team-scoped, isolated per team)
- Messages: `~/.agentteam/teams/<team>/inboxes/<agent>/msg-*.json`
- Costs: `~/.agentteam/costs/<team>/`
