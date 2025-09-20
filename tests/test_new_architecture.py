"""
Test New Architecture

This module provides tests for the Phase 3 service-oriented architecture.
"""

import asyncio
import os
import sys
import unittest
from unittest.mock import Mock, patch

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.container import ServiceContainer
from src.models.book import Book, Chapter, Paragraph
from src.models.character import Character, CharacterAnalysis, Gender
from src.models.transformation import TransformType
from src.plugins.base import Plugin, PluginManager
from src.services.base import BaseService, ServiceConfig


class TestDomainModels(unittest.TestCase):
    """Test domain models."""

    def test_book_creation(self):
        """Test creating a Book object."""
        paragraph = Paragraph(sentences=["This is a test.", "Another sentence."])
        chapter = Chapter(number=1, title="Test Chapter", paragraphs=[paragraph])
        book = Book(title="Test Book", author="Test Author", chapters=[chapter])

        self.assertEqual(book.title, "Test Book")
        self.assertEqual(book.author, "Test Author")
        self.assertEqual(len(book.chapters), 1)
        self.assertEqual(book.word_count(), 6)

    def test_character_creation(self):
        """Test creating a Character object."""
        character = Character(
            name="Alice",
            gender=Gender.FEMALE,
            pronouns={"subject": "she", "object": "her", "possessive": "her"},
            importance="main",
        )

        self.assertEqual(character.name, "Alice")
        self.assertEqual(character.gender, Gender.FEMALE)
        self.assertEqual(character.pronouns["subject"], "she")

    def test_book_serialization(self):
        """Test Book serialization to/from dict."""
        paragraph = Paragraph(sentences=["Test sentence."])
        chapter = Chapter(number=1, title="Chapter 1", paragraphs=[paragraph])
        book = Book(title="Test", author="Author", chapters=[chapter])

        # Convert to dict
        book_dict = book.to_dict()
        self.assertIn("metadata", book_dict)
        self.assertIn("chapters", book_dict)

        # Convert back from dict
        book2 = Book.from_dict(book_dict)
        self.assertEqual(book2.title, book.title)
        self.assertEqual(book2.author, book.author)
        self.assertEqual(len(book2.chapters), len(book.chapters))


class TestServiceContainer(unittest.TestCase):
    """Test dependency injection container."""

    def setUp(self):
        """Set up test container."""
        self.container = ServiceContainer()

    def test_service_registration(self):
        """Test registering a service."""

        # Create a mock service class
        class MockService(BaseService):
            def _initialize(self):
                pass

            async def process_async(self, data):
                return data

        # Register service
        self.container.register("mock", MockService)

        # Check it's registered
        self.assertTrue(self.container.has("mock"))

    def test_service_retrieval(self):
        """Test getting a service instance."""

        # Create a mock service
        class MockService(BaseService):
            def _initialize(self):
                pass

            async def process_async(self, data):
                return data

        # Register and get service
        self.container.register("mock", MockService)
        service = self.container.get("mock")

        # Check it's the right type
        self.assertIsInstance(service, MockService)

        # Check singleton behavior
        service2 = self.container.get("mock")
        self.assertIs(service, service2)

    def test_dependency_injection(self):
        """Test service dependencies."""

        # Create mock services
        class ServiceA(BaseService):
            def _initialize(self):
                pass

            async def process_async(self, data):
                return f"A: {data}"

        class ServiceB(BaseService):
            def __init__(self, service_a, config=None):
                self.service_a = service_a
                super().__init__(config)

            def _initialize(self):
                pass

            async def process_async(self, data):
                result_a = await self.service_a.process_async(data)
                return f"B: {result_a}"

        # Register with dependency
        self.container.register("service_a", ServiceA)
        self.container.register("service_b", ServiceB, dependencies={"service_a": "service_a"})

        # Get service B
        service_b = self.container.get("service_b")

        # Check dependency was injected
        self.assertIsNotNone(service_b.service_a)
        self.assertIsInstance(service_b.service_a, ServiceA)


class TestPluginSystem(unittest.TestCase):
    """Test plugin system."""

    def setUp(self):
        """Set up test plugin manager."""
        self.manager = PluginManager()

    def test_plugin_registration(self):
        """Test registering a plugin."""

        # Create a mock plugin
        class MockPlugin(Plugin):
            @property
            def name(self):
                return "mock"

            @property
            def version(self):
                return "1.0.0"

            def initialize(self, config):
                self.initialized = True

            def execute(self, context):
                return "executed"

        # Register plugin
        plugin = MockPlugin()
        self.manager.register(plugin)

        # Check it's registered
        self.assertIn("mock", self.manager.plugins)
        self.assertTrue(plugin.initialized)

    def test_plugin_execution(self):
        """Test executing a plugin."""

        # Create and register mock plugin
        class MockPlugin(Plugin):
            @property
            def name(self):
                return "mock"

            @property
            def version(self):
                return "1.0.0"

            def initialize(self, config):
                pass

            def execute(self, context):
                return context.get("value", 0) * 2

        plugin = MockPlugin()
        self.manager.register(plugin)

        # Execute plugin
        result = self.manager.execute("mock", {"value": 5})
        self.assertEqual(result, 10)


class TestAsyncServices(unittest.TestCase):
    """Test async service operations."""

    def test_async_service_execution(self):
        """Test async service execution."""

        # Create an async service
        class AsyncService(BaseService):
            def _initialize(self):
                self.call_count = 0

            async def process_async(self, data):
                self.call_count += 1
                await asyncio.sleep(0.01)  # Simulate async work
                return data * 2

        # Create and test service
        service = AsyncService()

        # Test async execution
        async def test():
            result = await service.process_async(5)
            return result

        result = asyncio.run(test())
        self.assertEqual(result, 10)
        self.assertEqual(service.call_count, 1)

    def test_sync_wrapper(self):
        """Test sync wrapper for async service."""

        # Create an async service
        class AsyncService(BaseService):
            def _initialize(self):
                pass

            async def process_async(self, data):
                await asyncio.sleep(0.01)
                return data + 1

        # Test sync wrapper - should work in non-async context
        service = AsyncService()
        with self.assertWarns(DeprecationWarning):
            result = service.process(10)
        self.assertEqual(result, 11)

    def test_sync_wrapper_in_async_context_fails(self):
        """Test that sync wrapper properly fails when called from async context."""

        # Create an async service
        class AsyncService(BaseService):
            def _initialize(self):
                pass

            async def process_async(self, data):
                return data + 1

        # Test that calling sync method from async context raises error
        async def test_in_async_context():
            service = AsyncService()
            with self.assertRaises(RuntimeError) as cm:
                service.process(10)  # This should fail

            self.assertIn("cannot be called from an async context", str(cm.exception))
            self.assertIn("Use 'await service.process_async(data)' instead", str(cm.exception))

        # Run the async test
        asyncio.run(test_in_async_context())


class TestIntegration(unittest.TestCase):
    """Integration tests for the new architecture."""

    def test_service_metrics(self):
        """Test service metrics collection."""

        # Create a service
        class MetricService(BaseService):
            def _initialize(self):
                self.process_count = 0

            async def process_async(self, data):
                self.process_count += 1
                return data

            def get_metrics(self):
                metrics = super().get_metrics()
                metrics["process_count"] = self.process_count
                return metrics

        # Test metrics
        service = MetricService()
        asyncio.run(service.process_async("test"))

        metrics = service.get_metrics()
        self.assertIn("service", metrics)
        self.assertIn("process_count", metrics)
        self.assertEqual(metrics["process_count"], 1)


if __name__ == "__main__":
    # Run tests
    unittest.main()
