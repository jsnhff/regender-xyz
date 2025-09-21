"""
Smart Character Registry V2 with Intelligent Indexing and Progress Feedback

This improved version uses name similarity indexing for fast lookups,
batches LLM calls, and provides visual progress feedback.
"""

import json
import re
from typing import List, Optional, Dict, Any, Set, Tuple
from collections import defaultdict
from difflib import SequenceMatcher
from src.models.character import Character, Gender
import logging
import asyncio


class SmartCharacterRegistry:
    """
    Improved character registry with intelligent name indexing and batching.

    Key improvements:
    1. Name similarity index for O(1) lookups of likely matches
    2. Batched LLM verification (only when needed)
    3. Progress feedback during processing
    4. Smarter caching based on name patterns
    """

    def __init__(self, llm_provider, logger=None, show_progress=True):
        """
        Initialize the improved registry.

        Args:
            llm_provider: The LLM provider for final verification
            logger: Optional logger instance
            show_progress: Whether to show progress feedback
        """
        self.characters = []  # List of confirmed unique characters
        self.llm = llm_provider
        self.logger = logger or logging.getLogger(__name__)
        self.show_progress = show_progress

        # Intelligent indexing structures
        self.name_index = {}  # Exact name -> Character
        self.normalized_index = {}  # Normalized name -> Character
        self.prefix_index = defaultdict(list)  # First word -> [Characters]
        self.surname_index = defaultdict(list)  # Last word -> [Characters]

        # Caching and statistics
        self.match_cache = {}  # Cache verified matches
        self.pending_verifications = []  # Batch LLM verifications
        self.stats = {
            "total_checked": 0,
            "fast_matches": 0,
            "llm_checks": 0,
            "characters_merged": 0
        }

    def _normalize_name(self, name: str) -> str:
        """Normalize a name for comparison."""
        # Remove titles, punctuation, extra spaces
        name = re.sub(r'\b(Mr\.|Mrs\.|Ms\.|Miss|Dr\.|Professor|Captain|Judge)\b', '', name, flags=re.IGNORECASE)
        name = re.sub(r'[^\w\s]', '', name)
        name = ' '.join(name.lower().split())
        return name

    def _get_name_parts(self, name: str) -> Tuple[str, str]:
        """Extract first and last name parts."""
        parts = name.strip().split()
        if not parts:
            return ("", "")
        first = parts[0].lower()
        last = parts[-1].lower() if len(parts) > 1 else ""
        return (first, last)

    def _calculate_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate similarity between two names.

        ULTRA-SAFE: Only returns high confidence for exact/normalized matches.
        Everything else gets low scores to trigger LLM verification.
        """
        # Exact match - 100% confident
        if name1.lower() == name2.lower():
            return 1.0

        # Normalized match (after removing titles) - very confident
        norm1 = self._normalize_name(name1)
        norm2 = self._normalize_name(name2)

        # Empty after normalization? Don't match
        if not norm1 or not norm2:
            return 0.0

        if norm1 == norm2:
            return 0.95

        # EVERYTHING ELSE NEEDS LLM VERIFICATION
        # We return low scores to trigger LLM checking

        # Even if names look similar, we're not confident without context
        # This includes:
        # - Partial matches (Tom vs Tom Sawyer)
        # - Shared components (Mary Smith vs Mary Jones)
        # - Nicknames (Lizzy vs Elizabeth)
        # - Patronymics (Ivan vs Ivanovich)

        # Return a low score to trigger LLM verification
        # But give slight preference based on similarity for candidate selection
        similarity = SequenceMatcher(None, norm1, norm2).ratio()

        # Scale down to always be below threshold
        # This ensures LLM is consulted for anything uncertain
        return similarity * 0.5  # Max 0.5, always below 0.85 threshold

    def _find_likely_matches(self, new_name: str, threshold: float = 0.7) -> List[Character]:
        """
        Find likely character matches using fast indexing.

        Returns characters that likely match based on name similarity,
        without making LLM calls.
        """
        candidates = []
        seen_ids = set()  # Track which characters we've already added

        def add_candidate(char):
            """Add character if not already in candidates."""
            char_id = id(char)
            if char_id not in seen_ids:
                candidates.append(char)
                seen_ids.add(char_id)

        # Check exact name index
        if new_name in self.name_index:
            add_candidate(self.name_index[new_name])

        # Check normalized index
        normalized = self._normalize_name(new_name)
        if normalized in self.normalized_index:
            add_candidate(self.normalized_index[normalized])

        # Check prefix/surname indices
        first, last = self._get_name_parts(new_name)
        if first:
            for char in self.prefix_index.get(first, []):
                similarity = self._calculate_similarity(new_name, char.name)
                if similarity >= threshold:
                    add_candidate(char)

        if last:
            for char in self.surname_index.get(last, []):
                similarity = self._calculate_similarity(new_name, char.name)
                if similarity >= threshold:
                    add_candidate(char)

        # Check aliases of all characters
        for char in self.characters:
            if char.aliases:
                for alias in char.aliases:
                    if self._calculate_similarity(new_name, alias) >= threshold:
                        add_candidate(char)
                        break

        return candidates

    def _index_character(self, character: Character):
        """Add character to all indices."""
        # Exact name
        self.name_index[character.name] = character

        # Normalized name
        normalized = self._normalize_name(character.name)
        self.normalized_index[normalized] = character

        # Name parts
        first, last = self._get_name_parts(character.name)
        if first:
            self.prefix_index[first].append(character)
        if last:
            self.surname_index[last].append(character)

        # Index aliases too
        if character.aliases:
            for alias in character.aliases:
                self.name_index[alias] = character
                norm_alias = self._normalize_name(alias)
                self.normalized_index[norm_alias] = character

    async def add_or_merge_batch(
        self, new_characters: List[Character], context: str
    ) -> List[Character]:
        """
        Process a batch of characters efficiently.

        Uses intelligent indexing to find likely matches, then verifies
        uncertain cases with a single batched LLM call.
        """
        if not new_characters:
            return []

        self.stats["total_checked"] += len(new_characters)

        # Show progress
        if self.show_progress and self.logger:
            self.logger.info(f"🔍 Processing {len(new_characters)} characters from chunk...")

        results = []
        needs_llm_verification = []

        # Phase 1: Fast matching using indices
        for new_char in new_characters:
            # Find likely matches without LLM
            candidates = self._find_likely_matches(new_char.name)

            if not candidates:
                # No match found - will add as new
                results.append((new_char, None, "new"))
                self.stats["fast_matches"] += 1
            elif len(candidates) == 1:
                # Single candidate - only auto-match if VERY confident
                similarity = self._calculate_similarity(new_char.name, candidates[0].name)
                if similarity >= 0.95:  # Only exact or normalized matches
                    results.append((new_char, candidates[0], "matched"))
                    self.stats["fast_matches"] += 1
                    if self.show_progress and self.logger:
                        self.logger.debug(f"  ✓ Auto-matched '{new_char.name}' to '{candidates[0].name}' (confidence: {similarity:.2f})")
                else:
                    # Not confident enough - ALWAYS verify with LLM
                    needs_llm_verification.append((new_char, candidates))
            else:
                # Multiple candidates - need LLM to decide
                needs_llm_verification.append((new_char, candidates))

        # Phase 2: Batch LLM verification for uncertain cases
        if needs_llm_verification:
            if self.show_progress and self.logger:
                self.logger.info(f"🤖 Verifying {len(needs_llm_verification)} uncertain matches with LLM...")

            llm_results = await self._batch_verify_with_llm(needs_llm_verification, context)
            self.stats["llm_checks"] += len(needs_llm_verification)

            for (new_char, candidates), llm_result in zip(needs_llm_verification, llm_results):
                if llm_result and llm_result.get("is_match"):
                    # Find the matching character
                    match_name = llm_result.get("matching_character")
                    match = next((c for c in candidates if c.name == match_name), candidates[0])
                    results.append((new_char, match, "llm_matched"))
                else:
                    results.append((new_char, None, "llm_new"))

        # Phase 3: Apply results
        final_results = []
        for new_char, match, reason in results:
            if match:
                # Merge into existing
                self._merge_into(match, new_char)
                final_results.append(match)
                self.stats["characters_merged"] += 1
                if self.show_progress and self.logger:
                    self.logger.debug(f"  ✓ Merged '{new_char.name}' → '{match.name}' ({reason})")
            else:
                # Add as new character
                self.characters.append(new_char)
                self._index_character(new_char)
                final_results.append(new_char)
                if self.show_progress and self.logger:
                    self.logger.debug(f"  + Added new character: {new_char.name}")

        # Show statistics
        if self.show_progress and self.logger:
            self.logger.info(
                f"📊 Progress: {len(self.characters)} unique characters | "
                f"{self.stats['characters_merged']} merged | "
                f"{self.stats['fast_matches']} fast matches | "
                f"{self.stats['llm_checks']} LLM verifications"
            )

        return final_results

    async def _batch_verify_with_llm(
        self, verification_items: List[Tuple[Character, List[Character]]], context: str
    ) -> List[Dict[str, Any]]:
        """
        Verify multiple uncertain matches in a single LLM call.
        """
        if not verification_items:
            return []

        # Build verification prompt
        verifications = []
        for new_char, candidates in verification_items:
            candidate_names = [c.name for c in candidates[:3]]  # Limit to top 3
            verifications.append({
                "new_name": new_char.name,
                "candidates": candidate_names
            })

        prompt = f"""Verify if these character names match any of their candidate matches.

