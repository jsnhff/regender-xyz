# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Jason Huff
"""What only a person can decide is asked before the transform, not found after it.

The run used to settle the names itself, behind the progress bar. A name given
to two characters was known in the first seconds and reported at the end, in
the finished book. And some things a rule cannot settle at all: whether the
"Mrs. Martin" of chapter four is his wife or his mother, or whether a "Mrs.
Rochester" said in teasing is a wedding.

So the names are planned as one step, shown, ruled on where the book leaves
room to be wrong, and then run exactly as shown.
"""

import asyncio
import inspect
import json

import pytest

from src.cli.tui import RegenderTUI
from src.models.character import Character, CharacterAnalysis, Gender
from src.services.character_state import MaritalState, marital_states, with_rulings


def man(name, *titles):
    return Character(name=name, gender=Gender.MALE, pronouns={}, titles=list(titles))


def woman(name, *titles):
    return Character(name=name, gender=Gender.FEMALE, pronouns={}, titles=list(titles))


def book(chapters):
    out = []
    for number, body in sorted(chapters.items()):
        paragraphs = [body] if isinstance(body, str) else list(body)
        out.append({"number": number, "paragraphs": [{"sentences": [p]} for p in paragraphs]})
    return {"chapters": out}


BOOK = book(
    {
        **{
            n: ["Mr. Collins bowed.", "Mr. Collins spoke.", "Mr. Bennet sighed."]
            for n in range(1, 16)
        },
        16: ["Mr. Denny called."],
        28: ["They arrived.", "Mrs. Collins welcomed her."],
        29: ["Mrs. Bennet was querulous.", "Mr. Collins agreed."],
    }
)
CAST = [
    man("Mr. Collins", "Mr."),
    man("Mr. Bennet", "Mr."),
    woman("Mrs. Bennet", "Mrs."),
    man("Mr. Denny", "Mr."),
]


# --------------------------------------------------------------------------- #
# Rulings
# --------------------------------------------------------------------------- #


class TestWhichVerdictsWantAPerson:
    @pytest.fixture
    def states(self):
        return marital_states(BOOK, CAST)

    def test_a_wedding_does(self, states):
        """The "Mrs." may have been said a chapter before the church."""
        assert states["Mr. Collins"].wedding == (28, 1)
        assert states["Mr. Collins"].worth_a_look

    def test_a_marriage_read_off_the_cast_does(self, states):
        """The cast cannot tell a wife from a mother."""
        assert states["Mr. Bennet"].opens == "married"
        assert states["Mr. Bennet"].worth_a_look

    def test_a_man_with_no_mrs_anywhere_does_not(self, states):
        assert states["Mr. Denny"].opens == "unmarried"
        assert not states["Mr. Denny"].worth_a_look

    def test_the_line_of_the_book_is_kept_either_way(self, states):
        """It is what a person reads to agree or disagree."""
        assert "Mrs. Collins" in states["Mr. Collins"].evidence
        assert "Mrs. Bennet" in states["Mr. Bennet"].evidence


class TestAReadersRulingReplacesTheVerdict:
    @pytest.fixture
    def states(self):
        return marital_states(BOOK, CAST)

    def test_married_from_the_start(self, states):
        ruled = with_rulings(states, {"Mr. Collins": {"opens": "married", "wedding": None}})
        assert (ruled["Mr. Collins"].opens, ruled["Mr. Collins"].wedding) == ("married", None)
        assert ruled["Mr. Collins"].reason == "settled by the reader"

    def test_never_marries(self, states):
        ruled = with_rulings(states, {"Mr. Bennet": {"opens": "unmarried", "wedding": None}})
        assert (ruled["Mr. Bennet"].opens, ruled["Mr. Bennet"].wedding) == ("unmarried", None)

    def test_marries_in_another_chapter(self, states):
        ruled = with_rulings(states, {"Mr. Collins": {"opens": "unmarried", "wedding": [22, 0]}})
        assert ruled["Mr. Collins"].wedding == (22, 0)

    def test_already_married_leaves_no_wedding_to_mark(self, states):
        ruled = with_rulings(states, {"Mr. Collins": {"opens": "married", "wedding": [22, 0]}})
        assert ruled["Mr. Collins"].wedding is None

    def test_the_others_are_untouched(self, states):
        ruled = with_rulings(states, {"Mr. Collins": {"opens": "married", "wedding": None}})
        assert ruled["Mr. Bennet"] == states["Mr. Bennet"]
        assert states["Mr. Collins"].opens == "unmarried", "the original was altered"

    def test_a_ruling_about_nobody_is_ignored(self, states):
        assert with_rulings(states, {"Mr. Nobody": {"opens": "married"}}) == states
        assert with_rulings(states, {"Mr. Collins": {"opens": "divorced"}}) == states
        assert with_rulings(states, None) == states


