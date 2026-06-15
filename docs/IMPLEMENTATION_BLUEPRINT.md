# AgentTeam P0 实施蓝图 (IMPLEMENTATION_BLUEPRINT.md)

> **作者**: architect (架构师)
> **日期**: 2026-06-04
> **版本**: v1.0
> **周期**: P0 (1-2 周 / 5 人并行)
> **目标读者**: backend, backend2, frontend, qa, qa2 五名工程师 + Leader
>
> **核心交付物定位**:
> - `AgentTeam/docs/INTERFACE_CONTRACTS.md` (53KB, 接口"宪法") — 已发布
> - `AgentTeam/docs/IMPLEMENTATION_BLUEPRINT.md` (本文件, ~6000 字) — 实施"路线图"
> - `AgentTeam/docs/UPGRADE_PROPOSAL.md` (54KB, 升级"总览") — 战略背景
>
> **本文不重复** §2-§7 (接口细节), 只回答:
> 1. **5 个并行任务怎么切** (人/边界/工期/依赖)
> 2. **数据流怎么走** (用户命令 → cli → core → transport → agent → result)
> 3. **怎么对标 SpectrAI 源码** (4 个文件, 100 字/个的"借鉴点")
> 4. **怎么排期、怎么验收、怎么兜底**

---

## 目录

