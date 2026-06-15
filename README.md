# 🦞 AgentTeam

[English](README.md) ·
[简体中文](README_CN.md) ·
[繁體中文](README_TW.md) ·
[日本語](README_JA.md) ·
[한국어](README_KO.md) ·
[Français](README_FR.md) ·
[Español](README_ES.md) ·
[Deutsch](README_DE.md) ·
[Italiano](README_IT.md) ·
[Русский](README_RU.md) ·
[Português (Brasil)](README_PT-BR.md)



<p align="center">
  <strong>Production-ready multi-agent swarm coordination — Built for <a href="https://openclaw.ai">OpenClaw</a>, powered by AI agents themselves</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-v0.8.0--openclaw-blue?style=for-the-badge" alt="Version">
  <img src="https://img.shields.io/badge/python-≥3.10-blue?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/tests-943%2B-brightgreen?style=for-the-badge" alt="Tests">
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

## ✨ 为什么选择 AgentTeam？

| | AgentTeam | Basic Agent Frameworks |
|---|---------|----------------------------|
| **Target** | AI agents coordinate themselves | Humans micromanage agents |
| **Setup** | `pip install -e .` → done | Docker + configs + cloud APIs |
| **Monitoring** | **Web UI Dashboard** + tmux | CLI only |
| **Reliability** | **Retry + Structured Logs + Alerts** | None |
| **Security** | **API Auth + Token Isolation** | Usually none |
| **Observability** | **Audit Logs + Drift Detection** | None |
| **Quality** | **943+ tests, P0-P37 verified** | Ad-hoc |
| **Infrastructure** | Filesystem (no Redis needed) | Redis/message queues required |

---

## 🚀 5 分钟快速开始

```bash
# 1. 安装
git clone https://github.com/YOUR_USERNAME/AgentTeam.git
cd AgentTeam
pip install -e .

# 2. 启动 Web 看板
agentteam board serve --port 8080

# 3. 告诉 AI："用 AgentTeam 构建一个博客系统"
# AI 自动创建团队、分发任务、协调结果
```

**Done.** 不需要 Redis、不需要 Docker、不需要手动配置。

---

## 🏗️ 核心架构

