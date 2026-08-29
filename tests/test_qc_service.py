"""Tests for the chapter-by-chapter QC checks.

QC has to catch the failure modes the transform can still produce, so each
test builds a book that exhibits one of them and asserts it is reported at the
right severity.
"""

import pytest

from src.models.transformation import TransformType
from src.services.qc_service import (
    AUTO_FIXABLE,
    NEEDS_REVIEW,
    STRUCTURAL,
    QCService,
    format_report,
    repair_book,
)


def book(*chapters):
    """A book dict shaped like the parser's output."""
    return {
        "metadata": {"title": "Test"},
        "chapters": [
            {"number": i + 1, "title": f"Chapter {i + 1}", "paragraphs": list(paragraphs)}
            for i, paragraphs in enumerate(chapters)
        ],
    }


@pytest.fixture
def qc():
    return QCService(TransformType.GENDER_SWAP)


def kinds(report):
    return {f.kind for f in report.all_findings}


class TestCleanTransform:
    def test_a_correct_swap_reports_nothing(self, qc):
        source = book(["Her husband spoke to the queen.", "She told her sister."])
        output = book(["His wife spoke to the king.", "He told his brother."])
        report = qc.check_book(source, output)
        assert report.all_findings == []
        assert report.coverage == 1.0


class TestPartialPair:
    def test_pronoun_moved_but_noun_did_not(self, qc):
        """Carly's report: one half of "her husband" changes and the other does not."""
        source = book(["Her husband was there."])
        output = book(["His husband was there."])
        report = qc.check_book(source, output)
        assert "partial_pair" in kinds(report)
        finding = next(f for f in report.all_findings if f.kind == "partial_pair")
        assert "husband" in finding.detail
        assert finding.severity == NEEDS_REVIEW

    def test_noun_moved_but_pronoun_did_not(self, qc):
        source = book(["Her husband was there."])
        output = book(["Her wife was there."])
        assert "partial_pair" in kinds(qc.check_book(source, output))


class TestSafetyNetRegressions:
    def test_reverted_noun_is_reported_as_auto_fixable(self, qc):
        """The pre-fix pipeline turned "his father" back into "his mother"."""
        source = book(["Her mother arrived."])
        output = book(["His mother arrived."])
        report = qc.check_book(source, output)
        assert AUTO_FIXABLE in {f.severity for f in report.all_findings}
        finding = next(f for f in report.all_findings if f.kind == "safety_net_would_change")
        assert "mother" in finding.detail and "father" in finding.detail

    def test_untransformed_paragraph_is_flagged(self, qc):
        source = book(["The queen spoke to her brother."])
        output = book(["The queen spoke to her brother."])
        report = qc.check_book(source, output)
        assert "untransformed_paragraph" in kinds(report)


class TestStructuralChecks:
    def test_chapter_count_mismatch(self, qc):
        report = qc.check_book(book(["a"], ["b"]), book(["a"]))
        finding = next(f for f in report.all_findings if f.kind == "chapter_count")
        assert finding.severity == STRUCTURAL

    def test_paragraph_count_mismatch(self, qc):
        report = qc.check_book(book(["a", "b"]), book(["a"]))
        assert "paragraph_count" in kinds(report)

    def test_truncated_paragraph_is_caught(self, qc):
        long_source = " ".join(["the man walked slowly along the quiet road"] * 6)
        report = qc.check_book(book([long_source]), book(["the woman walked."]))
        assert "length_drift" in kinds(report)

    def test_small_paragraphs_do_not_trip_length_drift(self, qc):
        report = qc.check_book(book(["The queen spoke."]), book(["The king spoke."]))
        assert "length_drift" not in kinds(report)


class TestNeutralPronouns:
    def test_they_and_them_are_not_counted_as_misses(self, qc):
        """A gender_swap leaves "them" alone by design; that is not a miss."""
        source = book(["How can it affect them?"])
        output = book(["How can it affect them?"])
        report = qc.check_book(source, output)
        assert report.all_findings == []


class TestCoverageAccounting:
    def test_coverage_reflects_transformed_share(self, qc):
        source = book(["The queen and the king and her sister."])
        output = book(["The king and the king and her sister."])
        report = qc.check_book(source, output)
        assert 0.0 < report.coverage < 1.0

    def test_report_renders(self, qc):
        report = qc.check_book(book(["Her husband."]), book(["His husband."]))
        rendered = format_report(report)
        assert "Coverage" in rendered
        assert "Chapter 1" in rendered


class TestRepair:
    """An edition produced before the fix can be corrected without an LLM."""

    def test_repair_clears_auto_fixable_findings(self, qc):
        source = book(["Her mother spoke to the king.", "A single man wants a wife."])
        # What the pre-fix pipeline produced: the noun reverted, the pronoun did not.
        broken = book(["His mother spoke to the king.", "A single woman wants a wife."])

        before = qc.check_book(source, broken)
        assert before.count(AUTO_FIXABLE) > 0

        fixed = repair_book(source, broken, TransformType.GENDER_SWAP)
        after = qc.check_book(source, fixed)

        assert after.count(AUTO_FIXABLE) == 0
        assert after.coverage == 1.0

    def test_repair_produces_the_expected_prose(self, qc):
        source = book(["A single man in possession of a good fortune must want a wife."])
        broken = book(["A single woman in possession of a good fortune must want a wife."])
        fixed = repair_book(source, broken, TransformType.GENDER_SWAP)
        assert fixed["chapters"][0]["paragraphs"][0] == (
            "A single woman in possession of a good fortune must want a husband."
        )

    def test_repair_leaves_a_correct_transform_alone(self, qc):
        source = book(["Her husband spoke to the queen."])
        good = book(["His wife spoke to the king."])
        assert repair_book(source, good, TransformType.GENDER_SWAP) == good

    def test_repair_preserves_paragraph_shape(self, qc):
        """Sentence-list paragraphs must come back as sentence lists."""
        source = {
            "metadata": {},
            "chapters": [{"number": 1, "title": "", "paragraphs": [{"sentences": ["Her son."]}]}],
        }
        broken = {
            "metadata": {},
            "chapters": [{"number": 1, "title": "", "paragraphs": [{"sentences": ["Her son."]}]}],
        }
        fixed = repair_book(source, broken, TransformType.GENDER_SWAP)
        assert fixed["chapters"][0]["paragraphs"][0] == {"sentences": ["His daughter."]}
