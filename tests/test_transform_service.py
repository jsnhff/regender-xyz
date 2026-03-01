"""
Unit tests for TransformService and its components.

Covers (no real LLM calls made):
- _get_transformation_rules (all 4 TransformTypes)
- _parse_batch_response (exact / too-few / too-many)
- _create_batch_transform_prompt (structure, batch size)
- _build_character_instructions (per transform type)
- _create_selective_context_string
- _get_character_transformation
- _create_context
- _estimate_batch_tokens (with / without token manager)
- process() validation paths
- transform_book() validation paths
- end-to-end transform with mock provider
"""

import asyncio
import json

import pytest

from src.models.book import Book, Chapter, Paragraph
from src.models.character import Character, CharacterAnalysis, Gender
from src.models.transformation import TransformType
from src.services.transform_service import TransformService
from src.utils.errors import ConfigurationError, ValidationError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_paragraph(text="He walked to his car."):
    return Paragraph(sentences=[text])


def make_chapter(number=1, title="Chapter One", paragraphs=None):
    return Chapter(
        number=number,
        title=title,
        paragraphs=paragraphs or [make_paragraph()],
    )


def make_book(chapters=None):
    return Book(
        title="Test Book",
        author="Test Author",
        chapters=chapters or [make_chapter()],
    )


def make_character(name="Alice", gender=Gender.FEMALE, aliases=None):
    return Character(
        name=name,
        gender=gender,
        pronouns={"subject": "she", "object": "her", "possessive": "her"},
        aliases=aliases or [],
        importance="main",
        confidence=0.9,
    )


def make_analysis(characters=None):
    return CharacterAnalysis(
        book_id="test123",
        characters=characters or [make_character()],
    )


class MockProvider:
    """Minimal async LLM provider — returns plain transformed text."""

    name = "mock"
    model = "mock-model"
    supports_json = False

    def __init__(self, response="She walked to her car."):
        self.response = response
        self.calls = []

    async def complete(self, messages, **kwargs):
        self.calls.append(messages)
        return self.response


def make_service(provider=None):
    return TransformService(provider=provider)


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# _get_transformation_rules
# ---------------------------------------------------------------------------


class TestGetTransformationRules:
    def setup_method(self):
        self.svc = make_service()
        self.rules = self.svc._get_transformation_rules

    def test_all_male_target_gender(self):
        r = self.rules(TransformType.ALL_MALE)
        assert r["target_gender"] == "male"

    def test_all_male_pronoun_map_she_to_he(self):
        r = self.rules(TransformType.ALL_MALE)
        assert r["pronouns"]["she"] == "he"

    def test_all_male_title_map_mrs_to_mr(self):
        r = self.rules(TransformType.ALL_MALE)
        assert r["titles"]["Mrs."] == "Mr."

    def test_all_male_term_map_mother_to_father(self):
        r = self.rules(TransformType.ALL_MALE)
        assert r["terms"]["mother"] == "father"

    def test_all_female_target_gender(self):
        r = self.rules(TransformType.ALL_FEMALE)
        assert r["target_gender"] == "female"

    def test_all_female_pronoun_map_he_to_she(self):
        r = self.rules(TransformType.ALL_FEMALE)
        assert r["pronouns"]["he"] == "she"

    def test_all_female_term_map_father_to_mother(self):
        r = self.rules(TransformType.ALL_FEMALE)
        assert r["terms"]["father"] == "mother"

    def test_gender_swap_is_symmetric_pronouns(self):
        r = self.rules(TransformType.GENDER_SWAP)
        assert r["pronouns"]["he"] == "she"
        assert r["pronouns"]["she"] == "he"
        assert r["pronouns"]["him"] == "her"
        assert r["pronouns"]["her"] == "him"

    def test_gender_swap_is_symmetric_terms(self):
        r = self.rules(TransformType.GENDER_SWAP)
        assert r["terms"]["king"] == "queen"
        assert r["terms"]["queen"] == "king"

    def test_gender_swap_has_swap_flag(self):
        r = self.rules(TransformType.GENDER_SWAP)
        assert r.get("swap") is True

    def test_nonbinary_returns_empty(self):
        # NONBINARY / CUSTOM use LLM without fixed rules
        r = self.rules(TransformType.NONBINARY)
        assert r == {}

    def test_custom_returns_empty(self):
        r = self.rules(TransformType.CUSTOM)
        assert r == {}


