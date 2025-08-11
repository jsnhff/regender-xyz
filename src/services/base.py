"""
Base Service Class

This module provides the foundation for all services in the application,
implementing common patterns for initialization, error handling, and
async/sync execution.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging
from dataclasses import dataclass
import asyncio


@dataclass
class ServiceConfig:
    """Configuration for services."""
    cache_enabled: bool = True
    async_enabled: bool = True
    max_retries: int = 3
    timeout: int = 300
    max_concurrent: int = 5
    target_quality: float = 90.0
    max_qc_iterations: int = 3


class BaseService(ABC):
    """
    Base class for all services.
    
    This class provides:
    - Standard initialization pattern
    - Async/sync execution support
    - Error handling
    - Input validation
    - Logging
    """
    
    def __init__(self, config: Optional[ServiceConfig] = None):
        """
        Initialize the service.
        
        Args:
            config: Service configuration
        """
        self.config = config or ServiceConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialize()
    
    @abstractmethod
    def _initialize(self):
        """
        Initialize service resources.
        
        This method should set up any resources needed by the service,
        such as caches, connection pools, or validators.
        """
        pass
    
    @abstractmethod
    async def process_async(self, data: Any) -> Any:
        """
        Process data asynchronously.
        
        This is the main processing method that all services must implement.
        
        Args:
            data: Input data to process
            
        Returns:
            Processed result
        """
        pass
    
    def process(self, data: Any) -> Any:
        """
        Synchronous wrapper for async processing.
        
        This allows services to be used in non-async contexts.
        
        Args:
            data: Input data to process
            
        Returns:
            Processed result
        """
        try:
            # Check if there's already an event loop running
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No loop running, create a new one
            return asyncio.run(self.process_async(data))
        else:
            # Loop already running, schedule the coroutine
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self.process_async(data))
                return future.result()
    
    def validate_input(self, data: Any) -> bool:
        """
        Validate input data.
        
        Override this method to add service-specific validation.
        
        Args:
            data: Data to validate
            
        Returns:
            True if valid, False otherwise
        """
        return data is not None
    
    def handle_error(self, error: Exception, context: Dict) -> None:
        """
        Centralized error handling.
        
        Args:
            error: The exception that occurred
            context: Context information about where the error occurred
            
        Raises:
            The original exception after logging
        """
        self.logger.error(
            f"Error in {self.__class__.__name__}: {error}",
            extra={"context": context}
        )
        raise
    
    async def _retry_async(self, 
                          func: callable, 
                          *args, 
                          max_retries: Optional[int] = None,
                          **kwargs) -> Any:
        """
        Retry an async function with exponential backoff.
        
        Args:
            func: Async function to retry
            args: Positional arguments for func
            max_retries: Maximum number of retries (uses config if not specified)
            kwargs: Keyword arguments for func
            
        Returns:
            Result from successful function call
            
        Raises:
            Last exception if all retries fail
        """
        max_retries = max_retries or self.config.max_retries
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    self.logger.warning(
                        f"Retry {attempt + 1}/{max_retries} after error: {e}. "
                        f"Waiting {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(f"All {max_retries} retries failed")
        
        if last_error:
            raise last_error
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get service metrics.
        
        Override this to provide service-specific metrics.
        
        Returns:
            Dictionary of metrics
        """
        return {
            "service": self.__class__.__name__,
            "config": {
                "cache_enabled": self.config.cache_enabled,
                "async_enabled": self.config.async_enabled,
                "max_retries": self.config.max_retries,
                "timeout": self.config.timeout
            }
        }
    
    def __repr__(self) -> str:
        """String representation of the service."""
        return f"{self.__class__.__name__}(config={self.config})"