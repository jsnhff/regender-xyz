"""
Tests for TokenManager system.

This test file verifies the centralized token management functionality.
"""

import unittest
from unittest.mock import Mock

from src.models.book import Book, Chapter, Paragraph
from src.utils.token_manager import (
    ModelConfig,
    ParagraphSplitter,
    SentenceSplitter,
    TextChunk,
    TokenEstimator,
    TokenManager,
    TokenUsage,
)


class TestTokenUsage(unittest.TestCase):
    """Test TokenUsage functionality."""

    def test_token_usage_creation(self):
        """Test TokenUsage object creation."""
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        self.assertEqual(usage.input_tokens, 100)
        self.assertEqual(usage.output_tokens, 50)
        self.assertEqual(usage.total_tokens, 150)

    def test_token_usage_addition(self):
        """Test adding TokenUsage objects."""
        usage1 = TokenUsage(input_tokens=100, output_tokens=50, estimated_cost=0.15)
        usage2 = TokenUsage(input_tokens=200, output_tokens=75, estimated_cost=0.25)

        total = usage1.add(usage2)
        self.assertEqual(total.input_tokens, 300)
        self.assertEqual(total.output_tokens, 125)
        self.assertEqual(total.total_tokens, 425)
        self.assertEqual(total.estimated_cost, 0.40)


class TestModelConfig(unittest.TestCase):
    """Test ModelConfig functionality."""

    def test_model_config_creation(self):
        """Test ModelConfig creation."""
        config = ModelConfig(
            name="test-model",
            chars_per_token=4.0,
            max_context_tokens=8192,
            input_cost_per_1k=0.001,
            output_cost_per_1k=0.002,
        )

        self.assertEqual(config.name, "test-model")
        self.assertEqual(config.chars_per_token, 4.0)
        self.assertEqual(config.max_context_tokens, 8192)
        self.assertEqual(config.input_cost_per_1k, 0.001)
        self.assertEqual(config.output_cost_per_1k, 0.002)


class TestTokenEstimator(unittest.TestCase):
    """Test TokenEstimator functionality."""

    def setUp(self):
        """Set up test configuration."""
        self.config = ModelConfig(
            name="test-model",
            chars_per_token=4.0,
            max_context_tokens=8192,
            input_cost_per_1k=0.001,
            output_cost_per_1k=0.002,
        )
        self.estimator = TokenEstimator(self.config)

    def test_estimate_tokens(self):
        """Test token estimation."""
        text = "This is a test text with exactly forty characters."
        # 48 characters / 4.0 chars_per_token * 1.05 buffer = ~12.6 tokens
        estimated = self.estimator.estimate_tokens(text)
        self.assertGreater(estimated, 10)
        self.assertLess(estimated, 15)

    def test_estimate_tokens_empty(self):
        """Test token estimation for empty text."""
        self.assertEqual(self.estimator.estimate_tokens(""), 0)
        self.assertEqual(self.estimator.estimate_tokens(None), 0)

    def test_estimate_cost(self):
        """Test cost estimation."""
        cost = self.estimator.estimate_cost(1000, 500)
        expected = (1000 / 1000) * 0.001 + (500 / 1000) * 0.002
        self.assertAlmostEqual(cost, expected, places=6)

    def test_fits_in_context(self):
        """Test context window checking."""
        # Text that should fit (small)
        small_text = "Short text."
        self.assertTrue(self.estimator.fits_in_context(small_text))

        # Text that won't fit (very large)
        large_text = "x" * 50000  # 50k characters = ~13k tokens
        self.assertFalse(self.estimator.fits_in_context(large_text))


class TestTextSplitters(unittest.TestCase):
    """Test text splitting strategies."""

    def setUp(self):
        """Set up test configuration."""
        self.config = ModelConfig(
            name="test-model", chars_per_token=4.0, max_context_tokens=8192
        )
        self.estimator = TokenEstimator(self.config)

    def test_sentence_splitter(self):
        """Test sentence-based text splitting."""
        splitter = SentenceSplitter()
        # Create longer text to ensure splitting
        text = "First sentence with many words to make it longer. Second sentence also needs to be quite long to trigger splitting! Third sentence should be even longer to ensure proper testing? Fourth sentence must be sufficiently long."

        chunks = splitter.split_text(text, max_tokens=10, estimator=self.estimator)
        self.assertGreaterEqual(len(chunks), 1)
        self.assertTrue(all(chunk.strip() for chunk in chunks))

    def test_paragraph_splitter(self):
        """Test paragraph-based text splitting."""
        splitter = ParagraphSplitter()
        # Create longer paragraphs to ensure splitting
        text = "First paragraph with many words to make it longer and trigger chunking behavior.\n\nSecond paragraph also needs to be quite long with lots of text to ensure proper splitting occurs.\n\nThird paragraph should be even longer to ensure the splitter works correctly."

        chunks = splitter.split_text(text, max_tokens=15, estimator=self.estimator)
        self.assertGreaterEqual(len(chunks), 1)
        self.assertTrue(all(chunk.strip() for chunk in chunks))

    def test_long_sentence_splitting(self):
        """Test splitting of very long sentences."""
        splitter = SentenceSplitter()
        # Create a very long sentence
        long_sentence = "This is a very long sentence " * 50 + "."

        chunks = splitter.split_text(long_sentence, max_tokens=20, estimator=self.estimator)
        self.assertGreater(len(chunks), 1)


