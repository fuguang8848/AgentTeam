# AgentTeam 依赖审计报告

> 审计时间：2025-06-04  
> 审计范围：依赖结构、安全扫描、平台兼容性、Docker 优化建议

---

## 1. 依赖结构总览

### 1.1 直接依赖 (Direct Dependencies)

| 包名 | 版本 | 用途 | 体积评估 | 风险 |
|------|------|------|----------|------|
| typer | >=0.12.0,<1.0.0 | CLI 框架 | 轻量 | ✅ 低 |
| pydantic | >=2.0.0,<3.0.0 | 数据验证 | 中等 | ✅ 低 |
| rich | >=13.0.0,<15.0.0 | 终端美化 | **较重** | ⚠️ 中 |
| psutil | >=5.9.0 | 系统信息 | 轻量 | ✅ 低 |
| pyyaml | >=6.0.0 | YAML 解析 | 轻量 | ✅ 低 |
| tomli | >=2.0.0 | TOML 解析 (Python <3.11) | 轻量 | ✅ 低 |

### 1.2 可选依赖组 (Optional Dependencies)

| 组名 | 依赖 | 用途 |
|------|------|------|
| `dev` | pytest>=9.0.0, pytest-asyncio>=0.23.0, ruff>=0.1.0 | 开发测试 |
| `p2p` | pyzmq>=25.0.0,<27.0.0 | P2P 通信 |
| `redis` | redis>=4.5.0,<6.0.0 | Redis 消息传输 |

### 1.3 传递依赖统计

```
poetry.lock 总包数: 32
├── 核心依赖 (optional=false): 17
├── 可选依赖 (optional=true): 15
└── 实际安装: 核心 + 选定可选组
```

### 1.4 体积 TOP10 重依赖

| 排名 | 包名 | 版本 | 传递依赖 | 备注 |
|------|------|------|----------|------|
| 1 | rich | 14.3.4 | pygments, markdown-it-py, mdurl | 终端美化框架 |
| 2 | pydantic | 2.13.3 | pydantic-core | 数据验证 |
| 3 | pyzmq | 26.4.0 | cffi (optional) | P2P 可选 |
| 4 | redis | 5.3.1 | async-timeout, urllib3 | Redis 可选 |
| 5 | ruff | 0.15.12 | - | 开发依赖 |
| 6 | pytest | 9.0.3 | iniconfig, exceptiongroup | 开发依赖 |
| 7 | typing-inspection | 0.4.2 | - | 类型检查工具 |
| 8 | shellingham | 1.5.4 | - | 进程检测 |
| 9 | annotated-doc | 0.0.4 | - | 文档注解 |
| 10 | annotated-types | 0.7.0 | - | 类型工具 |

---

## 2. 安全漏洞清单 (pip-audit 结果)

### 2.1 高危漏洞 (需立即修复)

| 漏洞 ID | 包 | 版本 | 修复版本 | 说明 |
|---------|-----|------|----------|------|
| CVE-2026-24049 | wheel | 0.45.1 | 0.46.2 | wheel 安全漏洞 |

### 2.2 中危漏洞 (建议修复)

| 漏洞 ID | 包 | 版本 | 修复版本 | 说明 |
|---------|-----|------|----------|------|
| CVE-2025-27477 | pytest | 9.0.3 | 未发布 | pytest 安全问题 |
| CVE-2026-34515 | aiohttp | 3.13.3 | 3.13.4 | Windows 静态资源处理信息泄露 |
| CVE-2026-34513 | aiohttp | 3.13.3 | 3.13.4 | DNS 缓存 DoS 风险 |
| CVE-2026-34517 | aiohttp | 3.13.3 | 3.13.4 | Multipart 请求内存耗尽 |
| PYSEC-2026-142 | urllib3 | 2.6.3 | 2.7.0 | urllib3 安全更新 |
| PYSEC-2026-161 | urllib3 | 2.6.3 | 2.7.0 | urllib3 安全更新 |

### 2.3 低危/信息级

| 漏洞 ID | 包 | 版本 | 说明 |
|---------|-----|------|------|
| GHSA-m5qp-6w8w-w647 | aiohttp | 3.13.3 | 响应头处理问题 |
| GHSA-3wq7-rqq7-wx6j | aiohttp | 3.13.3 | Multipart 字段处理 |
| GHSA-c427-h43c-vf67 | aiohttp | 3.13.3 | Host 头处理 |

