"""
clawteam daemon 命令 - 与 agentd 守护进程通信

用法：
    clawteam daemon start        # 启动守护进程
    clawteam daemon stop         # 停止守护进程
    clawteam daemon status       # 查看状态
    clawteam daemon list         # 列出运行中的 Agent
    clawteam daemon spawn        # 通过 daemon spawn Agent
"""

from __future__ import annotations

import json
import struct

try:
    import locale
    LOCALE_ENCODING = locale.getpreferredencoding(False) or "utf-8"
except Exception:
    LOCALE_ENCODING = "utf-8"

from pathlib import Path
from typing import Optional

import typer

from clawteam.console import console

DATA_DIR = Path("~/.clawteam").expanduser()
PID_FILE = DATA_DIR / "agentd.pid"

# Windows 不支持 Unix Socket
import platform
IS_WINDOWS = platform.system() == "Windows"
if IS_WINDOWS:
    DAEMON_HOST = "127.0.0.1"
    DAEMON_PORT = 18792
else:
    SOCKET_FILE = DATA_DIR / "agentd.sock"

app = typer.Typer(help="Manage the clawteam agent daemon")


def _send_daemon_command(command: str, args: dict = None) -> dict:
    """通过 Socket 发送命令到 daemon"""
    import socket

    if IS_WINDOWS:
        if not PID_FILE.exists():
            return {"ok": False, "error": "Daemon not running. Run 'clawteam daemon start' first."}
        address = (DAEMON_HOST, DAEMON_PORT)
        sock_type = socket.AF_INET
    else:
        if not SOCKET_FILE.exists():
            return {"ok": False, "error": "Daemon not running. Run 'clawteam daemon start' first."}
        address = str(SOCKET_FILE)
        sock_type = socket.AF_UNIX

    try:
        sock = socket.socket(sock_type, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect(address)

        request = json.dumps({
            "command": command,
            "args": args or {},
        }, ensure_ascii=False).encode("utf-8")

        sock.sendall(struct.pack("!I", len(request)))
        sock.sendall(request)

        # 接收响应长度
        length_data = sock.recv(4)
        if not length_data:
            sock.close()
            return {"ok": False, "error": "No response from daemon"}

        length = struct.unpack("!I", length_data)[0]

        # 接收响应内容
        data = b""
        while len(data) < length:
            chunk = sock.recv(length - len(data))
            if not chunk:
                break
            data += chunk

        sock.close()
        return json.loads(data.decode("utf-8"))

    except socket.timeout:
        return {"ok": False, "error": "Daemon connection timeout"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.command()
def start():
    """启动 agentd 守护进程"""
    import os
    import subprocess
    import sys

    # 检查是否已经在运行
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            import ctypes
            kernel32 = ctypes.windll.kernel32
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if handle:
                kernel32.CloseHandle(handle)
                console.print(f"[yellow]Daemon already running with PID {pid}[/yellow]")
                return
        except Exception:
            pass

    # 启动 daemon 进程
    daemon_script = Path(__file__).parent.parent / "daemon" / "agentd.py"

    # 在后台启动
    try:
        subprocess.Popen(
            [sys.executable, str(daemon_script), "start"],
            cwd=str(daemon_script.parent.parent),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if hasattr(subprocess, 'CREATE_NEW_PROCESS_GROUP') else 0,
        )
        console.print("[green]Starting daemon...[/green]")

        # 等待 daemon 启动
        import time
        for _ in range(10):
            time.sleep(0.5)
            if SOCKET_FILE.exists():
                console.print(f"[green]Daemon started successfully[/green]")
                return

        console.print("[yellow]Daemon may have started, checking status...[/yellow]")
        status()

    except Exception as e:
        console.print(f"[red]Failed to start daemon: {e}[/red]")


@app.command()
def stop():
    """停止 agentd 守护进程"""
    result = _send_daemon_command("stop")
    if result.get("ok"):
        console.print("[green]Daemon stopped[/green]")
    else:
        console.print(f"[red]Stop failed: {result.get('error')}[/red]")


@app.command()
def status():
    """查看 daemon 状态"""
    if not PID_FILE.exists():
        console.print("[yellow]Daemon not running[/yellow]")
        return

    try:
        pid = int(PID_FILE.read_text().strip())
        import ctypes
        kernel32 = ctypes.windll.kernel32
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            kernel32.CloseHandle(handle)
            console.print(f"[green]Daemon running (PID: {pid})[/green]")
        else:
            console.print("[yellow]Daemon not running (stale PID file)[/yellow]")
            PID_FILE.unlink()
    except Exception:
        console.print("[yellow]Daemon not running[/yellow]")


@app.command()
def list():
    """列出运行中的 Agent"""
    result = _send_daemon_command("list_agents")
    if not result.get("ok"):
        console.print(f"[red]Failed: {result.get('error')}[/red]")
        return

    agents = result.get("agents", [])
    if not agents:
        console.print("[yellow]No agents running[/yellow]")
        return

    from rich.table import Table
    table = Table(title="Running Agents")
    table.add_column("Name", style="cyan")
    table.add_column("Team", style="magenta")
    table.add_column("Type", style="green")
    table.add_column("Status", style="yellow")

    for agent in agents:
        status = "[green]Running[/green]" if agent.get("running") else "[red]Stopped[/red]"
        table.add_row(
            agent.get("name", ""),
            agent.get("team", ""),
            agent.get("type", ""),
            status,
        )

    console.print(table)


@app.command()
def spawn(
    team: str = typer.Option(..., help="Team name"),
    agent_name: str = typer.Option(..., help="Agent name"),
    agent_type: str = typer.Option("specialist", help="Agent type"),
    prompt: str = typer.Option(..., help="Task prompt"),
):
    """通过 daemon spawn Agent（Mode 2 支持）"""
    result = _send_daemon_command("spawn", {
        "agent_name": agent_name,
        "agent_id": agent_name,
        "agent_type": agent_type,
        "team_name": team,
        "prompt": prompt,
    })

    if result.get("ok"):
        console.print(f"[green]{result.get('message')}[/green]")
    else:
        console.print(f"[red]Spawn failed: {result.get('error')}[/red]")


if __name__ == "__main__":
    app()
