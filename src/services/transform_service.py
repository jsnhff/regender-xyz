"""
Transform Service

This service handles gender transformation of books.
"""

import asyncio
import difflib
import os
import re
import time
from typing import Any, Optional

from src.models.book import Book, Chapter
from src.models.character import CharacterAnalysis
from src.models.transformation import (
    Transformation,
    TransformationChange,
    TransformType,
)
from src.providers.base import LLMProvider
from src.services.base import BaseService, ServiceConfig
from src.services.prompts import TRANSFORM_BATCH_PROMPT_TEMPLATE, TRANSFORM_SIMPLE_PROMPT_TEMPLATE
from src.strategies.transform import SmartTransformStrategy, TransformStrategy
from src.utils.errors import (
    ConfigurationError,
    ErrorHandler,
    TransformationError,
    ValidationError,
)
from src.utils.token_manager import TokenManager

from .character_service import CharacterService


class TransformService(BaseService):
    """
    Service for gender transformation.

    This service:
    - Transforms books based on gender rules
    - Maintains consistency across the text
    - Tracks all changes made
    - Supports various transformation types
    """

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        character_service: Optional[CharacterService] = None,
        strategy: Optional[TransformStrategy] = None,
        config: Optional[ServiceConfig] = None,
        token_manager: Optional[TokenManager] = None,
    ):
        """
        Initialize transform service with validation.

        Args:
            provider: LLM provider for transformations
            character_service: Service for character analysis
            strategy: Transformation strategy
            config: Service configuration
            token_manager: Token manager for consistent estimation
        """
        self.provider = provider
        self.character_service = character_service
        self.strategy = strategy or self._get_default_strategy()
        self.token_manager = token_manager
        self.error_handler = ErrorHandler()
        super().__init__(config)

    def _initialize(self):
        """Initialize transformation resources."""
        self.transformation_cache = {}

        # Initialize token manager if not provided
        if not self.token_manager:
            if self.provider:
                provider_name = getattr(self.provider, "name", "openai")
                model_name = getattr(self.provider, "model", None)
                self.token_manager = TokenManager.for_provider(provider_name, model_name)
            else:
                self.token_manager = TokenManager()  # Default to GPT-4

        self.logger.info(f"Using TokenManager for {self.token_manager.config.name}")
        self.logger.info(f"Initialized {self.__class__.__name__}")

    def _get_default_strategy(self) -> TransformStrategy:
        """Get default transformation strategy."""
        return SmartTransformStrategy()

    async def process(self, data: dict[str, Any]) -> Transformation:
        """
        Transform a book's gender representation with validation.

        Args:
            data: Dictionary containing:
                - book: Book object
                - transform_type: TransformType or string
                - characters: Optional CharacterAnalysis

        Returns:
            Transformation result

        Raises:
            ValidationError: If input is invalid
        """
        # Validate input data structure
        if not data:
            raise ValidationError("Input data cannot be None")
        if not isinstance(data, dict):
            raise ValidationError(f"Expected dict, got {type(data).__name__}")

        # Extract and validate book
        book = data.get("book")
        if not book:
            raise ValidationError("'book' is required", field="book")
        if not isinstance(book, Book):
            raise ValidationError(
                f"'book' must be a Book object, got {type(book).__name__}", field="book"
            )

        # Extract and validate transform type
        transform_type = data.get("transform_type")
        if not transform_type:
            raise ValidationError("'transform_type' is required", field="transform_type")

        if isinstance(transform_type, str):
            try:
                transform_type = TransformType(transform_type)
            except ValueError as e:
                raise ValidationError(
                    f"Invalid transform type: {transform_type}",
                    field="transform_type",
                    details={"valid_types": [t.value for t in TransformType]},
                ) from e
        elif not isinstance(transform_type, TransformType):
            raise ValidationError(
                f"'transform_type' must be a TransformType or string, got {type(transform_type).__name__}",
                field="transform_type",
            )

        # Optional characters validation
        characters = data.get("characters")
        if characters and not isinstance(characters, CharacterAnalysis):
            raise ValidationError(
                f"'characters' must be a CharacterAnalysis object if provided, got {type(characters).__name__}",
                field="characters",
            )

        return await self.transform_book(book, transform_type, characters)

    async def transform_book(
        self,
        book: Book,
        transform_type: TransformType,
        characters: Optional[CharacterAnalysis] = None,
        selected_characters: Optional[list[str]] = None,
        name_map: Optional[dict[str, str]] = None,
        on_chapter_complete: Optional[Any] = None,
    ) -> Transformation:
        """
        Transform a book with the specified transformation type.

        Args:
            book: Book to transform
            transform_type: Type of transformation
            characters: Pre-analyzed characters (optional)
            selected_characters: Specific characters to transform (optional)
            name_map: Optional mapping of original character names to replacement names

        Returns:
            Transformation object with results

        Raises:
            ValidationError: If input is invalid
            TransformationError: If transformation fails
        """
        # Input validation
        if not book:
            raise ValidationError("Book cannot be None")

        if not isinstance(book, Book):
            raise ValidationError(
                f"Expected Book instance, got {type(book).__name__}", field="book"
            )

        # Validate book has content
        if not book.chapters or len(book.chapters) == 0:
            raise ValidationError(
                "Book has no chapters to transform",
                field="book.chapters",
                details={"book_title": book.title or "Unknown"},
            )

        # Validate provider
        if not self.provider:
            raise ConfigurationError(
                "LLM provider not initialized",
                config_key="provider",
                details={"service": "TransformService"},
            )

        # Validate transform type
        if not isinstance(transform_type, TransformType):
            raise ValidationError(
                f"Invalid transform type: {transform_type}", field="transform_type"
            )

        # Validate selected characters if provided
        if selected_characters is not None:
            if not isinstance(selected_characters, list):
                raise ValidationError(
                    f"selected_characters must be a list, got {type(selected_characters).__name__}",
                    field="selected_characters",
                )
            if not all(isinstance(char, str) for char in selected_characters):
                raise ValidationError(
                    "All selected characters must be strings", field="selected_characters"
                )

        start_time = time.time()

        try:
            # Get character analysis if not provided
            if not characters:
                if not self.character_service:
                    raise ConfigurationError(
                        "Character service required when characters not provided",
                        config_key="character_service",
                    )

                self.logger.info("Analyzing characters...")
                characters = await self.character_service.process(book)

            # Create transformation context
            context = self._create_context(characters, transform_type, selected_characters)

            # Auto-expand name_map with character aliases so nicknames are caught.
            # Best-effort: depends on the character service detecting aliases consistently.
            if name_map and characters:
                expanded = self._expand_name_map_with_aliases(name_map, characters)
                if len(expanded) > len(name_map):
                    self.logger.info(
                        f"Expanded name_map with {len(expanded) - len(name_map)} character aliases"
                    )
                name_map = expanded

            # Transform chapters
            self.logger.info(f"Transforming {len(book.chapters)} chapters...")
            transformed_chapters, all_changes = await self._transform_chapters(
                book.chapters, context, name_map=name_map, on_chapter_complete=on_chapter_complete
            )

            # Create transformation result
            transformation = Transformation(
                original_book=book,
                transformed_chapters=transformed_chapters,
                transform_type=transform_type,
                characters_used=characters,
                changes=all_changes,
                metadata={
                    "provider": self.provider.name if self.provider else "mock",
                    "strategy": self.strategy.__class__.__name__,
                    "processing_time": time.time() - start_time,
                },
            )

            self.logger.info(
                f"Transformation complete: {len(all_changes)} changes in "
                f"{time.time() - start_time:.1f}s"
            )

            return transformation

        except (ValidationError, TransformationError, ConfigurationError):
            # Re-raise our custom errors
            raise
        except Exception as e:
            # Convert unexpected errors
            error = self.error_handler.handle_error(e)
            self.error_handler.log_error(error)
            raise TransformationError(
                f"Transformation failed: {str(e)}",
                transform_type=transform_type.value,
                details={
                    "book_title": book.title or "Unknown",
                    "processing_time": time.time() - start_time,
                },
            ) from e

    def _create_context(
        self,
        characters: CharacterAnalysis,
        transform_type: TransformType,
        selected_characters: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Create transformation context.

        Args:
            characters: Character analysis
            transform_type: Transformation type

        Returns:
            Context dictionary for transformation
        """
        # Get transformation rules based on type
        rules = self._get_transformation_rules(transform_type)

        # Create character mappings
        character_mappings = {}
        characters_to_transform = []
        characters_to_preserve = []

        for char in characters.characters:
            # Check if this character should be transformed
            should_transform = selected_characters is None or char.name in selected_characters

            if should_transform:
                mappings = self._get_character_transformation(char, transform_type)
                character_mappings[char.name] = mappings
                for alias in char.aliases:
                    character_mappings[alias] = mappings
                characters_to_transform.append(char.name)
            else:
                # Preserve original gender
                mappings = {
                    "original_gender": char.gender,
                    "new_gender": char.gender,
                    "pronouns": char.pronouns,
                    "preserve": True,
                }
                character_mappings[char.name] = mappings
                for alias in char.aliases:
                    character_mappings[alias] = mappings
                characters_to_preserve.append(char.name)

        # Create context string for selective transformation
        character_context = self._create_selective_context_string(
            characters, characters_to_transform, characters_to_preserve
        )

        return {
            "transform_type": transform_type,
            "rules": rules,
            "characters": characters,
            "character_mappings": character_mappings,
            "character_context": character_context,
            "characters_to_transform": characters_to_transform,
            "characters_to_preserve": characters_to_preserve,
        }

    def _build_character_instructions(
        self,
        characters: Optional[CharacterAnalysis],
        transform_type: TransformType,
        character_mappings: dict,
    ) -> str:
        """Build character context for LLM transformation."""
        if not characters:
            return ""

        lines = ["\nKNOWN CHARACTERS:"]

        # Build compact character list with their transformations
        for char in characters.characters:
            if char.name not in character_mappings:
                continue

            mapping = character_mappings[char.name]
            current_gender = (
                char.gender.value if hasattr(char.gender, "value") else str(char.gender)
            )

            # Determine target gender based on transform type
            if mapping.get("preserve", False):
                target = "KEEP UNCHANGED"
            elif transform_type == TransformType.GENDER_SWAP:
                if current_gender == "male":
                    target = "→female"
                elif current_gender == "female":
                    target = "→male"
                else:
                    target = "→swap"
            elif transform_type == TransformType.ALL_FEMALE:
                target = "→female"
            elif transform_type == TransformType.ALL_MALE:
                target = "→male"
            elif transform_type == TransformType.NONBINARY:
                target = "→they/them"
            else:
                target = "→transform"

            # Compact format: Name (aliases) [current→target]
            name_str = char.name
            if char.aliases:
                name_str += f" (aka {', '.join(char.aliases[:3])})"  # Limit to 3 aliases
            lines.append(f"- {name_str}: {current_gender}{target}")

        lines.append(
            "\nApply these specific character transformations consistently throughout the text."
        )

        return "\n".join(lines)

    def _create_selective_context_string(
        self, characters: CharacterAnalysis, to_transform: list[str], to_preserve: list[str]
    ) -> str:
        """Create context string for selective transformation."""
        lines = []

        if to_transform:
            lines.append("Characters to transform:")
            for name in to_transform:
                char = next((c for c in characters.characters if c.name == name), None)
                if char:
                    lines.append(f"  - {name}: {char.gender.value} -> swap gender")

        if to_preserve:
            lines.append("\nCharacters to preserve (DO NOT change):")
            for name in to_preserve:
                char = next((c for c in characters.characters if c.name == name), None)
                if char:
                    lines.append(f"  - {name}: keep as {char.gender.value}")

        if not lines:
            return characters.create_context_string()

        return "\n".join(lines)

    def _get_transformation_rules(self, transform_type: TransformType) -> dict[str, Any]:
        """Get transformation rules for the specified type."""
        if transform_type == TransformType.ALL_MALE:
            return {
                "target_gender": "male",
                "pronouns": {"she": "he", "her": "him", "hers": "his"},
                "titles": {"Mrs.": "Mr.", "Ms.": "Mr.", "Miss": "Mr."},
                "terms": {
                    "mother": "father",
                    "daughter": "son",
                    "sister": "brother",
                    "wife": "husband",
                    "queen": "king",
                    "lady": "lord",
                },
            }
        elif transform_type == TransformType.ALL_FEMALE:
            return {
                "target_gender": "female",
                "pronouns": {"he": "she", "him": "her", "his": "hers"},
                "titles": {"Mr.": "Ms."},
                "terms": {
                    "father": "mother",
                    "son": "daughter",
                    "brother": "sister",
                    "husband": "wife",
                    "king": "queen",
                    "lord": "lady",
                },
            }
        elif transform_type == TransformType.GENDER_SWAP:
            return {
                "swap": True,
                "pronouns": {
                    "he": "she",
                    "she": "he",
                    "him": "her",
                    "her": "him",
                    "his": "hers",
                    "hers": "his",
                },
                "titles": {"Mr.": "Ms.", "Mrs.": "Mr.", "Ms.": "Mr.", "Miss": "Mr."},
                "terms": {
                    "father": "mother",
                    "mother": "father",
                    "son": "daughter",
                    "daughter": "son",
                    "brother": "sister",
                    "sister": "brother",
                    "husband": "wife",
                    "wife": "husband",
                    "king": "queen",
                    "queen": "king",
                    "lord": "lady",
                    "lady": "lord",
                },
            }
        elif transform_type == TransformType.NONBINARY:
            return {
                "target_gender": "nonbinary",
                "pronouns": {
                    "he": "they",
                    "she": "they",
                    "him": "them",
                    "her": "them",
                    "his": "their",
                    "hers": "theirs",
                    "himself": "themself",
                    "herself": "themself",
                },
                "titles": {"Mr.": "Mx.", "Mrs.": "Mx.", "Ms.": "Mx.", "Miss": "Mx."},
                "terms": {
                    "mother": "parent",
                    "father": "parent",
                    "son": "child",
                    "daughter": "child",
                    "brother": "sibling",
                    "sister": "sibling",
                    "husband": "spouse",
                    "wife": "spouse",
                    "king": "monarch",
                    "queen": "monarch",
                    "lord": "noble",
                    "lady": "noble",
                },
            }
        else:
            return {}

    def _get_character_transformation(self, character, transform_type: TransformType) -> dict:
        """Get transformation info for a specific character - let LLM handle the actual transformation."""
        mappings = {
            "original_gender": character.gender,
            "name": character.name,
            "aliases": character.aliases,
        }

        # Just track whether to transform or preserve - let LLM handle the actual transformation
        current_gender = (
            character.gender.value if hasattr(character.gender, "value") else str(character.gender)
        )

        if transform_type == TransformType.GENDER_SWAP:
            # LLM will swap genders
            mappings["transform"] = True
        elif transform_type in [
            TransformType.ALL_MALE,
            TransformType.ALL_FEMALE,
            TransformType.NONBINARY,
        ]:
            # LLM will apply the transformation type
            mappings["transform"] = True
        else:
            # Keep original
            mappings["preserve"] = True

        return mappings

    async def _transform_chapters(
        self,
        chapters: list[Chapter],
        context: dict[str, Any],
        name_map: Optional[dict[str, str]] = None,
        on_chapter_complete: Optional[Any] = None,
    ) -> tuple[list[Chapter], list[TransformationChange]]:
        """
        Transform chapters with the given context.

        Args:
            chapters: Chapters to transform
            context: Transformation context

        Returns:
            Tuple of (transformed chapters, list of changes)
        """
        # Check if we should use parallel processing
        use_parallel = len(chapters) > 2 and self.config.async_enabled and self.provider

        if use_parallel:
            return await self._transform_chapters_parallel(
                chapters, context, name_map=name_map, on_chapter_complete=on_chapter_complete
            )
        else:
            return await self._transform_chapters_sequential(
                chapters, context, name_map=name_map, on_chapter_complete=on_chapter_complete
            )

    async def _transform_chapters_sequential(
        self,
        chapters: list[Chapter],
        context: dict[str, Any],
        name_map: Optional[dict[str, str]] = None,
        on_chapter_complete: Optional[Any] = None,
    ) -> tuple[list[Chapter], list[TransformationChange]]:
        """Transform chapters sequentially with rate limiting."""
        transformed_chapters = []
        all_changes = []

        # Use rate limiter for OpenAI
        rate_limiter = None
        if self.provider and "openai" in self.provider.name.lower():
            from src.providers.rate_limiter import OpenAIRateLimiter

            rate_limiter = OpenAIRateLimiter(tier=self.config.rate_limit_tier)
            self.logger.info(f"Using OpenAI rate limiter for {len(chapters)} chapters")

        total = len(chapters)
        for i, chapter in enumerate(chapters):
            # Apply rate limiting if needed
            if rate_limiter:
                # Estimate tokens based on chapter content using TokenManager
                chapter_text = " ".join([p.get_text() for p in chapter.paragraphs])
                estimated_tokens = min(self.token_manager.estimate_tokens(chapter_text), 4500)
                await rate_limiter.acquire(estimated_tokens)

                # Track token usage
                self.token_manager.track_usage(
                    input_tokens=estimated_tokens,
                    provider=self.provider.name if self.provider else "unknown",
                )

            self.logger.debug(f"Transforming chapter {i + 1}/{total}")

            transformed_chapter, changes = await self._transform_single_chapter(
                chapter, i, context, name_map=name_map
            )

            transformed_chapters.append(transformed_chapter)
            all_changes.extend(changes)

            # Notify progress
            if on_chapter_complete:
                on_chapter_complete(i + 1, total, chapter.title or f"Chapter {i + 1}")
            elif (i + 1) % 5 == 0:
                self.logger.info(f"Progress: {i + 1}/{total} chapters transformed")

        return transformed_chapters, all_changes

    async def _transform_chapters_parallel(
        self,
        chapters: list[Chapter],
        context: dict[str, Any],
        name_map: Optional[dict[str, str]] = None,
        on_chapter_complete: Optional[Any] = None,
    ) -> tuple[list[Chapter], list[TransformationChange]]:
        """Transform chapters in parallel with rate limiting."""

        # For OpenAI, force sequential processing due to rate limits
        if self.provider and "openai" in self.provider.name.lower():
            self.logger.info("OpenAI detected - using sequential processing for rate limiting")
            return await self._transform_chapters_sequential(
                chapters, context, name_map=name_map, on_chapter_complete=on_chapter_complete
            )

        total = len(chapters)
        completed = 0

        async def run_chapter(chapter, i):
            nonlocal completed
            result = await self._transform_single_chapter(chapter, i, context, name_map=name_map)
            completed += 1
            if on_chapter_complete:
                on_chapter_complete(completed, total, chapter.title or f"Chapter {i + 1}")
            return result

        semaphore = asyncio.Semaphore(self.config.max_concurrent)

        async def limited_task(chapter, i):
            async with semaphore:
                return await run_chapter(chapter, i)

        results = await asyncio.gather(*[limited_task(ch, i) for i, ch in enumerate(chapters)])

        transformed_chapters = []
        all_changes = []
        for transformed_chapter, changes in results:
            transformed_chapters.append(transformed_chapter)
            all_changes.extend(changes)

        return transformed_chapters, all_changes

    async def _transform_single_chapter(
        self,
        chapter: Chapter,
        chapter_index: int,
        context: dict[str, Any],
        name_map: Optional[dict[str, str]] = None,
    ) -> tuple[Chapter, list[TransformationChange]]:
        """
        Transform a single chapter.

        Args:
            chapter: Chapter to transform
            chapter_index: Index of the chapter
            context: Transformation context
            name_map: Optional mapping of original names to replacement names

        Returns:
            Tuple of (transformed chapter, list of changes)
        """
        from src.models.book import Chapter, Paragraph
        from src.models.transformation import TransformationChange

        # Require LLM provider for transformation
        if not self.provider:
            raise ValueError(
                "LLM provider is required for transformation. Please configure an LLM provider (OpenAI or Anthropic)."
            )

        # Use LLM for transformation
        changes = []
        transformed_paragraphs = []

        # Apply rate limiting if needed
        if self.provider and "openai" in self.provider.name.lower():
            from src.providers.rate_limiter import OpenAIRateLimiter

            rate_limiter = OpenAIRateLimiter(tier=self.config.rate_limit_tier)

            # Estimate tokens for the chapter using TokenManager
            chapter_text = " ".join([p.get_text() for p in chapter.paragraphs])
            estimated_tokens = min(self.token_manager.estimate_tokens(chapter_text), 4500)
            await rate_limiter.acquire(estimated_tokens)

            # Track token usage
            self.token_manager.track_usage(
                input_tokens=estimated_tokens,
                provider=self.provider.name if self.provider else "unknown",
            )

        # Transform paragraphs in token-optimized batches
        from src.utils.config import config as app_config

        # Get batches optimized by token count
        batches = self._create_token_optimized_batches(chapter.paragraphs, context)
        total_paragraphs = len(chapter.paragraphs)
        total_batches = len(batches)

        avg_batch_size = sum(len(b) for b in batches) / len(batches) if batches else 0
        self.logger.info(
            f"Processing {total_paragraphs} paragraphs in {total_batches} token-optimized batches (avg size: {avg_batch_size:.1f})"
        )

        # Setup progress bar
        disable_progress = not os.isatty(1) if hasattr(os, "isatty") else True
        try:
            from tqdm import tqdm

            progress_bar = tqdm(
                total=total_batches,
                desc=f"Transforming {chapter.title or 'chapter'}",
                disable=disable_progress,
                unit="batch",
            )
        except ImportError:
            progress_bar = None

        transform_type = context.get("transform_type", TransformType.GENDER_SWAP)
        batch_start = 0
        for batch_num, batch_paragraphs in enumerate(batches, 1):
            batch_end = batch_start + len(batch_paragraphs)

            if not progress_bar:
                self.logger.info(
                    f"Processing batch {batch_num}/{total_batches} (paragraphs {batch_start + 1}-{batch_end}, ~{self._estimate_batch_tokens(batch_paragraphs, context)} tokens)"
                )
            else:
                progress_bar.set_postfix({"paragraphs": f"{batch_start + 1}-{batch_end}"})

            # Create batch prompt with the actual paragraph objects
            prompt = self._create_batch_transform_prompt(
                batch_paragraphs, context, len(batch_paragraphs)
            )

            try:
                # Call LLM for batch
                messages = [
                    {"role": "system", "content": prompt["system"]},
                    {"role": "user", "content": prompt["user"]},
                ]

                response = await self.provider.complete(
                    messages=messages,
                    temperature=self.config.llm_temperature,
                )

                # Split response by paragraph markers
                transformed_texts = self._parse_batch_response(response, len(batch_paragraphs))

                # Process each paragraph in the batch
                for i, (paragraph, transformed_text) in enumerate(
                    zip(batch_paragraphs, transformed_texts)
                ):
                    para_idx = batch_start + i
                    original_text = paragraph.get_text()

                    # Debug logging for first paragraph
                    if para_idx == 0:
                        self.logger.debug(f"Original text: {repr(original_text[:100])}")
                        self.logger.debug(f"Transformed text: {repr(transformed_text[:100])}")

                    # Apply name substitutions after LLM transform
                    if name_map:
                        transformed_text = self._apply_name_map(transformed_text, name_map)

                    # Apply deterministic term substitutions (safety net for LLM misses).
                    # original_text lets the substitution skip words the LLM already
                    # transformed, which a bidirectional swap map would otherwise undo.
                    transformed_text = self._apply_term_map(
                        transformed_text, transform_type, source_text=original_text
                    )

                    # Track changes
                    if transformed_text != original_text:
                        changes.append(
                            TransformationChange(
                                chapter_index=chapter_index,
                                paragraph_index=para_idx,
                                sentence_index=0,
                                original=original_text,
                                transformed=transformed_text,
                                change_type="gender_swap",
                            )
                        )

                    # Create transformed paragraph
                    transformed_paragraphs.append(Paragraph(sentences=[transformed_text]))

                # Update batch_start for next iteration
                batch_start = batch_end

                # Update progress
                if progress_bar:
                    progress_bar.update(1)

            except Exception as e:
                self.logger.warning(
                    f"Batch {batch_num}/{total_batches} failed ({e}), retrying at sentence level..."
                )
                retry_results = await self._retry_at_sentence_level(
                    batch_paragraphs, context, name_map, transform_type
                )
                transformed_paragraphs.extend(retry_results)
                batch_start = batch_end

        # Close progress bar
        if progress_bar:
            progress_bar.close()

        # Final term_map pass over all paragraphs — catches any that couldn't be
        # LLM-transformed (e.g. batches that failed retry). Each output paragraph is
        # compared against its source so already-transformed words are left alone;
        # a paragraph that fell back to its original text aligns wholly and gets the
        # full deterministic transform.
        for i, para in enumerate(transformed_paragraphs):
            current_text = para.get_text()
            source_text = chapter.paragraphs[i].get_text() if i < len(chapter.paragraphs) else None
            fixed_text = self._apply_term_map(current_text, transform_type, source_text=source_text)
            if fixed_text != current_text:
                transformed_paragraphs[i] = Paragraph(sentences=[fixed_text])

        # Create transformed chapter
        transformed_chapter = Chapter(
            number=chapter.number, title=chapter.title, paragraphs=transformed_paragraphs
        )

        return transformed_chapter, changes

    def _apply_name_map(self, text: str, name_map: dict[str, str]) -> str:
        """Apply case-aware name substitutions in a single simultaneous pass.

        Single-pass matters for two reasons: name maps can contain cycles
        (Elizabeth->Elias, Elias->Elizabeth) that sequential replacement would
        collapse onto one name, and word boundaries stop "Ann" from rewriting
        the inside of "Anne".
        """
        if not name_map:
            return text
        pattern, lookup = self._compile_substitution(tuple(sorted(name_map.items())))
        return pattern.sub(lambda m: self._match_case(m.group(0), lookup[m.group(0).lower()]), text)

    _WORD_RE = re.compile(r"[A-Za-z']+")

    # Word boundaries that also break on "_", so gendered words wrapped in the
    # italic markup the exporters use ("_her_") are still matched. Python's \b
    # counts "_" as a word character and skips them entirely.
    _BOUNDARY_BEFORE = r"(?<![A-Za-z'])"
    _BOUNDARY_AFTER = r"(?![A-Za-z'])"

    # Derived-once caches for the static term maps.
    _EFFECTIVE_TERM_MAPS: dict[str, dict[str, str]] = {}
    _GENDERED_NOUNS: dict[str, frozenset] = {}
    _GENDERED_VOCABULARY: dict[str, frozenset] = {}
    _COMPILED_SUBSTITUTIONS: dict[tuple, tuple] = {}

    # Gendered terms that the LLM occasionally misses — keyed by transform type.
    # ALL_MALE maps female→male; ALL_FEMALE maps male→female; GENDER_SWAP includes both.
    _TERM_MAPS: dict[str, dict[str, str]] = {
        "all_male": {
            # Familial / relational (also serves as fallback for timed-out batches)
            "mother": "father",
            "daughter": "son",
            "sister": "brother",
            "wife": "husband",
            "aunt": "uncle",
            "niece": "nephew",
            "grandmother": "grandfather",
            "granddaughter": "grandson",
            "widow": "widower",
            "maiden": "bachelor",
            "spinster": "bachelor",
            "woman": "man",
            "girl": "boy",
            "female": "male",
            "lass": "lad",
            # Social / aristocratic
            "queen": "king",
            "princess": "prince",
            "duchess": "duke",
            "countess": "count",
            "baroness": "baron",
            "empress": "emperor",
            "abbess": "abbot",
            "lady": "lord",
            "ladyship": "lordship",
            "dame": "sir",
            "heroine": "hero",
            "bride": "groom",
            "marchioness": "marquess",
            "viscountess": "viscount",
            # Occupational / address
            "mistress": "master",
            "madam": "sir",
            "maid": "manservant",
            "governess": "tutor",
            "housekeeper": "steward",
            "landlady": "landlord",
            "actress": "actor",
            "hostess": "host",
            "waitress": "waiter",
            "barmaid": "barman",
            "authoress": "author",
            "poetess": "poet",
            "murderess": "murderer",
            "shepherdess": "shepherd",
            "huntress": "hunter",
            "handmaid": "page",
            "handmaiden": "page",
            "gentlewoman": "gentleman",
            # Religious / mythological
            "nun": "monk",
            "witch": "warlock",
            "prophetess": "prophet",
            "priestess": "priest",
            "enchantress": "enchanter",
            "sorceress": "sorcerer",
            "nymph": "satyr",
            # Family (extended)
            "stepmother": "stepfather",
            "stepdaughter": "stepson",
            "stepsister": "stepbrother",
            "godmother": "godfather",
            "kinswoman": "kinsman",
            # Period / colloquial
            "wench": "knave",
            "damsel": "youth",
            "harlot": "rake",
            # Pronoun safety nets — unambiguous forms only
            # ("her" omitted: ambiguous object/possessive → LLM handles in context)
            "she": "he",
            "herself": "himself",
            # Title safety nets — LLM sometimes leaves gendered titles on character names
            "Mrs": "Mr",
        },
        "all_female": {
            # Familial / relational
            "father": "mother",
            "son": "daughter",
            "brother": "sister",
            "husband": "wife",
            "uncle": "aunt",
            "nephew": "niece",
            "grandfather": "grandmother",
            "grandson": "granddaughter",
            "widower": "widow",
            "bachelor": "maiden",
            "man": "woman",
            "boy": "girl",
            "male": "female",
            "lad": "lass",
            # Social / aristocratic
            "king": "queen",
            "prince": "princess",
            "duke": "duchess",
            "count": "countess",
            "baron": "baroness",
            "emperor": "empress",
            "abbot": "abbess",
            "lord": "lady",
            "lordship": "ladyship",
            "hero": "heroine",
            "groom": "bride",
            "marquess": "marchioness",
            "viscount": "viscountess",
            # Occupational / address
            "master": "mistress",
            "sir": "madam",
            "manservant": "maid",
            "tutor": "governess",
            "steward": "housekeeper",
            "landlord": "landlady",
            "actor": "actress",
            "host": "hostess",
            "waiter": "waitress",
            "barman": "barmaid",
            "author": "authoress",
            "poet": "poetess",
            "murderer": "murderess",
            "shepherd": "shepherdess",
            "hunter": "huntress",
            "page": "handmaid",
            "gentleman": "gentlewoman",
            # Religious / mythological
            "monk": "nun",
            "warlock": "witch",
            "prophet": "prophetess",
            "priest": "priestess",
            "enchanter": "enchantress",
            "sorcerer": "sorceress",
            "satyr": "nymph",
            # Family (extended)
            "stepfather": "stepmother",
            "stepson": "stepdaughter",
            "stepbrother": "stepsister",
            "godfather": "godmother",
            "kinsman": "kinswoman",
            # Period / colloquial
            "knave": "wench",
            "rake": "harlot",
            # Pronoun safety nets — unambiguous forms only
            # ("her" omitted: ambiguous object/possessive → LLM handles in context)
            "he": "she",
            "him": "her",
            "himself": "herself",
            # Title safety nets — LLM sometimes leaves gendered titles on character names
            "Mr": "Ms",
        },
        "gender_swap": {
            # Familial / relational (both directions)
            "mother": "father",
            "father": "mother",
            "daughter": "son",
            "son": "daughter",
            "sister": "brother",
            "brother": "sister",
            "wife": "husband",
            "husband": "wife",
            "aunt": "uncle",
            "uncle": "aunt",
            "niece": "nephew",
            "nephew": "niece",
            "grandmother": "grandfather",
            "grandfather": "grandmother",
            "granddaughter": "grandson",
            "grandson": "granddaughter",
            "widow": "widower",
            "widower": "widow",
            "maiden": "bachelor",
            "bachelor": "maiden",
            "spinster": "bachelor",
            "woman": "man",
            "man": "woman",
            "girl": "boy",
            "boy": "girl",
            "female": "male",
            "male": "female",
            "lass": "lad",
            "lad": "lass",
            # Social / aristocratic
            "queen": "king",
            "king": "queen",
            "princess": "prince",
            "prince": "princess",
            "duchess": "duke",
            "duke": "duchess",
            "countess": "count",
            "count": "countess",
            "baroness": "baron",
            "baron": "baroness",
            "empress": "emperor",
            "emperor": "empress",
            "abbess": "abbot",
            "abbot": "abbess",
            "lady": "lord",
            "lord": "lady",
            "ladyship": "lordship",
            "lordship": "ladyship",
            "dame": "sir",
            "heroine": "hero",
            "hero": "heroine",
            "bride": "groom",
            "groom": "bride",
            "marchioness": "marquess",
            "marquess": "marchioness",
            "viscountess": "viscount",
            "viscount": "viscountess",
            # Occupational / address
            "mistress": "master",
            "master": "mistress",
            "madam": "sir",
            "sir": "madam",
            "maid": "manservant",
            "manservant": "maid",
            "governess": "tutor",
            "tutor": "governess",
            "housekeeper": "steward",
            "steward": "housekeeper",
            "landlady": "landlord",
            "landlord": "landlady",
            "actress": "actor",
            "actor": "actress",
            "hostess": "host",
            "host": "hostess",
            "waitress": "waiter",
            "waiter": "waitress",
            "barmaid": "barman",
            "barman": "barmaid",
            "authoress": "author",
            "author": "authoress",
            "poetess": "poet",
            "poet": "poetess",
            "murderess": "murderer",
            "murderer": "murderess",
            "shepherdess": "shepherd",
            "shepherd": "shepherdess",
            "huntress": "hunter",
            "hunter": "huntress",
            "handmaid": "page",
            "handmaiden": "page",
            "page": "handmaid",
            "gentlewoman": "gentleman",
            "gentleman": "gentlewoman",
            # Religious / mythological
            "nun": "monk",
            "monk": "nun",
            "witch": "warlock",
            "warlock": "witch",
            "prophetess": "prophet",
            "prophet": "prophetess",
            "priestess": "priest",
            "priest": "priestess",
            "enchantress": "enchanter",
            "enchanter": "enchantress",
            "sorceress": "sorcerer",
            "sorcerer": "sorceress",
            "nymph": "satyr",
            "satyr": "nymph",
            # Family (extended)
            "stepmother": "stepfather",
            "stepfather": "stepmother",
            "stepdaughter": "stepson",
            "stepson": "stepdaughter",
            "stepsister": "stepbrother",
            "stepbrother": "stepsister",
            "godmother": "godfather",
            "godfather": "godmother",
            "kinswoman": "kinsman",
            "kinsman": "kinswoman",
            # Period / colloquial
            "wench": "knave",
            "knave": "wench",
            "damsel": "youth",
            "harlot": "rake",
            "rake": "harlot",
            # Pronoun safety nets — only forms with a single unambiguous swap.
            # "her" (him/his) and "his" (her/hers) depend on syntactic role and
            # are handled by _CONTEXTUAL_PRONOUNS instead.
            "he": "she",
            "she": "he",
            "him": "her",
            "hers": "his",
            "himself": "herself",
            "herself": "himself",
            # Title safety nets — the LLM treats honorifics as part of the name
            "Mr": "Mrs",
            "Mrs": "Mr",
        },
        "nonbinary": {
            # Pronouns (safety net for any LLM misses)
            "he": "they",
            "she": "they",
            "him": "them",
            # "her" and "his" are role-dependent ("her mother" -> "their parent"
            # but "spoke to her" -> "spoke to them") and live in
            # _CONTEXTUAL_PRONOUNS; a flat mapping here produced "them parent".
            "hers": "theirs",
            "himself": "themself",
            "herself": "themself",
            # Familial / relational
            "mother": "parent",
            "father": "parent",
            "daughter": "child",
            "son": "child",
            "sister": "sibling",
            "brother": "sibling",
            "aunt": "relative",
            "uncle": "relative",
            "niece": "nibling",
            "nephew": "nibling",
            "grandmother": "grandparent",
            "grandfather": "grandparent",
            "granddaughter": "grandchild",
            "grandson": "grandchild",
            "wife": "spouse",
            "husband": "spouse",
            "widow": "bereaved",
            "widower": "bereaved",
            "maiden": "single",
            "bachelor": "single",
            "spinster": "single",
            "woman": "person",
            "man": "person",
            "girl": "youth",
            "boy": "youth",
            "female": "person",
            "male": "person",
            # Social / aristocratic
            "queen": "monarch",
            "king": "monarch",
            "princess": "royal",
            "prince": "royal",
            "duchess": "noble",
            "duke": "noble",
            "empress": "ruler",
            "emperor": "ruler",
            "lady": "noble",
            "lord": "noble",
            "heroine": "hero",
            "bride": "betrothed",
            "groom": "betrothed",
            # Occupational / address
            "madam": "Mx.",
            "mistress": "master",
            "maid": "attendant",
            "governess": "tutor",
            "housekeeper": "steward",
            "landlady": "landlord",
            "actress": "actor",
            "hostess": "host",
            "waitress": "server",
            "waiter": "server",
            "gentlewoman": "person",
            "gentleman": "person",
            # Religious / mythological
            "nun": "monastic",
            "monk": "monastic",
            "witch": "mage",
            "warlock": "mage",
            "priestess": "priest",
            "sorceress": "sorcerer",
            "enchantress": "enchanter",
            # Family (extended)
            "stepmother": "stepparent",
            "stepfather": "stepparent",
            "stepdaughter": "stepchild",
            "stepson": "stepchild",
            "stepsister": "stepsibling",
            "stepbrother": "stepsibling",
            "godmother": "godparent",
            "godfather": "godparent",
            # Compound titles not caught by single-word rules
            "Ladyship": "Nobleship",
            "lordship": "nobleship",
            # Gendered titles the LLM sometimes leaves on character names
            # (period preserved from surrounding text for Mr/Mrs; Mx. added for Miss)
            # Note: "Miss" omitted here — case-insensitive match would corrupt the verb "miss"
            "Mr": "Mx",
            "Mrs": "Mx",
            # LLM typo correction: "nibling" is the target but LLM sometimes writes "nibbling"
            "nibbling": "nibling",
            # Verb agreement: singular 'they' takes 'were/have/do/are', not 'was/has/does/is'
            # The LLM inherits conjugation from the source gender and does not adjust.
            "they was": "they were",
            "they wasn't": "they weren't",
            "they has": "they have",
            "they hasn't": "they haven't",
            "they does": "they do",
            "they doesn't": "they don't",
            "they is": "they are",
        },
    }

    # Case-sensitive regex fixes applied after _apply_term_map.
    # Keyed by transform type value. Used for patterns where re.IGNORECASE
    # would cause false positives (e.g. "Miss" verb vs title).
    _CASE_SENSITIVE_FIXES: dict[str, list[tuple]] = {
        # "Miss Name" (title form — capital following word). Safe because:
        # - Verb "miss" is always lowercase in flowing prose
        # - Title "Miss" precedes a capital proper name
        "nonbinary": [
            (re.compile(r"Miss (?=[A-Z])"), "Mx. "),
            (re.compile(r"_Miss ([A-Z])"), r"_Mx. \1"),
        ],
        "all_male": [
            (re.compile(r"Miss (?=[A-Z])"), "Mr. "),
            (re.compile(r"_Miss ([A-Z])"), r"_Mr. \1"),
        ],
        "all_female": [
            # "Miss" is already female — only need to catch "Mr." on now-female characters.
            # Handled by the "Mr" → "Ms" term map entry; no case-sensitive fix needed here.
        ],
    }

    # Pronouns whose swapped form depends on syntactic role, so they cannot live
    # in the flat term map. Keyed by transform, then pronoun:
    #   (form before a gendered noun, form before punctuation / end of clause)
    # "her husband" is possessive -> "his wife"; "spoke to her." is objective ->
    # "spoke to him.". Anything in between is left for the QC report to surface.
    _CONTEXTUAL_PRONOUNS: dict[str, dict[str, tuple[str, str]]] = {
        "gender_swap": {"her": ("his", "him"), "his": ("her", "hers")},
        "all_male": {"her": ("his", "him")},
        "all_female": {"his": ("her", "hers")},
        "nonbinary": {"her": ("their", "them"), "his": ("their", "theirs")},
    }

    # "his" has no objective form: it is either a possessive determiner ("his
    # name") or a possessive pronoun ("a friend of his"). "her" is the one that
    # is genuinely ambiguous -- possessive in "her name", objective in "told her"
    # -- so it only gets resolved where the context settles it.
    _NO_OBJECTIVE_FORM = frozenset({"his"})

    # A word that can only follow a possessive determiner. "her own" is never
    # objective, so it settles a "her" that would otherwise be left ambiguous.
    _POSSESSIVE_MARKERS = frozenset({"own"})

    # Adverbs and degree words. A possessive determiner is never followed by one,
    # so "danced with her twice" and "thought her quite beautiful" are objective
    # while "her eye" and "her housekeeping" are possessive. Measured against the
    # Pride and Prejudice text: these mark every objective "her" that is followed
    # by a content word.
    _ADVERBIAL_AFTER = frozenset(
        {
            "again",
            "almost",
            "alone",
            "already",
            "also",
            "always",
            "apart",
            "aside",
            "away",
            "certainly",
            "coldly",
            "deeply",
            "entirely",
            "enough",
            "even",
            "ever",
            "formerly",
            "forth",
            "greatly",
            "hence",
            "here",
            "highly",
            "however",
            "immediately",
            "indeed",
            "instantly",
            "just",
            "kindly",
            "lately",
            "nearly",
            "never",
            "now",
            "off",
            "once",
            "only",
            "out",
            "perhaps",
            "presently",
            "probably",
            "quite",
            "rather",
            "really",
            "surely",
            "somewhat",
            "soon",
            "still",
            "then",
            "there",
            "therefore",
            "thus",
            "together",
            "too",
            "twice",
            "thrice",
            "very",
            "warmly",
            "wholly",
            "yesterday",
        }
    )

    # Words that cannot begin a noun phrase. A pronoun followed by one of these
    # is not a possessive determiner, so "a friend of his in town" resolves to
    # the standalone form and "gave her a book" to the objective one.
    _CLAUSE_CONTINUERS = frozenset(
        {
            # determiners and quantifiers
            "a",
            "an",
            "the",
            "this",
            "that",
            "these",
            "those",
            "some",
            "any",
            "each",
            "every",
            "no",
            "another",
            "such",
            "much",
            "many",
            "more",
            "most",
            "few",
            "several",
            "both",
            "either",
            "neither",
            # possessives that cannot follow another determiner
            "my",
            "your",
            "our",
            "their",
            "its",
            "his",
            "her",
            # prepositions
            "of",
            "in",
            "on",
            "at",
            "to",
            "for",
            "from",
            "by",
            "with",
            "about",
            "into",
            "upon",
            "over",
            "under",
            "after",
            "before",
            "between",
            "through",
            "against",
            "towards",
            "toward",
            "without",
            "within",
            "during",
            "than",
            "as",
            "like",
            # conjunctions and subordinators
            "and",
            "or",
            "but",
            "if",
            "when",
            "while",
            "because",
            "so",
            "then",
            "though",
            "although",
            "yet",
            "since",
            "unless",
            "whether",
            # relative and interrogative pronouns
            "who",
            "whom",
            "whose",
            "which",
            "what",
            "where",
            "why",
            "how",
            # auxiliaries and common finite verbs
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "am",
            "has",
            "have",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "shall",
            "should",
            "can",
            "could",
            "may",
            "might",
            "must",
        }
    )

    # Irregular plurals for the gendered nouns in the term maps. Everything else
    # is derived by _pluralize so that "her sisters" is covered as well as
    # "her sister" -- a bare \b<singular>\b pattern never matches the plural.
    _IRREGULAR_PLURALS: dict[str, str] = {
        "man": "men",
        "woman": "women",
        "gentleman": "gentlemen",
        "gentlewoman": "gentlewomen",
        "kinsman": "kinsmen",
        "kinswoman": "kinswomen",
        "wife": "wives",
        "hero": "heroes",
        "child": "children",
        "person": "people",
    }

    # Every pronoun form the transforms touch. Kept apart from the nouns because
    # they are neither pluralised nor eligible for the possessive rule's lookahead.
    _PRONOUN_FORMS = frozenset(
        {
            "he",
            "she",
            "him",
            "her",
            "his",
            "hers",
            "himself",
            "herself",
            "they",
            "them",
            "their",
            "theirs",
            "themself",
            "themselves",
        }
    )

    # Map keys that must never be pluralised: the pronouns above, plus adjectival
    # entries whose plural would not be a noun.
    _NO_PLURAL = _PRONOUN_FORMS | frozenset({"male", "female", "single"})

    @staticmethod
    def _pluralize(word: str) -> str:
        """Regular English pluralisation for the nouns in the term maps."""
        irregular = TransformService._IRREGULAR_PLURALS.get(word)
        if irregular:
            return irregular
        if word.endswith(("s", "x", "z", "ch", "sh")):
            return word + "es"
        if word.endswith("y") and len(word) > 1 and word[-2] not in "aeiou":
            return word[:-1] + "ies"
        return word + "s"

    @classmethod
    def _effective_term_map(cls, key: str) -> dict[str, str]:
        """Term map for a transform, extended with plural forms.

        Cached on the class: the maps are static, and rebuilding them per
        paragraph would dominate the cost of the substitution itself.
        """
        cached = cls._EFFECTIVE_TERM_MAPS.get(key)
        if cached is not None:
            return cached

        base = cls._TERM_MAPS.get(key, {})
        effective = dict(base)
        for original, replacement in base.items():
            if (
                original.lower() in cls._NO_PLURAL
                or " " in original
                or original[:1].isupper()
                or "." in replacement
            ):
                continue
            plural = cls._pluralize(original.lower())
            if plural not in effective and plural != original.lower():
                effective[plural] = cls._pluralize(replacement.lower())

        cls._EFFECTIVE_TERM_MAPS[key] = effective
        return effective

    @classmethod
    def _gendered_nouns(cls, key: str) -> frozenset:
        """Every gendered noun a transform knows about, before or after swapping.

        Used to decide whether a stray "her"/"his" is possessive. Includes the
        replacement side so the rule still fires when the LLM already corrected
        the noun but left the pronoun behind.
        """
        cached = cls._GENDERED_NOUNS.get(key)
        if cached is not None:
            return cached

        term_map = cls._effective_term_map(key)
        words = set()
        for original, replacement in term_map.items():
            for word in (original, replacement):
                lowered = word.lower().rstrip(".")
                if lowered.isalpha() and lowered not in cls._PRONOUN_FORMS:
                    words.add(lowered)
        result = frozenset(words)
        cls._GENDERED_NOUNS[key] = result
        return result

    @classmethod
    def _gendered_vocabulary(cls, key: str) -> frozenset:
        """Every word a transform may rewrite — gendered nouns plus all pronouns.

        This is the set treated as *not* an alignment anchor by _residual_mask.
        """
        cached = cls._GENDERED_VOCABULARY.get(key)
        if cached is None:
            cached = cls._gendered_nouns(key) | cls._PRONOUN_FORMS
            cls._GENDERED_VOCABULARY[key] = cached
        return cached

    @classmethod
    def _compile_substitution(cls, items: tuple) -> tuple:
        """Compile a mapping into one alternation regex plus a lowercase lookup.

        A single alternation is what makes a bidirectional map correct. Applying
        "mother->father" and then "father->mother" in sequence rewrites the
        output of the first rule with the second and collapses the whole pair
        onto one gender; one pass over the text cannot.

        Longest key first so compound and multi-word entries win over their own
        prefixes ("grandmother" before "mother", "they was" before "they").
        """
        cached = cls._COMPILED_SUBSTITUTIONS.get(items)
        if cached is not None:
            return cached

        lookup = {k.lower(): v for k, v in items}
        keys = sorted(lookup, key=len, reverse=True)
        pattern = re.compile(
            cls._BOUNDARY_BEFORE
            + r"(?:"
            + "|".join(re.escape(k) for k in keys)
            + r")"
            + cls._BOUNDARY_AFTER,
            re.IGNORECASE,
        )
        cls._COMPILED_SUBSTITUTIONS[items] = (pattern, lookup)
        return pattern, lookup

    @staticmethod
    def _match_case(matched: str, replacement: str) -> str:
        """Re-apply the casing of the matched text to its replacement.

        Replacements written with a period are honorifics ("Mx.") and are
        emitted verbatim; lowercasing them would yield "mx.".
        """
        if "." in replacement:
            return replacement
        if len(matched) > 1 and matched.isupper():
            return replacement.upper()
        if matched[:1].isupper():
            return replacement[:1].upper() + replacement[1:]
        return replacement.lower()

    @classmethod
    def align_gendered_words(cls, source_text: str, text: str, key: str) -> list[tuple]:
        """Pair each gendered word in `text` with the source word it came from.

        Returns ``(source_word, output_word, output_span, source_span)`` tuples,
        where ``source_word`` and ``source_span`` are None when no confident
        counterpart exists. An entry whose two words are equal is a word the LLM
        left untransformed. Both spans are reported because callers need to find
        the word in either text, and the two drift apart as words change length.

        The alignment anchors on the *non-gendered* words. Those are the ones the
        LLM leaves alone, so they say which source position each output position
        came from. Diffing raw tokens instead would let a correctly swapped pair
        match itself in reverse -- "queen and king" against "king and queen"
        reports both words as unchanged -- and the safety net would undo the very
        swap it exists to complete.
        """
        vocabulary = cls._gendered_vocabulary(key)

        def split(raw: str) -> tuple[list, dict]:
            """Split into anchor words and the gendered words sitting between them."""
            anchors: list[str] = []
            slots: dict[int, list] = {}
            for match in cls._WORD_RE.finditer(raw):
                word = match.group(0).lower()
                if word in vocabulary:
                    slots.setdefault(len(anchors), []).append((word, match.span()))
                else:
                    anchors.append(word)
            return anchors, slots

        source_anchors, source_slots = split(source_text)
        output_anchors, output_slots = split(text)

        # Slot N holds the gendered words following the Nth anchor. Aligning the
        # anchor streams says which source slot each output slot came from; a slot
        # with no confident mapping yields None and is treated as transformed.
        slot_map = {0: 0}
        matcher = difflib.SequenceMatcher(a=source_anchors, b=output_anchors, autojunk=False)
        for tag, i1, _i2, j1, j2 in matcher.get_opcodes():
            if tag != "equal":
                continue
            for offset in range(j2 - j1):
                slot_map[j1 + offset + 1] = i1 + offset + 1

        aligned = []
        for slot in sorted(output_slots):
            counterpart = source_slots.get(slot_map.get(slot, -1), [])
            for index, (word, span) in enumerate(output_slots[slot]):
                source = counterpart[index] if index < len(counterpart) else (None, None)
                aligned.append((source[0], word, span, source[1]))
        return aligned

    @classmethod
    def _residual_mask(cls, source_text: str, text: str, key: str) -> bytearray:
        """Mark the characters of `text` holding gendered words the LLM left alone.

        A swap map is not idempotent: applying "mother->father, father->mother"
        to text the LLM already transformed swaps it straight back, which is how
        a correct "his father" degrades into "his mother" -- the pronoun moves
        and the noun does not. Only words that match their source counterpart are
        genuine misses and safe to substitute.
        """
        mask = bytearray(len(text))
        for source_word, output_word, (start, end), _source_span in cls.align_gendered_words(
            source_text, text, key
        ):
            if source_word == output_word:
                mask[start:end] = b"\x01" * (end - start)
        return mask

    @staticmethod
    def _is_residual(mask: Optional[bytearray], text: str, start: int, end: int) -> bool:
        """True when every letter of text[start:end] came through the LLM unchanged."""
        if mask is None:
            return True
        return all(mask[i] for i in range(start, end) if text[i].isalpha())

    def _apply_contextual_pronouns(self, text: str, key: str, source_text: Optional[str]) -> str:
        """Resolve role-dependent pronouns the LLM missed ("her husband" -> "his wife").

        Runs after the term map, so the noun beside the pronoun is already
        correct. Only fires on pronouns the LLM left untouched, and only where
        the role is unambiguous: directly before a known gendered noun
        (possessive) or directly before punctuation or end of text (objective).
        """
        rules = self._CONTEXTUAL_PRONOUNS.get(key)
        if not rules:
            return text

        nouns = self._gendered_nouns(key)
        mask = self._residual_mask(source_text, text, key) if source_text is not None else None
        pattern = re.compile(
            self._BOUNDARY_BEFORE + r"(?:" + "|".join(rules) + r")" + self._BOUNDARY_AFTER,
            re.IGNORECASE,
        )

        def _replace(match: "re.Match") -> str:
            start, end = match.span()
            if not self._is_residual(mask, text, start, end):
                return match.group(0)
            pronoun = match.group(0).lower()
            possessive, standalone = rules[pronoun]
            rest = text[end:]

            # End of clause: nothing can be possessed, so it is the standalone
            # form -- "spoke to her." or "the book is his." Markup underscores
            # are skipped rather than treated as the end of the clause.
            if re.match(r"_?\s*(?:$|[^\w\s])", rest):
                return self._match_case(match.group(0), standalone)

            following = re.match(r"_?\s+_?([A-Za-z']+)", rest)
            if following is None:
                return match.group(0)
            word = following.group(1).lower()

            if word in self._POSSESSIVE_MARKERS or word in nouns:
                return self._match_case(match.group(0), possessive)
            if word in self._CLAUSE_CONTINUERS or word in self._ADVERBIAL_AFTER:
                return self._match_case(match.group(0), standalone)
            # A content word follows and nothing marks the pronoun as objective,
            # so it heads a noun phrase: "his name", "her housekeeping".
            return self._match_case(match.group(0), possessive)

        return pattern.sub(_replace, text)

    def _apply_term_map(
        self,
        text: str,
        transform_type: "TransformType",
        source_text: Optional[str] = None,
    ) -> str:
        """Deterministic safety net for gendered terms the LLM left untransformed.

        Pass `source_text` (the untransformed paragraph) wherever it is
        available. Without it the substitution cannot tell an LLM miss from an
        LLM success and, for a bidirectional map like gender_swap, will undo
        correct work.
        """
        key = transform_type.value
        term_map = self._effective_term_map(key)
        if term_map:
            pattern, lookup = self._compile_substitution(tuple(sorted(term_map.items())))
            mask = self._residual_mask(source_text, text, key) if source_text is not None else None
            current = text

            def _replace(match: "re.Match") -> str:
                start, end = match.span()
                if not self._is_residual(mask, current, start, end):
                    return match.group(0)
                return self._match_case(match.group(0), lookup[match.group(0).lower()])

            text = pattern.sub(_replace, text)

        text = self._apply_contextual_pronouns(text, key, source_text)

        for pattern, replacement in self._CASE_SENSITIVE_FIXES.get(key, []):
            text = pattern.sub(replacement, text)

        return text

    async def _transform_single_paragraph(
        self,
        para: Any,
        context: dict[str, Any],
        name_map: Optional[dict[str, str]],
        transform_type: "TransformType",
    ) -> str:
        """Transform one paragraph via LLM, applying post-processing. Used by retry logic."""
        prompt = self._create_batch_transform_prompt([para], context, 1)
        messages = [
            {"role": "system", "content": prompt["system"]},
            {"role": "user", "content": prompt["user"]},
        ]
        response = await self.provider.complete(
            messages=messages,
            temperature=self.config.llm_temperature,
        )
        texts = self._parse_batch_response(response, 1)
        transformed_text = texts[0] if texts else para.get_text()
        if name_map:
            transformed_text = self._apply_name_map(transformed_text, name_map)
        return self._apply_term_map(transformed_text, transform_type, source_text=para.get_text())

    async def _retry_at_sentence_level(
        self,
        batch_paragraphs: list,
        context: dict[str, Any],
        name_map: Optional[dict[str, str]],
        transform_type: "TransformType",
    ) -> list:
        """Retry a failed batch by processing each paragraph alone.

        If a single paragraph also times out (e.g. an extremely long paragraph like
        Darcy's letter), split its sentences into groups of ~10 and process each group
        separately, then merge the results back into a single paragraph.
        """
        from src.models.book import Paragraph

        results = []
        for para in batch_paragraphs:
            try:
                transformed_text = await self._transform_single_paragraph(
                    para, context, name_map, transform_type
                )
                results.append(Paragraph(sentences=[transformed_text]))
            except Exception as e:
                self.logger.warning(
                    f"Single-paragraph retry failed ({e}), splitting by sentences..."
                )
                sentences = para.sentences if para.sentences else [para.get_text()]
                # Process in groups of 10 sentences to stay well within timeout
                group_size = 10
                groups = [
                    sentences[i : i + group_size] for i in range(0, len(sentences), group_size)
                ]
                merged_parts = []
                for group in groups:
                    group_para = Paragraph(sentences=group)
                    try:
                        part_text = await self._transform_single_paragraph(
                            group_para, context, name_map, transform_type
                        )
                        merged_parts.append(part_text)
                    except Exception:
                        # True last resort: keep original sentence group text
                        merged_parts.append(group_para.get_text())
                results.append(Paragraph(sentences=[" ".join(merged_parts)]))
        return results

    def _expand_name_map_with_aliases(
        self, name_map: dict[str, str], characters: "CharacterAnalysis"
    ) -> dict[str, str]:
        """Expand name_map to include aliases of mapped characters.

        Checks both the character's canonical name and all stored aliases against the name_map.
        If any name for a character is in the map, all other aliases are added automatically.
        e.g. name_map has 'Elizabeth'; character 'Elizabeth Bennet' has aliases ['Lizzy','Eliza']
        → 'Lizzy' and 'Eliza' are added pointing to the same target.
        """
        expanded = dict(name_map)
        for char in characters.characters:
            all_names = [char.name] + list(char.aliases)
            matched_target = next((name_map[n] for n in all_names if n in name_map), None)
            if matched_target:
                for name in all_names:
                    if name not in expanded:
                        expanded[name] = matched_target
        return expanded

    def _parse_batch_response(self, response: str, expected_count: int) -> list[str]:
        """Parse batch response into individual paragraph texts."""
        # Simple approach: split by double newlines
        # The LLM should return paragraphs separated by blank lines
        paragraphs = response.strip().split("\n\n")

        # If we got the expected number, great!
        if len(paragraphs) == expected_count:
            return paragraphs

        # Otherwise, try to be smart about it
        self.logger.warning(f"Expected {expected_count} paragraphs, got {len(paragraphs)}")

        # Pad or truncate as needed
        if len(paragraphs) < expected_count:
            # Pad with empty strings
            paragraphs.extend([""] * (expected_count - len(paragraphs)))
        else:
            # Truncate
            paragraphs = paragraphs[:expected_count]

        return paragraphs

    def _create_token_optimized_batches(
        self, paragraphs: list, context: dict[str, Any]
    ) -> list[list]:
        """Create batches of paragraphs optimized for token count."""
        if not self.token_manager:
            # Fallback to fixed batch size if no token manager
            from src.utils.config import config as app_config

            batch_size = app_config.transform_batch_size
            return [paragraphs[i : i + batch_size] for i in range(0, len(paragraphs), batch_size)]

        # Get configuration
        from src.utils.config import config as app_config

        target_utilization = app_config._config.get("transformation", {}).get(
            "target_token_utilization", 0.66
        )
        max_request_tokens = app_config._config.get("transformation", {}).get(
            "max_tokens_per_request", 120000
        )

        # Get max tokens for this model
        max_context = self.token_manager.config.max_context_tokens
        max_context = min(max_context, max_request_tokens)  # Cap at configured maximum

        # Reserve tokens for prompt overhead, response, and character context
        prompt_overhead = 1500  # Estimated tokens for system prompt and instructions
        response_overhead = 2000  # Reserve space for response
        char_context_tokens = self._estimate_character_context_tokens(context)

        available_tokens = int(
            (max_context * target_utilization)
            - prompt_overhead
            - response_overhead
            - char_context_tokens
        )

        self.logger.debug(
            f"Token budget: {available_tokens} (context: {max_context}, prompt: {prompt_overhead}, response: {response_overhead}, chars: {char_context_tokens})"
        )

        batches = []
        current_batch = []
        current_tokens = 0

        for para in paragraphs:
            para_text = para.get_text()
            para_tokens = self.token_manager.estimate_tokens(para_text)

            # Start new batch if adding this paragraph would exceed limit
            if current_tokens + para_tokens > available_tokens and current_batch:
                batches.append(current_batch)
                current_batch = []
                current_tokens = 0

            # Add paragraph to current batch
            current_batch.append(para)
            current_tokens += para_tokens

            # If single paragraph exceeds limit, put it in its own batch
            if para_tokens > available_tokens:
                self.logger.warning(
                    f"Paragraph exceeds token limit ({para_tokens} > {available_tokens})"
                )
                if len(current_batch) > 1:
                    # Remove it and add to next batch
                    current_batch.pop()
                    batches.append(current_batch)
                    current_batch = [para]
                    current_tokens = para_tokens

        # Add remaining batch
        if current_batch:
            batches.append(current_batch)

        return batches

    def _estimate_batch_tokens(self, batch_paragraphs: list, context: dict[str, Any]) -> int:
        """Estimate total tokens for a batch including prompt."""
        if not self.token_manager:
            return len(batch_paragraphs) * 200  # Rough estimate

        total_tokens = 0
        # Add paragraph text tokens
        for para in batch_paragraphs:
            total_tokens += self.token_manager.estimate_tokens(para.get_text())

        # Add prompt overhead
        total_tokens += 1500  # System prompt
        total_tokens += self._estimate_character_context_tokens(context)

        return total_tokens

    def _estimate_character_context_tokens(self, context: dict[str, Any]) -> int:
        """Estimate tokens used by character context."""
        if not self.token_manager:
            return 500  # Default estimate

        char_info = context.get("character_info", "")
        return self.token_manager.estimate_tokens(char_info) if char_info else 200

    def _create_batch_transform_prompt(
        self, batch_paragraphs: list, context: dict[str, Any], batch_size: int
    ) -> dict[str, str]:
        """Create prompt for batch transformation."""
        transform_type = context.get("transform_type", TransformType.GENDER_SWAP)
        rules = context.get("rules", self._get_transformation_rules(transform_type))
        character_mappings = context.get("character_mappings", {})
        characters = context.get("characters")

        # Build character-specific transformation instructions
        character_instructions = self._build_character_instructions(
            characters, transform_type, character_mappings
        )

        system_prompt = f"""Gender transformation expert. Transform {batch_size} paragraphs.

{rules}
{character_instructions}

PRONOUN DISAMBIGUATION: In scenes where multiple characters share the same pronoun after transformation, replace ambiguous pronouns with the character's name where a first-time reader would be uncertain who is referred to. Prioritize dialogue attribution lines and sentences immediately following a speaker change. Do not alter sentence rhythm or add words beyond the name substitution.

For paired opposite-gender terms (e.g. "boys and girls", "ladies and gentlemen", "father and mother"), simplify to the target gender only (e.g. "girls", "ladies", "mother").
Return EXACTLY {batch_size} paragraphs separated by blank lines. Keep original style. Only change gender language."""

        # Simpler format without markers - just numbered paragraphs
        paragraphs_text = "\n\n".join(p.get_text() for p in batch_paragraphs)

        user_prompt = f"Transform these {batch_size} paragraphs (separated by blank lines):\n\n{paragraphs_text}"

        return {"system": system_prompt, "user": user_prompt}

    def _create_transform_prompt(self, text: str, context: dict[str, Any]) -> dict[str, str]:
        """Create prompt for LLM transformation."""
        transform_type = context.get("transform_type", TransformType.GENDER_SWAP)

        # Get the transformation rules for this type
        rules = context.get("rules", self._get_transformation_rules(transform_type))

        # Create specific examples for the transformation
        examples = ""
        if transform_type == TransformType.GENDER_SWAP:
            examples = """
Examples of transformations:
- "He walked to his car" → "She walked to her car"
- "Mr. Smith entered" → "Ms. Smith entered"
- "The father told his son" → "The mother told her daughter"
- "himself" → "herself"
"""

        system_prompt = f"""You are a precise text transformer. Apply gender swapping rules to the text.

TRANSFORMATION TYPE: {transform_type.value if hasattr(transform_type, "value") else transform_type}

{examples}

RULES:
1. Swap ALL gendered pronouns (he→she, him→her, his→hers, himself→herself, etc.)
2. Swap ALL titles (Mr.→Ms., Sir→Madam, Lord→Lady, etc.)
3. Swap ALL gendered terms (man→woman, boy→girl, father→mother, son→daughter, etc.)
4. Preserve proper names unchanged
5. Maintain exact punctuation and formatting

CRITICAL: You MUST make these changes. The text MUST be different from the input.
Return ONLY the transformed text with NO explanations or metadata."""

        user_prompt = f"""Apply gender swap transformation to this text:

INPUT TEXT:
{text}

TRANSFORMED TEXT:"""

        return {"system": system_prompt, "user": user_prompt}

    def get_metrics(self) -> dict[str, Any]:
        """Get service metrics."""
        metrics = super().get_metrics()
        metrics.update(
            {
                "provider": self.provider.name if self.provider else "none",
                "strategy": self.strategy.__class__.__name__,
                "cache_size": len(self.transformation_cache),
            }
        )

        # Add token usage metrics
        if self.token_manager:
            metrics["token_usage"] = self.token_manager.get_usage_stats()
            metrics["model_info"] = self.token_manager.get_model_info()

        return metrics
