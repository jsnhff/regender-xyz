#!/usr/bin/env python3
"""
Test script to verify parallel LLM processing is working correctly.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.providers.llm_client import UnifiedLLMClient
from src.services.character_service import CharacterService
from src.utils.token_manager import TokenManager


async def test_parallel_processing():
    """Test that multiple chunks are processed in parallel."""
    print("\n=== Testing Parallel LLM Processing ===\n")

    # Initialize the client and service
    client = UnifiedLLMClient(enable_circuit_breaker=True)
    provider = client.get_provider()
    print(f"Using provider: {provider}")
    print(f"Model: {client.get_default_model()}")

    # Create character service
    character_service = CharacterService(provider=client)

    # Load a book for testing - use Alice for more chunks
    book_path = Path("books/json/pg11-Alices_Adventures_in_Wonderland.json")
    with open(book_path) as f:
        book_data = json.load(f)

    # Get text from the book
    text_chunks = []
    for chapter in book_data["chapters"]:
        chapter_text = []
        for para in chapter["paragraphs"]:
            chapter_text.append(" ".join(para["sentences"]))
        text_chunks.append("\n".join(chapter_text))

    full_text = "\n\n".join(text_chunks)
    print(f"Book text length: {len(full_text)} characters")

    # Create chunks for parallel processing
    token_manager = TokenManager(model_name="gpt-4")  # Use defined model
    text_chunks_objs = token_manager.chunk_text(full_text, max_tokens=2000)
    # Extract text from TextChunk objects
    chunks = [chunk.text if hasattr(chunk, 'text') else str(chunk) for chunk in text_chunks_objs]
    print(f"Created {len(chunks)} chunks for analysis")

    # Time the parallel processing
    print("\n--- Starting Parallel Analysis ---")
    start_time = time.time()

    # Call the async method directly
    results = await character_service._analyze_chunks_async(chunks)

    end_time = time.time()
    elapsed = end_time - start_time

    print(f"Completed in {elapsed:.2f} seconds")
    print(f"Average time per chunk: {elapsed/len(chunks):.2f} seconds")

    # If chunks were truly processed in parallel with max_concurrent=5,
    # the total time should be roughly (num_chunks / 5) * time_per_chunk
    # not num_chunks * time_per_chunk

    # Parse results
    total_characters = 0
    for i, result in enumerate(results, 1):
        if "characters" in result:
            num_chars = len(result["characters"])
            total_characters += num_chars
            print(f"  Chunk {i}: Found {num_chars} characters")

    print(f"\nTotal characters found: {total_characters}")

    # Calculate theoretical times
    avg_chunk_time = elapsed / len(chunks)
    sequential_time = len(chunks) * avg_chunk_time
    parallel_time = (len(chunks) / 5) * avg_chunk_time  # with max_concurrent=5

    print(f"\nPerformance Analysis:")
    print(f"  Actual time: {elapsed:.2f}s")
    print(f"  Theoretical sequential: {sequential_time:.2f}s")
    print(f"  Theoretical parallel (5 concurrent): {parallel_time:.2f}s")

    if elapsed < sequential_time * 0.8:  # Allow some overhead
        print("✅ Parallel processing is working!")
    else:
        print("⚠️ May not be processing in parallel")

    return results


async def test_rate_limiting():
    """Test that rate limiting is working correctly."""
    print("\n=== Testing Rate Limiting ===\n")

    client = UnifiedLLMClient(enable_circuit_breaker=True)

    # Create a bunch of small requests
    messages = [{"role": "user", "content": "Say 'test'"}]

    print("Sending 10 rapid requests...")
    start_time = time.time()
    tasks = []

    for i in range(10):
        task = asyncio.create_task(client.complete_async(messages))
        tasks.append(task)

    # Wait for all to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)

    end_time = time.time()
    elapsed = end_time - start_time

    successful = sum(1 for r in results if not isinstance(r, Exception))
    failed = sum(1 for r in results if isinstance(r, Exception))

    print(f"Completed in {elapsed:.2f} seconds")
    print(f"Successful: {successful}, Failed: {failed}")

    # Check for rate limit errors
    rate_limit_errors = sum(
        1
        for r in results
        if isinstance(r, Exception) and "rate" in str(r).lower()
    )
    if rate_limit_errors > 0:
        print(f"⚠️ Hit rate limits: {rate_limit_errors} requests")
    else:
        print("✅ No rate limit errors")

    return results


async def main():
    """Run all tests."""
    try:
        # Test parallel processing
        await test_parallel_processing()

        # Test rate limiting
        # await test_rate_limiting()

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    print("Starting parallel processing tests...")
    asyncio.run(main())
    print("\n✅ All tests completed!")