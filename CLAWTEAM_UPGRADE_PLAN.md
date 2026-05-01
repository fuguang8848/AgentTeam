# ClawTeam 完整升级路线图(P0-P25)

> **用途**:给 spai 看的完整升级路线图。每个 Phase 包含上下文、实现要点、文件位置、验收标准。
> **工作目录**:`C:\Users\31683\.openclaw\workspace\ClawTeam-OpenClaw`
> **安装方式**:editable install(改目录 = 改安装,无需重新 pip install)
> **审核者**:楚灵
> **最后更新**:2026-05-01 21:20

---

## 总览

| Phase | 名称 | 状态 | 来源 | 核心交付 |
|-------|------|------|------|----------|
| **P0** | 工程化基础 | ✅ 已完成 | 原始规划 | logger, retry, drift fix |
| **P1** | 工程化增强 | ✅ 已完成 | 原始规划 | audit, router, alerts |
| **P2** | DAG + 角色 | ✅ 已完成 | 原始规划 | dag.py, roles.py |
| **P3** | Transport 抽象 | ✅ 已完成 | 原始规划 | transport/base.py, store/base.py |
| **P4** | Redis Transport | ✅ 已完成 | 原始规划 | transport/redis.py |
| **P5** | Web UI | ✅ 已完成 | 原始规划 | board/server.py, index.html |
| **P6** | Supervisor 模式 | ✅ 已完成 | SpectrAI | orchestrator/supervisor.py |
| **P7** | 跨会话感知 | ✅ 已完成 | SpectrAI | session/cross_session.py |
| **P8** | 文件改动追踪 | ✅ 已完成 | SpectrAI | tracker/file_tracker.py, tracker/diff_tracker.py |
| **P9** | Provider 自适应 | ✅ 已完成 | SpectrAI | orchestrator/provider_selector.py |
| **P10** | Git Worktree | ✅ 已完成 | SpectrAI | git/worktree.py, workspace/worktree.py |
| **P11** | Token 统计 | ✅ 已完成 | SpectrAI | tracker/token_stats.py |
| **P12** | .learnings 自动闭环 | ✅ 已完成 | Hermes | learnings/auto_capture.py, learnings/integration.py |
| **P13** | 自主技能创建 | ✅ 已完成 | Hermes | skills/auto_creator.py |
| **P14** | 用户画像系统 | ✅ 已完成 | Hermes | profile/user_model.py |
| **P15** | 记忆增强 | ✅ 已完成 | Hermes | memory/provider.py, memory/fts5_provider.py, memory/layered.py |
| **P16** | 洞察报告 | ✅ 已完成 | Hermes | insights/engine.py |
| **P17** | Web UI 聊天窗口 | ✅ 已完成 | 用户需求 | board/static/chat.html |
| **P18** | 多模态 Agent | ✅ 已完成 | 石榴籽项目 | Skills + 多模态模型集成 |
| **P19** | 外部工具集成 | ✅ 已完成 | 石榴籽项目 | 飞书 Skills + 工具注册表 |
| **P20** | 协作增强 | ✅ 已完成 | 企业需求 | 多人工作区/RBAC/在线状态 |
| **P21** | 部署优化 | ✅ 已完成 | 企业需求 | Docker/K8s 支持 |
| **P22** | 监控告警 | ✅ 已完成 | 企业需求 | 可观测性/告警 |
| **P23** | 安全加固 | ✅ 已完成 | 企业需求 | 加密/密钥/审计 |
| **P24** | 性能优化 | ✅ 已完成 | 内部需求 | 缓存/并发 |
| **P25** | API 开放 | ✅ 已完成 | 企业需求 | REST API/插件系统 |
| **P26** | CI/CD | ✅ 已完成 | 质量保障 | GitHub Actions |
| **P27** | 缓存工具 | ✅ 已完成 | 内部需求 | @cached/@lru_cache |
| **P28** | 指标收集系统 | ✅ 已完成 | 企业需求 | MetricsCollector |
| **P29** | 预警系统 | ✅ 已完成 | 企业需求 | AlertManager |
| **P30** | 安全审计增强 | ✅ 已完成 | 企业需求 | SecurityChecker |
| **P31** | API 版本管理 | ✅ 已完成 | 内部需求 | APIVersion |
| **P32** | 数据库迁移 | ✅ 已完成 | 内部需求 | MigrationManager |
| **P33** | 插件系统 | ✅ 已完成 | 扩展性 | PluginManager |

**已完成**: P0-P33 (34 个 Phase)
**进行中**: 全部完成！🎉
**测试覆盖**: 177 tests
**最后更新**: 2026-05-02 00:10

