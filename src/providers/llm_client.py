#!/usr/bin/env python3
"""
Unified LLM client for multiple providers (OpenAI and Anthropic/Claude).

This module provides a consistent interface for interacting with different
LLM APIs while maintaining security and flexibility.
"""

import os
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

# Import circuit breaker
try:
    from src.utils.circuit_breaker import (
        CircuitBreaker,
        CircuitBreakerConfig,
        CircuitBreakerOpenError,
        get_circuit_breaker,
    )
except ImportError:
    # Fallback for when called from within the src package
    from utils.circuit_breaker import (
        CircuitBreaker,
        CircuitBreakerConfig,
        CircuitBreakerOpenError,
        get_circuit_breaker,
    )

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


class RateLimitError(APIError):
    """Exception for rate limiting errors that shouldn't count as failures."""

    pass


class ServiceUnavailableError(APIError):
    """Exception for service unavailable errors."""

    pass


class NetworkTimeoutError(APIError):
    """Exception for network timeout errors."""

    pass


# Configure logging
logger = logging.getLogger(__name__)


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
            error_msg = str(e).lower()
            if "rate limit" in error_msg or "quota" in error_msg:
                raise RateLimitError(f"OpenAI rate limit exceeded: {e}")
            elif "timeout" in error_msg or "connection" in error_msg:
                raise NetworkTimeoutError(f"OpenAI network timeout: {e}")
            elif "service unavailable" in error_msg or "502" in error_msg or "503" in error_msg:
                raise ServiceUnavailableError(f"OpenAI service unavailable: {e}")
            else:
                raise APIError(f"OpenAI API error: {e}")
        except Exception as e:
            error_msg = str(e).lower()
            if "timeout" in error_msg or "connection" in error_msg:
                raise NetworkTimeoutError(f"Network error calling OpenAI: {e}")
            else:
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
            error_msg = str(e).lower()
            if "rate limit" in error_msg or "quota" in error_msg:
                raise RateLimitError(f"Anthropic rate limit exceeded: {e}")
            elif "timeout" in error_msg or "connection" in error_msg:
                raise NetworkTimeoutError(f"Anthropic network timeout: {e}")
            elif "service unavailable" in error_msg or "502" in error_msg or "503" in error_msg:
                raise ServiceUnavailableError(f"Anthropic service unavailable: {e}")
            else:
                raise APIError(f"Anthropic API error: {e}")
        except Exception as e:
            error_msg = str(e).lower()
            if "timeout" in error_msg or "connection" in error_msg:
                raise NetworkTimeoutError(f"Network error calling Anthropic: {e}")
            else:
                raise APIError(f"Unexpected error calling Anthropic: {e}")


