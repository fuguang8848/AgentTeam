# AgentTeam 接口契约 (INTERFACE_CONTRACTS.md)

> **作者**: architect (架构师)
> **生效日期**: 2026-06-04
> **版本**: v1.0 (Freeze)
> **目的**: 为 backend / backend2 / frontend / qa / qa2 五名工程师提供"宪法级"接口定义。所有 5 个并行任务必须严格遵守本文档中的类型签名与方法语义，不得擅自修改（变更须经 architect 评审并更新本文件版本号）。
>
> **范围**:
> - 5 个并行任务模块的边界
> - `agentteam/core/` (backend 拆包) 导出符号的 Python Protocol
> - `agentteam/protocol/a2a/contracts.py` (backend2 A2A) 的 dataclass schema
> - `agentteam/board/handlers/` (frontend 拆分) 与 backend 的回调契约
> - `agentteam/cli/commands/` (qa 拆分) sub-app 注册接口
> - `agentteam/observability/` (qa2 OTel) 的 SDK 复用接口
>
> **不在范围**: 实际 .py 实现 — 那是 5 名工程师的工作；本文档只规定"应当长什么样"。
>
> **对接文件** (工程师查阅时一并打开):
> - `AgentTeam/docs/UPGRADE_PROPOSAL.md` §5.1-5.6 (改造项详细说明)
> - `AgentTeam/ARCHITECTURE_REVIEW.md` (既有架构评分)
> - `AgentTeam/docs/SKILL_PLUGIN_AUDIT.md` (Skill/Plugin 现状)
> - `AgentTeam/agentteam/core.py` (待拆分的 monolith)
> - `AgentTeam/agentteam/cli/commands.py` (5894 行, 拆分对象)
> - `AgentTeam/agentteam/board/server.py` (3104 行, 拆分对象)
> - `AgentTeam/agentteam/team/dag.py` (DAG 现状)
> - `AgentTeam/agentteam/transport/base.py` (transport 抽象)
> - `AgentTeam/agentteam/plugins/__init__.py` (PluginManager 单例)

---

## 目录