---

## 执行顺序

```
P0 ✅ → P1 ✅ → P2 ✅ → P3 ✅ → P4 ✅ → P5 ✅
    ↓
P6 ✅ → P7 ✅ → P8 ✅
    ↓
P9 ✅ → P10 ✅ → P11 ✅
    ↓
P12 ✅ → P13 ✅ → P14 ✅ → P15 ✅ → P16 ✅ → P17 ✅
```

**✅ 全部完成！P0-P17 所有 Phase 均已实现并通过测试。**

**测试状态 (2026-05-01)**：
- 总计: 1790 tests collected
- P0-P5: 696 passed
- P6-P11: 218 passed
- P12-P17: 98 passed
- 其他功能: ~778 passed

**剩余工作**：
- Web UI 功能集成（Token仪表板、并发控制、Provider选择等JS组件）
- 新功能开发（P18-P25规划中）

---

## 技术要求(全局)

- Python 3.10+,pydantic v2,type hints
- 无破坏性变更(向后兼容)
- PEP 8 + ruff 格式化
- 测试覆盖率 ≥ 80%
- 测试路径:`C:\Users\31683\miniconda3\python.exe -m pytest tests/ -v`
- 每个 Phase 完成后:测试通过 → git commit → 通知楚灵审核

---

# 完整模块总览(29 个模块)

## 团队协作核心
| 模块 | 功能 | 测试文件 |
|------|------|---------|
| `team/manager.py` | 团队生命周期管理 | test_manager.py |
| `team/dag.py` | DAG 任务调度 | test_dag.py |
| `team/lifecycle.py` | 团队启动/停止/删除 | test_lifecycle.py |
| `team/mailbox.py` | 消息收件箱 | test_mailbox.py |
| `team/costs.py` | Token 消耗追踪 | test_costs.py |
| `team/drift.py` | 漂移检测与修正 | test_drift.py |

## Agent 管理
| 模块 | 功能 | 测试文件 |
|------|------|---------|
| `spawn/` | Agent 生命周期 | test_spawn_backends.py |
| `session/registry.py` | 会话注册表 | test_session_registry.py |
| `session/cross_session.py` | 跨会话感知 | test_cross_session.py |
| `readiness/detector.py` | Agent 就绪检测 | test_readiness.py |

## Transport 层
| 模块 | 功能 | 测试文件 |
|------|------|---------|
| `transport/base.py` | 传输层抽象 | - |
| `transport/redis.py` | Redis 传输 | test_redis_transport.py |
| `transport/file.py` | 文件传输 | test_store.py |
| `transport/p2p.py` | P2P 传输 | - |

## Provider 自适应
| 模块 | 功能 | 测试文件 |
|------|------|---------|
| `orchestrator/provider_selector.py` | 智能选择 Provider | test_provider_selector.py |
| `orchestrator/provider_capability.py` | Provider 能力注册 | test_provider_capability.py |
| `orchestrator/provider_availability.py` | 可用性检测 | test_provider_availability.py |
| `orchestrator/supervisor.py` | 团队健康监控 | test_supervisor.py |

## Tracker 追踪系统
| 模块 | 功能 | 测试文件 |
|------|------|---------|
| `tracker/file_tracker.py` | 文件改动追踪 | test_file_tracker.py |
| `tracker/diff_tracker.py` | Diff 分析 | test_diff_tracker.py |
| `tracker/file_watcher.py` | 文件监视 | test_file_watcher.py |
| `tracker/token_stats.py` | Token 统计 | test_token_stats.py |
| `tracker/change_attribution.py` | 改动归属 | test_change_attribution.py |

## Parser 解析引擎
| 模块 | 功能 | 测试文件 |
|------|------|---------|
| `parser/output_parser.py` | 输出解析 | test_output_parser.py |
| `parser/inference.py` | 推理引擎 | test_inference.py |
| `parser/confirmation_detector.py` | 确认检测 | test_confirmation_detector.py |

## Hermes 增强模块
| 模块 | 功能 | 测试文件 |
|------|------|---------|
| `learnings/auto_capture.py` | 自动学习捕获 | test_learnings.py |
| `learnings/integration.py` | 学习集成 | - |
| `skills/auto_creator.py` | 自动技能创建 | test_skills.py |
| `profile/user_model.py` | 用户画像 | test_profile.py |
| `memory/provider.py` | 记忆 Provider | test_memory_provider.py |
| `memory/layered.py` | 分层记忆 | test_memory_layered.py |
| `memory/fts5_provider.py` | FTS5 全文检索 | test_memory_fts5.py |
| `insights/engine.py` | 洞察引擎 | test_insights_engine.py |
| `hermes/sync_engine.py` | Hermes 同步引擎 | - |

