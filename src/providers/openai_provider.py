"""
OpenAI Provider Plugin

This module provides OpenAI LLM integration.
"""

from typing import List, Dict, Any, Optional
import os
import logging

from src.providers.base import LLMProvider
from src.plugins.base import Plugin


class OpenAIProvider(LLMProvider, Plugin):
    """OpenAI provider plugin for LLM operations."""
    
    def __init__(self):
        """Initialize OpenAI provider."""
        self.client = None
        self.model = "gpt-4o-mini"
        self.api_key = None
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @property
    def name(self) -> str:
        """Provider/plugin name."""
        return "openai"
    
    @property
    def version(self) -> str:
        """Plugin version."""
        return "1.0.0"
    
    @property
    def description(self) -> str:
        """Plugin description."""
        return "OpenAI GPT models provider"
    
    @property
    def supports_json(self) -> bool:
        """OpenAI supports JSON mode."""
        return True
    
    @property
    def max_tokens(self) -> int:
        """Maximum tokens for OpenAI models."""
        model_limits = {
            "gpt-4o": 128000,
            "gpt-4o-mini": 128000,
            "gpt-4-turbo": 128000,
            "gpt-4": 8192,
            "gpt-3.5-turbo": 16385
        }
        return model_limits.get(self.model, 4096)
    
    @property
    def rate_limit(self) -> Optional[int]:
        """Rate limit for OpenAI API."""
        # This varies by tier, returning conservative estimate
        return 60  # requests per minute
    
    def initialize(self, config: Dict[str, Any]):
        """
        Initialize OpenAI client.
        
        Args:
            config: Configuration with api_key, model, etc.
        """
        # Get API key from config or environment
        self.api_key = config.get('api_key') or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")
        
        # Set model
        self.model = config.get('model', 'gpt-4o-mini')
        
        # Initialize client
        try:
            import openai
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=config.get('base_url')
            )
            self.logger.info(f"Initialized OpenAI provider with model {self.model}")
        except ImportError:
            raise ImportError("openai package not installed")
    
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
            raise RuntimeError("OpenAI client not initialized")
        
        # Validate messages
        if not self.validate_messages(messages):
            raise ValueError("Invalid message format")
        
        # Prepare parameters
        params = {
            'model': kwargs.get('model', self.model),
            'messages': messages,
            'temperature': kwargs.get('temperature', 0.7),
            'max_tokens': kwargs.get('max_tokens', 4096)
        }
        
        # Add JSON mode if requested
        if kwargs.get('response_format'):
            params['response_format'] = kwargs['response_format']
        
        # Make async call
        import asyncio
        loop = asyncio.get_event_loop()
        
        def sync_complete():
            response = self.client.chat.completions.create(**params)
            return response.choices[0].message.content
        
        return await loop.run_in_executor(None, sync_complete)
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate provider configuration.
        
        Args:
            config: Configuration to validate
            
        Returns:
            True if valid
        """
        # Check for API key
        if not config.get('api_key') and not os.getenv('OPENAI_API_KEY'):
            self.logger.error("No OpenAI API key found")
            return False
        
        # Check model is valid
        valid_models = [
            'gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo',
            'gpt-4', 'gpt-3.5-turbo'
        ]
        model = config.get('model', 'gpt-4o-mini')
        if model not in valid_models:
            self.logger.warning(f"Unknown model: {model}")
        
        return True
    
    def shutdown(self):
        """Clean up resources."""
        self.client = None
        self.logger.info("OpenAI provider shutdown")