```
┌─────────────────────────────────────────────────────────────┐
│                    AgentTeam                       │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │
│  │  Web UI     │    │   CLI       │    │  REST API   │   │
│  │  Dashboard  │    │  (tmux)     │    │  (Auth)     │   │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘   │
│         │                   │                   │           │
│  ┌──────┴───────────────────┴───────────────────┴──────┐  │
│  │                   Router + Alerts + Audit            │  │
│  └───────────────────────┬─────────────────────────────┘  │
│                          │                                 │
│  ┌───────────────────────┴─────────────────────────────┐  │
│  │              Agent Pool (OpenClaw / Claude / Codex)   │  │
│  └───────────────────────┬─────────────────────────────┘  │
│                          │                                 │
│  ┌───────────────────────┴─────────────────────────────┐  │
│  │           Transport Layer (File / Redis / ZeroMQ)    │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 完整功能清单

### 🔧 Agent 协调引擎
- **智能路由** — 三因素算法（历史表现 + 负载感知 + 技能匹配）
- **动态角色分配** — 基于任务类型自动分配 Agent 角色
- **DAG 依赖管理** — 任务拓扑排序，智能调度
- **P0-P33 分层测试** — 1790+ 测试用例，全面覆盖
- **MailboxManager** — Agent 间消息传递，Transport 抽象层支持 File/P2P/Redis
- **P2P Transport** — ZeroMQ PUSH/PULL + 文件回退，无需 Redis
- **RoleStore** — 动态角色分配（developer/reviewer/tester/architect/coordinator）
- **BaseTaskStore** — 任务存储抽象，文件锁并发控制
- **WebSocketManager** — WebSocket 连接管理
- **Parent-Child 生命周期** — 父子 Agent 级联管理
- **OpenClaw SDK Backend** — 基于 Gateway Sessions API 的原生多 Agent 协作

### 🌐 Web UI 看板
- **实时会话监控** — 每秒刷新，看得见每个 Agent 在做什么
- **多标签页** — 看板 / 设计器 / 监控 / 工作流 / 设置
- **状态可视化** — 任务卡片、Agent 状态、漂移预警
- **一键部署** — `agentteam board serve --port 8080`

### 🔐 生产级安全
- **API 认证** — JWT-like Token 机制
- **Gateway Token 传递** — 自动分发到子 Agent
- **Session 隔离** — 每个 Agent 独立会话，互不干扰
- **环境变量管理** — `.env` 分离，敏感信息不上传

### 📋 可观测性
- **审计日志** — 事件追溯、Actor 分析、时间范围过滤
- **结构化日志** — JSON 格式 + trace_id 全链路追踪
- **漂移检测** — Jaccard + 语义相似度双校验
- **质量评分** — completeness / accuracy / quality 多维评估

### 🚨 告警系统
- **四级告警** — LOW / MEDIUM / HIGH / CRITICAL
- **告警类型** — TASK_TIMEOUT / AGENT_FAILURE_RATE_HIGH / TEAM_INACTIVITY
- **CRUD 操作** — 创建 / 查询 / 列表 / 确认
- **CLI 集成** — `agentteam alert check/list/ack`

### 🐳 部署选项
- **Docker** — `Dockerfile` + `docker-compose.yml`
- **裸机** — `pip install -e .` 一行命令
- **分布式** — Redis / ZeroMQ P2P 可选
- **Makefile** — `make dev` / `make prod` / `make test`

### 📚 文档
- **API 文档** — `API.md` 完整 REST API 参考
- **CLI 参考** — `CLI.md` 所有命令详解
- **部署指南** — `DEPLOY.md` Docker / 裸机 / 分布式
- **开发者指南** — `DEVELOPER_GUIDE.md`
- **多语言** — 中/英/日/韩/法/德等 10 种语言

### 🧩 扩展性
- **Shell 补全** — bash / zsh / fish
- **Provider API** — 模型分配、路由策略
- **插件架构** — 轻松集成新 Agent 类型
- **OpenClaw 原生** — 深度集成，默认 Agent

---

## 📊 版本对比

| 功能 | 上游 v0.3.0 | **AgentTeam v0.8.0** |
|------|-------------|-------------------------------|
| Web UI 看板 | ❌ | ✅ |
| API 认证 | ❌ | ✅ |
| 智能路由 | ❌ | ✅ |
| 审计日志 | ❌ | ✅ |
| 告警机制 | ❌ | ✅ |
| 漂移检测 | ❌ | ✅ |
| 质量评分 | ❌ | ✅ |
| Docker 支持 | ⚠️ 基础 | ✅ 完整 |
| Shell 补全 | ❌ | ✅ bash/zsh/fish |
| 多语言文档 | ❌ | ✅ 10 种语言 |
| 测试覆盖 | ~100 | **595+** |
| 重试框架 | ❌ | ✅ |
| 结构化日志 | ❌ | ✅ |
| MailboxManager | ❌ | ✅ (P2P/ZeroMQ) |
| Parent-Child 生命周期 | ❌ | ✅ (P26) |
| OpenClaw SDK Backend | ❌ | ✅ (原生集成) |
| WebSocket 实时推送 | ❌ | ✅ (SSE) |

---

## 🛠️ 支持的 Agent

| Agent | 命令 | 状态 |
|-------|------|------|
| **[OpenClaw](https://openclaw.ai)** | `agentteam spawn tmux openclaw` | ✅ **默认** |
| **[Claude Code](https://claude.ai/claude-code)** | `agentteam spawn tmux claude` | ✅ 完全支持 |
| **[Codex](https://openai.com/codex)** | `agentteam spawn tmux codex` | ✅ 完全支持 |
| **[nanobot](https://github.com/HKUDS/nanobot)** | `agentteam spawn tmux nanobot` | ✅ 完全支持 |
| **[Cursor](https://cursor.com)** | `agentteam spawn subprocess cursor` | ⚠️ 实验性 |
| **自定义脚本** | `agentteam spawn subprocess python` | ✅ 完全支持 |

---

## 📖 快速链接

| 文档 | 说明 |
|------|------|
| [README.md](README.md) | 本文档 |
| [CAPABILITIES.md](CAPABILITIES.md) | 完整功能清单 |
| [PLATFORM_COMPATIBILITY.md](PLATFORM_COMPATIBILITY.md) | 平台兼容性报告 |
| [API.md](API.md) | REST API 完整参考 |
| [CLI.md](CLI.md) | CLI 命令详解 |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Docker / 裸机部署指南 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 贡献指南 |
| [TODO.md](TODO.md) | 待办事项跟踪 |
| [CHANGELOG.md](CHANGELOG.md) | 升级日志 |

---

## 🧪 测试

```bash
# 运行全部测试
python -m pytest tests/ -v

# 只跑路由测试
python -m pytest tests/test_routing.py -v

# 只跑告警测试
python -m pytest tests/test_alerts.py -v

# 只跑审计测试
python -m pytest tests/test_audit.py -v
```

---

## 📦 安装

```bash
# 基础安装
git clone https://github.com/YOUR_USERNAME/AgentTeam.git
cd AgentTeam
pip install -e .

# 可选：P2P 传输
pip install -e ".[p2p]"

# 可选：Redis 传输
pip install -e ".[redis]"
```

---

## 🤝 贡献

欢迎提交 Issue 和 PR！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解更多。

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

## 🙏 致谢

**上游项目：**

- [HKUDS/ClawTeam](https://github.com/HKUDS/ClawTeam) — 原始框架，多智能体协调理论奠基
- [win4r/ClawTeam-OpenClaw](https://github.com/win4r/ClawTeam-OpenClaw) — 直接上游分支，OpenClaw 集成先行者（v0.3.0）
- [OpenClaw](https://openclaw.ai) — 默认 Agent 引擎，深度集成支持

**核心技术参考：**

- [VCP System](https://github.com/lioensky/VCPToolBox) — 认知架构启发
- [EverMind MSA](https://github.com/EverMind-AI/MSA) — 记忆系统架构参考

**所有贡献者，欢迎提交 PR！**

---

<p align="center">
  <strong>Made with ⚔️ by Yinta, for AI agents</strong>
</p>
