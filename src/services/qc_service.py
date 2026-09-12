"""
Quality Control Service

Verifies a transformed book against its source, chapter by chapter, without
calling an LLM. Every check is deterministic and reproducible, so it can gate
CI and be re-run over an already-printed edition.

Findings are graded by what can be done about them:

``auto_fixable``
    The deterministic safety net would still change this text. On output from
    the current pipeline this should be zero — a non-zero count means the text
    was produced before the safety net was fixed, or the net never ran.

``needs_review``
    A gendered word the LLM left untransformed that the safety net deliberately
    will not guess at (an ambiguous "her", a term outside the map). These are
    for a human or a second LLM pass.

``structural``
    Chapter or paragraph counts that do not line up, or paragraphs whose length
    drifted far enough to suggest truncated or hallucinated output.
"""

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from src.models.transformation import TransformType
from src.services.transform_service import TransformService

# Severity buckets, ordered worst first for reporting.
# Quote characters the exporter normalises; not evidence of corruption.
_EXPORT_PUNCTUATION = "\"'"

# The same word twice or more with nothing but space between it. Austen repeats
# words for effect ("very, very"), but always with punctuation between them.
_REPEATED_WORD = re.compile(r"\b(\w+)(?:\s+\1\b){1,}", re.IGNORECASE)

# "Mr. and Mrs. Gardiner" -- two titled people sharing one surname. The model
# drops the first half and leaves one person where the source had a couple.
# Words carrying more than one sense, only one of which is about gender.
# TransformService._SENSE_RULES resolves the frames that can be read off the
# surrounding words; anything left over is reported for a human to decide
# rather than guessed at.
_POLYSEMOUS: dict[str, frozenset] = {
    "nonbinary": frozenset({"master", "mistress", "sir", "madam", "ma'am"}),
}

# A title left standing with no surname after it. "Mx." needs a name, so this is
# never valid English however the vocative is finally resolved. The safety net
# repairs it by restoring the source word, but only where the vocative slots in
# source and output line up; where they do not it survives, and it must be
# reported rather than shipped.
#
# Case-insensitive on purpose: the model wrote the title in lower case in 19 of
# the 22 sites that shipped ("Dear mx.,"), which is the worse form of the same
# error, not a different one.
_BARE_TITLE = re.compile(
    r"(?<![A-Za-z])(?:Mx|Mr|Mrs|Ms)\.(?=\s*(?:[,.;:!?\"'”’)\]]|$))", re.IGNORECASE
)

_COORDINATED_TITLES = re.compile(
    r"\b(?:Mr|Mrs|Ms|Mx|Miss)\.?\s+and\s+(?:Mr|Mrs|Ms|Mx|Miss)\.?\s+([A-Z]\w+)"
)

AUTO_FIXABLE = "auto_fixable"
NEEDS_REVIEW = "needs_review"
STRUCTURAL = "structural"

# A paragraph whose word count moves by more than this fraction is suspicious:
# the LLM either dropped a sentence or invented one.
LENGTH_DRIFT_THRESHOLD = 0.25

# Short paragraphs need an absolute budget too — 25% of a four-word line is one
# word, so a hallucinated sentence would slip through a purely relative check.
# Set above the couple of words the prompt's pronoun disambiguation may add.
MIN_ABSOLUTE_DRIFT = 6

# Words that read as gendered but carry no gender in the source text, so a
# residual occurrence is not a miss worth reporting.
_REVIEW_IGNORE = frozenset({"master", "mistress"})


@dataclass
class Finding:
    """One problem located precisely enough to go and look at it."""

    severity: str
    kind: str
    chapter: int
    paragraph: int
    detail: str
    excerpt: str = ""
    # The exact word the finding is about, where there is one. A person
    # reviewing this needs something to act on, and the detail line is prose.
    term: str = ""
    # The same passage in the source. Without it a reader cannot tell a name
    # the transform correctly produced from one it failed to change: the last
    # chapter's "Mr. Darcy" is right because the source said "Mrs. Darcy", and
    # shown alone it looks exactly like a miss.
    source_excerpt: str = ""
    # Where in the transformed paragraph this is, so a correction lands on
    # the occurrence that was reported rather than every one that looks
    # like it.
    offset: int = -1
    # What to put there, where the answer is known. A person accepting a
    # suggestion is faster and less error-prone than one retyping it.
    suggestion: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "kind": self.kind,
            "chapter": self.chapter,
            "paragraph": self.paragraph,
            "detail": self.detail,
            "excerpt": self.excerpt,
            "term": self.term,
            "source_excerpt": self.source_excerpt,
            "offset": self.offset,
            "suggestion": self.suggestion,
        }


@dataclass
class ChapterReport:
    """Per-chapter totals, so a bad chapter stands out from a good book."""

    number: int
    title: str
    paragraphs: int = 0
    gendered_words: int = 0
    transformed_words: int = 0
    findings: list[Finding] = field(default_factory=list)

    @property
    def coverage(self) -> float:
        """Fraction of gendered words that actually changed."""
        if not self.gendered_words:
            return 1.0
        return self.transformed_words / self.gendered_words

    def count(self, severity: str) -> int:
        return sum(1 for f in self.findings if f.severity == severity)

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "title": self.title,
            "paragraphs": self.paragraphs,
            "gendered_words": self.gendered_words,
            "transformed_words": self.transformed_words,
            "coverage": round(self.coverage, 4),
            "auto_fixable": self.count(AUTO_FIXABLE),
            "needs_review": self.count(NEEDS_REVIEW),
            "structural": self.count(STRUCTURAL),
            "findings": [f.to_dict() for f in self.findings],
        }


