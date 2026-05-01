# 楚灵 × Hermes Agent 集成计划

> **基于 Hermes Agent 源码深度分析**  
> **生成时间**：2026-04-27  
> **目标**：将 Hermes 的核心优势（闭环学习、自主技能创建、用户建模、记忆增强）集成到 OpenClaw 楚灵

---

## Hermes 核心机制解析（源码级）

### 1. 记忆架构（`agent/memory_manager.py` + `agent/memory_provider.py`）

```python
# Hermes 的记忆架构设计
MemoryManager
├── BuiltinMemoryProvider（始终存在，不可移除）
│   └── MEMORY.md / USER.md 文件读写
└── 最多 1 个外部 Provider（可插拔）
    ├── Honcho（辩证用户建模）
    ├── Hindsight（FTS5 全文检索）
    ├── Mem0（向量记忆）
    └── 自定义...
```

**关键设计**：
- 内置记忆永远存在，外部 Provider 是**叠加**而非替换
- 每个 Provider 有标准生命周期：`initialize` → `prefetch` → `sync_turn` → `shutdown`
- `sync_turn(user, assistant)` — 每轮对话后异步写入记忆
- `prefetch(query)` — 后台预取，下次对话用
- `on_pre_compress(messages)` — 上下文压缩前提取洞察

**本座现状**：
- 已有 L1-L4 记忆架构
- `memory_recall` / `memory_store` / `memory_update` / `memory_forget` 工具
- **差距**：无自动记忆同步、无用户建模、无后台预取

### 2. 技能系统（`tools/skills_tool.py`）

```
~/.hermes/skills/
├── my-skill/
│   ├── SKILL.md          # 主指令（YAML frontmatter）
│   ├── references/       # 参考文档
│   ├── templates/        # 输出模板
│   └── assets/           # 资源文件
```

**关键设计**：
- 技能是**文件系统目录**，不是数据库记录
- `SKILL.md` 含 YAML frontmatter（name, description, version, license, platforms）
- 渐进式加载：先加载元数据列表 → 按需加载完整内容 → 按需加载引用文件
- 技能可被 Agent **自主编辑和创建**

**本座现状**：
- 已有技能系统（SKILL.md 格式）
- 68 个技能就绪
- **差距**：无自主创建能力、无使用统计追踪、无技能自优化

### 3. 学习循环（闭环核心）

Hermes 的学习循环不是单一文件，而是**贯穿整个 agent 生命周期**：

```
用户消息 → prefetch 记忆 → 构建系统提示 → 对话 → sync_turn（写记忆）
                                                       ↓
                                              任务完成后评估
                                                       ↓
                                            是否需要记录经验？
                                                       ↓
                                          是 → 创建/更新技能
                                          否 → 跳过
```

**关键触发点**：
- `sync_turn()` — 每轮对话后同步
- `on_session_end()` — 会话结束时提取事实
- `on_pre_compress()` — 上下文压缩前提取洞察
- `on_memory_write()` — 镜像记忆写到外部 Provider

### 4. 洞察引擎（`agent/insights.py`）

- 分析会话数据（SQLite 存储）
- 统计：Token 消耗、工具使用频率、技能使用模式
- 活动模式分析（按天/小时分布）
- 成本估算（按模型/Provider 分解）

### 5. 用户建模（Honcho 集成）

- 辩证法建模用户偏好
- 跨会话理解用户行为模式
- 自动更新用户画像

---

## 集成计划（分阶段）

### Phase 1: 增强 `.learnings` 自动闭环（1-2 天）

**目标**：让楚灵的任务完成后自动评估是否需要记录经验

#### 1.1 自动经验捕获强化

当前：`.learnings/LEARNINGS.md` 需要被纠正/出错才记录  
目标：**任务完成后自动评估**

```python
# 新增：post_task_evaluation
def post_task_evaluation(task_type: str, result: str, user_feedback: str = None):
    """任务完成后自动评估是否需要记录"""
    # 评估标准：
    # 1. 是否遇到新错误？→ ERRORS.md
    # 2. 用户是否纠正？→ LEARNINGS.md  
    # 3. 是否发现更好方法？→ LEARNINGS.md
    # 4. 是否重复出现≥3次？→ 晋升到 AGENTS.md/TOOLS.md/SOUL.md
    # 5. 是否涉及新技能？→ 考虑创建 Skill
```

