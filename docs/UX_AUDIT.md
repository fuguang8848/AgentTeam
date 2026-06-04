# AgentTeam UX Audit Report

> **Audit Date**: 2026-06-04  
> **Auditor**: Frontend Engineer  
> **Project Version**: v0.7.6 (CLI) / v0.5.1 (pyproject.toml)  
> **Document Version**: CLI.md v0.5.4 / API.md v0.5.4

---

## Executive Summary

AgentTeam 提供了功能丰富的多 Agent 协调框架，但在 **首次用户体验 (Onboarding)** 和 **文档一致性** 方面存在显著改进空间。核心痛点是版本号不一致、中文文档编码问题、以及缺少交互式引导。

**一句话总结**: 功能强大但首次使用门槛较高，需要简化入门流程并统一文档版本号。

---

## 1. CLI 易用性评分

| 维度 | 评分 (1-10) | 问题数 |
|------|-------------|--------|
| 命令命名一致性 | 7 | 中等 |
| --help 输出质量 | 6 | 严重 |
| 错误提示友好度 | 5 | 严重 |
| 交互式引导 | 3 | 严重 |
| 退出码规范性 | 6 | 中等 |
| **综合评分** | **5.4/10** | — |

---

## 2. CLI TOP 10 痛点 (用户首次使用会卡住)

### P1 - 版本号严重不一致 (Blocker)
| 项目 | 值 |
|------|-----|
| **CLI --version 输出** | `v0.7.6` |
| **pyproject.toml version** | `v0.5.1` |
| **CLI.md 文档版本** | `v0.5.4` |
| **API.md 文档版本** | `v0.5.4` |
| **README.md badge** | `v0.5.1-openclaw` |

**影响**: 用户无法确定实际版本，升级时无法准确对照文档。

---

### P2 - Windows 中文编码问题 (Critical)
**现象**: `agentteam daemon --help` 输出中文乱码
```
| start    ???? agentd ?????                                               |
| stop     ???? agentd ?????                                               |
```
**根因**: Typer 源码中的中文 docstring 未设置 UTF-8 编码。
**影响**: Windows 中文用户完全无法阅读 daemon 命令帮助。

---

### P3 - spawn 命令缺少 --task/--prompt 的强制校验 (Critical)
**现象**: `agentteam spawn` 不带参数时会尝试连接 OpenClaw Gateway，失败后才报错。
```
Error spawning OpenClaw SDK agent: Gateway call failed (code 1): gateway connect failed...
```
**期望**: `--task` 为必选参数或提供交互式提示。

---

### P4 - 缺少交互式引导 (High)
**现象**: 没有任何 `agentteam init` 或 `agentteam wizard` 命令引导用户完成首次配置。
**对比竞品**: LangChain、AutoGPT 都提供交互式初始化。

---

### P5 - 错误信息暴露内部实现 (High)
**现象**: 
```python
# agentteam/cli/daemon_cmd.py
except socket.timeout:
    return {"ok": False, "error": "Daemon connection timeout"}
```
用户看到 "Daemon connection timeout" 而非 "守护进程未启动，请运行 `agentteam daemon start`"。

---

### P6 - 命名风格混用 (Medium)
| 位置 | 风格 | 示例 |
|------|------|------|
| CLI 命令 | kebab-case | `agentteam spawn --agent-name` |
| Daemon 命令 | 中文 docstring | `"""启动 agentd 守护进程"""` |
| API 端点 | snake_case | `/api/v1/teams/{team_name}/agents` |
| Python 模块 | snake_case | `agentteam.api.__init__` |

---

### P7 - --help 输出过长无分类 (Medium)
**现象**: `agentteam --help` 显示 20+ 个子命令，全部平铺。
**期望**: 按功能分组（Agent 管理 / Team 管理 / 调试 / 系统）。

---

### P8 - 配置文件路径不一致 (Medium)
| 来源 | 默认路径 |
|------|----------|
| CLI.md 示例 | `./config.yaml` |
| commands.py | `~/.agentteam/` |
| 代码硬编码 | `~/.agentteam` (Path.expanduser) |

---

### P9 - 缺少 dry-run / --dry-run 选项 (Low)
**现象**: 破坏性操作如 `agentteam team cleanup` 直接执行。
**期望**: 提供 `--dry-run` 预览将要执行的操作。

---

### P10 - spawn 默认值不透明 (Low)
**现象**: 
```bash
agentteam spawn  # tmux backend, openclaw command
```
用户不知道实际使用了什么 backend/command。

---

## 3. API 易用性评分

| 维度 | 评分 (1-10) | 问题数 |
|------|-------------|--------|
| 端点命名一致性 | 7 | 轻微 |
| 错误响应格式 | 6 | 中等 |
| 鉴权机制 | 8 | 轻微 |
| 限流机制 | 5 | 中等 |
| OpenAPI/AsyncAPI | 2 | 严重 |
| **综合评分** | **5.6/10** | — |

---

## 4. API 痛点

### A1 - 缺少 OpenAPI/Swagger 规范 (Critical)
**现象**: API.md 是手写文档，没有自动生成的 OpenAPI 规范。
**影响**: 无法使用 Postman/Insomnia 自动导入，第三方集成困难。

### A2 - 缺少 rate limit 错误码处理说明 (Medium)
**现象**: API.md 提到限流但未说明 retry-after header。
**影响**: 开发者不知道限流后应该等待多久重试。

