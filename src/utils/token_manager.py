"""
Token Management System

Provides centralized token estimation, chunking, and tracking for different LLM providers.
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Track token usage for cost calculation and monitoring."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    model: Optional[str] = None
    provider: Optional[str] = None

    def __post_init__(self):
        """Calculate total if not provided."""
        if self.total_tokens == 0:
            self.total_tokens = self.input_tokens + self.output_tokens

    def add(self, other: "TokenUsage") -> "TokenUsage":
        """Add two TokenUsage objects."""
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            estimated_cost=self.estimated_cost + other.estimated_cost,
            model=self.model or other.model,
            provider=self.provider or other.provider,
        )


@dataclass
class ModelConfig:
    """Configuration for a specific model's token handling."""

    name: str
    chars_per_token: float
    max_context_tokens: int
    input_cost_per_1k: float = 0.0
    output_cost_per_1k: float = 0.0
    preferred_chunk_size: int = 4000
    overlap_tokens: int = 200


@dataclass
class TextChunk:
    """A chunk of text with metadata."""

    text: str
    estimated_tokens: int
    start_position: int
    end_position: int
    chunk_index: int
    overlap_start: Optional[int] = None
    overlap_end: Optional[int] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def has_overlap(self) -> bool:
        """Check if chunk has overlap with adjacent chunks."""
        return self.overlap_start is not None or self.overlap_end is not None


class TextSplitter(ABC):
    """Abstract base class for text splitting strategies."""

    @abstractmethod
    def split_text(self, text: str, max_tokens: int, estimator: "TokenEstimator") -> list[str]:
        """Split text into chunks respecting boundaries."""
        pass


class SentenceSplitter(TextSplitter):
    """Split text at sentence boundaries."""

    def __init__(self, min_chunk_size: int = 100):
        """
        Initialize sentence splitter.

        Args:
            min_chunk_size: Minimum tokens per chunk (avoid tiny chunks)
        """
        self.min_chunk_size = min_chunk_size
        # Improved sentence splitting regex
        self.sentence_pattern = re.compile(
            r'(?<=[.!?])\s+(?=[A-Z])|(?<=[.!?]")\s+(?=[A-Z])|(?<=[.!?]\')\s+(?=[A-Z])'
        )

    def split_text(self, text: str, max_tokens: int, estimator: "TokenEstimator") -> list[str]:
        """Split text at sentence boundaries."""
        # Split into sentences
        sentences = self.sentence_pattern.split(text)
        if not sentences:
            return [text] if text.strip() else []

        chunks = []
        current_chunk = []
        current_tokens = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_tokens = estimator.estimate_tokens(sentence)

            # If single sentence exceeds max_tokens, split it at word boundaries
            if sentence_tokens > max_tokens:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []
                    current_tokens = 0

                # Split long sentence at word boundaries
                word_chunks = self._split_long_sentence(sentence, max_tokens, estimator)
                chunks.extend(word_chunks)
                continue

            # Check if adding sentence would exceed limit
            if current_tokens + sentence_tokens > max_tokens and current_chunk:
                # Only create chunk if it meets minimum size
                if current_tokens >= self.min_chunk_size:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []
                    current_tokens = 0
                else:
                    # If current chunk is too small, try to add one more sentence
                    # even if it slightly exceeds the limit
                    pass

            current_chunk.append(sentence)
            current_tokens += sentence_tokens

        # Add remaining chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def _split_long_sentence(
        self, sentence: str, max_tokens: int, estimator: "TokenEstimator"
    ) -> list[str]:
        """Split a sentence that's too long at word boundaries."""
        words = sentence.split()
        chunks = []
        current_chunk = []
        current_tokens = 0

        for word in words:
            word_tokens = estimator.estimate_tokens(word + " ")

            if current_tokens + word_tokens > max_tokens and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_tokens = 0

            current_chunk.append(word)
            current_tokens += word_tokens

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks


