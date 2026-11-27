# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Jason Huff
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
    provider.client = Mock()
    # The one place the SDK is called, so the one place a test stands in for it.
    provider._send = AsyncMock(side_effect=create_side_effect, return_value=create_return)
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
    block.type = "text"
    block.text = text
    response = Mock()
    response.content = [block]
    response.stop_reason = "end_turn"
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
    assert provider._send.call_count == AnthropicProvider.MAX_RETRIES + 1


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
    assert provider._send.call_count == 3


async def test_anthropic_rate_limit_retries_then_raises():
    """A persistent 429 should also be bounded by MAX_RETRIES."""
    provider = _make_anthropic(create_side_effect=Exception("Error 429: rate limit exceeded"))

    with pytest.raises(Exception, match="429"):
        await provider._complete_impl([{"role": "user", "content": "hi"}])

    assert provider._send.call_count == AnthropicProvider.MAX_RETRIES + 1


async def test_anthropic_timeout_raises_timeouterror():
    """A timeout is surfaced as a clear TimeoutError, not retried."""
    provider = _make_anthropic(create_side_effect=asyncio.TimeoutError())

    with pytest.raises(TimeoutError):
        await provider._complete_impl([{"role": "user", "content": "hi"}])

    # Timeouts are not part of the retry budget.
    assert provider._send.call_count == 1


async def test_anthropic_billing_error_raises_valueerror():
    """Billing/credit errors fail fast with an actionable ValueError."""
    provider = _make_anthropic(create_side_effect=Exception("insufficient credit balance"))

    with pytest.raises(ValueError, match="billing"):
        await provider._complete_impl([{"role": "user", "content": "hi"}])

    assert provider._send.call_count == 1


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

    with pytest.raises(ValueError, match="no credits"):
        await provider._complete_impl([{"role": "user", "content": "hi"}])

    assert provider.client.chat.completions.create.call_count == 1


async def test_openai_timeout_raises_timeouterror():
    """A timeout is surfaced as a clear TimeoutError, not retried."""
    provider = _make_openai(create_side_effect=asyncio.TimeoutError())

    with pytest.raises(TimeoutError):
        await provider._complete_impl([{"role": "user", "content": "hi"}])

    assert provider.client.chat.completions.create.call_count == 1


class TestErrorClassification:
    """The error handler must recognise the timeout the providers actually raise."""

    def test_builtin_timeout_is_classified_as_a_timeout(self):
        """Providers raise the builtin TimeoutError.

        errors.py used to define its own class of the same name, which shadowed
        the builtin, so this branch never matched and every provider timeout was
        reported as a generic INTERNAL_ERROR.
        """
        from src.utils.errors import ErrorHandler, OperationTimeoutError

        handled = ErrorHandler().handle_error(TimeoutError("API call timed out"))

        assert isinstance(handled, OperationTimeoutError)
        assert handled.error_code == "TIMEOUT_ERROR"

    def test_asyncio_timeout_is_classified_as_a_timeout(self):
        import asyncio

        from src.utils.errors import ErrorHandler, OperationTimeoutError

        handled = ErrorHandler().handle_error(asyncio.TimeoutError("timed out"))
        assert isinstance(handled, OperationTimeoutError)


# --------------------------------------------------------------------------- #
# What a reply has to be before it is returned as one
# --------------------------------------------------------------------------- #

HI = [{"role": "user", "content": "hi"}]


def _block(kind: str, text: str = ""):
    block = Mock()
    block.type = kind
    block.text = text
    return block


def _reply(*blocks, stop_reason="end_turn"):
    response = Mock()
    response.content = list(blocks)
    response.stop_reason = stop_reason
    return response


class _BadRequestError(Exception):
    status_code = 400


