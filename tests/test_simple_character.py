#!/usr/bin/env python3
"""
Simple synchronous test of character analysis
"""

import json
import os
import sys
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from dotenv import load_dotenv

from src.providers.llm_client import UnifiedLLMClient

load_dotenv()


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"),
    reason="No API keys configured",
)
def test_character_analysis():
    """Test character analysis with simple synchronous approach"""

    # Use A Modest Proposal - it's very short
    project_root = Path(__file__).parent.parent
    book_path = project_root / "books/json/pg1080-A_Modest_Proposal.json"

    with open(book_path) as f:
        book = json.load(f)

    print(f"Book: {book['metadata']['title']}")
    print(f"Chapters: {len(book['chapters'])}")

    # Combine first chapter text
    text_chunks = []
    for chapter in book["chapters"][:1]:  # Just first chapter
        chapter_text = []
        for para in chapter["paragraphs"][:5]:  # Just first 5 paragraphs
            chapter_text.append(" ".join(para["sentences"]))
        text_chunks.append("\n".join(chapter_text))

    full_text = "\n\n".join(text_chunks)
    print(f"Analyzing {len(full_text)} characters of text...")

    # Analyze with default provider (auto-detected from env)
    client = UnifiedLLMClient()

    prompt = """Identify all characters/people mentioned in this text.
Output JSON: {"characters": [{"name": "...", "gender": "male/female/unknown", "importance": "main/supporting/minor"}]}"""

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": full_text[:2000]},  # Limit text length
    ]

    try:
        print(f"Calling {client.get_provider().upper()} API...")
        response = client.complete(messages, temperature=0.1)

        # Extract JSON from response (may be wrapped in markdown code blocks)
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        result = json.loads(content)

        print(f"\nFound {len(result['characters'])} characters:")
        for char in result["characters"]:
            print(f"  - {char['name']} ({char.get('gender', 'unknown')})")

        # Save character analysis
        output_path = book_path.parent / f"{book_path.stem}-characters.json"

        character_data = {
            "book_metadata": {
                "title": book["metadata"]["title"],
                "author": book["metadata"].get("author", "Unknown"),
                "source_file": str(book_path),
            },
            "characters": result["characters"],
            "metadata": {
                "total": len(result["characters"]),
                "provider": client.get_provider(),
                "model": client.get_default_model(),
            },
        }

        with open(output_path, "w") as f:
            json.dump(character_data, f, indent=2)

        print(f"\nSaved to: {output_path}")
        assert True  # Test passed

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        assert False, f"Test failed: {e}"


if __name__ == "__main__":
    success = test_character_analysis()
    sys.exit(0 if success else 1)
