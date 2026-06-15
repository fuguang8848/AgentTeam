"""Settings management mixin for the board handler."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agentteam.board.handlers.base import BaseHandler


class SettingsMixin:
    """Mixin for settings management functionality."""

    def _get_settings_file(self) -> Path:
        """Get the path to the settings configuration file."""
        config_dir = Path.home() / ".agentteam"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "settings.json"

    def _load_settings(self) -> dict[str, Any]:
        """Load settings configuration."""
        settings_file = self._get_settings_file()
        if settings_file.exists():
            with open(settings_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "theme": "dark",
            "language": "en",
            "notifications": {
                "enabled": True,
                "sound": True,
            },
            "dashboard": {
                "autoRefresh": True,
                "refreshInterval": 5,
            },
        }

    def _save_settings(self, data: dict[str, Any]) -> None:
        """Save settings configuration."""
        settings_file = self._get_settings_file()
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def handle_get_settings(self) -> None:
        """Handle GET /api/settings.

        Returns the settings configuration.
        """
        try:
            data = self._load_settings()
            self._serve_json(data)

        except Exception as e:
            self.send_error(500, str(e))

    def handle_save_settings(self) -> None:
        """Handle POST /api/settings.

        Saves the settings configuration.
        """
        payload = self._parse_json_body()
        if payload is None:
            return

        try:
            self._save_settings(payload)
            self._serve_json({"status": "ok", "saved": True})

        except Exception as e:
            self.send_error(400, str(e))

    def handle_reset_settings(self) -> None:
        """Handle POST /api/settings/reset.

        Resets settings to default values.
        """
        try:
            default_settings = {
                "theme": "dark",
                "language": "en",
                "notifications": {
                    "enabled": True,
                    "sound": True,
                },
                "dashboard": {
                    "autoRefresh": True,
                    "refreshInterval": 5,
                },
            }
            self._save_settings(default_settings)
            self._serve_json({"status": "ok", "reset": True})

        except Exception as e:
            self.send_error(400, str(e))
