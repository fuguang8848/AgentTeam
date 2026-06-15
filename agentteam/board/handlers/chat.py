"""Chat handlers mixin for the board handler."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

# Import from handlers.sse
from agentteam.board.handlers.sse import _chat_event_queue, _chat_subscribers, _subscriber_lock


class ChatHandlersMixin:
    """Mixin for chat-related handlers."""

    def _serve_skills(self):
        try:
            from agentteam.skills.manager import get_skill_manager

            self._serve_json({"skills": get_skill_manager().list_skills()})
        except Exception as e:
            self._serve_json({"skills": [], "error": str(e)})

    def _serve_chat_history(self):
        from agentteam.board.utils import _now_iso

        params = parse_qs(urlparse(self.path).query)
        limit = int(params.get("limit", ["100"])[0])
        with _subscriber_lock:
            self._serve_json({"messages": list(_chat_event_queue)[-limit:]})

    def _chat_send(self):
        from agentteam.board.chat.commands import handle_chat_command
        from agentteam.board.utils import _now_iso

        payload = self._parse_json_body()
        if payload is None:
            return
        msg, user = payload.get("message", ""), payload.get("user", "User")
        if not msg:
            return self.send_error(400, "Message required")
        resp = handle_chat_command(msg, user)
        if resp.get("content") != "CLEAR_CHAT_HISTORY":
            _chat_event_queue.append(
                {
                    "type": "message",
                    "role": resp.get("role", "assistant"),
                    "content": resp.get("content", ""),
                    "timestamp": resp.get("timestamp", _now_iso()),
                    "user": user,
                }
            )
            self._notify_chat()
        self._serve_json(resp)

    def _chat_save(self):
        from agentteam.board.utils import _now_iso

        payload = self._parse_json_body()
        if payload is None:
            return
        _chat_event_queue.append(
            {
                "type": "message",
                "role": payload.get("role", "user"),
                "content": payload.get("content", ""),
                "timestamp": payload.get("timestamp", _now_iso()),
                "user": payload.get("user", "User"),
            }
        )
        self._notify_chat()
        self._serve_json({"status": "ok"})

    def _chat_clear(self):
        global _chat_event_queue
        from collections import deque

        _chat_event_queue = deque(maxlen=100)
        self._serve_json({"status": "ok", "cleared": True})

    def _notify_chat(self):
        with _subscriber_lock:
            for lock in _chat_subscribers[:]:
                try:
                    lock.release()
                except RuntimeError:
                    pass

    def _import_tmpl(self):
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode()
        try:
            tmpl = tomllib.loads(body).get("template", {})
            name = tmpl.get("name", "")
            if not name:
                return self.send_error(400, "Template name required")
            from pathlib import Path

            p = Path.home() / ".agentteam" / "templates" / f"{name}.toml"
            p.parent.mkdir(parents=True, exist_ok=True)
            try:
                import tomllib

                p.write_text(tomllib.dumps({"template": tmpl}), encoding="utf-8")
            except ImportError:
                import tomli as tomli

                p.write_text(tomli.dumps({"template": tmpl}), encoding="utf-8")
            self._serve_json({"success": True, "template": name, "path": str(p)})
        except Exception as e:
            self.send_error(400, f"Failed: {e}")
