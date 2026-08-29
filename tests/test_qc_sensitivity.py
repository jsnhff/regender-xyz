"""Mutation test: QC must catch every class of transform error we know of.

A clean chapter is transformed correctly, then one realistic error is injected
at a time. Each must produce at least one finding. This guards the detection
rate itself — a future change that quietly stops catching dropped paragraphs
would still pass the per-check unit tests, but not this.
"""

import copy

import pytest

from src.models.transformation import TransformType
from src.services.qc_service import QCService

NAME_MAP = {"Lizzy": "Liam"}

SOURCE = [
    "It is a truth universally acknowledged, that a single man in possession of a "
    "good fortune must be in want of a wife.",
    "“My dear Mr. Bennet,” said his lady to him one day, “have you heard that "
    "Netherfield Park is let at last?”",
    "Mr. Bennet made no answer.",
    "This was invitation enough.",
    "“I will send a few lines by you to assure him of my hearty consent to his "
    "marrying whichever he chooses of the girls--though I must throw in a good "
    "word for my little Lizzy.”",
    "But you are always giving _her_ the preference, and Lizzy has something more "
    "of quickness than her sisters.",
]

# A correct gender_swap of the above, written naturally rather than by applying
# the term map, so the baseline is genuinely independent of the code under test.
TRANSFORMED = [
    "It is a truth universally acknowledged, that a single woman in possession of a "
    "good fortune must be in want of a husband.",
    "“My dear Mrs. Bennet,” said her husband to her one day, “have you heard that "
    "Netherfield Park is let at last?”",
    "Mrs. Bennet made no answer.",
    "This was invitation enough.",
    "“I will send a few lines by you to assure her of my hearty consent to her "
    "marrying whichever she chooses of the boys--though I must throw in a good "
    "word for my little Liam.”",
    "But you are always giving _him_ the preference, and Liam has something more "
    "of quickness than his brothers.",
]


def book(paragraphs):
    return {
        "metadata": {"title": "Test"},
        "chapters": [{"number": 1, "title": "Chapter 1", "paragraphs": list(paragraphs)}],
    }


@pytest.fixture(scope="module")
def qc():
    return QCService(TransformType.GENDER_SWAP, name_map=NAME_MAP)


def swap_in(index, old, new):
    def mutation(paragraphs):
        paragraphs[index] = paragraphs[index].replace(old, new, 1)

    return mutation


MUTATIONS = [
    ("noun reverted", swap_in(0, "husband", "wife")),
    ("pronoun reverted", swap_in(1, "said her husband", "said his husband")),
    ("honorific reverted", swap_in(1, "Mrs. Bennet", "Mr. Bennet")),
    ("possessive left behind", swap_in(4, "her marrying", "his marrying")),
    ("half a pair landed wrong", swap_in(1, "her husband", "her wife")),
    ("plural noun missed", swap_in(5, "his brothers", "his sisters")),
    ("italicised pronoun missed", swap_in(5, "_him_", "_her_")),
    ("paragraph left untransformed", lambda p: p.__setitem__(2, SOURCE[2])),
    ("paragraph truncated", lambda p: p.__setitem__(4, p[4][:60])),
    ("paragraph deleted", lambda p: p.pop(2)),
    ("paragraph emptied", lambda p: p.__setitem__(2, "")),
    ("character name not renamed", swap_in(4, "Liam", "Lizzy")),
    (
        "sentence hallucinated",
        lambda p: p.__setitem__(3, p[3] + " She smiled at the thought and said no more."),
    ),
]


def test_baseline_is_clean(qc):
    """Every mutation below is only meaningful if the unmutated pair passes."""
    assert qc.check_book(book(SOURCE), book(TRANSFORMED)).all_findings == []


@pytest.mark.parametrize("label,mutation", MUTATIONS, ids=[m[0] for m in MUTATIONS])
def test_mutation_is_detected(qc, label, mutation):
    paragraphs = copy.deepcopy(TRANSFORMED)
    mutation(paragraphs)
    assert paragraphs != TRANSFORMED, f"{label}: mutation did not change anything"

    findings = qc.check_book(book(SOURCE), book(paragraphs)).all_findings
    assert findings, f"{label} went undetected"
