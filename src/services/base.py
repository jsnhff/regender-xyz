"""
Base Service Class

This module provides the foundation for all services in the application,
implementing common patterns for initialization, error handling, and
async/sync execution.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ServiceConfig:
    """Configuration for services."""

    # Core configuration that all services might use
    cache_enabled: bool = False
    async_enabled: bool = True
    max_retries: int = 3
    timeout: int = 300
    max_concurrent: int = 5

    # Quality control
    target_quality: float = 90.0
    max_qc_iterations: int = 3

    # Cache-specific configuration
    cache_max_size: int = 100
    cache_ttl: Optional[float] = None  # TTL in seconds, None for no expiration

    # Transform-specific configuration
    llm_temperature: float = 0.3
    chunk_size: int = 1000
    batch_size: int = 10
    rate_limit_tier: str = "tier-1"

    # Character service configuration (new)
    extraction: dict = field(default_factory=dict)
    grouping: dict = field(default_factory=dict)
    merging: dict = field(default_factory=dict)

    # Additional configuration data
    extra_config: dict = field(default_factory=dict)
    config: dict = field(default_factory=dict)  # For nested config

    def __post_init__(self):
        """Initialize config dicts and handle nested configuration."""
        if self.extra_config is None:
            self.extra_config = {}
        if self.config is None:
            self.config = {}

        # Merge any nested config into attributes
        if self.config:
            for key, value in self.config.items():
                if not hasattr(self, key) or getattr(self, key) == {}:
                    setattr(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value by key, supporting both attributes and extra_config."""
        # First check if it's a direct attribute
        if hasattr(self, key):
            return getattr(self, key)
        # Then check config dict
        if key in self.config:
            return self.config[key]
        # Then check extra_config
        elif self.extra_config:
            return self.extra_config.get(key, default)
        return default


class BaseService(ABC):
    """
    Base class for all services.

    This class provides:
    - Standard initialization pattern
    - Async/sync execution support
    - Error handling
    - Input validation
    - Logging
    """

    def __init__(self, config: Optional[ServiceConfig] = None):
        """
        Initialize the service.

        Args:
            config: Service configuration
        """
        self.config = config or ServiceConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialize()

    @abstractmethod
    def _initialize(self):
        """
        Initialize service resources.

        This method should set up any resources needed by the service,
        such as caches, connection pools, or validators.
        """
        pass

    @abstractmethod
    async def process(self, data: Any) -> Any:
        """
        Process data.

        This is the main processing method that all services must implement.

        Args:
            data: Input data to process

        Returns:
            Processed result
        """
        pass

    def validate_input(self, data: Any) -> bool:
        """
        Validate input data.

        Override this method to add service-specific validation.

        Args:
            data: Data to validate

        Returns:
            True if valid, False otherwise
        """
        return data is not None

    def handle_error(self, error: Exception, context: dict) -> None:
        """
        Centralized error handling.

        Args:
            error: The exception that occurred
            context: Context information about where the error occurred

        Raises:
            The original exception after logging
        """
        self.logger.error(
            f"Error in {self.__class__.__name__}: {error}", extra={"context": context}
        )
        raise

    async def _retry(
        self, func: callable, *args, max_retries: Optional[int] = None, **kwargs
    ) -> Any:
        """
        Retry a function with exponential backoff.

        Args:
            func: Function to retry
            args: Positional arguments for func
            max_retries: Maximum number of retries (uses config if not specified)
            kwargs: Keyword arguments for func

        Returns:
            Result from successful function call

        Raises:
            Last exception if all retries fail
        """
        max_retries = max_retries or self.config.max_retries
        last_error = None

        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff
                    self.logger.warning(
                        f"Retry {attempt + 1}/{max_retries} after error: {e}. "
                        f"Waiting {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(f"All {max_retries} retries failed")

        if last_error:
            raise last_error

    def get_metrics(self) -> dict[str, Any]:
        """
        Get service metrics.

        Override this to provide service-specific metrics.

        Returns:
            Dictionary of metrics
        """
        return {
            "service": self.__class__.__name__,
            "config": {
                "cache_enabled": self.config.cache_enabled,
                "async_enabled": self.config.async_enabled,
                "max_retries": self.config.max_retries,
                "timeout": self.config.timeout,
            },
        }

    def __repr__(self) -> str:
        """String representation of the service."""
        return f"{self.__class__.__name__}(config={self.config})"
