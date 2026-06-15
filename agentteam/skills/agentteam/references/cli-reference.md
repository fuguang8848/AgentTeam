# AgentTeam CLI Complete Reference

## Global Options

```
agentteam [--version] [--json] [--data-dir PATH] <command>
```

- `--json` — Output JSON instead of human-readable text. Apply before subcommand: `agentteam --json team discover`
- `--data-dir PATH` — Override data directory (default: `~/.agentteam`)

## Environment Variables

AgentTeam agents use these environment variables for identity:

| Variable | Description | Example |
|----------|-------------|---------|
| `AGENTTEAM_AGENT_ID` | Unique agent identifier | `a1b2c3d4e5f6` |
| `AGENTTEAM_AGENT_NAME` | Human-readable agent name | `alice` |
| `AGENTTEAM_AGENT_TYPE` | Agent role type | `leader`, `general-purpose`, `researcher` |
| `AGENTTEAM_TEAM_NAME` | Team the agent belongs to | `dev-team` |
| `AGENTTEAM_DATA_DIR` | Override data directory | `/tmp/agentteam-data` |

When spawning agents via `agentteam spawn`, these are set automatically.

---

## Team Commands (`agentteam team`)

### `team spawn-team`

Create a new team and register the leader.

```bash
agentteam team spawn-team <name> [options]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--description, -d` | Team description | `""` |
| `--agent-name, -n` | Leader agent name | `"leader"` |
| `--agent-type` | Leader agent type | `"leader"` |

Example:
```bash
agentteam team spawn-team dev-team -d "Backend development team" -n alice
```

### `team discover`

List all existing teams.

```bash
agentteam team discover
agentteam --json team discover
```

Returns: name, description, leadAgentId, memberCount for each team.

### `team status`

Show team configuration and member list.

```bash
agentteam team status <team>
```

### `team request-join`

Request to join a team. Blocks until leader approves/rejects or timeout.

```bash
agentteam team request-join <team> <proposed-name> [options]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--capabilities, -c` | Agent capabilities description | `""` |
| `--timeout, -t` | Timeout in seconds | `60` |

### `team approve-join`

Approve a pending join request (leader only).

```bash
agentteam team approve-join <team> <request-id> [--assigned-name NAME]
```

### `team reject-join`

Reject a pending join request (leader only).

```bash
agentteam team reject-join <team> <request-id> [--reason TEXT]
```

### `team cleanup`

Delete a team and all its data (config, inboxes, tasks).

```bash
agentteam team cleanup <team> [--force]
```

---

## Inbox Commands (`agentteam inbox`)

### `inbox send`

Send a point-to-point message to an agent.

```bash
agentteam inbox send <team> <to> <content> [options]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--key, -k` | Routing key | `None` |
| `--type` | Message type | `"message"` |

### `inbox broadcast`

Broadcast a message to all team members (except sender).

```bash
agentteam inbox broadcast <team> <content> [options]
```

### `inbox receive`

Receive and consume messages from inbox (destructive — messages are deleted).

```bash
agentteam inbox receive <team> [options]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--agent, -a` | Agent name (default: from env) | env |
| `--limit, -l` | Max messages to receive | `10` |

### `inbox peek`

Peek at messages without consuming them (non-destructive).

```bash
agentteam inbox peek <team> [--agent NAME]
```

### `inbox watch`

Watch inbox for new messages in real-time (blocking, Ctrl+C to stop).

```bash
agentteam inbox watch <team> [--agent NAME] [--poll-interval 1.0]
```

---

## Task Commands (`agentteam task`)

### `task create`

Create a new task.

```bash
agentteam task create <team> <subject> [options]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--description, -d` | Task description | `""` |
| `--owner, -o` | Owner agent name | `""` |
| `--blocks` | Comma-separated task IDs this blocks | `None` |
| `--blocked-by` | Comma-separated task IDs blocking this | `None` |

Example:
```bash
agentteam task create dev-team "Implement auth" -o alice -d "Add JWT authentication"
```

### `task get`

Get a single task by ID.

```bash
agentteam task get <team> <task-id>
```

### `task update`

Update a task's status, owner, or dependencies.

```bash
agentteam task update <team> <task-id> [options]
```

