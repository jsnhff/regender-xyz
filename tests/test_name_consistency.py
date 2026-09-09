"""One character, one name.

The name engine settles each character's new name once, before any chapter is
transformed, so the whole book agrees. Three things defeated it: the prompt
never told the model the chosen name, the deterministic map ran afterwards and
re-swapped names the model had already got right, and QC was never given the
map so it could not see any of it. Elizabeth came out of a five-chapter run as
"Elliot" 34 times and "Edward Bennet" 3 times, at 99.7% coverage.
"""

import pytest

from src.models.character import Character, CharacterAnalysis, Gender
from src.models.transformation import TransformType
from src.services.qc_service import STRUCTURAL, QCService
from src.services.transform_service import TransformService


@pytest.fixture
def svc():
    return TransformService.__new__(TransformService)


SWAP_MAP = {
    "Mr. Bennet": "Mrs. Bennet",
    "Mrs. Bennet": "Mr. Bennet",
    "Elizabeth Bennet": "Edward Bennet",
}


class TestTheMapDoesNotUndoTheModel:
    """A name map holds exchange pairs, so applying it twice is a swap back."""

    def test_a_name_the_model_left_alone_is_renamed(self, svc):
        out = svc._apply_name_map(
            "Mr. Bennet was glad.", SWAP_MAP, source_text="Mr. Bennet was glad."
        )
        assert out == "Mrs. Bennet was glad."

    def test_a_name_the_model_already_swapped_is_left_alone(self, svc):
        """This is the bug: the model was right and the map reversed it."""
        out = svc._apply_name_map(
            "Mrs. Bennet was glad.", SWAP_MAP, source_text="Mr. Bennet was glad."
        )
        assert out == "Mrs. Bennet was glad."

    def test_both_halves_of_an_exchange_in_one_paragraph_survive(self, svc):
        source = "Mr. Bennet spoke to Mrs. Bennet."
        model = "Mrs. Bennet spoke to Mr. Bennet."
        assert svc._apply_name_map(model, SWAP_MAP, source_text=source) == model

    def test_the_philips_case(self, svc):
        """The model wrote a correct 'Mrs.'; the map restored the man."""
        source = "that my uncle Philips talks of turning away Richard?"
        model = "that Mrs. Philips Philips talks of turning away Richenda?"
        out = svc._apply_name_map(
            model,
            {"Mr. Philips": "Mrs. Philips", "Mrs. Philips": "Mr. Philips"},
            source_text=source,
        )
        assert "Mr. Philips Philips" not in out
        assert "Mrs. Philips" in out

    def test_a_rename_the_model_missed_still_lands(self, svc):
        out = svc._apply_name_map(
            "Elizabeth Bennet walked in.", SWAP_MAP, source_text="Elizabeth Bennet walked in."
        )
        assert out == "Edward Bennet walked in."

    def test_without_a_source_it_behaves_as_before(self, svc):
        """Callers that cannot supply the source must not silently stop working."""
        assert svc._apply_name_map("Mr. Bennet.", SWAP_MAP) == "Mrs. Bennet."


def cast(*specs):
    return CharacterAnalysis(
        book_id="test",
        characters=[
            Character(name=name, gender=gender, pronouns={}, aliases=list(aliases))
            for name, gender, aliases in specs
        ],
    )


class TestThePromptCarriesTheChosenName:
    def test_the_model_is_told_what_to_call_them(self, svc):
        characters = cast(("Elizabeth Bennet", Gender.FEMALE, ["Lizzy"]))
        context = svc._create_context(
            characters, TransformType.GENDER_SWAP, None, {"Elizabeth Bennet": "Edward Bennet"}
        )
        instructions = svc._build_character_instructions(
            characters,
            TransformType.GENDER_SWAP,
            context["character_mappings"],
            context["name_map"],
        )
        assert "Edward Bennet" in instructions

    def test_without_a_map_it_says_only_the_direction(self, svc):
        characters = cast(("Elizabeth Bennet", Gender.FEMALE, []))
        context = svc._create_context(characters, TransformType.GENDER_SWAP, None)
        instructions = svc._build_character_instructions(
            characters, TransformType.GENDER_SWAP, context["character_mappings"], None
        )
        assert "female" in instructions
        assert "always call them" not in instructions


