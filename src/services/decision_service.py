"""What a transform cannot decide on its own.

Some words have no neutral English equivalent. "sir" and "madam" carry no
information about the speaker's own sex -- they mark rank, deference, distance,
sometimes contempt -- but English offers nothing that does the same job without
choosing one. "master" is an employer, a teacher, a household head, and half of
"his own master", and only the words beside it say which.

Rules settle most of it. What is left is an editorial judgement per instance,
and this module's job is to say so before the transform runs rather than let
the reader find it in the printed book: how many rulings a book needs, where
they are, and what the mechanical readings of each one look like.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# A bare vocative: an address with no name after it. "Sir William" is a title
# and needs no ruling; "Indeed, sir," has nothing to convert it to.
_VOCATIVE = re.compile(r"(?<![A-Za-z])(sir|madam|ma['’]am)(?!\s+[A-Z])(?![A-Za-z])", re.IGNORECASE)

# Words whose sense depends on the words beside them.
_POLYSEMOUS = re.compile(r"(?<![A-Za-z])(master|mistress)(?![A-Za-z])", re.IGNORECASE)


def _resolved_frames(key: str) -> re.Pattern | None:
    """The collocations the sense rules already settle, as one pattern.

    An occurrence inside one of these needs no ruling -- "music master" becomes
    "music teacher" by rule. Counting it would overstate the work and train the
    reader to ignore the estimate.
    """
    from src.services.transform_service import TransformService

    frames = [
        frame for frame in TransformService._SENSE_RULES.get(key, {}) if _POLYSEMOUS.search(frame)
    ]
    if not frames:
        return None
    frames.sort(key=len, reverse=True)
    return re.compile("|".join(re.escape(f) for f in frames), re.IGNORECASE)


# A singular-agreeing verb reached from an earlier "they" across a coordinator:
# "they came down ... and was so much delighted". Sometimes the verb's subject
# really is that "they" and it has to become "were"; sometimes a noun subject
# stands closer -- "Jane was yielding ... and was in a way to be very much in
# love" -- and the singular verb is correct as it stands. The two are
# structurally identical, so this is offered as a decision, never repaired.
#
# The safety net only ever matched an adjacent pair ("they was"), so every one
# of these went through untouched.
_LOOSE_AGREEMENT = re.compile(
    r"\bthey\b(?:(?!\bthey\b)[^.!?;])*?"
    r"(?:,\s*(?:and|but)|\band\b|\bbut\b)\s+"
    r"(?P<verb>was|is|has|does)\b",
    re.IGNORECASE,
)

_PLURAL_FORM = {"was": "were", "is": "are", "has": "have", "does": "do"}

_SALUTATION = re.compile(r"(?:^|[\"“(])\s*(?:my\s+)?dear\s+$", re.IGNORECASE)
_CLOSE = re.compile(r"\bI\s+(?:am|remain)\b[^.?!]*$", re.IGNORECASE)
_SHORT_REPLY = re.compile(r"(?:yes|no|never|indeed|certainly|ay|oh)[,!]?", re.IGNORECASE)

FRAME_HELP = {
    "letter salutation": "opens a letter, where the addressee is already explicit",
    "letter close": "signs off a letter",
    "short reply": "the whole answer is two or three words",
    "clause opener": "opens the sentence, before anything else is said",
    "clause-final tag": "closes the sentence",
    "clause-medial": "sits inside the sentence, between clauses",
    "word sense": "employer, teacher, household head, or the 'own master' idiom",
    "verb agreement": "a singular verb reached from an earlier 'they' — whose subject is it?",
}


@dataclass
class Decision:
    """One site a person has to rule on."""

    chapter: int
    paragraph: int
    word: str
    frame: str
    excerpt: str
    offset: int = -1
    options: dict[str, str] = field(default_factory=dict)
    ruling: str | None = None

    @property
    def ref(self) -> str:
        return f"ch{self.chapter} p{self.paragraph}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "ref": self.ref,
            "chapter": self.chapter,
            "paragraph": self.paragraph,
            "word": self.word,
            "frame": self.frame,
            "why": FRAME_HELP.get(self.frame, ""),
            "offset": self.offset,
            "excerpt": self.excerpt,
            "options": self.options,
            "ruling": self.ruling,
        }


@dataclass
class DecisionReport:
    """Everything a book needs ruled, and the counts to show before starting."""

    transform_type: str
    decisions: list[Decision] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.decisions)

    def by_frame(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for decision in self.decisions:
            counts[decision.frame] = counts.get(decision.frame, 0) + 1
        return dict(sorted(counts.items(), key=lambda kv: -kv[1]))

    def by_word(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for decision in self.decisions:
            key = decision.word.lower().replace("’", "'")
            counts[key] = counts.get(key, 0) + 1
        return dict(sorted(counts.items(), key=lambda kv: -kv[1]))

    def to_dict(self, book_title: str = "") -> dict[str, Any]:
        return {
            "book": book_title,
            "variant": self.transform_type,
            "total_decisions": self.total,
            "by_word": self.by_word(),
            "by_frame": self.by_frame(),
            "instructions": (
                'Set "ruling" on each entry to one of its option keys, or to any '
                "wording of your own, which replaces the word itself. Entries left "
                "null are reported and left alone. Apply with --decisions <file>."
            ),
            "decisions": [d.to_dict() for d in self.decisions],
        }

    def as_note(self, book_title: str = "") -> str:
        """A plain-text account of what the transform could and could not settle.

        Written beside the book rather than into it. These exports feed
        InDesign, where a header would simply become the first paragraph of the
        printed text, so the note travels as its own file.

        Anyone can end up holding the output without having seen the run that
        produced it. This is what tells them the neutral edition involved
        judgement, where that judgement was needed, and what is still open.
        """
        title = book_title or "this book"
        lines = [
            "TRANSFORMATION NOTES",
            "=" * 20,
            "",
            f"Book:      {title}",
            f"Transform: {self.transform_type}",
            "",
            "WHAT THIS TRANSFORM DOES NOT DO BY ITSELF",
            "",
            "Neutralising a text is not a find-and-replace. Most of it is",
            "mechanical, but English has no neutral form of some words, and",
            "others mean different things in different sentences. Those are",
            "editorial judgements, and no rule settles them.",
            "",
        ]
        if not self.decisions:
            lines += [
                "Nothing was left undecided in this book. Every word the rules",
                "could not read on its own turned out not to occur here.",
                "",
            ]
        else:
            lines += [f"{self.total} place(s) were left for a person to decide:", ""]
            for frame, count in self.by_frame().items():
                why = FRAME_HELP.get(frame, "")
                lines.append(f"  {count:>4}  {frame} — {why}")
            lines += [
                "",
                "Unless a decision sheet was applied, these are UNRESOLVED in the",
                "text you are holding: the word was left as the source had it.",
                "The accompanying *_decisions.json lists every one with its",
                "options; filling in a ruling and re-running applies them.",
                "",
            ]
        lines += [
            "KNOWN LIMITS",
            "",
            "  - A singular 'they' far from its verb can leave the verb",
            "    unconjugated. Where the subject is unambiguous these are",
            "    listed above; where a noun subject stands closer, the singular",
            "    verb is correct and is left alone.",
            "  - Titles are converted only where a name follows. A bare address",
            "    has no neutral equivalent and is reported, not guessed at.",
            "  - Character names are preserved. Gender read into a name itself",
            "    is not something the transform changes.",
            "",
            "This file describes the transformation, not the book. It is safe to",
            "delete and is not part of the text.",
            "",
        ]
        return "\n".join(lines)


class DecisionService:
    """Find the sites a transform cannot settle by rule.

    Scans the source with no model calls, so the count can be shown before a
    transform starts rather than discovered after it finishes.
    """

    # Only the neutralising transform hits this. A swap turns "sir" into
    # "madam" and is finished; there is nothing to weigh.
    APPLIES_TO = frozenset({"nonbinary"})

    def __init__(self, transform_type: str):
        self.key = transform_type

    # ---------- estimating ----------

    def estimate(self, text: str) -> dict[str, int]:
        """Counts straight off the raw text, before the book is even parsed.

        An upper bound, deliberately. Every site here is a word with no neutral
        English form, but the model settles many of them in passing and the
        sense rules take more. The sheet written after the transform is the
        real list; this is what a reader is told before agreeing to start.
        """
        if self.key not in self.APPLIES_TO:
            return {}
        counts: dict[str, int] = {}
        for match in _VOCATIVE.finditer(text):
            word = match.group(0).lower().replace("\u2019", "'")
            counts[word] = counts.get(word, 0) + 1
        settled = _resolved_frames(self.key)
        covered = [m.span() for m in settled.finditer(text)] if settled else []
        for match in _POLYSEMOUS.finditer(text):
            if any(a <= match.start() and match.end() <= b for a, b in covered):
                continue
            word = match.group(0).lower()
            counts[word] = counts.get(word, 0) + 1
        return dict(sorted(counts.items(), key=lambda kv: -kv[1]))

    # ---------- scanning ----------

    def scan(self, book: dict) -> DecisionReport:
        report = DecisionReport(transform_type=self.key)
        if self.key not in self.APPLIES_TO:
            return report

        for chapter in book.get("chapters", []):
            number = chapter.get("number", 0)
            for position, para in enumerate(chapter.get("paragraphs", [])):
                text = " ".join(para.get("sentences", []))
                for match in _VOCATIVE.finditer(text):
                    frame = self._frame(text, match.start(), match.end())
                    report.decisions.append(
                        Decision(
                            chapter=number,
                            paragraph=position,
                            word=match.group(0),
                            frame=frame,
                            offset=match.start(),
                            excerpt=_excerpt(text, match.start(), match.end()),
                            options=self._options(text, match, frame),
                        )
                    )
                settled = _resolved_frames(self.key)
                covered = [m.span() for m in settled.finditer(text)] if settled else []
                for match in _POLYSEMOUS.finditer(text):
                    if any(a <= match.start() and match.end() <= b for a, b in covered):
                        continue  # a sense rule already reads this one
                    report.decisions.append(
                        Decision(
                            chapter=number,
                            paragraph=position,
                            word=match.group(0),
                            frame="word sense",
                            offset=match.start(),
                            excerpt=_excerpt(text, match.start(), match.end()),
                            options={
                                "employer": "employer",
                                "teacher": "teacher",
                                "head of the house": "head of the house",
                                "keep": match.group(0),
                            },
                        )
                    )
                for match in _LOOSE_AGREEMENT.finditer(text):
                    verb = match.group("verb")
                    plural = _PLURAL_FORM[verb.lower()]
                    report.decisions.append(
                        Decision(
                            chapter=number,
                            paragraph=position,
                            word=verb,
                            frame="verb agreement",
                            offset=match.start("verb"),
                            excerpt=_excerpt(text, *match.span("verb")),
                            options={
                                plural: _preview(
                                    _replaced(text, *match.span("verb"), plural),
                                    match.start("verb"),
                                ),
                                "keep": _preview(text, match.start("verb")),
                            },
                        )
                    )
        return report

    @staticmethod
    def _frame(text: str, start: int, end: int) -> str:
        """Classify by what stands either side of the vocative."""
        before, after = text[:start], text[end:]
        if _SALUTATION.search(before):
            return "letter salutation"
        stem = re.split(r"(?<=[.?!])\s", before)[-1].strip(" \"“'‘")
        if _CLOSE.search(stem):
            return "letter close"
        if not stem.rstrip(", "):
            return "clause opener"
        # A short reply is short all through: "Never, sir." is one, but
        # "Indeed, sir, I have not the least intention" only opens like one.
        closes_sentence = bool(re.match(r"\s*[.?!;]|\s*[\"”]", after))
        if closes_sentence and _SHORT_REPLY.fullmatch(stem.rstrip(", ")):
            return "short reply"
        if closes_sentence:
            return "clause-final tag"
        return "clause-medial"

    @staticmethod
    def _options(text: str, match: re.Match, frame: str) -> dict[str, str]:
        """The readings that need no knowledge of who is speaking.

        Deliberately mechanical. A name or a kinship term is very often the
        better answer, but picking one means knowing who is being addressed,
        which is exactly the judgement being handed to a person.
        """
        start, end = match.span()
        options = {
            "ser": _preview(_replaced(text, start, end, "Ser"), start),
            "gentlehom": _preview(_replaced(text, start, end, "gentlehom"), start),
            "keep": _preview(text, start),
        }
        # Deleting the address out of a salutation leaves "Dear," which is not
        # a salutation at all, so it is not offered there.
        if frame != "letter salutation":
            options["delete"] = _preview(_deleted(text, start, end), start)
        return options

    # ---------- applying ----------

    def apply(self, book: dict, sheet: dict) -> tuple[dict, int, list[str]]:
        """Write the rulings into a book. Returns (book, applied, problems)."""
        applied = 0
        problems: list[str] = []

        index: dict[tuple, list[dict]] = {}
        for entry in sheet.get("decisions", []):
            index.setdefault((entry.get("chapter"), entry.get("paragraph")), []).append(entry)

        for chapter in book.get("chapters", []):
            number = chapter.get("number", 0)
            for position, para in enumerate(chapter.get("paragraphs", [])):
                entries = index.get((number, position))
                if not entries:
                    continue
                text = " ".join(para.get("sentences", []))

                # Plan against the untouched paragraph, then apply right to
                # left, so two sites in one paragraph cannot displace each other.
                planned: list[tuple[int, int, str]] = []
                seen: dict[str, int] = {}
                for entry in entries:
                    word = entry.get("word", "")
                    ordinal = seen.get(word.lower(), 0)
                    seen[word.lower()] = ordinal + 1

                    ruling = entry.get("ruling")
                    if not ruling or ruling == "keep":
                        continue

                    span = _locate(text, word, entry.get("offset", -1), ordinal)
                    if span is None:
                        problems.append(f"{entry.get('ref', '?')}: {word!r} not found")
                        continue
                    planned.append((span[0], span[1], ruling))

                for start, end, ruling in sorted(planned, reverse=True):
                    if ruling == "delete":
                        text = _deleted(text, start, end)
                    elif ruling == "ser":
                        text = _replaced(text, start, end, "Ser")
                    elif ruling == "gentlehom":
                        text = _replaced(text, start, end, "gentlehom")
                    else:
                        # anything else is taken as the wording to use
                        text = _replaced(text, start, end, ruling)
                    applied += 1

                para["sentences"] = [text]
        return book, applied, problems


def _replaced(text: str, start: int, end: int, word: str) -> str:
    return text[:start] + word + text[end:]


def _deleted(text: str, start: int, end: int) -> str:
    """Remove the vocative and the one comma that belongs to it."""
    before, after = text[:start], text[end:]
    if re.match(r"\s*,", after):
        after = re.sub(r"^\s*,", "", after, count=1)
        # the space ahead of the vocative went with it, not with the comma
        before = before.rstrip()
    elif re.search(r",\s*$", before):
        before = re.sub(r",\s*$", "", before, count=1)
    joined = before + after
    joined = re.sub(r"\s+([,.;:!?])", r"\1", joined)
    return re.sub(r"(?<=\S) {2,}(?=\S)", " ", joined)


def _locate(text: str, word: str, offset: int, ordinal: int):
    """Where this decision's own word sits, preferring the recorded offset.

    Counting occurrences is enough for a vocative -- a paragraph holds one or
    two. It is not enough for a verb: "was" can appear six times in a
    paragraph and only one of them is the site being ruled on. The scan records
    the exact offset, so use it when the text there still matches, and fall
    back to counting for a sheet written before offsets existed.
    """
    if offset is not None and offset >= 0:
        end = offset + len(word)
        if text[offset:end].lower() == word.lower():
            return (offset, end)
    return _nth(text, word, ordinal)


def _nth(text: str, word: str, ordinal: int):
    pattern = re.compile(
        r"(?<![A-Za-z])" + re.escape(word).replace("'", "['’]") + r"(?![A-Za-z])",
        re.IGNORECASE,
    )
    hits = list(pattern.finditer(text))
    return (hits[ordinal].start(), hits[ordinal].end()) if ordinal < len(hits) else None


def _preview(text: str, around: int, width: int = 70) -> str:
    left = max(0, around - width)
    right = min(len(text), around + width)
    piece = re.sub(r"\s+", " ", text[left:right]).strip()
    return ("…" if left else "") + piece + ("…" if right < len(text) else "")


def _excerpt(text: str, start: int, end: int, width: int = 60) -> str:
    left = max(0, start - width)
    right = min(len(text), end + width)
    piece = re.sub(r"\s+", " ", text[left:right]).strip()
    return ("…" if left else "") + piece + ("…" if right < len(text) else "")
