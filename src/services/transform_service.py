"""
Transform Service

This service handles gender transformation of books.
"""

import asyncio
import os
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
    ValidationError,
    TransformationError,
    ConfigurationError,
    ErrorHandler,
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
                f"'book' must be a Book object, got {type(book).__name__}",
                field="book"
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
                    details={"valid_types": [t.value for t in TransformType]}
                ) from e
        elif not isinstance(transform_type, TransformType):
            raise ValidationError(
                f"'transform_type' must be a TransformType or string, got {type(transform_type).__name__}",
                field="transform_type"
            )

        # Optional characters validation
        characters = data.get("characters")
        if characters and not isinstance(characters, CharacterAnalysis):
            raise ValidationError(
                f"'characters' must be a CharacterAnalysis object if provided, got {type(characters).__name__}",
                field="characters"
            )

        return await self.transform_book(book, transform_type, characters)

    async def transform_book(
        self,
        book: Book,
        transform_type: TransformType,
        characters: Optional[CharacterAnalysis] = None,
        selected_characters: Optional[list[str]] = None,
    ) -> Transformation:
        """
        Transform a book with the specified transformation type.

        Args:
            book: Book to transform
            transform_type: Type of transformation
            characters: Pre-analyzed characters (optional)
            selected_characters: Specific characters to transform (optional)

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
                f"Expected Book instance, got {type(book).__name__}",
                field="book"
            )

        # Validate book has content
        if not book.chapters or len(book.chapters) == 0:
            raise ValidationError(
                "Book has no chapters to transform",
                field="book.chapters",
                details={"book_title": book.title or "Unknown"}
            )

        # Validate provider
        if not self.provider:
            raise ConfigurationError(
                "LLM provider not initialized",
                config_key="provider",
                details={"service": "TransformService"}
            )

        # Validate transform type
        if not isinstance(transform_type, TransformType):
            raise ValidationError(
                f"Invalid transform type: {transform_type}",
                field="transform_type"
            )

        # Validate selected characters if provided
        if selected_characters is not None:
            if not isinstance(selected_characters, list):
                raise ValidationError(
                    f"selected_characters must be a list, got {type(selected_characters).__name__}",
                    field="selected_characters"
                )
            if not all(isinstance(char, str) for char in selected_characters):
                raise ValidationError(
                    "All selected characters must be strings",
                    field="selected_characters"
                )

        start_time = time.time()

        try:
            # Get character analysis if not provided
            if not characters:
                if not self.character_service:
                    raise ConfigurationError(
                        "Character service required when characters not provided",
                        config_key="character_service"
                    )

                self.logger.info("Analyzing characters...")
                characters = await self.character_service.process(book)

            # Create transformation context
            context = self._create_context(characters, transform_type, selected_characters)

            # Transform chapters
            self.logger.info(f"Transforming {len(book.chapters)} chapters...")
            transformed_chapters, all_changes = await self._transform_chapters(
                book.chapters, context
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
                    "processing_time": time.time() - start_time
                }
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
        self, characters: Optional[CharacterAnalysis], transform_type: TransformType, character_mappings: dict
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
            current_gender = char.gender.value if hasattr(char.gender, 'value') else str(char.gender)

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

        lines.append("\nApply these specific character transformations consistently throughout the text.")

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
        else:
            return {}

    def _get_character_transformation(self, character, transform_type: TransformType) -> dict:
        """Get transformation info for a specific character - let LLM handle the actual transformation."""
        mappings = {
            "original_gender": character.gender,
            "name": character.name,
            "aliases": character.aliases
        }

        # Just track whether to transform or preserve - let LLM handle the actual transformation
        current_gender = character.gender.value if hasattr(character.gender, 'value') else str(character.gender)

        if transform_type == TransformType.GENDER_SWAP:
            # LLM will swap genders
            mappings["transform"] = True
        elif transform_type in [TransformType.ALL_MALE, TransformType.ALL_FEMALE, TransformType.NONBINARY]:
            # LLM will apply the transformation type
            mappings["transform"] = True
        else:
            # Keep original
            mappings["preserve"] = True

        return mappings

    async def _transform_chapters(
        self, chapters: list[Chapter], context: dict[str, Any]
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
            return await self._transform_chapters_parallel(chapters, context)
        else:
            return await self._transform_chapters_sequential(chapters, context)

    async def _transform_chapters_sequential(
        self, chapters: list[Chapter], context: dict[str, Any]
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

            self.logger.debug(f"Transforming chapter {i + 1}/{len(chapters)}")

            transformed_chapter, changes = await self._transform_single_chapter(chapter, i, context)

            transformed_chapters.append(transformed_chapter)
            all_changes.extend(changes)

            # Show progress
            if (i + 1) % 5 == 0:
                self.logger.info(f"Progress: {i + 1}/{len(chapters)} chapters transformed")

        return transformed_chapters, all_changes

    async def _transform_chapters_parallel(
        self, chapters: list[Chapter], context: dict[str, Any]
    ) -> tuple[list[Chapter], list[TransformationChange]]:
        """Transform chapters in parallel with rate limiting."""

        # For OpenAI, force sequential processing due to rate limits
        if self.provider and "openai" in self.provider.name.lower():
            self.logger.info("OpenAI detected - using sequential processing for rate limiting")
            return await self._transform_chapters_sequential(chapters, context)

        # Create tasks for each chapter
        tasks = [
            self._transform_single_chapter(chapter, i, context)
            for i, chapter in enumerate(chapters)
        ]

        # Limit concurrency
        semaphore = asyncio.Semaphore(self.config.max_concurrent)

        async def limited_task(task):
            async with semaphore:
                return await task

        # Execute all tasks
        results = await asyncio.gather(*[limited_task(t) for t in tasks])

        # Separate chapters and changes
        transformed_chapters = []
        all_changes = []

        for transformed_chapter, changes in results:
            transformed_chapters.append(transformed_chapter)
            all_changes.extend(changes)

        return transformed_chapters, all_changes

    async def _transform_single_chapter(
        self, chapter: Chapter, chapter_index: int, context: dict[str, Any]
    ) -> tuple[Chapter, list[TransformationChange]]:
        """
        Transform a single chapter.

        Args:
            chapter: Chapter to transform
            chapter_index: Index of the chapter
            context: Transformation context

        Returns:
            Tuple of (transformed chapter, list of changes)
        """
        from src.models.book import Chapter, Paragraph
        from src.models.transformation import TransformationChange

        # Require LLM provider for transformation
        if not self.provider:
            raise ValueError("LLM provider is required for transformation. Please configure an LLM provider (OpenAI or Anthropic).")

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
        self.logger.info(f"Processing {total_paragraphs} paragraphs in {total_batches} token-optimized batches (avg size: {avg_batch_size:.1f})")

        # Setup progress bar
        disable_progress = not os.isatty(1) if hasattr(os, 'isatty') else True
        try:
            from tqdm import tqdm
            progress_bar = tqdm(
                total=total_batches,
                desc=f"Transforming {chapter.title or 'chapter'}",
                disable=disable_progress,
                unit="batch"
            )
        except ImportError:
            progress_bar = None

        batch_start = 0
        for batch_num, batch_paragraphs in enumerate(batches, 1):
            batch_end = batch_start + len(batch_paragraphs)

            if not progress_bar:
                self.logger.info(f"Processing batch {batch_num}/{total_batches} (paragraphs {batch_start+1}-{batch_end}, ~{self._estimate_batch_tokens(batch_paragraphs, context)} tokens)")
            else:
                progress_bar.set_postfix({"paragraphs": f"{batch_start+1}-{batch_end}"})

            # Create batch prompt with the actual paragraph objects
            prompt = self._create_batch_transform_prompt(batch_paragraphs, context, len(batch_paragraphs))

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
                for i, (paragraph, transformed_text) in enumerate(zip(batch_paragraphs, transformed_texts)):
                    para_idx = batch_start + i
                    original_text = paragraph.get_text()

                    # Debug logging for first paragraph
                    if para_idx == 0:
                        self.logger.debug(f"Original text: {repr(original_text[:100])}")
                        self.logger.debug(f"Transformed text: {repr(transformed_text[:100])}")

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
                self.logger.warning(f"Failed to transform batch {batch_start}-{batch_end}: {e}")
                # Keep originals on error
                for paragraph in batch_paragraphs:
                    transformed_paragraphs.append(paragraph)

        # Close progress bar
        if progress_bar:
            progress_bar.close()

        # Create transformed chapter
        transformed_chapter = Chapter(
            number=chapter.number, title=chapter.title, paragraphs=transformed_paragraphs
        )

        return transformed_chapter, changes

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

    def _create_token_optimized_batches(self, paragraphs: list, context: dict[str, Any]) -> list[list]:
        """Create batches of paragraphs optimized for token count."""
        if not self.token_manager:
            # Fallback to fixed batch size if no token manager
            from src.utils.config import config as app_config
            batch_size = app_config.transform_batch_size
            return [paragraphs[i:i + batch_size] for i in range(0, len(paragraphs), batch_size)]

        # Get configuration
        from src.utils.config import config as app_config
        target_utilization = app_config._config.get("transformation", {}).get("target_token_utilization", 0.66)
        max_request_tokens = app_config._config.get("transformation", {}).get("max_tokens_per_request", 120000)

        # Get max tokens for this model
        max_context = self.token_manager.get_model_config(self.provider.model if self.provider else "gpt-4").max_context_tokens
        max_context = min(max_context, max_request_tokens)  # Cap at configured maximum

        # Reserve tokens for prompt overhead, response, and character context
        prompt_overhead = 1500  # Estimated tokens for system prompt and instructions
        response_overhead = 2000  # Reserve space for response
        char_context_tokens = self._estimate_character_context_tokens(context)

        available_tokens = int((max_context * target_utilization) - prompt_overhead - response_overhead - char_context_tokens)

        self.logger.debug(f"Token budget: {available_tokens} (context: {max_context}, prompt: {prompt_overhead}, response: {response_overhead}, chars: {char_context_tokens})")

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
                self.logger.warning(f"Paragraph exceeds token limit ({para_tokens} > {available_tokens})")
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

    def _create_batch_transform_prompt(self, batch_paragraphs: list, context: dict[str, Any], batch_size: int) -> dict[str, str]:
        """Create prompt for batch transformation."""
        transform_type = context.get("transform_type", TransformType.GENDER_SWAP)
        rules = context.get("rules", self._get_transformation_rules(transform_type))
        character_mappings = context.get("character_mappings", {})
        characters = context.get("characters")

        # Build character-specific transformation instructions
        character_instructions = self._build_character_instructions(characters, transform_type, character_mappings)

        system_prompt = f"""Gender transformation expert. Transform {batch_size} paragraphs.

{rules}
{character_instructions}

Return EXACTLY {batch_size} paragraphs separated by blank lines. Keep original style. Only change gender language."""

        # Simpler format without markers - just numbered paragraphs
        paragraphs_text = "\n\n".join(
            p.get_text() for p in batch_paragraphs
        )

        user_prompt = f"Transform these {batch_size} paragraphs (separated by blank lines):\n\n{paragraphs_text}"

        return {
            "system": system_prompt,
            "user": user_prompt
        }

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

TRANSFORMATION TYPE: {transform_type.value if hasattr(transform_type, 'value') else transform_type}

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
