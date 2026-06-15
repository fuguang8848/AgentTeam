"""SSE handlers mixin for the board handler."""

from __future__ import annotations

import json
import threading
from collections import deque
from urllib.parse import parse_qs, urlparse

# Global chat event broadcaster
_chat_event_queue = deque(maxlen=100)
_chat_subscribers = []
_subscriber_lock = threading.Lock()


class SSEHandlersMixin:
    """Mixin for SSE (Server-Sent Events) handlers."""

    def _sse_events(self):
        from agentteam.board.sse.broadcast import (
            _event_queue,
            _event_subscribers,
            _event_broadcaster_lock,
            _register_event_subscriber,
        )

        _register_event_subscriber()
        params = parse_qs(urlparse(self.path).query)
        team, agent = params.get("team", [None])[0], params.get("agent", [None])[0]
        self._stream_sse(_event_queue, _event_subscribers, _event_broadcaster_lock, team, agent)

    def _sse_activity(self):
        from agentteam.board.sse.agent_activity import (
            _agent_activity_queue,
            _agent_activity_subscribers,
            _agent_activity_lock,
        )

        params = parse_qs(urlparse(self.path).query)
        team, agent = params.get("team", [None])[0], params.get("agent", [None])[0]
        self._stream_sse(_agent_activity_queue, _agent_activity_subscribers, _agent_activity_lock, team, agent)

    def _sse_chat(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        last_idx, lock = self._reg_subscriber(_chat_subscribers, _subscriber_lock)
        self._stream_chat(lock, last_idx)

    def _stream_sse(self, queue, subscribers, lock, team, agent):
        from agentteam.board.utils import _now_iso

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        last_idx, sub_lock = self._reg_subscriber(subscribers, lock)
        try:
            self.wfile.write(
                f"data: {json.dumps({'type': 'connected', 'timestamp': _now_iso()}, ensure_ascii=False)}\n\n".encode()
            )
            self.wfile.flush()
            while True:
                acquired = sub_lock.acquire(timeout=10)
                if acquired:
                    sub_lock.release()
                with lock:
                    while len(queue) > last_idx:
                        d = queue[last_idx]
                        if (team is None or d.get("team_name") == team) and (
                            agent is None or d.get("agent_name") == agent
                        ):
                            self.wfile.write(
                                f"data: {json.dumps({'type': 'event', 'data': d}, ensure_ascii=False)}\n\n".encode()
                            )
                            self.wfile.flush()
                        last_idx += 1
                self.wfile.write(f"data: {json.dumps({'type': 'heartbeat'}, ensure_ascii=False)}\n\n".encode())
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            with lock:
                if sub_lock in subscribers:
                    subscribers.remove(sub_lock)

    def _stream_chat(self, sub_lock, last_idx):
        from agentteam.board.utils import _now_iso

        try:
            with _subscriber_lock:
                for e in list(_chat_event_queue)[-50:]:
                    self.wfile.write(
                        f"data: {json.dumps({'type': 'chat_event', 'data': e}, ensure_ascii=False)}\n\n".encode()
                    )
                    self.wfile.flush()
            while True:
                acquired = sub_lock.acquire(timeout=10)
                if acquired:
                    sub_lock.release()
                with _subscriber_lock:
                    while len(_chat_event_queue) > last_idx:
                        self.wfile.write(
                            f"data: {json.dumps({'type': 'chat_event', 'data': _chat_event_queue[last_idx]}, ensure_ascii=False)}\n\n".encode()
                        )
                        self.wfile.flush()
                        last_idx += 1
                self.wfile.write(f"data: {json.dumps({'type': 'heartbeat'}, ensure_ascii=False)}\n\n".encode())
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            with _subscriber_lock:
                if sub_lock in _chat_subscribers:
                    _chat_subscribers.remove(sub_lock)

    def _reg_subscriber(self, subscribers, lock):
        idx = len(subscribers)
        sub_lock = threading.Lock()
        sub_lock.acquire()
        with lock:
            subscribers.append(sub_lock)
        return idx, sub_lock

    def _emit_activity(self):
        from agentteam.board.sse.agent_activity import _broadcast_agent_activity
        from agentteam.board.utils import _now_iso

        payload = self._parse_json_body()
        if payload is None:
            return
        try:
            payload.setdefault("timestamp", _now_iso())
            _broadcast_agent_activity(payload)
            self._serve_json({"status": "ok"})
        except Exception as e:
            self.send_error(400, str(e))

    # Expose chat queue for import
    @staticmethod
    def get_chat_queue():
        return _chat_event_queue
