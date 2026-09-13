"""Two people may not be given one name.

A reservation existed for this and did nothing, because it held the wrong thing.
Supplied entries are written at full scale -- "Jane Bennet Bingley" -> "Sidney
Bennet Bingley" -- so reserving the value reserved the string "sidney bennet
bingley", while what a proposal offers is the bare given name "Sidney". The two
could never match, the engine was never told the name was taken, and Jane and
Sarah were both called Sidney.

It is the last naming fault a run of Pride and Prejudice reported, and the one
that matters most: two characters under one name cannot be told apart by any
later pass, by quality control, or by a reader.
"""

import asyncio
import json
import logging

import pytest

from src.models.character import Character, CharacterAnalysis, Gender
from src.models.transformation import TransformType
from src.services.name_engine import NameEngine, audit_name_map


class Stubborn:
    """A model that keeps offering the name that is already taken."""

    model = "stub"

    def __init__(self, target="Sidney"):
        self.target = target
        self.calls = 0

    async def complete(self, *args, **kwargs):
        self.calls += 1
        return json.dumps({"renames": [{"original": "Sarah", "target": self.target}]})


@pytest.fixture
def cast():
    return CharacterAnalysis(
        book_id="t",
        characters=[
            Character(
                name="Jane Bennet Bingley",
                gender=Gender.FEMALE,
                pronouns={},
                aliases=["Jane", "Miss Bennet"],
            ),
            Character(name="Sarah", gender=Gender.FEMALE, pronouns={}),
        ],
    )


def build(cast, provider, base_map):
    engine = NameEngine(provider=provider, logger=logging.getLogger("test"))
    return asyncio.run(
        engine.build_name_map(cast, TransformType.NONBINARY, base_map=dict(base_map))
    )


class TestANameAlreadyTakenIsNotOffered:
    def test_a_supplied_given_name_is_reserved(self, cast):
        """Reserved by its given name, which is the scale a proposal answers at."""
        provider = Stubborn("Sidney")
        name_map, report = build(cast, provider, {"Jane Bennet Bingley": "Sidney Bennet Bingley"})
        assert name_map.get("Sarah") != "Sidney"
        assert any("collides" in d for d in report.get("dropped", [])), report

    def test_the_model_gets_a_second_chance(self, cast):
        """Told which name clashed, rather than silently refused."""
        provider = Stubborn("Sidney")
        build(cast, provider, {"Jane Bennet Bingley": "Sidney Bennet Bingley"})
        assert provider.calls >= 2, "it should ask again with the collision named"

    def test_a_free_name_is_accepted(self, cast):
        name_map, _ = build(
            cast, Stubborn("Meredith"), {"Jane Bennet Bingley": "Sidney Bennet Bingley"}
        )
        assert name_map.get("Sarah") == "Meredith"

    def test_the_finished_map_has_no_collision(self, cast):
        name_map, _ = build(
            cast, Stubborn("Sidney"), {"Jane Bennet Bingley": "Sidney Bennet Bingley"}
        )
        problems = [p for p in audit_name_map(name_map, cast) if "one name" in p]
        assert problems == [], problems

    def test_the_surname_is_not_reserved_with_it(self, cast):
        """Only the given name. Families share surnames, and reserving "Bennet"
        would refuse every correct rename in the book."""
        name_map, _ = build(
            cast, Stubborn("Bennet"), {"Jane Bennet Bingley": "Sidney Bennet Bingley"}
        )
        # "Bennet" is refused for being a live surname, not for being reserved
        # as a target -- either way it must not become Sarah's name.
        assert name_map.get("Sarah") != "Bennet"


class TestTheRunThatFoundIt:
    def test_the_audit_reports_it(self):
        """The wording the reader saw, kept so the connection survives.

        Both sides bare, which is the shape the run actually produced: the
        engine's proposals are given names, and it was a proposal for Sarah
        that landed on the name Jane already had.
        """
        cast = CharacterAnalysis(
            book_id="t",
            characters=[
                Character(name="Jane", gender=Gender.FEMALE, pronouns={}),
                Character(name="Sarah", gender=Gender.FEMALE, pronouns={}),
            ],
        )
        problems = audit_name_map({"Jane": "Sidney", "Sarah": "Sidney"}, cast)
        assert any("2 different characters" in p for p in problems), problems

    def test_two_people_under_different_surnames_are_left_alone(self):
        """The audit deliberately allows this: Austen's own cast has two Marys,
        and a surname tells them apart. Reporting it would bury the real ones."""
        cast = CharacterAnalysis(
            book_id="t",
            characters=[
                Character(name="Caroline Bingley", gender=Gender.FEMALE, pronouns={}),
                Character(name="Kitty Bennet", gender=Gender.FEMALE, pronouns={}),
            ],
        )
        problems = audit_name_map(
            {"Caroline Bingley": "Christopher Bingley", "Kitty Bennet": "Christopher Bennet"},
            cast,
        )
        assert not [p for p in problems if "one name" in p], problems
