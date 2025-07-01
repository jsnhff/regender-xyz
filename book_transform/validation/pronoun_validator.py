#!/usr/bin/env python3
"""
Pronoun validation module for ensuring consistency in gender transformations.
"""

import re
import json
from typing import List, Dict, Tuple, Optional

class PronounValidator:
    """Validates and corrects pronoun usage in gender-transformed text."""
    
    def __init__(self, transform_type: str):
        """Initialize validator with the target transformation type.
        
        Args:
            transform_type: Type of transformation (feminine, masculine, neutral)
        """
        self.transform_type = transform_type
        
        # Define relationship possessive patterns to check based on transformation type
        if transform_type == "feminine":
            self.possessive_checks = [
                # Pattern, replacement, context description
                (r"his wife", r"her wife", "possessive for feminine subject with feminine partner"),
                (r"his lady", r"her lady", "possessive for feminine subject with feminine partner"),
                (r"his spouse", r"her spouse", "possessive for feminine subject with feminine partner"),
                (r"his daughter", r"her daughter", "possessive for feminine subject with feminine relation"),
                (r"his son", r"her son", "possessive for feminine subject with masculine relation"),
                (r"his child", r"her child", "possessive for feminine subject with neutral relation"),
                (r"his children", r"her children", "possessive for feminine subject with neutral relation"),
                (r"his family", r"her family", "possessive for feminine subject with neutral relation")
            ]
        elif transform_type == "masculine":
            self.possessive_checks = [
                (r"her (husband|gentleman|spouse)", r"his \1", "possessive for masculine subject with masculine partner"),
                (r"her (son|boy|nephew)", r"his \1", "possessive for masculine subject with masculine relation"),
                (r"her (daughter|girl|niece)", r"his \1", "possessive for masculine subject with feminine relation"),
                (r"her (child|children|family)", r"his \1", "possessive for masculine subject with neutral relation")
            ]
        else:  # neutral
            self.possessive_checks = [
                (r"his spouse", r"their spouse", "possessive for neutral subject with partner"),
                (r"her spouse", r"their spouse", "possessive for neutral subject with partner"),
                (r"his partner", r"their partner", "possessive for neutral subject with partner"),
                (r"her partner", r"their partner", "possessive for neutral subject with partner"),
                (r"his child", r"their child", "possessive for neutral subject with relation"),
                (r"her child", r"their child", "possessive for neutral subject with relation"),
                (r"his children", r"their children", "possessive for neutral subject with relation"),
                (r"her children", r"their children", "possessive for neutral subject with relation"),
                (r"his family", r"their family", "possessive for neutral subject with relation"),
                (r"her family", r"their family", "possessive for neutral subject with relation")
            ]
    
    def validate_and_correct(self, text: str) -> Tuple[str, List[Dict]]:
        """Validate and correct pronoun usage in transformed text.
        
        Args:
            text: The transformed text to validate
            
        Returns:
            Tuple containing (corrected_text, list_of_corrections)
        """
        corrected_text = text
        corrections = []
        
        # Check for relationship possessive inconsistencies
        for pattern, replacement, context in self.possessive_checks:
            matches = re.finditer(pattern, corrected_text, re.IGNORECASE)
            for match in matches:
                # Get the matched text and its context
                matched_text = match.group(0)
                start_idx = max(0, match.start() - 30)
                end_idx = min(len(corrected_text), match.end() + 30)
                context_text = corrected_text[start_idx:end_idx]
                
                # Create replacement with matching case
                if matched_text[0].isupper():
                    corrected = replacement[0].upper() + replacement[1:]
                else:
                    corrected = replacement
                
                # Apply correction - need to recalculate match position as text may have changed
                new_match = re.search(pattern, corrected_text, re.IGNORECASE)
                if new_match:
                    corrected_text = corrected_text[:new_match.start()] + corrected + corrected_text[new_match.end():]
                
                # Record the correction
                corrections.append({
                    "original": matched_text,
                    "corrected": corrected,
                    "context": context_text,
                    "type": context
                })
        
        return corrected_text, corrections

def validate_transformed_text(text: str, transform_type: str) -> Tuple[str, List[Dict]]:
    """Validate and correct a transformed text for pronoun consistency.
    
    Args:
        text: The transformed text to validate
        transform_type: Type of transformation (feminine, masculine, neutral)
        
    Returns:
        Tuple containing (corrected_text, list_of_corrections)
    """
    validator = PronounValidator(transform_type)
    return validator.validate_and_correct(text)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate pronoun consistency in transformed text")
    parser.add_argument("file_path", help="Path to the transformed text file")
    parser.add_argument(
        "-t", "--type", 
        choices=["feminine", "masculine", "neutral"], 
        default="feminine",
        help="Type of transformation that was applied"
    )
    parser.add_argument("-o", "--output", help="Path to save the corrected text")
    args = parser.parse_args()
    
    try:
        # Read the transformed text
        with open(args.file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # Validate and correct the text
        corrected_text, corrections = validate_transformed_text(text, args.type)
        
        # Report corrections
        if corrections:
            print(f"\nFound {len(corrections)} pronoun inconsistencies:")
            for i, correction in enumerate(corrections, 1):
                print(f"{i}. Changed '{correction['original']}' to '{correction['corrected']}'")
                print(f"   Context: '...{correction['context']}...'")
                print(f"   Type: {correction['type']}")
            print()
        else:
            print("\nNo pronoun inconsistencies found.")
        
        # Save corrected text if output path provided
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(corrected_text)
            print(f"Corrected text saved to {args.output}")
        
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
