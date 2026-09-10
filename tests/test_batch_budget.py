"""A batch must not be asked for more than it is allowed to write back.

Batches were sized against the context window -- 120k tokens, whole chapters
at a time -- while the reply was capped at 4096. A transform returns roughly
what it was given, so seven of Pride and Prejudice's sixty-one chapters asked
for more than they could receive. A truncated reply loses its paragraph
markers, and the whole chapter then falls back to one call per paragraph, each
re-sending the character instructions. The five golden chapters were all small
enough to never show it.
"""

import pytest

from src.services.transform_service import TransformService as T


class P:
    def __init__(self, text):
        self._t = text

    def get_text(self):
        return self._t


def para(tokens):
    """A paragraph of roughly `tokens` tokens."""
    return P("word " * (tokens * 4 // 5))


class TestTheCap:
    def test_a_big_batch_is_split(self):
        batches = T._cap_batches_by_reply([[para(2000) for _ in range(10)]])
        assert len(batches) > 1

    def test_no_batch_exceeds_the_budget(self):
        batches = T._cap_batches_by_reply([[para(2000) for _ in range(10)]])
        for batch in batches:
            assert sum(T._rough_tokens(p.get_text()) for p in batch) <= T.MAX_REPLY_TOKENS

    def test_a_small_batch_is_left_alone(self):
        original = [[para(100), para(100)]]
        assert T._cap_batches_by_reply(original) == original

    def test_no_paragraph_is_lost(self):
        original = [[para(1500) for _ in range(9)], [para(100)]]
        before = [p for b in original for p in b]
        after = [p for b in T._cap_batches_by_reply(original) for p in b]
        assert after == before, "splitting must preserve order and count"

    def test_a_single_oversized_paragraph_is_kept_whole(self):
        """Splitting one paragraph would break the text; the budget stretches."""
        big = para(9000)
        batches = T._cap_batches_by_reply([[big]])
        assert batches == [[big]]
        assert T._reply_budget([big]) >= T._rough_tokens(big.get_text())

    def test_an_empty_batch_list_is_fine(self):
        assert T._cap_batches_by_reply([]) == []


class TestTheReplyBudget:
    def test_it_leaves_room_to_grow(self):
        """A swap can be longer than its source: 'he' becomes 'she'."""
        p = para(1000)
        assert T._reply_budget([p]) > T._rough_tokens(p.get_text())

    def test_it_never_exceeds_the_model_ceiling(self):
        assert T._reply_budget([para(100_000)]) == T.MAX_OUTPUT_TOKENS

    def test_a_tiny_batch_still_gets_workable_room(self):
        assert T._reply_budget([para(1)]) >= 1024

    def test_a_capped_batch_always_fits_its_budget(self):
        for size in (500, 1500, 3000, 6000):
            for batch in T._cap_batches_by_reply([[para(size) for _ in range(12)]]):
                incoming = sum(T._rough_tokens(p.get_text()) for p in batch)
                assert incoming <= T._reply_budget(batch)


@pytest.mark.parametrize("count", [1, 5, 50, 200])
def test_the_cap_holds_for_any_chapter_shape(count):
    batches = T._cap_batches_by_reply([[para(120) for _ in range(count)]])
    assert sum(len(b) for b in batches) == count
    for batch in batches:
        assert sum(T._rough_tokens(p.get_text()) for p in batch) <= T.MAX_REPLY_TOKENS
