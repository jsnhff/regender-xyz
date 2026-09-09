"""What the QC gate hands back to the run.

QC counts every gendered word and how many of them changed, then reported
only the ratio. A percentage hides the scale of what a run did, and that
count is the point of the work -- so the gate now passes the raw totals up.
"""

import json
from pathlib import Path

import pytest

from src.app import Application
from src.models.transformation import TransformType


def chapter(number, *paragraphs):
    return {
        "number": number,
        "title": f"Chapter {number}",
        "paragraphs": [{"sentences": [text]} for text in paragraphs],
    }


def book(*chapters):
    return {"title": "T", "chapters": list(chapters)}


class _Transformation:
    def __init__(self, transformed):
        self._transformed = transformed

    def get_transformed_book(self):
        return type("B", (), {"to_dict": lambda _self: self._transformed})()


@pytest.fixture
def gate():
    app = Application.__new__(Application)
    import logging

    app.logger = logging.getLogger("test")
    return app


SOURCE = book(
    chapter(1, "He told his sister that he was her brother.", "The man bowed to his wife."),
    chapter(2, "She said her father was a gentleman."),
)
SWAPPED = book(
    chapter(1, "She told her brother that she was his sister.", "The woman bowed to her husband."),
    chapter(2, "He said his mother was a lady."),
)


def run(gate, tmp_path, source, transformed):
    out = tmp_path / "gender_swap.json"
    out.write_text("{}")
    return gate._run_quality_control(
        source, _Transformation(transformed), TransformType.GENDER_SWAP, str(out), []
    )


class TestTheWordCounts:
    def test_it_reports_how_many_gendered_words_it_found(self, gate, tmp_path):
        summary = run(gate, tmp_path, SOURCE, SWAPPED)
        assert summary["gendered_words"] > 0

    def test_it_reports_how_many_actually_changed(self, gate, tmp_path):
        summary = run(gate, tmp_path, SOURCE, SWAPPED)
        assert summary["transformed_words"] > 0

    def test_a_clean_swap_changes_every_gendered_word(self, gate, tmp_path):
        summary = run(gate, tmp_path, SOURCE, SWAPPED)
        assert summary["transformed_words"] == summary["gendered_words"]

    def test_the_totals_match_the_coverage_qc_computed(self, gate, tmp_path):
        """Two independent routes to the same fraction must agree."""
        summary = run(gate, tmp_path, SOURCE, SWAPPED)
        written = json.loads(Path(summary["report"]).read_text())
        ratio = summary["transformed_words"] / summary["gendered_words"]
        assert round(ratio, 4) == written["coverage"]

    def test_an_untransformed_book_changed_nothing(self, gate, tmp_path):
        summary = run(gate, tmp_path, SOURCE, SOURCE)
        assert summary["transformed_words"] == 0
        assert summary["gendered_words"] > 0

    def test_the_counts_never_exceed_what_was_found(self, gate, tmp_path):
        for transformed in (SOURCE, SWAPPED):
            summary = run(gate, tmp_path, SOURCE, transformed)
            assert summary["transformed_words"] <= summary["gendered_words"]


class TestTheGateStillGates:
    def test_a_missing_chapter_is_structural(self, gate, tmp_path):
        short = book(SWAPPED["chapters"][0])
        summary = run(gate, tmp_path, SOURCE, short)
        assert summary["structural"] >= 1
        assert summary["blocked"] is True

    def test_a_clean_run_does_not_block(self, gate, tmp_path):
        assert run(gate, tmp_path, SOURCE, SWAPPED)["blocked"] is False

    def test_qc_is_never_the_reason_a_run_is_lost(self, gate, tmp_path):
        """A transformation that cannot produce a book must not raise."""
        broken = type("X", (), {})()
        out = tmp_path / "o.json"
        out.write_text("{}")
        assert (
            gate._run_quality_control(SOURCE, broken, TransformType.GENDER_SWAP, str(out), [])
            is None
        )
