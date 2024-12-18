"""Main entry point for the application."""

from colorama import init as colorama_init
import sys
from pathlib import Path
from typing import List

from config.constants import CHARACTER_DATA_FILE, GENDER_CATEGORIES
from core.text_processor import TextProcessor
from models.character import CharacterManager, Character
from ui.cli import CLI
from utils.api_client import api_client
from utils.logger import Logger

def get_pronoun_set(gender: str) -> List[str]:
    """Get pronouns for a given gender category."""
    for category, data in GENDER_CATEGORIES.items():
        if data['label'].lower() == gender.lower():
            return data['pronouns']
    return GENDER_CATEGORIES['UNK']['pronouns']

def main():
    # Initialize colorama for cross-platform colored output
    colorama_init(autoreset=True)
    
    # Initialize components
    cli = CLI()
    logger = Logger()
    character_manager = CharacterManager(CHARACTER_DATA_FILE)
    text_processor = TextProcessor()
    
    # Clear screen and show banner
    print("\033[H\033[J", end="")
    cli.print_banner()
    
    # Check API connection
    if not api_client.check_api_key():
        cli.print_status("API connection failed. Please check your OpenAI API key.", "error")
        return
    cli.print_status("API connection established", "success")
    
    # Get input file
    if len(sys.argv) < 2:
        cli.print_status("Please provide an input file path", "error")
        return
    
    input_file = Path(sys.argv[1])
    if not input_file.exists():
        cli.print_status(f"Input file not found: {input_file}", "error")
        return
    
    # Load input text
    with open(input_file, 'r', encoding='utf-8') as f:
        input_text = f.read()
    cli.print_status(f"Loaded input file: {input_file}", "success")
    
    # Process text
    cli.print_status("Processing text...", "info")
    chunks, character_contexts = text_processor.chunk_text(input_text)
    cli.print_status(f"Split into {len(chunks)} chunks", "success")
    
    # Process each chunk
    character_manager.load_characters()
    combined_text = []
    confirmed_genders = {}

    for i, (chunk, context) in enumerate(zip(chunks, character_contexts)):
        cli.print_status(f"Processing chunk {i+1}/{len(chunks)}", "info")
        
        # Find new characters in this chunk
        new_characters = context['characters'] - set(confirmed_genders.keys())
        
        if new_characters:
            cli.print_status(f"Found new characters: {', '.join(new_characters)}", "info")
            
            # Get roles for new characters
            roles_info = text_processor._detect_roles(chunk)
            
            # Process each new character
            for character in new_characters:
                # Get current gender info if it exists
                char_info = character_manager.get_character(character)
                current_gender = char_info.original_gender if char_info else "Unknown"
                
                # Get user input for gender
                new_gender, new_name = cli.get_gender_choice(character, current_gender)
                confirmed_genders[character] = new_gender
                
                # Update character manager
                character_manager.update_character(Character(
                    original_name=character,
                    original_role="Unknown",  # You might want to extract this from roles_info
                    original_gender=current_gender,
                    updated_name=new_name,
                    updated_gender=new_gender
                ))
        
        # Prepare character information for regendering
        chunk_characters = [
            {
                'original_name': char,
                'updated_name': character_manager.get_character(char).updated_name,
                'updated_gender': confirmed_genders[char],
                'pronouns': get_pronoun_set(confirmed_genders[char])
            }
            for char in context['characters']
            if char in confirmed_genders
        ]
        
        # Process the chunk with confirmed genders
        if chunk_characters:
            processed_chunk = text_processor.regender_text(chunk, chunk_characters)
        else:
            processed_chunk = chunk
        
        combined_text.append(processed_chunk)
    
    # Save results
    output_text = ''.join(combined_text)
    logger.log_output(input_text, output_text)  # This now includes the diff
    
    log_path = logger.get_current_log_path()
    cli.print_status("Processing complete!", "success")
    if log_path:
        cli.print_status(f"Output saved to: {log_path}", "info")

if __name__ == "__main__":
    main()