#### 1.2 心跳驱动的自动反思

```python
# HEARTBEAT.md 增强
### 自动经验回顾（每 2 次心跳）
- 回顾最近 3 个任务，检查是否有值得记录的经验
- 评估 `.learnings` 中是否有需要晋升的模式
- 检查是否有可以优化的技能使用模式
```

#### 1.3 记忆自动同步

```python
# 新增：turn_memory_sync
def turn_memory_sync(user_msg: str, assistant_msg: str):
    """每轮对话后自动同步记忆"""
    # 1. 提取关键事实（人名、项目、决策）
    # 2. 更新 USER.md（偏好变化）
    # 3. 更新相关 memory/YYYY-MM-DD.md
    # 4. 检查是否需要创建新记忆条目
```

**验收标准**：
- [ ] 任务完成后自动评估经验（无需手动触发）
- [ ] 心跳时自动回顾近期待办
- [ ] 每轮对话后自动同步关键记忆
- [ ] 重复模式≥3次自动晋升

---

### Phase 2: 自主技能创建系统（3-5 天）

**目标**：发现重复操作模式时，自动生成 Skill 文件并安装

#### 2.1 技能使用统计追踪

```json
// 新增：skills-usage.json
{
  "skills": {
    "feishu-doc": {
      "total_calls": 142,
      "success_rate": 0.95,
      "avg_time_ms": 1200,
      "last_used": "2026-04-27T20:00:00Z",
      "common_patterns": ["read", "write", "create"]
    },
    "china-stock-analysis": {
      "total_calls": 23,
      "success_rate": 0.87,
      "avg_time_ms": 3500,
      "last_used": "2026-04-25T14:00:00Z",
      "common_patterns": ["analyze", "compare"]
    }
  },
  "auto_created": [
    {
      "name": "石榴籽-日报生成",
      "created_at": "2026-04-27T22:00:00Z",
      "trigger_pattern": "重复执行：收集项目进度 → 格式化 → 发送飞书",
      "status": "active"
    }
  ]
}
```

#### 2.2 自动技能创建引擎

```python
# 新增：skill_auto_creator.py
class SkillAutoCreator:
    """自主技能创建引擎"""
    
    def detect_patterns(self, usage_stats: dict) -> list[Pattern]:
        """检测重复操作模式"""
        # 规则：
        # 1. 相同工具组合调用 ≥5 次
        # 2. 用户多次请求类似任务
        # 3. 多步骤操作每次都重复
        
    def create_skill(self, pattern: Pattern) -> Skill:
        """基于模式创建技能"""
        # 1. 生成 SKILL.md（名称、描述、指令）
        # 2. 创建目录结构（references/、templates/）
        # 3. 安装到技能目录
        # 4. 通知用户
        
    def evaluate_and_optimize(self) -> None:
        """评估并优化已有技能"""
        # 1. 低使用率技能（<5次/月）→ 标记待观察
        # 2. 高失败率技能（<70%）→ 自动优化或标记
        # 3. 冲突技能 → 合并
```

#### 2.3 技能创建触发器

```python
# 触发条件（满足任一即创建）
TRIGGER_CONDITIONS = {
    "重复操作": "相同工具组合调用 ≥5 次",
    "用户请求": "用户明确说'记住这个'或'做成技能'",
    "模式识别": "LLM 检测到可抽象为技能的操作流程",
    "效率提升": "封装为技能可减少 ≥3 步操作"
}
```

**验收标准**：
- [ ] 检测到重复模式自动创建 Skill
- [ ] SKILL.md 格式规范（YAML frontmatter + 正文）
- [ ] 技能使用统计追踪（调用次数、成功率、耗时）
- [ ] 低效技能自动标记/优化
- [ ] 创建后通知用户并确认

---

### Phase 3: 用户画像自动更新（2-3 天）