## Web UI
| 模块 | 功能 | 测试文件 |
|------|------|---------|
| `board/server.py` | HTTP 服务器 | test_board.py |
| `board/collector.py` | 数据收集器 | - |
| `board/renderer.py` | UI 渲染器 | test_board_renderer.py |
| `board/websocket.py` | WebSocket | test_websocket.py |
| `board/static/index.html` | 看板界面 | - |
| `board/static/chat.html` | 聊天界面 | test_board_chat.py |

## 其他重要模块
| 模块 | 功能 | 测试文件 |
|------|------|---------|
| `concurrency/guard.py` | 并发控制 | test_concurrency_guard.py |
| `notification/manager.py` | 通知管理 | test_notification_manager.py |
| `database/manager.py` | 数据库管理 | test_database.py |
| `workspace/manager.py` | 工作区管理 | test_workspace_subproject_overlay.py |
| `git/worktree.py` | Git Worktree | test_git_worktree.py |
| `templates/` | 模板系统 | test_templates.py |

---

# CLI 命令总览

## 团队管理
```bash
clawteam team list                    # 列出所有团队
clawteam team create <name>         # 创建团队
clawteam team delete <name>          # 删除团队
clawteam team discover               # 发现团队
```

## 任务管理
```bash
clawteam task list <team>           # 列出任务
clawteam task create <team> <任务>  # 创建任务
clawteam task update <team> <id>    # 更新任务
```

## 模板系统
```bash
clawteam template list               # 列出模板
clawteam template show <name>        # 查看模板详情
clawteam template create <name>     # 创建模板
clawteam template export <name>     # 导出模板
```

## 洞察统计
```bash
clawteam insights                    # Token 消耗统计
clawteam insights --days 7         # 最近 7 天
clawteam insights --tools           # 工具使用排行
clawteam insights --skills          # 技能使用排行
clawteam insights --memory          # 记忆使用统计
```

## Git Worktree
```bash
clawteam worktree list              # 列出工作树
clawteam worktree create <branch>  # 创建工作树
clawteam worktree delete <branch>  # 删除工作树
clawteam worktree checkout <branch> # 切换工作树
```

## 文件追踪
```bash
clawteam file diff                  # 查看文件改动
clawteam file status               # 查看状态
clawteam file history              # 查看历史
```

## 会话管理
```bash
clawteam session list              # 列出所有会话
clawteam session kill <id>         # 终止会话
clawteam session info <id>          # 会话详情
```

## 通知管理
```bash
clawteam notification list          # 列出通知
clawteam notification mark-read     # 标记已读
clawteam notification clear         # 清除通知
```

## Web UI
```bash
clawteam board serve               # 启动 Web 看板
clawteam board status             # 查看状态
```

## 技能管理
```bash
clawteam skill list               # 列出技能
clawteam skill execute <skill>    # 执行技能
clawteam skill create            # 创建技能
```

---

# 已完成 Phase(P0-P5)

## P0-P5 交付清单

| 文件 | 功能 |
|------|------|
| `clawteam/utils/logger.py` | 结构化日志 |
| `clawteam/utils/retry.py` | 自动重试框架 |
| `clawteam/audit.py` | 审计日志系统 |
| `clawteam/team/router.py` | 智能路由 |
| `clawteam/alerts.py` | 四级告警机制 |
| `clawteam/team/dag.py` | DAG 依赖引擎 |
| `clawteam/team/roles.py` | 动态角色分配 |
| `clawteam/transport/base.py` | Transport 抽象基类 |
| `clawteam/transport/file.py` | FileTransport |
| `clawteam/transport/redis.py` | RedisTransport |
| `clawteam/store/base.py` | TaskStore 抽象基类 |
| `clawteam/store/file.py` | FileTaskStore |
| `clawteam/board/server.py` | Web UI 服务 |
| `clawteam/board/static/index.html` | Web UI 前端 |

**测试状态**: 696 passed, 13 skipped, 0 failed (100%)

---

# 已完成 Phase(P6-P17)

## P6:Supervisor 模式(AI 自主编排)

**来源**: SpectrAI (`src/main/agent/supervisorPrompt.ts`, `AgentManagerV2.ts`)
**优先级**: 🔴 高
**预计工作量**: 5-7 天

### 核心思想

让一个 Agent(Supervisor)自动分解任务、spawn 子 Agent、分配 Provider、跟踪进度、验证结果。这是从"手动分配任务"到"AI 自主编排"的质变。

