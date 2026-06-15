"""
Plugin system for AgentTeam

Provides a plugin architecture for extending AgentTeam functionality.
Supports both singleton (backward compatibility) and instance-based usage.

Example:
    # Instance-based (recommended for new code)
    from agentteam.plugins import PluginManager

    manager = PluginManager()
    manager.discover_plugins("/path/to/plugins")
    manager.load_plugin("my-plugin")

    # Singleton (backward compatible)
    from agentteam.plugins import get_plugin_manager

    manager = get_plugin_manager()
    manager.discover_plugins("/path/to/plugins")
"""

from __future__ import annotations

import importlib.util
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

from agentteam.utils.logger import get_logger

logger = get_logger(__name__)


# =============================================================================
# Standard Hook Names (Hook 标准化)
# =============================================================================


class Hooks(str, Enum):
    """Standard hook names for AgentTeam plugins.

    This enum provides a canonical list of all available hooks.
    Plugins should use these constants for consistency.
    """

    # Agent Lifecycle Hooks
    PRE_AGENT_SPAWN = "pre_agent_spawn"
    POST_AGENT_SPAWN = "post_agent_spawn"
    PRE_AGENT_KILL = "pre_agent_kill"
    POST_AGENT_KILL = "post_agent_kill"
    PRE_AGENT_RESTART = "pre_agent_restart"
    POST_AGENT_RESTART = "post_agent_restart"

    # Team Lifecycle Hooks
    PRE_TEAM_CREATE = "pre_team_create"
    POST_TEAM_CREATE = "post_team_create"
    PRE_TEAM_CLEANUP = "pre_team_cleanup"
    POST_TEAM_CLEANUP = "post_team_cleanup"
    PRE_AGENT_JOIN = "pre_agent_join"
    POST_AGENT_JOIN = "post_agent_join"

    # Task Lifecycle Hooks
    PRE_TASK_CREATE = "pre_task_create"
    POST_TASK_CREATE = "post_task_create"
    PRE_TASK_UPDATE = "pre_task_update"
    POST_TASK_UPDATE = "post_task_update"
    PRE_TASK_COMPLETE = "pre_task_complete"
    POST_TASK_COMPLETE = "post_task_complete"

    # Message Hooks
    PRE_MESSAGE_SEND = "pre_message_send"
    POST_MESSAGE_SEND = "post_message_send"
    PRE_MESSAGE_RECEIVE = "pre_message_receive"
    POST_MESSAGE_RECEIVE = "post_message_receive"

    # Lifecycle Hooks
    PRE_SHUTDOWN_REQUEST = "pre_shutdown_request"
    POST_SHUTDOWN_REQUEST = "post_shutdown_request"
    PRE_SHUTDOWN_APPROVE = "pre_shutdown_approve"
    POST_SHUTDOWN_APPROVE = "post_shutdown_approve"

    # Session Hooks
    PRE_SESSION_SAVE = "pre_session_save"
    POST_SESSION_SAVE = "post_session_save"
    PRE_SESSION_RESUME = "pre_session_resume"
    POST_SESSION_RESUME = "post_session_resume"

    # Config Hooks
    PRE_CONFIG_LOAD = "pre_config_load"
    POST_CONFIG_LOAD = "post_config_load"
    PRE_CONFIG_SAVE = "pre_config_save"
    POST_CONFIG_SAVE = "post_config_save"

    # Workspace Hooks
    PRE_WORKSPACE_CREATE = "pre_workspace_create"
    POST_WORKSPACE_CREATE = "post_workspace_create"
    PRE_WORKSPACE_MERGE = "pre_workspace_merge"
    POST_WORKSPACE_MERGE = "post_workspace_merge"

    @classmethod
    def values(cls) -> list[str]:
        """Return all hook names as strings."""
        return [h.value for h in cls]

    @classmethod
    def is_valid(cls, name: str) -> bool:
        """Check if a hook name is valid."""
        return name in cls.values()


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class PluginMetadata:
    """Plugin metadata"""

    id: str
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    hooks: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    entry_point: Optional[str] = None  # Path to plugin module

    @property
    def full_id(self) -> str:
        return f"{self.id}@{self.version}"


# =============================================================================
# Hook Registry
# =============================================================================


