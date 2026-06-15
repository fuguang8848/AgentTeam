# AgentTeam 升级方案 (UPGRADE_PROPOSAL.md)

> **作者**: architect (架构师)
> **评审日期**: 2026-06-04
> **评审对象**: `C:\Users\31683\AgentTeam` v0.7.6 (代码) / v0.5.1 (pyproject)
> **目标**: 对标 MetaGPT / AutoGen / CrewAI / LangGraph / OpenHands / Claude Skills / A2A / MCP 等顶尖项目，输出一份可拆分给 5 名工程师并行的升级蓝图
> **核心目标**: 易用性 / 可移植性 / 强大性 / 易修改性 / 适配性 (适配不同 Agent 框架或系统)

---

## 📑 目录

1. [执行摘要](#1-执行摘要)
2. [现状评估报告](#2-现状评估报告)
3. [顶尖项目对标](#3-顶尖项目对标)
4. [升级方案总览](#4-升级方案总览)
5. [具体改造清单（按模块）](#5-具体改造清单按模块)
6. [按角色拆分 (5 人并行)](#6-按角色拆分-5-人并行)
7. [优先级与 ROI 评估](#7-优先级与-roi-评估)
8. [验收标准与里程碑](#8-验收标准与里程碑)
9. [附录: 引用与链接](#9-附录引用与链接)

---

## 1. 执行摘要

AgentTeam 是一个**生产级多 Agent 协调 CLI**，在 v0.7.6 已经形成 171 个 Python 源文件 / 87 个测试文件 / 4 万行代码的稳定基座：6 种 spawn backend (tmux/subprocess/openclaw_sdk/openclaw_api/terminal_buffer/auto)、3 种 transport (file/p2p/redis)、完整的生命周期/角色/事件/告警/审计/可观测性体系。

**但与 MetaGPT、AutoGen、CrewAI、LangGraph、OpenHands、Claude Skills 相比，存在 3 大结构性差距**：

| 差距 | 现状 | 顶尖项目基准 | 影响 |
|------|------|--------------|------|
| **协议化** | 内部闭源协议（CTTeam/CTAgent） | A2A / MCP / OpenAI Agents SDK 等开放标准 | 难嵌入其他 Agent 框架 |
| **SDK 化** | CLI-first，无独立 Python SDK 入口 | Pydantic-AI / Smolagents 单一 `import` 即可用 | 难被集成 / 重用 |
| **运行时化** | 仅 spawn 外部 CLI (claude/codex/openclaw) | LangGraph Runtime / Agno AgentOS / OpenHands Server | 无真正"自我托管" 能力 |

**核心判断**：AgentTeam 的"协调层 + 持久化 + 可观测性"是行业内最完整之一，但**适配性（可被其他 Agent 框架集成）**和**运行时（可被嵌入式调用）**是最大短板。本次升级的核心，是把"工具型 CLI"演进为"协议型 Runtime + 嵌入式 SDK"。

**5 维度现状评分（10 分制）**：

- 易用性 **6.5** — pip 一键安装 + 10 语言文档 + Dashboard，但 onboarding 仍偏开发者
- 可移植性 **7.0** — Win/macOS/Linux 完整 CI，tmux 在 Windows 缺失
- 强大性 **7.5** — 595+ 测试 / 6 backend / 3 transport / 完整可观测性
- 易修改性 **5.0** — `cli/commands.py` 5894 行 / `board/server.py` 3104 行，是两个巨型单体
- 适配性 **3.5** — 无 A2A / MCP / SDK 入口，难嵌入其他 Agent 框架

**升级后目标（v1.0）**：

- 易用性 9.0（`agentteam init` 5 分钟 onboarding）
- 可移植性 9.0（无 tmux 全平台 + PyPI + Docker + 单一二进制）
- 强大性 9.0（异步 runtime + 内置原生 agent loop + checkpoint）
- 易修改性 8.0（按 feature 拆分模块，core < 500 行）
- 适配性 8.5（A2A Server / MCP Server / Python SDK / CLI 4 入口共存）

---

## 2. 现状评估报告

### 2.1 项目速览

| 维度 | 数值 | 证据 |
|------|------|------|
| **总文件数** | 263 个 `.py` (其中 `agentteam/` 下 171 个) | `find . -name "*.py" | wc -l` |
| **测试文件** | 87 个 | `tests/test_*.py` |
| **测试通过率** | 675 passed / 14 skipped | `CAPABILITIES.md` |
| **子模块** | 40+ (`agentteam/` 一级) | `ls agentteam/` |
| **pyproject 版本** | 0.5.1 / `__init__.py` 0.7.6 | 双版本不一致 ⚠️ |
| **依赖** | 6 个核心 (typer/pydantic/rich/psutil/pyyaml/tomli) | `pyproject.toml` |
| **Python 版本** | ≥3.10 | `pyproject.toml` |
| **License** | MIT | `LICENSE` |
| **平台** | Win/macOS/Linux | `PLATFORM_COMPATIBILITY.md` |
| **文档语言** | 10 种（zh/en/ja/ko/fr/de/it/ru/pt-br/tw） | `README*.md` |
| **核心 SDK** | `CTTeam/CTAgent/CTTask/CTMessage` | `agentteam/core.py` |
| **Transport 实现** | file / p2p(zmq) / redis | `agentteam/transport/` |
| **Spawn Backend** | tmux / subprocess / openclaw_sdk / openclaw_api / terminal_buffer | `agentteam/spawn/` |
| **数据库** | SQLite (events + agent data) | `agentteam/database/` |
| **记忆系统** | L1-L4 分层 + FTS5 全文检索 | `agentteam/memory/layered.py` |
| **插件系统** | Hook-based + PluginManager 单例 | `agentteam/plugins/__init__.py` |
| **技能系统** | `SKILL.md` 解析 + Auto-Creator | `agentteam/skills/auto_creator.py` |
| **Hermes 集成** | 5 Phase: learnings / skills / user-profile / memory / insights | `agentteam/hermes/` |
| **Web UI** | stdlib http.server + vanilla JS (7 个 .js) | `agentteam/board/` |
| **REST API** | 自带 + `APIVersion` 抽象 | `agentteam/api/` |
| **CLI 命令数** | 80+ (50 个 sub-app/command) | `cli/commands.py` 索引 |
| **最大单体文件** | `cli/commands.py` 5894 行 / `board/server.py` 3104 行 | `wc -l` |

### 2.2 5 维度评分（1-10 分）

#### 2.2.1 易用性 (Usability): **6.5 / 10**

**优势**：

- ✅ `pip install -e .` 一键安装；`agentteam board serve` 一键启动 Dashboard
- ✅ 10 种语言 README（含 zh-CN/TW/JA/KO/FR/DE/IT/RU/PT-BR）
- ✅ Rich CLI 表格 + JSON 双输出模式
- ✅ `make dev / make prod / make test` 一键 Makefile
- ✅ `agentteam config init` 配置向导
- ✅ shell-completion.bash / .zsh / .fish

**不足**：

- ❌ 缺 onboarding 引导（首次 `pip install` 后无 `agentteam init` 完整工作流）
- ❌ CLI 5800+ 行，新人难以发现命令
- ❌ 错误信息对最终用户不友好（典型如 `RuntimeError: f"Entity {id} not found"`，见 ARCHITECTURE_REVIEW.md 末尾建议）
- ❌ Web Board 仍是 vanilla JS（无 React/Vue 框架，无类型提示）

**关键证据**：

- `agentteam/cli/commands.py:5894` — 单文件 5894 行
- `agentteam/board/server.py:3104` — 单文件 3104 行
- `agentteam/exceptions.py` 已存在但未被一致使用（ARCHITECTURE_REVIEW 指出"应统一使用自定义异常类"）

#### 2.2.2 可移植性 (Portability): **7.0 / 10**

**优势**：

- ✅ GitHub Actions Linux CI (Python 3.10/3.11/3.12) + 本地 Windows 全跑通
- ✅ 跨平台 spawn backend: tmux (Linux/macOS) / openclaw_sdk (Windows 推荐)
- ✅ 跨平台 transport: file (零依赖) / p2p (zmq 可选) / redis (可选)
- ✅ Git worktree 跨平台修复（commit 57c14ab / 14d1d74）
- ✅ PATH 检查 / 环境变量过滤 (`spawn/command_validation.py`)

**不足**：

- ❌ tmux backend 在 Windows 直接不可用（"中等严重度"）
- ❌ Git worktree "偶发路径问题"（PLATFORM_COMPATIBILITY.md 自述）
- ❌ 未发布 PyPI（pyproject 仅本地开发）
- ❌ 无 standalone binary（PyInstaller/Nuitka）
- ❌ Shell 补全在 Windows "有限支持"

**关键证据**：

- `PLATFORM_COMPATIBILITY.md` 第 90-110 行：明确列出 Windows 已知问题
- `pyproject.toml` 无 `[tool.hatch.build.targets.wheel.bundled]` 或发布配置

#### 2.2.3 强大性 (Power): **7.5 / 10**

**优势**：

- ✅ 6 种 spawn backend + 3 种 transport，覆盖本地/分布式
- ✅ DAG 依赖管理 (`team/dag.py`) + Topological Sort
- ✅ 三因素智能路由（历史表现 + 负载感知 + 技能匹配）
- ✅ 任务复杂度分析 (TRIVIAL/LOW/MEDIUM/HIGH/EXPERT) + Model tier 自动选型
- ✅ Circuit Breaker 模式（`AgentHealth` 熔断器）
- ✅ 告警 4 级（LOW/MEDIUM/HIGH/CRITICAL）+ 告警类型（TASK_TIMEOUT/AGENT_FAILURE_RATE_HIGH/TEAM_INACTIVITY）
- ✅ EventTracker 40+ 事件类型 + SQLite 持久化
- ✅ Hermes 5 Phase（learnings / skills / user-profile / memory / insights）
- ✅ 漂移检测 (Jaccard + 语义相似度双校验)
- ✅ Daemon 模式 + 持久化 agent + socket API
- ✅ 595+ 测试用例 / 49 个测试文件 / 18070 行测试代码

**不足**：

- ❌ 核心循环仍是同步阻塞（`time.sleep(10)` 在 `CTTeam.wait_all`）
- ❌ 无 async/await 支持
- ❌ 无 checkpoint / resume 长任务（最长 1 小时超时 `wait_all(timeout: int = 3600)`）
- ❌ 无分布式锁（仅文件锁 `fcntl.flock` / `msvcrt.LOCK_EX`）
- ❌ 无 OpenTelemetry 集成
- ❌ 无 Prometheus exporter
- ❌ 模型路由只支持自家 provider（`orchestrator/provider_selector.py` 内部枚举），未走 LiteLLM 适配器

**关键证据**：

- `agentteam/core.py` `CTTeam.wait_all`: `while time.time() - start < timeout: ... time.sleep(10)` 同步
- `agentteam/transport/file.py`: 仅本地文件锁，缺分布式协调
- `agentteam/orchestrator/__init__.py`: 仅导出 `ProviderSelector/ProviderInfo/...`，未抽象 LLM 协议

#### 2.2.4 易修改性 (Modifiability): **5.0 / 10** ⚠️ 最大短板

**优势**：

- ✅ 模块边界清晰（ARCHITECTURE_REVIEW.md 评分 9/10 模块化）
- ✅ Repository 模式（`database/repositories/base.py`）抽象良好
- ✅ 6 种 spawn backend 可插拔
- ✅ 3 种 transport 可插拔
- ✅ 已有 Hook-based plugin 系统
- ✅ Pydantic 强类型模型
- ✅ ruff 格式 + pyright 类型检查 + pytest 测试

**不足**：

- ❌ **`cli/commands.py` 5894 行单体** — 50+ 命令/子应用混在一文件
- ❌ **`board/server.py` 3104 行单体** — HTTP handler / SSE / 静态服务 / WebSocket / 鉴权混在一起
- ❌ **`agent/` 模块实际是空的** — `agentteam/agent/__init__.py` 只导出一个 `HeadlessTerminalBuffer`，所有 Agent 实际类在 `core.py`（命名错位）
- ❌ **PluginManager 单例** — `__new__` 实现，难 mock / 难多实例
- ❌ **4 个并行的 manager**（TeamManager / LifecycleManager / MailboxManager / PlanManager）— 状态分散
- ❌ 大量 `print()` 调试（`board/server.py` 多处 `print("Failed to...")`）混入业务逻辑
- ❌ 缺乏依赖注入容器（全部用 `get_X()` 全局函数）
- ❌ `agentteam/spawn/registry.py:AgentHealth.state` 状态机硬编码 `healthy/degraded/open`

**关键证据**：

- `agentteam/cli/commands.py` wc -l: **5894**
- `agentteam/board/server.py` wc -l: **3104**
- `agentteam/agent/__init__.py` 仅 2 行（`from ...buffer import HeadlessTerminalBuffer`）
- `agentteam/plugins/__init__.py` 显式 `__new__` 单例

#### 2.2.5 适配性 (Adaptability): **3.5 / 10** ⚠️ 第二大短板

**优势**：

- ✅ 6 种 Agent CLI 适配（OpenClaw / Claude Code / Codex / nanobot / Cursor / 自定义）
- ✅ 3 种 transport 适配
- ✅ `OpenClawGatewayURL` 等环境变量多前缀兼容 (`AGENTTEAM_/OPENCLAW_/CLAUDE_CODE_`)
- ✅ Plugin hook 系统

**不足**：

- ❌ **无 A2A (Agent-to-Agent) 协议** — AgentTeam 自身不能作为 A2A Server
- ❌ **无 MCP (Model Context Protocol) Server** — 不能把 AgentTeam 工具暴露给 Claude/Cursor/Cline
- ❌ **无 Python SDK 入口** — `from agentteam import Team` 看似可用，但实际是 CLI wrapper，缺 async API / 上下文管理
- ❌ **无 REST OpenAPI 规范** — 没有 `openapi.json`，外部系统难自动对接
- ❌ **无 CLI `serve` 模式作为 daemon API** — 仅有 GUI dashboard，无 headless API server
- ❌ **无 OpenAI Agents SDK / LangGraph 适配器** — 不能"让 LangGraph 调用 AgentTeam agent"
- ❌ **数据模型是自创 CTTeam/CTAgent** — 不是 Agent Protocol 兼容
- ❌ **依赖外部 CLI 进程** — 没有"自托管 LLM 循环"，全靠 spawn 子进程

**关键证据**：

- 全文搜索 `a2a` / `mcp` / `model context protocol` 在 `agentteam/` 下零匹配
- `agentteam/__init__.py` 导出 `Team/Agent/Task/Message`，但都是 dataclass 包装，无运行时方法
- `agentteam/transport/base.py`: 抽象基于 bytes 透传，没有"消息 schema"标准化

### 2.3 TOP 10 痛点（按严重度排序）

| # | 痛点 | 证据 | 影响 |
|---|------|------|------|
| **1** | **缺 A2A + MCP 协议适配** | 全文无 `a2a`/`mcp` 引用 | 不能被 LangGraph / Claude / Cursor / Cline 直接调用 |
| **2** | **CLI 单体 5894 行** | `agentteam/cli/commands.py` | 新人 1 周才能理解命令全貌；改 1 行风险高 |
| **3** | **Board Server 单体 3104 行** | `agentteam/board/server.py` | 测试覆盖低；改 SSE 容易破坏静态资源服务 |
| **4** | **无 Python SDK Runtime** | `__init__.py` 导出 dataclass，无 `await team.run(task)` | Python 应用方无法 import 即用 |
| **5** | **agent/ 模块空壳** | `agentteam/agent/__init__.py` 仅 2 行 | 命名错位；概念"Agent"分散在 core.py / spawn / orchestrator 4 处 |
| **6** | **同步阻塞核心循环** | `core.py:CTTeam.wait_all: time.sleep(10)` | 无法高并发；FastAPI 集成阻塞 event loop |
| **7** | **无 OpenTelemetry / 标准化 metrics** | `metrics/` 模块存在但仅本地累计 | 无法接 Prometheus / Jaeger / Datadog |
| **8** | **PluginManager 单例** | `plugins/__init__.py:__new__` 强制单例 | 多团队实例并存 / 测试隔离困难 |
| **9** | **4 个 manager 状态分散** | TeamManager / LifecycleManager / MailboxManager / PlanManager | 状态同步需手工处理；事务边界不清晰 |
| **10** | **依赖外部 CLI 进程** | spawn backends 全部启动子进程 | 启动延迟高（>2s/agent）；无法 in-process 复用 LLM session |

**其他次要痛点（也已识别）**：

- pyproject 版本 (0.5.1) 与 `__init__.py` (0.7.6) 不一致
- 大量 `print()` 混入业务代码（特别是 board/server.py）
- 缺乏 `pyproject.toml` `[project.optional-dependencies.ui]` 区分 Web/Headless 安装
- README 提及 P0-P33 测试（"P0-P25 verified"）但实际架构文档只到 P38
- 缺乏 release notes 自动化生成
- `docs/UPGRADE.md` 与 `docs/UPGRADE_PROPOSAL.md` 命名易混

---
## 3. 顶尖项目对标

### 3.1 对标矩阵（11 项目 × 12 维度）

> **评级**：✅ 完整 | 🟡 部分 | ❌ 缺失

| 项目 | 协议标准 | 异步Runtime | 嵌入式 SDK | 技能系统 | 插件系统 | 团队协作 | 多 LLM | 可观测性 | 跨平台 | 文档质量 | 持久化 | 容错/重试 |
|------|---------|------------|------------|----------|----------|----------|--------|----------|--------|----------|--------|----------|
| **AgentTeam (当前)** | ❌ 自创 | ❌ 同步 | 🟡 导出 dataclass | ✅ SKILL.md | ✅ Hook | ✅ 角色+mailbox | 🟡 自家枚举 | 🟡 EventTracker | ✅ Win/Mac/Linux | ✅ 10 语言 | ✅ SQLite | 🟡 熔断+重试 |
| **MetaGPT** | ❌ 自创 SOP | ✅ async | ✅ `from metagpt import Team` | ❌ 无 | 🟡 Action 子类 | ✅ SOP 流程 | ✅ LiteLLM | 🟡 内置 log | ✅ 全平台 | ✅ | 🟡 文件 | 🟡 基础 |
| **AutoGen v0.4+** | ❌ RoutedAgent | ✅ async | ✅ `from autogen_agentchat import Team` | ❌ 无 | ✅ Component | ✅ GroupChat | ✅ ModelClient 抽象 | ✅ OpenTelemetry | ✅ | ✅ | 🟡 DB 抽象 | ✅ |
| **CrewAI** | ❌ 自创 | ✅ async | ✅ `from crewai import Crew` | ❌ 无 | ✅ Tools 体系 | ✅ Process=sequential/hierarchical | ✅ 多 LLM | ✅ OpenTelemetry | ✅ | ✅ 文档站 | ✅ 多种 DB | 🟡 |
| **LangGraph** | ❌ 自创图 | ✅ async | ✅ `from langgraph.graph import StateGraph` | ❌ 无 | ✅ Node/Send | ✅ Send/Command 委派 | ✅ 多 LLM | ✅ LangSmith | ✅ | ✅ 顶级 | ✅ Checkpointer | ✅ durable execution |
| **OpenHands SDK** | ✅ REST API | ✅ async | ✅ SDK + Server | ❌ 无 | ✅ Tools | ✅ Conversation | ✅ 多 LLM | ✅ WebSocket event | ✅ | ✅ | ✅ conversation 持久化 | ✅ retry |
| **Pydantic-AI** | ❌ 自创 | ✅ async | ✅ FastAPI-like | ❌ 无 | 🟡 Tool | 🟡 delegation | ✅ Model 抽象 | ✅ Logfire | ✅ | ✅ 顶级 | 🟡 | ✅ Pydantic Validation |
| **Smolagents** | ❌ 自创 | ✅ | ✅ | ❌ 无 | 🟡 Tool | ❌ | ✅ 多 LLM | 🟡 | ✅ | ✅ | ❌ | 🟡 |
| **Agno (AgentOS)** | ❌ 自创 | ✅ | ✅ + AgentOS 控制面 | ❌ 无 | ✅ Tools | ✅ Team/Workflow | ✅ 多 LLM | ✅ 50+ 端点 | ✅ | ✅ | ✅ Postgres/Sqlite | 🟡 |
| **OpenAI Agents SDK** | ✅ OpenAI 标准 | ✅ | ✅ `from agents import Agent` | ❌ 无 | 🟡 Tool | ✅ handoffs | ❌ 仅 OpenAI | ✅ Tracing | ✅ | ✅ | ✅ Sessions | ✅ Guardrails |
| **Claude Skills** | ✅ SKILL.md | n/a | n/a (数据) | ✅ 核心 | n/a | n/a | n/a | n/a | ✅ | ✅ Anthropic 官方 | n/a | n/a |
| **A2A Protocol** | ✅ 开放标准 | n/a | ✅ SDK | n/a | n/a | n/a | n/a | n/a | n/a | ✅ Google/LF | n/a | n/a |
| **MCP Protocol** | ✅ 开放标准 | n/a | ✅ SDK | n/a | n/a | n/a | n/a | n/a | n/a | ✅ 官方 | n/a | n/a |
| **Aider** | ❌ CLI 单体 | ❌ | ❌ (CLI only) | ❌ 无 | ❌ | ❌ | 🟡 多 | ❌ | ✅ | 🟡 | ❌ | 🟡 |
| **Goose (Block)** | ✅ MCP | n/a | 🟡 | ❌ 无 | ✅ MCP Extensions | 🟡 | ✅ 15+ providers | 🟡 | ✅ Mac/Win | 🟡 | ✅ Recipe | 🟡 |

### 3.2 各项目核心亮点拆解

#### 3.2.1 MetaGPT — `foundationagents/metagpt`
**核心架构**：

- **SOP (Standard Operating Procedure)** — `Code = SOP(Team)`：把软件公司流程编码为可执行图
- **Action 子类 + Watch 机制** — Action 自带 watch 的 MessageType，自动响应（事件驱动）
- **Team / Role / Profile** — 角色 + 配置文件 (`Profile`)，描述目标/约束/性格
- **Message Schema** — `send_to` 路由 + `cause_by` 触发追踪 + `instruct_content` 结构化负载

**可借鉴**：

- **Action Watch 自动注册** — AgentTeam 的 Hook 系统可以升级为"基于事件类型的 Action 路由"
- **Pydantic 结构化消息** — `Message.instruct_content: BaseModel` 是 AgentTeam 当前 JSON 字典的标准化方向

**链接**：

- https://github.com/foundationagents/metagpt

#### 3.2.2 AutoGen v0.4+ — `microsoft/autogen`
**核心架构**：

- **RoutedAgent + 消息订阅** — 用 `TypeSubscription` 替代硬编码路由（对比 AgentTeam 当前的 `from_agent/to_agent`）
- **GroupChat + Manager** — LLM 动态选下一位 speaker，避免循环
- **Component 抽象** — 所有可配置单元（Model Client / Agent / Tool）都是可序列化 Component
- **OpenTelemetry 原生集成**

**可借鉴**：

- **Component 序列化** — AgentTeam 的 `TeamConfig`（Pydantic BaseModel）已经走对路，应进一步统一所有 manager 配置
- **TypeSubscription 模式** — 替代 AgentTeam 当前硬编码的 `mailbox.send_to_agent(name)`

**链接**：

- https://github.com/microsoft/autogen

#### 3.2.3 CrewAI — `crewaiinc/crewai`
**核心架构**：

- **Agent(allow_delegation=True)** — Agent 可动态把任务委托给队友
- **Process.sequential / Process.hierarchical** — 流程引擎，hierarchical 自动产生 Manager Agent
- **Memory 五件套** — short-term / long-term / entity / contextual / user-memory
- **Tools 体系** — 200+ 内置 tool (Serper, Firecrawl, ...)

**可借鉴**：

- **`allow_delegation`** 设计极简；AgentTeam 当前的"角色权限隔离"可以更精细
- **Memory 五件套分层** — AgentTeam 已有 L1-L4，应该公开 `MemoryType` 枚举

**链接**：

- https://github.com/crewaiinc/crewai
- https://docs.crewai.com

#### 3.2.4 LangGraph — `langchain-ai/langgraph`
**核心架构**：

- **StateGraph + Reducer** — `Annotated[list[int], operator.add]` 用类型注解自动决定状态合并策略
- **Send + Command** — 动态并行执行（Map-Reduce / Supervisor 委派）
- **Durable Execution** — 长时间 agent 可"从上次中断点恢复"
- **Checkpoint** — 内置 Sqlite/Postgres/Redis 三种 checkpointer
- **Human-in-the-loop interrupt** — `interrupt()` 内置暂停

**可借鉴（最关键）**：

- **Send 模式** — AgentTeam 当前需要手工维护 DAG 依赖（`team/dag.py`），可引入 `Send("agent_node", state)` 实现 map-reduce
- **Reducer 思路** — AgentTeam 当前的 `team/models.py:TaskItem` 状态合并是命令式，可改为声明式
- **Checkpoint** — 解决 AgentTeam 当前的"无 resume 长任务"痛点

**链接**：

- https://github.com/langchain-ai/langgraph
- https://langchain-ai.github.io/langgraph/

#### 3.2.5 OpenHands Software Agent SDK — `openhands/software-agent-sdk`
**核心架构**：

- **Agent Server (FastAPI + WebSocket)** — 标准化 REST + WS 双接口（对比 AgentTeam 当前 stdlib http.server）
- **Conversation 抽象** — 每次 run 是有状态 Conversation，可恢复
- **Webhooks** — 事件外推到外部 HTTP endpoint
- **配置 JSON** — `{"session_api_key": ..., "webhooks": [...]}`

**可借鉴**：

- **Webhooks** — AgentTeam 当前 Board SSE 是单进程内推，应该有 webhook 外推
- **配置 JSON Server** — AgentTeam 当前缺统一 server config schema

**链接**：

- https://github.com/openhands/software-agent-sdk

#### 3.2.6 Claude Skills — `anthropics/skills`
**核心架构**：

- **SKILL.md 三级加载** — frontmatter (name/description) → SKILL.md body → bundled resources (scripts/references/assets)
- **YAML frontmatter** — `name` + `description` 是必填项（description 应"pushy"以提高 LLM 调用率）
- **目录化** — `skill-name/SKILL.md` + 可选 `scripts/` `references/` `assets/`
- **description 触发** — LLM 根据 description 自动判断何时调用

**AgentTeam 现状对比**：

- AgentTeam 已有 `SKILL.md` 系统（`agentteam/skills/auto_creator.py` + `agentteam/skill/engine.py`）
- 但 frontmatter 字段不一致（见 `engine.py` 内置 `BUILTIN_SKILLS`），且没有 `scripts/references/assets` 三级目录约定
- **升级方向**：完全对齐 `anthropics/skills` 的 SKILL.md 规范，做到技能可双向共享

**链接**：

- https://github.com/anthropics/skills
- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview

#### 3.2.7 A2A Protocol — `a2aproject/a2a-python`
**核心架构**：

- **Agent Card** — `/.well-known/agent-card.json` 自描述（name/description/skills/capabilities/security_schemes）
- **JSON-RPC 2.0** — 标准 RPC 协议
- **多传输** — JSON-RPC / HTTP+JSON / gRPC
- **Streaming** — `message/stream` SSE
- **Push Notifications** — webhook 推送任务状态
- **Security** — OpenID Connect / API Key / OAuth2

**AgentTeam 应实现**：

- `/.well-known/agent-card.json` — 暴露所有 role (developer/reviewer/architect/...) 为 A2A skills
- `POST /a2a/v1/message/send` — 接收外部 Agent 任务
- 复用现有 `MailboxManager` 作为内部总线

**链接**：

- https://a2a-protocol.org
- https://github.com/a2aproject/a2a-python

#### 3.2.8 MCP (Model Context Protocol) — `modelcontextprotocol/python-sdk`
**核心架构**：

- **3 个原语**: Resources / Prompts / Tools
- **2 种传输**: stdio (本地进程) / Streamable HTTP (远程)
- **JSON-RPC 2.0** + `Mcp-Session-Id` / `Mcp-Method` / `Mcp-Name` headers
- **Server / Client 角色**

**AgentTeam 应实现**：

- 把 `agentteam/tools/registry.py` 的工具（10+ 个内置工具）暴露为 MCP Server
- 这样 Claude Code / Cursor / Cline / Goose 都能直接调用 AgentTeam 的能力
- 通过 stdio 启动 `agentteam mcp serve`，作为 Claude Desktop 的 tool provider

**链接**：

- https://modelcontextprotocol.io
- https://github.com/modelcontextprotocol/python-sdk

#### 3.2.9 Pydantic-AI — `pydantic/pydantic-ai`
**核心架构**：

- **FastAPI-like DX** — `Agent('openai:gpt-5.2', deps_type=MyDeps, output_type=MyOutput)`
- **依赖注入 (deps)** — `@agent.tool` 拿 `ctx: RunContext[MyDeps]`
- **结构化输出 (output_type)** — 强类型
- **内建 TestModel / FunctionModel** — 单元测试无需 mock LLM

**可借鉴**：

- **`deps_type` 模式** — AgentTeam 当前的 `metadata: dict` 应该升级为强类型 `Context`
- **TestModel** — AgentTeam 当前测试大多 mock subprocess，可以做 in-process LLM mock

**链接**：

- https://github.com/pydantic/pydantic-ai
- https://ai.pydantic.dev

#### 3.2.10 Smolagents — `huggingface/smolagents`
**核心架构**：

- **CodeAgent / ToolCallingAgent** — 两种工具调用范式
- **MultiStepAgent 循环** — `while llm_should_continue(memory): ...`
- **极简** — 几百行核心

**可借鉴**：

- **极简的 agent loop** — AgentTeam 的 `orchestrator/supervisor.py` 可以参考这个简洁度

**链接**：

- https://github.com/huggingface/smolagents

#### 3.2.11 Agno + AgentOS — `agno-agi/agno`
**核心架构**：

- **Agent + Team + Workflow** 三层抽象
- **Workflow as Tool** — 把 workflow 包装成 tool，可被其他 agent 调用
- **AgentOS 控制面** — 50+ 生产就绪 API 端点 + SSE 流
- **Postgres/Sqlite 多 DB 抽象**

**可借鉴**：

- **Workflow as Tool 模式** — AgentTeam 当前的 `PlanManager` 是 process 模式，可升级
- **AgentOS 概念** — 借鉴其"控制面 vs 数据面"分层

**链接**：

- https://github.com/agno-agi/agno
- https://docs.agno.com

#### 3.2.12 OpenAI Agents SDK — `openai/openai-agents-python`
**核心架构**：

- **Handoffs** — Agent 间可声明 transfer
- **Guardrails** — input/output 验证
- **Sessions** — 内建会话持久化
- **Tracing** — 可视化执行轨迹
- **Voice Pipeline** — 多模态支持

**可借鉴**：

- **Handoffs** — AgentTeam 当前的 `terminate-tree` 是强制级联，"主动转移"是补充
- **Guardrails** — AgentTeam 已有 `security/__init__.py`，可对齐 Guardrail 模式

**链接**：

- https://github.com/openai/openai-agents-python

#### 3.2.13 Goose (Block) — `block/goose`
**核心架构**：

- **MCP Extensions 体系** — 70+ 内置 extension，全是 MCP server
- **Recipe (YAML)** — 可复用的 prompt + extension 组合
- **多 Provider** — 15+ LLM provider

**可借鉴**：

- **Recipe 概念** — AgentTeam 当前的 `templates/` 模块可以升级为 Recipe

**链接**：

- https://github.com/block/goose
- https://block.github.io/goose

---
## 4. 升级方案总览

### 4.1 阶段划分

| 阶段 | 时间 | 主题 | 预期产出 | 可并行 |
|------|------|------|----------|--------|
| **P0 紧急 (1-2 周)** | 5d | 拆分 monolith + 异步 runtime 骨架 | cli/commands.py < 2000 行；board/server.py < 1500 行 | ✅ 4 人 |
| **P0 协议 (3-4 周)** | 14d | A2A Server + MCP Server + Python SDK | `agentteam a2a serve` / `agentteam mcp serve` / `from agentteam import Team, run` | ✅ 3 人 |
| **P1 强化 (5-8 周)** | 21d | checkpoint / OpenTelemetry / 异步事件总线 / Plugin 多实例 | 端到端 async + 分布式追踪 + 熔断 | ✅ 5 人 |
| **P2 进化 (9-12 周)** | 21d | 内建 LLM runtime / Web UI 现代化 / 发布到 PyPI | 单二进制 + React/Vite Web UI + pip install | 🟡 3 人 |

### 4.2 5 大架构目标

#### 目标 1: **协议优先** — 把 AgentTeam 变成 A2A / MCP 双面手

```
                ┌─────────────────────┐
                │   AgentTeam Core    │
                │  (Runtime + State)  │
                └──────────┬──────────┘
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
       ▼                   ▼                   ▼
   A2A Server         MCP Server          CLI / Python SDK
   (对外接收任务)     (对外暴露工具)       (人/脚本调用)
```

- A2A Server: 接收 LangGraph/AutoGen/CrewAI agent 的任务
- MCP Server: 把 AgentTeam 工具暴露给 Claude/Cursor/Cline
- CLI / Python SDK: 人类和 Python 脚本入口

#### 目标 2: **运行时化** — 拆 cli/commands.py 5894 行

```
agentteam/cli/
├── app.py                  # typer root app (50 行)
├── commands/
│   ├── team.py            # team.* 命令 (~300 行)
│   ├── agent.py           # agent.* 命令 (~300 行)
│   ├── task.py            # task.* 命令 (~200 行)
│   ├── inbox.py           # inbox.* 命令 (~200 行)
│   ├── spawn.py           # spawn 命令 (~200 行)
│   ├── board.py           # board.* 命令 (~200 行)
│   ├── session.py         # session.* 命令 (~150 行)
│   ├── config.py          # config.* 命令 (~150 行)
│   ├── plan.py            # plan.* 命令 (~150 行)
│   ├── cost.py            # cost.* 命令 (~150 行)
│   ├── lifecycle.py       # lifecycle.* 命令 (~150 行)
│   ├── skill.py           # skill.* 命令 (~150 行)
│   ├── alert.py           # alert.* 命令 (~150 行)
│   └── _shared.py         # 共享工具 (~100 行)
```

#### 目标 3: **异步化** — 核心循环 async/await

- `core.py:CTTeam.wait_all` 从 `time.sleep(10)` → `asyncio.sleep + Event`
- `transport/file.py` → `aiofiles`
- `events/tracker.py` → `asyncio.Queue + aiosqlite`

#### 目标 4: **可观测性标准化** — OpenTelemetry 原生

- `tracer/meter/logger` 三件套
- 默认导出 OTLP，可接 Jaeger / Tempo / Honeycomb
- Langfuse / Phoenix 兼容

#### 目标 5: **易修改性 5→8** — 模块边界 + DI 容器

- 引入 `dependency-injector` 或自制 `Container`
- `agent/` 模块从 1 个文件 → 完整 Agent 抽象
- PluginManager 去单例
- 4 个 manager 合并为统一 `TeamStateMachine`

---

## 5. 具体改造清单（按模块）

> 每条改造都标注：难度 (L/M/H) / 工期 (人天) / 依赖 / 验收

### 5.1 核心层: core.py + agent/ 重构

#### 5.1.1 把 `core.py` 拆为 `core/` 目录

- **现状**：`agentteam/core.py` (350+ 行) 包含 `AgentState/TaskState/CTAgent/CTTask/CTMessage/CTTeam`
- **目标**：

  ```
  agentteam/core/
  ├── __init__.py        # 重新导出
  ├── enums.py           # AgentState / TaskState
  ├── models.py          # CTAgent/CTTask/CTMessage (Pydantic)
  ├── team.py            # CTTeam (async)
  └── exceptions.py      # TeamNotFound / AgentAlreadyExists ...
  ```

- **难度**：L / **工期**：1 人天 / **依赖**：无 / **验收**：现有测试全过

#### 5.1.2 充实 `agent/` 模块（解决空壳问题）

- **现状**：`agentteam/agent/__init__.py` 仅 2 行
- **目标**：

  ```
  agentteam/agent/
  ├── __init__.py
  ├── base.py            # AbstractAgent (新)
  ├── loop.py            # AgentLoop (think-act-observe 循环)
  ├── router.py          # AgentRouter (replaces team/router.py)
  ├── context.py         # AgentContext (deps 注入)
  └── builtin/
      ├── coder.py       # 对应 "coder" agent_type
      ├── reviewer.py
      ├── architect.py
      └── ...
  ```

- **设计要点**：
  - `AbstractAgent.run_async(prompt, context) -> AgentResult`
  - 与 Pydantic-AI 的 `Agent` 签名对齐：`Agent('model', deps_type=Context)`
- **难度**：H / **工期**：3 人天 / **依赖**：5.1.1 / **验收**：新 `from agentteam.agent import Agent` 可用

#### 5.1.3 引入 async Runtime

- **现状**：`CTTeam.wait_all` 同步 `time.sleep(10)` 阻塞
- **目标**：

  ```python
  class CTTeam:
      async def wait_all(self, timeout: Optional[float] = None) -> dict:
          async def _wait():
              async with asyncio.timeout(timeout or 3600):
                  while not all(a.state in (COMPLETED, FAILED) for a in self.agents.values()):
                      await asyncio.sleep(0.5)
          await _wait()
          return self.get_status()
  ```

- **向后兼容**：保留同步 `wait_all` 包装
- **难度**：M / **工期**：2 人天 / **依赖**：5.1.1 / **验收**：新增 `tests/test_async_team.py` 全过

### 5.2 协议层: A2A + MCP 适配

#### 5.2.1 A2A Server 实现

- **新增模块**：`agentteam/protocol/a2a/`

  ```
  agentteam/protocol/a2a/
  ├── __init__.py
  ├── server.py          # AgentTeamA2AServer (FastAPI app)
  ├── agent_card.py      # 从 RoleStore 生成 AgentCard
  ├── executor.py        # 把 message/send 委派给 MailboxManager
  └── task_store.py      # A2A Task → Team task 映射
  ```

- **关键 API**：

  ```bash
  # CLI
  $ agentteam a2a serve --port 41241 --team dev-team
  # 暴露 http://localhost:41241/.well-known/agent-card.json
  ```

- **Agent Card 内容**：
  - name: "AgentTeam-{team_name}"
  - skills: 每个 role (developer/reviewer/architect/tester/coordinator) 一个 skill
  - capabilities: streaming=True, pushNotifications=True
- **难度**：M / **工期**：5 人天 / **依赖**：5.1.3 / **验收**：用 `python-a2a` 客户端跨进程调用成功

#### 5.2.2 MCP Server 实现

- **新增模块**：`agentteam/protocol/mcp/`

  ```
  agentteam/protocol/mcp/
  ├── __init__.py
  ├── server.py          # AgentTeamMCPServer (mcp.server.Server)
  ├── tools.py           # 包装 team/agent/inbox 操作为 MCP tools
  └── resources.py       # 把 ~/.agentteam/ 暴露为 MCP resources
  ```

- **暴露的 Tools（最少集）**：
  - `agentteam_list_agents(team) -> list[dict]`
  - `agentteam_get_status(team, agent) -> dict`
  - `agentteam_send_message(team, to, content) -> dict`
  - `agentteam_create_task(team, title, description) -> dict`
  - `agentteam_assign_task(team, task_id, agent) -> dict`
  - `agentteam_spawn_agent(team, name, role) -> dict`
- **难度**：M / **工期**：4 人天 / **依赖**：5.1.1 / **验收**：`claude desktop` 配 stdio 后能看到工具

#### 5.2.3 标准化 SKILL.md

- **现状**：`agentteam/skill/engine.py` 内置 BUILTIN_SKILLS 字段名与 Claude 不完全一致
- **目标**：完全对齐 `anthropics/skills` 规范
  - frontmatter: `name` (kebab-case) + `description` (必填) + 可选 `allowed-tools` `model` `version`
  - 目录结构：`skill-name/{SKILL.md, scripts/, references/, assets/}`
  - description 写"何时触发"（pushy style）
- **改造**：

  ```python
  # agentteam/skill/spec.py
  class SkillSpec(BaseModel):
      name: str = Field(pattern=r"^[a-z0-9-]+$")
      description: str = Field(min_length=10)
      allowed_tools: list[str] = []
      model: str | None = None
      version: str = "1.0.0"
      scripts: dict[str, str] = {}     # path -> description
      references: dict[str, str] = {}  # path -> description
      assets: dict[str, str] = {}      # path -> description
  ```

- **双向兼容**：保留旧字段，加 `legacy_compat=True` 警告
- **难度**：L / **工期**：2 人天 / **依赖**：无 / **验收**：现有 skills 全部通过新 schema 验证

### 5.3 传输层: 异步 + 多后端增强

#### 5.3.1 transport 抽象升级

- **现状**：`agentteam/transport/base.py` 抽象基于 `bytes`
- **目标**：升级为 `MessageEnvelope` schema

  ```python
  @dataclass
  class MessageEnvelope:
      message_id: str
      sender: str
      recipient: str
      timestamp_ms: int
      schema_version: int = 1
      payload_type: str  # "text" | "task_assignment" | "result" | "alert" | "image_url" | ...
      payload: bytes     # 仍为原始 bytes，schema 在上层定义
      correlation_id: str | None = None
      ttl_ms: int | None = None
  ```

- **新接口**：

  ```python
  class Transport(ABC):
      async def send(self, env: MessageEnvelope) -> None: ...
      async def receive(self, agent: str, limit: int = 10) -> list[MessageEnvelope]: ...
      async def peek(self, agent: str, limit: int = 10) -> list[MessageEnvelope]: ...
      async def count(self, agent: str) -> int: ...
  ```

- **难度**：M / **工期**：3 人天 / **依赖**：5.1.3 / **验收**：File/Redis/P2P 三个 backend 都实现新接口

#### 5.3.2 新增 NATS Transport（可选）

- **目的**：分布式跨机器，比 Redis 更轻量
- **后端**：`agentteam/transport/nats.py`
- **依赖**：`pip install nats-py`
- **难度**：L / **工期**：2 人天 / **依赖**：5.3.1

#### 5.3.3 新增 gRPC Transport（可选）

- **目的**：高吞吐、强 schema
- **proto**：`agentteam/transport/grpc/agentteam.proto`
- **难度**：H / **工期**：5 人天 / **依赖**：5.3.1

### 5.4 团队协作层: 技能 + 插件重构

#### 5.4.1 PluginManager 去单例

- **现状**：`__new__` 强制单例
- **目标**：支持多实例

  ```python
  class PluginManager:
      def __init__(self, plugin_dir: Path | None = None):
          self._plugins: dict[str, Plugin] = {}
          self._hooks = HookRegistry()
      @classmethod
      def default(cls) -> "PluginManager":
          # 全局单例仍保留，但通过 default() 访问
          ...
  ```

- **向后兼容**：保留 `PluginManager()` 直接构造返回单例的行为，加 deprecation warning
- **难度**：M / **工期**：2 人天 / **依赖**：无 / **验收**：新 `tests/test_plugin_manager_multi.py`

#### 5.4.2 Plugin Hook 标准化（对齐 OpenAI Agents SDK / LangGraph）

- **现状**：`HookRegistry` 已存在但 hook 名字不统一
- **目标**：统一 hook 命名 + 文档

  ```
  Pre-hooks: pre_agent_spawn, pre_task_assign, pre_message_send
  Post-hooks: post_agent_spawn, post_task_complete, post_message_receive
  Lifecycle: on_team_create, on_team_destroy, on_agent_failure
  Observability: trace_event, log_metric
  ```

- **文档化**：每个 hook 写明 `Args/Returns/Exceptions` 契约
- **难度**：L / **工期**：2 人天 / **依赖**：5.4.1

#### 5.4.3 Skill 双向共享协议

- **目标**：AgentTeam 的 skill 可导出到 Claude Skills 目录，反之亦然

  ```bash
  # CLI
  $ agentteam skill export code-review --to ./claude-skills/
  $ agentteam skill import ./claude-skills/pdf-processing/
  ```

- **实现**：基于 5.2.3 的统一 schema
- **难度**：L / **工期**：3 人天 / **依赖**：5.2.3

### 5.5 可观测性: 事件 + 追踪 + 指标

#### 5.5.1 OpenTelemetry 集成

- **新增模块**：`agentteam/observability/`

  ```
  agentteam/observability/
  ├── __init__.py
  ├── tracer.py         # OpenTelemetry Tracer 封装
  ├── meter.py          # Meter 封装
  ├── logger.py         # 结构化 logger (replaces logging_config.py)
  └── exporter.py       # OTLP/Prometheus/Console exporter
  ```

- **默认 Span**：
  - `agentteam.team.create`
  - `agentteam.agent.spawn`
  - `agentteam.task.execute`
  - `agentteam.message.send`
  - `agentteam.tool.invoke`
- **默认 Metric**：
  - `agentteam_agents_total{team, state}`
  - `agentteam_tasks_total{team, state}`
  - `agentteam_messages_total{team, direction}`
  - `agentteam_token_usage_total{team, model, type}`
- **难度**：M / **工期**：4 人天 / **依赖**：5.1.3 / **验收**：对接 Jaeger 看到 trace

#### 5.5.2 EventTracker 升级

- **现状**：SQLite + 40+ 事件类型
- **目标**：
  - 加 `tracing_correlation_id` 字段，关联 OTel trace
  - 改用 `aiosqlite` 异步
  - 提供 OTel Exporter，把 event 同步到 trace
- **难度**：M / **工期**：2 人天 / **依赖**：5.5.1

#### 5.5.3 指标统一导出

- **新增**：`agentteam metrics serve --port 9090`
- **协议**：Prometheus `/metrics` 端点
- **难度**：L / **工期**：1 人天 / **依赖**：5.5.1

### 5.6 接口层: 拆分 monolith CLI / Board

#### 5.6.1 拆分 `cli/commands.py` 5894 行

- **目标结构**：见 4.2 目标 2
- **执行步骤**：
  1. 新建 `agentteam/cli/commands/team.py` 等 13 个文件
  2. 每个文件用 `from .commands.team import app as team_app` 注册
  3. `agentteam/cli/app.py` 总入口 `app.add_typer(team_app, name="team")` 等
  4. 保留 `cli/commands.py` 仅作 shim 旧 import
- **新增 sub-app**：
  - `agentteam a2a serve` — 5.2.1
  - `agentteam mcp serve` — 5.2.2
  - `agentteam metrics serve` — 5.5.3
  - `agentteam init` — onboarding 引导
  - `agentteam skill export/import` — 5.4.3
- **难度**：M / **工期**：5 人天 / **依赖**：5.1.1 / **验收**：每个命令 1 文件 + 旧 CLI 行为完全一致

#### 5.6.2 拆分 `board/server.py` 3104 行

- **目标结构**：

  ```
  agentteam/board/
  ├── server.py          # 入口 (200 行)
  ├── handlers/
  │   ├── teams.py       # /api/teams/*
  │   ├── agents.py      # /api/agents/*
  │   ├── tasks.py       # /api/tasks/*
  │   ├── messages.py    # /api/messages/*
  │   ├── chat.py        # /api/chat
  │   ├── metrics.py     # /api/metrics/*
  │   └── static.py      # /static/*
  ├── sse/
  │   ├── broadcaster.py # SSE 抽象
  │   ├── event_stream.py
  │   ├── agent_stream.py
  │   └── chat_stream.py
  ├── websocket.py       # WebSocket 独立
  ├── auth.py            # 鉴权独立 (already exists)
  └── static/            # 现有文件保留
  ```

- **改用 FastAPI**（可选 P2）：从 `http.server` 升级为 FastAPI + uvicorn，获得自动 OpenAPI
- **难度**：M-H / **工期**：5-7 人天 / **依赖**：无 / **验收**：所有端点单测通过 + 行为不变

#### 5.6.3 引入 FastAPI（推荐 P2）

- 优势：自动 OpenAPI / Pydantic 验证 / 异步原生 / Swagger UI
- 兼容：保留 stdlib server 作 fallback
- **难度**：H / **工期**：7 人天 / **依赖**：5.6.2

### 5.7 易用性提升

#### 5.7.1 `agentteam init` 5 分钟引导

- **目标**：交互式 onboarding

  ```text
  $ agentteam init
  ? Project name: my-app
  ? Primary LLM provider: [OpenAI / Anthropic / OpenClaw / Ollama]
  ? Default team size: (3) workers
  ? Enable Dashboard? (Y/n)
  ? Install as A2A Server? (Y/n)
  ✓ Created .agentteam/config.yaml
  ✓ Spawned 3 agents in team 'my-app'
  ✓ Dashboard running on http://localhost:8080
  ```

- **难度**：L / **工期**：2 人天 / **依赖**：5.1.1

#### 5.7.2 错误信息友好化

- 统一 `agentteam.exceptions` 使用
- 加 `errors_suggestions` 字段（参考 Rust 编译器风格）
- **难度**：L / **工期**：1 人天 / **依赖**：无

### 5.8 可移植性提升

#### 5.8.1 发布到 PyPI

- 配 `[tool.hatch.build.targets.wheel]` + `[project.urls]`
- 加 GitHub Actions release workflow
- **难度**：L / **工期**：1 人天 / **依赖**：5.1.1

#### 5.8.2 单二进制分发 (PyInstaller)

- `pyinstaller agentteam.spec` 生成 standalone
- **难度**：M / **工期**：3 人天 / **依赖**：5.8.1

#### 5.8.3 解决 tmux 在 Windows 的限制

- 已有 `openclaw_sdk` 替代方案
- 文档化自动 fallback：`--backend auto` 在 Windows 选 openclaw_sdk
- 加测试覆盖
- **难度**：L / **工期**：1 人天

### 5.9 易修改性提升

#### 5.9.1 引入 DI 容器

- 用 `dependency-injector` 或自实现
- 消除 `get_X()` 全局函数模式
- **难度**：M / **工期**：3 人天 / **依赖**：5.1.1

#### 5.9.2 合并 4 个 manager 为统一状态机

- `TeamManager` / `LifecycleManager` / `MailboxManager` / `PlanManager` → `TeamStateMachine`
- 引入 `transitions` 库或手写 FSM
- **难度**：H / **工期**：5 人天 / **依赖**：5.9.1

#### 5.9.3 测试覆盖率提升到 85%+

- 当前 595+ 测试 / ~20% 覆盖率（粗略）
- 目标 85%+
- **难度**：M / **工期**：10 人天 / **依赖**：5.6.1 + 5.6.2

---

## 6. 按角色拆分 (5 人并行)

| Engineer | 模块 | 工期 | 依赖项 | 关键交付物 |
|----------|------|------|--------|------------|
| **Backend 1** (核心 + A2A) | 5.1.1 + 5.1.2 + 5.1.3 + 5.2.1 | 9 d | 无 | core/ + agent/ + a2a/ + async |
| **Backend 2** (MCP + 传输) | 5.2.2 + 5.3.1 + 5.3.2 (可选) | 9 d | 5.1.1 | mcp/ + transport/ 升级 |
| **Backend 3** (可观测性) | 5.5.1 + 5.5.2 + 5.5.3 | 7 d | 5.1.3 | observability/ + Prometheus |
| **Frontend / Full-stack 1** (Board + Web) | 5.6.2 + 5.6.3 + 5.7.1 + Web UI 升级 | 14 d | 无 | board/ 拆分 + React/Vite |
| **QA / DevX** (CLI 拆分 + 发布 + 文档) | 5.2.3 + 5.4.1 + 5.4.2 + 5.6.1 + 5.8.1 + 5.9.1 + 测试 | 14 d | 5.1.1 | cli/ 拆分 + PyPI + 文档 |

**协作点（每周 sync 一次）**：

- 5.1.1 core 拆包 → 所有 5.2/5.3/5.4/5.5/5.6/5.9 都依赖
- 5.1.3 async → 5.3/5.5 依赖
- 5.6.1 cli 拆分 → 5.7/5.8 依赖

**最大并行**：

- 5.6.2 board 拆分（Frontend 1）和 5.1.x core 改造（Backend 1）完全可独立并行
- 5.4.x plugin/skill 重构和 5.5.x observability 可并行

---
## 7. 优先级与 ROI 评估

### 7.1 优先级矩阵

| 改造项 | 业务价值 | 实现成本 | ROI | 优先级 | 阶段 |
|--------|---------|---------|-----|--------|------|
| 5.1.1 core 拆包 | 🟡 中 | 🟢 低 | 🟡 | **P0** | P0 |
| 5.1.2 agent/ 重构 | 🟠 高 | 🟡 中 | 🟠 | **P0** | P0 |
| 5.1.3 async runtime | 🟠 高 | 🟡 中 | 🟠 | **P0** | P0 |
| 5.2.1 A2A Server | 🔴 极高 | 🟡 中 | 🔴 | **P0** | P0 |
| 5.2.2 MCP Server | 🔴 极高 | 🟡 中 | 🔴 | **P0** | P0 |
| 5.2.3 SKILL.md 标准化 | 🟠 高 | 🟢 低 | 🟠 | **P0** | P0 |
| 5.3.1 transport 升级 | 🟡 中 | 🟡 中 | 🟡 | **P1** | P1 |
| 5.4.1 PluginManager 去单例 | 🟡 中 | 🟢 低 | 🟡 | **P1** | P1 |
| 5.4.2 Hook 标准化 | 🟡 中 | 🟢 低 | 🟡 | **P1** | P1 |
| 5.4.3 Skill 双向共享 | 🟠 高 | 🟡 中 | 🟠 | **P1** | P1 |
| 5.5.1 OpenTelemetry | 🟠 高 | 🟡 中 | 🟠 | **P1** | P1 |
| 5.5.3 Prometheus | 🟡 中 | 🟢 低 | 🟡 | **P1** | P1 |
| 5.6.1 CLI 拆分 | 🟠 高 | 🟡 中 | 🟠 | **P0** | P0 |
| 5.6.2 Board 拆分 | 🟠 高 | 🟡 中 | 🟠 | **P0** | P0 |
| 5.6.3 FastAPI | 🟡 中 | 🔴 高 | 🟡 | **P2** | P2 |
| 5.7.1 init 引导 | 🟠 高 | 🟢 低 | 🟠 | **P1** | P1 |
| 5.7.2 错误友好化 | 🟡 中 | 🟢 低 | 🟡 | **P1** | P1 |
| 5.8.1 PyPI | 🟠 高 | 🟢 低 | 🟠 | **P1** | P1 |
| 5.8.2 单二进制 | 🟡 中 | 🟡 中 | 🟡 | **P2** | P2 |
| 5.9.1 DI 容器 | 🟡 中 | 🟡 中 | 🟡 | **P2** | P2 |
| 5.9.2 状态机合并 | 🟠 高 | 🔴 高 | 🟡 | **P2** | P2 |
| 5.9.3 测试覆盖率 | 🟠 高 | 🟡 中 | 🟠 | **P1** | P1 |

### 7.2 关键决策 ADR

#### ADR-001: 协议选型 — 同时支持 A2A + MCP

- **决策**：实现 A2A Server（接收外部任务）+ MCP Server（暴露 AgentTeam 工具）
- **原因**：两者不冲突。A2A 是"Agent-to-Agent"，MCP 是"Tool Provider"，场景互补
- **后果**：维护两个协议实现，但获得最广泛的可集成性
- **替代方案**：只做 A2A（放弃 Claude/Cursor 直接工具调用）/ 只做 MCP（放弃多 Agent 联邦）

#### ADR-002: 异步化策略 — 渐进迁移

- **决策**：保留同步 API，添加 `async` 版本，逐步迁移
- **原因**：5800+ 行同步代码全改风险高
- **具体**：
  - 新增 `CTTeam.wait_all_async()`
  - 内部关键路径用 `asyncio.to_thread` 包装同步代码
  - 鼓励新代码用 async
- **后果**：维护双 API 6-12 个月

#### ADR-003: DI 容器选型 — 自制 vs 第三方

- **决策**：先用全局 `Container` 模式（不引入新依赖），后续可换 `dependency-injector`
- **原因**：避免一开始引入重量级依赖
- **后果**：初期需手写 `Container` 类（~200 行）

#### ADR-004: Web 框架 — 保留 stdlib 短期，FastAPI 长期

- **决策**：P0/P1 保留 `http.server`（零依赖），P2 切换 FastAPI
- **原因**：短期稳定性优先；P2 获得自动 OpenAPI

#### ADR-005: LLM 抽象 — 不重写，用 LiteLLM 适配

- **决策**：通过 LiteLLM 接入多 LLM（而非自建 `ProviderSelector`）
- **原因**：LiteLLM 已支持 100+ LLM；避免重复造轮子
- **现状改造**：`agentteam/orchestrator/provider_selector.py` 改为 LiteLLM 包装

---

## 8. 验收标准与里程碑

### 8.1 P0 里程碑 (Week 1-4)

**完成标准**：

- [ ] `cli/commands.py` ≤ 2000 行
- [ ] `board/server.py` ≤ 1500 行
- [ ] `from agentteam.agent import Agent` 可用，async 签名
- [ ] `agentteam a2a serve --port 41241` 启动，能用 `python-a2a` 客户端跨进程调用
- [ ] `agentteam mcp serve` 启动，Claude Desktop 能看到 5+ 工具
- [ ] 所有现有测试通过 (675 passed)
- [ ] 新增 async 测试 50+

**交付物**：

- `agentteam/core/` (新)
- `agentteam/agent/` (充实)
- `agentteam/protocol/a2a/` (新)
- `agentteam/protocol/mcp/` (新)
- `agentteam/cli/commands/` (拆分)
- `agentteam/board/handlers/` (拆分)
- `agentteam/board/sse/` (拆分)

### 8.2 P1 里程碑 (Week 5-8)

**完成标准**：

- [ ] 端到端 async 测试通过
- [ ] OpenTelemetry 默认开启，Jaeger 看到完整 trace
- [ ] Prometheus `/metrics` 暴露 5+ 关键指标
- [ ] PluginManager 支持多实例
- [ ] `agentteam skill export/import` 双向兼容 Claude Skills
- [ ] 测试覆盖率 ≥ 75%
- [ ] 已发布 PyPI 包 `pip install agentteam` 可用

**交付物**：

- `agentteam/observability/` (新)
- `agentteam/transport/MessageEnvelope` 升级
- Plugin 体系文档

### 8.3 P2 里程碑 (Week 9-12)

**完成标准**：

- [ ] Board 切换 FastAPI，自动生成 OpenAPI
- [ ] Web UI 用 React 18 + Vite 重构
- [ ] 单一二进制 `agentteam-bin` 可下载（mac/win/linux）
- [ ] 端到端 demo：Claude → MCP → AgentTeam → A2A → CrewAI
- [ ] 文档更新（10 语言 + 1 个集成指南）
- [ ] 测试覆盖率 ≥ 85%

---

## 9. 附录: 引用与链接

### 9.1 项目现状核心文件

- `agentteam/cli/commands.py` (5894 行) — CLI 单体
- `agentteam/board/server.py` (3104 行) — Board 单体
- `agentteam/core.py` (350+ 行) — 核心 SDK
- `agentteam/transport/base.py` — Transport 抽象
- `agentteam/orchestrator/__init__.py` — Orchestrator 入口
- `agentteam/skills/auto_creator.py` — Skill 自动创建
- `agentteam/plugins/__init__.py` — PluginManager 单例
- `agentteam/agent/__init__.py` — 空壳模块
- `agentteam/hermes/__init__.py` — Hermes 5 Phase 集成
- `agentteam/memory/layered.py` — L1-L4 记忆

### 9.2 文档

- `README.md` / `CAPABILITIES.md` / `ARCHITECTURE_REVIEW.md`
- `PLATFORM_COMPATIBILITY.md` / `ROADMAP.md` / `DEVELOPER_GUIDE.md`
- `CHANGELOG.md` / `TODO.md` / `UPGRADE.md`

### 9.3 对标项目链接

| 项目 | 链接 | 备注 |
|------|------|------|
| MetaGPT | https://github.com/foundationagents/metagpt | SOP + Action Watch |
| AutoGen v0.4+ | https://github.com/microsoft/autogen | RoutedAgent + OpenTelemetry |
| CrewAI | https://github.com/crewaiinc/crewai | allow_delegation + 五种 memory |
| LangGraph | https://github.com/langchain-ai/langgraph | StateGraph + Send + Checkpoint |
| OpenHands SDK | https://github.com/openhands/software-agent-sdk | FastAPI Agent Server + Webhook |
| OpenHands | https://github.com/All-Hands-AI/OpenHands | 原 OpenDevin |
| Pydantic-AI | https://github.com/pydantic/pydantic-ai | FastAPI-like DX + deps 注入 |
| Smolagents | https://github.com/huggingface/smolagents | 极简 agent loop |
| Agno | https://github.com/agno-agi/agno | AgentOS 控制面 |
| OpenAI Agents SDK | https://github.com/openai/openai-agents-python | Handoffs + Guardrails + Tracing |
| Claude Skills | https://github.com/anthropics/skills | SKILL.md 规范 |
| A2A Protocol | https://github.com/a2aproject/a2a-python | Agent Card + JSON-RPC |
| MCP | https://github.com/modelcontextprotocol/python-sdk | Tools/Resources/Prompts |
| Goose (Block) | https://github.com/block/goose | MCP Extensions + Recipe |
| Aider | https://github.com/Aider-AI/aider | CLI 单体（反例） |

### 9.4 工具与规范

- OpenTelemetry Python SDK: https://opentelemetry.io/docs/languages/python/
- Prometheus Python client: https://github.com/prometheus/client_python
- LiteLLM (LLM 统一接口): https://github.com/BerriAI/litellm
- dependency-injector: https://github.com/ets-labs/python-dependency-injector
- FastAPI: https://fastapi.tiangolo.com
- PyInstaller: https://pyinstaller.org
- Hatchling (打包): https://hatch.pypa.io
- ruff: https://docs.astral.sh/ruff/

### 9.5 数字统计原始数据

```bash
$ find "C:/Users/31683/AgentTeam/agentteam" -type f -name "*.py" | wc -l
171

$ find "C:/Users/31683/AgentTeam" -type f -name "*.py" | wc -l
263

$ find "C:/Users/31683/AgentTeam/tests" -type f -name "*.py" | wc -l
87

$ wc -l "C:/Users/31683/AgentTeam/agentteam/cli/commands.py"
5894 cli/commands.py

$ wc -l "C:/Users/31683/AgentTeam/agentteam/board/server.py"
3104 board/server.py

$ ls "C:/Users/31683/AgentTeam/agentteam/" | wc -l
40 (一级子模块数)
```

---

## 📌 总结

**AgentTeam 已经是行业最完整的多 Agent 协调 CLI 之一**，但要从"工具型"演化为"协议型 Runtime + 嵌入式 SDK"，**P0 的 6 项改造**（核心拆包 / agent 充实 / async / A2A / MCP / SKILL.md 标准化 / CLI & Board 拆分）是最高 ROI，**4 周可完成**，并立即打开"被 Claude/Cursor/LangGraph/AutoGen 直接调用"的大门。

**P1 + P2 完成后**，AgentTeam 将从"内部工具"升级为"多 Agent 运行时 + 协议适配层"，**适配性从 3.5 → 8.5**，成为 MetaGPT / LangGraph / OpenHands / A2A / MCP 生态的**平等节点**而非孤立 CLI。

**5 人并行**的拆分方案见第 6 节；详细 ADR 见第 7.2 节；验收标准见第 8 节。

> 本提案基于实际代码分析（171 个 .py 文件、87 个测试、5.8k+3.1k 单体文件、4 个并行 manager、6 个 spawn backend、3 个 transport），每个改造都标注了具体文件路径与工期，可直接进入 Sprint 排期。
