#!/usr/bin/env python3
"""
Test gender transformation on Pride and Prejudice sample.

Tests the all_male transformation on the first chapter of Pride and Prejudice
to verify correctness of gender term replacements using a mock LLM provider
that applies rule-based substitutions.
"""

import asyncio
import json
import os
import re
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.book import Book, Chapter, Paragraph
from src.models.character import Character, CharacterAnalysis, Gender
from src.models.transformation import TransformType
from src.providers.base import LLMProvider
from src.services.transform_service import TransformService

# --------------------------------------------------------------------------- #
# Mock provider that applies deterministic all_male substitutions
# --------------------------------------------------------------------------- #


class MockAllMaleProvider(LLMProvider):
    """Mock LLM provider that applies rule-based all_male gender transformation."""

    ALL_MALE_RULES = {
        # Pronouns (case-sensitive word boundaries)
        r"\bShe\b": "He",
        r"\bshe\b": "he",
        r"\bHer\b": "His",
        r"\bher\b": "him",
        r"\bhers\b": "his",
        r"\bHers\b": "His",
        r"\bherself\b": "himself",
        r"\bHerself\b": "Himself",
        # Titles
        r"\bMrs\.": "Mr.",
        r"\bMs\.": "Mr.",
        r"\bMiss\b": "Mr.",
        # Gendered terms
        r"\bwife\b": "husband",
        r"\bWife\b": "Husband",
        r"\bmother\b": "father",
        r"\bMother\b": "Father",
        r"\bdaughter\b": "son",
        r"\bDaughter\b": "Son",
        r"\bdaughters\b": "sons",
        r"\bDaughters\b": "Sons",
        r"\bsister\b": "brother",
        r"\bSister\b": "Brother",
        r"\bsisters\b": "brothers",
        r"\bSisters\b": "Brothers",
        r"\blady\b": "lord",
        r"\bLady\b": "Lord",
        r"\bqueen\b": "king",
        r"\bQueen\b": "King",
        r"\bgirl\b": "boy",
        r"\bGirl\b": "Boy",
        r"\bgirls\b": "boys",
        r"\bGirls\b": "Boys",
        r"\bwoman\b": "man",
        r"\bWoman\b": "Man",
        r"\bwomen\b": "men",
        r"\bWomen\b": "Men",
    }

    @property
    def name(self) -> str:
        return "mock-all-male"

    @property
    def supports_json(self) -> bool:
        return False

    @property
    def max_tokens(self) -> int:
        return 4096

    async def complete_async(self, messages, **kwargs):
        """Apply deterministic rule-based substitutions to simulate LLM transformation."""
        # The user message contains the text to transform after "INPUT TEXT:\n"
        user_msg = next((m["content"] for m in messages if m["role"] == "user"), "")
        # Extract the actual text (after "INPUT TEXT:\n")
        if "INPUT TEXT:" in user_msg:
            text = user_msg.split("INPUT TEXT:\n", 1)[-1]
            # Remove trailing "TRANSFORMED TEXT:" if present
            if "TRANSFORMED TEXT:" in text:
                text = text.split("TRANSFORMED TEXT:")[0]
            text = text.strip()
        else:
            text = user_msg.strip()

        # Apply all substitution rules
        result = text
        for pattern, replacement in self.ALL_MALE_RULES.items():
            result = re.sub(pattern, replacement, result)

        return result


# --------------------------------------------------------------------------- #
# Helper functions
# --------------------------------------------------------------------------- #


def load_pride_prejudice_sample(num_paragraphs=5):
    """Load a small sample from Pride and Prejudice Chapter 1."""
    project_root = Path(__file__).parent.parent
    book_path = project_root / "books/json/pg1342-Pride_and_Prejudice.json"

    with open(book_path) as f:
        book_data = json.load(f)

    book = Book.from_dict(book_data)
    ch1 = book.chapters[0]

    limited_chapter = Chapter(
        number=ch1.number,
        title=ch1.title,
        paragraphs=ch1.paragraphs[:num_paragraphs],
    )
    return Book(
        title=book.title,
        author=book.author,
        chapters=[limited_chapter],
        metadata=book.metadata,
    )


def create_pride_prejudice_characters():
    """Create a known character analysis for P&P Chapter 1."""
    characters = [
        Character(
            name="Mr. Bennet",
            gender=Gender.MALE,
            pronouns={"subject": "he", "object": "him", "possessive": "his"},
            importance="main",
        ),
        Character(
            name="Mrs. Bennet",
            gender=Gender.FEMALE,
            pronouns={"subject": "she", "object": "her", "possessive": "her"},
            importance="main",
        ),
    ]
    return CharacterAnalysis(book_id="pg1342", characters=characters)


