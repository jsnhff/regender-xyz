"""Fast character scanning using regex and NLP patterns."""

import re
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict, Counter

# Common name patterns
NAME_PATTERNS = [
    # Mr./Mrs./Ms./Dr. followed by name
    r'\b(?:Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.|Sir|Lord|Lady|Miss|Master)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
    # Capitalized words that might be names (2-3 words)
    r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b(?:\s+(?:said|asked|replied|shouted|whispered|muttered|called|answered|demanded|exclaimed|suggested|told|was|had|did|went|came|looked|turned|walked|ran|stood|sat))',
    # Names with possessive
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})'s\b",
    # Names at sentence start followed by verb
    r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\s+(?:was|had|did|went|came|looked|turned|walked|ran|stood|sat|said|asked|replied)',
]

# Pronoun patterns for gender detection
PRONOUN_PATTERNS = {
    'male': r'\b(?:he|him|his|himself)\b',
    'female': r'\b(?:she|her|hers|herself)\b'
}

# Common non-name words to filter out
NON_NAMES = {
    'The', 'This', 'That', 'These', 'Those', 'There', 'Here', 'Where', 'When', 'What', 'Who',
    'Why', 'How', 'All', 'Some', 'Many', 'Few', 'More', 'Most', 'Other', 'Another', 'Each',
    'Every', 'Any', 'No', 'None', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven',
    'Eight', 'Nine', 'Ten', 'First', 'Second', 'Third', 'Fourth', 'Fifth', 'Next', 'Last',
    'New', 'Old', 'Young', 'Good', 'Bad', 'Great', 'Little', 'Big', 'Small', 'Large',
    'Long', 'Short', 'High', 'Low', 'Hot', 'Cold', 'Dark', 'Light', 'Black', 'White',
    'Red', 'Blue', 'Green', 'Yellow', 'North', 'South', 'East', 'West', 'January',
    'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September',
    'October', 'November', 'December', 'Monday', 'Tuesday', 'Wednesday', 'Thursday',
    'Friday', 'Saturday', 'Sunday', 'English', 'French', 'Spanish', 'German', 'Chinese',
    'But', 'And', 'Or', 'So', 'If', 'Then', 'Now', 'Just', 'Only', 'Very', 'Too', 'Also',
    'Well', 'Even', 'Still', 'Yet', 'Already', 'Perhaps', 'Maybe', 'Certainly', 'Indeed',
    'However', 'Therefore', 'Moreover', 'Furthermore', 'Nevertheless', 'Nonetheless',
    'Meanwhile', 'Otherwise', 'Suddenly', 'Finally', 'Actually', 'Really', 'Quite',
    'Rather', 'Somewhat', 'Exactly', 'Nearly', 'Almost', 'About', 'Around', 'Over',
    'Under', 'Above', 'Below', 'Behind', 'Before', 'After', 'During', 'Through',
    'Across', 'Between', 'Among', 'Within', 'Without', 'Beyond', 'Inside', 'Outside',
    'Beside', 'Besides', 'Despite', 'Except', 'Until', 'Unless', 'Since', 'While',
    'Though', 'Although', 'Because', 'Yes', 'Yeah', 'Yep', 'Sure', 'Okay', 'Alright'
}

# Common dialogue verbs that often follow character names
DIALOGUE_VERBS = {
    'said', 'asked', 'replied', 'shouted', 'whispered', 'muttered', 'called',
    'answered', 'demanded', 'exclaimed', 'suggested', 'told', 'cried', 'yelled',
    'screamed', 'laughed', 'smiled', 'frowned', 'nodded', 'shook', 'sighed',
    'groaned', 'gasped', 'announced', 'declared', 'admitted', 'confessed',
    'explained', 'continued', 'added', 'interrupted', 'agreed', 'disagreed',
    'wondered', 'thought', 'realized', 'remembered', 'knew', 'believed',
    'hoped', 'wished', 'wanted', 'decided', 'promised', 'warned', 'threatened'
}


