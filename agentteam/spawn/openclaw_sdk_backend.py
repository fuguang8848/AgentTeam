"""
OpenClaw SDK Backend - 基于 Gateway Sessions API 的原生多 Agent 协作后端

核心设计：
1. Agent 运行在 OpenClaw Session 中（有完整工具访问）
2. 通过 agentteam 协作协议（inbox/lifecycle）进行团队通信
3. 支持 Windows/Linux/macOS
4. 真正多轮协作，Agent 知道团队上下文

使用方式：
    agentteam spawn openclaw_sdk --team my-team --agent-name worker-1 --task "分析代码"
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from agentteam.spawn.base import SpawnBackend

GATEWAY_PORT = int(os.environ.get("OPENCLAW_GATEWAY_PORT", "18789"))
GATEWAY_TOKEN = os.environ.get("OPENCLAW_GATEWAY_TOKEN", "")
DATA_DIR = Path(os.environ.get("AGENTTEAM_DATA_DIR", "~/.agentteam")).expanduser()


# 持续运行 Block - 用于 specialist agents
_CONTINUOUS_RUN_BLOCK = """
## Continuous Running Mode

**IMPORTANT: Do NOT exit after completing a task. Stay alive and await new tasks.**

**Startup:**
1. Check your inbox for any pending tasks:
   `agentteam inbox peek {team_name} --agent {agent_name}`
2. If tasks exist, process them. If not, proceed to standby.

**Main Loop:**
- Every 30 seconds, check your inbox for new messages:
  `agentteam inbox peek {team_name} --agent {agent_name}`
- If you receive a new task:
  1. Execute the task
  2. Report completion to leader: `agentteam inbox send {team_name} {leader_name} "Task completed: [BRIEF_SUMMARY]"`
  3. Return to standby loop

**Message Handling:**
- When you receive any message from the leader, check its content:
  - If the message contains the word "shutdown" (case-insensitive):
    - Write to the shared workspace: `{{workspace}}/{{agent_name}}_shutdown.txt` with content "Agent {{agent_name}} received shutdown command"
    - Call `exit` to terminate this session immediately
  - If the message contains "continue" or "await" or "stay":
    - Continue running and monitoring your inbox
  - Otherwise, treat it as a new task and execute it

**Shutdown Protocol:**
- ONLY exit when the leader sends a message containing "shutdown"
- After completing a task, ALWAYS ask the leader:
  `agentteam inbox send {team_name} {leader_name} "Task done. Should I exit or await new tasks?"`
- Wait for leader's response before deciding to exit or continue

