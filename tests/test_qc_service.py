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


class TestPairGender:
    def test_pronoun_moved_but_noun_did_not(self, qc):
        """Carly's report: one half of "her husband" changes and the other does not."""
        source = book(["Her husband was there."])
        output = book(["His husband was there."])
        report = qc.check_book(source, output)
        assert "pair_gender" in kinds(report)
        finding = next(f for f in report.all_findings if f.kind == "pair_gender")
        assert "husband" in finding.detail
        assert finding.severity == NEEDS_REVIEW

    def test_noun_moved_but_pronoun_did_not(self, qc):
        source = book(["Her husband was there."])
        output = book(["Her wife was there."])
        assert "pair_gender" in kinds(qc.check_book(source, output))


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


class TestOneDirectionalTransforms:
    """A pronoun-only change is correct when the noun is already on target."""

    def test_all_female_his_wife_is_not_a_partial_pair(self):
        qc = QCService(TransformType.ALL_FEMALE)
        report = qc.check_book(book(["His wife spoke."]), book(["Her wife spoke."]))
        assert "pair_gender" not in kinds(report)

    def test_all_male_her_husband_is_not_a_partial_pair(self):
        qc = QCService(TransformType.ALL_MALE)
        report = qc.check_book(book(["Her husband spoke."]), book(["His husband spoke."]))
        assert "pair_gender" not in kinds(report)

    def test_all_female_still_catches_a_real_miss(self):
        """ "his brother" must become "her sister"; a stalled noun is a real pair break."""
        qc = QCService(TransformType.ALL_FEMALE)
        report = qc.check_book(book(["His brother spoke."]), book(["Her brother spoke."]))
        assert "pair_gender" in kinds(report)


class TestPairGenderCoherence:
    """Both halves moving is not enough — they have to land on the right genders."""

    def test_both_halves_moved_but_the_noun_landed_wrong(self):
        """ "his lady" becoming "her wife" passes a moved/not-moved check and is
        still wrong: the swap needs a female possessor and a male noun."""
        qc = QCService(TransformType.GENDER_SWAP)
        report = qc.check_book(book(["said his lady to him"]), book(["said her wife to her"]))
        finding = next(f for f in report.all_findings if f.kind == "pair_gender")
        assert "wanted male" in finding.detail

    def test_correct_swap_of_both_halves_passes(self):
        qc = QCService(TransformType.GENDER_SWAP)
        report = qc.check_book(book(["said his lady to him"]), book(["said her lord to her"]))
        assert "pair_gender" not in kinds(report)

    def test_natural_rephrasing_passes(self):
        """A model may write "her husband" where the term map would say "her lord"."""
        qc = QCService(TransformType.GENDER_SWAP)
        report = qc.check_book(book(["said his lady to him"]), book(["said her husband to her"]))
        assert "pair_gender" not in kinds(report)

    def test_nonbinary_pair_must_end_up_neutral(self):
        qc = QCService(TransformType.NONBINARY)
        report = qc.check_book(book(["her mother arrived"]), book(["their mother arrived"]))
        finding = next(f for f in report.all_findings if f.kind == "pair_gender")
        assert "still female" in finding.detail


class TestStructuralSensitivity:
    def test_emptied_paragraph_is_caught_however_short(self):
        """The signature of the old batch parser padding a short response."""
        qc = QCService(TransformType.GENDER_SWAP)
        report = qc.check_book(book(["Mrs. Bennet made no answer."]), book([""]))
        assert "empty_paragraph" in kinds(report)

    def test_short_paragraph_cannot_quietly_grow(self):
        """25% of a four-word line is one word, so a relative check alone misses this."""
        qc = QCService(TransformType.GENDER_SWAP)
        report = qc.check_book(
            book(["This was invitation enough."]),
            book(["This was invitation enough. She smiled at the thought and said nothing more."]),
        )
        assert "length_drift" in kinds(report)

    def test_a_normal_transform_does_not_trip_the_absolute_floor(self):
        qc = QCService(TransformType.GENDER_SWAP)
        report = qc.check_book(
            book(["Mr. Bennet replied that he had not."]),
            book(["Mrs. Bennet replied that she had not."]),
        )
        assert "length_drift" not in kinds(report)


class TestNameVerification:
    def test_unrenamed_character_is_caught(self):
        qc = QCService(TransformType.GENDER_SWAP, name_map={"Lizzy": "Liam"})
        report = qc.check_book(
            book(["a good word for my little Lizzy"]), book(["a good word for my little Lizzy"])
        )
        finding = next(f for f in report.all_findings if f.kind == "residual_name")
        assert "Liam" in finding.detail

    def test_applied_rename_passes(self):
        qc = QCService(TransformType.GENDER_SWAP, name_map={"Lizzy": "Liam"})
        report = qc.check_book(
            book(["a good word for my little Lizzy"]), book(["a good word for my little Liam"])
        )
        assert "residual_name" not in kinds(report)

    def test_names_respect_word_boundaries(self):
        """ "Ann" must not report a finding against "Anne"."""
        qc = QCService(TransformType.GENDER_SWAP, name_map={"Ann": "Alan"})
        report = qc.check_book(book(["Anne walked on"]), book(["Anne walked on"]))
        assert "residual_name" not in kinds(report)

    def test_no_name_map_means_no_name_checks(self):
        qc = QCService(TransformType.GENDER_SWAP)
        report = qc.check_book(book(["my little Lizzy"]), book(["my little Lizzy"]))
        assert "residual_name" not in kinds(report)


