"""
OpenAI Provider Plugin

Implements OpenAI API support including GPT-4, GPT-4o, and other models.
"""

import asyncio
import json
from typing import Any, Dict, List

from src.providers.base_provider import BaseProviderPlugin


class OpenAIProvider(BaseProviderPlugin):
    """OpenAI provider plugin implementation."""

    @property
    def provider_name(self) -> str:
        """Provider name."""
        return "openai"

    @property
    def version(self) -> str:
        """Plugin version."""
        return "1.0.0"

    @property
    def description(self) -> str:
        """Provider description."""
        return "OpenAI API provider for GPT models"

    @property
    def default_model(self) -> str:
        """Default model."""
        return "gpt-4o-mini"

    @property
    def supports_json(self) -> bool:
        """OpenAI supports JSON mode."""
        return True

    @property
    def max_tokens(self) -> int:
        """Max tokens for OpenAI models."""
        # GPT-4o supports 128k context
        return 128000

    @property
    def rate_limit(self) -> int:
        """OpenAI rate limit (requests per minute)."""
        return 500  # Tier 2 default

    def _initialize_client(self):
        """Initialize OpenAI client."""
        try:
            from openai import AsyncOpenAI

            self.client = AsyncOpenAI(api_key=self.api_key)
            self.logger.debug("OpenAI async client initialized")
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

    async def _complete_impl(
        self, messages: List[Dict[str, str]], **kwargs
    ) -> str:
        """
        OpenAI-specific completion implementation.

        Args:
            messages: List of message dicts
            **kwargs: Additional parameters like temperature, max_tokens

        Returns:
            Completion text
        """
        try:
            # Prepare request parameters
            request_params = {
                "model": kwargs.get("model", self.model),
                "messages": messages,
                "temperature": kwargs.get("temperature", 0.7),
            }

            # Add optional parameters
            if "max_tokens" in kwargs:
                request_params["max_tokens"] = kwargs["max_tokens"]

            # Handle JSON mode
            if kwargs.get("response_format") == "json_object":
                request_params["response_format"] = {"type": "json_object"}

            # Make the API call with await and timeout (60 seconds)
            response = await asyncio.wait_for(
                self.client.chat.completions.create(**request_params),
                timeout=60.0
            )

            # Extract the response text
            content = response.choices[0].message.content

            # If JSON mode was requested, validate the response
            if kwargs.get("response_format") == "json_object":
                try:
                    json.loads(content)  # Validate JSON
                except json.JSONDecodeError as e:
                    self.logger.warning(f"Invalid JSON response: {e}")

            return content

        except asyncio.TimeoutError:
            self.logger.error("OpenAI API call timed out after 60 seconds")
            raise TimeoutError("OpenAI API call timed out. The API may be slow or overloaded.")
        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            raise

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.

        Returns:
            Dictionary with model capabilities
        """
        model_info = {
            "gpt-4o-mini": {
                "context_window": 128000,
                "max_output": 4096,
                "supports_vision": True,
                "supports_json": True,
                "cost_per_1k_input": 0.00015,
                "cost_per_1k_output": 0.0006,
            },
            "gpt-4o": {
                "context_window": 128000,
                "max_output": 4096,
                "supports_vision": True,
                "supports_json": True,
                "cost_per_1k_input": 0.005,
                "cost_per_1k_output": 0.015,
            },
            "gpt-4-turbo": {
                "context_window": 128000,
                "max_output": 4096,
                "supports_vision": True,
                "supports_json": True,
                "cost_per_1k_input": 0.01,
                "cost_per_1k_output": 0.03,
            },
            "gpt-3.5-turbo": {
                "context_window": 16385,
                "max_output": 4096,
                "supports_vision": False,
                "supports_json": True,
                "cost_per_1k_input": 0.0005,
                "cost_per_1k_output": 0.0015,
            },
        }

        return model_info.get(
            self.model,
            {
                "context_window": 128000,
                "max_output": 4096,
                "supports_vision": False,
                "supports_json": True,
            },
        )