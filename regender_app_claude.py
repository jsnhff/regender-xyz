import os
import time
from openai import OpenAI
from datetime import datetime
import json
from langchain.text_splitter import RecursiveCharacterTextSplitter
import re
# Add to your imports
from colorama import init, Fore, Style
init(autoreset=True)  # Initialize colorama

# Initialize the OpenAI client with your API key
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def check_openai_api_key():
    """
    Verify OpenAI API key with styled output.
    """
    try:
        client.models.list()
        print(f"{Fore.GREEN}✓ API connection established{Style.RESET_ALL}")
        return True
    except Exception as e:
        print(f"{Fore.RED}✗ API Error: Please check your OpenAI API key{Style.RESET_ALL}")
        return False

check_openai_api_key()

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

def print_banner():
    """
    Print a more ornate application banner with proper alignment.
    """
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
    """
    Print an animated startup sequence.
    """
    # Clear screen first
    print("\033[H\033[J", end="")
    
    # Print banner
    print_banner()
    
    # Initialization message
    print(f"{Fore.CYAN}┌─{Style.RESET_ALL} System Initialization")
    print(f"{Fore.CYAN}│{Style.RESET_ALL}")

# Add this utility function for consistent status messages
def print_status(message, status_type="info"):
    """
    Print formatted status messages.
    """
    symbols = {
        "info": f"{Fore.BLUE}ℹ{Style.RESET_ALL}",
        "success": f"{Fore.GREEN}✓{Style.RESET_ALL}",
        "warning": f"{Fore.YELLOW}⚠{Style.RESET_ALL}",
        "error": f"{Fore.RED}✗{Style.RESET_ALL}"
    }
    print(f" {symbols.get(status_type, symbols['info'])} {message}")

def standardize_gender(gender_text):
    """
    Map various gender descriptions to standard categories.
    Returns tuple of (category_key, category_label).
    """
    if not gender_text:
        return 'UNK', GENDER_CATEGORIES['UNK']['label']
        
    gender_text = gender_text.lower().strip()
    
    # Direct match with category labels
    for category_key, category_data in GENDER_CATEGORIES.items():
        if gender_text == category_data['label'].lower():
            return category_key, category_data['label']
    
    # Check terms for each category
    for category_key, category_data in GENDER_CATEGORIES.items():
        if any(term in gender_text for term in category_data['terms']):
            return category_key, category_data['label']
    
    return 'UNK', GENDER_CATEGORIES['UNK']['label']

def get_user_gender_choice(character, current_gender):
    """
    Enhanced gender selection interface with colored formatting.
    Returns tuple of (selected_gender, new_name, gender_category).
    """
    # No change: Your existing nice CLI formatting
    print(f"\n{Fore.CYAN}╭─ Character: {Fore.WHITE}{character} {Fore.YELLOW}({current_gender.strip()}){Style.RESET_ALL}")
    print(f"{Fore.CYAN}├─ Select Gender:{Style.RESET_ALL}")
    
    # No change: Your existing menu display
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
        # NEW: When keeping current gender, standardize it and return all three values
        # Old: return current_gender, character
        category_key, standard_label = standardize_gender(current_gender)
        return standard_label, character, category_key
        
    try:
        choice_idx = int(choice) - 1
        # NEW: Explicit mapping of menu choices to gender categories
        # This ensures we always use the correct category keys
        category_keys = ['M', 'F', 'NB']  # Maps 1->M, 2->F, 3->NB
        
        if 0 <= choice_idx < len(category_keys):
            # NEW: Get the category key based on user's choice
            selected_key = category_keys[choice_idx]
            # NEW: Get the standard label for this category (Male/Female/Non-binary)
            selected_gender = GENDER_CATEGORIES[selected_key]['label']
            
            if selected_gender.lower() != current_gender.lower():
                # No change: Your existing name suggestion UI
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
                    # NEW: Return all three values (gender label, new name, category)
                    return selected_gender, new_name, selected_key
            
            # NEW: Return all three values (gender label, same name, category)
            return selected_gender, character, selected_key
    except ValueError:
        pass
        
    # NEW: If anything goes wrong, standardize current gender and return all three values
    category_key, standard_label = standardize_gender(current_gender)
    return standard_label, character, category_key

def get_gpt_response(prompt, model="gpt-4o-mini", temperature=0.7, retries=3, delay=5):
    """
    Function to interact with OpenAI's gpt-4o-mini API using the chat endpoint.
    Includes retry mechanism for handling API errors.
    """
    attempt = 0
    while attempt < retries:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error: {e}")
            attempt += 1
            time.sleep(delay)
    return "Error: Unable to get response after multiple attempts"

