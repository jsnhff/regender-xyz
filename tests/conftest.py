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

    async def complete(self, messages, **kwargs):
        """Mock LLM completion that returns gender-swapped text.

        Matches the real provider interface (``async def complete``) so that
        services awaiting ``provider.complete(...)`` exercise the same code path
        they would in production.
        """
        # Track the call
        self.calls.append({"messages": messages, "kwargs": kwargs})

        # Extract the user message
        user_msg = messages[-1]["content"] if messages else ""

        # Simple mock transformations based on content.
        #
        # "extract all characters" is what the real extraction prompt opens
        # with; the older "analyze characters" matched nothing it ever sent, so
        # extraction fell through to "Mocked response", the parser returned its
        # empty fallback, and the integration tests ran the whole pipeline
        # against a cast of nobody -- with a comment saying that was fine.
        lowered = user_msg.lower()
        if "extract all characters" in lowered or "analyze characters" in lowered:
            # Return mock character analysis
            return json.dumps(
                {
                    "characters": [
                        {
                            "name": "James Wilson",
                            "gender": "male",
                            "pronouns": "he/him",
                            "description": "a man in a story",
                            "aliases": ["James"],
                            "titles": ["Mr"],
                        },
                        {
                            "name": "Sarah Chen",
                            "gender": "female",
                            "pronouns": "she/her",
                            "description": "a woman in a story",
                            "aliases": ["Sarah"],
                            "titles": [],
                        },
                    ]
                }
            )
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

    # Backwards-compatible alias for any caller using the old name.
    complete_async = complete


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
