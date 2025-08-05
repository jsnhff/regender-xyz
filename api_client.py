#!/usr/bin/env python3
"""
Unified API client for multiple LLM providers (OpenAI and Grok).

This module provides a consistent interface for interacting with different
LLM APIs while maintaining security and flexibility.
"""

import os
import json
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

# Manual .env loading since dotenv might not be available
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    try:
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Only set if not already in environment
                    if key not in os.environ:
                        os.environ[key] = value.strip()
    except Exception:
        # Silently ignore .env loading errors
        pass

from openai import OpenAI, OpenAIError

# Try to import Grok client if available
try:
    import requests
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False


# Import APIError from book_transform.utils to avoid duplication
try:
    from book_transform.utils import APIError
except ImportError:
    # Fallback if utils not available
    class APIError(Exception):
        """Base exception for API-related errors."""
        pass


@dataclass
class _APIResponse:
    """Standardized response from any LLM API."""
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None
    raw_response: Optional[Any] = None


class _BaseLLMClient(ABC):
    """Abstract base class for LLM API clients."""
    
    @abstractmethod
    def complete(self, messages: List[Dict[str, str]], 
                model: Optional[str] = None,
                temperature: float = 0.0,
                response_format: Optional[Dict] = None) -> _APIResponse:
        """Complete a chat conversation."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this client is properly configured and available."""
        pass
    
    @abstractmethod
    def get_default_model(self) -> str:
        """Get the default model for this provider."""
        pass


class _OpenAIClient(_BaseLLMClient):
    """OpenAI API client implementation."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.client = None
        if self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key)
            except Exception as e:
                raise APIError(f"Failed to initialize OpenAI client: {e}")
    
    def is_available(self) -> bool:
        """Check if OpenAI client is available."""
        return self.client is not None
    
    def get_default_model(self) -> str:
        """Get default OpenAI model from environment or fallback."""
        return os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    
    def complete(self, messages: List[Dict[str, str]], 
                model: Optional[str] = None,
                temperature: float = 0.0,
                response_format: Optional[Dict] = None) -> _APIResponse:
        """Complete using OpenAI API."""
        if not self.client:
            raise APIError("OpenAI client not initialized. Set OPENAI_API_KEY.")
        
        try:
            kwargs = {
                "model": model or self.get_default_model(),
                "messages": messages,
                "temperature": temperature
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
                    "total_tokens": response.usage.total_tokens
                } if response.usage else None,
                raw_response=response
            )
            
        except OpenAIError as e:
            raise APIError(f"OpenAI API error: {e}")
        except Exception as e:
            raise APIError(f"Unexpected error calling OpenAI: {e}")


class _GrokClient(_BaseLLMClient):
    """Grok API client implementation."""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GROK_API_KEY")
        self.base_url = base_url or os.environ.get("GROK_API_BASE_URL", "https://api.x.ai/v1")
        
        if not _REQUESTS_AVAILABLE:
            raise APIError("requests library not available. Install with: pip install requests")
    
    def is_available(self) -> bool:
        """Check if Grok client is available."""
        return bool(self.api_key and self.base_url)
    
    def get_default_model(self) -> str:
        """Get default Grok model from environment or fallback."""
        return os.environ.get("GROK_MODEL", "grok-beta")
    
    def complete(self, messages: List[Dict[str, str]], 
                model: Optional[str] = None,
                temperature: float = 0.0,
                response_format: Optional[Dict] = None) -> _APIResponse:
        """Complete using Grok API."""
        if not self.is_available():
            raise APIError("Grok client not configured. Set GROK_API_KEY.")
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            data = {
                "model": model or self.get_default_model(),
                "messages": messages,
                "temperature": temperature,
                "stream": False
            }
            
            # Note: Grok API might not support response_format yet
            if response_format and response_format.get("type") == "json_object":
                # Add instruction to return JSON in the last message
                if messages and messages[-1]["role"] == "user":
                    messages[-1]["content"] += "\n\nPlease respond with valid JSON only."
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=60
            )
            
            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                raise APIError(f"Grok API error ({response.status_code}): {error_data}")
            
            result = response.json()
            
            return _APIResponse(
                content=result["choices"][0]["message"]["content"],
                model=result.get("model", model or self.get_default_model()),
                usage=result.get("usage"),
                raw_response=result
            )
            
        except requests.RequestException as e:
            raise APIError(f"Grok API request error: {e}")
        except Exception as e:
            raise APIError(f"Unexpected error calling Grok: {e}")


class UnifiedLLMClient:
    """
    Unified client that can use multiple LLM providers.
    
    Priority order:
    1. Explicitly specified provider
    2. Environment variable LLM_PROVIDER
    3. First available provider (OpenAI, then Grok)
    """
    
    def __init__(self, provider: Optional[str] = None):
        self.providers = {
            "openai": _OpenAIClient(),
            "grok": _GrokClient()
        }
        
        # Determine which provider to use
        self.provider = provider or os.environ.get("LLM_PROVIDER")
        
        if not self.provider:
            # Auto-detect first available provider
            for name, client in self.providers.items():
                if client.is_available():
                    self.provider = name
                    break
        
        if not self.provider:
            raise APIError(
                "No LLM provider available. Set either OPENAI_API_KEY or GROK_API_KEY, "
                "or specify provider explicitly."
            )
        
        if self.provider not in self.providers:
            raise APIError(f"Unknown provider: {self.provider}")
        
        self.client = self.providers[self.provider]
        if not self.client.is_available():
            raise APIError(f"Provider {self.provider} is not properly configured.")
    
    def complete(self, messages: List[Dict[str, str]], 
                model: Optional[str] = None,
                temperature: float = 0.0,
                response_format: Optional[Dict] = None) -> _APIResponse:
        """Complete using the configured provider."""
        return self.client.complete(messages, model, temperature, response_format)
    
    def get_provider(self) -> str:
        """Get the name of the current provider."""
        return self.provider
    
    def get_default_model(self) -> str:
        """Get the default model for the current provider."""
        return self.client.get_default_model()
    
    @classmethod
    def list_available_providers(cls) -> List[str]:
        """List all providers that are properly configured."""
        available = []
        temp_client = cls.__new__(cls)
        temp_client.providers = {
            "openai": _OpenAIClient(),
            "grok": _GrokClient()
        }
        
        for name, client in temp_client.providers.items():
            if client.is_available():
                available.append(name)
        
        return available


# Convenience function for backward compatibility
def get_llm_client(provider: Optional[str] = None) -> UnifiedLLMClient:
    """
    Get a unified LLM client.
    
    Args:
        provider: Optional provider name ('openai' or 'grok')
        
    Returns:
        UnifiedLLMClient instance
    """
    return UnifiedLLMClient(provider)


