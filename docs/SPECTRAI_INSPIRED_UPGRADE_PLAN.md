# ClawTeam × SpectrAI 升级计划

> **基于 SpectrAI 源码分析**  
> **生成时间**：2026-04-27  
> **当前状态**：P0-P5 全部完成，100% 测试通过  
> **目标**：吸收 SpectrAI 核心思想，补齐 ClawTeam 在 AI 自主编排方面的能力差距

---

## 差距总览

| 能力维度 | SpectrAI | ClawTeam（当前） | 差距等级 |
|---------|----------|-----------------|---------|
| Supervisor 模式 | ✅ AI 自动分解任务+spawn 子 Agent | ❌ 无 | 🔴 大 |
| 跨会话感知 | ✅ AI 能看到其他会话状态 | ❌ 无 | 🔴 大 |
| 文件改动追踪 | ✅ FS Watch+归因+diff | ❌ 无 | 🟡 中 |
| Provider 自适应 | ✅ 额度不足自动切换 | ❌ 无 | 🟡 中 |
| Git Worktree 管理 | ✅ 自动创建/合并/清理 | ❌ 无 | 🟢 小 |
| Token 统计 | ✅ 仪表盘+趋势图 | ❌ 无 | 🟢 小 |

---

## P6: Supervisor 模式（AI 自主编排）

**优先级**：🔴 高  
**预计工作量**：5-7 天  
**参考源码**：`SpectrAI/src/main/agent/supervisorPrompt.ts`

### 核心思想

让一个 Agent（Supervisor）自动分解任务、spawn 子 Agent、分配 Provider、跟踪进度、验证结果。

### 实现方案

#### 1. Supervisor 引擎（`clawteam/orchestrator/supervisor.py`）

```python
class SupervisorEngine:
    """Supervisor 引擎 — AI 自主任务编排"""
    
    def plan(self, goal: str) -> TaskPlan:
        """LLM 驱动的任务分解"""
        # 1. 分析目标，识别子任务
        # 2. 分析依赖关系，构建 DAG
        # 3. 为每个子任务推荐最佳 Provider
        # 4. 输出执行计划
        
    def execute(self, plan: TaskPlan) -> ExecutionResult:
        """执行计划"""
        # 1. 按 DAG 顺序 spawn 子 Agent
        # 2. 并行执行无依赖任务
        # 3. 等待完成，收集结果
        # 4. 验证结果质量
        
    def verify(self, task: Task, result: str) -> VerificationResult:
        """验证子任务结果"""
        # 1. 检查输出是否完整
        # 2. 运行测试/构建验证
        # 3. 不通过则重新分配或标记失败
```

#### 2. Provider 选择器（`clawteam/orchestrator/provider_selector.py`）

```python
class ProviderSelector:
    """智能 Provider 选择 + 自动 fallback"""
    
    def select(self, task: Task) -> str:
        """根据任务类型选择最佳 Provider"""
        # 规则：
        # - 架构设计 → claude（推理强）
        # - 代码生成 → codex（代码专长）
        # - 大文件分析 → gemini（上下文大）
        # - 文档总结 → gemini（长文本强）
        # - 多模型切换 → opencode
        
    def fallback(self, failed_provider: str) -> str:
        """额度不足时自动切换"""
        # fallback 链：claude → gemini → codex → opencode
```

#### 3. Supervisor CLI（`clawteam/cli/supervisor.py`）

```bash
# 启动 Supervisor 模式
clawteam supervisor start "实现 Redis 集群支持" --team 奶龙队

# 查看进度
clawteam supervisor status <plan_id>

# 查看子任务
clawteam supervisor tasks <plan_id>

# 终止计划
clawteam supervisor cancel <plan_id>
```

#### 4. 与现有系统集成

- **DAG 引擎**：复用 `dag.py` 的拓扑排序
- **角色系统**：复用 `roles.py` 的角色定义
- **路由系统**：复用 `router.py` 的分配算法
- **消息总线**：复用 `TeamBus` 实现跨 Agent 通信

### 验收标准

- [ ] 输入一个高级目标，Supervisor 自动分解为 3-5 个子任务
- [ ] 子任务按依赖关系并行/串行执行
- [ ] Provider 选择准确率 > 80%
- [ ] 额度不足时自动 fallback，成功率 > 90%
- [ ] 执行结果自动验证，不通过自动重试
- [ ] 20 个测试用例通过

---

## P7: 跨会话感知

**优先级**：🔴 高  
**预计工作量**：3-4 天  
**参考源码**：`SpectrAI/src/main/agent/supervisorPrompt.ts`（感知层）

### 核心思想

