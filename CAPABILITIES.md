# ClawTeam-OpenClaw 完整能力清单

> **版本**: v0.5.1 | **测试**: 666+ | **状态**: 生产就绪

本文档详细记录 ClawTeam-OpenClaw 的所有功能模块和实现状态。

---

## 📋 目录

1. [核心模块](#核心模块)
2. [Agent 生命周期管理](#agent-生命周期管理)
3. [消息传输系统](#消息传输系统)
4. [任务编排与路由](#任务编排与路由)
5. [Web Board UI](#web-board-ui)
6. [数据库与存储](#数据库与存储)
7. [事件追踪系统](#事件追踪系统)
8. [协作增强](#协作增强)
9. [监控与告警](#监控与告警)
10. [安全与认证](#安全与认证)
11. [开发工具](#开发工具)
12. [部署选项](#部署选项)
13. [测试覆盖](#测试覆盖)

---

## 核心模块

| 模块 | 路径 | 功能 | 状态 |
|------|------|------|------|
| team | `clawteam/team/` | Agent 生命周期、角色、邮箱、任务 | ✅ |
| transport | `clawteam/transport/` | 消息传输抽象 | ✅ |
| spawn | `clawteam/spawn/` | Agent 生成（6种backend） | ✅ |
| orchestrator | `clawteam/orchestrator/` | 任务编排、模型路由 | ✅ |
| board | `clawteam/board/` | Web UI、HTTP API、SSE | ✅ |
| api | `clawteam/api/` | REST API | ✅ |
| cli | `clawteam/cli/` | 命令行工具 | ✅ |
| database | `clawteam/database/` | SQLite + 连接池 | ✅ |
| events | `clawteam/events/` | 事件追踪 | ✅ |
| store | `clawteam/store/` | 任务存储 | ✅ |
| collaboration | `clawteam/collaboration/` | Activity/Presence/Mentions | ✅ |
| notification | `clawteam/notification/` | 通知系统 | ✅ |
| metrics | `clawteam/metrics/` | 指标收集 | ✅ |
| security | `clawteam/security/` | 安全模块 | ✅ |
| learnings | `clawteam/learnings/` | 经验学习 | ✅ |
| memory | `clawteam/memory/` | 记忆管理 | ✅ |
| insights | `clawteam/insights/` | 洞察分析 | ✅ |
| alerts | `clawteam/alerts/` | 告警系统 | ✅ |
| concurrency | `clawteam/concurrency/` | 并发控制 | ✅ |
| parser | `clawteam/parser/` | 消息解析 | ✅ |
| daemon | `clawteam/daemon/` | 持久Agent守护进程 | ✅ |

---

## Agent 生命周期管理

### 1.1 状态机 (`team/lifecycle.py`)
- **状态**: pending → running → completed/failed/stopped
- **事件**: AGENT_STARTED, AGENT_COMPLETED, AGENT_FAILED, AGENT_STOPPED
- **超时控制**: 可配置超时时间
- **重试机制**: 自动重试失败的 Agent

### 1.2 Parent-Child 关系 (`team/parent_child.py`)
- **P26**: Parent-Child 生命周期管理 ✅
- **CLI 命令**:
  - `clawteam terminate-children <agent>` - 终止子 Agent
  - `clawteam terminate-tree <agent>` - 终止整个树
  - `clawteam list-children <agent>` - 列出子 Agent
  - `clawteam show-parent <agent>` - 显示父 Agent
  - `clawteam register-child <parent> <child>` - 注册关系

### 1.3 角色管理 (`team/roles.py`)
- **动态角色**: developer, reviewer, tester, architect, coordinator
- **基于任务类型自动分配**
- **角色权限隔离**

### 1.4 Mailbox (`team/mailbox.py`)
- **Agent 间点对点消息**
- **邮箱队列管理**
- **消息持久化**

---

## 消息传输系统

### 2.1 Transport 抽象 (`transport/base.py`)
```python
class Transport(ABC):
    def send(self, to: str, message: dict) -> bool
    def receive(self, agent_id: str) -> Optional[dict]
    def broadcast(self, message: dict) -> int
```

### 2.2 File Transport (`transport/file.py`)
- **回退方案**: 无 ZeroMQ/Redis 时使用
- **基于文件的队列**
- **轮询机制**

### 2.3 P2P Transport (`transport/p2p.py`)
- **ZeroMQ PUSH/PULL**
- **低延迟**
- **无需中心服务器**

### 2.4 Redis Transport (`transport/redis.py`)
- **Pub/Sub 模式**
- **需要外部 Redis**
- **适合分布式部署**

---

## Agent Spawning (生成)

### 3.1 6 种 Backend

| Backend | 文件 | 适用场景 | 状态 |
|---------|------|----------|------|
| tmux | `tmux_backend.py` | Linux/macOS 默认 | ✅ |
| subprocess | `subprocess_backend.py` | 通用子进程 | ✅ |
| openclaw_sdk | `openclaw_sdk_backend.py` | OpenClaw Gateway API | ✅ |
| openclaw_api | `openclaw_api_backend.py` | OpenClaw REST API | ✅ |
| terminal_buffer | `terminal_buffer.py` | 终端缓冲 | ✅ |
| auto | - | 自动检测最佳 backend | ✅ |

### 3.2 命令验证 (`spawn/command_validation.py`)
- **PATH 检查**: 验证命令存在
- **环境变量过滤**: 防止泄露敏感变量
- **权限检查**: skip_permissions 模式

### 3.3 Registry (`spawn/registry.py`)
- **Agent 注册/注销**
- **状态追踪**
- **元数据存储**

---

## 任务编排与路由

### 4.1 Orchestrator (`orchestrator/`)
- **任务分解**: 将复杂任务拆分为子任务
- **依赖管理**: DAG 拓扑排序
- **并行调度**: 独立任务并行执行

### 4.2 模型路由 (`orchestrator/model_router.py`)
- **P38**: 智能模型路由 ✅
- **基于任务复杂度选择模型**
- **成本优化**
- **多模型支持**: OpenAI, Anthropic, 本地模型

### 4.3 运行时路由 (`orchestrator/runtime_router.py`)
- **动态路由**
- **负载感知**
- **失败转移**

---

## Web Board UI

### 5.1 Dashboard (`board/dashboard.py`)
- **实时监控**: 每秒刷新
- **多标签页**: 看板 / 设计器 / 监控 / 工作流 / 设置
- **状态卡片**: Agent 状态可视化

### 5.2 WebSocket (`board/websocket.py`)
- **实时推送**
- **连接管理**
- **心跳检测**

### 5.3 SSE (`board/server.py`)
- **P36**: SSE 实时推送 ✅
- **HTTP API**
- **CORS 支持**

### 5.4 静态文件 (`board/static/`)
- **Web UI 资源**
- **366KB+ JavaScript**
- **多模态支持**: 图片/附件渲染

### 5.5 监控面板 (`board/`)
- **会话列表**
- **任务列表**
- **Agent 监控**
- **状态推断**

---

## 数据库与存储

### 6.1 DatabaseManager (`database/manager.py`)
- **P3**: 数据库连接池 ✅
- **queue.Queue 线程本地连接**
- **WAL 模式**: 提升并发性能
- **预编译语句缓存**: LRU 驱逐策略

```python
class DatabaseConnectionPool:
    pool_size: int = 5
    def _get_conn(self) -> sqlite3.Connection
    def _release_conn(self, conn)
    def _enable_wal_mode(self, conn)
```

### 6.2 TaskStore (`store/base.py`)
- **BaseTaskStore 抽象**
- **文件锁并发控制**
- **任务持久化**

### 6.3 Memory (`memory/`)
- **记忆管理**
- **上下文追踪**
- **长期记忆**

---

## 事件追踪系统

### 7.1 EventTracker (`events/tracker.py`)
- **P35**: 事件追踪系统 ✅
- **40+ 事件类型**
- **SQLite 持久化**
- **查询 API**

### 7.2 事件类型
```
AGENT_STARTED, AGENT_COMPLETED, AGENT_FAILED
TEAM_CREATED, TEAM_DISSOLVED
TASK_ASSIGNED, TASK_COMPLETED, TASK_FAILED
MESSAGE_SENT, MESSAGE_RECEIVED
...
```

### 7.3 订阅通知 (`events/tracker.py`)
- **P5**: 异步订阅者通知 ✅
- **ThreadPoolExecutor**
- **超时保护**: wait(timeout=5.0)

### 7.4 EventAPI (`events/api.py`)
- **REST API**: 查询事件
- **统计接口**: get_stats()
- **过滤支持**: 时间范围、类型、Actor

---

## 协作增强

### 8.1 Activity Feed (`collaboration/activity_feed.py`)
- **P29**: 协作增强 ✅
- **实时活动流**
- **用户可见性**

### 8.2 Presence (`collaboration/presence.py`)
- **在线状态追踪**
- **实时更新**
- **超时检测**

### 8.3 Mentions (`collaboration/mentions.py`)
- **@提及功能**
- **通知触发**
- **上下文关联**

### 8.4 Context Board (`collaboration/context_board.py`)
- **共享上下文**
- **实时同步**
- **版本控制**

---

## 监控与告警

### 9.1 Metrics (`metrics/`)
- **指标收集**
- **性能监控**
- **资源使用**

### 9.2 Alerts (`alerts/`)
- **四级告警**: LOW / MEDIUM / HIGH / CRITICAL
- **告警类型**:
  - TASK_TIMEOUT
  - AGENT_FAILURE_RATE_HIGH
  - TEAM_INACTIVITY
- **CLI**: `clawteam alert check/list/ack`

### 9.3 漂移检测 (`team/drift.py`)
- **Jaccard 相似度**
- **语义相似度**
- **双校验机制**

### 9.4 质量评分 (`team/snapshot.py`)
- **completeness**: 任务完成度
- **accuracy**: 准确率
- **quality**: 质量评分

---

## 安全与认证

### 10.1 AuthManager (`security/`)
- **P41**: AuthManager 强制执行 ✅
- **JWT-like Token**
- **API 端点保护**

### 10.2 Session 隔离
- **每个 Agent 独立会话**
- **Token 传递**
- **环境变量管理**

### 10.3 配置安全 (`config.py`)
- **环境变量支持**
- **.env 文件分离**
- **敏感信息不上传**

---

## 开发工具

### 11.1 CLI (`cli/`)
- **50+ 命令**
- **Shell 补全**: bash / zsh / fish
- **详细帮助**

### 11.2 API (`api/`)
- **REST API 完整实现**
- **认证支持**
- **错误处理**

### 11.3 测试框架
- **pytest + pytest-asyncio**
- **595+ 测试用例**
- **覆盖率报告**

### 11.4 开发者指南
- **DEVELOPER_GUIDE.md**
- **CONTRIBUTING.md**
- **TROUBLESHOOTING.md**

---

## 部署选项

### 12.1 Docker
```bash
docker-compose up -d
```

### 12.2 裸机
```bash
pip install -e .
```

### 12.3 分布式
- Redis Transport
- ZeroMQ P2P

### 12.4 Makefile
```bash
make dev    # 开发模式
make prod   # 生产模式
make test   # 运行测试
```

---

## 测试覆盖

### 13.1 测试统计
- **总测试数**: 595+
- **通过率**: 99%+
- **跳过**: 14
- **警告**: 6

### 13.2 测试模块
| 模块 | 测试数 | 状态 |
|------|--------|------|
| team/ | ~150 | ✅ |
| events/ | ~100 | ✅ |
| spawn/ | ~80 | ✅ |
| board/ | ~60 | ✅ |
| database/ | ~50 | ✅ |
| orchestrator/ | ~40 | ✅ |
| 其他 | ~115 | ✅ |

### 13.3 CI/CD
- **GitHub Actions**
- **ruff format**: 代码格式化
- **pyright**: 类型检查
- **pip-audit**: 依赖安全

---

## 待完成项目

### P37: 组件集成 🔄 进行中
- **状态**: 待开始
- **负责人**: arch-integrator

### v0.5.1 待办
- [ ] 修复遗留 bug
- [ ] 完善文档
- [ ] 更多测试
- [ ] 性能优化

---

## Agent Daemon (持久Agent守护进程)

v0.5.1 新增功能，允许 Agent 持续运行并响应后续任务。

### 架构

```
┌─────────────────────────────────────────────────────────────┐
│                     ClawTeam CLI                            │
│  clawteam daemon start / spawn / send-task                 │
└─────────────────────┬───────────────────────────────────────┘
                      │ TCP Socket (Windows) / Unix Socket
┌─────────────────────▼───────────────────────────────────────┐
│                  agentd 守护进程                            │
│  - 持久运行，管理所有 Agent Session                         │
│  - 接收 spawn/send_task 命令                               │
│  - 自动恢复运行中的 Agent                                   │
└─────────────────────┬───────────────────────────────────────┘
                      │ Gateway Sessions API
┌─────────────────────▼───────────────────────────────────────┐
│              OpenClaw Gateway                               │
│  ws://127.0.0.1:18789                                      │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              OpenClaw Agent (Session)                       │
│  - 持续活跃，等待新任务                                     │
│  - 通过 clawteam inbox 与 leader 通信                       │
└─────────────────────────────────────────────────────────────┘
```

### CLI 命令

| 命令 | 说明 |
|------|------|
| `clawteam daemon start` | 启动守护进程 |
| `clawteam daemon stop` | 停止守护进程 |
| `clawteam daemon status` | 查看状态 |
| `clawteam daemon list` | 列出运行中的 Agent |
| `clawteam daemon spawn` | Spawn Agent |

### SDK 集成

```python
# 通过 socket 直接与 daemon 通信
import socket, json, struct

def send_command(command, args=None):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(("127.0.0.1", 18792))
    
    request = json.dumps({"command": command, "args": args}).encode()
    sock.sendall(struct.pack("!I", len(request)))
    sock.sendall(request)
    
    # 接收响应...

# 发送任务
send_command("send_task", {
    "agent_name": "worker1",
    "task": "创建文件.txt"
})
```

### 持久化

- PID 文件: `~/.clawteam/agentd.pid`
- 运行中 Agent: `~/.clawteam/running_agents.json`
- 自动恢复: Daemon 重启时恢复所有运行中的 Agent

---

## 更新日志

| 版本 | 日期 | 变化 |
|------|------|------|
| v0.5.1 | 2026-05-04 | Agent Daemon 持久运行、Continuous Mode、mentions/pinned 修复 |
| v0.5.0 | 2026-05-03 | P26-P37 Agent 协调增强 |
| v0.4.0 | 2026-04-26 | P1 问题修复升级 |
| v0.3.1 | 2026-04-26 | P0 基础架构 |

---

*本文档最后更新: 2026-05-04*
