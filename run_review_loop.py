#!/usr/bin/env python3
"""Run the review loop on an existing transformed text file."""

import sys
from review_loop import quality_control_loop

# Try to load environment variables from .env file if dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, assume environment variables are already set
    pass

def main():
    if len(sys.argv) < 3:
        print("Usage: python run_review_loop.py <input_file> <transform_type>")
        print("Transform types: all_male, all_female, gender_swap")
        print("Example: python run_review_loop.py books/output/pg1342-Pride_and_Prejudice_test_all_male.txt all_male")
        sys.exit(1)
    
    input_file = sys.argv[1]
    transform_type = sys.argv[2]
    
    # Review loop now uses the same transform types
    review_type = transform_type
    
    if transform_type not in ['all_male', 'all_female', 'gender_swap']:
        print(f"Error: Unknown transform type '{transform_type}'")
        sys.exit(1)
    
    if transform_type == 'gender_swap':
        print("Note: gender_swap mode is not directly supported by review_loop")
        print("You'll need to specify if you want to check for masculine or feminine compliance")
        sys.exit(1)
    
    # Read the input file
    print(f"Reading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        text = f.read()
    
    print(f"Running quality control loop for {transform_type} transformation...")
    print("=" * 60)
    
    # First, do a quick scan to see what issues exist
    from review_loop import find_specific_errors
    print("\nInitial scan for gendered language...")
    initial_errors = find_specific_errors(text, review_type, use_ai=True, provider='grok')
    
    if initial_errors:
        print(f"\nFound {len(initial_errors)} issues:")
        for i, error in enumerate(initial_errors[:10], 1):  # Show first 10
            print(f"  {i}. '{error['error']}' → '{error['correction']}' in: ...{error.get('context', 'N/A')}...")
        if len(initial_errors) > 10:
            print(f"  ... and {len(initial_errors) - 10} more")
    
    # Run the quality control loop with Grok
    cleaned_text, changes = quality_control_loop(
        text=text,
        transform_type=review_type,
        model=None,  # Will use GROK_MODEL from env
        provider='grok',
        max_iterations=5,
        verbose=True
    )
    
    print("\n" + "=" * 60)
    print(f"Quality control complete! Made {len(changes)} additional corrections")
    
    # Save the cleaned version
    output_file = input_file.replace('.txt', '_qc.txt')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(cleaned_text)
    
    print(f"Saved quality-controlled version to: {output_file}")
    
    # Optionally show the changes made
    if changes and input("Show changes made? (y/n): ").lower() == 'y':
        print("\nChanges made during quality control:")
        for i, change in enumerate(changes, 1):
            print(f"{i}. {change}")

if __name__ == "__main__":
    main()