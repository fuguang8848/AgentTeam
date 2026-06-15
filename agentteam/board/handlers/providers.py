"""Providers management mixin for the board handler."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agentteam.board.handlers.base import BaseHandler


class ProvidersMixin:
    """Mixin for providers management functionality."""

    def _get_providers_file(self) -> Path:
        """Get the path to the providers configuration file."""
        config_dir = Path.home() / ".agentteam"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "providers.json"

    def _load_providers(self) -> dict[str, Any]:
        """Load providers configuration."""
        providers_file = self._get_providers_file()
        if providers_file.exists():
            with open(providers_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"providers": {}}

    def _save_providers(self, data: dict[str, Any]) -> None:
        """Save providers configuration."""
        providers_file = self._get_providers_file()
        with open(providers_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def handle_get_providers(self) -> None:
        """Handle GET /api/providers.

        Returns the providers configuration.
        """
        try:
            data = self._load_providers()
            self._serve_json(data)

        except Exception as e:
            self.send_error(500, str(e))

    def handle_save_providers(self) -> None:
        """Handle POST /api/providers.

        Saves the providers configuration.
        """
        payload = self._parse_json_body()
        if payload is None:
            return

        try:
            self._save_providers(payload)
            self._serve_json({"status": "ok", "saved": True})

        except Exception as e:
            self.send_error(400, str(e))

    def handle_delete_provider(self, provider_name: str) -> None:
        """Handle DELETE /api/providers/{provider_name}.

        Deletes a provider from the configuration.
        """
        if not provider_name:
            self.send_error(400, "Provider name required")
            return

        try:
            data = self._load_providers()
            providers = data.get("providers", {})

            if provider_name not in providers:
                self.send_error(404, f"Provider '{provider_name}' not found")
                return

            del providers[provider_name]
            data["providers"] = providers
            self._save_providers(data)

            self._serve_json({"status": "ok", "deleted": provider_name})

        except Exception as e:
            self.send_error(400, str(e))

    def handle_import_provider(self) -> None:
        """Handle POST /api/providers/import.

        Imports a provider from TOML content.
        """
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self.send_error(400, "Request body required")
            return

        try:
            body = self.rfile.read(content_length).decode("utf-8")

            # Parse TOML content
            try:
                import tomllib
            except ImportError:
                import tomli as tomllib

            tmpl_data = tomllib.loads(body)
            provider_config = tmpl_data.get("provider", tmpl_data)
            provider_name = provider_config.get("name", "")
            if not provider_name:
                self.send_error(400, "Provider name is required")
                return

            # Load existing providers
            data = self._load_providers()
            providers = data.get("providers", {})

            # Add/update provider
            providers[provider_name] = provider_config
            data["providers"] = providers
            self._save_providers(data)

            self._serve_json({"success": True, "provider": provider_name})

        except Exception as e:
            self.send_error(400, f"Failed to import provider: {e}")