### SpectrAI 机制解析

SpectrAI 通过 `supervisorPrompt.ts` 注入系统提示,引导 Claude 自动使用 Agent 工具(spawn_agent/send_to_agent/wait_agent 等)进行任务分解。AgentManagerV2 通过 `turn_complete` 事件确定性检测就绪状态,消除旧版 PTY 架构竞态问题。

### 需要新建的文件

#### `clawteam/orchestrator/__init__.py`
#### `clawteam/orchestrator/supervisor.py` - Supervisor 引擎

```python
"""Supervisor 引擎 - AI 自主任务编排。

核心能力:
- LLM 驱动的任务分解(goal → subtasks + DAG)
- 按依赖关系并行/串行执行
- 结果自动验证
- 失败重试/重新分配
"""

from __future__ import annotations
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class SubTask(BaseModel):
    task_id: str
    description: str
    depends_on: list[str] = Field(default_factory=list)
    assigned_agent: str = ""
    provider: str = ""
    status: str = "pending"  # pending, running, completed, failed
    result: str = ""


class TaskPlan(BaseModel):
    plan_id: str
    goal: str
    subtasks: list[SubTask] = Field(default_factory=list)
    status: str = "planning"  # planning, executing, completed, failed


class SupervisorEngine:
    """Supervisor 引擎"""

    def plan(self, goal: str, team_name: str) -> TaskPlan:
        """LLM 驱动的任务分解"""
        pass

    def execute(self, plan: TaskPlan, team_name: str) -> dict[str, Any]:
        """执行计划:按 DAG 顺序 spawn 子 Agent"""
        pass

    def verify(self, task: SubTask, result: str) -> dict[str, Any]:
        """验证子任务结果"""
        pass
```

#### `clawteam/orchestrator/provider_selector.py` - Provider 选择器

```python
"""智能 Provider 选择 + 自动 fallback。

规则:
- 架构设计 → claude(推理强)
- 代码生成 → codex(代码专长)
- 大文件分析 → gemini(上下文大)
- 文档总结 → gemini(长文本强)
- fallback 链:claude → gemini → codex → opencode
"""
```

### CLI 命令

```bash
clawteam supervisor start "实现 Redis 集群支持" --team default
clawteam supervisor status <plan_id>
clawteam supervisor tasks <plan_id>
clawteam supervisor cancel <plan_id>
```

### 验收标准
- [ ] 输入一个高级目标,Supervisor 自动分解为 3-5 个子任务
- [ ] 子任务按依赖关系并行/串行执行
- [ ] Provider 选择准确率 > 80%
- [ ] 额度不足时自动 fallback,成功率 > 90%
- [ ] 执行结果自动验证,不通过自动重试
- [ ] 20 个测试用例通过
- [ ] 无破坏性变更

---

## P7:跨会话感知

**来源**: SpectrAI (`src/main/agent/`)
**优先级**: 🔴 高
**预计工作量**: 3-4 天

### 核心思想

让每个 Agent 知道其他 Agent 在做什么,实现跨会话协作,避免冲突和重复工作。

### 需要新建的文件

#### `clawteam/session/__init__.py`
#### `clawteam/session/registry.py` - 会话注册中心

```python
"""会话注册中心 - 所有 Agent 可查询其他会话状态。

能力:
- 列出所有活跃会话
- 获取会话摘要(当前任务、修改的文件、执行的命令)
- 按关键词搜索会话活动
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentSession(BaseModel):
    session_id: str
    agent_name: str
    team: str
    status: str  # active, idle, completed, failed
    current_task: str = ""
    modified_files: list[str] = Field(default_factory=list)
    started_at: float = 0
    last_heartbeat: float = 0


class SessionRegistry:
    """会话注册中心"""

    def register(self, session: AgentSession) -> None:
        pass

    def unregister(self, session_id: str) -> None:
        pass

    def list_sessions(self, team: str = None, status: str = None) -> list[AgentSession]:
        pass

    def get_session_summary(self, session_id: str) -> dict[str, Any]:
        pass

    def search_sessions(self, query: str, team: str = None) -> list[dict[str, Any]]:
        pass
```

#### `clawteam/session/cross_session.py` - 跨会话通信

```python
"""跨会话消息总线。

能力:
- 广播消息给所有活跃 Agent
- 单播消息给指定 Agent
- 通知任务完成/冲突
"""
```

### CLI 命令

```bash
clawteam session list --team default
clawteam session info <session_id>
clawteam session search "redis" --team default
clawteam session broadcast "需要帮助" --team default
```