**Task Completion:**
- After completing any task, do NOT auto-exit
- Send completion message to leader
- Ask if should exit or await new tasks
"""


@dataclass
class OCAProcess:
    """追踪 OpenClaw SDK Agent 会话"""

    name: str
    session_key: str
    session_id: str
    team_name: str
    agent_id: str = ""
    agent_type: str = "specialist"
    task_id: Optional[str] = None
    run_id: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    done: bool = False
    started_at: float = field(default_factory=time.time)
    # 新增：任务队列和生命周期管理
    task_queue: queue.Queue = field(default_factory=queue.Queue)
    shutdown_event: threading.Event = field(default_factory=threading.Event)
    keeper_thread: Optional[threading.Thread] = None
    cwd: Optional[str] = None
    heartbeat_count: int = 0  # 心跳计数器，用于控制广播频率


class OpenClawSDKBackend(SpawnBackend):
    """
    OpenClaw SDK Backend - 通过 Gateway Sessions API 实现原生多 Agent 协作

    架构图：
    ┌─────────────────────────────────────────────────────────────┐
    │                     AgentTeam CLI                            │
    │  agentteam spawn --backend openclaw_sdk --team foo ...       │
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
    │  - 通过 agentteam inbox 发送/接收消息                       │
    │  - 通过 agentteam lifecycle 报告状态                       │
    └─────────────────────────────────────────────────────────────┘
    """

    def __init__(self):
        self._processes: dict[str, OCAProcess] = {}
        self._gateway_cmd = self._detect_gateway_cmd()
        self._lock = threading.Lock()
        self._session_keepers: dict[str, threading.Thread] = {}  # 守护线程
        self._running_agents: dict[str, dict] = {}  # 持久化运行中 Agent 注册表
        self._load_running_agents()  # 加载持久化的运行中 agents

    def _get_running_agents_file(self) -> Path:
        """获取运行中 Agent 注册表文件路径"""
        return DATA_DIR / "running_agents.json"

    def _load_running_agents(self) -> None:
        """加载持久化的运行中 Agent 注册表"""
        registry_file = self._get_running_agents_file()
        if registry_file.exists():
            try:
                data = json.loads(registry_file.read_text(encoding="utf-8"))
                self._running_agents = data.get("agents", {})
            except Exception:
                self._running_agents = {}

    def _save_running_agents(self) -> None:
        """保存运行中 Agent 注册表到持久化存储"""
        registry_file = self._get_running_agents_file()
        registry_file.parent.mkdir(parents=True, exist_ok=True)
        data = {"agents": self._running_agents}
        registry_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _register_running_agent(self, agent_name: str, session_key: str, team_name: str, agent_type: str) -> None:
        """注册运行中的 Agent 到持久化注册表"""
        self._running_agents[agent_name] = {
            "session_key": session_key,
            "team_name": team_name,
            "agent_type": agent_type,
            "registered_at": time.time(),
        }
        self._save_running_agents()

    def _unregister_running_agent(self, agent_name: str) -> None:
        """从持久化注册表中移除 Agent"""
        self._running_agents.pop(agent_name, None)
        self._save_running_agents()

    def _detect_gateway_cmd(self) -> str:
        """检测 openclaw gateway 命令"""
        # 尝试不同平台的命令
        for cmd in ["openclaw", "openclaw.exe"]:
            try:
                r = subprocess.run(["cmd", "/c", cmd, "gateway", "health"], capture_output=True, timeout=5)
                if r.returncode == 0:
                    return cmd
            except Exception:
                pass
        return "openclaw"  # 默认

    def _broadcast_activity(
        self,
        agent_name: str,
        team_name: str,
        status: str,
        message: str = "",
        data: dict | None = None,
    ) -> None:
        """Broadcast agent activity to the board server for real-time monitoring.

        This sends activity to the board server's SSE stream so users can
        monitor agent progress in real-time via `agentteam board monitor`.

        If the board server is not running, this silently fails.
        """
        import urllib.request
        import urllib.parse

        # Board server configuration
        board_port = int(os.environ.get("AGENTTEAM_BOARD_PORT", "8080"))
        board_url = f"http://127.0.0.1:{board_port}/api/agents/activity"

        activity_data = {
            "team_name": team_name,
            "agent_name": agent_name,
            "status": status,
            "message": message,
        }
        if data:
            activity_data["data"] = data

        try:
            req = urllib.request.Request(
                board_url,
                data=json.dumps(activity_data).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=2) as response:
                pass  # Success - activity was broadcast
        except Exception:
            pass  # Silently fail if board server is not running

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
            raise RuntimeError(f"Gateway call failed (code {result.returncode}): {stderr or stdout}")

        output = stdout.strip()
        lines = output.split("\n")
        if lines and lines[0].startswith("Gateway call:"):
            json_str = "\n".join(lines[1:])
        else:
            json_str = output

        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
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
        parent_agent: str = "",
        on_ready: str | None = None,
    ) -> str:
        """
        通过 Gateway Sessions API 启动 OpenClaw Agent

        流程：
        1. 创建 Session（Agent 的独立运行环境）
        2. 发送任务消息（包含 agentteam 协作协议）
        3. Agent 在 Session 中运行，可以访问所有工具
        4. Agent 完成后通过 inbox 发送结果

        环境变量注入（env 参数）：
        - tmux_backend：直接传递给子进程（ subprocess.Popen(env=) ）
        - openclaw_sdk_backend：通过任务消息注入，Agent 执行 export 命令
          （适用于 AGENTMEMORY_BASE_DIR / AGENTMEMORY_NAMESPACE 等配置）
        """
        try:
            with self._lock:
                # 检查是否已存在同名 Agent
                if agent_name in self._processes and not self._processes[agent_name].done:
                    return f"Error: Agent '{agent_name}' is already running"

                # Step 1: 创建 Session
                create_data = self._gateway_call("sessions.create", timeout=30)
                session_key = create_data["key"]
                session_id = create_data["sessionId"]

                # Step 2: 构建任务消息（注入协作协议 + 环境变量）
                task = self._build_task_message(
                    agent_name=agent_name,
                    agent_id=agent_id,
                    agent_type=agent_type,
                    team_name=team_name,
                    prompt=prompt or "Complete your assigned task",
                    cwd=cwd,
                    on_ready=on_ready,
                    env=env,
                )

                # Step 3: 发送任务到 Session
                send_params = {
                    "key": session_key,
                    "message": task,
                }

                if model:
                    send_params["model"] = model

                send_data = self._gateway_call("sessions.send", params=send_params, timeout=30)
                run_id = send_data.get("runId")

                # Step 4: 注册到团队注册表
                proc = OCAProcess(
                    name=agent_name,
                    session_key=session_key,
                    session_id=session_id,
                    team_name=team_name,
                    agent_id=agent_id,
                    agent_type=agent_type,
                    run_id=run_id,
                    cwd=cwd,
                )
                self._processes[agent_name] = proc

                # 写入团队注册表
                self._register_agent(team_name, agent_name, session_key)

                # 注册到持久化运行中 Agent 注册表（支持跨进程 send_task）
                self._register_running_agent(agent_name, session_key, team_name, agent_type)

                # Step 5: 启动 Session Keeper（守护线程）
                keeper = threading.Thread(
                    target=self._session_keeper_loop,
                    args=(agent_name,),
                    daemon=True,
                )
                keeper.start()
                self._session_keepers[agent_name] = keeper

                # 广播 Agent 启动活动
                self._broadcast_activity(
                    agent_name=agent_name,
                    team_name=team_name,
                    status="started",
                    message=f"Agent {agent_name} ({agent_type}) started on team {team_name}",
                    data={"session_key": session_key, "agent_id": agent_id},
                )

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
        on_ready: str | None = None,
        env: dict[str, str] | None = None,
    ) -> str:
        """构建包含 agentteam 协作协议的任务消息"""

        # Build environment variables section (injected for SDK backend)
        env_section = []
        if env:
            # Escape double quotes in values to prevent prompt injection
            safe_vars = []
            for k, v in env.items():
                safe_v = v.replace('"', '\\"').replace("$", "\\$").replace("`", "\\`")
                safe_vars.append(f'export {k}="{safe_v}"')
            if safe_vars:
                env_section = [
                    "",
                    "## Environment Setup",
                    "```bash",
                    *safe_vars,
                    "```",
                    "",
                ]

        lines = [
            f"You are **{agent_name}** ({agent_type}), an agent on team **{team_name}**.",
            *env_section,
            "## Your Task",
            prompt,
            "",
            "## agentteam Collaboration Protocol",
            "",
            "**When you complete your task:**",
            "```bash",
            "# 1. Update task status (if task was assigned)",
            f"agentteam task update {team_name} [TASK_ID] --status completed",
            "",
            "# 2. Send result to leader",
            f'agentteam inbox send {team_name} leader "Task completed by {agent_name}. Summary: [BRIEF_SUMMARY]"',
            "",
            "# 3. Signal lifecycle exit",
            f"agentteam lifecycle on-exit --team {team_name} --agent {agent_name}",
            "```",
            "",
            "**If you're blocked:**",
            "```bash",
            f'agentteam inbox send {team_name} leader "Blocked: [ERROR_MESSAGE]"',
            "```",
            "",
            "**If you need to coordinate with teammates:**",
            "```bash",
            f"agentteam inbox send {team_name} [TEAMMATE_NAME] [MESSAGE]",
            f"agentteam inbox poll {team_name} --timeout 60",
            "```",
            "",
            "## Important",
            "- You have full tool access (read/write files, run commands, etc.)",
            "- Be concise in inbox messages",
            "- Use `agentteam status {team_name}` to see team status",
            "",
        ]

        if cwd:
            lines.insert(-2, f"**Working directory:** `{cwd}`\n")

        # 构建持续运行指令（针对 specialist 类型的 agent）
        if agent_type != "leader":
            lines.insert(
                -1,
                _CONTINUOUS_RUN_BLOCK.format(
                    team_name=team_name,
                    agent_name=agent_name,
                    leader_name="leader" if agent_type != "leader" else "",
                ),
            )

        # Post-Ready Hook (golutra-style): Execute after agent is ready
        if on_ready:
            lines.insert(
                -1,
                f"""## Post-Ready Hook

