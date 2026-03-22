"""
Quality Control Service

Reviews and corrects gender-transformed text using a second LLM pass.
"""

import copy
import re
from typing import Any, Optional

from src.models.book import Book, Paragraph
from src.models.character import CharacterAnalysis, Gender
from src.models.transformation import TransformType
from src.providers.base import LLMProvider
from src.services.base import BaseService, ServiceConfig
from src.services.prompts import CHARACTER_AUDIT_PROMPT_TEMPLATE, QC_REVIEW_PROMPT_TEMPLATE


class QualityService(BaseService):
    """
    Quality control service that reviews and corrects gender transformations.

    Uses a second LLM pass to catch missed pronouns, wrong honorifics,
    and inconsistent character treatment.
    """

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        config: Optional[ServiceConfig] = None,
    ):
        self.provider = provider
        super().__init__(config)

    def _initialize(self):
        """Initialize QC resources."""
        self.logger.info(f"Initialized {self.__class__.__name__}")

    async def process(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Review and correct a transformed book.

        Args:
            data: Dict with keys: book, characters, transform_type

        Returns:
            Dict with: corrected_book, quality_score, corrections_made, total_paragraphs
        """
        book = data["book"]
        characters = data.get("characters")
        transform_type = data["transform_type"]
        if isinstance(transform_type, str):
            transform_type = TransformType(transform_type)

        return await self.review_book(book, characters, transform_type)

    async def review_book(
        self,
        book: Book,
        characters: Optional[CharacterAnalysis],
        transform_type: TransformType,
    ) -> dict[str, Any]:
        """Review and correct all paragraphs in the book (two-pass QC)."""
        # --- Pass 1: batch paragraph scan ---
        rules_summary = self._build_rules_summary(transform_type)
        char_list = self._build_character_list(characters, transform_type)

        # Collect all paragraphs with their location
        all_paragraphs: list[tuple[int, int, int, str]] = []  # (ch_idx, para_idx, sent_idx, text)
        for ch_idx, chapter in enumerate(book.chapters):
            for para_idx, para in enumerate(chapter.paragraphs):
                text = " ".join(para.sentences)
                if text.strip():
                    all_paragraphs.append((ch_idx, para_idx, -1, text))

        # Process in batches
        batch_size = getattr(self.config, "batch_size", 10)
        pass1_corrections = 0
        total = len(all_paragraphs)

        # Build a corrected copy of the book
        corrected_book = copy.deepcopy(book)

        batches = [all_paragraphs[i : i + batch_size] for i in range(0, total, batch_size)]

        for batch in batches:
            texts = [item[3] for item in batch]
            corrected_texts = await self._review_batch(
                texts, rules_summary, char_list, transform_type, batch_size=len(texts)
            )

            for (ch_idx, para_idx, _, original), corrected in zip(batch, corrected_texts):
                if corrected.strip() and corrected.strip() != original.strip():
                    pass1_corrections += 1
                    corrected_book.chapters[ch_idx].paragraphs[para_idx] = Paragraph(
                        sentences=[corrected.strip()]
                    )

        self.logger.info(f"QC Pass 1 complete: {pass1_corrections}/{total} paragraphs corrected")

        # --- Pass 2: character-centric audit ---
        pass2_result = await self.review_book_by_character(
            corrected_book, characters, transform_type
        )
        corrected_book = pass2_result["corrected_book"]
        pass2_corrections = pass2_result["corrections_made"]

        total_corrections = pass1_corrections + pass2_corrections
        quality_score = (
            round(100.0 * (total - total_corrections) / total, 1) if total > 0 else 100.0
        )

        self.logger.info(
            f"QC complete: Pass1={pass1_corrections}, Pass2={pass2_corrections}, "
            f"total={total_corrections}/{total}, quality score: {quality_score}%"
        )

        return {
            "corrected_book": corrected_book,
            "quality_score": quality_score,
            "corrections_made": total_corrections,
            "pass1_corrections": pass1_corrections,
            "pass2_corrections": pass2_corrections,
            "total_paragraphs": total,
        }

    async def review_book_by_character(
        self,
        book: Book,
        characters: Optional[CharacterAnalysis],
        transform_type: TransformType,
    ) -> dict[str, Any]:
        """Pass 2: character-centric audit — verify each character's pronouns throughout the book."""
        if not characters or not characters.characters:
            return {"corrected_book": book, "corrections_made": 0}

        corrected_book = copy.deepcopy(book)
        total_corrections = 0

        for char in characters.characters:
            # Collect all paragraphs that mention this character
            name_variants = [char.name] + char.aliases
            matching: list[tuple[int, int, str]] = []  # (ch_idx, para_idx, text)

            for ch_idx, chapter in enumerate(corrected_book.chapters):
                for para_idx, para in enumerate(chapter.paragraphs):
                    text = " ".join(para.sentences)
                    if text.strip() and any(n.lower() in text.lower() for n in name_variants):
                        matching.append((ch_idx, para_idx, text))

            if not matching:
                continue

            # Process in batches of 30
            audit_batch_size = 30
            batches = [
                matching[i : i + audit_batch_size]
                for i in range(0, len(matching), audit_batch_size)
            ]

            for batch in batches:
                corrections = await self._audit_character_batch(char, batch, transform_type)
                for (ch_idx, para_idx), corrected_text in corrections.items():
                    original = " ".join(
                        corrected_book.chapters[ch_idx].paragraphs[para_idx].sentences
                    )
                    if corrected_text.strip() and corrected_text.strip() != original.strip():
                        total_corrections += 1
                        corrected_book.chapters[ch_idx].paragraphs[para_idx] = Paragraph(
                            sentences=[corrected_text.strip()]
                        )

        self.logger.info(f"QC Pass 2 complete: {total_corrections} character corrections made")

        return {"corrected_book": corrected_book, "corrections_made": total_corrections}

    async def _audit_character_batch(
        self,
        character: Any,
        batch: list[tuple[int, int, str]],
        transform_type: TransformType,
    ) -> dict[tuple[int, int], str]:
        """Send one character's paragraph batch to the LLM for pronoun audit."""
        if not self.provider:
            return {}

        original_gender = (
            character.gender.value if hasattr(character.gender, "value") else str(character.gender)
        )
        target_pronouns = self._get_target_pronouns_str(transform_type, original_gender)
        target_gender = self._get_target_gender_str(transform_type, original_gender)

        aliases_str = ""
        if character.aliases:
            aliases_str = f" (also known as: {', '.join(character.aliases[:5])})"

        numbered_paragraphs = "\n\n".join(f"[{i}] {text}" for i, (_, _, text) in enumerate(batch))

        prompt = CHARACTER_AUDIT_PROMPT_TEMPLATE.format(
            name=character.name,
            aliases_str=aliases_str,
            target_gender=target_gender,
            target_pronouns=target_pronouns,
            batch_size=len(batch),
            paragraphs=numbered_paragraphs,
        )

        try:
            messages = [{"role": "user", "content": prompt}]
            response = await self.provider.complete(messages, temperature=0.0)
            raw_corrections = self._parse_json_corrections(response)
            result: dict[tuple[int, int], str] = {}
            for item in raw_corrections:
                idx = item.get("index")
                corrected = item.get("corrected", "")
                if idx is not None and 0 <= idx < len(batch) and corrected:
                    ch_idx, para_idx, _ = batch[idx]
                    result[(ch_idx, para_idx)] = corrected
            return result
        except Exception as e:
            self.logger.warning(f"Character audit batch failed for {character.name}: {e}")
            return {}

    def _get_target_pronouns_str(self, transform_type: TransformType, original_gender: str) -> str:
        """Return a human-readable pronouns string for the target gender."""
        if transform_type == TransformType.ALL_FEMALE:
            return "she/her/hers/herself, title: Ms."
        elif transform_type == TransformType.ALL_MALE:
            return "he/him/his/himself, title: Mr."
        elif transform_type == TransformType.NONBINARY:
            return "they/them/their/themselves, title: Mx."
        elif transform_type == TransformType.GENDER_SWAP:
            if original_gender == Gender.MALE.value:
                return "she/her/hers/herself, title: Ms."
            elif original_gender == Gender.FEMALE.value:
                return "he/him/his/himself, title: Mr."
            else:
                return "they/them/their/themselves, title: Mx."
        return "they/them/their/themselves"

    def _get_target_gender_str(self, transform_type: TransformType, original_gender: str) -> str:
        """Return a human-readable target gender label."""
        if transform_type == TransformType.ALL_FEMALE:
            return "female"
        elif transform_type == TransformType.ALL_MALE:
            return "male"
        elif transform_type == TransformType.NONBINARY:
            return "nonbinary"
        elif transform_type == TransformType.GENDER_SWAP:
            if original_gender == Gender.MALE.value:
                return "female"
            elif original_gender == Gender.FEMALE.value:
                return "male"
            else:
                return "nonbinary"
        return "nonbinary"

    def _parse_json_corrections(self, response: str) -> list[dict]:
        """Robustly extract a JSON array of corrections from model response."""
        try:
            match = re.search(r"\[.*\]", response, re.DOTALL)
            if match:
                import json

                return json.loads(match.group(0))
        except Exception:
            pass
        return []

    async def _review_batch(
        self,
        paragraphs: list[str],
        rules_summary: str,
        char_list: str,
        transform_type: TransformType,
        batch_size: int,
    ) -> list[str]:
        """Send a batch of paragraphs to the LLM for review."""
        if not self.provider:
            return paragraphs  # No provider — return unchanged

        paragraphs_text = "\n\n".join(paragraphs)
        prompt = QC_REVIEW_PROMPT_TEMPLATE.format(
            transform_type=transform_type.value,
            rules_summary=rules_summary,
            character_list=char_list or "(no character list available)",
            batch_size=batch_size,
            paragraphs=paragraphs_text,
        )

        try:
            messages = [{"role": "user", "content": prompt}]
            response = await self.provider.complete(messages, temperature=0.1)
            returned = [p.strip() for p in response.strip().split("\n\n") if p.strip()]
            # Pad or trim to match input batch size
            if len(returned) < len(paragraphs):
                returned.extend(paragraphs[len(returned) :])
            return returned[: len(paragraphs)]
        except Exception as e:
            self.logger.warning(f"QC batch failed, keeping original: {e}")
            return paragraphs

    def _build_rules_summary(self, transform_type: TransformType) -> str:
        """Build a concise human-readable rules summary for the prompt."""
        if transform_type == TransformType.ALL_FEMALE:
            return (
                "All characters → female. he→she, him→her, his→her, Mr.→Ms., "
                "father→mother, son→daughter, brother→sister, husband→wife, king→queen."
            )
        elif transform_type == TransformType.ALL_MALE:
            return (
                "All characters → male. she→he, her→him, hers→his, Mrs./Ms./Miss→Mr., "
                "mother→father, daughter→son, sister→brother, wife→husband, queen→king."
            )
        elif transform_type == TransformType.GENDER_SWAP:
            return (
                "Swap all genders. he↔she, him↔her, his↔hers, Mr.↔Ms., Mrs.→Mr., "
                "father↔mother, son↔daughter, brother↔sister, husband↔wife, king↔queen."
            )
        elif transform_type == TransformType.NONBINARY:
            return (
                "All characters → nonbinary. he/she→they, him/her→them, "
                "his/her→their, Mr./Ms./Mrs.→Mx."
            )
        return f"Transformation type: {transform_type.value}"

    def _build_character_list(
        self, characters: Optional[CharacterAnalysis], transform_type: TransformType
    ) -> str:
        """Build a compact character list showing original → target gender."""
        if not characters or not characters.characters:
            return ""

        lines = []
        for char in characters.characters[:30]:  # Cap at 30 to keep prompt size reasonable
            original = char.gender.value if hasattr(char.gender, "value") else str(char.gender)

            if transform_type == TransformType.GENDER_SWAP:
                target = (
                    "female" if original == "male" else "male" if original == "female" else "swap"
                )
            elif transform_type == TransformType.ALL_FEMALE:
                target = "female"
            elif transform_type == TransformType.ALL_MALE:
                target = "male"
            elif transform_type == TransformType.NONBINARY:
                target = "they/them"
            else:
                target = "transform"

            name_str = char.name
            if char.aliases:
                name_str += f" (aka {', '.join(char.aliases[:2])})"
            lines.append(f"- {name_str}: {original}→{target}")

        return "\n".join(lines)
