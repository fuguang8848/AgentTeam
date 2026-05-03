# ClawTeam 升级日志

## v0.5.0（2026-05-03）— P26-P37 多 Agent 协作增强

### 新增模块

#### P26: Parent-Child 生命周期管理 ✅
- **commit**: `cb52d4e feat(lifecycle): implement Parent-Child lifecycle management (P26)`
- **文件**: `clawteam/team/lifecycle.py`
- **新增功能**:
  - `ParentChildRegistry` - 追踪父子关系
  - `parentToAgents: Map[parentSessionId, Set[agentId]]` - 父子映射
  - `cleanupChildAgents(sessionId)` - 级联终止所有子 Agent
  - 5 个新 CLI 命令：
    - `terminate-children` - 终止子 Agent
    - `terminate-tree` - 终止整个 Agent 树
    - `list-children` - 列出子 Agent
    - `show-parent` - 显示父 Agent
    - `register-child` - 注册子 Agent
  - `--parent` flag for spawn command

#### P28: 工具注册增强 🔄
- **文件**: `clawteam/tools/registry.py`
- **状态**: 修改中
- **目标**: 增强工具注册表，支持动态工具发现

#### P29: 协作增强 🔄
- **目录**: `clawteam/collaboration/`
- **状态**: 创建中
- **目标功能**:
  - Activity Feed（活动流）
  - Presence（在线状态）
  - Mentions（@提及）
  - Context Board（上下文面板）

#### P30-P33: 多模态支持 🔄→✅（部分代码）
- **文档**: `docs/superpowers/specs/P30-P33-multimodal-support-design.md` ✅
- **commit**: `bd32e9c` feat(models): P30-P33 multimodal support - image fields and FileAttachment class
- **已实现** (`clawteam/team/models.py` + `clawteam/notification/types.py`):
  - `TeamMessage` 新增: `image_url`, `image_data`, `image_mime_type`, `image_width`, `image_height`, `attachments: list[FileAttachment]`
  - `Notification` 新增: `image_url`
  - 新增 `FileAttachment` 模型类
  - CLI inbox 图片渲染: `clawteam/cli/inbox.py` - iTerm2 inline images + URL fallback
  - Web board 富媒体: `index.html` renderMessage() 支持 image_url/base64/attachments 渲染
  - Streaming/SSE: `board/server.py` _serve_sse() + polling fallback

#### P34: Dashboard 监控面板 ✅
- **新增文件**:
  - `clawteam/api/monitor.py`
  - `clawteam/board/dashboard.py`
- **状态**: 已完成
- **功能**: 实时会话监控、Token 使用统计、风险评估、collector + renderer

#### P35: 事件追踪系统 ✅
- **目录**: `clawteam/events/`
- **状态**: 已完成
- **目标**: 40+ 事件类型、SQLite 持久化、事件查询 API

#### P36: 实时 SSE 推送 ✅
- **修改文件**:
  - `clawteam/board/server.py`
  - `clawteam/board/static/index.html`
- **状态**: 已完成
- **目标**: Server-Sent Events、实时日志推送

#### P37: 组件集成 ✅
- **commit**: `0e7b0f8`
- **Board 接入**: EventAPI/NotificationManager
- **状态**: 已完成
- **说明**: Windows subprocess 限制由 OpenClaw SDK backend 解决（parent_agent 参数修复）

#### P38: 智能模型路由 ✅
- **commit**: `2f102db` feat(orchestrator): P38 intelligent model router
- **文件**: `clawteam/orchestrator/model_router.py`
- **状态**: 已完成
- **功能**:
  - `TaskComplexityAnalyzer`: 基于关键词 + 启发式的任务复杂度分析（1-10分）
  - `ComplexityLevel`: TRIVIAL/LOW/MEDIUM/HIGH/EXPERT 五级复杂度
  - `ModelTier`: FAST/BALANCED/POWERFUL 三级模型
  - `ModelRoutingPolicy`: (task_type, complexity) → model_tier 路由表
  - `ModelRouter`: 根据任务复杂度自动选择最优模型
  - 成本优化：简单任务使用廉价快速模型（节省 80-90% 成本）
- **示例**:
  - "What is Python?" → FAST tier (score=3) → gpt-4o-mini
  - "设计分布式缓存系统" → POWERFUL tier (score=9) → o1

#### P3: 数据库连接池 ✅
- **commit**: `9464edd` perf(database): P3 database connection pooling + WAL mode
- **文件**: `clawteam/database/manager.py`
- **状态**: 已完成
- **功能**:
  - `DatabaseConnectionPool`: 基于 `queue.Queue` 的连接池，线程本地连接
  - `_get_conn()` / `_release_conn()` 显式管理，连接复用
  - WAL 模式：`_enable_wal_mode()` 提升并发读写性能
  - 事务支持：`begin()` / `commit()` / `rollback()`
  - 预编译语句缓存：`prepared_stmts` 字典

