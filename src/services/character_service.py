"""
Character Service

This service handles character analysis and gender identification in books.
"""

import asyncio
import json
import time
from collections import OrderedDict
from threading import RLock
from typing import Any, Optional

from src.models.book import Book
from src.models.character import Character, CharacterAnalysis, Gender
from src.providers.base import LLMProvider
from src.services.base import BaseService, ServiceConfig
from src.strategies.analysis import AnalysisStrategy, SmartChunkingStrategy
from src.utils.token_manager import TokenManager


class CacheEntry:
    """Cache entry with TTL support."""

    def __init__(self, value: CharacterAnalysis, ttl: Optional[float] = None):
        self.value = value
        self.created_at = time.time()
        self.expires_at = self.created_at + ttl if ttl else None
        self.access_count = 1
        self.last_accessed = self.created_at

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return self.expires_at is not None and time.time() > self.expires_at

    def touch(self) -> None:
        """Update access statistics."""
        self.access_count += 1
        self.last_accessed = time.time()


class CharacterCache:
    """
    Thread-safe LRU cache for character analysis with TTL support.

    Features:
    - LRU eviction policy
    - Configurable maximum size
    - Optional TTL (time-to-live) for entries
    - Thread-safe operations for async contexts
    - Cache statistics (hits, misses, evictions)
    - Memory-efficient storage
    """

    def __init__(self, max_size: int = 100, default_ttl: Optional[float] = None):
        """
        Initialize LRU cache.

        Args:
            max_size: Maximum number of entries (default: 100)
            default_ttl: Default TTL in seconds (None for no expiration)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = RLock()  # Reentrant lock for thread safety

        # Statistics
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expired_evictions": 0,
            "size_evictions": 0,
        }

    async def get_async(self, key: str) -> Optional[CharacterAnalysis]:
        """
        Get cached analysis.

        Args:
            key: Cache key

        Returns:
            Cached analysis or None if not found/expired
        """
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats["misses"] += 1
                return None

            # Check if expired
            if entry.is_expired():
                self._cache.pop(key)
                self._stats["misses"] += 1
                self._stats["expired_evictions"] += 1
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.touch()
            self._stats["hits"] += 1

            return entry.value

    async def set_async(
        self, key: str, value: CharacterAnalysis, ttl: Optional[float] = None
    ) -> None:
        """
        Cache analysis.

        Args:
            key: Cache key
            value: Analysis to cache
            ttl: TTL for this entry (uses default_ttl if None)
        """
        ttl = ttl if ttl is not None else self.default_ttl

        with self._lock:
            # If key exists, update it
            if key in self._cache:
                self._cache[key] = CacheEntry(value, ttl)
                self._cache.move_to_end(key)
                return

            # Add new entry
            self._cache[key] = CacheEntry(value, ttl)

            # Evict if over capacity
            while len(self._cache) > self.max_size:
                # Remove least recently used item
                oldest_key, _ = self._cache.popitem(last=False)
                self._stats["evictions"] += 1
                self._stats["size_evictions"] += 1

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            # Reset stats except totals
            evictions = self._stats["evictions"]
            expired_evictions = self._stats["expired_evictions"]
            size_evictions = self._stats["size_evictions"]
            self._stats = {
                "hits": 0,
                "misses": 0,
                "evictions": evictions,
                "expired_evictions": expired_evictions,
                "size_evictions": size_evictions,
            }

    def cleanup_expired(self) -> int:
        """
        Remove expired entries.

        Returns:
            Number of entries removed
        """
        removed_count = 0

        with self._lock:
            # Collect expired keys
            expired_keys = []
            for key, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(key)

            # Remove expired entries
            for key in expired_keys:
                self._cache.pop(key)
                removed_count += 1
                self._stats["expired_evictions"] += 1
                self._stats["evictions"] += 1

        return removed_count

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0.0

            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "hit_rate": hit_rate,
                "evictions": self._stats["evictions"],
                "expired_evictions": self._stats["expired_evictions"],
                "size_evictions": self._stats["size_evictions"],
                "total_requests": total_requests,
                "memory_usage_bytes": self._estimate_memory_usage(),
            }

    def _estimate_memory_usage(self) -> int:
        """
        Estimate memory usage in bytes.

        Returns:
            Estimated memory usage
        """
        # Rough estimate based on entry count and average object sizes
        # This is an approximation since exact memory usage is difficult to calculate
        base_overhead = 200  # Per entry overhead (dict, CacheEntry object, etc.)
        avg_key_size = 64  # Average key size
        avg_value_size = 2048  # Average CharacterAnalysis size estimate

        return len(self._cache) * (base_overhead + avg_key_size + avg_value_size)

    def get_info(self) -> dict[str, Any]:
        """
        Get detailed cache information.

        Returns:
            Dictionary with cache configuration and statistics
        """
        with self._lock:
            stats = self.get_stats()

            # Add configuration info
            info = {
                "config": {
                    "max_size": self.max_size,
                    "default_ttl": self.default_ttl,
                },
                "statistics": stats,
            }

            # Add entry details if cache is small
            if len(self._cache) <= 10:
                info["entries"] = {}
                for key, entry in self._cache.items():
                    info["entries"][key] = {
                        "created_at": entry.created_at,
                        "expires_at": entry.expires_at,
                        "access_count": entry.access_count,
                        "last_accessed": entry.last_accessed,
                        "is_expired": entry.is_expired(),
                    }

            return info


class CharacterMerger:
    """Merges character results from multiple chunks."""

    def merge(self, chunk_results: list[dict[str, Any]]) -> list[Character]:
        """
        Merge character results from multiple chunks.

        Args:
            chunk_results: List of analysis results from chunks

        Returns:
            Merged list of characters
        """
        character_map = {}

        for result in chunk_results:
            for char_data in result.get("characters", []):
                name = char_data.get("name")
                if not name:
                    continue

                if name not in character_map:
                    # Ensure aliases and titles are lists
                    aliases = char_data.get("aliases", [])
                    if aliases is None:
                        aliases = []
                    elif isinstance(aliases, str):
                        aliases = [aliases] if aliases else []

                    titles = char_data.get("titles", [])
                    if titles is None:
                        titles = []
                    elif isinstance(titles, str):
                        titles = [titles] if titles else []

                    # Create new character
                    character_map[name] = Character(
                        name=name,
                        gender=Gender(char_data.get("gender", "unknown")),
                        pronouns=char_data.get("pronouns", {}),
                        titles=titles,
                        aliases=aliases,
                        description=char_data.get("description"),
                        importance=char_data.get("importance", "supporting"),
                        confidence=char_data.get("confidence", 1.0),
                    )
                else:
                    # Merge with existing
                    existing = character_map[name]

                    # Update importance if more significant
                    importance_rank = {"minor": 0, "supporting": 1, "main": 2}
                    if importance_rank.get(
                        char_data.get("importance", "minor"), 0
                    ) > importance_rank.get(existing.importance, 0):
                        existing.importance = char_data.get("importance")

                    # Merge aliases - handle both string and list
                    aliases = char_data.get("aliases", [])
                    if aliases is None:
                        aliases = []
                    elif isinstance(aliases, str):
                        aliases = [aliases] if aliases else []
                    for alias in aliases:
                        if alias and alias not in existing.aliases:
                            existing.aliases.append(alias)

                    # Average confidence
                    existing.confidence = (
                        existing.confidence + char_data.get("confidence", 1.0)
                    ) / 2

        return list(character_map.values())


class PromptGenerator:
    """Generates prompts for character analysis."""

    def generate_analysis_prompt(self, text: str) -> dict[str, str]:
        """
        Generate character analysis prompt.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with system and user prompts
        """
        system_prompt = """You are a literary character analyzer. Your task is to identify all characters mentioned in the text and determine their gender based on context clues like pronouns, titles, and descriptions.

