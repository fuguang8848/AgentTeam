"""Transport management mixin for the board handler."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentteam.board.handlers.base import BaseHandler


class TransportMixin:
    """Mixin for transport management functionality."""

    def handle_get_transport_status(self) -> None:
        """Handle GET /api/transport/status.

        Returns the current transport status.
        """
        try:
            import os

            transport_type = os.environ.get("AGENTTEAM_TRANSPORT", "file")
            redis_url = os.environ.get("AGENTTEAM_REDIS_URL", "")

            # Check transport health
            health = "unknown"
            try:
                if transport_type == "redis":
                    # Check Redis connection
                    import redis

                    r = redis.from_url(redis_url)
                    r.ping()
                    health = "healthy"
                elif transport_type == "p2p":
                    # Check P2P status
                    health = "active"
                else:
                    # File transport is always healthy
                    health = "healthy"
            except Exception:
                health = "unhealthy"

            self._serve_json(
                {
                    "transport": transport_type,
                    "health": health,
                    "redisUrl": redis_url if transport_type == "redis" else None,
                }
            )

        except Exception as e:
            self.send_error(500, str(e))

    def handle_get_transport_stats(self) -> None:
        """Handle GET /api/transport/stats.

        Returns transport statistics.
        """
        try:
            import os
            from pathlib import Path

            transport_type = os.environ.get("AGENTTEAM_TRANSPORT", "file")

            stats = {
                "transport": transport_type,
                "stats": {},
            }

            if transport_type == "file":
                # File transport stats
                transport_dir = Path.home() / ".agentteam" / "transport"
                if transport_dir.exists():
                    files = list(transport_dir.glob("**/*"))
                    stats["stats"] = {
                        "fileCount": len(files),
                        "dirSize": sum(f.stat().st_size for f in files if f.is_file()),
                    }

            self._serve_json(stats)

        except Exception as e:
            self.send_error(500, str(e))

    def handle_switch_transport(self) -> None:
        """Handle POST /api/transport/switch.

        Switches the transport type.
        """
        payload = self._parse_json_body()
        if payload is None:
            return

        new_transport = payload.get("transport", "file")
        if new_transport not in ("file", "redis", "p2p"):
            self.send_error(400, "Invalid transport type")
            return

        try:
            import os

            os.environ["AGENTTEAM_TRANSPORT"] = new_transport
            if new_transport == "redis" and payload.get("redis_url"):
                os.environ["AGENTTEAM_REDIS_URL"] = payload.get("redis_url")

            self._serve_json(
                {
                    "status": "ok",
                    "transport": new_transport,
                    "message": "Transport configuration updated. Restart required for full effect.",
                }
            )

        except Exception as e:
            self.send_error(400, str(e))
