# SpectrAI 与 ClawTeam 集成方案详细设计

## 1. 概述

本文档详细描述了将 SpectrAI 的核心功能模块集成到 ClawTeam 框架中的第一阶段方案。基于升级报告（docs/CLAWTEAM_UPGRADE_REPORT.md）的分析，我们确定了三个高优先级模块进行集成：
1. **DAG 任务管理**（`engine/dag_manager.py`, `engine/dag_resolver.py`）
2. **多平台适配器**（`adapters/*.py`）
3. **数据去重**（`pipeline/dedup.py`）

本方案重点评估了这些模块与 ClawTeam 现有架构的兼容性，并提供了详细的集成设计。

## 2. 现有架构分析

### 2.1 ClawTeam 当前架构

ClawTeam 目前是一个成熟的多 Agent 协作框架，主要包含：

- **团队协作模块**（`team/`）：
  - `dag.py`：现有的 DAG 依赖解析实现
  - `tasks.py`：任务管理
  - `router.py`：智能路由
  - `mailbox.py`：消息传递
  
- **传输层**（`transport/`）：
  - `redis.py`：Redis 传输实现，支持消息 TTL
  - `file.py`：文件传输实现
  - `p2p.py`：P2P 传输实现
  
- **工具模块**（`utils/`）：
  - `ttl.py`：消息 TTL 配置和工具
  - `retry.py`：自动重试框架
  - `logger.py`：结构化日志系统
  
- **Board 模块**（`board/`）：
  - WebSocket/SSE 实时监控面板
  - 任务状态推送

### 2.2 SpectrAI 核心模块分析（基于升级报告）

#### 2.2.1 DAG 任务管理模块

**功能特点**：
- 完整的 DAG（有向无环图）任务管理系统
- 支持 HARD/SOFT 依赖类型
- 自动循环依赖检测
- 拓扑排序生成执行顺序
- 实时状态跟踪和更新
- 并发控制和优先级调度

**与ClawTeam现有DAG的对比**：
- ClawTeam 的 `dag.py` 提供了基础的拓扑排序和循环检测
- SpectrAI 的 DAG 管理更复杂，支持动态依赖更新、就绪任务识别、执行计划管理
- SpectrAI 支持 HARD/SOFT 依赖类型，ClawTeam 只有简单的依赖关系

#### 2.2.2 多平台适配器模块

**功能特点**：
- 适配器模式支持主流平台（微博、抖音、小红书、知乎、B站）
- 统一的爬取接口（crawl, parse_item）
- HTTP/Playwright 双请求模式
- 内置反爬策略（UA 轮换、代理支持）
- 平台特定的解析逻辑

**与ClawTeam的集成点**：
- ClawTeam 目前没有专门的爬虫适配器
- 可以作为新的 `spawn/adapters.py` 扩展
- 与现有的 `spawn/` 模块集成

#### 2.2.3 数据去重模块

**功能特点**：
- Bloom Filter 实现高效大规模去重
- 支持多种去重策略（平台ID、URL、内容哈希）
- 可配置的误判率和容量
- 内存友好的实现

**与ClawTeam的集成点**：
- 可以作为新的 `utils/dedup.py` 模块
- 与现有的消息处理流程集成
- 利用现有的 TTL 机制进行去重缓存清理

## 3. 兼容性评估

### 3.1 技术栈兼容性

| 组件 | ClawTeam | SpectrAI (预期) | 兼容性 |
|------|----------|----------------|--------|
| Python 版本 | >=3.8 | >=3.8 | ✅ 完全兼容 |
| 异步框架 | asyncio | asyncio | ✅ 完全兼容 |
| Web 框架 | FastAPI | FastAPI | ✅ 完全兼容 |
| 数据模型 | Pydantic | Pydantic | ✅ 完全兼容 |
| Redis 客户端 | redis-py | redis-py | ✅ 完全兼容 |
| HTTP 客户端 | - | httpx | ✅ 无冲突 |
| 浏览器自动化 | - | Playwright | ✅ 可选依赖 |

### 3.2 架构兼容性

**优势**：
- 两者都采用模块化设计，易于集成
- 都使用异步编程模型，无缝协作
- 都支持配置驱动，便于统一管理
- ClawTeam 已有完善的传输层和 TTL 支持

**挑战**：
- SpectrAI 的模型定义需要与 ClawTeam 对齐
- 需要设计统一的配置管理方案
- DAG 功能需要与现有任务系统集成

