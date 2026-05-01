"""
Tool Registry - Register and discover tools for ClawTeam agents

Security: All credentials are loaded from environment variables or OpenClaw config.
NEVER hardcode sensitive information!
"""

import os
import json
from typing import Dict, Any, Optional, Callable
from pathlib import Path


class ToolRegistry:
    """Tool registry for ClawTeam agents"""
    
    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._load_builtin_tools()
    
    def _load_builtin_tools(self):
        """Load built-in tools"""
        self.register(
            name="http_request",
            description="Make HTTP requests",
            category="utility",
            schema={
                "url": {"type": "string", "required": True},
                "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"]},
                "headers": {"type": "object"},
                "body": {"type": "object"}
            },
            func=self._http_tool
        )
        
        self.register(
            name="file_read",
            description="Read file contents",
            category="file",
            schema={
                "path": {"type": "string", "required": True}
            },
            func=self._file_read_tool
        )
        
        self.register(
            name="file_write",
            description="Write content to file",
            category="file",
            schema={
                "path": {"type": "string", "required": True},
                "content": {"type": "string", "required": True}
            },
            func=self._file_write_tool
        )
    
    def register(
        self,
        name: str,
        description: str,
        category: str,
        schema: Dict[str, Any],
        func: Optional[Callable] = None,
        skill_path: Optional[str] = None
    ):
        """Register a tool
        
        Args:
            name: Tool name
            description: Tool description
            category: Tool category (utility, file, api, etc.)
            schema: JSON schema for tool arguments
            func: Python function to call
            skill_path: Path to skill directory (alternative to func)
        """
        self._tools[name] = {
            "name": name,
            "description": description,
            "category": category,
            "schema": schema,
            "func": func,
            "skill_path": skill_path
        }
    
    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """Get tool by name"""
        return self._tools.get(name)
    
    def list(self, category: Optional[str] = None) -> list[Dict[str, Any]]:
        """List all tools, optionally filtered by category"""
        tools = list(self._tools.values())
        if category:
            tools = [t for t in tools if t["category"] == category]
        return tools
    
    def call(self, name: str, **kwargs) -> Any:
        """Call a tool by name"""
        tool = self.get(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found")
        
        if tool["func"]:
            return tool["func"](**kwargs)
        elif tool["skill_path"]:
            return self._call_skill(tool["skill_path"], **kwargs)
        else:
            raise ValueError(f"Tool '{name}' has no implementation")
    
    def _call_skill(self, skill_path: str, **kwargs) -> Any:
        """Call a skill by path"""
        # Skills are called via subprocess or imported
        # This is a placeholder - actual implementation depends on skill structure
        raise NotImplementedError("Skill execution not yet implemented")
    
    def _http_tool(self, url: str, method: str = "GET", headers: Dict = None, body: Any = None) -> Dict[str, Any]:
        """Built-in HTTP request tool"""
        import urllib.request
        import urllib.parse
        
        data = None
        if body:
            data = json.dumps(body).encode("utf-8")
        
        req = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers=headers or {}
        )
        
        with urllib.request.urlopen(req, timeout=30) as resp:
            return {
                "status": resp.status,
                "headers": dict(resp.headers),
                "body": resp.read().decode("utf-8")
            }
    
    def _file_read_tool(self, path: str) -> str:
        """Built-in file read tool"""
        with open(path, encoding="utf-8") as f:
            return f.read()
    
    def _file_write_tool(self, path: str, content: str) -> Dict[str, Any]:
        """Built-in file write tool"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"status": "ok", "path": path}
    
    def get_by_category(self) -> Dict[str, list]:
        """Get tools grouped by category"""
        result = {}
        for tool in self._tools.values():
            cat = tool["category"]
            if cat not in result:
                result[cat] = []
            result[cat].append(tool["name"])
        return result


# Global registry instance
_registry = None

def get_registry() -> ToolRegistry:
    """Get global tool registry instance"""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


# CLI commands
def list_tools_cli(category: str = None):
    """List all registered tools"""
    registry = get_registry()
    tools = registry.list(category=category)
    
    print("\nAvailable Tools:")
    print("-" * 60)
    
    for tool in tools:
        print(f"\n{tool['name']}")
        print(f"  Description: {tool['description']}")
        print(f"  Category: {tool['category']}")
        print(f"  Schema: {json.dumps(tool['schema'], indent=4)}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ClawTeam Tool Registry")
    parser.add_argument("--list", action="store_true", help="List all tools")
    parser.add_argument("--category", help="Filter by category")
    
    args = parser.parse_args()
    
    if args.list:
        list_tools_cli(category=args.category)
