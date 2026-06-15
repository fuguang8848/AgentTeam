# AgentTeam-OpenClaw CLI Reference

> **Version**: v0.5.4

---

## Overview

AgentTeam CLI provides commands for team management, agent spawning, and system monitoring. All commands follow the pattern: `agentteam <resource> <action> [options]`

---

## Global Options

| Option | Description |
|--------|-------------|
| `--help` | Show help for any command |
| `--version` | Show version |
| `--config <path>` | Custom config file path |
| `--debug` | Enable debug mode |
| `--quiet` | Suppress output |

---

## Team Commands

### team create

Create a new team.

```bash
agentteam team create <team-name> [options]
```

**Options:**
- `--backend <backend>`: Backend to use (`tmux`, `subprocess`, `openclaw_sdk`, `auto`)
- `--transport <transport>`: Transport layer (`file`, `redis`, `p2p`)
- `--template <template>`: Team template to use

**Examples:**
```bash
# Create team with default settings
agentteam team create my-team

# Create team with tmux backend
agentteam team create my-team --backend tmux

# Create from template
agentteam team create ai-team --template research
```

### team list / team discover

List all teams.

```bash
agentteam team list
agentteam team discover
```

### team status

Show team status and members.

```bash
agentteam team status <team-name>
```

### team cleanup

Delete a team and all its data.

```bash
agentteam team cleanup <team-name> [options]
```

**Options:**
- `--force`: Skip confirmation

### team request-join

Request to join a team.

```bash
agentteam team request-join <team-name>
```

### team approve-join

Approve a join request.

```bash
agentteam team approve-join <team-name> <agent-name>
```

### team reject-join

Reject a join request.

```bash
agentteam team reject-join <team-name> <agent-name>
```

---

## Agent Commands

### spawn

Spawn a new agent.

```bash
agentteam spawn [options]
```

**Options:**
- `--team <team>`: Team name (default: default)
- `--agent-name <name>`: Agent name
- `--agent-type <type>`: Agent type (`general-purpose`, `coding`, `research`)
- `--model <model>`: Model to use
- `--prompt <prompt>`: Initial prompt
- `--parent <parent-id>`: Parent agent ID
- `--workspace <path>`: Workspace directory
- `--backend <backend>`: Backend override

**Examples:**
```bash
# Spawn agent in default team
agentteam spawn --agent-name worker --prompt "Do analysis"

# Spawn in specific team with parent
agentteam spawn --team my-team --agent-name analyzer \
  --parent agent-1 --prompt "Analyze code"

# Spawn with custom workspace
agentteam spawn --agent-name coder --workspace /tmp/project \
  --backend tmux
```

### agents list

List all agents.

```bash
agentteam agents list [options]
```

**Options:**
- `--team <team>`: Filter by team
- `--status <status>`: Filter by status (`running`, `stopped`)

### agent send

Send message to an agent.

```bash
agentteam agent send <agent-name> <message> [options]
```

**Options:**
- `--team <team>`: Team name

### agent inbox

View agent inbox messages.

```bash
agentteam agent inbox <agent-name> [options]
```

**Options:**
- `--team <team>`: Team name
- `--json`: Output as JSON

### agent terminate

Terminate an agent.

```bash
agentteam agent terminate <agent-name> [options]
```

**Options:**
- `--team <team>`: Team name
- `--force`: Skip confirmation

### agent terminate-children

Terminate all child agents.

```bash
agentteam agent terminate-children <agent-name> [options]
```

**Options:**
- `--team <team>`: Team name

### agent list-children

List child agents.

```bash
agentteam agent list-children <agent-name> [options]
```

**Options:**
- `--team <team>`: Team name

### agent show-parent

Show parent agent.

```bash
agentteam agent show-parent <agent-name> [options]
```

**Options:**
- `--team <team>`: Team name

### agent register-child

Register a child agent relationship.

```bash
agentteam agent register-child <parent-name> <child-name> [options]
```

**Options:**
- `--team <team>`: Team name

### agent terminate-tree

Terminate entire agent tree (parent + all children).

```bash
agentteam agent terminate-tree <agent-name> [options]
```

**Options:**
- `--team <team>`: Team name

---

## Lifecycle Commands

### lifecycle on-exit

Register lifecycle hook for agent exit.

```bash
agentteam lifecycle on-exit --team <team> --agent <agent> <action>
```

**Actions:**
- `cleanup`: Clean up workspace
- `notify`: Send notification
- `archive`: Archive session data

---

## Board Commands

### board serve

Start the web board server.

```bash
agentteam board serve [options]
```

**Options:**
- `--port <port>`: Port to listen on (default: 8080)
- `--host <host>`: Host to bind to (default: 0.0.0.0)
- `--auth <token>`: Authentication token

**Examples:**
```bash
# Start board on default port
agentteam board serve

# Start on custom port with auth
agentteam board serve --port 9000 --auth my-secret-token

# Bind to localhost only
agentteam board serve --host 127.0.0.1
```

### board status

Show board status.

```bash
agentteam board status
```

---

## Session Commands

### session list

List all sessions.

```bash
agentteam session list [options]
```

**Options:**
- `--team <team>`: Filter by team
- `--status <status>`: Filter by status
- `--json`: Output as JSON

### session show

Show session details.

```bash
agentteam session show <session-id>
```

### session send

Send message to session.

```bash
agentteam session send <session-id> <message>
```

### session terminate

Terminate a session.

```bash
agentteam session terminate <session-id> [options]
```

**Options:**
- `--force`: Skip confirmation

---

## Inbox Commands

### inbox list