# ---------------------------------------------------------------------------
# _parse_batch_response
# ---------------------------------------------------------------------------


class TestParseBatchResponse:
    def setup_method(self):
        self.svc = make_service()
        self.parse = self.svc._parse_batch_response

    def test_exact_count_returned_unchanged(self):
        response = "Para one.\n\nPara two.\n\nPara three."
        result = self.parse(response, 3)
        assert len(result) == 3
        assert result[0] == "Para one."

    def test_too_few_padded_with_empty_strings(self):
        response = "Only one paragraph."
        result = self.parse(response, 3)
        assert len(result) == 3
        assert result[0] == "Only one paragraph."
        assert result[1] == ""
        assert result[2] == ""

    def test_too_many_truncated(self):
        response = "P1.\n\nP2.\n\nP3.\n\nP4.\n\nP5."
        result = self.parse(response, 2)
        assert len(result) == 2

    def test_single_paragraph_expected_one(self):
        response = "Just one."
        result = self.parse(response, 1)
        assert result == ["Just one."]

    def test_strips_leading_trailing_whitespace(self):
        response = "  \n\nPara one.\n\nPara two.\n\n  "
        result = self.parse(response, 2)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# _create_batch_transform_prompt
# ---------------------------------------------------------------------------


class TestCreateBatchTransformPrompt:
    def setup_method(self):
        self.svc = make_service()

    def _context(self, transform_type=TransformType.GENDER_SWAP):
        return {
            "transform_type": transform_type,
            "rules": self.svc._get_transformation_rules(transform_type),
            "character_mappings": {},
            "characters": None,
        }

    def test_prompt_contains_batch_size_in_system(self):
        paras = [make_paragraph(), make_paragraph()]
        prompt = self.svc._create_batch_transform_prompt(paras, self._context(), 2)
        assert "2" in prompt["system"]

    def test_prompt_has_system_and_user_keys(self):
        paras = [make_paragraph()]
        prompt = self.svc._create_batch_transform_prompt(paras, self._context(), 1)
        assert "system" in prompt
        assert "user" in prompt

    def test_user_prompt_contains_paragraph_text(self):
        paras = [Paragraph(sentences=["Alice went to market."])]
        prompt = self.svc._create_batch_transform_prompt(paras, self._context(), 1)
        assert "Alice went to market." in prompt["user"]

    def test_system_prompt_changes_with_transform_type(self):
        paras = [make_paragraph()]
        ctx_swap = self._context(TransformType.GENDER_SWAP)
        ctx_male = self._context(TransformType.ALL_MALE)
        p_swap = self.svc._create_batch_transform_prompt(paras, ctx_swap, 1)
        p_male = self.svc._create_batch_transform_prompt(paras, ctx_male, 1)
        assert p_swap["system"] != p_male["system"]


# ---------------------------------------------------------------------------
# _build_character_instructions
# ---------------------------------------------------------------------------