def detect_roles_gpt(input_text):
    """
    Function to detect character roles and store original info immediately.
    """
    # No change: Get roles from GPT
    prompt = f"Identify all the characters, their roles, and their genders in the following text:\n\n{input_text}\n\nProvide the results in a structured format like: Character - Role - Gender. Arrange the results in a numbered list."
    response = get_gpt_response(prompt)
    lines = response.split('\n')
    character_list = [line for line in lines if " - " in line]
    
    # NEW: Store original info right when we first see it
    original_info = {}
    for line in character_list:
        parts = line.split(" - ")
        if len(parts) == 3:
            original_name, role, gender = parts
            original_name = clean_name(original_name)
            original_info[original_name] = {
                "name": original_name,    # This is the truly original name
                "role": role,
                "gender": gender.strip()  # Clean up any whitespace
            }
    
    # NEW: Save original info immediately
    try:
        with open("original_character_info.json", 'w', encoding='utf-8') as f:
            json.dump(original_info, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"{Fore.YELLOW}Warning: Could not save original character info: {e}{Style.RESET_ALL}")
    
    return '\n'.join(character_list)

def update_character_roles_genders_json(confirmed_roles, name_mappings=None, file_path="character_roles_genders.json"):
    """
    Updated version to use original character information.
    """
    # NEW: Initialize name_mappings if None
    if name_mappings is None:
        name_mappings = {}

    # No change: Load existing JSON data
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except FileNotFoundError:
        data = {"Characters": []}

    # NEW: Load original character information
    try:
        with open("original_character_info.json", 'r', encoding='utf-8') as f:
            original_info = json.load(f)
    except FileNotFoundError:
        original_info = {}

    # No change: Initialize updated characters list
    updated_characters = []
    
    # No change: Process each confirmed role
    for role in confirmed_roles:
        parts = role.split(" - ")
        if len(parts) == 3:
            new_name, role_desc, gender = parts
            new_name = clean_name(new_name)
            
            # NEW: Look up original character information
            original_character = None
            for orig_name, orig_data in original_info.items():
                if new_name in [orig_name, name_mappings.get(orig_name)]:
                    original_character = orig_data
                    break
            
            # No change: Get gender category
            category_key, standard_label = standardize_gender(gender)
            
            # NEW: Create character entry using original info when available
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

    # No change: Save updated data
    data["Characters"] = updated_characters
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump({"Characters": updated_characters}, file, ensure_ascii=False, indent=4)
    print(f"\n{Fore.GREEN}✓ Updated character roles and genders saved to {file_path}{Style.RESET_ALL}")

# NEW: Entire function is new
def save_original_character_info(info, file_path="original_character_info.json"):
    """
    Save the original character information to a separate JSON file.
    """
    try:
        # Try to load existing data
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        except FileNotFoundError:
            existing_data = {}
        
        # Update with new info, but don't overwrite existing entries
        for name, data in info.items():
            if name not in existing_data:
                existing_data[name] = data
        
        # Write updated data back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"{Fore.YELLOW}Warning: Could not save original character info: {e}{Style.RESET_ALL}")