def run_async(coro):
    """Run an async coroutine synchronously."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# --------------------------------------------------------------------------- #
# Test class
# --------------------------------------------------------------------------- #


class TestPridePrejudiceAllMale:
    """Test all_male transformation on Pride and Prejudice Chapter 1."""

    @pytest.fixture(scope="class")
    def transformed_result(self):
        """Run the transformation once and share across tests."""
        book = load_pride_prejudice_sample(num_paragraphs=10)
        characters = create_pride_prejudice_characters()
        provider = MockAllMaleProvider()

        transform_service = TransformService(
            provider=provider,
            character_service=None,
        )

        transformation = run_async(
            transform_service.transform_book_async(
                book,
                TransformType.ALL_MALE,
                characters=characters,
            )
        )

        original_texts = [p.get_text() for p in book.chapters[0].paragraphs]
        transformed_texts = [
            p.get_text() for p in transformation.transformed_chapters[0].paragraphs
        ]

        return {
            "transformation": transformation,
            "original_book": book,
            "original_texts": original_texts,
            "transformed_texts": transformed_texts,
        }

    def test_transformation_produced_changes(self, transformed_result):
        """Verify that the transformation actually made changes."""
        changes = transformed_result["transformation"].changes
        assert len(changes) > 0, "Transformation should have produced at least one change"
        print(f"\nTotal changes recorded: {len(changes)}")

    def test_chapter_count_preserved(self, transformed_result):
        """Verify chapter count is preserved."""
        original = transformed_result["original_book"]
        transformed = transformed_result["transformation"]
        assert len(transformed.transformed_chapters) == len(original.chapters)

    def test_paragraph_count_preserved(self, transformed_result):
        """Verify paragraph count is preserved."""
        original_paras = transformed_result["original_texts"]
        transformed_paras = transformed_result["transformed_texts"]
        assert len(transformed_paras) == len(original_paras), (
            f"Paragraph count mismatch: {len(original_paras)} -> {len(transformed_paras)}"
        )

    def test_mrs_replaced_with_mr(self, transformed_result):
        """Verify Mrs. Bennet references are changed to Mr."""
        combined_transformed = " ".join(transformed_result["transformed_texts"])
        combined_original = " ".join(transformed_result["original_texts"])

        # The original should have "Mrs." references
        assert "Mrs." in combined_original, "Original should contain 'Mrs.'"

        # The transformed should NOT have "Mrs." - they should be "Mr."
        mrs_count = combined_transformed.count("Mrs.")
        assert mrs_count == 0, (
            f"Transformed text should not contain 'Mrs.' but found {mrs_count} instances"
        )

    def test_female_pronouns_replaced(self, transformed_result):
        """Verify female pronouns are replaced with male equivalents."""
        combined_transformed = " ".join(transformed_result["transformed_texts"]).lower()
        combined_original = " ".join(transformed_result["original_texts"]).lower()

        # Check that the original contains female pronouns
        assert "she" in combined_original or "her" in combined_original, (
            "Original should contain female pronouns"
        )

        # In the transformed all_male version, "she" should not appear
        she_count = len(re.findall(r"\bshe\b", combined_transformed))
        assert she_count == 0, (
            f"Transformed text should not contain 'she' but found {she_count} instances"
        )

        # "he"/"him"/"his" should appear
        has_male = bool(
            re.search(r"\bhe\b", combined_transformed)
            or re.search(r"\bhim\b", combined_transformed)
            or re.search(r"\bhis\b", combined_transformed)
        )
        assert has_male, "Transformed text should contain male pronouns"

    def test_wife_replaced_with_husband(self, transformed_result):
        """Verify 'wife' is replaced with 'husband' in the famous opening."""
        first_para_original = transformed_result["original_texts"][0].lower()
        first_para_transformed = transformed_result["transformed_texts"][0].lower()

        assert "wife" in first_para_original, (
            "First paragraph should contain 'wife' in the original"
        )
        assert "wife" not in first_para_transformed, (
            "First paragraph should not contain 'wife' after all_male transformation"
        )
        assert "husband" in first_para_transformed, (
            "First paragraph should contain 'husband' after all_male transformation"
        )

    def test_daughters_replaced_with_sons(self, transformed_result):
        """Verify 'daughters' is replaced with 'sons'."""
        combined_original = " ".join(transformed_result["original_texts"]).lower()
        combined_transformed = " ".join(transformed_result["transformed_texts"]).lower()

        if "daughter" in combined_original:
            daughter_count = len(re.findall(r"\bdaughters?\b", combined_transformed))
            assert daughter_count == 0, (
                f"Transformed text should not contain 'daughter(s)' "
                f"but found {daughter_count} instances"
            )

    def test_lady_replaced_with_lord(self, transformed_result):
        """Verify 'lady' references are replaced with 'lord'."""
        combined_original = " ".join(transformed_result["original_texts"]).lower()
        combined_transformed = " ".join(transformed_result["transformed_texts"]).lower()

        if "lady" in combined_original:
            lady_count = len(re.findall(r"\blady\b", combined_transformed))
            assert lady_count == 0, (
                f"Transformed text should not contain 'lady' but found {lady_count} instances"
            )

    def test_text_not_empty(self, transformed_result):
        """Verify transformed text is not empty."""
        for i, text in enumerate(transformed_result["transformed_texts"]):
            assert len(text.strip()) > 0, f"Paragraph {i} should not be empty"

    def test_text_length_reasonable(self, transformed_result):
        """Verify transformed text length is within reasonable bounds of original."""
        for i, (orig, trans) in enumerate(
            zip(
                transformed_result["original_texts"],
                transformed_result["transformed_texts"],
            )
        ):
            ratio = len(trans) / len(orig) if len(orig) > 0 else 1.0
            assert 0.5 < ratio < 2.0, (
                f"Paragraph {i} length ratio {ratio:.2f} is suspicious "
                f"(original={len(orig)}, transformed={len(trans)})"
            )

    def test_transformation_rules_are_correct(self, transformed_result):
        """Verify transformation rules in TransformService match expected all_male rules."""
        transform_service = TransformService(provider=MockAllMaleProvider())
        rules = transform_service._get_transformation_rules(TransformType.ALL_MALE)

        assert rules["target_gender"] == "male"
        assert rules["pronouns"]["she"] == "he"
        assert rules["pronouns"]["her"] == "him"
        assert rules["pronouns"]["hers"] == "his"
        assert rules["titles"]["Mrs."] == "Mr."
        assert rules["titles"]["Ms."] == "Mr."
        assert rules["titles"]["Miss"] == "Mr."
        assert rules["terms"]["wife"] == "husband"
        assert rules["terms"]["mother"] == "father"
        assert rules["terms"]["daughter"] == "son"
        assert rules["terms"]["sister"] == "brother"
        assert rules["terms"]["lady"] == "lord"
        assert rules["terms"]["queen"] == "king"

    def test_character_mapping_all_male(self, transformed_result):
        """Verify character gender mapping for all_male transformation."""
        transform_service = TransformService(provider=MockAllMaleProvider())

        # Female character should be mapped to male
        female_char = Character(
            name="Mrs. Bennet",
            gender=Gender.FEMALE,
            pronouns={"subject": "she", "object": "her", "possessive": "her"},
            importance="main",
        )
        mapping = transform_service._get_character_transformation(
            female_char, TransformType.ALL_MALE
        )
        assert mapping["new_gender"] == Gender.MALE
        assert mapping["pronouns"]["subject"] == "he"
        assert mapping["pronouns"]["object"] == "him"
        assert mapping["pronouns"]["possessive"] == "his"

        # Male character should remain male
        male_char = Character(
            name="Mr. Bennet",
            gender=Gender.MALE,
            pronouns={"subject": "he", "object": "him", "possessive": "his"},
            importance="main",
        )
        mapping = transform_service._get_character_transformation(male_char, TransformType.ALL_MALE)
        assert mapping["new_gender"] == Gender.MALE

    def test_print_sample_output(self, transformed_result):
        """Print sample output for manual review."""
        print("\n" + "=" * 80)
        print("PRIDE AND PREJUDICE - ALL MALE TRANSFORMATION SAMPLE")
        print("=" * 80)

        for i in range(min(5, len(transformed_result["original_texts"]))):
            orig = transformed_result["original_texts"][i]
            trans = transformed_result["transformed_texts"][i]
            print(f"\n--- Paragraph {i + 1} ---")
            print(f"ORIGINAL:    {orig[:300]}")
            print(f"TRANSFORMED: {trans[:300]}")
            if orig != trans:
                print("  >> CHANGED")
            else:
                print("  >> UNCHANGED")

        print("\n" + "=" * 80)
        stats = transformed_result["transformation"].get_statistics()
        print(f"Statistics: {json.dumps(stats, indent=2, default=str)}")
        print("=" * 80)
