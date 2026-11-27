# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Jason Huff
"""The book decides who is married, and when. The cast does not.

A gender swap turns "Mr. Darcy" into a woman, and English then wants to know
something the source never said: "Miss" or "Mrs."? The answer changes as the
book goes on, and the transform keeps a timeline for it.

What fed that timeline was the cast, and the cast is written by a model. It
calls one man "Mr. Darcy" in one run, "Fitzwilliam Darcy" in the next and "Mr.
Fitzwilliam Darcy" in a third, and it lists a bride under her married name as
readily as a wife of twenty years. Fifteen real casts of Pride and Prejudice
were checked against the book: the old rule gave eight men the right opening
state and wedding 65 times out of 120, and never once gave Darcy or Bingley a
correct entry. Darcy was married because of Lady Anne Darcy, his mother;
Wickham because of Old Wickham, his father; Collins because Charlotte was
listed as a Collins from page one, so he was "Mrs. Collins" when he proposed
to Elizabeth.

And where the timeline was right, the model was never told. The prompt was
built once for the whole book, and the step that follows the model only
rewrites a name the model left alone.
"""

import asyncio
import json
import pathlib

import pytest

from src.models.character import Character, CharacterAnalysis, Gender
from src.models.transformation import TransformType
from src.services.character_state import (
    _SINGLE_LIFE,
    detect_marital_changes,
    initial_marital_state,
    marital_states,
    marital_title_maps,
)
from src.services.transform_service import TransformService


def man(name, *titles):
    return Character(name=name, gender=Gender.MALE, pronouns={}, titles=list(titles))


def woman(name, *titles):
    return Character(name=name, gender=Gender.FEMALE, pronouns={}, titles=list(titles))


def book(chapters):
    """{number: text | [paragraph, ...]}"""
    out = []
    for number, body in sorted(chapters.items()):
        paragraphs = [body] if isinstance(body, str) else list(body)
        out.append({"number": number, "paragraphs": [{"sentences": [p]} for p in paragraphs]})
    return {"chapters": out}


def a_single_life(surname, chapters=15, per_chapter=3):
    """A man named often, over many chapters, before any Mrs. of his name."""
    return {
        n: [f"Mr. {surname} called again." for _ in range(per_chapter)]
        for n in range(1, chapters + 1)
    }


def titles_for(cast, the_book):
    initial = initial_marital_state(cast, the_book)
    return marital_title_maps(cast, detect_marital_changes(the_book, cast), initial)


class TestALongSingleLifeIsNotOverruledByTheCast:
    """Collins: 104 mentions as a bachelor, and a cast that calls Charlotte a Collins."""

    BOOK = book({**a_single_life("Collins"), 28: ["They arrived.", "Mrs. Collins welcomed her."]})

    @pytest.mark.parametrize(
        "bride",
        [
            woman("Charlotte Collins", "Mrs."),
            woman("Charlotte Collins", "Miss", "Mrs."),
            woman("Charlotte Collins"),
            woman("Mrs. Collins"),
            woman("Charlotte Lucas Collins", "Miss"),
        ],
        ids=lambda c: f"{c.name} {c.titles}",
    )
    def test_he_is_miss_until_the_wedding_however_she_is_listed(self, bride):
        base, timeline = titles_for([man("Mr. Collins", "Mr."), bride], self.BOOK)
        assert base == {"Mr. Collins": "Miss Collins"}
        assert timeline == [(28, 1, {"Mr. Collins": "Mrs. Collins"})]

    def test_the_verdict_says_what_it_rests_on(self):
        state = marital_states(
            self.BOOK, [man("Mr. Collins", "Mr."), woman("Charlotte Collins", "Mrs.")]
        )["Mr. Collins"]
        assert (state.opens, state.wedding) == ("unmarried", (28, 1))
        assert state.before_first_mrs == 45 and state.wife_in_cast is True
        assert "named 45 times before the first Mrs." in state.reason
        assert "Mrs. Collins" in state.evidence
        assert state.to_dict()["wedding"] == [28, 1]


