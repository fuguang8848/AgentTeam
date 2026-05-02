"""Parsing rules for detecting events from AI provider outputs.

Supports multiple providers: Claude Code, Codex CLI, Gemini CLI, OpenCode.
Inspired by SpectrAI's rules.ts.
"""

from __future__ import annotations

import re
from typing import Any

from clawteam.parser.types import ActivityEventType, ParserRule


# ============================================================================
# Claude Code Rules (v2.x format: ⏺ ToolName(args))
# ============================================================================

CLAUDE_RULES: list[ParserRule] = [
    # Waiting for confirmation
    ParserRule(
        type=ActivityEventType.WAITING_CONFIRMATION,
        priority=20,
        provider_id="claude-code",
        patterns=[
            re.compile(r"Allow\s+.+\?\s*\(?y\)?", re.IGNORECASE),
            re.compile(r"Press Enter to continue", re.IGNORECASE),
        ],
        extract_detail=lambda line: (
            f"等待确认: {m.group(1)}"
            if (m := re.search(r"Allow\s+(.+?)\s*\?", line, re.IGNORECASE))
            else "等待用户确认"
        ),
    ),
    # Context compression
    ParserRule(
        type=ActivityEventType.CONTEXT_SUMMARY,
        priority=17,
        provider_id="claude-code",
        patterns=[
            re.compile(r"context\s+(?:window\s+)?compact", re.IGNORECASE),
            re.compile(r"conversation\s+(?:is\s+)?(?:being\s+)?compress", re.IGNORECASE),
            re.compile(r"Auto-compact", re.IGNORECASE),
            re.compile(r"summariz(?:ing|ed)\s+(?:the\s+)?conversation", re.IGNORECASE),
            re.compile(r"context\s+(?:limit|length)\s+(?:reached|exceeded)", re.IGNORECASE),
        ],
        extract_detail=lambda line: (
            "自动压缩上下文"
            if re.search(r"auto.compact", line, re.IGNORECASE)
            else "压缩对话上下文"
            if re.search(r"compress", line, re.IGNORECASE)
            else "摘要对话上下文"
            if re.search(r"summariz", line, re.IGNORECASE)
            else "上下文压缩"
        ),
    ),
    # Read file
    ParserRule(
        type=ActivityEventType.FILE_READ,
        priority=15,
        provider_id="claude-code",
        patterns=[
            re.compile(r"[⏺●]\s*Read\s*\(?([^\s)]+)"),
        ],
        extract_detail=lambda line: (
            f"读取文件: {m.group(1)}"
            if (m := re.search(r"[⏺●]\s*Read\s*\(?([^\s)]+)", line))
            else "读取文件"
        ),
    ),
    # Write/Edit file
    ParserRule(
        type=ActivityEventType.FILE_WRITE,
        priority=15,
        provider_id="claude-code",
        patterns=[
            re.compile(r"[⏺●]\s*Write\s*\(?([^\s)]+)"),
            re.compile(r"[⏺●]\s*Edit\s*\(?([^\s)]+)"),
            re.compile(r"[⏺●]\s*NotebookEdit\s*\(?([^\s)]+)"),
        ],
        extract_detail=lambda line: (
            f"写入文件: {m.group(1)}"
            if (m := re.search(r"[⏺●]\s*Write\s*\(?([^\s)]+)", line))
            else f"编辑文件: {m.group(1)}"
            if (m := re.search(r"[⏺●]\s*Edit\s*\(?([^\s)]+)", line))
            else f"编辑笔记本: {m.group(1)}"
            if (m := re.search(r"[⏺●]\s*NotebookEdit\s*\(?([^\s)]+)", line))
            else "写入文件"
        ),
    ),
    # Execute command
    ParserRule(
        type=ActivityEventType.COMMAND_EXECUTED,
        priority=14,
        provider_id="claude-code",
        patterns=[
            re.compile(r"[⏺●]\s*Bash\s*\(?(.+)\)?"),
        ],
        extract_detail=lambda line: (
            f"执行命令: {m.group(1)[:80]}"
            if (m := re.search(r"[⏺●]\s*Bash\s*\(?(.+?)\)?$", line))
            else "执行命令"
        ),
    ),
    # Search
    ParserRule(
        type=ActivityEventType.SEARCH,
        priority=14,
        provider_id="claude-code",
        patterns=[
            re.compile(r"[⏺●]\s*Glob\s*\(?([^\s)]+)"),
            re.compile(r"[⏺●]\s*Grep\s*\(?([^\s)]+)"),
            re.compile(r"[⏺●]\s*WebSearch\s*\(?(.+)\)?"),
            re.compile(r"[⏺●]\s*WebFetch\s*\(?(.+)\)?"),
        ],
        extract_detail=lambda line: (
            f"搜索文件: {m.group(1)}"
            if (m := re.search(r"[⏺●]\s*Glob\s*\(?([^\s)]+)", line))
            else f"搜索内容: {m.group(1)}"
            if (m := re.search(r"[⏺●]\s*Grep\s*\(?([^\s)]+)", line))
            else f"网络搜索: {m.group(1)[:60]}"
            if (m := re.search(r"[⏺●]\s*WebSearch\s*\(?(.+?)\)?$", line))
            else f"获取网页: {m.group(1)[:60]}"
            if (m := re.search(r"[⏺●]\s*WebFetch\s*\(?(.+?)\)?$", line))
            else "搜索"
        ),
    ),
    # Tool use (Task, MCP, Skill)
    ParserRule(
        type=ActivityEventType.TOOL_USE,
        priority=13,
        provider_id="claude-code",
        patterns=[
            re.compile(r"[⏺●]\s*Task\s*\(?(.+)\)?"),
            re.compile(r"[⏺●]\s*TodoRead"),
            re.compile(r"[⏺●]\s*TodoWrite"),
            re.compile(r"[⏺●]\s*mcp__(\w+)__(\w+)"),
            re.compile(r"[⏺●]\s*Skill\s*\(?(.+)\)?"),
            re.compile(r"[⏺●]\s*AskUserQuestion"),
            re.compile(r"[⏺●]\s*EnterPlanMode"),
            re.compile(r"[⏺●]\s*ExitPlanMode"),
        ],
        extract_detail=lambda line: (
            f"子任务: {m.group(1)[:80]}"
            if (m := re.search(r"[⏺●]\s*Task\s*\(?(.+?)\)?$", line))
            else "读取待办事项"
            if re.search(r"TodoRead", line)
            else "更新待办事项"
            if re.search(r"TodoWrite", line)
            else f"MCP 工具: {m.group(1)}.{m.group(2)}"
            if (m := re.search(r"[⏺●]\s*mcp__(\w+)__(\w+)", line))
            else f"技能: {m.group(1)[:60]}"
            if (m := re.search(r"[⏺●]\s*Skill\s*\(?(.+?)\)?$", line))
            else "向用户提问"
            if re.search(r"AskUserQuestion", line)
            else "进入规划模式"
            if re.search(r"EnterPlanMode", line)
            else "退出规划模式"
            if re.search(r"ExitPlanMode", line)
            else "工具调用"
        ),
    ),
    # Token usage statistics
    ParserRule(
        type=ActivityEventType.CONTEXT_SUMMARY,
        priority=8,
        provider_id="claude-code",
        patterns=[
            re.compile(r"(\d[\d,]+)\s+input\s+.*?(\d[\d,]+)\s+output\s+token", re.IGNORECASE),
        ],
        extract_detail=lambda line: (
            f"Token 统计: {m.group(1)} 输入 / {m.group(2)} 输出"
            if (m := re.search(r"(\d[\d,]+)\s+input\s+.*?(\d[\d,]+)\s+output", line, re.IGNORECASE))
            else "Token 用量统计"
        ),
    ),
]


