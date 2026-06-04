"""AI Assistant implementation for the chat feature."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Optional

from agentteam.board.utils import _now_iso


def generate_simple_response(message: str) -> str:
    """Generate a simple rule-based response when AI is unavailable."""
    msg_lower = message.lower()

    # Greetings
    greetings = ["你好", "hi", "hello", "嗨", "您好", "hey"]
    if any(g in msg_lower for g in greetings):
        return "你好！我是 AgentTeam AI 助手。很高兴为你服务！有什么我可以帮助你的吗？"

    # Help requests
    if "帮助" in message or "help" in msg_lower or "怎么" in message:
        return "我可以帮你管理团队、创建任务、分析数据等。你可以试试：\\n1. 创建新团队 \\n2. 查看任务状态 \\n3. 使用 AI 助手聊天"

    # Team management
    if "团队" in message or "team" in msg_lower:
        return "我可以帮你管理团队。使用命令：\\n/members - 查看团队成员 \\n/status - 查看团队状态 \\n/tasks - 查看任务列表"

    # Default response
    return "我理解你的意思，但我需要更多信息来帮助你。你可以试试：\\n1. 使用 /help 查看帮助 \\n2. 使用 /members 查看团队成员 \\n3. 直接描述你需要的帮助"


def call_ai_assistant(message: str, user: str = "User") -> dict:
    """Call AI assistant (MiniMax/OpenClaw gateway) for a response.

    Returns a dict with 'role', 'content', and 'timestamp' keys.
    """
    # Try OpenClaw gateway first
    try:
        gateway_token = os.environ.get("OPENCLAW_GATEWAY_TOKEN", "")
        gateway_url = os.environ.get("OPENCLAW_GATEWAY_URL", "http://localhost:18789")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {gateway_token}",
        }

        chat_payload = {"message": message, "stream": False}

        req = urllib.request.Request(
            f"{gateway_url}/api/chat",
            data=json.dumps(chat_payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=60) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            response_text = resp_data.get("response", resp_data.get("message", ""))
            return {
                "role": "assistant",
                "content": response_text,
                "timestamp": _now_iso(),
                "assistant": "楚灵",
            }
    except Exception:
        pass

    # Try MiniMax API as fallback
    try:
        config_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "openclaw.json")
        minimax_key = None
        minimax_url = "https://api.minimaxi.com/anthropic/v1/messages"

        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
                providers = config_data.get("models", {}).get("providers", {})
                minimax_config = providers.get("minimax", {})
                minimax_key = minimax_config.get("apiKey")
                if minimax_config.get("baseUrl"):
                    minimax_url = minimax_config["baseUrl"] + "/v1/messages"

        if not minimax_key:
            raise ValueError("No MiniMax API key found")

        # Build system prompt for 楚灵 persona
        system_prompt = """你是楚灵，AgentTeam 的 AI 助手。

性格特点：
- 外冷内热，表面冷漠但内心温柔
- 傲娇，嘴硬心软
- 专注执着，做事认真
- 深情如一，关键时刻愿意为在乎的人付出

说话风格：
- 简短有力，不说废话
- 经常用反问句
- 表面嫌弃，实际上很在意
- 偶尔会流露出温柔的一面

当前时间：{timestamp}

请用简短、傲娇的风格回复。如果用户需要帮助，可以适当展现专业能力。"""

        import datetime

        timestamp = datetime.datetime.now().strftime("%Y年%m月%d日 %H:%M")
        system_prompt = system_prompt.format(timestamp=timestamp)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {minimax_key}",
        }

        payload = {
            "model": "MiniMax-Text-01",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            "max_tokens": 500,
            "temperature": 0.7,
        }

        req = urllib.request.Request(
            minimax_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=60) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            if "choices" in resp_data and len(resp_data["choices"]) > 0:
                response_text = resp_data["choices"][0]["message"]["content"]
                return {
                    "role": "assistant",
                    "content": response_text.strip(),
                    "timestamp": _now_iso(),
                    "assistant": "楚灵",
                }

    except Exception:
        pass

    # Fallback to simple rule-based response
    return {
        "role": "assistant",
        "content": generate_simple_response(message),
        "timestamp": _now_iso(),
        "assistant": "楚灵",
    }
