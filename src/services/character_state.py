# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Jason Huff
"""Character state that changes partway through a book.

A cast is not static. Darcy is unmarried for sixty chapters and married in the
sixty-first; Collins marries in chapter twenty-two; Lydia becomes Mrs. Wickham
in chapter forty-nine. Anything that reads a character's state once and applies
it to the whole book is wrong for most of it.

This matters as soon as a transform has to choose between forms that encode
that state. English women's titles do: "Mrs." says married and "Miss" says not,
while "Mr." says nothing. So a gender swap that turns men into women has to
answer a question the source never asked, and the answer changes as the book
goes on.

The mechanism here is general -- a change is a character, a kind, a new value
and the chapter it takes effect. How changes are *found* is pluggable; the
detector below reads them off the titles the book itself uses, which needs no
model call and can be checked against the text.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import Any

# "Mrs. Darcy" appearing for the first time in a book that has been calling him
# "Mr. Darcy" is the book telling you a wedding happened.
_MARRIED_TITLE = "Mrs"
_SINGLE_TITLES = ("Mr", "Miss")


@dataclass(frozen=True)
class StateChange:
    """One character's state changing, from one chapter onward."""

    character: str
    kind: str
    becomes: str
    chapter: int
    # Weddings do not wait for a chapter break. Elizabeth is Miss Bennet in one
    # paragraph and Mrs. Darcy a few paragraphs later, inside one chapter, so
    # the marker has to be finer than the chapter it falls in.
    paragraph: int = 0
    evidence: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "character": self.character,
            "kind": self.kind,
            "becomes": self.becomes,
            "from_chapter": self.chapter,
            "from_paragraph": self.paragraph,
            "evidence": self.evidence,
        }


def _surname(name: str) -> str | None:
    """The family name in a display name, or None if there isn't one."""
    tokens = [t for t in re.split(r"\s+", name.strip()) if t]
    while tokens and tokens[0].rstrip(".") in {
        "Mr",
        "Mrs",
        "Ms",
        "Mx",
        "Miss",
        "Sir",
        "Lady",
        "Lord",
        "Dame",
        "Colonel",
        "Captain",
        "Major",
        "General",
        "Dr",
        "Doctor",
        "Reverend",
    }:
        tokens.pop(0)
    return tokens[-1] if tokens else None


# How often a book may say "Mr. S" before it first says "Mrs. S" and the two
# still be a couple who were married when we met them.
#
# Measured, not chosen: in Pride and Prejudice, Emma, Middlemarch, Little Women
# and Great Expectations, every man who marries during the book is named at
# least 37 times before his surname first takes a "Mrs." (Wemmick 37, Wickham
# 58, Lydgate 77, Collins 104, Casaubon 128, Elton 180, Darcy 270), and every
# man whose wife is there from the start at most 12 (Bennet 8, Bulstrode 8,
# Pocket 7, Hurst 1, and a few minor husbands whose wives are named late). A
# man called by his own title twenty times with no wife in sight is a single
# man, whatever the cast says about who shares his surname.
_SINGLE_LIFE = 20

# How a man's title renders once you know whether he is married. English gives
# women two titles and men one, so a swap has to answer a question the source
# never asked -- and the answer changes as the book goes on.
_MARITAL_TITLE = {"married": "Mrs.", "unmarried": "Miss"}

# Words that end a cast name without being the family name.
_GENERATION = {"senior", "junior", "sr", "jr", "elder", "younger", "esq"}


def _is_a_description(tokens: list[str]) -> bool:
    """True when a titled cast name describes a person instead of naming one.

    Judged on the word that would be read as the surname, and on anything
    possessive before it: "Mr. Jones's shopboy" is about the shopboy.
    """
    last = tokens[-1]
    # No capital anywhere, so "d'Arcy" and "de Bourgh" are still surnames.
    if not any(ch.isupper() for ch in last) or re.search(r"[()\[\]]", last):
        return True
    if last.rstrip(".").lower() in _GENERATION:
        return True
    return any(re.search(r"['’]s$", token) for token in tokens[:-1])


def _is_single_titled(char: Any) -> bool:
    """True when the cast records this character under Mr./Miss, not Mrs."""
    titles = {t.rstrip(".") for t in (getattr(char, "titles", None) or [])}
    name_title = (getattr(char, "name", "") or "").split()
    if name_title:
        titles.add(name_title[0].rstrip("."))
    if _MARRIED_TITLE in titles:
        return False
    return bool(titles & set(_SINGLE_TITLES))


