# ClawTeam CLI Reference

## Overview

ClawTeam provides a command-line interface for managing multi-agent teams.

## Installation

```bash
pip install clawteam
# or
poetry add clawteam
```

## Quick Start

```bash
# Create a new team
clawteam team spawn-team my-team -d "My project"

# Spawn an agent
clawteam spawn --team my-team --agent-name worker1 --task "Implement feature X"

# Check team status
clawteam team status my-team

# View the board
clawteam board attach my-team
```

## Commands

### Team Management

#### `clawteam team spawn-team`
Create a new team.

```bash
clawteam team spawn-team <team-name> [OPTIONS]

Options:
  -d, --description TEXT    Team description
  -n, --leader TEXT          Leader agent name
  -t, --template TEXT        Team template (dev-team, code-review, etc.)
```

**Examples:**
```bash
clawteam team spawn-team my-team -d "My awesome project"
clawteam team spawn-team dev-team -t dev-team-max
```

#### `clawteam team list`
List all teams.

```bash
clawteam team list [OPTIONS]

Options:
  --active          Show only active teams
  --format TABLE|JSON|YAML  Output format
```

#### `clawteam team status`
Show team status.

```bash
clawteam team status <team-name>
```

#### `clawteam team delete`
Delete a team.

```bash
clawteam team delete <team-name> [OPTIONS]

Options:
  --force           Skip confirmation
```

---

### Agent Management

#### `clawteam spawn`
Spawn a new agent in a team.

```bash
clawteam spawn --team <team-name> --agent-name <name> --task <task> [OPTIONS]

Options:
  --team TEXT              Team name (required)
  --agent-name TEXT        Agent name (required)
  --task TEXT              Task description (required)
  --agent openclaw|claude-code|codex|nanobot  Agent backend
```

**Examples:**
```bash
clawteam spawn --team my-team --agent-name worker1 --task "Write tests"
clawteam spawn --team my-team --agent-name dev1 --task "Implement API" --agent claude-code
```

#### `clawteam agents list`
List all agents in a team.

```bash
clawteam agents list <team-name>
```

#### `clawteam agents kill`
Kill an agent.

```bash
clawteam agents kill <team-name> <agent-name>
```

---

### Task Management

#### `clawteam task create`
Create a new task.

```bash
clawteam task create <team-name> [OPTIONS]

Options:
  -t, --title TEXT        Task title (required)
  -d, --description TEXT  Task description
  -p, --priority low|medium|high  Task priority
  -o, --owner TEXT        Task owner
```

**Examples:**
```bash
clawteam task create my-team -t "Implement login" -p high -o alice
```

#### `clawteam task list`
List tasks in a team.

```bash
clawteam task list <team-name> [OPTIONS]

Options:
  --status TEXT           Filter by status (todo|in_progress|done)
  --owner TEXT            Filter by owner
  --format TABLE|JSON     Output format
```

#### `clawteam task update`
Update a task.

```bash
clawteam task update <team-name> <task-id> [OPTIONS]

Options:
  --status TEXT           New status
  --owner TEXT            New owner
  --priority TEXT         New priority
```

#### `clawteam task delete`
Delete a task.

```bash
clawteam task delete <team-name> <task-id>
```

---

### Inbox / Messaging

#### `clawteam inbox send`
Send a message to an agent.

```bash
clawteam inbox send <team-name> <recipient> <message> [OPTIONS]

Options:
  --from TEXT             Sender name
```

**Examples:**
```bash
clawteam inbox send my-team alice "Task completed!"
clawteam inbox send my-team leader "All tests passing"
```

#### `clawteam inbox list`
List messages in your inbox.

```bash
clawteam inbox list [OPTIONS]

Options:
  --team TEXT             Team name
  --unread               Show only unread
  --format TABLE|JSON     Output format
```

#### `clawteam inbox read`
Read a message.

```bash
clawteam inbox read <message-id>
```

---

### Board / Dashboard

#### `clawteam board serve`
Start the web dashboard server.

```bash
clawteam board serve [OPTIONS]

Options:
  --port PORT            Port to listen on (default: 8080)
  --host HOST            Host to bind to (default: 127.0.0.1)
  --open                 Open browser automatically
```

**Examples:**
```bash
clawteam board serve --port 8080 --open
```

#### `clawteam board attach`
Attach to a team's real-time board.

```bash
clawteam board attach <team-name>
```

#### `clawteam board token-stats`
Show token usage statistics.

```bash
clawteam board token-stats [OPTIONS]

Options:
  --team TEXT            Team name
  --days INTEGER         Days to look back (default: 7)
```

---

### Configuration

#### `clawteam config list`
List current configuration.

```bash
clawteam config list
```

#### `clawteam config set`
Set a configuration value.

```bash
clawteam config set <key> <value>
```

**Example:**
```bash
clawteam config set default_agent openclaw
```

---

## Team Templates

ClawTeam supports team templates for common configurations:

### Built-in Templates

| Template | Description |
|----------|-------------|
| `dev-team` | Development team with leader, backend, frontend, tester |
| `dev-team-max` | Full development team with architect |
| `code-review` | Code review team with security, performance, maintainability checks |
| `dev-team-mix` | Mixed fullstack team |
| `office-team` | Office team with PPT, Excel, data analyst |

### Creating Custom Templates

Create a TOML file in `~/.clawteam/templates/`:

```toml
[template]
name = "my-template"
description = "My custom team template"

[[template.members]]
name = "leader"
role = "leader"
roleColor = "#FF5722"
prompt = "You are the team leader..."

[[template.members]]
name = "developer"
role = "developer"
roleColor = "#2196F3"
prompt = "You are a developer..."
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CLAWTEAM_HOME` | Home directory for ClawTeam | `~/.clawteam` |
| `CLAWTEAM_DB` | Database path | `~/.clawteam/db` |
| `OPENCLAW_GATEWAY_TOKEN` | OpenClaw gateway token | - |
| `OPENCLAW_GATEWAY_URL` | OpenClaw gateway URL | `http://localhost:18789` |

---

## Shell Completion

### Bash

```bash
# Add to ~/.bashrc
eval "$(_CLAWTEAM_COMPLETE=bash_source clawteam)"
```

### Zsh

```bash
# Add to ~/.zshrc
eval "$(_CLAWTEAM_COMPLETE=zsh_source clawteam)"
```

### Fish

```bash
# Add to ~/.config/fish/completions/clawteam.fish
clawteam --completion-script fish > ~/.config/fish/completions/clawteam.fish
```

---

## Debugging

### Verbose Output

```bash
clawteam --verbose spawn --team my-team --agent-name worker1 --task "Test"
```

### Log File

```bash
clawteam --log-file /tmp/clawteam.log board serve
```

### Check Agent Status

```bash
clawteam agents list my-team --verbose
```

---

## Troubleshooting

### Agent Not Responding

```bash
# Check agent status
clawteam agents list my-team

# Kill and respawn
clawteam agents kill my-team worker1
clawteam spawn --team my-team --agent-name worker1 --task "Same task"
```

### Database Locked

```bash
# Remove lock file
rm ~/.clawteam/db/*.lock
```

### Port Already in Use

```bash
# Use different port
clawteam board serve --port 8081
```
