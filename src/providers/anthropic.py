# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Jason Huff
"""
Anthropic Provider Plugin

Implements Anthropic API support for Claude models.
"""

import asyncio
import json
from typing import Any

from src.providers.base_provider import (
    BaseProviderPlugin,
    ResponseIncompleteError,
    _token_count,
)


class AnthropicProvider(BaseProviderPlugin):
    """Anthropic provider plugin implementation."""

    # Maximum number of automatic retries on transient errors (529/429)
    # before giving up and re-raising. Prevents unbounded recursion when
    # the API is persistently overloaded or rate limited.
    MAX_RETRIES = 3

    # The longest one request may take, start to finish. Requests are streamed,
    # so this is a guard against a stalled connection, not a budget for a reply.
    REQUEST_TIMEOUT = 600.0

    # How far a reply cut off at its limit may be allowed to grow, once.
    MAX_GROWN_TOKENS = 32000

    # What the run has actually spent so far. Class-level defaults so a
    # provider built without going through initialize() still reads as zero
    # rather than raising on the first call.
    tokens_in = 0
    tokens_out = 0
    calls = 0

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
        return "claude-sonnet-5-5"

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

    async def _send(self, request_params: dict[str, Any]):
        """One request, streamed, returned as the finished message.

        Streamed because the reply is a rewritten chapter: a fixed wait on a
        whole response fails on length alone, and a model that reasons before
        it writes takes longer still. The outer limit is only there so a
        stalled connection cannot hang a run for ever.
        """

        async def run():
            async with self.client.messages.stream(**request_params) as stream:
                return await stream.get_final_message()

        return await asyncio.wait_for(run(), timeout=self.REQUEST_TIMEOUT)

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
        # Convert messages to Anthropic format
        # Anthropic expects a system message separately
        system_message = None
        claude_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                claude_messages.append({"role": msg["role"], "content": msg["content"]})

        model = kwargs.get("model", self.model)
        request_params = {
            "model": model,
            "messages": claude_messages,
            "max_tokens": kwargs.get("max_tokens", 4096),
        }
        # Models that turned a temperature down, so each is only asked once.
        no_temperature = self.__dict__.setdefault("_no_temperature", set())
        if model not in no_temperature:
            request_params["temperature"] = kwargs.get("temperature", 0.7)

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

        try:
            response = await self._send(request_params)
        except asyncio.TimeoutError as e:
            self.logger.error(
                f"Anthropic API call timed out after {self.REQUEST_TIMEOUT:.0f} seconds"
            )
            raise TimeoutError(
                "Anthropic API call timed out. The API may be slow or overloaded."
            ) from e
        except Exception as e:
            error_message = str(e)
            lowered = error_message.lower()
            status = getattr(e, "status_code", None)

            # Newer models take no sampling parameters and answer a request
            # that carries one with a 400. Which models do is not something to
            # keep a table of: the API says so, and the provider remembers.
            if (
                status == 400
                and "temperature" in lowered
                and "temperature" in request_params
                and model not in no_temperature
            ):
                no_temperature.add(model)
                self.logger.info(f"{model} takes no temperature; sending requests without it")
                return await self._complete_impl(messages, _attempt=_attempt, **kwargs)

            # "rate limit", not "rate": the bare word is inside "generate" and
            # "separate", and matching it made unrelated errors wait a minute,
            # three times, before failing anyway.
            is_overloaded = status == 529 or "529" in error_message or "overloaded" in lowered
            is_rate_limit = (
                status == 429
                or "429" in error_message
                or "rate limit" in lowered
                or "rate_limit" in lowered
            )

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
            if "credit" in lowered or "billing" in lowered:
                self.logger.error("Anthropic API credits/billing issue")
                raise ValueError("Anthropic API billing issue. Please check your account.") from e

            # Log and re-raise other errors
            self.logger.error(f"Anthropic API error: {e}")
            raise

        # What the call actually cost. The response already carries it and
        # nothing was reading it, so the only number the interface could
        # show was an estimate made before the run from a token guess.
        #
        # Counting must never be the reason a call fails, so anything that
        # is not a plain number is ignored rather than added.
        usage = getattr(response, "usage", None)
        if usage is not None:
            self.tokens_in += _token_count(getattr(usage, "input_tokens", 0))
            self.tokens_out += _token_count(getattr(usage, "output_tokens", 0))
            self.calls += 1

        stop_reason = getattr(response, "stop_reason", None)

        # A reply cut off at the limit is not a reply. Returned as one, half a
        # paragraph went into the book as the whole paragraph. A model that
        # reasons first spends part of the same allowance before it writes a
        # word, so the first answer is more room, once; after that it is an
        # error the caller can see and split the work on.
        if stop_reason == "max_tokens":
            asked = request_params["max_tokens"]
            if not kwargs.get("_grown") and asked < self.MAX_GROWN_TOKENS:
                grown = min(self.MAX_GROWN_TOKENS, asked * 2 + 2048)
                self.logger.warning(
                    f"Reply cut off at {asked} tokens; asking once more with room for {grown}"
                )
                return await self._complete_impl(
                    messages, **{**kwargs, "max_tokens": grown, "_grown": True}
                )
            raise ResponseIncompleteError(
                f"The model's reply was cut off at {asked} tokens and is incomplete."
            )

        if stop_reason == "refusal":
            raise ResponseIncompleteError("The model declined this request.")

        # The text, wherever it sits. The first block is reasoning on a model
        # that reasons, and reading it as the answer raised on every call.
        content = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )

        # If JSON was expected, validate it
        if kwargs.get("response_format") == "json_object":
            try:
                json.loads(content)
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
