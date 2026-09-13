"""A report that cannot say "I did not check this" says "clean" instead.

Three checks returned in silence without a name map: the one that catches a
family name the book stopped using, the one that catches a rename that never
landed, and the one that catches a name the engine never chose. The usage
documented in CLAUDE.md passes no name map --

    python scripts/qc_report.py source.json gender_swap.json gender_swap

-- so the default invocation turned all three off and printed a report
indistinguishable from a clean one. Run against the shipped gender_swap edition
with its map, those three report sixteen findings the edition had always had:
residual_name=8, invented_name=7, surname_lost=1.

This is the same shape as the naming bugs of the same day -- a skip taken for a
good reason, wider than the reason -- except here the silence was the whole
defect, because quality control that does not run still prints a verdict.
"""

import json
import sys
from pathlib import Path

import pytest

from src.models.transformation import TransformType
from src.services.qc_service import QCReport, QCService, format_report

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


def book(paragraphs):
    return {
        "chapters": [
            {
                "number": 1,
                "title": "Chapter 1",
                "paragraphs": [{"sentences": [p]} for p in paragraphs],
            }
        ]
    }


SOURCE = book(["Mr. Darcy walked with Elizabeth Bennet.", "She admired his estate."])
OUTPUT = book(["Mrs. Darcy walked with Edward Bennet.", "He admired her estate."])
NAME_MAP = {"Elizabeth Bennet": "Edward Bennet"}


class TestWithoutAMap:
    @pytest.fixture
    def report(self):
        return QCService(TransformType.GENDER_SWAP).check_book(SOURCE, OUTPUT)

    def test_the_report_says_which_checks_did_not_run(self, report):
        assert set(report.not_checked) == {
            "surnames_survive",
            "renames_landed",
            "invented_names",
        }

    def test_each_one_says_why(self, report):
        for why in report.not_checked.values():
            assert "no name map" in why, why

    def test_the_report_knows_it_is_incomplete(self, report):
        assert report.complete is False

    def test_it_is_the_first_thing_on_screen(self, report):
        """Not a footnote. A report missing its name checks is a different kind
        of answer, not a weaker clean one."""
        first = format_report(report).splitlines()[0]
        assert "DID NOT RUN" in first
        assert "not a pass" in first

    def test_it_survives_the_json(self, report):
        assert report.to_dict()["not_checked"]


class TestWithAMap:
    @pytest.fixture
    def report(self):
        return QCService(TransformType.GENDER_SWAP, name_map=NAME_MAP).check_book(SOURCE, OUTPUT)

    def test_nothing_is_skipped(self, report):
        assert report.not_checked == {}
        assert report.complete is True

    def test_no_banner(self, report):
        assert "DID NOT RUN" not in format_report(report)


class TestFindingTheMapWithoutBeingTold:
    """The documented invocation passes no map, and nobody noticed for as long
    as that had been true. The run leaves one beside the edition; use it."""

    def script(self):
        import qc_report

        return qc_report

    def test_the_finished_map_is_found(self, tmp_path):
        (tmp_path / "name_map.json").write_text(json.dumps(NAME_MAP))
        edition = tmp_path / "gender_swap.json"
        edition.write_text("{}")
        found, where = self.script().find_name_map(edition)
        assert found == NAME_MAP
        assert where.name == "name_map.json"

    def test_the_audited_map_is_the_fallback(self, tmp_path):
        """Written when the map is audited, so it is the one that exists if the
        run was stopped before the transform."""
        (tmp_path / "name_map_proposed.json").write_text(json.dumps(NAME_MAP))
        edition = tmp_path / "gender_swap.json"
        edition.write_text("{}")
        found, where = self.script().find_name_map(edition)
        assert found == NAME_MAP
        assert where.name == "name_map_proposed.json"

    def test_the_finished_map_wins(self, tmp_path):
        (tmp_path / "name_map.json").write_text(json.dumps(NAME_MAP))
        (tmp_path / "name_map_proposed.json").write_text(json.dumps({"x": "y"}))
        edition = tmp_path / "gender_swap.json"
        edition.write_text("{}")
        _found, where = self.script().find_name_map(edition)
        assert where.name == "name_map.json"

    def test_nothing_beside_it_is_not_an_error(self, tmp_path):
        edition = tmp_path / "gender_swap.json"
        edition.write_text("{}")
        assert self.script().find_name_map(edition) == (None, None)

    def test_an_unreadable_map_is_not_an_error(self, tmp_path):
        """A truncated file should leave QC saying it did not check, not crash."""
        (tmp_path / "name_map.json").write_text("{ broken")
        edition = tmp_path / "gender_swap.json"
        edition.write_text("{}")
        assert self.script().find_name_map(edition) == (None, None)


class TestTheDefaultIsNotQuietlyEmpty:
    def test_an_empty_report_is_complete(self):
        """A report nobody skipped anything in must not claim it was."""
        assert QCReport(transform_type="gender_swap").complete is True
