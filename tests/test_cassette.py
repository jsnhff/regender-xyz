"""Tests for the cassette provider.

The cassette is how the pipeline gets exercised end-to-end without an API key:
record the prompts a run generates, answer them with any model, replay. It is
only useful if recording and replay agree on which answer belongs to which
prompt, and if a missing answer fails loudly rather than silently returning
something wrong.
"""

import asyncio

import pytest

from src.models.book import Chapter, Paragraph
from src.models.transformation import TransformType
from src.providers.cassette import (
    CassetteMissingError,
    CassetteProvider,
    build_response,
    echo_source,
    split_marked_prompt,
    write_response,
)
from src.services.transform_service import TransformService

USER = "Transform these 2 paragraphs:\n\n[[P1]]\nHer husband spoke.\n\n[[P2]]\nThe queen arrived."
MESSAGES = [{"role": "system", "content": "sys"}, {"role": "user", "content": USER}]


class TestPromptSplitting:
    def test_markers_and_text_are_separated(self):
        assert split_marked_prompt(USER) == [
            ("1", "Her husband spoke."),
            ("2", "The queen arrived."),
        ]

    def test_echo_returns_the_source_with_markers_intact(self):
        assert echo_source(USER) == "[[P1]]\nHer husband spoke.\n\n[[P2]]\nThe queen arrived."

    def test_build_response_numbers_from_one(self):
        assert build_response(["a", "b"]) == "[[P1]]\na\n\n[[P2]]\nb"


class TestRecordAndReplay:
    def test_recording_writes_the_prompt_and_echoes_the_source(self, tmp_path):
        provider = CassetteProvider(str(tmp_path), mode="record")
        result = asyncio.run(provider.complete(MESSAGES))
        key = provider.calls[0]
        assert provider.prompt_path(key).exists()
        assert "Her husband spoke." in result

    def test_replay_returns_the_recorded_answer(self, tmp_path):
        recorder = CassetteProvider(str(tmp_path), mode="record")
        asyncio.run(recorder.complete(MESSAGES))
        key = recorder.calls[0]
        write_response(str(tmp_path), key, ["His wife spoke.", "The king arrived."])

        player = CassetteProvider(str(tmp_path), mode="replay")
        assert "His wife spoke." in asyncio.run(player.complete(MESSAGES))

    def test_the_key_is_stable_across_runs(self, tmp_path):
        first = CassetteProvider(str(tmp_path), mode="record")
        second = CassetteProvider(str(tmp_path), mode="record")
        asyncio.run(first.complete(MESSAGES))
        asyncio.run(second.complete(MESSAGES))
        assert first.calls == second.calls

    def test_a_different_prompt_gets_a_different_key(self, tmp_path):
        provider = CassetteProvider(str(tmp_path), mode="record")
        asyncio.run(provider.complete(MESSAGES))
        other = [MESSAGES[0], {"role": "user", "content": USER + " and more"}]
        asyncio.run(provider.complete(other))
        assert len(set(provider.calls)) == 2

    def test_missing_answer_raises_and_saves_the_prompt(self, tmp_path):
        provider = CassetteProvider(str(tmp_path), mode="replay")
        with pytest.raises(CassetteMissingError, match="No answer recorded"):
            asyncio.run(provider.complete(MESSAGES))
        assert provider.prompt_path(provider.calls[0]).exists()

    def test_pending_lists_unanswered_prompts(self, tmp_path):
        provider = CassetteProvider(str(tmp_path), mode="record")
        asyncio.run(provider.complete(MESSAGES))
        assert len(provider.pending()) == 1
        write_response(str(tmp_path), provider.calls[0], ["a", "b"])
        assert provider.pending() == []

    def test_rejects_an_unknown_mode(self, tmp_path):
        with pytest.raises(ValueError, match="record"):
            CassetteProvider(str(tmp_path), mode="playback")


class TestThroughThePipeline:
    def test_an_answered_cassette_drives_a_real_chapter(self, tmp_path):
        source = ["Her husband spoke to the queen.", "She told her sister the news."]
        chapter = Chapter(
            number=1, title="One", paragraphs=[Paragraph(sentences=[t]) for t in source]
        )
        context = {"transform_type": TransformType.GENDER_SWAP, "rules": {}}

        recorder = TransformService(provider=CassetteProvider(str(tmp_path), mode="record"))
        asyncio.run(recorder._transform_single_chapter(chapter, 0, context))

        provider = CassetteProvider(str(tmp_path), mode="record")
        key = next(p.name.split(".")[0] for p in tmp_path.glob("*.prompt.json"))
        write_response(
            str(tmp_path), key, ["His wife spoke to the king.", "He told his brother the news."]
        )

        player = TransformService(provider=CassetteProvider(str(tmp_path), mode="replay"))
        transformed, _ = asyncio.run(player._transform_single_chapter(chapter, 0, context))
        assert [p.get_text() for p in transformed.paragraphs] == [
            "His wife spoke to the king.",
            "He told his brother the news.",
        ]
        assert provider.mode == "record"

    def test_a_missing_cassette_falls_back_rather_than_losing_text(self, tmp_path):
        """The retry path must keep the paragraph, not drop it."""
        source = ["Her husband spoke to the queen."]
        chapter = Chapter(
            number=1, title="One", paragraphs=[Paragraph(sentences=[t]) for t in source]
        )
        context = {"transform_type": TransformType.GENDER_SWAP, "rules": {}}
        service = TransformService(provider=CassetteProvider(str(tmp_path), mode="replay"))
        transformed, _ = asyncio.run(service._transform_single_chapter(chapter, 0, context))
        assert len(transformed.paragraphs) == 1
        # No model answer, so the safety net carried it on its own.
        assert transformed.paragraphs[0].get_text() == "His wife spoke to the king."
