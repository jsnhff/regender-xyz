# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Jason Huff
"""\"Keep the originals\" keeps them.

The name review offers four answers, and one of them is to keep every name the
book already uses. Choosing it cleared the map and started the run -- and no
map is precisely what tells the engine to choose names itself. So the reader
declined every rename, was told "Keeping original names", and got a book in
which sixteen characters had been renamed by a call they never saw.

Three things have to hold for the answer to mean what it says:

- the engine proposes nothing,
- the model is told a character with no new name keeps theirs, since a model
  left to fill that gap fills it differently in every batch,
- and QC can see a kept name go missing, because with no map every other name
  check stands down.
"""

import asyncio
import inspect

import pytest

from src.models.character import Character, CharacterAnalysis, Gender
from src.models.transformation import TransformType
from src.services.name_engine import NameEngine
from src.services.qc_service import QCService
from src.services.transform_service import TransformService


@pytest.fixture
def cast():
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
            Character(name="Jane Bennet", gender=Gender.FEMALE, pronouns={}, titles=["Miss"]),
            Character(
                name="Fitzwilliam Darcy",
                gender=Gender.MALE,
                pronouns={},
                aliases=["Mr. Darcy", "Darcy"],
                titles=["Mr."],
            ),
        ],
    )


class _Provider:
    def __init__(self):
        self.calls = 0

    async def complete(self, messages, **kwargs):
        self.calls += 1
        return (
            '{"renames": [{"original": "Elizabeth", "target": "Edmund"},'
            ' {"original": "Jane", "target": "Jonas"}]}'
        )


def _build(provider, cast, **kwargs):
    return asyncio.run(
        NameEngine(provider=provider).build_name_map(cast, TransformType.ALL_MALE, **kwargs)
    )


class TestTheEngineProposesNothing:
    def test_left_to_itself_it_renames(self, cast):
        """The behaviour "keep" was getting: no map in, a full map out."""
        provider = _Provider()
        name_map, _ = _build(provider, cast)
        assert provider.calls >= 1
        assert name_map.get("Elizabeth") == "Edmund"

    def test_asked_to_keep_it_makes_no_call_and_no_entries(self, cast):
        provider = _Provider()
        name_map, report = _build(provider, cast, propose=False)
        assert provider.calls == 0
        assert name_map == {}
        assert report["accepted"] == 0

    def test_keeping_is_reported_as_a_choice_not_a_failure(self, cast):
        _, report = _build(_Provider(), cast, propose=False)
        assert report["dropped"] == []
        assert report["kept"] == 2
        assert any("kept as written" in flag for flag in report["flags"])

    def test_a_rename_the_reader_did_supply_is_still_applied(self, cast):
        provider = _Provider()
        name_map, _ = _build(
            provider, cast, base_map={"Elizabeth Bennet": "Edmund Bennet"}, propose=False
        )
        assert name_map.get("Elizabeth") == "Edmund"
        assert "Jane" not in name_map, "the engine added a rename nobody asked for"


class TestTheChoiceReachesTheEngine:
    def test_process_book_takes_it(self):
        from src.app import Application

        assert "keep_names" in inspect.signature(Application.process_book).parameters

    def test_the_pipeline_makes_no_naming_call(self, app_with_mock, simple_story_path, tmp_path):
        result = asyncio.run(
            app_with_mock.process_book(
                file_path=simple_story_path,
                transform_type="gender_swap",
                output_path=str(tmp_path / "out.json"),
                keep_names=True,
            )
        )
        assert result["success"] is True
        provider = app_with_mock.context.get_service("llm_provider")
        naming = [
            call
            for call in provider.calls
            if "choosing replacement GIVEN NAMES" in call["messages"][-1]["content"]
        ]
        assert naming == []

    def test_without_it_the_pipeline_does_ask(self, app_with_mock, simple_story_path, tmp_path):
        """The control: the test above passes for the right reason."""
        asyncio.run(
            app_with_mock.process_book(
                file_path=simple_story_path,
                transform_type="gender_swap",
                output_path=str(tmp_path / "out.json"),
            )
        )
        provider = app_with_mock.context.get_service("llm_provider")
        assert any(
            "choosing replacement GIVEN NAMES" in call["messages"][-1]["content"]
            for call in provider.calls
        )

    def test_the_interface_records_the_answer(self):
        """K sets the flag; accepting the suggestions clears it again."""
        from src.cli.tui import RegenderTUI

        source = inspect.getsource(RegenderTUI._handle_name_review_input)
        keep = source.split('elif v == "k"')[1].split("elif")[0]
        accept = source.split('if v in ("a", "")')[1].split("elif")[0]
        assert "self._keep_names = True" in keep
        assert "self._keep_names = False" in accept
        assert "keep_names=" in inspect.getsource(RegenderTUI._run_processing)

    def test_the_command_line_has_the_flag(self):
        import regender_cli

        assert "--keep-names" in inspect.getsource(regender_cli)


