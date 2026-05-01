# Database/Repository 层架构设计

## 1. 设计目标

为 ClawTeam 实现一个完整的持久化存储层，参考 SpectrAI 的 DatabaseManager + Repository 模式，提供以下核心能力：

- **SQLite 数据库管理**：轻量级本地存储，支持内存降级方案
- **Repository 模式**：面向对象的数据访问层，封装 SQL 操作
- **版本化迁移**：支持数据库结构的平滑升级
- **连接池和并发**：支持多线程安全访问
- **数据表设计**：覆盖 sessions, activities, usage_stats, skills, tasks 等核心实体

## 2. 整体架构

```
clawteam/
├── storage/
│   ├── __init__.py
│   ├── database.py          # DatabaseManager 主类
│   ├── migrations.py        # 版本化迁移定义
│   ├── migration_runner.py  # 迁移执行器
│   ├── types.py            # 数据类型定义
│   └── repositories/
│       ├── __init__.py
│       ├── base.py         # Repository 基类
│       ├── session.py      # SessionRepository
│       ├── activity.py     # ActivityRepository  
│       ├── usage.py        # UsageRepository
│       ├── skill.py        # SkillRepository
│       └── task.py         # TaskRepository
```

## 3. DatabaseManager 设计

### 3.1 核心特性

- **SQLite 优先**：使用 `sqlite3` 模块（Python 标准库）
- **内存降级**：SQLite 不可用时自动切换到内存字典存储
- **WAL 模式**：启用 Write-Ahead Logging 提升并发性能
- **外键约束**：确保数据完整性
- **连接管理**：自动创建目录、处理异常

### 3.2 接口设计

```python
class DatabaseManager:
    def __init__(self, db_path: str):
        """初始化数据库管理器"""
        pass
        
    @property
    def sessions(self) -> SessionRepository:
        """获取会话仓库实例"""
        pass
        
    @property  
    def activities(self) -> ActivityRepository:
        """获取活动事件仓库实例"""
        pass
        
    @property
    def usage_stats(self) -> UsageRepository:
        """获取用量统计仓库实例"""
        pass
        
    @property
    def skills(self) -> SkillRepository:
        """获取技能仓库实例"""
        pass
        
    @property
    def tasks(self) -> TaskRepository:
        """获取任务仓库实例"""
        pass
        
    def close(self) -> None:
        """关闭数据库连接"""
        pass
```

## 4. Repository 基类设计

### 4.1 基类接口

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar

T = TypeVar('T')

class BaseRepository(ABC):
    def __init__(self, db_connection: Any, using_sqlite: bool):
        self.db = db_connection
        self.using_sqlite = using_sqlite
        self._memory_store: Dict[str, T] = {}
    
    @abstractmethod
    def create(self, data: Dict[str, Any]) -> T:
        """创建新记录"""
        pass
        
    @abstractmethod  
    def get(self, id: str) -> Optional[T]:
        """按ID获取记录"""
        pass
        
    @abstractmethod
    def get_all(self) -> List[T]:
        """获取所有记录"""
        pass
        
    @abstractmethod
    def update(self, id: str, updates: Dict[str, Any]) -> None:
        """更新记录"""
        pass
        
    @abstractmethod
    def delete(self, id: str) -> None:
        """删除记录"""
        pass
