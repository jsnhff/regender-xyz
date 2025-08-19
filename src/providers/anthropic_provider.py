"""
Anthropic Provider Plugin

This module provides Anthropic Claude LLM integration.
"""

from typing import List, Dict, Any, Optional
import os
import logging

from src.providers.base import LLMProvider
from src.plugins.base import Plugin


class AnthropicProvider(LLMProvider, Plugin):
    """Anthropic Claude provider plugin for LLM operations."""
    
    def __init__(self):
        """Initialize Anthropic provider."""
        self.client = None
        self.model = "claude-3-haiku-20240307"
        self.api_key = None
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @property
    def name(self) -> str:
        """Provider/plugin name."""
        return "anthropic"
    
    @property
    def version(self) -> str:
        """Plugin version."""
        return "1.0.0"
    
    @property
    def description(self) -> str:
        """Plugin description."""
        return "Anthropic Claude models provider"
    
    @property
    def supports_json(self) -> bool:
        """Claude supports structured output."""
        return True
    
    @property
    def max_tokens(self) -> int:
        """Maximum tokens for Claude models."""
        model_limits = {
            "claude-3-opus-20240229": 200000,
            "claude-3-sonnet-20240229": 200000,
            "claude-3-haiku-20240307": 200000,
            "claude-2.1": 100000,
            "claude-2.0": 100000,
            "claude-instant-1.2": 100000
        }
        return model_limits.get(self.model, 100000)
    
    @property
    def rate_limit(self) -> Optional[int]:
        """Rate limit for Anthropic API."""
        # Varies by tier, conservative estimate
        return 50  # requests per minute
    
    def initialize(self, config: Dict[str, Any]):
        """
        Initialize Anthropic client.
        
        Args:
            config: Configuration with api_key, model, etc.
        """
        # Get API key from config or environment
        self.api_key = config.get('api_key') or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("Anthropic API key not provided")
        
        # Set model
        self.model = config.get('model', 'claude-3-haiku-20240307')
        
        # Initialize client
        try:
            import anthropic
            self.client = anthropic.Anthropic(
                api_key=self.api_key,
                base_url=config.get('base_url')
            )
            self.logger.info(f"Initialized Anthropic provider with model {self.model}")
        except ImportError:
            raise ImportError("anthropic package not installed")
    
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
            raise RuntimeError("Anthropic client not initialized")
        
        # Validate messages
        if not self.validate_messages(messages):
            raise ValueError("Invalid message format")
        
        # Convert messages to Claude format
        system_message = None
        claude_messages = []
        
        for msg in messages:
            if msg['role'] == 'system':
                system_message = msg['content']
            else:
                claude_messages.append({
                    'role': msg['role'],
                    'content': msg['content']
                })
        
        # Prepare parameters
        params = {
            'model': kwargs.get('model', self.model),
            'messages': claude_messages,
            'max_tokens': kwargs.get('max_tokens', 4096),
            'temperature': kwargs.get('temperature', 0.7)
        }
        
        if system_message:
            params['system'] = system_message
        
        # Make async call
        import asyncio
        loop = asyncio.get_event_loop()
        
        def sync_complete():
            response = self.client.messages.create(**params)
            return response.content[0].text
        
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
        if not config.get('api_key') and not os.getenv('ANTHROPIC_API_KEY'):
            self.logger.error("No Anthropic API key found")
            return False
        
        # Check model is valid
        valid_models = [
            'claude-3-opus-20240229',
            'claude-3-sonnet-20240229', 
            'claude-3-haiku-20240307',
            'claude-2.1',
            'claude-2.0',
            'claude-instant-1.2'
        ]
        model = config.get('model', 'claude-3-haiku-20240307')
        if model not in valid_models:
            self.logger.warning(f"Unknown model: {model}")
        
        return True
    
    def shutdown(self):
        """Clean up resources."""
        self.client = None
        self.logger.info("Anthropic provider shutdown")