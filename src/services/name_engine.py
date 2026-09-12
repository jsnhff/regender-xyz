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

# Titles the variants introduce, which carry no gender and so are never mapped
# again. "Noble" is what Sir/Lady/Lord/Dame become for nonbinary; leaving it out
# of the title set made "Noble William Lucas" parse as the given name "Noble"
# with the surname "William Lucas".
NEUTRAL_TITLES = {"Noble", "Mx"}

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

# Every token that can lead a name without being part of it.
ALL_TITLES = GENDERED_TITLES | RANK_TITLES | NEUTRAL_TITLES

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
- One target per name; different names must not share a target.
- Targets must not equal any name or surname in the reserved list.
- For each nickname, give a matching nickname of the target name (e.g. Elizabeth→Elijah with Lizzy→Eli). If no natural nickname exists, reuse the target.
- Keep the first letter of the original name when a natural option exists, EXCEPT for the nonbinary variant, where a neutral name matters more than an echo of the original.
- If a listed name is actually a SURNAME (family name) of a minor character — not a given name — return {{"original": "...", "is_surname": true}} for it instead of a target. Surnames must never be renamed.

Required JSON:
{{"renames": [{{"original": "Elizabeth", "target": "Elijah", "nicknames": {{"Lizzy": "Eli", "Eliza": "Eli"}}}}]}}"""

_NICKNAME_PROMPT = """These characters have already been renamed. For each nickname the book uses, give the matching nickname of the NEW name, at the same level of familiarity. Return ONLY valid JSON.

{cast_lines}

Rules:
- Real, period-appropriate nicknames only. NEVER invent one.
- A nickname must be a plausible short form of the new name: Edward→Ned or Eddie, never Edward→Lizzy.
- Keep the register: a pet name in the source stays a pet name.
- If the new name has no natural short form, reuse the new name itself.