class TestParagraphContinuity:
    """A sentence cut in half by a stripped illustration plate."""

    def test_split_sentence_is_reported(self, qc):
        source = book(
            [
                "Lady Lucas quieted her fears a little by starting the idea of his",
                "being gone to London only to get a large party for the ball.",
            ]
        )
        report = qc.check_book(source, source)
        finding = next(f for f in report.all_findings if f.kind == "split_sentence")
        assert finding.severity == STRUCTURAL

    def test_ordinary_paragraphs_are_not_reported(self, qc):
        source = book(["Mr. Bennet made no answer.", "This was invitation enough."])
        assert "split_sentence" not in kinds(qc.check_book(source, source))

    def test_lower_case_opening_after_a_full_stop_is_fine(self, qc):
        source = book(["He came down on Monday.", "mid-sentence looking, but preceded by a stop."])
        assert "split_sentence" not in kinds(qc.check_book(source, source))


class TestTextIntegrity:
    """Corruption the model invented, which no gender-aware gate would notice.

    The printed all_male Pride and Prejudice shipped with two of these: a
    paragraph that fell into a repetition loop and emitted CJK, and another
    that duplicated a phrase. Nothing in either is gendered, so every other
    check passed them.
    """

    def test_character_absent_from_the_source_is_reported(self):
        qc = QCService(TransformType.ALL_MALE)
        report = qc.check_book(
            book(["It is settled between us already."]),
            book(["It is settled between us 当 already."]),
        )
        findings = [f for c in report.chapters for f in c.findings if f.kind == "alien_character"]
        assert len(findings) == 1
        assert findings[0].severity == STRUCTURAL

    def test_repetition_loop_is_reported(self):
        qc = QCService(TransformType.ALL_MALE)
        report = qc.check_book(
            book(["It is settled between us already."]),
            book(["It is settled settled between us already."]),
        )
        findings = [f for c in report.chapters for f in c.findings if f.kind == "repetition_loop"]
        assert len(findings) == 1

    def test_repetition_the_source_also_has_is_left_alone(self):
        qc = QCService(TransformType.ALL_MALE)
        report = qc.check_book(
            book(["He had had no compassion."]),
            book(["He had had no compassion."]),
        )
        assert not [f for c in report.chapters for f in c.findings if f.kind == "repetition_loop"]

    def test_two_words_collapsing_onto_one_target_is_not_a_repeat(self):
        """A swap turns "got him his commission" into "got her her commission"."""
        qc = QCService(TransformType.GENDER_SWAP)
        report = qc.check_book(
            book(["Darcy got him his commission."]),
            book(["Darcy got her her commission."]),
        )
        assert not [f for c in report.chapters for f in c.findings if f.kind == "repetition_loop"]

    def test_clean_text_reports_nothing(self):
        qc = QCService(TransformType.ALL_MALE)
        report = qc.check_book(
            book(["She was his sister."]),
            book(["He was his brother."]),
        )
        kinds = {f.kind for c in report.chapters for f in c.findings}
        assert "alien_character" not in kinds and "repetition_loop" not in kinds


class TestCoordination:
    """A couple collapsed into one person.

    "go after Mr. and Mrs. Gardiner" came back as "go after Mr. Gardiner" in
    the gender_swap, all_male and all_female editions -- three separate runs,
    the same sentence. Every honorific left behind is correct, so no
    gender-aware check notices; only the missing person is wrong.
    """

    def test_dropped_half_of_a_pair_is_reported(self):
        qc = QCService(TransformType.ALL_MALE)
        report = qc.check_book(
            book(["Go after Mr. and Mrs. Gardiner."]),
            book(["Go after Mr. Gardiner."]),
        )
        findings = [
            f for c in report.chapters for f in c.findings if f.kind == "dropped_coordination"
        ]
        assert len(findings) == 1
        assert findings[0].severity == STRUCTURAL
        assert "Gardiner" in findings[0].detail

    def test_a_pair_that_survives_is_not_reported(self):
        qc = QCService(TransformType.ALL_MALE)
        report = qc.check_book(
            book(["Go after Mr. and Mrs. Gardiner."]),
            book(["Go after Mr. and Mr. Gardiner."]),
        )
        assert not [
            f for c in report.chapters for f in c.findings if f.kind == "dropped_coordination"
        ]

    def test_swapped_pair_survives(self):
        """A gender_swap reverses the two titles; the pair is still a pair."""
        qc = QCService(TransformType.GENDER_SWAP)
        report = qc.check_book(
            book(["Go after Mr. and Mrs. Gardiner."]),
            book(["Go after Ms. and Mr. Gardiner."]),
        )
        assert not [
            f for c in report.chapters for f in c.findings if f.kind == "dropped_coordination"
        ]

    def test_a_lone_title_is_not_a_pair(self):
        qc = QCService(TransformType.ALL_MALE)
        report = qc.check_book(book(["Go after Mrs. Gardiner."]), book(["Go after Mr. Gardiner."]))
        assert not [
            f for c in report.chapters for f in c.findings if f.kind == "dropped_coordination"
        ]