# ============================================================================
# Codex CLI Rules
# ============================================================================

CODEX_RULES: list[ParserRule] = [
    # Waiting for confirmation
    ParserRule(
        type=ActivityEventType.WAITING_CONFIRMATION,
        priority=20,
        provider_id="codex",
        patterns=[
            re.compile(r"approve|reject", re.IGNORECASE),
            re.compile(r"permission.*(?:allow|deny)", re.IGNORECASE),
        ],
        extract_detail=lambda line: "等待确认: 权限请求",
    ),
    # File operations
    ParserRule(
        type=ActivityEventType.FILE_WRITE,
        priority=15,
        provider_id="codex",
        patterns=[
            re.compile(r"Writing\s+to\s+([^\s]+)"),
            re.compile(r"Editing\s+([^\s]+)"),
        ],
        extract_detail=lambda line: (
            f"写入文件: {m.group(1)}"
            if (m := re.search(r"Writing\s+to\s+([^\s]+)", line))
            else f"编辑文件: {m.group(1)}"
            if (m := re.search(r"Editing\s+([^\s]+)", line))
            else "写入文件"
        ),
    ),
    # Command execution
    ParserRule(
        type=ActivityEventType.COMMAND_EXECUTED,
        priority=14,
        provider_id="codex",
        patterns=[
            re.compile(r"Running\s+command:\s+(.+)", re.IGNORECASE),
            re.compile(r"Executing:\s+(.+)", re.IGNORECASE),
        ],
        extract_detail=lambda line: (
            f"执行命令: {m.group(1)[:80]}"
            if (m := re.search(r"Running\s+command:\s+(.+)", line, re.IGNORECASE))
            else f"执行命令: {m.group(1)[:80]}"
            if (m := re.search(r"Executing:\s+(.+)", line, re.IGNORECASE))
            else "执行命令"
        ),
    ),
]


