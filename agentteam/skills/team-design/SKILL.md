---
name: AgentTeam Team Design
description: >
  This skill should be used when the user asks to "use AgentTeam", "spawn a team",
  "coordinate multiple agents", "create an agent team", or any scenario requiring
  multi-agent collaboration. Provides guidance on team structure design, role
  assignment, and leader coordination workflow.
version: 0.1.0
---

# AgentTeam Team Design

## Purpose

When needing to use AgentTeam for complex tasks, follow this workflow:

当需要使用 AgentTeam 完成复杂任务时，按照以下流程工作：

## 标准工作流程

```
1. 设计团队结构 → 2. 创建团队 → 3. 派发专家 → 4. 告知 leader 需求
```

### 步骤一：设计团队结构

**在派发专家之前**，先思考团队需要什么角色：

| 角色类型 | 职责 | 适用场景 |
|---------|------|---------|
| **architect** | 架构设计、代码审查、技术评审 | 需要设计审查的任务 |
| **backend** | 后端开发、性能优化、代码实现 | 性能优化、重构 |
| **frontend** | 前端界面、用户体验 | Web/UI 任务 |
| **tester** | 测试覆盖、质量保障 | 测试增强 |
| **doc-writer** | 文档撰写、API 文档 | 文档更新 |
| **reviewer** | 代码审查、安全审查 | 代码审查 |
| **researcher** | 技术调研、方案评估 | 研究类任务 |

**不要**：有什么任务就临时派什么专家（子代理思维）

**应该**：先设计团队结构，再分配任务

### 步骤二：创建团队

```bash
# 使用模板创建（推荐）
agentteam team create <团队名> --template <模板名> --description "<描述>"

# 可用模板：
# - development-team-max: 架构师 + 后端 + 前端 + 测试
# - development-team-mix: 全栈 + UI + QA
# - research-paper: 研究团队
# - hedge-fund: 金融团队
# - strategy-room: 战略团队
```

**注意**：Windows 不支持 tmux 后端，需要用 SDK backend 手动派发专家。

### 步骤三：派发专家

```bash
agentteam spawn openclaw_sdk --team <团队名> --agent-name <名称> --agent-type <类型> --task "<任务描述>"
```

派发的专家类型应该与步骤一设计的团队结构一致。

### 步骤四：告知 leader 需求

**通过 inbox 发送需求文档给 leader**：

```bash
agentteam inbox send <团队名> leader "<需求文档>"
```

需求文档应包含：
- 项目背景
- 具体任务列表（每个任务指明负责角色）
- 工作目录
- leader 的协调职责

### 步骤五：让 leader 协调

**我只负责**：设计团队 → 告诉 leader 要什么

**leader 负责**：
- 接收需求
- 分配任务给合适的成员
- 协调进度
- 监控质量

**重要**：不要跳过 leader 直接管理专家，让 leader 做协调工作。

## 示例

### 场景：AgentTeam 升级任务

**错误做法（子代理思维）**：
```
有升级任务 → 随机派发 test-squad, perf-squad, doc-squad
```

**正确做法（团队思维）**：
```
1. 设计团队：architect + backend + tester + doc-writer
2. 创建团队：agentteam team create agentteam-upgrade
3. 派发专家：spawn architect, backend, tester, doc-writer
4. 告知 leader：
   "需要完成：测试增强、性能优化、代码审查、文档更新"
5. leader 协调分配任务
```

## 触发条件

当用户说：
- "用 AgentTeam 完成 X"
- "动用 agentteam 进行升级"
- "用团队协作方式处理"
- 或任何需要多代理协作的任务

## 核心原则

1. **先设计，后执行** — 团队结构优于临时任务分配
2. **leader 协调** — 我只对 leader，leader 对成员
3. **角色明确** — 每个专家知道自己是谁、负责什么
4. **流程规范** — 不要跳过步骤

---

_此技能确保 AgentTeam 团队协作流程规范化，避免临时凑齐专家的子代理思维。_
