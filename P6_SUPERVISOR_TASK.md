# P6 任务：Supervisor 模式（AI 自主编排）

> **执行者**: spai
> **审核者**: 楚灵
> **工作目录**: `C:\Users\31683\.openclaw\workspace\ClawTeam-OpenClaw`
> **优先级**: 🔴 高
> **预计工作量**: 5-7 天

---

## 目标

实现 Supervisor 引擎，让 ClawTeam 支持 AI 自主任务编排：输入一个高级目标 → 自动分解为子任务 → 按 DAG 依赖并行/串行执行 → 结果自动验证 → 失败自动重试。

---

## 参考实现（SpectrAI 已完成的 TS 版）

SpectrAI 项目（`C:\Users\31683\Downloads\SpectrAI-main`）已完整实现 Supervisor 模式。
以下为关键源码路径，**仔细阅读后按 Python 版本重写**：

| 模块 | SpectrAI 源码 | 说明 |
|------|-------------|------|
| Supervisor Prompt 构建 | `src/main/agent/supervisorPrompt.ts` | **核心参考**：任务分解引导、oneShot 模式、Provider 选择策略、开发任务生命周期 |
| Agent 管理引擎 | `src/main/agent/AgentManagerV2.ts` | spawn/wait/cancel/list 等完整生命周期管理、事件监听、idle 等待 |
| 会话管理（跨会话） | `src/main/session/SessionManagerV2.ts` | 会话创建/销毁、消息发送、状态机、Provider 适配 |
| Provider 适配器 | `src/main/adapter/AdapterRegistry.ts` | 注册表模式 + 5 种 Provider Adapter |
| 文件改动追踪 | `src/main/tracker/FileChangeTracker.ts` | FS Watch + 会话归因（P8 相关） |
| Git Worktree 服务 | `src/main/git/GitWorktreeService.ts` | Worktree 创建/合并/清理（P10 相关） |

### 必须理解的核心概念（从 `supervisorPrompt.ts` 提炼）

**1. 两层结构**
- 感知层：告知 AI 运行在多会话环境中，可查询其他会话
- 调度层：赋予创建/管理子 Agent 的能力（spawn_agent, wait_agent_idle 等）

**2. 两种模式**
- **oneShot（默认）**：任务完成后自动退出，适合代码分析、修 bug、写测试等单次任务
- **交互式（oneShot=false）**：保持存活，支持 send_to_agent 追加指令，适合多轮反馈

**3. 开发任务生命周期（Supervisor 思维框架）**
```
理解 → 拆分 → 实现 → 验证 → 交付
```
- 先读代码理解再 spawn，不要急着拆
- 无依赖任务并行，有依赖串行
- 子任务 prompt 必须包含：背景、目标、约束、验收标准
- 验证不要只听 Agent 汇报，要看实际 diff、跑构建、跑测试
- 发现问题 → send_to_agent 让同一个 Agent 修，不要另起

**4. Provider 选择策略**
- 复杂架构/多文件重构 → 最强推理模型
- 写代码/修 bug → 代码生成专长模型
- 大文件分析/代码审查 → 大上下文窗口模型
- 额度不足自动切换，不要在同一失败 provider 上重试

---

## 需要新建的文件

### 1. `clawteam/orchestrator/__init__.py`
空文件，包初始化。

### 2. `clawteam/orchestrator/supervisor.py` — Supervisor 核心引擎

实现以下类（参考 SpectrAI 的 `AgentManagerV2.ts` + `supervisorPrompt.ts`）：

```python
class SubTask(BaseModel):
    task_id: str
    description: str
    depends_on: list[str] = Field(default_factory=list)
    assigned_agent: str = ""
    provider: str = ""
    one_shot: bool = True
    status: str = "pending"  # pending, running, completed, failed, cancelled
    result: str = ""
    retries: int = 0
    max_retries: int = 2

class TaskPlan(BaseModel):
    plan_id: str
    goal: str
    subtasks: list[SubTask] = Field(default_factory=list)
    status: str = "planning"  # planning, executing, completed, failed

class SupervisorEngine:
    def plan(self, goal: str, team_name: str) -> TaskPlan:
        """LLM 驱动的任务分解：goal → subtasks + DAG
        参考 supervisorPrompt.ts 中的 buildSupervisorPrompt() 和任务生命周期框架。
        """

    def execute(self, plan: TaskPlan, team_name: str) -> dict:
        """按 DAG 顺序执行：拓扑排序 → 无依赖并行 spawn → 有依赖串行等待
        参考 AgentManagerV2.ts 的 spawnAgent / waitAgentIdle / waitAgent 模式。
        """

    def verify(self, task: SubTask, result: str) -> dict:
        """验证子任务结果是否达标（LLM 判断 result 是否符合 description 预期）
        参考 SpectrAI 的验证原则：不要只听 Agent 汇报，要看实际输出。
        """

    def retry(self, task: SubTask) -> SubTask:
        """失败自动重试，最多 max_retries 次"""
```