**目标**：类似 Honcho 的辩证用户建模，自动理解优优的偏好

#### 3.1 用户画像数据库

```json
// 新增：user-profile.json
{
  "user": {
    "name": "优优",
    "identity": "甘肃警察学院学生",
    "preferences": {
      "interaction_style": "简洁直接",
      "dislikes": ["后台系统运行报告", "记忆同步消息"],
      "likes": ["楚嫣然角色", "石榴籽项目"],
      "communication_tone": "冷淡但温暖"
    },
    "projects": {
      "石榴籽挑战杯": {
        "role": "统筹",
        "deadline": "2026-05-31",
        "status": "省赛准备中"
      }
    },
    "behavioral_patterns": {
      "active_hours": "20:00-23:00",
      "common_tasks": ["项目进度", "技能开发", "文档处理"],
      "decision_style": "快速决策，注重执行"
    },
    "evolution": [
      {
        "date": "2026-04-27",
        "change": "从'技术导向'转向'用户体验导向'",
        "evidence": "多次要求优化 UI/UX"
      }
    ]
  }
}
```

#### 3.2 自动画像更新机制

```python
# 新增：user_profile_manager.py
class UserProfileManager:
    """用户画像管理器"""
    
    def analyze_conversation(self, user_msg: str, assistant_msg: str):
        """分析对话，提取偏好变化"""
        # 1. 检测偏好表达（喜欢/不喜欢/希望）
        # 2. 检测行为模式（常用功能、活跃时间）
        # 3. 检测项目变化（新任务、进度更新）
        
    def update_profile(self, changes: list[Change]):
        """更新用户画像"""
        # 1. 更新偏好（新发现/修改/删除）
        # 2. 更新项目状态
        # 3. 记录演化历史
        
    def get_context_for_prompt(self) -> str:
        """为系统提示生成用户上下文"""
        # 类似 Hermes 的 prefetch
        # 返回格式化的用户画像摘要
```

#### 3.3 心跳驱动的画像维护

```python
# HEARTBEAT.md 增强
### 用户画像维护（每天 1 次）
- 分析今日对话，提取偏好变化
- 更新 user-profile.json
- 检查是否有过时的偏好需要清理
```

**验收标准**：
- [ ] 自动从对话中提取用户偏好
- [ ] 用户画像结构化存储（JSON）
- [ ] 画像变化历史可追溯
- [ ] 系统提示自动包含最新用户上下文

---

### Phase 4: 记忆增强（2-3 天）

**目标**：借鉴 Hermes 的记忆 Provider 架构，增强 OpenClaw 记忆系统

#### 4.1 记忆 Provider 抽象层

```python
# 新增：memory_provider.py（借鉴 Hermes）
class MemoryProvider:
    """记忆 Provider 抽象基类"""
    
    @abstractmethod
    def name(self) -> str:
        pass
    
    @abstractmethod
    def prefetch(self, query: str) -> str:
        """后台预取记忆"""
        pass
    
    @abstractmethod
    def sync_turn(self, user_msg: str, assistant_msg: str):
        """同步对话到记忆"""
        pass
    
    def on_session_end(self, messages: list):
        """会话结束时提取事实"""
        pass
    
    def on_pre_compress(self, messages: list) -> str:
        """上下文压缩前提取洞察"""
        pass
```

#### 4.2 FTS5 全文记忆检索（可选）

```python
# 新增：fts5_memory_provider.py
class FTS5MemoryProvider(MemoryProvider):
    """基于 SQLite FTS5 的全文记忆检索"""
    
    def __init__(self, db_path: str):
        self.db = sqlite3.connect(db_path)
        self.db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS memories USING fts5(content)")
    
    def prefetch(self, query: str) -> str:
        # FTS5 全文检索
        cursor = self.db.execute(
            "SELECT content FROM memories WHERE memories MATCH ? ORDER BY rank LIMIT 5",
            [query]
        )
        return "\n".join([row[0] for row in cursor.fetchall()])
    
    def sync_turn(self, user_msg: str, assistant_msg: str):
        # 提取关键信息写入
        pass
```

