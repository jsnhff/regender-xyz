"""
Plugin System Base Classes

This module provides the foundation for the plugin system,
allowing dynamic loading of providers and other extensions.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import importlib
import inspect
import logging
from pathlib import Path


class Plugin(ABC):
    """
    Base plugin interface.
    
    All plugins must implement this interface to be loaded
    and managed by the PluginManager.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Plugin name.
        
        This should be a unique identifier for the plugin.
        """
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version string."""
        pass
    
    @property
    def description(self) -> str:
        """Optional plugin description."""
        return ""
    
    @property
    def dependencies(self) -> List[str]:
        """List of required plugin dependencies."""
        return []
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]):
        """
        Initialize the plugin with configuration.
        
        Args:
            config: Plugin configuration dictionary
        """
        pass
    
    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Any:
        """
        Execute plugin functionality.
        
        Args:
            context: Execution context
            
        Returns:
            Plugin execution result
        """
        pass
    
    def shutdown(self):
        """
        Clean up plugin resources.
        
        Called when the plugin is being unloaded.
        """
        pass
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate plugin configuration.
        
        Args:
            config: Configuration to validate
            
        Returns:
            True if configuration is valid
        """
        return True
    
    def __repr__(self) -> str:
        """String representation of the plugin."""
        return f"{self.__class__.__name__}(name='{self.name}', version='{self.version}')"


class PluginManager:
    """
    Manages plugin loading, initialization, and execution.
    
    This manager:
    - Discovers and loads plugins
    - Manages plugin lifecycle
    - Resolves plugin dependencies
    - Provides plugin registry
    """
    
    def __init__(self):
        """Initialize the plugin manager."""
        self.plugins: Dict[str, Plugin] = {}
        self.plugin_paths: List[Path] = []
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def add_plugin_path(self, path: str):
        """
        Add a path to search for plugins.
        
        Args:
            path: Directory path containing plugins
        """
        plugin_path = Path(path)
        if plugin_path.exists() and plugin_path.is_dir():
            self.plugin_paths.append(plugin_path)
            self.logger.info(f"Added plugin path: {plugin_path}")
        else:
            self.logger.warning(f"Invalid plugin path: {plugin_path}")
    
    def load_plugin(self, module_path: str, config: Optional[Dict[str, Any]] = None):
        """
        Load a plugin from a module.
        
        Args:
            module_path: Python module path (e.g., 'src.providers.openai_provider')
            config: Optional configuration for the plugin
        """
        try:
            # Import the module
            module = importlib.import_module(module_path)
            
            # Find Plugin subclasses in the module
            plugin_classes = []
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, Plugin) and 
                    obj != Plugin):
                    plugin_classes.append(obj)
            
            if not plugin_classes:
                self.logger.warning(f"No plugin classes found in {module_path}")
                return
            
            # Load each plugin class
            for plugin_class in plugin_classes:
                try:
                    plugin = plugin_class()
                    
                    # Validate configuration
                    if config and not plugin.validate_config(config):
                        self.logger.error(
                            f"Invalid configuration for plugin {plugin.name}"
                        )
                        continue
                    
                    # Register the plugin
                    self.register(plugin, config)
                    
                except Exception as e:
                    self.logger.error(
                        f"Failed to instantiate plugin {plugin_class.__name__}: {e}"
                    )
                    
        except ImportError as e:
            self.logger.error(f"Failed to import module {module_path}: {e}")
    
    def register(self, plugin: Plugin, config: Optional[Dict[str, Any]] = None):
        """
        Register a plugin instance.
        
        Args:
            plugin: Plugin instance to register
            config: Optional configuration for the plugin
        """
        # Check dependencies
        for dep in plugin.dependencies:
            if dep not in self.plugins:
                self.logger.error(
                    f"Plugin {plugin.name} requires {dep} which is not loaded"
                )
                return
        
        # Initialize the plugin
        try:
            plugin.initialize(config or {})
            
            # Store the plugin
            self.plugins[plugin.name] = plugin
            self.logger.info(
                f"Registered plugin: {plugin.name} v{plugin.version}"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to initialize plugin {plugin.name}: {e}")
    
    def unregister(self, name: str):
        """
        Unregister and shutdown a plugin.
        
        Args:
            name: Plugin name to unregister
        """
        if name in self.plugins:
            plugin = self.plugins[name]
            try:
                plugin.shutdown()
            except Exception as e:
                self.logger.error(f"Error shutting down plugin {name}: {e}")
            
            del self.plugins[name]
            self.logger.info(f"Unregistered plugin: {name}")
    
    def get(self, name: str) -> Optional[Plugin]:
        """
        Get a plugin by name.
        
        Args:
            name: Plugin name
            
        Returns:
            Plugin instance or None if not found
        """
        return self.plugins.get(name)
    
    def execute(self, name: str, context: Dict[str, Any]) -> Any:
        """
        Execute a plugin by name.
        
        Args:
            name: Plugin name
            context: Execution context
            
        Returns:
            Plugin execution result
            
        Raises:
            ValueError: If plugin not found
        """
        plugin = self.get(name)
        if not plugin:
            raise ValueError(f"Plugin '{name}' not found")
        
        return plugin.execute(context)
    
    def discover_plugins(self):
        """
        Discover and load plugins from configured paths.
        
        This will search plugin paths for Python modules
        containing Plugin subclasses.
        """
        for plugin_path in self.plugin_paths:
            self.logger.info(f"Discovering plugins in {plugin_path}")
            
            # Find Python files in the directory
            for py_file in plugin_path.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue
                
                # Convert file path to module path
                module_name = py_file.stem
                
                # Try to load as plugin
                try:
                    # Add parent directory to Python path temporarily
                    import sys
                    sys.path.insert(0, str(plugin_path.parent))
                    
                    module_path = f"{plugin_path.name}.{module_name}"
                    self.load_plugin(module_path)
                    
                finally:
                    # Remove from path
                    sys.path.pop(0)
    
    def list_plugins(self) -> List[Dict[str, Any]]:
        """
        Get information about all loaded plugins.
        
        Returns:
            List of plugin information dictionaries
        """
        return [
            {
                'name': plugin.name,
                'version': plugin.version,
                'description': plugin.description,
                'dependencies': plugin.dependencies
            }
            for plugin in self.plugins.values()
        ]
    
    def shutdown_all(self):
        """Shutdown all plugins."""
        for name in list(self.plugins.keys()):
            self.unregister(name)
    
    def __repr__(self) -> str:
        """String representation of the plugin manager."""
        return f"PluginManager(plugins={len(self.plugins)})"


# Global plugin manager instance
_plugin_manager = None


def get_plugin_manager() -> PluginManager:
    """
    Get the global plugin manager instance.
    
    Returns:
        Global PluginManager instance
    """
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager