# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Jason Huff
"""The name map is finished, and judged, before the transform starts.

The audit that was meant to stop a bad map ran on the engine's renames alone.
The map a run applies is larger: a swap adds titles derived from marital
state, and the transform adds every alias. Most faults are born in those two
steps, so the early audit called maps clean that went on to lose given names,
and the audit that saw them ran after the book had been paid for.

A full run of Pride and Prejudice on 26 November 2026 showed what was in such
a map. The cast, written by a model, described people as readily as it named
them, and the title step took the last word of each description for a family
name: "Mr. Darcy (the late)" became "Miss late)", "Mr. Darcy's father" became
"Mrs. father", and the model was told to call them that.

That step is turned away from descriptions and from nothing else. What it
writes for a name is pinned below against the rule it has always used.
"""

import asyncio
import inspect

from src.models.character import Character, CharacterAnalysis, Gender
from src.services.character_state import initial_marital_state, marital_title_maps
from src.services.name_engine import audit_name_map
from src.services.transform_service import TransformService


def man(name, **kwargs):
    return Character(name=name, gender=Gender.MALE, pronouns={}, titles=["Mr."], **kwargs)


def woman(name, title="Miss", **kwargs):
    return Character(name=name, gender=Gender.FEMALE, pronouns={}, titles=[title], **kwargs)


def title_entries(*cast):
    base, _ = marital_title_maps(cast, [], initial_marital_state(cast))
    return base


class TestTitleEntriesAreNotWrittenFromDescriptions:
    def test_descriptions_are_not_names(self):
        """These produced "Miss late)", "Mrs. father", "Miss sister", "Mrs. senior"."""
        cast = [
            man("Mr. Darcy (the late)"),
            man("Mr. Darcy (the elder)"),
            man("Mr. Darcy's father"),
            man("Mr. Bingley's other sister"),
            man("Mr. Jones's shopboy"),
            man("Mr. Wickham senior"),
            man("Mr. Darcy Senior"),
            man("Mr. Bennet's great-uncle the judge"),
        ]
        assert title_entries(*cast) == {}

    def test_a_plain_titled_name_still_gets_one(self):
        assert title_entries(man("Mr. Denny")) == {"Mr. Denny": "Miss Denny"}

    def test_a_married_man_still_becomes_mrs(self):
        entries = title_entries(man("Mr. Bennet"), woman("Mrs. Bennet", title="Mrs."))
        assert entries == {"Mr. Bennet": "Mrs. Bennet"}

    def test_a_name_with_a_given_name_is_entered_as_the_text_names_him(self):
        """The book says "Mr. Bingley", whatever the cast calls him."""
        assert title_entries(man("Mr. Charles Bingley")) == {"Mr. Bingley": "Miss Bingley"}

    def test_surnames_of_other_shapes_are_still_surnames(self):
        for name, expected in (
            ("Mr. Fitz-Hugh", "Miss Fitz-Hugh"),
            ("Mr. O'Brien", "Miss O'Brien"),
            ("Mr. d'Arcy", "Miss d'Arcy"),
            ("Mr. McDonald", "Miss McDonald"),
        ):
            assert title_entries(man(name)) == {name: expected}


def _as_it_always_was(cast, changes, initial):
    """The title step before this change, kept here to hold the new one to it."""
    import re

    from src.services.character_state import _MARITAL_TITLE, _is_single_titled, _surname

    base, at = {}, {}
    for char in cast:
        name = char.name or ""
        surname = _surname(name)
        if not surname or not _is_single_titled(char):
            continue
        tokens = [t for t in re.split(r"\s+", name.strip()) if t]
        if not tokens or tokens[0].rstrip(".") != "Mr":
            continue
        base[name] = f"{_MARITAL_TITLE[initial.get(name, 'unmarried')]} {surname}"
        for change in changes:
            if change.character != name or change.kind != "marital":
                continue
            title = _MARITAL_TITLE.get(change.becomes)
            if title and f"{title} {surname}" != base[name]:
                at.setdefault((change.chapter, change.paragraph), {})[name] = f"{title} {surname}"
    return base, [(c, p, entries) for (c, p), entries in sorted(at.items())]


class TestNothingElseAboutTheTitleStepChanged:
    """Against a real cast: every entry for a name is what it was, to the letter."""

    DESCRIPTIONS = {
        "Mr. Bennet's great-uncle the judge",
        "Mr. Darcy Senior",
        "Mr. Darcy's father",
        "Mr. Collins's father",
        "Mr. Wickham Senior",
    }

    def cast(self):
        import json
        import pathlib

        path = pathlib.Path(__file__).parent / "fixtures" / "pride-and-prejudice-cast.json"
        return CharacterAnalysis.from_dict(json.loads(path.read_text())).characters

    def test_entries_for_names_are_unchanged(self):
        from src.services.character_state import StateChange

        cast = self.cast()
        initial = initial_marital_state(cast)
        # A wedding for everyone, so the timeline is exercised for every name.
        changes = [
            StateChange(
                character=c.name, kind="marital", becomes="married", chapter=49, paragraph=51
            )
            for c in cast
        ]
        old_base, old_timeline = _as_it_always_was(cast, changes, initial)
        new_base, new_timeline = marital_title_maps(cast, changes, initial)

        assert set(old_base) - set(new_base) <= self.DESCRIPTIONS
        assert new_base == {k: v for k, v in old_base.items() if k not in self.DESCRIPTIONS}
        expected_timeline = [
            (c, p, {k: v for k, v in entries.items() if k not in self.DESCRIPTIONS})
            for c, p, entries in old_timeline
        ]
        assert new_timeline == [entry for entry in expected_timeline if entry[2]]
        assert len(new_base) >= 10, "the comparison ran against almost nothing"
        assert new_timeline, "no wedding reached the timeline, so it was not compared"


