#!/usr/bin/env python3
"""
Simple test of the improved SmartCharacterRegistry performance
"""

import asyncio
import logging
import os
import sys
from src.models.character import Character, Gender
from src.utils.smart_character_registry import SmartCharacterRegistry

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Mock provider for testing
class MockProvider:
    """Mock provider that simulates LLM responses."""

    async def complete_async(self, messages, temperature=1.0):
        """Mock LLM response for character matching."""
        user_msg = messages[0]["content"]

        # Simulate intelligent matching
        if "Huck" in user_msg and "Huckleberry Finn" in user_msg:
            return """[
                {
                    "new_name": "Huck",
                    "is_match": true,
                    "matching_character": "Huckleberry Finn",
                    "confidence": 0.95
                }
            ]"""
        elif "Tom" in user_msg and "Tom Sawyer" in user_msg:
            return """[
                {
                    "new_name": "Tom",
                    "is_match": true,
                    "matching_character": "Tom Sawyer",
                    "confidence": 0.85
                }
            ]"""
        else:
            # Default: no match
            return """[
                {
                    "new_name": "Unknown",
                    "is_match": false,
                    "matching_character": null,
                    "confidence": 0.0
                }
            ]"""


async def test_registry():
    """Test the improved registry with sample characters."""

    # Use mock provider for testing
    provider = MockProvider()
    logger.info("Using mock provider for testing")

    # Create registry
    registry = SmartCharacterRegistry(provider, logger, show_progress=True)

    # Test data - characters from Huckleberry Finn
    test_batches = [
        # Batch 1: Main characters
        [
            Character(name="Huckleberry Finn", gender=Gender.MALE, pronouns={"subject": "he", "object": "him", "possessive": "his"}, importance="main"),
            Character(name="Tom Sawyer", gender=Gender.MALE, pronouns={"subject": "he", "object": "him", "possessive": "his"}, importance="main"),
            Character(name="Jim", gender=Gender.MALE, pronouns={"subject": "he", "object": "him", "possessive": "his"}, importance="main"),
        ],
        # Batch 2: Variations and duplicates
        [
            Character(name="Huck", gender=Gender.MALE, pronouns={"subject": "he", "object": "him", "possessive": "his"}, importance="main"),  # Should merge with Huckleberry Finn
            Character(name="Miss Watson", gender=Gender.FEMALE, pronouns={"subject": "she", "object": "her", "possessive": "her"}, importance="supporting"),
            Character(name="Widow Douglas", gender=Gender.FEMALE, pronouns={"subject": "she", "object": "her", "possessive": "her"}, importance="supporting"),
        ],
        # Batch 3: More variations
        [
            Character(name="Huckleberry", gender=Gender.MALE, pronouns={"subject": "he", "object": "him", "possessive": "his"}, importance="main"),  # Should merge
            Character(name="Tom", gender=Gender.MALE, pronouns={"subject": "he", "object": "him", "possessive": "his"}, importance="supporting"),  # Might merge with Tom Sawyer
            Character(name="Aunt Polly", gender=Gender.FEMALE, pronouns={"subject": "she", "object": "her", "possessive": "her"}, importance="supporting"),
        ],
    ]

    # Context for each batch
    contexts = [
        "Huckleberry Finn and Tom Sawyer were best friends. Jim was helping them.",
        "Huck ran away from Miss Watson's house. The Widow Douglas was kind to him.",
        "Huckleberry told Tom about his adventures. Aunt Polly was worried.",
    ]

    # Process batches
    for i, (batch, context) in enumerate(zip(test_batches, contexts)):
        logger.info(f"\n{'='*50}")
        logger.info(f"Processing batch {i+1}/{len(test_batches)}")
        logger.info(f"{'='*50}")

        await registry.add_or_merge_batch(batch, context)

    # Show final results
    final_characters = registry.get_all()
    stats = registry.get_statistics()

    logger.info(f"\n{'='*60}")
    logger.info("FINAL RESULTS")
    logger.info(f"{'='*60}")

    logger.info(f"\nUnique characters found: {len(final_characters)}")
    for char in final_characters:
        aliases_str = f" (aliases: {', '.join(char.aliases)})" if char.aliases else ""
        logger.info(f"  • {char.name}{aliases_str} - {char.gender.value} - {char.importance}")

    logger.info(f"\nStatistics:")
    logger.info(f"  • Total checked: {stats['total_checked']}")
    logger.info(f"  • Fast matches: {stats['fast_matches']} ({stats['efficiency_rate']})")
    logger.info(f"  • LLM verifications: {stats['llm_verifications']}")
    logger.info(f"  • Characters merged: {stats['characters_merged']}")

    # Expected: ~7-8 unique characters (Huck variations merged)
    expected_unique = 7
    if len(final_characters) <= expected_unique:
        logger.info(f"\n✅ Test PASSED! Got {len(final_characters)} unique characters (expected ~{expected_unique})")
        logger.info(f"✅ Efficiency rate: {stats['efficiency_rate']}")
    else:
        logger.warning(f"\n⚠️ Test shows {len(final_characters)} unique characters (expected ~{expected_unique})")

    # Verify specific merges happened
    huck_char = next((c for c in final_characters if "Huckleberry" in c.name), None)
    if huck_char and huck_char.aliases and "Huck" in huck_char.aliases:
        logger.info("✅ Successfully merged 'Huck' as alias of 'Huckleberry Finn'")

    tom_char = next((c for c in final_characters if c.name == "Tom Sawyer"), None)
    if tom_char and tom_char.aliases and "Tom" in tom_char.aliases:
        logger.info("✅ Successfully merged 'Tom' as alias of 'Tom Sawyer'")


if __name__ == "__main__":
    asyncio.run(test_registry())