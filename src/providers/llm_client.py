#!/usr/bin/env python3
"""
Unified LLM client for multiple providers (OpenAI and Anthropic/Claude).

This module provides a consistent interface for interacting with different
LLM APIs while maintaining security and flexibility.
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

# Manual .env loading since dotenv might not be available
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    try:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    # Only set if not already in environment
                    if key not in os.environ:
                        os.environ[key] = value.strip()
    except Exception:
        # Silently ignore .env loading errors
        pass

# Import providers
from openai import OpenAI, OpenAIError

# Try to import Anthropic client
try:
    from anthropic import Anthropic, AnthropicError

    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False
    AnthropicError = Exception  # Fallback



# Define APIError exception
class APIError(Exception):
    """Base exception for API-related errors."""
    pass


@dataclass
class _APIResponse:
    """Standardized API response across providers."""

    content: str
    model: str
    usage: Optional[dict[str, int]] = None
    raw_response: Optional[Any] = None


class _BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the client is properly configured."""
        pass

    @abstractmethod
    def get_default_model(self) -> str:
        """Get the default model for this provider."""
        pass

    @abstractmethod
    def complete(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.0,
        response_format: Optional[dict] = None,
    ) -> _APIResponse:
        """Send a completion request to the LLM."""
        pass


class _OpenAIClient(_BaseLLMClient):
    """OpenAI API client implementation."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.base_url = base_url or os.environ.get("OPENAI_API_BASE")

        if self.api_key:
            kwargs = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self.client = OpenAI(**kwargs)
        else:
            self.client = None

    def is_available(self) -> bool:
        """Check if OpenAI client is available."""
        return self.client is not None

    def get_default_model(self) -> str:
        """Get default OpenAI model from environment or fallback."""
        return os.environ.get("OPENAI_MODEL", "gpt-4o")

    def complete(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.0,
        response_format: Optional[dict] = None,
    ) -> _APIResponse:
        """Complete using OpenAI API."""
        if not self.client:
            raise APIError("OpenAI client not initialized. Set OPENAI_API_KEY.")

        try:
            kwargs = {
                "model": model or self.get_default_model(),
                "messages": messages,
                "temperature": temperature,
            }

            if response_format:
                kwargs["response_format"] = response_format

            response = self.client.chat.completions.create(**kwargs)

            return _APIResponse(
                content=response.choices[0].message.content,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
                if response.usage
                else None,
                raw_response=response,
            )

        except OpenAIError as e:
            raise APIError(f"OpenAI API error: {e}")
        except Exception as e:
            raise APIError(f"Unexpected error calling OpenAI: {e}")


class _AnthropicClient(_BaseLLMClient):
    """Anthropic/Claude API client implementation."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.base_url = base_url or os.environ.get("ANTHROPIC_API_BASE")

        if self.api_key and _ANTHROPIC_AVAILABLE:
            kwargs = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self.client = Anthropic(**kwargs)
        else:
            self.client = None

    def is_available(self) -> bool:
        """Check if Anthropic client is available."""
        return self.client is not None and _ANTHROPIC_AVAILABLE

    def get_default_model(self) -> str:
        """Get default Anthropic model from environment or fallback."""
        return os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-20250514")

    def complete(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.0,
        response_format: Optional[dict] = None,
    ) -> _APIResponse:
        """Complete using Anthropic API."""
        if not self.client:
            raise APIError(
                "Anthropic client not initialized. Set ANTHROPIC_API_KEY and install anthropic."
            )

        try:
            # Convert OpenAI-style messages to Anthropic format
            # Extract system message if present
            system_message = None
            anthropic_messages = []

            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    anthropic_messages.append({"role": msg["role"], "content": msg["content"]})

            # Build request
            kwargs = {
                "model": model or self.get_default_model(),
                "messages": anthropic_messages,
                "temperature": temperature,
                "max_tokens": 4096,  # Claude requires this
            }

            if system_message:
                kwargs["system"] = system_message

            # Handle JSON response format
            if response_format and response_format.get("type") == "json_object":
                # Add instruction to return JSON
                if anthropic_messages and anthropic_messages[-1]["role"] == "user":
                    anthropic_messages[-1]["content"] += "\n\nRespond with valid JSON only."

            response = self.client.messages.create(**kwargs)

            # Extract content from Claude's response
            content = ""
            if hasattr(response.content, "__iter__"):
                # Handle multiple content blocks
                for block in response.content:
                    if hasattr(block, "text"):
                        content += block.text
            else:
                content = response.content

            return _APIResponse(
                content=content,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                }
                if hasattr(response, "usage")
                else None,
                raw_response=response,
            )

        except AnthropicError as e:
            raise APIError(f"Anthropic API error: {e}")
        except Exception as e:
            raise APIError(f"Unexpected error calling Anthropic: {e}")


