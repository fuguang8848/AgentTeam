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

> **AgentTeam** is a production-hardened fork of [HKUDS/ClawTeam](https://github.com/HKUDS/ClawTeam), purpose-built for OpenClaw users who need enterprise-grade multi-agent coordination.
>
> All upstream fixes are synced. This is not a demo — it's production software.

---

## Why Choose AgentTeam?

| | AgentTeam | Basic Agent Frameworks |
|---|---------|----------------------------|
| **Target** | AI agents coordinate themselves | Humans micromanage agents |
| **Setup** | `pip install -e .` · done | Docker + configs + cloud APIs |
| **Monitoring** | **Web UI Dashboard** + tmux | CLI only |
| **Reliability** | **Retry + Structured Logs + Alerts** | None |
| **Security** | **API Auth + Token Isolation** | Usually none |
| **Observability** | **Audit Logs + Drift Detection** | None |
| **Quality** | **595+ tests, P0-P25 verified** | Ad-hoc |
| **Infrastructure** | Filesystem (no Redis needed) | Redis/message queues required |

---

## Quick Start (5 Minutes)

```bash
# 1. Install
git clone https://github.com/YintaTriss/AgentTeam.git
cd AgentTeam
pip install -e .

# 2. Start Web Dashboard
agentteam board serve --port 8080

# 3. Tell AI to build a blog system using AgentTeam
# AI automatically creates team, delegates tasks, coordinates results
```

**Done.** No Redis. No Docker. No manual configuration required.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      AgentTeam-OpenClaw                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│   │ Web UI   │    │   CLI    │    │ REST API │             │
│   │Dashboard │    │  (tmux)  │    │  (Auth)  │             │
│   └────┬─────┘    └────┬─────┘    └────┬─────┘             │
│        │               │               │                    │
│        └───────────────┼───────────────┘                    │
│                        │                                    │
│        ┌───────────────┴───────────────┐                   │
│        │     Router + Alerts + Audit    │                   │
│        └───────────────┬───────────────┘                   │
│                        │                                    │
│   ┌────────────────────┴────────────────────┐               │
│   │        Agent Pool (OpenClaw/Claude/Codex) │              │
│   └────────────────────┬────────────────────┘               │
│                        │                                    │
│   ┌────────────────────┴────────────────────┐               │
│   │    Transport Layer (File / Redis / ZeroMQ)  │           │
│   └─────────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

---

## Complete Feature List

### Agent Orchestration
- **Intelligent Routing** — Three-factor algorithm (history embedding + load awareness + capability matching)
- **Dynamic Role Assignment** — Auto-assign roles based on task type (developer/reviewer/tester/architect/coordinator)
- **DAG Task Management** — Task dependency graph with intelligent scheduling
- **P0-P33 Layered Testing** — 1790+ test cases, comprehensive coverage
- **MailboxManager** — Agent inter-process messaging, Transport abstraction layer supports File/P2P/Redis
- **P2P Transport** — ZeroMQ PUSH/PULL + file-based fallback, no Redis required
- **RoleStore** — Dynamic role assignment system
- **BaseTaskStore** — Task storage abstraction with file locking and concurrency control
- **WebSocketManager** — WebSocket connection management
- **Parent-Child Lifecycle** — Parent-child agent relationship management
- **OpenClaw SDK Backend** — Multi-agent coordination based on Gateway Sessions API

### Web UI Dashboard
- **Real-time Conversation Monitoring** — Update every second, see what each agent is doing
- **Multi-tab Dashboard** — Dashboard / Designer / Monitor / Workspace / Settings
- **Status Visualization** — Task progress, Agent status, anomaly prediction
- **One-line Setup** — `agentteam board serve --port 8080`

### Production Security
- **API Authentication** — JWT-like Token mechanism
- **Gateway Token Distribution** — Auto-distribute to child agents
- **Session Isolation** — Each agent has independent conversation, no interference
- **Environment Variable Isolation** — `.env` separation, sensitive info not uploaded

### Observability
- **Audit Logs** — Event tracking, Actor analysis, time range filtering
- **Structured Logging** — JSON format + trace_id full chain tracking
- **Drift Detection** — Jaccard + semantic similarity dual verification
- **Quality Scoring** — Multi-dimensional evaluation: completeness / accuracy / quality

### Alert System
- **4-level Alerts** — LOW / MEDIUM / HIGH / CRITICAL
- **Alert Types** — TASK_TIMEOUT / AGENT_FAILURE_RATE_HIGH / TEAM_INACTIVITY
- **CRUD Operations** — Create / Query / List / Confirm
- **CLI Integration** — `agentteam alert check/list/ack`

### Deployment Options
- **Docker** — `Dockerfile` + `docker-compose.yml`
- **Quick Install** — `pip install -e .` one-command setup
- **Distributed Mode** — Redis / ZeroMQ P2P optional
- **Makefile** — `make dev` / `make prod` / `make test`

### Documentation
- **Shell Completions** — bash / zsh / fish
- **API Reference** — Complete API documentation
- **Architecture Review** — Detailed system architecture analysis
- **Deployment Guide** — Step-by-step deployment instructions

---

## Complete Capabilities

### Core Capabilities

| Capability | Description |
|------------|-------------|
| **Agent Teams** | Create and manage multiple agent teams |
| **Task Orchestration** | DAG-based task scheduling and delegation |
| **Inter-Agent Messaging** | Mailbox system for agent communication |
| **Real-time Monitoring** | Web dashboard for live activity tracking |
| **Alert Management** | Configurable alerts for failures and anomalies |
| **Audit Logging** | Complete trail of all team activities |
| **Drift Detection** | Detect when agent behavior deviates |
| **Role-based Access** | JWT-like token authentication |

### Advanced Capabilities

| Capability | Description |
|------------|-------------|
| **Multi-Backend Support** | OpenClaw SDK, subprocess, tmux, API |
| **P2P Transport** | ZeroMQ-based peer-to-peer communication |
| **Session Isolation** | Each agent has independent context |
| **Parent-Child Lifecycle** | Hierarchical agent relationships |
| **Quality Scoring** | Multi-dimensional task quality assessment |
| **Structured Logging** | JSON logs with trace IDs |

---

## Version Comparison

| Version | Key Changes |
|---------|-------------|
| v0.5.1 | Production hardening, enterprise features |
| v0.5.0 | Major release with P0-P33 testing |
| v0.4.0 | Initial OpenClaw fork |

---

## Supported Agents

| Agent | Status | Notes |
|-------|--------|-------|
| **OpenClaw** | ✅ Primary | Default agent backend |
| **Claude Code** | ✅ Supported | Full compatibility |
| **Codex** | ✅ Supported | Via CLI interface |
| **nanobot** | ✅ Supported | Via CLI interface |
| **Cursor** | ✅ Supported | Via CLI interface |
| **Custom CLI** | ✅ Supported | Via subprocess backend |

---

## Quick Links

| Resource | Link |
|----------|------|
| Documentation | [OpenClaw Docs](https://docs.openclaw.ai) |
| CLI Reference | [CLI.md](CLI.md) |
| API Reference | [API.md](API.md) |
| Deployment | [DEPLOY.md](DEPLOY.md) |
| Architecture | [ARCHITECTURE_REVIEW.md](ARCHITECTURE_REVIEW.md) |
| Contributing | [CONTRIBUTING.md](CONTRIBUTING.md) |

---

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test layer
python -m pytest tests/test_p0.py -v
python -m pytest tests/test_p1.py -v
python -m pytest tests/test_integration.py -v

# Run with coverage
python -m pytest tests/ --cov=agentteam --cov-report=html

# Run audit tests
python -m pytest tests/test_audit.py -v
```

---

## Installation

```bash
# Basic installation
git clone https://github.com/YintaTriss/AgentTeam.git
cd AgentTeam
pip install -e .

# Optional: P2P transport
pip install -e ".[p2p]"

# Optional: Redis transport
pip install -e ".[redis]"

# Optional: All extras
pip install -e ".[all]"
```

---

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## License

MIT License - see [LICENSE](LICENSE)

---

## Acknowledgments

**Upstream Projects:**

- [HKUDS/ClawTeam](https://github.com/HKUDS/ClawTeam) — Original framework, multi-agent coordination research
- [OpenClaw](https://openclaw.ai) — Default agent backend, deep OpenClaw integration support

**Key Technologies:**

- [VCP System](https://github.com/lioensky/VCPToolBox) — Acknowledgment structure framework
- [EverMind MSA](https://github.com/EverMind-AI/MSA) — Memory system architecture reference

**All contributions are appreciated!**

---

<p align="center">
  <strong>Made with ❤️ by Yinta, for AI agents</strong>
</p>