def regender_text_gpt(input_text, confirmed_roles, name_mappings=None, timestamp=None):
    """
    Updated version to process all characters from JSON.
    """
    if name_mappings is None:
        name_mappings = {}
        
    gender_guidelines = []
    name_instructions = []
    debug_events = []
    
    debug_events.append(f"\nDEBUG - Starting regender_text_gpt")
    
    # Load current character data from JSON
    try:
        with open("character_roles_genders.json", 'r', encoding='utf-8') as f:
            char_data = json.load(f)
            debug_events.append(f"Loaded character data from JSON:")
            debug_events.append(json.dumps(char_data, indent=2))
    except Exception as e:
        debug_events.append(f"Error loading character data: {str(e)}")
        char_data = {"Characters": []}
    
    # Process all characters from JSON
    for char in char_data["Characters"]:
        character = char["Updated_Name"]
        gender = char["Updated_Gender"]
        gender_category = char["Gender_Category"]
        
        debug_events.append(f"\nDEBUG - Processing character: {character}")
        debug_events.append(f"  Gender: {gender}")
        debug_events.append(f"  Category: {gender_category}")
        
        if gender_category in GENDER_CATEGORIES:
            pronouns = GENDER_CATEGORIES[gender_category]['pronouns']
            debug_events.append(f"  Pronouns to use: {'/'.join(pronouns)}")
            
            # Create detailed pronoun instructions
            gender_guidelines.append(
                f"{character} ({gender}):\n"
                f"- Use pronouns: {'/'.join(pronouns)}\n"
                f"- Replace any she/her/hers with {'/'.join(pronouns)} when referring to {character}"
            )
    
    # Add name change instructions
    for old_name, new_name in name_mappings.items():
        name_instructions.append(f"Replace all instances of '{old_name}' with '{new_name}'")
        debug_events.append(f"\nDEBUG - Name change: {old_name} → {new_name}")

    # Create the prompt
    prompt = (
        f"Regender the following text exactly as specified:\n\n"
        f"1. Name changes (apply these first and exactly):\n{chr(10).join(name_instructions)}\n\n"
        f"2. Character pronouns (apply these consistently):\n{chr(10).join(gender_guidelines)}\n\n"
        f"3. Important rules:\n"
        f"- Apply name changes first, then handle pronouns\n"
        f"- Be thorough: check every pronoun and name reference\n"
        f"- Maintain story flow and readability\n"
        f"- Keep other character references unchanged\n\n"
        f"Text to regender:\n{input_text}\n\n"
        f"Return only the regendered text, no explanations."
    )
    
    debug_events.append("\nDEBUG - Final prompt to GPT:")
    debug_events.append(prompt)
    
    response = get_gpt_response(prompt, temperature=0.1)
    debug_events.append("\nDEBUG - GPT Response:")
    debug_events.append(response)
    
    # Write to linked debug log
    write_debug_log(debug_events, timestamp)
    
    return response

def log_output(original_text, updated_text, events_list=None, json_path="character_roles_genders.json", timestamp=None):
    """
    Enhanced logging function that links to debug logs.
    """
    if not os.path.exists("logs"):
        os.makedirs("logs")

    # Use provided timestamp or create new one
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    file_path = os.path.join("logs", f"{timestamp}_regender.log")
    debug_file_path = os.path.join("logs", f"{timestamp}_debug.log")
    separator = "\n" + "="*80 + "\n"

    # Calculate character statistics
    orig_count = len(original_text)
    updated_count = len(updated_text)
    diff_count = abs(orig_count - updated_count)
    
    # Create statistics summary
    stats_summary = (
        "CHARACTER STATISTICS\n"
        "====================\n"
        f"Original text character count: {orig_count:,}\n"
        f"Updated text character count: {updated_count:,}\n"
        f"Difference in characters: {diff_count:,}\n"
    )

    try:
        with open(json_path, 'r', encoding='utf-8') as json_file:
            character_data = json.load(json_file)
            char_count = len(character_data.get("Characters", []))
            stats_summary += f"Total named characters processed: {char_count}\n"
    except Exception as e:
        character_data = {"Characters": [], "error": str(e)}

    # Write all sections to the log file
    with open(file_path, 'w', encoding='utf-8') as file:
        # Write log version and linked files first
        file.write("~LOGGING v1.1\n\n")
        file.write("LINKED FILES\n")
        file.write("============\n")
        file.write(f"Main Log: {timestamp}_regender.log\n")
        file.write(f"Debug Log: {timestamp}_debug.log\n\n")

        # Write statistics
        file.write(stats_summary)
        file.write(separator)

        # Original text section
        file.write("ORIGINAL TEXT")
        file.write(separator)
        file.write(original_text)
        file.write(separator)

        # Updated text section
        file.write("UPDATED TEXT")
        file.write(separator)
        file.write(updated_text)
        file.write(separator)

        # Character roles and genders section
        file.write("CHARACTER ROLES AND GENDERS")
        file.write(separator)
        file.write(json.dumps(character_data, indent=4))
        file.write(separator)

        # Processing events section
        file.write("PROCESSING EVENTS")
        file.write(separator)
        if events_list:
            for event in events_list:
                file.write(f"- {event}\n")
        else:
            file.write("No notable events recorded during processing.\n")
        file.write(separator)

    print(f"{Fore.GREEN}✓ Log files created:")
    print(f"  {Fore.YELLOW}Main: {timestamp}_regender.log")
    print(f"  {Fore.YELLOW}Debug: {timestamp}_debug.log{Style.RESET_ALL}")

