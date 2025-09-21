"""
Transform Service

This service handles gender transformation of books.
"""

import asyncio
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
from src.strategies.transform import SmartTransformStrategy, TransformStrategy
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
        Initialize transform service.

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
        Transform a book's gender representation.

        Args:
            data: Dictionary containing:
                - book: Book object
                - transform_type: TransformType or string
                - characters: Optional CharacterAnalysis

        Returns:
            Transformation result
        """
        # Extract parameters
        book = data.get("book")
        if not isinstance(book, Book):
            raise ValueError("'book' must be a Book object")

        transform_type = data.get("transform_type")
        if isinstance(transform_type, str):
            transform_type = TransformType(transform_type)
        elif not isinstance(transform_type, TransformType):
            raise ValueError("'transform_type' must be a TransformType or string")

        characters = data.get("characters")

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

        Returns:
            Transformation object with results
        """
        start_time = time.time()

        try:
            # Get character analysis if not provided
            if not characters:
                if not self.character_service:
                    raise ValueError("Character service required when characters not provided")

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

        except Exception as e:
            import traceback

            self.logger.error(f"Transform error: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            self.handle_error(e, {"book_title": book.title, "transform_type": transform_type.value})

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
        """Get transformation mappings for a specific character."""
        from src.models.character import Gender

        mappings = {"original_gender": character.gender}

        if transform_type == TransformType.ALL_MALE:
            mappings["new_gender"] = Gender.MALE
            mappings["pronouns"] = {"subject": "he", "object": "him", "possessive": "his"}
        elif transform_type == TransformType.ALL_FEMALE:
            mappings["new_gender"] = Gender.FEMALE
            mappings["pronouns"] = {"subject": "she", "object": "her", "possessive": "her"}
        elif transform_type == TransformType.GENDER_SWAP:
            if character.gender == Gender.MALE:
                mappings["new_gender"] = Gender.FEMALE
                mappings["pronouns"] = {"subject": "she", "object": "her", "possessive": "her"}
            elif character.gender == Gender.FEMALE:
                mappings["new_gender"] = Gender.MALE
                mappings["pronouns"] = {"subject": "he", "object": "him", "possessive": "his"}
            else:
                mappings["new_gender"] = character.gender
                mappings["pronouns"] = character.pronouns

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

        # Transform paragraphs in batches for efficiency
        # Smaller batches for more reliable processing
        batch_size = getattr(self.config, 'batch_size', 10)  # Default to 10 paragraphs at a time
        total_paragraphs = len(chapter.paragraphs)
        total_batches = (total_paragraphs + batch_size - 1) // batch_size
        self.logger.info(f"Processing {total_paragraphs} paragraphs in {total_batches} batches of {batch_size}")

        for batch_num, batch_start in enumerate(range(0, total_paragraphs, batch_size), 1):
            batch_end = min(batch_start + batch_size, total_paragraphs)
            batch_paragraphs = chapter.paragraphs[batch_start:batch_end]

            self.logger.info(f"Processing batch {batch_num}/{total_batches} (paragraphs {batch_start+1}-{batch_end})")

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

            except Exception as e:
                self.logger.warning(f"Failed to transform batch {batch_start}-{batch_end}: {e}")
                # Keep originals on error
                for paragraph in batch_paragraphs:
                    transformed_paragraphs.append(paragraph)

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

    def _create_batch_transform_prompt(self, batch_paragraphs: list, context: dict[str, Any], batch_size: int) -> dict[str, str]:
        """Create prompt for batch transformation."""
        transform_type = context.get("transform_type", TransformType.GENDER_SWAP)
        rules = context.get("rules", self._get_transformation_rules(transform_type))
        character_context = context.get("character_context", "")

        system_prompt = f"""You are a literary transformation expert. Transform the following {batch_size} paragraphs according to these rules:

{rules}

{character_context}

IMPORTANT:
1. Transform each paragraph independently
2. Return EXACTLY {batch_size} paragraphs
3. Separate each paragraph with a blank line (double newline)
4. Maintain the original style and tone
5. Only change gender-related language
6. Do not add or remove content
7. Do not add any markers or labels - just the transformed text"""

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
