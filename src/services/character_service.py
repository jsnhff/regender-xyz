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

from rapidfuzz import fuzz, process

from src.models.book import Book
from src.models.character import (
    Character,
    CharacterAnalysis,
    Gender,
    normalise_pronouns,
)
from src.providers.base import LLMProvider
from src.services.base import BaseService, ServiceConfig
from src.services.prompts import EXTRACTION_PROMPT_TEMPLATE, MERGE_PROMPT_TEMPLATE
from src.utils.errors import (
    CharacterExtractionError,
    ConfigurationError,
    ErrorHandler,
    ValidationError,
)


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


#: Words that stand in front of a name without being part of it, lowercased and
#: without the period, for reading a cast entry's shape.
_GROUPING_TITLES = frozenset(
    {
        "mr",
        "mrs",
        "ms",
        "mx",
        "miss",
        "madam",
        "sir",
        "lady",
        "lord",
        "dame",
        "noble",
        "colonel",
        "captain",
        "major",
        "general",
        "admiral",
        "lieutenant",
        "dr",
        "doctor",
        "reverend",
        "professor",
    }
)


#: Words that make a phrase a description of somebody rather than a name for
#: them. An alias containing one of these identifies nobody in particular:
#: "his wife" belongs to three women in the Pride and Prejudice cast.
_RELATION_WORDS = frozenset(
    {
        "mother",
        "father",
        "mamma",
        "mama",
        "papa",
        "parent",
        "son",
        "daughter",
        "child",
        "children",
        "brother",
        "sister",
        "sibling",
        "husband",
        "wife",
        "spouse",
        "uncle",
        "aunt",
        "niece",
        "nephew",
        "cousin",
        "widow",
        "bride",
        "friend",
        "eldest",
        "youngest",
        "elder",
        "younger",
        "ladyship",
        "lordship",
        "housekeeper",
        "butler",
        "waiter",
        "gardener",
        "chambermaid",
        "boy",
        "boys",
        "girl",
        "girls",
    }
)


#: How prominent a character is, most prominent first. Used to pick the higher
#: of two values when merging, and to read whatever word the model offered.
_IMPORTANCE_RANK = {"main": 3, "major": 3, "supporting": 2, "secondary": 2, "minor": 1}


def _importance_of(value: Any) -> str:
    """One of main/supporting/minor, from whatever the model said.

    This was hard-coded to "supporting" at both construction sites, so all ninety
    characters came out equally important: get_main_characters() returned nothing
    on every run, the interface's "Main characters" block never rendered, and the
    transform prompt described the whole cast in one undifferentiated list.
    """
    word = str(value or "").strip().lower()
    if word in _IMPORTANCE_RANK:
        return {3: "main", 2: "supporting", 1: "minor"}[_IMPORTANCE_RANK[word]]
    # A number is how some replies answer "importance"; 8 of 10 is a main part.
    try:
        score = float(word)
    except ValueError:
        return "supporting"
    if score >= 8:
        return "main"
    return "supporting" if score >= 4 else "minor"


