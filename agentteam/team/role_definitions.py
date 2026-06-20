"""Role definition module for MetaGPT-style agents.

Defines RoleDefinition and RoleDefinitionRegistry for managing agent roles.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


@dataclass
class RoleDefinition:
    """Definition of an agent role with skills and system prompt."""
    name: str
    description: str
    skills: list[str] = field(default_factory=list)
    system_prompt_template: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "skills": self.skills,
            "system_prompt_template": self.system_prompt_template,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RoleDefinition":
        return cls(
            name=data["name"],
            description=data["description"],
            skills=data.get("skills", []),
            system_prompt_template=data.get("system_prompt_template", ""),
        )


class RoleDefinitionRegistry:
    """Registry for managing role definitions with JSON persistence."""

    _instance: Optional["RoleDefinitionRegistry"] = None

    def __init__(self):
        self._roles: dict[str, RoleDefinition] = {}
        self._data_dir = Path.home() / ".agentteam" / "data" / "sops"
        self._ensure_data_dir()

    @classmethod
    def get_instance(cls) -> "RoleDefinitionRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _ensure_data_dir(self):
        self._data_dir.mkdir(parents=True, exist_ok=True)

    def _role_file_path(self, name: str) -> Path:
        safe_name = name.replace("/", "_").replace("\\", "_")
        return self._data_dir / f"role_{safe_name}.json"

    def register_role(self, role: RoleDefinition, persist: bool = True) -> None:
        """Register a role definition, optionally persisting to disk."""
        self._roles[role.name] = role
        if persist:
            self._persist_role(role)

    def _persist_role(self, role: RoleDefinition) -> None:
        file_path = self._role_file_path(role.name)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(role.to_dict(), f, indent=2, ensure_ascii=False)

    def get_role(self, name: str) -> Optional[RoleDefinition]:
        """Get a role definition by name, loading from disk if not in memory."""
        if name in self._roles:
            return self._roles[name]
        file_path = self._role_file_path(name)
        if file_path.exists():
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            role = RoleDefinition.from_dict(data)
            self._roles[name] = role
            return role
        return None

    def list_roles(self) -> list[str]:
        """List all registered role names."""
        return list(self._roles.keys())

    def load_all_from_disk(self) -> None:
        """Load all roles from the data directory into memory."""
        if not self._data_dir.exists():
            return
        for file_path in self._data_dir.glob("role_*.json"):
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            role = RoleDefinition.from_dict(data)
            self._roles[role.name] = role

    def unregister_role(self, name: str) -> bool:
        """Unregister a role and remove its persisted file."""
        if name in self._roles:
            del self._roles[name]
        file_path = self._role_file_path(name)
        if file_path.exists():
            file_path.unlink()
            return True
        return False
