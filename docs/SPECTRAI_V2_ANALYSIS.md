# SpectrAI 深度源码分析报告

## 执行摘要

通过深入分析 SpectrAI v0.4.6 源码，识别出多个 ClawTeam 可以借鉴的关键架构模块。SpectrAI 基于 Electron + TypeScript 构建，采用 MCP (Model Context Protocol) 架构，提供了完整的 AI 会话编排平台。发现 8 个 ClawTeam 尚未实现的关键能力，包括数据库/Repository 层、任务会话协调器、MCP/Skill 注册系统等。

## 1. SpectrAI 核心架构分析

### 1.1 技术栈
- **前端**：Electron + React + TypeScript
- **后端**：Node.js + TypeScript + Better-SQLite3
- **通信**：MCP (Model Context Protocol) + IPC
- **数据库**：SQLite + Repository 模式 + 内存降级

### 1.2 主要目录结构

```
src/
├── main/                         # Electron 主进程
│   ├── agent/                    # AI Agent 管理
│   │   ├── AgentManager.ts       # Agent 管理器
│   │   ├── AgentManagerV2.ts     # Agent 管理器 v2
│   │   ├── AgentReadinessDetector.ts  # Agent 就绪检测器
│   │   ├── HeadlessTerminalBuffer.ts  # 无头终端缓冲区
│   │   ├── supervisorPrompt.ts   # Supervisor 提示词
│   │   └── types.ts
│   ├── adapter/                  # Provider 适配器
│   │   ├── ClaudeSdkAdapter.ts   # Claude SDK 适配器
│   │   ├── CodexAppServerAdapter.ts
│   │   ├── GeminiHeadlessAdapter.ts
│   │   ├── OpenCodeSdkAdapter.ts
│   │   └── types.ts
│   ├── storage/                  # 数据库层
│   │   ├── Database.ts           # 数据库管理器
│   │   ├── repositories/         # Repository 模式
│   │   │   ├── TaskRepository.ts
│   │   │   ├── SessionRepository.ts
│   │   │   ├── UsageRepository.ts
│   │   │   ├── SkillRepository.ts
│   │   │   └── McpRepository.ts
│   │   └── migrations/           # 数据库迁移
│   ├── task/                     # 任务管理
│   │   └── TaskSessionCoordinator.ts  # 任务-会话协调器
│   ├── skill/                    # 技能系统
│   │   ├── builtinSkills.ts      # 内置技能定义
│   │   └── SkillEngine.ts        # 技能引擎
│   ├── mcp/                      # MCP 系统
│   │   ├── builtinMcps.ts        # 内置 MCP 服务器定义
│   │   └── McpManager.ts         # MCP 管理器
│   ├── session/                  # 会话管理
│   │   ├── SessionManager.ts     # 会话管理器
│   │   ├── SessionManagerV2.ts
│   │   └── types.ts
│   └── ipc/                      # IPC 处理器
└── renderer/                     # Electron 渲染进程
    └── stores/sessionStore.ts    # 前端状态管理
```

## 2. 关键模块详细分析

### 2.1 Database + Repository 层

#### 2.1.1 DatabaseManager
```typescript
export class DatabaseManager {
  // SQLite 优先，支持内存降级
  constructor(dbPath: string)
  
  // 所有 Repository 实例
  private taskRepo: TaskRepository
  private sessionRepo: SessionRepository  
  private usageRepo: UsageRepository
  private skillRepo: SkillRepository
  private mcpRepo: McpRepository
  
  // 提供访问接口
  getTask(taskId: string): Task
  updateTask(taskId: string, updates: Partial<Task>): void
  getAllSessions(): Session[]
  // ... 其他方法
}
```

**关键特性**：
- ✅ SQLite 优先，无法加载时自动降级到内存存储
- ✅ WAL 模式支持高并发访问
- ✅ 外键约束保证数据完整性
- ✅ 内置数据预置（BUILTIN_MCPS, BUILTIN_SKILLS）

#### 2.1.2 Repository 模式
每个实体都有对应的 Repository：
- **TaskRepository**：任务 CRUD 操作
- **SessionRepository**：会话生命周期管理
- **UsageRepository**：用量统计和持久化
- **SkillRepository**：技能定义管理
- **McpRepository**：MCP 服务器管理

### 2.2 TaskSessionCoordinator

#### 2.2.1 核心功能
```typescript
export class TaskSessionCoordinator extends EventEmitter {
  // 会话状态 → 任务状态映射
  onSessionStatusChange(sessionId: string, status: SessionStatus): void
  
  // 活动事件 → 任务状态映射  
  onActivityEvent(sessionId: string, activityType: ActivityEventType): void
  
  // 防抖状态更新（1秒）
  private debouncedUpdate(): void
  
  // 多会话边界处理
  private handleSessionCompleted(): void
}
```