# --------------------------------------------------------------------------- #
# The plan
# --------------------------------------------------------------------------- #


class _Model:
    """Answers naming and transform prompts; counts the naming ones."""

    name = "mock"
    model = "mock-model"
    supports_json = True

    def __init__(self):
        self.naming_calls = 0
        self.transform_calls = 0

    async def complete(self, messages, **_kwargs):
        system = messages[0]["content"] if messages[0]["role"] == "system" else ""
        user = messages[-1]["content"]
        if system.startswith("You rewrite the gender language"):
            self.transform_calls += 1
            return user.split("\n\n", 1)[1]
        if "choosing replacement GIVEN NAMES" in user:
            self.naming_calls += 1
            return json.dumps({"renames": []})
        return "{}"


@pytest.fixture
def backend():
    from src.app import Application
    from src.container import ApplicationContext

    context = ApplicationContext()
    context.initialize()
    model = _Model()
    context.register_instance("llm_provider", model)
    app = Application(context=context)
    app.model = model
    return app


def plan_for(backend, rulings=None, kind="gender_swap"):
    return asyncio.run(
        backend.plan_names(
            transform_type=kind,
            characters=CharacterAnalysis(book_id="t", characters=CAST),
            book=BOOK,
            marital_rulings=rulings,
        )
    )


class TestThePlan:
    def test_it_holds_what_the_run_will_apply(self, backend):
        plan = plan_for(backend)
        assert plan["name_map"]["Mr. Collins"] == "Miss Collins"
        assert plan["name_map"]["Mr. Bennet"] == "Mrs. Bennet"
        assert plan["title_timeline"] == [(28, 1, {"Mr. Collins": "Mrs. Collins"})]
        assert plan["finished_map"] and plan["problems"] == plan["report"]["problems"]

    def test_a_ruling_changes_the_titles_and_nothing_else(self, backend):
        plan = plan_for(backend)
        calls = backend.model.naming_calls
        cast = CharacterAnalysis(book_id="t", characters=CAST)
        ruled = backend.finish_name_plan(
            plan, cast, {"Mr. Collins": {"opens": "unmarried", "wedding": [22, 0]}}
        )
        assert ruled["title_timeline"] == [(22, 0, {"Mr. Collins": "Mrs. Collins"})]
        assert ruled["engine_map"] == plan["engine_map"]
        assert backend.model.naming_calls == calls, "ruling on a title asked the model again"
        states = {s["name"]: s for s in ruled["report"]["marital_states"]}
        assert states["Mr. Collins"]["reason"] == "settled by the reader"

    def test_only_a_swap_carries_titles(self, backend):
        plan = plan_for(backend, kind="all_female")
        assert plan["title_timeline"] is None and plan["marital_states"] == {}


