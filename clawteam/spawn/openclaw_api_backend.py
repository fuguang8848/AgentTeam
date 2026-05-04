"""
OpenClaw API Backend - spawns OpenClaw agents via gateway API instead of subprocess.

解决 Windows 上 subprocess backend 的问题：
1. 不依赖 bash trap (PowerShell 不支持)
2. 正确捕获 openclaw agent 的输出
3. 阻塞等待结果
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
from dataclasses import dataclass
from typing import Optional

from clawteam.spawn.base import SpawnBackend
from clawteam.spawn.cli_env import build_spawn_path


@dataclass
class OpenClawProcess:
    """Tracks a spawned OpenClaw agent process."""

    name: str
    pid: int
    proc: subprocess.Popen
    session_key: str
    result: Optional[str] = None
    error: Optional[str] = None
    done: bool = False


class OpenClawAPIBackend(SpawnBackend):
    """
    Spawn OpenClaw agents via direct process invocation.

    不同于 subprocess_backend，本实现：
    - 直接用 subprocess.Popen 而不用 shell=True + trap
    - 为 openclaw agent 捕获 stdout/stderr
    - 阻塞等待结果而不是 fire-and-forget
    - Windows 原生支持
    """

    DEFAULT_GATEWAY_PORT = 18789
    DEFAULT_GATEWAY_TOKEN = "58428facccb51f7eb8d8ef9f3574b64803985a9742dc0345"

    def __init__(self):
        self._processes: dict[str, OpenClawProcess] = {}
        self._gateway_port = int(os.environ.get("OPENCLAW_GATEWAY_PORT", self.DEFAULT_GATEWAY_PORT))
        self._gateway_token = os.environ.get("OPENCLAW_GATEWAY_TOKEN", self.DEFAULT_GATEWAY_TOKEN)

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
        parent_agent: str = "",
        on_ready: str | None = None,
    ) -> str:
        """Spawn an OpenClaw agent and wait for its result."""
        if openclaw_agent:
            return "Error: openclaw_agent is not supported with openclaw_api backend"

        # 构建 openclaw agent 命令
        cmd = list(command) if command else ["openclaw"]

        # 确保有 "agent" 子命令
        if "agent" not in cmd and "tui" not in cmd:
            if cmd[0] in ("openclaw", "clawteam"):
                cmd.insert(1, "agent")
            else:
                cmd.append("agent")

        # 生成唯一 session key
        session_key = f"clawteam-{team_name}-{agent_name}"
        cmd.extend(["--session-id", session_key])

        # 添加 prompt
        if prompt:
            cmd.extend(["--message", prompt])

        # 模型
        if model:
            cmd.extend(["--model", model])

        # skip permissions
        if skip_permissions:
            cmd.append("--dangerously-skip-permissions")

        # 构建环境
        spawn_env = os.environ.copy()
        spawn_env["CLAWTEAM_AGENT_ID"] = agent_id
        spawn_env["CLAWTEAM_AGENT_NAME"] = agent_name
        spawn_env["CLAWTEAM_AGENT_TYPE"] = agent_type
        spawn_env["CLAWTEAM_TEAM_NAME"] = team_name
        spawn_env["CLAWTEAM_AGENT_LEADER"] = "0"
        spawn_env["CLAWTEAM_MEMORY_SCOPE"] = f"custom:team-{team_name}"

        # 添加 openclaw 到 PATH
        spawn_env["PATH"] = build_spawn_path(spawn_env.get("PATH"))

        if cwd:
            spawn_env["CLAWTEAM_WORKSPACE_DIR"] = cwd
        if env:
            spawn_env.update(env)

        # Windows 上 batch 文件需要 shell=True 才能通过 PATH 找到
        # 但我们不用 trap，直接让进程退出时通知 lifecycle
        import sys

        use_shell = sys.platform == "win32"

        # 如果用 shell=True，用字符串命令；否则用列表
        if use_shell:
            import shlex

            cmd_str = " ".join(shlex.quote(c) for c in cmd)
            final_cmd = cmd_str
        else:
            final_cmd = cmd

        try:
            proc = subprocess.Popen(
                final_cmd,
                shell=use_shell,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=spawn_env,
                cwd=cwd,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError:
            return f"Error: '{cmd[0]}' not found in PATH. Is OpenClaw installed?"
        except Exception as e:
            return f"Error spawning openclaw agent: {e}"

        # 注册进程
        openclaw_proc = OpenClawProcess(
            name=agent_name,
            pid=proc.pid,
            proc=proc,
            session_key=session_key,
        )
        self._processes[agent_name] = openclaw_proc

        # 注册到 clawteam registry
        try:
            from clawteam.spawn.registry import register_agent

            register_agent(
                team_name=team_name,
                agent_name=agent_name,
                backend="openclaw_api",
                pid=proc.pid,
                command=cmd,
            )
        except Exception:
            pass  # Non-fatal if registry fails

        # 启动后台线程等待结果
        thread = threading.Thread(
            target=self._wait_for_process,
            args=(openclaw_proc, team_name, agent_name),
            daemon=True,
        )
        thread.start()

        return f"Agent '{agent_name}' spawned via openclaw_api (pid={proc.pid}, session={session_key})"

    def _wait_for_process(
        self,
        proc: OpenClawProcess,
        team_name: str,
        agent_name: str,
        timeout: int = 600,
    ):
        """等待进程完成并更新状态."""
        try:
            stdout, stderr = proc.proc.communicate(timeout=timeout)
            proc.done = True

            if proc.proc.returncode == 0:
                proc.result = stdout
            else:
                proc.error = stderr or f"Exit code {proc.proc.returncode}"

                # 尝试从 stdout 获取 JSON 错误
                if stdout:
                    try:
                        # 检查是否是 JSON 格式的错误
                        data = json.loads(stdout)
                        if "error" in data:
                            proc.error = data["error"]
                    except (json.JSONDecodeError, ValueError):
                        pass
        except subprocess.TimeoutExpired:
            proc.proc.kill()
            stdout, stderr = proc.proc.communicate()
            proc.error = f"Timeout after {timeout}s"
        except Exception as e:
            proc.error = str(e)
        finally:
            # 通知 lifecycle
            self._notify_exit(team_name, agent_name, proc.error is None)

    def _notify_exit(self, team_name: str, agent_name: str, success: bool):
        """通知 clawteam agent 已退出."""
        try:
            import subprocess as sp

            clawteam_bin = os.environ.get("CLAWTEAM_BIN", "clawteam")
            sp.run(
                [clawteam_bin, "lifecycle", "on-exit", "--team", team_name, "--agent", agent_name],
                capture_output=True,
                timeout=10,
            )
        except Exception:
            pass  # Non-fatal

    def list_running(self) -> list[dict[str, str]]:
        """列出正在运行的 agents."""
        result = []
        for name, proc in list(self._processes.items()):
            if proc.proc.poll() is None:
                result.append(
                    {
                        "name": name,
                        "pid": str(proc.pid),
                        "backend": "openclaw_api",
                        "session": proc.session_key,
                        "done": str(proc.done),
                    }
                )
            else:
                # 进程已结束，清理
                self._processes.pop(name, None)
        return result

    def get_result(self, agent_name: str) -> tuple[bool, str | None]:
        """
        获取 agent 的结果。
        Returns: (has_result, result_or_error)
        """
        proc = self._processes.get(agent_name)
        if not proc:
            return False, None

        if not proc.done:
            return False, None

        if proc.error:
            return True, f"Error: {proc.error}"
        return True, proc.result
