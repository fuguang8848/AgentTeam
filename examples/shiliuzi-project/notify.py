#!/usr/bin/env python3
"""
发送飞书通知 - 石榴籽项目

Security: 所有凭证从环境变量获取，不硬编码！
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skills.feishu_message.scripts.send_message import send_to_chat, send_to_user


def send_notification(
    message: str,
    recipients: list = None,
    chat_id: str = None,
    msg_type: str = "text"
) -> dict:
    """发送飞书通知
    
    Args:
        message: 通知内容
        recipients: 用户 open_id 列表 (for send_to_user)
        chat_id: 群 ID (for send_to_chat)
        msg_type: 消息类型 (text/post)
    
    Returns:
        API 响应
    """
    if chat_id:
        result = send_to_chat(chat_id=chat_id, content=message)
    elif recipients:
        # 发送给多个用户
        results = []
        for open_id in recipients:
            result = send_to_user(open_id=open_id, content=message)
            results.append({"open_id": open_id, "result": result})
        result = {"code": 0, "data": {"results": results}}
    else:
        raise ValueError("Either chat_id or recipients is required")
    
    return result


def send_reminder(
    title: str,
    content: str,
    deadline: str = None,
    chat_id: str = None,
    recipients: list = None
) -> dict:
    """发送格式化提醒
    
    Args:
        title: 提醒标题
        content: 提醒内容
        deadline: 截止时间
        chat_id: 群 ID
        recipients: 用户列表
    """
    message = f"🔔 {title}\n\n{content}"
    
    if deadline:
        message += f"\n\n⏰ 截止时间: {deadline}"
    
    message += "\n\n📌 来自石榴籽挑战杯团队"
    
    return send_notification(
        message=message,
        chat_id=chat_id,
        recipients=recipients
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="发送石榴籽项目通知")
    parser.add_argument("--message", required=True, help="通知内容")
    parser.add_argument("--chat_id", help="飞书群 ID")
    parser.add_argument("--recipients", nargs="+", help="用户 open_id 列表")
    
    args = parser.parse_args()
    
    result = send_notification(
        message=args.message,
        chat_id=args.chat_id,
        recipients=args.recipients
    )
    
    if result.get("code") == 0:
        print("✅ 通知发送成功!")
    else:
        print(f"❌ 发送失败: {result.get('msg')}")