class ParagraphSplitter(TextSplitter):
    """Split text at paragraph boundaries."""

    def __init__(self, min_chunk_size: int = 100):
        """
        Initialize paragraph splitter.

        Args:
            min_chunk_size: Minimum tokens per chunk
        """
        self.min_chunk_size = min_chunk_size
        self.sentence_splitter = SentenceSplitter(min_chunk_size)

    def split_text(self, text: str, max_tokens: int, estimator: "TokenEstimator") -> list[str]:
        """Split text at paragraph boundaries, falling back to sentences."""
        # Split into paragraphs (double newline or more)
        paragraphs = re.split(r"\n\s*\n", text)
        if not paragraphs:
            return [text] if text.strip() else []

        chunks = []
        current_chunk = []
        current_tokens = 0

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            para_tokens = estimator.estimate_tokens(paragraph)

            # If single paragraph exceeds max_tokens, split it at sentence boundaries
            if para_tokens > max_tokens:
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_tokens = 0

                # Split paragraph using sentence splitter
                sentence_chunks = self.sentence_splitter.split_text(
                    paragraph, max_tokens, estimator
                )
                chunks.extend(sentence_chunks)
                continue

            # Check if adding paragraph would exceed limit
            if (
                current_tokens + para_tokens > max_tokens
                and current_chunk
                and current_tokens >= self.min_chunk_size
            ):
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_tokens = 0

            current_chunk.append(paragraph)
            current_tokens += para_tokens

        # Add remaining chunk
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks


class TokenEstimator:
    """Estimates tokens for different models."""

    def __init__(self, model_config: ModelConfig):
        """
        Initialize token estimator.

        Args:
            model_config: Configuration for the model
        """
        self.config = model_config

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate tokens for given text.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        if not text:
            return 0

        # Basic estimation based on character count
        estimated = len(text) / self.config.chars_per_token

        # Add small buffer for safety (5%)
        return int(estimated * 1.05)

    def estimate_cost(self, input_tokens: int, output_tokens: int = 0) -> float:
        """
        Estimate cost for token usage.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in dollars
        """
        input_cost = (input_tokens / 1000) * self.config.input_cost_per_1k
        output_cost = (output_tokens / 1000) * self.config.output_cost_per_1k
        return input_cost + output_cost

    def fits_in_context(self, text: str, reserve_tokens: int = 500) -> bool:
        """
        Check if text fits in model's context window.

        Args:
            text: Text to check
            reserve_tokens: Tokens to reserve for response

        Returns:
            True if text fits
        """
        tokens = self.estimate_tokens(text)
        return tokens + reserve_tokens <= self.config.max_context_tokens


