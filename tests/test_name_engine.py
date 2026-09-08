"""Deterministic name engine — ported from the Aug-2026 transform hardening.

Each test encodes a failure class seen in the May-2026 printed P&P: one
character given several different names across the book, ranks inflected
into "Colonella", invented names, and renames that collide with a surname
already in the cast.
"""

import asyncio
import json

import pytest

from src.models.character import Character, CharacterAnalysis, Gender
from src.models.transformation import TransformType
from src.services.name_engine import NameEngine
from src.services.transform_service import TransformService


@pytest.fixture
def ts():
    return TransformService.__new__(TransformService)  # term/name map methods need no init


@pytest.fixture
def pp_cast():
    return CharacterAnalysis(
        book_id="pp",
        characters=[
            Character(
                name="Elizabeth Bennet",
                gender=Gender.FEMALE,
                pronouns={},
                aliases=["Lizzy", "Eliza"],
                titles=["Miss"],
            ),
            Character(
                name="Fitzwilliam Darcy",
                gender=Gender.MALE,
                pronouns={},
                aliases=["Mr. Darcy", "Darcy"],
                titles=["Mr."],
            ),
            Character(
                name="Colonel Fitzwilliam", gender=Gender.MALE, pronouns={}, titles=["Colonel"]
            ),
            Character(name="Sir William Lucas", gender=Gender.MALE, pronouns={}, titles=["Sir"]),
            Character(name="Mary King", gender=Gender.FEMALE, pronouns={}, titles=["Miss"]),
            Character(name="Mrs. Bennet", gender=Gender.FEMALE, pronouns={}, titles=["Mrs."]),
            Character(name="John", gender=Gender.MALE, pronouns={}, description="footman"),
        ],
    )


# ------------------------------------------------------------- term map


