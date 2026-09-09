"""What a finished run tells you.

"Complete" and a path is the least a run can say, and the path was long enough
to wrap mid-word beside its label. What a reader needs before opening the book
is what it cost, whether every chapter made it, what QC found, and how much is
waiting on them.
"""

import re

import pytest

from src.cli.tui import HeaderBar, RegenderTUI


def plain(lines):
    return [re.sub(r"\[/?[^\]]*\]", "", line) for line in lines]


class _Provider:
    def __init__(self, tokens_in=100_000, tokens_out=50_000, calls=12):
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.calls = calls


class _App:
    def __init__(self, provider):
        self._provider = provider

    def get_service(self, _name):
        return type("svc", (), {"provider": self._provider})()


@pytest.fixture
def tui():
    app = RegenderTUI.__new__(RegenderTUI)
    app._ran_application = _App(_Provider())
    app._book_stats = {"chapters": 5}
    app._json_output_path = "books/output/book/gender_swap_2026-09-08_21-58/gender_swap.json"
    app._lines = []
    app.print = app._lines.append
    app.query_one = lambda _cls: type("h", (), {"set_actual_cost": staticmethod(lambda _s: None)})()
    return app


RESULT = {
    "changes": 312,
    "untransformed_chapters": [],
    "quality_control": {"structural": 0, "auto_fixable": 4, "needs_review": 2},
    "substitutions_to_review": 11,
}


class TestTheReport:
    def test_it_says_what_the_run_cost(self, tui):
        tui._show_run_report(RESULT, 62.0)
        assert any("Cost" in line and "$" in line for line in plain(tui._lines))

    def test_the_cost_is_from_real_tokens_not_an_estimate(self, tui):
        tui._show_run_report(RESULT, 62.0)
        text = " ".join(plain(tui._lines))
        assert "100,000 in" in text and "50,000 out" in text and "12 calls" in text

    def test_it_reports_qc(self, tui):
        tui._show_run_report(RESULT, 62.0)
        assert any("0 structural" in line for line in plain(tui._lines))

    def test_it_reports_what_is_waiting_on_a_person(self, tui):
        tui._show_run_report(RESULT, 62.0)
        assert any("11 substitution pairs" in line for line in plain(tui._lines))

    def test_the_path_sits_on_its_own_line(self, tui):
        """Beside a label it wrapped mid-word; the run folder is long."""
        tui._show_run_report(RESULT, 62.0)
        lines = plain(tui._lines)
        assert any(line.strip() == "Saved to" for line in lines)
        assert any(line.strip() == "gender_swap.json" for line in lines)

    def test_every_line_fits_eighty_columns(self, tui):
        tui._show_run_report(RESULT, 62.0)
        for line in plain(tui._lines):
            assert len(line) <= 78, f"too wide: {line!r}"


class TestWhenSomethingWentWrong:
    def test_untransformed_chapters_are_named(self, tui):
        """A chapter that failed kept its source, so the book is silently partial."""
        result = {**RESULT, "untransformed_chapters": [3, 7]}
        tui._show_run_report(result, 62.0)
        assert any("3, 7" in line for line in plain(tui._lines))

    def test_a_partial_run_is_marked_not_just_listed(self, tui):
        """It read exactly like the rows above it, so it was easy to skim past."""
        result = {**RESULT, "untransformed_chapters": [3, 7]}
        tui._show_run_report(result, 62.0)
        line = next(line for line in tui._lines if "Untransformed" in line)
        assert "#ffffff" not in line, "a partial book must not look like a clean one"

    def test_a_structural_finding_is_shown(self, tui):
        result = {
            **RESULT,
            "quality_control": {"structural": 2, "auto_fixable": 0, "needs_review": 0},
        }
        tui._show_run_report(result, 62.0)
        assert any("2 structural" in line for line in plain(tui._lines))
        line = next(line for line in tui._lines if "structural" in line)
        assert "#ffffff" not in line


class TestCostIsHonest:
    def test_no_cost_line_when_nothing_was_recorded(self, tui):
        tui._ran_application = _App(_Provider(0, 0, 0))
        tui._show_run_report(RESULT, 62.0)
        assert not any("Cost" in line for line in plain(tui._lines))

    def test_no_cost_line_without_a_provider(self, tui):
        tui._ran_application = None
        tui._show_run_report(RESULT, 62.0)
        assert not any("Cost" in line for line in plain(tui._lines))
        assert any("Time" in line for line in plain(tui._lines))


class TestTheHeaderCost:
    def test_an_unpriced_model_does_not_break_the_row(self):
        """f"${None:.2f}" raised, the caller suppressed it, and nothing updated."""
        bar = HeaderBar.__new__(HeaderBar)
        bar._pages = bar._chapters = bar._cost = bar._model = "—"
        bar._refresh = lambda: None
        bar.update_meta({"pages": 27, "chapters": 5, "estimated_cost": None, "model": "x"})
        assert bar._cost == "—"
        assert bar._chapters == "5", "the rest of the row must still update"

    def test_an_estimate_is_marked_as_one(self):
        bar = HeaderBar.__new__(HeaderBar)
        bar._pages = bar._chapters = bar._cost = bar._model = "—"
        bar._refresh = lambda: None
        bar.update_meta({"estimated_cost": 0.1234})
        assert bar._cost == "~$0.12"

    def test_the_actual_cost_is_not(self):
        """A receipt should not read like a guess."""
        bar = HeaderBar.__new__(HeaderBar)
        bar._cost = "~$0.12"
        bar._refresh = lambda: None
        bar.set_actual_cost(0.1789)
        assert bar._cost == "$0.18"


class TestAnUnpricedModel:
    def test_usage_is_still_reported_without_a_price(self, tui, monkeypatch):
        """A missing price is not a reason to hide real token usage."""
        monkeypatch.setattr("src.cli.tui._lookup_model_cost", lambda _m: None)
        tui._show_run_report(RESULT, 62.0)
        text = " ".join(plain(tui._lines))
        assert "100,000 in" in text and "12 calls" in text
        assert "$" not in text, "no price means no dollar figure"
