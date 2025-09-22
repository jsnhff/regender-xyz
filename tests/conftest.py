"""
Pytest configuration and fixtures for testing.
"""
import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest


class MockLLMProvider:
    """Mock LLM provider for testing without API calls."""

    def __init__(self):
        self.name = "mock"
        self.model = "mock-model"
        self.supports_json = True
        self.calls = []

    async def complete_async(self, messages, **kwargs):
        """Mock LLM completion that returns gender-swapped text."""
        # Track the call
        self.calls.append({"messages": messages, "kwargs": kwargs})

        # Extract the user message
        user_msg = messages[-1]["content"] if messages else ""

        # Simple mock transformations based on content
        if "analyze characters" in user_msg.lower():
            # Return mock character analysis
            return json.dumps({
                "characters": [
                    {"name": "James Wilson", "gender": "male", "importance": 10},
                    {"name": "Sarah Chen", "gender": "female", "importance": 8}
                ]
            })
        elif "gender" in user_msg.lower() and "swap" in user_msg.lower():
            # Return gender-swapped version
            response = user_msg.replace("Mr.", "Ms.")
            response = response.replace("James", "Jamie")
            response = response.replace(" he ", " she ")
            response = response.replace(" him ", " her ")
            response = response.replace(" his ", " her ")
            response = response.replace("He ", "She ")
            response = response.replace("His ", "Her ")
            return response
        else:
            # Default response
            return "Mocked response"

    def complete(self, messages, **kwargs):
        """Synchronous version for compatibility."""
        import asyncio
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(self.complete_async(messages, **kwargs))


@pytest.fixture
def mock_llm():
    """Provide a mock LLM instance."""
    return MockLLMProvider()


@pytest.fixture
def app_with_mock(mock_llm):
    """Create an Application instance with mock LLM provider."""
    from src.app import Application
    from src.container import ApplicationContext

    # Create context and app
    context = ApplicationContext()
    context.initialize()

    # Register mock provider
    context.register_instance("llm_provider", mock_llm)

    # Create app with this context
    app = Application(context=context)

    return app


@pytest.fixture
def test_fixtures_dir():
    """Path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def simple_story_path(test_fixtures_dir):
    """Path to simple test story."""
    return str(test_fixtures_dir / "simple_story.txt")