class UnifiedLLMClient:
    """
    Unified client that can use multiple LLM providers.

    Priority order:
    1. Explicitly specified provider
    2. Environment variable DEFAULT_PROVIDER
    3. First available provider (OpenAI, then Anthropic)
    """

    def __init__(self, provider: Optional[str] = None, enable_circuit_breaker: bool = True):
        self.providers: dict[str, _BaseLLMClient] = {
            "openai": _OpenAIClient(),
            "anthropic": _AnthropicClient(),
            "claude": _AnthropicClient(),  # Alias for anthropic
        }

        self.enable_circuit_breaker = enable_circuit_breaker
        self._circuit_breaker: Optional[CircuitBreaker] = None

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

        # Initialize circuit breaker if enabled
        if self.enable_circuit_breaker:
            self._init_circuit_breaker()

    def _init_circuit_breaker(self) -> None:
        """Initialize circuit breaker for this provider."""
        # Configure circuit breaker based on provider type
        config = CircuitBreakerConfig(
            failure_threshold=5,  # Open after 5 consecutive failures
            success_threshold=3,  # Close after 3 successes in half-open
            timeout_duration=60.0,  # Wait 1 minute before trying half-open
            reset_timeout=300.0,  # Reset failure count after 5 minutes of success
            monitoring_window=60.0,  # Track failures over 1 minute window
            half_open_max_calls=3,  # Allow 3 calls in half-open state
            expected_exceptions=(APIError, ServiceUnavailableError, NetworkTimeoutError),
            ignore_exceptions=(RateLimitError,),  # Don't count rate limits as failures
        )

        # Get or create named circuit breaker for this provider
        cb_name = f"llm_client_{self.provider}"
        self._circuit_breaker = get_circuit_breaker(cb_name, config)

        logger.info(f"Circuit breaker initialized for provider: {self.provider}")

    def _get_fallback_response(self, messages: list[dict[str, str]]) -> _APIResponse:
        """Generate a fallback response when circuit breaker is open."""
        fallback_content = (
            "I apologize, but the AI service is currently experiencing issues. "
            "Please try again in a few moments. If the problem persists, "
            "please contact support."
        )

        return _APIResponse(
            content=fallback_content,
            model="fallback",
            usage={
                "prompt_tokens": 0,
                "completion_tokens": len(fallback_content.split()),
                "total_tokens": len(fallback_content.split()),
            },
            raw_response=None,
        )

    def complete(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.0,
        response_format: Optional[dict] = None,
        use_fallback: bool = True,
    ) -> _APIResponse:
        """Complete using the configured provider with circuit breaker protection."""
        if not self.enable_circuit_breaker or not self._circuit_breaker:
            # Direct call without circuit breaker
            return self.client.complete(messages, model, temperature, response_format)

        try:
            # Use circuit breaker to protect the API call
            return self._circuit_breaker.call(
                self.client.complete,
                messages,
                model,
                temperature,
                response_format,
            )

        except CircuitBreakerOpenError as e:
            logger.warning(f"Circuit breaker open for {self.provider}: {e}")

            if use_fallback:
                logger.info(f"Using fallback response for {self.provider}")
                return self._get_fallback_response(messages)
            else:
                # Re-raise as APIError for upstream handling
                raise APIError(f"Service temporarily unavailable ({self.provider}): {e}")

        except (RateLimitError, NetworkTimeoutError, ServiceUnavailableError) as e:
            # These errors are already properly categorized
            logger.warning(f"Provider {self.provider} error: {e}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error in circuit breaker for {self.provider}: {e}")
            raise APIError(f"Unexpected error: {e}")

    def get_provider(self) -> str:
        """Get the name of the current provider."""
        return self.provider

    def get_default_model(self) -> str:
        """Get the default model for the current provider."""
        return self.client.get_default_model()

    def get_circuit_breaker_metrics(self) -> Optional[dict]:
        """Get circuit breaker metrics for monitoring."""
        if self._circuit_breaker:
            return self._circuit_breaker.get_metrics()
        return None

    def reset_circuit_breaker(self) -> None:
        """Reset the circuit breaker to closed state."""
        if self._circuit_breaker:
            self._circuit_breaker.reset()
            logger.info(f"Circuit breaker reset for provider: {self.provider}")

    def force_circuit_open(self) -> None:
        """Force circuit breaker to open state for testing."""
        if self._circuit_breaker:
            self._circuit_breaker.force_open()
            logger.warning(f"Circuit breaker forced open for provider: {self.provider}")

    def force_circuit_closed(self) -> None:
        """Force circuit breaker to closed state."""
        if self._circuit_breaker:
            self._circuit_breaker.force_close()
            logger.info(f"Circuit breaker forced closed for provider: {self.provider}")

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


def get_llm_client(
    provider: Optional[str] = None, enable_circuit_breaker: bool = True
) -> UnifiedLLMClient:
    """
    Get a unified LLM client.

    Args:
        provider: Optional provider name ('openai', 'anthropic', or 'claude')
        enable_circuit_breaker: Whether to enable circuit breaker protection

    Returns:
        UnifiedLLMClient instance
    """
    return UnifiedLLMClient(provider, enable_circuit_breaker)


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
