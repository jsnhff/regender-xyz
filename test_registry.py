#!/usr/bin/env python3
"""
Test the improved SmartCharacterRegistry performance
"""

import asyncio
import logging
import os
from src.models.character import Character, Gender
from src.utils.smart_character_registry import SmartCharacterRegistry
from src.plugins.base import PluginManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_registry():
    """Test the improved registry with sample characters."""

    # Initialize provider
    plugin_manager = PluginManager()
    provider_name = os.getenv("DEFAULT_PROVIDER", "openai")
    provider = plugin_manager.get_provider(provider_name)

    if not provider:
        logger.error(f"Failed to initialize {provider_name} provider")
        return

    logger.info(f"Using {provider_name} provider")

    # Create registry
    registry = SmartCharacterRegistry(provider, logger, show_progress=True)

    # Test data - characters from Huckleberry Finn
    test_batches = [
        # Batch 1: Main characters
        [
            Character(name="Huckleberry Finn", gender=Gender.MALE, importance="main"),
            Character(name="Tom Sawyer", gender=Gender.MALE, importance="main"),
            Character(name="Jim", gender=Gender.MALE, importance="main"),
        ],
        # Batch 2: Variations and duplicates
        [
            Character(name="Huck", gender=Gender.MALE, importance="main"),  # Should merge with Huckleberry Finn
            Character(name="Miss Watson", gender=Gender.FEMALE, importance="supporting"),
            Character(name="Widow Douglas", gender=Gender.FEMALE, importance="supporting"),
        ],
        # Batch 3: More variations
        [
            Character(name="Huckleberry", gender=Gender.MALE, importance="main"),  # Should merge
            Character(name="Tom", gender=Gender.MALE, importance="supporting"),  # Might merge with Tom Sawyer
            Character(name="Aunt Polly", gender=Gender.FEMALE, importance="supporting"),
        ],
        # Batch 4: Disguises and aliases
        [
            Character(name="Mary Williams", gender=Gender.FEMALE, importance="minor"),  # Huck in disguise
            Character(name="Sarah Williams", gender=Gender.FEMALE, importance="minor"),  # Another disguise
            Character(name="George Peters", gender=Gender.MALE, importance="minor"),  # Another disguise
        ]
    ]

    # Context for each batch
    contexts = [
        "Huckleberry Finn and Tom Sawyer were best friends. Jim was helping them.",
        "Huck ran away from Miss Watson's house. The Widow Douglas was kind to him.",
        "Huckleberry told Tom about his adventures. Aunt Polly was worried.",
        "Huck disguised himself as Mary Williams, then Sarah Williams, then George Peters to avoid detection."
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

    # Expected: ~8-9 unique characters (Huck variations merged, disguises kept separate or noted)
    logger.info(f"\n✅ Test complete! Efficiency rate: {stats['efficiency_rate']}")


if __name__ == "__main__":
    asyncio.run(test_registry())