# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Jason Huff
"""A model belongs to a provider, and each provider has to work as offered.

The README offers three ways in: an Anthropic key, an OpenAI key, or a local
model through Ollama. Only the first had been run recently, and the other two
had drifted:

- the menu lists every provider with a key side by side, but choosing a model
  recorded only the model, so picking GPT-4o with Anthropic as the default
  sent "gpt-4o" to Anthropic;
- the OpenAI list was a list of generations, so an account offering GPT-5 and
  GPT-6 was shown nothing newer than GPT-4.1;
- an OpenAI account with no credit answers 429, which was read as a rate limit:
  a minute's wait, three times, per call;
- a local-model setup counted as no setup, so the wizard ran on every launch.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from src.cli.tui import (
    RegenderTUI,
    _openai_models_to_offer,
    _provider_for_model,
    _should_show_openai_model,
)
from src.providers.base_provider import ResponseIncompleteError
from src.providers.ollama import OllamaProvider
from src.providers.openai import OpenAIProvider

HI = [{"role": "user", "content": "hi"}]


# --------------------------------------------------------------------------- #
# The menu
# --------------------------------------------------------------------------- #


class TestChoosingAModelChoosesItsProvider:
    @pytest.mark.parametrize(
        "model_id, pricing, provider",
        [
            ("claude-sonnet-5-5", "$2.00 / $10.00 per 1M tokens", "anthropic"),
            ("gpt-4o", "$2.50 / $10.00 per 1M tokens", "openai"),
            ("gpt-6-luna", "pricing unknown", "openai"),
            ("o3", "pricing unknown", "openai"),
            ("llama3.1:8b", "local", "ollama"),
            # A local model can be called anything, including this.
            ("gpt-oss:20b", "local", "ollama"),
        ],
    )
    def test_each_model_names_its_provider(self, model_id, pricing, provider):
        assert _provider_for_model(model_id, pricing) == provider

    def test_the_choice_sets_both(self, monkeypatch):
        # Set through monkeypatch first, so what the menu writes is undone
        # afterwards and no later test inherits this one's choice.
        monkeypatch.setenv("DEFAULT_PROVIDER", "anthropic")
        monkeypatch.setenv("DEFAULT_MODEL", "")
        RegenderTUI._choose_model("gpt-4o", "$2.50 / $10.00 per 1M tokens")
        import os

        assert os.environ["DEFAULT_MODEL"] == "gpt-4o"
        assert os.environ["DEFAULT_PROVIDER"] == "openai"

    async def test_the_application_then_calls_that_provider(self, monkeypatch):
        """End to end: what the menu sets is what the run is built from."""
        from src.app import Application

        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-not-a-real-key")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-not-a-real-key")
        monkeypatch.setenv("DEFAULT_PROVIDER", "anthropic")
        monkeypatch.setenv("DEFAULT_MODEL", "")
        monkeypatch.delenv("OPENAI_MODEL", raising=False)
        RegenderTUI._choose_model("gpt-4o", "")
        app = Application("src/config.json")
        try:
            provider = app.get_service("transform").provider
            assert (provider.provider_name, provider.model) == ("openai", "gpt-4o")
        finally:
            app.shutdown()


def _listed(*pairs):
    return [SimpleNamespace(id=model_id, created=created) for model_id, created in pairs]


class TestTheOpenAIListFollowsTheAccount:
    @pytest.mark.parametrize(
        "model_id", ["gpt-4o", "gpt-4.1-mini", "gpt-5.5", "gpt-6-luna", "gpt-6.2-sol", "o3"]
    )
    def test_text_models_of_any_generation_are_offered(self, model_id):
        assert _should_show_openai_model(model_id)

    @pytest.mark.parametrize(
        "model_id",
        [
            "gpt-4o-realtime-preview",
            "gpt-4o-transcribe",
            "gpt-image-1",
            "gpt-live-1",
            "gpt-5.5-pro",
            "gpt-6-astra-healthcare",
            "text-embedding-3-large",
            "whisper-1",
            "chat-latest",
        ],
    )
    def test_what_this_app_cannot_call_is_not(self, model_id):
        assert not _should_show_openai_model(model_id)

    def test_a_dated_snapshot_gives_way_to_its_name(self):
        offered = _openai_models_to_offer(_listed(("gpt-5.5", 20), ("gpt-5.5-2026-04-23", 20)))
        assert offered == ["gpt-5.5"]

    def test_a_snapshot_with_no_plain_name_is_kept(self):
        assert _openai_models_to_offer(_listed(("gpt-5.5-2026-04-23", 20))) == [
            "gpt-5.5-2026-04-23"
        ]

    def test_the_recommended_model_leads_then_newest_first(self):
        offered = _openai_models_to_offer(
            _listed(("gpt-4.1", 5), ("gpt-6-luna", 30), ("gpt-4o", 3), ("gpt-5.5", 20))
        )
        assert offered == ["gpt-4o", "gpt-6-luna", "gpt-5.5", "gpt-4.1"]


class TestALocalModelSetupIsASetup:
    def _needs_setup(self, monkeypatch, tmp_path, **env):
        monkeypatch.chdir(tmp_path)  # no .env here to load a key from
        for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DEFAULT_PROVIDER"):
            monkeypatch.delenv(name, raising=False)
        for name, value in env.items():
            monkeypatch.setenv(name, value)
        return RegenderTUI._check_llm_setup(Mock())

    def test_with_nothing_configured_the_wizard_runs(self, monkeypatch, tmp_path):
        assert self._needs_setup(monkeypatch, tmp_path) is True

    def test_a_local_model_does_not_ask_again(self, monkeypatch, tmp_path):
        assert self._needs_setup(monkeypatch, tmp_path, DEFAULT_PROVIDER="ollama") is False


# --------------------------------------------------------------------------- #
# OpenAI
# --------------------------------------------------------------------------- #


def _openai(side_effect=None, return_value=None):
    provider = OpenAIProvider()
    provider.model = "gpt-test"
    provider._initialized = True
    provider.client = Mock()
    provider.client.chat.completions.create = AsyncMock(
        side_effect=side_effect, return_value=return_value
    )
    return provider


def _reply(text="done", finish_reason="stop", prompt_tokens=10, completion_tokens=5):
    choice = Mock()
    choice.message.content = text
    choice.finish_reason = finish_reason
    response = Mock()
    response.choices = [choice]
    response.usage.prompt_tokens = prompt_tokens
    response.usage.completion_tokens = completion_tokens
    return response


class _APIError(Exception):
    def __init__(self, message, status_code, param=None):
        super().__init__(message)
        self.status_code = status_code
        self.param = param
        self.response = None


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    sleep = AsyncMock(return_value=None)
    monkeypatch.setattr("src.providers.openai.asyncio.sleep", sleep)
    return sleep


class TestAnAccountWithNoCreditFailsAtOnce:
    # The error exactly as the API returned it on 26 November 2026.
    NO_CREDIT = _APIError(
        "Error code: 429 - {'error': {'message': 'You have no credits remaining. Add credits "
        "to continue using the API at https://platform.openai.com/settings/organization/"
        "billing/.', 'type': 'insufficient_quota', 'param': None, "
        "'code': 'credit_balance_exhausted'}}",
        429,
    )

    async def test_it_is_not_waited_on_as_a_rate_limit(self, no_sleep):
        provider = _openai(side_effect=self.NO_CREDIT)
        with pytest.raises(ValueError, match="no credits"):
            await provider._complete_impl(HI)
        assert provider.client.chat.completions.create.call_count == 1
        no_sleep.assert_not_called()

    async def test_a_real_rate_limit_is_still_retried(self, no_sleep):
        limited = _APIError("Error code: 429 - rate_limit_exceeded", 429)
        provider = _openai(side_effect=[limited, _reply("after the wait")])
        assert await provider._complete_impl(HI) == "after the wait"
        assert no_sleep.call_count == 1


class TestOpenAIAdaptsToTheModel:
    async def test_max_tokens_becomes_max_completion_tokens_when_asked(self):
        refused = _APIError(
            "Unsupported parameter: 'max_tokens' is not supported with this model. "
            "Use 'max_completion_tokens' instead.",
            400,
            param="max_tokens",
        )
        provider = _openai(side_effect=[refused, _reply(), _reply()])
        assert await provider._complete_impl(HI, max_tokens=500) == "done"
        await provider._complete_impl(HI, max_tokens=500)
        first, second, third = (
            call.kwargs for call in provider.client.chat.completions.create.call_args_list
        )
        assert first["max_tokens"] == 500
        assert second["max_completion_tokens"] == 500 and "max_tokens" not in second
        assert "max_tokens" not in third, "the model was asked the old way a second time"

    async def test_a_refused_temperature_is_dropped(self):
        refused = _APIError(
            "Unsupported value: 'temperature' does not support 0.3 with this model. "
            "Only the default (1) value is supported.",
            400,
            param="temperature",
        )
        provider = _openai(side_effect=[refused, _reply()])
        assert await provider._complete_impl(HI, temperature=0.3) == "done"
        first, second = (
            call.kwargs for call in provider.client.chat.completions.create.call_args_list
        )
        assert first["temperature"] == 0.3
        assert "temperature" not in second

    async def test_some_other_bad_request_is_raised_as_it_is(self):
        provider = _openai(side_effect=_APIError("context length exceeded", 400))
        with pytest.raises(_APIError):
            await provider._complete_impl(HI, max_tokens=500)
        assert provider.client.chat.completions.create.call_count == 1


class TestOpenAIRepliesAreWholeOrAnError:
    async def test_a_cut_off_reply_is_asked_for_again_with_room(self):
        provider = _openai(side_effect=[_reply("half", finish_reason="length"), _reply("whole")])
        assert await provider._complete_impl(HI, max_tokens=1000) == "whole"
        calls = provider.client.chat.completions.create.call_args_list
        assert calls[1].kwargs["max_tokens"] > calls[0].kwargs["max_tokens"]

    async def test_still_cut_off_it_raises(self):
        provider = _openai(return_value=_reply("half", finish_reason="length"))
        with pytest.raises(ResponseIncompleteError):
            await provider._complete_impl(HI, max_tokens=1000)

    async def test_a_filtered_reply_raises(self):
        provider = _openai(return_value=_reply(None, finish_reason="content_filter"))
        with pytest.raises(ResponseIncompleteError, match="declined"):
            await provider._complete_impl(HI)

    async def test_a_reply_with_no_content_raises(self):
        """A refusal arrives as no content at all, with finish_reason "stop"."""
        provider = _openai(return_value=_reply(None))
        with pytest.raises(ResponseIncompleteError, match="no text"):
            await provider._complete_impl(HI)

    async def test_usage_is_counted(self):
        provider = _openai(return_value=_reply(prompt_tokens=120, completion_tokens=40))
        await provider._complete_impl(HI)
        await provider._complete_impl(HI)
        assert (provider.tokens_in, provider.tokens_out, provider.calls) == (240, 80, 2)


# --------------------------------------------------------------------------- #
# Local models
# --------------------------------------------------------------------------- #


def _ollama(return_value):
    provider = OllamaProvider()
    provider.model = "llama-test"
    provider._initialized = True
    provider.client = Mock()
    provider.client.chat.completions.create = AsyncMock(return_value=return_value)
    return provider


class TestLocalModels:
    async def test_json_mode_is_asked_for(self):
        provider = _ollama(_reply("{}"))
        assert provider.supports_json is True
        await provider._complete_impl(HI, response_format="json_object")
        sent = provider.client.chat.completions.create.call_args.kwargs
        assert sent["response_format"] == {"type": "json_object"}

    async def test_a_cut_off_reply_raises_rather_than_passing_as_whole(self):
        provider = _ollama(_reply("half a para", finish_reason="length"))
        with pytest.raises(ResponseIncompleteError):
            await provider._complete_impl(HI, max_tokens=500)

    async def test_a_reply_with_no_content_raises(self):
        provider = _ollama(_reply("  "))
        with pytest.raises(ResponseIncompleteError, match="no text"):
            await provider._complete_impl(HI)

    async def test_usage_is_counted(self):
        provider = _ollama(_reply(prompt_tokens=300, completion_tokens=90))
        await provider._complete_impl(HI)
        assert (provider.tokens_in, provider.tokens_out, provider.calls) == (300, 90, 1)

    def test_the_context_window_respects_the_servers_limit(self, monkeypatch):
        provider = OllamaProvider()
        provider.model = "llama-test"
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:9/v1")  # nothing listens here
        monkeypatch.setenv("OLLAMA_CONTEXT_LENGTH", "4096")
        assert provider.get_model_info()["context_window"] == 4096
