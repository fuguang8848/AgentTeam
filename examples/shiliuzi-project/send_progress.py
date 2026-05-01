#!/usr/bin/env python3
"""
发送石榴籽项目训练进度到飞书群

Security: 所有凭证从环境变量获取，不硬编码！
"""

import os
import sys
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skills.feishu_message.scripts.send_message import send_to_chat, send_to_user


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
    
    if not app_id or not app_secret:
        raise ValueError(
            "Missing Feishu credentials. Set FEISHU_APP_ID and FEISHU_APP_SECRET "
            "environment variables."
        )
    
    return app_id, app_secret


def format_progress_message(
    model_name: str,
    accuracy: float,
    steps: int,
    total_steps: int,
    status: str,
    additional_info: dict = None
) -> str:
    """格式化进度消息"""
    emoji_map = {
        "training": "🔄",
        "completed": "✅",
        "failed": "❌",
        "pending": "⏳"
    }
    emoji = emoji_map.get(status.lower(), "📊")
    
    msg = f"""📊 石榴籽项目进度更新

{emoji} 模型: {model_name}
📈 准确率: {accuracy * 100:.1f}%
🔢 训练步数: {steps}/{total_steps}
📌 状态: {status.upper()}

👥 团队: 魏会恩、白翌平、敏浩、优优
🏫 项目: 甘肃警察学院 - 石榴籽挑战杯
📅 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
    
    if additional_info:
        msg += "\n\n📋 附加信息:"
        for key, value in additional_info.items():
            msg += f"\n  • {key}: {value}"
    
    return msg


def send_training_progress(
    model_name: str,
    accuracy: float,
    steps: int,
    total_steps: int = None,
    status: str = "training",
    chat_id: str = None,
    additional_info: dict = None,
    app_id: str = None,
    app_secret: str = None
) -> dict:
    """发送训练进度到飞书群
    
    Args:
        model_name: 模型名称 (e.g., "SEAMLESSM4T v2")
        accuracy: 准确率 (0.0 - 1.0)
        steps: 当前步数
        total_steps: 总步数
        status: 状态 (training/completed/failed/pending)
        chat_id: 飞书群 ID
        additional_info: 附加信息 dict
        app_id: 飞书 app_id (可选，从环境变量读取)
        app_secret: 飞书 app_secret (可选，从环境变量读取)
    
    Returns:
        API 响应 dict
    """
    # 设置凭证
    if app_id and app_secret:
        os.environ["FEISHU_APP_ID"] = app_id
        os.environ["FEISHU_APP_SECRET"] = app_secret
    
    if not chat_id:
        chat_id = os.environ.get("FEISHU_TEAM_CHAT_ID")
    
    if not chat_id:
        raise ValueError("chat_id is required, or set FEISHU_TEAM_CHAT_ID env var")
    
    if total_steps is None:
        total_steps = steps
    
    message = format_progress_message(
        model_name=model_name,
        accuracy=accuracy,
        steps=steps,
        total_steps=total_steps,
        status=status,
        additional_info=additional_info
    )
    
    print(f"Sending progress update to chat {chat_id}...")
    result = send_to_chat(
        chat_id=chat_id,
        content=message,
        app_id=app_id,
        app_secret=app_secret
    )
    
    if result.get("code") == 0:
        print("✅ 发送成功!")
    else:
        print(f"❌ 发送失败: {result.get('msg')}")
    
    return result


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="发送石榴籽项目进度到飞书")
    parser.add_argument("--model", default="SEAMLESSM4T v2", help="模型名称")
    parser.add_argument("--accuracy", type=float, default=0.65, help="准确率 (0-1)")
    parser.add_argument("--steps", type=int, default=7150, help="当前步数")
    parser.add_argument("--total", type=int, help="总步数")
    parser.add_argument("--status", default="completed", help="状态")
    parser.add_argument("--chat_id", help="飞书群 ID")
    
    args = parser.parse_args()
    
    send_training_progress(
        model_name=args.model,
        accuracy=args.accuracy,
        steps=args.steps,
        total_steps=args.total,
        status=args.status,
        chat_id=args.chat_id
    )
