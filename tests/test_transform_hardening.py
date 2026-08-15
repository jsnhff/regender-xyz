"""
Tests for the Aug-2026 transform hardening: single-pass term maps, protected
surnames/places, the deterministic name engine, and the QC gates. Each test
encodes a failure class observed in the May-2026 P&P print books.
"""

import asyncio
import json

import pytest

from src.models.character import Character, CharacterAnalysis, Gender
from src.models.transformation import TransformType
from src.services.name_engine import NameEngine
from src.services.qc_gates import run_qc_gates
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
                aliases=["Mr. Darcy"],
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


class TestTermMap:
    def test_nonbinary_honorifics_and_titles(self, ts):
        out = ts._apply_term_map(
            'Sir William smiled. "Yes, sir," said Miss Bingley to Mrs. Hurst and Mr. Darcy.',
            TransformType.NONBINARY,
        )
        assert "Noble William" in out
        assert "Mx. Bingley" in out
        assert "Mx. Hurst" in out
        assert "Mx. Darcy" in out
        assert "sir" not in out.lower().replace("mx.", "")

    def test_nonbinary_verb_agreement(self, ts):
        out = ts._apply_term_map(
            "they was glad; they likes walking; they has seen it; they dines at six",
            TransformType.NONBINARY,
        )
        assert "they were glad" in out
        assert "they like walking" in out
        assert "they have seen" in out
        assert "they dine at six" in out

    def test_nonbinary_vocative_no_double_period(self, ts):
        out = ts._apply_term_map("Thank you, ma'am.", TransformType.NONBINARY)
        assert "Mx.." not in out
        assert "Mx." in out

    def test_all_male_maam_and_miss(self, ts):
        out = ts._apply_term_map('"Indeed, ma\'am," said Miss Lucas.', TransformType.ALL_MALE)
        assert "sir" in out
        assert "Mr. Lucas" in out

    def test_gender_swap_term_map_is_noop(self, ts):
        # After a swap both genders' words are legitimate; a global map would
        # re-swap correct output (the sequential version collapsed pairs).
        text = "His mother said the queen and the king were kind to her father."
        assert ts._apply_term_map(text, TransformType.GENDER_SWAP) == text

    def test_single_pass_no_chaining(self, ts):
        # all_female: father→mother must not be re-hit by any other entry.
        out = ts._apply_term_map("Her father and her mother.", TransformType.ALL_FEMALE)
        assert "mother" in out
        assert out.count("mother") == 2

    def test_protected_surname_king(self, ts, pp_cast):
        pats = ts._build_protected_patterns(pp_cast, TransformType.NONBINARY)
        out = ts._apply_term_map(
            "Mary King met the king, and Miss King curtsied.", TransformType.NONBINARY, pats
        )
        assert "Mary King" in out
        assert "Mx. King" in out  # title transformed, surname kept
        assert "the monarch" in out  # common noun still mapped

    def test_lowercase_miss_verb_untouched(self, ts):
        out = ts._apply_term_map("I shall miss you terribly.", TransformType.NONBINARY)
        assert "miss you" in out


# ------------------------------------------------------------- name map


