# 石榴籽项目 - 飞书集成示例

## 概述

本目录展示如何将石榴籽项目（东乡语 AI 翻译系统）与飞书集成，实现：
- 项目进度同步到飞书群
- 任务分配和跟踪
- 重要事件通知

## 文件说明

| 文件 | 说明 |
|------|------|
| `send_progress.py` | 发送训练进度到飞书群 |
| `create_task.py` | 创建任务到飞书多维表格 |
| `notify.py` | 发送通知到飞书 |

## 环境配置

```bash
# 设置飞书凭证
export FEISHU_APP_ID="cli_xxxxxxxxxxxxxxxx"
export FEISHU_APP_SECRET="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# 或在 OpenClaw 配置中设置 (~/.openclaw/openclaw.json)
```

## 使用示例

### 1. 发送训练进度

```python
from send_progress import send_training_progress

# M4T 训练完成，发送通知
send_training_progress(
    model_name="SEAMLESSM4T",
    accuracy=0.65,
    steps=7150,
    team_chat_id="oc_xxx"  # 飞书群 ID
)
```

输出示例：
```
📊 石榴籽项目进度更新

模型: SEAMLESSM4T v2
准确率: 65%
训练步数: 7150/7150
状态: ✅ 训练完成

团队: 魏会恩、白翌平、敏浩、优优
```

### 2. 创建任务

```python
from create_task import create_translation_task

# 创建新的翻译任务
task_id = create_translation_task(
    task_name="东乡语日常用语翻译",
    assignee="敏浩",
    deadline="2026-05-15",
    bitable_app_token="xxx",  # 多维表格 app token
    bitable_table_id="tblxxx"
)

print(f"Created task: {task_id}")
```

### 3. 发送通知

```python
from notify import send_notification

# 发送省赛答辩提醒
send_notification(
    message="📅 省赛答辩倒计时：15 天",
    recipients=["ou_youyou"],  # 优优的 open_id
    chat_id="oc_team_group"
)
```

## 安全注意事项

⚠️ **重要：不要提交敏感信息到 GitHub！**

1. 所有 API Key 和 App Secret 必须通过环境变量设置
2. 不要在代码中硬编码凭证
3. 使用 `.env.example` 作为模板，`.env` 不会被提交

```bash
# .env.example 模板
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
```

## 进一步集成

后续可以：
1. 在 CI/CD 中自动发送训练结果
2. 设置飞书机器人接收命令
3. 将飞书通知集成到 ClawTeam 的 notification system