class TestTheRunUsesThePlanItIsHanded:
    def run(self, backend, tmp_path, simple_story_path, **kwargs):
        return asyncio.run(
            backend.process_book(
                file_path=simple_story_path,
                transform_type="gender_swap",
                output_path=str(tmp_path / "out.json"),
                characters=CharacterAnalysis(book_id="t", characters=CAST),
                **kwargs,
            )
        )

    def test_the_names_are_not_chosen_a_second_time(self, backend, tmp_path, simple_story_path):
        plan = plan_for(backend, {"Mr. Collins": {"opens": "married", "wedding": None}})
        chosen = backend.model.naming_calls
        result = self.run(backend, tmp_path, simple_story_path, name_plan=plan)
        assert result["success"] is True
        assert backend.model.naming_calls == chosen

    def test_what_was_ruled_is_what_is_written_down(self, backend, tmp_path, simple_story_path):
        plan = plan_for(backend, {"Mr. Collins": {"opens": "married", "wedding": None}})
        self.run(backend, tmp_path, simple_story_path, name_plan=plan)
        proposed = json.loads((tmp_path / "name_map_proposed.json").read_text())
        assert proposed["Mr. Collins"] == "Mrs. Collins"
        report = json.loads((tmp_path / "name_report.json").read_text())
        states = {s["name"]: s for s in report["marital_states"]}
        assert states["Mr. Collins"]["reason"] == "settled by the reader"

    def test_rulings_reach_a_run_that_has_to_plan_for_itself(
        self, backend, tmp_path, simple_story_path
    ):
        """When the plan was lost, the rulings made on screen went with it."""
        story = tmp_path / "bennet.txt"
        story.write_text(
            "CHAPTER 1: One\n\nMr. Bennet sighed and Mrs. Bennet spoke.\n\n"
            "Mr. Bennet said nothing more.\n"
        )
        self.run(
            backend,
            tmp_path,
            str(story),
            marital_rulings={"Mr. Bennet": {"opens": "unmarried", "wedding": None}},
        )
        proposed = json.loads((tmp_path / "name_map_proposed.json").read_text())
        assert proposed["Mr. Bennet"] == "Miss Bennet"

    def test_with_no_plan_the_run_makes_its_own(self, backend, tmp_path, simple_story_path):
        result = self.run(backend, tmp_path, simple_story_path)
        assert result["success"] is True
        assert (tmp_path / "name_map_proposed.json").exists()

    def test_a_plan_for_another_transform_is_not_used(
        self, backend, tmp_path, simple_story_path, caplog
    ):
        plan = plan_for(backend, kind="all_female")
        with caplog.at_level("WARNING"):
            result = self.run(backend, tmp_path, simple_story_path, name_plan=plan)
        assert result["success"] is True
        assert "planning afresh" in caplog.text, "the swap ran on an all_female plan"


# --------------------------------------------------------------------------- #
# The questions
# --------------------------------------------------------------------------- #


class _Bare(RegenderTUI):
    book_title = "—"
    transform_type = "—"
    status_text = ""


def state(name, opens, wedding=None, mentions=40, before=None, evidence="", wife=False):
    return MaritalState(
        name=name,
        opens=opens,
        wedding=wedding,
        evidence=evidence,
        mentions=mentions,
        before_first_mrs=mentions if before is None else before,
        wife_in_cast=wife,
        reason="why",
    )


COLLINS = state(
    "Mr. Collins", "unmarried", (28, 2), mentions=149, before=104, evidence="Mrs. Collins welcomed"
)
BENNET = state(
    "Mr. Bennet", "married", mentions=89, before=8, evidence="Mrs. Bennet deigned", wife=True
)
DENNY = state("Mr. Denny", "unmarried", mentions=6)
PHILIPS = state("Mr. Philips", "married", mentions=3, before=1, wife=True)


@pytest.fixture
def tui():
    app = _Bare.__new__(_Bare)
    app._reset_run_state()
    app._lines = []
    app.print = lambda text="": app._lines.append(str(text))
    app.set_prompt = lambda _p: None
    app._accept_input = lambda: None
    app._live_heading = lambda text, suffix="": app._lines.append(f"{text} {suffix}")
    app._settle_heading = lambda: None
    app._selected_transform = "gender_swap"
    app._pending_characters = CharacterAnalysis(book_id="t", characters=CAST)
    app.went = []
    for name in ("_start_processing", "_plan_run"):
        setattr(app, name, (lambda n: lambda *a, **k: app.went.append(n))(name))
    app._name_plan = {
        "marital_states": {s.name: s for s in (BENNET, COLLINS, DENNY, PHILIPS)},
        "problems": [],
        "book": {"chapters": [{"number": n} for n in range(1, 62)]},
        "report": {},
    }
    return app