### 3.3 依赖冲突风险

**低风险**：
- 主要依赖都是现代 Python 库
- ClawTeam 已经使用 redis-py，与 SpectrAI 兼容
- 新增依赖（httpx, playwright）可以设为可选

## 4. 集成方案设计

### 4.1 文件结构设计

```
clawteam/
├── adapters/              # 新增：多平台适配器
│   ├── __init__.py
│   ├── base.py           # 适配器基类（从SpectrAI迁移）
│   ├── weibo.py          # 微博适配器
│   ├── douyin.py         # 抖音适配器
│   ├── xiaohongshu.py    # 小红书适配器
│   ├── zhihu.py          # 知乎适配器
│   └── bilibili.py       # B站适配器
├── engine/               # 新增：核心引擎
│   ├── __init__.py
│   ├── dag_manager.py    # DAG任务管理（增强现有dag.py）
│   ├── dag_resolver.py   # DAG依赖解析器（新增）
│   └── scheduler.py      # 任务调度器（新增）
├── pipeline/             # 新增：数据管道
│   ├── __init__.py
│   └── dedup.py          # Bloom Filter去重（从SpectrAI迁移）
├── spawn/                # 现有：Agent生成
│   └── crawler_adapters.py  # 爬虫适配器集成点
└── utils/                # 现有：工具模块
    └── dedup.py          # 数据去重工具（链接到pipeline/dedup.py）
```

### 4.2 集成策略

#### 4.2.1 DAG 任务管理集成

**策略**：增强而非替换现有 DAG 功能

- 保留现有的 `team/dag.py` 基础功能
- 在 `engine/dag_manager.py` 中实现高级功能：
  - HARD/SOFT 依赖类型支持
  - 动态依赖更新
  - 执行计划管理
  - 实时状态跟踪

**API 扩展**：
```python
# 在 team/tasks.py 中扩展
class TaskItem:
    # 现有字段...
    dependency_type: str = "HARD"  # 新增：HARD/SOFT
    
# 在 team/dag.py 中扩展函数
def get_ready_tasks_advanced(tasks: list[TaskItem], respect_soft_deps: bool = True) -> list[TaskItem]:
    """增强版就绪任务识别，支持 SOFT 依赖"""
    # 实现逻辑...
```

#### 4.2.2 多平台适配器集成

**策略**：作为新的 Agent 类型集成

- 创建 `spawn/crawler_adapters.py` 作为适配器注册点
- 每个平台适配器实现标准的 Agent 接口
- 通过环境变量或配置启用特定平台

**Agent 集成**：
```python
# 在 spawn/registry.py 中注册爬虫 Agent
CRAWLER_AGENTS = {
    "weibo_crawler": WeiboAdapter,
    "douyin_crawler": DouyinAdapter,
    "xiaohongshu_crawler": XiaoHongShuAdapter,
    # ...
}

# 在 spawn/adapters.py 中扩展
def get_crawler_adapter(platform: str) -> BaseAdapter:
    """获取指定平台的爬虫适配器"""
    return CRAWLER_AGENTS.get(f"{platform}_crawler")
```

#### 4.2.3 数据去重集成

**策略**：作为消息处理中间件

- 创建 `pipeline/dedup.py` 实现 Bloom Filter 去重
- 在消息发送前调用去重检查
- 利用现有的 TTL 机制自动清理去重缓存

**集成点**：
```python
# 在 transport/base.py 中扩展
class Transport:
    def send_message(self, message: Message) -> bool:
        if self._dedup_enabled and self._deduplicator.is_duplicate(message):
            return False  # 消息重复，不发送
        # 继续正常发送逻辑...
```

### 4.3 配置方式

#### 4.3.1 环境变量

```bash
# 爬虫功能开关
CLAWTEAM_CRAWLER_ENABLED=true
CLAWTEAM_DAG_ADVANCED=true

# 数据去重配置
CLAWTEAM_DEDUP_ENABLED=true
CLAWTEAM_BLOOM_CAPACITY=1000000
CLAWTEAM_BLOOM_ERROR_RATE=0.001

# 平台适配器配置
CLAWTEAM_CRAWLER_PLATFORMS=weibo,douyin,xiaohongshu

# 性能配置
CLAWTEAM_MAX_CONCURRENT_TASKS=5
CLAWTEAM_REQUEST_TIMEOUT=30
```

#### 4.3.2 配置文件集成

