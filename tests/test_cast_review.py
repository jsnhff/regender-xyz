"""The duplicates nothing could settle, put to the reader.

The deterministic merge folds only what it is certain of, on purpose: a wrong
merge makes two people one and says nothing about it, while a missed one shows up
as a character with two names. What it declines still has to go somewhere, and it
went nowhere. Five real pairs survived every check in the Pride and Prejudice
cast:

    Mrs. Collins / Charlotte Collins    a form of address and a full name
    Miss King / Mary King               the same
    Mrs. Nichols / Nicholls             one name, spelled two ways
    Kitty Bennet / Catherine Bennet     a nickname and a formal name
    Jane Bennet / Jane Bingley          a married surname

Nothing asked about any of them, and only one was ever noticed -- Kitty and
Catherine -- afterwards, and then only because the two names it produced happened
to collide with each other.

They are asked now, before naming, because the answer decides how many names
there are to choose. Ten questions for this book: the five above and five more
that deserve a look and get a quick no.
"""

import json
import pathlib

import pytest

from src.cli.tui import RegenderTUI, _surviving_name
from src.models.character import Character, CharacterAnalysis, Gender
from src.services.character_service import CharacterService

REAL_CAST = pathlib.Path(
    "/Users/jasonhuff/regender-xyz/books/output/pride-and-prejudice/"
    "all_male_2026-09-10_21-44/characters.json"
)


def person(name, gender=Gender.FEMALE, aliases=()):
    return Character(name=name, gender=gender, pronouns={}, aliases=list(aliases))


class TestWhichNameSurvives:
    @pytest.mark.parametrize(
        "a,b,keeps",
        [
            # A name is more use than a form of address.
            ("Miss King", "Mary King", "Mary King"),
            ("Mary King", "Miss King", "Mary King"),
            ("Mrs. Collins", "Charlotte Collins", "Charlotte Collins"),
            # Neither is a full name: the bare one wins. Austen spells the
            # Netherfield housekeeper "Nicholls".
            ("Mrs. Nichols", "Nicholls", "Nicholls"),
            ("Nicholls", "Mrs. Nichols", "Nicholls"),
            # Two full names: the first stands, so the answer does not depend on
            # the order they were found in.
            ("Catherine Bennet", "Kitty Bennet", "Catherine Bennet"),
            ("Jane Bennet", "Jane Bingley", "Jane Bennet"),
        ],
    )
    def test_the_better_name_is_kept(self, a, b, keeps):
        assert _surviving_name(a, b) == keeps


class TestWhatIsAsked:
    def test_the_five_that_survived_every_check(self):
        if not REAL_CAST.exists():
            pytest.skip("the real cast is not on this machine")
        cast = CharacterAnalysis.from_dict(json.loads(REAL_CAST.read_text()))
        merged, _ = CharacterService._merge_same_person(list(cast.characters))
        pairs = {
            tuple(sorted((c["a"], c["b"]))) for c in CharacterService.possible_duplicates(merged)
        }
        for a, b in (
            ("Mrs. Collins", "Charlotte Collins"),
            ("Miss King", "Mary King"),
            ("Mrs. Nichols", "Nicholls"),
            ("Kitty Bennet", "Catherine Bennet"),
            ("Jane Bennet", "Jane Bingley"),
        ):
            assert tuple(sorted((a, b))) in pairs, f"{a} / {b} is not asked about"

    def test_the_list_stays_short_enough_to_read(self):
        """A first version asked forty questions of which thirty-five were
        nonsense -- "The Waiter" against "The Gardener", three separate men named
        William against each other, every Bennet sister against her mother."""
        if not REAL_CAST.exists():
            pytest.skip("the real cast is not on this machine")
        cast = CharacterAnalysis.from_dict(json.loads(REAL_CAST.read_text()))
        merged, _ = CharacterService._merge_same_person(list(cast.characters))
        candidates = CharacterService.possible_duplicates(merged)
        assert len(candidates) <= 14, [f"{c['a']} / {c['b']}" for c in candidates]

    def test_collectives_and_jobs_are_not_asked_about(self):
        cast = [
            person("The Waiter", Gender.MALE),
            person("The Gardener", Gender.MALE),
            person("The Butler", Gender.MALE),
            person("The Lucases"),
        ]
        assert CharacterService.possible_duplicates(cast) == []

    def test_three_men_with_one_given_name_are_not_paired(self):
        """Sir William Lucas, William Collins and William Goulding."""
        cast = [
            person("Sir William Lucas", Gender.MALE),
            person("William Collins", Gender.MALE),
            person("William Goulding", Gender.MALE),
        ]
        assert CharacterService.possible_duplicates(cast) == []

    def test_a_mother_among_several_daughters_is_not_paired(self):
        """ "Mrs. Bennet" could be any of four named Bennet women, which is
        exactly why she is a fifth person and not one of them."""
        cast = [
            person("Mrs. Bennet"),
            person("Jane Bennet"),
            person("Mary Bennet"),
            person("Catherine Bennet"),
            person("Lydia Bennet"),
        ]
        pairs = {
            tuple(sorted((c["a"], c["b"]))) for c in CharacterService.possible_duplicates(cast)
        }
        assert not [p for p in pairs if "Mrs. Bennet" in p]