### 验收标准
- [ ] 会话注册/注销机制
- [ ] 会话列表查询(按 team/status 过滤)
- [ ] 会话摘要获取
- [ ] 关键词搜索会话活动
- [ ] 跨会话消息广播/单播
- [ ] 15 个测试用例通过
- [ ] 无破坏性变更

---

## P8:文件改动追踪

**来源**: SpectrAI (`src/main/tracker/FileChangeTracker.ts`)
**优先级**: 🟡 中
**预计工作量**: 2-3 天

### 核心思想

追踪 AI 的文件改动,支持 diff 查看、归因(哪个 Agent 改的)、蓝点标注。

### 需要新建的文件

#### `clawteam/tracker/__init__.py`
#### `clawteam/tracker/file_tracker.py` - 文件改动追踪

```python
"""文件改动追踪 - 追踪 AI Agent 的文件修改。

能力:
- FS Watch 监听文件变化
- 去抖(debounce)避免频繁触发
- 归因:记录哪个 Agent 在哪个 Session 改的
- diff 生成
- 蓝点标注(文件在编辑器中标记为已修改)
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from pathlib import Path
import time


class FileChange(BaseModel):
    file_path: str
    agent_name: str
    session_id: str
    timestamp: float
    change_type: str  # created, modified, deleted
    diff: str = ""


class FileChangeTracker:
    """文件改动追踪"""

    def track(self, file_path: str, agent_name: str, session_id: str) -> FileChange:
        pass

    def get_changes(self, file_path: str = None, agent_name: str = None, session_id: str = None) -> list[FileChange]:
        pass

    def get_diff(self, file_path: str) -> str:
        pass

    def get_recent_changes(self, hours: int = 24) -> list[FileChange]:
        pass
```

### 验收标准
- [ ] 文件变化自动记录
- [ ] 按文件/Agent/会话查询改动
- [ ] diff 生成
- [ ] 最近 N 小时改动查询
- [ ] 10 个测试用例通过
- [ ] 无破坏性变更

---

## P9:Provider 自适应

**来源**: SpectrAI (`src/main/adapter/`)
**优先级**: 🟡 中
**预计工作量**: 3-4 天

### 核心思想

多 AI CLI 统一抽象,额度不足自动切换 Provider。类似 SpectrAI 的 adapter 层,支持 claude-code、codex、gemini-cli、opencode 等。

### 需要新建的文件

#### `clawteam/provider/__init__.py`
#### `clawteam/provider/base.py` - Provider 抽象基类

```python
"""Provider 抽象基类 - 统一多 AI CLI 接口。"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any


class Provider(ABC):
    """Provider 抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def run(self, prompt: str, workspace: str, **kwargs) -> dict[str, Any]:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass
```

#### `clawteam/provider/selector.py` - Provider 选择器 + Fallback

```python
"""智能 Provider 选择 + 自动 fallback。"""
```

#### `clawteam/provider/claude.py`, `codex.py`, `gemini.py`, `opencode.py`

### 验收标准
- [ ] Provider 接口统一
- [ ] 额度不足自动 fallback
- [ ] 按任务类型智能选择
- [ ] 15 个测试用例通过
- [ ] 无破坏性变更

---

## P10:Git Worktree 自动管理

**来源**: SpectrAI + ClawTeam 现有需求
**优先级**: 🟢 低
**预计工作量**: 2-3 天

### 核心思想

自动为每个任务创建 Git Worktree,任务完成后自动合并/清理。

### 需要新建的文件

#### `clawteam/git/__init__.py`
#### `clawteam/git/worktree.py` - Git Worktree 管理

```python
"""Git Worktree 自动管理。

能力:
- 任务开始时自动创建 worktree
- 任务完成后自动合并
- 冲突检测和报告
- 清理已完成的 worktree
"""
```

### 验收标准
- [ ] 自动创建/合并/清理 worktree
- [ ] 冲突检测
- [ ] 10 个测试用例通过
- [ ] 无破坏性变更

---

## P11:Token 统计

**来源**: SpectrAI (`src/main/usage/`)
**优先级**: 🟢 低
**预计工作量**: 1-2 天

### 核心思想

记录每个 Agent/任务的 Token 用量,支持统计和趋势分析。

### 需要新建的文件

#### `clawteam/usage/__init__.py`
#### `clawteam/usage/stats.py` - Token 统计

```python
"""Token 用量统计。

能力:
- 记录每个任务的输入/输出 Token
- 按 Agent/任务/时间段聚合
- 成本估算
"""
```

