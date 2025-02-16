#!/usr/bin/env python3
"""
regender.xyz - A tool for transforming gender representation in literature
Version: 0.1.0
"""

import os
import sys
import shutil
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime, timedelta
import jsonschema
import json
from openai import OpenAI
from character_analysis import Mention
import math
from dataclasses import dataclass

# Initialize OpenAI client (will use OPENAI_API_KEY from environment)
openai_client = OpenAI()

# Project paths
PROJECT_ROOT = Path(__file__).parent
CACHE_DIR = PROJECT_ROOT / '.cache'
SCHEMA_PATH = PROJECT_ROOT / 'character_analysis.schema.json'

# Ensure cache directory exists
CACHE_DIR.mkdir(exist_ok=True)

def clean_old_cache(max_age_hours: int = 24) -> None:
    """Remove cache files older than specified hours."""
    if not CACHE_DIR.exists():
        return
        
    cutoff = datetime.now() - timedelta(hours=max_age_hours)
    for cache_file in CACHE_DIR.glob('*.json'):
        if cache_file.stat().st_mtime < cutoff.timestamp():
            cache_file.unlink()

def validate_analysis_json(data: dict) -> bool:
    """Validate analysis data against schema."""
    try:
        with open(SCHEMA_PATH) as f:
            schema = json.load(f)
        jsonschema.validate(data, schema)
        return True
    except Exception as e:
        print(f"Validation error: {e}")
        return False

def load_text(file_path: str) -> Tuple[Optional[str], str]:
    """Load and validate input text file."""
    try:
        if not os.path.exists(file_path):
            return None, f"Error: File '{file_path}' not found"
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            
        if not content:
            return None, f"Error: File '{file_path}' is empty"
            
        return content, "File loaded successfully"
    except Exception as e:
        return None, f"Error reading file: {str(e)}"

def print_mention_group(mentions: list[Mention], group_type: str) -> None:
    """Print a group of mentions with sample contexts."""
    if not mentions:
        return
        
    print(f"\n{group_type.title()} mentions ({len(mentions)}):")
    # Show up to 3 examples
    for mention in mentions[:3]:
        print(f"  {mention.text:>10}: ...{mention.context}...")
    if len(mentions) > 3:
        print(f"  ... and {len(mentions) - 3} more {group_type} mentions ...")

def print_character_info(name: str, character) -> None:
    """Print character information in a clean, organized format."""
    print(f"\nCharacter: {name}")
    print("-" * 60)
    print(f"Role: {character.role or 'Unknown'}")
    print(f"Gender: {character.gender or 'Unknown'}")
    
    if character.name_variants:
        variants = [v for v in character.name_variants if v != name]
        if variants:
            print("\nName variations:")
            for variant in variants:
                print(f"  - {variant}")
    
    # Group mentions by type
    mention_groups = {}
    for mention in character.mentions:
        mention_groups.setdefault(mention.mention_type, []).append(mention)
    
    print(f"\nTotal mentions: {len(character.mentions)}")
    for mention_type, mentions in mention_groups.items():
        print_mention_group(mentions, mention_type)
    
    print("-" * 60)

@dataclass
class BookAnalysisConfig:
    """Configuration for book analysis."""
    model_name: str = "gpt-4o-mini-2024-07-18"
    max_tokens_per_chunk: int = 50_000  # Smaller chunks for faster processing
    overlap_tokens: int = 5_000
    min_chapter_confidence: float = 0.8
    max_chapter_size_ratio: float = 3.0
    max_chunks_per_book: int = 10
    cost_per_1k_tokens: float = 0.01
    max_output_tokens: int = 16_000  # Safe margin below 16,384 limit
    
    def estimate_cost(self, total_tokens: int) -> float:
        """Estimate processing cost for a book."""
        chunks = math.ceil(total_tokens / self.max_tokens_per_chunk)
        chunks = min(chunks, self.max_chunks_per_book)
        total_tokens_with_overlap = total_tokens + (chunks - 1) * self.overlap_tokens
        return (total_tokens_with_overlap / 1000) * self.cost_per_1k_tokens

def process_book(file_path: str, config: BookAnalysisConfig = None) -> None:
    """Process a book file with the given configuration."""
    config = config or BookAnalysisConfig()
    
    with open(file_path, 'r') as f:
        text = f.read()
        
    analyzer = BookAnalyzer(config)
    chunks = analyzer.create_chunks(text)
    
    # Process chunks...

def main():
    """Main application entry point."""
    if len(sys.argv) != 2:
        print("Usage: python main.py <input_file>")
        sys.exit(1)
        
    input_file = sys.argv[1]
    content, message = load_text(input_file)
    
    if content is None:
        print(message)
        sys.exit(1)
        
    print(message)
    
    # Clean old cache files
    clean_old_cache()
    
    # Use hash of file content for cache filename
    from hashlib import sha256
    content_hash = sha256(content.encode()).hexdigest()[:12]
    cache_file = CACHE_DIR / f"analysis_{content_hash}.json"
    
    # Perform new analysis
    print("\nPerforming character analysis...")
    from character_analysis import find_characters, save_character_analysis
    characters = find_characters(content, openai_client)
    
    # Save analysis results (overwriting if exists)
    save_character_analysis(characters, str(cache_file))
    print(f"Analysis saved to {cache_file}")
    
    # Display results
    print(f"\nFound {len(characters)} characters:")
    for name, character in characters.items():
        print_character_info(name, character)

if __name__ == "__main__":
    main()
