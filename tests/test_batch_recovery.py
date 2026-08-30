"""End-to-end recovery when a batch response cannot be mapped.

The batch path is where paragraphs used to go missing: a response that did not
line up was padded or truncated and the chapter carried on with every later
paragraph in the wrong slot. These tests run a real chapter through
_transform_single_chapter with a provider that misbehaves, and assert the text
survives intact.
"""

import pytest

from src.models.book import Chapter, Paragraph
from src.models.transformation import TransformType
from src.services.transform_service import TransformService

SOURCE = [
    "Mr. Bennet was a gentleman of small fortune.",
    "His wife was a woman of mean understanding.",
    "Her daughters were her whole concern in life.",
    "The king and the queen were expected at Netherfield.",
]


def chapter():
    return Chapter(
        number=1,
        title="Chapter 1",
        paragraphs=[Paragraph(sentences=[text]) for text in SOURCE],
    )


class ScriptedProvider:
    """Returns whatever the script says, so batch failures can be replayed."""

    name = "scripted"
    model = "scripted-1"

    def __init__(self, batch_response):
        self.batch_response = batch_response
        self.calls = []

    async def complete(self, messages, **kwargs):
        user = messages[-1]["content"]
        self.calls.append(user)
        marker_count = user.count("[[P")
        if marker_count > 1:
            return self.batch_response
        # A single-paragraph retry: echo the source back untransformed, which is
        # the worst a real model does. The safety net then has to carry it.
        body = user.split("\n\n", 1)[1]
        return body.split("\n", 1)[1] if body.startswith("[[P") else body


async def run(provider):
    service = TransformService(provider=provider)
    context = {"transform_type": TransformType.GENDER_SWAP, "rules": {}}
    transformed, _changes = await service._transform_single_chapter(chapter(), 0, context)
    return [p.get_text() for p in transformed.paragraphs]


@pytest.mark.asyncio
class TestUnmappableBatchIsRecovered:
    async def test_short_response_does_not_delete_paragraphs(self):
        """Previously padded with empty strings, silently losing three paragraphs."""
        texts = await run(ScriptedProvider("Only one paragraph came back."))
        assert len(texts) == len(SOURCE)
        assert all(text.strip() for text in texts)

    async def test_short_response_keeps_every_paragraph_aligned(self):
        texts = await run(ScriptedProvider("Only one paragraph came back."))
        # Each paragraph fell back to its own source and was transformed
        # deterministically, so content stays in its own slot.
        assert "Mrs. Bennet" in texts[0]
        assert "Her husband" in texts[1]
        assert "sons" in texts[2]
        assert "queen and the king" in texts[3]

    async def test_long_response_does_not_truncate(self):
        texts = await run(ScriptedProvider("One.\n\nTwo.\n\nThree.\n\nFour.\n\nFive."))
        assert len(texts) == len(SOURCE)
        assert all(text.strip() for text in texts)

    async def test_the_batch_was_actually_retried(self):
        provider = ScriptedProvider("Only one paragraph came back.")
        await run(provider)
        # One batch call, then one call per paragraph.
        assert len(provider.calls) == 1 + len(SOURCE)


@pytest.mark.asyncio
class TestWellFormedBatchIsUsed:
    async def test_marked_response_is_taken_as_is(self):
        response = "\n\n".join(
            f"[[P{i}]]\n{text}"
            for i, text in enumerate(
                [
                    "Mrs. Bennet was a gentlewoman of small fortune.",
                    "Her husband was a man of mean understanding.",
                    "His sons were his whole concern in life.",
                    "The queen and the king were expected at Netherfield.",
                ],
                1,
            )
        )
        provider = ScriptedProvider(response)
        texts = await run(provider)
        assert len(provider.calls) == 1, "a well-formed batch must not be retried"
        assert texts[0] == "Mrs. Bennet was a gentlewoman of small fortune."
        assert texts[3] == "The queen and the king were expected at Netherfield."