def cast_of(*characters):
    return CharacterAnalysis(book_id="t", characters=list(characters))


class TestTheAuditKnowsANamesake:
    CAST = cast_of(
        woman("Catherine Bennet", aliases=["Kitty"]),
        woman("Lady Catherine de Bourgh", title="Lady", aliases=["Lady Catherine"]),
        woman("Caroline Bingley"),
    )

    def test_two_people_who_shared_a_name_may_go_on_sharing_one(self):
        """The engine renames a given name once for everyone who has it."""
        name_map = {"Catherine": "Christopher", "Lady Catherine": "Lord Christopher"}
        assert [p for p in audit_name_map(name_map, self.CAST) if "one name" in p] == []

    def test_two_different_names_onto_one_is_still_a_merge(self):
        name_map = {"Caroline": "Cornelius", "Catherine": "Cornelius"}
        merged = [p for p in audit_name_map(name_map, self.CAST) if "one name" in p]
        assert len(merged) == 1 and "'cornelius'" in merged[0]


class TestTheFinishedMapCanBeAskedFor:
    CAST = cast_of(woman("Elizabeth Bennet", aliases=["Lizzy", "Eliza"]))

    def service(self):
        return TransformService.__new__(TransformService)

    def test_it_is_the_map_the_transform_builds(self):
        service = self.service()
        name_map = {"Elizabeth Bennet": "Edmund Bennet"}
        finished = service.finished_name_map(name_map, self.CAST)
        assert finished == service._expand_name_map_with_aliases(name_map, self.CAST)
        assert finished["Lizzy"] == "Edmund"

    def test_asking_does_not_change_what_was_given(self):
        name_map = {"Elizabeth Bennet": "Edmund Bennet"}
        self.service().finished_name_map(name_map, self.CAST)
        assert name_map == {"Elizabeth Bennet": "Edmund Bennet"}

    def test_no_map_is_an_empty_map(self):
        assert self.service().finished_name_map(None, self.CAST) == {}

    def test_the_transform_uses_the_same_method(self):
        assert "self.finished_name_map(" in inspect.getsource(TransformService.transform_book)


class TestTheRunJudgesItBeforeSpending:
    def test_the_audit_sits_ahead_of_the_transform(self):
        from src.app import Application

        # The finished map is built and audited by the planning step, and the
        # run asks for the plan before it transforms anything.
        assert "finished_name_map(" in inspect.getsource(Application.finish_name_plan)
        source = inspect.getsource(Application.process_book)
        judged = source.index("self.plan_names(")
        spent = source.index("await transformer.transform_book(")
        assert judged < spent

    def test_asked_to_stop_it_stops_with_the_problems(
        self, app_with_mock, simple_story_path, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(
            "src.services.name_engine.audit_name_map",
            lambda _map, _cast=None: ["'laurie' is the new name of 2 different characters"],
        )
        out = tmp_path / "out.json"
        result = asyncio.run(
            app_with_mock.process_book(
                file_path=simple_story_path,
                transform_type="gender_swap",
                output_path=str(out),
                stop_on_name_problems=True,
            )
        )
        assert result["success"] is False
        assert result["stopped_before_transform"] is True
        assert result["name_map_problems"] == ["'laurie' is the new name of 2 different characters"]
        assert not out.exists(), "a book was written by a run that said it had stopped"
        assert (tmp_path / "name_map_problems.json").exists()
        assert (tmp_path / "name_map_proposed.json").exists()

    def test_not_asked_it_carries_on_as_before(
        self, app_with_mock, simple_story_path, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(
            "src.services.name_engine.audit_name_map",
            lambda _map, _cast=None: ["a problem"],
        )
        out = tmp_path / "out.json"
        result = asyncio.run(
            app_with_mock.process_book(
                file_path=simple_story_path, transform_type="gender_swap", output_path=str(out)
            )
        )
        assert result["success"] is True
        assert out.exists()

    def test_the_problems_file_keeps_what_was_found_before_the_run(
        self, app_with_mock, simple_story_path, tmp_path, monkeypatch
    ):
        """The audit after the run wrote its own list over the one from before."""
        calls = []

        def audit(_map, _cast=None):
            calls.append(1)
            return ["found before the run"] if len(calls) <= 2 else ["found after it"]

        monkeypatch.setattr("src.services.name_engine.audit_name_map", audit)
        asyncio.run(
            app_with_mock.process_book(
                file_path=simple_story_path,
                transform_type="gender_swap",
                output_path=str(tmp_path / "out.json"),
            )
        )
        import json

        listed = json.loads((tmp_path / "name_map_problems.json").read_text())
        assert "found before the run" in listed and "found after it" in listed

    def test_the_command_line_has_the_flag(self):
        import regender_cli

        assert "--stop-on-name-problems" in inspect.getsource(regender_cli)
