"""The cast's own answers have to reach the prompt that uses them.

Two fields were being thrown away on every run of every book.

The extraction prompt asks for pronouns as a string -- "she/her/hers" -- and the
field holds a dict, so a character built straight from the reply carried a string
where every reader expects a mapping. Only the reload path converted it, which is
why all ninety saved entries read {} and the transform prompt described the whole
cast as they/them, including Elizabeth Bennet.

Importance was worse: hard-coded to "supporting" at both construction sites, so
get_main_characters() returned nothing on every run, the interface's "Main
characters" block never rendered, and the prompt had no way to say which of
ninety people the book is about.
"""

import pytest

from src.models.character import CharacterAnalysis, normalise_pronouns
from src.services.character_service import CharacterService


@pytest.fixture
def svc():
    return CharacterService.__new__(CharacterService)


class TestReadingPronouns:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("she/her/hers", {"subject": "she", "object": "her", "possessive": "hers"}),
            ("he/him/his", {"subject": "he", "object": "him", "possessive": "his"}),
            ("they/them/theirs", {"subject": "they", "object": "them", "possessive": "theirs"}),
            # Two parts is enough; the possessive doubles the object.
            ("she/her", {"subject": "she", "object": "her", "possessive": "her"}),
            # Some replies use commas.
            ("he, him, his", {"subject": "he", "object": "him", "possessive": "his"}),
            # A dict comes through as it is, minus empties.
            ({"subject": "she", "object": "her"}, {"subject": "she", "object": "her"}),
            ({"subject": "she", "object": ""}, {"subject": "she"}),
            # Nothing usable is nothing, not a guess.
            ("", {}),
            (None, {}),
            ("she", {}),
        ],
    )
    def test_whatever_the_model_sent(self, value, expected):
        assert normalise_pronouns(value) == expected


class TestReadingImportance:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("main", "main"),
            ("major", "main"),
            ("supporting", "supporting"),
            ("minor", "minor"),
            # Numbers are how some replies answer it.
            ("10", "main"),
            ("8", "main"),
            ("5", "supporting"),
            ("2", "minor"),
            # Anything unreadable lands in the middle rather than at an extreme.
            ("", "supporting"),
            (None, "supporting"),
            ("very important indeed", "supporting"),
        ],
    )
    def test_whatever_the_model_sent(self, svc, value, expected):
        char = svc._dict_to_character({"name": "X", "gender": "female", "importance": value})
        assert char.importance == expected


class TestTheFieldsSurviveIntoTheCharacter:
    def test_a_reply_is_carried_through_whole(self, svc):
        char = svc._dict_to_character(
            {
                "name": "Elizabeth Bennet",
                "gender": "female",
                "pronouns": "she/her/hers",
                "importance": "main",
                "titles": ["Miss"],
                "aliases": ["Lizzy", "Eliza"],
            }
        )
        assert char.pronouns == {"subject": "she", "object": "her", "possessive": "hers"}
        assert char.importance == "main"
        assert char.titles == ["Miss"]
        assert char.aliases == ["Lizzy", "Eliza"]

    def test_a_round_trip_keeps_them(self, svc):
        char = svc._dict_to_character(
            {"name": "Mr. Stone", "gender": "male", "pronouns": "he/him", "importance": "minor"}
        )
        analysis = CharacterAnalysis(book_id="t", characters=[char])
        again = CharacterAnalysis.from_dict(analysis.to_dict())
        assert again.characters[0].pronouns == char.pronouns
        assert again.characters[0].importance == "minor"


class TestWhatThePromptIsTold:
    def test_the_main_characters_are_findable(self, svc):
        cast = CharacterAnalysis(
            book_id="t",
            characters=[
                svc._dict_to_character(
                    {
                        "name": "Elizabeth Bennet",
                        "gender": "female",
                        "pronouns": "she/her/hers",
                        "importance": "main",
                    }
                ),
                svc._dict_to_character(
                    {
                        "name": "Mr. Stone",
                        "gender": "male",
                        "pronouns": "he/him",
                        "importance": "minor",
                    }
                ),
            ],
        )
        assert [c.name for c in cast.get_main_characters()] == ["Elizabeth Bennet"]

    def test_the_context_names_her_own_pronouns(self, svc):
        """It used to say they/them for every character in the book."""
        cast = CharacterAnalysis(
            book_id="t",
            characters=[
                svc._dict_to_character(
                    {
                        "name": "Elizabeth Bennet",
                        "gender": "female",
                        "pronouns": "she/her/hers",
                        "importance": "main",
                    }
                )
            ],
        )
        context = cast.create_context_string()
        assert "she/her" in context
        assert "they/them" not in context


class TestThePromptAsksForThem:
    def test_importance_and_a_pronoun_shape_are_requested(self):
        from src.services.prompts import EXTRACTION_PROMPT_TEMPLATE

        assert '"importance"' in EXTRACTION_PROMPT_TEMPLATE
        assert "subject/object/possessive" in EXTRACTION_PROMPT_TEMPLATE