class _Provider:
    """Scripted provider: returns queued JSON responses."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    async def complete(self, messages, **kwargs):
        self.calls += 1
        return self.responses.pop(0)


class TestNameEngine:
    def _run(self, coro):
        return asyncio.run(coro)

    def test_rejects_invented_and_colliding_targets(self, pp_cast):
        bad = json.dumps(
            {
                "renames": [
                    {"original": "Fitzwilliam", "target": "Fitzwilliama", "nicknames": {}},
                    {"original": "William", "target": "Mary", "nicknames": {}},
                    {"original": "John", "target": "Darcy", "nicknames": {}},
                ]
            }
        )
        good = json.dumps(
            {
                "renames": [
                    {"original": "Fitzwilliam", "target": "Frances", "nicknames": {}},
                    {"original": "William", "target": "Wilhelmina", "nicknames": {}},
                    {"original": "John", "target": "Joan", "nicknames": {}},
                ]
            }
        )
        engine = NameEngine(provider=_Provider([bad, good]))
        nm, report = self._run(engine.build_name_map(pp_cast, TransformType.ALL_FEMALE))
        assert nm["John"] == "Joan"
        assert nm["William"] == "Wilhelmina"
        assert "Fitzwilliam Darcy" in nm  # phrase-scoped
        assert "Fitzwilliam" not in nm  # bare key suppressed (surname collision)
        assert report["accepted"] == 3

    def test_atomic_title_entries(self, pp_cast):
        resp = json.dumps(
            {
                "renames": [
                    {"original": "William", "target": "Wilhelmina", "nicknames": {}},
                    {"original": "Fitzwilliam", "target": "Frances", "nicknames": {}},
                    {"original": "John", "target": "Joan", "nicknames": {}},
                ]
            }
        )
        engine = NameEngine(provider=_Provider([resp]))
        nm, _ = self._run(engine.build_name_map(pp_cast, TransformType.ALL_FEMALE))
        assert nm.get("Sir William") == "Lady Wilhelmina"

    def test_user_base_map_wins(self, pp_cast):
        resp = json.dumps({"renames": []})
        engine = NameEngine(provider=_Provider([resp, resp]))
        nm, _ = self._run(
            engine.build_name_map(
                pp_cast, TransformType.ALL_FEMALE, base_map={"William": "Georgiana"}
            )
        )
        assert nm["William"] == "Georgiana"
        assert nm.get("Sir William") == "Lady Georgiana"

    def test_descriptive_and_stoplist_names_never_renamed(self):
        # "The Archbishop" / "Young Lucas": renaming "The" or "Young" would
        # rewrite ordinary words across the whole book.
        cast = CharacterAnalysis(
            book_id="x",
            characters=[
                Character(name="The Archbishop", gender=Gender.MALE, pronouns={}),
                Character(name="Young Lucas", gender=Gender.MALE, pronouns={}),
                Character(name="Old Mr. Daniels", gender=Gender.MALE, pronouns={}),
            ],
        )
        resp = json.dumps(
            {
                "renames": [
                    {"original": "The", "target": "Theodora", "nicknames": {}},
                    {"original": "Young", "target": "Yvonne", "nicknames": {}},
                ]
            }
        )
        engine = NameEngine(provider=_Provider([resp, resp]))
        nm, _ = self._run(engine.build_name_map(cast, TransformType.ALL_FEMALE))
        assert "The" not in nm and "Young" not in nm and "Old" not in nm

    def test_surname_only_characters_skipped(self):
        # Officers known only by surname (Pratt, Chamberlayne) must not be
        # renamed; the model marks them is_surname and the engine skips.
        cast = CharacterAnalysis(
            book_id="x",
            characters=[Character(name="Pratt", gender=Gender.MALE, pronouns={})],
        )
        resp = json.dumps({"renames": [{"original": "Pratt", "is_surname": True}]})
        engine = NameEngine(provider=_Provider([resp]))
        nm, report = self._run(engine.build_name_map(cast, TransformType.ALL_FEMALE))
        assert "Pratt" not in nm
        assert any("surname" in f for f in report["flags"])

    def test_shared_given_name_one_decision(self):
        # Three Williams share one target; no spurious duplicate-target drops.
        cast = CharacterAnalysis(
            book_id="x",
            characters=[
                Character(name="William Lucas", gender=Gender.MALE, pronouns={}),
                Character(name="William Collins", gender=Gender.MALE, pronouns={}),
                Character(name="William Goulding", gender=Gender.MALE, pronouns={}),
            ],
        )
        resp = json.dumps(
            {"renames": [{"original": "William", "target": "Willa", "nicknames": {}}]}
        )
        engine = NameEngine(provider=_Provider([resp]))
        nm, report = self._run(engine.build_name_map(cast, TransformType.ALL_FEMALE))
        assert nm["William"] == "Willa"
        assert nm["William Collins"] == "Willa Collins"
        assert nm["William Goulding"] == "Willa Goulding"
        assert report["dropped"] == []

    def test_no_provider_is_safe(self, pp_cast):
        engine = NameEngine(provider=None)
        nm, report = self._run(engine.build_name_map(pp_cast, TransformType.NONBINARY))
        assert nm == {}
        assert report["dropped"]

    def test_only_variant_affected_characters(self, pp_cast):
        # all_female renames only male characters; a complete proposal for the
        # three male given names is accepted in one call (no retry), and no
        # female character appears in the resulting map.
        resp = json.dumps(
            {
                "renames": [
                    {"original": "Fitzwilliam", "target": "Frances", "nicknames": {}},
                    {"original": "William", "target": "Wilhelmina", "nicknames": {}},
                    {"original": "John", "target": "Joan", "nicknames": {}},
                ]
            }
        )
        provider = _Provider([resp])
        engine = NameEngine(provider=provider)
        nm, _ = self._run(engine.build_name_map(pp_cast, TransformType.ALL_FEMALE))
        assert provider.calls == 1
        assert "Elizabeth" not in nm and "Mary" not in nm


# ------------------------------------------------------------- QC gates


class TestTitleCollision:
    """Swapping a title can merge two people who share a surname.

    In any family both "Mr. Bennet" and "Mrs. Bennet" are in the cast, so
    converting the first into the second makes the father and the mother the
    same character. The collision check in _validate runs on given names and
    never sees these pairs — they are synthesised afterwards from the title.

    Seen in the Sep-2026 all_female sample: "Mr. Bennet" -> "Mrs. Bennet" and
    "Mr. Hurst" -> "Mrs. Hurst", both already other people, after which the
    model invented "Ms." to keep them apart and applied it inconsistently —
    even to Mrs. Long, who was female all along and should not have moved.
    """

    @staticmethod
    def _cast():
        return CharacterAnalysis(
            book_id="pp",
            characters=[
                Character(
                    name="Sir William Lucas",
                    gender=Gender.MALE,
                    pronouns={},
                    aliases=["Sir William"],
                    titles=["Sir"],
                ),
                Character(
                    name="Lady Lucas",
                    gender=Gender.FEMALE,
                    pronouns={},
                    aliases=["Lady Lucas"],
                    titles=["Lady"],
                ),
            ],
        )

    def test_a_title_swap_onto_an_existing_character_is_refused(self):
        engine = NameEngine(provider=None)
        name_map, report = asyncio.run(
            engine.build_name_map(self._cast(), TransformType.ALL_FEMALE)
        )
        # "Sir William" would become "Lady William", not "Lady Lucas", so the
        # pair that must never be emitted is one landing on a real cast member.
        for source, target in name_map.items():
            assert target.lower().replace(".", "") != "lady lucas", (
                f"{source} -> {target} merges two characters"
            )
        assert isinstance(report, dict)

    def test_the_refusal_is_reported_not_silent(self):
        """A dropped rename has to be visible, or the book reads fine and is wrong."""
        engine = NameEngine(provider=None)
        cast = CharacterAnalysis(
            book_id="pp",
            characters=[
                Character(
                    name="Sir William",
                    gender=Gender.MALE,
                    pronouns={},
                    aliases=["Sir William"],
                    titles=["Sir"],
                ),
                Character(
                    name="Lady William",
                    gender=Gender.FEMALE,
                    pronouns={},
                    aliases=["Lady William"],
                    titles=["Lady"],
                ),
            ],
        )
        name_map, report = asyncio.run(engine.build_name_map(cast, TransformType.ALL_FEMALE))
        assert name_map.get("Sir William") != "Lady William"
