"""
Character Service

This service handles character analysis and gender identification in books.
"""

import asyncio
import json
import logging
import time
from collections import OrderedDict
from threading import RLock
from typing import Any, Optional

from src.models.book import Book
from src.models.character import Character, CharacterAnalysis, Gender
from src.providers.base import LLMProvider
from src.services.base import BaseService, ServiceConfig
from src.strategies.analysis import AnalysisStrategy, SmartChunkingStrategy
# from src.utils.smart_character_registry import SmartCharacterRegistry  # No longer needed with global dedup
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

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

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
                    # Handle gender with fallback for invalid values
                    gender_str = char_data.get("gender", "unknown").lower()
                    # Map common variations to valid values
                    gender_map = {
                        "unknown/mixed": "unknown",
                        "mixed": "unknown",
                        "other": "non-binary",
                        "nonbinary": "non-binary"
                    }
                    gender_str = gender_map.get(gender_str, gender_str)

                    # Try to create Gender enum, fallback to unknown if invalid
                    try:
                        gender = Gender(gender_str)
                    except ValueError:
                        self.logger.warning(f"Invalid gender '{gender_str}' for character {name}, using 'unknown'")
                        gender = Gender.UNKNOWN

                    character_map[name] = Character(
                        name=name,
                        gender=gender,
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
2. Gender (MUST be exactly one of: male, female, non-binary, unknown, neutral)
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

            # Use incremental LLM-based deduplication
            if self.provider:
                characters = await self._analyze_with_smart_deduplication(text_chunks)
            else:
                # Without a provider, can't do smart deduplication
                # Just merge results without deduplication
                chunk_results = await self._analyze_chunks_async(text_chunks)
                characters = self.character_merger.merge(chunk_results)
                self.logger.warning("No LLM provider available for smart deduplication")
                self.logger.info(f"Identified {len(characters)} characters (no deduplication)")

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

    async def _analyze_with_smart_deduplication(self, text_chunks: list[str]) -> list[Character]:
        """
        Analyze chunks with global LLM-based character deduplication.

        Two-phase approach:
        1. Extract all characters from all chunks (deterministic)
        2. Perform global deduplication in a single LLM call

        Args:
            text_chunks: Text chunks to analyze

        Returns:
            List of unique characters with aliases
        """
        self.logger.info("🚀 Using global LLM deduplication for accurate character analysis")

        # Phase 1: Extract all characters from all chunks
        all_raw_characters = await self._extract_all_characters(text_chunks)

        # Phase 2: Global LLM deduplication
        deduplicated_characters = await self._global_llm_deduplication(
            all_raw_characters,
            "Unknown Book"  # We'll improve this later
        )

        return deduplicated_characters

    async def _extract_all_characters(self, text_chunks: list[str]) -> list[dict]:
        """
        Extract characters from all chunks without deduplication.
        Uses lower temperature for consistency.
        """
        total_chunks = len(text_chunks)
        self.logger.info(f"📚 Phase 1: Extracting characters from {total_chunks} chunks")

        all_characters = []
        raw_count = 0

        for i, chunk in enumerate(text_chunks):
            progress_pct = ((i + 1) / total_chunks) * 100
            self.logger.info(f"  Processing chunk {i+1}/{total_chunks} ({progress_pct:.1f}% complete)")

            # Extract with lower temperature for consistency
            result = await self._analyze_single_chunk(chunk, i, temperature=0.3)

            if result and "characters" in result:
                # Add source tracking for better deduplication
                for char in result["characters"]:
                    if char.get("name"):
                        char["source_chunk"] = i
                        char["source_context"] = chunk[:200]  # Store context snippet
                        all_characters.append(char)
                        raw_count += 1

        self.logger.info(f"✅ Extracted {raw_count} raw character mentions")
        return all_characters

    async def _global_llm_deduplication(self, all_characters: list[dict], book_title: str) -> list[Character]:
        """
        Perform global LLM-based deduplication in a single call.
        """
        if not all_characters:
            return []

        self.logger.info(f"📊 Phase 2: Global deduplication of {len(all_characters)} character mentions")

        # Group potential duplicates
        character_groups = self._group_potential_duplicates(all_characters)
        self.logger.info(f"  Identified {len(character_groups)} potential character groups")

        # Create deduplication prompt
        dedup_prompt = self._create_global_dedup_prompt(character_groups, book_title)

        try:
            # Single LLM call for ALL deduplication decisions
            messages = [
                {"role": "system", "content": dedup_prompt["system"]},
                {"role": "user", "content": dedup_prompt["user"]}
            ]

            response = await self.provider.complete_async(
                messages=messages,
                temperature=0.3,  # Low temperature for consistency
                max_tokens=4000
            )

            # Parse and apply deduplication
            dedup_result = self._parse_dedup_response(response)
            final_characters = self._apply_deduplication_decisions(
                dedup_result, character_groups, all_characters
            )

            # Log statistics
            unique_count = len(final_characters)
            merged_count = len(all_characters) - unique_count

            self.logger.info("\n" + "="*60)
            self.logger.info("✅ CHARACTER ANALYSIS COMPLETE")
            self.logger.info("="*60)
            self.logger.info(f"📊 Final Statistics:")
            self.logger.info(f"  • Raw character mentions: {len(all_characters)}")
            self.logger.info(f"  • Unique characters: {unique_count}")
            self.logger.info(f"  • Duplicates merged: {merged_count}")
            self.logger.info(f"  • Deduplication rate: {merged_count/max(1, len(all_characters))*100:.1f}%")
            self.logger.info("="*60 + "\n")

            return final_characters

        except Exception as e:
            self.logger.error(f"Global deduplication failed: {e}")
            # Fallback to simple deduplication
            return self._fallback_deduplication(all_characters)

    def _group_potential_duplicates(self, all_characters: list[dict]) -> list[list[dict]]:
        """
        Group characters that might be duplicates for LLM review.
        """
        groups = []
        processed = set()

        for i, char1 in enumerate(all_characters):
            if i in processed:
                continue

            group = [char1]
            processed.add(i)

            # Find potential duplicates
            for j, char2 in enumerate(all_characters[i+1:], i+1):
                if j in processed:
                    continue

                # Check if potentially same character
                if self._potentially_same_character(char1, char2):
                    group.append(char2)
                    processed.add(j)

            groups.append(group)

        return groups

    def _potentially_same_character(self, char1: dict, char2: dict) -> bool:
        """
        Quick heuristic to check if two characters might be the same.
        Intentionally broad - LLM makes final decision.
        """
        name1 = char1.get("name", "").lower()
        name2 = char2.get("name", "").lower()

        # Exact match
        if name1 == name2:
            return True

        # One contains the other
        if name1 in name2 or name2 in name1:
            return True

        # Share significant name parts
        parts1 = set(name1.split())
        parts2 = set(name2.split())
        if parts1 & parts2:  # Intersection
            return True

        # Same gender and similar role
        if (char1.get("gender") == char2.get("gender") and
            char1.get("importance") == char2.get("importance")):
            desc1 = (char1.get("description") or "").lower()
            desc2 = (char2.get("description") or "").lower()
            if desc1 and desc2 and (desc1 in desc2 or desc2 in desc1):
                return True

        return False

    def _create_global_dedup_prompt(self, character_groups: list[list[dict]], book_title: str) -> dict:
        """
        Create comprehensive prompt for global deduplication.
        """
        system_prompt = f"""You are an expert at identifying duplicate character references in literature.

Analyzing the book: "{book_title}"

Consider:
- Nicknames and variations (Tom/Tommy/Thomas, Huck/Huckleberry)
- Titles and full names (Mr. Smith/John Smith/Smith)
- Role descriptions (the narrator/the author/Swift)
- Context from descriptions

Be thorough but accurate - only merge if confident they're the same person."""

        # Format groups for review
        groups_json = []
        for i, group in enumerate(character_groups):
            groups_json.append({
                "group_id": i,
                "characters": [
                    {
                        "name": c.get("name"),
                        "gender": c.get("gender"),
                        "description": c.get("description"),
                        "chunk": c.get("source_chunk")
                    }
                    for c in group
                ]
            })

        user_prompt = f"""Review these character groups and identify which characters in each group are the same person.

{json.dumps(groups_json, indent=2)}

For each group, return:
{{
  "group_id": <number>,
  "is_same": true/false,
  "primary_name": "most complete name if same",
  "aliases": ["other variations"],
  "confidence": 0.0-1.0
}}

Return JSON with a 'groups' array."""

        return {"system": system_prompt, "user": user_prompt}

    def _parse_dedup_response(self, response: str) -> dict:
        """Parse deduplication response from LLM."""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Try extracting from markdown
            import re
            json_match = re.search(r'```(?:json)?\s*({.*?})\s*```', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except:
                    pass

            # Try raw JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass

        return {"groups": []}

    def _apply_deduplication_decisions(
        self, dedup_result: dict, character_groups: list[list[dict]], all_characters: list[dict]
    ) -> list[Character]:
        """
        Apply LLM deduplication decisions to create final character list.
        """
        final_characters = []

        for group_decision in dedup_result.get("groups", []):
            group_id = group_decision.get("group_id", 0)
            if group_id >= len(character_groups):
                continue

            group = character_groups[group_id]

            if group_decision.get("is_same", False):
                # Merge into single character
                primary = group[0]

                # Use LLM's suggested primary name
                if group_decision.get("primary_name"):
                    primary["name"] = group_decision["primary_name"]

                # Collect aliases
                aliases = set(group_decision.get("aliases", []))
                for char in group[1:]:
                    if char["name"] != primary["name"]:
                        aliases.add(char["name"])

                character = self._create_character_object(primary, list(aliases))
                final_characters.append(character)

                self.logger.info(
                    f"  ✓ Merged {len(group)} mentions into '{character.name}' "
                    f"(aliases: {', '.join(aliases) if aliases else 'none'})"
                )
            else:
                # Keep as separate characters
                for char_data in group:
                    character = self._create_character_object(char_data)
                    final_characters.append(character)

        return final_characters

    def _create_character_object(self, char_data: dict, aliases: list = None) -> Character:
        """Create a Character object from raw data."""
        # Ensure lists
        if aliases is None:
            aliases = char_data.get("aliases", [])
        if isinstance(aliases, str):
            aliases = [aliases]
        elif aliases is None:
            aliases = []

        titles = char_data.get("titles", [])
        if isinstance(titles, str):
            titles = [titles]
        elif titles is None:
            titles = []

        return Character(
            name=char_data["name"],
            gender=Gender(char_data.get("gender", "unknown")),
            pronouns=char_data.get("pronouns", {}),
            titles=titles,
            aliases=aliases,
            description=char_data.get("description"),
            importance=char_data.get("importance", "supporting"),
            confidence=char_data.get("confidence", 0.8)
        )

    def _fallback_deduplication(self, all_characters: list[dict]) -> list[Character]:
        """
        Simple fallback if LLM deduplication fails.
        """
        seen_names = set()
        unique_characters = []

        for char_data in all_characters:
            name = char_data.get("name", "")
            if name and name not in seen_names:
                seen_names.add(name)
                unique_characters.append(self._create_character_object(char_data))

        self.logger.warning(f"Using fallback deduplication: {len(unique_characters)} unique from {len(all_characters)} raw")
        return unique_characters

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

        # Get concurrency limit from config, but adjust for provider
        max_concurrent = self.config.max_concurrent

        # Reduce concurrency for Anthropic to avoid overwhelming the async client
        if provider_name and "anthropic" in str(provider_name).lower():
            max_concurrent = min(max_concurrent, 5)  # Cap at 5 for Anthropic
            self.logger.info(f"Using reduced concurrency for Anthropic: {max_concurrent}")

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

    async def _analyze_single_chunk(self, chunk: str, chunk_index: int, temperature: float = 0.3) -> dict[str, Any]:
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
                temperature=temperature,  # Use passed temperature for consistency
                response_format={"type": "json_object"}
                if self.provider and self.provider.supports_json
                else None,
            )

            # Parse response
            try:
                result = json.loads(response)
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse JSON from chunk {chunk_index}: {e}")
                self.logger.debug(f"Response preview: {response[:500]}...")

                # Try to extract JSON from the response
                import re
                json_match = re.search(r'\{.*"characters".*\}', response, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group())
                        self.logger.info(f"Extracted JSON from response")
                    except:
                        self.logger.error("Could not parse extracted JSON")
                        result = {"characters": []}
                else:
                    self.logger.error("No JSON found in response")
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
