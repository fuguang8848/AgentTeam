"""
clawteam-agentd - 持久化 Agent 守护进程

运行方式：
    clawteam agentd start  # 启动守护进程
    clawteam agentd stop   # 停止守护进程
    clawteam agentd status # 查看状态

守护进程职责：
1. 维护所有运行中的 Agent Session
2. 定期发送心跳保持 Session 活跃
3. 监听持久化任务队列，注入新任务到 Agent
4. 管理 Agent 生命周期（启动/关闭/重启）

架构：
┌─────────────────────────────────────────────────────────────┐
│                   clawteam CLI (Client)                     │
│  clawteam spawn / inbox send / agentd stop                 │
└─────────────────────┬───────────────────────────────────────┘
                      │ IPC (Unix Socket / TCP)
┌─────────────────────▼───────────────────────────────────────┐
│                  clawteam-agentd (Daemon)                   │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              Agent Session Manager                    │  │
│  │  - 加载 running_agents.json                         │  │
│  │  - 维护 OCAProcess 字典                             │  │
│  │  - Session Keeper 线程池                            │  │
│  │  - 心跳调度器                                       │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import atexit
import json
import os
import queue
import signal
import socket
import socketserver
import struct
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# 尝试导入必要的模块
try:
    import locale
    LOCALE_ENCODING = locale.getpreferredencoding(False) or "utf-8"
except Exception:
    LOCALE_ENCODING = "utf-8"

# 路径配置
DATA_DIR = Path(os.environ.get("CLAWTEAM_DATA_DIR", "~/.clawteam")).expanduser()
PID_FILE = DATA_DIR / "agentd.pid"
# Windows 不支持 Unix Socket，使用 TCP
import platform
IS_WINDOWS = platform.system() == "Windows"
if IS_WINDOWS:
    DAEMON_PORT = 18792  # agentd 专用端口
    SOCKET_HOST = "127.0.0.1"
else:
    SOCKET_FILE = DATA_DIR / "agentd.sock"
RUNNING_AGENTS_FILE = DATA_DIR / "running_agents.json"

# Gateway 配置
GATEWAY_PORT = int(os.environ.get("OPENCLAW_GATEWAY_PORT", "18789"))
GATEWAY_TOKEN = os.environ.get("OPENCLAW_GATEWAY_TOKEN", "")


@dataclass
class OCAProcess:
    """追踪 OpenClaw SDK Agent 会话"""
    name: str
    session_key: str
    session_id: str
    team_name: str
    agent_id: str = ""
    agent_type: str = "specialist"
    done: bool = False
    started_at: float = field(default_factory=time.time)
    task_queue: queue.Queue = field(default_factory=queue.Queue)
    shutdown_event: threading.Event = field(default_factory=threading.Event)


class AgentDaemon:
    """Agent 守护进程 - 持久化管理所有 Agent Sessions"""

    def __init__(self):
        self._processes: dict[str, OCAProcess] = {}
        self._lock = threading.Lock()
        self._running = False
        self._gateway_cmd = self._detect_gateway_cmd()
        self._load_running_agents()

    def _detect_gateway_cmd(self) -> str:
        """检测 openclaw gateway 命令"""
        for cmd in ["openclaw", "openclaw.exe"]:
            try:
                import subprocess
                r = subprocess.run(
                    ["cmd", "/c", cmd, "gateway", "health"],
                    capture_output=True, timeout=5
                )
                if r.returncode == 0:
                    return cmd
            except Exception:
                pass
        return "openclaw"

    def _gateway_call(self, method: str, params: dict = None, timeout: int = 30) -> dict:
        """调用 Gateway RPC"""
        import subprocess

        cmd = ["cmd", "/c", self._gateway_cmd, "gateway", "call", method]
        if params:
            params_json = json.dumps(params, ensure_ascii=False)
            params_json = params_json.replace("<", "^<").replace(">", "^>")
            cmd.extend(["--params", params_json])
        if GATEWAY_TOKEN:
            cmd.extend(["--token", GATEWAY_TOKEN])

        try:
            result = subprocess.run(cmd, capture_output=True, timeout=timeout)
            stdout = result.stdout.decode(LOCALE_ENCODING, errors="replace") if result.stdout else ""
            if result.returncode != 0:
                stderr = result.stderr.decode(LOCALE_ENCODING, errors="replace") if result.stderr else ""
                raise RuntimeError(f"Gateway call failed: {stderr[:200]}")

            # 跳过 "Gateway call: METHOD" 行
            output = stdout.strip()
            lines = output.split("\n")
            if lines and lines[0].startswith("Gateway call:"):
                json_str = "\n".join(lines[1:])
            else:
                json_str = output

            return json.loads(json_str)
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Gateway call timeout after {timeout}s")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON from gateway: {e}")

    def _load_running_agents(self) -> None:
        """从持久化注册表加载运行中的 Agent"""
        if RUNNING_AGENTS_FILE.exists():
            try:
                data = json.loads(RUNNING_AGENTS_FILE.read_text(encoding="utf-8"))
                agents = data.get("agents", {})
                # 验证每个 agent 的 session 是否还活着
                for name, info in list(agents.items()):
                    session_key = info.get("session_key")
                    if session_key:
                        try:
                            # 尝试获取 session 状态
                            result = self._gateway_call("sessions.get", params={"key": session_key})
                            if result.get("session", {}).get("status") == "running":
                                # Session 还活着，恢复进程信息
                                self._processes[name] = OCAProcess(
                                    name=name,
                                    session_key=session_key,
                                    session_id=info.get("session_id", ""),
                                    team_name=info.get("team_name", ""),
                                    agent_type=info.get("agent_type", "specialist"),
                                    done=False,
                                )
                                print(f"[Daemon] Restored agent '{name}' (session: {session_key})")
                            else:
                                print(f"[Daemon] Agent '{name}' session not running, removing from registry")
                                del agents[name]
                        except Exception as e:
                            print(f"[Daemon] Failed to verify agent '{name}': {e}")
                            del agents[name]
                # 保存清理后的注册表
                RUNNING_AGENTS_FILE.write_text(json.dumps({"agents": agents}, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception as e:
                print(f"[Daemon] Failed to load running agents: {e}")

    def _save_running_agents(self) -> None:
        """保存运行中 Agent 注册表"""
        agents = {}
        for name, proc in self._processes.items():
            if not proc.done:
                agents[name] = {
                    "session_key": proc.session_key,
                    "session_id": proc.session_id,
                    "team_name": proc.team_name,
                    "agent_type": proc.agent_type,
                    "started_at": proc.started_at,
                }
        RUNNING_AGENTS_FILE.write_text(json.dumps({"agents": agents}, indent=2, ensure_ascii=False), encoding="utf-8")

    def spawn_agent(
        self,
        agent_name: str,
        agent_id: str,
        agent_type: str,
        team_name: str,
        prompt: str,
        cwd: str = None,
    ) -> str:
        """启动一个新的 Agent"""
        with self._lock:
            if agent_name in self._processes and not self._processes[agent_name].done:
                return f"Error: Agent '{agent_name}' is already running"

            try:
                # 1. 创建 Session
                create_data = self._gateway_call("sessions.create", timeout=10)
                session_key = create_data["key"]
                session_id = create_data["sessionId"]

                # 2. 构建任务消息
                task_msg = self._build_task_message(agent_name, agent_id, agent_type, team_name, prompt, cwd)

                # 3. 发送任务
                send_params = {"key": session_key, "message": task_msg}
                self._gateway_call("sessions.send", params=send_params, timeout=10)

                # 4. 注册进程
                proc = OCAProcess(
                    name=agent_name,
                    session_key=session_key,
                    session_id=session_id,
                    team_name=team_name,
                    agent_type=agent_type,
                )
                self._processes[agent_name] = proc

                # 5. 保存到持久化注册表
                self._save_running_agents()

                # 6. 启动 Session Keeper
                keeper = threading.Thread(
                    target=self._session_keeper_loop,
                    args=(agent_name,),
                    daemon=True,
                )
                keeper.start()

                return f"Agent '{agent_name}' started (session={session_key})"

            except Exception as e:
                return f"Error spawning agent: {e}"

    def _build_task_message(
        self,
        agent_name: str,
        agent_id: str,
        agent_type: str,
        team_name: str,
        prompt: str,
        cwd: str = None,
    ) -> str:
        """构建任务消息"""
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
            f"# Send result to leader",
            f'clawteam inbox send {team_name} leader "Task completed by {agent_name}: [BRIEF_SUMMARY]"',
            "",
            f"# Ask if should continue or exit",
            f'clawteam inbox send {team_name} leader "Task done. Should I exit or await new tasks?"',
            "```",
            "",
            "**Continuous Running Mode:**",
            "- Do NOT exit after completing a task",
            "- Stay alive and await new tasks or shutdown signal",
            "- You will receive new tasks via the leader",
            "",
        ]
        if cwd:
            lines.insert(-2, f"**Working directory:** `{cwd}`\n")
        lines.append("Begin your task now.\n")
        return "\n".join(lines)

    def send_task(self, agent_name: str, task: str) -> bool:
        """向运行中的 Agent 发送新任务"""
        proc = self._processes.get(agent_name)
        if not proc or proc.done:
            return False
        try:
            task_msg = (
                f"## New Task Assignment\n\n{task}\n\n"
                f"Execute this task and report completion when done."
            )
            self._gateway_call(
                "sessions.send",
                params={"key": proc.session_key, "message": task_msg},
                timeout=10,
            )
            return True
        except Exception:
            return False

    def shutdown_agent(self, agent_name: str) -> bool:
        """关闭 Agent"""
        proc = self._processes.get(agent_name)
        if not proc:
            return False
        try:
            shutdown_msg = "## Shutdown\n\nThe leader has sent the shutdown signal. Exit your session now."
            self._gateway_call(
                "sessions.send",
                params={"key": proc.session_key, "message": shutdown_msg},
                timeout=10,
            )
            time.sleep(2)
            self._gateway_call("sessions.abort", params={"key": proc.session_key}, timeout=10)
            proc.done = True
            self._save_running_agents()
            return True
        except Exception:
            return False

    def _session_keeper_loop(self, agent_name: str) -> None:
        """Session Keeper 线程 - 保持 Agent 活跃并处理新任务"""
        proc = self._processes.get(agent_name)
        if not proc:
            return

        heartbeat_count = 0
        while not proc.done and not proc.shutdown_event.is_set():
            try:
                heartbeat_count += 1
                if heartbeat_count % 4 == 0:  # 每 4 次循环（约 60 秒）
                    self._send_heartbeat(proc)

                # 检查任务队列
                try:
                    new_task = proc.task_queue.get_nowait()
                    self._inject_task(proc, new_task)
                except queue.Empty:
                    pass

                if proc.shutdown_event.is_set():
                    self._send_shutdown(proc)
                    break

            except Exception:
                pass

            proc.shutdown_event.wait(timeout=15)

        # 清理
        with self._lock:
            self._processes.pop(agent_name, None)
            self._save_running_agents()

    def _send_heartbeat(self, proc: OCAProcess) -> None:
        """发送心跳"""
        try:
            msg = (
                f"[System] Heartbeat. You are **{proc.name}** on team **{proc.team_name}**. "
                f"Continue awaiting tasks. Do NOT exit."
            )
            self._gateway_call("sessions.send", params={"key": proc.session_key, "message": msg}, timeout=10)
        except Exception:
            pass

    def _inject_task(self, proc: OCAProcess, task: str) -> None:
        """注入任务"""
        try:
            msg = f"## New Task\n\n{task}\n\nExecute and report completion."
            self._gateway_call("sessions.send", params={"key": proc.session_key, "message": msg}, timeout=10)
        except Exception:
            pass

    def _send_shutdown(self, proc: OCAProcess) -> None:
        """发送关闭信号"""
        try:
            self._gateway_call(
                "sessions.send",
                params={"key": proc.session_key, "message": "## Shutdown\n\nExit now."},
                timeout=10,
            )
            time.sleep(2)
            self._gateway_call("sessions.abort", params={"key": proc.session_key}, timeout=10)
        except Exception:
            pass

    def list_agents(self) -> list[dict]:
        """列出所有运行中的 Agent"""
        return [
            {
                "name": name,
                "team": proc.team_name,
                "type": proc.agent_type,
                "session_key": proc.session_key,
                "running": not proc.done,
            }
            for name, proc in self._processes.items()
        ]

    def stop(self) -> None:
        """停止守护进程"""
        self._running = False
        # 关闭所有 Agent
        for name in list(self._processes.keys()):
            self.shutdown_agent(name)
        # 清理 PID 文件
        if PID_FILE.exists():
            PID_FILE.unlink()
        print("[Daemon] Stopped")


# 全局实例
_daemon: Optional[AgentDaemon] = None


def get_daemon() -> AgentDaemon:
    global _daemon
    if _daemon is None:
        _daemon = AgentDaemon()
    return _daemon


# IPC 协议
class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    """处理 CLI 客户端请求"""

    def handle(self):
        try:
            # 读取请求长度（4 字节）
            length_data = self.request.recv(4)
            if not length_data:
                return
            length = struct.unpack("!I", length_data)[0]

            # 读取请求内容
            data = b""
            while len(data) < length:
                chunk = self.request.recv(length - len(data))
                if not chunk:
                    break
                data += chunk

            request = json.loads(data.decode("utf-8"))
            command = request.get("command")
            args = request.get("args", {})

            daemon = get_daemon()
            result = {"ok": False, "error": "Unknown command"}

            if command == "spawn":
                result = {
                    "ok": True,
                    "message": daemon.spawn_agent(**args),
                }
            elif command == "send_task":
                ok = daemon.send_task(args["agent_name"], args["task"])
                result = {"ok": ok}
            elif command == "shutdown_agent":
                ok = daemon.shutdown_agent(args["agent_name"])
                result = {"ok": ok}
            elif command == "list_agents":
                result = {"ok": True, "agents": daemon.list_agents()}
            elif command == "stop":
                daemon.stop()
                result = {"ok": True}

            # 发送响应
            response = json.dumps(result, ensure_ascii=False).encode("utf-8")
            self.request.sendall(struct.pack("!I", len(response)))
            self.request.sendall(response)

        except Exception as e:
            error = json.dumps({"ok": False, "error": str(e)}).encode("utf-8")
            self.request.sendall(struct.pack("!I", len(error)))
            self.request.sendall(error)


if IS_WINDOWS:
    class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        """Windows TCP 服务器"""
        allow_reuse_address = True
else:
    class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
        """Unix Socket TCP 服务器"""
        allow_reuse_address = True


def start_daemon():
    """启动守护进程"""
    global _daemon

    # 检查是否已经在运行
    if PID_FILE.exists():
        pid = int(PID_FILE.read_text().strip())
        try:
            # 检查进程是否存在
            import ctypes
            kernel32 = ctypes.windll.kernel32
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if handle:
                kernel32.CloseHandle(handle)
                print(f"[Daemon] Already running with PID {pid}")
                return
        except Exception:
            pass

    # 创建 socket 文件目录
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 清理旧的文件
    if not IS_WINDOWS and SOCKET_FILE.exists():
        SOCKET_FILE.unlink()

    # 初始化守护进程
    _daemon = AgentDaemon()

    # 注册退出处理
    def cleanup():
        if _daemon:
            _daemon.stop()
    atexit.register(cleanup)

    # 信号处理（跨平台）
    def _shutdown_daemon():
        print("\n[Daemon] Shutting down")
        if _daemon:
            _daemon.stop()
        sys.exit(0)

    def signal_handler(signum, frame):
        _shutdown_daemon()

    if IS_WINDOWS:
        # Windows: 使用控制台事件处理
        import ctypes
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

        EVENT_SHUTDOWN = 0x0001  # CTRL_C_EVENT

        def windows_signal_handler(sig):
            if sig in (0, 1):  # CTRL_C_EVENT or CTRL_BREAK_EVENT
                _shutdown_daemon()
            return 1  # tell caller we handled it

        # 注册控制台 Ctrl+C/Ctrl+Break 处理
        kernel32.SetConsoleCtrlHandler(
            ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_uint)(windows_signal_handler),
            True
        )
    else:
        # Unix: 使用标准 signal
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    # 启动服务器
    if IS_WINDOWS:
        server = ThreadedTCPServer((SOCKET_HOST, DAEMON_PORT), ThreadedTCPRequestHandler)
        bind_addr = f"{SOCKET_HOST}:{DAEMON_PORT}"
    else:
        server = ThreadedTCPServer(str(SOCKET_FILE), ThreadedTCPRequestHandler)
        bind_addr = str(SOCKET_FILE)

    # 保存 PID
    import os
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")

    print(f"[Daemon] Started (PID: {os.getpid()})")
    print(f"[Daemon] Listening on: {bind_addr}")
    print("[Daemon] Ready to accept connections")

    _daemon._running = True

    # 运行服务器
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[Daemon] Shutting down")
        cleanup()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python agentd.py [start|stop|status]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "start":
        start_daemon()
    elif command == "stop":
        # 通过 socket 发送 stop 命令（跨平台）
        try:
            import socket
            if IS_WINDOWS:
                # Windows: 使用 TCP 连接
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect((SOCKET_HOST, DAEMON_PORT))
            else:
                # Unix: 使用 Unix Socket
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect(str(SOCKET_FILE))
            request = json.dumps({"command": "stop"}).encode("utf-8")
            sock.sendall(struct.pack("!I", len(request)))
            sock.sendall(request)
            response_len_data = sock.recv(4)
            response_len = struct.unpack("!I", response_len_data)[0]
            response = sock.recv(response_len).decode("utf-8")
            print(json.loads(response))
            sock.close()
        except Exception as e:
            print(f"[Daemon] Stop failed: {e}")
    elif command == "status":
        if PID_FILE.exists():
            pid = PID_FILE.read_text().strip()
            print(f"[Daemon] Running (PID: {pid})")
        else:
            print("[Daemon] Not running")
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
