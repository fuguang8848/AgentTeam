# AgentTeam-OpenClaw v0.5.5 待办事项

> **目标**: SDK Agent 消息路由修复、文档完善

---

## ✅ v0.5.5 已完成 (2026-05-04)

### SDK Agent 消息路由修复
- [x] Smart Routing - inbox send 直接通过 Gateway API 发送消息给 running agent ✅
- [x] Activity 广播 - task_assigned 事件实时推送到 Board 服务器 ✅
- [x] Board Monitor - agentteam board monitor 实时显示 agent 活动 ✅
- [x] Agent Shutdown - prompt 新增 shutdown 检测逻辑 ✅
- [x] Release v0.5.5 创建 ✅

### P37: 组件集成
- [x] Board SSE → EventAPI 打通 ✅
- [x] 全系统集成测试 ✅

---

## 📝 文档完善

### 文档更新
- [x] `CAPABILITIES.md` - 完整能力清单 ✅
- [x] `PLATFORM_COMPATIBILITY.md` - 平台兼容性报告 ✅
- [x] `API.md` - REST API 完整参考 ✅
- [x] `CLI.md` - CLI 命令详解 ✅
- [x] `CONTRIBUTING.md` - 贡献指南 ✅
- [x] `DEPLOYMENT.md` - Docker / 裸机部署指南 ✅
- [x] README 链接已更新 ✅

### GitHub 更新
- [ ] Release v0.5.0 正式发布
- [ ] 更新 GitHub Tags
- [ ] 更新 Milestones

---

## 🧪 测试增强

### 测试覆盖
- [ ] `agentteam/collaboration/` - 协作模块测试
- [ ] `agentteam/notification/` - 通知模块测试
- [ ] `agentteam/insights/` - 洞察模块测试
- [ ] `agentteam/learnings/` - 学习模块测试

### 测试质量
- [ ] 提升覆盖率至 80%+
- [ ] 添加集成测试
- [ ] 添加端到端测试

---

## 🐛 Bug 修复

### 已知问题
- [x] ~~Web UI 导航问题（所有页面显示实时会话监控）~~ ✅ 已修复 2026-05-03
- [ ] Windows tmux backend 适配
- [x] ~~test_events.db 共享问题~~ ✅ 已修复

---

## 🚀 性能优化

### v0.5.1 优化
- [ ] 数据库查询优化
- [ ] WebSocket 连接复用
- [ ] 内存使用优化

### v0.6.0 规划
- [ ] 分布式部署支持
- [ ] 插件系统完善
- [ ] 更多 Agent backend

---

## 📋 进度记录

### 2026-05-04
- [x] 创建 CAPABILITIES.md
- [x] 更新 README.md 指向新文档

### 2026-05-04 (v0.5.5)
- [x] SDK Agent 消息路由修复 - Smart Routing + Activity 广播
- [x] Board Monitor 命令实现
- [x] Agent Shutdown 检测逻辑
- [x] CAPABILITIES.md 更新 v0.5.5
- [x] Release v0.5.5 创建

---

*本文档最后更新: 2026-05-04 | v0.5.5*
