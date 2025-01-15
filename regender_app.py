#!/usr/bin/env python3
"""
regender.xyz - A tool for transforming gender representation in literature
Version: 0.1.0

This application processes text to detect characters and their genders,
allowing users to transform gender representation while preserving narrative coherence.
"""

# Standard library imports
import os
import time
import json
import re
from datetime import datetime
import sys

# Third-party imports
from openai import OpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

#------------------------------------------------------------------------------
# Configuration
#------------------------------------------------------------------------------

# OpenAI client setup
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Gender categories and their associated terms
GENDER_CATEGORIES = {
    'M': {
        'label': 'Male',
        'terms': ['male', 'man', 'boy', 'gentleman', 'father', 'son', 'mr', 'sir', 'he', 'his'],
        'pronouns': ['he', 'him', 'his']
    },
    'F': {
        'label': 'Female',
        'terms': ['female', 'woman', 'girl', 'lady', 'mother', 'daughter', 'ms', 'mrs', 'miss', 'she', 'her'],
        'pronouns': ['she', 'her', 'hers']
    },
    'NB': {
        'label': 'Non-binary',
        'terms': ['non-binary', 'nonbinary', 'enby', 'neutral', 'they'],
        'pronouns': ['they', 'them', 'theirs']
    },
    'UNK': {
        'label': 'Unknown',
        'terms': ['unknown', 'unspecified'],
        'pronouns': ['they', 'them', 'theirs']
    }
}

#------------------------------------------------------------------------------
# UI/Output Helpers
#------------------------------------------------------------------------------

def print_banner():
    """Print application banner with proper alignment."""
    banner = f"""
{Fore.CYAN}╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃  {Fore.WHITE}⚡ regender.xyz ⚡{Fore.CYAN}                      
┃  {Fore.YELLOW}~ transforming gender in open source books ~{Fore.CYAN}     
┃  {Fore.MAGENTA}[ Version 0.1.0 ]{Fore.CYAN}                      
┃                                           
┃  {Fore.WHITE}✧{Fore.BLUE} gender analysis {Fore.WHITE}✧{Fore.GREEN} gender processing {Fore.WHITE}✧{Fore.CYAN}       
╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}
"""
    print(banner)

def print_startup_sequence():
    """Print animated startup sequence."""
    print("\033[H\033[J", end="")
    print_banner()
    print(f"{Fore.CYAN}┌─{Style.RESET_ALL} System Initialization")
    print(f"{Fore.CYAN}│{Style.RESET_ALL}")

def print_status(message, status_type="info"):
    """Print formatted status messages."""
    symbols = {
        "info": f"{Fore.BLUE}ℹ{Style.RESET_ALL}",
        "success": f"{Fore.GREEN}✓{Style.RESET_ALL}",
        "warning": f"{Fore.YELLOW}⚠{Style.RESET_ALL}",
        "error": f"{Fore.RED}✗{Style.RESET_ALL}"
    }
    print(f" {symbols.get(status_type, symbols['info'])} {message}")

#------------------------------------------------------------------------------
# OpenAI API Interaction
#------------------------------------------------------------------------------

def check_openai_api_key():
    """Verify OpenAI API key with styled output."""
    try:
        client.models.list()
        print(f"{Fore.GREEN}✓ API connection established{Style.RESET_ALL}")
        return True
    except Exception as e:
        print(f"{Fore.RED}✗ API Error: Please check your OpenAI API key{Style.RESET_ALL}")
        return False

def get_gpt_response(prompt, model="gpt-4o", temperature=0.7, retries=3, delay=5):
    """Interact with OpenAI API with retry mechanism."""
    attempt = 0
    while attempt < retries:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error: {e}")
            attempt += 1
            time.sleep(delay)
    return "Error: Unable to get response after multiple attempts"

#------------------------------------------------------------------------------
# Character Detection
#------------------------------------------------------------------------------