class TestNameMap:
    def test_word_boundaries_eliza_vs_elizabeth(self, ts):
        nm = {"Elizabeth": "Elliot", "Eliza": "Ned"}
        out = ts._apply_name_map("Elizabeth wrote to Eliza.", nm)
        assert out == "Elliot wrote to Ned."

    def test_case_sensitive_nicknames(self, ts):
        nm = {"Will": "Willa", "Kit": "Kate"}
        out = ts._apply_name_map("Will said he will kit out the boat with Kit.", nm)
        assert out == "Willa said he will kit out the boat with Kate."

    def test_all_caps_signature(self, ts):
        nm = {"Fitzwilliam Darcy": "Frances Darcy", "Lydia": "Lionel"}
        out = ts._apply_name_map("FITZWILLIAM DARCY. LYDIA BENNET.", nm)
        assert "FRANCES DARCY." in out
        assert "LIONEL BENNET." in out

    def test_phrase_precedence_over_token(self, ts):
        nm = {"Catherine": "Christopher", "Lady Catherine": "Lord Christopher"}
        out = ts._apply_name_map("Lady Catherine scolded; Catherine laughed.", nm)
        assert "Lord Christopher scolded" in out
        assert "Christopher laughed" in out

    def test_place_names_protected(self, ts):
        nm = {"James": "Jane", "Edward": "Edwina", "George": "Georgette"}
        text = (
            "They were presented at St. James's, lodged on Edward Street, and dined at the George."
        )
        out = ts._apply_name_map(text, nm)
        assert "St. James's" in out
        assert "Edward Street" in out
        assert "the George" in out

    def test_surname_scoped_fitzwilliam(self, ts):
        nm = {"Fitzwilliam Darcy": "Frances Darcy"}
        out = ts._apply_name_map("Fitzwilliam Darcy bowed to Colonel Fitzwilliam.", nm)
        assert "Frances Darcy" in out
        assert "Colonel Fitzwilliam" in out


# ---------------------------------------------------------- name engine


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


class TestQCGates:
    ORIG = (
        "Elizabeth Bennet met Mary King near St. James's. "
        "Sir William Lucas bowed. They walked down Edward Street."
    )
    NAME_MAP = {
        "Elizabeth": "Ellis",
        "Lizzy": "Ellis",
        "William": "Wil",
        "Sir William": "Noble Wil",
    }

    def test_catches_all_may_2026_failure_classes(self, pp_cast):
        bad = (
            "Ellis Bennet met Mary Monarch near St. James's. "  # surname mutated
            "Lady William Lucas bowed, and she said Miss Bingley knew. "  # atomicity + residual
            "they was pleased. Colonelle Fitzwilliam and Elizabeth arrived. "  # verb + rank + rename residual
            "They walked down Edward Street."
        )
        result = run_qc_gates(
            original_text=self.ORIG,
            transformed_text=bad,
            transform_type="nonbinary",
            characters=pp_cast,
            name_map=self.NAME_MAP,
            original_chapters=61,
            transformed_chapters=61,
        )
        assert result["passed"] is False
        verdicts = {g["name"]: g["verdict"] for g in result["gates"]}
        assert verdicts["residual_gender"] == "FAIL"
        assert verdicts["verb_agreement"] == "FAIL"
        assert verdicts["name_consistency"] == "FAIL"
        assert verdicts["surname_place_immutability"] == "FAIL"
        assert verdicts["title_name_atomicity"] == "FAIL"

    def test_clean_output_passes(self, pp_cast):
        good = (
            "Ellis Bennet met Mary King near St. James's. "
            "Noble Wil Lucas bowed, and they said Mx. Bingley knew. "
            "they were pleased. They walked down Edward Street."
        )
        result = run_qc_gates(
            original_text=self.ORIG,
            transformed_text=good,
            transform_type="nonbinary",
            characters=pp_cast,
            name_map=self.NAME_MAP,
            original_chapters=61,
            transformed_chapters=61,
        )
        assert result["passed"] is True

    def test_chapter_count_gate(self, pp_cast):
        result = run_qc_gates(
            original_text="x",
            transformed_text="x",
            transform_type="gender_swap",
            characters=pp_cast,
            name_map={},
            original_chapters=61,
            transformed_chapters=49,
        )
        assert result["passed"] is False

    def test_they_allowlist_no_false_positives(self):
        text = "they express regret; they always pass; they miss the Bennets; they address the room"
        result = run_qc_gates(
            original_text=text,
            transformed_text=text,
            transform_type="nonbinary",
            characters=None,
            name_map={},
        )
        verdicts = {g["name"]: g["verdict"] for g in result["gates"]}
        assert verdicts["verb_agreement"] == "PASS"
