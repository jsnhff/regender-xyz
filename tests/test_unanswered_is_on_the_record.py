# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Jason Huff
"""Text the model never answered for is on the record.

A failed batch is retried paragraph by paragraph, then in groups of sentences,
and if every one of those fails the original text is kept so the book stays
whole. That last step kept it without a word: no log line, no entry anywhere.

So a run in which the model never answered once -- a dead key, an account with
no credit, no network -- wrote the source back out with the term map run over
it, counted those substitutions as its changes, and reported success. It was
seen happening on 26 November 2026: 110 failed calls, "success: True".
"""

import asyncio
import json
import pathlib

import pytest

from src.app import run_problems

REWRITE = "You rewrite the gender language"


class _Model:
    """Analyses the cast as the shared mock does; answers transforms on its own terms."""

    name = "mock"
    model = "mock-model"
    supports_json = True

    def __init__(self, refuses=lambda _text: False):
        self.refuses = refuses
        self.transform_calls = 0

    async def complete(self, messages, **_kwargs):
        system = messages[0]["content"] if messages[0]["role"] == "system" else ""
        user = messages[-1]["content"]
        if system.startswith(REWRITE):
            self.transform_calls += 1
            if self.refuses(user):
                raise RuntimeError("Error code: 401 - invalid x-api-key")
            # The paragraphs back, markers and all, with one word changed.
            return user.split("\n\n", 1)[1].replace(" he ", " she ")
        if "extract all characters" in user.lower():
            return json.dumps(
                {
                    "characters": [
                        {
                            "name": "James Wilson",
                            "gender": "male",
                            "pronouns": "he/him",
                            "description": "a man",
                            "aliases": ["James"],
                            "titles": ["Mr"],
                        }
                    ]
                }
            )
        return "{}"


def _app(model):
    from src.app import Application
    from src.container import ApplicationContext

    context = ApplicationContext()
    context.initialize()
    context.register_instance("llm_provider", model)
    return Application(context=context)


def _run(model, story, out):
    return asyncio.run(
        _app(model).process_book(
            file_path=story, transform_type="gender_swap", output_path=str(out)
        )
    )


@pytest.fixture
def chapter_two_phrase(simple_story_path):
    """A run of words that occurs in the second chapter and not the first."""
    text = pathlib.Path(simple_story_path).read_text()
    second = text.split("CHAPTER 2", 1)[1]
    first = text.split("CHAPTER 2", 1)[0]
    for line in second.splitlines():
        words = line.split()
        for i in range(len(words) - 3):
            phrase = " ".join(words[i : i + 4])
            if phrase not in first:
                return phrase
    raise AssertionError("the fixture's chapters could not be told apart")


class TestAModelThatNeverAnswers:
    def test_the_run_is_a_failure_not_a_book(self, simple_story_path, tmp_path):
        out = tmp_path / "out.json"
        model = _Model(refuses=lambda _text: True)
        result = _run(model, simple_story_path, out)

        assert model.transform_calls > 0, "the transform was never attempted"
        assert result["success"] is False
        assert "did not answer for any of the 2 chapters" in result["error"]
        assert "no book was written" in result["error"]

    def test_the_first_failure_is_quoted(self, simple_story_path, tmp_path):
        result = _run(_Model(refuses=lambda _text: True), simple_story_path, tmp_path / "o.json")
        assert "401 - invalid x-api-key" in result["error"]

    def test_nothing_is_written_where_the_book_would_go(self, simple_story_path, tmp_path):
        out = tmp_path / "out.json"
        _run(_Model(refuses=lambda _text: True), simple_story_path, out)
        assert not out.exists()
        assert not (tmp_path / "gender_swap.txt").exists()


class TestAModelThatAnswersForSomeOfIt:
    def test_the_chapter_is_named(self, simple_story_path, tmp_path, chapter_two_phrase):
        model = _Model(refuses=lambda text: chapter_two_phrase in text)
        result = _run(model, simple_story_path, tmp_path / "out.json")

        assert result["success"] is True, "half a book is still a book, and says so"
        assert result["untransformed_chapters"] == [2]

    def test_it_is_listed_among_the_problems(self, simple_story_path, tmp_path, chapter_two_phrase):
        model = _Model(refuses=lambda text: chapter_two_phrase in text)
        result = _run(model, simple_story_path, tmp_path / "out.json")
        assert any("Chapter 2 kept original text" in p for p in run_problems(result))

    def test_a_model_that_answers_everything_leaves_no_record(self, simple_story_path, tmp_path):
        result = _run(_Model(), simple_story_path, tmp_path / "out.json")
        assert result["success"] is True
        assert result["untransformed_chapters"] == []


class TestEachRunStartsClean:
    def test_one_books_failures_do_not_reach_the_next(
        self, simple_story_path, tmp_path, chapter_two_phrase
    ):
        """failed_chapters was a class attribute that nothing reset."""
        model = _Model(refuses=lambda text: chapter_two_phrase in text)
        app = _app(model)

        def run(out):
            return asyncio.run(
                app.process_book(
                    file_path=simple_story_path, transform_type="gender_swap", output_path=out
                )
            )

        assert run(str(tmp_path / "a.json"))["untransformed_chapters"] == [2]
        model.refuses = lambda _text: False
        assert run(str(tmp_path / "b.json"))["untransformed_chapters"] == []