After you are ready and initialized, execute the following:

```
{on_ready}
```

Report completion to leader when done.
""",
            )

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

        registry_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")

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
            # 1. 发送 shutdown 信号
            proc.shutdown_event.set()

            # 2. 通过 gateway 关闭 session
            self._gateway_call("sessions.abort", params={"key": proc.session_key}, timeout=10)
            proc.done = True

            # 3. 广播 Agent 终止活动
            self._broadcast_activity(
                agent_name=agent_name,
                team_name=proc.team_name,
                status="terminated",
                message=f"Agent {agent_name} terminated by leader",
            )

            # 4. 清理 keeper 线程引用
            self._session_keepers.pop(agent_name, None)

            return True
        except Exception:
            return False

    def _session_keeper_loop(self, agent_name: str) -> None:
        """
        Session Keeper 线程 - 保持 Agent Session 活跃并处理新任务

        职责：
        1. 每 15 秒发送一次心跳保持 session 活跃
        2. 检查任务队列，有新任务则 inject 到 session
        3. 监听 shutdown 信号并清理
        """
        proc = self._processes.get(agent_name)
        if not proc:
            return

        heartbeat_count = 0
        while not proc.done and not proc.shutdown_event.is_set():
            try:
                # 1. 心跳保活（每 15 秒）
                heartbeat_count += 1
                if heartbeat_count % 4 == 0:  # 每 4 次循环（约 60 秒）
                    self._send_heartbeat(proc)

                # 2. 检查任务队列
                try:
                    new_task = proc.task_queue.get_nowait()
                    self._inject_task(proc, new_task)
                except queue.Empty:
                    pass

                # 3. 检查 shutdown 信号
                if proc.shutdown_event.is_set():
                    self._send_shutdown(proc)
                    break

            except Exception as e:
                # 守护线程不抛出异常，只记录
                pass

            # 等待下次检查
            proc.shutdown_event.wait(timeout=15)

        # Agent 完成或关闭 - 广播完成活动
        if proc.done:
            self._broadcast_activity(
                agent_name=agent_name,
                team_name=proc.team_name,
                status="completed",
                message=f"Agent {agent_name} completed session",
            )

    def _send_heartbeat(self, proc: OCAProcess) -> None:
        """发送心跳保持 session 活跃"""
        try:
            heartbeat_msg = (
                f"[System] Session heartbeat. You are **{proc.name}** ({proc.agent_type}) on team **{proc.team_name}**. "
                f"Continue monitoring your inbox for new tasks. Do NOT exit."
            )
            self._gateway_call(
                "sessions.send",
                params={"key": proc.session_key, "message": heartbeat_msg},
                timeout=10,
            )

            # 广播心跳活动（每3次心跳广播一次，约3分钟一次，避免噪声）
            proc.heartbeat_count += 1
            if proc.heartbeat_count % 3 == 0:
                self._broadcast_activity(
                    agent_name=proc.name,
                    team_name=proc.team_name,
                    status="heartbeat",
                    message=f"Agent {proc.name} is alive and waiting for tasks",
                )
        except Exception:
            pass

    def _inject_task(self, proc: OCAProcess, task: str) -> None:
        """Inject 新任务到 Agent Session"""
        try:
            task_msg = (
                f"## New Task Assignment\n\n{task}\n\n"
                f"Execute this task and report completion to your leader when done.\n"
                f"Remember: Do NOT exit after completing. Await further instructions."
            )
            self._gateway_call(
                "sessions.send",
                params={"key": proc.session_key, "message": task_msg},
                timeout=10,
            )

            # 广播任务分配活动
            self._broadcast_activity(
                agent_name=proc.name,
                team_name=proc.team_name,
                status="task_assigned",
                message=f"New task assigned to {proc.name}",
                data={"task": task[:100] + "..." if len(task) > 100 else task},
            )
        except Exception:
            pass

    def _send_shutdown(self, proc: OCAProcess) -> None:
        """发送 shutdown 命令"""
        try:
            shutdown_msg = "## Shutdown\n\nThe leader has sent the shutdown signal. Exit your session now."
            self._gateway_call(
                "sessions.send",
                params={"key": proc.session_key, "message": shutdown_msg},
                timeout=10,
            )
            # 等待一下让 agent 处理
            time.sleep(2)
            # 终止 session
            self._gateway_call("sessions.abort", params={"key": proc.session_key}, timeout=10)
            proc.done = True
        except Exception:
            pass

    def send_task(self, agent_name: str, task: str) -> bool:
        """
        向运行中的 Agent 发送新任务

        支持两种模式：
        1. 本地模式：agent 由当前 backend 实例 spawn，直接入队
        2. 持久化模式：agent 由其他 backend 实例 spawn，从注册表查找 session_key 并直接发送

        Args:
            agent_name: Agent 名称
            task: 任务描述

        Returns:
            True 如果任务发送成功，False 如果 agent 不存在或发送失败
        """
        # 模式 1：本地 agent（当前 backend 实例 spawn 的）
        proc = self._processes.get(agent_name)
        if proc and not proc.done:
            try:
                proc.task_queue.put_nowait(task)
                return True
            except queue.Full:
                return False

        # 模式 2：持久化 agent（由其他 backend 实例 spawn 的）
        if agent_name in self._running_agents:
            agent_info = self._running_agents[agent_name]
            session_key = agent_info["session_key"]
            team_name = agent_info.get("team_name", "unknown")

            # 直接通过 Gateway Sessions API 发送任务
            task_msg = (
                f"## New Task Assignment\n\n{task}\n\n"
                f"Execute this task and report completion to your leader when done.\n"
                f'After completing, ask your leader: "Task done. Should I exit or await new tasks?"'
            )

            try:
                self._gateway_call(
                    "sessions.send",
                    params={"key": session_key, "message": task_msg},
                    timeout=10,
                )
                return True
            except Exception:
                # Session 可能已结束，从注册表中移除
                self._unregister_running_agent(agent_name)
                return False

        return False

    def shutdown_agent(self, agent_name: str) -> bool:
        """
        发送 shutdown 信号给 Agent（优雅关闭）

        Args:
            agent_name: Agent 名称

        Returns:
            True 如果成功发送 shutdown 信号
        """
        # 模式 1：本地 agent
        proc = self._processes.get(agent_name)
        if proc:
            proc.shutdown_event.set()
            return True

        # 模式 2：持久化 agent
        if agent_name in self._running_agents:
            agent_info = self._running_agents[agent_name]
            session_key = agent_info["session_key"]

            try:
                shutdown_msg = "## Shutdown\n\nThe leader has sent the shutdown signal. Exit your session now."
                self._gateway_call(
                    "sessions.send",
                    params={"key": session_key, "message": shutdown_msg},
                    timeout=10,
                )
                # 等待一下让 agent 处理
                time.sleep(2)
                # 终止 session
                self._gateway_call("sessions.abort", params={"key": session_key}, timeout=10)
            except Exception:
                pass

            # 从注册表中移除
            self._unregister_running_agent(agent_name)
            return True

        return False