class TestTheStepper:
    @pytest.fixture
    def app(self):
        class Bare(RegenderTUI):
            book_title = "—"
            transform_type = "—"
            status_text = ""

        app = Bare.__new__(Bare)
        app._lines = []
        app.print = app._lines.append
        app.set_prompt = lambda _p: None
        app._accept_input = lambda: None
        app._stage = ""
        app._output_path = None
        app._json_output_path = None
        app.reached_names = False
        app._run_name_review = lambda: setattr(app, "reached_names", True)
        app._pending_characters = CharacterAnalysis(
            book_id="t",
            characters=[
                person("Charlotte Collins", aliases=["Charlotte"]),
                person("Mrs. Collins"),
            ],
        )
        return app

    def test_a_cast_with_nothing_ambiguous_asks_nothing(self, app):
        app._pending_characters = CharacterAnalysis(
            book_id="t", characters=[person("Elizabeth Bennet")]
        )
        app._start_cast_review()
        assert app.reached_names, "it must not stop to ask a question it does not have"

    def test_yes_merges_and_keeps_the_better_name(self, app):
        app._start_cast_review()
        assert app._cast_candidates, "the pair should be offered"
        app._handle_cast_review_input("y")
        names = {c.name for c in app._pending_characters.characters}
        assert names == {"Charlotte Collins"}
        assert "Mrs. Collins" in app._pending_characters.characters[0].aliases
        assert app.reached_names

    def test_enter_keeps_them_separate(self, app):
        app._start_cast_review()
        app._handle_cast_review_input("")
        names = {c.name for c in app._pending_characters.characters}
        assert names == {"Charlotte Collins", "Mrs. Collins"}
        assert app.reached_names

    def test_s_leaves_the_rest_alone(self, app):
        app._start_cast_review()
        app._handle_cast_review_input("s")
        assert len(app._pending_characters.characters) == 2
        assert app.reached_names

    def test_back_returns_to_the_previous_question(self, app):
        app._pending_characters.characters.append(person("Miss King"))
        app._pending_characters.characters.append(person("Mary King"))
        app._start_cast_review()
        assert len(app._cast_candidates) >= 2
        app._handle_cast_review_input("y")
        assert app._cast_idx == 1
        app._handle_cast_review_input("b")
        assert app._cast_idx == 0
        assert app._cast_merges == [], "going back should undo the answer given"

    def test_the_decisions_are_recorded(self, app, tmp_path):
        app._output_path = str(tmp_path / "out.json")
        app._start_cast_review()
        app._handle_cast_review_input("y")
        written = json.loads((tmp_path / "cast_decisions.json").read_text())
        assert written[0]["same_person"] is True
        assert written[0]["reason"]


class TestTheAnswerReachesTheNames:
    def test_the_review_runs_before_naming(self):
        """The cast decides how many names there are to choose, so it has to be
        settled first. Every path out of the analysis goes here."""
        source = pathlib.Path(RegenderTUI.__module__.replace(".", "/") + ".py")
        if not source.exists():
            source = pathlib.Path("src/cli/tui.py")
        text = source.read_text()
        # The analysis hands to the cast review, and only the cast review hands
        # on to the names.
        assert text.count("self._start_cast_review()") >= 4
        assert text.count("self._run_name_review()") == 2
