"""
Unified Provider

This module provides a unified interface that wraps the existing
api_client.py for backward compatibility.
"""

from typing import List, Dict, Any, Optional
import os
import logging

from src.providers.base import LLMProvider
from src.plugins.base import Plugin


class UnifiedProvider(LLMProvider, Plugin):
    """
    Unified provider that wraps the existing UnifiedLLMClient.
    
    This provides backward compatibility with the existing codebase
    while conforming to the new plugin architecture.
    """
    
    def __init__(self):
        """Initialize unified provider."""
        self.client = None
        self.provider_name = None
        self.model = None
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @property
    def name(self) -> str:
        """Provider/plugin name."""
        return "unified"
    
    @property
    def version(self) -> str:
        """Plugin version."""
        return "1.0.0"
    
    @property
    def description(self) -> str:
        """Plugin description."""
        return "Unified provider wrapping existing api_client"
    
    @property
    def supports_json(self) -> bool:
        """Check if current provider supports JSON."""
        if self.provider_name == "openai":
            return True
        elif self.provider_name == "anthropic":
            return True
        return False
    
    @property
    def max_tokens(self) -> int:
        """Get max tokens for current provider."""
        # Use conservative default
        return 4096
    
    @property
    def rate_limit(self) -> Optional[int]:
        """Get rate limit for current provider."""
        if self.provider_name == "grok":
            return 5  # Grok has strict rate limits
        return None
    
    def initialize(self, config: Dict[str, Any]):
        """
        Initialize unified client.
        
        Args:
            config: Configuration with provider, model, etc.
        """
        # Import existing client
        try:
            from api_client import UnifiedLLMClient
            
            # Get provider from config or environment
            self.provider_name = (
                config.get('provider') or 
                os.getenv('DEFAULT_PROVIDER') or
                'openai'
            )
            
            self.model = config.get('model')
            
            # Create client
            self.client = UnifiedLLMClient(
                provider=self.provider_name,
                model=self.model
            )
            
            self.logger.info(
                f"Initialized unified provider with {self.provider_name}"
            )
            
        except ImportError as e:
            self.logger.error(f"Failed to import UnifiedLLMClient: {e}")
            raise
    
    def execute(self, context: Dict[str, Any]) -> Any:
        """
        Execute plugin (complete a prompt).
        
        Args:
            context: Must contain 'messages' key
            
        Returns:
            Completion text
        """
        messages = context.get('messages', [])
        if not messages:
            raise ValueError("No messages provided")
        
        return self.complete(messages, **context)
    
    async def complete_async(self,
                           messages: List[Dict[str, str]],
                           **kwargs) -> str:
        """
        Complete a prompt asynchronously.
        
        Args:
            messages: List of message dicts
            **kwargs: Additional parameters
            
        Returns:
            Completion text
        """
        if not self.client:
            raise RuntimeError("Unified client not initialized")
        
        # Use the existing client's complete method
        import asyncio
        loop = asyncio.get_event_loop()
        
        def sync_complete():
            response = self.client.complete(
                messages=messages,
                model=kwargs.get('model', self.model),
                temperature=kwargs.get('temperature', 0.7),
                max_tokens=kwargs.get('max_tokens'),
                response_format=kwargs.get('response_format')
            )
            
            # Extract content from response
            if hasattr(response, 'content'):
                return response.content
            elif isinstance(response, dict):
                return response.get('content', str(response))
            else:
                return str(response)
        
        return await loop.run_in_executor(None, sync_complete)
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate provider configuration.
        
        Args:
            config: Configuration to validate
            
        Returns:
            True if valid
        """
        # Check that at least one API key is available
        has_key = (
            os.getenv('OPENAI_API_KEY') or
            os.getenv('ANTHROPIC_API_KEY') or
            os.getenv('GROK_API_KEY')
        )
        
        if not has_key:
            self.logger.error("No API keys found in environment")
            return False
        
        return True
    
    def shutdown(self):
        """Clean up resources."""
        self.client = None
        self.logger.info("Unified provider shutdown")