让每个 Agent 知道其他 Agent 在做什么，实现跨会话协作，避免冲突和重复。

### 实现方案

#### 1. 会话注册中心（`clawteam/session/registry.py`）

```python
class SessionRegistry:
    """会话注册中心 — 所有 Agent 可查询"""
    
    def register(self, session: AgentSession):
        """注册会话"""
        
    def unregister(self, session_id: str):
        """注销会话"""
        
    def list_sessions(self, status: str = None) -> list[AgentSession]:
        """查询会话列表"""
        
    def get_session_summary(self, session_id: str) -> SessionSummary:
        """获取会话摘要（当前任务、修改的文件、执行的命令）"""
        
    def search_sessions(self, query: str) -> list[SessionActivity]:
        """按关键词搜索会话活动"""
```

#### 2. 跨会话通信（`clawteam/team/cross_session.py`）

```python
class CrossSessionBus:
    """跨会话消息总线"""
    
    def broadcast(self, sender_id: str, message: str, target_role: str = None):
        """广播或单播消息"""
        
    def notify_completion(self, session_id: str, result: str):
        """通知任务完成"""
        
    def notify_conflict(self, session_id: str, conflict_info: dict):
        """通知文件冲突"""
```

#### 3. CLI 命令（`clawteam/cli/session.py`）

```bash
# 查看所有会话
clawteam session list

# 查看会话详情
clawteam session info <session_id>

# 搜索会话活动
clawteam session search "修改了 config.py"

# 查看冲突
clawteam session conflicts
```

### 验收标准

- [ ] Agent 可以查询其他会话的状态和进度
- [ ] 任务完成时自动通知相关 Agent
- [ ] 文件冲突时自动检测并告警
- [ ] 15 个测试用例通过

---

## P8: 文件改动追踪

**优先级**：🟡 中  
**预计工作量**：3-4 天  
**参考源码**：`SpectrAI/src/main/tracker/FileChangeTracker.ts`

### 核心思想

通过 FS Watch 实时追踪 AI 会话改动了哪些文件，归因到具体 Agent，支持 diff 预览。

### 实现方案

#### 1. 文件追踪器（`clawteam/tracker/file_tracker.py`）

```python
class FileChangeTracker:
    """文件改动追踪器"""
    
    def start_watching(self, session_id: str, work_dir: str):
        """开始监听目录"""
        
    def stop_watching(self, session_id: str):
        """停止监听"""
        
    def get_changes(self, session_id: str) -> list[FileChange]:
        """获取会话的文件改动列表"""
        
    def get_diff(self, file_path: str) -> str:
        """获取文件 diff"""
        
    def attribute_changes(self) -> dict[str, list[str]]:
        """归因：哪个 Agent 改了哪些文件"""
```

#### 2. Web UI 集成（`clawteam/board/static/file-viewer.html`）

- 文件树视图（带改动标记）
- 会话改动列表（创建/修改/删除分类）
- 代码查看器（语法高亮 + diff 对比）

#### 3. CLI 命令（`clawteam/cli/tracker.py`）

```bash
# 查看会话改动
clawteam changes list <session_id>

# 查看文件 diff
clawteam changes diff <file_path>

# 查看归因
clawteam changes attribution
```

### 验收标准

- [ ] 实时追踪文件创建/修改/删除（< 500ms 延迟）
- [ ] 多会话改动正确归因
- [ ] 竞态冲突自动标记
- [ ] Web UI 显示改动文件列表和 diff
- [ ] 15 个测试用例通过

---

## P9: Provider 自适应

**优先级**：🟡 中  
**预计工作量**：2-3 天

### 核心思想

根据任务类型自动选择最佳 Provider，额度不足时自动 fallback。

### 实现方案

#### 1. Provider 路由（`clawteam/provider/router.py`）

```python
class ProviderRouter:
    """Provider 路由器"""
    
    def route(self, task: Task) -> str:
        """根据任务类型选择 Provider"""
        # 规则引擎：
        # - 架构设计/复杂推理 → claude
        # - 代码生成/修 bug → codex
        # - 大文件分析/长文本 → gemini
        # - 多模型切换 → opencode
        
    def fallback(self, provider: str, error: str) -> str:
        """额度不足时 fallback"""
        # fallback 链配置化
        
    def record_usage(self, provider: str, tokens: int):
        """记录用量，触发限额告警"""
```

#### 2. 配置（`clawteam/provider/config.yaml`）

```yaml
providers:
  claude:
    command: claude
    strengths: [architecture, reasoning, complex-tasks]
    fallback_to: [gemini, codex]
    rate_limit: 1000/min
    
  gemini:
    command: gemini
    strengths: [large-files, documentation, long-context]
    fallback_to: [codex, claude]
    
  codex:
    command: codex
    strengths: [code-generation, bug-fix, testing]
    fallback_to: [gemini, claude]
```