class TestTheModelIsToldToLeaveNamesAlone:
    def test_the_rule_is_in_the_cast_instructions(self, cast):
        service = TransformService.__new__(TransformService)
        mappings = {c.name: {} for c in cast.characters}
        text = service._build_character_instructions(cast, TransformType.ALL_MALE, mappings, {})
        assert "Never invent or substitute a name" in text
        assert "Titles and other gendered words still change" in text

    def test_a_chosen_name_is_still_given(self, cast):
        service = TransformService.__new__(TransformService)
        mappings = {c.name: {} for c in cast.characters}
        text = service._build_character_instructions(
            cast, TransformType.ALL_MALE, mappings, {"Elizabeth Bennet": "Edmund Bennet"}
        )
        assert 'always call them "Edmund Bennet"' in text


def _book(*paragraphs):
    return {
        "chapters": [
            {"number": 1, "title": "I", "paragraphs": [{"sentences": [p]} for p in paragraphs]}
        ]
    }


SOURCE = _book(*[f"Elizabeth walked to Meryton with Jane on day {n}." for n in range(12)])
CAST = ["Elizabeth Bennet", "Jane Bennet", "Fitzwilliam Darcy"]


def _findings(output, name_map=None):
    report = QCService(TransformType.ALL_MALE, name_map=name_map, cast=CAST).check_book(
        SOURCE, output
    )
    return [f for f in report.findings if f.kind == "kept_name_lost"]


class TestQCSeesAKeptNameGoMissing:
    def test_a_model_that_renamed_anyway_is_caught(self):
        renamed = _book(*[f"Elliot walked to Meryton with Jane on day {n}." for n in range(12)])
        found = _findings(renamed)
        assert len(found) == 1
        assert "'Elizabeth'" in found[0].detail
        assert found[0].severity == "structural"

    def test_names_that_came_through_raise_nothing(self):
        assert _findings(SOURCE) == []

    def test_a_name_the_map_does_change_is_not_this_checks_business(self):
        renamed = _book(*[f"Edmund walked to Meryton with Jane on day {n}." for n in range(12)])
        assert _findings(renamed, name_map={"Elizabeth": "Edmund"}) == []

    def test_a_job_the_cast_lists_as_a_name_is_not_one(self):
        """ "Housekeeper" in the cast, "the housekeeper" in the book, "steward" after."""
        source = _book(
            *[f"The housekeeper showed them in on day {n}." for n in range(12)],
            "Housekeeper Reynolds smiled.",
        )
        output = _book(
            *[f"The steward showed them in on day {n}." for n in range(12)],
            "Steward Reynolds smiled.",
        )
        report = QCService(TransformType.GENDER_SWAP, cast=["Housekeeper"]).check_book(
            source, output
        )
        assert [f for f in report.findings if f.kind == "kept_name_lost"] == []

    def test_a_name_too_rare_to_count_is_left_alone(self):
        source = _book(*["Elizabeth walked to Meryton."] * 4)
        output = _book(*["Elliot walked to Meryton."] * 4)
        report = QCService(TransformType.ALL_MALE, cast=CAST).check_book(source, output)
        assert [f for f in report.findings if f.kind == "kept_name_lost"] == []
