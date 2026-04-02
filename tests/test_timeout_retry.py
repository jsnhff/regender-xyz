"""
Test that the transform service retries at sentence level when a batch times out.

Simulates the Darcy's letter scenario: a very long paragraph that causes an API
timeout on the first batch attempt. The retry logic should split the paragraph
into sentence groups and successfully transform it without re-running the whole book.
"""
import re

import pytest

# Excerpt from Darcy's letter (Chapter 35, Pride & Prejudice) — the actual paragraph
# that timed out on the full P&P all_male transform. Contains multiple female pronouns
# (she/her/hers) that must be converted to male equivalents.
DARCYS_LETTER = (
    "Two offences of a very different nature, and by no means of equal magnitude, "
    "you last night laid to my charge. "
    "The first mentioned was, that, regardless of the sentiments of either, "
    "I had detached Mr. Bingley from your sister. "
    "Bingley preferred your elder sister to any other young woman in the country. "
    "Your sister I also watched. "
    "Her look and manners were open, cheerful, and engaging as ever, "
    "but without any symptom of peculiar regard; "
    "and I remained convinced, from the evening's scrutiny, "
    "that though she received his attentions with pleasure, "
    "she did not invite them by any participation of sentiment. "
    "That I was desirous of believing her indifferent is certain; "
    "but I will venture to say that my investigations and decisions "
    "are not usually influenced by my hopes or fears. "
    "I did not believe her to be indifferent because I wished it; "
    "I believed it on impartial conviction, as truly as I wished it in reason. "
    "My sister, who is more than ten years my junior, was left to my guardianship. "
    "She was then but fifteen, which must be her excuse; "
    "and after stating her imprudence, I am happy to add, "
    "that I owed the knowledge of it to herself. "
    "Regard for my sister's credit and feelings prevented any public exposure. "
    "Mr. Wickham's chief object was unquestionably my sister's fortune. "
    "This, madam, is a faithful narrative of every event in which we have been concerned together."
)


def _make_transformed(text: str) -> str:
    """Simple female→male substitution for mock responses."""
    replacements = [
        (" she ", " he "),
        (" She ", " He "),
        (" her ", " him "),
        (" Her ", " His "),
        (" hers ", " his "),
        ("herself", "himself"),
        ("sister", "brother"),
        ("madam", "sir"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _extract_paragraphs_from_prompt(user_msg: str) -> list[str]:
    """Pull paragraph text out of the batch transform user prompt."""
    # Format: "Transform these N paragraphs (separated by blank lines):\n\n<text>"
    _, _, body = user_msg.partition("\n\n")
    return [p.strip() for p in body.strip().split("\n\n") if p.strip()]


class TimeoutThenSucceedProvider:
    """Mock provider: raises TimeoutError on the first call, transforms on retries."""

    name = "mock"
    model = "mock-model"

    def __init__(self):
        self.call_count = 0

    async def complete(self, messages, **kwargs):
        self.call_count += 1
        if self.call_count == 1:
            raise TimeoutError("Simulated API timeout on large paragraph")
        user_msg = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
        )
        paragraphs = _extract_paragraphs_from_prompt(user_msg)
        return "\n\n".join(_make_transformed(p) for p in paragraphs)


@pytest.mark.asyncio
async def test_timeout_triggers_sentence_level_retry():
    """When a batch times out, the service retries at sentence level and succeeds."""
    from src.models.book import Chapter, Paragraph
    from src.models.character import CharacterAnalysis
    from src.models.transformation import TransformType
    from src.services.base import ServiceConfig
    from src.services.transform_service import TransformService

    provider = TimeoutThenSucceedProvider()
    service = TransformService(provider=provider, config=ServiceConfig())

    sentences = [s.strip() + "." for s in DARCYS_LETTER.rstrip(".").split(". ") if s.strip()]
    para = Paragraph(sentences=sentences)
    chapter = Chapter(number=1, title="Darcy's Letter", paragraphs=[para])
    context = {
        "transform_type": TransformType.ALL_MALE,
        "characters": CharacterAnalysis(book_id="test", characters=[]),
    }

    transformed_chapter, _changes = await service._transform_single_chapter(
        chapter, 0, context
    )

    assert provider.call_count > 1, "Expected at least one retry call after initial timeout"

    output_text = transformed_chapter.paragraphs[0].get_text()

    # Female pronouns should be gone — either from mock substitution or from term_map fallback
    assert " she " not in output_text, f"'she' survived in output:\n{output_text[:300]}"
    assert " her " not in output_text, f"'her' survived in output:\n{output_text[:300]}"

    # Male pronouns should be present (transform happened)
    assert " he " in output_text or " him " in output_text, (
        f"No male pronouns found — transform may not have run:\n{output_text[:300]}"
    )


@pytest.mark.asyncio
async def test_retry_falls_back_to_term_map_on_total_failure():
    """When ALL retry attempts fail, the final term_map pass still catches gendered nouns."""
    from src.models.book import Chapter, Paragraph
    from src.models.character import CharacterAnalysis
    from src.models.transformation import TransformType
    from src.services.base import ServiceConfig
    from src.services.transform_service import TransformService

    class AlwaysFailProvider:
        name = "mock"
        model = "mock-model"

        async def complete(self, messages, **kwargs):
            raise TimeoutError("Simulated persistent failure")

    service = TransformService(provider=AlwaysFailProvider(), config=ServiceConfig())

    # Paragraph with gendered nouns that _TERM_MAPS covers (aunt, widow, queen)
    text = "Her aunt arrived. The widow sat quietly. The queen held court."
    para = Paragraph(sentences=[text])
    chapter = Chapter(number=1, title="Test", paragraphs=[para])
    context = {
        "transform_type": TransformType.ALL_MALE,
        "characters": CharacterAnalysis(book_id="test", characters=[]),
    }

    transformed_chapter, _changes = await service._transform_single_chapter(
        chapter, 0, context
    )

    output_text = transformed_chapter.paragraphs[0].get_text()

    # Term_map should have caught these even though LLM completely failed.
    # Use word-boundary checks so "widower" doesn't match the "widow" pattern.
    assert not re.search(r"\baunt\b", output_text), f"'aunt' not caught by term_map: {output_text}"
    assert not re.search(r"\bwidow\b", output_text), f"'widow' not caught by term_map: {output_text}"
    assert not re.search(r"\bqueen\b", output_text), f"'queen' not caught by term_map: {output_text}"
    assert re.search(r"\buncle\b", output_text), f"'uncle' not in output: {output_text}"
    assert re.search(r"\bwidower\b", output_text), f"'widower' not in output: {output_text}"
    assert re.search(r"\bking\b", output_text), f"'king' not in output: {output_text}"