class UnifiedLLMClient:
    """
    Unified client that can use multiple LLM providers.

    Priority order:
    1. Explicitly specified provider
    2. Environment variable DEFAULT_PROVIDER
    3. First available provider (OpenAI, then Anthropic)
    """

    def __init__(self, provider: Optional[str] = None):
        self.providers: dict[str, _BaseLLMClient] = {
            "openai": _OpenAIClient(),
            "anthropic": _AnthropicClient(),
            "claude": _AnthropicClient(),  # Alias for anthropic
        }

        # Handle provider aliases
        if provider == "claude":
            provider = "anthropic"

        # Determine which provider to use
        self.provider: str = (
            provider or os.environ.get("DEFAULT_PROVIDER") or os.environ.get("LLM_PROVIDER") or ""
        )

        if not self.provider:
            # Auto-detect first available provider
            for name, client in self.providers.items():
                if name != "claude" and client.is_available():  # Skip alias
                    self.provider = name
                    break

        if not self.provider:
            available = self.list_available_providers()
            if available:
                raise APIError(
                    f"No default provider set. Available providers: {', '.join(available)}. "
                    f"Set DEFAULT_PROVIDER in .env or specify provider explicitly."
                )
            else:
                raise APIError(
                    "No LLM provider available. Set one of: OPENAI_API_KEY or ANTHROPIC_API_KEY "
                    "in your .env file."
                )

        if self.provider not in self.providers:
            raise APIError(f"Unknown provider: {self.provider}")
        
        # Type assertion - provider is guaranteed to be non-None here
        assert self.provider is not None

        self.client = self.providers[self.provider]
        if not self.client.is_available():
            # Check which providers are available
            available = self.list_available_providers()

            error_msg = f"Provider {self.provider} is not properly configured.\n\n"
            error_msg += "To fix this:\n"

            if self.provider == "openai":
                error_msg += "1. Copy .env.example to .env\n"
                error_msg += "2. Add your OpenAI API key: OPENAI_API_KEY=your-key-here\n"
                error_msg += "3. Get a key from: https://platform.openai.com/api-keys\n"
            elif self.provider == "anthropic":
                error_msg += "1. Copy .env.example to .env\n"
                error_msg += "2. Add your Anthropic API key: ANTHROPIC_API_KEY=your-key-here\n"
                error_msg += "3. Get a key from: https://console.anthropic.com/settings/keys\n"

            if available:
                error_msg += f"\nAlternatively, use one of these configured providers: {', '.join(available)}\n"
                error_msg += f"Example: --provider {available[0]}"
            else:
                error_msg += "\nNo providers are currently configured. See .env.example for setup instructions."

            raise APIError(error_msg)

    def complete(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.0,
        response_format: Optional[dict] = None,
    ) -> _APIResponse:
        """Complete using the configured provider."""
        return self.client.complete(messages, model, temperature, response_format)

    def get_provider(self) -> str:
        """Get the name of the current provider."""
        return self.provider

    def get_default_model(self) -> str:
        """Get the default model for the current provider."""
        return self.client.get_default_model()

    @classmethod
    def list_available_providers(cls) -> list[str]:
        """List all providers that are properly configured."""
        available = []
        temp_client = cls.__new__(cls)
        temp_client.providers = {
            "openai": _OpenAIClient(),
            "anthropic": _AnthropicClient(),
        }

        for name, client in temp_client.providers.items():
            if client.is_available():
                available.append(name)

        return available


def get_llm_client(provider: Optional[str] = None) -> UnifiedLLMClient:
    """
    Get a unified LLM client.

    Args:
        provider: Optional provider name ('openai', 'anthropic', or 'claude')

    Returns:
        UnifiedLLMClient instance
    """
    return UnifiedLLMClient(provider)


# Provider information for CLI help
SUPPORTED_PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        "env_key": "OPENAI_API_KEY",
        "default_model": "gpt-4o",
    },
    "anthropic": {
        "name": "Anthropic/Claude",
        "models": ["claude-opus-4-20250514"],
        "env_key": "ANTHROPIC_API_KEY",
        "default_model": "claude-opus-4-20250514",
    },
}
