"""MetaGPT-style SOP (Standard Operating Procedure) module.

Defines SOPStep, SOP, and SOPRegistry for managing agent workflows.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path


@dataclass
class SOPStep:
    """A single step in a Standard Operating Procedure."""
    step_id: str
    agent_role: str
    action: str
    input_keys: list[str] = field(default_factory=list)
    output_key: str = ""
    condition: str = ""  # Optional condition to trigger this step


@dataclass
class SOP:
    """A Standard Operating Procedure composed of multiple steps."""
    name: str
    description: str
    steps: list[SOPStep] = field(default_factory=list)
    required_roles: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "steps": [asdict(s) for s in self.steps],
            "required_roles": self.required_roles,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SOP":
        steps = [SOPStep(**s) for s in data.get("steps", [])]
        return cls(
            name=data["name"],
            description=data["description"],
            steps=steps,
            required_roles=data.get("required_roles", []),
        )


class SOPRegistry:
    """Registry for managing SOPs with JSON persistence."""

    _instance: Optional["SOPRegistry"] = None

    def __init__(self):
        self._sops: dict[str, SOP] = {}
        self._data_dir = Path.home() / ".agentteam" / "data" / "sops"
        self._ensure_data_dir()

    @classmethod
    def get_instance(cls) -> "SOPRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _ensure_data_dir(self):
        self._data_dir.mkdir(parents=True, exist_ok=True)

    def _sop_file_path(self, name: str) -> Path:
        safe_name = name.replace("/", "_").replace("\\", "_")
        return self._data_dir / f"{safe_name}.json"

    def register_sop(self, sop: SOP, persist: bool = True) -> None:
        """Register a SOP, optionally persisting to disk."""
        self._sops[sop.name] = sop
        if persist:
            self._persist_sop(sop)

    def _persist_sop(self, sop: SOP) -> None:
        file_path = self._sop_file_path(sop.name)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(sop.to_dict(), f, indent=2, ensure_ascii=False)

    def get_sop(self, name: str) -> Optional[SOP]:
        """Get a SOP by name, loading from disk if not in memory."""
        if name in self._sops:
            return self._sops[name]
        file_path = self._sop_file_path(name)
        if file_path.exists():
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            sop = SOP.from_dict(data)
            self._sops[name] = sop
            return sop
        return None

    def list_sops(self) -> list[str]:
        """List all registered SOP names."""
        return list(self._sops.keys())

    def load_all_from_disk(self) -> None:
        """Load all SOPs from the data directory into memory."""
        if not self._data_dir.exists():
            return
        for file_path in self._data_dir.glob("*.json"):
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            sop = SOP.from_dict(data)
            self._sops[sop.name] = sop

    def unregister_sop(self, name: str) -> bool:
        """Unregister a SOP and remove its persisted file."""
        if name in self._sops:
            del self._sops[name]
        file_path = self._sop_file_path(name)
        if file_path.exists():
            file_path.unlink()
            return True
        return False