class TestSharingASurnameIsNotBeingMarried:
    """Darcy's mother, and Wickham's father, each made a bachelor a husband."""

    def test_a_mother_who_is_a_lady_is_not_a_wife(self):
        cast = [man("Mr. Darcy", "Mr."), woman("Lady Anne Darcy", "Lady")]
        base, _ = titles_for(cast, book({1: "Mr. Darcy was proud."}))
        assert base == {"Mr. Darcy": "Miss Darcy"}

    def test_a_father_with_no_title_is_not_a_wife(self):
        cast = [man("Mr. Wickham", "Mr."), man("Old Wickham")]
        base, _ = titles_for(cast, book({1: "Mr. Wickham bowed."}))
        assert base == {"Mr. Wickham": "Miss Wickham"}

    def test_an_untitled_sister_is_not_a_wife(self):
        cast = [man("Mr. Bingley", "Mr."), woman("Caroline Bingley")]
        base, _ = titles_for(cast, book({1: "Mr. Bingley smiled."}))
        assert base == {"Mr. Bingley": "Miss Bingley"}

    def test_a_wife_the_cast_calls_mrs_still_is_one(self):
        cast = [man("Mr. Hurst", "Mr."), woman("Louisa Hurst", "Mrs.")]
        the_book = book({3: ["Mr. Hurst merely looked the gentleman.", "Mrs. Hurst sang."]})
        base, timeline = titles_for(cast, the_book)
        assert base == {"Mr. Hurst": "Mrs. Hurst"} and timeline == []


class TestTheEntryIsUnderTheNameTheTextUses:
    """However the cast names him, the book says "Mr. Darcy"."""

    BOOK = book({**a_single_life("Darcy"), 61: "She visited Mrs. Darcy."})

    @pytest.mark.parametrize(
        "him",
        [
            man("Mr. Darcy", "Mr."),
            man("Fitzwilliam Darcy", "Mr."),
            man("Fitzwilliam Darcy"),
            man("Mr. Fitzwilliam Darcy", "Mr."),
        ],
        ids=lambda c: f"{c.name} {c.titles}",
    )
    def test_every_way_the_cast_names_him_gives_one_entry(self, him):
        base, timeline = titles_for([him], self.BOOK)
        assert base == {"Mr. Darcy": "Miss Darcy"}
        assert timeline == [(61, 0, {"Mr. Darcy": "Mrs. Darcy"})]

    def test_duplicates_of_him_do_not_multiply_it(self):
        cast = [
            man("Mr. Fitzwilliam Darcy", "Mr."),
            man("The late Mr. Darcy", "Mr."),
            man("Mr. Darcy (the late)", "Mr."),
            man("Mr. Darcy's father"),
        ]
        base, _ = titles_for(cast, self.BOOK)
        assert base == {"Mr. Darcy": "Miss Darcy"}

    def test_a_given_name_after_the_title_is_not_a_surname(self):
        """ "Mr. Fitzwilliam Darcy" is not a mention of Colonel Fitzwilliam."""
        cast = [man("Colonel Fitzwilliam", "Colonel"), man("Fitzwilliam Darcy", "Mr.")]
        the_book = book({1: "It was signed Mr. Fitzwilliam Darcy.", 2: "Mr. Darcy bowed."})
        base, _ = titles_for(cast, the_book)
        assert base == {"Mr. Darcy": "Miss Darcy"}

    def test_a_man_the_book_never_titles_gets_no_entry(self):
        cast = [man("Sir William Lucas", "Sir"), woman("Charlotte Lucas", "Miss")]
        assert titles_for(cast, book({1: "Sir William and Miss Lucas came."})) == ({}, [])

    def test_a_bare_given_name_is_not_read_as_a_family(self):
        cast = [man("John"), man("John Knightley", "Mr.")]
        base, _ = titles_for(cast, book({1: "Mr. John Knightley came in."}))
        assert base == {}


class TestACoupleMarriedWhenWeMeetThem:
    def test_a_wife_named_a_chapter_later_is_still_a_wife(self):
        """Bennet: eight mentions before the book says "Mrs. Bennet"."""
        cast = [man("Mr. Bennet", "Mr."), woman("Mrs. Bennet", "Mrs.")]
        the_book = book({1: ["Mr. Bennet replied."] * 8, 2: "Mrs. Bennet deigned no reply."})
        base, timeline = titles_for(cast, the_book)
        assert base == {"Mr. Bennet": "Mrs. Bennet"} and timeline == []

    def test_the_line_between_the_two_is_where_it_was_measured(self):
        cast = [man("Mr. Bennet", "Mr."), woman("Mrs. Bennet", "Mrs.")]

        def opens(mentions):
            the_book = book({1: ["Mr. Bennet replied."] * mentions, 2: "Mrs. Bennet came."})
            return marital_states(the_book, cast)["Mr. Bennet"].opens

        assert opens(_SINGLE_LIFE - 1) == "married"
        assert opens(_SINGLE_LIFE) == "unmarried"
        assert 12 < _SINGLE_LIFE < 37, "outside the gap the five novels left"


