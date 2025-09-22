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
import os
import re
from typing import Any, Optional

from src.models.book import Book
from src.models.character import Character, CharacterAnalysis, Gender
from src.providers.base import LLMProvider
from src.services.base import BaseService, ServiceConfig
from src.services.prompts import EXTRACTION_PROMPT_TEMPLATE, MERGE_PROMPT_TEMPLATE


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

        # Load configuration from simple config
        from src.simple_config import config as app_config

        self.extraction_config = {
            "chunk_size": app_config.character_chunk_size,
            "temperature": app_config.character_temperature,
            "max_retries": app_config.max_retries,
        }
        self.grouping_config = {
            "algorithm": "union_find",
            "similarity_threshold": app_config.similarity_threshold,
            "max_group_size": 20,
        }
        self.merging_config = {
            "temperature": app_config.character_temperature,
            "timeout": 30,
            "batch_size": 50,
        }

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
        # Make chunking async-safe to avoid blocking
        chunks = await asyncio.to_thread(self._create_chunks, text)
        raw_characters = []

        # Process chunks with limited concurrency to avoid overwhelming the API
        # Use batch size of 1 for OpenAI to avoid rate limiting
        max_concurrent = 1 if 'openai' in str(type(self.provider)).lower() else 3

        async def process_chunk_batch(batch_chunks: list[tuple[int, str]]):
            """Process a batch of chunks concurrently."""
            tasks = []
            for i, chunk in batch_chunks:
                tasks.append(self._extract_from_chunk(chunk, i))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            batch_characters = []
            for i, result in enumerate(results):
                chunk_idx = batch_chunks[i][0]
                if isinstance(result, Exception):
                    self.logger.warning(f"Failed to extract from chunk {chunk_idx}: {result}")
                else:
                    batch_characters.extend(result)

            return batch_characters

        # Process in batches with progress
        # Check if we're in a TTY/interactive environment
        disable_progress = not os.isatty(1) if hasattr(os, 'isatty') else True

        try:
            from tqdm.asyncio import tqdm
            progress_bar = tqdm(
                total=len(chunks),
                desc="Extracting characters",
                disable=disable_progress,
                unit="chunk"
            )
        except ImportError:
            progress_bar = None

        for batch_start in range(0, len(chunks), max_concurrent):
            batch_end = min(batch_start + max_concurrent, len(chunks))
            batch_chunks = [(i, chunks[i]) for i in range(batch_start, batch_end)]

            self.logger.debug(f"Processing chunks {batch_start} to {batch_end-1}")
            batch_results = await process_chunk_batch(batch_chunks)
            raw_characters.extend(batch_results)

            if progress_bar:
                progress_bar.update(batch_end - batch_start)

            # Add a small delay between batches to avoid rate limiting
            if batch_end < len(chunks):
                await asyncio.sleep(1)

        if progress_bar:
            progress_bar.close()

        return raw_characters

    def _create_chunks(self, text: str, chunk_size: int = None) -> list[str]:
        """
        Split text into manageable chunks.

        Args:
            text: Text to chunk
            chunk_size: Approximate size of each chunk in tokens

        Returns:
            List of text chunks
        """
        # Use configured chunk size if not specified
        if chunk_size is None:
            chunk_size = self.extraction_config.get("chunk_size", 2000)

        # Better tokenization approximation:
        # GPT models use ~1.3 chars per token for English text
        # So we need chunk_size * 1.3 characters per chunk
        chars_per_chunk = int(chunk_size * 1.3)

        # Split text into chunks by character count, respecting word boundaries
        chunks = []
        words = text.split()
        current_chunk = []
        current_chars = 0

        for word in words:
            word_len = len(word) + 1  # +1 for space
            if current_chars + word_len > chars_per_chunk and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_chars = 0
            current_chunk.append(word)
            current_chars += word_len

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        self.logger.info(f"Created {len(chunks)} chunks of ~{chunk_size} tokens ({chars_per_chunk} chars) each")
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
        prompt = EXTRACTION_PROMPT_TEMPLATE.format(text=chunk)

        for attempt in range(self.extraction_config["max_retries"]):
            try:
                response = await self._complete_with_retry(
                    prompt, temperature=self.extraction_config["temperature"]
                )

                characters = self._parse_json_response(response)

                # Handle different response formats
                if isinstance(characters, dict):
                    # Expected format: {"characters": [...]}
                    characters = characters.get("characters", [])
                elif not isinstance(characters, list):
                    # Unexpected format
                    self.logger.warning(f"Unexpected response type: {type(characters)}")
                    characters = []

                # Validate and add metadata
                valid_chars = []
                for char in characters:
                    if isinstance(char, dict) and char.get("name"):
                        # Ensure required fields
                        char.setdefault("gender", "unknown")
                        char.setdefault("pronouns", "")
                        char.setdefault("description", "")
                        char.setdefault("aliases", [])
                        char.setdefault("titles", [])
                        char["chunk_index"] = chunk_index
                        valid_chars.append(char)

                return valid_chars

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
        name1 = char1.get("name", "")
        name2 = char2.get("name", "")

        # Don't merge if both have first and last names but first names differ
        # This prevents merging "Elizabeth Bennet" with "Jane Bennet"
        parts1 = name1.split()
        parts2 = name2.split()

        if len(parts1) >= 2 and len(parts2) >= 2:
            # Both have at least first and last name
            if parts1[0].lower() != parts2[0].lower() and parts1[-1].lower() == parts2[-1].lower():
                # Different first names, same last name - likely family members
                self.logger.debug(f"Not merging family members: {name1} vs {name2}")
                return False

        name1_tokens = self._tokenize_name(name1)
        name2_tokens = self._tokenize_name(name2)

        # Check for exact match
        if name1_tokens == name2_tokens:
            return True

        # Be more careful with subset relationships
        # "Elizabeth" should match "Elizabeth Bennet" but not "Jane Bennet"
        if name1_tokens.issubset(name2_tokens) or name2_tokens.issubset(name1_tokens):
            # Only merge if it's clearly the same person
            if len(name1_tokens) == 1 and len(name2_tokens) <= 2:
                # Like "Elizabeth" and "Elizabeth Bennet"
                return True

        # Calculate Jaccard similarity with stricter threshold
        if name1_tokens and name2_tokens:
            intersection = len(name1_tokens & name2_tokens)
            union = len(name1_tokens | name2_tokens)
            similarity = intersection / union
            # Use stricter threshold (0.8 instead of 0.7) to avoid over-merging
            return similarity >= 0.8

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

        prompt = MERGE_PROMPT_TEMPLATE.format(characters=group_desc)

        try:
            response = await self._complete_with_retry(
                prompt, temperature=self.merging_config["temperature"]
            )

            result = self._parse_json_response(response)

            # Handle both object and array responses
            if isinstance(result, list):
                # If LLM returned an array, take the first item
                if result:
                    result = result[0]
                else:
                    # Empty array, use first from group
                    return self._dict_to_character(group[0])

            # Ensure result is a dict
            if not isinstance(result, dict):
                self.logger.warning(f"Unexpected result type: {type(result)}")
                return self._dict_to_character(group[0])

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
                # Only use JSON mode if provider supports it
                # Our new prompts already explicitly request JSON
                kwargs = {}

                # Some models like gpt-5-mini only support temperature=1.0
                # Check if the model has this limitation
                model_name = getattr(self.provider, 'model', '')
                if 'gpt-5-mini' in model_name or 'gpt-5-nano' in model_name:
                    # These models only support temperature=1.0
                    kwargs["temperature"] = 1.0
                else:
                    kwargs["temperature"] = temperature

                if hasattr(self.provider, "supports_json") and self.provider.supports_json:
                    # For providers that support JSON mode, use it
                    kwargs["response_format"] = "json_object"

                response = await self.provider.complete(messages, **kwargs)
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
        if not response or not response.strip():
            self.logger.warning("Empty response received")
            return {"characters": []}

        # Strategy 1: Direct parse
        try:
            result = json.loads(response)
            return result
        except json.JSONDecodeError as e:
            self.logger.debug(f"Direct parse failed: {e}")

        # Strategy 2: Clean and parse
        try:
            cleaned = self._clean_json_text(response)
            result = json.loads(cleaned)
            return result
        except json.JSONDecodeError as e:
            self.logger.debug(f"Cleaned parse failed: {e}")

        # Strategy 3: Extract JSON from markdown
        try:
            # Look for code blocks
            json_match = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(1))
                return result
        except (json.JSONDecodeError, AttributeError) as e:
            self.logger.debug(f"Markdown extraction failed: {e}")

        # Strategy 4: Find JSON-like content
        try:
            # More precise regex for JSON objects/arrays
            json_match = re.search(r"(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}|\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\])", response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(1))
                return result
        except (json.JSONDecodeError, AttributeError) as e:
            self.logger.debug(f"JSON extraction failed: {e}")

        # Strategy 5: Try to fix common issues and parse
        try:
            # Remove everything before first { or [
            start_idx = min(
                response.find('{') if '{' in response else len(response),
                response.find('[') if '[' in response else len(response)
            )
            if start_idx < len(response):
                trimmed = response[start_idx:]
                # Find matching close
                if trimmed[0] == '{':
                    end_idx = trimmed.rfind('}')
                    if end_idx > 0:
                        trimmed = trimmed[:end_idx + 1]
                else:
                    end_idx = trimmed.rfind(']')
                    if end_idx > 0:
                        trimmed = trimmed[:end_idx + 1]

                cleaned = self._clean_json_text(trimmed)
                result = json.loads(cleaned)
                return result
        except Exception as e:
            self.logger.debug(f"Advanced extraction failed: {e}")

        # Final fallback: Return empty structure with proper format
        self.logger.warning(f"Could not parse JSON from response: {response[:200]}...")
        return {"characters": []}

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

        # Remove markdown code blocks
        text = re.sub(r"^\s*```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)

        # Remove any text before/after JSON
        text = re.sub(r"^[^{\[]*", "", text)  # Remove text before JSON
        text = re.sub(r"[}\]][^}\]]*$", lambda m: m.group(0)[0], text)  # Keep only last } or ]

        # Fix missing commas between array elements (common LLM error)
        text = re.sub(r'"\s*\n\s*"', '",\n"', text)
        text = re.sub(r'}\s*\n\s*{', '},\n{', text)
        text = re.sub(r'\]\s*\n\s*\[', '],\n[', text)

        # Fix trailing commas (not allowed in JSON)
        text = re.sub(r',\s*}', '}', text)
        text = re.sub(r',\s*]', ']', text)
        text = re.sub(r',\s*,', ',', text)  # Remove double commas

        # Fix incomplete strings at the end (truncation issue)
        if text.count('"') % 2 != 0:
            # Odd number of quotes, likely truncated
            # Try to close the last string and array/object
            if '...' in text[-10:]:
                text = re.sub(r'\.\.\..*$', '"}]', text)
            elif text.rstrip().endswith(','):
                text = text.rstrip()[:-1] + '}]'
            else:
                # Determine what needs closing
                open_braces = text.count('{') - text.count('}')
                open_brackets = text.count('[') - text.count(']')
                closing = '"'
                closing += '}' * open_braces
                closing += ']' * open_brackets
                text += closing

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
