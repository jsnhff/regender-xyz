"""
Character Service (Refactored)

Simplified character analysis and deduplication service.
Key improvements:
- O(n log n) grouping algorithm using Union-Find
- Robust JSON parsing with multiple strategies
- Retry logic with exponential backoff
- Externalized configuration
- Clear separation of concerns
"""

import asyncio
import json
import logging
import re
from typing import Any, Optional

from src.models.book import Book
from src.models.character import Character, CharacterAnalysis, Gender
from src.providers.base import LLMProvider
from src.services.base import BaseService, ServiceConfig


class UnionFind:
    """Efficient Union-Find data structure for character grouping."""

    def __init__(self, n: int):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        """Find with path compression."""
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x: int, y: int) -> None:
        """Union by rank."""
        px, py = self.find(x), self.find(y)
        if px == py:
            return
        if self.rank[px] < self.rank[py]:
            px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1

    def get_groups(self) -> list[list[int]]:
        """Get all connected components."""
        groups = {}
        for i in range(len(self.parent)):
            root = self.find(i)
            if root not in groups:
                groups[root] = []
            groups[root].append(i)
        return list(groups.values())


class CharacterService(BaseService):
    """
    Refactored character analysis service.

    Simplified architecture:
    1. Extract characters from text chunks
    2. Group similar characters efficiently
    3. Merge groups using LLM verification
    """

    def __init__(
        self, provider: Optional[LLMProvider] = None, config: Optional[ServiceConfig] = None
    ):
        """Initialize service."""
        super().__init__(config)
        self.provider = provider
        self.logger = logging.getLogger(__name__)

        # Load configuration from config or use defaults
        if config:
            # Try to get from attributes first (new style)
            self.extraction_config = getattr(config, "extraction", None) or {
                "chunk_size": 2000,
                "temperature": 0.3,
                "max_retries": 3,
            }
            self.grouping_config = getattr(config, "grouping", None) or {
                "algorithm": "union_find",
                "similarity_threshold": 0.7,
                "max_group_size": 20,
            }
            self.merging_config = getattr(config, "merging", None) or {
                "temperature": 0.3,
                "timeout": 30,
                "batch_size": 50,
            }
        else:
            # Use defaults if no config provided
            self.extraction_config = {"chunk_size": 2000, "temperature": 0.3, "max_retries": 3}
            self.grouping_config = {
                "algorithm": "union_find",
                "similarity_threshold": 0.7,
                "max_group_size": 20,
            }
            self.merging_config = {"temperature": 0.3, "timeout": 30, "batch_size": 50}

    def _initialize(self):
        """Initialize service resources (required by BaseService)."""
        # No additional initialization needed for refactored service
        pass

    async def process(self, data: Any) -> Any:
        """
        Process data (required by BaseService).

        Args:
            data: Book to analyze

        Returns:
            CharacterAnalysis result
        """
        if isinstance(data, Book):
            return await self.analyze_book(data)
        else:
            raise ValueError(f"Expected Book, got {type(data)}")

    # === MAIN INTERFACE ===

    async def analyze_book(self, book: Book) -> CharacterAnalysis:
        """
        Analyze characters in a book.

        Args:
            book: Book to analyze

        Returns:
            CharacterAnalysis with deduplicated characters
        """
        try:
            self.logger.info(f"Starting character analysis for book: {book.title or 'Unknown'}")

            # Phase 1: Extract all character mentions
            raw_characters = await self._extract_all_characters(book.get_text())
            self.logger.info(f"Extracted {len(raw_characters)} raw character mentions")

            # Phase 2: Group similar characters efficiently
            character_groups = self._group_similar_characters(raw_characters)
            self.logger.info(f"Created {len(character_groups)} character groups")

            # Phase 3: Merge groups using LLM
            final_characters = await self._merge_character_groups(character_groups)
            self.logger.info(f"Final character count: {len(final_characters)}")

            # Create analysis result
            return CharacterAnalysis(
                book_id=book.hash(),  # Use book hash as ID
                characters=final_characters,
                metadata=self._calculate_metadata(final_characters),
            )

        except Exception as e:
            self.logger.error(f"Character analysis failed: {e}")
            raise

    # === EXTRACTION METHODS ===

    async def _extract_all_characters(self, text: str) -> list[dict[str, Any]]:
        """
        Extract raw character mentions from text.

        Args:
            text: Book text

        Returns:
            List of raw character dictionaries
        """
        chunks = self._create_chunks(text)
        raw_characters = []

        for i, chunk in enumerate(chunks):
            try:
                characters = await self._extract_from_chunk(chunk, i)
                raw_characters.extend(characters)
            except Exception as e:
                self.logger.warning(f"Failed to extract from chunk {i}: {e}")
                continue

        return raw_characters

    def _create_chunks(self, text: str, chunk_size: int = 2000) -> list[str]:
        """
        Split text into manageable chunks.

        Args:
            text: Text to chunk
            chunk_size: Approximate size of each chunk in tokens

        Returns:
            List of text chunks
        """
        # Simple word-based chunking (4 chars per token approximation)
        words = text.split()
        chunks = []
        current_chunk = []
        current_size = 0

        for word in words:
            word_tokens = len(word) / 4
            if current_size + word_tokens > chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_size = 0
            current_chunk.append(word)
            current_size += word_tokens

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    async def _extract_from_chunk(self, chunk: str, chunk_index: int) -> list[dict]:
        """
        Extract characters from a single chunk with retry logic.

        Args:
            chunk: Text chunk
            chunk_index: Index of chunk for tracking

        Returns:
            List of character dictionaries
        """
        prompt = f"""Extract all characters mentioned in this text. Include:
- Full name
- Gender (if identifiable)
- Pronouns used
- Brief description
- Any aliases or titles

Text:
{chunk}

Return as JSON list with fields: name, gender, pronouns, description, aliases"""

        for attempt in range(self.extraction_config["max_retries"]):
            try:
                response = await self._complete_with_retry(
                    prompt, temperature=self.extraction_config["temperature"]
                )

                characters = self._parse_json_response(response)

                # Add chunk metadata
                for char in characters:
                    char["chunk_index"] = chunk_index

                return characters

            except Exception as e:
                if attempt == self.extraction_config["max_retries"] - 1:
                    self.logger.error(f"Failed to extract from chunk {chunk_index}: {e}")
                    return []
                await asyncio.sleep(2**attempt)  # Exponential backoff

    # === GROUPING METHODS ===

    def _group_similar_characters(self, characters: list[dict]) -> list[list[dict]]:
        """
        Group potentially similar characters using Union-Find.
        O(n log n) complexity instead of O(n²).

        Args:
            characters: List of raw character dictionaries

        Returns:
            List of character groups
        """
        n = len(characters)
        if n == 0:
            return []

        uf = UnionFind(n)

        # Build name tokens index for efficient lookup
        name_tokens_index = {}
        for i, char in enumerate(characters):
            tokens = self._tokenize_name(char.get("name", ""))
            for token in tokens:
                if token not in name_tokens_index:
                    name_tokens_index[token] = []
                name_tokens_index[token].append(i)

        # Find similar characters efficiently
        for i, char in enumerate(characters):
            candidates = self._find_candidates(char, name_tokens_index, i)
            for j in candidates:
                if self._are_similar(characters[i], characters[j]):
                    uf.union(i, j)

        # Convert to groups
        group_indices = uf.get_groups()
        return [[characters[i] for i in group] for group in group_indices]

    def _tokenize_name(self, name: str) -> set[str]:
        """
        Tokenize name for similarity matching.

        Args:
            name: Character name

        Returns:
            Set of name tokens (lowercase)
        """
        # Remove titles and split on non-alphanumeric
        name = re.sub(r"\b(mr|mrs|ms|dr|prof|sir|lady|lord)\b\.?", "", name, flags=re.I)
        tokens = re.findall(r"\b\w+\b", name.lower())
        return set(tokens)

    def _find_candidates(self, char: dict, index: dict, char_idx: int) -> set[int]:
        """
        Find candidate characters for similarity comparison.

        Args:
            char: Character to find candidates for
            index: Name token index
            char_idx: Current character index

        Returns:
            Set of candidate indices
        """
        candidates = set()
        tokens = self._tokenize_name(char.get("name", ""))

        for token in tokens:
            if token in index:
                for idx in index[token]:
                    if idx != char_idx:
                        candidates.add(idx)

        return candidates

    def _are_similar(self, char1: dict, char2: dict) -> bool:
        """
        Check if two characters are similar enough to group.

        Args:
            char1: First character
            char2: Second character

        Returns:
            True if similar enough to group
        """
        name1_tokens = self._tokenize_name(char1.get("name", ""))
        name2_tokens = self._tokenize_name(char2.get("name", ""))

        # Check for exact match
        if name1_tokens == name2_tokens:
            return True

        # Check for subset relationship (one name contains the other)
        if name1_tokens.issubset(name2_tokens) or name2_tokens.issubset(name1_tokens):
            return True

        # Calculate Jaccard similarity
        if name1_tokens and name2_tokens:
            intersection = len(name1_tokens & name2_tokens)
            union = len(name1_tokens | name2_tokens)
            similarity = intersection / union
            return similarity >= self.grouping_config["similarity_threshold"]

        return False

    # === MERGING METHODS ===

    async def _merge_character_groups(self, groups: list[list[dict]]) -> list[Character]:
        """
        Use LLM to intelligently merge character groups.

        Args:
            groups: List of character groups

        Returns:
            List of final Character objects
        """
        final_characters = []

        for group in groups:
            if len(group) == 1:
                # Single character, no merging needed
                final_characters.append(self._dict_to_character(group[0]))
            else:
                # Need LLM to determine if these are the same character
                merged = await self._merge_group_with_llm(group)
                final_characters.append(merged)

        return final_characters

    async def _merge_group_with_llm(self, group: list[dict]) -> Character:
        """
        Use LLM to merge a group of potentially similar characters.

        Args:
            group: List of character dictionaries

        Returns:
            Merged Character object
        """
        # Prepare group for LLM
        group_desc = json.dumps(group, indent=2)

        prompt = f"""Analyze these character mentions and determine if they refer to the same person.
If they are the same, provide the canonical name and list any aliases.
If they are different people, keep them separate.

Character mentions:
{group_desc}

Return JSON with:
- is_same_person: boolean
- canonical_name: string (primary name if same person)
- aliases: list of strings (alternate names/titles)
- gender: string
- pronouns: string
- description: string (combined description)"""

        try:
            response = await self._complete_with_retry(
                prompt, temperature=self.merging_config["temperature"]
            )

            result = self._parse_json_response(response)

            if result.get("is_same_person", True):
                # Merge into single character
                return Character(
                    name=result.get("canonical_name", group[0].get("name", "Unknown")),
                    gender=self._parse_gender(result.get("gender")),
                    pronouns=result.get("pronouns", ""),
                    aliases=result.get("aliases", []),
                    description=result.get("description", ""),
                    importance="supporting",
                    confidence=0.8,
                )
            else:
                # Just return the first one (shouldn't happen often)
                return self._dict_to_character(group[0])

        except Exception as e:
            self.logger.warning(f"Failed to merge group: {e}")
            # Fallback: return the first character
            return self._dict_to_character(group[0])

    # === UTILITY METHODS ===

    async def _complete_with_retry(self, prompt: str, temperature: float = 0.7) -> str:
        """
        Complete prompt with exponential backoff retry.

        Args:
            prompt: Prompt to complete
            temperature: Temperature for completion

        Returns:
            Completion text
        """
        messages = [
            {"role": "system", "content": "You are a literary analysis expert."},
            {"role": "user", "content": prompt},
        ]

        for attempt in range(self.extraction_config["max_retries"]):
            try:
                response = await self.provider.complete(
                    messages, temperature=temperature, response_format="json_object"
                )
                return response

            except Exception as e:
                if attempt == self.extraction_config["max_retries"] - 1:
                    raise
                wait_time = 2**attempt
                self.logger.warning(f"Retry {attempt + 1} after {wait_time}s: {e}")
                await asyncio.sleep(wait_time)

    def _parse_json_response(self, response: str) -> Any:
        """
        Parse JSON response with multiple fallback strategies.

        Args:
            response: Response text to parse

        Returns:
            Parsed JSON object
        """
        # Strategy 1: Direct parse
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Strategy 2: Clean and parse
        try:
            cleaned = self._clean_json_text(response)
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Strategy 3: Extract JSON from markdown
        try:
            json_match = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
        except (json.JSONDecodeError, AttributeError):
            pass

        # Strategy 4: Find JSON-like content
        try:
            json_match = re.search(r"(\{.*\}|\[.*\])", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
        except (json.JSONDecodeError, AttributeError):
            pass

        # Strategy 5: Return empty structure
        self.logger.warning(f"Could not parse JSON from response: {response[:200]}...")
        return [] if "[" in response else {}

    def _clean_json_text(self, text: str) -> str:
        """
        Clean JSON text for parsing.

        Args:
            text: Text to clean

        Returns:
            Cleaned text
        """
        # Remove common issues
        text = text.strip()
        text = re.sub(r"^\s*```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)
        text = re.sub(r'(?<!\\)"(\w+)":\s*"([^"]*)"', r'"\1": "\2"', text)
        return text

    def _dict_to_character(self, char_dict: dict) -> Character:
        """
        Convert character dictionary to Character object.

        Args:
            char_dict: Character dictionary

        Returns:
            Character object
        """
        return Character(
            name=char_dict.get("name", "Unknown"),
            gender=self._parse_gender(char_dict.get("gender")),
            pronouns=char_dict.get("pronouns", ""),
            aliases=char_dict.get("aliases", []),
            description=char_dict.get("description", ""),
            importance="supporting",
            confidence=0.7,
        )

    def _parse_gender(self, gender_str: Optional[str]) -> Gender:
        """
        Parse gender string to Gender enum.

        Args:
            gender_str: Gender string

        Returns:
            Gender enum value
        """
        if not gender_str:
            return Gender.UNKNOWN

        gender_str = gender_str.lower()
        if "female" in gender_str or "woman" in gender_str:
            return Gender.FEMALE
        elif "male" in gender_str or "man" in gender_str:
            return Gender.MALE
        elif "non" in gender_str or "neutral" in gender_str:
            return Gender.NEUTRAL
        else:
            return Gender.UNKNOWN

    def _calculate_metadata(self, characters: list[Character]) -> dict[str, Any]:
        """
        Calculate metadata for character analysis.

        Args:
            characters: List of characters

        Returns:
            Metadata dictionary
        """
        gender_counts = {}
        importance_counts = {}

        for char in characters:
            # Count by gender
            gender_str = char.gender.value if hasattr(char.gender, "value") else str(char.gender)
            gender_counts[gender_str] = gender_counts.get(gender_str, 0) + 1

            # Count by importance
            importance_counts[char.importance] = importance_counts.get(char.importance, 0) + 1

        return {
            "total": len(characters),
            "by_gender": gender_counts,
            "by_importance": importance_counts,
        }
