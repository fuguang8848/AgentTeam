# AgentTeam Developer Guide

## Overview

This guide covers development setup, architecture, and contribution guidelines for AgentTeam-OpenClaw.

## Architecture

```
âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ?
â?                     AgentTeam Core                          â?
âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ?
â? orchestrator/     â? supervisor.py  â?Provider selection   â?
â?                   â? provider_*.py  â?Load balancing       â?
â?                   âââââââââââââââââââ¼ââââââââââââââââââââââ?
â? session/         â? session.py     â?Per-agent sessions   â?
â?                   â? cross_session.pyâ?Cross-session aware â?
â?                   âââââââââââââââââââ¼ââââââââââââââââââââââ?
â? team/            â? team.py        â?Team management      â?
â?                   â? mailbox.py     â?Message passing      â?
â?                   âââââââââââââââââââ¼ââââââââââââââââââââââ?
â? tracker/         â? file_tracker   â?Change tracking      â?
â?                   â? diff_tracker   â?Diff analysis       â?
â?                   â? token_stats   â?Usage monitoring    â?
â?                   âââââââââââââââââââ¼ââââââââââââââââââââââ?
â? workspace/       â? worktree.py    â?Git worktree mgmt   â?
â?                   âââââââââââââââââââ¼ââââââââââââââââââââââ?
â? board/           â? server.py      â?Web UI server       â?
â?                   â? collector.py   â?Data collection     â?
â?                   â? static/        â?Web assets          â?
âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ?
â? Transport Layer  â? file/  redis/  zmqp/  (pluggable)    â?
âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ?
```

## Development Setup

### Prerequisites

- Python 3.10+
- Git
- Miniconda3 or virtualenv

### Clone and Install

```bash
git clone https://github.com/your-repo/AgentTeam-OpenClaw.git
cd AgentTeam-OpenClaw
pip install -e .
```

### Install Dev Dependencies

```bash
pip install pytest pytest-asyncio pytest-cov
pip install black flake8 mypy
```

### Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_config.py -v

# Run with coverage
pytest tests/ --cov=agentteam --cov-report=html
```

### Code Style

```bash
# Format code
black AgentTeam/ tests/

# Lint
flake8 AgentTeam/ --max-line-length=100

# Type check
mypy AgentTeam/
```

## Module Guide

### orchestrator/

**supervisor.py** - Orchestrates multi-agent task execution
- `Supervisor` class manages agent lifecycles
- Provider selection for load balancing
- Task queuing and result aggregation

**provider_*.py** - Provider management
- `ProviderCapability` - Model capabilities
- `ProviderAvailability` - Real-time availability
- `ProviderSelector` - Smart routing

### session/

**session.py** - Per-agent session management
- Session creation, storage, retrieval
- Message history
- Context isolation

**cross_session.py** - Cross-session awareness
- `CrossSessionMonitor` - Tracks all sessions
- Pattern detection across sessions
- `SharedContext` - Shared state between agents

### team/

**team.py** - Team orchestration
- Team creation and membership
- Task assignment and tracking
- Leader election

**mailbox.py** - Message passing
- Async message queues per team
- Mailbox forwarding
- TTL and cleanup

### tracker/

**file_tracker.py** - File change tracking
- Watch directories for changes
- Debounced notifications
- Git integration

**diff_tracker.py** - Diff analysis
- Compute file differences
- Highlight changes
- Conflict detection

**token_stats.py** - Token usage monitoring
- Per-agent usage tracking
- Provider breakdown
- Cost estimation

### workspace/

**worktree.py** - Git worktree management
- Create/remove worktrees
- Branch management
- Cleanup of stale worktrees

### board/

**server.py** - Web UI server
- REST API endpoints
- SSE for real-time updates
- Static file serving

**collector.py** - Data aggregation
- Team metrics collection
- Session state monitoring
- Usage statistics

## Adding New Features

### 1. Create a New Module

```python
# agentteam/new_module.py
from typing import Optional
from dataclasses import dataclass

@dataclass
class NewFeature:
    name: str
    enabled: bool = True

    def do_something(self) -> str:
        return f"Doing {self.name}"
```

### 2. Add Tests

```python
# tests/test_new_module.py
import pytest
from agentteam.new_module import NewFeature

def test_new_feature():
    feature = NewFeature(name="test")
    assert feature.do_something() == "Doing test"
```

### 3. Update Exports

```python
# agentteam/__init__.py
from agentteam.new_module import NewFeature

__all__ = [..., "NewFeature"]
```

## Configuration

### config.yaml

```yaml
database:
  path: "agentteam.db"
  pool_size: 5

agents:
  max_concurrent: 10
  spawn_timeout: 60

transport:
  backend: "file"  # file, redis, zmqp

debug: false
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AgentTeam_DATA_DIR` | Data directory | `~/.agentteam` |
| `AgentTeam_DEBUG` | Enable debug mode | `false` |
| `AgentTeam_TRANSPORT` | Transport backend | `file` |
| `OPENCLAW_GATEWAY_URL` | Gateway URL | `http://localhost:18789` |

## Debugging

### Enable Debug Logging

```bash
export AgentTeam_DEBUG=1
agentteam --debug ...
```

### Check Logs

```bash
# View recent logs
tail -f ~/.agentteam/logs/agentteam.log

# JSON logging for parsing
export AgentTeam_LOG_JSON=1
```

### Common Issues

**Import Errors**: Ensure `pip install -e .` was run

**Port Already in Use**: Check `netstat -tlnp | grep 8080` and kill the process

**Git Worktree Errors**: Ensure git version >= 2.38 and no stale worktrees

## API Extension

### Adding New REST Endpoints

```python
# In board/server.py
@app.route("/api/my_endpoint", methods=["GET"])
async def my_endpoint(request):
    # Handle request
    return json_response({"status": "ok"})
```

### Adding SSE Events

```python
async def event_stream():
    for i in range(10):
        yield f"data: message {i}\n\n"
        await asyncio.sleep(1)

@app.route("/api/events/my_stream")
async def my_stream(request):
    return sse_response(event_stream())
```

## Performance

### Profiling

```python
import cProfile
import pstats

pr = cProfile.Profile()
pr.enable()
# ... your code ...
pr.disable()

stats = pstats.Stats(pr)
stats.sort_stats("cumulative")
stats.print_stats(20)
```

### Benchmarking

```bash
pytest tests/ --benchmark-only
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make changes with tests
4. Run `black` and `flake8`
5. Submit a PR

## License

MIT License - see LICENSE file