class TestWhenTheBookNeverPrintsHer:
    """The cast is the only witness, and it has to say "Mrs. S" outright."""

    BOOK = book({1: ["Mr. Mason arrived from Jamaica."] * 5, 2: ["Mr. Woodhouse fretted."] * 5})

    def test_a_sister_listed_under_her_maiden_name_does_not_marry_her_brother(self):
        """Jane Eyre: Bertha Mason is a Mrs. -- Mrs. Rochester."""
        cast = [man("Mr. Mason", "Mr."), woman("Bertha Antoinetta Mason", "Mrs.")]
        assert marital_states(self.BOOK, cast)["Mr. Mason"].opens == "unmarried"

    def test_a_wife_named_as_one_makes_a_widower_mrs(self):
        """Emma: Mrs. Woodhouse is dead before page one, and a widow is still Mrs."""
        cast = [man("Mr. Woodhouse", "Mr."), woman("Mrs. Woodhouse", "Mrs.")]
        assert marital_states(self.BOOK, cast)["Mr. Woodhouse"].opens == "married"


class TestSomebodyElsesWife:
    """Emma: Mr. Knightley's brother is married, so the book prints "Mrs. Knightley"."""

    def knightley(self, mrs_mentions_after):
        chapters = a_single_life("Knightley")  # 45 mentions, chapters 1 to 15
        chapters[16] = ["You must know, my dear Mrs. Knightley, that we are not sure."]
        chapters[17] = ["Mr. Knightley walked in."] * 230
        chapters[18] = ["Mrs. Knightley smiled."] * mrs_mentions_after
        cast = [man("Mr. George Knightley", "Mr."), woman("Isabella Knightley", "Mrs.")]
        return marital_states(book(chapters), cast)["Mr. Knightley"]

    def test_a_mrs_named_four_times_against_230_of_him_is_not_his_wedding(self):
        state = self.knightley(mrs_mentions_after=3)
        assert (state.opens, state.wedding) == ("unmarried", None)
        assert "someone else's wife" in state.reason

    def test_a_wife_who_is_named_as_a_wife_would_be_still_marks_one(self):
        state = self.knightley(mrs_mentions_after=40)
        assert (state.opens, state.wedding) == ("unmarried", (16, 0))

    def test_a_wedding_on_the_last_page_is_still_a_wedding(self):
        """Darcy: one "Mrs. Darcy", and two more of him after it."""
        chapters = {**a_single_life("Darcy"), 61: ["She visited Mrs. Darcy.", "Mr. Darcy smiled."]}
        state = marital_states(book(chapters), [man("Fitzwilliam Darcy", "Mr.")])["Mr. Darcy"]
        assert state.wedding == (61, 0)

    def test_it_does_not_unmarry_a_man_whose_wife_the_cast_knows(self):
        """Only a wedding is undone this way; a marriage already made is left alone."""
        chapters = {
            1: ["Mr. Hurst said nothing.", "Mrs. Hurst sang."],
            2: ["Mr. Hurst slept."] * 60,
        }
        cast = [man("Mr. Hurst", "Mr."), woman("Louisa Hurst", "Mrs.")]
        assert marital_states(book(chapters), cast)["Mr. Hurst"].opens == "married"


class TestOnTheRepoSampleAndItsRealCast:
    """Six chapters of the real book, and a cast a real run produced."""

    @pytest.fixture(scope="class")
    def states(self):
        from src.app import Application
        from src.container import ApplicationContext

        context = ApplicationContext()
        context.initialize()
        root = pathlib.Path(__file__).parent
        sample = root.parent / "books" / "texts" / "pride-prejudice-sample.txt"
        parsed = asyncio.run(
            Application(context=context).get_service("parser").process(str(sample))
        ).to_dict()
        cast = CharacterAnalysis.from_dict(
            json.loads((root / "fixtures" / "pride-and-prejudice-cast.json").read_text())
        ).characters
        return marital_states(parsed, cast)

    def test_the_married_men_open_married(self, states):
        assert states["Mr. Bennet"].opens == "married"
        assert states["Mr. Hurst"].opens == "married"

    def test_the_bachelors_open_unmarried(self, states):
        assert states["Mr. Darcy"].opens == "unmarried"
        assert states["Mr. Bingley"].opens == "unmarried"

    def test_nobody_marries_in_the_first_six_chapters(self, states):
        assert [s.name for s in states.values() if s.wedding] == []

    def test_no_entry_is_made_from_a_description(self, states):
        assert all(name.count(" ") == 1 for name in states), sorted(states)


