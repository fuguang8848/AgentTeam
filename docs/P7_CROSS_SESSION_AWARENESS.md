# P7 跨会话感知核心实现

## 概述

P7 实现了跨会话感知核心模块，参考 SpectrAI 的 supervisorPrompt.ts 感知层设计，为 ClawTeam 提供多会话协作能力。

## 核心模块

### 1. SessionRegistry（会话注册中心）

**文件**: `clawteam/session/registry.py`

**功能**:
- `register()` - 注册新会话
- `unregister()` - 注销会话
- `list_sessions()` - 查询会话列表（支持状态、团队、角色、Provider过滤）
- `get_session_summary()` - 获取会话详细摘要
- `search_sessions()` - 按关键词搜索会话
- `heartbeat()` - 更新会话心跳
- `log_activity()` - 记录会话活动
- `cleanup_stale_sessions()` - 清理过期会话

**数据模型**:
```python
class SessionInfo:
    session_id: str          # 会话ID
    session_name: str        # 会话名称
    status: SessionStatus    # active, idle, completed, shutdown
    work_dir: str            # 工作目录
    team_name: str           # 所属团队
    agent_name: str          # Agent名称
    agent_id: str            # Agent ID
    role: str                # 角色（leader, worker）
    provider: str            # AI Provider
    files_modified: list     # 修改的文件列表
    commands_executed: list  # 执行的命令列表
    tasks_completed: int     # 完成的任务数
    current_task: str        # 当前任务
```

### 2. CrossSessionBus（跨会话消息总线）

**文件**: `clawteam/session/cross_session.py`

**功能**:
- `send()` - 发送消息到指定会话
- `broadcast()` - 广播消息到所有会话
- `receive()` - 接收消息
- `peek()` - 查看消息（不标记已读）
- `notify_completion()` - 通知任务完成
- `notify_conflict()` - 通知文件冲突
- `notify_file_modified()` - 通知文件修改
- `count_unread()` - 统计未读消息
- `clear_read()` - 清理已读消息

**消息类型**:
```python
class NotificationType:
    task_complete      # 任务完成
    task_started       # 任务开始
    file_conflict      # 文件冲突
    file_modified      # 文件修改
    broadcast          # 广播消息
    direct_message     # 直接消息
    session_joined     # 会话加入
    session_left       # 会话离开
    status_update      # 状态更新
    alert              # 警告
```

### 3. CLI命令

**文件**: `clawteam/cli/session.py`

**命令列表**:

#### 会话管理
```bash
# 注册会话
clawteam session register --name "my-session" --team "team-1" --agent "worker-1"

# 注销会话
clawteam session unregister <session-id>

# 更新心跳
clawteam session heartbeat <session-id>

# 列出会话
clawteam session list --status active --team team-1

# 获取会话摘要
clawteam session summary --id <session-id>
clawteam session summary --name "my-session"

# 搜索会话
clawteam session search "api.py"

# 清理过期会话
clawteam session cleanup --max-age 24

# 记录活动
clawteam session log <session-id> --type file_write --desc "Modified file" --file "/src/api.py"
```

#### 跨会话消息
```bash
# 广播消息
clawteam session msg broadcast "Team announcement" --from <session-id>

# 发送消息
clawteam session msg send <to-session-id> "Hello" --from <session-id>

# 接收消息
clawteam session msg receive <session-id> --limit 10

# 查看消息
clawteam session msg peek <session-id>

# 统计未读
clawteam session msg count <session-id>

# 清理已读
clawteam session msg clear <session-id>
```

#### 通知
```bash
# 任务完成通知
clawteam session notify complete <task-id> --name "Task" --summary "Done"

# 文件冲突通知
clawteam session notify conflict <file-path> --type write --desc "Conflict"
```

## 使用示例

### Python API

```python
from clawteam.session.registry import get_session_registry
from clawteam.session.cross_session import get_cross_session_bus, NotificationType

# 注册会话
registry = get_session_registry()
session = registry.register(
    session_name="backend-worker",
    team_name="team-1",
    agent_name="backend",
    role="worker",
    provider="claude-code",
)

# 发送消息
bus = get_cross_session_bus()
bus.send(
    from_session=session.session_id,
    from_agent="backend",
    to_session="leader-session-id",
    content="Task completed",
    notification_type=NotificationType.task_complete,
)

# 接收消息
messages = bus.receive(session.session_id)
for msg in messages:
    print(f"From: {msg.from_agent}, Content: {msg.content}")

# 搜索会话
results = registry.search_sessions("api.py")
for result in results:
    print(f"Session: {result['session']['sessionName']}, Matches: {result['matches']}")
```

## 测试覆盖

**测试文件**:
- `tests/test_session_registry.py` - 29个测试
- `tests/test_cross_session.py` - 20个测试

**测试结果**: 49 passed, 0 failed

**覆盖范围**:
- SessionInfo 模型创建和序列化
- SessionRegistry 所有方法
- CrossSessionMessage 模型和消息类型
- CrossSessionBus 所有方法
- 通知功能（任务完成、文件冲突、文件修改）
- 集成测试（完整工作流）

## 与 SpectrAI 对应

SpectrAI supervisorPrompt.ts 中的感知层工具：

| SpectrAI 工具 | ClawTeam 实现 |
|--------------|---------------|
| `list_sessions(status?, limit?)` | `SessionRegistry.list_sessions()` |
| `get_session_summary(sessionId?, sessionName?)` | `SessionRegistry.get_session_summary()` |
| `search_sessions(query, limit?)` | `SessionRegistry.search_sessions()` |

新增功能（超出 SpectrAI）：
- 会话注册/注销
- 心跳机制
- 活动日志
- 跨会话消息总线
- 文件冲突通知
- 过期会话清理

## 文件结构

```
clawteam/session/
├── __init__.py          # 模块入口
├── registry.py          # 会话注册中心（17KB）
├── cross_session.py     # 跨会话消息总线（18KB）

clawteam/cli/
├── session.py           # CLI命令（24KB）

tests/
├── test_session_registry.py  # Registry测试（14KB）
├── test_cross_session.py     # Bus测试（16KB）
```

## 配置

环境变量：
- `CLAWTEAM_DATA_DIR` - 数据目录（默认 `~/.clawteam`）

数据存储：
- `{data_dir}/sessions/*.json` - 会话信息
- `{data_dir}/sessions/activities/{session_id}/*.json` - 活动日志
- `{data_dir}/cross_session_bus/{session_id}/*.json` - 消息收件箱

## 后续扩展建议

1. **WebSocket 实时推送** - 将跨会话消息通过 WebSocket 实时推送
2. **Redis Transport** - 支持分布式环境下的跨会话通信
3. **会话状态同步** - 多节点间的会话状态同步
4. **会话亲和性** - 基于文件/任务的会话关联推荐
5. **会话历史分析** - 会话活动历史分析和报告生成