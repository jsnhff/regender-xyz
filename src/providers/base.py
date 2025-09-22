"""
Base Provider Classes

This module defines the base interface for LLM providers.
"""

from abc import ABC, abstractmethod
from typing import Optional


class LLMProvider(ABC):
    """
    Base class for LLM provider plugins.

    All LLM providers must implement this interface.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass

    @property
    @abstractmethod
    def supports_json(self) -> bool:
        """Whether provider supports JSON mode."""
        pass

    @property
    @abstractmethod
    def max_tokens(self) -> int:
        """Maximum token limit."""
        pass

    @property
    def rate_limit(self) -> Optional[int]:
        """Rate limit in requests per minute."""
        return None

    @abstractmethod
    async def complete(self, messages: list[dict[str, str]], **kwargs) -> str:
        """
        Complete a prompt (async by default).

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            **kwargs: Additional provider-specific parameters

        Returns:
            Completion text
        """
        pass

    def complete_sync(self, messages: list[dict[str, str]], **kwargs) -> str:
        """
        Synchronous wrapper for completion (use only when async is not possible).

        Args:
            messages: List of message dictionaries
            **kwargs: Additional parameters

        Returns:
            Completion text
        """
        import asyncio

        return asyncio.run(self.complete(messages, **kwargs))

    def validate_messages(self, messages: list[dict[str, str]]) -> bool:
        """
        Validate message format.

        Args:
            messages: Messages to validate

        Returns:
            True if valid
        """
        if not messages:
            return False

        for msg in messages:
            if not isinstance(msg, dict):
                return False
            if "role" not in msg or "content" not in msg:
                return False
            if msg["role"] not in ["system", "user", "assistant"]:
                return False

        return True

    @abstractmethod
    async def get_rate_limits(self) -> dict:
        """
        Get current rate limit status.

        Returns:
            Dictionary with rate limit info:
            - requests_remaining: Number of requests remaining
            - requests_limit: Total requests allowed
            - tokens_remaining: Tokens remaining (if applicable)
            - reset_time: When limits reset
        """
        pass

    @abstractmethod
    def get_model_info(self) -> dict:
        """
        Get information about the current model.

        Returns:
            Dictionary with model capabilities:
            - context_window: Maximum context size
            - max_output: Maximum output tokens
            - supports_vision: Whether it supports images
            - supports_json: Whether it supports JSON mode
            - cost_per_1k_input: Input token cost
            - cost_per_1k_output: Output token cost
        """
        pass

    def get_capabilities(self) -> dict:
        """
        Get provider capabilities.

        Returns:
            Dictionary of capabilities
        """
        return {
            "supports_json": self.supports_json,
            "max_tokens": self.max_tokens,
            "rate_limit": self.rate_limit,
            "model_info": self.get_model_info(),
        }
