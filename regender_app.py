import os
import time
import difflib
from openai import OpenAI
from datetime import datetime
import json

# Initialize the OpenAI client with your API key
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def check_openai_api_key():
    try:
        # Make a simple request to the OpenAI API to check if the API key is valid
        client.models.list()
        print("OpenAI API key is valid.")
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
                "Name": character,
                "Role": role_desc,
                "Gender": gender
            })

    # Write the JSON data to the file
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump({"Characters": characters}, file, ensure_ascii=False, indent=4)
    print(f"Character roles and genders saved to {file_path}")

def regender_text_gpt(input_text, confirmed_roles):
    """
    Function to use gpt-4o-mini for regendering the input text.
    """
    # Refine the prompt for more clarity and consistency
    prompt = f"""You are a language expert tasked with regendering the characters in the following text.
Please regender the characters in the text according to the characters and genders provided. 
Maintain the storyline, coherence, and consistency of the original text, ensuring only the specified characters' genders are changed.

Text:
{input_text}

Characters and their genders:
{confirmed_roles}

Please ensure the following:
1. Ensure the overall story remains coherent and natural.
2. Do not alter characters whose gender roles are not explicitly listed in the given list of characters.

Provide the updated text below:"""
    
    print(f"Prompt sent to gpt-4o-mini:\n{prompt}")  # Debug print to understand what was sent

    # Get the response from gpt-4o-mini using retries for robustness
    response = get_gpt_response(prompt)
    if "Error" in response:
        print("Failed to get a proper response from gpt-4o-mini.")
        return None

    print(f"Response from gpt-4o-mini:\n{response}")  # Debug print for the response
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

def confirm_roles(roles_info):
    """
    Function to confirm roles and genders with the user.
    """
    roles = roles_info.splitlines()
    confirmed_roles = []
    for role in roles:
        parts = role.split(" - ")
        if len(parts) != 3:
            print(f"Skipping invalid role format.")
            continue
        character, role_desc, gender = parts
        new_gender = input(f"Enter new gender for {character} (leave blank to keep '{gender}'): ")
        if new_gender:
            new_name = get_new_name_suggestion(character, new_gender)
            # print(f"Suggested new name for {character}: {new_name}")
            confirmed_roles.append(f"{new_name} - {role_desc} - {new_gender}")
        else:
            confirmed_roles.append(role)
        print(f"Confirmed Roles so far: {confirmed_roles}")  # Debug print
    return '\n'.join(confirmed_roles)

def get_new_name_suggestion(character, new_gender):
    """
    Function to get a new name suggestion based on the character and new gender.
    """
    prompt = f"Suggest one new name for the character '{character}' who is now '{new_gender}'. Provide the single best new name as your response and nothing more."
    response = get_gpt_response(prompt)
    return response.strip()

def main():
    # Load the input text from a file or user input
    # input_text = load_input_text("input_one_character.txt") # one character test
    input_text = load_input_text("input_two_characters_related.txt") # two related characters test
    print("Input text loaded.")  # Debug print

    # Detect roles and genders in the input text
    roles_info = detect_roles_gpt(input_text)
    if roles_info:
        print("Detected Characters, Roles, and Genders:")
        print(roles_info)

        # Create a JSON file to store all identified characters, roles and genders for reference
        create_character_roles_genders_json(roles_info)

        # Confirm roles and genders with the user
        confirmed_roles = confirm_roles(roles_info)
        print("Roles confirmed.")  # Debug print

        # Regender the text using GPT with confirmed roles
        regendered_text = regender_text_gpt(input_text, confirmed_roles)
        print("Text regendered.")  # Debug print

        # Highlight changes between original and regendered text
        highlighted_text = highlight_changes(input_text, regendered_text) if regendered_text else None
        print("Changes highlighted.")  # Debug print

        # Log the output to files
        log_output(input_text, roles_info, confirmed_roles, regendered_text)
        print("Output logged to unique file in logs folder.")  # Debug print
        if highlighted_text:
            log_output(input_text, roles_info, confirmed_roles, regendered_text, highlighted_text)
            create_highlighted_xml_log("highlighted_log.xml", highlighted_text)
            print("Highlighted log created.")  # Debug print

if __name__ == "__main__":
    main()