class HookRegistry:
    """Registry for hook handlers.

    Thread-safe registry that manages hook subscriptions and execution.
    """

    def __init__(self):
        self._hooks: dict[str, list[Callable]] = {}
        self._lock = threading.RLock()

    def register(self, hook_name: str, handler: Callable, *, priority: int = 0) -> None:
        """Register a hook handler.

        Args:
            hook_name: Name of the hook (use Hooks constants)
            handler: Callable to invoke when hook fires
            priority: Higher priority handlers run first (default: 0)
        """
        with self._lock:
            if hook_name not in self._hooks:
                self._hooks[hook_name] = []

            # Check for duplicates
            if handler not in [h[0] for h in self._hooks[hook_name]]:
                self._hooks[hook_name].append((handler, priority))
                # Sort by priority (descending)
                self._hooks[hook_name].sort(key=lambda x: x[1], reverse=True)
                logger.debug(f"Registered hook: {hook_name} -> {handler.__name__} (priority={priority})")

    def unregister(self, hook_name: str, handler: Callable) -> None:
        """Unregister a hook handler."""
        with self._lock:
            if hook_name in self._hooks:
                self._hooks[hook_name] = [(h, p) for h, p in self._hooks[hook_name] if h != handler]
                logger.debug(f"Unregistered hook: {hook_name} -> {handler.__name__}")

    def execute(self, hook_name: str, *args, **kwargs) -> list[Any]:
        """Execute all handlers for a hook.

        Returns:
            List of results from each handler
        """
        with self._lock:
            handlers = [(h, p) for h, p in self._hooks.get(hook_name, [])]

        results = []
        for handler, priority in handlers:
            try:
                result = handler(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Error executing hook {hook_name}: {e}")

        return results

    def execute_first(self, hook_name: str, *args, default: Any = None, **kwargs) -> Any:
        """Execute hooks and return the first non-None result.

        Useful for hooks that may modify data (e.g., pre_* hooks).
        """
        results = self.execute(hook_name, *args, **kwargs)
        for result in results:
            if result is not None:
                return result
        return default

    def list_hooks(self) -> list[str]:
        """List all registered hooks (only those with handlers)."""
        with self._lock:
            return [k for k, v in self._hooks.items() if v]

    def get_handlers(self, hook_name: str) -> list[Callable]:
        """Get all handlers for a specific hook."""
        with self._lock:
            return [h for h, p in self._hooks.get(hook_name, [])]

    def clear(self) -> None:
        """Clear all hooks."""
        with self._lock:
            self._hooks.clear()


# =============================================================================
# Plugin Base Class
# =============================================================================


class Plugin(ABC):
    """
    Base class for AgentTeam plugins

    Example:
        class MyPlugin(Plugin):
            @property
            def id(self) -> str:
                return "my-plugin"

            @property
            def name(self) -> str:
                return "My Plugin"

            def register_hooks(self, registry: HookRegistry):
                registry.register(Hooks.PRE_AGENT_SPAWN, self.on_pre_spawn)
    """

    @property
    @abstractmethod
    def id(self) -> str:
        """Unique plugin identifier"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable plugin name"""
        pass

    @property
    def version(self) -> str:
        """Plugin version"""
        return "1.0.0"

    @property
    def description(self) -> str:
        """Plugin description"""
        return ""

    @property
    def author(self) -> str:
        """Plugin author"""
        return ""

    def get_hooks(self) -> list[str]:
        """List hooks this plugin provides"""
        return []

    def get_dependencies(self) -> list[str]:
        """List plugin dependencies"""
        return []

    def on_load(self) -> None:
        """Called when plugin is loaded"""
        logger.info(f"Plugin loaded: {self.id}")

    def on_unload(self) -> None:
        """Called when plugin is unloaded"""
        logger.info(f"Plugin unloaded: {self.id}")

    def register_hooks(self, registry: HookRegistry) -> None:
        """Register plugin hooks"""
        pass


# =============================================================================
# Plugin Manager (去单例化)
# =============================================================================


class PluginManager:
    """
    Plugin manager for AgentTeam.

    This class is designed to be instantiated directly (no singleton).
    For backward compatibility, use get_plugin_manager() to get a shared instance.

    Example:
        # Direct instantiation (recommended)
        manager = PluginManager()
        manager.discover_plugins("/path/to/plugins")
        manager.load_plugin("my-plugin")

        # Or with custom hook registry
        registry = HookRegistry()
        manager = PluginManager(hook_registry=registry)
    """

    # Class-level singleton instance (backward compatibility)
    _instance: Optional["PluginManager"] = None
    _instance_lock = threading.Lock()

    def __init__(self, hook_registry: Optional[HookRegistry] = None):
        """Initialize plugin manager.

        Args:
            hook_registry: Optional custom hook registry. If not provided,
                          a new HookRegistry is created.
        """
        # Initialize only once (even with __init__)
        if hasattr(self, "_initialized") and self._initialized:
            return

        self._plugins: dict[str, Plugin] = {}
        self._plugin_hooks: dict[str, list[tuple[str, Callable]]] = {}
        self._hook_registry = hook_registry or HookRegistry()
        self._lock = threading.RLock()
        self._discovered_paths: list[str] = []
        self._initialized = True

    @property
    def hooks(self) -> HookRegistry:
        """Get the hook registry"""
        return self._hook_registry

    def discover_plugins(self, plugin_dir: str) -> list[PluginMetadata]:
        """Discover plugins in a directory.

        Args:
            plugin_dir: Path to directory containing plugins

        Returns:
            List of discovered plugin metadata
        """
        discovered = []
        plugin_path = Path(plugin_dir)

        if not plugin_path.exists():
            logger.warning(f"Plugin directory does not exist: {plugin_dir}")
            return discovered

        for item in plugin_path.iterdir():
            if item.is_dir():
                init_file = item / "__init__.py"
                plugin_file = item / "plugin.py"

                if init_file.exists() or plugin_file.exists():
                    try:
                        module_name = f"agentteam_plugins.{item.name}"

                        if init_file.exists():
                            spec = importlib.util.spec_from_file_location(module_name, init_file)
                        else:
                            spec = importlib.util.spec_from_file_location(module_name, plugin_file)

                        if spec and spec.loader:
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)

                            for attr_name in dir(module):
                                attr = getattr(module, attr_name)
                                if isinstance(attr, type) and issubclass(attr, Plugin) and attr != Plugin:
                                    plugin = attr()
                                    discovered.append(
                                        PluginMetadata(
                                            id=plugin.id,
                                            name=plugin.name,
                                            version=plugin.version,
                                            description=plugin.description,
                                            author=plugin.author,
                                            hooks=plugin.get_hooks(),
                                            dependencies=plugin.get_dependencies(),
                                            entry_point=str(init_file if init_file.exists() else plugin_file),
                                        )
                                    )
                                    logger.info(f"Discovered plugin: {plugin.id}")
                    except Exception as e:
                        logger.error(f"Failed to load plugin from {item}: {e}")

        self._discovered_paths.append(plugin_dir)
        return discovered

    def _register_plugin_hooks(self, plugin: Plugin) -> None:
        """Helper to register hooks and track them"""
        hook_list = []

        original_register = self._hook_registry.register

        def tracked_register(hook_name: str, handler: Callable, **kwargs) -> None:
            original_register(hook_name, handler, **kwargs)
            hook_list.append((hook_name, handler))

        self._hook_registry.register = tracked_register
        try:
            plugin.register_hooks(self._hook_registry)
        finally:
            self._hook_registry.register = original_register

        self._plugin_hooks[plugin.id] = hook_list

    def _unregister_plugin_hooks(self, plugin_id: str) -> None:
        """Helper to unregister hooks for a plugin"""
        if plugin_id not in self._plugin_hooks:
            return

        for hook_name, handler in self._plugin_hooks[plugin_id]:
            self._hook_registry.unregister(hook_name, handler)

        del self._plugin_hooks[plugin_id]

    def load_plugin(self, plugin: Plugin) -> bool:
        """Load a plugin instance.

        Args:
            plugin: Plugin instance to load

        Returns:
            True if loaded successfully
        """
        with self._lock:
            if plugin.id in self._plugins:
                logger.warning(f"Plugin already loaded: {plugin.id}")
                return False

            # Check dependencies
            for dep in plugin.get_dependencies():
                if dep not in self._plugins:
                    logger.error(f"Plugin {plugin.id} requires {dep} which is not loaded")
                    return False

            # Register hooks
            self._register_plugin_hooks(plugin)

            # Store and call on_load
            self._plugins[plugin.id] = plugin
            plugin.on_load()

            logger.info(f"Loaded plugin: {plugin.id}")
            return True

    def unload_plugin(self, plugin_id: str) -> bool:
        """Unload a plugin.

        Args:
            plugin_id: Plugin ID to unload

        Returns:
            True if unloaded successfully
        """
        with self._lock:
            if plugin_id not in self._plugins:
                logger.warning(f"Plugin not loaded: {plugin_id}")
                return False

            plugin = self._plugins[plugin_id]

            # Unregister hooks
            self._unregister_plugin_hooks(plugin_id)

            # Call on_unload and remove
            plugin.on_unload()
            del self._plugins[plugin_id]

            logger.info(f"Unloaded plugin: {plugin_id}")
            return True

    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """Get a loaded plugin by ID."""
        with self._lock:
            return self._plugins.get(plugin_id)

    def list_plugins(self) -> list[str]:
        """List all loaded plugin IDs."""
        with self._lock:
            return list(self._plugins.keys())

    def list_all_metadata(self) -> list[PluginMetadata]:
        """Get metadata for all loaded plugins."""
        with self._lock:
            return [
                PluginMetadata(
                    id=p.id,
                    name=p.name,
                    version=p.version,
                    description=p.description,
                    author=p.author,
                    hooks=p.get_hooks(),
                    dependencies=p.get_dependencies(),
                )
                for p in self._plugins.values()
            ]

    def execute_hook(self, hook_name: str, *args, **kwargs) -> list[Any]:
        """Execute all handlers for a hook.

        Args:
            hook_name: Name of the hook
            *args: Positional arguments to pass to handlers
            **kwargs: Keyword arguments to pass to handlers

        Returns:
            List of results from handlers
        """
        return self._hook_registry.execute(hook_name, *args, **kwargs)

    def reset(self) -> None:
        """Reset the plugin manager (unload all plugins)."""
        with self._lock:
            plugin_ids = list(self._plugins.keys())
            for plugin_id in plugin_ids:
                self.unload_plugin(plugin_id)

            self._hook_registry.clear()
            logger.info("Plugin manager reset")


