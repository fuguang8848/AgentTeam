"""
Configuration and System Health Commands

Provides config management: show, init, set, get, health.
Provides doctor command: run, fix.
"""

from __future__ import annotations

import os
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich import box

from agentteam import __version__

app = typer.Typer(help="Configuration management commands")
doctor_app = typer.Typer(help="System health check commands")

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
        import json
        print(json.dumps(data, indent=2, ensure_ascii=False))
    elif human_fn:
        human_fn(data)
    else:
        import json
        print(json.dumps(data, indent=2, ensure_ascii=False))


# ============================================================================
# Doctor Commands
# ============================================================================


@doctor_app.command("run")
def doctor_run():
    """Run comprehensive system health check."""
    from agentteam.config import get_effective, config_path
    from agentteam.team.models import get_data_dir

    results = []

    # Check 1: Data directory
    data_dir = get_data_dir()
    result = {"check": "Data Directory", "status": "PASS", "details": ""}
    if not data_dir.exists():
        result["status"] = "FAIL"
        result["details"] = f"Directory does not exist: {data_dir}"
    else:
        try:
            test_file = data_dir / ".doctor-check"
            test_file.write_text("ok", encoding="utf-8")
            content = test_file.read_text(encoding="utf-8")
            test_file.unlink()
            if content == "ok":
                result["details"] = f"OK: {data_dir} (writable)"
            else:
                result["status"] = "FAIL"
                result["details"] = "Write/read verification failed"
        except Exception as e:
            result["status"] = "FAIL"
            result["details"] = f"Not writable: {e}"
    results.append(result)

    # Check 2: Config directory
    cfg_dir = config_path().parent
    result = {"check": "Config Directory", "status": "PASS", "details": ""}
    if not cfg_dir.exists():
        result["status"] = "WARN"
        result["details"] = f"Directory does not exist: {cfg_dir} (will use defaults)"
    else:
        result["details"] = f"OK: {cfg_dir}"
    results.append(result)

    # Check 3: Gateway connectivity
    result = {"check": "Gateway API", "status": "PASS", "details": ""}
    try:
        import urllib.request
        import json as json_module
        port = int(os.environ.get("OPENCLAW_GATEWAY_PORT", "18789"))
        url = f"http://127.0.0.1:{port}/health"
        token = os.environ.get("OPENCLAW_GATEWAY_TOKEN", "")
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json_module.loads(resp.read().decode())
            result["details"] = f"OK: Gateway responding (v{data.get('version', '?')})"
    except urllib.error.URLError:
        result["status"] = "WARN"
        result["details"] = "Gateway not reachable (may not be running)"
    except Exception as e:
        result["status"] = "WARN"
        result["details"] = f"Gateway check skipped: {e}"
    results.append(result)

    # Check 4: Config validity
    result = {"check": "Config Validity", "status": "PASS", "details": ""}
    try:
        val, source = get_effective("data_dir")
        result["details"] = f"data_dir={val} (from {source})"
    except Exception as e:
        result["status"] = "FAIL"
        result["details"] = f"Config error: {e}"
    results.append(result)

    # Check 5: Teams directory
    result = {"check": "Teams Directory", "status": "PASS", "details": ""}
    teams_dir = data_dir / "teams"
    if not teams_dir.exists():
        result["status"] = "WARN"
        result["details"] = "Teams directory does not exist (no teams created yet)"
    else:
        try:
            teams = [d.name for d in teams_dir.iterdir() if d.is_dir()]
            teams_str = ", ".join(teams[:5])
            if len(teams) > 5:
                teams_str += "..."
            result["details"] = f"OK: {len(teams)} team(s) found: {teams_str}"
        except Exception as e:
            result["status"] = "WARN"
            result["details"] = f"Cannot read teams: {e}"
    results.append(result)

    # Check 6: Database
    result = {"check": "Database", "status": "PASS", "details": ""}
    db_path = data_dir / "collab" / "collab.db"
    if db_path.exists():
        try:
            size = db_path.stat().st_size
            result["details"] = f"OK: Database exists ({size} bytes)"
        except Exception as e:
            result["status"] = "WARN"
            result["details"] = f"Database exists but error reading: {e}"
    else:
        result["status"] = "WARN"
        result["details"] = "Database not initialized (will be created on first use)"
    results.append(result)

    # Output results
    def _human(results):
        table = Table(title="System Health Check", box=box.ROUNDED)
        table.add_column("Check", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Details")
        for r in results:
            status_style = {"PASS": "green", "FAIL": "red", "WARN": "yellow"}.get(r["status"], "")
            table.add_row(r["check"], f"[{status_style}]{r['status']}[/{status_style}]", r["details"])
        console.print(table)

    _output(results, _human)


@doctor_app.command("fix")
def doctor_fix(
    all_fixes: bool = typer.Option(False, "--all", "-a", help="Apply all possible fixes"),
    cleanup: bool = typer.Option(False, "--cleanup", "-c", help="Clean up temp files and dead sessions"),
    init_config: bool = typer.Option(False, "--init-config", help="Initialize default config"),
):
    """Attempt to fix common issues found by doctor."""
    from agentteam.config import config_path
    from agentteam.team.models import get_data_dir

    fixes_applied = []

    # Fix 1: Create data directory
    data_dir = get_data_dir()
    if not data_dir.exists() or init_config:
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
            fixes_applied.append(f"Created data directory: {data_dir}")
        except Exception as e:
            console.print(f"[red]Failed to create data directory: {e}[/red]")

    # Fix 2: Initialize config
    if init_config or not config_path().exists():
        try:
            config_path().parent.mkdir(parents=True, exist_ok=True)
            config_content = f"""# AgentTeam Configuration
# Generated by agentteam doctor fix

data_dir: "{data_dir}"
default_backend: "auto"
workspace: "auto"
skip_permissions: true
"""
            config_path().write_text(config_content, encoding="utf-8")
            fixes_applied.append(f"Initialized config at: {config_path()}")
        except Exception as e:
            console.print(f"[red]Failed to initialize config: {e}[/red]")

    # Fix 3: Cleanup
    if cleanup or all_fixes:
        cleaned = 0
        try:
            for pattern in [".*.tmp", "*.tmp", ".health-check"]:
                for f in data_dir.glob(pattern):
                    try:
                        f.unlink()
                        cleaned += 1
                    except Exception:
                        pass
        except Exception:
            pass

        if cleaned > 0:
            fixes_applied.append(f"Cleaned up {cleaned} item(s)")
        else:
            console.print("[dim]No cleanup needed[/dim]")

    if fixes_applied:
        console.print("[bold]Fixes applied:[/bold]")
        for fix in fixes_applied:
            console.print(f"  [green]OK[/green] {fix}")
    else:
        console.print("[dim]No fixes needed[/dim]")


# ============================================================================
# Config Commands
# ============================================================================


@app.command("show")
def config_show():
    """Show current configuration."""
    from agentteam.config import get_effective

    settings = [
        "data_dir", "default_backend", "workspace", "skip_permissions",
        "max_agents", "transport", "log_level",
    ]

    def _human(items):
        table = Table(title="Configuration")
        table.add_column("Setting", style="cyan")
        table.add_column("Value")
        table.add_column("Source", style="dim")
        for key, val, source in items:
            table.add_row(key, str(val) if val else "(not set)", source)
        console.print(table)

    results = []
    for key in settings:
        try:
            val, source = get_effective(key)
            results.append((key, val, source))
        except Exception:
            results.append((key, "(error)", "unknown"))

    _output(results, _human)


@app.command("init")
def config_init(
    data_dir: Optional[str] = typer.Option(None, "--data-dir", help="Data directory"),
    backend: Optional[str] = typer.Option(None, "--backend", help="Default backend"),
    workspace: Optional[str] = typer.Option(None, "--workspace", help="Workspace mode"),
):
    """Initialize configuration file."""
    from pathlib import Path
    import yaml

    cfg_path = Path.home() / ".agentteam" / "config.yaml"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)

    config = {}
    if cfg_path.exists():
        try:
            config = yaml.safe_load(cfg_path.read_text()) or {}
        except Exception:
            pass

    if data_dir:
        config["data_dir"] = data_dir
    if backend:
        config["default_backend"] = backend
    if workspace:
        config["workspace"] = workspace

    cfg_path.write_text(yaml.dump(config), encoding="utf-8")
    _output({"status": "initialized", "path": str(cfg_path)}, lambda d: console.print(f"[green]OK[/green] Config saved to {d['path']}"))


