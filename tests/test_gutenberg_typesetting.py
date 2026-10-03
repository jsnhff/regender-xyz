# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Jason Huff
"""Project Gutenberg's typesetting instructions are not words Austen wrote.

Its plain text marks a letter's salutation and date line with instructions to a
typesetter:

    /* NIND "My dear friend, */
    /* RIGHT "Hunsford, near Westerham, Kent, _15th October_. */

NIND is no-indent, RIGHT is right-align. The parser carried the wrapper through
and it reached the printed page -- nine per edition, in all four, "/* NIND" and
all, discovered by Jason reading chapter 7 of a laid-out proof.

The instruction is dropped rather than translated: where the text is laid out,
those paragraphs already carry Salutation and Date Line styles, which says the
same thing properly.
"""

import pytest

from src.parsers.parser import IntegratedParser


@pytest.fixture
def parser():
    return IntegratedParser()


REAL = [
    ('/* NIND "My dear friend, */', '"My dear friend,'),
    ('/* NIND "My dearest Lizzie, */', '"My dearest Lizzie,'),
    (
        '/* RIGHT "Hunsford, near Westerham, Kent, _15th October_. */',
        '"Hunsford, near Westerham, Kent, _15th October_.',
    ),
    ('/* "My dear Sir, */', '"My dear Sir,'),
    (
        '/* RIGHT "Gracechurch Street, _Monday, August 2_. */',
        '"Gracechurch Street, _Monday, August 2_.',
    ),
]


class TestTheNineThatReachedPrint:
    @pytest.mark.parametrize(("wrapped", "expected"), REAL)
    def test_the_instruction_is_dropped(self, parser, wrapped, expected):
        assert parser._lines_to_paragraphs([wrapped, ""]) == [expected]

    def test_a_whole_letter_opening(self, parser):
        """The salutation and the line after it, as they sit in the file."""
        lines = ['/* NIND "My dear friend, */', "", "I am very glad to hear it.", ""]
        assert parser._lines_to_paragraphs(lines) == [
            '"My dear friend,',
            "I am very glad to hear it.",
        ]


class TestWhatItMustNotTouch:
    @pytest.mark.parametrize(
        "text",
        [
            "She said the price was 5/8 of a pound.",
            "It was a fine day, and */ meant nothing to her.",
            "The ratio was 3/4 * 2, he explained.",
            "A plain paragraph with no markup at all.",
        ],
    )
    def test_ordinary_prose_survives(self, parser, text):
        assert parser._lines_to_paragraphs([text, ""]) == [text]

    def test_an_unclosed_instruction_is_left_alone(self, parser):
        """Half a wrapper is not a wrapper; better kept and seen than eaten."""
        text = '/* NIND "My dear friend,'
        assert parser._lines_to_paragraphs([text, ""]) == [text]

    def test_an_empty_wrapper_leaves_nothing_behind(self, parser):
        assert parser._lines_to_paragraphs(["/* */", ""]) == []


class TestTheIndentInLetters:
    """Gutenberg indents each continuation line of a letter:

        "The disagreement subsisting between yourself and my late honoured
              father always gave me much uneasiness; and, since I have had the

    rstrip() took the trailing whitespace and left the leading, so the indent
    was joined into the middle of the sentence -- "my late honoured      father".
    316 gaps per edition, every one six spaces wide, all inside the letters.
    Chapter 52's letter carried 147 of them in a single paragraph.
    """

    def test_the_indent_does_not_reach_the_sentence(self, parser):
        lines = [
            '"The disagreement subsisting between yourself and my late honoured',
            "      father always gave me much uneasiness; and, since I have had the",
            "      misfortune to lose him, I have frequently wished to heal the",
            "",
        ]
        got = parser._lines_to_paragraphs(lines)
        assert "  " not in got[0], got[0]
        assert "honoured father always" in got[0]

    def test_every_line_joins_with_exactly_one_space(self, parser):
        lines = ["    first line", "        second line", "   third line", ""]
        assert parser._lines_to_paragraphs(lines) == ["first line second line third line"]

    def test_a_paragraph_that_was_never_indented_is_unchanged(self, parser):
        lines = ["It is a truth universally acknowledged,", "that a single man", ""]
        assert parser._lines_to_paragraphs(lines) == [
            "It is a truth universally acknowledged, that a single man"
        ]
