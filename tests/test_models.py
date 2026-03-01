"""
Unit tests for domain models: Paragraph, Chapter, Book, Character,
CharacterAnalysis, TransformType, Transformation, TransformationChange.
"""

import pytest

from src.models.book import Book, Chapter, Paragraph
from src.models.character import Character, CharacterAnalysis, Gender
from src.models.transformation import (
    Transformation,
    TransformationChange,
    TransformationResult,
    TransformType,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_paragraph(sentences=None):
    return Paragraph(sentences=sentences or ["Hello world.", "Goodbye world."])


def make_chapter(number=1, title="Chapter One", paragraphs=None):
    return Chapter(
        number=number,
        title=title,
        paragraphs=paragraphs or [make_paragraph()],
    )


def make_book(title="Test Book", author="Test Author", chapters=None):
    return Book(
        title=title,
        author=author,
        chapters=chapters or [make_chapter()],
    )


def make_character(name="Alice", gender=Gender.FEMALE, importance="main"):
    return Character(
        name=name,
        gender=gender,
        pronouns={"subject": "she", "object": "her", "possessive": "her"},
        titles=["Ms."],
        aliases=["Ally"],
        importance=importance,
        confidence=0.95,
    )


def make_analysis(characters=None):
    return CharacterAnalysis(
        book_id="abc123",
        characters=characters or [make_character()],
    )


# ---------------------------------------------------------------------------
# Paragraph
# ---------------------------------------------------------------------------


class TestParagraph:
    def test_get_text_joins_sentences(self):
        p = Paragraph(sentences=["Hello.", "World."])
        assert p.get_text() == "Hello. World."

    def test_get_text_empty(self):
        p = Paragraph(sentences=[])
        assert p.get_text() == ""

    def test_word_count(self):
        p = Paragraph(sentences=["one two three", "four five"])
        assert p.word_count() == 5

    def test_word_count_empty(self):
        assert Paragraph(sentences=[]).word_count() == 0

    def test_to_dict_roundtrip(self):
        p = Paragraph(sentences=["A sentence.", "Another one."])
        restored = Paragraph.from_dict(p.to_dict())
        assert restored.sentences == p.sentences

    def test_from_dict_missing_key_defaults_to_empty(self):
        p = Paragraph.from_dict({})
        assert p.sentences == []


# ---------------------------------------------------------------------------
# Chapter
# ---------------------------------------------------------------------------


class TestChapter:
    def test_get_text_joins_paragraphs_with_double_newline(self):
        p1 = Paragraph(sentences=["First."])
        p2 = Paragraph(sentences=["Second."])
        ch = Chapter(number=1, title="T", paragraphs=[p1, p2])
        assert ch.get_text() == "First.\n\nSecond."

    def test_get_sentences_flattens_all(self):
        p1 = Paragraph(sentences=["A.", "B."])
        p2 = Paragraph(sentences=["C."])
        ch = Chapter(number=1, title="T", paragraphs=[p1, p2])
        assert ch.get_sentences() == ["A.", "B.", "C."]

    def test_word_count_sums_paragraphs(self):
        p1 = Paragraph(sentences=["one two"])
        p2 = Paragraph(sentences=["three four five"])
        ch = Chapter(number=1, title="T", paragraphs=[p1, p2])
        assert ch.word_count() == 5

    def test_to_dict_roundtrip(self):
        ch = make_chapter()
        restored = Chapter.from_dict(ch.to_dict())
        assert restored.number == ch.number
        assert restored.title == ch.title
        assert len(restored.paragraphs) == len(ch.paragraphs)

    def test_from_dict_defaults(self):
        ch = Chapter.from_dict({"number": None, "title": None, "paragraphs": []})
        assert ch.number is None
        assert ch.paragraphs == []


# ---------------------------------------------------------------------------
# Book
# ---------------------------------------------------------------------------


class TestBook:
    def test_word_count_sums_chapters(self):
        ch1 = make_chapter(paragraphs=[Paragraph(["one two"])])
        ch2 = make_chapter(number=2, paragraphs=[Paragraph(["three"])])
        book = make_book(chapters=[ch1, ch2])
        assert book.word_count() == 3

    def test_chapter_count(self):
        book = make_book(chapters=[make_chapter(), make_chapter(number=2)])
        assert book.chapter_count() == 2

    def test_get_chapter_by_number(self):
        ch1 = make_chapter(number=1, title="First")
        ch2 = make_chapter(number=2, title="Second")
        book = make_book(chapters=[ch1, ch2])
        assert book.get_chapter(2).title == "Second"

    def test_get_chapter_missing_returns_none(self):
        book = make_book()
        assert book.get_chapter(99) is None

    def test_get_text_includes_title_header(self):
        ch = make_chapter(title="My Chapter", paragraphs=[Paragraph(["Body text."])])
        book = make_book(chapters=[ch])
        text = book.get_text()
        assert "# My Chapter" in text
        assert "Body text." in text

    def test_hash_is_16_chars(self):
        book = make_book()
        assert len(book.hash()) == 16

    def test_hash_is_deterministic(self):
        book = make_book()
        assert book.hash() == book.hash()

    def test_hash_changes_with_content(self):
        book1 = make_book(title="Book A")
        book2 = make_book(title="Book B")
        assert book1.hash() != book2.hash()

    def test_to_dict_roundtrip(self):
        book = make_book()
        restored = Book.from_dict(book.to_dict())
        assert restored.title == book.title
        assert restored.author == book.author
        assert restored.chapter_count() == book.chapter_count()

    def test_validate_returns_no_errors_for_valid_book(self):
        assert make_book().validate() == []

    def test_validate_detects_no_chapters(self):
        # Don't use make_book() — its default fills in chapters when passed []
        book = Book(title="Test Book", author="Test Author", chapters=[])
        errors = book.validate()
        assert any("no chapters" in e.lower() for e in errors)

    def test_validate_detects_empty_chapter(self):
        empty_chapter = Chapter(number=1, title="Empty", paragraphs=[])
        book = make_book(chapters=[empty_chapter])
        errors = book.validate()
        assert any("no paragraphs" in e.lower() for e in errors)

    def test_validate_detects_empty_paragraph(self):
        ch = Chapter(number=1, title="Ch", paragraphs=[Paragraph(sentences=[])])
        book = make_book(chapters=[ch])
        errors = book.validate()
        assert any("no sentences" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# Gender
# ---------------------------------------------------------------------------


class TestGender:
    def test_all_values_accessible(self):
        assert Gender.MALE.value == "male"
        assert Gender.FEMALE.value == "female"
        assert Gender.NONBINARY.value == "non-binary"
        assert Gender.UNKNOWN.value == "unknown"
        assert Gender.NEUTRAL.value == "neutral"


# ---------------------------------------------------------------------------
# Character
# ---------------------------------------------------------------------------


class TestCharacter:
    def test_get_all_names_includes_aliases(self):
        c = make_character()
        names = c.get_all_names()
        assert "Alice" in names
        assert "Ally" in names

    def test_get_gendered_terms_female(self):
        c = make_character(gender=Gender.FEMALE)
        terms = c.get_gendered_terms()
        assert terms["sibling"] == "sister"
        assert terms["spouse"] == "wife"
        assert terms["royalty"] == "queen"

    def test_get_gendered_terms_male(self):
        c = make_character(name="Bob", gender=Gender.MALE)
        c.pronouns = {"subject": "he", "object": "him", "possessive": "his"}
        terms = c.get_gendered_terms()
        assert terms["sibling"] == "brother"
        assert terms["spouse"] == "husband"
        assert terms["royalty"] == "king"

    def test_get_gendered_terms_nonbinary_has_no_sibling(self):
        c = make_character(gender=Gender.NONBINARY)
        terms = c.get_gendered_terms()
        assert "sibling" not in terms

    def test_to_dict_roundtrip(self):
        c = make_character()
        restored = Character.from_dict(c.to_dict())
        assert restored.name == c.name
        assert restored.gender == c.gender
        assert restored.importance == c.importance
        assert restored.confidence == c.confidence

    def test_from_dict_string_pronouns_she_her(self):
        c = Character.from_dict(
            {
                "name": "Alice",
                "gender": "female",
                "pronouns": "she/her/hers",
            }
        )
        assert c.pronouns["subject"] == "she"
        assert c.pronouns["object"] == "her"
        assert c.pronouns["possessive"] == "hers"

    def test_from_dict_string_pronouns_two_parts(self):
        c = Character.from_dict(
            {
                "name": "Bob",
                "gender": "male",
                "pronouns": "he/him",
            }
        )
        assert c.pronouns["subject"] == "he"
        assert c.pronouns["object"] == "him"
        # possessive falls back to object when only 2 parts
        assert c.pronouns["possessive"] == "him"

    def test_from_dict_none_pronouns(self):
        c = Character.from_dict({"name": "X", "gender": "unknown", "pronouns": None})
        assert c.pronouns == {}

    def test_titles_primary_in_gendered_terms(self):
        c = make_character()
        c.titles = ["Lady", "Dame"]
        terms = c.get_gendered_terms()
        assert terms["title"] == "Lady"


# ---------------------------------------------------------------------------
# CharacterAnalysis
# ---------------------------------------------------------------------------


class TestCharacterAnalysis:
    def test_get_character_by_name(self):
        analysis = make_analysis()
        assert analysis.get_character("Alice") is not None

    def test_get_character_by_alias(self):
        analysis = make_analysis()
        assert analysis.get_character("Ally") is not None

    def test_get_character_missing_returns_none(self):
        analysis = make_analysis()
        assert analysis.get_character("Nobody") is None

    def test_get_main_characters(self):
        main = make_character(importance="main")
        supporting = make_character(name="Bob", importance="supporting")
        analysis = make_analysis(characters=[main, supporting])
        mains = analysis.get_main_characters()
        assert len(mains) == 1
        assert mains[0].name == "Alice"

    def test_get_by_gender(self):
        female = make_character(gender=Gender.FEMALE)
        male = make_character(name="Bob", gender=Gender.MALE)
        analysis = make_analysis(characters=[female, male])
        females = analysis.get_by_gender(Gender.FEMALE)
        assert len(females) == 1
        assert females[0].name == "Alice"

    def test_get_statistics(self):
        chars = [
            make_character(importance="main"),
            make_character(name="Bob", gender=Gender.MALE, importance="supporting"),
        ]
        analysis = make_analysis(characters=chars)
        stats = analysis.get_statistics()
        assert stats["total"] == 2
        assert stats["by_gender"]["female"] == 1
        assert stats["by_gender"]["male"] == 1
        assert "Alice" in stats["main_characters"]

    def test_to_dict_roundtrip(self):
        analysis = make_analysis()
        d = analysis.to_dict()
        restored = CharacterAnalysis.from_dict(d)
        assert restored.book_id == analysis.book_id
        assert len(restored.characters) == len(analysis.characters)

    def test_create_context_string_contains_main_section(self):
        analysis = make_analysis()
        ctx = analysis.create_context_string()
        assert "Main Characters" in ctx
        assert "Alice" in ctx

    def test_create_context_string_minor_shows_count(self):
        chars = [make_character(importance="minor") for _ in range(3)]
        analysis = make_analysis(characters=chars)
        ctx = analysis.create_context_string()
        assert "Minor Characters" in ctx
        assert "3" in ctx


# ---------------------------------------------------------------------------
# TransformType
# ---------------------------------------------------------------------------


class TestTransformType:
    def test_all_types_have_descriptions(self):
        for tt in TransformType:
            desc = tt.get_description()
            assert isinstance(desc, str) and len(desc) > 0


# ---------------------------------------------------------------------------
# TransformationChange
# ---------------------------------------------------------------------------


class TestTransformationChange:
    def test_to_dict_structure(self):
        change = TransformationChange(
            chapter_index=0,
            paragraph_index=1,
            sentence_index=2,
            original="he",
            transformed="she",
            change_type="pronoun",
            character_affected="Bob",
        )
        d = change.to_dict()
        assert d["location"] == {"chapter": 0, "paragraph": 1, "sentence": 2}
        assert d["original"] == "he"
        assert d["transformed"] == "she"
        assert d["type"] == "pronoun"
        assert d["character"] == "Bob"


# ---------------------------------------------------------------------------
# Transformation
# ---------------------------------------------------------------------------


class TestTransformation:
    def _make_transformation(self, changes=None, quality_score=None, n_chapters=1):
        book = make_book()
        chapters = [make_chapter(number=i + 1) for i in range(n_chapters)]
        analysis = make_analysis()
        return Transformation(
            original_book=book,
            transformed_chapters=chapters,
            transform_type=TransformType.GENDER_SWAP,
            characters_used=analysis,
            changes=changes or [],
            quality_score=quality_score,
        )

    def test_get_transformed_book_title_includes_type(self):
        t = self._make_transformation()
        transformed = t.get_transformed_book()
        assert "gender_swap" in transformed.title

    def test_get_transformed_book_preserves_author(self):
        t = self._make_transformation()
        assert t.get_transformed_book().author == "Test Author"

    def test_get_changes_by_type(self):
        changes = [
            TransformationChange(0, 0, 0, "he", "she", "pronoun"),
            TransformationChange(0, 0, 1, "him", "her", "pronoun"),
            TransformationChange(0, 0, 2, "Mr.", "Ms.", "title"),
        ]
        t = self._make_transformation(changes=changes)
        by_type = t.get_changes_by_type()
        assert len(by_type["pronoun"]) == 2
        assert len(by_type["title"]) == 1

    def test_get_changes_by_character(self):
        changes = [
            TransformationChange(0, 0, 0, "he", "she", "pronoun", "Bob"),
            TransformationChange(0, 0, 1, "him", "her", "pronoun", "Bob"),
            TransformationChange(0, 0, 2, "she", "he", "pronoun", "Alice"),
        ]
        t = self._make_transformation(changes=changes)
        by_char = t.get_changes_by_character()
        assert len(by_char["Bob"]) == 2
        assert len(by_char["Alice"]) == 1

    def test_get_statistics(self):
        changes = [TransformationChange(0, 0, 0, "he", "she", "pronoun")]
        t = self._make_transformation(changes=changes, quality_score=85.0)
        stats = t.get_statistics()
        assert stats["total_changes"] == 1
        assert stats["quality_score"] == 85.0
        assert stats["chapters_transformed"] == 1

    def test_validate_passes_for_valid(self):
        changes = [TransformationChange(0, 0, 0, "he", "she", "pronoun")]
        t = self._make_transformation(changes=changes)
        assert t.validate() == []

    def test_validate_detects_chapter_mismatch(self):
        book = make_book(chapters=[make_chapter(1), make_chapter(2)])
        analysis = make_analysis()
        t = Transformation(
            original_book=book,
            transformed_chapters=[make_chapter(1)],  # only 1, should be 2
            transform_type=TransformType.GENDER_SWAP,
            characters_used=analysis,
            changes=[TransformationChange(0, 0, 0, "he", "she", "pronoun")],
        )
        errors = t.validate()
        assert any("mismatch" in e.lower() for e in errors)

    def test_validate_detects_no_changes(self):
        t = self._make_transformation(changes=[])
        errors = t.validate()
        assert any("no changes" in e.lower() for e in errors)

    def test_validate_custom_type_allows_no_changes(self):
        book = make_book()
        analysis = make_analysis()
        t = Transformation(
            original_book=book,
            transformed_chapters=[make_chapter()],
            transform_type=TransformType.CUSTOM,
            characters_used=analysis,
            changes=[],
        )
        errors = t.validate()
        assert not any("no changes" in e.lower() for e in errors)

    def test_validate_detects_invalid_quality_score(self):
        changes = [TransformationChange(0, 0, 0, "he", "she", "pronoun")]
        t = self._make_transformation(changes=changes, quality_score=150.0)
        errors = t.validate()
        assert any("quality score" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# TransformationResult
# ---------------------------------------------------------------------------


class TestTransformationResult:
    def test_from_transformation_captures_stats(self):
        book = make_book()
        analysis = make_analysis()
        changes = [TransformationChange(0, 0, 0, "he", "she", "pronoun")]
        t = Transformation(
            original_book=book,
            transformed_chapters=[make_chapter()],
            transform_type=TransformType.ALL_FEMALE,
            characters_used=analysis,
            changes=changes,
            quality_score=90.0,
        )
        result = TransformationResult.from_transformation(t, processing_time=1.23)
        assert result.total_changes == 1
        assert result.transform_type == "all_female"
        assert result.quality_score == 90.0
        assert result.processing_time == 1.23
        assert "chapters" in result.transformed_book