Required JSON:
{{"characters": [{{"name": "Edward", "nicknames": {{"Lizzy": "Ned", "Eliza": "Ned"}}}}]}}"""

_VARIANT_STYLE = {
    "all_male": "traditionally male names",
    "all_female": "traditionally female names",
    "gender_swap": "names of the opposite gender to the character's current gender",
    "nonbinary": (
        "names that read as neither masculine nor feminine. Prefer names genuinely "
        "used across genders in English before 1850 -- Francis, Evelyn, Hilary, "
        "Vivian, Meredith, Jocelyn, Sidney, Leslie, Valentine, Clare, Aubrey -- "
        "or a period-plausible surname used as a given name. Not modern unisex "
        "coinages, which break the period"
    ),
}


def _strip_titles(name: str) -> list[str]:
    """Split a display name into tokens with leading titles removed."""
    tokens = [t for t in re.split(r"\s+", name.strip()) if t]
    while tokens and tokens[0].rstrip(".") in ALL_TITLES:
        tokens.pop(0)
    return tokens


def _is_title_led(alias: str) -> bool:
    """True for alias forms like "Miss Bennet" / "Mr. Darcy".

    These are title+surname references, not nicknames: the term map transforms
    the title and the surname must survive, so they never belong in a rename map.
    """
    tokens = alias.split()
    return bool(tokens) and tokens[0].rstrip(".") in ALL_TITLES


# Capitalized English words that character extraction sometimes mistakes for
# given names ("The Archbishop", "Young Lucas"). Renaming one of these would
# rewrite ordinary words across the whole book.
_GIVEN_STOPLIST = {"the", "a", "an", "young", "old", "elder", "little", "poor", "dear"}


def _is_descriptive_name(name: str) -> bool:
    """True for extraction artifacts like "Young Lucas boy" or "The Archbishop".

    A lowercase token after title-stripping, or a first token that is a common
    English word, means this is a description rather than a Given+Surname name;
    renaming its first token would corrupt ordinary words throughout the book.
    """
    tokens = _strip_titles(name)
    if any(not t[0].isupper() for t in tokens):
        return True
    return bool(tokens) and tokens[0].lower() in _GIVEN_STOPLIST


def _is_plausible_name(target: str) -> bool:
    return bool(re.fullmatch(r"[A-Z][a-zA-Z'\-]+", target))


#: A possessive marks a term substitution rather than a rename: "Wickham's
#: father" -> "Wickham's parent" is about the noun, not the name.
_POSSESSIVE = re.compile(r"['’]s\b")


def _is_invented(original: str, target: str) -> bool:
    """A name that is the original wearing a gendered ending.

    Exact concatenation was too narrow: it catches "Fitzwilliam" ->
    "Fitzwilliama" and misses "Darcy" -> "Darcia", which is the same move with
    the last letter traded rather than kept.
    """
    o, t = original.lower(), target.lower()
    if any(t == o + s for s in _INVENTED_SUFFIXES):
        return True
    stem = o[:-1]
    return len(stem) >= 3 and any(t == stem + s for s in _INVENTED_SUFFIXES)


#: Particles that belong to a surname rather than standing between names.
#: Without these "Miss de Bourgh" reads as the given name "de".
_SURNAME_PARTICLES = {"de", "van", "von", "du", "del", "della", "di", "da", "la", "le"}

#: Words that disambiguate a surname instead of following a given name, so
#: "Mrs. Wickham senior" is a surname with a qualifier. Only ever lowercase:
#: Elder, Younger and Senior are real English surnames, and matching those
#: turned "Elizabeth Elder" -> "Edmund Elder" into a rejected surname change.
_SURNAME_QUALIFIERS = {"senior", "junior", "elder", "younger", "snr", "jnr"}

#: Titles that take a surname. "Mr. Jones" says nothing about his given name.
SURNAME_TITLES = {"Mr", "Mrs", "Ms", "Mx", "Miss", "Madam"}

#: Titles that take a given name: "Sir William", "Lady Catherine". English
#: allows the surname too -- "Lady Lucas" is Sir William's wife -- so one token
#: behind these is genuinely ambiguous and only the cast can settle it.
GIVEN_TITLES = {"Sir", "Lady", "Lord", "Dame", "Noble"}


def given_and_surname(
    name: str,
    surnames: frozenset = frozenset(),
    givens: frozenset = frozenset(),
    like: Optional[tuple] = None,
) -> tuple[Optional[str], Optional[str]]:
    """Split a display name into (given, surname), either of which may be absent.

    Two or more tokens are Given + Surname, except where the tail says
    otherwise: particles keep a surname together ("de Bourgh"), and a lowercase
    qualifier means the whole thing is a surname ("Wickham senior").

    One token behind a title is the hard case, because the title decides and not
    every title agrees. Mr./Mrs./Miss take a surname; Sir/Lady/Lord/Dame take a
    given name -- "Sir William" is William Lucas's given name, and reading it as
    a surname made "Sir William" -> "Noble Vivian" look like a destroyed
    surname and dropped the correct suggestion. But English allows "Lady Lucas"
    as well, so the title alone is not enough. Pass the cast's surnames and
    given names and the question is settled; without them, ambiguity returns
    (None, None) and the caller forms no opinion rather than a wrong one.

    `like` is the (given, surname) shape of a name this one is meant to replace.
    A proposed name is not in the cast -- that is what makes it proposed -- so
    cast lookup cannot resolve it, and "Sir William" -> "Noble Vivian" read as a
    given name losing its match. Given the shape it answers to, a lone token
    takes the role the original had.
    """
    tokens = _strip_titles(name)
    if not tokens:
        return None, None

    lowered = [t.lower() for t in tokens]

    # A leading particle means no given name. So does a qualifier -- but only a
    # lowercase one: capitalised Elder, Younger and Senior are real surnames.
    qualified = any(t.islower() and t.lower() in _SURNAME_QUALIFIERS for t in tokens[1:])
    if lowered[0] in _SURNAME_PARTICLES or qualified:
        return None, " ".join(tokens)

    if len(tokens) > 1:
        return tokens[0], " ".join(tokens[1:])

    if like is not None:
        like_given, like_surname = like
        if like_given and not like_surname:
            return tokens[0], None
        if like_surname and not like_given:
            return None, tokens[0]

    only, lower = tokens[0], lowered[0]
    leading = name.strip().split()[0].rstrip(".")

    # The cast knows. Ask it first, whatever the title says.
    if lower in surnames and lower not in givens:
        return None, only
    if lower in givens and lower not in surnames:
        return only, None
    if lower in givens and lower in surnames:
        return None, None  # both, as "Fitzwilliam" is: no answer to give

    if leading in GIVEN_TITLES:
        return None, None  # ambiguous without the cast
    if leading in ALL_TITLES:
        return None, only
    return only, None


def cast_name_index(characters: Any) -> tuple[frozenset, frozenset, frozenset]:
    """(surnames, given names, everything spoken for) for a cast.

    Built in one place because the order matters and got it wrong when spread
    out. Surnames come from the multi-token forms first; only then is a bare
    single token read as a given name, and only if it is not already a known
    surname. Taking bare tokens at face value put "Darcy" in both sets, which
    made every judgement about it ambiguous -- so "Darcy" -> "Darcia" passed as
    a rename of a name that is nobody's given name.
    """
    surnames: set = set()
    bare: set = set()
    givens: set = set()

    forms = []
    for char in getattr(characters, "characters", characters):
        forms.append(getattr(char, "name", ""))
        forms.extend(getattr(char, "aliases", []) or [])

    for form in forms:
        if not form:
            continue
        tokens = _strip_titles(form)
        if len(tokens) > 1:
            given, surname = given_and_surname(form)
            if given:
                givens.add(given.lower())
            if surname:
                surnames.update(part.lower() for part in surname.split())
        elif len(tokens) == 1:
            leading = form.strip().split()[0].rstrip(".")
            if leading in SURNAME_TITLES or leading in RANK_TITLES:
                surnames.add(tokens[0].lower())
            else:
                bare.add(tokens[0].lower())

    givens |= {token for token in bare if token not in surnames}
    return frozenset(surnames), frozenset(givens), frozenset(surnames | givens)


def check_rename(
    original: str,
    suggested: str,
    surnames: frozenset = frozenset(),
    givens: frozenset = frozenset(),
    reserved: frozenset = frozenset(),
) -> Optional[str]:
    """Why this rename is wrong, or None if it is fine.

    Both naming paths need these answers and only one of them had them. The
    engine validated its own proposals; the interface's suggestions -- which the
    reader sees, approves, and which then outrank the engine entirely -- were
    checked for nothing beyond being different from the original. So "Sir
    William Lucas" -> "Noble William Lucas" was offered, accepted and shipped:
    the honorific had changed, the man's given name had not, and nothing in the
    pipeline was looking at the given name.

    Pass the cast's surnames, given names, and the names already spoken for.
    Without them this function has to guess from the shape of a name, and its
    guesses were wrong in both directions -- rejecting "Sir William" -> "Noble
    Vivian" as a destroyed surname, and accepting "Elizabeth" -> "Jane", which
    merges two characters.
    """
    # Not every entry in a name map is a person. "Lucas boys" -> "Lucas
    # children", "The chambermaid" -> "The chamberperson" and "Wickham's father"
    # -> "Wickham's parent" are term substitutions that happen to contain a
    # surname; read as Given + Surname they cost nineteen correct entries. The
    # term map governs those, and this function has no opinion.
    #
    # Only the ORIGINAL decides that. Testing the suggestion too turned a
    # malformed suggestion into a way of switching validation off: "Elizabeth
    # Bennet" -> "edward jones" destroyed a surname and returned no problem at
    # all, because the lowercase made it look like a term substitution.
    if _is_descriptive_name(original) or _POSSESSIVE.search(original):
        return None

    orig = given_and_surname(original, surnames, givens)
    orig_given, orig_surname = orig
    new_given, new_surname = given_and_surname(suggested, surnames, givens, like=orig)

    new_tokens = _strip_titles(suggested)

    # A title or rank standing in for a name rewrites every occurrence of that
    # word in the book. "Catherine" -> "Noble" removed the name from all 132
    # places the source used it and left '"Certainly, Noble;"' in the dialogue.
    if not new_tokens:
        return f"{suggested!r} is only a title, not a name"

    # A suggestion that is not a name at all is a rejection, never a bypass.
    for token in new_tokens:
        if not token[:1].isupper():
            return f"{suggested!r} is not a name ({token!r} is not capitalised)"
    # Only the leading token: "Elizabeth Elder" -> "Edmund Elder" is a real
    # surname, and Elder, Younger and Little are all attested ones.
    if new_tokens[0].lower() in _GIVEN_STOPLIST:
        return f"{suggested!r} is not a name ({new_tokens[0]!r} is an ordinary word)"

    # Surnames are family, not gender. Losing one renames a whole household --
    # this is how ~300 surnames were destroyed in the all-female edition.
    if orig_surname and new_surname and orig_surname.lower() != new_surname.lower():
        return f"surname changed: {orig_surname!r} became {new_surname!r}"
    if orig_surname and not new_surname and orig_given is not None:
        return f"surname {orig_surname!r} lost"

    # A character the book knows only by family name has no given name to
    # change, so there is nothing here to rename. Pratt and Chamberlayne are
    # officers named only by surname; the engine has an escape for them and this
    # side had none, so "Pratt" -> "Perry" and "Darcy" -> "Darcia" both passed.
    if orig_surname and not orig_given:
        if new_surname and new_surname.lower() != orig_surname.lower():
            return f"{original!r} is a family name, which is not renamed"
        if new_given and not new_surname:
            return f"{original!r} is a family name, which is not renamed"

    # A character who has a given name must be given a different one. Changing
    # only the honorific leaves the gendered name in place, which is the whole
    # thing the reader asked for.
    if orig_given:
        if not new_given:
            return f"given name {orig_given!r} lost with nothing in its place"
        if new_given.lower() == orig_given.lower():
            return f"given name {orig_given!r} unchanged; only the title moved"
        if _is_invented(orig_given, new_given):
            return f"{new_given!r} looks invented (the original with a suffix)"
        if not _is_plausible_name(new_given):
            return f"{new_given!r} is not a plausible given name"
        # Somebody else's name is not available. "Elizabeth" -> "Jane" reads as
        # a valid rename and makes two characters one person.
        if new_given.lower() in reserved and new_given.lower() != orig_given.lower():
            return f"{new_given!r} is already somebody in this book"

    return None


def target_gender(gender: Gender, transform_type: TransformType) -> Optional[Gender]:
    """What a character of this gender becomes, or None if they are untouched.

    The rule was written into the rename check, where only the engine could
    read it. It is also the answer to "how many characters did this actually
    regender", which is the whole point of a run, so it lives on its own now.
    """
    if gender not in (Gender.MALE, Gender.FEMALE):
        return None
    if transform_type == TransformType.ALL_MALE:
        return Gender.MALE if gender == Gender.FEMALE else None
    if transform_type == TransformType.ALL_FEMALE:
        return Gender.FEMALE if gender == Gender.MALE else None
    if transform_type == TransformType.NONBINARY:
        return Gender.NONBINARY
    if transform_type == TransformType.GENDER_SWAP:
        return Gender.FEMALE if gender == Gender.MALE else Gender.MALE
    return None


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
        return target_gender(char.gender, transform_type) is not None

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

    async def _propose_nicknames(
        self, requests: list[tuple[str, str, list]]
    ) -> dict[str, dict[str, str]]:
        """Nicknames for names somebody else already chose.

        The proposal path asks for these alongside the name and has done for a
        while, but it only runs when the engine picks the names itself. Names
        chosen in the interface skipped it, so every pet name in the book fell
        back to the formal given name: "No, Lizzy, that is what I do not
        choose" became "No, Edward". Worse, the model was then free to invent
        its own short form per batch, which is the inconsistency the engine
        exists to prevent.
        """
        cast_lines = "\n".join(
            f"- {given} is now {target}; nicknames in the book: {', '.join(aliases)}"
            for given, target, aliases in requests
        )
        response = await self.provider.complete(
            messages=[{"role": "user", "content": _NICKNAME_PROMPT.format(cast_lines=cast_lines)}],
            temperature=0.0,
        )
        cleaned = re.sub(r"^```(?:json)?|```$", "", response.strip(), flags=re.MULTILINE).strip()
        data = json.loads(cleaned)
        return {
            entry["name"]: entry.get("nicknames") or {}
            for entry in data.get("characters", [])
            if entry.get("name")
        }

    @staticmethod
    def _match_supplied(index: dict, orig: str) -> Optional[dict]:
        """The character a supplied map entry names, by full name or given name."""
        for info in index.values():
            if info["char"].name.lower() == orig.lower():
                return info
        for info in index.values():
            if info["given"] and info["given"].lower() == orig.lower():
                return info
        return None

    @staticmethod
    def _nickname_aliases(char, given: str) -> list:
        """Single-word aliases that are a familiar form rather than the name."""
        return [
            alias
            for alias in char.aliases
            if not _is_title_led(alias)
            and len(_strip_titles(alias)) == 1
            and _strip_titles(alias)[0].lower() != given.lower()
        ]

    # -------------------------------------------------------------- validate

    def _validate(
        self, proposals: dict[str, dict], to_rename: list[dict], reserved: set[str]
    ) -> tuple[dict[str, dict], list[str], list[str]]:
        """Filter proposals; return (accepted, problems, surname_skips).

        to_rename must already be unique by given name: characters sharing a
        given name share one rename decision (token replacement cannot tell
        them apart anyway).
        """
        accepted: dict[str, dict] = {}
        problems: list[str] = []
        surname_skips: list[str] = []
        taken: set[str] = set()
        for info in to_rename:
            given = info["given"]
            prop = proposals.get(given)
            if prop and prop.get("is_surname"):
                # The model identified this single-token "given" as a family
                # name (e.g. officers known only as Pratt, Chamberlayne).
                # Surnames are immutable — skip, don't retry.
                surname_skips.append(f"'{given}' identified as a surname — not renamed")
                continue
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
                # Not a no-op: a refusal. The model was asked for a different
                # name and returned the same one, and dropping that in silence
                # is how a masculine given name reaches a nonbinary edition with
                # nothing anywhere saying so.
                problems.append(f"{given}: proposed its own name back — not renamed")
                continue
            if target.lower() in reserved:
                problems.append(f"{given}: '{target}' collides with an existing cast name")
                continue
            if target.lower() in taken:
                problems.append(f"{given}: '{target}' already used for another character")
                continue
            taken.add(target.lower())
            accepted[given] = prop
        return accepted, problems, surname_skips

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
        # Characters sharing a given name (three Williams in P&P) share one
        # rename decision — token replacement cannot tell them apart, and a
        # consistent shared target is exactly what we want.
        unique_by_given: dict[str, dict] = {}
        for info in to_rename:
            unique_by_given.setdefault(info["given"], info)
        proposal_list = list(unique_by_given.values())

        report: dict[str, Any] = {"proposed": 0, "accepted": 0, "dropped": [], "flags": []}
        accepted: dict[str, dict] = {}

        if proposal_list and self.provider:
            # Targets may not collide with anything in the book OR the user map.
            reserved_for_targets = reserved | {v.lower() for v in base_map.values()}
            try:
                proposals = await self._propose(proposal_list, transform_type, reserved_for_targets)
                report["proposed"] = len(proposals)
                accepted, problems, surname_skips = self._validate(
                    proposals, proposal_list, reserved_for_targets
                )
                if problems:
                    self._log("warning", f"Name proposals rejected: {problems}; retrying once")
                    retry = await self._propose(
                        proposal_list,
                        transform_type,
                        reserved_for_targets,
                        feedback="\n".join(problems),
                    )
                    merged = {**retry, **{k: v for k, v in proposals.items() if k in accepted}}
                    accepted, problems, more_skips = self._validate(
                        merged, proposal_list, reserved_for_targets
                    )
                    surname_skips = sorted(set(surname_skips) | set(more_skips))
                    report["dropped"] = problems
                report["flags"].extend(surname_skips)
            except Exception as e:  # LLM/JSON failure → no auto renames, still safe
                self._log("warning", f"Name proposal failed ({e}); characters keep original names")
                report["dropped"] = [f"proposal failed: {e}"]
        elif proposal_list:
            report["dropped"] = ["no provider — characters keep original names"]

        # ---------------- emit map entries
        surnames_lower = {
            tok.lower()
            for info in index.values()
            if info["surname"]
            for tok in info["surname"].split()
        }

        # Every title+name form the cast already answers to, e.g. "mrs bennet".
        # Periods are dropped so "Mrs. Bennet" and "Mrs Bennet" compare equal.
        def _form(text: str) -> str:
            return re.sub(r"\s+", " ", text.replace(".", "")).strip().lower()

        cast_forms: dict[str, str] = {}
        for info in index.values():
            char = info["char"]
            for form in [char.name, *char.aliases]:
                cast_forms.setdefault(_form(form), char.name)

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
                # A nickname that comes back unchanged is not a nickname: the
                # character would keep the pet name of the gender they no
                # longer have. Fall back to the formal name instead.
                if (
                    _is_plausible_name(nick_target)
                    and not _is_invented(alias, nick_target)
                    and nick_target.strip().lower() != alias.strip().lower()
                ):
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
                source_form = f"{title} {given}"
                new_form = f"{title_map[title]} {target}"
                # Swapping the title is where collisions are born: in a family
                # both "Mr. Bennet" and "Mrs. Bennet" are in the cast, so
                # converting one into the other merges two people. The check in
                # _validate runs on given names and never sees these pairs,
                # because they are synthesised here afterwards.
                owner = cast_forms.get(_form(new_form))
                if owner and _form(new_form) != _form(source_form):
                    report["flags"].append(
                        f"'{source_form}' would become '{new_form}', which is already "
                        f"{owner} — left unchanged so two characters do not merge"
                    )
                    continue
                name_map[source_form] = new_form

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
        #
        # Matched on the full name as well as the given name. The interface
        # supplies full names -- "Elizabeth Bennet" -> "Edmund Bennet" -- and
        # only the given-name spelling was looked for, so entries chosen in the
        # interface reached none of this: no bare given name, no aliases, no
        # nicknames, no title units.
        supplied: list[tuple] = []
        for orig, target in base_map.items():
            info = self._match_supplied(index, orig)
            if not info:
                continue
            given = info["given"]
            if not given:
                continue
            # The target is written at the same scale as the key, so a full
            # name on the left means a full name on the right. _emit_for adds
            # the surname itself, and handing it the whole thing produced
            # "Edward Bennet Bennet".
            target_given = _strip_titles(target)[0] if _strip_titles(target) else target
            aliases = self._nickname_aliases(info["char"], given)
            supplied.append((info, given, target_given, aliases))

        # One call for the whole cast, so the answer is settled once and every
        # chapter agrees. A failure here must not cost the run: without
        # nicknames each alias falls back to the formal name, which is what
        # happened before and is merely flat rather than wrong.
        nicknames_for: dict[str, dict[str, str]] = {}
        wanted = [(g, t, a) for _i, g, t, a in supplied if a]
        if wanted and self.provider:
            try:
                nicknames_for = await self._propose_nicknames(wanted)
                report["nicknames"] = sum(len(v) for v in nicknames_for.values())
            except Exception as error:
                report["flags"].append(f"nickname proposal failed, using formal names: {error}")

        for info, given, target_given, _aliases in supplied:
            _emit_for(info, given, target_given, nicknames_for.get(target_given, {}))

        # Supplied entries outrank the engine's own, but not to the point of
        # merging two people. "Mr. Bennet" -> "Mrs. Bennet" reads as a correct
        # feminisation and silently makes the father into the mother; the same
        # happened to Mr. and Mrs. Hurst. Every engine-generated name is checked
        # against the cast, and these were the one path that was not.
        for orig, target in base_map.items():
            owner = cast_forms.get(_form(target))
            # An exchange is not a merge. In a swap "Mr. Bennet" becomes
            # "Mrs. Bennet" while "Mrs. Bennet" becomes "Mr. Bennet"; the name
            # being taken is given up in the same breath, so nobody ends up
            # sharing one. Only a one-way move onto an occupied name merges.
            vacated = any(
                _form(other) == _form(target) and _form(dest) != _form(target)
                for other, dest in base_map.items()
            )
            if owner and not vacated and _form(target) != _form(orig) and _form(orig) in cast_forms:
                report["flags"].append(
                    f"'{orig}' would become '{target}', which is already {owner} — "
                    f"left unchanged so two characters do not merge"
                )
                continue
            name_map[orig] = target

        report["accepted"] = len(accepted)
        report["entries"] = len(name_map)
        return name_map, report
