"""
Dependency Injection Container

This module provides a dependency injection container for managing
service instances and their dependencies.
"""

import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Type

from src.services.base import BaseService, ServiceConfig


class ServiceContainer:
    """
    Dependency injection container for managing services.

    This container:
    - Manages service lifecycle
    - Resolves dependencies automatically
    - Provides singleton instances
    - Supports lazy initialization
    """

    def __init__(self):
        """Initialize the service container."""
        self._services: Dict[str, BaseService] = {}
        self._factories: Dict[str, Callable] = {}
        self._configs: Dict[str, ServiceConfig] = {}
        self._dependencies: Dict[str, Dict[str, str]] = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    def register(
        self,
        name: str,
        service_class: Type[BaseService],
        config: Optional[Dict] = None,
        dependencies: Optional[Dict[str, str]] = None,
    ):
        """
        Register a service with the container.

        Args:
            name: Service identifier
            service_class: Service class to instantiate
            config: Configuration dictionary for the service
            dependencies: Map of parameter names to service names
        """
        # Store configuration
        if config:
            self._configs[name] = ServiceConfig(**config)
        else:
            self._configs[name] = ServiceConfig()

        # Store dependencies
        if dependencies:
            self._dependencies[name] = dependencies
        else:
            self._dependencies[name] = {}

        # Create factory function
        self._factories[name] = lambda: self._create_service(
            service_class, self._configs.get(name), self._dependencies.get(name, {})
        )

        self.logger.info(f"Registered service: {name} -> {service_class.__name__}")

    def _create_service(
        self,
        service_class: Type[BaseService],
        config: Optional[ServiceConfig],
        dependencies: Dict[str, str],
    ) -> BaseService:
        """
        Create a service instance with resolved dependencies.

        Args:
            service_class: Service class to instantiate
            config: Service configuration
            dependencies: Dependency mapping

        Returns:
            Instantiated service
        """
        # Resolve dependencies
        resolved_deps = {}
        for param_name, service_name in dependencies.items():
            resolved_deps[param_name] = self.get(service_name)

        # Create service instance
        try:
            service = service_class(config=config, **resolved_deps)
            self.logger.info(f"Created service instance: {service_class.__name__}")
            return service
        except Exception as e:
            self.logger.error(f"Failed to create service {service_class.__name__}: {e}")
            raise

    def get(self, name: str) -> BaseService:
        """
        Get or create a service instance.

        This provides singleton behavior - the same instance
        is returned for subsequent calls.

        Args:
            name: Service identifier

        Returns:
            Service instance

        Raises:
            ValueError: If service is not registered
        """
        # Return existing instance if available
        if name in self._services:
            return self._services[name]

        # Check if factory exists
        if name not in self._factories:
            raise ValueError(f"Service '{name}' not registered")

        # Create and cache instance
        self._services[name] = self._factories[name]()
        return self._services[name]

    def has(self, name: str) -> bool:
        """
        Check if a service is registered.

        Args:
            name: Service identifier

        Returns:
            True if service is registered
        """
        return name in self._factories

    def configure_from_file(self, config_path: str):
        """
        Load service configuration from a JSON file.

        Args:
            config_path: Path to configuration file
        """
        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path) as f:
            config = json.load(f)

        # Register services from config
        for service_name, service_config in config.get("services", {}).items():
            # Get service class
            class_path = service_config.get("class")
            if not class_path:
                self.logger.warning(f"No class specified for service: {service_name}")
                continue

            service_class = self._get_class(class_path)

            # Register service
            self.register(
                name=service_name,
                service_class=service_class,
                config=service_config.get("config"),
                dependencies=service_config.get("dependencies"),
            )

    def _get_class(self, class_path: str) -> Type:
        """
        Import and return a class from a module path.

        Args:
            class_path: Full module path to class (e.g., 'src.services.parser_service.ParserService')

        Returns:
            Class object
        """
        parts = class_path.split(".")
        module_path = ".".join(parts[:-1])
        class_name = parts[-1]

        try:
            import importlib

            module = importlib.import_module(module_path)
            return getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            self.logger.error(f"Failed to import class {class_path}: {e}")
            raise

    def clear(self):
        """Clear all registered services and instances."""
        self._services.clear()
        self._factories.clear()
        self._configs.clear()
        self._dependencies.clear()
        self.logger.info("Container cleared")

    def get_all_services(self) -> Dict[str, BaseService]:
        """
        Get all instantiated services.

        Returns:
            Dictionary of service name to instance
        """
        # Instantiate any services that haven't been created yet
        for name in self._factories:
            if name not in self._services:
                self.get(name)

        return self._services.copy()

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get container metrics.

        Returns:
            Container statistics and metrics
        """
        return {
            "registered_services": len(self._factories),
            "instantiated_services": len(self._services),
            "services": {name: service.get_metrics() for name, service in self._services.items()},
        }

    def __repr__(self) -> str:
        """String representation of the container."""
        return (
            f"ServiceContainer("
            f"registered={len(self._factories)}, "
            f"instantiated={len(self._services)})"
        )


# Global container instance
_container = None


def get_container() -> ServiceContainer:
    """
    Get the global service container instance.

    Returns:
        Global ServiceContainer instance
    """
    global _container
    if _container is None:
        _container = ServiceContainer()
    return _container


def configure_container(config_path: Optional[str] = None):
    """
    Configure the global container.

    Args:
        config_path: Optional path to configuration file
    """
    container = get_container()

    if config_path:
        container.configure_from_file(config_path)
    else:
        # Register default services
        from src.services.character_service import CharacterService
        from src.services.parser_service import ParserService
        from src.services.quality_service import QualityService
        from src.services.transform_service import TransformService

        container.register("parser", ParserService)
        container.register("character", CharacterService, dependencies={"provider": "llm_provider"})
        container.register(
            "transform",
            TransformService,
            dependencies={"provider": "llm_provider", "character_service": "character"},
        )
        container.register("quality", QualityService, dependencies={"provider": "llm_provider"})