class TestBuildCharacterInstructions:
    def setup_method(self):
        self.svc = make_service()

    def _mappings(self, transform=True):
        return {"transform": transform} if transform else {"preserve": True}

    def test_empty_characters_returns_empty_string(self):
        result = self.svc._build_character_instructions(None, TransformType.GENDER_SWAP, {})
        assert result == ""

    def test_known_characters_header_present(self):
        analysis = make_analysis([make_character("Alice", Gender.FEMALE)])
        mappings = {"Alice": self._mappings()}
        result = self.svc._build_character_instructions(
            analysis, TransformType.GENDER_SWAP, mappings
        )
        assert "KNOWN CHARACTERS" in result

    def test_gender_swap_female_shows_arrow_male(self):
        analysis = make_analysis([make_character("Alice", Gender.FEMALE)])
        mappings = {"Alice": self._mappings()}
        result = self.svc._build_character_instructions(
            analysis, TransformType.GENDER_SWAP, mappings
        )
        assert "→male" in result

    def test_gender_swap_male_shows_arrow_female(self):
        male = make_character("Bob", Gender.MALE)
        male.pronouns = {"subject": "he", "object": "him"}
        analysis = make_analysis([male])
        mappings = {"Bob": self._mappings()}
        result = self.svc._build_character_instructions(
            analysis, TransformType.GENDER_SWAP, mappings
        )
        assert "→female" in result

    def test_all_female_shows_arrow_female(self):
        analysis = make_analysis([make_character("Alice", Gender.FEMALE)])
        mappings = {"Alice": self._mappings()}
        result = self.svc._build_character_instructions(
            analysis, TransformType.ALL_FEMALE, mappings
        )
        assert "→female" in result

    def test_all_male_shows_arrow_male(self):
        analysis = make_analysis([make_character("Alice", Gender.FEMALE)])
        mappings = {"Alice": self._mappings()}
        result = self.svc._build_character_instructions(analysis, TransformType.ALL_MALE, mappings)
        assert "→male" in result

    def test_nonbinary_shows_they_them(self):
        analysis = make_analysis([make_character("Alex", Gender.NONBINARY)])
        mappings = {"Alex": self._mappings()}
        result = self.svc._build_character_instructions(analysis, TransformType.NONBINARY, mappings)
        assert "→they/them" in result

    def test_preserve_shows_keep_unchanged(self):
        analysis = make_analysis([make_character("Alice", Gender.FEMALE)])
        mappings = {"Alice": self._mappings(transform=False)}
        result = self.svc._build_character_instructions(
            analysis, TransformType.GENDER_SWAP, mappings
        )
        assert "KEEP UNCHANGED" in result

    def test_character_name_present_in_output(self):
        analysis = make_analysis([make_character("Elizabeth", Gender.FEMALE)])
        mappings = {"Elizabeth": self._mappings()}
        result = self.svc._build_character_instructions(
            analysis, TransformType.GENDER_SWAP, mappings
        )
        assert "Elizabeth" in result


# ---------------------------------------------------------------------------
# _create_selective_context_string
# ---------------------------------------------------------------------------


class TestCreateSelectiveContextString:
    def setup_method(self):
        self.svc = make_service()

    def test_to_transform_list_present(self):
        analysis = make_analysis([make_character("Alice", Gender.FEMALE)])
        result = self.svc._create_selective_context_string(analysis, ["Alice"], [])
        assert "Characters to transform" in result
        assert "Alice" in result

    def test_to_preserve_list_present(self):
        analysis = make_analysis([make_character("Bob", Gender.MALE)])
        result = self.svc._create_selective_context_string(analysis, [], ["Bob"])
        assert "preserve" in result.lower()
        assert "Bob" in result

    def test_both_lists_present(self):
        chars = [make_character("Alice", Gender.FEMALE), make_character("Bob", Gender.MALE)]
        analysis = make_analysis(chars)
        result = self.svc._create_selective_context_string(analysis, ["Alice"], ["Bob"])
        assert "Alice" in result
        assert "Bob" in result

    def test_empty_both_falls_back_to_default_context(self):
        analysis = make_analysis()
        result = self.svc._create_selective_context_string(analysis, [], [])
        # Falls back to analysis.create_context_string()
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# _get_character_transformation
# ---------------------------------------------------------------------------


class TestGetCharacterTransformation:
    def setup_method(self):
        self.svc = make_service()

    def test_gender_swap_sets_transform_true(self):
        char = make_character()
        result = self.svc._get_character_transformation(char, TransformType.GENDER_SWAP)
        assert result.get("transform") is True

    def test_all_female_sets_transform_true(self):
        char = make_character()
        result = self.svc._get_character_transformation(char, TransformType.ALL_FEMALE)
        assert result.get("transform") is True

    def test_all_male_sets_transform_true(self):
        char = make_character()
        result = self.svc._get_character_transformation(char, TransformType.ALL_MALE)
        assert result.get("transform") is True

    def test_nonbinary_sets_transform_true(self):
        char = make_character()
        result = self.svc._get_character_transformation(char, TransformType.NONBINARY)
        assert result.get("transform") is True

    def test_custom_sets_preserve_true(self):
        char = make_character()
        result = self.svc._get_character_transformation(char, TransformType.CUSTOM)
        assert result.get("preserve") is True

    def test_result_contains_original_gender(self):
        char = make_character(gender=Gender.FEMALE)
        result = self.svc._get_character_transformation(char, TransformType.GENDER_SWAP)
        assert result["original_gender"] == Gender.FEMALE

    def test_result_contains_name(self):
        char = make_character(name="Alice")
        result = self.svc._get_character_transformation(char, TransformType.GENDER_SWAP)
        assert result["name"] == "Alice"


