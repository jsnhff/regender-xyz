"""A pet name should stay a pet name.

The engine has asked for nicknames alongside each new name for a while, but
only on the path where it picks the names itself. Names chosen in the
interface skipped it, so "No, Lizzy, that is what I do not choose" came out as
"No, Edward" -- a father addressing his child by her formal name -- and the
model was left free to invent its own short form per batch.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.character import Character, CharacterAnalysis, Gender
from src.models.transformation import TransformType
from src.services.name_engine import NameEngine


def cast(*specs):
    return CharacterAnalysis(
        book_id="t",
        characters=[Character(name=n, gender=g, pronouns={}, aliases=list(a)) for n, g, a in specs],
    )


ELIZABETH = cast(("Elizabeth Bennet", Gender.FEMALE, ["Lizzy", "Eliza"]))


def engine(response=None, fail=False):
    e = NameEngine.__new__(NameEngine)
    e.logger = MagicMock()
    provider = MagicMock()
    if fail:
        provider.complete = AsyncMock(side_effect=RuntimeError("no"))
    else:
        provider.complete = AsyncMock(return_value=json.dumps(response or {}))
    e.provider = provider
    return e


async def build(e, base_map, characters=ELIZABETH):
    return await e.build_name_map(characters, TransformType.GENDER_SWAP, base_map)


NICKS = {"characters": [{"name": "Edward Bennet", "nicknames": {"Lizzy": "Ned", "Eliza": "Ned"}}]}


class TestTheNicknameIsAsked:
    @pytest.mark.asyncio
    async def test_a_pet_name_maps_to_a_pet_name(self):
        e = engine(NICKS)
        name_map, _ = await build(e, {"Elizabeth": "Edward Bennet"})
        assert name_map.get("Lizzy") == "Ned"

    @pytest.mark.asyncio
    async def test_the_formal_name_is_untouched(self):
        e = engine(NICKS)
        name_map, _ = await build(e, {"Elizabeth": "Edward Bennet"})
        assert name_map.get("Elizabeth") == "Edward Bennet"

    @pytest.mark.asyncio
    async def test_every_alias_of_one_character_agrees(self):
        """One decision for the book: Lizzy and Eliza cannot diverge."""
        e = engine(NICKS)
        name_map, _ = await build(e, {"Elizabeth": "Edward Bennet"})
        assert name_map.get("Lizzy") == name_map.get("Eliza")

    @pytest.mark.asyncio
    async def test_it_costs_one_call_for_the_whole_cast(self):
        e = engine(NICKS)
        await build(
            e,
            {"Elizabeth": "Edward Bennet", "Jane": "John Bennet"},
            cast(
                ("Elizabeth Bennet", Gender.FEMALE, ["Lizzy"]),
                ("Jane Bennet", Gender.FEMALE, ["Jenny"]),
            ),
        )
        assert e.provider.complete.await_count == 1


class TestItCannotCostTheRun:
    @pytest.mark.asyncio
    async def test_a_failed_call_falls_back_to_the_formal_name(self):
        e = engine(fail=True)
        name_map, report = await build(e, {"Elizabeth": "Edward Bennet"})
        assert name_map.get("Elizabeth") == "Edward Bennet"
        assert any("nickname" in f for f in report["flags"])

    @pytest.mark.asyncio
    async def test_nonsense_json_does_not_raise(self):
        e = NameEngine.__new__(NameEngine)
        e.logger = MagicMock()
        e.provider = MagicMock()
        e.provider.complete = AsyncMock(return_value="not json at all")
        name_map, _ = await build(e, {"Elizabeth": "Edward Bennet"})
        assert name_map.get("Elizabeth") == "Edward Bennet"

    @pytest.mark.asyncio
    async def test_an_invented_nickname_is_refused(self):
        """'Edward' -> 'Lizzy' is not a short form of anything."""
        e = engine({"characters": [{"name": "Edward Bennet", "nicknames": {"Lizzy": "Lizzy"}}]})
        name_map, _ = await build(e, {"Elizabeth": "Edward Bennet"})
        assert name_map.get("Lizzy") != "Lizzy"

    @pytest.mark.asyncio
    async def test_no_nickname_aliases_means_no_call(self):
        e = engine(NICKS)
        await build(
            e, {"Elizabeth": "Edward Bennet"}, cast(("Elizabeth Bennet", Gender.FEMALE, []))
        )
        assert e.provider.complete.await_count == 0


class TestWhichAliasesCount:
    def test_a_short_form_counts(self):
        char = Character(
            name="Elizabeth Bennet", gender=Gender.FEMALE, pronouns={}, aliases=["Lizzy"]
        )
        assert NameEngine._nickname_aliases(char, "Elizabeth") == ["Lizzy"]

    def test_a_titled_alias_does_not(self):
        char = Character(
            name="Elizabeth Bennet", gender=Gender.FEMALE, pronouns={}, aliases=["Miss Elizabeth"]
        )
        assert NameEngine._nickname_aliases(char, "Elizabeth") == []

    def test_the_given_name_itself_does_not(self):
        char = Character(
            name="Elizabeth Bennet", gender=Gender.FEMALE, pronouns={}, aliases=["Elizabeth"]
        )
        assert NameEngine._nickname_aliases(char, "Elizabeth") == []