def detect_roles_gpt(input_text):
    """Detect and store character roles and original info."""
    prompt = f"Identify all the characters, their roles, and their genders in the following text:\n\n{input_text}\n\nProvide the results in a structured format like: Character - Role - Gender. Arrange the results in a numbered list."
    response = get_gpt_response(prompt)
    lines = response.split('\n')
    character_list = [line for line in lines if " - " in line]
    
    original_info = {}
    for line in character_list:
        parts = line.split(" - ")
        if len(parts) == 3:
            original_name, role, gender = parts
            original_name = clean_name(original_name)
            original_info[original_name] = {
                "name": original_name,
                "role": role,
                "gender": gender.strip()
            }
    
    try:
        with open("original_character_info.json", 'w', encoding='utf-8') as f:
            json.dump(original_info, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"{Fore.YELLOW}Warning: Could not save original character info: {e}{Style.RESET_ALL}")
    
    return '\n'.join(character_list)

def extract_characters_from_chunk(chunk):
    """Extract character names and their locations from text chunk."""
    roles_info = detect_roles_gpt(chunk)
    character_info = {
        'characters': set(),
        'character_locations': {}
    }
    
    if roles_info:
        for line in roles_info.splitlines():
            parts = line.split(" - ")
            if len(parts) >= 1:
                character = clean_name(parts[0])
                character_info['characters'].add(character)
                
                # Find all occurrences of the character name in the chunk
                start_pos = 0
                locations = []
                while True:
                    pos = chunk.find(character, start_pos)
                    if pos == -1:
                        break
                    locations.append(pos)
                    start_pos = pos + 1
                    
                character_info['character_locations'][character] = locations
    
    return character_info

#------------------------------------------------------------------------------
# Gender Processing
#------------------------------------------------------------------------------

def standardize_gender(gender_text):
    """Map gender descriptions to standard categories."""
    if not gender_text:
        return 'UNK', GENDER_CATEGORIES['UNK']['label']
        
    gender_text = gender_text.lower().strip()
    
    for category_key, category_data in GENDER_CATEGORIES.items():
        if gender_text == category_data['label'].lower():
            return category_key, category_data['label']
    
    for category_key, category_data in GENDER_CATEGORIES.items():
        if any(term in gender_text for term in category_data['terms']):
            return category_key, category_data['label']
    
    return 'UNK', GENDER_CATEGORIES['UNK']['label']

def get_user_gender_choice(character, current_gender):
    """Get user input for character gender selection."""
    print(f"\n{Fore.CYAN}╭─ Character: {Fore.WHITE}{character} {Fore.YELLOW}({current_gender.strip()}){Style.RESET_ALL}")
    print(f"{Fore.CYAN}├─ Select Gender:{Style.RESET_ALL}")
    
    options = [
        f"{Fore.GREEN}1{Style.RESET_ALL} Male",
        f"{Fore.MAGENTA}2{Style.RESET_ALL} Female",
        f"{Fore.BLUE}3{Style.RESET_ALL} Non-binary",
        f"{Fore.YELLOW}↵{Style.RESET_ALL} Keep current"
    ]
    print(f"{Fore.CYAN}│  {Style.RESET_ALL}" + " | ".join(options))
    print(f"{Fore.CYAN}╰─{Style.RESET_ALL}", end=" ")
    
    choice = input().strip()
    
    if not choice:
        category_key, standard_label = standardize_gender(current_gender)
        return standard_label, character, category_key
        
    try:
        choice_idx = int(choice) - 1
        category_keys = ['M', 'F', 'NB']
        
        if 0 <= choice_idx < len(category_keys):
            selected_key = category_keys[choice_idx]
            selected_gender = GENDER_CATEGORIES[selected_key]['label']
            
            if selected_gender.lower() != current_gender.lower():
                print(f"\n{Fore.CYAN}╭─ Name Suggestions:{Style.RESET_ALL}")
                suggested_names = get_gpt_response(
                    f"Suggest three {selected_gender.lower()} versions of the name '{character}'. "
                    f"Provide only the names separated by commas, no explanation."
                ).split(',')
                suggested_names = [name.strip() for name in suggested_names]
                
                print(f"{Fore.CYAN}│  {Style.RESET_ALL}" + 
                      " | ".join(f"{Fore.YELLOW}{name}{Style.RESET_ALL}" for name in suggested_names))
                print(f"{Fore.CYAN}╰─{Style.RESET_ALL}", end=" ")
                new_name = input("Enter name (↵ to keep current): ").strip()
                
                if new_name:
                    return selected_gender, new_name, selected_key
            
            return selected_gender, character, selected_key
    except ValueError:
        pass
        
    category_key, standard_label = standardize_gender(current_gender)
    return standard_label, character, category_key

