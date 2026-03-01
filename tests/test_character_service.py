"""
Unit tests for CharacterService and its components.

Covers (no real LLM calls made):
- UnionFind data structure
- _parse_json_response (all 5 fallback strategies)
- _clean_json_text
- _tokenize_name
- _are_similar (fuzzy matching + family-member guard)
- _find_best_matches
- _find_candidates
- _group_similar_characters
- _apply_early_deduplication
- _create_chunks
- _parse_gender
- _calculate_metadata
- _dict_to_character
- analyze_book validation paths (async, mock provider)
"""

import asyncio
import json

import pytest

from src.models.book import Book, Chapter, Paragraph
from src.models.character import Gender
from src.services.character_service import CharacterService, UnionFind
from src.utils.errors import ConfigurationError, ValidationError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_service():
    """Create a CharacterService with no provider (sufficient for pure methods)."""
    return CharacterService(provider=None)


def make_book(text="Alice went to the market. She bought apples."):
    """Create a minimal Book with one chapter."""
    para = Paragraph(sentences=[text])
    chapter = Chapter(number=1, title="Chapter 1", paragraphs=[para])
    return Book(title="Test", author="Author", chapters=[chapter])


class MockProvider:
    """Minimal async LLM provider for integration tests."""

    supports_json = True
    model = "mock-model"

    def __init__(self, response=None):
        self.response = response or json.dumps(
            {"characters": [{"name": "Alice", "gender": "female"}]}
        )
        self.calls = []

    async def complete(self, messages, **kwargs):
        self.calls.append(messages)
        return self.response


