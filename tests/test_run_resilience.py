"""One bad chapter must not cost the other sixty.

asyncio.gather without return_exceptions propagates the first failure
immediately and discards every other chapter's completed work. Nothing is
written until transform_book returns, so a two-hour run over sixty-one
chapters died with no output and a one-line error.
"""

import asyncio

import pytest

from src.models.book import Book, Chapter, Paragraph
from src.models.transformation import TransformType
from src.services.transform_service import TransformService


def chapters(n):
    return [
        Chapter(
            number=i + 1, title=f"Chapter {i + 1}", paragraphs=[Paragraph(sentences=[f"Text {i}."])]
        )
        for i in range(n)
    ]


class _Service(TransformService):
    """A transform whose chapter step fails for the chapters named."""

    def __init__(self, fail_on):
        self.fail_on = fail_on
        self.logger = __import__("logging").getLogger("test")
        self.failed_chapters = []
        self.provider = None
        self.config = type("cfg", (), {"max_concurrent": 3})()

    async def _transform_single_chapter(self, chapter, index, context, name_map=None):
        if index in self.fail_on:
            raise RuntimeError(f"chapter {index} exploded")
        return chapter, []


class TestParallelPath:
    def test_one_failure_does_not_lose_the_others(self):
        service = _Service(fail_on={2})
        out, _ = asyncio.run(service._transform_chapters_parallel(chapters(6), {}, name_map=None))
        assert len(out) == 6, "every chapter must come back, whole"

    def test_the_failed_chapter_keeps_its_source_text(self):
        source = chapters(4)
        service = _Service(fail_on={1})
        out, _ = asyncio.run(service._transform_chapters_parallel(source, {}, name_map=None))
        assert out[1] is source[1]

    def test_the_failures_are_reported(self):
        service = _Service(fail_on={0, 3})
        asyncio.run(service._transform_chapters_parallel(chapters(5), {}, name_map=None))
        assert service.failed_chapters == [1, 4]

    def test_a_clean_run_reports_nothing(self):
        service = _Service(fail_on=set())
        out, _ = asyncio.run(service._transform_chapters_parallel(chapters(5), {}, name_map=None))
        assert len(out) == 5
        assert service.failed_chapters == []


class TestSequentialPath:
    """OpenAI is forced down this path, so it needs the same bargain."""

    def test_one_failure_does_not_lose_the_others(self):
        service = _Service(fail_on={2})
        out, _ = asyncio.run(service._transform_chapters_sequential(chapters(6), {}, name_map=None))
        assert len(out) == 6
        assert service.failed_chapters == [3]

    def test_order_is_preserved(self):
        source = chapters(5)
        service = _Service(fail_on={1, 3})
        out, _ = asyncio.run(service._transform_chapters_sequential(source, {}, name_map=None))
        assert [c.number for c in out] == [1, 2, 3, 4, 5]
