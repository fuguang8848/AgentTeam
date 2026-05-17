# AgentTeam

Production-ready multi-agent swarm coordination framework. Built for OpenClaw, powered by AI agents themselves.

<p align="center">
  <strong>Self-organizing agent teams that collaborate, delegate, and deliver results.</strong>
</p>

<p align="center">
  <a href="https://github.com/openclaw/openclaw"><strong>Based on OpenClaw</strong></a>
  ·
  <a href="https://discord.com/invite/clawd"><strong>Community</strong></a>
  ·
  <a href="https://docs.openclaw.ai"><strong>Docs</strong></a>
</p>

---

## Why AgentTeam?

| | AgentTeam | Basic Agent Frameworks |
|---|---------|----------------------------|
| **Target** | AI agents coordinate themselves | Humans micromanage agents |
| **Setup** | `pip install` · done | Docker + configs + cloud APIs |
| **Monitoring** | **Web UI Dashboard** + tmux | CLI only |
| **Reliability** | **Retry + Structured Logs + Alerts** | None |
| **Security** | **API Auth + Token Isolation** | Usually none |
| **Observability** | **Audit Logs + Drift Detection** | None |
| **Quality** | **595+ tests, P0-P25 verified** | Ad-hoc |
| **Infrastructure** | Filesystem (no Redis needed) | Redis/message queues required |

---

## Features

### Multi-Agent Orchestration
- **Team Management**: Create, manage, and monitor agent teams with role-based assignments
- **Dynamic Task Distribution**: Intelligent routing based on agent capabilities
- **Message Passing**: Inter-agent communication with mailbox and inbox system

### Reliability
- **Auto-Retry**: Failed tasks automatically retried with exponential backoff
- **Structured Logging**: Consistent log format across all components
- **Alert System**: Configurable alerts for task failures and team events

### Security
- **API Authentication**: Token-based auth for all API endpoints
- **Token Isolation**: Each agent gets isolated credentials
- **Audit Logs**: Complete trail of all agent actions

### Observability
- **Real-time Dashboard**: Web UI for monitoring team activities
- **Event Tracking**: Track all team events and agent interactions
- **Drift Detection**: Detect when agent behavior deviates from expectations

---

## Quick Start

### Installation

```bash
pip install agentteam
```

Or install from source:

```bash
git clone https://github.com/YintaTriss/AgentTeam.git
cd AgentTeam
pip install -e .
```

### Initialize a Team

```bash
# Create a new team
agentteam init my-team

# Navigate to team directory
cd my-team
```

### Start the Team

```bash
# Start the team leader
agentteam start

# In another terminal, spawn agents
agentteam spawn --name worker-1 --role researcher
agentteam spawn --name worker-2 --role coder
```

### Using the Dashboard

```bash
# Start the web dashboard
agentteam dashboard
```

Then open http://localhost:8080 to monitor your team.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   CLI Layer                      │
│         (agentteam/cli/, team/, spawn/)         │
└─────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────┐
│                   Core SDK Layer                 │
│      (CTTeam, CTAgent, CTTask, CTMessage)        │
└─────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────┐
│               Orchestration Layer                 │
│     (orchestrator/, spawn/, session/, events/)   │
└─────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────┐
│                   Storage Layer                   │
│       (database/, store/, memory/, board/)       │
└─────────────────────────────────────────────────┘
```

---

## Documentation

For full documentation, visit [OpenClaw Docs](https://docs.openclaw.ai).

### Key Topics

- [CLI Reference](CLI.md) - Complete CLI command reference
- [API Documentation](API.md) - API reference
- [Deployment Guide](DEPLOY.md) - Deployment instructions
- [Architecture Review](ARCHITECTURE_REVIEW.md) - System architecture details

---

## License

MIT
