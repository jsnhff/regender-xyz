"""What the safety net changed, and which of those changes deserve a look.

The change log records whole-paragraph diffs, so a decision like
"pages -> handmaids" was buried inside a paragraph and nobody could see the net
had made it. Every defect in the printed edition was found by hand-writing a
scan for it after the fact. These two tiers make the calls visible and sift
them, without a model call.
"""

import pytest

from src.models.transformation import TransformType
from src.services.transform_service import TransformService


@pytest.fixture
def logged():
    service = TransformService.__new__(TransformService)
    service.start_substitution_log()
    return service


def swap(service, text, where=(1, 0)):
    return service._apply_term_map(text, TransformType.GENDER_SWAP, text, where=where)


class TestTierOneTheAuditTrail:
    def test_each_substitution_is_recorded(self, logged):
        swap(logged, "Her father was a widower.")
        pairs = {(e["before"], e["after"]) for e in logged._substitution_log}
        assert ("father", "mother") in pairs
        assert ("widower", "widow") in pairs

    def test_the_location_is_kept(self, logged):
        swap(logged, "Her father spoke.", where=(7, 13))
        entry = logged._substitution_log[0]
        assert (entry["chapter"], entry["paragraph"]) == (7, 13)

    def test_an_excerpt_is_kept_for_reading(self, logged):
        swap(logged, "Her father was a widower.")
        assert "father" in logged._substitution_log[0]["excerpt"]

    def test_logging_is_off_unless_asked_for(self):
        """Every existing caller records nothing and pays nothing."""
        service = TransformService.__new__(TransformService)
        assert service._apply_term_map("Her father spoke.", TransformType.GENDER_SWAP) is not None
        assert getattr(service, "_substitution_log", None) is None


class TestTierTwoTheTripwire:
    def test_a_capitalised_midsentence_word_is_flagged(self, logged):
        """The shape of "Mary King" -> "Mary Queen"."""
        service = TransformService.__new__(TransformService)
        service.start_substitution_log()
        swap(service, "Wickham is marrying Mary King.")
        flagged = service.suspicious_substitutions(service._substitution_log)
        assert [(p["before"], p["after"]) for p in flagged] == [("King", "Queen")]

    def test_a_sentence_opener_is_not_flagged(self, logged):
        """Capitalised by grammar, not because it is a name."""
        swap(logged, "Brothers are troublesome.")
        assert logged.suspicious_substitutions(logged._substitution_log) == []

    def test_a_lowercase_word_is_not_flagged(self, logged):
        swap(logged, "Her father was a widower.")
        assert logged.suspicious_substitutions(logged._substitution_log) == []

    def test_pairs_are_deduped_with_a_count(self, logged):
        swap(logged, "Mary King and Miss King and young King.")
        flagged = logged.suspicious_substitutions(logged._substitution_log)
        assert len(flagged) == 1
        assert flagged[0]["count"] == 3

    def test_the_commonest_pair_comes_first(self, logged):
        swap(logged, "Mary King, Mary King, and a Duke.")
        flagged = logged.suspicious_substitutions(logged._substitution_log)
        assert flagged[0]["count"] >= flagged[-1]["count"]

    def test_an_empty_log_is_handled(self):
        assert TransformService.suspicious_substitutions([]) == []
        assert TransformService.suspicious_substitutions(None) == []


class TestItWouldHaveCaughtTheRealBugs:
    """Both defects that reached print, from the sentences they appear in."""

    def test_mary_king(self):
        service = TransformService.__new__(TransformService)
        service.start_substitution_log()
        swap(service, "There is no danger of Wickham's marrying Mary King.")
        flagged = service.suspicious_substitutions(service._substitution_log)
        assert any(p["before"] == "King" for p in flagged)

    def test_sir_william(self):
        service = TransformService.__new__(TransformService)
        service.start_substitution_log()
        swap(service, "by Sir William Lucas's accidental information")
        flagged = service.suspicious_substitutions(service._substitution_log)
        # With the guard in place Sir becomes Lady, which is right -- but it is
        # still a capitalised mid-sentence change, so it stays visible.
        assert any(p["before"] == "Sir" for p in flagged)