### 2.4 无法审计的包 (PyPI 未收录)

| 包名 | 版本 | 状态 |
|------|------|------|
| agentmemory | 1.0.0 | 内部包 |
| agentteam | 0.5.1 | 本地包 |
| clawteam | 0.5.1 | 内部包 |
| torch | 2.11.0+cu130 | CUDA 定制版 |
| super-thinking | 0.1.0 | 内部包 |

---

## 3. Python 版本兼容性矩阵

### 3.1 声明支持 vs 实际使用

| 版本 | 声明支持 | 语法特性使用 | 兼容性 | 备注 |
|------|----------|--------------|--------|------|
| 3.9 | ❌ | 无 | ⚠️ 需测试 | pyproject.toml 要求 >=3.10 |
| 3.10 | ✅ | 无 match/case | ✅ 良好 | 项目使用基础语法 |
| 3.11 | ✅ | 无特殊特性 | ✅ 良好 | 推荐版本 |
| 3.12 | ✅ | 无特殊特性 | ✅ 良好 | 稳定版本 |
| 3.13 | ✅ | 无特殊特性 | ✅ 良好 | 当前测试环境 |

### 3.2 语法兼容性分析

```bash
# 检查结果：
- match/case (Python 3.10+): ❌ 未使用
- 类型联合语法 X | Y (Python 3.10+): ❌ 未使用
- PEP 604 union types: ❌ 未使用
- asyncio 增强: ❌ 未使用
```

**结论**：代码语法保守，向下兼容性好，可考虑放宽至 Python 3.9。

### 3.3 条件依赖分析

```toml
# pyproject.toml 中的条件依赖
tomli>=2.0.0; python_version < '3.11'  # Python 3.11+ 自带 tomllib
```

---

## 4. 平台兼容性风险点

### 4.1 跨平台问题扫描结果

| 问题类型 | 搜索模式 | 匹配数 | 风险等级 |
|----------|----------|--------|----------|
| 路径分隔符硬编码 | `os\.sep` | 0 | ✅ 无 |
| 路径拼接 | `os\.path\.join` | 0 | ✅ 无 |
| Shell 执行 | `subprocess.*shell=True` | 0 | ✅ 无 |
| 信号处理 | `SIGTERM\|SIGKILL` | 0 | ✅ 无 |
| 硬编码编码 | `open\([^)]*encoding` | 0 | ✅ 无 |

### 4.2 平台兼容性评估

| 平台 | 兼容性 | 备注 |
|------|--------|------|
| Windows | ✅ 良好 | colorama 处理跨平台彩色输出 |
| Linux | ✅ 良好 | 标准 POSIX 兼容 |
| macOS | ✅ 良好 | 无特殊依赖 |
| Alpine Linux | ⚠️ 需验证 | musllinux wheel 支持情况 |

### 4.3 Dockerfile 平台问题

```dockerfile
# 当前 Dockerfile 问题：
1. 使用 python:3.10-slim (Debian-based)
2. 包含非必要工具 vim
3. 无 multi-stage 构建
4. 无 distroless/alpine 选项
```

---

## 5. Docker 镜像基线

### 5.1 当前配置

| 项目 | 当前值 | 评估 |
|------|--------|------|
| 基础镜像 | `python:3.10-slim` | ⚠️ 可优化 |
| 镜像大小 | ~500MB (估算) | ⚠️ 偏大 |
| Multi-stage | ❌ 无 | ❌ 可优化 |
| 非 root 用户 | ✅ 有 | ✅ 良好 |
| Healthcheck | ✅ 有 | ✅ 良好 |

### 5.2 Dockerfile 问题清单

1. **不必要的系统包**：`vim` 在容器中通常不需要
2. **无 multi-stage**：导致最终镜像包含构建工具
3. **pip install poetry**：增加一层和大小
4. **无镜像分层优化**：依赖安装未充分利用缓存

### 5.3 优化建议

```dockerfile
# 建议的优化版本
# Stage 1: Build
FROM python:3.10-slim AS builder
RUN pip install poetry
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-dev --no-interaction

# Stage 2: Runtime
FROM python:3.10-slim
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
# ... 其他复制
```