List inbox messages for current user.

```bash
agentteam inbox list [options]
```

**Options:**
- `--team <team>`: Filter by team
- `--unread-only`: Only show unread messages
- `--json`: Output as JSON

### inbox read

Read a specific message.

```bash
agentteam inbox read <message-id>
```

### inbox reply

Reply to a message.

```bash
agentteam inbox reply <message-id> <content>
```

### inbox delete

Delete a message.

```bash
agentteam inbox delete <message-id>
```

---

## Events Commands

### events list

List events.

```bash
agentteam events list [options]
```

**Options:**
- `--team <team>`: Filter by team
- `--type <type>`: Filter by event type
- `--limit <n>`: Max events to show (default: 100)
- `--json`: Output as JSON

### events stream

Stream events in real-time.

```bash
agentteam events stream [options]
```

**Options:**
- `--team <team>`: Team name

---

## Config Commands

### config show

Show current configuration.

```bash
agentteam config show [options]
```

**Options:**
- `--json`: Output as JSON

### config set

Set a configuration value.

```bash
agentteam config set <key> <value>
```

**Examples:**
```bash
agentteam config set agents.max_concurrent 10
agentteam config set alerts.enabled true
```

### config get

Get a configuration value.

```bash
agentteam config get <key>
```

---

## Database Commands

### db status

Show database status.

```bash
agentteam db status
```

### db backup

Create database backup.

```bash
agentteam db backup [options]
```

**Options:**
- `--output <path>`: Output file path

### db restore

Restore from backup.

```bash
agentteam db restore <backup-file>
```

---

## Monitor Commands

### monitor usage

Show token usage statistics.

```bash
agentteam monitor usage [options]
```

**Options:**
- `--period <period>`: Period (`daily`, `weekly`, `monthly`)
- `--json`: Output as JSON

### monitor costs

Show cost breakdown.

```bash
agentteam monitor costs [options]
```

**Options:**
- `--period <period>`: Period (`daily`, `weekly`, `monthly`)
- `--json`: Output as JSON

---

## Daemon Commands

### daemon start

Start the agent daemon (`agentd`) in the background. The daemon manages persistent agent sessions and allows agents to stay alive between tasks.

```bash
agentteam daemon start
```

**Details:**
- Runs `agentd.py` as a background subprocess
- On Windows: uses TCP socket at `127.0.0.1:18792`
- On Unix/Linux/macOS: uses Unix domain socket at `~/.agentteam/agentd.sock`
- Saves PID to `~/.agentteam/agentd.pid`
- Automatically restores previously running agents on restart

### daemon stop

Stop the running agent daemon and all managed agents.

```bash
agentteam daemon stop
```

**Details:**
- Sends `stop` command to daemon via socket
- Gracefully shuts down all running agents
- Cleans up PID file

### daemon status

Check whether the daemon is currently running.

```bash
agentteam daemon status
```

**Details:**
- Checks if `~/.agentteam/agentd.pid` exists
- Verifies the process is alive via OS API
- Reports stale PID file if process is dead

### daemon list

List all agents currently managed by the daemon.

```bash
agentteam daemon list
```

**Output:**
| Column | Description |
|--------|-------------|
| Name | Agent name |
| Team | Team the agent belongs to |
| Type | Agent type (e.g. specialist) |
| Status | Running or Stopped |

### daemon spawn

Spawn a new persistent agent through the daemon. The agent stays alive and awaits further tasks.

```bash
agentteam daemon spawn --team <team> --agent-name <name> --prompt <task> [options]
```

**Required Options:**
- `--team <team>`: Team name
- `--agent-name <name>`: Name for the new agent
- `--prompt <task>`: Initial task prompt

**Optional Options:**
- `--agent-type <type>`: Agent type (default: `specialist`)

**Examples:**
```bash
# Spawn a persistent specialist agent
agentteam daemon spawn --team my-team --agent-name doc-writer \
  --prompt "Update the API documentation"

# Spawn with custom type
agentteam daemon spawn --team ai-team --agent-name researcher \
  --agent-type research --prompt "Analyze competition"
```

---

## Debug Commands

### debug logs

Show recent logs.

```bash
agentteam debug logs [options]
```

**Options:**
- `--level <level>`: Log level (`debug`, `info`, `warning`, `error`)
- `--limit <n>`: Max log lines (default: 50)
- `--follow`: Follow log output

### debug test-connection

Test connection to remote services.

```bash
agentteam debug test-connection
```

### debug doctor

Run diagnostics.

```bash
agentteam debug doctor
```

---

## Help Commands

### help

Show general help or help for specific command.

```bash
agentteam help
agentteam help <command>
```

### version

Show version information.

```bash
agentteam version
```

---

## Shell Completion

### bash

```bash
# Add to ~/.bashrc
eval "$(agentteam --completion bash)"
```

### zsh

```bash
# Add to ~/.zshrc
eval "$(agentteam --completion zsh)"
```

### fish

```bash
# Add to ~/.config/fish/config.fish
agentteam --completion fish | source
```

---

## Configuration File

Default location: `./config.yaml`

**Example config.yaml:**
```yaml
# Team settings
default_team: my-team
default_backend: tmux

# Agent settings
agents:
  max_concurrent: 10
  spawn_timeout: 60
  retry_attempts: 3

# Logging
logging:
  level: info
  file: logs/agentteam.log

# Alerts
alerts:
  enabled: true
  webhook_url: https://hooks.example.com/alerts

# Metrics
metrics:
  enabled: true
  storage_days: 30
```

---

*Last updated: 2026-05-04 | v0.5.4*
