# AgentTeam

生产级多智能体 swarm 协作框架。基于 OpenClaw 构建，由 AI Agent 自主驱动。

<p align="center">
  <strong>自组织的 Agent 团队，协同工作、分配任务、交付结果。</strong>
</p>

<p align="center">
  <a href="https://github.com/openclaw/openclaw"><strong>基于 OpenClaw</strong></a>
  ·
  <a href="https://discord.com/invite/clawd"><strong>社区</strong></a>
  ·
  <a href="https://docs.openclaw.ai"><strong>文档</strong></a>
</p>

---

> **AgentTeam** 是 [HKUDS/ClawTeam](https://github.com/HKUDS/ClawTeam) 的生产级分支，专为需要企业级多智能体协作的 OpenClaw 用户构建。
>
> 所有上游修复已同步。这不是演示——这是生产级软件。

---

## 为什么选择 AgentTeam？

| | AgentTeam | 基础 Agent 框架 |
|---|---------|----------------------------|
| **目标** | AI Agent 自主协调 | 人类管理每个 Agent |
| **安装** | `pip install -e .` · 一步完成 | Docker + 配置 + 云 API |
| **监控** | **Web UI 仪表盘** + tmux | 仅 CLI |
| **可靠性** | **重试 + 结构化日志 + 告警** | 无 |
| **安全性** | **API 认证 + 令牌隔离** | 通常无 |
| **可观测性** | **审计日志 + 漂移检测** | 无 |
| **质量** | **595+ 测试，P0-P25 验证** | 临时 |
| **基础设施** | 文件系统（无需 Redis） | 需要 Redis/消息队列 |

---

## 快速开始（5 分钟）

```bash
# 1. 安装
git clone https://github.com/YintaTriss/AgentTeam.git
cd AgentTeam
pip install -e .

# 2. 启动 Web 仪表盘
agentteam board serve --port 8080

# 3. 告诉 AI 使用 AgentTeam 构建博客系统
# AI 自动创建团队、分配任务、协调结果
```

**完成。** 无需 Redis。无需 Docker。无需手动配置。

---

## 架构

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

## 完整功能清单

### Agent 编排引擎
- **智能路由** — 三因素算法（历史嵌入 + 负载感知 + 能力匹配）
- **动态角色分配** — 基于任务类型自动分配 Agent 角色（developer/reviewer/tester/architect/coordinator）
- **DAG 任务管理** — 任务依赖图，智能调度
- **P0-P33 分层测试** — 1790+ 测试用例，全面覆盖
- **MailboxManager** — Agent 进程间消息传递，Transport 支持 File/P2P/Redis
- **P2P Transport** — ZeroMQ PUSH/PULL + 文件兜底，无需 Redis
- **RoleStore** — 动态角色分配
- **BaseTaskStore** — 任务存储抽象，文件锁并发控制
- **WebSocketManager** — WebSocket 连接管理
- **Parent-Child 生命周期** — 父子 Agent 关系管理
- **OpenClaw SDK Backend** — 基于 Gateway Sessions API 的多 Agent 协作

### Web UI 仪表盘
- **实时对话监控** — 每秒更新，看到每个 Agent 在做什么
- **多标签页** — 仪表盘 / 设计器 / 监控器 / 工作区 / 设置
- **状态可视化** — 任务进度、Agent 状态、异常预测
- **一行启动** — `agentteam board serve --port 8080`

### 生产级安全
- **API 认证** — JWT-like Token 机制
- **Gateway Token 分发** — 自动分发到子 Agent
- **会话隔离** — 每个 Agent 独立对话，互不干扰
- **环境变量隔离** — `.env` 分离，敏感信息不上传

### 可观测性
- **审计日志** — 事件追踪、Actor 分析、时间范围过滤
- **结构化日志** — JSON 格式 + trace_id 全链路追踪
- **漂移检测** — Jaccard + 语义相似度双验证
- **质量评分** — 多维度评估：完整性 / 准确性 / 质量

### 告警系统
- **四级告警** — LOW / MEDIUM / HIGH / CRITICAL
- **告警类型** — TASK_TIMEOUT / AGENT_FAILURE_RATE_HIGH / TEAM_INACTIVITY
- **CRUD 操作** — 创建 / 查询 / 列表 / 确认
- **CLI 集成** — `agentteam alert check/list/ack`

### 部署选项
- **Docker** — `Dockerfile` + `docker-compose.yml`
- **快速安装** — `pip install -e .` 一命令搞定
- **分布式模式** — Redis / ZeroMQ P2P 可选
- **Makefile** — `make dev` / `make prod` / `make test`

### 文档
- **Shell 补全** — bash / zsh / fish
- **API 参考** — 完整的 API 文档
- **架构审查** — 详细的系统架构分析
- **部署指南** — 一步一步的部署说明

---

## 完整能力

### 核心能力

| 能力 | 描述 |
|------|------|
| **Agent 团队** | 创建和管理多个 Agent 团队 |
| **任务编排** | 基于 DAG 的任务调度和委托 |
| **Agent 间消息传递** | 用于 Agent 通信的邮箱系统 |
| **实时监控** | 实时活动追踪的 Web 仪表盘 |
| **告警管理** | 故障和异常的可配置告警 |
| **审计日志** | 所有团队活动的完整追踪 |
| **漂移检测** | 检测 Agent 行为何时偏离 |
| **基于角色的访问** | JWT-like 令牌认证 |

### 高级能力

| 能力 | 描述 |
|------|------|
| **多后端支持** | OpenClaw SDK、subprocess、tmux、API |
| **P2P 传输** | 基于 ZeroMQ 的点对点通信 |
| **会话隔离** | 每个 Agent 有独立上下文 |
| **父子生命周期** | 层级 Agent 关系 |
| **质量评分** | 多维度任务质量评估 |
| **结构化日志** | 带 trace ID 的 JSON 日志 |

---

## 版本对比

| 版本 | 主要变化 |
|------|----------|
| v0.5.1 | 生产级加固，企业功能 |
| v0.5.0 | 重大发布，P0-P33 测试 |
| v0.4.0 | 初始 OpenClaw 分支 |

---

## 支持的 Agent

| Agent | 状态 | 备注 |
|-------|------|------|
| **OpenClaw** | ✅ 主要 | 默认 Agent 后端 |
| **Claude Code** | ✅ 支持 | 完全兼容 |
| **Codex** | ✅ 支持 | 通过 CLI 接口 |
| **nanobot** | ✅ 支持 | 通过 CLI 接口 |
| **Cursor** | ✅ 支持 | 通过 CLI 接口 |
| **自定义 CLI** | ✅ 支持 | 通过 subprocess 后端 |

---

## 快速链接

| 资源 | 链接 |
|------|------|
| 文档 | [OpenClaw 文档](https://docs.openclaw.ai) |
| CLI 参考 | [CLI.md](CLI.md) |
| API 参考 | [API.md](API.md) |
| 部署 | [DEPLOY.md](DEPLOY.md) |
| 架构 | [ARCHITECTURE_REVIEW.md](ARCHITECTURE_REVIEW.md) |
| 贡献 | [CONTRIBUTING.md](CONTRIBUTING.md) |

---

## 测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试层
python -m pytest tests/test_p0.py -v
python -m pytest tests/test_p1.py -v
python -m pytest tests/test_integration.py -v

# 带覆盖率
python -m pytest tests/ --cov=agentteam --cov-report=html

# 审计测试
python -m pytest tests/test_audit.py -v
```

---

## 安装

```bash
# 基础安装
git clone https://github.com/YintaTriss/AgentTeam.git
cd AgentTeam
pip install -e .

# 可选：P2P 传输
pip install -e ".[p2p]"

# 可选：Redis 传输
pip install -e ".[redis]"

# 可选：所有扩展
pip install -e ".[all]"
```

---

## 贡献

欢迎贡献！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解更多。

---

## 许可证

MIT 许可证 - 参见 [LICENSE](LICENSE)

---

## 致谢

**上游项目：**

- [HKUDS/ClawTeam](https://github.com/HKUDS/ClawTeam) — 原始框架，多智能体协作研究
- [OpenClaw](https://openclaw.ai) — 默认 Agent 后端，深度 OpenClaw 集成支持

**核心技术参考：**

- [VCP System](https://github.com/lioensky/VCPToolBox) — Acknowledgment 结构框架
- [EverMind MSA](https://github.com/EverMind-AI/MSA) — 记忆系统架构参考

**所有贡献都很感激！**

---

<p align="center">
  <strong>由 Yinta 用 ❤️ 为 AI agents 打造</strong>
</p>