# ---------------------------------------------------------------------------
# _create_context
# ---------------------------------------------------------------------------


class TestCreateContext:
    def setup_method(self):
        self.svc = make_service()

    def test_has_required_keys(self):
        analysis = make_analysis()
        ctx = self.svc._create_context(analysis, TransformType.GENDER_SWAP)
        for key in ("transform_type", "rules", "characters", "character_mappings"):
            assert key in ctx

    def test_transform_type_matches(self):
        analysis = make_analysis()
        ctx = self.svc._create_context(analysis, TransformType.ALL_FEMALE)
        assert ctx["transform_type"] == TransformType.ALL_FEMALE

    def test_character_mappings_contains_character_name(self):
        analysis = make_analysis([make_character("Alice")])
        ctx = self.svc._create_context(analysis, TransformType.GENDER_SWAP)
        assert "Alice" in ctx["character_mappings"]

    def test_aliases_added_to_mappings(self):
        char = make_character("Alice", aliases=["Ally", "Al"])
        analysis = make_analysis([char])
        ctx = self.svc._create_context(analysis, TransformType.GENDER_SWAP)
        assert "Ally" in ctx["character_mappings"]
        assert "Al" in ctx["character_mappings"]

    def test_selected_characters_preserved_in_mappings(self):
        chars = [make_character("Alice"), make_character("Bob", Gender.MALE)]
        analysis = make_analysis(chars)
        # Only transform Alice; preserve Bob
        ctx = self.svc._create_context(analysis, TransformType.GENDER_SWAP, ["Alice"])
        assert ctx["character_mappings"]["Bob"].get("preserve") is True

    def test_characters_to_transform_list(self):
        analysis = make_analysis([make_character("Alice")])
        ctx = self.svc._create_context(analysis, TransformType.GENDER_SWAP)
        assert "Alice" in ctx["characters_to_transform"]


# ---------------------------------------------------------------------------
# _estimate_batch_tokens
# ---------------------------------------------------------------------------


class TestEstimateBatchTokens:
    def setup_method(self):
        self.svc = make_service()

    def test_without_token_manager_returns_len_times_200(self):
        self.svc.token_manager = None
        paras = [make_paragraph(), make_paragraph(), make_paragraph()]
        result = self.svc._estimate_batch_tokens(paras, {})
        assert result == 3 * 200

    def test_with_token_manager_returns_positive_int(self):
        # token_manager is created during _initialize()
        paras = [Paragraph(sentences=["Alice went to market."])]
        result = self.svc._estimate_batch_tokens(paras, {})
        assert isinstance(result, int)
        assert result > 0


# ---------------------------------------------------------------------------
# process() — validation paths
# ---------------------------------------------------------------------------


class TestProcessValidation:
    def setup_method(self):
        self.svc = make_service(provider=MockProvider())

    def test_none_data_raises_validation_error(self):
        with pytest.raises(ValidationError):
            run(self.svc.process(None))

    def test_non_dict_raises_validation_error(self):
        with pytest.raises(ValidationError):
            run(self.svc.process("not a dict"))

    def test_missing_book_raises_validation_error(self):
        with pytest.raises(ValidationError):
            run(self.svc.process({"transform_type": "gender_swap"}))

    def test_wrong_book_type_raises_validation_error(self):
        with pytest.raises(ValidationError):
            run(self.svc.process({"book": "not a book", "transform_type": "gender_swap"}))

    def test_missing_transform_type_raises_validation_error(self):
        with pytest.raises(ValidationError):
            run(self.svc.process({"book": make_book()}))

    def test_invalid_string_transform_type_raises_validation_error(self):
        with pytest.raises(ValidationError):
            run(self.svc.process({"book": make_book(), "transform_type": "turbo_swap"}))

    def test_wrong_transform_type_type_raises_validation_error(self):
        with pytest.raises(ValidationError):
            run(self.svc.process({"book": make_book(), "transform_type": 42}))

    def test_valid_string_transform_type_accepted(self):
        # "gender_swap" string should be auto-converted to TransformType
        analysis = make_analysis()
        data = {
            "book": make_book(),
            "transform_type": "gender_swap",
            "characters": analysis,
        }
        result = run(self.svc.process(data))
        assert result is not None

    def test_invalid_characters_type_raises_validation_error(self):
        with pytest.raises(ValidationError):
            run(
                self.svc.process(
                    {
                        "book": make_book(),
                        "transform_type": "gender_swap",
                        "characters": "not an analysis",
                    }
                )
            )


