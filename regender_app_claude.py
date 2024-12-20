# TODO: TBD working with Claude

import os
import time
import difflib
from openai import OpenAI
from datetime import datetime
import json
from langchain.text_splitter import RecursiveCharacterTextSplitter
import re
# Add to your imports
from colorama import init, Fore, Back, Style
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
┃  {Fore.YELLOW}transforming gender in open source books{Fore.CYAN}     
┃  {Fore.MAGENTA}[ Version  ]{Fore.CYAN}                      
┃                                           
┃  {Fore.WHITE}✧{Fore.BLUE} Gender Analysis {Fore.WHITE}✧{Fore.GREEN} Name Processing {Fore.WHITE}✧{Fore.CYAN}       
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
    """
    print(f"\n{Fore.CYAN}╭─ Character: {Fore.WHITE}{character} {Fore.YELLOW}({current_gender}){Style.RESET_ALL}")
    print(f"{Fore.CYAN}├─ Select Gender:{Style.RESET_ALL}")
    
    # Display options in a compact, colored format
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
        return current_gender, character
        
    try:
        choice_idx = int(choice) - 1
        category_keys = [k for k in GENDER_CATEGORIES.keys() if k != 'UNK']
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
                
                # Display suggestions in a colored, inline format
                print(f"{Fore.CYAN}│  {Style.RESET_ALL}" + 
                      " | ".join(f"{Fore.YELLOW}{name}{Style.RESET_ALL}" for name in suggested_names))
                print(f"{Fore.CYAN}╰─{Style.RESET_ALL}", end=" ")
                new_name = input("Enter name (↵ to keep current): ").strip()
                if new_name:
                    return selected_gender, new_name
            
            return selected_gender, character
    except ValueError:
        pass
        
    return current_gender, character

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
    Function to use gpt-4o-mini to identify roles, genders, and character details in the input text.
    """
    prompt = f"Identify all the characters, their roles, and their genders in the following text:\n\n{input_text}\n\nProvide the results in a structured format like: Character - Role - Gender. Arrange the results in a numbered list."
    response = get_gpt_response(prompt)
    lines = response.split('\n')
    character_list = [line for line in lines if " - " in line]
    return '\n'.join(character_list)

def create_character_roles_genders_json(roles_info, file_path="character_roles_genders.json"):
    """
    Function to create a JSON file with character roles and genders.
    """
    roles = [line.split(". ", 1)[1] if ". " in line else line for line in roles_info.splitlines()]
    characters = []
    for role in roles:
        parts = role.split(" - ")
        if len(parts) == 3:
            character, role_desc, gender = parts
            characters.append({
                "Original_Name": character,
                "Original_Role": role_desc,
                "Original_Gender": gender
            })

    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump({"Characters": characters}, file, ensure_ascii=False, indent=4)
    print(f"Character roles and genders saved to {file_path}")

