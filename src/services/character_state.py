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
from dataclasses import dataclass
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


def detect_marital_changes(book: dict, characters: Iterable[Any]) -> list[StateChange]:
    """Find the chapter each character's surname first takes a married title.

    Deterministic and checkable: it reports what the book already says. In
    Pride and Prejudice this finds Collins at 28, Wickham at 49, and Darcy and
    Bingley at 61 -- the chapter they marry -- while Bennet and Gardiner are
    married from their first appearance and produce no change at all.

    A character is only reported if the book calls them by a single title
    first. Someone who is "Mrs." throughout was never unmarried on the page,
    and inventing a wedding for them would be worse than saying nothing.
    """
    wanted: dict[str, list] = {}
    for char in characters:
        surname = _surname(getattr(char, "name", "") or "")
        if surname:
            wanted.setdefault(surname, []).append(char)
    if not wanted:
        return []

    pattern = re.compile(
        r"(?<![A-Za-z])(Mr|Mrs|Miss)\.?\s+(" + "|".join(re.escape(s) for s in wanted) + r")\b"
    )

    first_single: dict[str, int] = {}
    first_married: dict[str, tuple[int, str]] = {}
    for chapter in book.get("chapters", []):
        number = chapter.get("number")
        if number is None:
            continue
        for index, para in enumerate(chapter.get("paragraphs", [])):
            text = " ".join(para.get("sentences", []))
            for match in pattern.finditer(text):
                title, surname = match.group(1), match.group(2)
                if title in _SINGLE_TITLES:
                    first_single.setdefault(surname, (number, index))
                elif title == _MARRIED_TITLE and surname not in first_married:
                    start = max(0, match.start() - 40)
                    first_married[surname] = (
                        number,
                        index,
                        re.sub(r"\s+", " ", text[start : match.end() + 40]).strip(),
                    )

    # A surname whose "Mrs." is already a cast member in her own right. The
    # Bennets have a Mr. and a Mrs. from the start -- she is his wife, not him
    # having married in chapter two. Without this the detector reports a
    # wedding for every married couple in the book.
    spoken_for = {
        surname for surname, chars in wanted.items() if any(not _is_single_titled(c) for c in chars)
    }

    changes: list[StateChange] = []
    for surname, (chapter, paragraph, evidence) in sorted(first_married.items()):
        if surname in spoken_for:
            continue
        single_at = first_single.get(surname)
        # Married from the first mention: nothing changed on the page.
        if single_at is None or (chapter, paragraph) <= single_at:
            continue
        for char in wanted[surname]:
            if _is_single_titled(char):
                changes.append(
                    StateChange(
                        character=char.name,
                        kind="marital",
                        becomes="married",
                        chapter=chapter,
                        paragraph=paragraph,
                        evidence=evidence,
                    )
                )
    return changes


def _is_single_titled(char: Any) -> bool:
    """True when the cast records this character under Mr./Miss, not Mrs."""
    titles = {t.rstrip(".") for t in (getattr(char, "titles", None) or [])}
    name_title = (getattr(char, "name", "") or "").split()
    if name_title:
        titles.add(name_title[0].rstrip("."))
    if _MARRIED_TITLE in titles:
        return False
    return bool(titles & set(_SINGLE_TITLES))


def initial_marital_state(characters: Iterable[Any]) -> dict[str, str]:
    """What each character's marital state is when the book opens.

    Changes alone are not enough. Mr. Bennet never becomes married during the
    book -- he is married on page one, and a reader who only saw the changes
    would take him for a bachelor with five daughters. A man whose surname
    already carries a "Mrs." in the cast is married from the start; anyone else
    is treated as unmarried until the text says otherwise.
    """
    cast = list(characters)
    by_surname: dict[str, list] = {}
    for char in cast:
        surname = _surname(getattr(char, "name", "") or "")
        if surname:
            by_surname.setdefault(surname, []).append(char)

    state: dict[str, str] = {}
    for chars in by_surname.values():
        has_spouse = any(not _is_single_titled(c) for c in chars)
        for char in chars:
            if not _is_single_titled(char):
                state[char.name] = "married"
            else:
                state[char.name] = "married" if has_spouse else "unmarried"
    return state


# How a man's title renders once you know whether he is married. English gives
# women two titles and men one, so a swap has to answer a question the source
# never asked -- and the answer changes as the book goes on.
_MARITAL_TITLE = {"married": "Mrs.", "unmarried": "Miss"}


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
    """
    base: dict[str, str] = {}
    at: dict[tuple[int, int], dict[str, str]] = {}

    for char in characters:
        name = getattr(char, "name", "") or ""
        surname = _surname(name)
        if not surname or not _is_single_titled(char):
            continue
        tokens = [t for t in re.split(r"\s+", name.strip()) if t]
        if not tokens or tokens[0].rstrip(".") != "Mr":
            continue  # only "Mr." is ambiguous; Miss and Mrs. already say enough

        opening = initial.get(name, "unmarried")
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