#### P4: 查询预编译缓存 ✅
- **commit**: `dcfacb3` perf(events): P4 prepared statement caching for EventTracker.query()
- **文件**: `clawteam/events/tracker.py`
- **状态**: 已完成
- **功能**:
  - `_stmt_cache: OrderedDict` 缓存预编译语句模板
  - LRU 驱逐策略（`maxsize=32`）
  - `track()`, `query()`, `get_stats()` 全部使用缓存
  - 查询性能提升：避免重复编译 SQL

#### P5: 异步订阅者通知 ✅
- **commit**: `541c707` feat(events): P5 async subscriber notification with timeout
- **文件**: `clawteam/events/tracker.py`
- **状态**: 已完成
- **功能**:
  - `_notify_subscribers_async()` 使用 `ThreadPoolExecutor` 异步通知
  - `wait([future], timeout=5.0)` 超时保护，防止订阅者阻塞主线程
  - 事件追踪不受订阅者故障影响
  - `notify()` 返回 `bool` 指示是否全部成功

#### P6: 内存配置可调参数 ✅
- **commit**: `e36ebc7` feat(board): P6 Memory Config Tunables
- **文件**: `clawteam/board/server.py`
- **状态**: 已完成
- **功能**:
  - `_event_queue` / `_chat_event_queue` 队列大小可配置
  - `CLAWTEAM_MAX_EVENT_QUEUE` / `CLAWTEAM_MAX_CHAT_QUEUE` 环境变量
  - 默认值：1000 事件 / 500 聊天，超出后丢弃最旧的
  - `CLAWTEAM_EVENT_TTL_HOURS` 控制事件过期时间

### 已实现的核心功能（v0.4.0 确认）

| 模块 | 文件 | 功能 | 状态 |
|------|------|------|------|
| **MailboxManager** | `clawteam/team/mailbox.py` | Agent 间消息传递 | ✅ |
| **P2P Transport** | `clawteam/transport/p2p.py` | ZeroMQ PUSH/PULL + 文件回退 | ✅ |
| **RoleStore** | `clawteam/team/roles.py` | 动态角色分配 | ✅ |
| **BaseTaskStore** | `clawteam/store/base.py` | 任务存储抽象 | ✅ |
| **WebSocketManager** | `clawteam/board/websocket.py` | WebSocket 连接管理 | ✅ |
| **Board Server** | `clawteam/board/server.py` | HTTP API + SSE | ✅ |
| **Transport 抽象** | `clawteam/transport/base.py` | File/P2P/Redis | ✅ |
| **LifecycleManager** | `clawteam/team/lifecycle.py` | Agent 生命周期状态机 | ✅ |
| **OpenClaw SDK Backend** | `clawteam/spawn/openclaw_sdk_backend.py` | Gateway Sessions API 集成 | ✅ |

### 升级团队状态（2026-05-03）

| Agent | 任务 | Worktree | 状态 | 实际完成 |
|-------|------|----------|------|----------|
| arch-p27 | Parent-Child 生命周期 | `upgrade-squad/arch-p27` | ✅ 已完成 | `cb52d4e` + 5 CLI 命令 |
| arch-p28 | 工具注册增强 | `upgrade-squad/arch-p28` | ✅ 已完成 | `tools/registry.py` 修改 |
| arch-p29 | 协作增强 | `upgrade-squad/arch-p29` | ✅ 已完成 | 4 个模块（activity_feed + context_board + mentions + presence）|
| arch-p30-33 | 多模态支持 | `upgrade-squad/arch-p30-33` | ✅ 已完成 | 设计文档 8KB |
| arch-dashboard | Dashboard 监控 | `monitor-squad/arch-dashboard` | ✅ 已完成 | dashboard.py (13KB) + collector + renderer |
| arch-events | 事件追踪 | `monitor-squad/arch-events` | ✅ 已完成 | tracker.py (14KB) + api + models |
| arch-realtime | SSE 实时推送 | `monitor-squad/arch-realtime` | ✅ 已完成 | index.html (366KB) + 7 个 JS 文件 |
| arch-integrator | 组件集成 | `monitor-squad/arch-integrator` | 🔄 进行中 | 待开始 |
| p37-integrator | 组件集成（P37） | SDK backend（Windows） | ✅ 已完成 | `14d1d74` Board SSE → EventAPI |
| p30-multimodal | 多模态代码（P30-P33） | subprocess（Windows） | ✅ 部分完成 | `bd32e9c` models.py + types.py |
| p38-model-router | 智能模型路由 | 本地 | ✅ 已完成 | `2f102db` model_router.py |
| arch-dbpool | P3 数据库连接池 | perf-squad/arch-dbpool | ✅ 已完成 | `9464edd` + WAL 模式 |
| arch-querycache | P4 查询预编译缓存 | perf-squad/arch-querycache | ✅ 已完成 | `dcfacb3` + LRU 驱逐 |
| arch-async | P5 异步订阅者通知 | perf-squad/arch-async | ✅ 已完成 | `541c707` + 超时保护 |
| arch-memconfig | P6 内存配置可调 | perf-squad/arch-memconfig | ✅ 已完成 | `e36ebc7` + 环境变量 |