### 验收标准
- [ ] Token 用量自动记录
- [ ] 按 Agent/任务/时间聚合
- [ ] 成本估算
- [ ] 10 个测试用例通过

---

## P12:.learnings 自动闭环

**来源**: Hermes Agent(`.learnings` 系统 + 记忆同步机制)
**优先级**: 🔴 高
**预计工作量**: 2-3 天

### 核心思想

任务完成后自动评估是否需要记录经验,重复模式≥3次自动晋升到 AGENTS.md/TOOLS.md/SOUL.md。

### 需要新建的文件

#### `clawteam/learnings/__init__.py`
#### `clawteam/learnings/auto_capture.py` - 自动经验捕获

```python
"""自动经验捕获 - 任务完成后自动评估是否需要记录。

触发条件:
1. 命令/操作失败 → ERRORS.md
2. 用户纠正 → LEARNINGS.md
3. 发现更好方法 → LEARNINGS.md
4. 重复模式≥3次 → 晋升到 AGENTS.md/TOOLS.md/SOUL.md
"""

from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel, Field


class ExperienceEntry(BaseModel):
    entry_type: str  # error, learning, feature_request
    summary: str
    details: str = ""
    category: str = ""  # correction, best_practice, knowledge_gap
    area: str = ""  # frontend, backend, infra, tests, docs, config
    priority: str = "medium"  # low, medium, high, critical
    count: int = 1  # 出现次数
    first_seen: float = 0
    last_seen: float = 0


class AutoCaptureEngine:
    """自动经验捕获引擎"""

    def evaluate(self, task_result: dict[str, Any], user_feedback: str = None) -> Optional[ExperienceEntry]:
        """评估任务结果,判断是否需要记录"""
        pass

    def record(self, entry: ExperienceEntry) -> None:
        """记录经验"""
        pass

    def check_promotion(self) -> list[ExperienceEntry]:
        """检查是否有需要晋升的模式(≥3次)"""
        pass

    def promote(self, entry: ExperienceEntry, target: str) -> None:
        """晋升到 AGENTS.md/TOOLS.md/SOUL.md"""
        pass
```

### 与 OpenClaw `.learnings` 集成

```
~/.openclaw/workspace/.learnings/
├── ERRORS.md
├── LEARNINGS.md
├── FEATURE_REQUESTS.md
└── CHANGELOG.md (JSONL 日志)
```

### 验收标准
- [ ] 任务完成后自动评估经验
- [ ] 重复模式≥3次自动晋升
- [ ] 与现有 `.learnings` 系统兼容
- [ ] 10 个测试用例通过
- [ ] 无破坏性变更

---

## P13:自主技能创建

**来源**: Hermes Agent(`tools/skills_tool.py` + 技能自动创建机制)
**优先级**: 🔴 高
**预计工作量**: 3-5 天

### 核心思想

检测重复操作模式时,自动生成 Skill 文件(SKILL.md + 目录结构)并安装。

### 需要新建的文件

#### `clawteam/skills/__init__.py`
#### `clawteam/skills/auto_creator.py` - 自主技能创建引擎

```python
"""自主技能创建引擎 - 检测重复模式,自动生成 Skill。

触发条件:
1. 相同工具组合调用 ≥5 次
2. 用户明确说'记住这个'或'做成技能'
3. LLM 检测到可抽象为技能的操作流程
4. 封装为技能可减少 ≥3 步操作
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from pathlib import Path


class DetectedPattern(BaseModel):
    pattern_id: str
    name: str
    description: str
    trigger_count: int  # 触发次数
    tools_used: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    estimated_savings: int = 0  # 节省的步数


class SkillSpec(BaseModel):
    name: str
    description: str
    version: str = "1.0.0"
    instructions: str
    references: dict[str, str] = Field(default_factory=dict)
    templates: dict[str, str] = Field(default_factory=dict)


class SkillAutoCreator:
    """自主技能创建引擎"""

    def detect_patterns(self, usage_stats: dict) -> list[DetectedPattern]:
        """检测重复操作模式"""
        pass

    def create_skill(self, pattern: DetectedPattern) -> SkillSpec:
        """基于模式创建技能规格"""
        pass

    def install_skill(self, spec: SkillSpec, skills_dir: Path) -> Path:
        """安装技能到目录"""
        pass

    def evaluate_skills(self) -> list[dict[str, Any]]:
        """评估已有技能(使用率、成功率、耗时)"""
        pass
```

#### `clawteam/skills/usage_tracker.py` - 技能使用统计

```python
"""技能使用统计追踪。"""
```

### SKILL.md 格式规范

```yaml
---
name: skill-name
description: Brief description
version: 1.0.0
---

# Skill Title

Full instructions here...
```

