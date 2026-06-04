"""
Message (Inbox) Management Commands

Provides inter-agent messaging operations: send, broadcast, receive, peek, log, watch.
"""

from __future__ import annotations

import json
import time
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from agentteam import __version__

app = typer.Typer(help="Inter-agent messaging commands")
console = Console()

# Global state (set by parent module)
_json_output = False


def _init_json_output(json_flag: bool):
    """Initialize JSON output flag from parent module."""
    global _json_output
    _json_output = json_flag


def _output(data: dict | list, human_fn=None):
    """Output data as JSON or human-readable."""
    if _json_output:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    elif human_fn:
        human_fn(data)
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))


# ============================================================================
# Inbox Commands
# ============================================================================


@app.command("send")
def inbox_send(
    team: str = typer.Argument(..., help="Team name"),
    to: str = typer.Argument(..., help="Recipient agent name"),
    content: str = typer.Argument(..., help="Message content"),
    from_agent: Optional[str] = typer.Option(None, "--from", "-f", help="Sender name (default: from env)"),
):
    """Send a message to an agent (send)."""
    from agentteam.identity import AgentIdentity
    from agentteam.team.mailbox import MailboxManager

    sender = from_agent or AgentIdentity.from_env().agent_name
    mailbox = MailboxManager(team)
    message_id = mailbox.send(
        from_agent=sender,
        to=to,
        msg_type="message",
        content=content,
    )

    _output(
        {"status": "sent", "messageId": message_id, "to": to, "from": sender},
        lambda d: console.print(f"[green]OK[/green] Message sent to '{to}' (id: {d['messageId'][:12]})"),
    )


@app.command("broadcast")
def inbox_broadcast(
    team: str = typer.Argument(..., help="Team name"),
    content: str = typer.Argument(..., help="Broadcast message content"),
    from_agent: Optional[str] = typer.Option(None, "--from", "-f", help="Sender name"),
):
    """Broadcast a message to all team members (broadcast)."""
    from agentteam.identity import AgentIdentity
    from agentteam.team.mailbox import MailboxManager
    from agentteam.team.manager import TeamManager

    sender = from_agent or AgentIdentity.from_env().agent_name
    config = TeamManager.get_team(team)

    if not config:
        console.print(f"[red]Team '{team}' not found[/red]")
        raise typer.Exit(1)

    mailbox = MailboxManager(team)
    sent_count = 0
    for member in config.members:
        if member.name != sender:
            mailbox.send(
                from_agent=sender,
                to=member.name,
                msg_type="broadcast",
                content=content,
            )
            sent_count += 1

    _output(
        {"status": "broadcast", "sent": sent_count, "from": sender},
        lambda d: console.print(f"[green]OK[/green] Broadcast sent to {d['sent']} agents"),
    )


@app.command("receive")
def inbox_receive(
    team: str = typer.Argument(..., help="Team name"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent name (default: from env)"),
    limit: int = typer.Option(10, "--limit", "-n", help="Max messages to receive"),
    delete: bool = typer.Option(True, "--delete/--no-delete", help="Delete received messages"),
):
    """Receive messages from inbox (receive)."""
    from agentteam.identity import AgentIdentity
    from agentteam.team.mailbox import MailboxManager

    inbox_name = agent or AgentIdentity.from_env().agent_name
    mailbox = MailboxManager(team)
    messages = mailbox.receive(inbox_name, limit=limit, delete=delete)

    def _human(msgs):
        if not msgs:
            console.print("[dim]No messages[/dim]")
            return
        table = Table(title=f"Inbox - {inbox_name}")
        table.add_column("From", style="cyan")
        table.add_column("Type", style="dim")
        table.add_column("Content")
        table.add_column("Time", style="dim")
        for m in msgs:
            table.add_row(
                m.get("from_agent", ""),
                m.get("type", ""),
                m.get("content", "")[:50] + ("..." if len(str(m.get("content", ""))) > 50 else ""),
                m.get("timestamp", "")[:19],
            )
        console.print(table)

    _output([{"from_agent": m.from_agent, "type": str(m.type), "content": m.content, "timestamp": m.timestamp} for m in messages], _human)


@app.command("peek")
def inbox_peek(
    team: str = typer.Argument(..., help="Team name"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent name"),
    limit: int = typer.Option(10, "--limit", "-n", help="Max messages"),
):
    """Peek at inbox messages without deleting (peek)."""
    from agentteam.identity import AgentIdentity
    from agentteam.team.mailbox import MailboxManager

    inbox_name = agent or AgentIdentity.from_env().agent_name
    mailbox = MailboxManager(team)
    messages = mailbox.peek(inbox_name, limit=limit)

    def _human(msgs):
        if not msgs:
            console.print("[dim]No messages[/dim]")
            return
        table = Table(title=f"Inbox (peek) - {inbox_name}")
        table.add_column("From", style="cyan")
        table.add_column("Type", style="dim")
        table.add_column("Content")
        for m in msgs:
            table.add_row(
                m.get("from_agent", ""),
                m.get("type", ""),
                m.get("content", "")[:60],
            )
        console.print(table)

    _output([{"from_agent": m.from_agent, "type": str(m.type), "content": m.content} for m in messages], _human)


@app.command("log")
def inbox_log(
    team: str = typer.Argument(..., help="Team name"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent name"),
    limit: int = typer.Option(50, "--limit", "-n", help="Max messages"),
):
    """Show message log history (log)."""
    from agentteam.identity import AgentIdentity
    from agentteam.team.mailbox import MailboxManager

    inbox_name = agent or AgentIdentity.from_env().agent_name
    mailbox = MailboxManager(team)
    messages = mailbox.peek(inbox_name, limit=limit)

    def _human(msgs):
        if not msgs:
            console.print("[dim]No message history[/dim]")
            return
        for m in msgs:
            ts = m.get("timestamp", "")[:19]
            fr = m.get("from_agent", "unknown")
            content = m.get("content", "")[:80]
            console.print(f"[dim]{ts}[/dim] [{fr}] {content}")

    _output([{"from_agent": m.from_agent, "content": m.content, "timestamp": m.timestamp} for m in messages], _human)


@app.command("watch")
def inbox_watch(
    team: str = typer.Argument(..., help="Team name"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent name"),
    interval: int = typer.Option(2, "--interval", "-i", help="Polling interval in seconds"),
):
    """Continuously watch inbox for new messages (watch)."""
    from agentteam.identity import AgentIdentity
    from agentteam.team.mailbox import MailboxManager

    inbox_name = agent or AgentIdentity.from_env().agent_name
    mailbox = MailboxManager(team)
    seen_ids = set()

    console.print(f"[cyan]Watching inbox '{inbox_name}' (Ctrl+C to stop)[/cyan]\n")

    try:
        while True:
            messages = mailbox.peek(inbox_name, limit=20)
            new_msgs = [m for m in messages if m.message_id not in seen_ids]

            for m in new_msgs:
                seen_ids.add(m.message_id)
                ts = m.timestamp[:19] if m.timestamp else ""
                console.print(f"[dim]{ts}[/dim] [{m.from_agent}] {m.content}")

            time.sleep(interval)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped watching[/yellow]")


if __name__ == "__main__":
    app()
