# AgentTeam 编排组件说明

> 本文档澄清 AgentTeam 中 `SupervisorEngine` 和 `TeamManager` 的定位、职责和扩展方式。
> 解决"AgentSupervisor/AgentManager 独立项目不存在"的困惑——它们不是独立项目，而是 AgentTeam 内的两个核心组件。

---

## 组件总览

```
AgentTeam
├── orchestrator/
│   └── supervisor.py  →  SupervisorEngine     （任务分解 & 执行编排）
└── team/
    └── manager.py     →  TeamManager          （团队生命周期 & 成员管理）
```

---

## SupervisorEngine

**文件**: `agentteam/orchestrator/supervisor.py`

**职责**: 负责任务分解和执行编排。

### 核心能力

| 能力 | 说明 |
|------|------|
| 任务分解 | 将复杂目标按 DecompositionPattern 规则拆分为子任务 DAG |
| Provider 选择 | 根据 TaskType 选择合适的 AI Provider（支持 fallback） |
| 结果验证 | 对执行结果进行质量检查 |
| DAG 排序 | 支持并行/串行执行顺序的拓扑排序 |

### 关键类

```python
from agentteam.orchestrator.supervisor import (
    SupervisorEngine,
    DecompositionPattern,
    DecompositionRule,
)

# 使用示例
engine = SupervisorEngine()
result = await engine.run(task="实现用户登录功能")
```

### DecompositionPattern 枚举

```python
class DecompositionPattern(str, Enum):
    IMPLEMENT_FEATURE = "implement_feature"
    FIX_BUG = "fix_bug"
    ADD_TEST = "add_test"
    REFACTOR = "refactor"
    DOCUMENT = "document"
    ANALYZE = "analyze"
    DEPLOY = "deploy"
    REVIEW = "review"
    GENERAL = "general"
```

---

## TeamManager

**文件**: `agentteam/team/manager.py`

**职责**: 负责团队生命周期管理和成员管理。

### 核心能力

| 能力 | 说明 |
|------|------|
| 团队 CRUD | 创建、获取、更新、删除团队配置 |
| 成员管理 | 按逻辑名称（可选按用户 scope）查找团队成员 |
| 配置持久化 | 团队配置存储为 `~/.agentteam/teams/<team>/config.json` |

### 关键类

```python
from agentteam.team.manager import TeamManager

# 查询成员
member = TeamManager.get_member("my-team", "coder")
if member:
    print(f"Found: {member.name}")

# 列出所有团队
teams = TeamManager.list_teams()
```

### 团队配置模型

```python
from agentteam.team.models import TeamConfig, TeamMember

config = TeamConfig(
    name="my-team",
    members=[
        TeamMember(name="coder", role="engineer", ...),
        TeamMember(name="reviewer", role="senior", ...),
    ]
)
TeamManager.create(config)
```

---

## 缺失功能与改进建议

### 1. 看门狗/健康检查机制（缺失）

当前 `SupervisorEngine` 无内置看门狗。建议扩展：

```python
@dataclass
class SupervisorWatchdogConfig:
    max_task_age_seconds: float = 300.0    # 任务超时阈值
    health_check_interval: float = 30.0     # 健康检查间隔
    max_retries: int = 3                   # 最大重试次数

class SupervisorEngine:
    def __init__(self, watchdog_config: SupervisorWatchdogConfig | None = None):
        self._watchdog = watchdog_config or SupervisorWatchdogConfig()
        self._task_timestamps: dict[str, float] = {}
```

### 2. AgentMemory 集成（缺失）

SupervisorEngine 当前不直接集成 AgentMemory。扩展方式：

```python
# 在 supervisor.py 中添加
from agentmemory import load_config

class SupervisorEngine:
    def __init__(self, memory_config_path: str | None = None):
        if memory_config_path:
            self._memory = load_config(memory_config_path)
```

### 3. TeamManager 事件通知（缺失）

建议为 TeamManager 添加事件钩子：

```python
class TeamManager:
    def __init__(self):
        self._event_handlers: dict[str, list[Callable]] = {}

    def on_member_added(self, team: str, member: TeamMember):
        for handler in self._event_handlers.get("member_added", []):
            handler(team, member)
```

---

## 与其他系统的关系

```
SupervisorEngine ──→ AgentMemory      （可选集成，当前未启用）
      │
      └──────────→ TeamManager         （管理执行团队）
                        │
                        └──────────→ AgentSymphony skills （通过 skill 协议调用）
                                         │
                                         └──────────→ AgentSafety  （安全检查）
```

---

## 扩展开发指南

### 添加新的 DecompositionPattern

```python
# 1. 在 supervisor.py 中添加枚举值
class DecompositionPattern(str, Enum):
    MY_PATTERN = "my_pattern"  # 新增

# 2. 添加分解规则
MY_RULE = DecompositionRule(
    pattern=DecompositionPattern.MY_PATTERN,
    keywords=["我的关键词"],
    subtask_templates=[
        "分析需求",
        "制定计划",
        "执行任务",
    ],
    dependencies=[(0, 1), (1, 2)],  # 0号依赖1号，1号依赖2号
    provider_preferences={0: "fast", 1: "smart"},
)
```

### 添加团队角色

```python
# 在 team/models.py 中扩展 TeamMember
@dataclass
class TeamMember:
    name: str
    role: str  # 可扩展：添加 "capabilities: list[str]" 字段
    # 新增
    capabilities: list[str] = field(default_factory=list)
```

---

*文档生成: 2026-06-05*
*澄清: "AgentSupervisor/AgentManager" 不是独立项目，而是 AgentTeam 内 SupervisorEngine 和 TeamManager 组件的旧称*