def update_character_roles_genders_json(confirmed_roles, file_path="character_roles_genders.json"):
    """
    Updated version to use standardized gender categories.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except FileNotFoundError:
        data = {"Characters": []}

    updated_characters = []
    for role in confirmed_roles:
        parts = role.split(" - ")
        if len(parts) == 3:
            new_name, role_desc, gender = parts
            new_name = clean_name(new_name)
            # Standardize the gender
            category_key, standard_label = standardize_gender(gender)
            updated_characters.append({
                "Original_Name": new_name,
                "Original_Role": role_desc,
                "Original_Gender": gender,
                "Updated_Name": new_name,
                "Updated_Role": role_desc,
                "Updated_Gender": standard_label,
                "Gender_Category": category_key
            })

    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump({"Characters": updated_characters}, file, ensure_ascii=False, indent=4)
    print(f"\n{Fore.GREEN}✓ Updated character roles and genders saved to {file_path}{Style.RESET_ALL}")

def regender_text_gpt(input_text, confirmed_roles, name_mappings=None):
    """
    Updated version to handle explicit name changes.
    """
    if name_mappings is None:
        name_mappings = {}
        
    gender_guidelines = []
    name_instructions = []
    
    for role in confirmed_roles.splitlines():
        parts = role.split(" - ")
        if len(parts) == 3:
            character, role_desc, gender = parts
            category_key, _ = standardize_gender(gender)
            if category_key in GENDER_CATEGORIES:
                pronouns = GENDER_CATEGORIES[category_key]['pronouns']
                gender_guidelines.append(f"{character}: {gender} (pronouns: {'/'.join(pronouns)})")
    
    # Add explicit name change instructions
    for old_name, new_name in name_mappings.items():
        name_instructions.append(f"Replace all instances of '{old_name}' with '{new_name}'")

    prompt = (
        f"Regender the following text, following these rules exactly:\n\n"
        f"1. Name changes (apply these first and consistently):\n{chr(10).join(name_instructions)}\n\n"
        f"2. Character genders and pronouns:\n{chr(10).join(gender_guidelines)}\n\n"
        f"3. Maintain absolute consistency in names and pronouns throughout the text.\n\n"
        f"Text to regender:\n{input_text}"
    )
    
    response = get_gpt_response(prompt)
    return response

def highlight_changes(original_text, regendered_text):
    """
    Function to highlight changes between original and regendered text.
    """
    return '\n'.join(difflib.unified_diff(original_text.splitlines(), regendered_text.splitlines()))

def log_output(*args):
    """
    Function to log the output to a file with a unique name in the logs folder.
    """
    if not os.path.exists("logs"):
        os.makedirs("logs")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join("logs", f"log_{timestamp}.txt")

    with open(file_path, 'w') as file:
        for arg in args:
            file.write(str(arg) + "\n\n")
    print(f"Output logged to {file_path}")

def create_highlighted_xml_log(file_path, highlighted_text):
    """
    Function to create an XML log of highlighted changes.
    """
    pass

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

def process_chunks_with_context(chunks, character_contexts, confirmed_genders):
    """
    Updated processing with enhanced visual feedback.
    """
    all_regendered_text = []
    name_mappings = {}
    
    total_chunks = len(chunks)
    
    for i, (chunk, context) in enumerate(zip(chunks, character_contexts)):
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
                confirmed_roles, chunk_name_mappings = confirm_new_characters(
                    roles_info, confirmed_genders, new_characters
                )
                name_mappings.update(chunk_name_mappings)
                update_character_roles_genders_json(confirmed_roles)
        
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
            chunk, '\n'.join(all_confirmed_roles), name_mappings
        )
        all_regendered_text.append(regendered_chunk)
    
    return '\n'.join(all_regendered_text)

def confirm_new_characters(roles_info, confirmed_genders, new_characters):
    """
    Updated version to handle both gender and name changes.
    """
    confirmed_roles = []
    name_mappings = {}  # Store character name changes
    
    for role in roles_info.splitlines():
        parts = role.split(" - ")
        if len(parts) != 3:
            continue
            
        character, role_desc, gender = parts
        character = clean_name(character)
        
        if character in new_characters:
            # Get both gender and possible name change
            standardized_gender, new_name = get_user_gender_choice(character, gender)
            confirmed_genders[character] = standardized_gender
            if new_name != character:
                name_mappings[character] = new_name
                character = new_name
        
        current_gender = confirmed_genders.get(character, gender)
        confirmed_roles.append(f"{character} - {role_desc} - {current_gender}")
    
    return confirmed_roles, name_mappings

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
    
    # Check API connection
    if not check_openai_api_key():
        return

    # Load and process the text
    input_text = process_large_text_file("input_3_chunk_story_1000.txt")
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

    # Process chunks
    combined_regendered_text = process_chunks_with_context(chunks, character_contexts, confirmed_genders)

    # Log results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"logs/log_{timestamp}.txt"
    log_output(input_text, combined_regendered_text)
    print(f"\n{Fore.GREEN}✓ Processing complete!{Style.RESET_ALL}")
    print(f"{Fore.BLUE}ℹ Output saved to: {Fore.YELLOW}{log_file}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()