"""Base handler class for the board server."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from agentteam.auth import auth_manager

if TYPE_CHECKING:
    from agentteam.board.collector import BoardCollector


class BaseHandler(BaseHTTPRequestHandler):
    """Base HTTP handler for the board Web UI.

    This class provides common functionality for all handlers.
    Subclasses should inherit from this and implement specific mixins.
    """

    # Class-level attributes to be set by the server
    collector: "BoardCollector"
    default_team: str = ""
    interval: float = 2.0

    # Public endpoints that don't require authentication
    _PUBLIC_ENDPOINTS = frozenset(["/", "/index.html", "/chat.html", "/api/health"])

    # Content type mappings for static files
    _CONTENT_TYPES = {
        ".html": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".ico": "image/x-icon",
        ".svg": "image/svg+xml",
        ".woff2": "font/woff2",
        ".woff": "font/woff",
        ".ttf": "font/ttf",
        ".eot": "application/vnd.ms-fontobject",
        ".map": "application/json; charset=utf-8",
    }

    @property
    def _static_dir(self) -> Path:
        """Get the static directory path."""
        return Path(__file__).parent.parent / "static"

    def _check_auth(self) -> bool:
        """Check authentication for the current request.

        Returns True if the request is authenticated or auth is not required.
        Returns False and sends 401 error if authentication fails.
        """
        # Check if auth is required
        if not auth_manager.is_auth_required():
            return True

        # Check for API key in X-API-Key header
        api_key = self.headers.get("X-API-Key", "")
        if api_key and auth_manager.verify_api_key(api_key):
            return True

        # Check for Bearer token in Authorization header
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            payload = auth_manager.verify_token(token)
            if payload and not payload.is_expired():
                return True

        # Authentication failed - send 401
        self.send_error(401, "Unauthorized")
        return False

    def _is_public_endpoint(self, path: str) -> bool:
        """Check if the path is a public endpoint that doesn't require auth."""
        if path in self._PUBLIC_ENDPOINTS:
            return True
        # Static files are public
        if not path.startswith("/api/"):
            return True
        return False

    def _get_content_type(self, filename: str) -> str:
        """Get the content type for a filename."""
        ext = Path(filename).suffix.lower()
        return self._CONTENT_TYPES.get(ext, "application/octet-stream")

    def _serve_json(self, data: dict) -> None:
        """Serve JSON response."""
        import json

        json_str = json.dumps(data, ensure_ascii=False)
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(json_str.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(json_str.encode("utf-8"))

    def _serve_static(self, filename: str, content_type: str) -> None:
        """Serve a static file."""
        file_path = self._static_dir / filename
        if not file_path.exists():
            self.send_error(404, f"File not found: {filename}")
            return

        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, str(e))

    def log_message(self, format: str, *args) -> None:
        """Log an HTTP request."""
        # Custom log format for the board server
        print(f"[Board] {self.address_string()} - {format % args}")

    def _parse_json_body(self) -> Optional[dict]:
        """Parse JSON body from the request."""
        import json

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return None

        try:
            body = self.rfile.read(content_length).decode("utf-8")
            return json.loads(body)
        except json.JSONDecodeError as e:
            self.send_error(400, f"Invalid JSON: {e}")
            return None
        except Exception as e:
            self.send_error(500, str(e))
            return None