# =============================================================================
# Singleton Accessor (Backward Compatibility)
# =============================================================================


def get_plugin_manager() -> PluginManager:
    """Get the global PluginManager singleton instance.

    For new code, consider instantiating PluginManager directly.

    Returns:
        The global PluginManager instance
    """
    if PluginManager._instance is None:
        with PluginManager._instance_lock:
            if PluginManager._instance is None:
                PluginManager._instance = object.__new__(PluginManager)
                PluginManager._instance.__init__()
    return PluginManager._instance


def reset_plugin_manager() -> None:
    """Reset the global PluginManager singleton.

    Useful for testing.
    """
    with PluginManager._instance_lock:
        if PluginManager._instance is not None:
            PluginManager._instance.reset()
            PluginManager._instance = None


# =============================================================================
# Convenience Functions
# =============================================================================


def register_hook(hook_name: str, handler: Callable, **kwargs) -> None:
    """Register a hook handler with the global manager."""
    get_plugin_manager().hooks.register(hook_name, handler, **kwargs)


def execute_hook(hook_name: str, *args, **kwargs) -> list[Any]:
    """Execute a hook with the global manager."""
    return get_plugin_manager().execute_hook(hook_name, *args, **kwargs)


# =============================================================================
# Example Plugin
# =============================================================================