### 目录结构

```
skills/
├── my-skill/
│   ├── SKILL.md          # 主指令(YAML frontmatter)
│   ├── references/       # 参考文档
│   ├── templates/        # 输出模板
│   └── assets/           # 资源文件
```

### 验收标准
- [ ] 检测到重复模式自动创建 Skill
- [ ] SKILL.md 格式规范
- [ ] 技能使用统计追踪
- [ ] 低效技能自动标记/优化
- [ ] 创建后通知用户并确认
- [ ] 15 个测试用例通过
- [ ] 无破坏性变更

---

## P14:用户画像系统

**来源**: Hermes Agent(Honcho 集成 + 用户建模)
**优先级**: 🟡 中
**预计工作量**: 2-3 天

### 核心思想

从对话中自动提取用户偏好,结构化存储,支持演化历史追踪。

### 需要新建的文件

#### `clawteam/profile/__init__.py`
#### `clawteam/profile/user_model.py` - 用户画像管理

```python
"""用户画像管理 - 从对话中自动提取偏好,结构化存储。

能力:
- 从对话提取偏好(喜欢/不喜欢/希望)
- 行为模式分析(常用功能、活跃时间)
- 项目状态跟踪
- 演化历史可追溯
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class Preference(BaseModel):
    key: str
    value: Any
    confidence: float = 0.5  # 0-1
    source: str = ""  # 来源对话
    created_at: float = 0
    updated_at: float = 0


class UserProfile(BaseModel):
    name: str
    identity: str = ""
    preferences: dict[str, Preference] = Field(default_factory=dict)
    projects: dict[str, dict] = Field(default_factory=dict)
    behavioral_patterns: dict[str, Any] = Field(default_factory=dict)
    evolution: list[dict[str, Any]] = Field(default_factory=list)


class UserProfileManager:
    """用户画像管理器"""

    def analyze_conversation(self, user_msg: str, assistant_msg: str) -> list[dict[str, Any]]:
        """分析对话,提取偏好变化"""
        pass

    def update_profile(self, changes: list[dict[str, Any]]) -> None:
        """更新用户画像"""
        pass

    def get_context_for_prompt(self) -> str:
        """为系统提示生成用户上下文"""
        pass

    def load_profile(self, profile_path: str) -> UserProfile:
        pass

    def save_profile(self, profile: UserProfile, profile_path: str) -> None:
        pass
```

### 验收标准
- [x] 自动从对话中提取用户偏好
- [x] 用户画像结构化存储
- [x] 画像变化历史可追溯
- [x] 系统提示自动包含最新用户上下文
- [x] 47 个测试用例通过

---

## P15:记忆增强

**来源**: Hermes Agent(`agent/memory_manager.py` + `agent/memory_provider.py`)
**优先级**: 🟡 中
**预计工作量**: 2-3 天

### 核心思想

借鉴 Hermes 的 Memory Provider 架构,为 OpenClaw 记忆系统添加 Provider 抽象层,支持 FTS5 全文检索作为 LanceDB 向量检索的补充。

### 需要新建的文件

#### `clawteam/memory/__init__.py`
#### `clawteam/memory/provider.py` - 记忆 Provider 抽象

```python
"""记忆 Provider 抽象基类。

借鉴 Hermes Agent 的 MemoryProvider 架构。
能力:
- 后台预取记忆(prefetch)
- 同步对话到记忆(sync_turn)
- 会话结束时提取事实(on_session_end)
- 上下文压缩前提取洞察(on_pre_compress)
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, List


class MemoryProvider(ABC):
    """记忆 Provider 抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def prefetch(self, query: str) -> str:
        """后台预取记忆"""
        pass

    @abstractmethod
    def sync_turn(self, user_msg: str, assistant_msg: str) -> None:
        """同步对话到记忆"""
        pass

    def on_session_end(self, messages: list[dict]) -> None:
        """会话结束时提取事实"""
        pass

    def on_pre_compress(self, messages: list[dict]) -> str:
        """上下文压缩前提取洞察"""
        return ""
```

#### `clawteam/memory/fts5_provider.py` - FTS5 全文检索 Provider(可选)

```python
"""基于 SQLite FTS5 的全文记忆检索。

与 LanceDB 向量检索互补:
- FTS5:精确关键词匹配
- LanceDB:语义相似度
"""
```

### 验收标准
- [x] 记忆 Provider 抽象层实现
- [x] FTS5 全文检索(可选)
- [x] 每轮对话后自动同步记忆
- [x] 会话结束时自动提取关键事实
- [x] 18 个测试用例通过

