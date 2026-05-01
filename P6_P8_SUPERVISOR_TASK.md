# P6-P8 联合任务：Supervisor + 跨会话感知 + 文件改动追踪

> **执行者**: spai
> **审核者**: 楚灵
> **工作目录**: `C:\Users\31683\.openclaw\workspace\ClawTeam-OpenClaw`
> **优先级**: 🔴 高
> **预计工作量**: 10-14 天

---

## 总体目标

一次性实现三个 Phase，让 ClawTeam 从"手动分配任务"升级到"AI 自主编排 + 跨会话协作 + 改动自动追踪"。

| Phase | 名称 | 一句话描述 |
|-------|------|-----------|
| **P6** | Supervisor 模式 | 输入高级目标 → 自动分解子任务 → DAG 并行/串行执行 → 结果验证 → 失败重试 |
| **P7** | 跨会话感知 | 子 Agent 能查看其他会话状态、搜索结果、获取摘要，实现协作 |
| **P8** | 文件改动追踪 | 自动追踪每个 Agent 改了哪些文件，输出改动报告 |

---

## 参考实现（SpectrAI）

SpectrAI（`C:\Users\31683\Downloads\SpectrAI-main`）已完整实现这三个 Phase，全部为 TypeScript。
**仔细阅读源码 → 理解设计 → 用 Python 重写。**

| Phase | SpectrAI 核心源码 | 关键概念 |
|-------|-----------------|---------|
| **P6** | `src/main/agent/supervisorPrompt.ts`<br>`src/main/agent/AgentManagerV2.ts` | 两层结构（感知+调度）、oneShot/交互模式、开发任务生命周期、Provider 选择策略 |
| **P7** | `src/main/session/SessionManagerV2.ts`<br>`src/main/agent/supervisorPrompt.ts` (感知层) | 跨会话列表、会话摘要、关键词搜索、会话间状态感知 |
| **P8** | `src/main/tracker/FileChangeTracker.ts` | FS Watch + 会话归因、多会话竞争决策、worktree 追踪、去抖缓冲 |

---

# ═══════════════════════════════════════════
# P6: Supervisor 模式
# ═══════════════════════════════════════════

## 新建文件

### `clawteam/orchestrator/__init__.py`
空文件。

### `clawteam/orchestrator/supervisor.py`

```python
class SubTask(BaseModel):
    task_id: str
    description: str
    depends_on: list[str] = Field(default_factory=list)
    assigned_agent: str = ""
    one_shot: bool = True
    status: str = "pending"
    result: str = ""
    retries: int = 0
    max_retries: int = 2

class TaskPlan(BaseModel):
    plan_id: str
    goal: str
    subtasks: list[SubTask] = Field(default_factory=list)
    status: str = "planning"

class SupervisorEngine:
    def plan(self, goal: str, team_name: str) -> TaskPlan: ...
    def execute(self, plan: TaskPlan, team_name: str) -> dict: ...
    def verify(self, task: SubTask, result: str) -> dict: ...
    def retry(self, task: SubTask) -> SubTask: ...
```

**参考 `supervisorPrompt.ts` 的核心设计**：

1. **plan() — LLM 任务分解**
   - 用 `bailian/qwen3.6-plus` 把 goal 分解为 3-5 个 SubTask
   - 每个 SubTask 的 description 必须包含：背景、目标、约束、验收标准
   - 粒度判断：单文件改动不值得 spawn，跨模块才值得
   - 无依赖的并行（depends_on=[]），有依赖的串行

2. **execute() — DAG 执行引擎**
   - 拓扑排序 SubTask
   - 无依赖的并行 spawn（用 `sessions_spawn`）
   - 有依赖的等上游完成后再 spawn
   - 监听完成事件 → 更新状态 → 触发下游
   - 参考 `AgentManagerV2.ts` 的 `waitAgentIdle` / `waitAgent` 模式

3. **verify() — 结果验证**
   - result 非空
   - 用 LLM 判断 result 是否符合 task.description 预期
   - 返回 `{"passed": bool, "reason": str}`

4. **retry() — 失败重试**
   - retries < max_retries 时重新执行
   - 每次重试都更新状态

### `clawteam/cli_supervisor.py`

```bash
clawteam supervisor start "目标描述" --team default
clawteam supervisor status <plan_id>
clawteam supervisor tasks <plan_id>
clawteam supervisor cancel <plan_id>
```

---

# ═══════════════════════════════════════════
# P7: 跨会话感知
# ═══════════════════════════════════════════

## 目标

让 Supervisor 和子 Agent 能够：
- 查看所有活跃会话的状态
- 获取某个会话的摘要（做了什么、改了什么）
- 按关键词搜索所有会话的活动记录

## 新建文件

### `clawteam/orchestrator/cross_session.py`

```python
class SessionInfo(BaseModel):
    session_id: str
    name: str
    status: str  # running, idle, completed, failed
    work_dir: str
    started_at: str
    parent_session_id: str = ""

class SessionSummary(BaseModel):
    session_id: str
    name: str
    files_modified: list[str]
    commands_executed: list[str]
    key_outputs: list[str]  # AI 回答的关键内容摘要

class CrossSessionAwareness:
    def list_sessions(self, status: str = "all", limit: int = 20) -> list[SessionInfo]:
        """列出所有会话，可按状态筛选"""

    def get_session_summary(self, session_id: str = "", session_name: str = "") -> SessionSummary:
        """获取某个会话的摘要"""

    def search_sessions(self, query: str, limit: int = 10) -> list[dict]:
        """按关键词搜索所有会话的活动记录"""
```

