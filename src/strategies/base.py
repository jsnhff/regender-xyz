"""
Base Strategy Classes

This module defines the base interfaces for all strategy patterns
used in the application.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class Strategy(ABC):
    """Base strategy interface."""

    @abstractmethod
    async def execute_async(self, data: Any) -> Any:
        """
        Execute strategy asynchronously.

        Args:
            data: Input data for the strategy

        Returns:
            Strategy execution result
        """
        pass

    def execute(self, data: Any) -> Any:
        """
        Synchronous wrapper for strategy execution.

        Args:
            data: Input data for the strategy

        Returns:
            Strategy execution result
        """
        import asyncio

        return asyncio.run(self.execute_async(data))