```

### 4.2 内存降级策略

每个 Repository 同时维护：
- **SQLite 存储**：当 `using_sqlite=True` 时使用
- **内存字典**：当 SQLite 不可用或作为缓存时使用

所有操作同时更新两种存储，确保数据一致性。

## 5. 数据表设计

### 5.1 sessions 表

```sql
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    task_id TEXT,
    name TEXT NOT NULL,
    working_directory TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',
    started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at DATETIME,
    exit_code INTEGER,
    estimated_tokens INTEGER NOT NULL DEFAULT 0,
    config TEXT,
    provider_id TEXT NOT NULL DEFAULT 'claude-code',
    claude_session_id TEXT,
    name_locked INTEGER NOT NULL DEFAULT 0
);
```

### 5.2 activity_events 表

```sql
CREATE TABLE IF NOT EXISTS activity_events (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    type TEXT NOT NULL,
    detail TEXT NOT NULL,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
);
```

### 5.3 usage_stats 表

```sql
CREATE TABLE IF NOT EXISTS usage_stats (
    session_id TEXT NOT NULL,
    date TEXT NOT NULL,
    tokens_used INTEGER NOT NULL DEFAULT 0,
    minutes_active INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (session_id, date),
    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
);
```

### 5.4 skills 表

```sql
CREATE TABLE IF NOT EXISTS skills (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    category TEXT DEFAULT 'general',
    slash_command TEXT,
    type TEXT NOT NULL DEFAULT 'prompt',
    compatible_providers TEXT NOT NULL DEFAULT '"all"',
    prompt_template TEXT,
    system_prompt_addition TEXT,
    input_variables TEXT,
    is_enabled INTEGER NOT NULL DEFAULT 1,
    source TEXT NOT NULL DEFAULT 'custom',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

### 5.5 tasks 表

```sql
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'todo',
    priority TEXT NOT NULL DEFAULT 'medium',
    tags TEXT,
    parent_task_id TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    FOREIGN KEY (parent_task_id) REFERENCES tasks (id)
);
```

## 6. 迁移机制设计

### 6.1 迁移定义

```python
from typing import Protocol

class Migration(Protocol):
    version: int
    description: str
    
    def up(self, db_connection) -> None:
        """执行迁移逻辑"""
        pass

MIGRATIONS: List[Migration] = [
    # v1: 初始表结构
    # v2: 添加新列
    # v3: 修改表结构
    # ...
]
```

### 6.2 迁移执行器

- **版本跟踪**：使用 `schema_version` 表记录已执行的迁移
- **增量执行**：只执行版本号大于当前版本的迁移
- **错误容忍**：单个迁移失败不影响后续迁移执行
- **原子性**：每个迁移在事务中执行

### 6.3 迁移流程

1. 检查 `schema_version` 表是否存在，不存在则创建
2. 查询当前最大版本号
3. 过滤出待执行的迁移（version > current_version）
4. 按版本号升序执行每个迁移
5. 记录成功执行的迁移版本

## 7. 并发访问支持

### 7.1 连接池设计

- **线程局部存储**：每个线程使用独立的数据库连接
- **连接复用**：避免频繁创建/销毁连接的开销
- **自动清理**：线程结束时自动关闭连接

### 7.2 读写锁

- **读操作**：多个线程可同时读取
- **写操作**：独占锁确保数据一致性
- **WAL 模式**：SQLite 的 Write-Ahead Logging 支持高并发读写

### 7.3 事务管理

- **自动事务**：每个 Repository 方法自动包装在事务中
- **手动事务**：支持跨多个 Repository 的复合操作
- **回滚机制**：异常时自动回滚

## 8. 具体 Repository 实现

### 8.1 SessionRepository

- **会话生命周期管理**：创建、更新状态、删除
- **批量查询**：按状态、时间范围等条件查询
- **孤儿会话清理**：定期清理异常终止的会话

### 8.2 ActivityRepository  

- **活动事件记录**：记录 AI 的各种活动（工具调用、文件编辑等）
- **去重机制**：基于时间窗口避免重复事件
- **批量插入**：优化高频事件的写入性能

### 8.3 UsageRepository

- **用量统计**：按会话和日期统计 Token 使用量
- **定期 flush**：内存中的用量定期持久化到数据库
- **历史查询**：支持按日期范围查询用量历史

### 8.4 SkillRepository

- **技能管理**：CRUD 操作管理技能定义
- **命令拦截**：根据 `/command` 快速查找启用的技能
- **兼容性过滤**：按 Provider 过滤兼容的技能

### 8.5 TaskRepository

- **任务管理**：支持任务的层级结构（父子任务）
- **状态跟踪**：任务状态变更历史
- **批量操作**：支持批量更新任务状态

## 9. 错误处理和日志

### 9.1 异常处理

- **数据库异常**：捕获并记录 SQLite 异常
- **降级策略**：SQLite 失败时自动切换到内存模式
- **数据恢复**：内存模式下定期尝试重新连接 SQLite

### 9.2 日志记录

- **迁移日志**：记录每个迁移的执行状态
- **操作日志**：关键数据库操作的日志记录
- **性能日志**：慢查询和高负载情况的监控

## 10. 测试策略

### 10.1 单元测试

- **内存模式测试**：快速验证 Repository 逻辑
- **SQLite 模式测试**：验证实际数据库操作
- **迁移测试**：验证迁移的正确性和兼容性

### 10.2 集成测试

- **并发测试**：多线程同时访问的稳定性测试
- **大数据量测试**：大量数据下的性能测试
- **异常场景测试**：磁盘满、权限不足等异常情况

## 11. 实施计划

### 第一阶段：基础框架（2-3天）
- 创建 DatabaseManager 基础类
- 实现 Repository 基类
- 设计数据表结构

### 第二阶段：核心 Repository（3-4天）
- 实现 SessionRepository 和 ActivityRepository
- 实现 UsageRepository
- 基本的 CRUD 操作

### 第三阶段：高级功能（2-3天）
- 实现 SkillRepository 和 TaskRepository
- 完善迁移机制
- 添加并发支持

### 第四阶段：测试和优化（2-3天）
- 编写完整测试套件
- 性能优化和错误处理
- 文档完善

## 12. 与现有架构集成

### 12.1 替换 store 模块
- 将现有的 `clawteam/store` 模块逐步迁移到新的 storage 架构
- 保持向后兼容的适配层

### 12.2 集成到会话管理
- SessionManager 使用新的 DatabaseManager
- 活动事件通过 ActivityRepository 记录
- 用量统计通过 UsageRepository 管理

### 12.3 技能系统集成
- SkillEngine 使用 SkillRepository 加载技能
- `/command` 拦截器查询数据库获取技能定义

## 结论

这个 Database/Repository 设计提供了完整的持久化存储解决方案，既借鉴了 SpectrAI 的成熟模式，又针对 Python 环境和 ClawTeam 的具体需求进行了优化。通过分阶段实施，可以逐步替换现有的存储机制，最终实现一个高性能、高可靠性的数据存储层。