class TestAliasesKeepTheirScale:
    """'No, Lizzy' must not become 'No, Edward Bennet'."""

    def test_a_nickname_takes_the_given_name(self, svc):
        characters = cast(("Elizabeth Bennet", Gender.FEMALE, ["Lizzy", "Eliza"]))
        expanded = svc._expand_name_map_with_aliases(
            {"Elizabeth Bennet": "Edward Bennet"}, characters
        )
        assert expanded["Lizzy"] == "Edward"
        assert expanded["Eliza"] == "Edward"

    def test_the_full_name_still_maps_in_full(self, svc):
        characters = cast(("Elizabeth Bennet", Gender.FEMALE, ["Lizzy"]))
        expanded = svc._expand_name_map_with_aliases(
            {"Elizabeth Bennet": "Edward Bennet"}, characters
        )
        assert expanded["Elizabeth Bennet"] == "Edward Bennet"

    def test_the_bare_given_name_is_covered(self, svc):
        """The commonest form in the prose, and it had no mapping at all."""
        characters = cast(("Elizabeth Bennet", Gender.FEMALE, []))
        expanded = svc._expand_name_map_with_aliases(
            {"Elizabeth Bennet": "Edward Bennet"}, characters
        )
        assert expanded["Elizabeth"] == "Edward"

    def test_an_ambiguous_given_name_is_left_alone(self, svc):
        """Two Catherines: a bare 'Catherine' cannot be assigned without guessing."""
        characters = cast(
            ("Catherine Bennet", Gender.FEMALE, []),
            ("Lady Catherine de Bourgh", Gender.FEMALE, []),
        )
        expanded = svc._expand_name_map_with_aliases(
            {
                "Catherine Bennet": "Charles Bennet",
                "Lady Catherine de Bourgh": "Lord Cuthbert de Bourgh",
            },
            characters,
        )
        assert "Catherine" not in expanded

    def test_a_title_does_not_become_a_first_name(self, svc):
        """'Mr. King' must not be shortened to the bare surname 'King'."""
        assert svc._given_name("Mr. King") == "Mr. King"
        assert svc._given_name("Edward Bennet") == "Edward"


def chapter(number, *paragraphs):
    return {
        "number": number,
        "title": "",
        "paragraphs": [{"sentences": [t]} for t in paragraphs],
    }


class TestQCSeesRenaming:
    MAP = {"Elizabeth Bennet": "Edward Bennet", "Elizabeth": "Edward"}

    def qc(self, source, output, name_map=None):
        return QCService(
            TransformType.GENDER_SWAP, name_map=name_map if name_map is not None else self.MAP
        ).check_book({"chapters": [source]}, {"chapters": [output]})

    def test_an_invented_name_is_structural(self):
        """Elizabeth called something nobody chose."""
        source = chapter(
            1,
            "Elizabeth spoke.",
            "Elizabeth smiled.",
            "Elizabeth left.",
            "Elizabeth wrote.",
            "Elizabeth read.",
        )
        output = chapter(
            1, "Elliot spoke.", "Elliot smiled.", "Elliot left.", "Elliot wrote.", "Elliot read."
        )
        report = self.qc(source, output)
        kinds = [f.kind for f in report.all_findings]
        assert "rename_lost" in kinds
        assert any(f.severity == STRUCTURAL for f in report.all_findings)

    def test_the_agreed_name_passes(self):
        source = chapter(
            1,
            "Elizabeth spoke.",
            "Elizabeth smiled.",
            "Elizabeth left.",
            "Elizabeth wrote.",
            "Elizabeth read.",
        )
        output = chapter(
            1, "Edward spoke.", "Edward smiled.", "Edward left.", "Edward wrote.", "Edward read."
        )
        assert not [f for f in self.qc(source, output).all_findings if f.kind == "rename_lost"]

    def test_a_pronoun_here_and_there_is_not_a_finding(self):
        """Prose replaces a name with a pronoun; that is not a lost rename."""
        source = chapter(
            1,
            "Elizabeth spoke.",
            "Elizabeth smiled.",
            "Elizabeth left.",
            "Elizabeth wrote.",
            "Elizabeth read.",
        )
        output = chapter(
            1, "Edward spoke.", "Edward smiled.", "He left.", "Edward wrote.", "Edward read."
        )
        assert not [f for f in self.qc(source, output).all_findings if f.kind == "rename_lost"]

    def test_without_the_map_qc_is_blind(self):
        """This is why a book naming its protagonist two ways scored 99.7%."""
        source = chapter(
            1,
            "Elizabeth spoke.",
            "Elizabeth smiled.",
            "Elizabeth left.",
            "Elizabeth wrote.",
            "Elizabeth read.",
        )
        output = chapter(
            1, "Elliot spoke.", "Elliot smiled.", "Elliot left.", "Elliot wrote.", "Elliot read."
        )
        assert not self.qc(source, output, name_map={}).all_findings