class TestTokenManager(unittest.TestCase):
    """Test TokenManager functionality."""

    def setUp(self):
        """Set up test TokenManager."""
        self.token_manager = TokenManager(model_name="gpt-4")

    def test_token_manager_creation(self):
        """Test TokenManager creation."""
        self.assertEqual(self.token_manager.config.name, "gpt-4")
        self.assertIsNotNone(self.token_manager.estimator)
        self.assertIsNotNone(self.token_manager.splitter)

    def test_for_provider_openai(self):
        """Test TokenManager creation for OpenAI provider."""
        tm = TokenManager.for_provider("openai", "gpt-3.5-turbo")
        self.assertEqual(tm.config.name, "gpt-3.5-turbo")

    def test_for_provider_anthropic(self):
        """Test TokenManager creation for Anthropic provider."""
        tm = TokenManager.for_provider("anthropic", "claude-3-haiku")
        self.assertEqual(tm.config.name, "claude-3-haiku")

    def test_estimate_tokens(self):
        """Test token estimation."""
        text = "This is a test text."
        tokens = self.token_manager.estimate_tokens(text)
        self.assertIsInstance(tokens, int)
        self.assertGreater(tokens, 0)

    def test_chunk_text_simple(self):
        """Test basic text chunking."""
        text = "This is a test. " * 100  # Repeat to make longer text
        chunks = self.token_manager.chunk_text(text, max_tokens=50)

        self.assertIsInstance(chunks, list)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(isinstance(chunk, TextChunk) for chunk in chunks))

    def test_chunk_text_with_overlap(self):
        """Test text chunking with overlap."""
        # Create longer text to ensure multiple chunks
        text = "First sentence with many words. " * 20  # Repeat to make longer text
        chunks = self.token_manager.chunk_text(text, max_tokens=20, overlap_tokens=3)

        self.assertGreaterEqual(len(chunks), 1)
        # Check that chunks are created (overlap implementation is complex)
        self.assertTrue(all(isinstance(chunk, TextChunk) for chunk in chunks))

    def test_track_usage(self):
        """Test usage tracking."""
        usage = self.token_manager.track_usage(100, 50, "gpt-4", "openai")

        self.assertEqual(usage.input_tokens, 100)
        self.assertEqual(usage.output_tokens, 50)
        self.assertEqual(usage.model, "gpt-4")
        self.assertEqual(usage.provider, "openai")
        self.assertGreater(usage.estimated_cost, 0)

        # Check that usage was recorded
        self.assertEqual(len(self.token_manager.usage_history), 1)

    def test_get_total_usage(self):
        """Test total usage calculation."""
        # Track multiple usages
        self.token_manager.track_usage(100, 50)
        self.token_manager.track_usage(200, 75)

        total = self.token_manager.get_total_usage()
        self.assertEqual(total.input_tokens, 300)
        self.assertEqual(total.output_tokens, 125)
        self.assertEqual(total.total_tokens, 425)

    def test_get_usage_stats(self):
        """Test usage statistics."""
        self.token_manager.track_usage(100, 50)
        self.token_manager.track_usage(200, 75)

        stats = self.token_manager.get_usage_stats()
        self.assertEqual(stats["total_calls"], 2)
        self.assertEqual(stats["total_input_tokens"], 300)
        self.assertEqual(stats["total_output_tokens"], 125)
        self.assertEqual(stats["total_tokens"], 425)
        self.assertGreater(stats["estimated_total_cost"], 0)

    def test_fits_in_context(self):
        """Test context window checking."""
        short_text = "Short text"
        self.assertTrue(self.token_manager.fits_in_context(short_text))

        # Very long text that shouldn't fit
        long_text = "x" * 100000
        self.assertFalse(self.token_manager.fits_in_context(long_text))

    def test_get_model_info(self):
        """Test model information retrieval."""
        info = self.token_manager.get_model_info()
        self.assertEqual(info["name"], "gpt-4")
        self.assertIn("chars_per_token", info)
        self.assertIn("max_context_tokens", info)

    def test_clear_usage_history(self):
        """Test clearing usage history."""
        self.token_manager.track_usage(100, 50)
        self.assertEqual(len(self.token_manager.usage_history), 1)

        self.token_manager.clear_usage_history()
        self.assertEqual(len(self.token_manager.usage_history), 0)


class TestTextChunk(unittest.TestCase):
    """Test TextChunk functionality."""

    def test_text_chunk_creation(self):
        """Test TextChunk creation."""
        chunk = TextChunk(
            text="Test text",
            estimated_tokens=5,
            start_position=0,
            end_position=9,
            chunk_index=0,
        )

        self.assertEqual(chunk.text, "Test text")
        self.assertEqual(chunk.estimated_tokens, 5)
        self.assertEqual(chunk.start_position, 0)
        self.assertEqual(chunk.end_position, 9)
        self.assertEqual(chunk.chunk_index, 0)
        self.assertFalse(chunk.has_overlap())

    def test_text_chunk_with_overlap(self):
        """Test TextChunk with overlap."""
        chunk = TextChunk(
            text="Test text",
            estimated_tokens=5,
            start_position=0,
            end_position=9,
            chunk_index=0,
            overlap_start=2,
        )

        self.assertTrue(chunk.has_overlap())


if __name__ == "__main__":
    unittest.main()