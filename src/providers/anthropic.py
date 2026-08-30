"""
Anthropic Provider Plugin

Implements Anthropic API support for Claude models.
"""

import asyncio
import json
from typing import Any

from src.providers.base_provider import BaseProviderPlugin


class AnthropicProvider(BaseProviderPlugin):
    """Anthropic provider plugin implementation."""

    # Maximum number of automatic retries on transient errors (529/429)
    # before giving up and re-raising. Prevents unbounded recursion when
    # the API is persistently overloaded or rate limited.
    MAX_RETRIES = 3

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
        return "claude-opus-4-1-20250805"  # Claude Opus 4.1 (latest)

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
            from anthropic import AsyncAnthropic

            self.client = AsyncAnthropic(api_key=self.api_key)
            self.logger.debug("Anthropic async client initialized")
        except ImportError as e:
            raise ImportError("anthropic package not installed. Run: pip install anthropic") from e

    async def _complete_impl(
        self, messages: list[dict[str, str]], _attempt: int = 0, **kwargs
    ) -> str:
        """
        Anthropic-specific completion implementation.

        Args:
            messages: List of message dicts
            _attempt: Internal retry counter (do not set manually)
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
                    claude_messages.append({"role": msg["role"], "content": msg["content"]})

            # Prepare request parameters
            request_params = {
                "model": kwargs.get("model", self.model),
                "messages": claude_messages,
                "max_tokens": kwargs.get("max_tokens", 4096),
                "temperature": kwargs.get("temperature", 0.7),
            }

            # Add JSON instruction if JSON format is requested
            if kwargs.get("response_format") == "json_object":
                json_instruction = "\n\nIMPORTANT: You must respond with valid JSON only. Do not include any explanatory text, markdown formatting, or code blocks. Return only the raw JSON object or array."
                if system_message:
                    system_message += json_instruction
                else:
                    system_message = json_instruction

            # Add system message if present
            if system_message:
                request_params["system"] = system_message

            # Make the API call with await and timeout (60 seconds)
            response = await asyncio.wait_for(
                self.client.messages.create(**request_params), timeout=60.0
            )

            # Extract the response text
            content = response.content[0].text

            # If JSON was expected, validate it
            if kwargs.get("response_format") == "json_object":
                try:
                    json.loads(content)
                except json.JSONDecodeError as e:
                    self.logger.warning(f"Invalid JSON response: {e}")

            return content

        except asyncio.TimeoutError as e:
            self.logger.error("Anthropic API call timed out after 60 seconds")
            raise TimeoutError(
                "Anthropic API call timed out. The API may be slow or overloaded."
            ) from e
        except Exception as e:
            error_message = str(e)

            is_overloaded = "529" in error_message or "overloaded" in error_message.lower()
            is_rate_limit = "429" in error_message or "rate" in error_message.lower()

            # Retry transient errors (overloaded/rate limit) with a bounded
            # number of attempts to avoid unbounded recursion.
            if is_overloaded or is_rate_limit:
                if _attempt >= self.MAX_RETRIES:
                    self.logger.error(
                        f"Anthropic API still failing after {self.MAX_RETRIES} "
                        f"retries, giving up: {e}"
                    )
                    raise

                wait_time = 30 if is_overloaded else 60
                reason = "overloaded (529)" if is_overloaded else "rate limit (429)"
                self.logger.warning(
                    f"Anthropic API {reason}, waiting {wait_time}s "
                    f"(retry {_attempt + 1}/{self.MAX_RETRIES})..."
                )
                await asyncio.sleep(wait_time)
                return await self._complete_impl(messages, _attempt=_attempt + 1, **kwargs)

            # Check for insufficient credits
            if "credit" in error_message.lower() or "billing" in error_message.lower():
                self.logger.error("Anthropic API credits/billing issue")
                raise ValueError("Anthropic API billing issue. Please check your account.") from e

            # Log and re-raise other errors
            self.logger.error(f"Anthropic API error: {e}")
            raise

    def get_model_info(self) -> dict[str, Any]:
        """
        Get information about the current model.

        Returns:
            Dictionary with model capabilities
        """
        model_info = {
            "claude-opus-4-1-20250805": {  # Claude Opus 4.1 (Latest, August 2025)
                "context_window": 200000,
                "max_output": 8192,
                "supports_vision": True,
                "supports_json": True,
                "cost_per_1k_input": 0.015,
                "cost_per_1k_output": 0.075,
            },
            "claude-opus-4-20250514": {  # Claude Opus 4 (May 2025)
                "context_window": 200000,
                "max_output": 8192,
                "supports_vision": True,
                "supports_json": True,
                "cost_per_1k_input": 0.015,
                "cost_per_1k_output": 0.075,
            },
            "claude-sonnet-4-20250514": {  # Claude Sonnet 4 (May 2025)
                "context_window": 200000,
                "max_output": 8192,
                "supports_vision": True,
                "supports_json": True,
                "cost_per_1k_input": 0.003,
                "cost_per_1k_output": 0.015,
            },
            "claude-3-7-sonnet-20250219": {  # Claude Sonnet 3.7
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

    async def get_rate_limits(self) -> dict:
        """
        Get current rate limit status for Anthropic.

        Returns:
            Dictionary with rate limit info
        """
        # Anthropic doesn't provide a direct API for checking rate limits
        return {
            "requests_remaining": "N/A",
            "requests_limit": self.rate_limit,
            "tokens_remaining": "N/A",
            "reset_time": "Per minute",
            "note": "Anthropic uses per-minute rate limits",
        }
