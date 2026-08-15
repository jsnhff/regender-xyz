"""
QC Gates

Content-level checks that run on the final transformed text. Execution
success is not correctness: every one of the May-2026 print regressions
shipped from a run that "succeeded". These gates fail on residual gendered
language, inconsistent renames, mutated surnames/places, and half-transformed
title+name units — the actual failure classes observed in print.

Verdicts: PASS / FAIL / INFO. FAIL is zero-tolerance. INFO annotates
(needs-review counts, ambiguous names) without changing the verdict, per the
informative-PASS rule: hints belong in the detail, not the verdict.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from src.models.character import CharacterAnalysis

from .name_engine import RANK_TITLES, _strip_titles

# ---------------------------------------------------------------- residual

# Words/patterns that must not survive in each unidirectional variant.
# gender_swap is absent by design: after a swap both genders' language is
# legitimate, so only the atomicity and rank checks apply there.
_RESIDUAL_PATTERNS: dict[str, list[str]] = {
    "all_male": [
        r"\bshe\b",
        r"\bher\b",
        r"\bherself\b",
        r"\bhers\b",
        r"\bMrs\.?(?=\s)",
        r"\bMiss(?=\s+[A-Z])",
        r"\bmadam\b",
        r"\bma'am\b",
        r"\bmother\b",
        r"\bmamma\b",
        r"\bdaughter(s?)\b",
        r"\bsister(s?)\b",
        r"\baunt\b",
        r"\bniece(s?)\b",
        r"\bwife\b",
        r"\bwidow\b",
        r"\blady\b",
        r"\bladies\b",
        r"\bwoman\b",
        r"\bwomen\b",
        r"\bgirl(s?)\b",
        r"\bgentlewom[ae]n\b",
    ],
    "all_female": [
        r"\bhe\b",
        r"\bhis\b",
        r"\bhimself\b",
        r"\bMr\.(?=\s)",
        r"\bsir\b",
        r"\bSir(?=\s+[A-Z])",
        r"\bfather\b",
        r"\bpapa\b",
        r"\bson(s?)\b",
        r"\bbrother(s?)\b",
        r"\buncle\b",
        r"\bnephew(s?)\b",
        r"\bhusband\b",
        r"\bwidower\b",
        r"\blord\b",
        r"\bgentlem[ae]n\b",
        r"\bman\b",
        r"\bmen\b",
        r"\bboy(s?)\b",
    ],
    "nonbinary": [
        r"\bhe\b",
        r"\bshe\b",
        r"\bhim\b",
        r"\bher\b",
        r"\bhis\b",
        r"\bhers\b",
        r"\bhimself\b",
        r"\bherself\b",
        r"\b(?:Mr|Mrs|Ms)\.(?=\s)",
        r"\bMiss(?=\s+[A-Z])",
        r"\b[Ss]ir\b",
        r"\bmadam\b",
        r"\bma'am\b",
        r"\bmother\b",
        r"\bfather\b",
        r"\bmamma\b",
        r"\bpapa\b",
        r"\bdaughter(s?)\b",
        r"\bson(s?)\b",
        r"\bsister(s?)\b",
        r"\bbrother(s?)\b",
        r"\baunt\b",
        r"\buncle\b",
        r"\bwife\b",
        r"\bhusband\b",
        r"\blady\b",
        r"\bladies\b",
        r"\blord(s?)\b",
        r"\bgentlem[ae]n\b",
        r"\bgentlewom[ae]n\b",
        r"\bgentlemanlike\b",
        r"\bwoman\b",
        r"\bwomen\b",
        r"\bman\b",
        r"\bmen\b",
        r"\bgirl(s?)\b",
        r"\bboy(s?)\b",
    ],
}

# After "they", these s-final words are fine (adverbs, plural verbs whose base
# ends in s, reflexives). Anything else ending in s/es is a conjugation error.
_THEY_ALLOWLIST = {
    "as",
    "always",
    "alas",
    "perhaps",
    "thus",
    "besides",
    "unless",
    "across",
    "themselves",
    "his",
    "this",
    "miss",
    "pass",
    "express",
    "address",
    "possess",
    "discuss",
    "confess",
    "dress",
    "press",
    "kiss",
    "cross",
    "toss",
    "guess",
    "bless",
    "witness",
    "canvass",
    "embarrass",
    "harass",
    "caress",
    "assess",
    "wits",
    "less",
    "sometimes",
    "afterwards",
    "towards",
    "upwards",
    "downwards",
    "backwards",
    "forwards",
    "doubtless",
    "regardless",
    "nevertheless",
    "nowadays",
    "whereas",
    "others",
}

_INVENTED_RANK = re.compile(
    r"\b(?:Colonel|Captain|General|Major|Admiral|Sergeant|Lieutenant)"
    r"(?:le|la|e|ess|essa|ette|ina)\b"
)

_GATE_ARTICLE_WORDS = {"The", "A", "An"}

_GATE_TITLES = (
    "Sir",
    "Lady",
    "Lord",
    "Dame",
    "Mr\\.",
    "Mrs\\.",
    "Ms\\.",
    "Miss",
    "Mx\\.?",
    "Noble",
)


@dataclass
class GateResult:
    name: str
    verdict: str  # PASS | FAIL | INFO
    details: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "verdict": self.verdict, "details": self.details}


def _pattern_flags(pattern: str) -> int:
    """Lowercase-only patterns match case-insensitively ("His" is residue as
    much as "his"); patterns with deliberate capitals (Miss, Sir, Mr.) stay
    case-sensitive."""
    return 0 if any(c.isupper() for c in pattern) else re.IGNORECASE


def _find_all(pattern: str, text: str, limit: int = 8) -> list[str]:
    """Occurrences of pattern with a little context, capped for readability."""
    out = []
    for m in re.finditer(pattern, text, _pattern_flags(pattern)):
        start = max(0, m.start() - 25)
        out.append(f"…{text[start : m.end() + 25]}…".replace("\n", " "))
        if len(out) >= limit:
            break
    return out


def _count(pattern: str, text: str) -> int:
    return sum(1 for _ in re.finditer(pattern, text, _pattern_flags(pattern)))


# ------------------------------------------------------------------- gates


def residual_gender_gate(transformed: str, variant: str) -> GateResult:
    patterns = _RESIDUAL_PATTERNS.get(variant)
    if patterns is None:
        return GateResult(
            "residual_gender",
            "INFO",
            ["not applicable to gender_swap: both genders' language is legitimate after a swap"],
        )
    details = []
    for pat in patterns:
        n = _count(pat, transformed)
        if n:
            examples = _find_all(pat, transformed, limit=3)
            details.append(f"{pat}: {n}× — e.g. {examples[0] if examples else ''}")
    return GateResult("residual_gender", "FAIL" if details else "PASS", details)


def verb_agreement_gate(transformed: str, variant: str) -> GateResult:
    if variant != "nonbinary":
        return GateResult("verb_agreement", "INFO", ["nonbinary-only gate"])
    details = []
    for m in re.finditer(r"\b[Tt]hey ([a-z]+(?:s|es))\b", transformed):
        word = m.group(1)
        if word not in _THEY_ALLOWLIST:
            start = max(0, m.start() - 25)
            details.append(
                f"they {word} — …{transformed[start : m.end() + 25]}…".replace("\n", " ")
            )
        if len(details) >= 20:
            details.append("(truncated)")
            break
    return GateResult("verb_agreement", "FAIL" if details else "PASS", details)


def name_consistency_gate(
    transformed: str, name_map: dict[str, str], engine_flags: Optional[list[str]] = None
) -> GateResult:
    """After a rename, the original given name must be gone (0 occurrences).

    The May regression shipped Elizabeth+Elliot+Edward simultaneously — this
    gate is the one that would have caught it.
    """
    if not name_map:
        return GateResult("name_consistency", "INFO", ["no renames in this run"])
    details = []
    infos = list(engine_flags or [])
    single_keys = [k for k in name_map if " " not in k]
    protected = _protected_place_spans(transformed, single_keys)
    scrubbed = transformed
    for span in protected:
        scrubbed = scrubbed.replace(span, "\x00")
    for orig in single_keys:
        n = _count(rf"\b{re.escape(orig)}\b", scrubbed)
        if n:
            examples = _find_all(rf"\b{re.escape(orig)}\b", scrubbed, limit=2)
            details.append(f"'{orig}' still appears {n}× after rename — {'; '.join(examples)}")
    # A rename applied on top of an already-renamed span reads as a doubled
    # name ("Felicity Felicity Darcy") — catch it for every target given name.
    for target in {v.split()[0] for v in name_map.values()}:
        pat = rf"\b{re.escape(target)}\s+{re.escape(target)}\b"
        n = _count(pat, transformed)
        if n:
            examples = _find_all(pat, transformed, limit=2)
            details.append(f"doubled name '{target} {target}' {n}× — {'; '.join(examples)}")
    # Phrase-only entries (ambiguous names like Fitzwilliam): report, don't fail.
    for key in name_map:
        if " " in key:
            first = key.split()[0]
            if first not in single_keys and first not in RANK_TITLES:
                n = _count(rf"\b{re.escape(first)}\b(?!\s+{re.escape(key.split()[-1])})", scrubbed)
                if n:
                    infos.append(f"'{first}' appears bare {n}× (phrase-scoped rename) — review")
    verdict = "FAIL" if details else "PASS"
    return GateResult("name_consistency", verdict, details + [f"[info] {i}" for i in infos])


def _protected_place_spans(text: str, given_names: list[str]) -> set[str]:
    """Literal place phrases in the text built on given names (St. X, X Street, the X)."""
    spans: set[str] = set()
    for name in given_names:
        esc = re.escape(name)
        for pat in (
            rf"\bSt\.\s+{esc}(?:'s)?\b",
            rf"\b{esc}\s+(?:Street|Road|Lane|Square|Court|Park|House|Row)\b",
            rf"\bthe\s+{esc}\b",
        ):
            for m in re.finditer(pat, text):
                spans.add(m.group())
    return spans


def immutability_gate(
    original: str,
    transformed: str,
    characters: Optional[CharacterAnalysis],
    name_map: Optional[dict[str, str]] = None,
) -> GateResult:
    """Surnames and name-bearing places must survive the transform.

    A decrease that is fully covered by gains in the same characters' target
    given names is an address-style shift, not a mutation: bare-surname
    address ("Bingley said") is male Regency convention, so a swapped-female
    Bingley is correctly rendered by her new given name ("Clara said").
    Anything else that lowers a surname count is the King→Monarch class.
    """
    if not characters:
        return GateResult("surname_place_immutability", "INFO", ["no character analysis provided"])
    name_map = name_map or {}
    details = []
    surnames: set[str] = set()
    givens: set[str] = set()
    surname_to_targets: dict[str, set[str]] = {}
    for char in characters.characters:
        tokens = _strip_titles(char.name)
        # Names like "The Miss Webbs" survive title-stripping with a leading
        # article and an embedded title; the immutable surname is only the
        # family-name tail ("Webbs") — a vanished "Miss" is a correct
        # transform, not a mutated surname.
        had_prefix = False
        while tokens and (
            tokens[0].rstrip(".") in _GATE_ARTICLE_WORDS or not tokens[0][0].isupper()
        ):
            tokens.pop(0)
            had_prefix = True
        if had_prefix:
            tokens = _strip_titles(" ".join(tokens))
        if len(tokens) > 1:
            givens.add(tokens[0])
            surname = " ".join(tokens[1:])
            surnames.add(surname)
            target = name_map.get(tokens[0])
            if target:
                surname_to_targets.setdefault(surname, set()).add(target.split()[0])
        elif len(tokens) == 1 and (had_prefix or tokens[0] != char.name.strip()):
            surnames.add(tokens[0])
        elif len(tokens) == 1:
            givens.add(tokens[0])
    # Phrase renames also consume surname-words: "Fitzwilliam Darcy" →
    # "Frederica Darcy" removes one occurrence of the Colonel's surname
    # "Fitzwilliam". Credit the phrase's target given name against it.
    for key, value in name_map.items():
        key_tokens = key.split()
        if len(key_tokens) > 1:
            surname_to_targets.setdefault(key_tokens[0], set()).add(value.split()[0])
    infos = []
    for surname in sorted(surnames):
        pat = rf"\b{re.escape(surname)}\b"
        before, after = _count(pat, original), _count(pat, transformed)
        if after < before:
            # Address-style shift check: did this surname's characters gain at
            # least that many mentions under their new given names?
            gain = sum(
                max(
                    0,
                    _count(rf"\b{re.escape(t)}\b", transformed)
                    - _count(rf"\b{re.escape(t)}\b", original),
                )
                for t in surname_to_targets.get(surname, ())
            )
            if gain >= before - after:
                infos.append(
                    f"surname '{surname}': {before}× → {after}× (address style shifted to "
                    f"{'/'.join(sorted(surname_to_targets[surname]))}, +{gain})"
                )
            else:
                # Fewer occurrences not explained by renames: the surname was
                # rewritten somewhere (the Mary King → Mary Monarch class).
                details.append(
                    f"surname '{surname}': {before}× in source, {after}× after transform"
                )
        elif after > before:
            # More occurrences is expected: pronoun disambiguation inserts
            # names for clarity. Annotate, don't fail.
            infos.append(f"surname '{surname}': {before}× → {after}× (disambiguation insertions)")
    for given in sorted(givens):
        for span in _protected_place_spans(original, [given]):
            before = original.count(span)
            after = transformed.count(span)
            if before != after:
                details.append(f"place '{span}': {before}× in source, {after}× after transform")
    verdict = "FAIL" if details else "PASS"
    return GateResult(
        "surname_place_immutability", verdict, details + [f"[info] {i}" for i in infos]
    )


def title_atomicity_gate(transformed: str, name_map: dict[str, str]) -> GateResult:
    """No invented ranks; no gendered title still glued to a renamed given name."""
    details = []
    for m in _INVENTED_RANK.finditer(transformed):
        start = max(0, m.start() - 20)
        details.append(f"invented rank: …{transformed[start : m.end() + 20]}…".replace("\n", " "))
    title_alt = "|".join(_GATE_TITLES)
    for orig in (k for k in (name_map or {}) if " " not in k):
        pat = rf"\b(?:{title_alt})\s+{re.escape(orig)}\b"
        n = _count(pat, transformed)
        if n:
            examples = _find_all(pat, transformed, limit=2)
            details.append(f"title still paired with renamed '{orig}' {n}× — {'; '.join(examples)}")
    return GateResult("title_name_atomicity", "FAIL" if details else "PASS", details)


def text_integrity_gate(original: str, transformed: str) -> GateResult:
    """Transformed text must not silently lose content (empty-paragraph class)."""
    ow, tw = len(original.split()), len(transformed.split())
    if ow and tw / ow < 0.9:
        return GateResult(
            "text_integrity",
            "FAIL",
            [f"transformed text has {tw} words vs {ow} in source ({tw / ow:.0%}) — content lost"],
        )
    return GateResult("text_integrity", "PASS", [f"{tw} words vs {ow} in source"])


def chapter_count_gate(original_count: int, transformed_count: int) -> GateResult:
    if original_count != transformed_count:
        return GateResult(
            "chapter_count",
            "FAIL",
            [f"source has {original_count} chapters, output has {transformed_count}"],
        )
    return GateResult("chapter_count", "PASS", [f"{transformed_count} chapters"])


# ------------------------------------------------------------------ runner


def run_qc_gates(
    *,
    original_text: str,
    transformed_text: str,
    transform_type: str,
    characters: Optional[CharacterAnalysis] = None,
    name_map: Optional[dict[str, str]] = None,
    engine_flags: Optional[list[str]] = None,
    original_chapters: Optional[int] = None,
    transformed_chapters: Optional[int] = None,
) -> dict[str, Any]:
    """Run every gate; returns {'passed': bool, 'gates': [...]}.

    'passed' is False iff any gate FAILs — INFO never changes the verdict.
    """
    gates = [
        residual_gender_gate(transformed_text, transform_type),
        verb_agreement_gate(transformed_text, transform_type),
        name_consistency_gate(transformed_text, name_map or {}, engine_flags),
        immutability_gate(original_text, transformed_text, characters, name_map),
        title_atomicity_gate(transformed_text, name_map or {}),
        text_integrity_gate(original_text, transformed_text),
    ]
    if original_chapters is not None and transformed_chapters is not None:
        gates.append(chapter_count_gate(original_chapters, transformed_chapters))
    return {
        "passed": all(g.verdict != "FAIL" for g in gates),
        "gates": [g.to_dict() for g in gates],
    }