#------------------------------------------------------------------------------
# Text Processing
#------------------------------------------------------------------------------

def improved_chunk_text(text, max_tokens=80000):
    """Split text into chunks while preserving context.
    
    With GPT-4's 128k context window, we use chunks of 80k tokens to leave room for:
    - System prompts and instructions (~10k tokens)
    - Response space (up to 16k tokens)
    - Safety margin (~22k tokens)
    """
    print(f"\n{Fore.CYAN}┌─ Starting text chunking process{Style.RESET_ALL}")
    print(f"{Fore.CYAN}├─ Text length: {Fore.YELLOW}{len(text):,}{Fore.CYAN} characters{Style.RESET_ALL}")
    
    # Create text splitter with larger chunks and overlap
    print(f"{Fore.CYAN}├─ Chunk settings:{Style.RESET_ALL}")
    print(f"│  └─ Max size: {Fore.YELLOW}{max_tokens}{Style.RESET_ALL} tokens")
    print(f"│  └─ Overlap : {Fore.YELLOW}1000{Style.RESET_ALL} tokens")  # Increased overlap for better context
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_tokens,
        chunk_overlap=1000,  # Increased from 200 to 1000
        length_function=len,
        is_separator_regex=False
    )
    
    # Split text and show progress
    print(f"{Fore.CYAN}├─ Splitting text...{Style.RESET_ALL}")
    chunks = text_splitter.split_text(text)
    print(f"{Fore.GREEN}├─ Created {Fore.YELLOW}{len(chunks)}{Fore.GREEN} chunks{Style.RESET_ALL}")
    
    # Process character contexts
    character_contexts = []
    all_characters = set()
    
    print(f"{Fore.CYAN}├─ Analyzing chunks:{Style.RESET_ALL}")
    for i, chunk in enumerate(chunks):
        # Get first and last 50 characters of chunk
        start = chunk[:50].replace('\n', '↵')
        end = chunk[-50:].replace('\n', '↵')
        
        # Extract characters and update context
        character_info = extract_characters_from_chunk(chunk)
        all_characters.update(character_info['characters'])
        
        # Store context for this chunk
        character_contexts.append({
            'chunk_index': i,
            'character_info': character_info,
            'all_characters_so_far': set(all_characters)
        })
        
        # Show chunk info
        print(f"│  Chunk {i + 1}: {Fore.YELLOW}{len(chunk):,}{Style.RESET_ALL} chars")
        print(f"│  ├─ Start: {Fore.WHITE}{start}...{Style.RESET_ALL}")
        print(f"│  ├─ End: {Fore.WHITE}...{end}{Style.RESET_ALL}")
        
        # Show characters found in chunk
        if character_info['characters']:
            chars = ", ".join(sorted(character_info['characters']))
            print(f"│  └─ Characters: {Fore.YELLOW}{chars}{Style.RESET_ALL}")
            # Show character locations
            for char in sorted(character_info['characters']):
                locations = character_info['character_locations'][char]
                if locations:
                    pos_list = ", ".join(str(pos) for pos in locations)
                    print(f"│     └─ {char} at positions: {pos_list}")
        print(f"│")
    
    # Show final statistics
    print(f"{Fore.CYAN}└─ Total unique characters: {Fore.YELLOW}{len(all_characters)}{Style.RESET_ALL}")
    
    return chunks, character_contexts

