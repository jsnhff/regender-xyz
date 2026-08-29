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
AUTO_FIXABLE = "auto_fixable"
NEEDS_REVIEW = "needs_review"
STRUCTURAL = "structural"

# A paragraph whose word count moves by more than this fraction is suspicious:
# the LLM either dropped a sentence or invented one.
LENGTH_DRIFT_THRESHOLD = 0.25

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

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "kind": self.kind,
            "chapter": self.chapter,
            "paragraph": self.paragraph,
            "detail": self.detail,
            "excerpt": self.excerpt,
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

    def __init__(self, transform_type: TransformType):
        self.transform_type = transform_type
        self.key = transform_type.value
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
        return report

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
        self._check_partial_pairs(chapter, number, position, source, output)
        self._check_residual_terms(chapter, number, position, output, residual)

    def _check_length_drift(
        self, chapter: ChapterReport, number: int, position: int, source: str, output: str
    ) -> None:
        """Catch truncated or padded paragraphs — usually a partial LLM response."""
        source_words = len(source.split())
        if source_words < 20:
            return
        drift = abs(len(output.split()) - source_words) / source_words
        if drift > LENGTH_DRIFT_THRESHOLD:
            chapter.findings.append(
                Finding(
                    STRUCTURAL,
                    "length_drift",
                    number,
                    position,
                    f"word count moved {drift:.0%} ({source_words} -> {len(output.split())})",
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

    def _check_partial_pairs(
        self, chapter: ChapterReport, number: int, position: int, source: str, output: str
    ) -> None:
        """The "her husband" case: a possessive pronoun and its noun disagreeing.

        Both halves of "her husband" have to move together. If exactly one of
        them changed, the phrase is incoherent even though each word on its own
        looks transformed.
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
            if match.group(2).lower() not in self._nouns:
                continue
            pronoun = aligned.get(match.span(1))
            noun = aligned.get(match.span(2))
            if pronoun is None or noun is None:
                continue
            pronoun_moved = pronoun[0] != pronoun[1]
            noun_moved = noun[0] != noun[1]
            if pronoun_moved != noun_moved:
                moved, stayed = (pronoun, noun) if pronoun_moved else (noun, pronoun)
                chapter.findings.append(
                    Finding(
                        NEEDS_REVIEW,
                        "partial_pair",
                        number,
                        position,
                        f"{match.group(0)!r}: {moved[0]!r} became {moved[1]!r} "
                        f"but {stayed[0]!r} did not change",
                        _excerpt(output, noun[2][0]),
                    )
                )

    def _check_residual_terms(
        self, chapter: ChapterReport, number: int, position: int, output: str, residual: list
    ) -> None:
        """Gendered words the LLM missed and the safety net declined to guess at."""
        for _source_word, word, span, _source_span in residual:
            if word in _REVIEW_IGNORE:
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
                )
            )


# --------------------------------------------------------------------- helpers


def _text_of(paragraph: Any) -> str:
    """Paragraphs are dicts of sentences in the JSON, plain strings elsewhere."""
    if isinstance(paragraph, str):
        return paragraph
    return " ".join(paragraph.get("sentences", []))


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
) -> QCReport:
    """Compare two book JSON files, optionally writing the full report to disk."""
    report = QCService(transform_type).check_book(
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
