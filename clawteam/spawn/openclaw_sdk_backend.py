"""
OpenClaw SDK Backend - 基于 Gateway Sessions API 的原生多 Agent 协作后端

核心设计：
1. Agent 运行在 OpenClaw Session 中（有完整工具访问）
2. 通过 clawteam 协作协议（inbox/lifecycle）进行团队通信
3. 支持 Windows/Linux/macOS
4. 真正多轮协作，Agent 知道团队上下文

使用方式：
    clawteam spawn openclaw_sdk --team my-team --agent-name worker-1 --task "分析代码"
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from clawteam.spawn.base import SpawnBackend

GATEWAY_PORT = int(os.environ.get("OPENCLAW_GATEWAY_PORT", "18789"))
GATEWAY_TOKEN = os.environ.get("OPENCLAW_GATEWAY_TOKEN", "")
DATA_DIR = Path(os.environ.get("CLAWTEAM_DATA_DIR", "~/.clawteam")).expanduser()


@dataclass
class OCAProcess:
    """追踪 OpenClaw SDK Agent 会话"""

    name: str
    session_key: str
    session_id: str
    team_name: str
    task_id: Optional[str] = None
    run_id: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    done: bool = False
    started_at: float = field(default_factory=time.time)


class OpenClawSDKBackend(SpawnBackend):
    """
    OpenClaw SDK Backend - 通过 Gateway Sessions API 实现原生多 Agent 协作

    架构图：
    ┌─────────────────────────────────────────────────────────────┐
    │                     ClawTeam CLI                            │
    │  clawteam spawn --backend openclaw_sdk --team foo ...       │
    └─────────────────────┬───────────────────────────────────────┘
                          │
    ┌─────────────────────▼───────────────────────────────────────┐
    │              OpenClaw SDK Backend                          │
    │  1. sessions.create (创建 Agent Session)                   │
    │  2. sessions.send (发送任务 + 协作协议)                     │
    │  3. 监听 inbox/状态变化                                    │
    └─────────────────────┬───────────────────────────────────────┘
                          │
    ┌─────────────────────▼───────────────────────────────────────┐
    │              OpenClaw Gateway                              │
    │  ws://127.0.0.1:18789/rpc                                 │
    │  - sessions.create/send/list/history                       │
    │  - gateway.call                                           │
    └─────────────────────┬───────────────────────────────────────┘
                          │
    ┌─────────────────────▼───────────────────────────────────────┐
    │              OpenClaw Agent (Session)                       │
    │  - 运行在独立 Session 中                                   │
    │  - 有完整工具访问权限                                      │
    │  - 通过 clawteam inbox 发送/接收消息                       │
    │  - 通过 clawteam lifecycle 报告状态                       │
    └─────────────────────────────────────────────────────────────┘
    """

    def __init__(self):
        self._processes: dict[str, OCAProcess] = {}
        self._gateway_cmd = self._detect_gateway_cmd()
        self._lock = threading.Lock()

    def _detect_gateway_cmd(self) -> str:
        """检测 openclaw gateway 命令"""
        # 尝试不同平台的命令
        for cmd in ["openclaw", "openclaw.exe"]:
            try:
                r = subprocess.run(
                    ["cmd", "/c", cmd, "gateway", "health"], capture_output=True, timeout=5
                )
                if r.returncode == 0:
                    return cmd
            except Exception:
                pass
        return "openclaw"  # 默认

    def _gateway_call(self, method: str, params: dict = None, timeout: int = 30) -> dict:
        """调用 Gateway RPC"""
        import locale

        encoding = locale.getpreferredencoding(False) or "utf-8"

        cmd = ["cmd", "/c", self._gateway_cmd, "gateway", "call", method]

        if params:
            params_json = json.dumps(params, ensure_ascii=False)
            # Escape < > for cmd.exe (redirection operators) - MUST be before extending cmd
            params_json = params_json.replace("<", "^<").replace(">", "^>")
            cmd.extend(["--params", params_json])

        if GATEWAY_TOKEN:
            cmd.extend(["--token", GATEWAY_TOKEN])

        try:
            result = subprocess.run(cmd, capture_output=True, timeout=timeout)
            stdout = result.stdout.decode(encoding, errors="replace") if result.stdout else ""
            stderr = result.stderr.decode(encoding, errors="replace") if result.stderr else ""
        except Exception as e:
            raise RuntimeError(f"Gateway call exception: {e}")

        if result.returncode != 0:
            raise RuntimeError(
                f"Gateway call failed (code {result.returncode}): {stderr or stdout}"
            )

        output = stdout.strip()
        lines = output.split("\n")
        if lines and lines[0].startswith("Gateway call:"):
            json_str = "\n".join(lines[1:])
        else:
            json_str = output

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON from gateway: {json_str[:200]}")

    def spawn(
        self,
        command: list[str],
        agent_name: str,
        agent_id: str,
        agent_type: str,
        team_name: str,
        prompt: str | None = None,
        env: dict[str, str] | None = None,
        cwd: str | None = None,
        skip_permissions: bool = False,
        openclaw_agent: str | None = None,
        model: str | None = None,
    ) -> str:
        """
        通过 Gateway Sessions API 启动 OpenClaw Agent

        流程：
        1. 创建 Session（Agent 的独立运行环境）
        2. 发送任务消息（包含 clawteam 协作协议）
        3. Agent 在 Session 中运行，可以访问所有工具
        4. Agent 完成后通过 inbox 发送结果
        """
        try:
            with self._lock:
                # 检查是否已存在同名 Agent
                if agent_name in self._processes and not self._processes[agent_name].done:
                    return f"Error: Agent '{agent_name}' is already running"

                # Step 1: 创建 Session
                create_data = self._gateway_call("sessions.create", timeout=10)
                session_key = create_data["key"]
                session_id = create_data["sessionId"]

                # Step 2: 构建任务消息（注入协作协议）
                task = self._build_task_message(
                    agent_name=agent_name,
                    agent_id=agent_id,
                    agent_type=agent_type,
                    team_name=team_name,
                    prompt=prompt or "Complete your assigned task",
                    cwd=cwd,
                )

                # Step 3: 发送任务到 Session
                send_params = {
                    "key": session_key,
                    "message": task,
                }

                if model:
                    send_params["model"] = model

                send_data = self._gateway_call("sessions.send", params=send_params, timeout=10)
                run_id = send_data.get("runId")

                # Step 4: 注册到团队注册表
                proc = OCAProcess(
                    name=agent_name,
                    session_key=session_key,
                    session_id=session_id,
                    team_name=team_name,
                    run_id=run_id,
                )
                self._processes[agent_name] = proc

                # 写入团队注册表
                self._register_agent(team_name, agent_name, session_key)

                return f"Agent '{agent_name}' started via OpenClaw SDK (session={session_key})"

        except Exception as e:
            return f"Error spawning OpenClaw SDK agent: {e}"

    def _build_task_message(
        self,
        agent_name: str,
        agent_id: str,
        agent_type: str,
        team_name: str,
        prompt: str,
        cwd: str | None = None,
    ) -> str:
        """构建包含 clawteam 协作协议的任务消息"""

        lines = [
            f"You are **{agent_name}** ({agent_type}), an agent on team **{team_name}**.",
            "",
            "## Your Task",
            prompt,
            "",
            "## clawteam Collaboration Protocol",
            "",
            "**When you complete your task:**",
            "```bash",
            f"# 1. Update task status (if task was assigned)",
            f"clawteam task update {team_name} [TASK_ID] --status completed",
            "",
            "# 2. Send result to leader",
            f'clawteam inbox send {team_name} leader "Task completed by {agent_name}. Summary: [BRIEF_SUMMARY]"',
            "",
            "# 3. Signal lifecycle exit",
            f"clawteam lifecycle on-exit --team {team_name} --agent {agent_name}",
            "```",
            "",
            "**If you're blocked:**",
            "```bash",
            f'clawteam inbox send {team_name} leader "Blocked: [ERROR_MESSAGE]"',
            "```",
            "",
            "**If you need to coordinate with teammates:**",
            "```bash",
            f"clawteam inbox send {team_name} [TEAMMATE_NAME] [MESSAGE]",
            f"clawteam inbox poll {team_name} --timeout 60",
            "```",
            "",
            "## Important",
            "- You have full tool access (read/write files, run commands, etc.)",
            "- Be concise in inbox messages",
            "- Use `clawteam status {team_name}` to see team status",
            "",
        ]

        if cwd:
            lines.insert(-2, f"**Working directory:** `{cwd}`\n")

        lines.append("Begin your task now.\n")

        return "\n".join(lines)

    def _register_agent(self, team_name: str, agent_name: str, session_key: str) -> None:
        """注册 Agent 到团队注册表"""
        registry_path = DATA_DIR / "teams" / team_name / "agents.json"
        registry_path.parent.mkdir(parents=True, exist_ok=True)

        registry = {}
        if registry_path.exists():
            try:
                registry = json.loads(registry_path.read_text(encoding="utf-8"))
            except Exception:
                registry = {}

        registry[agent_name] = {
            "session_key": session_key,
            "backend": "openclaw_sdk",
            "registered_at": time.time(),
        }

        registry_path.write_text(
            json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def list_running(self) -> list[dict[str, str]]:
        """列出正在运行的 Agents"""
        with self._lock:
            return [
                {
                    "name": name,
                    "session_key": proc.session_key,
                    "team": proc.team_name,
                    "backend": "openclaw_sdk",
                    "uptime": f"{int(time.time() - proc.started_at)}s",
                }
                for name, proc in self._processes.items()
                if not proc.done
            ]

    def get_result(self, agent_name: str) -> tuple[bool, str | None]:
        """获取 Agent 结果"""
        proc = self._processes.get(agent_name)
        if not proc:
            return False, None

        if proc.done:
            if proc.error:
                return True, f"Error: {proc.error}"
            return True, proc.result or "Completed"

        return False, None

    def wait_for_result(self, agent_name: str, timeout: int = 300) -> str:
        """等待 Agent 完成并返回结果"""
        start = time.time()
        while time.time() - start < timeout:
            done, result = self.get_result(agent_name)
            if done:
                return result or "Completed"
            time.sleep(5)
        return "Timeout waiting for agent"

    def terminate(self, agent_name: str) -> bool:
        """终止 Agent（通过关闭 Session）"""
        proc = self._processes.get(agent_name)
        if not proc:
            return False

        try:
            # 通过 gateway 关闭 session
            self._gateway_call("sessions.abort", params={"key": proc.session_key}, timeout=10)
            proc.done = True
            return True
        except Exception:
            return False