def write_debug_log(events, timestamp):
    """
    Write debug events to a linked debug log file.
    """
    debug_file = f"logs/{timestamp}_debug.log"
    with open(debug_file, 'w', encoding='utf-8') as f:
        # Write header with linked files
        f.write("~DEBUG LOGGING v1.1\n\n")
        f.write("LINKED FILES\n")
        f.write("============\n")
        f.write(f"Main Log: {timestamp}_regender.log\n")
        f.write(f"Debug Log: {timestamp}_debug.log\n\n")
        
        # Write debug events
        f.write("DEBUG EVENTS\n")
        f.write("============\n")
        f.write('\n'.join(events))
    
    return debug_file

def load_input_text(file_path):
    """
    Load input text with status feedback.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            print(f"{Fore.GREEN}✓ Loaded: {Fore.BLUE}{file_path}{Style.RESET_ALL}")
            return content
    except FileNotFoundError:
        print(f"{Fore.RED}✗ File not found: {file_path}{Style.RESET_ALL}")
        return None
    except Exception as e:
        print(f"{Fore.RED}✗ Error loading file: {str(e)}{Style.RESET_ALL}")
        return None

def improved_chunk_text(text, max_tokens=1000):
    """
    Enhanced text chunking that preserves sentence boundaries and maintains context between chunks.
    Returns both chunks and their character context.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_tokens,
        chunk_overlap=200,  # Increased overlap to maintain better context
        separators=["\n\n", "\n", ".", "!", "?", " "],  # Priority order for splitting
        keep_separator=True
    )
    chunks = text_splitter.split_text(text)
    
    # Track character mentions across chunks
    character_contexts = []
    all_characters = set()
    
    for i, chunk in enumerate(chunks):
        # Extract character mentions from current chunk
        characters_in_chunk = extract_characters_from_chunk(chunk)
        all_characters.update(characters_in_chunk)
        
        character_contexts.append({
            'chunk_index': i,
            'characters': characters_in_chunk,
            'all_characters_so_far': set(all_characters)  # Copy of running character set
        })
    
    return chunks, character_contexts

def extract_characters_from_chunk(chunk):
    """
    Helper function to extract character mentions from a chunk using existing role detection.
    """
    roles_info = detect_roles_gpt(chunk)
    characters = set()
    
    if roles_info:
        for line in roles_info.splitlines():
            parts = line.split(" - ")
            if len(parts) >= 1:
                character = clean_name(parts[0])
                characters.add(character)
    
    return characters

def process_chunks_with_context(chunks, character_contexts, confirmed_genders, timestamp):
    """
    Updated processing with timestamp for logging.
    """
    all_regendered_text = []
    name_mappings = {}
    all_events = []  # Initialize events list
    
    total_chunks = len(chunks)
    
    for i, (chunk, context) in enumerate(zip(chunks, character_contexts)):
        # Add basic chunk processing event
        all_events.append(f"Processing chunk {i+1} of {total_chunks}")

        # Progress indicator
        progress = f"{Fore.CYAN}[{i+1}/{total_chunks}]{Style.RESET_ALL}"
        print(f"\n{progress} Processing chunk...")
        
        if context['characters']:
            chars = ", ".join(f"{Fore.YELLOW}{c}{Style.RESET_ALL}" for c in context['characters'])
            print(f"└─ Characters found: {chars}")
        
        new_characters = context['characters'] - set(confirmed_genders.keys())
        if new_characters:
            new_chars = ", ".join(f"{Fore.GREEN}{c}{Style.RESET_ALL}" for c in new_characters)
            print(f"└─ New characters found: {new_chars}")
            
            roles_info = detect_roles_gpt(chunk)
            if roles_info:
                confirmed_roles, chunk_name_mappings, new_events = confirm_new_characters(
                    roles_info, confirmed_genders, new_characters
                )
                all_events.extend(new_events)  # Add the new events to our collection
                name_mappings.update(chunk_name_mappings)
                update_character_roles_genders_json(confirmed_roles, name_mappings)
        
        # Rest of the processing...
        all_confirmed_roles = []
        for character in context['all_characters_so_far']:
            if character in confirmed_genders:
                role_info = get_character_role_from_json(character)
                if role_info:
                    current_name = name_mappings.get(character, character)
                    all_confirmed_roles.append(
                        f"{current_name} - {role_info['role']} - {role_info['gender']}"
                    )
        
        regendered_chunk = regender_text_gpt(
            chunk,
            '\n'.join(all_confirmed_roles),
            name_mappings,
            timestamp
        )
        all_regendered_text.append(regendered_chunk)
    
    combined_regendered_text = '\n'.join(all_regendered_text)
    return combined_regendered_text, all_events

