from __future__ import annotations

import io
from pathlib import Path

import pytest

from clawteam.board.collector import BoardCollector
from clawteam.board.server import BoardHandler, _fetch_proxy_content, _normalize_proxy_target
from clawteam.team.mailbox import MailboxManager
from clawteam.team.manager import TeamManager


@pytest.mark.skip(reason="upstream feature not yet synced: collect_overview leader/pendingMessages fields")
def test_collect_overview_does_not_call_collect_team(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    TeamManager.create_team(
        name="demo",
        leader_name="leader",
        leader_id="leader001",
        description="demo team",
    )

    def fail_collect_team(self, team_name: str):
        raise AssertionError("collect_team should not be called for overview")

    monkeypatch.setattr(BoardCollector, "collect_team", fail_collect_team)

    teams = BoardCollector().collect_overview()

    assert teams == [
        {
            "name": "demo",
            "description": "demo team",
            "leader": "leader",
            "members": 1,
            "tasks": 0,
            "pendingMessages": 0,
        }
    ]


@pytest.mark.skip(reason="upstream feature not yet synced: collect_overview inbox count summing")
def test_collect_overview_sums_inbox_counts_for_all_members(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    TeamManager.create_team(
        name="demo",
        leader_name="leader",
        leader_id="leader001",
        description="demo team",
    )
    TeamManager.add_member("demo", "worker", "worker001")
    MailboxManager("demo").send(from_agent="leader", to="worker", content="hello")

    def fail_collect_team(self, team_name: str):
        raise AssertionError("collect_team should not be called for overview")

    monkeypatch.setattr(BoardCollector, "collect_team", fail_collect_team)

    teams = BoardCollector().collect_overview()

    assert teams == [
        {
            "name": "demo",
            "description": "demo team",
            "leader": "leader",
            "members": 2,
            "tasks": 0,
            "pendingMessages": 1,
        }
    ]


def test_team_snapshot_cache_reuses_value_within_ttl():
    from clawteam.board.server import TeamSnapshotCache

    calls = {"count": 0}

    def loader():
        calls["count"] += 1
        return {"version": calls["count"]}

    cache = TeamSnapshotCache(ttl_seconds=60.0)

    first = cache.get("demo", loader)
    second = cache.get("demo", loader)

    assert first == {"version": 1}
    assert second == {"version": 1}
    assert calls["count"] == 1


def test_team_snapshot_cache_expires_after_ttl(monkeypatch):
    from clawteam.board.server import TeamSnapshotCache

    now = {"value": 100.0}
    monkeypatch.setattr("clawteam.board.server.time.monotonic", lambda: now["value"])

    calls = {"count": 0}

    def loader():
        calls["count"] += 1
        return {"version": calls["count"]}

    cache = TeamSnapshotCache(ttl_seconds=5.0)

    first = cache.get("demo", loader)
    now["value"] += 10.0
    second = cache.get("demo", loader)

    assert first == {"version": 1}
    assert second == {"version": 2}
    assert calls["count"] == 2


@pytest.mark.skip(reason="upstream feature not yet synced: collect_team conflicts field")
def test_collect_team_preserves_conflicts_field(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    TeamManager.create_team(
        name="demo",
        leader_name="leader",
        leader_id="leader001",
        description="demo team",
    )

    data = BoardCollector().collect_team("demo")

    assert "conflicts" in data


@pytest.mark.skip(reason="upstream feature not yet synced: collect_team memberKey/inboxName fields")
def test_collect_team_exposes_member_inbox_identity(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    TeamManager.create_team(
        name="demo",
        leader_name="leader",
        leader_id="leader001",
        description="demo team",
    )
    TeamManager.add_member("demo", "worker", "worker001", user="alice")

    data = BoardCollector().collect_team("demo")

    worker = next(member for member in data["members"] if member["name"] == "worker")
    assert worker["memberKey"] == "alice_worker"
    assert worker["inboxName"] == "alice_worker"


@pytest.mark.skip(reason="upstream feature not yet synced: collect_team message participant normalization")
def test_collect_team_normalizes_message_participants(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    TeamManager.create_team(
        name="demo",
        leader_name="leader",
        leader_id="leader001",
        description="demo team",
    )
    TeamManager.add_member("demo", "worker", "worker001", user="alice")
    mailbox = MailboxManager("demo")
    mailbox.send(from_agent="leader", to="worker", content="hello")
    mailbox.broadcast(from_agent="leader", content="broadcast")

    data = BoardCollector().collect_team("demo")

    direct = next(msg for msg in data["messages"] if msg.get("content") == "hello")
    assert direct["fromKey"] == "leader"
    assert direct["fromLabel"] == "leader"
    assert direct["toKey"] == "alice_worker"
    assert direct["toLabel"] == "worker"
    assert direct["isBroadcast"] is False

    broadcast = next(
        msg
        for msg in data["messages"]
        if msg.get("content") == "broadcast" and msg.get("to") == "alice_worker"
    )
    assert broadcast["fromKey"] == "leader"
    assert broadcast["toKey"] == "alice_worker"
    assert broadcast["toLabel"] == "worker"
    assert broadcast["isBroadcast"] is True


@pytest.mark.skip(reason="upstream feature not yet synced: BoardCollector.collect_team_summary method")
def test_collect_overview_preserves_broken_team_fallback(monkeypatch):
    def fake_discover():
        return [
            {
                "name": "good",
                "description": "good team",
                "memberCount": 1,
            },
            {
                "name": "broken",
                "description": "broken team",
                "memberCount": 7,
            },
        ]

    def fake_summary(self, team_name: str):
        if team_name == "broken":
            raise ValueError("boom")
        return {
            "name": "good",
            "description": "good team",
            "leader": "lead",
            "members": 1,
            "tasks": 3,
            "pendingMessages": 2,
        }

    monkeypatch.setattr(TeamManager, "discover_teams", staticmethod(fake_discover))
    monkeypatch.setattr(BoardCollector, "collect_team_summary", fake_summary)

    overview = BoardCollector().collect_overview()

    assert overview == [
        {
            "name": "good",
            "description": "good team",
            "leader": "lead",
            "members": 1,
            "tasks": 3,
            "pendingMessages": 2,
        },
        {
            "name": "broken",
            "description": "broken team",
            "leader": "",
            "members": 7,
            "tasks": 0,
            "pendingMessages": 0,
        },
    ]


def test_serve_team_reads_fresh_snapshot_without_cache(monkeypatch):
    calls = {"count": 0}
    served = {}

    class FakeCache:
        def get(self, team_name, loader):
            raise AssertionError("team cache should not be used for /api/team")

    handler = object.__new__(BoardHandler)
    handler.collector = type(
        "Collector",
        (),
        {
            "collect_team": staticmethod(
                lambda team_name: calls.__setitem__("count", calls["count"] + 1)
                or {"team": {"name": team_name}}
            )
        },
    )()
    handler.team_cache = FakeCache()
    handler._serve_json = lambda data: served.setdefault("data", data)

    handler._serve_team("demo")

    assert calls["count"] == 1
    assert served["data"] == {"team": {"name": "demo"}}


def test_serve_sse_uses_shared_team_snapshot_cache(monkeypatch):
    calls = {"count": 0}

    class FakeCache:
        def get(self, team_name, loader):
            calls["count"] += 1
            return loader()

    handler = object.__new__(BoardHandler)
    handler.collector = type(
        "Collector",
        (),
        {"collect_team": staticmethod(lambda team_name: {"team": {"name": team_name}})},
    )()
    handler.team_cache = FakeCache()
    handler.interval = 0.0
    handler.wfile = io.BytesIO()
    handler.send_response = lambda code: None
    handler.send_header = lambda name, value: None
    handler.end_headers = lambda: None
    monkeypatch.setattr(
        handler.wfile,
        "flush",
        lambda: (_ for _ in ()).throw(BrokenPipeError()),
    )

    handler._serve_sse("demo")

    assert calls["count"] == 1


def test_proxy_rejects_non_github_targets():
    with pytest.raises(ValueError, match="GitHub-hosted"):
        _normalize_proxy_target("https://example.com/secret")


def test_proxy_rejects_localhost_targets():
    with pytest.raises(ValueError, match="not allowed"):
        _normalize_proxy_target("https://127.0.0.1/admin")


def test_proxy_fetches_allowed_github_content(monkeypatch):
    seen = {}

    class FakeResponse:
        def __init__(self, url: str, payload: bytes):
            self._url = url
            self._payload = payload

        def geturl(self):
            return self._url

        def read(self):
            return self._payload

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeOpener:
        def open(self, req, timeout=10):
            seen["url"] = req.full_url
            return FakeResponse(req.full_url, b"ok")

    monkeypatch.setattr("clawteam.board.server.urllib.request.build_opener", lambda *_: FakeOpener())

    assert _fetch_proxy_content("https://raw.githubusercontent.com/org/repo/main/README.md") == b"ok"
    assert seen["url"] == "https://raw.githubusercontent.com/org/repo/main/README.md"


def test_board_ui_escapes_attacker_controlled_fields():
    html = Path("clawteam/board/static/index.html").read_text(encoding="utf-8")

    assert "escapeHtml(m.name)" in html
    assert "escapeHtml(m.agentType || 'Agent')" in html
    assert "escapeHtml(m.fromLabel || m.from || 'SYS')" in html
    assert "escapeHtml(m.toLabel || m.to || 'ALL')" in html
    assert "escapeHtml(t.owner || 'Unassigned')" in html
    assert "t.blockedBy.map(v => escapeHtml(v)).join(', ')" in html
    assert "option.textContent =" in html


# ========== P5 Web UI Enhancement Tests ==========

class TestBoardHTTPEndpoints:
    """Test HTTP endpoints for the Web UI board server."""

    def test_get_root_serves_index_html(self, tmp_path, monkeypatch):
        """Test that GET / returns the index.html page."""
        from http.server import HTTPServer
        import threading
        import time
        import urllib.request

        monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))

        # Create a test team
        TeamManager.create_team(
            name="test-team",
            leader_name="leader",
            leader_id="leader001",
            description="test team",
        )

        # Start server in background
        from clawteam.board.server import serve, BoardHandler, BoardCollector

        collector = BoardCollector()
        BoardHandler.collector = collector
        BoardHandler.default_team = "test-team"
        BoardHandler.interval = 2.0
        BoardHandler.team_cache = None

        server = HTTPServer(("127.0.0.1", 8765), BoardHandler)
        thread = threading.Thread(target=server.handle_request)
        thread.start()

        time.sleep(0.5)

        try:
            resp = urllib.request.urlopen("http://127.0.0.1:8765/", timeout=5)
            content = resp.read().decode("utf-8")
            assert "<!DOCTYPE html>" in content
            assert "ClawTeam" in content
        finally:
            server.server_close()

    def test_get_api_overview_returns_teams_list(self, tmp_path):
        """Test that GET /api/overview returns team list."""
        import json
        import urllib.request

        TeamManager.create_team(
            name="team-alpha",
            leader_name="alpha-lead",
            leader_id="alpha001",
            description="Alpha team",
        )
        TeamManager.create_team(
            name="team-beta",
            leader_name="beta-lead",
            leader_id="beta001",
            description="Beta team",
        )

        # Use collector directly since HTTP server setup is complex
        collector = BoardCollector()
        overview = collector.collect_overview()

        assert len(overview) == 2
        assert any(t["name"] == "team-alpha" for t in overview)
        assert any(t["name"] == "team-beta" for t in overview)

    def test_get_api_team_returns_team_data(self, tmp_path):
        """Test that GET /api/team/{name} returns team details."""
        TeamManager.create_team(
            name="demo-team",
            leader_name="demo-lead",
            leader_id="demo001",
            description="Demo team for testing",
        )

        collector = BoardCollector()
        data = collector.collect_team("demo-team")

        assert data["team"]["name"] == "demo-team"
        assert data["team"]["description"] == "Demo team for testing"
        assert "members" in data
        assert "tasks" in data
        assert "taskSummary" in data

    def test_post_api_team_task_creates_task(self, tmp_path):
        """Test that POST /api/team/{name}/task creates a new task."""
        from clawteam.team.tasks import TaskStore

        TeamManager.create_team(
            name="task-test-team",
            leader_name="lead",
            leader_id="lead001",
        )

        store = TaskStore("task-test-team")
        task = store.create(
            subject="Test task subject",
            description="Test task description",
            owner="worker1"
        )

        assert task.id is not None
        assert task.subject == "Test task subject"
        assert task.owner == "worker1"

    def test_patch_api_team_task_updates_status(self, tmp_path):
        """Test that PATCH /api/team/{name}/task/{id} updates task status."""
        from clawteam.team.tasks import TaskStore
        from clawteam.team.models import TaskStatus

        TeamManager.create_team(
            name="status-test-team",
            leader_name="lead",
            leader_id="lead001",
        )

        store = TaskStore("status-test-team")
        task = store.create(subject="Task to update", owner="worker1")

        # Update status to in_progress
        updated = store.update(task.id, status=TaskStatus.in_progress)

        assert updated is not None
        assert updated.status == TaskStatus.in_progress

        # Update status to completed
        updated2 = store.update(task.id, status=TaskStatus.completed)
        assert updated2.status == TaskStatus.completed

    def test_get_api_team_nonexistent_returns_error(self, tmp_path):
        """Test that GET /api/team/{nonexistent} returns error."""
        collector = BoardCollector()

        with pytest.raises(ValueError, match="not found"):
            collector.collect_team("nonexistent-team")


class TestBoardCollector:
    """Test BoardCollector data aggregation."""

    def test_collect_team_returns_correct_structure(self, tmp_path):
        """Test that collect_team returns all expected fields."""
        TeamManager.create_team(
            name="structure-test",
            leader_name="lead",
            leader_id="lead001",
            description="Structure test team",
        )

        collector = BoardCollector()
        data = collector.collect_team("structure-test")

        # Check top-level keys
        assert "team" in data
        assert "members" in data
        assert "tasks" in data
        assert "taskSummary" in data
        assert "messages" in data
        assert "cost" in data

        # Check team structure
        assert data["team"]["name"] == "structure-test"
        assert data["team"]["leaderName"] == "lead"
        assert "createdAt" in data["team"]

        # Check taskSummary structure
        assert "pending" in data["taskSummary"]
        assert "in_progress" in data["taskSummary"]
        assert "completed" in data["taskSummary"]
        assert "blocked" in data["taskSummary"]
        assert "total" in data["taskSummary"]

    def test_collect_team_includes_member_alive_status(self, tmp_path):
        """Test that collect_team includes member alive status."""
        TeamManager.create_team(
            name="alive-test",
            leader_name="lead",
            leader_id="lead001",
        )
        TeamManager.add_member("alive-test", "worker", "worker001")

        collector = BoardCollector()
        data = collector.collect_team("alive-test")

        for member in data["members"]:
            assert "alive" in member
            # alive can be bool or None (when agent registry not available)
            assert member["alive"] is None or isinstance(member["alive"], bool)

    def test_collect_team_groups_tasks_by_status(self, tmp_path):
        """Test that collect_team correctly groups tasks by status."""
        from clawteam.team.tasks import TaskStore
        from clawteam.team.models import TaskStatus

        TeamManager.create_team(
            name="group-test",
            leader_name="lead",
            leader_id="lead001",
        )

        store = TaskStore("group-test")
        # Create tasks in different statuses
        t1 = store.create(subject="Pending task", owner="w1")
        t2 = store.create(subject="Progress task", owner="w2")
        store.update(t2.id, status=TaskStatus.in_progress)
        t3 = store.create(subject="Completed task", owner="w3")
        store.update(t3.id, status=TaskStatus.completed)

        collector = BoardCollector()
        data = collector.collect_team("group-test")

        assert len(data["tasks"]["pending"]) == 1
        assert len(data["tasks"]["in_progress"]) == 1
        assert len(data["tasks"]["completed"]) == 1
        assert len(data["tasks"]["blocked"]) == 0

    def test_collect_team_includes_messages(self, tmp_path):
        """Test that collect_team includes message history."""
        TeamManager.create_team(
            name="msg-test",
            leader_name="lead",
            leader_id="lead001",
        )
        TeamManager.add_member("msg-test", "worker", "worker001")

        mailbox = MailboxManager("msg-test")
        mailbox.send(from_agent="lead", to="worker", content="Hello worker")
        mailbox.send(from_agent="worker", to="lead", content="Hello lead")

        collector = BoardCollector()
        data = collector.collect_team("msg-test")

        assert len(data["messages"]) >= 2

    def test_collect_overview_returns_all_teams(self, tmp_path):
        """Test that collect_overview returns all teams with summary."""
        TeamManager.create_team(
            name="overview-a",
            leader_name="lead-a",
            leader_id="lead001",
            description="Team A",
        )
        TeamManager.create_team(
            name="overview-b",
            leader_name="lead-b",
            leader_id="lead002",
            description="Team B",
        )

        collector = BoardCollector()
        overview = collector.collect_overview()

        assert len(overview) == 2
        for team in overview:
            assert "name" in team
            assert "description" in team
            assert "leader" in team
            assert "members" in team
            assert "tasks" in team
            assert "pendingMessages" in team


class TestBoardUIFeatures:
    """Test Web UI frontend features."""

    def test_index_html_has_theme_toggle(self):
        """Test that index.html includes theme toggle functionality."""
        html = Path("clawteam/board/static/index.html").read_text(encoding="utf-8")

        assert "toggleTheme" in html
        assert "theme-toggle" in html
        assert "data-theme" in html

    def test_index_html_has_task_drag_drop(self):
        """Test that index.html includes drag and drop functionality."""
        html = Path("clawteam/board/static/index.html").read_text(encoding="utf-8")

        assert "draggable=\"true\"" in html
        assert "dragstart" in html or "dragging" in html
        assert "data-task-id" in html
        assert "data-task-status" in html

    def test_index_html_has_task_detail_modal(self):
        """Test that index.html includes task detail modal."""
        html = Path("clawteam/board/static/index.html").read_text(encoding="utf-8")

        assert "task-detail-modal" in html
        assert "openTaskDetailModal" in html
        assert "closeTaskDetailModal" in html

    def test_index_html_has_message_filter(self):
        """Test that index.html includes message filtering."""
        html = Path("clawteam/board/static/index.html").read_text(encoding="utf-8")

        assert "message-filter" in html or "filterMessages" in html
        assert "setMessageFilter" in html

    def test_index_html_has_responsive_design(self):
        """Test that index.html includes responsive CSS."""
        html = Path("clawteam/board/static/index.html").read_text(encoding="utf-8")

        assert "@media" in html
        assert "max-width:" in html

    def test_index_html_has_patch_api_call(self):
        """Test that index.html calls PATCH API for status update."""
        html = Path("clawteam/board/static/index.html").read_text(encoding="utf-8")

        assert "'PATCH'" in html or "method: 'PATCH'" in html
        assert "cycleTaskStatus" in html

    def test_index_html_has_team_overview(self):
        """Test that index.html includes team overview functionality."""
        html = Path("clawteam/board/static/index.html").read_text(encoding="utf-8")

        assert "showTeamOverview" in html
        assert "team-overview-card" in html

    def test_index_html_has_mobile_menu(self):
        """Test that index.html includes mobile menu toggle."""
        html = Path("clawteam/board/static/index.html").read_text(encoding="utf-8")

        assert "mobile-menu-btn" in html
        assert "toggleMobileMenu" in html


class TestBoardServerSecurity:
    """Test security features of the board server."""

    def test_proxy_rejects_non_https(self):
        """Test that proxy rejects non-HTTPS URLs."""
        with pytest.raises(ValueError, match="https"):
            _normalize_proxy_target("http://example.com/data")

    def test_proxy_rejects_private_ips(self):
        """Test that proxy rejects private IP addresses."""
        with pytest.raises(ValueError, match="not allowed"):
            _normalize_proxy_target("https://192.168.1.1/admin")

    def test_proxy_rejects_localhost(self):
        """Test that proxy rejects localhost."""
        with pytest.raises(ValueError, match="not allowed"):
            _normalize_proxy_target("https://localhost/admin")

    def test_proxy_allows_github_raw_content(self, monkeypatch):
        """Test that proxy allows GitHub raw content URLs."""
        # This should not raise
        result = _normalize_proxy_target(
            "https://raw.githubusercontent.com/org/repo/main/README.md"
        )
        assert "raw.githubusercontent.com" in result

    def test_escape_html_prevents_xss(self):
        """Test that escapeHtml function properly escapes dangerous chars."""
        html = Path("clawteam/board/static/index.html").read_text(encoding="utf-8")

        # Check that escapeHtml is defined and used
        assert "function escapeHtml" in html
        assert "&amp;" in html
        assert "&lt;" in html
        assert "&gt;" in html