**状态映射规则**：
- `running/idle` → `in_progress`
- `waiting_input` → `waiting`
- `task_complete` → `done`
- `waiting_confirmation` → `waiting`

### 2.3 Skill 系统

#### 2.3.1 技能定义
```typescript
interface Skill {
  id: string
  name: string
  description: string
  slashCommand: string        // 例如 "code-review"
  type: 'prompt' | 'native' | 'orchestration'
  promptTemplate: string     // 支持 {{variable}} 模板
  inputVariables: InputVariable[]
  compatibleProviders: string // "all" 或逗号分隔列表
  // ...
}
```

#### 2.3.2 内置技能
SpectrAI 内置 8 个技能：
1. **code-review**：代码全面审查
2. **translate**：多语言翻译
3. **explain**：代码解释
4. **write-test**：单元测试生成
5. **write-doc**：文档生成
6. **refactor**：重构建议
7. **commit-msg**：提交信息生成
8. **debug**：调试分析

### 2.4 MCP (Model Context Protocol) 系统

#### 2.4.1 内置 MCP 服务器
```typescript
export const BUILTIN_MCPS: McpServer[] = [
  {
    id: 'mcp-filesystem',     // 文件系统
    command: 'npx',
    args: ['-y', '@modelcontextprotocol/server-filesystem', '.']
  },
  {
    id: 'mcp-git',           // Git 操作
    command: 'uvx',
    args: ['mcp-server-git', '--repository', '.']
  },
  {
    id: 'mcp-sqlite',        // SQLite 数据库
    command: 'uvx',
    args: ['mcp-server-sqlite']
  },
  {
    id: 'mcp-github',        // GitHub API
    command: 'npx',
    args: ['-y', '@modelcontextprotocol/server-github']
  },
  // ...
]
```

#### 2.4.2 MCP 管理器
- ✅ 服务器启动/停止管理
- ✅ 按需懒加载（30 分钟空闲自动关闭）
- ✅ 配置和环境变量管理
- ✅ 与 Provider 兼容性检查

### 2.5 Agent 就绪检测系统

#### 2.5.1 AgentReadinessDetector v5
```typescript
export class AgentReadinessDetector {
  // 三路径检测：
  // 1. Fast Path（事件驱动）：检测 prompt marker
  // 2. Slow Path（轮询兜底）：屏幕内容稳定阈值
  // 3. 结构化信号：notifyTaskComplete()
  
  onScreenUpdate(lastLines: string[], totalAppended: number): void
  waitReady(options: WaitReadyOptions): Promise<boolean>
  notifyTaskComplete(): void
}
```

**检测策略**：
- **CLI 启动检测**：使用 Fast Path + Quiescence
- **交互式模式**：仅使用 Quiescence（关闭 Fast Path 避免误判）
- **确定性信号**：通过 JSONL 解析器通知完成

### 2.6 OutputReaderManager

#### 2.6.1 多 Provider 输出读取
```typescript
export class OutputReaderManager {
  // 注册输出读取器
  registerReader(sessionId: string, reader: BaseOutputReader): void
  
  // 开始/停止监控
  startWatching(sessionId: string, options?: WatchOptions): void
  stopWatching(sessionId: string): void
  
  // 事件回调
  registerCallback(callback: (event: OutputEvent) => void): void
  emitEvent(event: OutputEvent): void
  
  // 会话 ID 检测
  onConversationIdDetected(sessionId: string, conversationId: string): void
}
```

**支持的读取器**：
- `ClaudeJsonlReader`：解析 Claude JSONL 格式
- `GenericRegexReader`：基于正则的通用解析
- `GeminiOutputReader`：Gemini 特定格式

## 3. ClawTeam 现状对比

### 3.1 已移植模块

| 模块 | ClawTeam 实现 | 状态 |
|------|---------------|------|
| **AgentReadinessDetector** | `clawteam/readiness/detector.py` | ✅ 完整实现 |
| **OutputReaderManager** | `clawteam/reader/manager.py` | ✅ 完整实现 |
| **StateInference** | `clawteam/parser/inference.py` | ✅ 完整实现 |
| **HeadlessTerminalBuffer** | `clawteam/spawn/terminal_buffer.py` | ✅ 完整实现 |
| **ConcurrencyGuard** | `clawteam/concurrency/guard.py` | ✅ 完整实现 |
| **SkillEngine** | `clawteam/skill/engine.py` | ✅ 完整实现 |
| **ConfirmationDetector** | `clawteam/parser/confirmation_detector.py` | ✅ 完整实现 |

### 3.2 缺失的关键模块

