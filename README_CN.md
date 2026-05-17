# AgentTeam

生产级多智能体 swarm 协作框架。基于 OpenClaw 构建，由 AI Agent 自主驱动。

## 特性

- **多智能体编排**：协调多个 AI Agent 协同完成复杂任务
- **团队管理**：创建、管理和监控 Agent 团队，支持角色分配
- **消息传递**：Agent 间通信，支持邮箱和收件箱系统
- **会话感知**：跨 Agent 会话追踪和维护上下文
- **实时仪表盘**：可视化监控 Agent 活动和协作状态
- **插件系统**：可扩展架构，支持自定义技能和集成

## 快速开始

```bash
# 安装
pip install agentteam

# 初始化团队
agentteam init my-team

# 启动团队
agentteam start my-team

# 启动 Agent
agentteam spawn --name worker-1 --role researcher
agentteam spawn --name worker-2 --role coder
```

## 文档

更多文档请访问 [OpenClaw 文档](https://docs.openclaw.ai)。

## 许可证

MIT
