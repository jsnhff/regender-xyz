"""
Rate Limiter for API calls

Implements token bucket algorithm for rate limiting.
"""

import asyncio
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter for API calls.

    This ensures we don't exceed token limits per minute.
    """

    def __init__(self, tokens_per_minute: int = 30000, tokens_per_request: int = 4000):
        """
        Initialize rate limiter.

        Args:
            tokens_per_minute: Maximum tokens allowed per minute
            tokens_per_request: Estimated tokens per request
        """
        self.max_tokens = tokens_per_minute
        self.tokens_per_request = tokens_per_request
        self.available_tokens = tokens_per_minute
        self.last_refill = time.time()
        self.lock = asyncio.Lock()

        # Calculate optimal delay
        self.requests_per_minute = tokens_per_minute / tokens_per_request
        self.min_delay = 60.0 / self.requests_per_minute  # Minimum seconds between requests

    async def acquire(self, tokens: Optional[int] = None):
        """
        Acquire tokens from the bucket, waiting if necessary.

        Args:
            tokens: Number of tokens to acquire (defaults to tokens_per_request)
        """
        if tokens is None:
            tokens = self.tokens_per_request

        async with self.lock:
            # Refill bucket based on time elapsed
            now = time.time()
            elapsed = now - self.last_refill
            tokens_to_add = (elapsed / 60.0) * self.max_tokens

            self.available_tokens = min(self.max_tokens, self.available_tokens + tokens_to_add)
            self.last_refill = now

            # Wait if not enough tokens
            while self.available_tokens < tokens:
                wait_time = ((tokens - self.available_tokens) / self.max_tokens) * 60.0
                wait_time = max(wait_time, self.min_delay)  # At least min_delay

                logger.info(f"Rate limit: waiting {wait_time:.1f}s for {tokens} tokens...")
                await asyncio.sleep(wait_time)

                # Refill again after waiting
                now = time.time()
                elapsed = now - self.last_refill
                tokens_to_add = (elapsed / 60.0) * self.max_tokens

                self.available_tokens = min(self.max_tokens, self.available_tokens + tokens_to_add)
                self.last_refill = now

            # Consume tokens
            self.available_tokens -= tokens

            # Always wait minimum delay to prevent bursts
            await asyncio.sleep(self.min_delay)


class OpenAIRateLimiter:
    """Specific rate limiter for OpenAI API."""

    def __init__(self, tier: str = "tier-1"):
        """
        Initialize OpenAI rate limiter.

        Args:
            tier: OpenAI tier level (tier-1, tier-2, etc.)
        """
        # Tier 1 limits (your current tier based on errors)
        if tier == "tier-1":
            self.limiter = TokenBucketRateLimiter(tokens_per_minute=30000, tokens_per_request=4000)
        elif tier == "tier-2":
            self.limiter = TokenBucketRateLimiter(tokens_per_minute=150000, tokens_per_request=4000)
        else:
            # Default conservative limits
            self.limiter = TokenBucketRateLimiter(tokens_per_minute=30000, tokens_per_request=4000)

    async def acquire(self, estimated_tokens: Optional[int] = None):
        """Acquire permission to make an API call."""
        await self.limiter.acquire(estimated_tokens)