#------------------------------------------------------------------------------
# File I/O and Logging
#------------------------------------------------------------------------------

def load_input_text(file_path):
    """Load input text file with enhanced validation and feedback.
    
    Args:
        file_path (str): Path to the input text file
        
    Returns:
        tuple: (content, status_message)
            - content: The text content if successful, None if failed
            - status_message: A user-friendly status message about the operation
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
            # Basic validation
            if not content.strip():
                return None, f"{Fore.RED}✗ File is empty: {file_path}{Style.RESET_ALL}"
                
            # Success message with file stats
            word_count = len(content.split())
            char_count = len(content)
            status = (
                f"{Fore.GREEN}✓ Successfully loaded: {Fore.BLUE}{file_path}{Style.RESET_ALL}\n"
                f"  └─ {Fore.YELLOW}{word_count:,}{Style.RESET_ALL} words, "
                f"{Fore.YELLOW}{char_count:,}{Style.RESET_ALL} characters"
            )
            return content, status
            
    except FileNotFoundError:
        return None, f"{Fore.RED}✗ File not found: {file_path}{Style.RESET_ALL}"
    except UnicodeDecodeError:
        return None, f"{Fore.RED}✗ File encoding error. Please ensure the file is UTF-8 encoded: {file_path}{Style.RESET_ALL}"
    except Exception as e:
        return None, f"{Fore.RED}✗ Error loading file: {str(e)}{Style.RESET_ALL}"

def log_output(original_text, processed_result):
    """Log original and processed text to files.
    
    Writes three files for the current run:
    - logs/original.txt: The input text
    - logs/processed.txt: The transformed text
    - logs/diff.txt: Differences between original and processed
    """
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    # Unpack the tuple if it's a tuple, otherwise use the text directly
    processed_text = processed_result[0] if isinstance(processed_result, tuple) else processed_result
    
    # Log original text
    with open("logs/original.txt", "w", encoding="utf-8") as file:
        file.write(original_text)
    
    # Log processed text
    with open("logs/processed.txt", "w", encoding="utf-8") as file:
        file.write(processed_text)
    
    # Create diff if original text exists
    if original_text:
        create_diff(original_text, processed_text)
        
    print(f"\n{Fore.GREEN}✓ Output logged to logs/processed.txt{Style.RESET_ALL}")

def create_diff(original_text, processed_text):
    """Create a diff between original and processed text."""
    # Create diff file
    diff_file = "logs/diff.txt"
    with open(diff_file, 'w', encoding='utf-8') as f:
        f.write("DIFFERENCE SUMMARY\n")
        f.write("=" * 25 + "\n\n")
        
        # Calculate differences
        original_lines = original_text.splitlines()
        processed_lines = processed_text.splitlines()
        
        # Handle cases where line counts differ
        max_lines = max(len(original_lines), len(processed_lines))
        original_lines.extend([''] * (max_lines - len(original_lines)))
        processed_lines.extend([''] * (max_lines - len(processed_lines)))
        
        diff_lines = []
        for i, (orig_line, proc_line) in enumerate(zip(original_lines, processed_lines)):
            if orig_line != proc_line:
                diff_lines.append(f"Line {i+1}:")
                diff_lines.append(f"  Original: {orig_line}")
                diff_lines.append(f"  Processed: {proc_line}")
                diff_lines.append("")
        
        if diff_lines:
            f.write("\n".join(diff_lines))
        else:
            f.write("No differences found between original and processed text.")
    
    print(f"{Fore.GREEN}✓ Diff logged to {diff_file}{Style.RESET_ALL}")

def write_debug_log(events, timestamp):
    """Write debug events to a linked debug log file."""
    debug_file = f"logs/{timestamp}_debug.log"
    with open(debug_file, 'w', encoding='utf-8') as f:
        f.write("~DEBUG LOGGING v1.1\n\n")
        f.write("LINKED FILES\n")
        f.write("============\n")
        f.write(f"Main Log: {timestamp}_regender.log\n")
        f.write(f"Debug Log: {timestamp}_debug.log\n\n")
        f.write("DEBUG EVENTS\n")
        f.write("============\n")
        f.write('\n'.join(events))
    
    return debug_file

#------------------------------------------------------------------------------
# Main Application Logic
#------------------------------------------------------------------------------

def detect_all_characters(chunks, character_contexts):
    """Detect all characters across all chunks before any user interaction.
    
    Args:
        chunks (list): List of text chunks
        character_contexts (list): List of context dictionaries for each chunk
        
    Returns:
        tuple: (all_characters, roles_by_character)
            - all_characters: Set of all unique characters
            - roles_by_character: Dict mapping characters to their roles
    """
    all_characters = set()
    roles_by_character = {}
    
    print(f"\n{Fore.CYAN}Phase 1: Initial Character Detection{Style.RESET_ALL}")
    
    for i, (chunk, context) in enumerate(zip(chunks, character_contexts)):
        if not context['character_info']['characters']:
            continue
            
        print(f"\n{Fore.CYAN}[{i+1}/{len(chunks)}]{Style.RESET_ALL} Analyzing chunk...")
        
        # Get roles for this chunk
        roles_info = detect_roles_gpt(chunk)
        if roles_info:
            for line in roles_info.splitlines():
                parts = line.split(" - ")
                if len(parts) == 3:
                    character, role_desc, gender = parts
                    character = clean_name(character)
                    
                    all_characters.add(character)
                    if character not in roles_by_character:
                        roles_by_character[character] = {
                            'role': role_desc,
                            'original_gender': gender,
                            'appearances': []
                        }
                    
                    roles_by_character[character]['appearances'].append(i)
                    
        # Show progress
        print(f"└─ Found {Fore.YELLOW}{len(context['character_info']['characters'])}{Style.RESET_ALL} characters in chunk")
    
    print(f"\n{Fore.GREEN}✓ Character Detection Complete")
    print(f"└─ Found {Fore.YELLOW}{len(all_characters)}{Style.RESET_ALL} unique characters")
    
    # Log the initial character detection results
    detection_log = "logs/initial_detection.json"
    with open(detection_log, 'w', encoding='utf-8') as f:
        json.dump({
            'all_characters': list(all_characters),
            'roles_by_character': roles_by_character
        }, f, indent=4)
    print(f"└─ Detection results saved to: {Fore.YELLOW}{detection_log}{Style.RESET_ALL}")
    
    return all_characters, roles_by_character

def handle_user_input_phase(all_characters, roles_by_character):
    """Handle all user input for character changes in a single phase.
    
    Args:
        all_characters (set): Set of all unique characters
        roles_by_character (dict): Dict mapping characters to their roles
        
    Returns:
        tuple: (confirmed_genders, name_mappings)
    """
    print(f"\n{Fore.CYAN}┌─ Character Gender and Name Decisions{Style.RESET_ALL}")
    print(f"├─ {Fore.YELLOW}{len(all_characters)}{Fore.CYAN} characters found{Style.RESET_ALL}")
    
    confirmed_genders = {}
    name_mappings = {}
    character_decisions = []
    
    # Sort characters by appearance count for prioritization
    sorted_characters = sorted(
        all_characters,
        key=lambda x: len(roles_by_character[x]['appearances']),
        reverse=True
    )
    
    for idx, character in enumerate(sorted_characters, 1):
        role_info = roles_by_character[character]
        current_gender = role_info['original_gender']
        
        # Show character context
        appearances = len(role_info['appearances'])
        print(f"\n{Fore.CYAN}Character {idx}/{len(sorted_characters)}:{Style.RESET_ALL}")
        print(f"└─ Name: {Fore.YELLOW}{character}{Style.RESET_ALL}")
        print(f"   Role: {role_info['role']}")
        print(f"   Current Gender: {current_gender}")
        print(f"   Appearances: {appearances} chunks")
        
        # Get user decisions
        standardized_gender, new_name, gender_category = get_user_gender_choice(
            character, current_gender
        )
        
        confirmed_genders[character] = standardized_gender
        if new_name != character:
            name_mappings[character] = new_name
        
        # Store decision for logging
        character_decisions.append({
            "original_name": character,
            "new_name": new_name,
            "original_gender": current_gender,
            "new_gender": standardized_gender,
            "role": role_info['role'],
            "appearances": role_info['appearances']
        })
    
    # Log all decisions
    decisions_log = "logs/character_decisions.json"
    with open(decisions_log, 'w', encoding='utf-8') as f:
        json.dump({
            "total_characters": len(all_characters),
            "decisions": character_decisions
        }, f, indent=4)
    print(f"\n{Fore.GREEN}✓ Character decisions saved to: {decisions_log}{Style.RESET_ALL}")
    
    return confirmed_genders, name_mappings

def process_chunks_with_context(chunks, character_contexts, confirmed_genders):
    """Process text chunks while maintaining character context."""
    print(f"\n{Fore.CYAN}┌─ Starting text transformation{Style.RESET_ALL}")
    
    combined_text = ""
    events = []
    
    for i, (chunk, context) in enumerate(zip(chunks, character_contexts), 1):
        print(f"{Fore.CYAN}├─ Processing chunk {i}/{len(chunks)}{Style.RESET_ALL}")
        
        # Transform this chunk
        transformed_chunk = regender_text_gpt(
            chunk,
            confirmed_genders
        )
        
        combined_text += transformed_chunk
        
        if i < len(chunks):
            print(f"{Fore.CYAN}│{Style.RESET_ALL}")
    
    print(f"{Fore.GREEN}└─ Text transformation complete{Style.RESET_ALL}")
    return combined_text

def confirm_new_characters(roles_info, confirmed_genders, new_characters):
    """Process and confirm gender choices for new characters."""
    confirmed_roles = []
    name_mappings = {}
    events = []
    
    for role in roles_info.splitlines():
        parts = role.split(" - ")
        if len(parts) != 3:
            continue
            
        character, role_desc, gender = parts
        character = clean_name(character)
        
        if character in new_characters:
            original_name = character
            original_gender = gender
            
            events.append(f"Found new character: {character} ({role_desc})")
            standardized_gender, new_name, gender_category = get_user_gender_choice(character, gender)
            confirmed_genders[character] = standardized_gender
            
            events.append(f"  -> Gender set to: {standardized_gender}")

            if new_name != character:
                name_mappings[character] = new_name
                character = new_name
                events.append(f"  -> Character renamed to: {new_name}")
            
            role_entry = {
                "Original_Name": original_name,
                "Original_Role": role_desc,
                "Original_Gender": original_gender,
                "Updated_Name": new_name if new_name != original_name else original_name,
                "Updated_Role": role_desc,
                "Updated_Gender": standardized_gender,
                "Gender_Category": gender_category,
            }
            
            confirmed_roles.append(f"{character} - {role_desc} - {standardized_gender}")
        else:
            current_gender = confirmed_genders.get(character, gender)
            confirmed_roles.append(f"{character} - {role_desc} - {current_gender}")
    
    return confirmed_roles, name_mappings, events

def get_character_role_from_json(character_name, file_path="character_roles_genders.json"):
    """Get character data from JSON storage."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            for char in data["Characters"]:
                if clean_name(char["Original_Name"]) == character_name:
                    return {
                        "role": char["Original_Role"],
                        "gender": char["Updated_Gender"] if "Updated_Gender" in char else char["Original_Gender"]
                    }
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    return None