def confirm_new_characters(roles_info, confirmed_genders, new_characters):
    """
    Process new characters to confirm their genders and possible name changes.
    Returns: (confirmed_roles, name_mappings, events)
    """
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
            # Store original information before any changes
            original_name = character
            original_gender = gender
            
            # No change: Your existing nice event formatting
            events.append(f"Found new character: {character} ({role_desc})")

            # Get gender choice and possible new name
            standardized_gender, new_name, gender_category = get_user_gender_choice(character, gender)
            confirmed_genders[character] = standardized_gender
            
            events.append(f"  -> Gender set to: {standardized_gender}")

            # Handle name changes and logging
            if new_name != character:
                name_mappings[character] = new_name
                character = new_name
                events.append(f"  -> Character renamed to: {new_name}")
            
            # Create role entry with correct original and updated fields
            role_entry = {
                "Original_Name": original_name,       # Store initial name
                "Original_Role": role_desc,
                "Original_Gender": original_gender,   # Store initial gender
                "Updated_Name": new_name if new_name != original_name else original_name,
                "Updated_Role": role_desc,
                "Updated_Gender": standardized_gender,
                "Gender_Category": gender_category
            }
            
            confirmed_roles.append(f"{character} - {role_desc} - {standardized_gender}")
        else:
            current_gender = confirmed_genders.get(character, gender)
            confirmed_roles.append(f"{character} - {role_desc} - {current_gender}")
    
    return confirmed_roles, name_mappings, events

def get_character_role_from_json(character_name, file_path="character_roles_genders.json"):
    """
    Retrieve a character's role and gender from the JSON file.
    """
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
    """
    Function to load confirmed genders from a JSON file.
    """
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

def load_large_text_file(file_path):
    """
    Function to load a large text file in chunks to avoid memory issues.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            while True:
                chunk = file.read(1024 * 4)  # Read in 4KB chunks
                if not chunk:
                    break
                yield chunk
    except Exception as e:
        print(f"Error reading larger file {file_path}: {e}")
        return

def process_large_text_file(file_path):
    """
    Function to process a large text file by loading it in chunks.
    """
    text = ""
    for chunk in load_large_text_file(file_path):
        text += chunk
    return text

def clean_name(name):
    """
    Function to clean the name by removing any leading numbers and periods.
    """
    return re.sub(r'^\d+\.\s*', '', name).strip()

def main():
    # Clear the terminal (optional)
    print("\033[H\033[J", end="")
    
    # Show application banner
    print_banner()

    # Create an events list at the start to track events in the log file
    events = []
    # Create timestamp for log files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Check API connection
    if not check_openai_api_key():
        return

    # Load and process the text
    input_text = process_large_text_file("test_samples/input_nickname_test.txt")

    if not input_text:
        print(f"{Fore.RED}✗ Failed to load input text.{Style.RESET_ALL}")
        return
    
    # Initialize processing
    print(f"\n{Fore.CYAN}┌─ Initializing...{Style.RESET_ALL}")
    
    # Reset the JSON file
    with open("character_roles_genders.json", 'w', encoding='utf-8') as file:
        json.dump({"Characters": []}, file, ensure_ascii=False, indent=4)
    print(f"{Fore.GREEN}├─ Reset character database{Style.RESET_ALL}")

    # Load confirmed genders
    confirmed_genders = load_confirmed_genders()
    print(f"{Fore.GREEN}├─ Loaded character profiles{Style.RESET_ALL}")

    # Process text chunks
    chunks, character_contexts = improved_chunk_text(input_text)
    print(f"{Fore.GREEN}└─ Split into {Fore.YELLOW}{len(chunks)}{Fore.GREEN} chunks{Style.RESET_ALL}")
    print(f"\n{Fore.CYAN}Starting character analysis...{Style.RESET_ALL}\n")

    # Process chunks, with events
    combined_regendered_text, events = process_chunks_with_context(
        chunks,
        character_contexts,
        confirmed_genders,
        timestamp
    )

    # Log results with descriptive file names
    log_file = f"logs/{timestamp}_regender.log"
    debug_file = f"logs/{timestamp}_debug.log"
    log_output(input_text, combined_regendered_text, events, timestamp=timestamp)
    print(f"\n{Fore.GREEN}✓ Processing complete!{Style.RESET_ALL}")

if __name__ == "__main__":
    main()