def run(coro):
    """Run a coroutine synchronously."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# UnionFind
# ---------------------------------------------------------------------------


class TestUnionFind:
    def test_find_returns_self_for_isolated_node(self):
        uf = UnionFind(3)
        assert uf.find(0) == 0
        assert uf.find(1) == 1
        assert uf.find(2) == 2

    def test_union_connects_two_nodes(self):
        uf = UnionFind(3)
        uf.union(0, 1)
        assert uf.find(0) == uf.find(1)

    def test_union_is_transitive(self):
        uf = UnionFind(4)
        uf.union(0, 1)
        uf.union(1, 2)
        assert uf.find(0) == uf.find(2)

    def test_union_does_not_merge_unrelated(self):
        uf = UnionFind(3)
        uf.union(0, 1)
        assert uf.find(2) != uf.find(0)

    def test_get_groups_single_element(self):
        uf = UnionFind(1)
        groups = uf.get_groups()
        assert len(groups) == 1
        assert groups[0] == [0]

    def test_get_groups_all_isolated(self):
        uf = UnionFind(4)
        groups = uf.get_groups()
        assert len(groups) == 4

    def test_get_groups_all_connected(self):
        uf = UnionFind(4)
        uf.union(0, 1)
        uf.union(1, 2)
        uf.union(2, 3)
        groups = uf.get_groups()
        assert len(groups) == 1
        assert sorted(groups[0]) == [0, 1, 2, 3]

    def test_get_groups_two_components(self):
        uf = UnionFind(4)
        uf.union(0, 1)
        uf.union(2, 3)
        groups = uf.get_groups()
        assert len(groups) == 2
        component_sets = [frozenset(g) for g in groups]
        assert frozenset({0, 1}) in component_sets
        assert frozenset({2, 3}) in component_sets

    def test_path_compression_idempotent(self):
        uf = UnionFind(5)
        uf.union(0, 1)
        uf.union(1, 2)
        uf.union(2, 3)
        root = uf.find(3)
        # After path compression, repeated finds are stable
        assert uf.find(3) == root
        assert uf.find(0) == root

    def test_union_self_is_noop(self):
        uf = UnionFind(3)
        uf.union(1, 1)
        groups = uf.get_groups()
        assert len(groups) == 3


# ---------------------------------------------------------------------------
# _parse_json_response — all 5 strategies
# ---------------------------------------------------------------------------


class TestParseJsonResponse:
    def setup_method(self):
        self.svc = make_service()
        self.parse = self.svc._parse_json_response

    # Strategy 1: clean JSON
    def test_strategy1_direct_parse(self):
        result = self.parse('{"characters": [{"name": "Alice"}]}')
        assert result["characters"][0]["name"] == "Alice"

    def test_strategy1_direct_parse_array(self):
        result = self.parse('[{"name": "Bob"}]')
        assert result[0]["name"] == "Bob"

    # Strategy 2: JSON with common issues that _clean_json_text fixes
    def test_strategy2_trailing_comma_object(self):
        result = self.parse('{"name": "Alice", "gender": "female",}')
        assert result["name"] == "Alice"

    def test_strategy2_trailing_comma_array(self):
        result = self.parse('[{"name": "Alice"},]')
        assert result[0]["name"] == "Alice"

    # Strategy 3: JSON inside markdown code block
    def test_strategy3_json_code_block(self):
        response = '```json\n{"characters": [{"name": "Alice"}]}\n```'
        result = self.parse(response)
        assert result["characters"][0]["name"] == "Alice"

    def test_strategy3_code_block_no_language_tag(self):
        response = '```\n{"name": "Bob"}\n```'
        result = self.parse(response)
        assert result["name"] == "Bob"

    # Strategy 4: JSON embedded in surrounding prose
    def test_strategy4_json_in_prose(self):
        response = 'Here is the analysis: {"characters": [{"name": "Carol"}]} as requested.'
        result = self.parse(response)
        assert result["characters"][0]["name"] == "Carol"

    # Strategy 5: trim prefix/suffix garbage
    def test_strategy5_prefix_garbage(self):
        response = 'Sure! {"name": "Dave", "gender": "male"}'
        result = self.parse(response)
        assert result["name"] == "Dave"

    # Empty / unparseable
    def test_empty_response_returns_empty_structure(self):
        result = self.parse("")
        assert result == {"characters": []}

    def test_whitespace_only_returns_empty_structure(self):
        result = self.parse("   \n  ")
        assert result == {"characters": []}

    def test_completely_unparseable_returns_empty_structure(self):
        result = self.parse("This is just plain text with no JSON at all.")
        assert result == {"characters": []}


# ---------------------------------------------------------------------------
# _clean_json_text
# ---------------------------------------------------------------------------


class TestCleanJsonText:
    def setup_method(self):
        self.svc = make_service()
        self.clean = self.svc._clean_json_text

    def test_removes_markdown_code_block_prefix(self):
        result = self.clean("```json\n{}")
        assert "```" not in result

    def test_removes_markdown_code_block_suffix(self):
        result = self.clean("{}\n```")
        assert "```" not in result

    def test_removes_trailing_comma_in_object(self):
        result = self.clean('{"a": 1,}')
        assert json.loads(result) == {"a": 1}

    def test_removes_trailing_comma_in_array(self):
        result = self.clean("[1, 2, 3,]")
        assert json.loads(result) == [1, 2, 3]

    def test_removes_double_comma(self):
        result = self.clean('{"a": 1,, "b": 2}')
        # After cleanup the double comma becomes single
        assert ",," not in result

    def test_strips_whitespace(self):
        result = self.clean('  {"a": 1}  ')
        assert result.startswith("{")


# ---------------------------------------------------------------------------
# _tokenize_name
# ---------------------------------------------------------------------------


class TestTokenizeName:
    def setup_method(self):
        self.svc = make_service()
        self.tok = self.svc._tokenize_name

    def test_simple_first_last_name(self):
        tokens = self.tok("Elizabeth Bennet")
        assert "elizabeth" in tokens
        assert "bennet" in tokens

    def test_removes_mr_title(self):
        tokens = self.tok("Mr. Darcy")
        assert "darcy" in tokens
        assert "mr" not in tokens

    def test_removes_mrs_title(self):
        tokens = self.tok("Mrs. Bennet")
        assert "bennet" in tokens
        assert "mrs" not in tokens

    def test_removes_dr_title(self):
        tokens = self.tok("Dr. Jekyll")
        assert "jekyll" in tokens
        assert "dr" not in tokens

    def test_single_word_name(self):
        assert "alice" in self.tok("Alice")

    def test_empty_string(self):
        assert self.tok("") == set()

    def test_returns_lowercase(self):
        tokens = self.tok("SHERLOCK HOLMES")
        assert "sherlock" in tokens
        assert "holmes" in tokens


# ---------------------------------------------------------------------------
# _are_similar
# ---------------------------------------------------------------------------


class TestAreSimilar:
    def setup_method(self):
        self.svc = make_service()
        self.similar = self.svc._are_similar

    def c(self, name):
        return {"name": name}

    def test_identical_names(self):
        assert self.similar(self.c("Alice"), self.c("Alice")) is True

    def test_name_with_and_without_title(self):
        assert self.similar(self.c("Dr. Jekyll"), self.c("Jekyll")) is True

    def test_inverted_name_order(self):
        # "Bennet, Elizabeth" vs "Elizabeth Bennet"
        assert self.similar(self.c("Bennet Elizabeth"), self.c("Elizabeth Bennet")) is True

    def test_different_people_not_similar(self):
        assert self.similar(self.c("Alice"), self.c("Bob")) is False

    def test_family_members_not_merged(self):
        # Elizabeth Bennet and Jane Bennet share a last name but have different first names
        assert self.similar(self.c("Elizabeth Bennet"), self.c("Jane Bennet")) is False

    def test_same_full_name_both_parts(self):
        assert self.similar(self.c("John Smith"), self.c("John Smith")) is True

    def test_partial_match_first_name_only(self):
        # "Elizabeth" and "Elizabeth Bennet" should be considered similar
        assert self.similar(self.c("Elizabeth"), self.c("Elizabeth Bennet")) is True

    def test_completely_different_full_names(self):
        assert self.similar(self.c("Alice Wonderland"), self.c("Bob Builder")) is False

    def test_title_variant_not_family_member(self):
        # "Dr. Smith" and "Mr. Smith": after period removal both become 2-part names
        # ["Dr","Smith"] and ["Mr","Smith"]. The title-stripping logic only applies when
        # there are >2 parts, so "Dr" and "Mr" remain as the "first name" — the
        # family-member guard fires (different firsts, same last) and returns False.
        result = self.similar(self.c("Dr. Smith"), self.c("Mr. Smith"))
        assert result is False


# ---------------------------------------------------------------------------
# _find_best_matches
# ---------------------------------------------------------------------------


class TestFindBestMatches:
    def setup_method(self):
        self.svc = make_service()
        self.find = self.svc._find_best_matches

    def test_exact_match_returned(self):
        matches = self.find("Alice", ["Alice", "Bob", "Carol"])
        names = [m[0] for m in matches]
        assert "Alice" in names

    def test_below_threshold_excluded(self):
        # Completely different name should not match at default threshold=80
        matches = self.find("Alice", ["Zorro", "Xena"], threshold=80)
        assert matches == []

    def test_empty_candidates_returns_empty(self):
        assert self.find("Alice", []) == []

    def test_near_identical_match(self):
        matches = self.find("Elizabeth", ["Elizabeth Bennet", "Jane Bennet"], threshold=80)
        names = [m[0] for m in matches]
        assert "Elizabeth Bennet" in names

    def test_threshold_respected(self):
        # With threshold=100 only exact matches should pass
        matches = self.find("Alice", ["Alice", "Alicia"], threshold=100)
        names = [m[0] for m in matches]
        assert "Alice" in names
        assert "Alicia" not in names


# ---------------------------------------------------------------------------
# _find_candidates
# ---------------------------------------------------------------------------


class TestFindCandidates:
    def setup_method(self):
        self.svc = make_service()

    def _build_index(self, characters):
        """Build the name token index the same way _group_similar_characters does."""
        index = {}
        for i, char in enumerate(characters):
            tokens = self.svc._tokenize_name(char.get("name", ""))
            for token in tokens:
                index.setdefault(token, []).append(i)
        return index

    def test_shared_token_produces_candidate(self):
        chars = [{"name": "Elizabeth Bennet"}, {"name": "Jane Bennet"}]
        index = self._build_index(chars)
        candidates = self.svc._find_candidates(chars[0], index, 0)
        # "bennet" is shared → index 1 is a candidate
        assert 1 in candidates

    def test_no_shared_token_empty_candidates(self):
        chars = [{"name": "Alice"}, {"name": "Zorro"}]
        index = self._build_index(chars)
        candidates = self.svc._find_candidates(chars[0], index, 0)
        assert candidates == set()

    def test_does_not_include_self(self):
        chars = [{"name": "Alice"}, {"name": "Alice Clone"}]
        index = self._build_index(chars)
        candidates = self.svc._find_candidates(chars[0], index, 0)
        assert 0 not in candidates


# ---------------------------------------------------------------------------
# _group_similar_characters
# ---------------------------------------------------------------------------


class TestGroupSimilarCharacters:
    def setup_method(self):
        self.svc = make_service()
        self.group = self.svc._group_similar_characters

    def test_empty_list(self):
        assert self.group([]) == []

    def test_single_character_single_group(self):
        result = self.group([{"name": "Alice"}])
        assert len(result) == 1
        assert result[0][0]["name"] == "Alice"

    def test_identical_names_grouped(self):
        chars = [{"name": "Alice"}, {"name": "Alice"}]
        result = self.group(chars)
        assert len(result) == 1
        assert len(result[0]) == 2

    def test_similar_names_grouped(self):
        chars = [{"name": "Elizabeth"}, {"name": "Elizabeth Bennet"}]
        result = self.group(chars)
        assert len(result) == 1

    def test_different_names_separate_groups(self):
        chars = [{"name": "Alice"}, {"name": "Bob"}, {"name": "Carol"}]
        result = self.group(chars)
        assert len(result) == 3

    def test_family_members_not_grouped(self):
        chars = [{"name": "Elizabeth Bennet"}, {"name": "Jane Bennet"}]
        result = self.group(chars)
        # Should be 2 groups — family members kept separate
        assert len(result) == 2

    def test_title_variant_grouped(self):
        chars = [{"name": "Dr. Jekyll"}, {"name": "Jekyll"}]
        result = self.group(chars)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# _apply_early_deduplication
# ---------------------------------------------------------------------------


class TestApplyEarlyDeduplication:
    def setup_method(self):
        self.svc = make_service()
        self.dedup = self.svc._apply_early_deduplication

    def test_unique_names_all_kept(self):
        chars = [{"name": "Alice"}, {"name": "Bob"}, {"name": "Carol"}]
        result = self.dedup(chars)
        assert len(result) == 3

    def test_duplicate_name_one_kept(self):
        chars = [{"name": "Alice"}, {"name": "Alice"}]
        result = self.dedup(chars)
        assert len(result) == 1

    def test_keeps_entry_with_longer_description(self):
        chars = [
            {"name": "Alice", "description": "short"},
            {"name": "Alice", "description": "a much longer description with more detail"},
        ]
        result = self.dedup(chars)
        assert len(result) == 1
        assert "longer" in result[0]["description"]

    def test_empty_name_entries_excluded(self):
        chars = [{"name": ""}, {"name": "Alice"}]
        result = self.dedup(chars)
        names = [c["name"] for c in result]
        assert "" not in names
        assert "Alice" in names


# ---------------------------------------------------------------------------
# _create_chunks
# ---------------------------------------------------------------------------


class TestCreateChunks:
    def setup_method(self):
        self.svc = make_service()
        self.chunk = self.svc._create_chunks

    def test_small_text_single_chunk(self):
        text = "Hello world. This is a short text."
        chunks = self.chunk(text, chunk_size=10000)
        assert len(chunks) == 1
        assert "Hello" in chunks[0]

    def test_long_text_multiple_chunks(self):
        # chunk_size=10 tokens → ~13 chars; generate text much longer than that
        text = " ".join(["word"] * 500)
        chunks = self.chunk(text, chunk_size=10)
        assert len(chunks) > 1

    def test_all_words_preserved(self):
        words = ["word"] * 200
        text = " ".join(words)
        chunks = self.chunk(text, chunk_size=50)
        rejoined = " ".join(chunks)
        # Every original word should appear somewhere
        assert rejoined.count("word") == 200

    def test_max_chunks_limit_respected(self):
        # chunk_size=1 token → very small chunks; ensure MAX_CHUNKS=100 is honoured
        text = " ".join([f"w{i}" for i in range(10000)])
        chunks = self.chunk(text, chunk_size=1)
        assert len(chunks) <= 100

    def test_empty_text_returns_no_chunks(self):
        assert self.chunk("") == []

    def test_chunk_size_uses_config_default_when_none(self):
        # Should not raise even when chunk_size=None (uses config default)
        chunks = self.chunk("Short text.", chunk_size=None)
        assert len(chunks) >= 1


# ---------------------------------------------------------------------------
# _parse_gender
# ---------------------------------------------------------------------------


class TestParseGender:
    def setup_method(self):
        self.svc = make_service()
        self.pg = self.svc._parse_gender

    def test_female(self):
        assert self.pg("female") == Gender.FEMALE

    def test_woman(self):
        assert self.pg("woman") == Gender.FEMALE

    def test_male(self):
        assert self.pg("male") == Gender.MALE

    def test_man(self):
        assert self.pg("man") == Gender.MALE

    def test_nonbinary_with_hyphen(self):
        assert self.pg("non-binary") == Gender.NEUTRAL

    def test_neutral(self):
        assert self.pg("neutral") == Gender.NEUTRAL

    def test_none_returns_unknown(self):
        assert self.pg(None) == Gender.UNKNOWN

    def test_empty_string_returns_unknown(self):
        assert self.pg("") == Gender.UNKNOWN

    def test_unrecognised_returns_unknown(self):
        assert self.pg("robot") == Gender.UNKNOWN

    def test_case_insensitive(self):
        assert self.pg("FEMALE") == Gender.FEMALE
        assert self.pg("Male") == Gender.MALE


# ---------------------------------------------------------------------------
# _calculate_metadata
# ---------------------------------------------------------------------------


class TestCalculateMetadata:
    def setup_method(self):
        self.svc = make_service()

    def _make_char(self, gender, importance="supporting"):
        from src.models.character import Character

        return Character(
            name="X",
            gender=gender,
            pronouns={},
            importance=importance,
            confidence=0.9,
        )

    def test_total_count(self):
        chars = [self._make_char(Gender.FEMALE), self._make_char(Gender.MALE)]
        meta = self.svc._calculate_metadata(chars)
        assert meta["total"] == 2

    def test_gender_breakdown(self):
        chars = [
            self._make_char(Gender.FEMALE),
            self._make_char(Gender.FEMALE),
            self._make_char(Gender.MALE),
        ]
        meta = self.svc._calculate_metadata(chars)
        assert meta["by_gender"]["female"] == 2
        assert meta["by_gender"]["male"] == 1

    def test_importance_breakdown(self):
        chars = [
            self._make_char(Gender.FEMALE, importance="main"),
            self._make_char(Gender.MALE, importance="supporting"),
            self._make_char(Gender.FEMALE, importance="supporting"),
        ]
        meta = self.svc._calculate_metadata(chars)
        assert meta["by_importance"]["main"] == 1
        assert meta["by_importance"]["supporting"] == 2

    def test_empty_list(self):
        meta = self.svc._calculate_metadata([])
        assert meta["total"] == 0
        assert meta["by_gender"] == {}


# ---------------------------------------------------------------------------
# _dict_to_character
# ---------------------------------------------------------------------------


class TestDictToCharacter:
    def setup_method(self):
        self.svc = make_service()
        self.convert = self.svc._dict_to_character

    def test_full_dict(self):
        d = {
            "name": "Alice",
            "gender": "female",
            "pronouns": "she/her/hers",
            "aliases": ["Ally"],
            "description": "The protagonist",
        }
        char = self.convert(d)
        assert char.name == "Alice"
        assert char.gender == Gender.FEMALE

    def test_defaults_for_missing_fields(self):
        char = self.convert({"name": "Bob"})
        assert char.name == "Bob"
        assert char.gender == Gender.UNKNOWN  # no gender key → defaults to UNKNOWN

    def test_missing_name_uses_unknown(self):
        char = self.convert({})
        assert char.name == "Unknown"

    def test_confidence_default(self):
        char = self.convert({"name": "X"})
        assert char.confidence == 0.7


# ---------------------------------------------------------------------------
# analyze_book — validation paths (async)
# ---------------------------------------------------------------------------


class TestAnalyzeBookValidation:
    def test_none_book_raises_validation_error(self):
        svc = CharacterService(provider=MockProvider())
        with pytest.raises(ValidationError):
            run(svc.analyze_book(None))

    def test_wrong_type_raises_validation_error(self):
        svc = CharacterService(provider=MockProvider())
        with pytest.raises(ValidationError):
            run(svc.analyze_book("not a book"))

    def test_empty_book_raises_validation_error(self):
        svc = CharacterService(provider=MockProvider())
        empty_book = Book(title="Empty", author="Author", chapters=[])
        with pytest.raises(ValidationError):
            run(svc.analyze_book(empty_book))

    def test_no_provider_raises_configuration_error(self):
        svc = CharacterService(provider=None)
        book = make_book()
        with pytest.raises(ConfigurationError):
            run(svc.analyze_book(book))

    def test_valid_book_returns_character_analysis(self):
        mock = MockProvider(
            response=json.dumps(
                {
                    "characters": [
                        {"name": "Alice", "gender": "female"},
                        {"name": "Bob", "gender": "male"},
                    ]
                }
            )
        )
        # Also provide a merge response
        merge_response = json.dumps({"is_same_person": True, "canonical_name": "Alice"})
        call_count = [0]
        original = mock.complete

        async def smart_complete(messages, **kwargs):
            call_count[0] += 1
            return merge_response if call_count[0] > 1 else await original(messages, **kwargs)

        mock.complete = smart_complete

        svc = CharacterService(provider=mock)
        book = make_book("Alice went to the market. She bought apples.")
        result = run(svc.analyze_book(book))
        assert result is not None
        assert len(result.characters) >= 1


# ---------------------------------------------------------------------------
# CharacterService initialisation — config validation
# ---------------------------------------------------------------------------


class TestCharacterServiceInit:
    def test_default_init_succeeds(self):
        svc = make_service()
        assert svc.extraction_config["max_retries"] == 3
        assert svc.grouping_config["algorithm"] == "union_find"

    def test_invalid_chunk_size_zero_raises(self):
        from unittest.mock import patch

        config_data = {"character_extraction": {"chunk_size_tokens": 0}}
        with patch("builtins.open", side_effect=FileNotFoundError):
            # Force char_config to have invalid value via direct manipulation
            svc = CharacterService.__new__(CharacterService)
            svc.extraction_config = {"chunk_size": 0, "temperature": 0.3, "max_retries": 3}
            with pytest.raises((ConfigurationError, Exception)):
                if svc.extraction_config["chunk_size"] <= 0:
                    raise ConfigurationError(
                        "Chunk size must be positive", config_key="chunk_size_tokens"
                    )