def fast_scan_for_characters(book_data: Dict[str, Any], verbose: bool = True) -> Dict[str, Dict[str, Any]]:
    """
    Quickly scan book for potential character names using regex patterns.
    Returns a dictionary of character names with their frequency and likely gender.
    """
    if verbose:
        print("Fast-scanning book for character names...")
    
    # Compile patterns for efficiency
    compiled_patterns = [re.compile(pattern) for pattern in NAME_PATTERNS]
    male_pattern = re.compile(PRONOUN_PATTERNS['male'], re.IGNORECASE)
    female_pattern = re.compile(PRONOUN_PATTERNS['female'], re.IGNORECASE)
    
    # Track potential character names and their contexts
    name_mentions = defaultdict(list)
    name_sentences = defaultdict(set)
    
    # Extract all sentences from book
    total_sentences = 0
    for chapter in book_data['chapters']:
        # Handle both old and new structures
        sentences = []
        if 'paragraphs' in chapter:
            for paragraph in chapter['paragraphs']:
                sentences.extend(paragraph.get('sentences', []))
        elif 'sentences' in chapter:
            sentences = chapter['sentences']
        
        total_sentences += len(sentences)
        
        # Scan each sentence
        for sent_idx, sentence in enumerate(sentences):
            # Quick pre-filter: skip sentences without capital letters
            if not re.search(r'[A-Z]', sentence):
                continue
            
            # Check each name pattern
            for pattern in compiled_patterns:
                matches = pattern.finditer(sentence)
                for match in matches:
                    name = match.group(1).strip()
                    
                    # Filter out common non-names
                    name_parts = name.split()
                    if name_parts[0] in NON_NAMES:
                        continue
                    
                    # Filter out single letters or very short names
                    if len(name) < 3 or (len(name_parts) == 1 and len(name) < 4):
                        continue
                    
                    # Store the mention
                    name_mentions[name].append({
                        'chapter': chapter.get('number', '?'),
                        'sentence_idx': sent_idx,
                        'context': sentence[:200]  # First 200 chars for context
                    })
                    name_sentences[name].add(sentence)
    
    if verbose:
        print(f"  Scanned {total_sentences} sentences")
        print(f"  Found {len(name_mentions)} potential character names")
    
    # Analyze each potential character
    characters = {}
    name_counter = Counter({name: len(mentions) for name, mentions in name_mentions.items()})
    
    # Only keep names that appear at least 3 times
    for name, count in name_counter.most_common():
        if count < 3:
            break
        
        # Try to determine gender from pronouns in nearby context
        gender = 'unknown'
        male_refs = 0
        female_refs = 0
        
        for sentence in name_sentences[name]:
            # Count gendered pronouns in sentences mentioning this character
            male_refs += len(male_pattern.findall(sentence))
            female_refs += len(female_pattern.findall(sentence))
        
        if male_refs > female_refs * 2:
            gender = 'male'
        elif female_refs > male_refs * 2:
            gender = 'female'
        
        characters[name] = {
            'name': name,
            'gender': gender,
            'mentions': count,
            'first_appearance': name_mentions[name][0]['chapter'],
            'sample_contexts': [m['context'] for m in name_mentions[name][:3]]
        }
    
    # Merge similar names (e.g., "Harry" and "Harry Potter")
    merged_characters = merge_character_variants(characters)
    
    if verbose:
        print(f"  Identified {len(merged_characters)} likely characters")
        if merged_characters:
            top_chars = sorted(merged_characters.items(), key=lambda x: x[1]['mentions'], reverse=True)[:10]
            print("  Top characters:")
            for name, info in top_chars:
                print(f"    - {name}: {info['mentions']} mentions ({info['gender']})")
    
    return merged_characters


def merge_character_variants(characters: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Merge character name variants (e.g., 'Harry' and 'Harry Potter')."""
    merged = {}
    processed = set()
    
    # Sort by mention count (process most frequent first)
    sorted_chars = sorted(characters.items(), key=lambda x: x[1]['mentions'], reverse=True)
    
    for name, info in sorted_chars:
        if name in processed:
            continue
        
        # Look for variants
        variants = [name]
        name_parts = name.split()
        
        for other_name in characters:
            if other_name == name or other_name in processed:
                continue
            
            other_parts = other_name.split()
            
            # Check if one name contains the other
            if (name in other_name or other_name in name or
                (len(name_parts) > 0 and len(other_parts) > 0 and 
                 (name_parts[0] == other_parts[0] or name_parts[-1] == other_parts[-1]))):
                
                # Merge if they have the same gender or one is unknown
                if (info['gender'] == characters[other_name]['gender'] or
                    info['gender'] == 'unknown' or
                    characters[other_name]['gender'] == 'unknown'):
                    
                    variants.append(other_name)
                    processed.add(other_name)
                    
                    # Update gender if we found a definitive one
                    if info['gender'] == 'unknown' and characters[other_name]['gender'] != 'unknown':
                        info['gender'] = characters[other_name]['gender']
                    
                    # Add mentions
                    info['mentions'] += characters[other_name]['mentions']
        
        # Use the longest variant as the main name
        main_name = max(variants, key=len)
        info['name'] = main_name
        info['variants'] = variants
        merged[main_name] = info
        processed.add(name)
    
    return merged


def get_character_sentences(book_data: Dict[str, Any], 
                          characters: Dict[str, Dict[str, Any]], 
                          max_sentences: int = 500) -> List[str]:
    """
    Extract only sentences that mention characters or contain gendered pronouns.
    This dramatically reduces the amount of text sent to the LLM.
    """
    # Create pattern for all character names and variants
    all_names = []
    for char_info in characters.values():
        all_names.append(char_info['name'])
        all_names.extend(char_info.get('variants', []))
    
    # Escape names for regex and create pattern
    escaped_names = [re.escape(name) for name in all_names]
    name_pattern = re.compile(r'\b(?:' + '|'.join(escaped_names) + r')\b', re.IGNORECASE)
    
    # Also match gendered pronouns
    pronoun_pattern = re.compile(
        r'\b(?:he|him|his|himself|she|her|hers|herself)\b', 
        re.IGNORECASE
    )
    
    relevant_sentences = []
    
    for chapter in book_data['chapters']:
        # Get sentences
        sentences = []
        if 'paragraphs' in chapter:
            for paragraph in chapter['paragraphs']:
                sentences.extend(paragraph.get('sentences', []))
        elif 'sentences' in chapter:
            sentences = chapter['sentences']
        
        # Filter for relevant sentences
        for sentence in sentences:
            if name_pattern.search(sentence) or pronoun_pattern.search(sentence):
                relevant_sentences.append(sentence)
                if len(relevant_sentences) >= max_sentences:
                    break
        
        if len(relevant_sentences) >= max_sentences:
            break
    
    return relevant_sentences