def _is_name_form(alias: str) -> bool:
    """True when an alias names a person rather than describing one.

    Every token capitalised (titles and nobiliary particles excepted) and no
    relation word anywhere. "Darcy" and "Miss Lucas" qualify; "his wife", "her
    mother", "mamma" and "the eldest Miss Bennet" do not.
    """
    tokens = [t for t in alias.split() if t]
    if not tokens:
        return False
    for position, token in enumerate(tokens):
        bare = token.rstrip(".").lower()
        if bare in _RELATION_WORDS:
            return False
        if token[:1].isupper():
            continue
        if position and bare in {"de", "van", "von", "du", "del", "della", "di", "da", "la", "le"}:
            continue
        return False
    return True


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
        """Initialize service with validation."""
        super().__init__(config)
        self.provider = provider
        self.logger = logging.getLogger(__name__)
        self.error_handler = ErrorHandler(self.logger)

        # Load configuration from config.json or use defaults
        if config and hasattr(config, "character_extraction"):
            char_config = config.character_extraction
        else:
            # Load from config.json file
            config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
            if os.path.exists(config_path):
                with open(config_path) as f:
                    config_data = json.load(f)
                    char_config = config_data.get("character_extraction", {})
            else:
                char_config = {}

        # Set up configuration with defaults and validation
        self.extraction_config = {
            "chunk_size": char_config.get("chunk_size_tokens", 32000),
            "temperature": char_config.get("temperature", 0.0),
            "max_retries": 3,
            "retry_backoff": char_config.get("retry_backoff_seconds", 1.0),
        }

        # Chunks that named nobody even after every retry. A short cast used to
        # be indistinguishable from a short book, so the analysis could return
        # 77 characters one run and 91 the next with nothing anywhere saying a
        # chunk had been lost. Recorded so the run can say so.
        self.empty_chunks: list[int] = []

        # Said once per run, not once per call: a chunked book would otherwise
        # repeat it eighteen times.
        self._warned_forced_temperature = False

        # Validate chunk size
        if self.extraction_config["chunk_size"] <= 0:
            raise ConfigurationError(
                "Chunk size must be positive",
                config_key="chunk_size_tokens",
                details={"value": self.extraction_config["chunk_size"]},
            )
        if self.extraction_config["chunk_size"] > 100000:
            raise ConfigurationError(
                "Chunk size too large (max 100000)",
                config_key="chunk_size_tokens",
                details={"value": self.extraction_config["chunk_size"]},
            )

        self.grouping_config = {
            "algorithm": "union_find",
            "similarity_threshold": char_config.get("similarity_threshold", 0.8),
            "deduplication_similarity_threshold": char_config.get(
                "deduplication_similarity_threshold", 80
            ),
            "max_group_size": 20,
        }

        # Validate thresholds
        if not 0 <= self.grouping_config["deduplication_similarity_threshold"] <= 100:
            raise ConfigurationError(
                "Deduplication threshold must be between 0 and 100",
                config_key="deduplication_similarity_threshold",
                details={"value": self.grouping_config["deduplication_similarity_threshold"]},
            )

        self.merging_config = {
            "temperature": char_config.get("temperature", 0.0),
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
        Analyze characters in a book with input validation.

        Args:
            book: Book to analyze

        Returns:
            CharacterAnalysis with deduplicated characters

        Raises:
            ValidationError: If input is invalid
            CharacterExtractionError: If extraction fails
        """
        # Input validation
        if not book:
            raise ValidationError("Book cannot be None")

        if not isinstance(book, Book):
            raise ValidationError(
                f"Expected Book instance, got {type(book).__name__}", field="book"
            )

        # Validate book has content
        book_text = book.get_text()
        if not book_text or not book_text.strip():
            raise ValidationError(
                "Book has no content to analyze",
                field="book.text",
                details={"book_title": book.title or "Unknown"},
            )

        # Validate provider is initialized
        if not self.provider:
            raise ConfigurationError(
                "LLM provider not initialized",
                config_key="provider",
                details={"service": "CharacterService"},
            )

        try:
            self.logger.info(f"Starting character analysis for book: {book.title or 'Unknown'}")

            # Phase 1: Extract all character mentions
            self.empty_chunks = []
            raw_characters = await self._extract_all_characters(book_text)
            self.logger.info(f"Extracted {len(raw_characters)} raw character mentions")
            if self.empty_chunks:
                # Say it plainly. A cast short by a chunk used to look exactly
                # like a book with fewer people in it.
                self.logger.error(
                    f"{len(self.empty_chunks)} chunk(s) named nobody after every retry "
                    f"(chunk {', '.join(str(n) for n in self.empty_chunks)}); this cast is "
                    "incomplete and the run is not comparable to one that is"
                )

            # Phase 2: Group similar characters efficiently
            character_groups = self._group_similar_characters(raw_characters)
            self.logger.info(f"Created {len(character_groups)} character groups")

            # Phase 3: Merge groups using LLM
            final_characters = await self._merge_character_groups(character_groups)
            self.logger.info(f"Final character count: {len(final_characters)}")

            # Phase 4: one person, one entry.
            final_characters, merged = self._merge_same_person(final_characters)
            if merged:
                self.logger.info(
                    f"Merged {len(merged)} duplicate character entries: "
                    + "; ".join(f"{b} into {a}" for a, b in merged[:8])
                )

            # Create analysis result
            return CharacterAnalysis(
                book_id=book.hash(),  # Use book hash as ID
                characters=final_characters,
                metadata=self._calculate_metadata(final_characters),
            )

        except (ValidationError, CharacterExtractionError, ConfigurationError):
            # Re-raise our custom errors
            raise
        except Exception as e:
            # Convert unexpected errors
            error = self.error_handler.handle_error(e)
            self.error_handler.log_error(error)
            raise CharacterExtractionError(
                f"Character analysis failed: {str(e)}",
                details={"book_title": book.title or "Unknown"},
            ) from e

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

        # Memory management: limit characters to prevent unbounded growth
        max_characters = 1000
        seen_names = set()
        unique_characters = []

        # Process chunks with limited concurrency to avoid overwhelming the API
        # Use batch size of 1 for OpenAI to avoid rate limiting
        max_concurrent = 1 if "openai" in str(type(self.provider)).lower() else 3

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
                    # Early deduplication to prevent memory growth
                    for char in result:
                        char_name = char.get("name", "").lower().strip()
                        if char_name and char_name not in seen_names:
                            if len(unique_characters) < max_characters:
                                seen_names.add(char_name)
                                batch_characters.append(char)
                            else:
                                self.logger.debug(f"Character limit reached, skipping: {char_name}")

            return batch_characters

        # Process in batches with progress
        # Check if we're in a TTY/interactive environment
        disable_progress = not os.isatty(1) if hasattr(os, "isatty") else True

        try:
            from tqdm.asyncio import tqdm

            progress_bar = tqdm(
                total=len(chunks),
                desc="Extracting characters",
                disable=disable_progress,
                unit="chunk",
            )
        except ImportError:
            progress_bar = None

        for batch_start in range(0, len(chunks), max_concurrent):
            batch_end = min(batch_start + max_concurrent, len(chunks))
            batch_chunks = [(i, chunks[i]) for i in range(batch_start, batch_end)]

            self.logger.debug(f"Processing chunks {batch_start} to {batch_end - 1}")
            batch_results = await process_chunk_batch(batch_chunks)

            # Add unique characters and manage memory
            unique_characters.extend(batch_results)

            # Clear batch results to free memory
            del batch_results

            # Apply early deduplication if getting too large
            if len(unique_characters) > max_characters * 0.8:
                self.logger.debug(
                    f"Applying early deduplication at {len(unique_characters)} characters"
                )
                unique_characters = self._apply_early_deduplication(unique_characters)

            if progress_bar:
                progress_bar.update(batch_end - batch_start)

            # Add a small delay between batches to avoid rate limiting
            if batch_end < len(chunks):
                await asyncio.sleep(1)

        if progress_bar:
            progress_bar.close()

        # Clear chunks from memory
        del chunks

        self.logger.info(
            f"Extracted {len(unique_characters)} unique characters (deduped from {len(seen_names)} names)"
        )
        return unique_characters

    def _apply_early_deduplication(self, characters: list[dict]) -> list[dict]:
        """Apply early deduplication to prevent memory overflow."""
        name_groups = {}
        for char in characters:
            name = char.get("name", "").strip()
            if name:
                if name not in name_groups:
                    name_groups[name] = char
                else:
                    # Keep the one with more details
                    existing = name_groups[name]
                    if len(str(char.get("description", ""))) > len(
                        str(existing.get("description", ""))
                    ):
                        name_groups[name] = char
        return list(name_groups.values())

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
        # Use memory-efficient approach with chunk limit
        max_chunks = 100  # Limit chunks to prevent excessive memory usage
        chunks = []

        # Process text line by line to avoid loading all words at once
        lines = text.splitlines()
        current_chunk = []
        current_chars = 0

        for line in lines:
            if len(chunks) >= max_chunks:
                self.logger.warning(f"Reached maximum chunk limit ({max_chunks}), truncating text")
                break

            words = line.split()
            for word in words:
                word_len = len(word) + 1  # +1 for space
                if current_chars + word_len > chars_per_chunk and current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []
                    current_chars = 0

                    if len(chunks) >= max_chunks:
                        break

                current_chunk.append(word)
                current_chars += word_len

        if current_chunk and len(chunks) < max_chunks:
            chunks.append(" ".join(current_chunk))

        # Clear intermediate variables
        del lines
        del current_chunk

        self.logger.info(
            f"Created {len(chunks)} chunks of ~{chunk_size} tokens ({chars_per_chunk} chars) each"
        )
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

        attempts = max(1, self.extraction_config["max_retries"])
        for attempt in range(attempts):
            try:
                response = await self._complete_with_retry(
                    prompt, temperature=self.extraction_config["temperature"]
                )

                characters = self._parse_json_response(response, strict=True)

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

                # A chunk of a novel holds people. Coming back with none is a
                # reply that went wrong -- a refusal, a preamble, a truncation --
                # and it used to end the loop as a success.
                if not valid_chars:
                    raise ValueError("parsed, but named no characters")

                return valid_chars

            except Exception as e:
                if attempt == attempts - 1:
                    self.logger.error(
                        f"Chunk {chunk_index} named no characters after {attempts} "
                        f"attempts: {e}. The cast for this run is short by whoever "
                        f"first appears in it."
                    )
                    self.empty_chunks.append(chunk_index)
                    return []
                # Exponential backoff. Scaled by a configured factor so a test
                # exercising the retry path does not have to wait out the real
                # one; three seconds a case is how a fast suite stops being run.
                await asyncio.sleep(self.extraction_config.get("retry_backoff", 1.0) * 2**attempt)

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

    def _find_best_matches(
        self, name: str, candidates: list[str], threshold: int = 80
    ) -> list[tuple[str, float, int]]:
        """
        Find best matching names from candidates using rapidfuzz.

        Args:
            name: Name to match
            candidates: List of candidate names
            threshold: Minimum similarity score (0-100)

        Returns:
            List of (name, score, index) tuples for matches above threshold
        """
        if not candidates:
            return []

        # Use rapidfuzz's extract to get best matches
        # Returns list of (match, score, index) tuples
        matches = process.extract(
            name, candidates, scorer=fuzz.token_set_ratio, limit=None, score_cutoff=threshold
        )

        return matches

    def _are_similar(self, char1: dict, char2: dict) -> bool:
        """
        Check if two characters are similar enough to group using rapidfuzz.

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
        # First, normalize by removing periods from abbreviations
        normalized1 = name1.replace(".", "")
        normalized2 = name2.replace(".", "")

        parts1 = normalized1.split()
        parts2 = normalized2.split()

        if len(parts1) >= 2 and len(parts2) >= 2:
            # Both have at least first and last name
            # Check if these might be family members (different first name, same last name)
            first1 = parts1[0].lower()
            first2 = parts2[0].lower()
            last1 = parts1[-1].lower()
            last2 = parts2[-1].lower()

            # Skip titles when comparing. Two gaps here made this guard reject
            # every duplicate in the book. "miss" was missing from the set, and
            # Pride and Prejudice's cast is full of Miss Bennets; and the skip
            # only applied when a name had three tokens, so for the two-token
            # "Mr. Darcy" the title itself was compared as the first name --
            # against "Fitzwilliam", which differs, with the same surname, which
            # reads as a sibling. On the real 90-entry cast this produced 90
            # groups and not one pair, so the merge phase after it had nothing to
            # do. "Anne de Bourgh" against "Miss Anne de Bourgh" scored a perfect
            # 100 and was still rejected.
            titles = {
                "dr",
                "mr",
                "mrs",
                "ms",
                "mx",
                "miss",
                "prof",
                "sir",
                "lady",
                "lord",
                "dame",
                "madam",
                "colonel",
                "captain",
                "major",
                "general",
                "reverend",
            }
            titled1 = first1 in titles
            titled2 = first2 in titles
            behind1 = parts1[1:] if titled1 else parts1
            behind2 = parts2[1:] if titled2 else parts2

            # Two titled forms of one surname, with different titles, are two
            # people: Mr. and Mrs. Bennet are husband and wife, and so are the
            # Hursts, the Gardiners, the Philipses and the Wickhams. Grouping
            # them asks the merge step a question it should never be asked.
            if (
                titled1
                and titled2
                and len(behind1) == 1
                and len(behind2) == 1
                and behind1[0].lower() == behind2[0].lower()
                and first1 != first2
            ):
                self.logger.debug(f"Not grouping a married pair: {name1} vs {name2}")
                return False

            # "Mr. Darcy" and "Fitzwilliam Darcy" are one man, but they are NOT
            # grouped here, deliberately. Grouping is transitive, so calling that
            # pair similar also pulls in every other Darcy through the title
            # form, and the whole Bennet family arrives in one group -- seven
            # people the merge step is then asked about as a single question,
            # with a wrong "yes" collapsing a family. That pair is settled
            # deterministically instead, in _merge_same_person, where a title
            # form is folded into a given name only when exactly one person of
            # that gender carries the surname.
            if titled1 and len(parts1) > 1:
                first1 = parts1[1].lower()
            if titled2 and len(parts2) > 1:
                first2 = parts2[1].lower()

            if first1 != first2 and last1 == last2:
                # Different first names, same last name - likely family members
                self.logger.debug(f"Not merging family members: {name1} vs {name2}")
                return False

        # Get similarity threshold from config
        threshold = self.grouping_config.get("deduplication_similarity_threshold", 80)

        # Use rapidfuzz for advanced fuzzy matching
        # Token set ratio handles out-of-order tokens well (e.g., "Jekyll Dr." vs "Dr. Jekyll")
        token_set_ratio = fuzz.token_set_ratio(name1, name2)
        if token_set_ratio >= threshold:
            return True

        # Partial ratio for substring matching (e.g., "Elizabeth" vs "Elizabeth Bennet")
        partial_ratio = fuzz.partial_ratio(name1.lower(), name2.lower())
        if partial_ratio >= 95:  # Higher threshold for partial matches
            # Additional check: ensure the shorter name is actually contained
            if len(name1) < len(name2):
                if name1.lower() in name2.lower():
                    return True
            elif name2.lower() in name1.lower():
                return True

        # Token sort ratio for reordered names (e.g., "Bennet, Elizabeth" vs "Elizabeth Bennet")
        token_sort_ratio = fuzz.token_sort_ratio(name1, name2)
        # Slightly higher threshold for the reordered form
        return token_sort_ratio >= threshold + 5

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
                final_characters.extend(await self._merge_group_with_llm(group))

        return final_characters

    async def _merge_group_with_llm(self, group: list[dict]) -> list[Character]:
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

            # Every path that is not a merge keeps the whole group. Returning
            # only the first member deleted the rest of the cast: asked whether
            # Jane Bennet and Lydia Bennet are the same person, a correct "no"
            # removed Lydia from the book. So did a 529 from the provider, and
            # so did a reply in a shape this code did not expect. Not merging is
            # the safe answer to an uncertain question; deleting is not.
            unmerged = [self._dict_to_character(member) for member in group]

            # Handle both object and array responses
            if isinstance(result, list):
                # If LLM returned an array, take the first item
                if result:
                    result = result[0]
                else:
                    return unmerged

            # Ensure result is a dict
            if not isinstance(result, dict):
                self.logger.warning(f"Unexpected result type: {type(result)}")
                return unmerged

            # Absent means unanswered, and an unanswered question must not
            # collapse a group. This defaulted to True, so a reply that omitted
            # the field merged people the model had not said were one.
            if result.get("is_same_person") is not True:
                if "is_same_person" not in result:
                    self.logger.warning(
                        "Merge reply did not say whether these are one person; "
                        f"keeping all {len(group)} separate: "
                        + ", ".join(m.get("name", "?") for m in group)
                    )
                return unmerged

            # Merge into single character
            return [
                Character(
                    name=result.get("canonical_name", group[0].get("name", "Unknown")),
                    gender=self._parse_gender(result.get("gender")),
                    pronouns=normalise_pronouns(result.get("pronouns"))
                    # The merged reply may omit pronouns; the members had them.
                    or next(
                        (p for p in (normalise_pronouns(m.get("pronouns")) for m in group) if p),
                        {},
                    ),
                    titles=result.get("titles") or group[0].get("titles", []),
                    aliases=result.get("aliases", []),
                    description=result.get("description", ""),
                    importance=_importance_of(
                        result.get("importance")
                        or max(
                            (m.get("importance") for m in group if m.get("importance")),
                            default=None,
                            key=lambda v: _IMPORTANCE_RANK.get(str(v).lower(), 0),
                        )
                    ),
                    confidence=0.8,
                )
            ]

        except Exception as e:
            self.logger.warning(f"Failed to merge group, keeping all members separate: {e}")
            return [self._dict_to_character(member) for member in group]

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

                # Some models like gpt-5-mini only support temperature=1.0.
                # Say so rather than substituting in silence: reading a cast is
                # a task that wants no sampling at all, and a run that could not
                # have it should not look like a run that did.
                model_name = getattr(self.provider, "model", "")
                if "gpt-5-mini" in model_name or "gpt-5-nano" in model_name:
                    if temperature != 1.0 and not self._warned_forced_temperature:
                        self._warned_forced_temperature = True
                        self.logger.warning(
                            f"{model_name} accepts only temperature 1.0, so the configured "
                            f"{temperature} cannot be used. This cast will vary between runs; "
                            "a model that honours temperature 0 will not."
                        )
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

    def _parse_json_response(self, response: str, strict: bool = False) -> Any:
        """
        Parse JSON response with multiple fallback strategies.

        Args:
            response: Response text to parse
            strict: Raise instead of returning an empty structure when nothing
                could be parsed. Character extraction needs this: the empty
                fallback is indistinguishable from a chunk that really held no
                characters, so a refusal, a truncated reply or a paragraph of
                prose all read as a successful extraction of nobody -- and the
                retry loop above never ran, because a fallback is not an
                exception. One silent chunk out of eighteen costs three to eight
                characters, which is the whole of the run-to-run spread.

        Returns:
            Parsed JSON object

        Raises:
            ValueError: only when strict and no strategy could parse the reply.
        """
        if not response or not response.strip():
            self.logger.warning("Empty response received")
            if strict:
                raise ValueError("empty response")
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
            json_match = re.search(
                r"(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}|\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\])",
                response,
                re.DOTALL,
            )
            if json_match:
                result = json.loads(json_match.group(1))
                return result
        except (json.JSONDecodeError, AttributeError) as e:
            self.logger.debug(f"JSON extraction failed: {e}")

        # Strategy 5: Try to fix common issues and parse
        try:
            # Remove everything before first { or [
            start_idx = min(
                response.find("{") if "{" in response else len(response),
                response.find("[") if "[" in response else len(response),
            )
            if start_idx < len(response):
                trimmed = response[start_idx:]
                # Find matching close
                if trimmed[0] == "{":
                    end_idx = trimmed.rfind("}")
                    if end_idx > 0:
                        trimmed = trimmed[: end_idx + 1]
                else:
                    end_idx = trimmed.rfind("]")
                    if end_idx > 0:
                        trimmed = trimmed[: end_idx + 1]

                cleaned = self._clean_json_text(trimmed)
                result = json.loads(cleaned)
                return result
        except Exception as e:
            self.logger.debug(f"Advanced extraction failed: {e}")

        # Final fallback: Return empty structure with proper format
        self.logger.warning(f"Could not parse JSON from response: {response[:200]}...")
        if strict:
            raise ValueError(f"could not parse a reply of {len(response)} characters")
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
        text = re.sub(r"}\s*\n\s*{", "},\n{", text)
        text = re.sub(r"\]\s*\n\s*\[", "],\n[", text)

        # Fix trailing commas (not allowed in JSON)
        text = re.sub(r",\s*}", "}", text)
        text = re.sub(r",\s*]", "]", text)
        text = re.sub(r",\s*,", ",", text)  # Remove double commas

        # Fix incomplete strings at the end (truncation issue)
        if text.count('"') % 2 != 0:
            # Odd number of quotes, likely truncated
            # Try to close the last string and array/object
            if "..." in text[-10:]:
                text = re.sub(r"\.\.\..*$", '"}]', text)
            elif text.rstrip().endswith(","):
                text = text.rstrip()[:-1] + "}]"
            else:
                # Determine what needs closing
                open_braces = text.count("{") - text.count("}")
                open_brackets = text.count("[") - text.count("]")
                closing = '"'
                closing += "}" * open_braces
                closing += "]" * open_brackets
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
            pronouns=normalise_pronouns(char_dict.get("pronouns")),
            titles=char_dict.get("titles", []),
            aliases=char_dict.get("aliases", []),
            description=char_dict.get("description", ""),
            importance=_importance_of(char_dict.get("importance")),
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

    # Titles that stand in place of a given name, so a character called only
    # "Mrs. Bennet" has no name of their own to carry across.
    _TITLES = frozenset({"mr.", "mrs.", "ms.", "miss", "mx.", "lady", "lord", "sir", "dame"})

    _TITLE_FOR = {
        "all_male": "Mr.",
        "all_female": "Mrs.",
        "nonbinary": "Mx.",
    }

    #: For gender_swap there is no single destination title: each one crosses to
    #: the other side. Leaving this out returned no collisions at all for the
    #: swap -- 73 characters changing, nothing checked -- which is how "Miss
    #: Darcy" came to be renamed onto her own brother's form.
    _SWAPPED_TITLE = {
        "mr.": "Mrs.",
        "mrs.": "Mr.",
        "miss": "Mr.",
        "ms.": "Mr.",
        "mx.": "Mx.",
        "lady": "Lord",
        "lord": "Lady",
        "sir": "Lady",
        "dame": "Sir",
    }

    @classmethod
    def _landing_for(cls, form: str, transform_type) -> Optional[str]:
        """Where a title-and-surname form lands, or None if it is not one."""
        parts = form.split()
        if len(parts) != 2 or parts[0].lower() not in cls._TITLES:
            return None
        variant = getattr(transform_type, "value", "")
        title = cls._TITLE_FOR.get(variant)
        if title is None:
            if variant != "gender_swap":
                return None
            title = cls._SWAPPED_TITLE.get(parts[0].lower())
            if title is None:
                return None
        return f"{title} {parts[1]}"

    @classmethod
    def _name_collisions(cls, characters, changing, transform_type) -> dict:
        """Characters whose transformed name is already somebody else's.

        A woman known only as "Mrs. Bennet" has no given name, so an all_male
        transform can only swap her title -- and lands her on Mr. Bennet, who
        is her husband. Eight of Pride and Prejudice's cast do this. Nothing
        downstream can separate them afterwards: one name, two people.

        Forms of address are counted as well as cast names, because that is
        where most of these live. Charlotte Collins is listed under her full
        name, so nothing titled was ever examined for her -- yet the book calls
        her "Mrs. Collins" forty times, and in an all-male edition that lands
        exactly on her husband. The alias expansion used to paper over this by
        quietly renaming "Mrs. Collins" to a bare given name, which cost the
        book its honorifics; the collision belongs here, where it can be put to
        the reader and answered once.
        """
        taken: dict[str, str] = {}
        for char in characters.characters:
            for form in [char.name, *(char.aliases or [])]:
                taken.setdefault(form.lower(), char.name)

        # Where each title-and-surname form would land, by the character it
        # belongs to. A character may own several: "Mrs. Collins" and "Miss
        # Lucas" are both Charlotte.
        landing: dict[str, str] = {}
        for char in changing:
            for form in [char.name, *(char.aliases or [])]:
                destination = cls._landing_for(form, transform_type)
                if destination and form not in landing:
                    landing[form] = destination

        # A form whose owner is also changing is not a clash: both move.
        changing_names = {c.name for c in changing}

        collisions = {}
        for form, candidate in landing.items():
            owner = taken.get(candidate.lower())
            if owner and owner not in (taken.get(form.lower()), form) and owner in changing_names:
                # The owner is moving too, so ask where they land instead.
                owner_forms = [f for f, d in landing.items() if taken.get(f.lower()) == owner]
                if any(landing[f] != candidate for f in owner_forms):
                    owner = None
            if owner and owner != taken.get(form.lower()) and owner != form:
                collisions[form] = {"candidate": candidate, "clashes_with": owner}
                continue
            # Two characters can also land on each other rather than on someone
            # already there: Lady Lucas and Miss Lucas both become Mr. Lucas,
            # and no existing man is involved.
            others = [
                f
                for f, d in landing.items()
                if d == candidate and taken.get(f.lower()) != taken.get(form.lower())
            ]
            if others:
                collisions[form] = {"candidate": candidate, "clashes_with": others[0]}
        return collisions

    @staticmethod
    def _merge_same_person(characters: list) -> tuple:
        """Fold entries that are the same person into one.

        The extraction lists a person once by name and again by title, and a
        third time under a married surname: "Lydia Bennet", "Lydia Wickham" and
        "Mrs. Wickham" are one woman. Each entry is then renamed on its own, so
        she came out of an all_male run as Lionel 182 times and Lyle once. The
        naming can only be consistent if the cast is.

        Only entries that name each other are merged. Guessing from a shared
        surname would fold a mother into her daughter.
        """
        by_name = {c.name: c for c in characters}
        parent: dict[str, str] = {}

        def root(name: str) -> str:
            while parent.get(name, name) != name:
                name = parent[name]
            return name

        # Two entries that answer to the same short name are one person --
        # unless their given names differ, in which case the short name is
        # ambiguous and they are two.
        #
        # "Mr. Darcy" and "Fitzwilliam Darcy" both list the alias "Darcy".
        # Neither names the other, so nothing folded them, and the protagonist's
        # suitor was two cast entries: the gender-swap edition called one
        # "Frances Darcy" and the other "Mrs. Fitzwillia Darcy". One has no given
        # name and the other does, so there is nothing to contradict.
        #
        # The guard matters as much as the rule. "Charlotte Lucas" and "Maria
        # Lucas" both list the alias "Miss Lucas", and they are sisters.
        #
        # Structure cannot settle every case: "Mrs. Bennet" and "Jane Bennet"
        # are mother and daughter, share a surname and a gender, and only the
        # honorific says which is which. Where it cannot be known, nothing is
        # merged and the map audit raises the pair for a person to answer.
        def _behind_titles(name: str) -> list:
            parts = [part for part in name.split() if part]
            while parts and parts[0].rstrip(".").lower() in _GROUPING_TITLES:
                parts.pop(0)
            return parts

        def given_of(name: str) -> Optional[str]:
            parts = _behind_titles(name)
            return parts[0].lower() if len(parts) > 1 else None

        def surname_of(name: str) -> Optional[str]:
            parts = _behind_titles(name)
            return parts[-1].lower() if parts else None

        claimants: dict[str, list] = {}
        for char in characters:
            for alias in getattr(char, "aliases", []) or []:
                if alias in by_name:
                    continue  # the alias-names-an-entry rule below covers this
                if not _is_name_form(alias):
                    # A relation is not an identity. "his wife" is listed for
                    # Mrs. Bennet, Mrs. Wickham and Harriet Forster, and taking
                    # it as a shared name chained six different women into one
                    # person -- Mrs. Bennet, Lydia Bennet, Lydia Wickham, Mrs.
                    # Wickham, Harriet Harrington and Mrs. Forster all folded
                    # into Harriet Forster.
                    continue
                claimants.setdefault(alias.lower(), []).append(char)

        for sharers in claimants.values():
            if len(sharers) < 2:
                continue
            first = sharers[0]
            for other in sharers[1:]:
                if first.gender != other.gender:
                    continue
                given_a, given_b = given_of(first.name), given_of(other.name)
                if given_a and given_b and given_a != given_b:
                    continue  # two people who share a form of address
                surname_a, surname_b = surname_of(first.name), surname_of(other.name)
                if surname_a and surname_b and surname_a != surname_b:
                    # Harriet Forster and Harriet Harrington both answer to
                    # "Harriet" and are two women. A married name crossing
                    # surnames -- Lydia Bennet to Lydia Wickham -- is only ever
                    # merged on the stronger evidence of one entry naming the
                    # other, which the rule below does.
                    continue
                a, b = root(first.name), root(other.name)
                if a == b:
                    continue
                # The form carrying a given name makes the better canonical one.
                if given_of(a) and not given_of(b):
                    keep, fold = a, b
                elif given_of(b) and not given_of(a):
                    keep, fold = b, a
                else:
                    keep, fold = sorted((a, b), key=lambda n: (-len(by_name[n].aliases or []), n))
                parent[fold] = keep

        for char in characters:
            for alias in getattr(char, "aliases", []) or []:
                other = by_name.get(alias)
                if other is None or other.name == char.name:
                    continue
                if other.gender != char.gender:
                    continue  # a different person who happens to be named here
                a, b = root(char.name), root(other.name)
                if a != b:
                    # The entry carrying more aliases is the better-known form
                    # and makes the better canonical name; ties go alphabetical
                    # so a run is reproducible.
                    keep, fold = sorted((a, b), key=lambda n: (-len(by_name[n].aliases or []), n))
                    parent[fold] = keep

        if not parent:
            return characters, []

        merged = []
        out = []
        for char in characters:
            target = root(char.name)
            if target == char.name:
                out.append(char)
                continue
            merged.append((target, char.name))
            canonical = by_name[target]
            names = list(canonical.aliases or [])
            for extra in [char.name, *(char.aliases or [])]:
                if extra != canonical.name and extra not in names:
                    names.append(extra)
            canonical.aliases = names
        return out, merged

    # Neutrality was one hedged clause -- "gender-neutral where possible" --
    # against three firm ones about tradition, rhythm and period, plus the name
    # engine's "keep the first letter". For a Regency cast those combine to
    # produce Elizabeth -> Edmund: three rules obeyed and the fourth quietly
    # dropped. The fix is to make neutrality the requirement, release the
    # first letter, and hand over a pool that is genuinely period-attested
    # rather than leaving the model to invent or approximate.
    _NONBINARY_NAMING = """
- THE NAME MUST READ AS NEITHER MASCULINE NOR FEMININE. This outranks matching
  the rhythm, the register, or the first letter of the original. A name most
  readers would class as a man's or a woman's name is wrong here, however well
  it echoes the original: "Elizabeth" -> "Edmund" is a failure, not a
  compromise.
- Do NOT keep the first letter if doing so costs neutrality.
- Prefer names genuinely used across genders in English before 1850. Among
  them: Francis, Frances, Evelyn, Hilary, Vivian, Meredith, Jocelyn, Sidney,
  Leslie, Valentine, Clare, Cyril, Aubrey, Shirley, Beverly, Carol, Dana,
  Esme, Laurie, Morgan, Quincy, Reilly, Sydney. Shirley and Evelyn were men's
  names in this period and women's later, which is exactly the quality wanted.
- Do NOT use modern unisex coinages (Rowan, Sage, River, Phoenix). They are
  neutral but break the period, which is as wrong as breaking the neutrality.
- A surname used as a given name (Bennet, Darcy, Fitzwilliam) is period-plausible
  and neutral, and is a good answer when no given name fits."""

    async def suggest_name_alternatives(
        self,
        characters: CharacterAnalysis,
        transform_type: Any,
        style_context: str = "",
        steer: str = "",
    ) -> list[dict[str, str]]:
        """Suggest gender-appropriate name alternatives for characters whose gender changes.

        Returns list of dicts: [{"original": ..., "suggested": ..., "character_id": ...}]
        Only returns characters whose gender actually changes for this transform type.

        A character with no given name of their own is given one wherever the
        title swap alone would merge them with somebody else, so the interface
        can offer it and the reader can change it.
        """
        from src.models.transformation import TransformType

        if isinstance(transform_type, str):
            try:
                transform_type = TransformType(transform_type)
            except ValueError:
                return []

        # Determine which characters need name changes
        chars_needing_changes = []
        for char in characters.characters:
            gender_val = char.gender.value if hasattr(char.gender, "value") else str(char.gender)
            needs_change = False

            if (
                transform_type == TransformType.ALL_FEMALE
                and gender_val == "male"
                or transform_type == TransformType.ALL_MALE
                and gender_val == "female"
                or transform_type == TransformType.GENDER_SWAP
                and gender_val in ("male", "female")
                or transform_type == TransformType.NONBINARY
                and gender_val in ("male", "female")
            ):
                needs_change = True

            if needs_change:
                chars_needing_changes.append(char)

        if not chars_needing_changes:
            return []

        collisions = self._name_collisions(characters, chars_needing_changes, transform_type)

        # Build character list for prompt
        char_lines = []
        for char in chars_needing_changes:
            gender_val = char.gender.value if hasattr(char.gender, "value") else str(char.gender)
            note = ""
            if char.name in collisions:
                clash = collisions[char.name]
                note = (
                    f" — NEEDS A GIVEN NAME: swapping the title alone gives "
                    f'"{clash["candidate"]}", which is also {clash["clashes_with"]}'
                )
            char_lines.append(f'  - name: "{char.name}", gender: {gender_val}{note}')
        char_list_str = "\n".join(char_lines)

        style_note = f"\nStyle context: {style_context}" if style_context else ""
        neutral_note = self._NONBINARY_NAMING if transform_type == TransformType.NONBINARY else ""
        # What the reader said about the last set. Their words, put where the
        # model will weigh them against the rules rather than under them.
        steer_note = (
            f"\n\nThe reader has seen a previous set of suggestions and asked for "
            f"this: {steer}\nTreat it as the most important instruction here."
            if steer
            else ""
        )

        prompt = f"""You are a literary name consultant. For a gender-transformed version of a book, suggest new names for characters whose gender is changing.

Transform type: {transform_type.value}
Characters needing new names:
{char_list_str}{style_note}

Rules:
- Suggest names from the same cultural/ethnic tradition as the original
- Match the rhythm and feel of the original name (similar syllables, similar register)
- Keep the era/period appropriate (Victorian names stay Victorian, etc.)
- For titles like "Sir [Name]": use "Dame [Name]" for female equivalents; for "Mr." use "Ms." or "Mrs."
- Do NOT change family surnames — only given names and honorific titles
- If the character HAS a given name, that given name must CHANGE. Changing only
  the title is not an answer: "Sir William Lucas" -> "Noble William Lucas" leaves
  a man's name in place and will be rejected. Give them a new given name and keep
  the surname: "Sir William Lucas" -> "Noble Vivian Lucas".
- A character marked NEEDS A GIVEN NAME has none of their own, so swapping the
  title would merge them with an existing character. Give them a period-appropriate
  given name and return the full form, e.g. "Mrs. Bennet" -> "Mr. Thomas Bennet".
  The given name must not already belong to anyone in the book.
{neutral_note}
- Return a JSON array only, no other text:
[{{"original": "original name here", "suggested": "suggested name here", "character_id": "original name here"}}]

Return ONLY the JSON array.{steer_note}"""

        try:
            response = await self._complete_with_retry(prompt, temperature=0.5)
            parsed = self._parse_json_response(response)

            # Handle both list and dict responses
            if isinstance(parsed, dict):
                for key in ("suggestions", "names", "characters", "results"):
                    if isinstance(parsed.get(key), list):
                        parsed = parsed[key]
                        break
                else:
                    return []

            if not isinstance(parsed, list):
                return []

            # Validate and clean each entry
            from src.services.name_engine import cast_name_index, check_rename

            # What the cast already is. Without it the check has to guess from
            # the shape of a name whether "Sir William" names a man called
            # William or the Lucas family, and whether "Jane" is free.
            cast_surnames, cast_givens, reserved = cast_name_index(characters)

            result = []
            for item in parsed:
                if not isinstance(item, dict):
                    continue
                original = str(item.get("original", "")).strip()
                suggested = str(item.get("suggested", "")).strip()
                character_id = str(item.get("character_id", original)).strip()
                if original and suggested and original != suggested:
                    # A suggestion the reader approves becomes the book's name and
                    # overrides the engine, so it has to clear the same bar the
                    # engine's own proposals clear. It used to clear none: "Sir
                    # William Lucas" -> "Noble William Lucas" changed the title,
                    # left the masculine given name, and was offered as a valid
                    # nonbinary name. A suggestion that fails here is not shown;
                    # the character falls through to the engine, which has the
                    # period-attested pool and will choose.
                    problem = check_rename(
                        original,
                        suggested,
                        surnames=cast_surnames,
                        givens=cast_givens,
                        reserved=reserved,
                    )
                    if problem:
                        self.logger.warning(
                            f"Dropped name suggestion {original!r} -> {suggested!r}: {problem}"
                        )
                        continue
                    entry = {
                        "original": original,
                        "suggested": suggested,
                        "character_id": character_id,
                    }
                    # Say why, for the ones where it matters. Most suggestions
                    # are a matter of taste; these are the ones that stop two
                    # characters becoming one person.
                    clash = collisions.get(original)
                    if clash:
                        entry["reason"] = f"otherwise both are {clash['candidate']}"
                    result.append(entry)

            return result

        except Exception:
            return []