| Option | Description |
|--------|-------------|
| `--status, -s` | New status: `pending`, `in_progress`, `completed`, `blocked` |
| `--owner, -o` | New owner |
| `--subject` | New subject |
| `--description, -d` | New description |
| `--add-blocks` | Comma-separated task IDs to add to blocks |
| `--add-blocked-by` | Comma-separated task IDs to add to blocked-by |

When a task is marked `completed`, any tasks blocked by it are automatically unblocked (moved from `blocked` to `pending` if no other blockers remain).

### `task list`

List all tasks for a team, with optional filters.

```bash
agentteam task list <team> [--status STATUS] [--owner NAME]
```

---

## Board Commands (`agentteam board`)

### `board show`

Show detailed kanban board for a team: header, members with inbox counts, 4-column task board.

```bash
agentteam board show <team>
agentteam --json board show <team>
```

### `board overview`

Show summary of all teams in a table.

```bash
agentteam board overview
agentteam --json board overview
```

### `board live`

Live-refreshing kanban board. Auto-refreshes at interval. Ctrl+C to stop.

```bash
agentteam board live <team> [--interval 2.0]
```

---

## Plan Commands (`agentteam plan`)

### `plan submit`

Submit a plan for leader approval. Content can be inline text or a file path.

```bash
agentteam plan submit <team> <agent> <plan-content-or-file> [--summary TEXT]
```

### `plan approve`

Approve a submitted plan.

```bash
agentteam plan approve <team> <plan-id> <agent> [--feedback TEXT]
```

### `plan reject`

Reject a submitted plan.

```bash
agentteam plan reject <team> <plan-id> <agent> [--feedback TEXT]
```

---

## Lifecycle Commands (`agentteam lifecycle`)

### `lifecycle request-shutdown`

Request an agent to shut down.

```bash
agentteam lifecycle request-shutdown <team> <from-agent> <to-agent> [--reason TEXT]
```

### `lifecycle approve-shutdown`

Agent agrees to shut down.

```bash
agentteam lifecycle approve-shutdown <team> <request-id> <agent>
```

### `lifecycle reject-shutdown`

Agent rejects shutdown request.

```bash
agentteam lifecycle reject-shutdown <team> <request-id> <agent> [--reason TEXT]
```

### `lifecycle idle`

Send idle notification to leader (agent has no more work).

```bash
agentteam lifecycle idle <team> [--last-task ID] [--task-status STATUS]
```

---

## Spawn Command

Spawn a new agent process with team environment variables.

```bash
agentteam spawn <backend> <command...> [options]
```

| Option | Description | Default |
|--------|-------------|---------|
| `--team, -t` | Team name | `"default"` |
| `--agent-name, -n` | Agent name | auto-generated |
| `--agent-type` | Agent type | `"general-purpose"` |

Backends: `subprocess`, `tmux`

Example:
```bash
agentteam spawn subprocess claude --team dev-team --agent-name bob --agent-type researcher
```

---

## Identity Commands (`agentteam identity`)

### `identity show`

Show current agent identity from environment variables.

```bash
agentteam identity show
```

### `identity set`

Print shell export commands to set identity environment variables.

```bash
eval $(agentteam identity set --agent-name alice --team dev-team)
```

---

## Data Model

### Task Statuses

| Status | Description |
|--------|-------------|
| `pending` | Not yet started |
| `in_progress` | Currently being worked on |
| `completed` | Done (auto-unblocks dependents) |
| `blocked` | Waiting on other tasks |

### Message Types

| Type | Description |
|------|-------------|
| `message` | General point-to-point message |
| `broadcast` | Broadcast to all members |
| `join_request` | Request to join team |
| `join_approved` / `join_rejected` | Join response |
| `plan_approval_request` | Plan submitted for review |
| `plan_approved` / `plan_rejected` | Plan response |
| `shutdown_request` | Shutdown request |
| `shutdown_approved` / `shutdown_rejected` | Shutdown response |
| `idle` | Agent idle notification |

### File Storage Layout

```
~/.agentteam/
├── teams/{team}/
│   ├── config.json          # TeamConfig (name, members, leader)
│   └── inboxes/{agent}/     # msg-{timestamp}-{uuid}.json files
├── tasks/{team}/
│   └── task-{id}.json       # Individual task files
└── plans/
    └── {agent}-{id}.md      # Plan documents
```
