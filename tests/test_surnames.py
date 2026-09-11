"""A surname is not a nickname.

Single-word aliases were sent to the target's given name so that "Lizzy" would
become "Ned" rather than "Edward Bennet". Correct for a nickname. Catastrophic
for a surname: "Darcy" is listed as an alias of Fitzwilliam Darcy, and Austen's
characters address each other by surname, so "Come, Darcy" became "Come,
Fitzwillia" in three hundred places of a finished book.

A rename changes a given name. The surname is the part that must survive.
"""

import pytest

from src.models.character import Character, CharacterAnalysis, Gender
from src.models.transformation import TransformType
from src.services.qc_service import STRUCTURAL, QCService
from src.services.transform_service import TransformService


@pytest.fixture
def svc():
    return TransformService.__new__(TransformService)


def cast(*specs):
    return CharacterAnalysis(
        book_id="t",
        characters=[Character(name=n, gender=g, pronouns={}, aliases=list(a)) for n, g, a in specs],
    )


class TestASurnameIsNotANickname:
    def test_a_surname_alias_is_refused(self, svc):
        characters = cast(("Fitzwilliam Darcy", Gender.MALE, ["Darcy"]))
        expanded = svc._expand_name_map_with_aliases(
            {"Fitzwilliam Darcy": "Fitzwillia Darcy"}, characters
        )
        assert "Darcy" not in expanded, "the surname must not be renamed"

    def test_the_full_name_still_maps(self, svc):
        characters = cast(("Fitzwilliam Darcy", Gender.MALE, ["Darcy"]))
        expanded = svc._expand_name_map_with_aliases(
            {"Fitzwilliam Darcy": "Fitzwillia Darcy"}, characters
        )
        assert expanded["Fitzwilliam Darcy"] == "Fitzwillia Darcy"

    def test_a_real_nickname_still_works(self, svc):
        """The behaviour this rule must not undo."""
        characters = cast(("Elizabeth Bennet", Gender.FEMALE, ["Lizzy"]))
        expanded = svc._expand_name_map_with_aliases(
            {"Elizabeth Bennet": "Edward Bennet"}, characters
        )
        assert expanded["Lizzy"] == "Edward"

    def test_a_title_and_surname_entry_claims_its_surname(self, svc):
        assert svc._surname_of("Mr. Darcy") == "Darcy"
        assert svc._surname_of("Fitzwilliam Darcy") == "Darcy"

    def test_a_rank_works_like_a_title(self, svc):
        """ "Colonel Fitzwilliam" is a surname with a rank, not a given name."""
        assert svc._surname_of("Colonel Fitzwilliam") == "Fitzwilliam"

    def test_a_bare_given_name_has_no_surname(self, svc):
        assert svc._surname_of("Elizabeth") is None


class TestAmbiguityBetweenAGivenNameAndASurname:
    def test_a_rank_titled_surname_blocks_the_bare_word(self, svc):
        """Fitzwilliam is Darcy's given name and the Colonel's surname."""
        characters = cast(
            ("Fitzwilliam Darcy", Gender.MALE, []),
            ("Colonel Fitzwilliam", Gender.MALE, []),
        )
        expanded = svc._expand_name_map_with_aliases(
            {"Fitzwilliam Darcy": "Fitzwillia Darcy"}, characters
        )
        assert "Fitzwilliam" not in expanded

    def test_without_the_clash_the_bare_name_is_mapped(self, svc):
        characters = cast(("Fitzwilliam Darcy", Gender.MALE, []))
        expanded = svc._expand_name_map_with_aliases(
            {"Fitzwilliam Darcy": "Fitzwillia Darcy"}, characters
        )
        assert expanded["Fitzwilliam"] == "Fitzwillia"


def chapter(*lines):
    return {"number": 1, "title": "", "paragraphs": [{"sentences": [t]} for t in lines]}


class TestQCCatchesALostSurname:
    MAP = {"Fitzwilliam Darcy": "Fitzwillia Darcy"}

    def run(self, source, output):
        return QCService(TransformType.ALL_FEMALE, name_map=self.MAP).check_book(
            {"chapters": [chapter(*source)]}, {"chapters": [chapter(*output)]}
        )

    def test_a_surname_that_mostly_vanished_is_structural(self):
        source = [f"Darcy spoke to her, and Darcy left. {i}" for i in range(8)]
        output = [f"Fitzwillia spoke to her, and Fitzwillia left. {i}" for i in range(8)]
        found = [f for f in self.run(source, output).all_findings if f.kind == "surname_lost"]
        assert found and found[0].severity == STRUCTURAL

    def test_a_surname_that_survives_is_not_reported(self):
        source = [f"Darcy spoke to her, and Darcy left. {i}" for i in range(8)]
        output = [f"Darcy spoke to him, and Darcy left. {i}" for i in range(8)]
        assert not [f for f in self.run(source, output).all_findings if f.kind == "surname_lost"]

    def test_a_rare_surname_is_not_judged_by_count(self):
        """Two mentions are not evidence of anything."""
        found = [
            f
            for f in self.run(["Darcy spoke."], ["Fitzwillia spoke."]).all_findings
            if f.kind == "surname_lost"
        ]
        assert not found

    def test_a_kinship_word_is_not_treated_as_a_surname(self):
        """Map keys include phrases like "her father"."""
        qc = QCService(TransformType.ALL_FEMALE, name_map={"her father": "her mother"})
        source = [f"her father spoke {i}" for i in range(12)]
        output = [f"her mother spoke {i}" for i in range(12)]
        report = qc.check_book({"chapters": [chapter(*source)]}, {"chapters": [chapter(*output)]})
        assert not [f for f in report.all_findings if f.kind == "surname_lost"]