class ExamplePlugin(Plugin):
    """Example plugin demonstrating the plugin API"""

    @property
    def id(self) -> str:
        return "example-plugin"

    @property
    def name(self) -> str:
        return "Example Plugin"

    @property
    def description(self) -> str:
        return "An example plugin for demonstration"

    def get_hooks(self) -> list[str]:
        return [Hooks.PRE_AGENT_SPAWN, Hooks.POST_AGENT_SPAWN]

    def register_hooks(self, registry: HookRegistry):
        registry.register(Hooks.PRE_AGENT_SPAWN, self.on_pre_agent_spawn)
        registry.register(Hooks.POST_AGENT_SPAWN, self.on_post_agent_spawn)

    def on_pre_agent_spawn(self, team_name: str, config: dict) -> dict:
        """Called before an agent is spawned"""
        logger.info(f"ExamplePlugin: About to spawn agent in team {team_name}")
        return config

    def on_post_agent_spawn(self, team_name: str, agent_id: str) -> None:
        """Called after an agent is spawned"""
        logger.info(f"ExamplePlugin: Spawned agent {agent_id} in team {team_name}")


# =============================================================================
# Exports
# =============================================================================


__all__ = [
    # Classes
    "Plugin",
    "PluginMetadata",
    "PluginManager",
    "HookRegistry",
    # Enums
    "Hooks",
    # Functions
    "get_plugin_manager",
    "reset_plugin_manager",
    "register_hook",
    "execute_hook",
    # Example
    "ExamplePlugin",
]