@dataclass
class QCReport:
    """The whole-book result."""

    transform_type: str
    chapters: list[ChapterReport] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    @property
    def all_findings(self) -> list[Finding]:
        return self.findings + [f for c in self.chapters for f in c.findings]

    def count(self, severity: str) -> int:
        return sum(1 for f in self.all_findings if f.severity == severity)

    @property
    def coverage(self) -> float:
        gendered = sum(c.gendered_words for c in self.chapters)
        if not gendered:
            return 1.0
        return sum(c.transformed_words for c in self.chapters) / gendered

    def to_dict(self) -> dict[str, Any]:
        return {
            "transform_type": self.transform_type,
            "coverage": round(self.coverage, 4),
            "totals": {
                AUTO_FIXABLE: self.count(AUTO_FIXABLE),
                NEEDS_REVIEW: self.count(NEEDS_REVIEW),
                STRUCTURAL: self.count(STRUCTURAL),
            },
            "book_findings": [f.to_dict() for f in self.findings],
            "chapters": [c.to_dict() for c in self.chapters],
        }


class QCService:
    """Compares a transformed book against its source, chapter by chapter."""

    def __init__(
        self,
        transform_type: TransformType,
        name_map: Optional[dict[str, str]] = None,
        cast: Optional[list] = None,
    ):
        self.transform_type = transform_type
        self.key = transform_type.value
        # Renaming is driven by character analysis, not the term map, so QC is
        # blind to it unless the map used for the run is handed over.
        self.name_map = {k: v for k, v in (name_map or {}).items() if k.lower() != v.lower()}
        self._name_pattern = (
            re.compile(
                r"(?<![A-Za-z'])(?:"
                + "|".join(re.escape(name) for name in sorted(self.name_map, key=len, reverse=True))
                + r")(?![A-Za-z'])"
            )
            if self.name_map
            else None
        )
        # The map read one word at a time. "Elizabeth Bennet" -> "Edward Bennet"
        # says Elizabeth becomes Edward and Bennet stays Bennet, and that is
        # what makes it possible to see the model calling her something else.
        # Only same-length pairs line up word for word; the rest are skipped.
        self._expected_word: dict[str, set] = {}
        for original, replacement in self.name_map.items():
            before = TransformService._WORD_RE.findall(original)
            after = TransformService._WORD_RE.findall(replacement)
            if len(before) != len(after) or not before:
                continue
            # Only proper nouns, and only entries free of honorifics on both
            # sides. An entry like "Miss Elizabeth" -> "Edward Bennet" has the
            # same word count and still does not line up word for word: it
            # pairs Elizabeth with Bennet and teaches this that her name is
            # supposed to become her surname. Aliases like "her sister" bring
            # pronouns and kinship nouns in the same way, which is the term
            # map's territory, not a question of identity.
            words = [w.lower() for w in before + after]
            if any(w in TransformService._HONORIFICS for w in words):
                continue
            if not all(w[:1].isupper() for w in before + after):
                continue
            for source_word, target_word in zip(before, after):
                self._expected_word.setdefault(source_word.lower(), set()).add(target_word.lower())
        # The family names in this cast. A capitalised one is a person even
        # when the word means something else: "Miss King" is Mary King, and
        # the transform protects her for exactly this reason.
        # Taken from the cast where it is available, because the map only
        # holds people who are being renamed -- and Mary King is not, in an
        # all_female book, so nothing in the map says "King" is anybody's
        # family name.
        self._surnames = set()
        for original in list(cast or []) + list(self.name_map):
            if "'" in original or "\u2019" in original:
                continue  # "Elizabeth's Uncle" describes a person, not names one
            words = TransformService._WORD_RE.findall(original)
            kept = [
                w
                for w in words
                if w[:1].isupper()
                and w.lower() not in TransformService._HONORIFICS
                and w.lower() not in TransformService._RANKS
            ]
            # Only a full name tells you which word is the family name. "Mr.
            # Darcy" and "Sir William" have the same shape and opposite
            # answers -- Darcy is a surname, William a given name -- so a
            # titled short form is skipped and the surname comes from
            # "Fitzwilliam Darcy" or "Sir William Lucas" instead.
            if len(kept) > 1:
                self._surnames.add(kept[-1])

        self._exchange_targets = {
            name for name in self.name_map if name in set(self.name_map.values())
        }
        # Honorifics join the alignment vocabulary even though they carry no
        # expectation of their own. The aligner anchors on words outside the
        # vocabulary, and a swap changes "Mr." to "Mrs." -- so leaving them as
        # anchors shifts the whole stream by one and pairs the wrong names.
        # That is how a correct "Mr. Darcy / Miss Bingley" -> "Mrs. Darcy /
        # Mr. Bingley" was reported as Darcy becoming Bingley.
        self._name_words = (
            frozenset(self._expected_word)
            | {word for words in self._expected_word.values() for word in words}
            | TransformService._HONORIFICS
        )

        # Borrowed rather than duplicated: QC must judge the transform against
        # the same vocabulary the transform itself uses, or the two drift apart.
        self._transform = TransformService.__new__(TransformService)
        self._term_map = TransformService._effective_term_map(self.key)
        self._vocabulary = TransformService._gendered_vocabulary(self.key)
        self._nouns = TransformService._gendered_nouns(self.key)
        self._contextual = TransformService._CONTEXTUAL_PRONOUNS.get(self.key, {})
        # Words this transform would actually rewrite. The vocabulary is wider —
        # it includes "they"/"them", which are already neutral and must not be
        # counted as misses when a gender_swap leaves them alone.
        self._changeable = frozenset(self._term_map) | frozenset(self._contextual)

    # ------------------------------------------------------------------ public

    def check_book(self, source: dict, transformed: dict) -> QCReport:
        """Run every check over a source/transformed pair of book dictionaries."""
        report = QCReport(transform_type=self.key)
        source_chapters = source.get("chapters", [])
        output_chapters = transformed.get("chapters", [])
        self._source_charset = self._charset(source_chapters)

        if len(source_chapters) != len(output_chapters):
            report.findings.append(
                Finding(
                    STRUCTURAL,
                    "chapter_count",
                    0,
                    0,
                    f"source has {len(source_chapters)} chapters, "
                    f"transformed has {len(output_chapters)}",
                )
            )

        for index, (source_chapter, output_chapter) in enumerate(
            zip(source_chapters, output_chapters)
        ):
            report.chapters.append(self.check_chapter(index, source_chapter, output_chapter))

        self._check_invented_names(report, source_chapters, output_chapters)
        self._check_renames_landed(report, source_chapters, output_chapters)
        self._check_surnames_survive(report, source_chapters, output_chapters)
        return report

    def _check_surnames_survive(self, report: QCReport, source_chapters, output_chapters) -> None:
        """A family name the book stopped using.

        A rename changes a given name. The surname is the one part that must
        come through untouched, and nothing else here would notice it going:
        every gendered word can be correct, every agreed name can have landed,
        and the book can still have replaced "Come, Darcy" with "Come,
        Fitzwillia" three hundred times because a surname was listed as an
        alias and took the given name meant for a nickname.

        Counted rather than aligned. A surname is used too often, in too many
        shapes, for position to be reliable -- but it cannot quietly lose most
        of its mentions.
        """
        if not self.name_map:
            return
        surnames = set(self._surnames)

        source_text = "\n".join(
            _text_of(p) for c in source_chapters for p in c.get("paragraphs", [])
        )
        output_text = "\n".join(
            _text_of(p) for c in output_chapters for p in c.get("paragraphs", [])
        )
        for surname in sorted(surnames):
            before = self._word_count(source_text, surname)
            if before < 10:
                continue  # too rare to judge by count
            after = self._word_count(output_text, surname)
            if after < before * 0.6:
                report.findings.append(
                    Finding(
                        STRUCTURAL,
                        "surname_lost",
                        0,
                        0,
                        f"{surname!r} is a family name used {before}x in the source and "
                        f"only {after}x in the transform: a rename changes given names, "
                        f"never the surname",
                    )
                )

    @staticmethod
    def _word_count(text: str, word: str) -> int:
        return len(
            re.findall(rf"(?<![A-Za-z']){re.escape(word)}(?![A-Za-z'])", text, re.IGNORECASE)
        )

    def _check_renames_landed(self, report: QCReport, source_chapters, output_chapters) -> None:
        """A character the book stopped calling anything the map recognises.

        _check_invented_names can only see a substitute name that happens to
        belong to some other character. When the model coins a brand new one it
        is not in any vocabulary, so nothing aligns to it and the paragraph
        checks stay silent: Elizabeth became "Elliot" 34 times without a single
        finding. Counting catches it -- 35 mentions in the source, 3 of the
        agreed "Edward" in the transform, 2 left as "Elizabeth", and 30 gone
        somewhere with no name at all.

        A name legitimately gives way to a pronoun sometimes, so this wants a
        real shortfall rather than any shortfall.
        """
        if not self._expected_word:
            return
        source_text = "\n".join(
            _text_of(p) for c in source_chapters for p in c.get("paragraphs", [])
        )
        output_text = "\n".join(
            _text_of(p) for c in output_chapters for p in c.get("paragraphs", [])
        )
        for word, targets in sorted(self._expected_word.items()):
            if word in targets:
                continue  # a surname that does not change
            in_source = self._word_count(source_text, word)
            if in_source < 3:
                continue
            landed = max(self._word_count(output_text, target) for target in targets)
            survived = self._word_count(output_text, word)
            missing = in_source - (landed + survived)
            if missing >= 3 and missing >= in_source * 0.3:
                agreed = "/".join(sorted(targets))
                report.findings.append(
                    Finding(
                        STRUCTURAL,
                        "rename_lost",
                        0,
                        0,
                        f"{word!r} appears {in_source}x in the source, but the agreed "
                        f"{agreed!r} appears only {landed}x and {word!r} {survived}x: "
                        f"{missing} mentions are called something else",
                    )
                )

    def _check_invented_names(self, report: QCReport, source_chapters, output_chapters) -> None:
        """A character called by a name the engine never chose.

        The engine settles each character's new name once, before any chapter
        is transformed, so that the whole book agrees. When the model renames
        on its own instead, the deterministic map that runs afterwards finds
        nothing left to rewrite, and the book ends up with two names for one
        person -- Elizabeth came out of a five-chapter run as "Elliot" 34 times
        and "Edward Bennet" 3 times. Coverage was 99.7%: every gendered word
        was correct, and the protagonist still had two names.

        Reported once per pair rather than once per occurrence, because 34
        findings that say the same thing bury the other 3.
        """
        if not self._expected_word:
            return
        counts: dict[tuple, int] = {}
        where: dict[tuple, tuple] = {}
        for source_chapter, output_chapter in zip(source_chapters, output_chapters):
            number = output_chapter.get("number", 0)
            for position, (source_paragraph, output_paragraph) in enumerate(
                zip(source_chapter.get("paragraphs", []), output_chapter.get("paragraphs", []))
            ):
                source = _text_of(source_paragraph)
                output = _text_of(output_paragraph)
                # A name is only missing if it is missing. Word alignment is
                # fragile exactly here -- titles change length under a swap, so
                # the streams slip by one and pair the wrong names -- and this
                # check blocks a book from printing. So the alignment only
                # nominates a suspect; the paragraph decides. If the source
                # name is still somewhere in the transformed paragraph, nobody
                # lost their identity and there is nothing to report.
                # Normalised the way the aligner normalises, or the two do not
                # agree on what a word is: "Wickham’s" in the source and
                # "Wickham's" in the output are one word each to the pattern,
                # so a bare "wickham" is never found and every possessive reads
                # as a lost name.
                present = {
                    TransformService._fold_apostrophe(
                        TransformService._CLITIC_RE.sub("", w).lower()
                    )
                    for w in TransformService._WORD_RE.findall(output)
                }
                for source_word, output_word, span, _ in TransformService.align_vocabulary(
                    source, output, self._name_words
                ):
                    if source_word is None or source_word not in self._expected_word:
                        continue
                    expected = self._expected_word[source_word]
                    if output_word in expected or output_word == source_word:
                        continue
                    if source_word in present or expected & present:
                        continue
                    pair = (source_word, output_word)
                    counts[pair] = counts.get(pair, 0) + 1
                    where.setdefault(pair, (number, position, _excerpt(output, span[0])))

        for (source_word, output_word), count in sorted(counts.items(), key=lambda kv: -kv[1]):
            number, position, excerpt = where[(source_word, output_word)]
            agreed = "/".join(sorted(self._expected_word[source_word]))
            report.findings.append(
                Finding(
                    STRUCTURAL,
                    "invented_name",
                    number,
                    position,
                    f"{source_word!r} became {output_word!r} {count}x, "
                    f"but the name map says {agreed!r}",
                    excerpt,
                )
            )

    def check_chapter(self, index: int, source: dict, transformed: dict) -> ChapterReport:
        """Run every check over one chapter."""
        number = transformed.get("number", index + 1)
        chapter = ChapterReport(number=number, title=transformed.get("title") or "")

        source_paragraphs = source.get("paragraphs", [])
        output_paragraphs = transformed.get("paragraphs", [])
        chapter.paragraphs = len(output_paragraphs)

        if len(source_paragraphs) != len(output_paragraphs):
            chapter.findings.append(
                Finding(
                    STRUCTURAL,
                    "paragraph_count",
                    number,
                    0,
                    f"source has {len(source_paragraphs)} paragraphs, "
                    f"transformed has {len(output_paragraphs)}",
                )
            )

        self._check_continuity(chapter, number, source_paragraphs)

        for position, (source_paragraph, output_paragraph) in enumerate(
            zip(source_paragraphs, output_paragraphs)
        ):
            self._check_paragraph(
                chapter,
                number,
                position,
                _text_of(source_paragraph),
                _text_of(output_paragraph),
            )
        return chapter

    # ----------------------------------------------------------------- checks

    def _check_paragraph(
        self, chapter: ChapterReport, number: int, position: int, source: str, output: str
    ) -> None:
        if not source.strip():
            return

        aligned = [
            entry
            for entry in TransformService.align_gendered_words(source, output, self.key)
            if entry[0] in self._changeable
        ]
        residual = [entry for entry in aligned if entry[0] == entry[1]]

        chapter.gendered_words += len(aligned)
        chapter.transformed_words += len(aligned) - len(residual)

        repaired = self._transform._apply_term_map(output, self.transform_type, source_text=source)

        self._check_length_drift(chapter, number, position, source, output)
        self._check_untransformed(
            chapter, number, position, source, output, aligned, residual, repaired
        )
        self._check_auto_fixable(chapter, number, position, output, repaired)
        self._check_pair_gender(chapter, number, position, source, output)
        self._check_names(chapter, number, position, source, output)
        self._check_residual_terms(chapter, number, position, output, residual, source)
        self._check_text_integrity(chapter, number, position, source, output)
        self._check_coordination(chapter, number, position, source, output)
        self._check_collapsed_contrast(chapter, number, position, source, output)
        self._check_polysemy(chapter, number, position, output)
        self._check_bare_title(chapter, number, position, repaired)

    def _check_bare_title(
        self, chapter: ChapterReport, number: int, position: int, repaired: str
    ) -> None:
        """A title with no name left after the safety net has run.

        Checked against the repaired text, not the raw output: anything the net
        can put right is already reported as auto_fixable. What reaches here is
        what it could not align -- the source and output vocative slots
        disagreed -- so no rule can decide it and a person has to.
        """
        for match in _BARE_TITLE.finditer(repaired):
            chapter.findings.append(
                Finding(
                    NEEDS_REVIEW,
                    "bare_title",
                    number,
                    position,
                    f"{match.group(0)!r} has no name after it — a title cannot stand alone",
                    _excerpt(repaired, match.start()),
                )
            )

    def _check_polysemy(
        self, chapter: ChapterReport, number: int, position: int, output: str
    ) -> None:
        """A word whose sense the rules could not determine, left for a person.

        "master" is an employer, a teacher, a household head, a proprietor, and
        half of the "his own master" idiom. Mapping it blindly produced "they
        are their own owner" and "a London owner". So the sense-scoped rules
        take the frames they can read, and whatever survives is surfaced here
        instead of being silently rewritten.
        """
        terms = _POLYSEMOUS.get(self.key)
        if not terms:
            return
        # Tokenise with the apostrophe inside the word. A plain \b[A-Za-z]+\b
        # splits "ma'am" into "ma" and "am", so those sites were unreachable.
        for match in TransformService._WORD_RE.finditer(output):
            word = match.group(0).lower().replace("’", "'")
            if word not in terms:
                continue
            chapter.findings.append(
                Finding(
                    NEEDS_REVIEW,
                    "polysemous_term",
                    number,
                    position,
                    f"{word!r} has senses the rules cannot tell apart — decide by hand",
                    _excerpt(output, match.start()),
                )
            )

    def _check_coordination(
        self, chapter: ChapterReport, number: int, position: int, source: str, output: str
    ) -> None:
        """A coordinated pair of titled people collapsed into one.

        "go after Mr. and Mrs. Gardiner" came back as "go after Mr. Gardiner"
        in the gender_swap, all_male and all_female editions -- three separate
        runs, the same sentence, a couple turned into one person each time. The
        honorifics that remain are all correct, so no gender-aware check sees
        anything wrong; only the missing person is wrong.
        """
        expected = _COORDINATED_TITLES.findall(source)
        if not expected:
            return

        # Count people, not phrasing. Where a collision was resolved by giving
        # one of them a name, the pair survives as "Mr. Gardiner and Mr. Edmund
        # Gardiner" -- which is both of them, correctly, and matches no
        # "Title and Title Surname" pattern at all. Insisting on the shape
        # reported eighteen losses in a book that had lost nobody.
        titles = r"(?:Mr|Mrs|Ms|Mx|Miss|Lady|Lord|Sir|Dame)"

        def titled_mentions(text: str, surname: str) -> int:
            """How many distinct people the text names with a title.

            Two shapes count. "Mr. Edmund Gardiner" names one outright. And a
            title handed straight to another title -- "Mr. and Mrs. Gardiner"
            -- names one more, sharing the surname that follows.
            """
            # "Mr. Gardiner" names one. So does "Winifred Collins": once a
            # collision is resolved by giving somebody a name, the pair can
            # survive with no title on either half.
            named = len(
                re.findall(
                    r"\b(?:"
                    + titles
                    + r"\.?|[A-Z]\w+)\s+(?:[A-Z]\w+\s+)?"
                    + re.escape(surname)
                    + r"\b",
                    text,
                )
            )
            sharing = len(
                re.findall(r"\b" + titles + r"\.?\s+and\s+(?=" + titles + r"\.?\s)", text)
            )
            return named + sharing

        lost = Counter()
        for surname, wanted in Counter(expected).items():
            # Each coordination in the source names two people.
            if titled_mentions(output, surname) < wanted * 2:
                lost[surname] = wanted
        for surname, count in lost.items():
            chapter.findings.append(
                Finding(
                    STRUCTURAL,
                    "dropped_coordination",
                    number,
                    position,
                    f"source pairs two titled people as '... and ... {surname}'; "
                    f"the transform leaves one ({count} lost)",
                    _excerpt(output, max(0, output.find(surname))),
                )
            )

    def _degenerate_repeat(self, source: str, output: str):
        """A word repeated back to back that the source does not repeat.

        Two different source words can legitimately collapse onto one target --
        a gender_swap turns "got him his commission" into "got her her
        commission" -- so a repeat of anything this transform writes is not
        evidence of anything. Only repeats of ordinary words are.
        """
        targets = {t.lower() for t in self._term_map.values()}
        for pair in self._contextual.values():
            targets.update(t.lower() for t in pair)
        for match in _REPEATED_WORD.finditer(output):
            word = match.group(1).lower()
            if word in targets:
                continue
            if re.search(
                r"\b" + re.escape(word) + r"(?:\s+" + re.escape(word) + r")\b", source, re.I
            ):
                continue
            return match
        return None

    @staticmethod
    def _charset(chapters: list) -> frozenset:
        """Every character the source book uses."""
        seen: set = set()
        for chapter in chapters:
            for paragraph in chapter.get("paragraphs", []):
                seen.update(_text_of(paragraph))
        return frozenset(seen)

    def _check_text_integrity(
        self, chapter: ChapterReport, number: int, position: int, source: str, output: str
    ) -> None:
        """Characters and repetition the model invented — corruption, not gender.

        A transform rewrites words; it has no reason to introduce a character
        the source never used. The printed all_male Pride and Prejudice carries
        a paragraph where the model fell into a repetition loop and emitted CJK
        (`when when I when I tell 当 ...`), and every gender-aware gate passed
        it, because nothing in it is gendered. This is the gate that catches it.
        """
        charset = getattr(self, "_source_charset", None)
        if charset is not None:
            # Straight quotes are a deliberate export choice, not corruption.
            allowed = charset | set(_EXPORT_PUNCTUATION)
            alien = {c for c in output if c not in allowed and not c.isascii()}
            if alien:
                shown = " ".join(f"{c!r} (U+{ord(c):04X})" for c in sorted(alien)[:5])
                chapter.findings.append(
                    Finding(
                        STRUCTURAL,
                        "alien_character",
                        number,
                        position,
                        f"character(s) absent from the source: {shown}",
                        _excerpt(output, output.index(sorted(alien)[0])),
                    )
                )

        repeat = self._degenerate_repeat(source, output)
        if repeat:
            chapter.findings.append(
                Finding(
                    STRUCTURAL,
                    "repetition_loop",
                    number,
                    position,
                    f"{repeat.group(1)!r} repeated back to back, and not in the source",
                    _excerpt(output, repeat.start()),
                )
            )

    def _check_continuity(self, chapter: ChapterReport, number: int, paragraphs: list) -> None:
        """Paragraphs that are really one sentence cut in half.

        Illustrated Gutenberg editions place plates mid-sentence; stripping the
        plate can leave the blank lines around it and split the paragraph. The
        break shows up as an indent mid-sentence in print, and the transform
        sees a fragment ending on a bare possessive with its noun in a different
        paragraph. Checked against the source, since the split is inherited from
        the parse rather than introduced by the transform.
        """
        for position in range(len(paragraphs) - 1):
            before = _text_of(paragraphs[position]).strip()
            after = _text_of(paragraphs[position + 1]).strip()
            if not before or not after:
                continue
            if (before[-1].isalnum() or before[-1] in ",;:-—") and after[0].islower():
                chapter.findings.append(
                    Finding(
                        STRUCTURAL,
                        "split_sentence",
                        number,
                        position,
                        f"paragraph ends mid-sentence and the next opens lower case: "
                        f"{before[-40:]!r} + {after[:40]!r}",
                        _excerpt(after, 0),
                    )
                )

    def _check_length_drift(
        self, chapter: ChapterReport, number: int, position: int, source: str, output: str
    ) -> None:
        """Catch truncated, padded or emptied paragraphs — a partial LLM response.

        An empty output is always a finding: it is the signature of the old
        batch parser padding a short response, which deleted paragraphs from the
        book outright. Short paragraphs are held to an absolute word budget as
        well as a relative one, so a four-word line cannot quietly grow by
        twenty without tripping the check.
        """
        source_words = len(source.split())
        output_words = len(output.split())

        if source_words and not output_words:
            chapter.findings.append(
                Finding(
                    STRUCTURAL,
                    "empty_paragraph",
                    number,
                    position,
                    f"output is empty; source has {source_words} words",
                    _excerpt(source, 0),
                )
            )
            return

        if not source_words:
            return

        delta = abs(output_words - source_words)
        allowed = max(MIN_ABSOLUTE_DRIFT, LENGTH_DRIFT_THRESHOLD * source_words)
        if delta > allowed:
            chapter.findings.append(
                Finding(
                    STRUCTURAL,
                    "length_drift",
                    number,
                    position,
                    f"word count moved by {delta} ({source_words} -> {output_words})",
                    _excerpt(output, 0),
                )
            )

    def _check_untransformed(
        self,
        chapter: ChapterReport,
        number: int,
        position: int,
        source: str,
        output: str,
        aligned: list,
        residual: list,
        repaired: str,
    ) -> None:
        """A paragraph that came through byte-identical despite carrying gender."""
        if aligned and len(residual) == len(aligned) and source.strip() == output.strip():
            chapter.findings.append(
                Finding(
                    AUTO_FIXABLE if repaired != output else NEEDS_REVIEW,
                    "untransformed_paragraph",
                    number,
                    position,
                    f"paragraph is identical to source but holds {len(aligned)} gendered words",
                    _excerpt(output, 0),
                )
            )

    def _check_auto_fixable(
        self, chapter: ChapterReport, number: int, position: int, output: str, repaired: str
    ) -> None:
        """Report whatever the safety net would still change.

        On text from the current pipeline the answer is nothing, because the net
        has already run. Any finding here means the text predates the fix.
        """
        if repaired == output:
            return
        for before, after in _word_diffs(output, repaired):
            chapter.findings.append(
                Finding(
                    AUTO_FIXABLE,
                    "safety_net_would_change",
                    number,
                    position,
                    f"{before!r} -> {after!r}",
                    _excerpt(output, output.find(before)),
                )
            )

    def _check_pair_gender(
        self, chapter: ChapterReport, number: int, position: int, source: str, output: str
    ) -> None:
        """The "her husband" case: a possessive pronoun and its noun must agree.

        Checking only whether each half *moved* is not enough — "his lady" can
        become "her wife", where both halves moved and the phrase is still wrong.
        So this compares the gender each half actually lands on against the
        gender the transform calls for. In all_female "his wife" correctly
        becomes "her wife" (both female); in gender_swap it must become
        "her husband" (female possessor, male noun).
        """
        if not self._contextual:
            return
        pronouns = "|".join(self._contextual)
        pattern = re.compile(rf"\b({pronouns})\s+([A-Za-z']+)", re.IGNORECASE)

        # Keyed by position in the *source*, because that is where a pair's
        # pronoun and noun are located; the output spans have already shifted by
        # however much the words around them changed length.
        aligned = {
            source_span: (source_word, output_word, output_span)
            for source_word, output_word, output_span, source_span in (
                TransformService.align_gendered_words(source, output, self.key)
            )
            if source_word is not None
        }

        for match in pattern.finditer(source):
            if match.group(2).lower() not in self._term_map:
                continue
            pronoun = aligned.get(match.span(1))
            noun = aligned.get(match.span(2))
            if pronoun is None or noun is None:
                continue

            problems = []
            for role, (source_word, output_word, _span) in (
                ("pronoun", pronoun),
                ("noun", noun),
            ):
                wanted = TransformService.expected_gender(
                    self.key, TransformService.gender_of(source_word)
                )
                if wanted is None:
                    continue
                landed = TransformService.gender_of(output_word)
                if wanted == "neutral":
                    if landed is not None:
                        problems.append(f"{role} {output_word!r} is still {landed}")
                elif landed != wanted:
                    problems.append(
                        f"{role} {source_word!r} became {output_word!r} "
                        f"({landed or 'neutral'}, wanted {wanted})"
                    )

            if problems:
                chapter.findings.append(
                    Finding(
                        NEEDS_REVIEW,
                        "pair_gender",
                        number,
                        position,
                        f"{match.group(0)!r}: " + "; ".join(problems),
                        _excerpt(output, noun[2][0]),
                    )
                )

    def _check_names(
        self, chapter: ChapterReport, number: int, position: int, source: str, output: str
    ) -> None:
        """A character name that should have been replaced but survived.

        Nothing in the term map knows about character names, so a run can score
        100% on gendered words while still calling a renamed character by their
        original name.
        """
        if self._name_pattern is None:
            return
        present = {m.group(0) for m in self._name_pattern.finditer(source)}
        if not present:
            return
        for match in self._name_pattern.finditer(output):
            name = match.group(0)
            # This exact name has to have been in the source. Asking only
            # whether *some* mapped name was there flags a name the transform
            # correctly produced: the last chapter reads "talked of Mrs.
            # Darcy" of Elizabeth, a swap turns her into Mr. Darcy, and Mr.
            # Darcy is also a map key -- so a correct sentence was reported as
            # an un-renamed one, and acting on it would have been an error.
            if name not in present:
                continue
            # "Mrs. Bennet" in the output of a swap is not a missed rename: it
            # is what "Mr. Bennet" became. A name that is somebody's target
            # belongs in the text, and only the paragraph's other checks can
            # say whether it landed on the right person.
            if name in self._exchange_targets:
                continue
            chapter.findings.append(
                Finding(
                    NEEDS_REVIEW,
                    "residual_name",
                    number,
                    position,
                    f"{name!r} was not renamed to {self.name_map[name]!r}",
                    _excerpt(output, match.start()),
                    term=name,
                    source_excerpt=_excerpt(source, _nearest(source, name, match.start())),
                    offset=match.start(),
                )
            )

    # "my mother" / "your father" -- a possessive and the person it owns.
    # The trailing guard keeps a noun out of a compound: "my brother-in-law" is
    # not a possessive and "brother", and reporting it wastes the reader's time.
    _POSSESSED = re.compile(
        r"\b(my|your|his|her|their|our)\s+([A-Za-z]+)(?![A-Za-z-])", re.IGNORECASE
    )

    _SENTENCE_END = re.compile(r"(?<=[.!?\"\u201d]) +")

    # "his uncle and uncle" -- the same relation twice, joined. A plural says
    # it properly.
    # " and aunt" following "her uncle": the second half of a shared possessive.
    _COORDINATED_TAIL = re.compile(r"\s+and\s+([A-Za-z]+)(?![A-Za-z-])", re.IGNORECASE)

    _COORDINATED_PAIR = re.compile(
        r"\b(my|your|his|her|their|our)\s+([A-Za-z]+)\s+and\s+(?:\1\s+)?\2(?![A-Za-z-])",
        re.IGNORECASE,
    )

    def _check_collapsed_contrast(
        self, chapter: ChapterReport, number: int, position: int, source: str, output: str
    ) -> None:
        """Two people the source told apart, that the transform gives one name.

        In an all-male book Elizabeth has two fathers, and "his father" is the
        right words for each of them -- this is not about that. It is about the
        sentence that leans on the contrast: "My mother would have no
        objection, but my father hates London" becomes "My father would have no
        objection, but my father hates London", and a reader cannot tell which
        father is meant.

        Both words transformed correctly, so nothing else here has anything to
        report: there is no residual term, no missed name, no drift in length.
        Only the collision of the two is wrong, and only a person can settle it.

        Three sentences in Pride and Prejudice, which is why it is worth
        surfacing and not worth a rule.
        """
        nouns = self._nouns
        if not nouns:
            return

        def possessed(text):
            found = []
            for match in self._POSSESSED.finditer(text):
                owner, noun = match.group(1).lower(), match.group(2).lower()
                if noun not in nouns:
                    continue
                found.append((owner, noun, match.start()))
                # A coordination usually states the possessive once: "her uncle
                # and aunt", not "her uncle and her aunt". The second noun is
                # owned by the same word and has to be counted, or the pair
                # that reads worst is the one that goes unreported.
                tail = self._COORDINATED_TAIL.match(text, match.end())
                if tail and tail.group(1).lower() in nouns:
                    found.append((owner, tail.group(1).lower(), tail.start(1)))
            return found

        before, after = possessed(source), possessed(output)
        # Without a one-to-one correspondence there is no way to say which
        # phrase became which, and a guess here would be a false accusation.
        if len(before) != len(after) or not after:
            return

        # Which sentence each offset falls in. A reader holds a sentence in
        # mind, not a paragraph: two mentions pages apart are usually two
        # different people and read perfectly well.
        bounds = [m.end() for m in self._SENTENCE_END.finditer(output)]

        def sentence_of(offset: int) -> int:
            return sum(1 for b in bounds if b <= offset)

        seen: dict[tuple, tuple] = {}
        for (_owner_b, noun_b, _start_b), (owner_a, noun_a, start_a) in zip(before, after):
            key = (owner_a, noun_a)
            earlier = seen.get(key)
            if earlier and earlier[0] != noun_b and sentence_of(earlier[1]) == sentence_of(start_a):
                detail = (
                    f"{earlier[0]!r} and {noun_b!r} both became "
                    f"{owner_a!r} {noun_a!r}, so the two cannot be told apart"
                )
                term = f"{owner_a} {noun_a}"
                suggestion = ""
                # Where the two sit side by side -- "her uncle and aunt" giving
                # "his uncle and uncle" -- English has a better answer than
                # either of them: one plural. Offer the whole phrase as the
                # thing to replace, so it takes one edit rather than two that
                # would each rewrite the other.
                # Anchored on the occurrence being reported, not on the first
                # one in the paragraph. Chapter 61 says "his aunt" of Lady
                # Catherine early, and "her uncle and aunt" of the Gardiners
                # much later; searching from the first found nothing, the
                # phrase was never offered, and correcting the bare word
                # rewrote Lady Catherine too.
                joined = next(
                    (
                        m
                        for m in self._COORDINATED_PAIR.finditer(output)
                        if m.start() <= start_a < m.end()
                    ),
                    None,
                )
                if joined:
                    term = joined.group(0)
                    suggestion = f"{owner_a} {noun_a}s"
                    detail += f'; "{suggestion}" would read better'
                chapter.findings.append(
                    Finding(
                        NEEDS_REVIEW,
                        "collapsed_contrast",
                        number,
                        position,
                        detail,
                        _excerpt(output, start_a),
                        term=term,
                        source_excerpt=_excerpt(source, _start_b),
                        offset=joined.start() if joined else start_a,
                        suggestion=suggestion,
                    )
                )
            elif not earlier:
                seen[key] = (noun_b, start_a)

    def _check_residual_terms(
        self,
        chapter: ChapterReport,
        number: int,
        position: int,
        output: str,
        residual: list,
        source: str = "",
    ) -> None:
        """Gendered words the LLM missed and the safety net declined to guess at."""
        protected = TransformService.protected_spans(output)
        for _source_word, word, span, source_span in residual:
            if word in _REVIEW_IGNORE:
                continue
            # A capitalised cast surname is a person, not a gendered word. The
            # transform already declines to touch "King" while still swapping
            # "king"; reporting it here asked a reader to rule on a monarch who
            # is actually Mary King.
            if output[span[0] : span[1]][:1].isupper() and word.capitalize() in self._surnames:
                continue
            if any(a <= span[0] and span[1] <= b for a, b in protected):
                continue
            if word not in self._term_map and word not in self._contextual:
                continue
            chapter.findings.append(
                Finding(
                    NEEDS_REVIEW,
                    "residual_pronoun" if word in self._contextual else "residual_term",
                    number,
                    position,
                    f"{word!r} left untransformed",
                    _excerpt(output, span[0]),
                    term=word,
                    source_excerpt=(
                        _excerpt(source, source_span[0]) if source and source_span else ""
                    ),
                    offset=span[0],
                )
            )


