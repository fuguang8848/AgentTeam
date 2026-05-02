# 🎉 ClawTeam-OpenClaw v0.4.0 发布说明

**发布日期**: 2026-05-02  
**版本**: v0.4.0-openclaw  
**类型**: 生产级多智能体协调框架

---

## 📣 公告

ClawTeam-OpenClaw 是 [HKUDS/ClawTeam](https://github.com/HKUDS/ClawTeam) 的生产级 fork，专注 OpenClaw 生态。

> **这不是一个 demo。这是可以上线的生产软件。**

---

## 🆕 v0.4.0 新功能（相比上游 v0.3.0）

### 1. 🌐 Web UI 看板

**变更**: 🆕 新增

不再只能用 CLI 盯 tmux 窗口了。现在有完整的 Web 看板：

- **端口**: `8080`（默认）
- **标签页**: 看板 / 设计器 / 实时监控 / 工作流 / 设置
- **实时刷新**: Agent 状态、任务进度、漂移预警一目了然
- **一键启动**: `clawteam board serve --port 8080`

```bash
# 启动 Web 看板
clawteam board serve --port 8080

# 浏览器打开
open http://127.0.0.1:8080
```

---

### 2. 🔐 API 认证系统

**变更**: 🆕 新增

生产环境必备的 API 安全机制：

- **Token 认证**: JWT-like 短期 Token
- **Gateway Token 传递**: 自动分发到子 Agent（解决子 Agent 无法连接的问题）
- **Session 隔离**: 每个 Agent 独立会话
- **环境变量管理**: `.env` 分离，敏感信息不上传

---

### 3. 🧠 智能路由系统

**变更**: 🆕 新增

三因素路由算法，比"随机分配"聪明 10 倍：

| 因素 | 权重 | 说明 |
|------|------|------|
| **技能匹配** | 0-50 分 | 关键词提取（支持中英文） |
| **历史表现** | 0-30 分 | 成功率 + 质量评分 |
| **负载感知** | -15 分 | 当前任务数过多自动降权 |

```python
# 路由示例
best_agent = router.route(
    available_agents=[alice, bob, charlie],
    task="implement authentication",
    topic="backend auth security"
)
# 自动选择最合适的 Agent
```

---

### 4. 📋 审计日志

**变更**: 🆕 新增

完整的事件追溯系统：

- **事件类型**: SPAWN / TASK_UPDATE / INBOX_SEND / ALERT_TRIGGER 等
- **字段**: event_id / event_type / actor / details / timestamp / team
- **追加写入**: 历史事件永不修改
- **查询 CLI**: `clawteam audit query <team> --action SPAWN --limit 100`

```bash
# 查询团队审计日志
clawteam audit query my-team --actor alice --json

# 审计活动摘要
clawteam audit summary my-team
```

---

### 5. 🚨 告警机制

**变更**: 🆕 新增

四级告警系统，出了问题第一时间知道：

| 级别 | 说明 | 场景 |
|------|------|------|
| **LOW** | 提示 | 任务长时间无更新 |
| **MEDIUM** | 注意 | Agent 失败率 > 10% |
| **HIGH** | 警告 | 团队 > 5 分钟无活动 |
| **CRITICAL** | 紧急 | 关键任务超时 |

```bash
# 检查告警
clawteam alert check --team my-team

# 列出所有告警
clawteam alert list --team my-team

# 确认告警
clawteam alert ack --alert-id <id>
```

---

### 6. 📊 质量评分与漂移检测

**变更**: 🆕 新增

| 功能 | 说明 |
|------|------|
| **QualityScore** | completeness(0.25) / accuracy(0.30) / quality(0.20) / 规范性(0.15) / innovation(0.10) |
| **漂移检测** | Jaccard + 语义相似度双校验，阈值 5 级（无→严重） |

---

### 7. 🔁 重试框架

**变更**: 🆕 新增

再也不用担心网络抖动了：

- **装饰器**: `@retry` / `@retry_async`
- **指数退避**: 自动延迟 + 抖动
- **统计**: 自动记录重试次数

```python
from clawteam.utils.retry import retry

@retry(max_attempts=3, delay=1.0, backoff=2.0)
def deliver_message():
    transport.deliver(message)
```

---

### 8. 📝 结构化日志

**变更**: 🆕 新增

生产级可调试日志：

- **JSON 格式**: 结构化输出，方便解析
- **trace_id**: 全链路追踪
- **RotatingFileHandler**: 10MB/文件，5 个备份
- **环境变量**: `CLAWTEAM_LOG_LEVEL=DEBUG`

---

### 9. 🐳 Docker 支持

**变更**: 🆕 新增 / 增强

```bash
# 开发环境
make dev

# 生产环境
make prod

# 运行测试
make test

# 清理
make clean
```

`docker-compose.yml` 包含完整的服务栈，无需手动安装。

---

### 10. 🧪 测试覆盖

**变更**: 🆕 新增

| 测试模块 | 用例数 | 状态 |
|----------|--------|------|
| P0 工程化 | 50+ | ✅ |
| P1 路由 | 18+ | ✅ |
| P1 告警 | 5+ | ✅ |
| P1 审计 | 7+ | ✅ |
| 集成测试 | 30+ | ✅ |
| **总计** | **1790+** | **✅ 全部通过** |

---

### 11. 📚 完整文档

**变更**: 🆕 新增 / 增强

| 文档 | 内容 |
|------|------|
| [README.md](README.md) | 完整项目介绍 |
| [API.md](API.md) | REST API 完整参考（~5000 字） |
| [CLI.md](CLI.md) | CLI 命令详解（~5000 字） |
| [DEPLOY.md](DEPLOY.md) | Docker / 裸机 / 分布式部署 |
| [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | 开发者指南 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 贡献指南 |

---

### 12. 🐚 Shell 补全

**变更**: 🆕 新增

```bash
# 安装 bash 补全
./shell-completion.sh bash

# 安装 zsh 补全
./shell-completion.sh zsh

# 安装 fish 补全
./shell-completion.sh fish
```

---

### 13. 🌍 多语言文档

**变更**: 🆕 新增

| 语言 | 文件 |
|------|------|
| 🇺🇸 English | README.md |
| 🇨🇳 简体中文 | README_CN.md |
| 🇹🇼 繁體中文 | README_TW.md |
| 🇯🇵 日本語 | README_JA.md |
| 🇰🇷 한국어 | README_KO.md |
| 🇫🇷 Français | README_FR.md |
| 🇩🇪 Deutsch | README_DE.md |
| 🇮🇹 Italiano | README_IT.md |
| 🇷🇺 Русский | README_RU.md |
| 🇧🇷 Português | README_PT-BR.md |

---

## 🔧 技术细节

### 版本对应关系

| 组件 | 版本 |
|------|------|
| Python | ≥3.10 |
| OpenClaw | 4.2+ 兼容 |
| Claude Code | 支持 |
| Codex | 支持 |

### 文件传输层

| 传输方式 | 说明 | 依赖 |
|----------|------|------|
| **Filesystem** | 默认，无需额外依赖 | 无 |
| **Redis** | 分布式团队 | `redis` |
| **ZeroMQ P2P** | 点对点 | `pyzmq` |

---

## 📈 升级路径

### 从上游 ClawTeam 升级

```bash
# 1. 拉取最新代码
git remote add upstream https://github.com/HKUDS/ClawTeam.git
git fetch upstream
git merge upstream/main

# 2. 安装依赖
pip install -e .

# 3. 运行测试
python -m pytest tests/ -v

# 4. 启动 Web 看板验证
clawteam board serve --port 8080
```

### 从旧版本升级

```bash
# 1. 拉取最新
git pull origin main

# 2. 重新安装依赖
pip install -e .

# 3. 验证
clawteam --version
clawteam board serve --port 8080
```

---

## 🙏 致谢

- **[HKUDS/ClawTeam](https://github.com/HKUDS/ClawTeam)** — 原始框架，所有上游贡献者
- **[OpenClaw](https://openclaw.ai)** — 默认 Agent 引擎
- **所有测试者** — 1790+ 测试用例的背后

---

## 📞 联系我们

- **GitHub Issues**: https://github.com/YOUR_USERNAME/ClawTeam-OpenClaw/issues
- **Discord**: https://discord.com/invite/clawd
- **文档**: https://docs.openclaw.ai

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

_ClawTeam-OpenClaw v0.4.0 — 2026-05-02_