**核心设计要点（直接翻译 SpectrAI 的思路）**：

1. **plan() 的 LLM prompt**：参考 `supervisorPrompt.ts` 中的"开发任务生命周期"部分
   - 先理解，再拆分
   - 无依赖的并行，有依赖的串行
   - 每个子任务必须包含完整上下文
   - 粒度判断：一个文件的改动不值得 spawn，跨模块的才值得

2. **execute() 的执行逻辑**：参考 `AgentManagerV2.ts` 的事件监听模式
   - 使用现有的 sessions_spawn 机制创建子任务
   - 用 wait_agent_idle 等待完成（turn_complete 事件）
   - oneShot=true 时任务完成后自动清理
   - 并发控制：无依赖的子任务可以并行 spawn

3. **verify() 的验证标准**：
   - result 非空
   - 用 LLM 判断 result 是否符合 task.description 的预期
   - 验证失败时返回 failed 并记录原因

4. **状态管理**：参考 `AgentManagerV2.ts` 的状态机
   - pending → running → completed/failed
   - 失败时 retries++，< max_retries 则自动 retry
   - 所有状态变更通过事件通知

### 3. `clawteam/cli_supervisor.py` — CLI 命令入口

实现以下命令（参考 SpectrAI 的 IPC handler 中 `spawn_agent` / `wait_agent` / `list_agents` / `cancel_agent`）：
```bash
clawteam supervisor start "实现 Redis 集群支持" --team default
clawteam supervisor status <plan_id>
clawteam supervisor tasks <plan_id>
clawteam supervisor cancel <plan_id>
```

---

## 需要修改的文件

### `clawteam/__init__.py`
导出 SupervisorEngine, SubTask, TaskPlan

### `setup.py` 或 `pyproject.toml`
确保 `clawteam.orchestrator` 包被包含

---

## 技术约束

- Python 3.10+，pydantic v2，type hints
- **无破坏性变更**（向后兼容，现有功能不坏）
- PEP 8 + ruff 格式化
- 使用现有 Transport/Store 抽象（P3-P4 已完成），不要绕过
- 使用现有 DAG 引擎（P2 已完成 `clawteam/team/dag.py`），不要重写
- LLM 调用使用 `bailian/qwen3.6-plus`（API Key 已有）
- 子任务执行使用 OpenClaw 现有的 sessions_spawn 机制

---

## 验收标准（必须全部满足）

- [ ] `SubTask` 和 `TaskPlan` Pydantic 模型正确定义
- [ ] `SupervisorEngine.plan()` 能输入 goal 输出带依赖关系的 SubTask 列表
- [ ] `SupervisorEngine.execute()` 按 DAG 顺序执行，无依赖并行，有依赖串行
- [ ] `SupervisorEngine.verify()` 验证结果，不达标返回 failed
- [ ] `SupervisorEngine.retry()` 失败自动重试，最多 2 次
- [ ] CLI 四个命令可用：start/status/tasks/cancel
- [ ] **20 个测试用例全部通过**
- [ ] `python -m pytest tests/ -v` 全绿（包含已有 696 个测试）
- [ ] 无破坏性变更

---

## 测试文件

新建 `tests/test_supervisor.py`，覆盖：
1. SubTask 模型创建和验证
2. TaskPlan 模型创建和验证
3. SupervisorEngine.plan() 返回有效 SubTask 列表
4. plan() 分解结果包含 depends_on
5. plan() 分解 3-5 个子任务
6. execute() 按拓扑顺序执行
7. execute() 并行执行无依赖任务
8. execute() 串行执行有依赖任务
9. execute() 更新任务状态
10. verify() 验证通过返回 success
11. verify() 验证失败返回 failed
12. retry() 重试次数限制
13. retry() 重试后状态更新
14. CLI start 命令
15. CLI status 命令
16. CLI tasks 命令
17. CLI cancel 命令
18. 向后兼容（现有测试不坏）
19. DAG 集成（复用 team/dag.py）
20. Transport 集成（复用 transport/base.py）

---

## 完成后

1. 运行 `python -m pytest tests/ -v` 确认全绿
2. `git add -A && git commit -m "feat: P6 Supervisor mode"`
3. 通知楚灵审核

---

_任务文档，2026-04-29 创建，2026-04-29 更新（增加 SpectrAI 参考）_