| 模块 | SpectrAI 位置 | ClawTeam 状态 | 优先级 |
|------|---------------|---------------|---------|
| **Database + Repository** | `src/main/storage/` | ❌ 部分实现（buggy） | 🔴 高 |
| **TaskSessionCoordinator** | `src/main/task/` | ❌ 未实现 | 🔴 高 |
| **MCP 注册系统** | `src/main/mcp/` | ❌ 未实现 | 🔴 高 |
| **Skill 注册系统** | `src/main/skill/builtinSkills.ts` | ❌ 未实现（硬编码） | 🟡 中 |
| **会话状态协调** | `src/main/session/` | ❌ 未实现 | 🟡 中 |
| **Provider 适配器** | `src/main/adapter/` | ❌ 未实现 | 🟢 低 |
| **IPC 处理器** | `src/main/ipc/` | ❌ 未实现 | 🟢 低 |

### 3.3 测试发现的问题

#### 3.3.1 数据库层问题
- **语法错误**：`manager.py` 第 223 行未闭合的括号
- **未完成实现**：部分 Repository 方法缺失
- **导入错误**：测试无法正常导入

#### 3.3.2 StateInference 测试失败
- **startup_stuck 检测逻辑错误**：测试期望返回 session 但实际为空
- **POSSIBLE_STUCK → STUCK 转换**：阈值计算有问题

#### 3.3.3 OutputReaderManager 测试失败
- **OutputEvent 构造函数**：缺少 `timestamp` 参数
- **类型定义不完整**：需要添加默认值

#### 3.3.4 HeadlessTerminalBuffer 测试失败
- **total_appended 计算错误**：预期 22，实际 23
- **换行符处理不一致**：Windows vs Unix

## 4. 新升级机会详细方案

### 4.1 数据库/Repository 层重构

**目标**：实现完整的 DatabaseManager + Repository 架构

**实施方案**：
1. 修复现有数据库代码（语法错误）
2. 实现完整的 Repository 基类
3. 添加内存降级策略
4. 集成到现有系统（替换 store 模块）

**验收标准**：
- ✅ 语法正确，测试通过
- ✅ SQLite 和内存模式都能工作
- ✅ 所有 CRUD 操作正常工作
- ✅ 集成到现有 session 和 task 系统

### 4.2 TaskSessionCoordinator 实现

**目标**：实现任务-会话状态自动联动

**实施方案**：
1. 创建 `clawteam/task/coordinator.py`
2. 实现状态映射规则
3. 添加防抖更新机制
4. 集成到 TeamBus 和 SessionManager

**验收标准**：
- ✅ 会话状态变化自动更新任务状态
- ✅ 活动事件自动触发状态更新
- ✅ 多会话边界正确处理
- ✅ 防抖机制避免频繁更新

### 4.3 MCP/Skill 注册系统

**目标**：实现 MCP 服务器和技能的可配置管理

**实施方案**：
1. 创建 MCP 服务器定义格式
2. 实现 MCP 管理器（启动/停止/监控）
3. 将硬编码技能迁移到数据库
4. 添加技能管理 CLI 命令

**验收标准**：
- ✅ MCP 服务器可配置、可启动
- ✅ 技能可以从数据库加载
- ✅ 支持技能热更新
- ✅ 与现有 SkillEngine 集成

### 4.4 会话状态协调系统

**目标**：实现 SpectrAI 风格的会话状态管理

**实施方案**：
1. 创建 `clawteam/session/coordinator.py`
2. 集成 TaskSessionCoordinator
3. 添加会话生命周期回调
4. 与 Board Web UI 集成

**验收标准**：
- ✅ 会话状态可持久化
- ✅ 状态变化触发相应事件
- ✅ 支持跨会话协调
- ✅ Web UI 实时显示状态

## 5. 优先级排序和实施路线图

### 5.1 优先级排序

| 优先级 | 模块 | 预计工作量 | 依赖 |
|--------|------|------------|------|
| **P1** | 数据库层修复 | 1-2 天 | 无 |
| **P2** | TaskSessionCoordinator | 2-3 天 | P1 |
| **P3** | MCP 注册系统 | 3-4 天 | P1 |
| **P4** | Skill 注册系统 | 2-3 天 | P1 |
| **P5** | 会话状态协调 | 2-3 天 | P2 |
| **P6** | Provider 适配器 | 3-5 天 | 无 |
| **P7** | IPC 处理器 | 2-3 天 | P2 |

### 5.2 实施路线图

**第 1 周**：
- 修复数据库层所有 bug
- 完成 TaskSessionCoordinator 实现
- 集成到现有系统

**第 2 周**：
- 实现 MCP 注册系统
- 将技能迁移到数据库
- 添加技能管理 CLI

