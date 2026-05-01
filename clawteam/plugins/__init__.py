"""
Plugin system for ClawTeam

Provides a plugin architecture for extending ClawTeam functionality.
"""
import importlib.util
import os
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from clawteam.utils.logger import get_logger

logger = get_logger(__name__)


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
    
    @property
    def full_id(self) -> str:
        return f"{self.id}@{self.version}"


class HookRegistry:
    """Registry for hook handlers"""
    
    def __init__(self):
        self._hooks: dict[str, list[Callable]] = {}
        self._lock = threading.Lock()
    
    def register(self, hook_name: str, handler: Callable) -> None:
        """Register a hook handler"""
        with self._lock:
            if hook_name not in self._hooks:
                self._hooks[hook_name] = []
            # Avoid duplicate registration
            if handler not in self._hooks[hook_name]:
                self._hooks[hook_name].append(handler)
                logger.info(f"Registered hook: {hook_name} -> {handler.__name__}")
    
    def unregister(self, hook_name: str, handler: Callable) -> None:
        """Unregister a hook handler"""
        with self._lock:
            if hook_name in self._hooks:
                try:
                    self._hooks[hook_name].remove(handler)
                    logger.info(f"Unregistered hook: {hook_name} -> {handler.__name__}")
                except ValueError:
                    pass
    
    def execute(self, hook_name: str, *args, **kwargs) -> list[Any]:
        """Execute all handlers for a hook"""
        with self._lock:
            handlers = list(self._hooks.get(hook_name, []))
        
        results = []
        for handler in handlers:
            try:
                result = handler(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Error executing hook {hook_name}: {e}")
        
        return results
    
    def list_hooks(self) -> list[str]:
        """List all registered hooks (only those with handlers)"""
        with self._lock:
            return [k for k, v in self._hooks.items() if v]
    
    def clear(self) -> None:
        """Clear all hooks"""
        with self._lock:
            self._hooks.clear()


class Plugin(ABC):
    """
    Base class for ClawTeam plugins
    
    Example:
        class MyPlugin(Plugin):
            @property
            def id(self) -> str:
                return "my-plugin"
            
            @property
            def name(self) -> str:
                return "My Plugin"
            
            def register_hooks(self, registry: HookRegistry):
                registry.register("pre_agent_spawn", self.on_pre_spawn)
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


class PluginManager:
    """
    Central plugin manager for ClawTeam
    
    Manages plugin discovery, loading, and hook execution.
    """
    
    _instance: Optional["PluginManager"] = None
    
    def __new__(cls) -> "PluginManager":
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self._plugins: dict[str, Plugin] = {}
        self._plugin_hooks: dict[str, list[tuple[str, Callable]]] = {}  # plugin_id -> [(hook_name, handler)]
        self._hook_registry = HookRegistry()
        self._lock = threading.Lock()
        self._discovered_paths: list[str] = []
    
    @property
    def hooks(self) -> HookRegistry:
        """Get the hook registry"""
        return self._hook_registry
    
    def discover_plugins(self, plugin_dir: str) -> list[PluginMetadata]:
        """Discover plugins in a directory"""
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
                        module_name = f"clawteam_plugins.{item.name}"
                        
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
                                    discovered.append(PluginMetadata(
                                        id=plugin.id,
                                        name=plugin.name,
                                        version=plugin.version,
                                        description=plugin.description,
                                        author=plugin.author,
                                        hooks=plugin.get_hooks(),
                                        dependencies=plugin.get_dependencies(),
                                    ))
                                    logger.info(f"Discovered plugin: {plugin.id}")
                    except Exception as e:
                        logger.error(f"Failed to load plugin from {item}: {e}")
        
        self._discovered_paths.append(plugin_dir)
        return discovered
    
    def _register_plugin_hooks(self, plugin: Plugin) -> None:
        """Helper to register hooks and track them"""
        hook_list = []
        
        # Create a wrapper that tracks registration
        original_register = self._hook_registry.register
        
        def tracked_register(hook_name: str, handler: Callable) -> None:
            original_register(hook_name, handler)
            hook_list.append((hook_name, handler))
        
        # Temporarily replace register method
        self._hook_registry.register = tracked_register
        
        try:
            plugin.register_hooks(self._hook_registry)
        finally:
            self._hook_registry.register = original_register
        
        # Store tracked hooks
        self._plugin_hooks[plugin.id] = hook_list
    
    def _unregister_plugin_hooks(self, plugin_id: str) -> None:
        """Unregister all hooks for a plugin"""
        if plugin_id in self._plugin_hooks:
            for hook_name, handler in self._plugin_hooks[plugin_id]:
                self._hook_registry.unregister(hook_name, handler)
            del self._plugin_hooks[plugin_id]
    
    def load_plugin(self, plugin: Plugin) -> bool:
        """Load a plugin"""
        with self._lock:
            if plugin.id in self._plugins:
                logger.warning(f"Plugin already loaded: {plugin.id}")
                return False
            
            # Check dependencies
            for dep_id in plugin.get_dependencies():
                if dep_id not in self._plugins:
                    logger.error(f"Plugin {plugin.id} missing dependency: {dep_id}")
                    return False
            
            try:
                plugin.on_load()
                self._register_plugin_hooks(plugin)
                self._plugins[plugin.id] = plugin
                logger.info(f"Loaded plugin: {plugin.id}")
                return True
            except Exception as e:
                logger.error(f"Failed to load plugin {plugin.id}: {e}")
                return False
    
    def unload_plugin(self, plugin_id: str) -> bool:
        """Unload a plugin"""
        with self._lock:
            if plugin_id not in self._plugins:
                logger.warning(f"Plugin not loaded: {plugin_id}")
                return False
            
            plugin = self._plugins[plugin_id]
            
            try:
                # Unregister hooks first
                self._unregister_plugin_hooks(plugin_id)
                
                plugin.on_unload()
                del self._plugins[plugin_id]
                logger.info(f"Unloaded plugin: {plugin_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to unload plugin {plugin_id}: {e}")
                return False
    
    def load_all(self) -> int:
        """Load all discovered plugins"""
        count = 0
        for path in self._discovered_paths:
            discovered = self.discover_plugins(path)
            for meta in discovered:
                count += 1
        
        for plugin in list(self._plugins.values()):
            count += 1
        
        return count
    
    def get_loaded_plugins(self) -> list[Plugin]:
        """Get all loaded plugins"""
        with self._lock:
            return list(self._plugins.values())
    
    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """Get a plugin by ID"""
        with self._lock:
            return self._plugins.get(plugin_id)
    
    def execute_hook(self, hook_name: str, *args, **kwargs) -> list[Any]:
        """Execute a hook and return results from all handlers"""
        return self._hook_registry.execute(hook_name, *args, **kwargs)
    
    def list_hooks(self) -> list[str]:
        """List all available hooks"""
        return self._hook_registry.list_hooks()


# Global plugin manager instance
_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """Get the global plugin manager instance"""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager


# Built-in hooks
class Hooks:
    """Standard ClawTeam hooks"""
    
    # Agent lifecycle
    PRE_AGENT_SPAWN = "pre_agent_spawn"
    POST_AGENT_SPAWN = "post_agent_spawn"
    PRE_AGENT_TERMINATE = "pre_agent_terminate"
    POST_AGENT_TERMINATE = "post_agent_terminate"
    
    # Task lifecycle
    PRE_TASK_CREATE = "pre_task_create"
    POST_TASK_CREATE = "post_task_create"
    PRE_TASK_COMPLETE = "pre_task_complete"
    POST_TASK_COMPLETE = "post_task_complete"
    
    # Team lifecycle
    PRE_TEAM_CREATE = "pre_team_create"
    POST_TEAM_CREATE = "post_team_create"
    PRE_TEAM_DELETE = "pre_team_delete"
    POST_TEAM_DELETE = "post_team_delete"
    
    # Session lifecycle
    PRE_SESSION_START = "pre_session_start"
    POST_SESSION_START = "post_session_start"
    PRE_SESSION_END = "pre_session_end"
    POST_SESSION_END = "post_session_end"
    
    # Error handling
    ON_ERROR = "on_error"
    
    # Metrics
    ON_METRICS_COLLECT = "on_metrics_collect"


# Convenience functions
def register_hook(hook_name: str, handler: Callable) -> None:
    """Register a hook handler"""
    get_plugin_manager().hooks.register(hook_name, handler)


def execute_hook(hook_name: str, *args, **kwargs) -> list[Any]:
    """Execute a hook"""
    return get_plugin_manager().execute_hook(hook_name, *args, **kwargs)


# Example plugin
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
        return [
            Hooks.PRE_AGENT_SPAWN,
            Hooks.POST_AGENT_SPAWN,
        ]
    
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


__all__ = [
    "Plugin",
    "PluginMetadata",
    "PluginManager",
    "HookRegistry",
    "Hooks",
    "get_plugin_manager",
    "register_hook",
    "execute_hook",
    "ExamplePlugin",
]