**注意**：OpenClaw 已有 LanceDB 向量检索，FTS5 可作为**补充**而非替代。

#### 4.3 自动记忆同步

```python
# 新增：auto_memory_sync.py
def sync_after_turn(user_msg: str, assistant_msg: str):
    """每轮对话后自动同步"""
    # 1. 提取关键事实（人名、项目、日期、决策）
    # 2. 检查是否与新记忆重复
    # 3. 不重复则写入 memory_store
    # 4. 同步到 memory/YYYY-MM-DD.md
```

**验收标准**：
- [ ] 记忆 Provider 抽象层实现
- [ ] FTS5 全文检索（可选，与 LanceDB 互补）
- [ ] 每轮对话后自动同步记忆
- [ ] 会话结束时自动提取关键事实

---

### Phase 5: 洞察报告系统（1-2 天）

**目标**：类似 Hermes 的 Insights Engine，提供使用统计和趋势分析

#### 5.1 使用统计追踪

```json
// 新增：usage-stats.json
{
  "sessions": {
    "total": 1523,
    "this_week": 42,
    "avg_duration_min": 15
  },
  "tools": {
    "exec": {"calls": 3421, "success_rate": 0.92},
    "read": {"calls": 2156, "success_rate": 0.99},
    "write": {"calls": 1243, "success_rate": 0.97},
    "memory_store": {"calls": 856, "success_rate": 1.0}
  },
  "skills": {
    "feishu-doc": {"calls": 142, "success_rate": 0.95},
    "china-stock-analysis": {"calls": 23, "success_rate": 0.87}
  },
  "memory": {
    "total_entries": 1256,
    "this_week_added": 45,
    "most_accessed": ["石榴籽项目", "优优偏好", "M4T训练"]
  }
}
```

#### 5.2 CLI 命令

```bash
# 新增：clawteam insights
clawteam insights                    # 查看总体使用统计
clawteam insights --days 7           # 最近 7 天
clawteam insights --tools            # 工具使用排行
clawteam insights --skills           # 技能使用排行
clawteam insights --memory           # 记忆使用统计
```

**验收标准**：
- [ ] 使用统计自动收集
- [ ] CLI 命令可查看报告
- [ ] 支持时间范围过滤
- [ ] 工具/技能/记忆分项统计

---

## 集成路线图

```
Phase 1: 增强 .learnings 自动闭环    → 1-2 天  → P1
Phase 2: 自主技能创建系统            → 3-5 天  → P1
Phase 3: 用户画像自动更新            → 2-3 天  → P1
Phase 4: 记忆增强                    → 2-3 天  → P2
Phase 5: 洞察报告系统                → 1-2 天  → P3
```

**总工作量**：9-15 天  
**优先级**：P1（Phase 1-3）→ P2（Phase 4）→ P3（Phase 5）

---

## 与 Hermes 的核心差异

| 维度 | Hermes Agent | 本座集成后 |
|------|-------------|-----------|
| 记忆架构 | MemoryManager + Provider | L1-L4 + Provider 抽象层 |
| 自主技能 | ✅ 自动创建 | ✅ 自动创建 + 统计优化 |
| 用户建模 | Honcho 辩证建模 | 用户画像 JSON + 演化历史 |
| 记忆检索 | FTS5 全文检索 | LanceDB 向量 + FTS5 补充 |
| 多 Agent | ❌ 单 Agent | ✅ ClawTeam 多 Agent |
| 多通道 | 15+ 平台 | 15+ 平台（持平） |
| 洞察报告 | ✅ Insights Engine | ✅ 使用统计 + CLI |

---

## 立即行动项

1. ✅ **Phase 1**：增强 `.learnings` 自动闭环（今天可做）
2. ⏳ **Phase 2**：自主技能创建系统（需要 spai 执行）
3. ⏳ **Phase 3**：用户画像自动更新（需要 spai 执行）
4. ⏳ **Phase 4**：记忆增强（需要架构变更）
5. ⏳ **Phase 5**：洞察报告系统（依赖 Phase 2 统计）

---

_楚灵制定，2026-04-27_