def text(app):
    import re

    return "\n".join(re.sub(r"\[/?[^\]]*\]", "", line) for line in app._lines)


class TestTheNamesHandOverToThePlan:
    def test_accepting_the_names_plans_before_it_runs(self, tui):
        tui._name_suggestions = [{"original": "Elizabeth", "suggested": "Edmund"}]
        tui._handle_name_review_input("a")
        assert tui.went == ["_plan_run"]

    def test_enter_keeps_when_nothing_was_suggested(self, tui):
        """The screen cursors "keep the originals"; Enter accepted an empty list."""
        tui._name_suggestions = []
        tui._handle_name_review_input("")
        assert tui._keep_names is True and tui._name_map is None
        assert tui.went == ["_plan_run"]

    def test_enter_still_accepts_when_there_is_something_to_accept(self, tui):
        tui._name_suggestions = [{"original": "Elizabeth", "suggested": "Edmund"}]
        tui._handle_name_review_input("")
        assert tui._keep_names is False and tui._name_map == {"Elizabeth": "Edmund"}

    def test_keeping_the_names_plans_too(self, tui):
        tui._handle_name_review_input("k")
        assert tui.went == ["_plan_run"] and tui._keep_names is True

    def test_the_run_is_handed_the_plan(self):
        assert '"name_plan": self._name_plan' in inspect.getsource(RegenderTUI._start_processing)
        assert "name_plan=" in inspect.getsource(RegenderTUI._run_processing)


class TestNothingIsAnsweredWhileTheNamesAreChecked:
    @pytest.fixture
    def checking(self, tui):
        tui._plan_run = RegenderTUI._plan_run.__get__(tui)
        tui._check_the_names = lambda: tui.went.append("_check_the_names")
        tui.query_one = lambda _cls: (_ for _ in ()).throw(RuntimeError("no screen"))
        return tui

    def test_the_stage_moves_on_before_the_wait(self, checking):
        """A second Enter used to land on the question just answered."""
        checking._stage = "name_review"
        checking._plan_run()
        assert checking._stage == "planning"
        assert checking.went == ["_check_the_names"]

    def test_the_old_plan_is_dropped_first(self, checking):
        """Or a run started mid-check would use the plan from before a fix."""
        assert checking._name_plan is not None
        checking._plan_run()
        assert checking._name_plan is None

    def test_no_stage_answers_to_planning(self):
        source = inspect.getsource(RegenderTUI.on_input_submitted)
        assert '"planning"' not in source

    def test_a_check_that_fails_is_said_to_have_failed(self, tui, monkeypatch):
        """Silence here looked exactly like having nothing to ask."""

        class _Broken:
            def __init__(self, _config):
                raise RuntimeError("no model is set up")

        monkeypatch.setattr("src.app.Application", _Broken)
        tui.query_one = lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("no screen"))
        tui._selected_book = "book.txt"
        asyncio.run(RegenderTUI._check_the_names.__wrapped__(tui))
        shown = text(tui)
        assert "could not be checked beforehand" in shown and "no model is set up" in shown
        assert tui._name_plan is None
        assert tui.went == ["_start_processing"], "the run did not go on to check them itself"

    def test_the_rulings_go_with_the_run_even_without_a_plan(self):
        assert '"marital_rulings": self._title_rulings' in inspect.getsource(
            RegenderTUI._start_processing
        )
        assert "marital_rulings=" in inspect.getsource(RegenderTUI._run_processing)