class TestTemperatureIsDroppedWhereItIsRefused:
    """Newer models answer a request carrying `temperature` with a 400.

    Seen live: claude-sonnet-5, claude-sonnet-5-5, claude-opus-5-5 and
    claude-haiku-5-5 all refuse it; claude-opus-4-5 and claude-haiku-4-5 take it.
    """

    async def test_the_call_is_repeated_without_it(self):
        provider = _make_anthropic(
            create_side_effect=[
                _BadRequestError("`temperature` is deprecated for this model."),
                _anthropic_response("done"),
            ]
        )
        assert await provider._complete_impl(HI, temperature=0.3) == "done"
        first, second = (call.args[0] for call in provider._send.call_args_list)
        assert first["temperature"] == 0.3
        assert "temperature" not in second

    async def test_the_model_is_only_asked_once(self):
        provider = _make_anthropic(
            create_side_effect=[
                _BadRequestError("`temperature` is deprecated for this model."),
                _anthropic_response("one"),
                _anthropic_response("two"),
            ]
        )
        await provider._complete_impl(HI, temperature=0.3)
        await provider._complete_impl(HI, temperature=0.3)
        assert provider._send.call_count == 3
        assert "temperature" not in provider._send.call_args_list[2].args[0]

    async def test_a_model_that_takes_it_still_gets_it(self):
        provider = _make_anthropic(create_return=_anthropic_response("done"))
        await provider._complete_impl(HI, temperature=0.0)
        assert provider._send.call_args.args[0]["temperature"] == 0.0

    async def test_some_other_bad_request_is_not_retried(self):
        provider = _make_anthropic(create_side_effect=_BadRequestError("messages: too long"))
        with pytest.raises(_BadRequestError):
            await provider._complete_impl(HI)
        assert provider._send.call_count == 1


class TestTheAnswerIsTheTextNotTheFirstBlock:
    async def test_reasoning_ahead_of_the_text_is_skipped(self):
        """claude-opus-5-5 and claude-haiku-5-5 answer ['thinking', 'text']."""
        provider = _make_anthropic(
            create_return=_reply(_block("thinking"), _block("text", "He gave her his book."))
        )
        assert await provider._complete_impl(HI) == "He gave her his book."

    async def test_text_in_several_blocks_is_joined(self):
        provider = _make_anthropic(
            create_return=_reply(_block("text", "one "), _block("thinking"), _block("text", "two"))
        )
        assert await provider._complete_impl(HI) == "one two"


class TestACutOffReplyIsNotAReply:
    async def test_it_is_asked_again_with_more_room_once(self):
        provider = _make_anthropic(
            create_side_effect=[
                _reply(_block("thinking"), stop_reason="max_tokens"),
                _anthropic_response("whole"),
            ]
        )
        assert await provider._complete_impl(HI, max_tokens=1000) == "whole"
        first, second = (call.args[0]["max_tokens"] for call in provider._send.call_args_list)
        assert first == 1000
        assert second > first

    async def test_still_cut_off_it_raises_rather_than_returning_half(self):
        from src.providers.base_provider import ResponseIncompleteError

        provider = _make_anthropic(
            create_return=_reply(_block("text", "half a parag"), stop_reason="max_tokens")
        )
        with pytest.raises(ResponseIncompleteError, match="cut off"):
            await provider._complete_impl(HI, max_tokens=1000)
        assert provider._send.call_count == 2

    async def test_a_refusal_raises(self):
        from src.providers.base_provider import ResponseIncompleteError

        provider = _make_anthropic(create_return=_reply(stop_reason="refusal"))
        with pytest.raises(ResponseIncompleteError, match="declined"):
            await provider._complete_impl(HI)


async def test_an_error_that_merely_contains_rate_is_not_a_rate_limit():
    """ "rate" is inside "generate"; matching it slept three minutes, then failed."""
    provider = _make_anthropic(create_side_effect=Exception("failed to generate a response"))
    with pytest.raises(Exception, match="generate"):
        await provider._complete_impl(HI)
    assert provider._send.call_count == 1