```python
# 在 config.py 中扩展
class ClawTeamConfig:
    # 现有配置...
    
    # 新增爬虫配置
    crawler_enabled: bool = False
    dag_advanced: bool = False
    dedup_enabled: bool = False
    bloom_capacity: int = 1000000
    bloom_error_rate: float = 0.001
    crawler_platforms: list[str] = []
    max_concurrent_tasks: int = 5
    request_timeout: int = 30
```

### 4.4 API 设计

#### 4.4.1 任务管理扩展

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/tasks | 创建普通任务（现有）|
| POST | /api/v1/crawler/tasks | 创建爬虫任务（新增）|
| POST | /api/v1/dags | 创建 DAG 任务（现有增强）|
| POST | /api/v1/crawler/dags | 创建爬虫 DAG 任务（新增）|

#### 4.4.2 平台管理 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/crawler/platforms | 获取支持的平台列表 |
| GET | /api/v1/crawler/platforms/{platform} | 获取平台详情 |

#### 4.4.3 结果查询 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/crawler/tasks/{id}/results | 获取爬虫结果 |

## 5. 技术风险和缓解措施

### 5.1 技术风险

#### 5.1.1 DAG 功能冲突风险
- **风险描述**：SpectrAI 的 DAG 功能可能与 ClawTeam 现有的 DAG 实现有冲突
- **影响程度**：中
- **缓解措施**：
  - 采用增强而非替换策略
  - 保持向后兼容性
  - 提供功能开关控制

#### 5.1.2 性能影响风险
- **风险描述**：新增的爬虫功能和去重机制可能影响现有性能
- **影响程度**：低
- **缓解措施**：
  - 功能默认关闭，按需启用
  - 异步非阻塞实现
  - 性能基准测试

#### 5.1.3 依赖管理风险
- **风险描述**：新增依赖（httpx, playwright）增加部署复杂性
- **影响程度**：低
- **缓解措施**：
  - 将复杂依赖设为可选
  - 提供精简安装选项（pip install clawteam[crawler]）
  - 详细的依赖文档

### 5.2 集成风险

#### 5.2.1 功能耦合风险
- **风险描述**：爬虫功能与核心协作功能过度耦合
- **影响程度**：中
- **缓解措施**：
  - 保持清晰的模块边界
  - 使用插件式架构
  - 独立的配置和测试

#### 5.2.2 测试覆盖风险
- **风险描述**：新功能需要充分测试
- **影响程度**：高
- **缓解措施**：
  - 遵循现有的测试规范
  - 确保 80%+ 测试覆盖率
  - 集成测试验证端到端流程

## 6. 实施计划

### 6.1 第一阶段：核心功能集成（3-5天）

**目标**：完成三个高优先级模块的基础集成

**里程碑**：
1. DAG 功能增强完成
2. 多平台适配器集成完成
3. 数据去重集成完成
4. 基础 API 实现完成

**验收标准**：
- 能够创建和执行简单的爬虫任务
- 支持 HARD/SOFT 依赖类型的 DAG 任务
- 数据去重功能正常工作
- 所有单元测试通过

### 6.2 第二阶段：功能完善（2-3天）

**目标**：完善功能和用户体验

**任务**：
- 完善 API 文档和示例
- 添加错误处理和重试机制
- 优化性能和资源使用
- 完善配置管理

### 6.3 第三阶段：测试和文档（1-2天）

**目标**：确保稳定性和可用性

**任务**：
- 完整的集成测试
- 性能基准测试
- 用户文档编写
- 示例项目提供

## 7. 预期收益

### 7.1 功能增强
- 获得企业级爬虫能力
- 支持复杂任务编排（HARD/SOFT 依赖）
- 开箱即用的多平台支持

### 7.2 稳定性提升
- 数据去重避免资源浪费
- 错误处理和重试机制
- 统一的配置管理

### 7.3 可扩展性
- 插件式架构易于扩展新平台
- 模块化设计便于功能增减
- 与现有 ClawTeam 生态无缝集成

### 7.4 工程化水平
- 标准化 API 接口
- 完善的配置管理
- 充分的测试覆盖

## 8. 结论

SpectrAI 与 ClawTeam 的集成在技术上是可行的，两者在架构设计和编程范式上高度兼容。通过增强现有功能而非完全替换的方式，可以在保持 ClawTeam 稳定性的基础上，获得 SpectrAI 强大的爬虫能力。

建议按照本文档的设计方案，分阶段实施集成，优先完成第一阶段的核心功能集成，确保基础功能稳定后再逐步完善高级特性。