class TestWhoIsAskedAbout:
    def test_only_the_verdicts_that_could_be_wrong_and_only_men_who_matter(self, tui):
        tui._start_title_review()
        assert [s.name for s in tui._title_items] == ["Mr. Collins", "Mr. Bennet"]

    def test_the_most_named_man_comes_first(self, tui):
        tui._start_title_review()
        assert tui._title_items[0].mentions > tui._title_items[1].mentions

    def test_the_count_is_said_and_one_is_singular(self, tui):
        tui._start_title_review()
        assert "2 titles to settle" in text(tui)
        tui._lines.clear()
        tui._name_plan["marital_states"].pop("Mr. Bennet")
        tui._start_title_review()
        assert "1 title to settle" in text(tui)

    def test_what_the_book_appears_to_say_is_shown_with_its_evidence(self, tui):
        tui._start_title_review()
        shown = text(tui)
        assert "Miss Collins until chapter 28, then Mrs. Collins" in shown
        assert "Mrs. Collins welcomed" in shown
        assert "1 of 2" in shown

    def test_with_nothing_to_ask_it_goes_on(self, tui):
        tui._name_plan["marital_states"] = {"Mr. Denny": DENNY}
        tui._start_title_review()
        assert tui.went == ["_start_processing"]

    def test_with_no_plan_at_all_the_run_still_starts(self, tui):
        tui._name_plan = None
        tui._start_title_review()
        assert tui.went == ["_start_processing"]


class TestAnswering:
    @pytest.fixture
    def asked(self, tui, monkeypatch):
        finished = []

        class _Backend:
            def __init__(self, _config):
                pass

            def finish_name_plan(self, plan, characters, rulings):
                finished.append(dict(rulings))
                return {**plan, "ruled": dict(rulings)}

            def shutdown(self):
                pass

        monkeypatch.setattr("src.app.Application", _Backend)
        tui.finished = finished
        tui._start_title_review()
        return tui

    def test_enter_keeps_what_the_book_says(self, asked):
        asked._handle_title_review_input("")
        assert asked._title_rulings == {} and asked._title_idx == 1

    def test_two_marries_him_from_the_start(self, asked):
        asked._handle_title_review_input("2")
        assert asked._title_rulings == {"Mr. Collins": {"opens": "married", "wedding": None}}
        assert "Mr. Collins: Mrs. Collins throughout" in text(asked)

    def test_three_never_marries_him(self, asked):
        asked._handle_title_review_input("3")
        assert asked._title_rulings == {"Mr. Collins": {"opens": "unmarried", "wedding": None}}

    def test_four_asks_which_chapter(self, asked):
        asked._handle_title_review_input("4")
        assert asked._title_idx == 0, "moved on before the chapter was given"
        asked._handle_title_review_input("22")
        assert asked._title_rulings == {"Mr. Collins": {"opens": "unmarried", "wedding": [22, 0]}}
        assert "Miss Collins until chapter 22, then Mrs. Collins" in text(asked)

    @pytest.mark.parametrize("answer", ["", "b"])
    def test_the_chapter_prompt_can_be_left(self, asked, answer):
        """The only way out used to be to make a chapter up."""
        asked._handle_title_review_input("4")
        asked._lines.clear()
        asked._handle_title_review_input(answer)
        assert asked._title_rulings == {} and asked._title_idx == 0
        assert asked._title_chapter_mode is False
        assert "Miss Collins until chapter 28" in text(asked), "the question was not shown again"

    @pytest.mark.parametrize("chapter", ["0", "62", "soon"])
    def test_a_chapter_the_book_does_not_have_is_asked_for_again(self, asked, chapter):
        asked._handle_title_review_input("4")
        asked._handle_title_review_input(chapter)
        assert asked._title_rulings == {} and asked._title_idx == 0
        assert "Enter a chapter from 1 to 61" in text(asked)
        asked._handle_title_review_input("22")
        assert asked._title_rulings["Mr. Collins"]["wedding"] == [22, 0]

    def test_back_returns_and_forgets_that_answer(self, asked):
        asked._handle_title_review_input("2")
        asked._handle_title_review_input("b")
        assert asked._title_idx == 0 and asked._title_rulings == {}

    def test_keep_the_rest_ends_the_questions(self, asked):
        asked._handle_title_review_input("s")
        assert asked.went == ["_start_processing"]
        assert asked.finished == [], "nothing was ruled, so nothing was redone"

    def test_anything_else_is_turned_away_in_the_usual_words(self, asked):
        asked._handle_title_review_input("maybe")
        assert asked._title_idx == 0
        assert "Enter 1-4, b, s" in text(asked)

    def test_the_rulings_are_laid_over_the_plan_without_a_model(self, asked):
        asked._handle_title_review_input("2")
        asked._handle_title_review_input("")
        assert asked.finished == [{"Mr. Collins": {"opens": "married", "wedding": None}}]
        assert asked._name_plan["ruled"] == asked.finished[0]
        assert asked.went == ["_start_processing"]