---

## 6. 可选依赖 / Feature Flag 设计现状

### 6.1 当前设计

| Feature | 实现方式 | 依赖 | 可插拔 |
|---------|----------|------|--------|
| CLI | typer | - | ✅ |
| P2P 通信 | pyzmq | 可选组 | ✅ |
| Redis 传输 | redis-py | 可选组 | ✅ |
| 开发工具 | pytest/ruff | dev 组 | ✅ |
| 数据验证 | pydantic | 核心 | ❌ |

### 6.2 Entry Points 检查

```bash
# 当前 entry point：
[project.scripts]
agentteam = "agentteam.cli.commands:app"
```

**评估**：
- ✅ 使用标准 entry point
- ❌ 无插件动态加载机制
- ❌ 无 importlib 动态导入

### 6.3 依赖规避现状

| 场景 | 当前实现 | 优化空间 |
|------|----------|----------|
| YAML 解析 | pyyaml | ✅ 必需 |
| JSON 解析 | 内置 json | ✅ 无依赖 |
| TOML 解析 | tomli (条件) | ✅ 已优化 |
| 数据验证 | pydantic | ⚠️ 较重但必需 |
| 终端输出 | rich | ⚠️ 较重但必需 |

---

## 7. "零依赖核心 + 可选特性" 重构建议

### 7.1 核心层 (Core) - 最小依赖

```toml
[project]
name = "agentteam-core"
dependencies = [
    "pydantic>=2.0.0,<3.0.0",
]
```

**核心模块**：
- `agentteam/core.py` - 核心抽象
- `agentteam/config.py` - 配置管理
- `agentteam/exceptions.py` - 异常定义
- `agentteam/identity.py` - 身份管理

### 7.2 CLI 层 (需要 typer)

```toml
[project.optional-dependencies]
cli = ["typer>=0.12.0"]
```

### 7.3 传输层 (Transport)

```toml
[project.optional-dependencies]
transport-file = []  # 无外部依赖
transport-redis = ["redis>=4.5.0"]
transport-p2p = ["pyzmq>=25.0.0"]
```

### 7.4 UI 层 (UI)

```toml
[project.optional-dependencies]
ui-basic = []  # 纯文本输出
ui-rich = ["rich>=13.0.0"]  # 富文本输出
```

### 7.5 开发层 (Dev)

```toml
[project.optional-dependencies]
dev = [
    "pytest>=9.0.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.1.0",
]
```

### 7.6 推荐的依赖分组

```toml
[project.optional-dependencies]
# 最小安装
minimal = []

# CLI 基础
cli = ["typer>=0.12.0"]
cli-rich = ["typer>=0.12.0", "rich>=13.0.0"]

# 传输方式
file-transport = []  # 无额外依赖
redis-transport = ["redis>=4.5.0,<6.0.0"]
p2p-transport = ["pyzmq>=25.0.0,<27.0.0"]

# 开发
dev = ["pytest>=9.0.0", "pytest-asyncio>=0.23.0", "ruff>=0.1.0"]

# 全量
full = ["typer>=0.12.0", "rich>=13.0.0", "redis>=4.5.0,<6.0.0", "pyzmq>=25.0.0,<27.0.0"]
```

---

## 8. 升级行动计划

### 8.1 短期 (1-2 周)

- [ ] 修复高危漏洞 wheel
- [ ] 移除 Dockerfile 中的 vim
- [ ] 添加 multi-stage 构建

### 8.2 中期 (1 个月)

- [ ] 重构依赖分组，实现可选特性
- [ ] 添加插件动态加载机制
- [ ] 测试 Python 3.9 兼容性
- [ ] 考虑 Alpine 镜像

### 8.3 长期 (2-3 个月)

- [ ] 评估将 rich 设为可选
- [ ] 评估轻量级替代方案
- [ ] 建立依赖安全监控流程

---

## 附录：快速检查命令

```bash
# 依赖总数
grep -c '^\[\[package\]\]' poetry.lock

# 可选依赖
grep 'optional = true' poetry.lock | wc -l

# 安全扫描
pip-audit

# 平台问题
rg "os\.sep|shell=True|SIGTERM" agentteam/ --type py

# Python 版本检查
rg "match |case :" agentteam/ --type py
```
