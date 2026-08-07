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
        # Ollama supports JSON mode (format: json) since v0.1.9, exposed through
        # the OpenAI-compatible endpoint as response_format {"type": "json_object"}.
        return True

    @property
    def max_tokens(self) -> int:
        return self.get_model_info().get("context_window", 8192)

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
            if kwargs.get("response_format") == "json_object":
                request_params["response_format"] = {"type": "json_object"}

            timeout = float(os.getenv("OLLAMA_TIMEOUT", "600"))
            response = await asyncio.wait_for(
                self.client.chat.completions.create(**request_params),
                timeout=timeout,  # Local models can be slower; long batches need headroom
            )
            return response.choices[0].message.content

        except asyncio.TimeoutError as e:
            raise TimeoutError(
                "Ollama request timed out. The model may be loading or your hardware is slow."
            ) from e
        except Exception as e:
            if "connection" in str(e).lower() or "refused" in str(e).lower():
                raise ConnectionError(
                    "Cannot connect to Ollama at localhost:11434. "
                    "Make sure Ollama is running: open the Ollama app or run 'ollama serve'."
                ) from e
            self.logger.error(f"Ollama error: {e}")
            raise

    def get_model_info(self) -> dict[str, Any]:
        context_window = self._get_context_window()
        return {
            "context_window": context_window,
            "max_output": min(context_window // 2, 8192),
            "supports_vision": False,
            "supports_json": True,
        }

    def _get_context_window(self) -> int:
        """Read the model's real context length from Ollama's /api/show.

        The effective window is the smaller of the model's trained context and the
        server's num_ctx (OLLAMA_CONTEXT_LENGTH, VRAM-based default). Falls back to
        8192 if the server is unreachable.
        """
        if getattr(self, "_context_window", None):
            return self._context_window

        import json as _json
        import urllib.request

        base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1").removesuffix("/v1")
        try:
            req = urllib.request.Request(
                f"{base}/api/show",
                data=_json.dumps({"model": self.model}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                info = _json.load(resp).get("model_info", {})
            model_ctx = next((v for k, v in info.items() if k.endswith(".context_length")), 8192)
        except Exception as e:
            self.logger.debug(f"Could not read context length from Ollama: {e}")
            model_ctx = 8192

        server_ctx = os.getenv("OLLAMA_CONTEXT_LENGTH")
        if server_ctx and server_ctx.isdigit():
            model_ctx = min(model_ctx, int(server_ctx))

        self._context_window = model_ctx
        return model_ctx

    async def get_rate_limits(self) -> dict:
        return {"note": "Local model — no rate limits"}
