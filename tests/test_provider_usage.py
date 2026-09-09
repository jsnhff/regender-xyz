"""The provider counts what a run actually spent.

`response.usage` was returned by every call and discarded, so the only figure
the interface could show was an estimate made before the run from a token
guess. Counting is bookkeeping: it must never be the reason a call fails.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.providers.anthropic import AnthropicProvider


def _response(input_tokens=100, output_tokens=40, text="ok"):
    response = MagicMock()
    response.content = [MagicMock(text=text)]
    response.usage.input_tokens = input_tokens
    response.usage.output_tokens = output_tokens
    return response


@pytest.fixture
def provider():
    p = AnthropicProvider.__new__(AnthropicProvider)
    p.model = "claude-opus-4-1-20250805"
    p.logger = MagicMock()
    p.client = MagicMock()
    p.tokens_in = p.tokens_out = p.calls = 0
    return p


MESSAGES = [{"role": "user", "content": "hi"}]


def test_a_call_records_what_it_used(provider):
    provider.client.messages.create = AsyncMock(return_value=_response())
    asyncio.run(provider._complete_impl(MESSAGES))
    assert (provider.tokens_in, provider.tokens_out, provider.calls) == (100, 40, 1)


def test_usage_accumulates_across_calls(provider):
    provider.client.messages.create = AsyncMock(return_value=_response())
    for _ in range(3):
        asyncio.run(provider._complete_impl(MESSAGES))
    assert (provider.tokens_in, provider.tokens_out, provider.calls) == (300, 120, 3)


def test_a_fresh_provider_reads_as_zero():
    """Built without initialize(), it must read zero rather than raise."""
    p = AnthropicProvider.__new__(AnthropicProvider)
    assert (p.tokens_in, p.tokens_out, p.calls) == (0, 0, 0)


class TestCountingNeverBreaksACall:
    def test_a_non_numeric_usage_field_is_ignored(self, provider):
        """A MagicMock usage made `+=` raise, which would kill the transform."""
        response = _response()
        response.usage.input_tokens = MagicMock()
        provider.client.messages.create = AsyncMock(return_value=response)
        assert asyncio.run(provider._complete_impl(MESSAGES)) == "ok"
        assert provider.tokens_in == 0
        assert provider.tokens_out == 40, "the field that was real still counts"

    def test_a_response_without_usage_still_returns_its_text(self, provider):
        response = _response()
        del response.usage
        provider.client.messages.create = AsyncMock(return_value=response)
        assert asyncio.run(provider._complete_impl(MESSAGES)) == "ok"
        assert provider.calls == 0

    def test_a_boolean_is_not_a_token_count(self, provider):
        response = _response()
        response.usage.input_tokens = True
        provider.client.messages.create = AsyncMock(return_value=response)
        asyncio.run(provider._complete_impl(MESSAGES))
        assert provider.tokens_in == 0