# ============================================================================
# Gemini CLI Rules
# ============================================================================

GEMINI_RULES: list[ParserRule] = [
    # Waiting for confirmation
    ParserRule(
        type=ActivityEventType.WAITING_CONFIRMATION,
        priority=20,
        provider_id="gemini-cli",
        patterns=[
            re.compile(r"Approve\?\s*\(?Y/n\)?", re.IGNORECASE),
            re.compile(r"Approve\?\s*\(?y/n/always\)?", re.IGNORECASE),
        ],
        extract_detail=lambda line: "等待确认: 权限请求",
    ),
    # File operations
    ParserRule(
        type=ActivityEventType.FILE_WRITE,
        priority=15,
        provider_id="gemini-cli",
        patterns=[
            re.compile(r"Creating\s+file:\s+([^\s]+)"),
            re.compile(r"Modifying\s+file:\s+([^\s]+)"),
        ],
        extract_detail=lambda line: (
            f"创建文件: {m.group(1)}"
            if (m := re.search(r"Creating\s+file:\s+([^\s]+)", line))
            else f"修改文件: {m.group(1)}"
            if (m := re.search(r"Modifying\s+file:\s+([^\s]+)", line))
            else "文件操作"
        ),
    ),
    # Command execution
    ParserRule(
        type=ActivityEventType.COMMAND_EXECUTED,
        priority=14,
        provider_id="gemini-cli",
        patterns=[
            re.compile(r"Running:\s+(.+)", re.IGNORECASE),
        ],
        extract_detail=lambda line: (
            f"执行命令: {m.group(1)[:80]}"
            if (m := re.search(r"Running:\s+(.+)", line, re.IGNORECASE))
            else "执行命令"
        ),
    ),
]


# ============================================================================
# Generic Rules (apply to all providers)
# ============================================================================