**参考 `supervisorPrompt.ts` 的感知层 prompt**：
- 注入到 Supervisor 会话的系统提示中
- 告知 AI 它运行在多会话环境中
- 提供跨会话感知工具的说明和使用场景

**实现方式**：
- 使用 `sessions_list` / `sessions_history` 获取现有会话信息
- 将结果缓存到内存 + 持久化到 SQLite
- 搜索使用 BM25 或简单关键词匹配

### 修改 `clawteam/orchestrator/supervisor.py`

在 `SupervisorEngine.plan()` 生成的 prompt 中注入跨会话感知能力说明（参考 `buildAwarenessPrompt()`）。

---

# ═══════════════════════════════════════════
# P8: 文件改动追踪
# ═══════════════════════════════════════════

## 目标

自动追踪每个 Agent 在执行过程中修改了哪些文件，生成改动报告。

## 新建文件

### `clawteam/orchestrator/file_tracker.py`

```python
from enum import Enum

class ChangeType(str, Enum):
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"

class FileChange(BaseModel):
    file_path: str
    change_type: ChangeType
    timestamp: float
    session_id: str
    concurrent: bool = False

class FileChangeTracker:
    def start_tracking(self, session_id: str, work_dir: str):
        """开始追踪某个会话的文件改动"""

    def stop_tracking(self, session_id: str) -> list[FileChange]:
        """停止追踪，返回改动的文件列表"""

    def get_changes(self, session_id: str) -> list[FileChange]:
        """获取某个会话的改动（实时）"""

    def get_report(self, plan_id: str) -> dict:
        """生成整个 Plan 的文件改动报告"""
```

**参考 `FileChangeTracker.ts` 的核心设计**：

1. **FS Watch 监听**：用 `watchdog` 库监听工作目录的文件变化
2. **会话归因**：通过 `active_windows` 判断哪个会话在活跃，将文件改动归因给该会话
3. **多会话竞争**：
   - Rule 1：工作目录层级更深的会话优先
   - Rule 2：同深度时，最近有输出的会话优先
   - 1 秒内差距视为并发
4. **去抖**：同一文件 300ms 内只处理最后一次
5. **缓冲 + flush**：改动先存内存缓冲，会话结束时 flush 到数据库
6. **排除目录**：`node_modules`, `.git`, `__pycache__`, `dist`, `build`

**简化版（适合 ClawTeam）**：
- 用 git diff 代替 FS Watch：session 开始前 `git stash`，结束后 `git diff --name-status` 获取改动
- 归因：每个 session 对应一个 work_dir，直接 `git diff --name-status -- work_dir` 获取该 session 的改动
- 不需要复杂的多会话竞争（ClawTeam 的子 Agent 通常在不同目录工作）

---

# ═══════════════════════════════════════════
# 技术约束（适用于 P6-P8）
# ═══════════════════════════════════════════

- Python 3.10+，pydantic v2，type hints
- **无破坏性变更**（向后兼容，已有 696 个测试不坏）
- PEP 8 + ruff 格式化
- 使用现有 Transport/Store/DAG 抽象，不要绕过
- LLM 调用使用 `bailian/qwen3.6-plus`
- P8 优先用 git diff 方案（简单可靠），不要过度设计

---

# ═══════════════════════════════════════════
# 验收标准
# ═══════════════════════════════════════════

## P6
- [ ] SubTask / TaskPlan 模型正确
- [ ] plan() 输入 goal 输出 3-5 个带依赖关系的 SubTask
- [ ] execute() 按 DAG 执行，无依赖并行，有依赖串行
- [ ] verify() 能判断结果是否达标
- [ ] retry() 失败自动重试，最多 2 次
- [ ] CLI: start/status/tasks/cancel 可用
- [ ] 10 个测试通过

## P7
- [ ] list_sessions() 返回活跃会话列表
- [ ] get_session_summary() 返回会话摘要
- [ ] search_sessions() 按关键词搜索
- [ ] Supervisor prompt 注入跨会话感知说明
- [ ] 5 个测试通过

## P8
- [ ] start_tracking() 开始追踪
- [ ] stop_tracking() 返回改动列表
- [ ] get_changes() 实时查询
- [ ] get_report() 生成 Plan 级别报告
- [ ] 5 个测试通过

## 全局
- [ ] `python -m pytest tests/ -v` 全绿（696 + 20 = 716）
- [ ] 无破坏性变更

---

# ═══════════════════════════════════════════
# 测试文件
# ═══════════════════════════════════════════

### `tests/test_supervisor.py`（10 个测试）
1. SubTask 模型创建
2. TaskPlan 模型创建
3. plan() 返回有效 SubTask 列表
4. plan() 包含 depends_on
5. plan() 分解 3-5 个子任务
6. execute() 拓扑顺序
7. execute() 并行无依赖
8. execute() 串行有依赖
9. verify() 通过/失败
10. retry() 次数限制

### `tests/test_cross_session.py`（5 个测试）
1. list_sessions() 返回列表
2. get_session_summary() 返回摘要
3. search_sessions() 搜索命中
4. SessionInfo 模型
5. SessionSummary 模型

### `tests/test_file_tracker.py`（5 个测试）
1. start_tracking + stop_tracking 返回改动
2. get_changes() 实时查询
3. 排除目录不被追踪
4. 改动类型（create/modify/delete）
5. get_report() Plan 级别报告

---

# ═══════════════════════════════════════════
# 完成后
# ═══════════════════════════════════════════

1. `python -m pytest tests/ -v` 确认全绿
2. `git add -A && git commit -m "feat: P6-P8 Supervisor + Cross-session + File tracking"`
3. 通知楚灵审核

---

_任务文档，2026-04-29 创建_
