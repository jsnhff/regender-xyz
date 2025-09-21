"""
Anthropic Provider Plugin

Implements Anthropic API support for Claude models.
"""

import json
from typing import Any

from src.providers.base_provider import BaseProviderPlugin


class AnthropicProvider(BaseProviderPlugin):
    """Anthropic provider plugin implementation."""

    @property
    def provider_name(self) -> str:
        """Provider name."""
        return "anthropic"

    @property
    def version(self) -> str:
        """Plugin version."""
        return "1.0.0"

    @property
    def description(self) -> str:
        """Provider description."""
        return "Anthropic API provider for Claude models"

    @property
    def default_model(self) -> str:
        """Default model."""
        return "claude-opus-4-20250514"  # Claude Opus 4.1

    @property
    def supports_json(self) -> bool:
        """Claude supports structured output."""
        return True

    @property
    def max_tokens(self) -> int:
        """Max tokens for Claude models."""
        return 200000  # Claude 3 supports 200k context

    @property
    def rate_limit(self) -> int:
        """Anthropic rate limit (requests per minute)."""
        return 4000  # Opus 4 tier: 4,000 requests/min

    def _initialize_client(self):
        """Initialize Anthropic client."""
        try:
            from anthropic import Anthropic

            self.client = Anthropic(api_key=self.api_key)
            self.logger.debug("Anthropic client initialized")
        except ImportError as e:
            raise ImportError(
                "anthropic package not installed. Run: pip install anthropic"
            ) from e

    async def _complete_impl(
        self, messages: list[dict[str, str]], **kwargs
    ) -> str:
        """
        Anthropic-specific completion implementation.

        Args:
            messages: List of message dicts
            **kwargs: Additional parameters

        Returns:
            Completion text
        """
        try:
            # Convert messages to Anthropic format
            # Anthropic expects a system message separately
            system_message = None
            claude_messages = []

            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    claude_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })

            # Prepare request parameters
            request_params = {
                "model": kwargs.get("model", self.model),
                "messages": claude_messages,
                "max_tokens": kwargs.get("max_tokens", 4096),
                "temperature": kwargs.get("temperature", 0.7),
            }

            # Add system message if present
            if system_message:
                request_params["system"] = system_message

            # Make the API call
            response = self.client.messages.create(**request_params)

            # Extract the response text
            content = response.content[0].text

            # If JSON was expected, validate it
            if kwargs.get("response_format") == "json_object":
                try:
                    json.loads(content)
                except json.JSONDecodeError as e:
                    self.logger.warning(f"Invalid JSON response: {e}")

            return content

        except Exception as e:
            self.logger.error(f"Anthropic API error: {e}")
            raise

    def get_model_info(self) -> dict[str, Any]:
        """
        Get information about the current model.

        Returns:
            Dictionary with model capabilities
        """
        model_info = {
            "claude-opus-4-20250514": {  # Claude Opus 4.1 (Latest Opus)
                "context_window": 200000,
                "max_output": 8192,
                "supports_vision": True,
                "supports_json": True,
                "cost_per_1k_input": 0.015,
                "cost_per_1k_output": 0.075,
            },
            "claude-sonnet-4-20250514": {  # Claude Sonnet 4 (if available)
                "context_window": 200000,
                "max_output": 8192,
                "supports_vision": True,
                "supports_json": True,
                "cost_per_1k_input": 0.003,
                "cost_per_1k_output": 0.015,
            },
            # Keeping Claude 3.5 Sonnet as fallback since it's newer than 3.0
            "claude-3-5-sonnet-20241022": {  # Claude 3.5 Sonnet (Latest pre-v4)
                "context_window": 200000,
                "max_output": 8192,
                "supports_vision": True,
                "supports_json": True,
                "cost_per_1k_input": 0.003,
                "cost_per_1k_output": 0.015,
            },
        }

        # Handle case where self.model might be None
        model_name = self.model or self.default_model
        return model_info.get(
            model_name,
            {
                "context_window": 200000,
                "max_output": 4096,
                "supports_vision": True,
                "supports_json": True,
            },
        )