For each character, provide:
1. Name (full name if available)
2. Gender (male, female, non-binary, or unknown)
3. Pronouns used (subject/object/possessive)
4. Any titles (Mr., Mrs., Dr., etc.)
5. Aliases or nicknames
6. Brief description if available
7. Importance (main, supporting, or minor)
8. Confidence level (0-1)

Output as JSON with a 'characters' array."""

        user_prompt = f"""Analyze the following text and identify all characters with their genders:

{text}

Remember to output valid JSON with a 'characters' array containing the character information."""

        return {"system": system_prompt, "user": user_prompt}


class CharacterService(BaseService):
    """
    Service for character analysis.

    This service:
    - Analyzes books to identify characters
    - Determines character genders
    - Provides character context for transformations
    """

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        strategy: Optional[AnalysisStrategy] = None,
        config: Optional[ServiceConfig] = None,
        token_manager: Optional[TokenManager] = None,
    ):
        """
        Initialize character service.

        Args:
            provider: LLM provider for analysis
            strategy: Analysis strategy
            config: Service configuration
            token_manager: Token manager for consistent estimation
        """
        self.provider = provider
        self.strategy = strategy or self._get_default_strategy()
        self.token_manager = token_manager
        super().__init__(config)

    def _initialize(self):
        """Initialize character analysis resources."""
        self.prompt_generator = PromptGenerator()
        self.character_merger = CharacterMerger()

        # Initialize token manager if not provided
        if not self.token_manager:
            if self.provider:
                provider_name = getattr(self.provider, "name", "openai")
                model_name = getattr(self.provider, "model", None)
                self.token_manager = TokenManager.for_provider(provider_name, model_name)
            else:
                self.token_manager = TokenManager()  # Default to GPT-4

        self.logger.info(f"Using TokenManager for {self.token_manager.config.name}")

        # Initialize cache with configurable parameters
        if self.config.cache_enabled:
            # Get cache configuration from service config or use defaults
            cache_max_size = getattr(self.config, "cache_max_size", 100)
            cache_ttl = getattr(self.config, "cache_ttl", None)  # No TTL by default

            self.cache = CharacterCache(max_size=cache_max_size, default_ttl=cache_ttl)
            self.logger.info(f"Initialized cache with max_size={cache_max_size}, ttl={cache_ttl}")
        else:
            self.cache = None

        self.logger.info(f"Initialized {self.__class__.__name__}")

    def _get_default_strategy(self) -> AnalysisStrategy:
        """Get default analysis strategy."""
        return SmartChunkingStrategy()

    async def process_async(self, book: Book) -> CharacterAnalysis:
        """
        Analyze characters in a book.

        Args:
            book: Book to analyze

        Returns:
            Character analysis results
        """
        # Check cache
        book_hash = book.hash()
        if self.cache:
            cached = await self.cache.get_async(book_hash)
            if cached:
                self.logger.info(f"Using cached character analysis for {book_hash}")
                return cached

        try:
            # Extract text for analysis
            text_chunks = await self.strategy.chunk_book_async(book)
            self.logger.info(f"Created {len(text_chunks)} chunks for analysis")

            # Analyze each chunk
            chunk_results = await self._analyze_chunks_async(text_chunks)

            # Merge results
            characters = self.character_merger.merge(chunk_results)
            self.logger.info(f"Identified {len(characters)} characters")

            # Create analysis result
            analysis = CharacterAnalysis(
                book_id=book_hash,
                characters=characters,
                metadata=self._generate_metadata(characters),
                provider=getattr(self.provider, 'name', getattr(self.provider, 'get_provider', lambda: 'unknown')()) if self.provider else "unknown",
                model=getattr(self.provider, "model", "unknown") if self.provider else "unknown",
            )

            # Cache result
            if self.cache:
                await self.cache.set_async(book_hash, analysis)

            return analysis

        except Exception as e:
            self.handle_error(e, {"book_title": book.title})
            # Return empty analysis on error
            return CharacterAnalysis(
                book_id=book.hash(),
                characters=[],
                metadata={"error": str(e)},
                provider=getattr(self.provider, 'name', getattr(self.provider, 'get_provider', lambda: 'unknown')()) if self.provider else "unknown",
                model=getattr(self.provider, "model", "unknown") if self.provider else "unknown",
            )

    async def _analyze_chunks_async(self, chunks: list[str]) -> list[dict]:
        """
        Analyze text chunks with concurrent processing and smart rate limiting.

        Args:
            chunks: Text chunks to analyze

        Returns:
            List of analysis results (maintains order despite concurrent processing)
        """

        # If no provider, return mock results
        if not self.provider:
            self.logger.warning("No LLM provider configured, returning mock results")
            return [{"characters": []} for _ in chunks]

        # Use rate limiter for OpenAI
        rate_limiter = None
        provider_name = getattr(self.provider, 'name', None) or getattr(self.provider, 'get_provider', lambda: '')()
        if provider_name and "openai" in str(provider_name).lower():
            from src.providers.rate_limiter import OpenAIRateLimiter

            rate_limiter = OpenAIRateLimiter(tier="tier-1")
            self.logger.info(f"Using OpenAI rate limiter for {len(chunks)} chunks")

        # Get concurrency limit from config
        max_concurrent = self.config.max_concurrent
        self.logger.info(f"Processing {len(chunks)} chunks with max_concurrent={max_concurrent}")

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)

        async def analyze_chunk_with_semaphore(chunk: str, idx: int) -> tuple[int, dict]:
            """Analyze a single chunk with semaphore control."""
            async with semaphore:
                # Apply rate limiting if needed
                if rate_limiter:
                    # Use TokenManager for consistent estimation
                    estimated_tokens = min(
                        self.token_manager.estimate_tokens(chunk), 4500
                    )  # Cap at 4500
                    await rate_limiter.acquire(estimated_tokens)

                    # Track token usage
                    self.token_manager.track_usage(
                        input_tokens=estimated_tokens,
                        provider=getattr(self.provider, 'name', getattr(self.provider, 'get_provider', lambda: 'unknown')()) if self.provider else "unknown",
                    )

                # Analyze chunk
                self.logger.debug(f"Starting analysis of chunk {idx + 1}/{len(chunks)}")
                try:
                    result = await self._analyze_single_chunk(chunk, idx)
                    self.logger.debug(f"Completed analysis of chunk {idx + 1}/{len(chunks)}")
                    return (idx, result)
                except Exception as e:
                    self.logger.error(f"Error analyzing chunk {idx + 1}: {e}")
                    return (idx, {"chunk_index": idx, "characters": [], "error": str(e)})

        # Create tasks for all chunks
        tasks = [analyze_chunk_with_semaphore(chunk, idx) for idx, chunk in enumerate(chunks)]

        # Track progress
        completed_count = 0
        results_dict = {}

        # Process tasks as they complete
        for coro in asyncio.as_completed(tasks):
            try:
                idx, result = await coro
                results_dict[idx] = result
                completed_count += 1

                # Show progress every 5 completions or at the end
                if completed_count % 5 == 0 or completed_count == len(chunks):
                    self.logger.info(f"Progress: {completed_count}/{len(chunks)} chunks analyzed")

            except Exception as e:
                self.logger.error(f"Task failed with error: {e}")
                # Continue processing other tasks

        # Ensure we have results for all chunks, maintaining order
        results = []
        for idx in range(len(chunks)):
            if idx in results_dict:
                results.append(results_dict[idx])
            else:
                # Fallback for any missing results
                self.logger.warning(f"Missing result for chunk {idx}, using empty result")
                results.append({"chunk_index": idx, "characters": []})

        self.logger.info(f"Completed analysis of {len(results)} chunks")
        return results

    async def _analyze_single_chunk(self, chunk: str, chunk_index: int) -> dict[str, Any]:
        """
        Analyze a single text chunk.

        Args:
            chunk: Text to analyze
            chunk_index: Index of the chunk

        Returns:
            Analysis results
        """
        self.logger.debug(f"Analyzing chunk {chunk_index}")

        # Generate prompt
        prompts = self.prompt_generator.generate_analysis_prompt(chunk)

        # Create messages
        messages = [
            {"role": "system", "content": prompts["system"]},
            {"role": "user", "content": prompts["user"]},
        ]

        if not self.provider:
            self.logger.error("No LLM provider configured for character analysis")
            return {"chunk_index": chunk_index, "characters": []}

        try:
            # Call LLM
            response = await self.provider.complete_async(
                messages=messages,
                temperature=0.1,  # Low temperature for consistency
                response_format={"type": "json_object"}
                if self.provider and self.provider.supports_json
                else None,
            )

            # Parse response
            try:
                result = json.loads(response)
            except json.JSONDecodeError:
                self.logger.warning(f"Failed to parse JSON from chunk {chunk_index}")
                result = {"characters": []}

            result["chunk_index"] = chunk_index
            return result

        except Exception as e:
            self.logger.error(f"Error analyzing chunk {chunk_index}: {e}")
            return {"chunk_index": chunk_index, "characters": []}

    def _generate_metadata(self, characters: list[Character]) -> dict[str, Any]:
        """
        Generate metadata about the analysis.

        Args:
            characters: List of identified characters

        Returns:
            Metadata dictionary
        """
        stats = {"total": len(characters), "by_gender": {}, "by_importance": {}}

        for char in characters:
            # Count by gender
            gender_key = char.gender.value
            stats["by_gender"][gender_key] = stats["by_gender"].get(gender_key, 0) + 1

            # Count by importance
            stats["by_importance"][char.importance] = (
                stats["by_importance"].get(char.importance, 0) + 1
            )

        return stats

    def get_metrics(self) -> dict[str, Any]:
        """Get service metrics including detailed cache statistics."""
        metrics = super().get_metrics()
        metrics.update(
            {
                "provider": getattr(self.provider, 'name', getattr(self.provider, 'get_provider', lambda: 'none')()) if self.provider else "none",
                "strategy": self.strategy.__class__.__name__,
            }
        )

        # Add detailed cache metrics if cache is enabled
        if self.cache:
            cache_stats = self.cache.get_stats()
            metrics["cache"] = cache_stats
            # Also include cache size at top level for backward compatibility
            metrics["cache_size"] = cache_stats["size"]
        else:
            metrics["cache_size"] = 0
            metrics["cache"] = None

        # Add token usage metrics
        if self.token_manager:
            metrics["token_usage"] = self.token_manager.get_usage_stats()
            metrics["model_info"] = self.token_manager.get_model_info()

        return metrics

    def clear_cache(self) -> bool:
        """
        Clear the character analysis cache.

        Returns:
            True if cache was cleared, False if no cache is enabled
        """
        if self.cache:
            self.cache.clear()
            self.logger.info("Character analysis cache cleared")
            return True
        return False

    def cleanup_expired_cache(self) -> int:
        """
        Remove expired entries from the cache.

        Returns:
            Number of expired entries removed
        """
        if self.cache:
            removed_count = self.cache.cleanup_expired()
            if removed_count > 0:
                self.logger.info(f"Removed {removed_count} expired cache entries")
            return removed_count
        return 0

    def get_cache_info(self) -> Optional[dict[str, Any]]:
        """
        Get detailed cache information including configuration and statistics.

        Returns:
            Cache information dictionary or None if cache is disabled
        """
        return self.cache.get_info() if self.cache else None
