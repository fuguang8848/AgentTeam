#!/usr/bin/env python3
"""
在飞书多维表格中创建石榴籽项目任务

Security: 所有凭证从环境变量获取，不硬编码！
"""

import os
import sys
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_feishu_credentials():
    """从环境变量或 OpenClaw 配置获取飞书凭证"""
    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")
    
    if not app_id or not app_secret:
        try:
            config_path = os.path.expanduser("~/.openclaw/openclaw.json")
            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)
            feishu = config.get("channels", {}).get("feishu", {})
            app_id = app_id or feishu.get("appId") or feishu.get("app_id")
            app_secret = app_secret or feishu.get("appSecret") or feishu.get("app_secret")
        except Exception:
            pass
    
    return app_id, app_secret


def create_translation_task(
    task_name: str,
    assignee: str,
    deadline: str,
    task_type: str = "翻译",
    priority: str = "中",
    bitable_app_token: str = None,
    bitable_table_id: str = None,
    description: str = None
) -> dict:
    """创建翻译任务到飞书多维表格
    
    Args:
        task_name: 任务名称
        assignee: 负责人
        deadline: 截止日期 (YYYY-MM-DD)
        task_type: 任务类型
        priority: 优先级 (高/中/低)
        bitable_app_token: 多维表格 app token
        bitable_table_id: 表格 ID
        description: 任务描述
    
    Returns:
        创建的记录信息
    """
    # 从环境变量获取
    bitable_app_token = bitable_app_token or os.environ.get("FEISHU_BITABLE_APP_TOKEN")
    bitable_table_id = bitable_table_id or os.environ.get("FEISHU_BITABLE_TABLE_ID")
    
    if not bitable_app_token or not bitable_table_id:
        raise ValueError(
            "bitable_app_token and bitable_table_id are required. "
            "Set FEISHU_BITABLE_APP_TOKEN and FEISHU_BITABLE_TABLE_ID env vars."
        )
    
    # 构建记录数据
    fields = {
        "任务名称": task_name,
        "负责人": assignee,
        "截止日期": deadline,
        "任务类型": task_type,
        "优先级": priority,
        "状态": "待开始",
        "创建时间": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    
    if description:
        fields["描述"] = description
    
    # 这里调用 OpenClaw 的 feishu_bitable 工具
    # 由于是脚本模式，我们需要通过 API 或 CLI 调用
    # 实际使用时通过 ClawTeam agent 调用更方便
    
    print(f"Creating task: {task_name}")
    print(f"  Assignee: {assignee}")
    print(f"  Deadline: {deadline}")
    print(f"  Bitable: {bitable_app_token}/{bitable_table_id}")
    
    # 返回模拟数据，实际使用时替换为真实 API 调用
    return {
        "status": "ready",
        "task_name": task_name,
        "assignee": assignee,
        "deadline": deadline,
        "note": "Use ClawTeam agent with feishu_bitable tools to execute"
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="创建石榴籽项目任务")
    parser.add_argument("--name", required=True, help="任务名称")
    parser.add_argument("--assignee", required=True, help="负责人")
    parser.add_argument("--deadline", required=True, help="截止日期 (YYYY-MM-DD)")
    parser.add_argument("--type", default="翻译", help="任务类型")
    parser.add_argument("--priority", default="中", help="优先级")
    parser.add_argument("--desc", help="任务描述")
    
    args = parser.parse_args()
    
    result = create_translation_task(
        task_name=args.name,
        assignee=args.assignee,
        deadline=args.deadline,
        task_type=args.type,
        priority=args.priority,
        description=args.desc
    )
    
    print(f"\nResult: {json.dumps(result, ensure_ascii=False, indent=2)}")
