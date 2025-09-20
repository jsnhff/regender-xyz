"""Pytest configuration and shared fixtures."""

import os
from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_openai_key():
    """Mock OpenAI API key for testing."""
    return "sk-test1234567890abcdef1234567890abcdef12345678901234567890"


@pytest.fixture
def mock_anthropic_key():
    """Mock Anthropic API key for testing."""
    return "sk-ant-test1234567890abcdef1234567890abcdef1234567890"


@pytest.fixture
def mock_env_keys(monkeypatch, mock_openai_key, mock_anthropic_key):
    """Mock environment variables for API keys."""
    monkeypatch.setenv("OPENAI_API_KEY", mock_openai_key)
    monkeypatch.setenv("ANTHROPIC_API_KEY", mock_anthropic_key)
    monkeypatch.setenv("DEFAULT_PROVIDER", "openai")


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    client = Mock()
    client.generate_completion.return_value = "Mock response"
    return client