# ---------------------------------------------------------------------------
# transform_book() — validation paths
# ---------------------------------------------------------------------------


class TestTransformBookValidation:
    def setup_method(self):
        self.svc_with_provider = make_service(provider=MockProvider())
        self.svc_no_provider = make_service(provider=None)

    def test_none_book_raises_validation_error(self):
        with pytest.raises(ValidationError):
            run(self.svc_with_provider.transform_book(None, TransformType.GENDER_SWAP))

    def test_wrong_type_raises_validation_error(self):
        with pytest.raises(ValidationError):
            run(self.svc_with_provider.transform_book("not a book", TransformType.GENDER_SWAP))

    def test_empty_book_raises_validation_error(self):
        empty_book = Book(title="Empty", author="Author", chapters=[])
        with pytest.raises(ValidationError):
            run(self.svc_with_provider.transform_book(empty_book, TransformType.GENDER_SWAP))

    def test_no_provider_raises_configuration_error(self):
        with pytest.raises(ConfigurationError):
            run(self.svc_no_provider.transform_book(make_book(), TransformType.GENDER_SWAP))

    def test_invalid_transform_type_raises_validation_error(self):
        with pytest.raises(ValidationError):
            run(self.svc_with_provider.transform_book(make_book(), "not_a_type"))

    def test_selected_characters_not_list_raises(self):
        with pytest.raises(ValidationError):
            run(
                self.svc_with_provider.transform_book(
                    make_book(), TransformType.GENDER_SWAP, selected_characters="Alice"
                )
            )

    def test_selected_characters_non_strings_raises(self):
        with pytest.raises(ValidationError):
            run(
                self.svc_with_provider.transform_book(
                    make_book(), TransformType.GENDER_SWAP, selected_characters=[1, 2, 3]
                )
            )


# ---------------------------------------------------------------------------
# End-to-end transform with mock provider
# ---------------------------------------------------------------------------


class TestTransformBookEndToEnd:
    def _run_transform(self, transform_type, response_text="She walked to her car."):
        mock = MockProvider(response=response_text)
        svc = make_service(provider=mock)
        book = make_book(
            chapters=[
                make_chapter(
                    paragraphs=[
                        Paragraph(sentences=["He walked to his car."]),
                    ]
                )
            ]
        )
        analysis = make_analysis()
        return run(svc.transform_book(book, transform_type, characters=analysis))

    def test_returns_transformation_object(self):
        from src.models.transformation import Transformation

        result = self._run_transform(TransformType.GENDER_SWAP)
        assert isinstance(result, Transformation)

    def test_transform_type_matches_requested(self):
        result = self._run_transform(TransformType.ALL_FEMALE)
        assert result.transform_type == TransformType.ALL_FEMALE

    def test_transformed_chapters_count_matches_original(self):
        result = self._run_transform(TransformType.GENDER_SWAP)
        assert len(result.transformed_chapters) == 1

    def test_change_recorded_when_text_differs(self):
        result = self._run_transform(
            TransformType.GENDER_SWAP, response_text="She walked to her car."
        )
        assert len(result.changes) >= 1

    def test_no_change_when_text_identical(self):
        result = self._run_transform(
            TransformType.GENDER_SWAP, response_text="He walked to his car."
        )
        assert len(result.changes) == 0

    def test_all_transform_types_complete_without_error(self):
        for tt in (
            TransformType.GENDER_SWAP,
            TransformType.ALL_FEMALE,
            TransformType.ALL_MALE,
            TransformType.NONBINARY,
        ):
            result = self._run_transform(tt)
            assert result is not None

    def test_metadata_contains_provider_name(self):
        result = self._run_transform(TransformType.GENDER_SWAP)
        assert result.metadata.get("provider") is not None

    def test_provider_was_called(self):
        mock = MockProvider()
        svc = make_service(provider=mock)
        analysis = make_analysis()
        run(svc.transform_book(make_book(), TransformType.GENDER_SWAP, characters=analysis))
        assert len(mock.calls) >= 1
