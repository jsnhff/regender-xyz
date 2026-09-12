"""A run must be self-contained.

Two versions of one bug were shipped for weeks.

On disk: the character analysis was loaded out of whichever *previous* run
folder for the book sorted last. The interface analysed a fresh cast, told the
reader how many characters it found, took their renames -- and then the
transform ran against a ninety-entry cast from three days earlier. Five run
folders held byte-identical characters.json files while the logs showed the
analysis finding 88, 86, 85, 77, 80 and 82 characters.

In memory: "Try another book" reset sixteen fields by hand and let twenty-one
others through, including the cast, the renames, the title and the review
queue. The second book inherited the first book's characters.

Both are the same mistake -- run state outliving its run -- and both were
possible because the list of what belongs to a run lived in two places, or in
none. These tests put it in one place and keep it there.
"""

import ast
import inspect
import pathlib

import pytest

from src.cli.tui import RegenderTUI


def _self_attrs(fn):
    """Every `self._x = ...` in a function body."""
    found = set()
    for node in ast.walk(fn):
        targets = node.targets if isinstance(node, ast.Assign) else []
        if isinstance(node, ast.AnnAssign):
            targets = [node.target]
        for target in targets:
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
                and target.attr.startswith("_")
            ):
                found.add(target.attr)
    return found


@pytest.fixture(scope="module")
def tui_methods():
    source = pathlib.Path(inspect.getfile(RegenderTUI)).read_text()
    tree = ast.parse(source)
    cls = next(n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == "RegenderTUI")
    return {n.name: n for n in cls.body if isinstance(n, ast.FunctionDef)}


class TestEveryFieldIsClassified:
    """A new field is either run state or session state, and says which."""

    def test_no_field_escapes_both(self, tui_methods):
        run_state = _self_attrs(tui_methods["_reset_run_state"])

        everything = set()
        for name, fn in tui_methods.items():
            if name == "_reset_run_state":
                continue
            everything |= _self_attrs(fn)

        unclassified = sorted(everything - run_state - RegenderTUI.SESSION_STATE)
        assert not unclassified, (
            "These fields are neither reset between runs nor declared as session "
            "state, so they will leak from one book into the next. Add each to "
            "_reset_run_state, or to SESSION_STATE if it genuinely outlives a "
            f"run: {unclassified}"
        )

    def test_session_state_is_not_also_reset(self, tui_methods):
        """A field cannot be both, or the preference dies at every restart."""
        run_state = _self_attrs(tui_methods["_reset_run_state"])
        overlap = sorted(run_state & RegenderTUI.SESSION_STATE)
        assert not overlap, f"declared session state but reset per run: {overlap}"


class TestTheCastDoesNotSurviveARestart:
    """The field that actually caused it, named on its own."""

    @pytest.fixture
    def app(self):
        app = RegenderTUI.__new__(RegenderTUI)
        app._process_callback = None
        app._session_usage = {"tokens_in": 0, "tokens_out": 0, "calls": 0}
        app._friendly_mode = False
        app._setup_provider = ""
        app._reset_run_state()
        return app

    def test_a_reviewed_cast_is_cleared(self, app):
        app._pending_characters = ["Elizabeth", "Darcy"]
        app._name_map = {"Elizabeth": "Edmund"}
        app._name_steer = "less masculine"
        app._custom_title = "Pride and Persuasion"
        app._review_items = [{"term": "uncle"}]
        app._review_idx = 3

        app._reset_run_state()

        assert app._pending_characters is None
        assert app._name_map is None
        assert app._name_steer == ""
        assert app._custom_title == ""
        assert app._review_items == []
        assert app._review_idx == 0

    def test_the_session_total_is_kept(self, app):
        """Cost is the one number that is about the session, not the book."""
        app._session_usage["calls"] = 7
        app._friendly_mode = True
        app._reset_run_state()
        assert app._session_usage["calls"] == 7
        assert app._friendly_mode is True


class TestTheTransformGetsTheCastThatWasReviewed:
    def test_process_book_accepts_a_cast(self):
        """Without this parameter the interface had no way to say which cast."""
        from src.app import Application

        params = inspect.signature(Application.process_book).parameters
        assert "characters" in params, (
            "process_book must accept the cast its caller already analysed"
        )
        assert params["characters"].default is None

    def test_the_tui_passes_its_own_cast(self):
        source = pathlib.Path(inspect.getfile(RegenderTUI)).read_text()
        assert "characters=self._pending_characters" in source, (
            "the interface analysed a cast, showed it to the reader, and must "
            "hand that same cast to the transform"
        )


def _cast_file(name):
    """The smallest characters.json the loader accepts."""
    return {
        "book_id": "pride-and-prejudice",
        "characters": [
            {
                "name": name,
                "gender": "female",
                "pronouns": {"subject": "she", "object": "her", "possessive": "her"},
            }
        ],
    }


class TestTheAnalysisNeverBorrowsFromAnotherRun:
    def test_it_only_looks_in_this_runs_folder(self, tmp_path):
        """The old code globbed every run folder for the book and took the
        newest. A sibling run's cast is not this run's cast."""
        import asyncio
        import json
        import logging

        from src.app import Application
        from src.models.character import CharacterAnalysis

        sibling = tmp_path / "nonbinary_2026-09-11"
        sibling.mkdir()
        (sibling / "characters.json").write_text(json.dumps(_cast_file("Stale")))
        mine = tmp_path / "all_female_2026-09-12"
        mine.mkdir()

        app = Application.__new__(Application)
        app.logger = logging.getLogger("test")

        analysed = []

        class _Service:
            async def process(self, _book):
                analysed.append(True)
                return CharacterAnalysis(book_id="fresh", characters=[])

        app.get_service = lambda _name: _Service()

        asyncio.run(app._get_or_analyze_characters(object(), mine))
        assert analysed, "it must analyse rather than borrow the sibling's cast"

    def test_it_does_reuse_the_same_runs_own_file(self, tmp_path):
        """Rebuilding the same output path is the one safe reuse."""
        import asyncio
        import json
        import logging

        from src.app import Application

        mine = tmp_path / "all_female_2026-09-12"
        mine.mkdir()
        (mine / "characters.json").write_text(json.dumps(_cast_file("Kept")))

        app = Application.__new__(Application)
        app.logger = logging.getLogger("test")

        def _no_service(_name):
            raise AssertionError("should not re-analyse when this run has its own cast")

        app.get_service = _no_service

        result = asyncio.run(app._get_or_analyze_characters(object(), mine))
        assert [c.name for c in result.characters] == ["Kept"]