### A3 - Daemon API 协议文档不完整 (Medium)
**现象**: 二进制长度前缀协议只有文字描述，没有代码示例。
**影响**: 开发者需要阅读源码才能正确实现客户端。

### A4 - WebSocket 协议文档不完整 (Medium)
**现象**: WebSocket 消息类型列表不完整。
**影响**: 前端开发者需要逆向源码。

---

## 5. 文档一致性问题清单

### 版本号不一致 (Critical)
| 文档/文件 | 版本 |
|-----------|------|
| CLI --version | **v0.7.6** |
| pyproject.toml | v0.5.1 |
| CLI.md | v0.5.4 |
| API.md | v0.5.4 |
| README.md badge | v0.5.1-openclaw |

### README 多语言版本差异 (High)
| 项目 | README.md | README_CN.md |
|------|-----------|--------------|
| 安装命令 | `YOUR_USERNAME/AgentTeam` | `YintaTriss/AgentTeam` |
| 架构图 ASCII | 有 | 有 |
| 功能对比表 | 有 | 部分缺失 |

### 命令参数不一致 (High)
| 命令 | CLI.md | 实际 --help |
|------|--------|-------------|
| `spawn --task` | `--task <task>` | `--task TEXT` (无描述) |
| `spawn --agent-type` | 默认: `general-purpose` | 默认: `general-purpose` (OK) |

### DEVELOPER_GUIDE.md 编码问题 (Medium)
**现象**: ASCII 架构图显示乱码。
```bash
â"Œâ"€â"€â"€â"€â"€â"€...
```
**影响**: 中文用户阅读开发者指南时架构图无法正常显示。

### CHANGELOG.md 编码问题 (Medium)
**现象**: 中文 changelog 显示乱码。
```bash
# AgentTeam å"‡çº§æ---å¿---...
```
**影响**: 中文用户无法阅读版本历史。

---

## 6. Onboarding 流程分析

### 当前流程 (6 步)
```
1. git clone [repo]
2. cd AgentTeam
3. pip install -e .
4. agentteam board serve --port 8080
5. 告诉 AI: "用 AgentTeam 构建博客系统"
6. 等待 AI 自主协调
```

### 问题点
| 步骤 | 问题 |
|------|------|
| 1 | README 中的 git clone URL 可能是占位符 |
| 4 | 依赖 OpenClaw Gateway，未安装会失败 |
| 5 | 缺少具体示例，用户不知道该说什么 |

### 缺少的要素
- NO `agentteam init` 交互式初始化
- NO 示例项目/模板 (demo project)
- NO `agentteam doctor` 自动检测依赖
- NO 首次使用向导

---

## 7. 改进建议 (按优先级排序)

### 立即修复 (P0)
1. **统一版本号**: 
   - pyproject.toml 改为 v0.7.6
   - 所有文档版本号更新到 v0.7.6

2. **修复中文编码**:
   - `daemon_cmd.py` 中文 docstring 添加 UTF-8 编码声明
   - 或将中文 docstring 改为英文

3. **修复 CHANGELOG.md 和 DEVELOPER_GUIDE.md 编码**:
   - 重新保存为 UTF-8 编码

### 高优先级 (P1)
4. **添加 `--task` 必选校验**: 
   ```python
   if not task:
       console.print("[red]--task is required[/red]")
       raise typer.Exit(1)
   ```

5. **添加 `agentteam init` 命令**:
   ```bash
   agentteam init  # 交互式创建配置文件
   ```

6. **生成 OpenAPI 规范**: 使用 FastAPI + openapi-pythonclient

### 中优先级 (P2)
7. **分组 --help 输出**:
   ```
   agentteam agent --help    # Agent 管理组
   agentteam team --help     # Team 管理组
   ```

8. **改进错误消息**: 添加"您可能需要"提示

9. **添加 `--dry-run` 选项**

---

## 8. Onboarding 改进后流程 (目标)

```
1. git clone [repo]
2. cd AgentTeam
3. pip install -e .
4. agentteam init          # [NEW] 交互式配置
   ? 输入 OpenClaw Gateway Token (可选)
   ? 选择默认 team 名称
   OK 配置文件已创建

5. agentteam doctor        # [NEW] 自动检测
   OK openclaw: installed
   OK gateway: connected
   OK tmux: skipped (Windows)
   
6. agentteam board serve --port 8080
7. 打开 http://localhost:8080
8. 使用模板: agentteam launch --template hello-world
```

---

## 9. 附录：测试命令记录

```bash
# CLI 版本
$ agentteam --version
agentteam v0.7.6

# CLI 帮助
$ agentteam --help
OK 正常显示

# Daemon 帮助 (Windows 中文环境)
$ agentteam daemon --help
FAIL 中文乱码

# Spawn 命令
$ agentteam spawn --help
OK 正常显示

# 实际运行 spawn
$ agentteam spawn
FAIL 需要 OpenClaw Gateway Token
```

---

## 10. 评分汇总

| 类别 | 当前分 | 目标分 | 差距 |
|------|--------|--------|------|
| CLI 易用性 | 5.4/10 | 8.0/10 | -2.6 |
| API 易用性 | 5.6/10 | 8.0/10 | -2.4 |
| 文档一致性 | 4.0/10 | 9.0/10 | -5.0 |
| Onboarding | 3.0/10 | 8.0/10 | -5.0 |
| **总体** | **4.5/10** | **8.0/10** | **-3.5** |

---

*Report generated by Frontend Engineer | 2026-06-04*
