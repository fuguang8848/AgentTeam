# AgentTeam Skill/Plugin 体系深度审计报告

> **审计日期**: 2026-06-04  
> **审计版本**: v1.0  
> **审计范围**: AgentTeam-OpenClaw Skills/Plugins 体系 vs 业界顶尖系统

---

## 目录

1. [执行摘要](#执行摘要)
2. [当前体系架构](#当前体系架构)
3. [当前体系详细分析](#当前体系详细分析)
4. [业界对标分析](#业界对标分析)
5. [痛点 TOP 10](#痛点-top-10)
6. [改造方案](#改造方案)
7. [推荐落地路径](#推荐落地路径)
8. [附录：SKILL.md 格式规范](#附录skillmd-格式规范)

---

## 执行摘要

### 审计结论

AgentTeam 当前已构建了 **Skill 引擎** 和 **Plugin 钩子系统** 两个独立体系，具备基础的扩展能力，但与 Claude Skills、LangChain Tools 等业界顶尖系统相比，在标准化、可组合性、安全沙箱、生态兼容性等方面存在显著差距。

**核心差距**：
- 缺乏统一的 Skill 描述格式（SKILL.md）
- Plugin/Skill 边界模糊，功能重叠
- 无跨框架兼容能力（MCP 协议）
- 无安全沙箱和资源限制
- Skill 组合/编排能力不足

### 改造收益预估

| 改进方向 | 预期收益 |
|---------|---------|
| 统一 SKILL.md 格式 | 生态可移植性 +80% |
| MCP 协议兼容 | 框架互操作性 +90% |
| 沙箱执行 | 安全隔离 +100% |
| Skill 组合 | 复用率 +60% |
| Entry Points 发现 | 开发者体验 +70% |

---

## 当前体系架构

### 2.1 整体架构图

```
+---------------------------------------------------------------------+
|                         AgentTeam 系统                                |
+---------------------------------------------------------------------+
|                                                                      |
|  +-------------+     +-------------+     +-------------+            |
|  |   Skill/    |     |   Plugin/   |     |  Template/  |            |
|  |   skills/   |     |   plugins/  |     |  templates/ |            |
|  |             |     |             |     |             |            |
|  | auto_creator|     | __init__.py |     |  *.toml     |            |
|  +------+------+     +------+------+     +------+------+            |
|         |                    |                    |                 |
|  +------+------+     +------+------+              |                 |
|  | SkillEngine |     | HookRegistry|              |                 |
|  | BUILTIN_   |     |   Hooks    |              |                 |
|  | SKILLS     |     | PluginMgr  |              |                 |
|  +------------+     +------------+              |                 |
+---------------------------------------------------------------------+
```

### 2.2 目录结构

| 目录 | 说明 |
|------|------|
| agentteam/skill/ | Skill 引擎模块 |
| agentteam/skills/ | 自主 Skill 创建系统 |
| agentteam/plugins/ | Plugin 钩子系统 |
| agentteam/templates/ | 团队模板 |

### 2.3 组件职责

| 组件 | 职责 | 状态 |
|-----|------|------|
| SkillEngine | 提示词模板展开、变量解析 | 已实现 |
| BUILTIN_SKILLS | 4个内置技能 | 基础 |
| SkillAutoCreator | 模式检测、自动生成 SKILL.md | P13规划 |
| SkillUsageTracker | 使用统计、效率分析 | P13规划 |
| PluginManager | 插件发现、加载、生命周期 | 基本实现 |
| HookRegistry | 钩子注册、执行 | 基本实现 |
| Hooks | 预定义钩子点(12个) | 基本实现 |

---

## 当前体系详细分析

### 3.1 Skill 发现机制

| 维度 | 当前实现 | 评估 |
|-----|---------|-----|
| 发现方式 | 代码硬编码 BUILTIN_SKILLS 列表 | 无动态发现 |
| 文件系统扫描 | 不支持 | 缺失 |
| Entry Points | 不支持 | 缺失 |
| MCP Server | 不支持 | 缺失 |
| 热加载 | 不支持 | 缺失 |

### 3.2 Skill 元数据格式

- 纯代码定义，无 YAML/JSON/Markdown 格式
- 无法被外部工具解析和共享
- 缺乏描述性文档字段

### 3.3 Plugin 发现机制

| 维度 | 当前实现 | 评估 |
|-----|---------|-----|
| 发现方式 | 手动 register() | 半自动 |
| 文件系统扫描 | 不支持 | 缺失 |
| Entry Points | 不支持 | 缺失 |
| 热加载 | 不支持 | 缺失 |
| 卸载 | 不支持 | 缺失 |

### 3.4 Skill 执行模型

| 维度 | 当前实现 | 评估 |
|-----|---------|-----|
| 执行方式 | 模板展开后直接传递给 LLM | 间接 |
| Subprocess | 不支持 | 缺失 |
| 沙箱 | 不支持 | 缺失 |
| 资源限制 | 不支持 | 缺失 |
| 超时控制 | 不支持 | 缺失 |

---

## 业界对标分析

### 4.1 对标系统概览

| 系统 | 类型 | 核心特点 | 评分 |
|-----|------|---------|------|
| Claude Skills | Prompt-based | SKILL.md标准化、生态丰富 | 5星 |
| OpenAI GPTs | Hybrid | Actions、Knowledge、Instructions | 5星 |
| CrewAI Tools | Code-based | @tool decorator、类型安全 | 4星 |
| LangChain Tools | Code-based | @tool、StructuredTool、JSON Schema | 5星 |
| MCP | Protocol | 标准化工具描述、跨框架 | 5星 |
| Gemini Gems | Prompt-based | 简单配置、快速定制 | 3星 |

### 4.2 详细对比表

| 维度 | AgentTeam | Claude Skills | OpenAI GPTs | CrewAI | LangChain | MCP |
|-----|-----------|---------------|-------------|--------|-----------|-----|
| 描述格式 | dataclass | SKILL.md | GUI+API | @tool | @tool | JSON-RPC |
| 发现机制 | 无 | Entry Points | Marketplace | import | Entry Points | stdio/http |
| 动态加载 | 无 | 即装即用 | 云端 | scan | Dynamic | Server |
| 类型安全 | Partial | Partial | 强类型 | Pydantic | JSON Schema | JSON Schema |
| 组合能力 | 无 | Chain | Sequence | Sequential | LangGraph | Pipeline |
| 沙箱安全 | 无 | 无 | 云端隔离 | 无 | 无 | Server级 |
| 跨框架 | 无 | 仅自家 | 封闭 | LangChain | LangChain | 协议标准化 |
| 版本管理 | 无 | Semantic | 版本控制 | PyPI | PyPI | 协议 |

### 4.3 Claude Skills 亮点

- Frontmatter + Markdown 结构化格式
- 变量类型支持 select/text/number
- 简洁的 slash command 触发机制
- 分类标签便于发现管理

### 4.4 LangChain Tools 亮点

- Decorator 模式简洁定义 Tool
- 类型注解自动生成 JSON Schema
- Docstring 自动提取描述
- StructuredTool 支持复杂输入输出

### 4.5 MCP 协议亮点

- 标准化 JSON Schema 工具描述
- stdio/http/sse 多协议支持
- /tools/list 端点工具发现
- 工具可主动回调 LLM

---

## 痛点 TOP 10

| 排名 | 痛点 | 严重性 | 影响范围 |
|-----|------|--------|---------|
| 1 | 无标准 SKILL.md 格式 | 严重 | 生态兼容性 |
| 2 | Skill 发现机制缺失 | 严重 | 开发者体验 |
| 3 | 无 MCP 协议兼容 | 严重 | 跨框架能力 |
| 4 | Plugin 发现机制缺失 | 严重 | 扩展性 |
| 5 | 无 Skill 沙箱执行 | 严重 | 安全性 |
| 6 | 无 Skill 组合/编排 | 中等 | 功能复用 |
| 7 | SkillUsageTracker 未完成 | 中等 | 优化能力 |
| 8 | 无 Skill 版本管理 | 中等 | 升级回滚 |
| 9 | Plugin 热加载缺失 | 轻微 | 运维体验 |
| 10 | Skill 市场机制缺失 | 轻微 | 生态建设 |

---

## 改造方案

### 方案 1: 统一 SKILL.md 描述格式 (P0)

- 优先级: P0 (Critical)
- 工作量: 3 人天
- 破坏兼容: 部分兼容
- 预期收益: 生态可移植性 +80%

### 方案 2: Skill 动态发现机制 (P0)

- 优先级: P0 (Critical)
- 工作量: 5 人天
- 破坏兼容: 向后兼容
- 预期收益: 开发者体验 +70%

### 方案 3: MCP 协议兼容层 (P0)

- 优先级: P0 (Critical)
- 工作量: 8 人天
- 破坏兼容: 向后兼容
- 预期收益: 跨框架互操作性 +90%

### 方案 4: Skill 沙箱执行引擎 (P1)

- 优先级: P1 (High)
- 工作量: 6 人天
- 破坏兼容: 向后兼容
- 预期收益: 安全性 +100%

### 方案 5: Skill 组合与编排 (P1)

- 优先级: P1 (High)
- 工作量: 7 人天
- 破坏兼容: 向后兼容
- 预期收益: 功能复用 +60%

### 方案 6: Plugin 文件系统发现 (P1)

- 优先级: P1 (High)
- 工作量: 4 人天
- 破坏兼容: 向后兼容
- 预期收益: 扩展性 +50%

### 方案 7: Skill 版本管理与分发 (P2)

- 优先级: P2 (Medium)
- 工作量: 5 人天
- 破坏兼容: 向后兼容
- 预期收益: 运维体验 +40%

### 方案 8: 使用追踪与优化 (P2)

- 优先级: P2 (Medium)
- 工作量: 3 人天
- 破坏兼容: 向后兼容
- 预期收益: 数据驱动优化 +30%

---

## 推荐落地路径

### 阶段 1: 基础标准化 (1-2 周)

目标: 建立 Skill 描述标准，兼容 Claude Skills 生态

任务:
- [P0] 实现 SKILL.md 解析器 (3d)
- [P0] 实现 Skill 文件系统发现 (3d)
- [P0] 迁移现有内置 Skill 到 SKILL.md (2d)

产出: docs/SKILL_SPEC.md, agentteam/skill/parser.py, agentteam/skill/discovery.py

### 阶段 2: 协议兼容 (2-3 周)

目标: 支持 MCP 协议，实现跨框架互操作

任务:
- [P0] 实现 MCP Client SDK (5d)
- [P0] 实现 MCP Server Adapter (5d)
- [P1] AgentTeam Skill -> MCP Server (3d)

产出: agentteam/mcp/client.py, agentteam/mcp/server.py, docs/MCP_INTEGRATION.md

### 阶段 3: 安全与编排 (2-3 周)

目标: 完善沙箱安全和 Skill 组合能力

任务:
- [P1] 实现 SandboxedSkillExecutor (6d)
- [P1] 实现 SkillOrchestrator (7d)
- [P1] Plugin 文件系统发现 (4d)

产出: agentteam/skill/sandbox.py, agentteam/skill/orchestrator.py

### 阶段 4: 生态完善 (2 周)

目标: 版本管理、使用追踪、市场分发

任务:
- [P2] Skill 版本管理 (5d)
- [P2] 使用追踪系统 (3d)
- [P2] 基础市场 API (4d)

---

## 附录：SKILL.md 格式规范

```markdown
---
name: code-review
description: 专业的代码审查技能
category: development
slash_command: code-review
version: 1.0.0
author: AgentTeam
tags: [code, review, security, quality]

variables:
  - name: focus_area
    type: select
    options: [security, performance, maintainability]
    default: security

required_mcps:
  - github
  - filesystem
---

# 代码审查技能

请对以下代码进行审查：
**审查范围**: {{focus_area}}

{{user_input}}
```

---

## 参考资料

1. Claude Skills 官方文档
2. LangChain Tools 文档
3. MCP 协议规范
4. CrewAI Tools 文档
5. OpenAI GPTs Actions

---

*报告生成时间: 2026-06-04*
*审计工具: AgentTeam Internal*