def _tokens(char: Any) -> list[str]:
    return [t for t in re.split(r"\s+", (getattr(char, "name", "") or "").strip()) if t]


def _family_name(char: Any) -> str | None:
    """A cast member's family name, or None when the cast does not give one.

    A description has none ("Mr. Darcy's father"), and neither does a single
    bare word: "John" may be a footman's given name, and reading it as a
    surname would have "Mr. John Knightley" counted as a Mr. John.
    """
    tokens = _tokens(char)
    if not tokens or _is_a_description(tokens):
        return None
    surname = _surname(" ".join(tokens))
    if not surname:
        return None
    titled = tokens[0] != surname and _surname(tokens[0]) is None
    return surname if titled or len(tokens) > 1 else None


def _is_a_man(char: Any) -> bool:
    gender = getattr(char, "gender", None)
    if getattr(gender, "value", gender) == "male":
        return True
    tokens = _tokens(char)
    return bool(tokens) and tokens[0].rstrip(".") == "Mr"


def _is_recorded_as_mrs(char: Any) -> bool:
    """The cast calls her Mrs., by name or among her titles.

    Narrower than "is not Mr. or Miss", which is what stood here. That test
    took Lady Anne Darcy for her son's wife, Old Wickham for his son's, and
    every character the cast had left untitled for somebody's.
    """
    tokens = _tokens(char)
    if tokens and tokens[0].rstrip(".") == _MARRIED_TITLE:
        return True
    return _MARRIED_TITLE in {t.rstrip(".") for t in (getattr(char, "titles", None) or [])}


@dataclass(frozen=True)
class MaritalState:
    """What the book and the cast say about one "Mr. Surname", and the verdict."""

    name: str  # the form the text uses, "Mr. Darcy"
    opens: str  # "married" or "unmarried"
    wedding: tuple[int, int] | None  # (chapter, paragraph) his surname first takes "Mrs."
    evidence: str
    mentions: int  # times the book says "Mr. S"
    before_first_mrs: int  # how many of those come before the first "Mrs. S"
    wife_in_cast: bool
    reason: str

    @property
    def worth_a_look(self) -> bool:
        """Whether a person should see this verdict before it is used.

        One kind needs no second opinion: the book never prints a "Mrs." of
        his name and the cast names none, so there is nothing to mistake. Every
        other verdict rests on a "Mrs." that might be his mother, his brother's
        wife, or his own a chapter before the wedding, and telling those apart
        takes someone who has read the book.
        """
        nothing_to_mistake = (
            self.opens == "unmarried"
            and self.wedding is None
            and self.before_first_mrs == self.mentions
        )
        return not nothing_to_mistake

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "opens": self.opens,
            "wedding": list(self.wedding) if self.wedding else None,
            "evidence": self.evidence,
            "mr_mentions": self.mentions,
            "mr_mentions_before_first_mrs": self.before_first_mrs,
            "wife_in_cast": self.wife_in_cast,
            "reason": self.reason,
        }


def with_rulings(
    states: dict[str, MaritalState], rulings: dict[str, dict] | None
) -> dict[str, MaritalState]:
    """The verdicts, with a reader's rulings laid over them.

    A ruling is ``{"opens": "married" | "unmarried", "wedding": [chapter,
    paragraph] | None}`` for one "Mr. Surname". It replaces the verdict whole:
    a person who has read the book outranks a count of how often it says
    "Mrs.".
    """
    ruled = dict(states)
    for name, ruling in (rulings or {}).items():
        state = ruled.get(name)
        if state is None or ruling.get("opens") not in _MARITAL_TITLE:
            continue
        wedding = ruling.get("wedding")
        wedding = (int(wedding[0]), int(wedding[1])) if wedding else None
        if ruling["opens"] == "married":
            wedding = None  # already married; there is no later wedding to mark
        ruled[name] = replace(
            state, opens=ruling["opens"], wedding=wedding, reason="settled by the reader"
        )
    return ruled


def changes_from(states: dict[str, MaritalState]) -> list[StateChange]:
    """The weddings in a set of verdicts, as changes the timeline can apply."""
    return [
        StateChange(
            character=state.name,
            kind="marital",
            becomes="married",
            chapter=state.wedding[0],
            paragraph=state.wedding[1],
            evidence=state.evidence,
        )
        for state in states.values()
        if state.wedding
    ]


