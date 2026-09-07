"""Tests for the editorial-decision scanner.

The nonbinary transform meets words English has no neutral form for. These
tests pin down what gets handed to a person, what does not, and that a filled
sheet is applied where it says.
"""

import pytest

from src.services.decision_service import DecisionService


def book(paragraphs, number=1):
    return {
        "chapters": [{"number": number, "paragraphs": [{"sentences": [p]} for p in paragraphs]}]
    }


@pytest.fixture
def service():
    return DecisionService("nonbinary")


class TestWhatNeedsARuling:
    def test_a_bare_vocative_is_surfaced(self, service):
        report = service.scan(book(['"Indeed, sir, I have not."']))
        assert report.total == 1
        assert report.decisions[0].word == "sir"

    @pytest.mark.parametrize("text", ["Sir William Lucas bowed.", "She met Sir Lewis de Bourgh."])
    def test_a_title_with_a_name_is_not_a_decision(self, service, text):
        assert service.scan(book([text])).total == 0

    def test_maam_is_found_with_either_apostrophe(self, service):
        assert service.scan(book(["“Yes, ma’am.”"])).total == 1
        assert service.scan(book(["“Yes, ma'am.”"])).total == 1

    def test_a_sense_rule_removes_the_need_to_rule(self, service):
        """ "music master" is settled; a bare "master" is not."""
        assert service.scan(book(["the music master called"])).total == 0
        assert service.scan(book(["an express came for master"])).total == 1

    @pytest.mark.parametrize("key", ["gender_swap", "all_male", "all_female"])
    def test_other_transforms_need_no_rulings(self, key):
        """A swap turns "sir" into "madam" and is finished."""
        assert DecisionService(key).scan(book(['"Indeed, sir."'])).total == 0

    def test_two_sites_in_one_paragraph_are_both_found(self, service):
        report = service.scan(book(['"Yes, sir," they said. "No, sir."']))
        assert report.total == 2


class TestFrames:
    @pytest.mark.parametrize(
        "text,frame",
        [
            ('"Dear sir,', "letter salutation"),
            ('"My dear sir,', "letter salutation"),
            ('"Never, sir."', "short reply"),
            ('"You saw me dance, I believe, sir."', "clause-final tag"),
            ('"Indeed, sir, I have not the least intention."', "clause-medial"),
        ],
    )
    def test_the_frame_is_read_off_the_context(self, service, text, frame):
        assert service.scan(book([text])).decisions[0].frame == frame

    def test_a_salutation_is_not_offered_deletion(self, service):
        """Dropping the address out of "Dear sir," leaves "Dear," """
        options = service.scan(book(['"Dear sir,'])).decisions[0].options
        assert "delete" not in options
        assert "ser" in options

    def test_deleting_takes_one_comma_with_it(self, service):
        options = service.scan(book(['"Indeed, sir, I have not."'])).decisions[0].options
        assert "Indeed, I have not" in options["delete"]

    def test_deleting_a_trailing_tag_takes_the_comma_before_it(self, service):
        options = service.scan(book(['"You saw me dance, sir."'])).decisions[0].options
        assert "You saw me dance." in options["delete"]


class TestApplying:
    def test_an_option_key_is_applied(self, service):
        data = book(['"Indeed, sir, I have not."'])
        sheet = service.scan(data).to_dict()
        sheet["decisions"][0]["ruling"] = "ser"
        data, applied, problems = service.apply(data, sheet)
        assert applied == 1 and not problems
        assert "Indeed, Ser, I have not." in data["chapters"][0]["paragraphs"][0]["sentences"][0]

    def test_free_text_replaces_the_word(self, service):
        data = book(['"Indeed, sir, I have not."'])
        sheet = service.scan(data).to_dict()
        sheet["decisions"][0]["ruling"] = "cousin"
        data, applied, _ = service.apply(data, sheet)
        assert "Indeed, cousin, I have not." in data["chapters"][0]["paragraphs"][0]["sentences"][0]

    def test_keep_and_null_change_nothing(self, service):
        original = '"Indeed, sir, I have not."'
        data = book([original])
        sheet = service.scan(data).to_dict()
        sheet["decisions"][0]["ruling"] = "keep"
        data, applied, _ = service.apply(data, sheet)
        assert applied == 0
        assert data["chapters"][0]["paragraphs"][0]["sentences"][0] == original

    def test_two_sites_in_one_paragraph_do_not_displace_each_other(self, service):
        data = book(['"Yes, sir," they said. "No, sir."'])
        sheet = service.scan(data).to_dict()
        sheet["decisions"][0]["ruling"] = "delete"
        sheet["decisions"][1]["ruling"] = "cousin"
        data, applied, problems = service.apply(data, sheet)
        assert applied == 2 and not problems
        assert data["chapters"][0]["paragraphs"][0]["sentences"][0] == (
            '"Yes," they said. "No, cousin."'
        )

    def test_a_site_that_moved_is_reported_not_guessed(self, service):
        data = book(['"Indeed, sir, I have not."'])
        sheet = service.scan(data).to_dict()
        sheet["decisions"][0]["ruling"] = "ser"
        data["chapters"][0]["paragraphs"][0]["sentences"] = ["nothing to match here"]
        _, applied, problems = service.apply(data, sheet)
        assert applied == 0
        assert problems and "not found" in problems[0]


class TestEstimate:
    def test_it_counts_from_raw_text(self, service):
        counts = service.estimate('"Indeed, sir." "Yes, madam." "No, sir."')
        assert counts == {"sir": 2, "madam": 1}

    def test_a_settled_sense_is_not_counted(self, service):
        assert service.estimate("the music master called") == {}

    @pytest.mark.parametrize("key", ["gender_swap", "all_male", "all_female"])
    def test_other_transforms_estimate_nothing(self, key):
        assert DecisionService(key).estimate('"Indeed, sir."') == {}