**第 3 周**：
- 实现会话状态协调
- 集成 Board Web UI
- 完善测试覆盖

**第 4 周**：
- 实现 Provider 适配器框架
- 添加 IPC 通信层
- 性能优化和文档完善

### 5.3 风险评估

#### 高风险：
- **数据库迁移**：可能影响现有数据
- **架构变更**：可能需要重构现有代码

#### 中风险：
- **测试覆盖不足**：新模块可能引入 bug
- **性能影响**：增加的抽象层可能降低性能

#### 低风险：
- **向后兼容**：保持现有 API 不变
- **功能缺失**：可逐步添加功能

#### 缓解措施：
1. **分阶段实施**：小步快跑，频繁验证
2. **单元测试先行**：先写测试，再实现
3. **回滚计划**：保留原有实现作为备选
4. **性能基准**：添加性能监控和告警

## 6. 与历史升级计划对比

### 6.1 已完成升级（P0-P5）
- ✅ P0：基础架构（已完成）
- ✅ P1：Agent + 解析器（已完成）
- ✅ P2：DAG 引擎 + 角色系统（已完成）
- ✅ P3：Transport + Store 抽象（已完成）
- ✅ P4：Redis Transport（已完成）
- ✅ P5：Web UI 看板（已完成）

### 6.2 SpectrAI 启发的升级（P6-P11）
基于 `SPECTRAI_INSPIRED_UPGRADE_PLAN.md` 分析：

**已实现**：
- P6 Supervisor 模式：部分实现（`orchestrator/` 目录）
- P8 文件改动追踪：已实现（`tracker/` 目录）
- P10 Git Worktree 管理：部分实现（`workspace/` 目录）
- P11 Token 统计增强：已实现（`tracker/token_stats.py`）

**新增发现**：
- **Database/Repository 层**：核心缺失，需要优先实现
- **TaskSessionCoordinator**：关键状态协调机制
- **MCP 注册系统**：SpectrAI 的核心扩展能力
- **Skill 注册系统**：技能可配置化管理

### 6.3 推荐整合方案

将新增发现与原有 P6-P11 整合：

1. **数据库层**作为基础，支撑所有其他模块
2. **TaskSessionCoordinator**作为状态协调核心
3. **MCP/Skill 注册**作为扩展能力
4. **P6 Supervisor**在此之上构建
5. **P7 跨会话感知**利用数据库和协调器

## 7. 测试覆盖率统计和质量评估

### 7.1 当前测试状态

**AgentReadinessDetector**：✅ 11/11 通过  
**StateInference**：⚠️ 21/23 通过（2个失败）  
**HeadlessTerminalBuffer**：⚠️ 19/20 通过（1个失败）  
**OutputReaderManager**：⚠️ 14/17 通过（3个失败）  
**Database 层**：❌ 无法运行（语法错误）

### 7.2 质量评估

**整体质量**：7/10  
**优点**：架构设计合理，代码结构清晰  
**缺点**：测试覆盖不足，边缘情况处理不够  
**改进方向**：增加单元测试，修复已知 bug

### 7.3 测试策略建议

1. **数据库测试**：修复语法错误后编写完整测试
2. **集成测试**：测试模块间协作
3. **性能测试**：检测资源使用和响应时间
4. **边界测试**：测试异常情况和极端输入

## 8. 结论和建议

### 8.1 核心结论

1. **SpectrAI 架构优势**：完善的 Repository 模式、MCP 扩展、状态协调机制
2. **ClawTeam 当前差距**：数据库层不完整，缺少任务协调和可配置化
3. **最大升级机会**：Database/Repository + TaskSessionCoordinator + MCP/Skill 注册

### 8.2 短期行动建议

1. **立即修复**：数据库语法错误和测试失败
2. **优先实现**：TaskSessionCoordinator 状态协调
3. **逐步迁移**：将硬编码技能迁移到数据库
4. **测试完善**：补全所有模块的单元测试

### 8.3 长期架构方向

1. **向 MCP 架构靠拢**：实现可插拔的工具扩展
2. **强化状态管理**：统一的任务-会话状态协调
3. **完善可配置化**：所有模块都可配置、可扩展
4. **提升用户体验**：通过 Web UI 提供更好监控和管理

### 8.4 风险提示

⚠️ **数据库迁移风险**：可能影响现有数据，需谨慎操作  
⚠️ **架构变更风险**：需要保持向后兼容性  
✅ **技术可行性**：所有方案都有成熟参考实现  
✅ **团队能力**：已有相关模块实现经验

---

**分析完成时间**：2026-04-27  
**分析人员**：后端工程师2号  
**参考版本**：SpectrAI v0.4.6  
**目标版本**：ClawTeam V2