def marital_states(book: dict | None, characters: Iterable[Any]) -> dict[str, MaritalState]:
    """Whether each "Mr. Surname" is married when the book opens, and when he marries.

    Keyed by the form the text uses, never by what the cast happens to call
    him. The cast is written by a model and names one man "Mr. Darcy" in one
    run, "Fitzwilliam Darcy" in the next and "Mr. Fitzwilliam Darcy" in a
    third; the book only ever says "Mr. Darcy", and that is what a title has
    to be attached to.

    The book decides. Three cases, in order:

    - He is named many times before any "Mrs." of his surname appears. He was
      a single man for all of that, and the first "Mrs." is his wedding.
      Nothing in the cast overrides this: it lists a bride under her married
      name as readily as a wife of twenty years.
    - Otherwise, a woman the cast records as "Mrs." of his surname is his
      wife, and he is married from the start.
    - Otherwise he opens unmarried, and marries where the text first prints
      "Mrs." after him, if it ever does.

    Without a book only the cast can speak, and only for men it names as
    "Mr. Surname".
    """
    cast = list(characters)
    men: dict[str, list] = {}
    wives: set[str] = set()
    named_mrs: set[str] = set()
    for char in cast:
        surname = _family_name(char)
        if not surname:
            continue
        if _is_recorded_as_mrs(char):
            wives.add(surname)
            if _tokens(char)[0].rstrip(".") == _MARRIED_TITLE:
                named_mrs.add(surname)
        elif _is_a_man(char):
            men.setdefault(surname, []).append(char)

    if book is None:
        return {
            f"Mr. {surname}": MaritalState(
                name=f"Mr. {surname}",
                opens="married" if surname in wives else "unmarried",
                wedding=None,
                evidence="",
                mentions=0,
                before_first_mrs=0,
                wife_in_cast=surname in wives,
                reason="no book to read; the cast alone",
            )
            for surname, chars in men.items()
            if any(_tokens(c)[0].rstrip(".") == "Mr" for c in chars)
        }
    if not men:
        return {}

    # "Mr. S" standing alone. Followed by another capitalised word it is a
    # given name -- "Mr. Fitzwilliam Darcy" is not a mention of the Colonel.
    pattern = re.compile(
        r"(?<![A-Za-z])(Mr|Mrs)\.?\s+("
        + "|".join(re.escape(s) for s in sorted(men, key=len, reverse=True))
        + r")\b(?!\s+[A-Z][a-z])"
    )
    mr: dict[str, list[tuple[int, int]]] = {}
    mrs_count: dict[str, int] = {}
    first_mrs: dict[str, tuple[int, int, str]] = {}
    for chapter in book.get("chapters", []):
        number = chapter.get("number")
        if number is None:
            continue
        for index, para in enumerate(chapter.get("paragraphs", [])):
            text = " ".join(para.get("sentences", []))
            for match in pattern.finditer(text):
                title, surname = match.group(1), match.group(2)
                if title == "Mr":
                    mr.setdefault(surname, []).append((number, index))
                    continue
                mrs_count[surname] = mrs_count.get(surname, 0) + 1
                if surname not in first_mrs:
                    start = max(0, match.start() - 40)
                    first_mrs[surname] = (
                        number,
                        index,
                        re.sub(r"\s+", " ", text[start : match.end() + 40]).strip(),
                    )

    states: dict[str, MaritalState] = {}
    for surname in men:
        mentions = mr.get(surname, [])
        seen = first_mrs.get(surname)
        if not mentions:
            continue  # the book never calls anyone this; nothing to attach a title to
        wife = surname in wives
        point = (seen[0], seen[1]) if seen else None
        before = sum(1 for at in mentions if point is None or at < point)
        wedding = None
        if point is None:
            # The book never prints "Mrs. S", so the cast is the only witness,
            # and it has to say "Mrs. S" outright. A "Mrs." among someone's
            # titles is not that: Jane Eyre's cast lists Bertha Mason as a
            # Mrs., which she is -- Mrs. Rochester -- and that made her brother
            # a married man. Emma's lists "Mrs. Woodhouse", who is dead before
            # the book opens and never named in it, and a widow is still Mrs.
            wife = surname in named_mrs
            opens = "married" if wife else "unmarried"
            reason = (
                'the cast names a "Mrs." of this surname'
                if wife
                else "the book never prints a Mrs. of this name"
            )
        elif before >= _SINGLE_LIFE:
            opens, wedding = "unmarried", point
            reason = f"named {before} times before the first Mrs. of this name: single until then"
        elif wife:
            opens = "married"
            reason = "the cast records a Mrs. of this name, and the book prints her early"
        elif mentions and point > mentions[0]:
            opens, wedding = "unmarried", point
            reason = "no Mrs. of this name in the cast; the first one printed is his wedding"
        else:
            opens = "unmarried"
            reason = "a Mrs. of this name is printed before him and the cast does not know her"

        # A wedding is a strong claim, and one more thing can undo it: the Mrs.
        # may be somebody else's wife. Mr. Knightley's brother is married, so
        # Emma prints "Mrs. Knightley" in chapter fourteen -- four times in
        # all, against 230 more of him. A man's own wife is not named once for
        # every fifty times he is.
        after = len(mentions) - before
        hers = mrs_count.get(surname, 0)
        if wedding and after > hers * _SINGLE_LIFE:
            wedding = None
            reason = (
                f"a Mrs. of this name is printed {hers} time(s) against {after} of him "
                "afterwards: someone else's wife, not his"
            )
        states[f"Mr. {surname}"] = MaritalState(
            name=f"Mr. {surname}",
            opens=opens,
            wedding=wedding,
            # The first "Mrs." of his name, whatever was made of it: it is
            # what a person needs to read to agree or disagree.
            evidence=seen[2] if seen else "",
            mentions=len(mentions),
            before_first_mrs=before,
            wife_in_cast=wife,
            reason=reason,
        )
    return states


