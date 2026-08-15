"""
Name Engine

Builds the per-book character rename map ONCE, before any chapter is
transformed. The map is then applied deterministically everywhere (prompt
instructions + post-LLM substitution), so every chunk of the book agrees on
what each character is called.

Background: renames used to be improvised by the LLM chunk-by-chunk, which
produced multiple conflicting targets for the same character within one book
(Elizabeth → Elliot in one chapter, Edward in another). This module is the
fix: decide once, persist, apply everywhere.
"""

import json
import re
from typing import Any, Optional

from src.models.character import CharacterAnalysis, Gender
from src.models.transformation import TransformType

# Titles that carry gender and transform with the variant.
GENDERED_TITLES = {"Mr", "Mrs", "Ms", "Mx", "Miss", "Sir", "Lady", "Lord", "Dame", "Madam"}

# Ranks and professions are gender-neutral: never inflected, never mapped.
RANK_TITLES = {
    "Colonel",
    "Captain",
    "Major",
    "General",
    "Admiral",
    "Sergeant",
    "Lieutenant",
    "Dr",
    "Doctor",
    "Professor",
    "Reverend",
    "Rev",
}

# How Sir/Lady/Lord/Dame + given-name units transform, per variant.
# (Mr./Mrs./Miss + surname units are handled by the transform service's term
# map; only title+GIVEN units need atomic phrase entries, because the given
# name changes with them.)
TITLE_GIVEN_MAP: dict[str, dict[str, str]] = {
    "all_male": {"Lady": "Lord", "Dame": "Sir", "Sir": "Sir", "Lord": "Lord"},
    "all_female": {"Sir": "Lady", "Lord": "Lady", "Lady": "Lady", "Dame": "Dame"},
    "gender_swap": {"Sir": "Lady", "Lord": "Lady", "Lady": "Lord", "Dame": "Sir"},
    "nonbinary": {"Sir": "Noble", "Lord": "Noble", "Lady": "Noble", "Dame": "Noble"},
}

# Suffixes that turn a real name into an invented one ("Fitzwilliama",
# "Colonelle"). A proposed target matching original+suffix is rejected.
_INVENTED_SUFFIXES = ("a", "e", "ella", "elle", "ette", "ina", "ia", "essa")

_PROPOSAL_PROMPT = """You are choosing replacement GIVEN NAMES for characters in a classic novel so the cast matches a gender variant. Return ONLY valid JSON.

Variant: {variant}
Target style: {style}

Characters to rename (given name, current gender, nicknames):
{cast_lines}

Full cast names and surnames already in use (targets must NOT collide with any of these):
{reserved}

Rules:
- Real, period-appropriate given names only. NEVER invent names (no "Fitzwilliama", no feminized ranks).
- One target per character; no two characters may share a target.
- Targets must not equal any name or surname in the reserved list.
- For each nickname, give a matching nickname of the target name (e.g. Elizabeth→Elijah with Lizzy→Eli). If no natural nickname exists, reuse the target.
- Keep the first letter of the original name when a natural option exists.

Required JSON:
{{"renames": [{{"original": "Elizabeth", "target": "Elijah", "nicknames": {{"Lizzy": "Eli", "Eliza": "Eli"}}}}]}}"""

_VARIANT_STYLE = {
    "all_male": "traditionally male names",
    "all_female": "traditionally female names",
    "gender_swap": "names of the opposite gender to the character's current gender",
    "nonbinary": "gender-neutral names",
}


def _strip_titles(name: str) -> list[str]:
    """Split a display name into tokens with leading titles removed."""
    tokens = [t for t in re.split(r"\s+", name.strip()) if t]
    while tokens and tokens[0].rstrip(".") in (GENDERED_TITLES | RANK_TITLES):
        tokens.pop(0)
    return tokens


def _is_title_led(alias: str) -> bool:
    """True for alias forms like "Miss Bennet" / "Mr. Darcy".

    These are title+surname references, not nicknames: the term map transforms
    the title and the surname must survive, so they never belong in a rename map.
    """
    tokens = alias.split()
    return bool(tokens) and tokens[0].rstrip(".") in (GENDERED_TITLES | RANK_TITLES)


def _is_descriptive_name(name: str) -> bool:
    """True for extraction artifacts like "Young Lucas boy".

    Any lowercase token after title-stripping means this is a description, not
    a Given+Surname name; renaming its first token would corrupt ordinary
    words ("Young …") throughout the book.
    """
    return any(not t[0].isupper() for t in _strip_titles(name))


def _is_plausible_name(target: str) -> bool:
    return bool(re.fullmatch(r"[A-Z][a-zA-Z'\-]+", target))


def _is_invented(original: str, target: str) -> bool:
    o, t = original.lower(), target.lower()
    return any(t == o + s for s in _INVENTED_SUFFIXES)