1. [总体架构与 5 模块边界](#1-总体架构与-5-模块边界)
2. [Backend 任务: `agentteam/core/` 拆包导出契约](#2-backend-任务-agentteamcore-拆包导出契约)
3. [Backend2 任务: A2A + MCP 协议契约](#3-backend2-任务-a2a--mcp-协议契约)
4. [Frontend 任务: `board/handlers/` 拆分契约](#4-frontend-任务-boardhandlers-拆分契约)
5. [QA 任务: `cli/commands/` sub-app 注册契约](#5-qa-任务-clicommands-sub-app-注册契约)
6. [QA2 任务: 可观测性 / OTel / 异常契约](#6-qa2-任务-可观测性--otel--异常契约)
7. [跨模块共享类型 (Team, Agent, Task, Message)](#7-跨模块共享类型-team-agent-task-message)
8. [接口冻结检查清单 (Interface Freeze Checklist)](#8-接口冻结检查清单-interface-freeze-checklist)

---

## 1. 总体架构与 5 模块边界

### 1.1 拆分目标 (摘自 UPGRADE_PROPOSAL.md §4.2 目标 2)

```
                ┌─────────────────────┐
                │   AgentTeam Core    │   ← Backend 拆包 (本契约 §2)
                │  (Runtime + State)  │
                └──────────┬──────────┘
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
       ▼                   ▼                   ▼
   A2A Server         MCP Server          CLI / Python SDK
   (backend2 §3.1)    (backend2 §3.2)     (qa §5 / qa2 §6)
       │                   │                   │
       └────────┬──────────┴──────────┬────────┘
                ▼                     ▼
        Board Handlers           Observability
        (frontend §4)            (qa2 §6 OTel)
```

### 1.2 模块依赖矩阵 (单向无环)

| 上游模块 (依赖方) | 可调用下游 | 不可调用 | 理由 |
|------------------|------------|---------|------|
| `cli/commands/*` (qa) | `core/`, `protocol/a2a/`, `protocol/mcp/`, `observability/` | — | CLI 是顶层入口 |
| `board/handlers/*` (frontend) | `core/` 的只读 API, `observability/` | `protocol/*` | 板子是控制面，不直接出网 |
| `protocol/a2a/server.py` (backend2) | `core/` (callbacks), `observability/` | `cli/`, `board/` | A2A 是协议层 |
| `protocol/mcp/server.py` (backend2) | `core/` (callbacks), `observability/` | `cli/`, `board/` | 同上 |
| `core/*` (backend) | `transport/`, `team/`, `agent/`, `database/`, `events/` (只读) | `cli/`, `board/`, `protocol/*` | Core 是中间层 |
| `observability/*` (qa2) | 仅 stdlib + OTel SDK | 业务模块 | 可观测性是被动监听 |
| `transport/*` (内部) | `core/` 的 dataclass type | — | — |

**关键约束 (Freeze Rule)**:
- **Core 不能 import `protocol/`、`cli/`、`board/`** — 这是层间隔离
- **Protocol 不能 import `cli/`、`board/`** — 同上
- **Observability 不能 import 任何业务模块** — 它只能"被注入"
- **依赖方向**: `cli` → `core` ← `protocol` (core 不依赖任一侧)

### 1.3 文件所有权 (No Overlap)

| 路径 | 负责人 | 其他人**只读** | 理由 |
|------|--------|---------------|------|
| `agentteam/core/` (新建) | backend | ✅ | 宪法由 backend 起草 |
| `agentteam/agent/` (充实) | backend | ✅ | 同上 |
| `agentteam/protocol/a2a/` (新建) | backend2 | ✅ | A2A 协议 |
| `agentteam/protocol/mcp/` (新建) | backend2 | ✅ | MCP 协议 |
| `agentteam/board/handlers/` (新建) | frontend | ✅ | UI 层 |
| `agentteam/board/sse/` (新建) | frontend | ✅ | 同上 |
| `agentteam/cli/commands/` (新建) | qa | ✅ | CLI |
| `agentteam/observability/` (新建) | qa2 | ✅ | OTel |
| `agentteam/exceptions.py` (改造) | qa2 | ✅ | 统一异常 |
| `agentteam/transport/` (升级) | backend2 | ✅ | 传输层 |
| `agentteam/plugins/__init__.py` (去单例) | backend2 | ✅ | 旁路 (P1) |
| `agentteam/orchestrator/dag.py` (扩展) | backend | ✅ | DAG 步类型扩展 |
| `docs/IMPLEMENTATION_BLUEPRINT.md` | architect | 任何人 review | 蓝图由架构师维护 |
| `docs/INTERFACE_CONTRACTS.md` (本文件) | architect | 任何人 review | 同上 |

---

## 2. Backend 任务: `agentteam/core/` 拆包导出契约

### 2.1 任务范围 (摘自 UPGRADE_PROPOSAL.md §5.1.1)

**目标**: 将 414 行的 `agentteam/core.py` (CTTeam/CTAgent/CTTask/CTMessage) + 周边 4 个 manager (`TeamManager`/`LifecycleManager`/`MailboxManager`/`PlanManager`) 拆分为 `agentteam/core/` 子包。

**验收** (本契约 §8.1 详细 checklist):
- `from agentteam.core import Team, Agent, Task, Message, run` 全部可用
- `cli/commands.py` 中所有 `from agentteam.core import CTTeam` 改为 `from agentteam.core import Team`，并加 `CTTeam = Team` shim 保证向后兼容
- `from agentteam.core.async_api import wait_all_async` 可用
- 现有 675 测试全过

### 2.2 必须导出的符号 (Freeze)

`agentteam/core/__init__.py` 应当**只 re-export** 以下符号（具体实现可分散到 `core/team.py`、`core/agent.py` 等子模块，`__init__.py` 聚合）：

```python
# agentteam/core/__init__.py  ——  接口契约，backend 必须照此实现
from __future__ import annotations
from agentteam.core.team import Team  # CTTeam 重命名
from agentteam.core.agent import Agent  # CTAgent 重命名
from agentteam.core.task import Task  # CTTask 重命名
from agentteam.core.message import Message, MessageEnvelope  # 升级版 (含 transport envelope)
from agentteam.core.enums import AgentState, TaskState, TeamState
from agentteam.core.protocols import (
    TeamProtocol,
    AgentProtocol,
    TaskProtocol,
    MessageBusProtocol,
    CallbackRegistryProtocol,
)
from agentteam.core.callbacks import (
    CallbackRegistry,
    register_default_callbacks,
    fire_event,
)
from agentteam.core.exceptions import (
    CoreError,
    TeamNotFoundError,
    AgentNotFoundError,
    TaskNotFoundError,
    CallbackError,
    AsyncNotSupportedError,
)
from agentteam.core.async_api import (
    wait_all_async,
    spawn_agent_async,
    send_message_async,
    AsyncTeam,
)
from agentteam.core.compat import CTTeam, CTAgent, CTTask  # 向后兼容 shim

__all__ = [
    "Team", "Agent", "Task", "Message", "MessageEnvelope",
    "AgentState", "TaskState", "TeamState",
    "TeamProtocol", "AgentProtocol", "TaskProtocol",
    "MessageBusProtocol", "CallbackRegistryProtocol",
    "CallbackRegistry", "register_default_callbacks", "fire_event",
    "CoreError", "TeamNotFoundError", "AgentNotFoundError",
    "TaskNotFoundError", "CallbackError", "AsyncNotSupportedError",
    "wait_all_async", "spawn_agent_async", "send_message_async", "AsyncTeam",
    "CTTeam", "CTAgent", "CTTask",  # compat shim
]
```

### 2.3 Protocol 类定义 (用 typing.Protocol, backend 必须实现)

```python
# agentteam/core/protocols.py
from __future__ import annotations
from typing import Any, Awaitable, Callable, Protocol, runtime_checkable
from agentteam.core.enums import AgentState, TaskState, TeamState


@runtime_checkable
class AgentProtocol(Protocol):
    """Agent 的最小契约 — 任何能跑 LLM 的实体都应满足"""
    agent_id: str
    name: str
    agent_type: str  # "coder" / "reviewer" / "architect" / ...
    state: AgentState
    session_key: str
    team_name: str
    task_id: str | None
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentProtocol": ...
    async def run_async(self, prompt: str, **ctx: Any) -> "AgentResult": ...
    def run(self, prompt: str, **ctx: Any) -> "AgentResult": ...


@runtime_checkable
class TaskProtocol(Protocol):
    task_id: str
    title: str
    description: str
    status: TaskState
    depends_on: list[str]
    assigned_agent: str | None
    created_at: float
    updated_at: float
    metadata: dict[str, Any]


@runtime_checkable
class TeamProtocol(Protocol):
    team_name: str
    agents: dict[str, AgentProtocol]
    tasks: dict[str, TaskProtocol]
    state: TeamState

    # 同步 API (保持兼容)
    def add_agent(self, agent: AgentProtocol) -> None: ...
    def spawn_agent(self, name: str, agent_type: str, **kw: Any) -> AgentProtocol: ...
    def add_task(self, task: TaskProtocol) -> None: ...
    def assign_task(self, task_id: str, agent_id: str) -> None: ...
    def send_message(self, from_id: str, to_id: str, content: str) -> str: ...
    def wait_all(self, timeout: float | None = 3600.0) -> dict[str, Any]: ...
    def get_status(self) -> dict[str, Any]: ...

    # 异步 API (新增, 渐进迁移)
    async def wait_all_async(self, timeout: float | None = None) -> dict[str, Any]: ...
    async def spawn_agent_async(self, name: str, agent_type: str, **kw: Any) -> AgentProtocol: ...


@runtime_checkable
class MessageBusProtocol(Protocol):
    """消息总线 — transport 层实现 (file / p2p / redis)"""
    def publish(self, envelope: "MessageEnvelope") -> None: ...
    def subscribe(self, agent_id: str, callback: Callable[["MessageEnvelope"], None]) -> None: ...
    def unsubscribe(self, agent_id: str) -> None: ...
    async def publish_async(self, envelope: "MessageEnvelope") -> None: ...


@runtime_checkable
class CallbackRegistryProtocol(Protocol):
    """钩子注册 — 取代 PluginManager 的部分职责"""
    def register(self, event: str, callback: Callable[..., Any]) -> None: ...
    def unregister(self, event: str, callback: Callable[..., Any]) -> None: ...
    def fire(self, event: str, *args: Any, **kwargs: Any) -> list[Any]: ...
    def list_events(self) -> list[str]: ...
```

### 2.4 CallbackRegistry 行为契约

```python
# agentteam/core/callbacks.py
from __future__ import annotations
import asyncio
import inspect
import threading
from collections import defaultdict
from typing import Any, Callable

class CallbackRegistry:
    """事件回调中心, 替代 PluginManager.__new__ 单例的部分职责

    设计原则:
    - 不是单例, 可创建多实例 (每个 team / 每个 session 一个)
    - 线程安全 (threading.Lock)
    - 异步友好 (callable 可以是 async function)
    - 失败隔离 (一个 callback 抛错不影响其他)
    """

    def __init__(self, name: str = "default") -> None:
        self._name = name
        self._handlers: dict[str, list[Callable[..., Any]]] = defaultdict(list)
        self._lock = threading.RLock()

    @property
    def name(self) -> str:
        return self._name

    def register(self, event: str, callback: Callable[..., Any]) -> None:
        """注册事件回调。重复注册同一 callback 会被忽略。"""
        with self._lock:
            if callback not in self._handlers[event]:
                self._handlers[event].append(callback)

    def unregister(self, event: str, callback: Callable[..., Any]) -> None:
        with self._lock:
            try:
                self._handlers[event].remove(callback)
            except ValueError:
                pass

    def fire(self, event: str, *args: Any, **kwargs: Any) -> list[Any]:
        """同步触发。所有 callback 串行执行，异常被记录但不中断。"""
        with self._lock:
            handlers = list(self._handlers[event])
        results: list[Any] = []
        for h in handlers:
            try:
                if inspect.iscoroutinefunction(h):
                    # 同步 fire 不能 await, 给出警告
                    continue
                results.append(h(*args, **kwargs))
            except Exception:
                # 失败隔离 — 记录到 observability, 不向上抛
                continue
        return results

    async def fire_async(self, event: str, *args: Any, **kwargs: Any) -> list[Any]:
        with self._lock:
            handlers = list(self._handlers[event])
        results: list[Any] = []
        for h in handlers:
            try:
                if inspect.iscoroutinefunction(h):
                    results.append(await h(*args, **kwargs))
                else:
                    results.append(h(*args, **kwargs))
            except Exception:
                continue
        return results

    def list_events(self) -> list[str]:
        with self._lock:
            return [k for k, v in self._handlers.items() if v]

    def clear(self) -> None:
        with self._lock:
            self._handlers.clear()


# 事件名常量 (Freeze — 不可改)
class CoreEvents:
    AGENT_SPAWNED = "core.agent.spawned"
    AGENT_TERMINATED = "core.agent.terminated"
    AGENT_STATE_CHANGED = "core.agent.state_changed"
    TASK_CREATED = "core.task.created"
    TASK_ASSIGNED = "core.task.assigned"
    TASK_COMPLETED = "core.task.completed"
    TASK_FAILED = "core.task.failed"
    MESSAGE_SENT = "core.message.sent"
    MESSAGE_RECEIVED = "core.message.received"
    TEAM_STATE_CHANGED = "core.team.state_changed"
```

### 2.5 Core 异常类契约 (qa2 复用)

```python
# agentteam/core/exceptions.py
class CoreError(Exception):
    """所有 Core 层异常的基类"""
    code: str = "core_error"
    def __init__(self, message: str, *, code: str | None = None, context: dict | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.context = context or {}


class TeamNotFoundError(CoreError):
    code = "team_not_found"

class AgentNotFoundError(CoreError):
    code = "agent_not_found"

class TaskNotFoundError(CoreError):
    code = "task_not_found"

class CallbackError(CoreError):
    code = "callback_failed"

class AsyncNotSupportedError(CoreError):
    code = "async_not_supported"
    def __init__(self, method_name: str):
        super().__init__(f"{method_name}() 不支持异步调用, 请用同步版本")
```

### 2.6 异步 API 契约

```python
# agentteam/core/async_api.py
from __future__ import annotations
import asyncio
from typing import Any
from agentteam.core.team import Team
from agentteam.core.agent import Agent
from agentteam.core.exceptions import AsyncNotSupportedError


async def wait_all_async(team: Team, timeout: float | None = None) -> dict[str, Any]:
    """异步等待所有 agent 完成任务 (替代 time.sleep 轮询)

    实现要求 (Freeze):
    - 用 asyncio.timeout() 而不是 signal.alarm
    - 内部 polling 间隔 <= 0.5s (vs 旧版 10s)
    - 返回结构与同步 wait_all 完全一致
    """
    loop = asyncio.get_event_loop()
    poll_interval = 0.5
    deadline = loop.time() + (timeout or 3600.0)
    while loop.time() < deadline:
        statuses = team.get_status()
        if all(a["state"] in ("completed", "failed", "terminated")
               for a in statuses["agents"].values()):
            return statuses
        await asyncio.sleep(poll_interval)
    raise asyncio.TimeoutError(f"wait_all_async timeout after {timeout}s")


async def spawn_agent_async(team: Team, name: str, agent_type: str, **kw: Any) -> Agent:
    """异步 spawn (用 asyncio.to_thread 包装同步 spawn 兼容老 backend)"""
    return await asyncio.to_thread(team.spawn_agent, name, agent_type, **kw)


async def send_message_async(team: Team, from_id: str, to_id: str, content: str) -> str:
    return await asyncio.to_thread(team.send_message, from_id, to_id, content)
```

---

## 3. Backend2 任务: A2A + MCP 协议契约

### 3.1 A2A Server 契约 (`agentteam/protocol/a2a/`)

**目标**: 实现 A2A (Agent-to-Agent) Server，让 LangGraph/AutoGen/CrewAI 的 agent 可以把任务委派给 AgentTeam。

**对接规范** (Freeze):
- 协议版本: A2A v0.3 (`a2a-python` 库)
- 默认端口: 41241
- 必暴露端点: `/.well-known/agent-card.json`, `/a2a/jsonrpc`, `/a2a/stream`
- AgentCard 从 `RoleStore` (即 `agentteam/team/roles.py`) 动态生成

#### 3.1.1 必备 dataclass schema (`protocol/a2a/contracts.py`)

```python
# agentteam/protocol/a2a/contracts.py
from __future__ import annotations
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict


# === AgentCard (Freeze — 对齐 a2a-python AgentCard) ===
class AgentSkill(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    name: str
    description: str = Field(min_length=10)
    tags: list[str] = []


class AgentCapabilities(BaseModel):
    model_config = ConfigDict(extra="forbid")
    streaming: bool = True
    push_notifications: bool = True
    state_transition_history: bool = True


class AgentCard(BaseModel):
    """A2A agent 描述卡 — 从 RoleStore 自动生成"""
    model_config = ConfigDict(extra="forbid")
    name: str
    description: str
    url: str  # e.g. "http://localhost:41241"
    version: str = "1.0.0"
    capabilities: AgentCapabilities = Field(default_factory=AgentCapabilities)
    skills: list[AgentSkill]
    default_input_modes: list[str] = ["text"]
    default_output_modes: list[str] = ["text"]


# === Task & Message (Freeze) ===
class A2ATaskState(str, Enum):
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class TextPart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["text"] = "text"
    text: str


class A2AMessage(BaseModel):
    """A2A 消息 = 角色 + parts"""
    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "agent"]
    parts: list[TextPart]


class A2AArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    description: str = ""
    parts: list[TextPart]


class A2ATask(BaseModel):
    """A2A Task — backend2 必须与 CTTask 双向映射"""
    model_config = ConfigDict(extra="forbid")
    id: str
    context_id: str | None = None
    state: A2ATaskState = A2ATaskState.SUBMITTED
    messages: list[A2AMessage] = []
    artifacts: list[A2AArtifact] = []
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    metadata: dict[str, Any] = {}

    # 映射关系 — backend2 必须实现
    @classmethod
    def from_ct_task(cls, ct_task: Any) -> "A2ATask":
        """从 CTTask 转 A2ATask"""
        ...
    def to_ct_task(self) -> Any:
        """反向 — 写到 MailboxManager"""
        ...


# === JSON-RPC 请求/响应 (Freeze) ===
class JsonRpcRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    jsonrpc: Literal["2.0"] = "2.0"
    id: str | int
    method: str  # "message/send" | "message/stream" | "tasks/get" | "tasks/cancel"
    params: dict[str, Any]


class JsonRpcError(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: int
    message: str
    data: dict[str, Any] | None = None


class JsonRpcResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    jsonrpc: Literal["2.0"] = "2.0"
    id: str | int
    result: Any | None = None
    error: JsonRpcError | None = None


# === A2A → CTTeam callback 契约 ===
@dataclass
class A2AInboundMessage:
    """A2A server 收到外部 agent 的 message 后, 必须转成这个 dataclass
    再调用 core/team.send_message"""
    a2a_task_id: str
    context_id: str | None
    from_role: str  # 对应 A2AMessage.role
    to_team: str  # AgentTeam team name
    to_agent: str | None  # None = 广播
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


# === register_to_team 回调接口 ===
class TeamMessageCallback(Protocol):
    """A2A executor 必须实现的回调 — 委派给 MailboxManager"""
    def __call__(self, msg: A2AInboundMessage) -> str: ...
    # 返回 A2A task id
```

#### 3.1.2 A2A server 启动契约 (CLI 注册接口)

backend2 必须在 `agentteam.cli.commands.a2a` sub-app 注册以下命令 (qa 拆分 cli 时调用):

```python
# agentteam/protocol/a2a/cli.py  —  由 qa 在 cli/commands/a2a.py 中 import
from typing import Protocol

class A2ACLIProtocol(Protocol):
    """A2A server 的 CLI 启动接口 — qa 会用 typer 注册"""
    def serve(self, port: int = 41241, team: str = "default",
              transport: Literal["http", "https"] = "http") -> None: ...
    def show_card(self, team: str = "default", output: str = "json") -> None: ...
    def list_skills(self, team: str = "default") -> list[str]: ...
```

### 3.2 MCP Server 契约 (`agentteam/protocol/mcp/`)

**目标**: 把 AgentTeam 工具 (`agentteam/tools/registry.py`) 暴露为 MCP Server, 让 Claude Desktop / Cursor / Cline 能调用。

**对接规范** (Freeze):
- 协议版本: MCP 2025-06-18
- 传输: stdio (默认) + Streamable HTTP (可选)
- JSON-RPC 2.0 + `Mcp-Session-Id` header

#### 3.2.1 MCP Tool Schema (Freeze — backend2 必须导出)

```python
# agentteam/protocol/mcp/contracts.py
from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict
from typing import Any, Literal


class MCPToolParameter(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["string", "integer", "number", "boolean", "object", "array"]
    description: str
    enum: list[Any] | None = None
    default: Any | None = None


class MCPToolSchema(BaseModel):
    """对标 MCP 2025-06-18 tools/list 端点格式"""
    model_config = ConfigDict(extra="forbid")
    name: str = Field(pattern=r"^[a-z0-9_]+$")
    description: str = Field(min_length=10)
    inputSchema: dict[str, Any]  # JSON Schema
    annotations: dict[str, Any] | None = None


# === AgentTeam 必须暴露的 MCP 工具 (Freeze — 6 个) ===
AGENTTEAM_MCP_TOOLS: list[MCPToolSchema] = [
    MCPToolSchema(
        name="agentteam_list_agents",
        description="列出指定 team 的所有 agent 状态",
        inputSchema={
            "type": "object",
            "properties": {
                "team": {"type": "string", "description": "Team 名称"}
            },
            "required": ["team"]
        }
    ),
    MCPToolSchema(
        name="agentteam_get_status",
        description="获取指定 team/agent 的当前状态、任务进度",
        inputSchema={
            "type": "object",
            "properties": {
                "team": {"type": "string"},
                "agent": {"type": "string", "description": "Agent 名称, 留空取团队整体"}
            },
            "required": ["team"]
        }
    ),
    MCPToolSchema(
        name="agentteam_send_message",
        description="向 team 内的 agent 发送消息",
        inputSchema={
            "type": "object",
            "properties": {
                "team": {"type": "string"},
                "to": {"type": "string", "description": "目标 agent 名称"},
                "content": {"type": "string", "description": "消息内容"}
            },
            "required": ["team", "to", "content"]
        }
    ),
    MCPToolSchema(
        name="agentteam_create_task",
        description="在 team 中创建任务",
        inputSchema={
            "type": "object",
            "properties": {
                "team": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "depends_on": {"type": "array", "items": {"type": "string"}, "default": []}
            },
            "required": ["team", "title", "description"]
        }
    ),
    MCPToolSchema(
        name="agentteam_assign_task",
        description="将任务分配给指定 agent",
        inputSchema={
            "type": "object",
            "properties": {
                "team": {"type": "string"},
                "task_id": {"type": "string"},
                "agent": {"type": "string"}
            },
            "required": ["team", "task_id", "agent"]
        }
    ),
    MCPToolSchema(
        name="agentteam_spawn_agent",
        description="在 team 中 spawn 一个新 agent",
        inputSchema={
            "type": "object",
            "properties": {
                "team": {"type": "string"},
                "name": {"type": "string"},
                "role": {"type": "string", "description": "coder / reviewer / architect / ..."},
                "provider": {"type": "string", "default": "auto"}
            },
            "required": ["team", "name", "role"]
        }
    ),
]


# === MCP 资源 (暴露 ~/.agentteam/ 目录) ===
class MCPResource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    uri: str  # e.g. "file://~/.agentteam/skills"
    name: str
    description: str
    mimeType: str = "text/plain"


# === Sampling 协议契约 (参考 SpectrAI SamplingServer.ts) ===
class MCPSamplingRequest(BaseModel):
    """Server → Client 的 sampling/createMessage 请求"""
    model_config = ConfigDict(extra="forbid")
    messages: list[dict[str, Any]]
    systemPrompt: str | None = None
    temperature: float | None = None
    maxTokens: int | None = None
    includeContext: str | None = None  # "thisServer" | "allServers" | None


class MCPSamplingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["assistant"] = "assistant"
    content: list[dict[str, Any]]  # text / image / tool_use blocks
    model: str
    stopReason: str | None = None


# === MCP Server 启动契约 (CLI 注册接口) ===
class MCPCLIProtocol(Protocol):
    """MCP server 的 CLI 启动接口 — qa 会用 typer 注册"""
    def serve(self, transport: Literal["stdio", "http"] = "stdio",
              port: int = 41242) -> None: ...
    def list_tools(self) -> list[str]: ...
```

#### 3.2.2 Sampling 协议实现要点 (借鉴 SpectrAI SamplingServer.ts)

参考 `SpectrAI-ref/main/chunks/SamplingServer.ts:32-100`:
- Server 端 `createMessageStream` 必须先检查 `getClientCapabilities()?.sampling` 是否存在
- 验证 `tool_result` 块必须与上一轮 `tool_use` 配对
- 流式返回用 `requestStream(method, params, schema, options)`
- 我们的 Python 端用 `mcp.server.Server` 的 `request_stream` 抽象

### 3.3 协议层与 Core 的解耦约定 (Freeze)

**backend2 必须遵守**:
1. **不直接 import** `from agentteam.core import Team` — 而是通过 `CallbackRegistryProtocol` (本契约 §2.3) 拿到回调
2. **不调用** `team.send_message()` — 而是把消息封装成 `A2AInboundMessage` dataclass, 调用由 backend 注册的 `TeamMessageCallback`
3. **配置注入**: backend 启动时调用 `protocol.a2a.executor.register_team_callback(team, callback)`
4. **停止协议**: 提供 `protocol.a2a.executor.unregister_team_callback(team)` — backend2 负责实现, 由 backend 触发

---

## 4. Frontend 任务: `board/handlers/` 拆分契约

### 4.1 任务范围

**目标**: 将 3104 行的 `board/server.py` 拆分为 `board/handlers/` 子包 + `board/sse/` 子包, 同时引入 FastAPI (P2, 暂不强制)。

**验收**:
- `board/server.py` 缩到 ≤ 200 行 (入口)
- 每个 handler 文件 ≤ 300 行
- 所有现有 `/api/*` 端点行为完全一致
- 端到端单测全过

### 4.2 Handler 模块契约

```python
# agentteam/board/handlers/base.py
from __future__ import annotations
from typing import Any, Protocol
from agentteam.core.protocols import TeamProtocol, CallbackRegistryProtocol


class BoardHandlerContext(Protocol):
    """每个 handler 拿到的上下文 — 由 board/server.py 注入"""
    team: TeamProtocol
    callbacks: CallbackRegistryProtocol
    storage: Any  # 旧 board 用的 sqlite handle
    config: dict[str, Any]
    request_id: str


class BoardHandler(Protocol):
    """所有 handler 必须实现的契约"""
    route_prefix: str  # e.g. "/api/teams"
    methods: list[str]  # e.g. ["GET", "POST"]

    async def handle(self, ctx: BoardHandlerContext,
                     method: str, path: str,
                     query: dict[str, Any],
                     body: dict[str, Any] | None) -> tuple[int, dict[str, Any]]:
        """返回 (HTTP status, JSON body)"""
        ...


# === 各 handler 的具体契约 ===

# agentteam/board/handlers/teams.py
class TeamsHandler(BoardHandler, Protocol):
    route_prefix = "/api/teams"
    methods = ["GET", "POST"]
    async def handle(self, ctx, method, path, query, body) -> tuple[int, dict]: ...

# agentteam/board/handlers/agents.py
class AgentsHandler(BoardHandler, Protocol):
    route_prefix = "/api/agents"
    methods = ["GET", "POST", "PUT", "DELETE"]
    async def handle(self, ctx, method, path, query, body) -> tuple[int, dict]: ...

# agentteam/board/handlers/tasks.py
class TasksHandler(BoardHandler, Protocol):
    route_prefix = "/api/tasks"
    methods = ["GET", "POST", "PUT", "DELETE"]
    async def handle(self, ctx, method, path, query, body) -> tuple[int, dict]: ...

# agentteam/board/handlers/messages.py
class MessagesHandler(BoardHandler, Protocol):
    route_prefix = "/api/messages"
    methods = ["GET", "POST"]
    async def handle(self, ctx, method, path, query, body) -> tuple[int, dict]: ...

# agentteam/board/handlers/chat.py
class ChatHandler(BoardHandler, Protocol):
    route_prefix = "/api/chat"
    methods = ["POST"]
    async def handle(self, ctx, method, path, query, body) -> tuple[int, dict]: ...

# agentteam/board/handlers/metrics.py
class MetricsHandler(BoardHandler, Protocol):
    route_prefix = "/api/metrics"
    methods = ["GET"]
    async def handle(self, ctx, method, path, query, body) -> tuple[int, dict]: ...

# agentteam/board/handlers/static.py
class StaticHandler(BoardHandler, Protocol):
    route_prefix = "/static"
    methods = ["GET"]
    async def handle(self, ctx, method, path, query, body) -> tuple[int, bytes]: ...
```

### 4.3 SSE 子包契约

```python
# agentteam/board/sse/broadcaster.py
from __future__ import annotations
import asyncio
from typing import AsyncIterator, Protocol

class SSEBroadcasterProtocol(Protocol):
    """SSE 多客户端广播器 — frontend 必须实现"""
    async def publish(self, event: str, data: dict) -> None: ...
    def subscribe(self, client_id: str) -> "SSEChannelProtocol": ...
    def unsubscribe(self, client_id: str) -> None: ...
    def total_clients(self) -> int: ...


class SSEChannelProtocol(Protocol):
    async def events(self) -> AsyncIterator[tuple[str, dict]]: ...
    def close(self) -> None: ...


# === 事件类型 (Freeze) ===
class SSEEvents:
    AGENT_STATE_CHANGED = "agent.state_changed"
    TASK_PROGRESS = "task.progress"
    MESSAGE_RECEIVED = "message.received"
    ALERT_RAISED = "alert.raised"
    LOG_LINE = "log.line"
    METRICS_TICK = "metrics.tick"
```

### 4.4 Frontend 与 Backend 的回调约定

**frontend 必须遵守**:
1. 所有 handler 通过 `BoardHandlerContext` 拿 `team` 和 `callbacks` — **不直接 import** core 内部
2. 触发事件时, 调用 `ctx.callbacks.fire(CoreEvents.AGENT_STATE_CHANGED, ...)` — **不直接调** `team.add_agent()`
3. SSE 广播必须通过 `SSEBroadcasterProtocol` — **不直接** 操作 websocket
4. 静态文件由 `StaticHandler` 单独管, 不混入 API

**frontend 可用**:
- `from agentteam.core.protocols import TeamProtocol, CallbackRegistryProtocol`
- `from agentteam.core.enums import AgentState, TaskState`
- `from agentteam.core.exceptions import AgentNotFoundError, ...` (本契约 §2.5)

---

## 5. QA 任务: `cli/commands/` sub-app 注册契约

### 5.1 任务范围

**目标**: 将 5894 行的 `cli/commands.py` 拆分为 `cli/commands/` 子包, 50+ 命令按 feature 分文件。

**验收**:
- `cli/commands.py` 缩到 ≤ 100 行 (仅 shim)
- `agentteam.cli.app:app` (typer) 总入口
- 每个命令文件 ≤ 300 行
- 旧 CLI 行为完全一致 (`agentteam --help` 输出不变)

### 5.2 CLI 拆分目标结构

```
agentteam/cli/
├── __init__.py
├── app.py                  # 总入口 typer.Typer, 注册所有 sub-app
├── commands.py             # 兼容 shim (重导出)
├── _utils.py               # 共享的 typer 选项 / 全局 callback
└── commands/
    ├── __init__.py
    ├── team.py             # agentteam team *
    ├── agent.py            # agentteam agent *
    ├── task.py             # agentteam task *
    ├── board.py            # agentteam board *
    ├── skill.py            # agentteam skill *
    ├── plugin.py           # agentteam plugin *
    ├── config.py           # agentteam config *
    ├── init.py             # agentteam init  (qa 也会写)
    ├── a2a.py              # agentteam a2a * (从 protocol.a2a.cli 导入)
    ├── mcp.py              # agentteam mcp * (从 protocol.mcp.cli 导入)
    ├── metrics.py          # agentteam metrics * (从 observability 导入)
    └── doctor.py           # agentteam doctor / diagnose
```

### 5.3 Sub-app 注册接口 (Freeze)

```python
# agentteam/cli/commands/_base.py  — qa 实现
from __future__ import annotations
import typer
from typing import Protocol

class SubAppProtocol(Protocol):
    """每个 commands/*.py 必须导出的对象"""
    app: typer.Typer  # typer 应用
    name: str         # 注册到主 app 的名字 (e.g. "team", "board", "a2a")
    help_text: str    # typer 显示的帮助

# 用法 (在 cli/app.py):
#   from agentteam.cli.commands.team import app as team_app
#   app.add_typer(team_app, name="team", help="...")
```

### 5.4 Sub-app 标准模板 (qa 必须遵循)

```python
# agentteam/cli/commands/a2a.py  — 由 qa 写, 但调用 backend2 实现的 protocol
from __future__ import annotations
import typer
from agentteam.protocol.a2a.cli import A2ACLIProtocol, get_a2a_cli  # 来自 backend2

app = typer.Typer(help="A2A (Agent-to-Agent) Server 管理")
name = "a2a"
help_text = "A2A Server 命令"


@a2a_app.command("serve")
def serve_cmd(
    port: int = typer.Option(41241, "--port", "-p", help="监听端口"),
    team: str = typer.Option("default", "--team", "-t", help="AgentTeam team 名"),
    transport: str = typer.Option("http", "--transport", help="http / https"),
) -> None:
    """启动 A2A Server, 暴露 /.well-known/agent-card.json"""
    cli: A2ACLIProtocol = get_a2a_cli()
    cli.serve(port=port, team=team, transport=transport)


@a2a_app.command("card")
def show_card_cmd(
    team: str = typer.Option("default", "--team", "-t"),
    output: str = typer.Option("json", "--output", "-o"),
) -> None:
    """显示 AgentCard 内容"""
    cli = get_a2a_cli()
    cli.show_card(team=team, output=output)
```

### 5.5 QA 与其他工程师的协作约定

- **qa 不实现** `protocol/a2a/cli.py` 和 `protocol/mcp/cli.py` — 那是 backend2 的工作
- **qa 只写** `cli/commands/a2a.py` 和 `cli/commands/mcp.py` 调用上面接口
- **qa 必须等** backend2 提交 `A2ACLIProtocol` / `MCPCLIProtocol` 后才能写对应 sub-app
- **qa 同时负责** `cli/commands/init.py` (UPGRADE_PROPOSAL §5.7.1 引导) 和 `cli/commands/metrics.py` (与 qa2 协调)

---

## 6. QA2 任务: 可观测性 / OTel / 异常契约

### 6.1 任务范围

**目标**: 引入 OpenTelemetry SDK + 统一异常类 (`agentteam/exceptions.py` 升级) + Prometheus exporter (可选 P1)。

**验收**:
- `agentteam/observability/` 新建子包
- 默认开启 OTel, 输出到 stdout (开发) / OTLP (生产)
- 现有 40+ 事件类型自动转 OTel span
- `agentteam metrics serve --port 9090` 暴露 Prometheus `/metrics`

### 6.2 Observability 子包导出契约

```python
# agentteam/observability/__init__.py  — qa2 实现
from __future__ import annotations
from agentteam.observability.tracing import (
    init_tracing,
    get_tracer,
    start_span,
    trace_span,
    TracerProtocol,
)
from agentteam.observability.metrics import (
    init_metrics,
    get_meter,
    Counter,
    Gauge,
    Histogram,
    MetricsProtocol,
)
from agentteam.observability.events import (
    EventBridge,
    event_to_span,
    event_to_metric,
)
from agentteam.observability.exporters import (
    OTelStdoutExporter,
    OTelOTLPExporter,
    PrometheusExporter,
)


__all__ = [
    "init_tracing", "get_tracer", "start_span", "trace_span", "TracerProtocol",
    "init_metrics", "get_meter", "Counter", "Gauge", "Histogram", "MetricsProtocol",
    "EventBridge", "event_to_span", "event_to_metric",
    "OTelStdoutExporter", "OTelOTLPExporter", "PrometheusExporter",
]
```

### 6.3 Tracer 协议 (Freeze)

```python
# agentteam/observability/tracing.py
from __future__ import annotations
from contextlib import contextmanager
from typing import Any, Callable, Iterator, Protocol
from opentelemetry.trace import Span, Status, StatusCode


class TracerProtocol(Protocol):
    """OTel Tracer 的轻量抽象, 便于其他模块 mock"""

    @contextmanager
    def start_as_current_span(self, name: str, **attrs: Any) -> Iterator[Span]: ...

    def set_attribute(self, key: str, value: Any) -> None: ...
    def record_exception(self, exc: BaseException) -> None: ...
    def set_status(self, status: Status, description: str | None = None) -> None: ...


def init_tracing(service_name: str = "agentteam",
                 otlp_endpoint: str | None = None,
                 sample_ratio: float = 1.0) -> TracerProtocol:
    """初始化 OTel tracer, 返回 TracerProtocol 实例"""
    ...


@contextmanager
def trace_span(name: str, **attrs: Any) -> Iterator[Span]:
    """全局便捷函数, 用于装饰代码块"""
    ...


def trace_span_decorator(name: str | None = None, **attrs: Any) -> Callable:
    """装饰器版本"""
    def decorator(func: Callable) -> Callable:
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any: ...
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any: ...
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator
```

### 6.4 Metrics 协议 (Freeze)

```python
# agentteam/observability/metrics.py
from __future__ import annotations
from typing import Protocol


class Counter(Protocol):
    def add(self, amount: int | float = 1, **attrs: Any) -> None: ...


class Gauge(Protocol):
    def set(self, value: int | float, **attrs: Any) -> None: ...
    def add(self, amount: int | float, **attrs: Any) -> None: ...


class Histogram(Protocol):
    def record(self, value: int | float, **attrs: Any) -> None: ...


class MetricsProtocol(Protocol):
    def counter(self, name: str, unit: str = "", description: str = "") -> Counter: ...
    def gauge(self, name: str, unit: str = "", description: str = "") -> Gauge: ...
    def histogram(self, name: str, unit: str = "", description: str = "") -> Histogram: ...


# === 预定义 metrics (Freeze — 所有模块复用) ===
AGENTTEAM_METRICS = {
    "agent.spawn.count": ("counter", "agents", "Total agents spawned"),
    "agent.spawn.duration_ms": ("histogram", "ms", "Time to spawn an agent"),
    "agent.message.count": ("counter", "messages", "Messages exchanged"),
    "agent.message.latency_ms": ("histogram", "ms", "Message delivery latency"),
    "task.create.count": ("counter", "tasks", "Tasks created"),
    "task.complete.duration_ms": ("histogram", "ms", "Task end-to-end duration"),
    "task.failed.count": ("counter", "tasks", "Tasks failed"),
    "transport.message.count": ("counter", "messages", "Transport-level messages"),
    "callback.fire.count": ("counter", "events", "CallbackRegistry fires"),
    "callback.error.count": ("counter", "errors", "Callback errors"),
}
```

### 6.5 Event → OTel 桥接契约

```python
# agentteam/observability/events.py
from __future__ import annotations
from typing import Any, Protocol
from agentteam.core.callbacks import CallbackRegistry, CoreEvents
from agentteam.observability.tracing import TracerProtocol
from agentteam.observability.metrics import MetricsProtocol


class EventBridgeProtocol(Protocol):
    """把 CoreEvents 翻译成 OTel span/metric"""

    def install(self, registry: CallbackRegistry,
                tracer: TracerProtocol,
                metrics: MetricsProtocol) -> None: ...

    def uninstall(self, registry: CallbackRegistry) -> None: ...


# === 事件名 → span 名映射 (Freeze) ===
EVENT_TO_SPAN_NAME: dict[str, str] = {
    CoreEvents.AGENT_SPAWNED: "agent.spawn",
    CoreEvents.AGENT_TERMINATED: "agent.terminate",
    CoreEvents.TASK_CREATED: "task.create",
    CoreEvents.TASK_COMPLETED: "task.complete",
    CoreEvents.TASK_FAILED: "task.fail",
    CoreEvents.MESSAGE_SENT: "message.send",
    CoreEvents.MESSAGE_RECEIVED: "message.receive",
    CoreEvents.TEAM_STATE_CHANGED: "team.state_change",
}


def event_to_span(event: str, payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """事件 → (span_name, span_attributes)"""
    span_name = EVENT_TO_SPAN_NAME.get(event, event.replace(".", "_"))
    return span_name, {f"agentteam.{k}": v for k, v in payload.items()}


def event_to_metric(event: str) -> str | None:
    """事件 → metric name, 仅对计数类事件"""
    mapping = {
        CoreEvents.AGENT_SPAWNED: "agent.spawn.count",
        CoreEvents.MESSAGE_SENT: "agent.message.count",
        CoreEvents.TASK_CREATED: "task.create.count",
        CoreEvents.TASK_FAILED: "task.failed.count",
    }
    return mapping.get(event)
```

### 6.6 统一异常类契约 (qa2 升级 `agentteam/exceptions.py`)

```python
# agentteam/exceptions.py  — qa2 升级
from __future__ import annotations
from typing import Any


class AgentTeamError(Exception):
    """所有 AgentTeam 异常的基类 — 所有 5 个模块的异常都继承这个

    设计原则:
    - 有 code 字段 (机器可读)
    - 有 context 字段 (可序列化的上下文)
    - 有 suggestions 字段 (人类可读的修复建议, 参考 Rust 编译器风格)
    """
    code: str = "agentteam_error"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        context: dict[str, Any] | None = None,
        suggestions: list[str] | None = None,
    ):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.context = context or {}
        self.suggestions = suggestions or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": self.code,
            "message": self.message,
            "context": self.context,
            "suggestions": self.suggestions,
        }


# === 由 5 个模块的异常都注册到这里 ===
# Core 异常 (来自 §2.5) 也继承 AgentTeamError
# 这样: from agentteam.exceptions import AgentTeamError  一处兜底

class ConfigurationError(AgentTeamError):
    code = "configuration_error"

class PluginError(AgentTeamError):
    code = "plugin_error"

class CLIError(AgentTeamError):
    code = "cli_error"
    exit_code: int = 1
    def __init__(self, message: str, *, exit_code: int = 1, **kw: Any):
        super().__init__(message, **kw)
        self.exit_code = exit_code
```

### 6.7 QA2 与其他工程师的协作约定

- **qa2 必须等** backend 完成 `core/callbacks.py` (本契约 §2.4) 后, 才能写 `EventBridge` 桥接
- **qa2 不修改** `core/` — 只通过 `CallbackRegistryProtocol` 注入
- **qa2 提供** `init_tracing()` 给 `agentteam/__init__.py` 在 `import` 时调用 (默认 stdout exporter)
- **qa 与 qa2 协调**: qa 写 `cli/commands/metrics.py`, qa2 写 `observability.exporters.PrometheusExporter`, 两者通过 `MetricsProtocol` 对接

---

## 7. 跨模块共享类型 (Team, Agent, Task, Message)

### 7.1 共享 dataclass 位置

**Freeze Rule**: 所有 5 个模块共享的类型, **只**在 `agentteam/core/` 下列文件定义, 其他人**只 import** 不定义:

| 类型 | 文件 | 谁可以定义 | 谁可以 import |
|------|------|------------|---------------|
| `Team`, `CTTeam` | `agentteam/core/team.py` | backend | 所有人 |
| `Agent`, `CTAgent`, `AgentState` | `agentteam/core/agent.py` | backend | 所有人 |
| `Task`, `CTTask`, `TaskState` | `agentteam/core/task.py` | backend | 所有人 |
| `Message`, `MessageEnvelope` | `agentteam/core/message.py` | backend | 所有人 |
| `TeamState` | `agentteam/core/enums.py` | backend | 所有人 |
| `CoreEvents` | `agentteam/core/callbacks.py` | backend | qa2 |
| `A2ATask`, `A2AMessage` | `agentteam/protocol/a2a/contracts.py` | backend2 | qa (仅类型) |
| `MCPToolSchema` | `agentteam/protocol/mcp/contracts.py` | backend2 | qa (仅类型) |
| `AgentTeamError` | `agentteam/exceptions.py` | qa2 | 所有人 |

### 7.2 类型兼容性 (Freeze)

`A2ATask.from_ct_task()` 必须能处理 backend 的 `Task` (反之亦然):

```python
# 伪代码 — backend2 实现
def from_ct_task(ct_task: "agentteam.core.Task") -> "A2ATask":
    return A2ATask(
        id=ct_task.task_id,
        state=A2ATaskState.from_task_state(ct_task.status),  # 枚举映射
        messages=[A2AMessage.from_ct_message(m) for m in ct_task.messages],
        metadata={"ct_task_id": ct_task.task_id, **ct_task.metadata},
    )
```

**TaskState → A2ATaskState 映射** (Freeze):

| `TaskState` (core) | `A2ATaskState` (a2a) |
|--------------------|----------------------|
| `PENDING` | `SUBMITTED` |
| `IN_PROGRESS` | `WORKING` |
| `BLOCKED` | `INPUT_REQUIRED` |
| `COMPLETED` | `COMPLETED` |
| `CANCELLED` | `CANCELED` |
| — | `FAILED` (core 无, 需 a2a 加) |

---

## 8. 接口冻结检查清单 (Interface Freeze Checklist)

### 8.1 Backend 任务 (`agentteam/core/`) 验收

- [ ] `agentteam/core/__init__.py` 存在, 导出 §2.2 全部 26 个符号
- [ ] `agentteam/core/protocols.py` 包含 5 个 `Protocol` 类 (§2.3)
- [ ] `agentteam/core/callbacks.py` 包含 `CallbackRegistry` + `CoreEvents` (§2.4)
- [ ] `agentteam/core/exceptions.py` 包含 6 个异常类 (§2.5), 全部继承 `AgentTeamError` (§6.6)
- [ ] `agentteam/core/async_api.py` 包含 4 个 async 函数 + `AsyncTeam` 类 (§2.6)
- [ ] `agentteam/core/compat.py` 提供 `CTTeam = Team` 等兼容 shim
- [ ] 现有 675 测试全过 (`pytest tests/`)
- [ ] `mypy agentteam/core/` 零 error
- [ ] `from agentteam.core import Team, Agent, Task` 三个 import 都能用

### 8.2 Backend2 任务 (`agentteam/protocol/`) 验收

- [ ] `agentteam/protocol/a2a/contracts.py` 包含 §3.1.1 全部 dataclass + Pydantic 模型
- [ ] `agentteam/protocol/mcp/contracts.py` 包含 §3.2.1 全部 6 个 `MCPToolSchema` + 资源/sampling 模型
- [ ] `agentteam/protocol/a2a/cli.py` 提供 `A2ACLIProtocol` 实现 (§3.1.2)
- [ ] `agentteam/protocol/mcp/cli.py` 提供 `MCPCLIProtocol` 实现 (§3.2.1)
- [ ] **不**直接 import `from agentteam.core import Team`, 只用 `CallbackRegistryProtocol` (§3.3)
- [ ] A2A server 启动后 `curl http://localhost:41241/.well-known/agent-card.json` 返回合法 JSON
- [ ] MCP server 启动后 `claude_desktop_config.json` 配置 stdio 能列出 6 个工具

### 8.3 Frontend 任务 (`agentteam/board/`) 验收

- [ ] `agentteam/board/server.py` ≤ 200 行
- [ ] `agentteam/board/handlers/` 至少 7 个文件 (teams/agents/tasks/messages/chat/metrics/static)
- [ ] `agentteam/board/sse/broadcaster.py` 实现 `SSEBroadcasterProtocol` (§4.3)
- [ ] 所有 handler 实现 `BoardHandler` 协议 (§4.2)
- [ ] 旧 `board/server.py` 的 50+ 端点全部保留, 行为不变
- [ ] 单测 `tests/test_board_*.py` 全过

### 8.4 QA 任务 (`agentteam/cli/commands/`) 验收

- [ ] `agentteam/cli/commands.py` ≤ 100 行 (仅 shim)
- [ ] `agentteam/cli/commands/` 至少 12 个 sub-app (team/agent/task/board/skill/plugin/config/init/a2a/mcp/metrics/doctor)
- [ ] 每个 sub-app 用 `SubAppProtocol` 模板 (§5.4)
- [ ] `agentteam --help` 输出与 v0.5.1 一致
- [ ] `agentteam team --help` 等子命令帮助正常
- [ ] 旧 import (`from agentteam.cli.commands import ...`) 仍能工作 (向后兼容)

### 8.5 QA2 任务 (`agentteam/observability/`) 验收

- [ ] `agentteam/observability/__init__.py` 导出 §6.2 全部符号
- [ ] `init_tracing()` 默认 stdout, 可切 OTLP
- [ ] `init_metrics()` 注册 §6.4 的 10 个预定义 metrics
- [ ] `EventBridge.install()` 后, 触发 `CoreEvents.AGENT_SPAWNED` 能看到 OTel span
- [ ] `agentteam/exceptions.py` 中 `AgentTeamError` 是所有异常基类
- [ ] `agentteam metrics serve --port 9090` 启动后能 `curl /metrics` 看到指标
- [ ] 现有测试全过 + 新增 20+ OTel 测试

### 8.6 跨模块集成验收

- [ ] 5 个模块的 PR 合并后, `pytest tests/ -v` 全过
- [ ] `mypy agentteam/` 零 error
- [ ] `agentteam a2a serve &` + `agentteam mcp serve &` + `agentteam board serve &` 可同时启动
- [ ] 端到端集成测试: 用 `python-a2a` 客户端发任务到 A2A server, AgentTeam 接收, spawn agent, 完成, 返回结果
- [ ] 端到端集成测试: 用 Claude Desktop 配 stdio MCP, 调 `agentteam_list_agents` 能看到当前 team

### 8.7 接口变更管理 (变更须走 architect)

任何对本契约的修改必须:
1. 在 PR 中明确标注 "INTERFACE_CONTRACTS.md 变更"
2. 提供 migration guide (旧 API → 新 API)
3. architect 评审通过后才合并
4. 同步更新 `IMPLEMENTATION_BLUEPRINT.md` §6 接口锁定部分

---

## 附录 A: 5 个 PR 的依赖图

```
backend (core/)  ─────┬──────────→ backend2 (protocol/)  ──→ qa (cli/ a2a.py, mcp.py)
                      │                                       ↘
                      └──────────→ frontend (board/)  ──────── qa2 (observability/)
                                                              ↗
backend (async)  ────────────────────────────────────────── qa2 (OTel spans)
```

**合并顺序建议** (按依赖拓扑):
1. backend (#1: `core/` 拆包)
2. backend (#2: `agent/` 充实 + `core/async_api.py`)
3. qa2 (`observability/` 提前, 不依赖 core.async, 只需要 core.callbacks)
4. backend2 (`protocol/`)
5. frontend (`board/`)
6. qa (`cli/commands/` 拆分, 最后做)
7. qa + qa2 联合 (`init` + `metrics` 命令)

---

## 附录 B: 关键文件引用清单 (Engineers 必读)

| 文件 | 角色 | 必读原因 |
|------|------|----------|
| `AgentTeam/docs/UPGRADE_PROPOSAL.md` | 全部 | 升级总览 |
| `AgentTeam/docs/INTERFACE_CONTRACTS.md` (本文件) | 全部 | 接口宪法 |
| `AgentTeam/docs/IMPLEMENTATION_BLUEPRINT.md` | 全部 | 实施蓝图 |
| `AgentTeam/ARCHITECTURE_REVIEW.md` | 全部 | 既有架构评分 |
| `AgentTeam/docs/SKILL_PLUGIN_AUDIT.md` | backend, backend2 | Skill/Plugin 现状 |
| `AgentTeam/agentteam/core.py` | backend, qa2 | 待拆分 |
| `AgentTeam/agentteam/cli/commands.py` | qa | 待拆分 |
| `AgentTeam/agentteam/board/server.py` | frontend | 待拆分 |
| `AgentTeam/agentteam/team/dag.py` | backend | DAG 扩展 |
| `AgentTeam/agentteam/transport/base.py` | backend2 | transport 升级 |
| `AgentTeam/agentteam/plugins/__init__.py` | backend2 | 去单例 |
| `AgentTeam/agentteam/exceptions.py` | qa2 | 统一异常 |
| `SpectrAI-ref/main/chunks/SamplingServer.ts` | backend2 | MCP sampling |
| `SpectrAI-ref/main/chunks/MCPGatewayChunk.ts` | backend2 | MCP gateway |
| `SpectrAI-ref/main/plugin/PluginManager.ts` | backend2 | PluginManager |
| `SpectrAI-ref/main/workflow/WorkflowGenerator.ts` | backend | DAG 步类型 |

---

**END OF INTERFACE_CONTRACTS.md v1.0**

*本文件由 architect 起草, 任何变更须走 §8.7 流程。*
*签字: architect (架构师) @ 2026-06-04*
