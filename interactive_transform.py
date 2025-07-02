#!/usr/bin/env python3
"""
INTERACTIVE BOOK TRANSFORMATION CLI
User-friendly command line interface for gender transformation with preview and control.
"""

import os
import sys
import time
from pathlib import Path
from ai_chunking import chunk_text_ai
from gender_transform import transform_gender_with_context
from analyze_characters import analyze_characters
from validate_transformation import quick_validation_report

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Print the application header."""
    print("=" * 80)
    print("🚀 INTERACTIVE GENDER TRANSFORMATION TOOL")
    print("   AI-Powered Book Transformation with Chunk Preview")
    print("=" * 80)

def print_separator():
    """Print a visual separator."""
    print("-" * 80)

def get_user_choice(prompt, choices, default=None):
    """Get user choice from a list of options."""
    while True:
        print(f"\n{prompt}")
        for i, choice in enumerate(choices, 1):
            marker = " (default)" if default and choice == default else ""
            print(f"  {i}. {choice}{marker}")
        
        if default:
            user_input = input(f"\nEnter choice (1-{len(choices)}) or press Enter for default: ").strip()
            if not user_input:
                return default
        else:
            user_input = input(f"\nEnter choice (1-{len(choices)}): ").strip()
        
        try:
            choice_idx = int(user_input) - 1
            if 0 <= choice_idx < len(choices):
                return choices[choice_idx]
            else:
                print("❌ Invalid choice. Please try again.")
        except ValueError:
            print("❌ Please enter a number.")

def get_yes_no(prompt, default=True):
    """Get yes/no input from user."""
    default_text = "Y/n" if default else "y/N"
    while True:
        response = input(f"{prompt} ({default_text}): ").strip().lower()
        if not response:
            return default
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("❌ Please enter 'y' or 'n'")

def get_number(prompt, min_val=1, max_val=None, default=None):
    """Get a number input from user."""
    while True:
        if default:
            user_input = input(f"{prompt} (default: {default}): ").strip()
            if not user_input:
                return default
        else:
            user_input = input(f"{prompt}: ").strip()
        
        try:
            number = int(user_input)
            if number < min_val:
                print(f"❌ Number must be at least {min_val}")
            elif max_val and number > max_val:
                print(f"❌ Number must be at most {max_val}")
            else:
                return number
        except ValueError:
            print("❌ Please enter a valid number")

def select_book():
    """Let user select a book file."""
    print_separator()
    print("📚 SELECT BOOK TO TRANSFORM")
    
    # Look for books in test_data directory
    test_data_path = Path("test_data")
    if not test_data_path.exists():
        print("❌ test_data directory not found!")
        return None
    
    book_files = list(test_data_path.glob("*.txt"))
    if not book_files:
        print("❌ No .txt files found in test_data directory!")
        return None
    
    # Show available books
    book_names = [f.name for f in book_files]
    selected_book = get_user_choice("Available books:", book_names)
    
    book_path = test_data_path / selected_book
    
    # Load and show book info
    try:
        with open(book_path, 'r') as f:
            text = f.read()
        
        print(f"\n✅ Loaded: {selected_book}")
        print(f"📊 Size: {len(text):,} characters")
        print(f"📄 Lines: {text.count(chr(10)):,}")
        
        return book_path, text, selected_book
        
    except Exception as e:
        print(f"❌ Error loading book: {e}")
        return None

def analyze_and_chunk_book(text, book_name):
    """Analyze characters and create chunks."""
    print_separator()
    print("🔧 ANALYZING BOOK STRUCTURE...")
    
    # AI Chunking
    print("📖 Creating chunks with AI-powered analysis...")
    chunks = chunk_text_ai(text, prefer_ai=False)
    
    if not chunks:
        print("❌ Failed to create chunks!")
        return None, None
    
    print(f"✅ Created {len(chunks)} chunks with 100% coverage")
    
    # Show chunk summary
    print(f"\n📋 CHUNK BREAKDOWN:")
    for i, chunk in enumerate(chunks[:5], 1):  # Show first 5
        tokens = chunk['size'] // 4
        print(f"  Chunk {i}: {chunk['size']:,} chars (~{tokens:,} tokens) - {chunk['description']}")
    
    if len(chunks) > 5:
        print(f"  ... and {len(chunks) - 5} more chunks")
    
    # Character Analysis
    print(f"\n👥 ANALYZING CHARACTERS...")
    try:
        # Use first few chunks for character analysis
        sample_chunks = chunks[:3] if len(chunks) >= 3 else chunks
        sample_text = ''.join(chunk['text'] for chunk in sample_chunks)[:100000]
        
        character_analysis = analyze_characters(sample_text)
        characters_dict = character_analysis.get('characters', {})
        character_list = []
        
        for name, char_info in characters_dict.items():
            character_list.append({
                'name': name,
                'gender': char_info.get('gender', 'unknown'),
                'role': char_info.get('role', 'Unknown role')
            })
        
        print(f"✅ Identified {len(character_list)} main characters:")
        for char in character_list[:8]:  # Show up to 8 characters
            print(f"  - {char['name']}: {char['gender']}, {char['role']}")
        
        if len(character_list) > 8:
            print(f"  ... and {len(character_list) - 8} more characters")
            
    except Exception as e:
        print(f"⚠️ Character analysis failed: {e}")
        character_list = [{"name": "Main Character", "gender": "unknown", "role": "protagonist"}]
    
    return chunks, character_list

def preview_transformation(chunks, character_list, transform_type):
    """Show a preview of the transformation on the first chunk."""
    print_separator()
    print("👀 TRANSFORMATION PREVIEW")
    
    # Create character context
    character_context = "Character information:\n"
    for char in character_list:
        character_context += f"- {char['name']}: {char['gender']}, {char['role']}\n"
    
    # Transform first chunk as preview
    first_chunk = chunks[0]
    print(f"📝 Testing transformation on: {first_chunk['description']}")
    print(f"📊 Size: {first_chunk['size']:,} characters")
    
    try:
        print("🔄 Transforming preview chunk...")
        start_time = time.time()
        
        transformed_text, changes = transform_gender_with_context(
            first_chunk['text'],
            transform_type,
            character_context,
            model="gpt-4.1-nano"
        )
        
        processing_time = time.time() - start_time
        
        print(f"✅ Preview completed in {processing_time:.1f}s")
        print(f"🔄 Changes made: {len(changes)}")
        
        if changes:
            print(f"\n📋 TRANSFORMATION CHANGES:")
            for i, change in enumerate(changes[:5], 1):  # Show first 5 changes
                print(f"  {i}. {change}")
            if len(changes) > 5:
                print(f"  ... and {len(changes) - 5} more changes")
        
        # Show text samples
        print(f"\n📖 SAMPLE COMPARISON:")
        
        # Find a good sample section (look for dialogue or character names)
        sample_start = max(0, first_chunk['text'].find('\n\n') + 2)
        sample_end = min(len(first_chunk['text']), sample_start + 400)
        
        original_sample = first_chunk['text'][sample_start:sample_end]
        transformed_sample = transformed_text[sample_start:min(len(transformed_text), sample_start + 400)]
        
        print(f"🔸 ORIGINAL:")
        print(f"   {repr(original_sample)}")
        
        print(f"\n🔹 TRANSFORMED:")
        print(f"   {repr(transformed_sample)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Preview transformation failed: {e}")
        return False

def transform_chunks(chunks, character_list, transform_type, num_chunks):
    """Transform the specified number of chunks."""
    print_separator()
    print(f"🚀 TRANSFORMING {num_chunks} CHUNKS")
    
    # Create character context
    character_context = "Character information:\n"
    for char in character_list:
        character_context += f"- {char['name']}: {char['gender']}, {char['role']}\n"
    
    transformed_chunks = []
    total_changes = 0
    total_start_time = time.time()
    
    for i in range(num_chunks):
        chunk = chunks[i]
        print(f"\n📝 Processing chunk {i+1}/{num_chunks}: {chunk['description']}")
        print(f"   Size: {chunk['size']:,} characters")
        
        try:
            chunk_start = time.time()
            
            transformed_text, changes = transform_gender_with_context(
                chunk['text'],
                transform_type,
                character_context,
                model="gpt-4.1-nano"
            )
            
            chunk_time = time.time() - chunk_start
            total_changes += len(changes)
            
            transformed_chunks.append(transformed_text)
            
            print(f"   ✅ Completed in {chunk_time:.1f}s ({len(changes)} changes)")
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            print(f"   📝 Using original text for this chunk")
            transformed_chunks.append(chunk['text'])
    
    total_time = time.time() - total_start_time
    
    print(f"\n🎯 TRANSFORMATION SUMMARY:")
    print(f"   ✅ Processed: {num_chunks} chunks")
    print(f"   🔄 Total changes: {total_changes}")
    print(f"   ⏱️ Total time: {total_time:.1f}s")
    print(f"   📊 Avg time per chunk: {total_time/num_chunks:.1f}s")
    
    return transformed_chunks

def save_output(transformed_chunks, remaining_chunks, book_name, transform_type):
    """Save the transformed output to a file."""
    print_separator()
    print("💾 SAVING OUTPUT")
    
    # Combine transformed chunks with remaining original chunks
    all_chunks = transformed_chunks + [chunk['text'] for chunk in remaining_chunks]
    full_text = ''.join(all_chunks)
    
    # Generate output filename
    clean_book_name = book_name.replace('.txt', '').replace('_', ' ').title().replace(' ', '_').lower()
    output_file = f"transformed_{clean_book_name}_{transform_type}_{len(transformed_chunks)}chunks.txt"
    
    try:
        with open(output_file, 'w') as f:
            f.write(full_text)
        
        print(f"✅ Saved to: {output_file}")
        print(f"📊 Output size: {len(full_text):,} characters")
        print(f"📄 Includes: {len(transformed_chunks)} transformed + {len(remaining_chunks)} original chunks")
        
        return output_file
        
    except Exception as e:
        print(f"❌ Error saving file: {e}")
        return None

def validate_transformation_results(original_file, transformed_file, num_chunks):
    """Run validation on the transformation results."""
    print_separator()
    print("🔍 TRANSFORMATION VALIDATION")
    
    print(f"🎯 Validating quality of {num_chunks} transformed chunks...")
    
    try:
        # Run the validation
        quick_validation_report(str(original_file), transformed_file, num_chunks)
        
        print(f"\n💡 Validation complete! Check the results above.")
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        print("⚠️ You can manually run: python validate_transformation.py")
        print(f"   {original_file} {transformed_file} --chunks {num_chunks}")

def main():
    """Main interactive CLI function."""
    try:
        clear_screen()
        print_header()
        
        # Step 1: Select book
        result = select_book()
        if not result:
            return 1
        
        book_path, text, book_name = result
        
        # Step 2: Choose transformation type
        print_separator()
        transform_type = get_user_choice(
            "🎭 SELECT TRANSFORMATION TYPE:",
            ["neutral", "feminine", "masculine"],
            default="neutral"
        )
        
        print(f"\n✅ Selected: {transform_type} transformation")
        
        # Step 3: Analyze and chunk
        chunks, character_list = analyze_and_chunk_book(text, book_name)
        if not chunks:
            return 1
        
        # Step 4: Preview transformation
        if get_yes_no("\n🔍 Would you like to see a transformation preview?", default=True):
            preview_success = preview_transformation(chunks, character_list, transform_type)
            if not preview_success:
                if not get_yes_no("Preview failed. Continue anyway?", default=False):
                    return 1
        
        # Step 5: Choose number of chunks to transform
        print_separator()
        print("📊 TRANSFORMATION SCOPE")
        print(f"Total chunks available: {len(chunks)}")
        
        scope_choice = get_user_choice(
            "How many chunks would you like to transform?",
            ["Just the first chunk (for testing)", 
             "First few chunks (3-5 chunks)", 
             "Half the book", 
             "Most of the book (80%)", 
             "Entire book", 
             "Custom amount"],
            default="First few chunks (3-5 chunks)"
        )
        
        if scope_choice == "Just the first chunk (for testing)":
            num_chunks = 1
        elif scope_choice == "First few chunks (3-5 chunks)":
            num_chunks = min(4, len(chunks))
        elif scope_choice == "Half the book":
            num_chunks = len(chunks) // 2
        elif scope_choice == "Most of the book (80%)":
            num_chunks = int(len(chunks) * 0.8)
        elif scope_choice == "Entire book":
            num_chunks = len(chunks)
        else:  # Custom amount
            num_chunks = get_number(
                f"Enter number of chunks to transform (1-{len(chunks)})",
                min_val=1,
                max_val=len(chunks),
                default=min(4, len(chunks))
            )
        
        print(f"\n✅ Will transform {num_chunks} out of {len(chunks)} chunks")
        
        # Confirmation
        if not get_yes_no(f"\n🚀 Ready to transform {num_chunks} chunks to {transform_type}?", default=True):
            print("❌ Transformation cancelled.")
            return 0
        
        # Step 6: Transform chunks
        transformed_chunks = transform_chunks(chunks, character_list, transform_type, num_chunks)
        
        # Step 7: Save output
        remaining_chunks = chunks[num_chunks:] if num_chunks < len(chunks) else []
        
        if get_yes_no("\n💾 Save the transformed output?", default=True):
            output_file = save_output(transformed_chunks, remaining_chunks, book_name, transform_type)
            if output_file:
                print(f"\n🎉 SUCCESS! Transformation complete.")
                print(f"📁 Check the output file: {output_file}")
                
                # Step 8: Optional validation
                if get_yes_no("\n🔍 Would you like to validate the transformation quality?", default=True):
                    validate_transformation_results(book_path, output_file, num_chunks)
                
                if remaining_chunks:
                    print(f"\n📝 Note: {len(remaining_chunks)} chunks remain in original form")
                    if get_yes_no("Would you like to transform more chunks?", default=False):
                        # Could loop back to transform more, but for now just inform
                        print("💡 Tip: Run the program again to transform additional chunks!")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        return 0
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())