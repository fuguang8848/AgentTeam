# ClawTeam Developer Guide

## Overview

This guide covers development setup, architecture, and contribution guidelines for ClawTeam-OpenClaw.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      ClawTeam Core                          │
├─────────────────────────────────────────────────────────────┤
│  orchestrator/     │  supervisor.py  │ Provider selection   │
│                    │  provider_*.py  │ Load balancing       │
│                    ├─────────────────┼─────────────────────│
│  session/         │  session.py     │ Per-agent sessions   │
│                    │  cross_session.py│ Cross-session aware │
│                    ├─────────────────┼─────────────────────│
│  team/            │  team.py        │ Team management      │
│                    │  mailbox.py     │ Message passing      │
│                    ├─────────────────┼─────────────────────│
│  tracker/         │  file_tracker   │ Change tracking      │
│                    │  diff_tracker   │ Diff analysis       │
│                    │  token_stats   │ Usage monitoring    │
│                    ├─────────────────┼─────────────────────│
│  workspace/       │  worktree.py    │ Git worktree mgmt   │
│                    ├─────────────────┼─────────────────────│
│  board/           │  server.py      │ Web UI server       │
│                    │  collector.py   │ Data collection     │
│                    │  static/        │ Web assets          │
├─────────────────────────────────────────────────────────────┤
│  Transport Layer  │  file/  redis/  zmqp/  (pluggable)    │
└─────────────────────────────────────────────────────────────┘
```

## Development Setup

### Prerequisites

- Python 3.10+
- Git
- Miniconda3 or virtualenv

### Clone and Install

```bash
git clone https://github.com/your-repo/ClawTeam-OpenClaw.git
cd ClawTeam-OpenClaw
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
pytest tests/ --cov=clawteam --cov-report=html
```

### Code Style

```bash
# Format code
black clawteam/ tests/

# Lint
flake8 clawteam/ --max-line-length=100

# Type check
mypy clawteam/
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
# clawteam/new_module.py
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
from clawteam.new_module import NewFeature

def test_new_feature():
    feature = NewFeature(name="test")
    assert feature.do_something() == "Doing test"
```

### 3. Update Exports

```python
# clawteam/__init__.py
from clawteam.new_module import NewFeature

__all__ = [..., "NewFeature"]
```

## Configuration

### config.yaml

```yaml
database:
  path: "clawteam.db"
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
| `CLAWTEAM_DATA_DIR` | Data directory | `~/.clawteam` |
| `CLAWTEAM_DEBUG` | Enable debug mode | `false` |
| `CLAWTEAM_TRANSPORT` | Transport backend | `file` |
| `OPENCLAW_GATEWAY_URL` | Gateway URL | `http://localhost:18789` |

## Debugging

### Enable Debug Logging

```bash
export CLAWTEAM_DEBUG=1
clawteam --debug ...
```

### Check Logs

```bash
# View recent logs
tail -f ~/.clawteam/logs/clawteam.log

# JSON logging for parsing
export CLAWTEAM_LOG_JSON=1
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