class TokenManager:
    """
    Centralized token management system.

    Provides consistent token estimation, intelligent text chunking,
    and usage tracking across different LLM providers.
    """

    # Predefined model configurations
    MODEL_CONFIGS = {
        "gpt-4": ModelConfig(
            name="gpt-4",
            chars_per_token=3.5,  # More conservative for GPT-4
            max_context_tokens=8192,
            input_cost_per_1k=0.03,
            output_cost_per_1k=0.06,
            preferred_chunk_size=4000,
            overlap_tokens=200,
        ),
        "gpt-4-turbo": ModelConfig(
            name="gpt-4-turbo",
            chars_per_token=3.5,
            max_context_tokens=128000,
            input_cost_per_1k=0.01,
            output_cost_per_1k=0.03,
            preferred_chunk_size=6000,
            overlap_tokens=300,
        ),
        "gpt-3.5-turbo": ModelConfig(
            name="gpt-3.5-turbo",
            chars_per_token=4.0,
            max_context_tokens=16384,
            input_cost_per_1k=0.001,
            output_cost_per_1k=0.002,
            preferred_chunk_size=4000,
            overlap_tokens=200,
        ),
        "claude-3-sonnet": ModelConfig(
            name="claude-3-sonnet",
            chars_per_token=3.8,
            max_context_tokens=200000,
            input_cost_per_1k=0.003,
            output_cost_per_1k=0.015,
            preferred_chunk_size=8000,
            overlap_tokens=400,
        ),
        "claude-3-haiku": ModelConfig(
            name="claude-3-haiku",
            chars_per_token=4.0,
            max_context_tokens=200000,
            input_cost_per_1k=0.00025,
            output_cost_per_1k=0.00125,
            preferred_chunk_size=6000,
            overlap_tokens=300,
        ),
        "claude-3-opus": ModelConfig(
            name="claude-3-opus",
            chars_per_token=3.5,
            max_context_tokens=200000,
            input_cost_per_1k=0.015,
            output_cost_per_1k=0.075,
            preferred_chunk_size=10000,
            overlap_tokens=500,
        ),
    }

    def __init__(
        self,
        model_name: str = "gpt-4",
        custom_config: Optional[ModelConfig] = None,
        splitter: Optional[TextSplitter] = None,
    ):
        """
        Initialize token manager.

        Args:
            model_name: Name of the model to use
            custom_config: Custom model configuration
            splitter: Text splitter strategy
        """
        if custom_config:
            self.config = custom_config
        elif model_name in self.MODEL_CONFIGS:
            self.config = self.MODEL_CONFIGS[model_name]
        else:
            logger.warning(f"Unknown model {model_name}, using gpt-4 config")
            self.config = self.MODEL_CONFIGS["gpt-4"]

        self.estimator = TokenEstimator(self.config)
        self.splitter = splitter or ParagraphSplitter()
        self.usage_history: list[TokenUsage] = []

        logger.info(f"Initialized TokenManager for {self.config.name}")

    @classmethod
    def for_provider(cls, provider_name: str, model_name: str = None) -> "TokenManager":
        """
        Create TokenManager for a specific provider.

        Args:
            provider_name: Name of the provider ('openai', 'anthropic')
            model_name: Specific model name (optional)

        Returns:
            Configured TokenManager
        """
        provider_lower = provider_name.lower()

        if provider_lower == "openai":
            default_model = model_name or "gpt-4"
        elif provider_lower == "anthropic":
            default_model = model_name or "claude-3-sonnet"
        else:
            logger.warning(f"Unknown provider {provider_name}, using gpt-4")
            default_model = "gpt-4"

        return cls(model_name=default_model)

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate tokens for given text.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        return self.estimator.estimate_tokens(text)

    def chunk_text(
        self,
        text: str,
        max_tokens: Optional[int] = None,
        overlap_tokens: Optional[int] = None,
        preserve_boundaries: bool = True,
    ) -> list[TextChunk]:
        """
        Intelligently chunk text respecting boundaries.

        Args:
            text: Text to chunk
            max_tokens: Maximum tokens per chunk (uses config default if None)
            overlap_tokens: Tokens to overlap between chunks (uses config default if None)
            preserve_boundaries: Whether to preserve sentence/paragraph boundaries

        Returns:
            List of text chunks with metadata
        """
        if not text.strip():
            return []

        max_tokens = max_tokens or self.config.preferred_chunk_size
        overlap_tokens = overlap_tokens or self.config.overlap_tokens

        # Get raw text chunks
        if preserve_boundaries:
            raw_chunks = self.splitter.split_text(text, max_tokens, self.estimator)
        else:
            # Fallback to simple character-based chunking
            raw_chunks = self._simple_chunk(text, max_tokens)

        # Convert to TextChunk objects with overlap
        chunks = []
        total_position = 0

        for i, chunk_text in enumerate(raw_chunks):
            estimated_tokens = self.estimator.estimate_tokens(chunk_text)

            # Calculate positions
            start_pos = total_position
            end_pos = start_pos + len(chunk_text)

            # Add overlap for context continuity (except for first/last chunks)
            overlap_start = None
            overlap_end = None

            if i > 0 and overlap_tokens > 0:
                # Add overlap from previous chunk
                prev_chunk = raw_chunks[i - 1]
                overlap_text = self._get_overlap_text(prev_chunk, overlap_tokens, from_end=True)
                if overlap_text:
                    chunk_text = overlap_text + " " + chunk_text
                    overlap_start = len(overlap_text)

            if i < len(raw_chunks) - 1 and overlap_tokens > 0:
                # Add overlap to next chunk (we'll handle this in next iteration)
                pass

            chunk = TextChunk(
                text=chunk_text,
                estimated_tokens=self.estimator.estimate_tokens(chunk_text),
                start_position=start_pos,
                end_position=end_pos,
                chunk_index=i,
                overlap_start=overlap_start,
                overlap_end=overlap_end,
                metadata={
                    "original_tokens": estimated_tokens,
                    "has_prefix_overlap": overlap_start is not None,
                    "model": self.config.name,
                },
            )

            chunks.append(chunk)
            total_position = end_pos

        logger.debug(f"Created {len(chunks)} chunks from {len(text)} characters")
        return chunks

    def _simple_chunk(self, text: str, max_tokens: int) -> list[str]:
        """Simple character-based chunking as fallback."""
        max_chars = int(max_tokens * self.config.chars_per_token)
        chunks = []

        for i in range(0, len(text), max_chars):
            chunk = text[i : i + max_chars]
            chunks.append(chunk)

        return chunks

    def _get_overlap_text(self, text: str, overlap_tokens: int, from_end: bool = True) -> str:
        """Extract overlap text from beginning or end of a chunk."""
        overlap_chars = int(overlap_tokens * self.config.chars_per_token)

        if from_end:
            # Get text from the end
            if len(text) <= overlap_chars:
                return text
            overlap_text = text[-overlap_chars:]
            # Try to break at word boundary
            space_idx = overlap_text.find(" ")
            if space_idx > 0:
                return overlap_text[space_idx + 1 :]
            return overlap_text
        else:
            # Get text from the beginning
            if len(text) <= overlap_chars:
                return text
            overlap_text = text[:overlap_chars]
            # Try to break at word boundary
            space_idx = overlap_text.rfind(" ")
            if space_idx > 0:
                return overlap_text[:space_idx]
            return overlap_text

    def track_usage(
        self,
        input_tokens: int,
        output_tokens: int = 0,
        model: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> TokenUsage:
        """
        Track token usage for monitoring and cost calculation.

        Args:
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens generated
            model: Model name (uses config default if None)
            provider: Provider name

        Returns:
            TokenUsage object with cost calculation
        """
        model = model or self.config.name
        estimated_cost = self.estimator.estimate_cost(input_tokens, output_tokens)

        usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost=estimated_cost,
            model=model,
            provider=provider,
        )

        self.usage_history.append(usage)
        return usage

    def get_total_usage(self) -> TokenUsage:
        """
        Get total token usage across all tracked calls.

        Returns:
            Aggregated TokenUsage
        """
        if not self.usage_history:
            return TokenUsage()

        total = self.usage_history[0]
        for usage in self.usage_history[1:]:
            total = total.add(usage)

        return total

    def get_usage_stats(self) -> dict[str, Any]:
        """
        Get detailed usage statistics.

        Returns:
            Dictionary with usage statistics
        """
        total_usage = self.get_total_usage()

        return {
            "total_calls": len(self.usage_history),
            "total_input_tokens": total_usage.input_tokens,
            "total_output_tokens": total_usage.output_tokens,
            "total_tokens": total_usage.total_tokens,
            "estimated_total_cost": total_usage.estimated_cost,
            "average_tokens_per_call": (
                total_usage.total_tokens / len(self.usage_history) if self.usage_history else 0
            ),
            "model": self.config.name,
            "recent_calls": self.usage_history[-5:] if self.usage_history else [],
        }

    def fits_in_context(self, text: str, reserve_tokens: int = 500) -> bool:
        """
        Check if text fits in model's context window.

        Args:
            text: Text to check
            reserve_tokens: Tokens to reserve for response

        Returns:
            True if text fits
        """
        return self.estimator.fits_in_context(text, reserve_tokens)

    def get_model_info(self) -> dict[str, Any]:
        """
        Get information about the current model configuration.

        Returns:
            Dictionary with model info
        """
        return {
            "name": self.config.name,
            "chars_per_token": self.config.chars_per_token,
            "max_context_tokens": self.config.max_context_tokens,
            "preferred_chunk_size": self.config.preferred_chunk_size,
            "overlap_tokens": self.config.overlap_tokens,
            "input_cost_per_1k": self.config.input_cost_per_1k,
            "output_cost_per_1k": self.config.output_cost_per_1k,
        }

    def clear_usage_history(self) -> None:
        """Clear usage tracking history."""
        self.usage_history.clear()
        logger.info("Cleared token usage history")