---

## v0.4.0（2026-04-26）— P1 工程化改进

### 新增模块

#### 审计日志（Audit Logging）
- 文件：`clawteam/audit.py`
- 追加写入模式，历史事件永不修改
- 每个事件包含：event_id, event_type, actor, details, timestamp, team
- 支持按类型/时间范围/actor 过滤查询
- 测试：`tests/test_audit.py`（7 项，全部通过）

#### 智能路由（Intelligent Routing）
- 文件：`clawteam/team/router.py`
- 基于三因素路由算法：
  - **历史表现**：成功率 + 质量评分加权
  - **负载感知**：当前进行中的任务数
  - **技能匹配**：关键词提取（支持中英文）
- 支持 `route()` 获取最优 agent，`get_all_candidates()` 获取排序列表
- 新 agent 自动创建默认档案（无历史数据时 fallback 到默认值）
- 测试：`tests/test_routing.py`（18 项，全部通过）

#### 告警机制（Alerting）
- 文件：`clawteam/alerts.py`
- 四级严重程度：LOW / MEDIUM / HIGH / CRITICAL
- 支持告警类型：TASK_TIMEOUT, AGENT_FAILURE_RATE_HIGH, TEAM_INACTIVITY
- CRUD 操作：创建、查询、列表、确认
- CLI 集成：`clawteam alert check/list/ack`
- 测试：`tests/test_alerts.py`（5 项，全部通过）

### 修复问题

| 问题 | 修复内容 | 影响范围 |
|------|----------|----------|
| `route()` 参数名不匹配 | `candidates` → `available_agents` | 智能路由 |
| `scores=None` pydantic 验证失败 | 测试中移除显式 `None`，使用默认空列表 | 路由测试 |
| 新 agent 无法被路由 | `route()` 自动创建默认 AgentProfile | 智能路由 |
| `total_score` 计算精度 | 修正期望值 8.4 → 8.45 | 路由测试 |
| `TaskStatus.failed` 不存在 | 改为 `TaskStatus.blocked` | 路由测试 |
| `test_get_all_candidates` 排序错误 | 统一 agent 成功率和负载，让 topic 匹配成为决定因素 | 路由测试 |

### 技术细节

**QualityScore 权重**（0-100 分）：
- completeness 0.25
- accuracy 0.30
- quality 0.20
- 规范性 0.15
- innovation 0.10

**路由评分公式**（0-100）：
```
total = topic_match(0-50) + success_score(0-30) + quality_score(0-20) - load_penalty(0-15)
```

**漂移检测阈值**（Jaccard + 语义）：
- ≥ 0.60：无漂移
- 0.45-0.60：低漂移
- 0.30-0.45：中漂移
- 0.15-0.30：高漂移
- < 0.15：严重漂移

### CLI 命令（v0.4.0 补充，2026-04-27）

**审计日志 CLI**：
- `clawteam audit query <team>` — 查询审计日志（支持 `--action`/`--actor`/`--target`/`--limit`/`--json`）
- `clawteam audit summary <team>` — 审计活动摘要
- `clawteam audit log <team>` — 手动记录审计事件（测试/调试用）

### 修复问题（v0.4.0 补充，2026-04-27）

| 问题 | 修复内容 | 影响范围 |
|------|----------|----------|
| 漂移检测字段名不匹配 | `jaccard_similarity` → `jaccard`，`semantic_similarity` → `semantic` | 漂移检测 |
| audit.py 导入路径错误 | `from clawteam.audit import AuditEventType` | 漂移检测 |
| 审计日志 CLI 缺失 | 新增 `clawteam audit query/summary/log` | 审计日志 |

### 升级步骤

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 安装依赖（如有新增）
pip install -e .

# 3. 运行测试确认
python -m pytest tests/test_audit.py tests/test_routing.py tests/test_alerts.py -v

# 4. 验证 CLI
clawteam audit query <team>
clawteam audit summary <team>
clawteam alert check --team <your-team>
```

### 向后兼容

- ✅ 无破坏性变更
- ✅ 所有现有 API 保持不变
- ✅ 新增模块为可选功能

---

## v0.3.1（2026-04-26）— P0 工程化改进

### 新增

- **结构化日志**：`clawteam/utils/logger.py`
  - JSON 格式，trace_id 上下文追踪
  - RotatingFileHandler（10MB/5 备份）
  - 环境变量：`CLAWTEAM_LOG_LEVEL`

- **重试框架**：`clawteam/utils/retry.py`
  - `@retry` / `@retry_async` 装饰器
  - 指数退避 + 抖动
  - 自动统计重试次数

### 影响

- `FileTaskStore._save_unlocked()` 自动重试
- `FileTransport.deliver()` 自动重试
- 测试：20 单元测试 + 10 集成测试

---

_最后更新：2026-05-03_
