"""The naming run that failed, replayed against the real cast.

Every naming defect so far has been found by Jason running the real thing and
not by the tests, because the tests fed hand-made casts of two or three people
to the function that had just been edited. This replays the run of
2026-09-13 -- eighty real characters with their real aliases, and the model
output that actually collided -- through the functions the app actually calls.

The run reported six characters sharing a name with another character:

    'aubrey'  Anne, William        'morgan'  Maria, Mary
    'clare'   Catherine, Kitty     'shirley' Lewis, Sally
    'leslie'  Louisa, Lydia        'sidney'  Charles, Jane

The cause was two naming paths. The engine's own validator refused a target
already used for another character in the same batch; the interface's
suggestion loop, whose approved output becomes base_map and outranks the
engine, had no such rule -- it checked each suggestion against the cast and
nothing against the other suggestions. So the weaker screen decided the book.
"""

import asyncio
import json
import logging
from pathlib import Path

import pytest

from src.models.character import CharacterAnalysis
from src.services.character_service import CharacterService
from src.services.name_engine import claimed_given, screen_renames

FIXTURE = Path(__file__).parent / "fixtures" / "pride-and-prejudice-cast.json"


@pytest.fixture(scope="module")
def cast():
    """The cast as the analysis actually produced it, aliases and all."""
    return CharacterAnalysis.from_dict(json.loads(FIXTURE.read_text()))


# What the model offered on the run that failed, in the book's own full forms.
COLLIDING = [
    {"original": "Miss Anne de Bourgh", "suggested": "Aubrey de Bourgh"},
    {"original": "William Goulding", "suggested": "Aubrey Goulding"},
    {"original": "Louisa Hurst", "suggested": "Leslie Hurst"},
    {"original": "Lydia Bennet Wickham", "suggested": "Leslie Bennet Wickham"},
    {"original": "Maria Lucas", "suggested": "Morgan Lucas"},
    {"original": "Mary Bennet", "suggested": "Morgan Bennet"},
    {"original": "Charles Bingley", "suggested": "Sidney Bingley"},
    {"original": "Jane Bennet Bingley", "suggested": "Sidney Bennet Bingley"},
]


class Recorded:
    """A provider that replays one recorded answer, so no key and no spend."""

    model = "recorded"

    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    async def complete(self, *args, **kwargs):
        self.calls += 1
        return json.dumps(self.payload)


def suggestions_for(cast, payload):
    """Run the interface's suggestion step exactly as the TUI calls it."""
    service = CharacterService.__new__(CharacterService)
    service.provider = Recorded(payload)
    service.logger = logging.getLogger("replay")
    service._complete_with_retry = lambda prompt, temperature=0.5: service.provider.complete()
    return asyncio.run(service.suggest_name_alternatives(cast, "nonbinary"))


def given_names(entries):
    counts: dict[str, list] = {}
    for entry in entries:
        first = entry["suggested"].split()[0].lower()
        counts.setdefault(first, []).append(entry["original"])
    return counts


class TestTheRunThatFailed:
    def test_the_real_cast_is_what_is_being_tested(self, cast):
        """Eighty people, not the three a hand-made fixture would have."""
        assert len(cast.characters) > 70
        names = {c.name for c in cast.characters}
        assert "Jane Bennet Bingley" in names
        assert "Lady Catherine de Bourgh" in names

    def test_no_two_characters_are_offered_one_name(self, cast):
        offered = suggestions_for(cast, COLLIDING)
        shared = {given: who for given, who in given_names(offered).items() if len(who) > 1}
        assert shared == {}, f"still offering one name to two people: {shared}"

    def test_the_first_of_a_clashing_pair_survives(self, cast):
        """Refusing both would be a worse answer than refusing one: the
        character falls through to the engine, which has the attested pool."""
        offered = suggestions_for(cast, COLLIDING)
        assert any(e["original"] == "Miss Anne de Bourgh" for e in offered)

    @pytest.mark.parametrize(
        "loser", ["William Goulding", "Lydia Bennet Wickham", "Mary Bennet", "Jane Bennet Bingley"]
    )
    def test_the_second_is_refused(self, cast, loser):
        offered = suggestions_for(cast, COLLIDING)
        assert not any(e["original"] == loser for e in offered)

    def test_a_batch_with_no_clash_is_untouched(self, cast):
        """The gate must not cost correct suggestions; this is the shape of a
        good batch and every entry should survive it."""
        clean = [
            {"original": "Miss Anne de Bourgh", "suggested": "Aubrey de Bourgh"},
            {"original": "William Goulding", "suggested": "Vivian Goulding"},
            {"original": "Louisa Hurst", "suggested": "Leslie Hurst"},
            {"original": "Maria Lucas", "suggested": "Morgan Lucas"},
        ]
        offered = suggestions_for(cast, clean)
        assert len(offered) == len(clean), [e["original"] for e in offered]


class TestTheGateIsShared:
    """The rule lived in the engine and not in the interface, which is why the
    interface shipped the book. It now lives in one place; these say so."""

    def test_the_engine_validator_still_refuses_a_repeat(self):
        from src.services.name_engine import NameEngine

        engine = NameEngine(provider=None, logger=logging.getLogger("t"))
        accepted, problems, _skips = engine._validate(
            {
                "Anne": {"target": "Aubrey"},
                "William": {"target": "Aubrey"},
            },
            [{"given": "Anne"}, {"given": "William"}],
            reserved=set(),
        )
        assert list(accepted) == ["Anne"]
        assert any("already used for another character" in p for p in problems)

    def test_the_shared_gate_refuses_the_same_thing(self, cast):
        accepted, reasons = screen_renames(
            [("Miss Anne de Bourgh", "Aubrey de Bourgh"), ("William Goulding", "Aubrey Goulding")],
            cast,
        )
        assert len(accepted) == 1
        assert any("two people, one name" in r for r in reasons)

    def test_two_forms_of_one_person_may_share_a_name(self, cast):
        """Catherine Bennet answers to Kitty. Both must become the same person,
        and calling that a collision is the opposite of the truth."""
        accepted, reasons = screen_renames(
            [("Catherine Bennet", "Clare Bennet"), ("Kitty Bennet", "Clare Bennet")],
            cast,
        )
        assert len(accepted) == 2, reasons


class TestWhatAProposalClaims:
    def test_a_term_substitution_claims_no_name(self):
        """ "The chambermaid" -> "The chamberperson" must not reserve a word."""
        assert claimed_given("The chambermaid", "The chamberperson") == ""

    def test_a_person_claims_their_given_name(self):
        assert claimed_given("Jane Bennet Bingley", "Sidney Bennet Bingley") == "sidney"

    def test_a_title_is_not_the_claim(self):
        assert claimed_given("Sir William Lucas", "Noble Vivian Lucas") == "vivian"