### 验收标准

- [ ] 任务类型 → Provider 匹配准确率 > 80%
- [ ] 额度不足自动 fallback 成功率 > 90%
- [ ] 用量统计正确
- [ ] 10 个测试用例通过

---

## P10: Git Worktree 自动管理

**优先级**：🟢 低  
**预计工作量**：2-3 天  
**参考源码**：`SpectrAI/src/main/git/GitWorktreeService.ts`

### 核心思想

为每个子任务自动创建隔离的 Git Worktree，完成后自动合并和清理。

### 实现方案

#### 1. Worktree 服务（`clawteam/git/worktree.py`）

```python
class WorktreeService:
    """Git Worktree 自动管理"""
    
    def create(self, task_id: str, base_branch: str = None) -> str:
        """创建隔离 worktree"""
        
    def merge(self, task_id: str, squash: bool = True) -> MergeResult:
        """合并回主分支（先检查冲突）"""
        
    def cleanup(self, task_id: str):
        """清理 worktree 和分支"""
        
    def check_conflicts(self, task_id: str) -> ConflictResult:
        """检查合并冲突"""
```

### 验收标准

- [ ] 自动创建 worktree（无冲突）
- [ ] 合并前冲突检测
- [ ] 完成后自动清理
- [ ] 10 个测试用例通过

---

## P11: Token 统计仪表盘

**优先级**：🟢 低  
**预计工作量**：1-2 天

### 核心思想

统计每个会话/Agent 的 Token 用量，提供可视化仪表盘。

### 实现方案

#### 1. 用量仓库（`clawteam/storage/usage_repository.py`）

```python
class UsageRepository:
    """Token 用量统计"""
    
    def record(self, session_id: str, tokens: int, provider: str):
        """记录用量"""
        
    def get_today_usage(self) -> UsageSummary:
        """今日用量"""
        
    def get_trend(self, days: int = 30) -> list[DailyUsage]:
        """30 天趋势"""
        
    def get_session_distribution(self) -> dict[str, int]:
        """各会话 Token 分布"""
```

#### 2. Web UI 集成

- 用量统计卡片（今日/累计）
- 30 天趋势图（柱状图）
- 会话分布饼图

### 验收标准

- [ ] 用量记录准确
- [ ] Web UI 显示统计图表
- [ ] 5 个测试用例通过

---

## 执行顺序建议

| 阶段 | 内容 | 时间 | 依赖 |
|------|------|------|------|
| **P6** | Supervisor 模式 | 5-7 天 | 无（复用 DAG+Roles） |
| **P7** | 跨会话感知 | 3-4 天 | P6（共享会话注册中心） |
| **P8** | 文件改动追踪 | 3-4 天 | 无 |
| **P9** | Provider 自适应 | 2-3 天 | 无 |
| **P10** | Git Worktree 管理 | 2-3 天 | 无 |
| **P11** | Token 统计 | 1-2 天 | 无 |

**总计**：约 16-23 天

---

## 并行建议

**人员 A**：P6（Supervisor）+ P7（跨会话感知）  
**人员 B**：P8（文件追踪）+ P9（Provider 自适应）+ P10（Worktree）+ P11（Token 统计）

P6/P7 有依赖关系，建议串行。P8-P11 互相独立，可并行。

---

## 技术要点（来自 SpectrAI 源码）

### 1. Supervisor Prompt 注入

SpectrAI 通过写入 `.claude/rules/spectrai-session.md` 让 AI 自动加载 Supervisor 能力。ClawTeam 可采用类似机制，通过系统提示注入编排指令。

### 2. 确定性就绪检测

SpectrAI 用 `turn_complete` 事件而非超时推断来判断 Agent 就绪。ClawTeam 应复用此模式，避免竞态问题。

### 3. 文件操作规范

SpectrAI 强制 AI 使用 MCP 文件操作工具（而非 CLI 内置工具），以便精确追踪改动。ClawTeam 可借鉴此思想，定义统一文件操作接口。

### 4. Worktree 合并流程

SpectrAI 的 worktree 合并流程：`check_merge → merge → cleanup`，合并前一定先检查冲突。ClawTeam 应遵循相同模式。

### 5. Provider 选择策略

SpectrAI 的 Supervisor Prompt 明确指导 AI 根据任务类型选择 Provider，而非总是用默认的 claude-code。ClawTeam 应内置类似的路由规则。

---

_基于 SpectrAI v0.4.6 源码分析_  
_ClawTeam 当前版本：P0-P5 全部完成_
