"""The order the questions arrive in.

It used to run character analysis — thirty seconds and real money — before
asking what you were making, and then put the book title between the transform
and the naming. Two decisions about the output, two about the characters, and
they were interleaved.

The title is computed from the transform, so it cannot move earlier. What was
out of place was the analysis.
"""

import pytest

from src.cli.tui import RegenderTUI


class _Bare(RegenderTUI):
    """The three reactives stand in as plain attributes off-screen."""

    book_title = "—"
    transform_type = "—"
    status_text = ""


@pytest.fixture
def tui():
    app = _Bare.__new__(_Bare)
    app._lines = []
    app.print = app._lines.append
    app.set_prompt = lambda _p: None
    app._accept_input = lambda: None
    app._stage = ""
    app._selected_transform = "all_female"
    app._custom_title = None
    app.book_title = "Pride and Prejudice"
    app._suggested_title = ""
    app._no_qc = False
    app._analysis_running = False
    app._pending_characters = None
    app._output_path = "out.json"
    app._calculate_output_path = lambda: None
    app._book_stats = {"tokens": 1000}

    app.went = []
    for name in (
        "_show_transform_menu",
        "_show_model_menu",
        "_show_character_analysis_prompt",
        "_run_name_review",
        "_show_options_menu",
        "_start_processing",
        "_show_editorial_notice",
    ):
        setattr(app, name, (lambda n: lambda *a, **k: app.went.append(n))(name))
    return app


class TestTheTransformComesBeforeTheAnalysis:
    def test_choosing_a_model_offers_the_transform(self, tui):
        """Not the analysis: nobody should pay for that before deciding."""
        tui._model_choices = []
        tui._handle_model_input("1")
        assert tui.went == ["_show_transform_menu"]

    def test_back_from_the_transform_returns_to_the_model(self, tui):
        tui._handle_transform_input("back")
        assert tui.went == ["_show_model_menu"]


class TestTheTitleComesAfterTheTransform:
    def test_a_plain_transform_goes_to_the_options(self, tui):
        tui._selected_transform = "all_female"
        tui._after_transform_chosen()
        assert tui.went == ["_show_options_menu"]

    def test_nonbinary_shows_its_notice_first(self, tui):
        tui._selected_transform = "nonbinary"
        tui._after_transform_chosen()
        assert tui.went == ["_show_editorial_notice"]


class TestTheTitleHandsOverToTheCharacters:
    def test_after_the_title_comes_the_analysis(self, tui):
        tui._stage = "retitle"
        tui._handle_retitle_input("")
        assert tui.went == ["_show_character_analysis_prompt"]

    def test_a_typed_title_is_kept(self, tui):
        tui._handle_retitle_input("Pride and Persuasion")
        assert tui._custom_title == "Pride and Persuasion"
        assert tui.went == ["_show_character_analysis_prompt"]


class TestTheAnalysisHandsOverToTheNames:
    def test_skipping_the_analysis_goes_to_the_names(self, tui):
        tui._handle_analyze_prompt_input("n")
        assert tui.went == ["_run_name_review"]

    def test_the_names_are_the_last_question_before_the_run(self, tui):
        """Nothing about the output comes after the characters."""
        tui._pending_characters = None
        tui._run_name_review = RegenderTUI._run_name_review.__wrapped__.__get__(tui)
        # With no characters the review hands straight to processing.
        import asyncio

        asyncio.run(tui._run_name_review())
        assert tui.went == ["_start_processing"]


def test_the_whole_order(tui):
    """Walk it end to end: model, transform, title, analysis, names."""
    tui._model_choices = []
    tui._handle_model_input("1")
    tui._selected_transform = "all_female"
    tui._after_transform_chosen()
    tui._handle_retitle_input("")
    tui._handle_analyze_prompt_input("n")
    assert tui.went == [
        "_show_transform_menu",
        "_show_options_menu",
        "_show_character_analysis_prompt",
        "_run_name_review",
    ]