PROBLEM = (
    "'laurie' is the new name of 2 different characters (Charles, Louisa); two people, one name"
)


class TestTheNameMapsProblems:
    @pytest.fixture
    def troubled(self, tui):
        tui._name_plan["marital_states"] = {}
        tui._name_plan["problems"] = [PROBLEM, "a second problem"]
        tui._start_title_review()
        return tui

    def test_they_are_shown_before_anything_is_spent(self, troubled):
        assert troubled.went == [] and troubled._stage == "plan_problems"
        shown = text(troubled)
        assert "The name map has 2 problems" in shown
        assert "'laurie' is the new name of 2 different characters" in shown

    def test_one_problem_is_singular(self, tui):
        tui._name_plan["marital_states"] = {}
        tui._name_plan["problems"] = [PROBLEM]
        tui._start_title_review()
        assert "The name map has 1 problem " in text(tui) + " "
        assert "1 problems" not in text(tui)

    def test_no_line_runs_past_eighty_columns(self, troubled):
        for line in text(troubled).splitlines():
            assert len(line) <= 78, f"too wide: {line!r}"

    def test_two_starts_anyway(self, troubled):
        troubled._handle_plan_problems_input("2")
        assert troubled.went == ["_start_processing"]

    def test_enter_asks_for_the_fix_and_a_fix_is_checked_again(self, troubled):
        troubled._handle_plan_problems_input("")
        assert troubled.went == []
        troubled._handle_plan_problems_input("Louisa = Lesley")
        assert troubled._name_map == {"Louisa": "Lesley"}
        assert troubled.went == ["_plan_run"]

    def test_a_fix_is_added_to_the_names_already_chosen(self, troubled):
        troubled._name_map = {"Elizabeth": "Edmund"}
        troubled._handle_plan_problems_input("1")
        troubled._handle_plan_problems_input("Louisa=Lesley")
        assert troubled._name_map == {"Elizabeth": "Edmund", "Louisa": "Lesley"}

    def test_something_that_is_not_a_mapping_changes_nothing(self, troubled):
        troubled._handle_plan_problems_input("1")
        troubled._handle_plan_problems_input("no idea")
        assert troubled._name_map is None and troubled.went == []
        assert troubled._stage == "plan_problems"

    def test_the_titles_are_not_asked_about_twice(self, tui):
        """A fixed name plans again; the titles were settled the first time."""
        tui._start_title_review()
        tui._handle_title_review_input("s")
        tui.went.clear()
        tui._lines.clear()
        tui._start_title_review()
        assert tui._title_items == [] and "to settle" not in text(tui)

    def test_a_name_the_engine_turned_down_is_said_to_have_been(self, tui):
        tui._name_plan["report"] = {"refused": {"Louisa": "'Lewis' is a masculine name"}}
        tui._say_what_was_refused()
        shown = text(tui)
        assert "Louisa was left as it is" in shown and "masculine" in shown


class TestOnALiveScreen:
    pytestmark = pytest.mark.asyncio

    async def test_the_question_can_be_typed_into(self):
        """A question you cannot answer is not a question."""
        from src.cli.tui import InputBar

        app = RegenderTUI(process_callback=None)
        async with app.run_test() as pilot:
            app._name_plan = {
                "marital_states": {"Mr. Collins": COLLINS},
                "problems": [],
                "book": {"chapters": [{"number": 1}]},
                "report": {},
            }
            started = []
            app._start_processing = lambda: started.append(True)
            bar = app.query_one(InputBar)
            bar.disable()
            await pilot.pause()

            app._start_title_review()
            await pilot.pause()
            assert app._stage == "title_review"
            assert not bar.disabled, "the title question left the input disabled"

            app._handle_title_review_input("")
            await pilot.pause()
            assert started == [True]
