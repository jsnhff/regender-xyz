import os
import time
import difflib
from openai import OpenAI
from datetime import datetime
import json
from langchain.text_splitter import RecursiveCharacterTextSplitter
import re

# Initialize the OpenAI client with your API key
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def check_openai_api_key():
    try:
        client.models.list()
    except Exception as e:
        print(f"Error: {e}")
        print("OpenAI API key is invalid or there is an issue with the connection.")

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
    Enhanced gender selection interface that also handles name changes.
    """
    print(f"\nCharacter: {character}")
    current_category, current_label = standardize_gender(current_gender)
    print(f"Current gender: {current_label}")
    
    print("\nOptions:")
    for i, (key, data) in enumerate(GENDER_CATEGORIES.items(), 1):
        if key != 'UNK':  # Don't show UNK as an explicit option
            print(f"{i}. {data['label']}")
    print("Enter to keep current")
    
    choice = input("Select option (1-3, or Enter to keep current): ").strip()
    
    if not choice:  # Keep current
        return current_label, character
        
    try:
        choice_idx = int(choice) - 1
        category_keys = [k for k in GENDER_CATEGORIES.keys() if k != 'UNK']
        if 0 <= choice_idx < len(category_keys):
            selected_key = category_keys[choice_idx]
            selected_gender = GENDER_CATEGORIES[selected_key]['label']
            
            # Ask for new name if gender changed
            if selected_gender.lower() != current_label.lower():
                print(f"\nSuggested names for {selected_gender} version of {character}:")
                suggested_name = get_gpt_response(
                    f"Suggest three {selected_gender.lower()} versions of the name '{character}'. "
                    f"Provide only the names separated by commas, no explanation."
                )
                print(f"Suggestions: {suggested_name}")
                new_name = input(f"Enter new name for {character} (press Enter to keep current name): ").strip()
                if new_name:
                    return selected_gender, new_name
            
            return selected_gender, character
    except ValueError:
        pass
        
    return current_label, character

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
    print(f"Updated character roles and genders saved to {file_path}")

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
    Function to load input text from a file.
    """
    with open(file_path, 'r') as file:
        return file.read()

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
    Updated version to handle name mappings across chunks.
    """
    all_regendered_text = []
    name_mappings = {}
    
    for i, (chunk, context) in enumerate(zip(chunks, character_contexts)):
        print(f"\nProcessing chunk {i+1}/{len(chunks)}")
        print(f"Characters in this chunk: {', '.join(context['characters'])}")
        
        # Only ask for gender confirmation for new characters
        new_characters = context['characters'] - set(confirmed_genders.keys())
        if new_characters:
            print(f"\nNew characters detected: {', '.join(new_characters)}")
            
            # Detect roles for new characters only
            roles_info = detect_roles_gpt(chunk)
            if roles_info:
                confirmed_roles, chunk_name_mappings = confirm_new_characters(
                    roles_info, confirmed_genders, new_characters
                )
                name_mappings.update(chunk_name_mappings)
                update_character_roles_genders_json(confirmed_roles)
        
        # Use all confirmed characters for regendering
        all_confirmed_roles = []
        for character in context['all_characters_so_far']:
            if character in confirmed_genders:
                role_info = get_character_role_from_json(character)
                if role_info:
                    # Use new name if available
                    current_name = name_mappings.get(character, character)
                    all_confirmed_roles.append(
                        f"{current_name} - {role_info['role']} - {role_info['gender']}"
                    )
        
        # Regender the chunk using all confirmed character information
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
        print(f"Confirmed genders loaded from {file_path}")
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
    # Load the input text
    input_text = process_large_text_file("input_3_chunk_story_1000.txt")
    if not input_text:
        print("Failed to load input text.")
        return
    print("Input text loaded.")

    # Reset the character_roles_genders.json file
    with open("character_roles_genders.json", 'w', encoding='utf-8') as file:
        json.dump({"Characters": []}, file, ensure_ascii=False, indent=4)
    print("character_roles_genders.json reset to empty.")

    # Load confirmed genders
    confirmed_genders = load_confirmed_genders()
    print("Confirmed genders loaded.")

    # Use improved chunking
    chunks, character_contexts = improved_chunk_text(input_text)
    print(f"Text split into {len(chunks)} chunks with character tracking.")

    # Process all chunks with context
    combined_regendered_text = process_chunks_with_context(chunks, character_contexts, confirmed_genders)

    # Highlight changes
    highlighted_text = highlight_changes(input_text, combined_regendered_text)

    # Log outputs
    log_output(input_text, combined_regendered_text, highlighted_text)
    if highlighted_text:
        create_highlighted_xml_log("highlighted_log.xml", highlighted_text)

if __name__ == "__main__":
    main()