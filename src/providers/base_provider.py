"""
Base Provider Plugin

Provides the foundation for all LLM provider plugins.
Each provider (OpenAI, Anthropic, etc.) should inherit from this.
"""

import logging
from abc import abstractmethod
from typing import Any, Dict, List, Optional

from src.plugins.base import Plugin
from src.providers.base import LLMProvider
from src.providers.rate_limiter import TokenBucketRateLimiter as RateLimiter


class BaseProviderPlugin(LLMProvider, Plugin):
    """
    Base class for all LLM provider plugins.

    This combines the LLMProvider interface with the Plugin system,
    providing common functionality like rate limiting and logging.
    """

    def __init__(self):
        """Initialize base provider."""
        self.api_key: Optional[str] = None
        self.model: Optional[str] = None
        self.rate_limiter: Optional[RateLimiter] = None
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialized = False

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """The provider's name (e.g., 'openai', 'anthropic')."""
        pass

    @property
    def name(self) -> str:
        """Plugin name (for plugin system)."""
        return self.provider_name

    @property
    @abstractmethod
    def version(self) -> str:
        """Provider plugin version."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Provider description."""
        pass

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Default model for this provider."""
        pass

    @property
    @abstractmethod
    def supports_json(self) -> bool:
        """Whether this provider supports JSON mode."""
        pass

    @property
    @abstractmethod
    def max_tokens(self) -> int:
        """Maximum tokens supported by this provider."""
        pass

    @property
    def rate_limit(self) -> Optional[int]:
        """Requests per minute limit."""
        return 60  # Default, can be overridden

    def initialize(self, config: Dict[str, Any]):
        """
        Initialize the provider with configuration.

        Args:
            config: Configuration dictionary with api_key, model, etc.
        """
        import os

        # Get API key from config or environment
        self.api_key = config.get("api_key") or os.getenv(
            f"{self.provider_name.upper()}_API_KEY"
        )

        if not self.api_key:
            raise ValueError(
                f"No API key provided for {self.provider_name}. "
                f"Set {self.provider_name.upper()}_API_KEY environment variable."
            )

        # Get model from config or use default
        self.model = config.get("model") or os.getenv(
            f"{self.provider_name.upper()}_MODEL", self.default_model
        )

        # Initialize rate limiter if specified
        if self.rate_limit:
            # TokenBucketRateLimiter uses tokens_per_minute parameter
            self.rate_limiter = RateLimiter(
                tokens_per_minute=100000,  # Default token limit
                tokens_per_request=4000    # Estimated tokens per request
            )

        # Provider-specific initialization
        self._initialize_client()

        self._initialized = True
        self.logger.info(
            f"Initialized {self.provider_name} provider with model {self.model}"
        )

    @abstractmethod
    def _initialize_client(self):
        """Initialize the provider-specific client."""
        pass

    def execute(self, context: Dict[str, Any]) -> Any:
        """
        Execute plugin (complete a prompt).

        Args:
            context: Must contain 'messages' key

        Returns:
            Completion text
        """
        messages = context.get("messages", [])
        if not messages:
            raise ValueError("No messages provided")

        return self.complete(messages, **context)

    async def complete_async(
        self, messages: List[Dict[str, str]], **kwargs
    ) -> str:
        """
        Complete a prompt asynchronously.

        Args:
            messages: List of message dicts
            **kwargs: Additional parameters

        Returns:
            Completion text
        """
        if not self._initialized:
            raise RuntimeError(f"{self.provider_name} provider not initialized")

        # Apply rate limiting if configured
        if self.rate_limiter:
            await self.rate_limiter.acquire()

        # Call provider-specific implementation
        return await self._complete_impl(messages, **kwargs)

    @abstractmethod
    async def _complete_impl(
        self, messages: List[Dict[str, str]], **kwargs
    ) -> str:
        """
        Provider-specific completion implementation.

        Args:
            messages: List of message dicts
            **kwargs: Additional parameters

        Returns:
            Completion text
        """
        pass

    def complete(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Synchronous wrapper for completion.

        Args:
            messages: List of message dicts
            **kwargs: Additional parameters

        Returns:
            Completion text
        """
        import asyncio

        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.complete_async(messages, **kwargs))

    def shutdown(self):
        """Clean up provider resources."""
        self._initialized = False
        self.logger.info(f"Shut down {self.provider_name} provider")

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate provider configuration.

        Args:
            config: Configuration to validate

        Returns:
            True if configuration is valid
        """
        # Can be overridden for provider-specific validation
        return True