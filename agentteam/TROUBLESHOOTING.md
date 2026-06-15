# AgentTeam Troubleshooting Guide

## Common Issues

### Installation Issues

#### `ModuleNotFoundError: No module named 'agentteam'`

**Cause**: Package not installed or not installed in editable mode.

**Solution**:
```bash
pip install -e .
# or
pip install agentteam
```

---

#### `UnicodeDecodeError` on Windows

**Cause**: Default encoding is GBK on Chinese Windows.

**Solution**:
```bash
# Set UTF-8 encoding
set PYTHONIOENCODING=utf-8
# or in Python
import sys
sys.stdout.reconfigure(encoding='utf-8')
```

---

### Board Server Issues

#### `Address already in use` (Port 8080)

**Cause**: Another process is using the port.

**Solution**:
```bash
# Find and kill the process
netstat -ano | findstr :8080
taskkill /PID <pid> /F

# Or use a different port
agentteam board serve --port 8081
```

---

#### `Remote end closed connection without response`

**Cause**: Server crashed or request timed out.

**Solution**:
1. Check server logs
2. Restart the server:
```bash
agentteam board serve --port 8080
```
3. Try with debug mode:
```bash
agentteam board serve --debug
```

---

#### Board UI shows "Not Connected" or empty data

**Cause**: BoardCollector failing to gather data.

**Solution**:
1. Check if teams exist: `agentteam team list`
2. Check file permissions on data directory
3. Restart the board server

---

### Agent Issues

#### Agent fails to spawn

**Cause**: Various - check error message.

**Solution**:
1. Check agent binary is installed:
```bash
which openclaw  # or claude, codex, etc.
```
2. Check SSH connectivity (if using remote agents)
3. Verify working directory is clean:
```bash
cd /path/to/workspace
git status
```

---

#### Agent times out

**Cause**: Task took too long or agent is stuck.

**Solution**:
1. Kill the stuck agent:
```bash
agentteam agent kill <agent_id>
```
2. Increase timeout:
```bash
agentteam spawn --timeout 3600 ...  # 1 hour
```
3. Check agent logs:
```bash
agentteam agent logs <agent_id>
```

---

#### Agent "seems stuck" but is actually working

**Cause**: Long-running task without output.

**Solution**:
1. Check task status:
```bash
agentteam task list <team_name>
```
2. Monitor agent activity:
```bash
agentteam agent status <agent_id>
```
3. Check if there are any blocking operations in the task

---

### Git Worktree Issues

#### `fatal: cannot create working tree file`

**Cause**: Disk full or permission issue.

**Solution**:
```bash
# Check disk space
df -h

# Check permissions
ls -la /path/to/worktree/parent
```

---

#### Stale worktrees not cleaned up

**Cause**: Worktree cleanup not running.

**Solution**:
```bash
# Manual cleanup
agentteam worktree cleanup --force

# Check existing worktrees
git worktree list
```

---

### Transport/Mailbox Issues

#### Messages not delivered

**Cause**: Mailbox full or transport not responding.

**Solution**:
1. Check mailbox size:
```bash
agentteam mailbox status <team_name>
```
2. Clear old messages:
```bash
agentteam mailbox clear <team_name> --older-than 24h
```
3. Check transport status:
```bash
agentteam transport status
```

---

#### `MailboxFullError`

**Cause**: Mailbox reached maximum capacity.

**Solution**:
1. Increase mailbox size in config:
```yaml
mailbox:
  max_size: 10000
```
2. Implement message cleanup policy
3. Archive old messages

---

### Database Issues

#### `Database is locked`

**Cause**: Multiple processes accessing database.

**Solution**:
1. Check for stuck processes:
```bash
ps aux | grep agentteam
```
2. Kill extra processes
3. If using SQLite, enable WAL mode:
```python
conn.execute("PRAGMA journal_mode=WAL")
```

---

#### Corrupted database

**Cause**: Crash during write or disk issue.

**Solution**:
1. Backup current database:
```bash
cp agentteam.db agentteam.db.bak
```
2. Run integrity check:
```bash
sqlite3 agentteam.db "PRAGMA integrity_check;"
```
3. If corrupted, restore from backup or reinitialize

---

### Performance Issues

#### High memory usage

**Cause**: Memory leak or too many agents.

**Solution**:
1. Check number of running agents:
```bash
agentteam agent list --running
```
2. Kill idle agents:
```bash
agentteam agent kill --idle
```
3. Set memory limits in config:
```yaml
agents:
  max_memory_mb: 2048
```

---

#### Slow token stats updates

**Cause**: Too many providers or database writes.

**Solution**:
1. Reduce stats collection frequency:
```yaml
metrics:
  export_interval: 300  # 5 minutes
```
2. Use Redis for stats storage:
```yaml
database:
  provider: redis
```

---

## Debug Mode

Enable debug mode for detailed logging:

```bash
# Environment variable
export AgentTeam_DEBUG=1

# Or CLI flag
agentteam --debug board serve

# JSON logging for parsing
export AgentTeam_LOG_JSON=1
```

## Getting Help

### Check Version

```bash
agentteam --version
```

### Check Configuration

```bash
agentteam config show
```

### Check System Status

```bash
agentteam status
```

### View Full Logs

```bash
# All logs
agentteam logs

# Recent logs
agentteam logs --tail 100

# Filter by level
agentteam logs --level ERROR
```

## Report Issues

When reporting issues, include:

1. **Version**: `agentteam --version`
2. **OS**: Windows/Linux/macOS + version
3. **Python version**: `python --version`
4. **Command**: Exact command that failed
5. **Error message**: Full error traceback
6. **Logs**: Relevant log entries
7. **Config**: Non-sensitive parts of config.yaml

## Known Limitations

1. **Windows**: Some features require WSL for full compatibility
2. **SQLite**: Not suitable for high-concurrency scenarios; use Redis
3. **Git worktrees**: Requires Git 2.38+
4. **Remote agents**: Require SSH key-based authentication