Context where they appeared:
{context[:300]}...

For each verification below, determine if the new name matches any candidate:

{json.dumps(verifications, indent=2)}

Consider nicknames, titles, aliases, and context clues.
Be careful: similar names might be different people!

Respond with a JSON array matching the input order:
[
    {{
        "new_name": "name from input",
        "is_match": true/false,
        "matching_character": "exact candidate name if matched" or null,
        "confidence": 0.0-1.0
    }},
    ...
]"""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = await self.llm.complete_async(messages, temperature=1.0)

            # Parse response
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                results = json.loads(json_match.group())
                if len(results) == len(verification_items):
                    return results

            # Fallback if parsing fails
            return [{"is_match": False} for _ in verification_items]

        except Exception as e:
            self.logger.error(f"Batch LLM verification failed: {e}")
            return [{"is_match": False} for _ in verification_items]

    def _merge_into(self, existing: Character, new_character: Character):
        """Merge new character data into existing character."""
        # Add new name as alias if different
        if new_character.name != existing.name:
            if not existing.aliases:
                existing.aliases = []
            if new_character.name not in existing.aliases:
                existing.aliases.append(new_character.name)
                # Update indices with new alias
                self.name_index[new_character.name] = existing
                normalized = self._normalize_name(new_character.name)
                self.normalized_index[normalized] = existing

        # Merge other fields (same as before)
        if new_character.aliases:
            if not existing.aliases:
                existing.aliases = []
            for alias in new_character.aliases:
                if alias not in existing.aliases and alias != existing.name:
                    existing.aliases.append(alias)

        # Update importance if higher
        importance_rank = {"main": 3, "supporting": 2, "minor": 1}
        existing_rank = importance_rank.get(str(existing.importance).lower(), 0)
        new_rank = importance_rank.get(str(new_character.importance).lower(), 0)
        if new_rank > existing_rank:
            existing.importance = new_character.importance

    async def add_or_merge(self, new_character: Character, context: str) -> Character:
        """Single character add/merge for compatibility."""
        results = await self.add_or_merge_batch([new_character], context)
        return results[0] if results else new_character

    def get_all(self) -> List[Character]:
        """Get all unique characters."""
        return self.characters

    def get_statistics(self) -> Dict[str, Any]:
        """Get detailed statistics about the deduplication process."""
        return {
            "unique_characters": len(self.characters),
            "total_checked": self.stats["total_checked"],
            "fast_matches": self.stats["fast_matches"],
            "llm_verifications": self.stats["llm_checks"],
            "characters_merged": self.stats["characters_merged"],
            "efficiency_rate": (
                f"{(self.stats['fast_matches'] / max(1, self.stats['total_checked'])) * 100:.1f}%"
                if self.stats["total_checked"] > 0 else "N/A"
            )
        }