# --------------------------------------------------------------------- helpers


def _text_of(paragraph: Any) -> str:
    """Paragraphs are dicts of sentences in the JSON, plain strings elsewhere."""
    if isinstance(paragraph, str):
        return paragraph
    return " ".join(paragraph.get("sentences", []))


def _nearest(text: str, needle: str, position: int) -> int:
    """Where in `text` to look for `needle`, closest to `position`.

    A name often appears more than once in a paragraph. Taking the first
    occurrence put the source line and the transformed line at different
    points in the same paragraph, so the two did not describe the same moment
    and could not be compared -- which is the only reason a person is shown
    both.
    """
    places = [m.start() for m in re.finditer(re.escape(needle), text)]
    if not places:
        return 0
    return min(places, key=lambda start: abs(start - position))


def _excerpt(text: str, position: int, width: int = 70) -> str:
    """A window of text around `position`, for eyeballing the finding."""
    if position < 0:
        position = 0
    start = max(0, position - width // 2)
    end = min(len(text), start + width)
    prefix = "..." if start else ""
    suffix = "..." if end < len(text) else ""
    return f"{prefix}{text[start:end].strip()}{suffix}"


def _word_diffs(before: str, after: str) -> list[tuple]:
    """Word-level changes between two versions of the same text."""
    import difflib

    before_words = before.split()
    after_words = after.split()
    diffs = []
    matcher = difflib.SequenceMatcher(a=before_words, b=after_words, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "replace":
            diffs.append((" ".join(before_words[i1:i2]), " ".join(after_words[j1:j2])))
    return diffs


def load_book(path: str) -> dict:
    """Load a book JSON produced by the parser or the transform."""
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def format_report(report: QCReport, limit: int = 8) -> str:
    """Render a report as a terminal table plus a sample of findings."""
    lines = []
    lines.append(f"Transform: {report.transform_type}")
    lines.append(f"Coverage:  {report.coverage:.1%} of gendered words transformed")
    totals = report.to_dict()["totals"]
    lines.append(
        f"Findings:  {totals[AUTO_FIXABLE]} auto-fixable, "
        f"{totals[NEEDS_REVIEW]} need review, {totals[STRUCTURAL]} structural"
    )
    lines.append("")
    lines.append(
        f"{'Ch':>4}  {'Paras':>6}  {'Gendered':>9}  {'Coverage':>9}  "
        f"{'Auto':>5}  {'Review':>7}  {'Struct':>7}  Title"
    )
    lines.append("-" * 100)
    for chapter in report.chapters:
        flag = "  <-- " if chapter.count(AUTO_FIXABLE) or chapter.coverage < 0.9 else "  "
        lines.append(
            f"{chapter.number:>4}  {chapter.paragraphs:>6}  {chapter.gendered_words:>9}  "
            f"{chapter.coverage:>8.1%}  {chapter.count(AUTO_FIXABLE):>5}  "
            f"{chapter.count(NEEDS_REVIEW):>7}  {chapter.count(STRUCTURAL):>7}"
            f"{flag}{chapter.title[:40]}"
        )

    findings = report.all_findings
    if findings:
        lines.append("")
        kinds = Counter(f.kind for f in findings)
        lines.append("By kind: " + ", ".join(f"{k}={v}" for k, v in kinds.most_common()))
        for severity in (AUTO_FIXABLE, NEEDS_REVIEW, STRUCTURAL):
            sample = [f for f in findings if f.severity == severity][:limit]
            if not sample:
                continue
            lines.append("")
            lines.append(f"{severity} (showing {len(sample)}):")
            for finding in sample:
                lines.append(f"  ch{finding.chapter} p{finding.paragraph}  {finding.detail}")
                if finding.excerpt:
                    lines.append(f"      {finding.excerpt}")
    return "\n".join(lines)


def check_files(
    source_path: str,
    transformed_path: str,
    transform_type: TransformType,
    report_path: Optional[str] = None,
    name_map: Optional[dict[str, str]] = None,
) -> QCReport:
    """Compare two book JSON files, optionally writing the full report to disk."""
    report = QCService(transform_type, name_map=name_map).check_book(
        load_book(source_path), load_book(transformed_path)
    )
    if report_path:
        Path(report_path).parent.mkdir(parents=True, exist_ok=True)
        Path(report_path).write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    return report


def repair_book(source: dict, transformed: dict, transform_type: TransformType) -> dict:
    """Re-run the safety net over an existing transform, against its source.

    Every auto_fixable finding is a word the current safety net can settle on
    its own, so an edition produced before the net was fixed can be repaired
    from the JSON without paying for another LLM pass. Words the net will not
    guess at are left exactly as they are.
    """
    service = TransformService.__new__(TransformService)
    repaired = dict(transformed)
    repaired_chapters = []

    for index, output_chapter in enumerate(transformed.get("chapters", [])):
        source_chapter = (
            source.get("chapters", [])[index] if index < len(source.get("chapters", [])) else {}
        )
        source_paragraphs = source_chapter.get("paragraphs", [])
        chapter = dict(output_chapter)
        paragraphs = []

        for position, output_paragraph in enumerate(output_chapter.get("paragraphs", [])):
            text = _text_of(output_paragraph)
            if position < len(source_paragraphs):
                text = service._apply_term_map(
                    text, transform_type, source_text=_text_of(source_paragraphs[position])
                )
            paragraphs.append(text if isinstance(output_paragraph, str) else {"sentences": [text]})

        chapter["paragraphs"] = paragraphs
        repaired_chapters.append(chapter)

    repaired["chapters"] = repaired_chapters
    return repaired