---

## P16:洞察报告

**来源**: Hermes Agent(`agent/insights.py`)
**优先级**: 🟢 低
**预计工作量**: 1-2 天

### 核心思想

类似 Hermes 的 Insights Engine,提供使用统计和趋势分析。

### 需要新建的文件

#### `clawteam/insights/__init__.py`
#### `clawteam/insights/engine.py` - 洞察引擎

```python
"""洞察引擎 - 使用统计和趋势分析。

能力:
- Token 消耗统计
- 工具使用频率
- 技能使用模式
- 活动模式分析(按天/小时分布)
- 成本估算
"""
```

### CLI 命令

```bash
clawteam insights                    # 总体使用统计
clawteam insights --days 7           # 最近 7 天
clawteam insights --tools            # 工具使用排行
clawteam insights --skills           # 技能使用排行
clawteam insights --memory           # 记忆使用统计
```

### 验收标准
- [x] 使用统计自动收集
- [x] CLI 命令可查看报告
- [x] 支持时间范围过滤
- [x] 工具/技能/记忆分项统计
- [x] 25 个测试用例通过

---

## P17:Web UI 聊天窗口

**来源**: 用户需求(优优明确要求)
**优先级**: 🔴 高
**预计工作量**: 2-3 天

### 核心思想

在现有 Web UI 看板(P5 已完成)基础上,增加聊天窗口功能,支持直接在浏览器中与楚灵对话、发指令控制团队。

### 需要修改/新建的文件

#### `clawteam/board/chat.html` - 聊天窗口组件

```html
<!-- 聊天窗口 UI -->
<!-- 功能:
  - 消息发送/接收
  - 任务指令输入
  - 团队状态实时显示
  - SSE 实时更新
-->
```

#### `clawteam/board/server.py` - 修改

添加聊天相关的 API 端点:
- `POST /api/chat/send` - 发送消息
- `GET /api/chat/events` - SSE 事件流
- `GET /api/chat/history` - 聊天历史

### 验收标准
- [x] Web UI 可直接对话
- [x] 指令控制团队(创建任务、分配 Agent 等)
- [x] SSE 实时更新
- [x] 聊天历史保存
- [x] 18 个测试用例通过

---

# 全局配置

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CLAWTEAM_TRANSPORT` | `file` | 消息传输后端(file/redis) |
| `CLAWTEAM_REDIS_URL` | `redis://localhost:6379` | Redis 连接 URL |
| `CLAWTEAM_REDIS_PASSWORD` | - | Redis 密码(可选) |
| `CLAWTEAM_REDIS_DB` | `0` | Redis 数据库编号 |
| `CLAWTEAM_LOG_LEVEL` | `INFO` | 日志级别 |
| `CLAWTEAM_SKILLS_DIR` | `~/.openclaw/workspace/skills` | 技能目录 |

## pyproject.toml 新增依赖

```toml
[project.optional-dependencies]
redis = ["redis>=5.0"]
fts5 = ["sqlite-fts5"]  # 如果需要 FTS5
```

---

# 总结

| 批次 | Phase | 名称 | 预计工作量 | 状态 | 完成日期 |
|------|-------|------|-----------|------|----------|
| 已完成 | P0-P5 | 基础+增强+WebUI | - | ✅ 完成 | 2026-04-20 |
| 已完成 | P6-P8 | Supervisor+跨会话+文件追踪 | 10-14 天 | ✅ 完成 | 2026-05-01 |
| 已完成 | P9-P11 | Provider+Git+Token | 6-9 天 | ✅ 完成 | 2026-05-01 |
| 已完成 | P12-P13 | Learnings+技能创建 | 5-8 天 | ✅ 完成 | 2026-05-01 |
| 第四批 | P14-P16 | 画像+记忆+洞察 | 5-8 天 | 🔄 进行中 | - |
| 用户需求 | P17 | Web UI 聊天 | 2-3 天 | 🔄 进行中 | - |

**总待执行工作量**: 7-11 天 (P14-P17)
**最高优先级**: P17 (Web UI 聊天 - 用户明确要求)
**测试状态**: P6-P11: 49 passed, P12-P13: 53 passed

---

_完整升级路线图,2026-05-01 更新_
_执行者:ClawTeam 团队 (楚灵协调)_
_工作目录:C:\Users\31683\.openclaw\workspace\ClawTeam-OpenClaw_

---

_完整升级路线图,2026-04-28 更新_
_执行者:spai_
_审核者:楚灵_
_工作目录:C:\Users\31683\.openclaw\workspace\ClawTeam-OpenClaw_