class TestQCDoesNotCryWolf:
    """A check that fires on correct work gets switched off."""

    def test_an_honorific_swap_is_not_an_invented_name(self):
        """'Sir' becoming 'Lady' is the term map doing its job."""
        qc = QCService(
            TransformType.GENDER_SWAP,
            name_map={"Sir William Lucas": "Dame Wilhelmina Lucas"},
        )
        assert "sir" not in qc._expected_word

    def test_a_kinship_alias_does_not_teach_it_nonsense(self):
        """'her sister' -> 'James Bennet' would pair 'her' with 'James'."""
        qc = QCService(TransformType.GENDER_SWAP, name_map={"her sister": "James Bennet"})
        assert "her" not in qc._expected_word

    def test_a_mismatched_title_entry_is_not_paired_word_for_word(self):
        """'Miss Elizabeth' -> 'Edward Bennet' must not teach Elizabeth->Bennet."""
        qc = QCService(TransformType.GENDER_SWAP, name_map={"Miss Elizabeth": "Edward Bennet"})
        assert "bennet" not in qc._expected_word.get("elizabeth", set())

    def test_an_exchanged_name_is_not_reported_as_un_renamed(self):
        """'Mrs. Bennet' in a swap's output is what 'Mr. Bennet' became."""
        qc = QCService(
            TransformType.GENDER_SWAP,
            name_map={"Mr. Bennet": "Mrs. Bennet", "Mrs. Bennet": "Mr. Bennet"},
        )
        report = qc.check_book(
            {"chapters": [chapter(1, "Mr. Bennet spoke to Mrs. Bennet.")]},
            {"chapters": [chapter(1, "Mrs. Bennet spoke to Mr. Bennet.")]},
        )
        assert not [f for f in report.all_findings if f.kind == "residual_name"]


class TestAnAliasMustBeAName:
    """A real cast list offered "her husband" and "Wickham" as aliases.

    Mapping the first to "Mrs. Bennet" would put a name where a relationship
    belongs; the second to "Miss Wickham" produced "Miss Miss Wickham" twice in
    one book. Between them they accounted for 23 of 24 review findings.
    """

    @pytest.mark.parametrize(
        "alias",
        ["her husband", "his wife", "the old lady", "her friend", "my aunt", "their father"],
    )
    def test_a_relationship_is_not_a_name(self, svc, alias):
        assert svc._unsafe_alias(alias, "Mrs. Bennet")

    def test_a_proper_noun_inside_one_does_not_rescue_it(self, svc):
        """'my uncle Philips' is better served by the term map."""
        assert svc._unsafe_alias("my uncle Philips", "Mrs. Philips")

    def test_a_name_must_not_contain_itself(self, svc):
        """'Wickham' -> 'Miss Wickham' adds a title, and doubles an existing one."""
        assert svc._unsafe_alias("Wickham", "Miss Wickham")
        assert svc._unsafe_alias("Darcy", "Mrs. Darcy")

    @pytest.mark.parametrize(
        ("alias", "target"),
        [("Lizzy", "Edmund"), ("Mrs. Collins", "Charles Collins"), ("Kitty", "Charles")],
    )
    def test_a_real_name_is_kept(self, svc, alias, target):
        assert not svc._unsafe_alias(alias, target)

    def test_the_kinship_aliases_never_reach_the_map(self, svc):
        characters = cast(("Mr. Bennet", Gender.MALE, ["her husband", "their father"]))
        expanded = svc._expand_name_map_with_aliases({"Mr. Bennet": "Mrs. Bennet"}, characters)
        assert "her husband" not in expanded
        assert "their father" not in expanded


class TestNoDoubledTitle:
    def test_a_replacement_never_repeats_the_word_before_it(self, svc):
        """Belt and braces: even a bad map entry must not reach the page."""
        out = svc._apply_name_map(
            "between himself and Miss Wickham was",
            {"Wickham": "Miss Wickham"},
            source_text="between herself and Mr. Wickham was",
        )
        assert "Miss Miss" not in out


class TestASwappedNameIsNotAMissedOne:
    """The last chapter says "talked of Mrs. Darcy", meaning Elizabeth.

    A swap turns her into Mr. Darcy -- which is also a map key, so the correct
    sentence was reported as an un-renamed one. Acting on that would have put
    the error in.
    """

    MAP = {"Mr. Darcy": "Mrs. Darcy", "Mr. Bingley": "Miss Bingley"}

    def findings(self, source, output):
        report = QCService(TransformType.GENDER_SWAP, name_map=self.MAP).check_book(
            {"chapters": [chapter(1, source)]}, {"chapters": [chapter(1, output)]}
        )
        return [f for f in report.all_findings if f.kind == "residual_name"]

    def test_a_name_the_transform_produced_is_not_flagged(self):
        assert not self.findings(
            "she visited Mrs. Bingley, and talked of Mrs. Darcy.",
            "he visited Mr. Bingley, and talked of Mr. Darcy.",
        )

    def test_a_name_genuinely_left_alone_is_still_flagged(self):
        found = self.findings("she saw Mr. Darcy there.", "he saw Mr. Darcy there.")
        assert len(found) == 1
        assert "Mr. Darcy" in found[0].detail

    def test_another_name_in_the_paragraph_does_not_implicate_it(self):
        """The old check asked only whether *some* mapped name was in the source."""
        assert not self.findings(
            "she wrote to Mr. Bingley about Mrs. Darcy.",
            "he wrote to Miss Bingley about Mr. Darcy.",
        )