# --------------------------------------------------------------------------- #
# The model is told
# --------------------------------------------------------------------------- #


class _Paragraph:
    def __init__(self, text):
        self.text = text

    def get_text(self):
        return self.text


def paragraphs(*texts):
    return [_Paragraph(t) for t in texts]


@pytest.fixture
def service():
    s = TransformService.__new__(TransformService)
    s.set_title_timeline([(49, 51, {"Mr. Wickham": "Mrs. Wickham"})])
    return s


SWAP = {"transform_type": TransformType.GENDER_SWAP, "name_map": {}}
MAP = {"Mr. Wickham": "Miss Wickham", "Mr. Bennet": "Mrs. Bennet", "Lydia": "Lyle"}


class TestThePromptCarriesTheTitleAsItStands:
    def test_before_the_wedding_he_is_miss(self, service):
        batch = paragraphs("Mr. Wickham came in.", "Mr. Bennet rose.")
        context = service._context_at(SWAP, 15, 0, batch, MAP)
        assert '- "Mr. Wickham" is "Miss Wickham"' in context["titles_note"]
        assert context["name_map"]["Mr. Wickham"] == "Miss Wickham"

    def test_after_it_he_is_mrs(self, service):
        batch = paragraphs("Mr. Wickham came in.")
        context = service._context_at(SWAP, 52, 0, batch, MAP)
        assert '- "Mr. Wickham" is "Mrs. Wickham"' in context["titles_note"]
        assert context["name_map"]["Mr. Wickham"] == "Mrs. Wickham"

    def test_a_wedding_inside_the_batch_is_placed_by_its_marker(self, service):
        batch = paragraphs(*["Mr. Wickham was mentioned."] * 4)
        note = service._context_at(SWAP, 49, 49, batch, MAP)["titles_note"]
        assert (
            '- "Mr. Wickham" is "Miss Wickham" up to [[P2]], and "Mrs. Wickham" from [[P3]] on'
            in note
        )

    def test_only_the_men_in_this_batch_are_listed(self, service):
        note = service._context_at(SWAP, 15, 0, paragraphs("Mr. Bennet rose."), MAP)["titles_note"]
        assert "Mr. Bennet" in note and "Wickham" not in note

    def test_a_rename_is_not_a_title(self, service):
        note = service._context_at(SWAP, 15, 0, paragraphs("Lydia laughed."), MAP)["titles_note"]
        assert note == ""

    def test_the_base_map_is_not_altered(self, service):
        service._context_at(SWAP, 52, 0, paragraphs("Mr. Wickham came in."), MAP)
        assert MAP["Mr. Wickham"] == "Miss Wickham"

    @pytest.mark.parametrize(
        "kind", [TransformType.ALL_FEMALE, TransformType.ALL_MALE, TransformType.NONBINARY]
    )
    def test_other_transforms_get_their_context_back_untouched(self, service, kind):
        context = {"transform_type": kind, "name_map": MAP}
        assert service._context_at(context, 52, 0, paragraphs("Mr. Wickham."), MAP) is context

    def test_the_note_reaches_the_prompt(self, service):
        batch = paragraphs("Mr. Wickham came in.")
        context = {
            **service._context_at(SWAP, 15, 0, batch, MAP),
            "rules": {},
            "character_mappings": {},
            "characters": None,
        }
        system = service._create_batch_transform_prompt(batch, context, 1)["system"]
        assert "TITLES AT THIS POINT IN THE BOOK" in system
        assert '"Mr. Wickham" is "Miss Wickham"' in system

    def test_the_transform_asks_for_it_per_batch(self):
        import inspect

        source = inspect.getsource(TransformService._transform_single_chapter)
        assert "self._context_at(" in source