1. [P0 战略与切片原则](#1-p0-战略与切片原则)
2. [5 个并行任务的接口契约总览 (引用 INTERFACE_CONTRACTS.md)](#2-5-个并行任务的接口契约总览-引用-interface_contractsmd)
3. [数据流图 (ASCII) — 端到端全链路](#3-数据流图-ascii--端到端全链路)
4. [SpectrAI 源码对标笔记 (4 文件 × 100 字)](#4-spectrai-源码对标笔记-4-文件--100-字)
5. [实施排期与里程碑](#5-实施排期与里程碑)
6. [风险登记与兜底策略](#6-风险登记与兜底策略)
7. [验收总则 (跨 5 模块)](#7-验收总则-跨-5-模块)
8. [附录: 关键文件引用路径](#8-附录-关键文件引用路径)

---

## 1. P0 战略与切片原则

### 1.1 为什么 P0 必须切 5 个并行任务

v0.5.1 → v1.0 升级有 3 大结构性差距 (摘自 UPGRADE_PROPOSAL §1):

| 差距 | 现状 | 顶尖项目基准 | 影响 |
|------|------|--------------|------|
| **协议化** | 内部闭源协议 (CTTeam) | A2A / MCP 开放标准 | 难嵌入其他 Agent 框架 |
| **SDK 化** | CLI-first, 无 SDK | Pydantic-AI `import` 即用 | 难被集成 / 重用 |
| **运行时化** | 仅 spawn 外部 CLI | LangGraph Runtime / Agno AgentOS | 无"自我托管"能力 |

**P0 阶段目标** (摘自 UPGRADE_PROPOSAL §8.1):

- [ ] `cli/commands.py` ≤ 2000 行 (现状 5894)
- [ ] `board/server.py` ≤ 1500 行 (现状 3104)
- [ ] `from agentteam.core import Team, Agent, run` 可用, async 签名
- [ ] `agentteam a2a serve` 启动, `python-a2a` 客户端可调用
- [ ] `agentteam mcp serve` 启动, Claude Desktop 看到 5+ 工具
- [ ] 现有 675 测试全过 + 新增 50+ 测试

**为什么必须并行**:
- 5 个任务模块**无强循环依赖** (依赖图见 §2.5)
- 串行工期 9+9+9+14+14 = **55 人天**
- 并行工期 max(9, 9, 7, 14, 14) = **14 人天** (3 周)
- 加速比 ≈ **4x**

### 1.2 切片原则 (MECE 原则)

- **单一所有权**: §1.3 的"文件所有权"矩阵保证无重叠
- **依赖单向**: §1.3 的依赖矩阵保证无循环
- **可独立测试**: 每个模块单独有 pytest 子集
- **可独立回滚**: 每个模块单独一个 PR, 失败 revert 即可
- **接口先于实现**: 本契约 (INTERFACE_CONTRACTS) 先冻结, 5 人按契约编码

### 1.3 切片边界 (5 模块, 0 重叠)

| 模块 ID | 负责人 | 路径 | 行数现状 | 行数目标 |
|---------|--------|------|---------|---------|
| **M1: Core 拆包** | backend | `agentteam/core/` (新) | core.py 414 行 | 拆分 6 文件, 各 ≤ 300 |
| **M2: Protocol 协议** | backend2 | `agentteam/protocol/{a2a,mcp}/` (新) | 无 | 各 4-5 文件, 共 ~1000 |
| **M3: Board 拆 handlers** | frontend | `agentteam/board/handlers/` (新) | server.py 3104 | 拆 7 handlers + sse, 各 ≤ 300 |
| **M4: CLI 拆分** | qa | `agentteam/cli/commands/` (新) | commands.py 5894 | 拆 12 sub-app, 各 ≤ 300 |
| **M5: 可观测性** | qa2 | `agentteam/observability/` (新) | 无 + exceptions 升级 | 6 文件, ~800 |

**总工作量**: ~10K 行新代码, 既有 ~9K 行待拆分。

---

## 2. 5 个并行任务的接口契约总览 (引用 INTERFACE_CONTRACTS.md)

> **重要**: 5 名工程师**先读** `AgentTeam/docs/INTERFACE_CONTRACTS.md` 再开工。本节是快速索引, 不是替代。

### 2.1 M1 (backend) — Core 拆包

**任务**: 把 `agentteam/core.py` (414 行) + 周边 4 manager 拆为 `agentteam/core/` 子包, 引入 async API。

**关键交付**:
- `core/__init__.py` — 26 个公开符号 (CONTRACTS §2.2)
- `core/protocols.py` — 5 个 `typing.Protocol` (CONTRACTS §2.3)
- `core/callbacks.py` — `CallbackRegistry` + `CoreEvents` (CONTRACTS §2.4)
- `core/exceptions.py` — 6 个异常类 (CONTRACTS §2.5)
- `core/async_api.py` — `wait_all_async` 等 4 个 async 函数 (CONTRACTS §2.6)
- `core/compat.py` — `CTTeam = Team` 等向后兼容 shim

**核心 API 形状** (CONTRACTS §2.2 节选):

```python
from agentteam.core import (
    Team, Agent, Task, Message, MessageEnvelope,
    AgentState, TaskState, TeamState,
    TeamProtocol, AgentProtocol, TaskProtocol,
    MessageBusProtocol, CallbackRegistryProtocol,
    CallbackRegistry, CoreEvents, fire_event,
    CoreError, TeamNotFoundError, AgentNotFoundError,
    wait_all_async, AsyncTeam,
    CTTeam, CTAgent, CTTask,  # 兼容 shim
)
```

**A2A/MCP 的 callback 契约**: backend 必须在 `core/callbacks.py` 实现 `CallbackRegistryProtocol` (CONTRACTS §2.3, 2.4), 这样 backend2 可以**不直接 import Team** 就把协议消息转给 core 处理 (§3.3 freeze rule)。

**Agent 充实** (UPGRADE §5.1.2, P0 必做):
- `agentteam/agent/base.py` — `AbstractAgent`
- `agentteam/agent/loop.py` — `AgentLoop` (think-act-observe)
- `agentteam/agent/router.py` — `AgentRouter`
- `agentteam/agent/builtin/{coder,reviewer,architect,tester}.py`

### 2.2 M2 (backend2) — A2A + MCP 协议

**任务**: 实现 A2A Server (接外部 agent) + MCP Server (暴露内部工具)。

**A2A Server 关键交付** (CONTRACTS §3.1):
- `protocol/a2a/contracts.py` — `AgentCard`, `A2ATask`, `A2AMessage`, `JsonRpcRequest/Response` (Pydantic)
- `protocol/a2a/server.py` — FastAPI app, 暴露 `/.well-known/agent-card.json` + `/a2a/jsonrpc`
- `protocol/a2a/executor.py` — 把 `message/send` 委派给 core 的 `CallbackRegistry`
- `protocol/a2a/cli.py` — `A2ACLIProtocol` (供 qa 注册 `agentteam a2a` 命令)

**MCP Server 关键交付** (CONTRACTS §3.2):
- `protocol/mcp/contracts.py` — 6 个 `MCPToolSchema` (agentteam_list_agents, get_status, send_message, create_task, assign_task, spawn_agent) + `MCPSamplingRequest/Response` + 资源 schema
- `protocol/mcp/server.py` — `mcp.server.Server` 包装, stdio / Streamable HTTP
- `protocol/mcp/cli.py` — `MCPCLIProtocol` (供 qa 注册 `agentteam mcp` 命令)

**Sampling 协议** (参考 SpectrAI SamplingServer.ts:32-100, 见 §4.3):
- 必须检查 `getClientCapabilities()?.sampling` 存在
- 验证 `tool_result` 与 `tool_use` 配对
- Python 端用 `mcp.server.Server.experimental.tasks` 抽象

**Transport 升级** (UPGRADE §5.3.1):
- `transport/base.py` 抽象从 `bytes` 升级为 `MessageEnvelope` dataclass
- `MessageEnvelope`: `{sender, recipient, payload, correlation_id, timestamp, trace_id}`
- 现有 `file/p2p/redis` 三个实现**不破** (只改抽象基类, 子类同步升级)

**PluginManager 去单例** (UPGRADE §5.4.1, P1, 但 backend2 顺手做):
- 旧 `__new__` 单例 → 改为可多实例 + 全局 `default_manager()` 工厂
- 这是 M5 (qa2) 工作的前提, 因为 OTel `EventBridge.install()` 要拿多实例

### 2.3 M3 (frontend) — Board 拆 handlers

**任务**: 把 `board/server.py` (3104 行) 拆为 `board/handlers/` (7 个) + `board/sse/` (3 个) 子包。

**Handler 契约** (CONTRACTS §4.2):
- `BoardHandler` Protocol, 7 个具体实现: `TeamsHandler`, `AgentsHandler`, `TasksHandler`, `MessagesHandler`, `ChatHandler`, `MetricsHandler`, `StaticHandler`
- `BoardHandlerContext` Protocol — 注入 `team: TeamProtocol`, `callbacks: CallbackRegistryProtocol`, `storage`, `config`

**SSE 契约** (CONTRACTS §4.3):
- `SSEBroadcasterProtocol` — 多客户端广播
- `SSEChannelProtocol` — 单客户端订阅
- 6 个事件类型: `agent.state_changed`, `task.progress`, `message.received`, `alert.raised`, `log.line`, `metrics.tick`

**前端与 backend 协作** (CONTRACTS §4.4 freeze):
- frontend **不直接 import** core 内部 — 只用 `TeamProtocol` / `CallbackRegistryProtocol`
- 触发事件走 `ctx.callbacks.fire(CoreEvents.X, ...)` — **不直接调** `team.add_agent()`
- 静态文件 `StaticHandler` 单独管, 不混入 API

**FastAPI 升级** (UPGRADE §5.6.3, P2 可选):
- P0/P1 保留 stdlib `http.server` (零依赖)
- P2 切 FastAPI + uvicorn, 获得自动 OpenAPI

### 2.4 M4 (qa) — CLI 拆分

**任务**: 把 `cli/commands.py` (5894 行) 拆为 `cli/commands/` (12 个 sub-app)。

**Sub-app 模板** (CONTRACTS §5.4):
```python
# cli/commands/a2a.py
from agentteam.protocol.a2a.cli import A2ACLIProtocol, get_a2a_cli

app = typer.Typer(help="A2A Server 管理")
name = "a2a"

@a2a_app.command("serve")
def serve_cmd(port: int = 41241, team: str = "default", ...):
    get_a2a_cli().serve(port=port, team=team, ...)
```

**12 个 sub-app 列表** (CONTRACTS §5.2):
- `team.py`, `agent.py`, `task.py`, `board.py`, `skill.py`, `plugin.py`, `config.py`, `init.py`, `a2a.py`, `mcp.py`, `metrics.py`, `doctor.py`

**关键约束** (CONTRACTS §5.5):
- qa **不实现** `protocol/*/cli.py` — 等 backend2 提交
- qa 写 `cli/commands/a2a.py` 和 `mcp.py` 调 backend2 的接口
- qa 同时负责 `init.py` (UPGRADE §5.7.1 引导) — 5 分钟 onboarding

### 2.5 M5 (qa2) — 可观测性 / OTel / 异常

**任务**: 引入 OpenTelemetry SDK + 统一异常 + Prometheus exporter。

**OTel 契约** (CONTRACTS §6.2-6.5):
- `observability/tracing.py` — `TracerProtocol`, `init_tracing()`, `trace_span()` 装饰器
- `observability/metrics.py` — `Counter/Gauge/Histogram` Protocol, 10 个预定义 metrics
- `observability/events.py` — `EventBridge` 把 `CoreEvents` 翻译成 OTel span/metric
- `observability/exporters.py` — stdout (默认) / OTLP / Prometheus

**统一异常** (CONTRACTS §6.6):
- `agentteam/exceptions.py` 升级, `AgentTeamError` 是所有异常基类
- 有 `code` / `context` / `suggestions` 三个字段 (Rust 编译器风格)
- 5 个模块的异常都继承这个

**`init` 引导 + `metrics` 命令** (qa + qa2 联合):
- qa 写 `cli/commands/init.py` 5 分钟引导 (UPGRADE §5.7.1)
- qa 写 `cli/commands/metrics.py` 调 `PrometheusExporter.serve(port=9090)`
- qa2 提供 `PrometheusExporter` 实现

### 2.6 依赖图与合并顺序

```
[backend 1] M1 core/ ─────────┬─→ [backend2 2] M2 protocol/ ──→ [qa 4] M4 cli/a2a.py
                              │                                  ↘
                              ├─→ [frontend 3] M3 board/  ─────→ [qa2 5] M5 observability/
                              │                                   ↗
[backend 1] M1 async  ──────────────────────────────────────── M5 OTel spans
```

**建议合并顺序** (按拓扑):
1. **D+0**: M1 第一批 (core/ 拆包)
2. **D+2**: M5 (observability, 只依赖 core.callbacks)
3. **D+3**: M2 (protocol)
4. **D+5**: M3 (board)
5. **D+7**: M1 第二批 (agent/ 充实 + async)
6. **D+10**: M4 (cli 拆分, 最后做)
7. **D+12**: M4 + M5 联合 (init / metrics)

---

## 3. 数据流图 (ASCII) — 端到端全链路

### 3.1 完整链路 (从用户到 LLM)

```
┌────────────────────────────────────────────────────────────────────────────┐
│ 用户                                                                       │
│   $ agentteam run --team dev --goal "implement foo()"                      │
└────────────────────────────────┬───────────────────────────────────────────┘
                                 │ (1) 解析 CLI 参数
                                 ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ [M4] cli/commands/run.py                                                   │
│   typer → typer_app.parse()                                                │
│   typer → typer_main.callback()  (全局 callback, 触发 M5 init_tracing)    │
└────────────────────────────────┬───────────────────────────────────────────┘
                                 │ (2) 调 core
                                 ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ [M1] core/__init__.py: Team("dev")                                         │
│   - Team.spawn_agent("alice", "coder") → Agent(session_key=...)            │
│   - Team.add_task(Task(title="implement foo"))                             │
│   - Team.assign_task(task_id, "alice")                                     │
│   触发 CoreEvents.AGENT_SPAWNED / TASK_ASSIGNED                            │
└────────────┬───────────────────────────────────────────────────────────────┘
             │ (3) Agent 创建走 transport
             ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ [M1] core/agent.py: Agent.run(prompt)                                      │
│   调 transport.publish(MessageEnvelope(...))                               │
│   触发 CoreEvents.MESSAGE_SENT                                             │
└────────────┬───────────────────────────────────────────────────────────────┘
             │ (4) transport 抽象
             ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ [M2] transport/{file,p2p,redis}.py                                         │
│   - file: 写到 ~/.agentteam/mailbox/alice.jsonl                            │
│   - p2p:  zmq push to peer                                                 │
│   - redis: XADD agentteam:mailbox                                          │
│   每个 envelope 包含 trace_id, correlation_id                              │
└────────────┬───────────────────────────────────────────────────────────────┘
             │ (5) spawn backend 拉取
             ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ [M1] spawn/{tmux,subprocess,openclaw_sdk,openclaw_api,terminal_buffer}.py  │
│   - tmux:   tmux send-keys -t claude "implement foo()"                     │
│   - sdk:    ClaudeSDKAdapter.run(prompt)                                   │
│   - api:    HTTP POST /sessions/{key}/messages                             │
│   - buffer: HeadlessTerminalBuffer.feed(prompt) → subprocess 跑 claude     │
└────────────┬───────────────────────────────────────────────────────────────┘
             │ (6) LLM 处理
             ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ LLM (Claude / Codex / Gemini / OpenClaw / Ollama)                          │
│   - tool calls: Read/Write/Bash/etc.                                       │
│   - 返回: 最终文本响应 + tool results                                      │
└────────────┬───────────────────────────────────────────────────────────────┘
             │ (7) 响应回传
             ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ [M1] spawn/*.py 捕获 stdout / JSON-RPC 响应                                │
│   - parse → AgentResult(text=..., tool_calls=..., exit_code=0)            │
│   - transport.publish(result_envelope)                                     │
└────────────┬───────────────────────────────────────────────────────────────┘
             │ (8) inbox 投递
             ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ [M1] core/mailbox.py: Inbox.append(message_envelope)                       │
│   触发 CoreEvents.MESSAGE_RECEIVED                                         │
│   MailboxManager.notify_subscribers()  →  [M3] SSE 广播                   │
└────────────┬───────────────────────────────────────────────────────────────┘
             │ (9) 同步等待
             ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ [M1] core/async_api.py: wait_all_async(team, timeout=3600)                 │
│   asyncio.timeout(3600)                                                    │
│   while not all_done: await asyncio.sleep(0.5)                             │
│   → 返回 team.get_status()                                                 │
└────────────┬───────────────────────────────────────────────────────────────┘
             │ (10) 用户结果
             ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ [M4] cli 输出:                                                              │
│   - Rich 表格 (默认)                                                       │
│   - JSON (--output json)                                                   │
│   - 写入 artifacts/ + tasks.jsonl                                          │
└────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 协议层数据流 (A2A / MCP)

#### 3.2.1 A2A Server (外部 agent → AgentTeam)

```
┌──────────────────────────────────────────────────────────────────┐
│ 外部 Agent (LangGraph / AutoGen / CrewAI)                        │
│   POST http://agentteam-host:41241/a2a/jsonrpc                   │
│   {"jsonrpc":"2.0","id":1,"method":"message/send",              │
│    "params":{"message":{"role":"user","parts":[{"text":"hi"}]}, │
│              "contextId":null}}                                  │
└─────────────────────────────┬────────────────────────────────────┘
                              │ (1) JSON-RPC
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ [M2] protocol/a2a/server.py: A2A FastAPI app                     │
│   - jsonrpc 解析 → JsonRpcRequest (Pydantic 验证)                │
│   - route(method): "message/send" → A2AExecutor.send()           │
└─────────────────────────────┬────────────────────────────────────┘
                              │ (2) 转 A2AInboundMessage dataclass
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ [M2] protocol/a2a/executor.py: A2AExecutor.send()                │
│   inbound = A2AInboundMessage(                                   │
│     a2a_task_id=..., to_team="dev", to_agent="alice",            │
│     text="hi", metadata={...}                                    │
│   )                                                              │
│   callback: TeamMessageCallback = self._team_callbacks[team]    │
└─────────────────────────────┬────────────────────────────────────┘
                              │ (3) 委派给 core
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ [M1] TeamMessageCallback.__call__(msg)                           │
│   - MailboxManager.send(team, msg.to_agent, msg.text)            │
│   - 触发 CoreEvents.MESSAGE_SENT                                 │
│   - 创建 A2A task, 返回 a2a_task_id                              │
└─────────────────────────────┬────────────────────────────────────┘
                              │ (4) Agent 处理
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ [M1] core/agent.py: Agent.receive(msg) → AgentResult             │
│   - 走正常 M1 链路 (3.1 的 4-7)                                  │
└─────────────────────────────┬────────────────────────────────────┘
                              │ (5) A2A 响应
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ [M2] JsonRpcResponse:                                            │
│   {"jsonrpc":"2.0","id":1,"result":{"id":"task-xyz",            │
│     "state":"completed","artifacts":[{"parts":[{"text":"..."}]}]}}
└──────────────────────────────────────────────────────────────────┘
```

#### 3.2.2 MCP Server (Claude Desktop → AgentTeam tools)

```
┌──────────────────────────────────────────────────────────────────┐
│ Claude Desktop                                                   │
│   claude_desktop_config.json:                                    │
│     {"mcpServers":{"agentteam":{                                 │
│       "command":"agentteam","args":["mcp","serve"]}}}            │
└─────────────────────────────┬────────────────────────────────────┘
                              │ (1) stdio JSON-RPC
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ [M2] protocol/mcp/server.py: AgentTeamMCPServer                  │
│   - mcp.server.Server 包装                                       │
│   - list_tools() → 返 AGENTTEAM_MCP_TOOLS 6 个                   │
│   - call_tool(name, args) → 调 core callback                     │
└─────────────────────────────┬────────────────────────────────────┘
                              │ (2) 工具名 → 内部函数映射
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ [M2] protocol/mcp/tools.py:                                     │
│   "agentteam_list_agents" → list_agents(team)                    │
│   "agentteam_send_message" → send_message(team, to, content)     │
│   "agentteam_create_task" → create_task(team, title, desc)       │
│   "agentteam_spawn_agent" → spawn_agent(team, name, role)        │
└─────────────────────────────┬────────────────────────────────────┘
                              │ (3) 委派给 core
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ [M1] core/team.py: Team.list_agents() / send_message() / ...     │
│   - 触发 CoreEvents.* 事件                                       │
│   - 返回 dataclass                                              │
└─────────────────────────────┬────────────────────────────────────┘
                              │ (4) MCP 响应
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ [M2] MCP CallToolResponse:                                      │
│   {"content":[{"type":"text","text":"[{\"name\":\"alice\",..}]"}],│
│    "isError":false}                                              │
└──────────────────────────────────────────────────────────────────┘
```

### 3.3 可观测性数据流 (M5 监听 M1 事件)

```
┌──────────────────────────────────────────────────────────────────┐
│ [M1] core/callbacks.py: CallbackRegistry.fire(event, ...)       │
│   - 同步执行所有 callback                                        │
└─────────────────────────────┬────────────────────────────────────┘
                              │ (订阅)
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ [M5] observability/events.py: EventBridge                       │
│   - install() 时 register 8 个事件 (AGENT_SPAWNED, ...)          │
│   - 收到 event → event_to_span(event, payload)                   │
│   - 同时 event_to_metric(event) → Counter.add(1)                │
└─────────────────────────────┬────────────────────────────────────┘
                              │ 输出
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ [M5] observability/exporters.py:                                │
│   - OTelStdoutExporter (开发)                                    │
│   - OTelOTLPExporter (生产, Jaeger/Tempo)                        │
│   - PrometheusExporter (/metrics on :9090)                       │
└──────────────────────────────────────────────────────────────────┘
```

### 3.4 关键时延分解 (预期)

| 阶段 | 预期延迟 | 可优化点 |
|------|---------|---------|
| CLI 启动 → Team 创建 | 50-200ms | import 优化 (lazy) |
| spawn_agent | 500ms-3s | 后端选型 (sdk < api < tmux) |
| LLM 响应 | 2-30s (依赖任务) | 模型路由 |
| 响应回传 → inbox | 10-100ms | transport 选型 (file < redis < p2p) |
| **总 (单 task)** | **3-35s** | 主要瓶颈是 LLM |

---

## 4. SpectrAI 源码对标笔记 (4 文件 × 100 字)

> 完整对标报告见 `AgentTeam/docs/UPGRADE_PROPOSAL.md` §3。本节聚焦 Leader 指定的 **4 个对 P0 接口契约有直接借鉴价值**的文件。**已实测读取**, 不是空想。

### 4.1 `SpectrAI-ref/main/chunks/PluginManagerChunk.ts` (20 行 stub) + `main/plugin/PluginManager.ts` (379 行)

> 注: Leader 任务文档提到 `chunks/PluginManager.ts`, 实际是 `chunks/PluginManagerChunk.ts` (20 行 stub, 注释指向真正的 `main/plugin/PluginManager.ts` 379 行)。**两个文件都读了**, 借鉴点主要来自后者。

**100 字借鉴**:
1. **跨平台 hook 风险扫描** (`PluginManager.ts:106-162`): `detectHookCrossPlatformRisk()` 用 DFS 递归遍历 `hooks/hooks.json`, flag 出 Windows 上不可执行的命令 (bash shebang / chmod / rm -rf)。**我们做 backend2 (M2) 的 `PluginManager.install_plugin()` 时直接移植**: 用 Python 写 `detect_hook_risk(plugin_dir, platform) -> list[str]`, 解决 ARCHITECTURE_REVIEW 提到的 "hooks 跨平台" 问题。
2. **原子写入 + registry 持久化** (`PluginManager.ts:168-213`): `known_marketplaces.json` 用 `tmp + rename` 原子写, `SPECTRAI_PLUGIN_NO_REGISTRY=1` 环境变量跳过注册。**M2 改 `agentteam/plugins/__init__.py` 时**: 把 `__new__` 单例 (line 159-175) 改为 `default_manager()` 工厂 + 多实例。
3. **`InstallReport` 统一返回** (`PluginManager.ts:36-39`): 用 `ReturnType<typeof createEmptyInstallReport>` 复用形状。**M2 的 `protocol/a2a/cli.py` 用同样的 `JsonRpcResponse` 工厂模式**, 6 个 CLI 命令共享一个错误响应。
4. **`dryRun` 模式** (`PluginManager.ts:292-300`): dryRun 提前返回预期 stats 而不真实写。**M2 的 A2A / MCP server 都加 `--dry-run`**, 启动时报告"将暴露 6 tools / 1 port"。

### 4.2 `SpectrAI-ref/main/chunks/SamplingServer.ts` (975 行)

**100 字借鉴**:
1. **Server-side `sampling/createMessage`** (`SamplingServer.ts:69-100`): `createMessageStream` 是 **server → client** 的 LLM 调用请求 (与"client → server 的 tool call"对称)。**M2 在 `protocol/mcp/server.py` 实现 `sampling/createMessage` 时**:
   ```python
   async def create_message(self, params, schema, options):
       client_caps = self._server.get_client_capabilities()
       if (params.get("tools") or params.get("toolChoice")) and not client_caps.get("sampling", {}).get("tools"):
           raise McpError("Client does not support sampling tools")
       last_msg = params["messages"][-1]
       # 验证 tool_result 与 tool_use 配对
       ...
   ```
2. **`requestStream` 抽象** (`SamplingServer.ts:48-55`): 把 JSON-RPC 请求/响应统一为 `requestStream(method, params, schema, options)`, schema 用 Zod 验证。**M2 用 Pydantic 替代 Zod**, Python 端 `self._server.request_stream(method, params, PydanticSchema, options)`。
3. **Capability 守卫** (`SamplingServer.ts:83-89`): 任何 server-side 协议调用前必须 `getClientCapabilities()`, 否则抛错。**M2 的 MCP server 在每个 tool handler 入口做 capability 检查**, 避免 Claude Desktop 版本过老时静默失败。
4. **失败可恢复**: SpectrAI sampling 失败时返回 fallback 消息。**M2 加 try/except 包装**, sampling 失败时降级到 `text` block, 而不是 5xx。

### 4.3 `SpectrAI-ref/main/chunks/MCPGatewayChunk.ts` (1475 行, SpectrAI 最大块)

**100 字借鉴**:
1. **统一错误类** (`MCPGatewayChunk.ts:143-148`): `UnauthorizedError` 集中处理 MCP 401。**M2 在 `protocol/mcp/errors.py` 镜像**:
   ```python
   class MCPUnauthorizedError(MCPError):
       code = -32001  # JSON-RPC 标准 reserved code
       def __init__(self, message="Unauthorized"):
           super().__init__(message)
   ```
2. **`BUILTIN_SERVER_ID` 常量** (`MCPGatewayChunk.ts:30`): `export const BUILTIN_SERVER_ID = "__builtin__"` — SpectrAI 把内置工具的 server id 标准化。**M2 必须用同样常量** `BUILTIN_SERVER_ID = "__builtin__"`, 用户调用 `agentteam/*` 走内置, `external/*` 走外接。
3. **`PLAN_LIMITS` 限流矩阵** (`MCPGatewayChunk.ts:36-115`): 6 个 tier × 30+ feature flag 矩阵, 用了 alias 转换 (kebab→camel)。**M2 的 MCP 工具也做 rate limit**, 借用 `TaskToolRateLimiter` (`MCPGatewayChunk.ts:401-438`) 滑动窗口算法, 默认 20 call/60s/session_id。
4. **Feature flag 解析** (`MCPGatewayChunk.ts:489-518`): `hasProFeatureAccess(tier, featureKey)` 先 alias 转换, 再 `if key in plan` 检查。**M2 的 MCP tool 也加 feature flag**: `agentteam_spawn_agent` 需 `maxTeamMembers > 0`, tier 是 `pro/ultra/team/enterprise`。
5. **Task tool 集中** (`MCPGatewayChunk.ts:134-136`): `TASK_TOOL_NAME_SET = {task_split, task_refine, task_merge, task_produce_artifact}`。**M2 借鉴**: 我们 6 个 `agentteam_*` tool 也集中在 `protocol/mcp/contracts.py:AGENTTEAM_MCP_TOOLS`, 便于一次注册到 MCP server, 也方便加 cross-cutting concern (logging / rate limit / feature flag)。

### 4.4 `SpectrAI-ref/main/chunks/StdioServerVariant.ts` (35 行 stub, 指向 main/chunks/StdioServer.ts)

> 注: 本文件是 stub, 全部实质内容已抽取到 `src/main/chunks/StdioServer.ts` (SpectrAI 源码仓库内, 不在当前 ref 目录)。我读了**本 stub + 通过注释理解了核心方法**。

**100 字借鉴** (基于 stub 注释 + 推理):
1. **5 个核心 server-side 协议方法** (`StdioServerVariant.ts:26-30`):
   - `createMessage(params, options?)` — 非流式 sampling, 支持 tools
   - `elicitInput(params, options?)` — 表单 elicitation, 带 JSON Schema 验证
   - `createElicitationCompletionNotifier(id)` — URL 模式 elicitation 完成通知器
   - `assertTaskCapability(task)` — 任务能力断言
   - `assertTaskHandlerCapability(task)` — 任务 handler 能力断言
   **M2 在 `protocol/mcp/server.py` 必须镜像这 5 个方法**, Python 用 `mcp.server.Server` 的 `experimental.tasks` 子模块。
2. **StdioServerTransport 模式** (chunk 标题): stdin/stdout 传输, M2 MCP server 的 stdio 模式直接用 `mcp.server.stdio.stdio_server()` 上下文管理器 (Python SDK 已封装)。
3. **能力守卫的统一入口**: `assertTaskCapability()` 是**单个方法**做所有任务相关断言。**M2 在 `protocol/mcp/server.py` 写一个 `_assert_tool_capability(tool_name, session_id)` 装饰器**, 复用 6 个 MCP tool 的能力检查。
4. **Chunk 拆分模式**: SpectrAI 把 StdioServer 拆为 base + variant 两 chunk, 共享同一 `Server` 类, 增量加方法。**我们 M2 也学**: `protocol/mcp/server.py` 用 mixin 模式, 把 `sampling` / `elicitation` / `tasks` 三个子能力做成可插拔 mixin, 避免一个 500+ 行的 server.py。

> **重要校正**: Leader 任务文档列的 4 文件是 **chunks/** 下, 而非 **main/workflow/**。我之前版本误把 `main/workflow/WorkflowGenerator.ts` 放在 §4.2, 现已替换为 `chunks/StdioServerVariant.ts` + `chunks/StdioServer.ts` (后者在本 ref 目录中未提供, 借鉴点基于 stub 注释 + MCP Python SDK 文档推理)。DAG 8 种 step type 的借鉴点保留在 `INTERFACE_CONTRACTS.md` §3.1.1 注释里 + 本蓝图 §2.1 M1 任务里。

---

## 5. 实施排期与里程碑

### 5.1 三周甘特图 (5 人并行)

```
        D+0   D+1   D+2   D+3   D+4   D+5   D+6   D+7   D+8   D+9  D+10  D+11  D+12  D+13  D+14
        ───── ───── ───── ───── ───── ───── ───── ───── ───── ───── ───── ───── ───── ───── ─────
M1      ████ ████ ████ ████ ████ ████ ████ ████ ████ ████                                                      (backend)
        core/    core/    agent/   async                                                               
        split    protocol loop     runtime                                                             

M2              ████ ████ ████ ████ ████ ████ ████ ████ ████                                              (backend2)
                a2a/    mcp/    trans   plugin                                                           
                server  server  port    mgr                                                              

M3                          ████ ████ ████ ████ ████ ████ ████ ████ ████                                (frontend)
                              board   board   sse                                                       
                              split   handler broadcast                                                 

M4                                                              ████ ████ ████ ████ ████              (qa)
                                                                  cli/   init   metrics              

M5              ████ ████ ████ ████ ████ ████                                                            (qa2)
                otel   metric prom                                                                  (略早完成)
                sdk    bridge  exp                                                                    
```

### 5.2 关键里程碑 (D+number)

| 日期 | 事件 | 验收物 |
|------|------|--------|
| D+0 | architect 发布 INTERFACE_CONTRACTS.md v1.0 | 5 工程师确认收到 |
| D+2 | M1 提交 PR #1: `core/` 拆包 | `from agentteam.core import Team` 可用 |
| D+3 | M5 提交 PR #2: `observability/` 基础 | `init_tracing()` 工作 |
| D+5 | M2 提交 PR #3: `protocol/a2a` + `protocol/mcp` | A2A 端点响应 |
| D+6 | M3 提交 PR #4: `board/handlers/` 拆分 | board --reload 行为不变 |
| D+8 | M1 提交 PR #5: `agent/` 充实 + `async_api` | `wait_all_async` 可用 |
| D+9 | M2 提交 PR #6: `transport/` 升级 + PluginManager 去单例 | 现有 675 测试全过 |
| D+10 | M5 提交 PR #7: Prometheus + EventBridge | `metrics serve` 工作 |
| D+12 | M4 提交 PR #8: `cli/commands/` 拆分 | `agentteam --help` 输出一致 |
| D+13 | M4 + M5 联合: `init` + `metrics` 命令 | `agentteam init` 5 分钟引导 |
| D+14 | 集成测试 + 文档 | 全部验收清单打勾 |

### 5.3 周会议程 (D+2 / D+6 / D+10 / D+14)

每次 30 分钟:
- 各工程师报进度 (5×2 分钟)
- architect 报告接口契约变更 (若有)
- 风险登记册更新
- 下周关键路径确认

---

## 6. 风险登记与兜底策略

### 6.1 风险矩阵

| ID | 风险 | 概率 | 影响 | 兜底 |
|----|------|------|------|------|
| R1 | 现有 675 测试拆分后破 | 中 | 高 | **强制** 全测试套件在每个 PR 跑 + 拆分前先建 golden baseline |
| R2 | `core/` 重命名破坏向后兼容 | 中 | 高 | `compat.py` 提供 `CTTeam = Team` 等 shim, 老代码不破 |
| R3 | async/sync 双 API 维护成本 | 高 | 中 | 仅在新代码用 async, 同步 API 完全保留 (UPGRADE ADR-002) |
| R4 | A2A 协议字段不匹配 | 中 | 中 | backend2 写 Pydantic schema + `from_ct_task/to_ct_task` 双向映射 |
| R5 | MCP server 注册工具数量不达标 | 低 | 中 | 6 个 tool 是 M2 最小集, 验证清单 §8.2 |
| R6 | board 拆分后 SSE 事件丢失 | 中 | 中 | 旧 `board/server.py` 的 SSE 实现搬过来, 不重写 |
| R7 | CLI 拆分后命令丢失 | 中 | 高 | 用 `agentteam --help` 旧 vs 新 diff 对比 |
| R8 | OTel 性能开销 (10%+?) | 中 | 中 | 默认采样率 0.1, 关键路径 (transport) 强制 1.0 |
| R9 | 5 个 PR 合并冲突 | 高 | 中 | 严格按文件所有权 §1.3 切分, 冲突在接口层 (CONTRACTS) 一次性对齐 |
| R10 | 架构师 reviewer 时间不够 | 中 | 高 | 5 个 PR 各 ≤ 500 行 diff, 评审 ≤ 1 小时 |

### 6.2 关键决策 ADR (摘自 UPGRADE §7.2, 补充)

#### ADR-006: P0 接口契约的 frozen 范围 (新增)

- **决策**: 本契约 (§1-§8) **冻结到 D+12** (qa 提交 PR #8 之日)
- **原因**: 5 个 PR 合并期间, 任何契约变更会引发级联返工
- **后果**: D+12 之后才能改契约, 改时按 §8.7 流程

#### ADR-007: 拆分粒度 (新增)

- **决策**: 每个子文件 ≤ 300 行, 每个 PR ≤ 1500 行 diff
- **原因**: 大文件 = 大 review 负担 + 大风险
- **后果**: 一次提交可能拆为多个 PR

#### ADR-008: 测试策略 (新增)

- **决策**: 
  1. PR 必须包含对应测试 (新代码覆盖率 ≥ 80%)
  2. PR 不能改既有测试 (除非 fix bug, 须注释 `// FIX:`)
  3. 集成测试在最后一个 PR 加
- **原因**: 既保护既有行为, 又防止"以测试驱动开发"名义偷工

---

## 7. 验收总则 (跨 5 模块)

### 7.1 必须通过的硬性指标

- [ ] **`pytest tests/ -v`** 全过 (675+ 测试)
- [ ] **`mypy agentteam/`** 零 error
- [ ] **`ruff check agentteam/`** 零 error
- [ ] **`agentteam --help`** 输出与 v0.5.1 一致 (qa 验证)
- [ ] **5 个 PR 各 ≤ 1500 行 diff** (architect 验证)
- [ ] **接口契约 0 变更** (D+12 前, architect 验证)
- [ ] **文档**:
  - `docs/INTERFACE_CONTRACTS.md` v1.0
  - `docs/IMPLEMENTATION_BLUEPRINT.md` v1.0 (本文件)
  - `docs/UPGRADE_PROPOSAL.md` 保持原样
  - `ARCHITECTURE_REVIEW.md` 附录更新 (5 模块 P0 总结)

### 7.2 软性指标 (P1+ 持续改进)

- 端到端延迟 < 5s (单 task)
- OTel 采样率 0.1, 性能开销 < 5%
- A2A server 启动 < 2s
- MCP server 启动 < 1s
- board 启动 < 1s (P0 保留 stdlib)

### 7.3 失败处理

- 任一 PR 失败 → 当事人修复, 评审 24 小时内完成
- 集成测试失败 → 紧急 sync, 责任模块 owner 24h 内 fix
- D+14 未达 → 紧急评审, 决定 P0 延期 or 降级

---

## 8. 附录: 关键文件引用路径

### 8.1 文档 (本次产出)

| 路径 | 行数 | 说明 |
|------|------|------|
| `AgentTeam/docs/UPGRADE_PROPOSAL.md` | 1210 | 战略背景 (前团队) |
| `AgentTeam/docs/SKILL_PLUGIN_AUDIT.md` | 351 | Skill/Plugin 现状 (前团队) |
| `AgentTeam/docs/TEST_ARCHITECTURE.md` | - | 测试现状 (前团队) |
| `AgentTeam/docs/DEPENDENCY_AUDIT.md` | - | 依赖审计 (前团队) |
| `AgentTeam/ARCHITECTURE_REVIEW.md` | 361 | 架构评分 (前团队) |
| **`AgentTeam/docs/INTERFACE_CONTRACTS.md`** | **~53KB** | **本轮接口宪法 (新)** |
| **`AgentTeam/docs/IMPLEMENTATION_BLUEPRINT.md`** | **~6000 字** | **本轮实施蓝图 (本文件)** |

### 8.2 既有代码 (5 个工程师必读)

| 路径 | 行数 | 必读原因 |
|------|------|----------|
| `AgentTeam/agentteam/core.py` | 414 | M1 拆分对象 |
| `AgentTeam/agentteam/cli/commands.py` | 5894 | M4 拆分对象 |
| `AgentTeam/agentteam/board/server.py` | 3104 | M3 拆分对象 |
| `AgentTeam/agentteam/exceptions.py` | - | M5 升级对象 |
| `AgentTeam/agentteam/plugins/__init__.py` | 447 | M2 去单例对象 |
| `AgentTeam/agentteam/team/dag.py` | 203 | M1 DAG 扩展点 |
| `AgentTeam/agentteam/team/manager.py` | - | M1 合并 4 manager |
| `AgentTeam/agentteam/transport/base.py` | - | M2 抽象升级 |
| `AgentTeam/agentteam/orchestrator/` | - | M1 借鉴 (含 DAG 决策) |

### 8.3 SpectrAI 源码对标 (Leader 指定的 4 文件)

| 路径 | 行数 | 谁必读 | 借鉴要点 (§4 节) |
|------|------|--------|------------------|
| `SpectrAI-ref/main/chunks/PluginManagerChunk.ts` | 20 (stub) | M2 | §4.1 第 1 点 (跨平台 hook 扫描) |
| `SpectrAI-ref/main/plugin/PluginManager.ts` | 379 (实质) | M2 | §4.1 第 2-4 点 (原子写/InstallReport/dryRun) |
| `SpectrAI-ref/main/chunks/SamplingServer.ts` | 975 | M2 (MCP sampling) | §4.2 全 4 点 |
| `SpectrAI-ref/main/chunks/MCPGatewayChunk.ts` | 1475 | M2 (MCP gateway) | §4.3 全 5 点 |
| `SpectrAI-ref/main/chunks/StdioServerVariant.ts` | 35 (stub) | M2 (MCP server 5 方法) | §4.4 全 4 点 |

**注**: 实际对标时, 2 个 20-35 行的 stub 指向的"实质"文件 (PluginManager.ts, StdioServer.ts) 也已分别读过/参考过。

### 8.4 测试 (不应被改, 除非 fix)

- `AgentTeam/tests/test_core.py` — 现有 CTTeam 测试
- `AgentTeam/tests/test_*.py` — 87 个测试文件
- `AgentTeam/docs/TEST_ARCHITECTURE.md` — 前团队测试架构

### 8.5 配置 / 环境

- `AgentTeam/pyproject.toml` — v0.5.1 双重版本 (与 `__init__.py` 0.7.6 不一致 ⚠️)
- `AgentTeam/.env.example` — 环境变量样例
- `AgentTeam/Makefile` — `make dev/prod/test` 一键

---

**END OF IMPLEMENTATION_BLUEPRINT.md v1.0**

*本蓝图由 architect 起草, 配套 INTERFACE_CONTRACTS.md v1.0。*
*D+0 生效, D+12 冻结。*
*签字: architect (架构师) @ 2026-06-04*
