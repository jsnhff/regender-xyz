#!/usr/bin/env python3
"""
Test script to use the new transformation logic directly
"""
import asyncio
import json
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from models.book import Book
from services.character_service import CharacterService
from services.transform_service import TransformService
from providers.llm_client import UnifiedLLMClient

async def main():
    # Load the book
    with open('books/json/pg43-The_Strange_Case_of_Dr_Jekyll_and_Mr_Hyde.json', 'r') as f:
        book_data = json.load(f)

    book = Book.from_dict(book_data)

    print(f"Loaded book: {book.title}")
    print(f"Chapters: {len(book.chapters)}")

    # Initialize services
    llm_client = UnifiedLLMClient()
    character_service = CharacterService(provider=llm_client)
    transform_service = TransformService(character_service)

    # Apply transformation
    print("\nApplying gender_swap transformation...")
    transformed_book = await transform_service.transform_book(book, 'gender_swap')

    print(f"Transformation complete!")

    # Save the result
    output_path = 'jekyll_hyde_properly_swapped.json'
    with open(output_path, 'w') as f:
        json.dump(transformed_book.to_dict(), f, indent=2)

    print(f"Saved to {output_path}")

    # Show a sample of the transformation
    print("\n=== SAMPLE OF TRANSFORMED TEXT ===")
    first_para = transformed_book.chapters[0].paragraphs[0]
    print(first_para.text[:500])

    # Check for actual changes
    original_text = book.chapters[0].paragraphs[0].text
    transformed_text = transformed_book.chapters[0].paragraphs[0].text

    if original_text != transformed_text:
        print("\n✅ Text was successfully transformed!")
    else:
        print("\n❌ Text was not transformed")

if __name__ == "__main__":
    asyncio.run(main())