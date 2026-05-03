# ClawTeam-OpenClaw CLI Reference

> **Version**: v0.5.1

---

## Overview

ClawTeam CLI provides commands for team management, agent spawning, and system monitoring. All commands follow the pattern: `clawteam <resource> <action> [options]`

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
clawteam team create <team-name> [options]
```

**Options:**
- `--backend <backend>`: Backend to use (`tmux`, `subprocess`, `openclaw_sdk`, `auto`)
- `--transport <transport>`: Transport layer (`file`, `redis`, `p2p`)
- `--template <template>`: Team template to use

**Examples:**
```bash
# Create team with default settings
clawteam team create my-team

# Create team with tmux backend
clawteam team create my-team --backend tmux

# Create from template
clawteam team create ai-team --template research
```

### team list / team discover

List all teams.

```bash
clawteam team list
clawteam team discover
```

### team status

Show team status and members.

```bash
clawteam team status <team-name>
```

### team cleanup

Delete a team and all its data.

```bash
clawteam team cleanup <team-name> [options]
```

**Options:**
- `--force`: Skip confirmation

### team request-join

Request to join a team.

```bash
clawteam team request-join <team-name>
```

### team approve-join

Approve a join request.

```bash
clawteam team approve-join <team-name> <agent-name>
```

### team reject-join

Reject a join request.

```bash
clawteam team reject-join <team-name> <agent-name>
```

---

## Agent Commands

### spawn

Spawn a new agent.

```bash
clawteam spawn [options]
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
clawteam spawn --agent-name worker --prompt "Do analysis"

# Spawn in specific team with parent
clawteam spawn --team my-team --agent-name analyzer \
  --parent agent-1 --prompt "Analyze code"

# Spawn with custom workspace
clawteam spawn --agent-name coder --workspace /tmp/project \
  --backend tmux
```

### agents list

List all agents.

```bash
clawteam agents list [options]
```

**Options:**
- `--team <team>`: Filter by team
- `--status <status>`: Filter by status (`running`, `stopped`)

### agent send

Send message to an agent.

```bash
clawteam agent send <agent-name> <message> [options]
```

**Options:**
- `--team <team>`: Team name

### agent inbox

View agent inbox messages.

```bash
clawteam agent inbox <agent-name> [options]
```

**Options:**
- `--team <team>`: Team name
- `--json`: Output as JSON

### agent terminate

Terminate an agent.

```bash
clawteam agent terminate <agent-name> [options]
```

**Options:**
- `--team <team>`: Team name
- `--force`: Skip confirmation

### agent terminate-children

Terminate all child agents.

```bash
clawteam agent terminate-children <agent-name> [options]
```

**Options:**
- `--team <team>`: Team name

### agent list-children

List child agents.

```bash
clawteam agent list-children <agent-name> [options]
```

**Options:**
- `--team <team>`: Team name

### agent show-parent

Show parent agent.

```bash
clawteam agent show-parent <agent-name> [options]
```

**Options:**
- `--team <team>`: Team name

### agent register-child

Register a child agent relationship.

```bash
clawteam agent register-child <parent-name> <child-name> [options]
```

**Options:**
- `--team <team>`: Team name

### agent terminate-tree

Terminate entire agent tree (parent + all children).

```bash
clawteam agent terminate-tree <agent-name> [options]
```

**Options:**
- `--team <team>`: Team name

---

## Lifecycle Commands

### lifecycle on-exit

Register lifecycle hook for agent exit.

```bash
clawteam lifecycle on-exit --team <team> --agent <agent> <action>
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
clawteam board serve [options]
```

**Options:**
- `--port <port>`: Port to listen on (default: 8080)
- `--host <host>`: Host to bind to (default: 0.0.0.0)
- `--auth <token>`: Authentication token

**Examples:**
```bash
# Start board on default port
clawteam board serve

# Start on custom port with auth
clawteam board serve --port 9000 --auth my-secret-token

# Bind to localhost only
clawteam board serve --host 127.0.0.1
```

### board status

Show board status.

```bash
clawteam board status
```

---

## Session Commands

### session list

List all sessions.

```bash
clawteam session list [options]
```

**Options:**
- `--team <team>`: Filter by team
- `--status <status>`: Filter by status
- `--json`: Output as JSON

### session show

Show session details.

```bash
clawteam session show <session-id>
```

### session send

Send message to session.

```bash
clawteam session send <session-id> <message>
```

### session terminate

Terminate a session.

```bash
clawteam session terminate <session-id> [options]
```

**Options:**
- `--force`: Skip confirmation

---

## Inbox Commands

### inbox list

List inbox messages for current user.

```bash
clawteam inbox list [options]
```

**Options:**
- `--team <team>`: Filter by team
- `--unread-only`: Only show unread messages
- `--json`: Output as JSON

### inbox read

Read a specific message.

```bash
clawteam inbox read <message-id>
```

### inbox reply

Reply to a message.

```bash
clawteam inbox reply <message-id> <content>
```

### inbox delete

Delete a message.

```bash
clawteam inbox delete <message-id>
```

---

## Events Commands

### events list

List events.

```bash
clawteam events list [options]
```

**Options:**
- `--team <team>`: Filter by team
- `--type <type>`: Filter by event type
- `--limit <n>`: Max events to show (default: 100)
- `--json`: Output as JSON

### events stream

Stream events in real-time.

```bash
clawteam events stream [options]
```

**Options:**
- `--team <team>`: Team name

---

## Config Commands

### config show

Show current configuration.

```bash
clawteam config show [options]
```

**Options:**
- `--json`: Output as JSON

### config set

Set a configuration value.

```bash
clawteam config set <key> <value>
```

**Examples:**
```bash
clawteam config set agents.max_concurrent 10
clawteam config set alerts.enabled true
```

### config get

Get a configuration value.

```bash
clawteam config get <key>
```

---

## Database Commands

### db status

Show database status.

```bash
clawteam db status
```

### db backup

Create database backup.

```bash
clawteam db backup [options]
```

**Options:**
- `--output <path>`: Output file path

### db restore

Restore from backup.

```bash
clawteam db restore <backup-file>
```

---

## Monitor Commands

### monitor usage

Show token usage statistics.

```bash
clawteam monitor usage [options]
```

**Options:**
- `--period <period>`: Period (`daily`, `weekly`, `monthly`)
- `--json`: Output as JSON

### monitor costs

Show cost breakdown.

```bash
clawteam monitor costs [options]
```

**Options:**
- `--period <period>`: Period (`daily`, `weekly`, `monthly`)
- `--json`: Output as JSON

---

## Debug Commands

### debug logs

Show recent logs.

```bash
clawteam debug logs [options]
```

**Options:**
- `--level <level>`: Log level (`debug`, `info`, `warning`, `error`)
- `--limit <n>`: Max log lines (default: 50)
- `--follow`: Follow log output

### debug test-connection

Test connection to remote services.

```bash
clawteam debug test-connection
```

### debug doctor

Run diagnostics.

```bash
clawteam debug doctor
```

---

## Help Commands

### help

Show general help or help for specific command.

```bash
clawteam help
clawteam help <command>
```

### version

Show version information.

```bash
clawteam version
```

---

## Shell Completion

### bash

```bash
# Add to ~/.bashrc
eval "$(clawteam --completion bash)"
```

### zsh

```bash
# Add to ~/.zshrc
eval "$(clawteam --completion zsh)"
```

### fish

```bash
# Add to ~/.config/fish/config.fish
clawteam --completion fish | source
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
  file: logs/clawteam.log

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

*Last updated: 2026-05-04*