class NameEngine:
    """Builds a deterministic, collision-checked rename map for one book."""

    def __init__(self, provider: Optional[Any] = None, logger: Optional[Any] = None):
        self.provider = provider
        self.logger = logger

    def _log(self, level: str, msg: str):
        if self.logger:
            getattr(self.logger, level)(msg)

    # ------------------------------------------------------------------ cast

    def _cast_index(self, characters: CharacterAnalysis) -> dict[str, dict]:
        """Per-character parsed name info keyed by character name."""
        index = {}
        for char in characters.characters:
            tokens = _strip_titles(char.name)
            had_title = bool(tokens) and tokens != [
                t for t in re.split(r"\s+", char.name.strip()) if t
            ]
            given = None
            surname = None
            if len(tokens) > 1:
                given = tokens[0]
                surname = " ".join(tokens[1:])
            elif len(tokens) == 1:
                if had_title:
                    surname = tokens[0]  # "Mrs. Bennet" → surname only
                else:
                    given = tokens[0]  # "Elizabeth" → given only
            index[char.name] = {"char": char, "given": given, "surname": surname}
        return index

    def _reserved_names(self, index: dict[str, dict]) -> set[str]:
        """Every name token already in use in the book (lowercased)."""
        reserved: set[str] = set()
        for info in index.values():
            if info["given"]:
                reserved.add(info["given"].lower())
            if info["surname"]:
                for tok in info["surname"].split():
                    if tok[0].isupper():  # skip particles like "de"
                        reserved.add(tok.lower())
            for alias in info["char"].aliases:
                for tok in _strip_titles(alias):
                    reserved.add(tok.lower())
        return reserved

    def _needs_rename(self, char, transform_type: TransformType, selected: Optional[set]) -> bool:
        if selected is not None and char.name not in selected:
            return False
        if char.gender not in (Gender.MALE, Gender.FEMALE):
            return False
        if transform_type == TransformType.ALL_MALE:
            return char.gender == Gender.FEMALE
        if transform_type == TransformType.ALL_FEMALE:
            return char.gender == Gender.MALE
        return transform_type in (TransformType.GENDER_SWAP, TransformType.NONBINARY)

    # -------------------------------------------------------------- proposal

    async def _propose(
        self,
        to_rename: list[dict],
        transform_type: TransformType,
        reserved: set[str],
        feedback: str = "",
    ) -> dict[str, dict]:
        """One LLM call proposing targets for every character needing a rename."""
        cast_lines = "\n".join(
            f"- {info['given']} ({info['char'].gender.value}"
            + (
                f", nicknames: {', '.join(a for a in info['char'].aliases if not _is_title_led(a) and len(_strip_titles(a)) == 1 and _strip_titles(a)[0] != info['given'])}"
                if info["char"].aliases
                else ""
            )
            + ")"
            for info in to_rename
        )
        prompt = _PROPOSAL_PROMPT.format(
            variant=transform_type.value,
            style=_VARIANT_STYLE[transform_type.value],
            cast_lines=cast_lines,
            reserved=", ".join(sorted(reserved)),
        )
        if feedback:
            prompt += f"\n\nPrevious attempt had problems — fix ONLY these and keep valid choices:\n{feedback}"

        response = await self.provider.complete(
            messages=[{"role": "user", "content": prompt}], temperature=0.0
        )
        cleaned = re.sub(r"^```(?:json)?|```$", "", response.strip(), flags=re.MULTILINE).strip()
        data = json.loads(cleaned)
        return {r["original"]: r for r in data.get("renames", []) if r.get("original")}

    # -------------------------------------------------------------- validate

    def _validate(
        self, proposals: dict[str, dict], to_rename: list[dict], reserved: set[str]
    ) -> tuple[dict[str, dict], list[str]]:
        """Filter proposals; return (accepted, problems)."""
        accepted: dict[str, dict] = {}
        problems: list[str] = []
        taken: set[str] = set()
        for info in to_rename:
            given = info["given"]
            prop = proposals.get(given)
            if not prop or not prop.get("target"):
                problems.append(f"{given}: no target proposed")
                continue
            target = prop["target"].strip()
            if not _is_plausible_name(target):
                problems.append(f"{given}: '{target}' is not a plausible name")
                continue
            if _is_invented(given, target):
                problems.append(f"{given}: '{target}' looks invented (original + suffix)")
                continue
            if target.lower() == given.lower():
                continue  # no-op rename; drop silently
            if target.lower() in reserved:
                problems.append(f"{given}: '{target}' collides with an existing cast name")
                continue
            if target.lower() in taken:
                problems.append(f"{given}: '{target}' already used for another character")
                continue
            taken.add(target.lower())
            accepted[given] = prop
        return accepted, problems

    # ----------------------------------------------------------------- build

    async def build_name_map(
        self,
        characters: CharacterAnalysis,
        transform_type: TransformType,
        base_map: Optional[dict[str, str]] = None,
        selected_characters: Optional[list[str]] = None,
    ) -> tuple[dict[str, str], dict[str, Any]]:
        """Build the book's rename map.

        Returns (name_map, report). base_map entries (user-provided) always win
        and suppress LLM proposals for those characters. The report records
        drops and review flags for QC.
        """
        index = self._cast_index(characters)
        reserved = self._reserved_names(index)
        selected = set(selected_characters) if selected_characters is not None else None

        base_map = dict(base_map or {})
        base_lower = {k.lower() for k in base_map}

        to_rename = [
            info
            for info in index.values()
            if info["given"]
            and not _is_descriptive_name(info["char"].name)
            and self._needs_rename(info["char"], transform_type, selected)
            and info["given"].lower() not in base_lower
            and info["char"].name.lower() not in base_lower
        ]

        report: dict[str, Any] = {"proposed": 0, "accepted": 0, "dropped": [], "flags": []}
        accepted: dict[str, dict] = {}

        if to_rename and self.provider:
            # Targets may not collide with anything in the book OR the user map.
            reserved_for_targets = reserved | {v.lower() for v in base_map.values()}
            try:
                proposals = await self._propose(to_rename, transform_type, reserved_for_targets)
                report["proposed"] = len(proposals)
                accepted, problems = self._validate(proposals, to_rename, reserved_for_targets)
                if problems:
                    self._log("warning", f"Name proposals rejected: {problems}; retrying once")
                    retry = await self._propose(
                        to_rename,
                        transform_type,
                        reserved_for_targets,
                        feedback="\n".join(problems),
                    )
                    merged = {**retry, **{k: v for k, v in proposals.items() if k in accepted}}
                    accepted, problems = self._validate(merged, to_rename, reserved_for_targets)
                    report["dropped"] = problems
            except Exception as e:  # LLM/JSON failure → no auto renames, still safe
                self._log("warning", f"Name proposal failed ({e}); characters keep original names")
                report["dropped"] = [f"proposal failed: {e}"]
        elif to_rename:
            report["dropped"] = ["no provider — characters keep original names"]

        # ---------------- emit map entries
        surnames_lower = {
            tok.lower()
            for info in index.values()
            if info["surname"]
            for tok in info["surname"].split()
        }
        name_map: dict[str, str] = {}
        title_map = TITLE_GIVEN_MAP[transform_type.value]

        def _emit_for(info: dict, given: str, target: str, nicknames: dict[str, str]):
            surname = info["surname"]
            ambiguous = given.lower() in surnames_lower and not (
                surname and given.lower() in surname.lower().split()
            )
            if ambiguous:
                # e.g. Fitzwilliam: Darcy's given name AND the Colonel's surname.
                # Emit only surname-anchored phrases; bare occurrences are left
                # for QC to flag rather than guessed at.
                report["flags"].append(
                    f"'{given}' is also a surname in this cast: only '{given} {surname}' "
                    f"is renamed; bare occurrences need review"
                )
                if surname:
                    name_map[f"{given} {surname}"] = f"{target} {surname}"
            else:
                name_map[given] = target
                if surname:
                    name_map[f"{given} {surname}"] = f"{target} {surname}"
            for alias, nick_target in nicknames.items():
                if alias.lower() in surnames_lower or _is_title_led(alias):
                    continue
                if _is_plausible_name(nick_target) and not _is_invented(alias, nick_target):
                    name_map[alias] = nick_target
                else:
                    name_map[alias] = target
            # Atomic title+given units ("Sir William" → "Lady Wilhelmina").
            titles = {t.rstrip(".") for t in info["char"].titles}
            for alias in info["char"].aliases:
                first = alias.split()[0].rstrip(".") if alias.split() else ""
                if first in title_map:
                    titles.add(first)
            for title in titles & set(title_map):
                name_map[f"{title} {given}"] = f"{title_map[title]} {target}"

        for info in to_rename:
            given = info["given"]
            if given in accepted:
                prop = accepted[given]
                nicknames = {
                    a: n
                    for a, n in (prop.get("nicknames") or {}).items()
                    if a in info["char"].aliases or len(_strip_titles(a)) == 1
                }
                _emit_for(info, given, prop["target"].strip(), nicknames)

        # User-provided entries win over everything the engine generated, and
        # get the same phrase/title expansion when they name a known character.
        for orig, target in base_map.items():
            for info in index.values():
                if info["given"] and info["given"].lower() == orig.lower():
                    _emit_for(info, info["given"], target, {})
                    break
        name_map.update(base_map)

        report["accepted"] = len(accepted)
        report["entries"] = len(name_map)
        return name_map, report
