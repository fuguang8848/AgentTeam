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

## 为什么选择 AgentTeam？

| | AgentTeam | 基础 Agent 框架 |
|---|---------|----------------------------|
| **目标** | AI Agent 自主协调 | 人类管理每个 Agent |
| **安装** | `pip install` · 完成 | Docker + 配置 + 云 API |
| **监控** | **Web UI 仪表盘** + tmux | 仅 CLI |
| **可靠性** | **重试 + 结构化日志 + 告警** | 无 |
| **安全性** | **API 认证 + 令牌隔离** | 通常无 |
| **可观测性** | **审计日志 + 漂移检测** | 无 |
| **质量** | **595+ 测试，P0-P25 验证** | 临时 |
| **基础设施** | 文件系统（无需 Redis） | 需要 Redis/消息队列 |

---

## 特性

### 多智能体编排
- **团队管理**：基于角色分配创建、管理和监控 Agent 团队
- **动态任务分发**：基于 Agent 能力的智能路由
- **消息传递**：Agent 间通信，支持邮箱和收件箱系统

### 可靠性
- **自动重试**：失败任务自动指数退避重试
- **结构化日志**：所有组件日志格式一致
- **告警系统**：任务失败和团队事件的可配置告警

### 安全性
- **API 认证**：所有 API 端点基于令牌认证
- **令牌隔离**：每个 Agent 获取隔离的凭证
- **审计日志**：所有 Agent 操作的完整追踪

### 可观测性
- **实时仪表盘**：监控团队活动的 Web UI
- **事件追踪**：追踪所有团队事件和 Agent 交互
- **漂移检测**：检测 Agent 行为何时偏离预期

---

## 快速开始

### 安装

```bash
pip install agentteam
```

或从源码安装：

```bash
git clone https://github.com/YintaTriss/AgentTeam.git
cd AgentTeam
pip install -e .
```

### 初始化团队

```bash
# 创建新团队
agentteam init my-team

# 进入团队目录
cd my-team
```

### 启动团队

```bash
# 启动团队 leader
agentteam start

# 在另一个终端，启动 Agent
agentteam spawn --name worker-1 --role researcher
agentteam spawn --name worker-2 --role coder
```

### 使用仪表盘

```bash
# 启动 Web 仪表盘
agentteam dashboard
```

然后打开 http://localhost:8080 监控团队。

---

## 架构

```
┌─────────────────────────────────────────────────┐
│                   CLI 层                          │
│         (agentteam/cli/, team/, spawn/)          │
└─────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────┐
│                   核心 SDK 层                      │
│      (CTTeam, CTAgent, CTTask, CTMessage)       │
└─────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────┐
│                  编排层                            │
│     (orchestrator/, spawn/, session/, events/)   │
└─────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────┐
│                   存储层                            │
│       (database/, store/, memory/, board/)       │
└─────────────────────────────────────────────────┘
```

---

## 文档

更多文档请访问 [OpenClaw 文档](https://docs.openclaw.ai)。

### 关键主题

- [CLI 参考](CLI.md) - 完整的 CLI 命令参考
- [API 文档](API.md) - API 参考
- [部署指南](DEPLOY.md) - 部署说明
- [架构审查](ARCHITECTURE_REVIEW.md) - 系统架构详情

---

## 许可证

MIT
