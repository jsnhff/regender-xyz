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
        # Make a simple request to the OpenAI API to check if the API key is valid
        client.models.list()
        # print("OpenAI API key is valid.")
    except Exception as e:
        print(f"Error: {e}")
        print("OpenAI API key is invalid or there is an issue with the connection.")

# Call the function to check the API key
check_openai_api_key()

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
    # Create a prompt to instruct GPT to detect character roles and genders.
    prompt = f"Identify all the characters, their roles, and their genders in the following text:\n\n{input_text}\n\nProvide the results in a structured format like: Character - Role - Gender. Arrange the results in a numbered list."
    
    # Get the response from gpt-4o-mini
    response = get_gpt_response(prompt)

    # Extract the list of characters, roles, and genders from the response
    lines = response.split('\n')
    character_list = [line for line in lines if " - " in line]

    return '\n'.join(character_list)

def create_character_roles_genders_json(roles_info, file_path="character_roles_genders.json"):
    """
    Function to create a JSON file with character roles and genders.
    """

    # Split the roles_info into lines and process each line
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

    # Write the JSON data to the file
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump({"Characters": characters}, file, ensure_ascii=False, indent=4)
    print(f"Character roles and genders saved to {file_path}")

def update_character_roles_genders_json(confirmed_roles, file_path="character_roles_genders.json"):
    """
    Function to update the JSON file with confirmed character roles and genders.
    """
    # Load the existing data from the JSON file
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except FileNotFoundError:
        data = {"Characters": []}

    # Update the characters with confirmed roles and genders
    updated_characters = []
    for role in confirmed_roles:
        parts = role.split(" - ")
        if len(parts) == 3:
            new_name, role_desc, new_gender = parts
            new_name = clean_name(new_name)
            updated_characters.append({
                "Original_Name": new_name,
                "Original_Role": role_desc,
                "Original_Gender": new_gender,
                "Updated_Name": new_name,
                "Updated_Role": role_desc,
                "Updated_Gender": new_gender
            })

    # Write the updated JSON data to the file
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump({"Characters": updated_characters}, file, ensure_ascii=False, indent=4)
    print(f"Updated character roles and genders saved to {file_path}")

def regender_text_gpt(input_text, confirmed_roles):
    """
    Function to use GPT-3.5 for regendering the input text.
    """
    # Create a prompt to instruct GPT to regender the text
    prompt = f"""Regender the following text:

    {input_text}

    Roles and genders:
    {confirmed_roles}"""
    
    # Get the response from GPT-3.5
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
    # Create logs directory if it doesn't exist
    if not os.path.exists("logs"):
        os.makedirs("logs")

    # Generate a unique filename using the current date and time
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join("logs", f"log_{timestamp}.txt")

    # Write the output to the file with improved formatting and whitespace
    with open(file_path, 'w') as file:
        for arg in args:
            file.write(str(arg) + "\n\n")
    print(f"Output logged to {file_path}")

def create_highlighted_xml_log(file_path, highlighted_text):
    """
    Function to create an XML log of highlighted changes.
    """
    # Placeholder for actual implementation
    pass

def load_input_text(file_path):
    """
    Function to load input text from a file.
    """
    with open(file_path, 'r') as file:
        return file.read()

def confirm_roles(roles_info, confirmed_genders):
    """
    Function to confirm roles and genders with the user.
    """
    roles = roles_info.splitlines()
    confirmed_roles = []
    for role in roles:
        parts = role.split(" - ")
        if len(parts) != 3:
            print(f"Skipping invalid role format: {role}")
            continue
        character, role_desc, gender = parts
        gender = gender.strip()  # Remove any leading or trailing spaces
        if character in confirmed_genders:
            new_gender = confirmed_genders[character]
            print(f"Using confirmed gender: {new_gender}") #Debug print
        else:
            new_gender = input(f"Enter new gender for {character} (leave blank to keep '{gender}'): ")
            if new_gender:
                confirmed_genders[character] = new_gender
            else:
                new_gender = gender
        confirmed_roles.append(f"{character} - {role_desc} - {new_gender}")
        print(f"Confirmed Roles so far: {confirmed_roles}")  # Debug print
    return '\n'.join(confirmed_roles)

def get_new_name_suggestion(character, new_gender):
    """
    Function to get a new name suggestion based on the character and new gender.
    """
    prompt = f"Suggest one new name for the character '{character}' who is now '{new_gender}'. Provide the single best new name as your response and nothing more."
    response = get_gpt_response(prompt)
    return response.strip()