GENERIC_RULES: list[ParserRule] = [
    # Error detection
    ParserRule(
        type=ActivityEventType.ERROR,
        priority=25,
        patterns=[
            re.compile(r"Error:\s+(.+)", re.IGNORECASE),
            re.compile(r"Failed\s+to\s+(.+)", re.IGNORECASE),
            re.compile(r"Exception:\s+(.+)", re.IGNORECASE),
            re.compile(r"ERROR\s+\[.+?\]:\s+(.+)", re.IGNORECASE),
        ],
        extract_detail=lambda line: (
            f"错误: {m.group(1)[:100]}"
            if (m := re.search(r"Error:\s+(.+)", line, re.IGNORECASE))
            else f"失败: {m.group(1)[:100]}"
            if (m := re.search(r"Failed\s+to\s+(.+)", line, re.IGNORECASE))
            else f"异常: {m.group(1)[:100]}"
            if (m := re.search(r"Exception:\s+(.+)", line, re.IGNORECASE))
            else f"错误: {m.group(1)[:100]}"
            if (m := re.search(r"ERROR\s+\[.+?\]:\s+(.+)", line, re.IGNORECASE))
            else "错误"
        ),
    ),
    # Task completion
    ParserRule(
        type=ActivityEventType.TASK_COMPLETE,
        priority=22,
        patterns=[
            re.compile(r"Task\s+completed", re.IGNORECASE),
            re.compile(r"Done\s+\(.*?\)", re.IGNORECASE),
            re.compile(r"Finished\s+(.+)", re.IGNORECASE),
            re.compile(r"Successfully\s+completed", re.IGNORECASE),
        ],
        extract_detail=lambda line: (
            "任务完成"
            if re.search(r"Task\s+completed", line, re.IGNORECASE)
            else "完成"
            if re.search(r"Done\s+\(.*?\)", line, re.IGNORECASE)
            else f"完成: {m.group(1)[:60]}"
            if (m := re.search(r"Finished\s+(.+)", line, re.IGNORECASE))
            else "成功完成"
        ),
    ),
    # Thinking indicator
    ParserRule(
        type=ActivityEventType.THINKING,
        priority=5,
        patterns=[
            re.compile(r"Thinking\s*...", re.IGNORECASE),
            re.compile(r"Analyzing\s*...", re.IGNORECASE),
            re.compile(r"Processing\s*...", re.IGNORECASE),
        ],
        extract_detail=lambda line: "思考中...",
    ),
    # File created
    ParserRule(
        type=ActivityEventType.FILE_CREATED,
        priority=16,
        patterns=[
            re.compile(r"Created\s+file:\s+([^\s]+)", re.IGNORECASE),
            re.compile(r"New\s+file:\s+([^\s]+)", re.IGNORECASE),
        ],
        extract_detail=lambda line: (
            f"创建文件: {m.group(1)}"
            if (m := re.search(r"Created\s+file:\s+([^\s]+)", line, re.IGNORECASE))
            else f"新文件: {m.group(1)}"
            if (m := re.search(r"New\s+file:\s+([^\s]+)", line, re.IGNORECASE))
            else "创建文件"
        ),
    ),
    # File deleted
    ParserRule(
        type=ActivityEventType.FILE_DELETED,
        priority=16,
        patterns=[
            re.compile(r"Deleted\s+file:\s+([^\s]+)", re.IGNORECASE),
            re.compile(r"Removed\s+file:\s+([^\s]+)", re.IGNORECASE),
        ],
        extract_detail=lambda line: (
            f"删除文件: {m.group(1)}"
            if (m := re.search(r"Deleted\s+file:\s+([^\s]+)", line, re.IGNORECASE))
            else f"移除文件: {m.group(1)}"
            if (m := re.search(r"Removed\s+file:\s+([^\s]+)", line, re.IGNORECASE))
            else "删除文件"
        ),
    ),
]


# ============================================================================
# Combined Rules (sorted by priority)
# ============================================================================

PARSER_RULES: list[ParserRule] = sorted(
    CLAUDE_RULES + CODEX_RULES + GEMINI_RULES + GENERIC_RULES,
    key=lambda r: r.priority,
    reverse=True,
)