def load_confirmed_genders(file_path="character_roles_genders.json"):
    """Load saved gender information from JSON."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read().strip()
            if not content:
                raise FileNotFoundError
            data = json.loads(content)
            confirmed_genders = {character["Original_Name"]: character["Original_Gender"] for character in data["Characters"]}
        print(f"{Fore.GREEN}├─ Confirmed genders loaded from {file_path}{Style.RESET_ALL}")
    except FileNotFoundError:
        confirmed_genders = {}
        print(f"No confirmed genders file found or file is empty. Starting with an empty dictionary.")
    return confirmed_genders

def clean_name(name):
    """Remove leading numbers and periods from names."""
    return re.sub(r'^\d+\.\s*', '', name).strip()

def regender_text_gpt(input_text, confirmed_genders, name_mappings=None):
    """Process text with gender and name changes."""
    if name_mappings is None:
        name_mappings = {}
        
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Updated model name
            messages=[
                {"role": "system", "content": "You are a literary text transformation assistant. Your task is to carefully transform character genders while preserving the narrative flow, tone, and literary quality of the text."},
                {"role": "user", "content": f"Transform this text by changing character genders as specified. Preserve all literary qualities, narrative flow, and maintain consistent pronouns and gender references throughout:\n\nCharacter Gender Map:\n{json.dumps(confirmed_genders, indent=2)}\n\nText to Transform:\n{input_text}"}
            ],
            max_tokens=16000,  # Set to maximum allowed output tokens
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"{Fore.RED}Error in regender_text_gpt: {str(e)}{Style.RESET_ALL}")
        return input_text

def update_character_roles_genders_json(confirmed_roles, name_mappings=None, file_path="character_roles_genders.json"):
    """Update character information JSON with new data."""
    if name_mappings is None:
        name_mappings = {}

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except FileNotFoundError:
        data = {"Characters": []}

    try:
        with open("original_character_info.json", 'r', encoding='utf-8') as f:
            original_info = json.load(f)
    except FileNotFoundError:
        original_info = {}

    updated_characters = []
    
    for role in confirmed_roles:
        parts = role.split(" - ")
        if len(parts) == 3:
            new_name, role_desc, gender = parts
            new_name = clean_name(new_name)
            
            original_character = None
            for orig_name, orig_data in original_info.items():
                if new_name in [orig_name, name_mappings.get(orig_name)]:
                    original_character = orig_data
                    break
            
            category_key, standard_label = standardize_gender(gender)
            
            character_entry = {
                "Original_Name": original_character["name"] if original_character else new_name,
                "Original_Role": original_character["role"] if original_character else role_desc,
                "Original_Gender": original_character["gender"] if original_character else gender,
                "Updated_Name": new_name,
                "Updated_Role": role_desc,
                "Updated_Gender": standard_label,
                "Gender_Category": category_key
            }
            updated_characters.append(character_entry)

    data["Characters"] = updated_characters
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump({"Characters": updated_characters}, file, ensure_ascii=False, indent=4)
    print(f"\n{Fore.GREEN}✓ Updated character roles and genders saved to {file_path}{Style.RESET_ALL}")

def log_character_mapping(character_contexts):
    """Create a visualization of character presence in chunks and save to log."""
    mermaid_diagram = create_character_mapping_diagram(character_contexts)
    
    # Save diagram to a file
    diagram_file = "logs/character_mapping.mermaid"
    with open(diagram_file, 'w', encoding='utf-8') as f:
        f.write(mermaid_diagram)
    
    # Also create a text-based summary
    summary_file = "logs/character_summary.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("CHARACTER PRESENCE SUMMARY\n")
        f.write("=" * 25 + "\n\n")
        
        # Get all unique characters
        all_characters = set()
        for context in character_contexts:
            all_characters.update(context['character_info']['characters'])
        
        # Write summary for each character
        for char in sorted(all_characters):
            f.write(f"\nCharacter: {char}\n")
            f.write("-" * (len(char) + 10) + "\n")
            
            for i, context in enumerate(character_contexts):
                char_info = context['character_info']
                if char in char_info['characters']:
                    locations = char_info['character_locations'].get(char, [])
                    f.write(f"Chunk {i}: Present at positions {locations}\n")
                else:
                    f.write(f"Chunk {i}: Not present\n")
            f.write("\n")
    
    return diagram_file, summary_file

def create_character_mapping_diagram(character_contexts):
    """Create a Mermaid diagram showing character presence across chunks."""
    
    # Get unique characters across all chunks
    all_characters = set()
    for context in character_contexts:
        all_characters.update(context['character_info']['characters'])
    
    # Start building Mermaid diagram
    mermaid_lines = [
        "graph TD",
        "    subgraph Characters",
    ]
    
    # Add character nodes
    for char in sorted(all_characters):
        char_id = char.replace(" ", "_").replace("/", "_")
        mermaid_lines.append(f'        {char_id}["{char}"]')
    
    mermaid_lines.append("    end")
    mermaid_lines.append("")
    
    # Create chunk subgraph
    mermaid_lines.append("    subgraph ChunkIndex[\"Chunk Index\"]")
    for i in range(len(character_contexts)):
        mermaid_lines.append(
            f'        C{i}["Chunk {i}<br/>'
            f'[Paragraphs {i*2+1}-{i*2+2}]"]'
        )
    mermaid_lines.append("    end")
    mermaid_lines.append("")
    
    # Create presence/absence markers and connections
    for char in sorted(all_characters):
        char_id = char.replace(" ", "_").replace("/", "_")
        for i, context in enumerate(character_contexts):
            present = char in context['character_info']['characters']
            marker = "✓" if present else "×"
            
            # Create presence/absence node
            node_id = f"{char_id}_{i}"
            style_class = "present" if present else "absent"
            mermaid_lines.append(f'    {node_id}["{marker}"]')
            
            # Connect character to marker
            if i == 0:  # Direct connection for first chunk
                mermaid_lines.append(f'    {char_id} --> {node_id}')
            else:  # Dotted line for subsequent chunks
                mermaid_lines.append(f'    {char_id} -.-> {node_id}')
            
            # Connect marker to chunk
            mermaid_lines.append(f'    {node_id} --> C{i}')
    
    # Add styles
    mermaid_lines.extend([
        "",
        "    style Lucy fill:#f9f,stroke:#333",
        "    style Mrs fill:#f9f,stroke:#333",
        "    style Professor fill:#f9f,stroke:#333",
        "",
        "    classDef present fill:#d4edda,stroke:#333",
        "    classDef absent fill:#f8d7da,stroke:#333",
        "    class " + ",".join([
            f"{char.replace(' ', '_')}_{i}" 
            for char in all_characters 
            for i, context in enumerate(character_contexts)
            if char in context['character_info']['characters']
        ]) + " present",
        "    class " + ",".join([
            f"{char.replace(' ', '_')}_{i}"
            for char in all_characters
            for i, context in enumerate(character_contexts)
            if char not in context['character_info']['characters']
        ]) + " absent"
    ])
    
    return "\n".join(mermaid_lines)

#------------------------------------------------------------------------------
# Main Application Function
#------------------------------------------------------------------------------

def main():
    """Main application entry point."""
    print_startup_sequence()
    
    # Check API connection
    if not check_openai_api_key():
        return
    
    # Get input file from command line
    if len(sys.argv) != 2:
        print(f"{Fore.RED}✗ Please provide an input file path{Style.RESET_ALL}")
        print(f"Usage: python {sys.argv[0]} input_file.txt")
        return
    
    input_file = sys.argv[1]
    
    # Load and validate input text
    content, status = load_input_text(input_file)
    if not content:
        print(status)
        return
    print(status)
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Process text in chunks
    chunks, character_contexts = improved_chunk_text(content)
    
    # Detect all characters before user interaction
    all_characters, roles_by_character = detect_all_characters(
        chunks, character_contexts
    )
    
    # Handle all user input in a single phase
    confirmed_genders, name_mappings = handle_user_input_phase(
        all_characters, roles_by_character
    )
    
    # Process chunks with confirmed changes
    updated_text = process_chunks_with_context(
        chunks, character_contexts, confirmed_genders
    )
    
    # Log results
    log_output(content, updated_text)
    print(f"\n{Fore.GREEN}✓ Processing complete!{Style.RESET_ALL}")

if __name__ == "__main__":
    main()