import os
import time
import difflib
from openai import OpenAI
from datetime import datetime

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

def get_gpt_response(prompt, model="gpt-3.5-turbo", temperature=0.7, retries=3, delay=5):
    """
    Function to interact with OpenAI's GPT-3.5 API using the chat endpoint.
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
    Function to use GPT-3.5 to identify roles, genders, and character details in the input text.
    """
    # Create a prompt to instruct GPT to detect character roles and genders.
    prompt = f"Identify all the characters, their roles, and their genders in the following text:\n\n{input_text}\n\nProvide the results in a structured format like: Character - Role - Gender."
    
    # Get the response from GPT-3.5
    response = get_gpt_response(prompt)
    return response

def regender_text_gpt(input_text, confirmed_roles, target_gender="female"):
    """
    Function to use GPT-3.5 for regendering the input text.
    """
    # Create a prompt to instruct GPT to regender the text
    prompt = f"""Regender the following text to {target_gender}:

{input_text}

Roles and genders:
{confirmed_roles}
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
        character, role_desc, gender = role.split(" - ")
        print(f"Character: {character}, Role: {role_desc}, Current Gender: {gender}")
        new_gender = input(f"Enter new gender for {character} (leave blank to keep '{gender}'): ")
        if new_gender:
            confirmed_roles.append(f"{character} - {role_desc} - {new_gender}")
        else:
            confirmed_roles.append(role)
        print(f"Confirmed Roles so far: {confirmed_roles}")  # Debug print
    return '\n'.join(confirmed_roles)

def main():
    # Load the input text from a file or user input
    input_text = load_input_text("input.txt")
    print("Input text loaded.")  # Debug print

    # Detect roles and genders in the input text
    roles_info = detect_roles_gpt(input_text)
    if roles_info:
        print("Detected Roles and Genders:")
        print(roles_info)

        # Confirm roles and genders with the user
        confirmed_roles = confirm_roles(roles_info)
        print("Roles confirmed.")  # Debug print

        # Regender the text using GPT with confirmed roles
        regendered_text = regender_text_gpt(input_text, confirmed_roles, target_gender="female")
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
