"""
Ollama Provider Plugin

Local model support via Ollama (https://ollama.com).
Ollama exposes an OpenAI-compatible API at localhost:11434/v1,
so this provider is a thin wrapper over the OpenAI SDK with a
custom base_url — no API key required.
"""

import asyncio
import os
from typing import Any, Optional

from src.providers.base_provider import BaseProviderPlugin


class OllamaProvider(BaseProviderPlugin):
    """Local model provider via Ollama."""

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Local models via Ollama (no API key required)"

    @property
    def default_model(self) -> str:
        return os.getenv("OLLAMA_MODEL", "llama3")

    @property
    def supports_json(self) -> bool:
        return False

    @property
    def max_tokens(self) -> int:
        return 8192

    @property
    def rate_limit(self) -> Optional[int]:
        return None  # Local — no rate limit

    def initialize(self, config: dict[str, Any]) -> None:
        """Override to skip API key requirement — Ollama is local."""
        self.api_key = "ollama"  # Required by SDK, ignored by Ollama
        self.model = config.get("model") or self.default_model
        self.rate_limiter = None
        self._initialize_client()
        self._initialized = True
        self.logger.info(f"Initialized ollama provider with model {self.model}")

    def _initialize_client(self) -> None:
        """Initialize OpenAI client pointed at local Ollama endpoint."""
        try:
            from openai import AsyncOpenAI

            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
            self.client = AsyncOpenAI(api_key="ollama", base_url=base_url)
            self.logger.debug(f"Ollama client initialized at {base_url}")
        except ImportError as e:
            raise ImportError("openai package not installed. Run: pip install openai") from e

    async def _complete_impl(self, messages: list[dict[str, str]], **kwargs) -> str:
        """Send completion request to local Ollama instance."""
        try:
            request_params = {
                "model": kwargs.get("model", self.model),
                "messages": messages,
                "temperature": kwargs.get("temperature", 0.7),
            }
            if "max_tokens" in kwargs:
                request_params["max_tokens"] = kwargs["max_tokens"]

            response = await asyncio.wait_for(
                self.client.chat.completions.create(**request_params),
                timeout=120.0,  # Local models can be slower
            )
            return response.choices[0].message.content

        except asyncio.TimeoutError as e:
            raise TimeoutError("Ollama request timed out. The model may be loading or your hardware is slow.") from e
        except Exception as e:
            if "connection" in str(e).lower() or "refused" in str(e).lower():
                raise ConnectionError(
                    "Cannot connect to Ollama at localhost:11434. "
                    "Make sure Ollama is running: open the Ollama app or run 'ollama serve'."
                ) from e
            self.logger.error(f"Ollama error: {e}")
            raise

    def get_model_info(self) -> dict[str, Any]:
        return {"context_window": 8192, "max_output": 4096, "supports_vision": False, "supports_json": False}

    async def get_rate_limits(self) -> dict:
        return {"note": "Local model — no rate limits"}
