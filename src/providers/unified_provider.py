"""
Unified Provider

This module provides a unified interface that wraps the 
UnifiedLLMClient from llm_client.py for plugin integration.
"""

import logging
import os
from typing import Any, Optional

from src.plugins.base import Plugin
from src.providers.base import LLMProvider


class UnifiedProvider(LLMProvider, Plugin):
    """
    Unified provider that wraps the existing UnifiedLLMClient.

    This provides backward compatibility with the existing codebase
    while conforming to the new plugin architecture.
    """

    def __init__(self):
        """Initialize unified provider."""
        self.client = None
        self.provider_name = None
        self.model = None
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    def name(self) -> str:
        """Provider/plugin name."""
        return "unified"

    @property
    def version(self) -> str:
        """Plugin version."""
        return "1.0.0"

    @property
    def description(self) -> str:
        """Plugin description."""
        return "Unified provider wrapping existing api_client"

    @property
    def supports_json(self) -> bool:
        """Check if current provider supports JSON."""
        if self.provider_name == "openai" or self.provider_name == "anthropic":
            return True
        return False

    @property
    def max_tokens(self) -> int:
        """Get max tokens for current provider."""
        # Use conservative default
        return 4096

    @property
    def rate_limit(self) -> Optional[int]:
        """Get rate limit for current provider."""
        return None

    def initialize(self, config: dict[str, Any]):
        """
        Initialize unified client.

        Args:
            config: Configuration with provider, model, etc.
        """
        # Import existing client
        try:
            from .llm_client import UnifiedLLMClient

            # Get provider from config or environment
            # Handle ${VAR} syntax if present in config
            provider_from_config = config.get("provider")
            if provider_from_config and provider_from_config.startswith("${"):
                # Extract env var name
                env_var = provider_from_config[2:-1]  # Remove ${ and }
                provider_from_config = os.getenv(env_var)

            self.provider_name = provider_from_config or os.getenv("DEFAULT_PROVIDER") or "openai"

            # Get model from config or environment
            model_from_config = config.get("model")
            if model_from_config and model_from_config.startswith("${"):
                # Extract env var name
                env_var = model_from_config[2:-1]  # Remove ${ and }
                model_from_config = os.getenv(env_var)

            # Fall back to provider-specific model env var
            if not model_from_config:
                if self.provider_name == "openai":
                    model_from_config = os.getenv("OPENAI_MODEL", "gpt-4o")
                elif self.provider_name == "anthropic":
                    model_from_config = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-20250514")

            self.model = model_from_config

            # Create client
            self.client = UnifiedLLMClient(provider=self.provider_name)

            self.logger.info(f"Initialized unified provider with {self.provider_name}")

        except ImportError as e:
            self.logger.error(f"Failed to import UnifiedLLMClient: {e}")
            raise

    def execute(self, context: dict[str, Any]) -> Any:
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

    async def complete_async(self, messages: list[dict[str, str]], **kwargs) -> str:
        """
        Complete a prompt asynchronously.

        Args:
            messages: List of message dicts
            **kwargs: Additional parameters

        Returns:
            Completion text
        """
        if not self.client:
            raise RuntimeError("Unified client not initialized")

        # Use the existing client's complete method
        import asyncio

        loop = asyncio.get_event_loop()

        def sync_complete():
            response = self.client.complete(
                messages=messages,
                model=kwargs.get("model", self.model),
                temperature=kwargs.get("temperature", 0.7),
                response_format=kwargs.get("response_format"),
            )

            # Extract content from response
            if hasattr(response, "content"):
                return response.content
            elif isinstance(response, dict):
                return response.get("content", str(response))
            else:
                return str(response)

        return await loop.run_in_executor(None, sync_complete)

    def validate_config(self, config: dict[str, Any]) -> bool:
        """
        Validate provider configuration.

        Args:
            config: Configuration to validate

        Returns:
            True if valid
        """
        # Check that at least one API key is available
        has_key = (
            os.getenv("OPENAI_API_KEY")
            or os.getenv("ANTHROPIC_API_KEY")
        )

        if not has_key:
            self.logger.error("No API keys found in environment")
            return False

        return True

    def shutdown(self):
        """Clean up resources."""
        self.client = None
        self.logger.info("Unified provider shutdown")