def chunk_text(text, max_tokens=1000):
    """
    Function to split the text into chunks that fit within the token limits using RecursiveCharacterTextSplitter.
    """
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=max_tokens, chunk_overlap=0)
    chunks = text_splitter.split_text(text)
    return chunks

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

def clean_name(name):
    """
    Function to clean the name by removing any leading numbers and periods.
    """
    return re.sub(r'^\d+\.\s*', '', name).strip()

def main():
    # TODO: Clean up chunking problems with some improvements
    # DONE 1. Chunks end on a word boundary not a sentence boundary
    # DONE 2. Chunks are saved in the log file in a way that is hard to read, breaking formatting of the text
    # DONE 3. Characters and not saved in a way that allows for the regendering of the entire text after one user decision about the gender of each character, the current version asks for a new gender each time
    # 4. Successive chunks are not referencing the same character list and asking the user for input each time
    # 5. The user is not given the option to change the name of the character when changing the gender
    # 6. Gender descriptions are not consistent when identifying characters consider providing a framework to make matching easier
    # 7. Update inputs to be simple selects vs. free form typing
    # 8. Remove array objects storiing roles and rely on the JSON source of truth
    # 9. Chunking is producing an error where characters are changing gender when the user wants to keep them the same

    # Load the input text from a file or user input. Change input to test different scenarios.
    # input_text = load_input_text("input_one_character.txt") # one character test
    # input_text = load_input_text("input_two_characters_related.txt") # two related characters test
    # input_text = load_input_text("input_three_characters_related_dialog.txt") # two related characters dialog test
    # input_text = load_input_text("input_six_characters_related_dialog.txt") # seven related characters dialog test
    input_text = process_large_text_file("input_3_chunk_story_1000.txt")
    if not input_text:
        print("Failed to load input text.")
        return
    print("Input text loaded.")  # Debug print

    # Reset the character_roles_genders.json file to start fresh with each test run
    with open("character_roles_genders.json", 'w', encoding='utf-8') as file:
        json.dump({"Characters": []}, file, ensure_ascii=False, indent=4)
    print("character_roles_genders.json reset to empty.")

    # Load confirmed genders from the JSON file
    confirmed_genders = load_confirmed_genders()
    print("Confirmed genders loaded.")  # Debug print

    # Chunk the input text
    chunks = chunk_text(input_text)
    print(f"Text split into {len(chunks)} chunks.")  # Debug print

    all_roles_info = []
    all_confirmed_roles = []
    all_regendered_text = []

    for i, chunk in enumerate(chunks):
        print(f"Processing chunk {i+1}/{len(chunks)}")  # Debug print

        # Detect roles and genders in the chunk
        roles_info = detect_roles_gpt(chunk)
        if roles_info:
            print("Detected Roles and Genders:")
            print(roles_info)
            all_roles_info.append(roles_info) # Can delete this variable, probably used for log but needs to reference the JSON file

            # Update the JSON file with the identified characters, roles, and genders on first chunk
            if i == 0:
                create_character_roles_genders_json(roles_info)
                print("JSON role file created.")  # Debug print
                confirmed_genders = load_confirmed_genders()

            # Confirm roles and genders with the user
            confirmed_roles = confirm_roles(roles_info, confirmed_genders).splitlines()
            print("Roles confirmed.")  # Debug print
            all_confirmed_roles.append(confirmed_roles)

            # Update the JSON file with confirmed roles and genders
            update_character_roles_genders_json(confirmed_roles)
            confirmed_genders = load_confirmed_genders()

            # Regender the text using GPT with confirmed roles
            regendered_text = regender_text_gpt(chunk, confirmed_roles)
            print("Text regendered.")  # Debug print
            all_regendered_text.append(regendered_text)

    # Combine all chunks
    combined_roles_info = '\n'.join(all_roles_info)
    combined_confirmed_roles = '\n'.join(['\n'.join(roles) for roles in all_confirmed_roles])
    combined_regendered_text = '\n'.join(all_regendered_text)

    # Highlight changes between original and regendered text
    highlighted_text = highlight_changes(input_text, combined_regendered_text) if combined_regendered_text else None
    print("Changes highlighted.")  # Debug print

    # Log the output to files
    log_output(input_text, combined_roles_info, combined_confirmed_roles, combined_regendered_text)
    print("Output logged to unique file in logs folder.")  # Debug print
    if highlighted_text:
        log_output(input_text, combined_roles_info, combined_confirmed_roles, combined_regendered_text, highlighted_text)
        create_highlighted_xml_log("highlighted_log.xml", highlighted_text)
        print("Highlighted log created.")  # Debug print

if __name__ == "__main__":
    main()