def detect_marital_changes(book: dict, characters: Iterable[Any]) -> list[StateChange]:
    """Find the paragraph each man's surname first takes a married title.

    Deterministic and checkable: it reports what the book already says. In
    Pride and Prejudice this finds Collins at 28, Wickham at 49, and Darcy and
    Bingley at 61 -- the chapter the book first calls their wives by their new
    name -- while Bennet and Gardiner are married from their first appearance
    and produce no change at all.

    Each change names the man as the text does, "Mr. Darcy". See
    marital_states for how a wedding is told from a marriage already made.
    """
    return changes_from(marital_states(book, characters))


def initial_marital_state(characters: Iterable[Any], book: dict | None = None) -> dict[str, str]:
    """What each "Mr. Surname"'s marital state is when the book opens.

    Changes alone are not enough. Mr. Bennet never becomes married during the
    book -- he is married on page one, and a reader who only saw the changes
    would take him for a bachelor with five daughters.

    Pass the book. Without it only the cast can be asked, and the cast cannot
    tell a wife from a bride: it lists Charlotte under "Collins" from the first
    page, which made Mr. Collins a married man when he proposed to Elizabeth.
    """
    return {name: state.opens for name, state in marital_states(book, characters).items()}


def marital_title_maps(
    characters: Iterable[Any],
    changes: Iterable[StateChange],
    initial: dict[str, str],
) -> tuple[dict[str, str], list[tuple[int, int, dict[str, str]]]]:
    """Title entries for a gender swap, and the points they change at.

    Returns ``(base, timeline)``. ``base`` holds the form each name takes from
    the first paragraph; ``timeline`` is a sorted list of
    ``(chapter, paragraph, entries)`` that replace it from that point onward.

    Keyed to the paragraph, not the chapter: a wedding does not wait for a
    chapter break, so a character can be Miss in one paragraph and Mrs. four
    paragraphs later inside the same chapter.

    One entry per man, under the name the text calls him by. ``initial``
    already holds exactly those, so the cast is not consulted again here.
    """
    base: dict[str, str] = {}
    at: dict[tuple[int, int], dict[str, str]] = {}
    changes = list(changes)

    for name, opening in initial.items():
        if not name.startswith("Mr. "):
            continue  # only "Mr." is ambiguous; Miss and Mrs. already say enough
        surname = name[len("Mr. ") :]
        base[name] = f"{_MARITAL_TITLE[opening]} {surname}"

        for change in changes:
            if change.character != name or change.kind != "marital":
                continue
            title = _MARITAL_TITLE.get(change.becomes)
            if title and f"{title} {surname}" != base[name]:
                at.setdefault((change.chapter, change.paragraph), {})[name] = f"{title} {surname}"

    timeline = [(c, p, entries) for (c, p), entries in sorted(at.items())]
    return base, timeline


def state_at(
    changes: Iterable[StateChange],
    character: str,
    kind: str,
    chapter: int,
    paragraph: int = 10**9,
    initial: dict[str, str] | None = None,
) -> str | None:
    """The value of one kind of state for one character, at one paragraph.

    The paragraph defaults to the end of the chapter, so callers that only care
    about chapter granularity can leave it out.
    """
    value = (initial or {}).get(character)
    for change in sorted(changes, key=lambda c: (c.chapter, c.paragraph)):
        if change.character != character or change.kind != kind:
            continue
        if (change.chapter, change.paragraph) <= (chapter, paragraph):
            value = change.becomes
    return value
