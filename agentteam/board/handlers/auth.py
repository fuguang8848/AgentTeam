"""Authentication mixin for the board handler."""

from __future__ import annotations

from typing import TYPE_CHECKING

from agentteam.auth import auth_manager

if TYPE_CHECKING:
    from agentteam.board.handlers.base import BaseHandler


class AuthMixin:
    """Mixin for authentication functionality."""

    # This will be a reference to the handler instance when mixed in
    _handler: "BaseHandler"

    def check_auth(self) -> bool:
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

    def is_public_endpoint(self, path: str) -> bool:
        """Check if the path is a public endpoint that doesn't require auth."""
        public_endpoints = frozenset(["/", "/index.html", "/chat.html", "/api/health"])
        if path in public_endpoints:
            return True
        # Static files are public
        if not path.startswith("/api/"):
            return True
        return False

    def handle_login(self) -> None:
        """Handle login request.

        POST /api/login
        """
        import json

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self.send_error(400, "Request body required")
            return

        try:
            body = json.loads(self.rfile.read(content_length).decode("utf-8"))
            username = body.get("username", "")
            password = body.get("password", "")

            # Attempt login
            token = auth_manager.login(username, password)
            if token:
                self._serve_json({
                    "success": True,
                    "token": token,
                    "expires_in": 86400,  # 24 hours
                })
            else:
                self.send_error(401, "Invalid credentials")

        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
        except Exception as e:
            self.send_error(500, str(e))

    def handle_logout(self) -> None:
        """Handle logout request.

        POST /api/logout
        """
        # Get token from header
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            auth_manager.logout(token)

        self._serve_json({"success": True})

    def handle_register(self) -> None:
        """Handle registration request.

        POST /api/register
        """
        import json

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self.send_error(400, "Request body required")
            return

        try:
            body = json.loads(self.rfile.read(content_length).decode("utf-8"))
            username = body.get("username", "")
            password = body.get("password", "")

            if not username or not password:
                self.send_error(400, "Username and password required")
                return

            # Attempt registration
            success, error = auth_manager.register(username, password)
            if success:
                self._serve_json({"success": True})
            else:
                self.send_error(400, error or "Registration failed")

        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
        except Exception as e:
            self.send_error(500, str(e))

    def handle_change_password(self) -> None:
        """Handle password change request.

        POST /api/password/change
        """
        import json

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self.send_error(400, "Request body required")
            return

        try:
            body = json.loads(self.rfile.read(content_length).decode("utf-8"))
            current_password = body.get("current_password", "")
            new_password = body.get("new_password", "")

            if not current_password or not new_password:
                self.send_error(400, "Current and new password required")
                return

            # Get current user
            auth_header = self.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                self.send_error(401, "Unauthorized")
                return

            token = auth_header[7:]
            payload = auth_manager.verify_token(token)
            if not payload or payload.is_expired():
                self.send_error(401, "Unauthorized")
                return

            # Change password
            success, error = auth_manager.change_password(payload.username, current_password, new_password)
            if success:
                self._serve_json({"success": True})
            else:
                self.send_error(400, error or "Password change failed")

        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
        except Exception as e:
            self.send_error(500, str(e))