class TestTheChosenModelIsTheModelCalled:
    """The menu wrote DEFAULT_MODEL and nothing read it."""

    def _model(self, monkeypatch, **env):
        from src.app import Application

        for name in ("DEFAULT_MODEL", "ANTHROPIC_MODEL"):
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv("DEFAULT_PROVIDER", "anthropic")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-not-a-real-key")
        for name, value in env.items():
            monkeypatch.setenv(name, value)
        app = Application("src/config.json")
        try:
            return app.get_service("transform").provider.model
        finally:
            app.shutdown()

    async def test_the_menu_choice_wins(self, monkeypatch):
        model = self._model(
            monkeypatch, DEFAULT_MODEL="claude-haiku-5-5", ANTHROPIC_MODEL="claude-opus-5-5"
        )
        assert model == "claude-haiku-5-5"

    async def test_without_one_the_env_file_still_decides(self, monkeypatch):
        assert self._model(monkeypatch, ANTHROPIC_MODEL="claude-opus-5-5") == "claude-opus-5-5"

    async def test_with_neither_the_default_is_used(self, monkeypatch):
        assert self._model(monkeypatch) == "claude-sonnet-5-5"


class TestAReplyWithNoTextInIt:
    async def test_reasoning_and_nothing_after_it_raises(self):
        from src.providers.base_provider import ResponseIncompleteError

        provider = _make_anthropic(create_return=_reply(_block("thinking")))
        with pytest.raises(ResponseIncompleteError, match="no text"):
            await provider._complete_impl(HI)

    async def test_a_stop_that_is_not_an_ending_raises(self):
        from src.providers.base_provider import ResponseIncompleteError

        provider = _make_anthropic(
            create_return=_reply(_block("text", "part of"), stop_reason="pause_turn")
        )
        with pytest.raises(ResponseIncompleteError, match="pause_turn"):
            await provider._complete_impl(HI)

    async def test_a_stop_sequence_is_an_ending(self):
        provider = _make_anthropic(
            create_return=_reply(_block("text", "whole"), stop_reason="stop_sequence")
        )
        assert await provider._complete_impl(HI) == "whole"


class ReadTimeout(Exception):  # noqa: N818 -- the name is the thing under test
    """Stands in for httpx.ReadTimeout, which is raised with no message at all."""


class TestAReplyLostToTheConnection:
    """Seen on a full run: a stream went quiet for 579 seconds and the call failed.

    The SDK retries a connection that fails before a reply starts, not one that
    stalls part-way through it.
    """

    async def test_it_is_asked_for_again(self, no_sleep):
        provider = _make_anthropic(
            create_side_effect=[ReadTimeout(""), _anthropic_response("the names")]
        )
        assert await provider._complete_impl(HI) == "the names"
        assert provider._send.call_count == 2

    async def test_it_gives_up_after_a_few_and_says_what_happened(self, no_sleep):
        provider = _make_anthropic(create_side_effect=ReadTimeout(""))
        with pytest.raises(TimeoutError, match="stalled or dropped \\(ReadTimeout\\)"):
            await provider._complete_impl(HI)
        assert provider._send.call_count == AnthropicProvider.MAX_TRANSPORT_RETRIES + 1

    async def test_a_failure_wrapped_in_another_is_still_recognised(self, no_sleep):
        class APIConnectionError(Exception):
            pass

        wrapped = APIConnectionError("Connection error.")
        wrapped.__cause__ = ReadTimeout("")
        provider = _make_anthropic(create_side_effect=[wrapped, _anthropic_response("ok")])
        assert await provider._complete_impl(HI) == "ok"

    async def test_an_answer_from_the_api_is_not_a_lost_connection(self, no_sleep):
        """A 400 is the API replying; asking again would only get it again."""
        provider = _make_anthropic(create_side_effect=_BadRequestError("messages: too long"))
        with pytest.raises(_BadRequestError):
            await provider._complete_impl(HI)
        assert provider._send.call_count == 1

    async def test_our_own_ten_minute_limit_is_still_final(self):
        provider = _make_anthropic(create_side_effect=asyncio.TimeoutError())
        with pytest.raises(TimeoutError):
            await provider._complete_impl(HI)
        assert provider._send.call_count == 1
