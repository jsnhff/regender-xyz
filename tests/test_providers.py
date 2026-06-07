"""
Provider error-path tests.

These exercise the retry/error handling branches in the OpenAI and Anthropic
providers without making real API calls. The provider clients are replaced with
mocks, and ``asyncio.sleep`` is patched out so the bounded-retry logic runs
instantly instead of waiting the real 30/60 second backoffs.
"""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from src.providers.anthropic import AnthropicProvider
from src.providers.openai import OpenAIProvider


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Make every ``asyncio.sleep`` in the providers return immediately."""
    fake_sleep = AsyncMock(return_value=None)
    monkeypatch.setattr("src.providers.anthropic.asyncio.sleep", fake_sleep)
    monkeypatch.setattr("src.providers.openai.asyncio.sleep", fake_sleep)
    return fake_sleep


def _make_anthropic(create_side_effect=None, create_return=None):
    """Build an AnthropicProvider with a mocked client."""
    provider = AnthropicProvider()
    provider.model = provider.default_model
    provider._initialized = True
    client = Mock()
    client.messages = Mock()
    client.messages.create = AsyncMock(side_effect=create_side_effect, return_value=create_return)
    provider.client = client
    return provider


def _make_openai(create_side_effect=None, create_return=None):
    """Build an OpenAIProvider with a mocked client."""
    provider = OpenAIProvider()
    provider.model = provider.default_model
    provider._initialized = True
    client = Mock()
    client.chat = Mock()
    client.chat.completions = Mock()
    client.chat.completions.create = AsyncMock(
        side_effect=create_side_effect, return_value=create_return
    )
    provider.client = client
    return provider


def _anthropic_response(text: str):
    """Build a mock Anthropic SDK response object."""
    block = Mock()
    block.text = text
    response = Mock()
    response.content = [block]
    return response


def _openai_response(text: str):
    """Build a mock OpenAI SDK response object."""
    message = Mock()
    message.content = text
    choice = Mock()
    choice.message = message
    response = Mock()
    response.choices = [choice]
    return response


# --------------------------------------------------------------------------- #
# Anthropic
# --------------------------------------------------------------------------- #


async def test_anthropic_overload_retries_then_raises():
    """A persistent 529 should retry MAX_RETRIES times, then re-raise (no infinite loop)."""
    provider = _make_anthropic(create_side_effect=Exception("Error 529: overloaded"))

    with pytest.raises(Exception, match="529"):
        await provider._complete_impl([{"role": "user", "content": "hi"}])

    # Initial attempt + MAX_RETRIES retries.
    assert provider.client.messages.create.call_count == AnthropicProvider.MAX_RETRIES + 1


async def test_anthropic_recovers_after_transient_overload():
    """If the API recovers within the retry budget, the result is returned."""
    provider = _make_anthropic(
        create_side_effect=[
            Exception("Error 529: overloaded"),
            Exception("Error 529: overloaded"),
            _anthropic_response("recovered"),
        ]
    )

    result = await provider._complete_impl([{"role": "user", "content": "hi"}])

    assert result == "recovered"
    assert provider.client.messages.create.call_count == 3


async def test_anthropic_rate_limit_retries_then_raises():
    """A persistent 429 should also be bounded by MAX_RETRIES."""
    provider = _make_anthropic(create_side_effect=Exception("Error 429: rate limit exceeded"))

    with pytest.raises(Exception, match="429"):
        await provider._complete_impl([{"role": "user", "content": "hi"}])

    assert provider.client.messages.create.call_count == AnthropicProvider.MAX_RETRIES + 1


async def test_anthropic_timeout_raises_timeouterror():
    """A timeout is surfaced as a clear TimeoutError, not retried."""
    provider = _make_anthropic(create_side_effect=asyncio.TimeoutError())

    with pytest.raises(TimeoutError):
        await provider._complete_impl([{"role": "user", "content": "hi"}])

    # Timeouts are not part of the retry budget.
    assert provider.client.messages.create.call_count == 1


async def test_anthropic_billing_error_raises_valueerror():
    """Billing/credit errors fail fast with an actionable ValueError."""
    provider = _make_anthropic(create_side_effect=Exception("insufficient credit balance"))

    with pytest.raises(ValueError, match="billing"):
        await provider._complete_impl([{"role": "user", "content": "hi"}])

    assert provider.client.messages.create.call_count == 1


# --------------------------------------------------------------------------- #
# OpenAI
# --------------------------------------------------------------------------- #


async def test_openai_rate_limit_retries_then_raises():
    """A persistent 429 should retry MAX_RETRIES times, then re-raise."""
    provider = _make_openai(create_side_effect=Exception("Error 429: rate_limit exceeded"))

    with pytest.raises(Exception, match="429"):
        await provider._complete_impl([{"role": "user", "content": "hi"}])

    assert provider.client.chat.completions.create.call_count == OpenAIProvider.MAX_RETRIES + 1


async def test_openai_recovers_after_transient_rate_limit():
    """If the API recovers within the retry budget, the result is returned."""
    provider = _make_openai(
        create_side_effect=[
            Exception("Error 429: rate_limit"),
            _openai_response("recovered"),
        ]
    )

    result = await provider._complete_impl([{"role": "user", "content": "hi"}])

    assert result == "recovered"
    assert provider.client.chat.completions.create.call_count == 2


async def test_openai_quota_error_raises_valueerror():
    """Quota exhaustion fails fast with an actionable ValueError."""
    provider = _make_openai(create_side_effect=Exception("insufficient_quota"))

    with pytest.raises(ValueError, match="quota"):
        await provider._complete_impl([{"role": "user", "content": "hi"}])

    assert provider.client.chat.completions.create.call_count == 1


async def test_openai_timeout_raises_timeouterror():
    """A timeout is surfaced as a clear TimeoutError, not retried."""
    provider = _make_openai(create_side_effect=asyncio.TimeoutError())

    with pytest.raises(TimeoutError):
        await provider._complete_impl([{"role": "user", "content": "hi"}])

    assert provider.client.chat.completions.create.call_count == 1