@app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Config key"),
    value: str = typer.Argument(..., help="Config value"),
):
    """Set a configuration value."""
    from agentteam.config import config_path
    import yaml
    from pathlib import Path

    cfg_path = config_path()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)

    config = {}
    if cfg_path.exists():
        try:
            config = yaml.safe_load(cfg_path.read_text()) or {}
        except Exception:
            pass

    config[key] = value
    cfg_path.write_text(yaml.dump(config), encoding="utf-8")
    _output({"status": "set", "key": key, "value": value}, lambda d: console.print(f"[green]OK[/green] {d['key']} = {d['value']}"))


@app.command("get")
def config_get(
    key: Optional[str] = typer.Argument(None, help="Config key (show all if omitted)"),
):
    """Get configuration value."""
    from agentteam.config import get_effective

    if key:
        val, source = get_effective(key)
        _output({"key": key, "value": val, "source": source}, lambda d: console.print(f"{d['key']} = {d['value']} (from {d['source']})"))
    else:
        config_show()


@app.command("health")
def config_health():
    """Check configuration health."""
    from agentteam.config import get_effective, config_path

    issues = []

    # Check config file
    if not config_path().exists():
        issues.append("Config file not found (using defaults)")
    else:
        try:
            for key in ["data_dir", "default_backend"]:
                val, source = get_effective(key)
                if source == "default" and key in ["data_dir"]:
                    issues.append(f"{key} using default value (consider setting explicit value)")
        except Exception as e:
            issues.append(f"Config error: {e}")

    if issues:
        def _human(items):
            console.print("[yellow]Configuration issues:[/yellow]")
            for issue in items:
                console.print(f"  - {issue}")
        _output(issues, _human)
    else:
        console.print("[green]✓ Configuration is healthy[/green]")


if __name__ == "__main__":
    app()
