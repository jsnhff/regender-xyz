# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Jason Huff
"""
OpenAI Provider Plugin

Implements OpenAI API support including GPT-4, GPT-4o, and other models.
"""

import asyncio
import json
from typing import Any

from src.providers.base_provider import (
    BaseProviderPlugin,
    ResponseIncompleteError,
    _token_count,
)


class OpenAIProvider(BaseProviderPlugin):
    """OpenAI provider plugin implementation."""

    # Maximum number of automatic retries on transient errors (429)
    # before giving up and re-raising. Prevents unbounded recursion when
    # the API is persistently rate limited.
    MAX_RETRIES = 3

    # The longest one request may take. A chapter-sized reply from a model
    # that reasons first does not arrive inside a minute.
    REQUEST_TIMEOUT = 600.0

    # How far a reply cut off at its limit may be allowed to grow, once.
    MAX_GROWN_TOKENS = 32000

    # What the run has actually spent so far. Class-level defaults so a
    # provider built without going through initialize() still reads as zero.
    tokens_in = 0
    tokens_out = 0
    calls = 0

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
        except ImportError as e:
            raise ImportError("openai package not installed. Run: pip install openai") from e

    async def _complete_impl(
        self, messages: list[dict[str, str]], _attempt: int = 0, **kwargs
    ) -> str:
        """
        OpenAI-specific completion implementation.

        Args:
            messages: List of message dicts
            _attempt: Internal retry counter (do not set manually)
            **kwargs: Additional parameters like temperature, max_tokens

        Returns:
            Completion text
        """
        model = kwargs.get("model", self.model)
        # What each model has turned down, learned from its own 400s rather
        # than kept as a table: newer models take `max_completion_tokens` in
        # place of `max_tokens`, and no temperature but their own.
        quirks = self.__dict__.setdefault("_quirks", {}).setdefault(model, set())

        request_params = {"model": model, "messages": messages}
        if "no_temperature" not in quirks:
            request_params["temperature"] = kwargs.get("temperature", 0.7)
        if "max_tokens" in kwargs:
            limit = "max_completion_tokens" if "completion_tokens" in quirks else "max_tokens"
            request_params[limit] = kwargs["max_tokens"]

        # Handle JSON mode
        if kwargs.get("response_format") == "json_object":
            request_params["response_format"] = {"type": "json_object"}

        try:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(**request_params),
                timeout=self.REQUEST_TIMEOUT,
            )
        except asyncio.TimeoutError as e:
            self.logger.error(f"OpenAI API call timed out after {self.REQUEST_TIMEOUT:.0f} seconds")
            raise TimeoutError(
                "OpenAI API call timed out. The API may be slow or overloaded."
            ) from e
        except Exception as e:
            error_message = str(e)
            lowered = error_message.lower()
            status = getattr(e, "status_code", None)
            param = getattr(e, "param", None)

            # An account with no credit answers 429, the same status as a rate
            # limit. Checked second, it was never reached: each call waited a
            # minute, three times, for credit that was not coming, and the
            # transform then tried again paragraph by paragraph.
            if (
                "insufficient_quota" in lowered
                or "credit_balance" in lowered
                or "no credits remaining" in lowered
            ):
                self.logger.error("OpenAI account has no credits")
                raise ValueError(
                    "This OpenAI account has no credits. Add some at "
                    "https://platform.openai.com/settings/organization/billing "
                    "or choose another provider."
                ) from e

            if status == 400:
                if (
                    "max_tokens" in request_params
                    and (param == "max_tokens" or "max_completion_tokens" in lowered)
                    and "completion_tokens" not in quirks
                ):
                    quirks.add("completion_tokens")
                    self.logger.info(f"{model} takes max_completion_tokens; using it from here")
                    return await self._complete_impl(messages, _attempt=_attempt, **kwargs)
                if (
                    "temperature" in request_params
                    and (param == "temperature" or "temperature" in lowered)
                    and "no_temperature" not in quirks
                ):
                    quirks.add("no_temperature")
                    self.logger.info(f"{model} takes no temperature; sending requests without it")
                    return await self._complete_impl(messages, _attempt=_attempt, **kwargs)

            # Handle rate limiting specifically, with a bounded number of
            # retries to avoid unbounded recursion under persistent limits.
            if status == 429 or "rate_limit" in lowered or "429" in error_message:
                if _attempt >= self.MAX_RETRIES:
                    self.logger.error(
                        f"OpenAI API still rate limited after {self.MAX_RETRIES} "
                        f"retries, giving up: {e}"
                    )
                    raise

                self.logger.warning(f"Rate limit hit: {e}")
                # Extract retry-after if available
                wait_time = 60  # Default to 60 seconds
                if hasattr(e, "response") and e.response:
                    retry_after = e.response.headers.get("retry-after")
                    if retry_after:
                        wait_time = int(retry_after)

                self.logger.info(
                    f"Waiting {wait_time}s before retry ({_attempt + 1}/{self.MAX_RETRIES})..."
                )
                await asyncio.sleep(wait_time)
                return await self._complete_impl(messages, _attempt=_attempt + 1, **kwargs)

            # Log and re-raise other errors
            self.logger.error(f"OpenAI API error: {e}")
            raise

        # What the call actually cost, so the interface can report spend for
        # this provider as it does for Anthropic. Counting must never be the
        # reason a call fails.
        usage = getattr(response, "usage", None)
        if usage is not None:
            self.tokens_in += _token_count(getattr(usage, "prompt_tokens", 0))
            self.tokens_out += _token_count(getattr(usage, "completion_tokens", 0))
            self.calls += 1

        choice = response.choices[0]
        finish_reason = getattr(choice, "finish_reason", None)

        # A reply cut off at the limit is not a reply. A reasoning model spends
        # part of the same allowance before it writes, so it is asked once
        # more with room; after that the caller hears about it.
        if finish_reason == "length":
            asked = kwargs.get("max_tokens")
            if asked and not kwargs.get("_grown") and asked < self.MAX_GROWN_TOKENS:
                grown = min(self.MAX_GROWN_TOKENS, asked * 2 + 2048)
                self.logger.warning(
                    f"Reply cut off at {asked} tokens; asking once more with room for {grown}"
                )
                return await self._complete_impl(
                    messages, **{**kwargs, "max_tokens": grown, "_grown": True}
                )
            raise ResponseIncompleteError("The model's reply was cut off and is incomplete.")

        if finish_reason == "content_filter":
            raise ResponseIncompleteError("The model declined this request.")

        content = choice.message.content or ""
        # A refusal arrives as no content at all. Returned as an empty string,
        # it was taken for a paragraph the model had rewritten as nothing.
        if not content.strip():
            raise ResponseIncompleteError("The model returned no text.")

        # If JSON mode was requested, validate the response
        if kwargs.get("response_format") == "json_object":
            try:
                json.loads(content)  # Validate JSON
            except json.JSONDecodeError as e:
                self.logger.warning(f"Invalid JSON response: {e}")

        return content

    def get_model_info(self) -> dict[str, Any]:
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

    async def get_rate_limits(self) -> dict:
        """
        Get current rate limit status for OpenAI.

        Returns:
            Dictionary with rate limit info
        """
        # OpenAI doesn't provide a direct API for checking rate limits
        # Return estimated values based on tier
        return {
            "requests_remaining": "N/A",
            "requests_limit": self.rate_limit,
            "tokens_remaining": "N/A",
            "reset_time": "Rolling window",
            "note": "OpenAI uses rolling rate limits",
        }
