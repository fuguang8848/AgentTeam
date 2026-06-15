"""Static file serving mixin for the board handler."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentteam.board.handlers.base import BaseHandler


class StaticMixin:
    """Mixin for static file serving functionality."""

    _static_dir: Path

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

    def serve_static_file(self, filename: str) -> bool:
        """Serve a static file.

        Returns True if the file was served, False if not found.
        """
        file_path = self._static_dir / filename
        if not file_path.exists():
            return False

        # Determine content type
        ext = Path(filename).suffix.lower()
        content_type = self._CONTENT_TYPES.get(ext, "application/octet-stream")

        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return True
        except Exception as e:
            self.send_error(500, str(e))
            return True  # Return True to indicate we handled the request

    def serve_files(self, filename: str) -> bool:
        """Serve a file from the static directory.

        Supports index.html, chat.html, and other static assets.
        Returns True if the file was served, False otherwise.
        """
        # Handle special cases
        if filename == "" or filename == "index.html":
            return self.serve_static_file("index.html")
        elif filename == "chat.html":
            return self.serve_static_file("chat.html")

        # Handle static assets
        if self.serve_static_file(filename):
            return True

        # Try with .html extension
        if not Path(filename).suffix:
            if self.serve_static_file(f"{filename}.html"):
                return True

        # Try index.html for directory-like paths
        if self.serve_static_file(f"{filename}/index.html"):
            return True

        return False

    def guess_content_type(self, filename: str) -> str:
        """Guess the content type for a filename."""
        ext = Path(filename).suffix.lower()
        return self._CONTENT_TYPES.get(ext, "application/octet-stream")
