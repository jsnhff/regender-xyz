"""A short cast should not look like a short book.

Successive analyses of Pride and Prejudice found 89, 91, 88, 86, 85, 77, 80 and
82 characters. The same file, the same prompt, a fourteen-character spread, and
the gender split moving with it.

The dominant cause was a reply that could not be parsed. The parser has five
strategies and then a fallback that returns {"characters": []}, and the caller
treated that as a successful extraction of nobody -- so a refusal, a preamble, a
truncated object and an empty string all ended the retry loop as a success,
because a fallback is not an exception. The book is eighteen chunks; one silent
chunk costs whoever first appears in it, three to eight people.

The second cause deleted characters outright. Asked whether a group of similar
names is one person, every answer other than "yes" returned only the first
member of the group and dropped the rest. So a correct "Jane Bennet and Lydia
Bennet are different people" removed Lydia from the book, and so did a 529 from
the provider, and so did a reply in an unexpected shape. Worse, a reply that
simply omitted the field defaulted to "yes" and merged people nobody had said
were one.
"""

import asyncio
import json
import logging

import pytest

from src.services.character_service import CharacterService


def service(replies):
    """A service whose next completions are the given replies, in order."""
    svc = CharacterService.__new__(CharacterService)
    svc.logger = logging.getLogger("test")
    svc.extraction_config = {
        "chunk_size": 32000,
        "temperature": 0.0,
        "max_retries": 3,
        "retry_backoff": 0,
    }
    svc.merging_config = {"temperature": 0.0}
    svc.empty_chunks = []
    svc.calls = []

    async def _complete(prompt, temperature=0.0):
        svc.calls.append(prompt)
        return replies[min(len(svc.calls) - 1, len(replies) - 1)]

    svc._complete_with_retry = _complete
    return svc


class TestAnUnparseableReplyIsRetried:
    GOOD = json.dumps({"characters": [{"name": "Elizabeth Bennet", "gender": "female"}]})

    @pytest.mark.parametrize(
        "bad",
        [
            "I'm sorry, I can't help with that.",
            "Here are the characters I found:",
            '{"characters": [{"name": "Eliz',
            "",
            "Mocked response",
        ],
    )
    def test_it_does_not_count_as_a_successful_extraction(self, bad):
        """Each of these used to end the loop with one call and no characters."""
        svc = service([bad, bad, self.GOOD])
        result = asyncio.run(svc._extract_from_chunk("some text", 0))
        assert [c["name"] for c in result] == ["Elizabeth Bennet"]
        assert len(svc.calls) == 3, "it should have retried"

    def test_a_reply_naming_nobody_is_also_retried(self):
        """A chunk of a novel holds people; an empty list is a reply gone wrong."""
        svc = service([json.dumps({"characters": []}), self.GOOD])
        result = asyncio.run(svc._extract_from_chunk("some text", 0))
        assert [c["name"] for c in result] == ["Elizabeth Bennet"]
        assert len(svc.calls) == 2

    def test_a_chunk_that_stays_empty_is_recorded(self):
        """Silence was the problem: the cast was short and nothing said why."""
        svc = service(["I'm sorry, I can't help with that."])
        result = asyncio.run(svc._extract_from_chunk("some text", 7))
        assert result == []
        assert svc.empty_chunks == [7]
        assert len(svc.calls) == 3

    def test_a_good_reply_costs_one_call(self):
        svc = service([self.GOOD])
        asyncio.run(svc._extract_from_chunk("some text", 0))
        assert len(svc.calls) == 1


class TestTheParserStillHasItsFallbackForEveryoneElse:
    """Only extraction asks for strict parsing."""

    def test_lenient_by_default(self):
        svc = service(["x"])
        assert svc._parse_json_response("not json at all") == {"characters": []}

    def test_strict_when_asked(self):
        svc = service(["x"])
        with pytest.raises(ValueError):
            svc._parse_json_response("not json at all", strict=True)


class TestNotMergingIsNotDeleting:
    GROUP = [
        {"name": "Jane Bennet", "gender": "female"},
        {"name": "Lydia Bennet", "gender": "female"},
        {"name": "Mary Bennet", "gender": "female"},
    ]

    def names(self, svc, group):
        return sorted(c.name for c in asyncio.run(svc._merge_group_with_llm(group)))

    def test_a_correct_no_keeps_everyone(self):
        """ "Jane and Lydia Bennet are different people" removed Lydia."""
        svc = service([json.dumps({"is_same_person": False})])
        assert self.names(svc, self.GROUP) == ["Jane Bennet", "Lydia Bennet", "Mary Bennet"]

    def test_a_provider_error_keeps_everyone(self):
        svc = CharacterService.__new__(CharacterService)
        svc.logger = logging.getLogger("test")
        svc.merging_config = {"temperature": 0.0}

        async def _boom(prompt, temperature=0.0):
            raise RuntimeError("529 overloaded")

        svc._complete_with_retry = _boom
        assert self.names(svc, self.GROUP) == ["Jane Bennet", "Lydia Bennet", "Mary Bennet"]

    def test_an_unexpected_shape_keeps_everyone(self):
        svc = service([json.dumps(["just", "a", "list"])])
        result = asyncio.run(svc._merge_group_with_llm(self.GROUP))
        assert len(result) == 3

    def test_an_empty_array_keeps_everyone(self):
        svc = service([json.dumps([])])
        assert len(asyncio.run(svc._merge_group_with_llm(self.GROUP))) == 3

    def test_an_unanswered_question_does_not_merge(self):
        """The field defaulted to True, so a reply that omitted it collapsed the
        group -- merging people the model had not said were one."""
        svc = service([json.dumps({"canonical_name": "Jane Bennet"})])
        assert len(asyncio.run(svc._merge_group_with_llm(self.GROUP))) == 3

    def test_but_a_real_yes_still_merges(self):
        svc = service(
            [
                json.dumps(
                    {
                        "is_same_person": True,
                        "canonical_name": "Lydia Wickham",
                        "gender": "female",
                        "aliases": ["Lydia Bennet"],
                    }
                )
            ]
        )
        result = asyncio.run(
            svc._merge_group_with_llm(
                [
                    {"name": "Lydia Bennet", "gender": "female"},
                    {"name": "Lydia Wickham", "gender": "female"},
                ]
            )
        )
        assert [c.name for c in result] == ["Lydia Wickham"]
